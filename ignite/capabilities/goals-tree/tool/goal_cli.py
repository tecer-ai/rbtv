#!/usr/bin/env python3
"""rbtv-goal — the goals-tree machinery (task 7.63).

Five verbs over the CMP-4 goals tree, all LOCAL file operations (they work with
the daemon down, which is why they live on the rbtv side and never on ignite):

    rbtv-goal scaffold <goal-name> --contract FILE|-  [--type T] [--kind K] [--due DATE] [--dry-run]
    rbtv-goal reindex
    rbtv-goal lint <goal-name>
    rbtv-goal materialize <goal-name> [--catalog-root DIR] [--force] [--dry-run]
    rbtv-goal gate-key-check <goal-name> --pass-folder NAME [--override ANCHOR]
    rbtv-goal branch-home <goal-name> [--parent REL] [--branch branch-M] [--dry-run]

Grammar is owner-ruled (r-763-grammar-ruled, all four items at their recommended
defaults) and is implemented here, not re-derived. Exit codes follow the sd-graph
convention: 0 success/clean, 1 refusal/gate-fail/not-found, 2 usage error — and
`gate-key-check` extends it by exactly one: 3 flagged-pass (it never uses 2,
which argparse reserves for a mistyped flag).

v1 ships standalone; it folds into `rbtv goal <verb>` verbatim when task 7.65
lands (the operator-surface stand-in pattern — no contract change at fold-in).
"""

from __future__ import annotations

import argparse
import ast
import csv
import datetime as _dt
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------- constants

GOAL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

GOAL_TYPES = ("one-shot", "recurring")
GOAL_STATUSES = ("briefed", "active", "standing", "completed", "abandoned")

# Owner ruling d-owner-batch1 (2), 2026-08-08: `goal-kind` is OPTIONAL goal.md frontmatter
# defaulting to `interactive`, and the carrier is the FRONTMATTER — no queue-row carrier.
#
# The enum lives HERE because this module already owns GOAL_TYPES/GOAL_STATUSES and is the
# creation verb. `goal_creation_request.py` keeps its own literal copy ON PURPOSE (its own
# stated convention for GOAL_NAME_RE: importing would couple the request layer's contract to a
# tool's internals) — that duplication is deliberate, not drift.
#
# OPTIONAL is load-bearing in two places and nowhere else: `goal-kind` is NOT in lint's
# identity-fields tuple (a pre-existing goal carries no such key and must stay lint-green,
# exactly like `due-date`), and every consumer that ASKS for a kind reads it through the ONE
# defaulting helper rather than defaulting for itself.
GOAL_KINDS = ("interactive", "non-interactive")
GOAL_KIND_DEFAULT = "interactive"

# goals-index schema (concept goals-index § file schema)
#
# ⚠ DIVERGENCE TO TRANSCRIBE, NOT A DRIFT: the registry's `concepts/goals-index.md` file-schema
# block enumerates five columns and is marked `design-intent` — it was written before `goal-kind`
# existed. Its DEFINITION ("a FULL deterministic projection of each goal's goal.md frontmatter")
# is what governs here: a frontmatter field the projection omits would make the index partial.
# The column list needs a registry-side update; the registry is never edited from this build.
GOALS_INDEX_COLUMNS = ["name", "creation date", "due date", "type", "goal-kind", "status"]
# run-log schema (concept run-log § file schema)
RUNS_COLUMNS = ["run-id", "type", "state", "taskforce-id(s)", "opened", "closed"]

# threads-store schema (concept threads-store § file schema)
THREADS_SCHEMA = """\
-- threads.sql — the goal-scoped message/completion store (concept: threads-store).
-- One row per message sent or received under this goal. Created empty at scaffold.
CREATE TABLE IF NOT EXISTS threads (
    message_id  TEXT PRIMARY KEY,
    reply_to    TEXT,            -- answer rows only: the message-id answered
    session_id  TEXT,            -- tracing column; resolves the run via runs.csv
    sender      TEXT NOT NULL,   -- a seat, set by the identity gate
    recipient   TEXT NOT NULL,
    corpus      TEXT NOT NULL,
    type        TEXT NOT NULL CHECK (type IN
                  ('completion','ask','answer','verdict','note')),
    sent_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS threads_recipient_idx ON threads (recipient);
CREATE INDEX IF NOT EXISTS threads_reply_to_idx  ON threads (reply_to);
"""

# INVOKED kinds enter an assembly as loader stubs (description + entry-point
# pointer) and are always @latest; every other kind is ASSEMBLED — its full
# content is inlined and its reference frozen (d-seat-assembled-projection).
INVOKED_KINDS = ("capability", "reference")

# Frontmatter keys of a taskforce.csv row that form the executor binding.
BINDING_COLUMNS = ("harness", "model", "effort", "ctx-refresh")

# Registry divergence 5 — the version-string STAND-IN. CMP-5's repo-root
# `cognitive-units-index.csv` (version-id -> commit, filepath) does not exist;
# until it does, a frozen `@latest` records a content digest under this prefix so
# the marker is greppable and can never be mistaken for the settled schema.
STANDIN_VERSION_PREFIX = "standin-sha256:"


class Refusal(Exception):
    """Exit 1 — a refusal, gate-fail, or not-found. Never a crash."""


# ---------------------------------------------------------------- helpers


def _today() -> str:
    return _dt.date.today().isoformat()


def split_frontmatter(text: str, path: Path) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Raises Refusal naming the file."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise Refusal(f"{path}: no YAML frontmatter block")
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise Refusal(f"{path}: frontmatter is not valid YAML — {exc}") from exc
    if not isinstance(fm, dict):
        raise Refusal(f"{path}: frontmatter is not a mapping")
    return fm, text[m.end():]


def read_goal_md(goal_dir: Path) -> tuple[dict, str]:
    gm = goal_dir / "goal.md"
    if not gm.is_file():
        raise Refusal(f"{gm}: missing goal.md (the goal-descriptor)")
    return split_frontmatter(gm.read_text(encoding="utf-8"), gm)


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    """Write a csv atomically with LF endings — a projection is machine-owned."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow({c: row.get(c, "") for c in columns})
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8", newline="")
    tmp.replace(path)


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        raise Refusal(f"{path}: missing")
    with path.open(encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def resolve_goals_root(explicit: str | None) -> Path:
    """The `.rbtv/goals` root. Explicit --root wins; else walk up from cwd.

    An explicit root is how a caller aims a WRITE verb at a test tree instead of
    a live package, so it is never inferred when the caller supplied one.
    """
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not root.is_dir():
            raise Refusal(f"--root {root}: not a directory")
        return root
    here = Path.cwd().resolve()
    for cand in (here, *here.parents):
        goals = cand / ".rbtv" / "goals"
        if goals.is_dir():
            return goals.resolve()
    raise Refusal(
        "no .rbtv/goals root found by walking up from the working directory — "
        "pass --root explicitly"
    )


def resolve_goal_dir(root: Path, name: str) -> Path:
    """`root / name`, refused whenever the result is not a folder DIRECTLY under root.

    `Path.__truediv__` discards the left operand when the right one is absolute, so an
    absolute `goal_name` escapes `--root` entirely — the verb then reads, and materialize
    WRITES, outside the declared root while still reporting ok. `..` segments walk out the
    same way. A goal name is one folder name under the root, never a path, so anything that
    does not resolve to a direct child of root is refused before any read or write.
    """
    goal_dir = (root / name).resolve()
    if goal_dir.parent != root or goal_dir == root:
        raise Refusal(
            f"goal name '{name}' escapes --root {root} (resolves to {goal_dir}) — a goal "
            "name is a single folder name directly under the root, never a path"
        )
    return goal_dir


def unit_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- reindex


def project_goals(root: Path) -> list[dict]:
    """One row per goal, projected from every goal.md frontmatter.

    Fail loud: a projection that silently drops a goal is corruption, so an
    unparseable goal.md aborts the whole projection naming the file.
    """
    rows = []
    for goal_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (goal_dir / "goal.md").is_file():
            continue
        fm, _ = read_goal_md(goal_dir)
        rows.append(
            {
                "name": fm.get("name", ""),
                "creation date": fm.get("creation-date", fm.get("creation date", "")),
                "due date": fm.get("due-date", fm.get("due date", "")),
                "type": fm.get("type", ""),
                # PROJECTED, NOT DEFAULTED — deliberately unlike a consumer read. The index is a
                # projection of what each descriptor SAYS, so a goal that declares no kind
                # projects empty (the `due date` idiom above), and the ONE place absence becomes
                # `interactive` is the read helper every consumer goes through. Defaulting here
                # too would put the ruled default in two files free to disagree.
                "goal-kind": fm.get("goal-kind", ""),
                "status": fm.get("status", ""),
            }
        )
    return rows


def cmd_reindex(args) -> int:
    root = resolve_goals_root(args.root)
    rows = project_goals(root)  # raises before anything is written
    target = root / "goals.csv"
    if args.json:
        print(json.dumps({"ok": True, "file": str(target), "goals": rows}, indent=2))
    write_csv(target, GOALS_INDEX_COLUMNS, rows)
    if not args.json:
        print(f"reindexed {target} — {len(rows)} goal(s)")
    return 0


# ---------------------------------------------------------------- scaffold


def cmd_scaffold(args) -> int:
    root = resolve_goals_root(args.root)
    name = args.goal_name

    if not GOAL_NAME_RE.match(name):
        raise Refusal(
            f"goal name '{name}' violates the naming rule — lowercase kebab-case "
            "([a-z0-9] words joined by single hyphens)"
        )
    if args.type not in GOAL_TYPES:
        raise Refusal(f"--type {args.type}: must be one of {', '.join(GOAL_TYPES)}")

    # `getattr` because the field is OPTIONAL at the contract level, and this function is called
    # directly with a Namespace by selftest and by the request handler's argv — a caller that
    # names no kind gets the ruled default rather than an AttributeError. Validated anyway:
    # argparse's `choices` does not run on a hand-built Namespace.
    kind = getattr(args, "kind", None) or GOAL_KIND_DEFAULT
    if kind not in GOAL_KINDS:
        raise Refusal(f"--kind {kind}: must be one of {', '.join(GOAL_KINDS)}")

    goal_dir = root / name
    if goal_dir.exists():
        raise Refusal(
            f"{goal_dir}: already exists — scaffold is create-only and never overwrites"
        )

    # G-118: the read is GUARDED. An unreadable `--contract` (absent file, a directory, a
    # permission denial) used to escape `main()` — which catches `Refusal` only — as a raw
    # FileNotFoundError/IsADirectoryError traceback, breaking the never-a-crash contract the
    # README's exit-code table states (`1` refusal/not-found, never an unhandled exception).
    # Every OTHER path-taking verb already refuses cleanly, so the defect is this one read,
    # not a missing global handler: the narrow guard is the whole fix.
    try:
        contract = (
            sys.stdin.read() if args.contract == "-"
            else Path(args.contract).read_text(encoding="utf-8")
        )
    except OSError as exc:
        raise Refusal(f"--contract {args.contract}: {exc.strerror or exc}") from exc
    if not contract.strip():
        raise Refusal("--contract resolved to empty text — a goal is born with its contract")

    fm = {
        "name": name,
        "creation-date": _today(),
        "due-date": args.due or "",
        "type": args.type,
        "goal-kind": kind,
        "status": "briefed",
    }
    goal_md = (
        "---\n"
        + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
        + "---\n\n"
        + contract.strip()
        + "\n"
    )

    plan = {
        "goal": name,
        "root": str(root),
        "creates": [
            str(goal_dir / f) for f in ("goal.md", "decisions.md", "runs.csv", "threads.sql")
        ],
        "then": f"reindex {root / 'goals.csv'}",
    }
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, **plan}, indent=2)
              if args.json else
              f"dry-run: would create {goal_dir}/ "
              f"(goal.md, decisions.md, runs.csv, threads.sql) then reindex")
        return 0

    goal_dir.mkdir(parents=True)
    (goal_dir / "goal.md").write_text(goal_md, encoding="utf-8", newline="\n")
    (goal_dir / "decisions.md").write_text(
        f"# decisions — {name}\n\nGoal-scoped decision log. Empty at scaffold.\n",
        encoding="utf-8", newline="\n",
    )
    write_csv(goal_dir / "runs.csv", RUNS_COLUMNS, [])
    (goal_dir / "threads.sql").write_text(THREADS_SCHEMA, encoding="utf-8", newline="\n")

    write_csv(root / "goals.csv", GOALS_INDEX_COLUMNS, project_goals(root))

    if args.json:
        print(json.dumps({"ok": True, **plan}, indent=2))
    else:
        print(f"scaffolded {goal_dir} — goal.md, decisions.md, runs.csv, threads.sql")
        print(f"reindexed {root / 'goals.csv'}")
    return 0


# ---------------------------------------------------------------- lint


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, check: str, file: str, reason: str) -> None:
        self.items.append({"check": check, "file": file, "reason": reason})

    def __bool__(self) -> bool:
        return bool(self.items)


def current_run_dir(goal_dir: Path, f: Findings) -> Path | None:
    """The goal's current run, resolved through runs.csv (7.37 owns the machinery;
    lint only reads its result). Falls back to the highest-numbered run folder when
    runs.csv carries no open row, and says so."""
    runs_csv = goal_dir / "runs.csv"
    open_ids = []
    if runs_csv.is_file():
        try:
            for row in read_csv(runs_csv):
                state = (row.get("state") or "").strip().lower()
                closed = (row.get("closed") or "").strip()
                if state not in ("completed", "failed") and not closed:
                    open_ids.append((row.get("run-id") or "").strip())
        except Refusal as exc:
            f.add("runs.csv parses", str(runs_csv), str(exc))
            return None
    if len(open_ids) > 1:
        f.add(
            "one live run per goal", str(runs_csv),
            f"{len(open_ids)} runs are open at once: {', '.join(open_ids)}",
        )
    runs_dir = goal_dir / "runs"
    if not runs_dir.is_dir():
        return None
    for rid in open_ids:
        cand = runs_dir / rid
        if cand.is_dir():
            return cand
    # G-117: highest-numbered means NUMERICALLY highest. A lexicographic sort on the folder
    # name returned `run-9` while `run-11` existed — latent while a goal had fewer than ten
    # runs and certain to fire at run-10. `RUN_NAME_RE` (defined with the branch-numbering
    # rule below) is the repo's one spelling of a run folder name, so the ordering key and
    # the `branch-{M+1}` mint now read the suffix the same way. A name that is not
    # `run-<digits>` carries no number to be highest, so it no longer enters the ordering
    # at all — the fallback returns None instead of a folder whose position was an accident.
    numbered = [(int(m.group(1)), p) for p in runs_dir.iterdir()
                if p.is_dir() and (m := RUN_NAME_RE.match(p.name))]
    return max(numbered)[1] if numbered else None


# ---------------------------------------------------------------- branch home (MC8 / 7.450)
#
# The registry SETTLES this shape; nothing here invents it. `concepts/branch.md`
# (settled-by d-branch-family): *"their files live under the parent run's branches
# folder (`runs/run-{n}/branches/branch-{m}/`), each branch folder shaped exactly
# like a run folder, recursively — a branch may carry its own `branches/`"*.
#
# THE NUMBERING RULE, stated before it runs: `branch-{M+1}` where M is the largest
# integer suffix among the entries directly under this parent's `branches/` whose
# NAME matches `branch-<digits>` exactly, and M = 0 when none exists. It is a
# pure function of that listing — two calls over the same state return the same
# name — and it never reuses a number while the higher-numbered folder is present.
#
# This resolver MINTS THE HOME AND NOTHING ELSE. Filling that home with a run
# folder's contents (taskforce.csv, seat folders) is the materialization step's
# (MC10), which is why nothing here writes a file.

BRANCHES_DIR_NAME = "branches"
BRANCH_NAME_RE = re.compile(r"^branch-(\d+)$")
RUN_NAME_RE = re.compile(r"^run-(\d+)$")


def branch_parent_kind(parent: Path) -> str | None:
    """`"run"`, `"branch"`, or None — what the path itself says the parent is.

    A branch homes under a RUN folder (`runs/run-{n}`) or, recursively, under
    another BRANCH folder (`branches/branch-{m}`). Both the folder name and its
    holder are checked: a bare directory called `run-1` sitting outside a `runs/`
    layout is not a run folder, and admitting it would put `branches/` somewhere
    the registry's path never reaches.
    """
    holder = parent.parent.name
    if RUN_NAME_RE.match(parent.name) and holder == "runs":
        return "run"
    if BRANCH_NAME_RE.match(parent.name) and holder == BRANCHES_DIR_NAME:
        return "branch"
    return None


def next_branch_name(branches_dir: Path) -> str:
    """The numbering rule above, over one directory listing.

    A matching NAME counts whatever the entry is. Counting only directories would
    let a stray `branches/branch-4` FILE stay invisible to the numbering and then
    block the mint as a collision several branches later.
    """
    used = []
    if branches_dir.is_dir():
        for p in branches_dir.iterdir():
            m = BRANCH_NAME_RE.match(p.name)
            if m:
                used.append(int(m.group(1)))
    return f"branch-{max(used, default=0) + 1}"


def resolve_branch_home(parent: Path, branch: str | None = None,
                        create: bool = True) -> Path:
    """The branch home under `parent`, minted create-only. Returns its path.

    `branch` names the folder explicitly (a caller that already knows the id);
    omitted, it is auto-numbered. CREATE-ONLY: an existing home is REFUSED, never
    reused and never written into — `mkdir` runs without `exist_ok`, so the refusal
    holds even against a folder that appears between the check and the create.
    """
    parent = parent.resolve()
    if not parent.is_dir():
        raise Refusal(f"{parent}: no such parent run/branch folder")
    kind = branch_parent_kind(parent)
    if kind is None:
        raise Refusal(
            f"{parent}: not a run folder or a branch folder — a branch homes under "
            f"`runs/run-{{n}}/` or, recursively, under `{BRANCHES_DIR_NAME}/branch-{{m}}/` "
            "(concepts/branch.md, settled-by d-branch-family). Nothing was created."
        )
    branches_dir = parent / BRANCHES_DIR_NAME
    if branch is None:
        branch = next_branch_name(branches_dir)
    elif not BRANCH_NAME_RE.match(branch):
        raise Refusal(
            f"branch name '{branch}' violates the settled form `branch-{{m}}` "
            "(concepts/branch.md) — m is an integer"
        )
    home = branches_dir / branch
    if home.exists():
        raise Refusal(
            f"{home}: already exists — minting a branch home is create-only and "
            "never overwrites, reuses or writes into an existing home"
        )
    if create:
        home.mkdir(parents=True)   # no exist_ok: the create IS the collision check
    return home


def cmd_branch_home(args) -> int:
    root = resolve_goals_root(args.root)
    goal_dir = resolve_goal_dir(root, args.goal_name)
    if not goal_dir.is_dir():
        raise Refusal(f"{goal_dir}: no such goal folder")

    if args.parent:
        # Same hazard resolve_goal_dir guards: an absolute right operand discards
        # the left one, and `..` walks out — either would mint outside the goal.
        parent = (goal_dir / args.parent).resolve()
        if not parent.is_relative_to(goal_dir) or parent == goal_dir:
            raise Refusal(
                f"--parent '{args.parent}' resolves to {parent}, outside the goal folder "
                f"{goal_dir} — it is a path RELATIVE to the goal folder, never an escape"
            )
    else:
        f = Findings()
        parent = current_run_dir(goal_dir, f)
        if parent is None:
            raise Refusal(f"{goal_dir}: no run compartment — nothing to home a branch under")

    home = resolve_branch_home(parent, args.branch, create=not args.dry_run)
    payload = {
        "ok": True,
        "goal": args.goal_name,
        "parent": str(parent),
        "parent_kind": branch_parent_kind(parent),
        "branch": home.name,
        "home": str(home),
    }
    if args.dry_run:
        payload["dry_run"] = True
    if args.json:
        print(json.dumps(payload, indent=2))
    elif args.dry_run:
        print(f"dry-run: would mint {home}")
    else:
        print(f"minted {home}")
    return 0


# ------------------------------------- the `after` MEMBER grammar (7.426 / W3)
#
# ⚠ THE PROOF SURFACE OF THIS ARM IS THE TEST GOAL, AND NOTHING HERE IS WIRED INTO
# THE LIVE ROOM. `check_after_grammar` runs where a VERB invokes it — the two
# no-act verbs `lint` and `check-acyclic`, and, since 7.456/MC14, the `materialize`
# ACT itself, which now REFUSES rather than reporting. No daemon lane, no job and no
# watcher calls it, and materializing a live-room goal remains an authored act.
# Live-room adoption is a separate, later act behind `r-cutover-gated`. See README.md
# § "The guard-grammar arm (7.426) and its carve-out" for the full statement.
#
# ⚠ ONE DECOMPOSITION, IMPORTED. The member grammar `<seat>[<key>=<value>]` is
# decomposed in exactly one place in this system — `coord.py`'s
# `parse_after_member` (7.424/W1 collapsed the two readings that used to exist).
# This module IMPORTS it. A copy here would be the third reading, and the defect
# W1 closed is precisely "which parse a consumer got depended on which function it
# called". `_module_level_literals` reads coord.py by AST for a different reason —
# it needs module-level LITERALS, which do not require execution; a grammar does.

_AFTER_GRAMMAR = None


def after_member_grammar():
    """`coord.py`'s `parse_after_member`, imported. Refuses rather than degrading.

    `coord.py` imports `budget` from its own directory, so that directory goes on
    `sys.path` for the exec and comes straight back off — the "not importable from
    an arbitrary cwd" this module records elsewhere is a CWD problem, not an
    importability one (measured: 0.13s, no side effects; it launches nothing,
    writes nothing, messages nobody).

    Every failure to reach the grammar is a `Refusal`. A grammar arm that silently
    passed when it could not read the grammar would report CLEAN over a file whose
    guards were never checked — the vacuous-clean class `check_acyclic` exists to
    close, rebuilt one layer up.
    """
    global _AFTER_GRAMMAR
    if _AFTER_GRAMMAR is not None:
        return _AFTER_GRAMMAR
    import importlib.util

    coord_path = coord_source_path()
    if not coord_path.is_file():
        raise Refusal(
            f"{coord_path}: the after-member grammar source is absent, so NO guard-grammar "
            f"claim can be made about any manifest. This check imports "
            f"`parse_after_member` (7.424) and never re-implements it.")
    spec = importlib.util.spec_from_file_location("_coord_after_grammar", coord_path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(coord_path.parent))
    # `lint` WRITES NOTHING, EVER, and an import is otherwise a write: measured, a
    # plain exec_module drops three `.pyc` files into `team-kit/__pycache__/`. They
    # are gitignored and harmless, and that is exactly the argument that erodes a
    # read-only contract one exception at a time. Suppressed, then restored.
    bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # any import-time failure of a 20k-line module
        raise Refusal(
            f"{coord_path}: the after-member grammar source did not import "
            f"({exc.__class__.__name__}: {exc}), so NO guard-grammar claim can be made.")
    finally:
        sys.dont_write_bytecode = bytecode
        sys.path.remove(str(coord_path.parent))
    fn = getattr(mod, "parse_after_member", None)
    if not callable(fn):
        raise Refusal(
            f"{coord_path}: `parse_after_member` is absent or not callable — the grammar "
            f"this check imports has moved or been renamed; NO claim can be made.")
    _AFTER_GRAMMAR = fn
    return fn


def after_cell_members(raw: str) -> list[str]:
    """The CELL grammar: comma-separated members, exactly as `taskforce_after` splits."""
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


def after_member_limbs(member: str) -> list[str]:
    """The alternates of ONE member: `a|b` -> `['a', 'b']`, `a[g=y]` -> `['a[g=y]']`.

    ⚠ THE ORDER IS LOAD-BEARING and is `_manifest_after_ids`' own: bracketed content
    is neutralised BEFORE the alternate split, so a `|` INSIDE a guard value never
    reads as an alternate. Cutting the other way round is the strip-then-split defect
    (#3386) this file used to carry: `a[g=y]|b` truncated at the first `[` and limb
    `b` vanished from the graph — an edge never traversed, reported clean.

    Blanked positionally rather than removed, so each limb is sliced from the
    ORIGINAL text and keeps its own guard for the member-grammar read below.
    """
    blanked = re.sub(r"\[[^\]]*\]", lambda m: "\0" * len(m.group(0)), member)
    limbs, start = [], 0
    for i, ch in enumerate(blanked):
        if ch == "|":
            limbs.append(member[start:i])
            start = i + 1
    limbs.append(member[start:])
    return limbs


def after_pred_names(raw: str) -> list[str]:
    """Every predecessor NAME an `after` cell declares — guards stripped, alternates
    expanded, through the imported grammar. The one edge-extraction of this module.

    A limb whose guard is malformed keeps its WHOLE token as the name, so it lands as
    an unresolvable edge rather than being silently dropped. `check_after_grammar`
    names the grammar rule it broke; this one refuses to pretend the graph was read.
    """
    parse = after_member_grammar()
    names = []
    for member in after_cell_members(raw):
        for limb in after_member_limbs(member):
            if not limb.strip():
                continue
            names.append(parse(limb)[0] or limb.strip())
    return names


# The rules, stated once. A refusal message NAMES the rule it violated: the `check`
# string IS the rule, and the reason carries the offending token.
RULE_GUARD_GRAMMAR = "guard grammar `ref[field=value]`"
RULE_ALTERNATE_GRAMMAR = "alternate grammar `a|b`"


def check_after_grammar(rows: list[dict], f: Findings, path: Path,
                        id_col: str = "seat", after_col: str = "after") -> None:
    """Guard grammar + alternates, validated ON TOP OF acyclicity (7.426 / W3).

    `check_acyclic` answers "is this graph acyclic and do its edges resolve". It says
    nothing about whether a guard is ADMISSIBLE: `a[nokey]` is not a guarded member at
    all — `parse_after_member` hands it back whole and the edge-runner treats it as a
    seat name that cannot exist, so the edge is permanently unmet and nothing says why.
    This arm refuses it at registration instead, naming the rule.

    Grammar-only. It rules on ADMISSIBILITY, never on whether a guard is satisfied —
    that is the edge-runner's evaluation (CMP-25) against the predecessor's validated
    output, and no verdict about it is implied here.
    """
    parse = after_member_grammar()
    for row in rows:
        node = (row.get(id_col) or "").strip()
        for member in after_cell_members(row.get(after_col) or ""):
            limbs = after_member_limbs(member)
            for limb in limbs:
                if not limb.strip():
                    f.add(RULE_ALTERNATE_GRAMMAR, str(path),
                          f"{id_col} '{node}': `after` member {member!r} has an EMPTY "
                          f"alternate limb — `a|b` joins two named predecessors, and an "
                          f"empty limb names none")
                    continue
                name, key, _value, _unsupported = parse(limb)
                if key is None and ("[" in limb or "]" in limb):
                    f.add(RULE_GUARD_GRAMMAR, str(path),
                          f"{id_col} '{node}': `after` member {limb.strip()!r} carries "
                          f"brackets but is not a guard — the grammar is exactly "
                          f"`ref[field=value]`: ONE trailing bracket group, a non-empty "
                          f"field, no bracket inside either half. As written it reads as a "
                          f"predecessor literally named {name!r}, which no row can be")


def check_acyclic(rows: list[dict], f: Findings, path: Path,
                  id_col: str = "seat", after_col: str = "after") -> None:
    """The after-graph MUST be acyclic (taskforce-descriptor; goal-lint rejects a cycle).

    This is the room's ONLY sanctioned acyclicity check (Rule 9 forbids a hand-rolled
    walk), so a false clean here is invisible everywhere and correctable nowhere.

    An ABSENT COLUMN and an EMPTY CELL are different failures and `row.get()` cannot
    tell them apart — which is the whole defect this signature exists to close
    (B1, G-planner-0804-1345). A caller passing `milestones.csv` (`milestone-id`) or a
    manifest (`Seat/workflow`) used to `continue` past every row and get an EMPTY edge
    map and a CLEAN verdict on a graph never read. So:

      column absent  -> Refusal. The check CANNOT RUN on this file; saying nothing is
                        a lie about a graph that was never traversed.
      cell empty     -> a finding. The file is the right shape; one row is broken.
    """
    if rows:
        for col, what in ((id_col, "id"), (after_col, "after")):
            if col not in rows[0]:
                raise Refusal(
                    f"{path}: no '{col}' column — the {what} column was not found, so the "
                    f"after-graph cannot be read and NO acyclicity claim can be made about "
                    f"this file. Columns present: {', '.join(rows[0]) or '(none)'}. "
                    f"Pass --id-col/--after-col naming this file's own columns."
                )
    edges: dict[str, list[str]] = {}
    for row in rows:
        seat = (row[id_col] or "").strip()
        if not seat:
            f.add(f"every row names a {id_col}", str(path),
                  f"a row carries an empty '{id_col}' and cannot join the graph: {row}")
            continue
        # 7.426: through `after_pred_names` — the imported grammar, one reading.
        # It replaces a local `entry.split("[", 1)[0]` that truncated at the first
        # bracket, so `a[g=y]|b` lost limb `b` and a cycle through it was invisible.
        edges[seat] = after_pred_names(row[after_col])

    for seat, preds in edges.items():
        for p in preds:
            if p not in edges:
                f.add("after edge resolves", str(path),
                      f"{id_col} '{seat}' lists predecessor '{p}', which is not a row of this file")

    WHITE, GREY, BLACK = 0, 1, 2
    colour = {s: WHITE for s in edges}

    def visit(node: str, stack: list[str]) -> bool:
        colour[node] = GREY
        for pred in edges.get(node, []):
            if pred not in colour:
                continue
            if colour[pred] == GREY:
                cycle = " -> ".join(stack + [node, pred])
                f.add("after graph acyclic", str(path), f"cycle: {cycle}")
                return True
            if colour[pred] == WHITE and visit(pred, stack + [node]):
                return True
        colour[node] = BLACK
        return False

    for seat in edges:
        if colour[seat] == WHITE and visit(seat, []):
            break


def read_md_dag(path: Path, after_col: str = "after") -> list[dict]:
    """Rows off a markdown task DAG, whose edge set lives in prose rather than columns.

    The form this run's DAG documents use, and the only one read here:

        ### 7.342 — `goal-cli-failloud`
        **`after`: EMPTY (ROOT).**            -> no predecessors
        **`after`: `7.340, 7.341`** — …       -> two predecessors

    ponytail: one document family, matched against the real artifact. A markdown
    PIPE TABLE carrying the columns is the other plausible shape and is deliberately
    not read — no DAG document in this corpus uses one. Add that branch when one does.
    """
    rows: list[dict] = []
    after_re = re.compile(r"\*\*`" + re.escape(after_col) + r"`:\s*(.*?)\*\*", re.DOTALL)
    for chunk in re.split(r"^#{2,4}\s+", path.read_text(encoding="utf-8"), flags=re.M)[1:]:
        head, _, body = chunk.partition("\n")
        ident = head.split("—")[0].strip().strip("`")
        if not ident:
            continue
        m = after_re.search(body)
        raw = "" if not m or "EMPTY" in m.group(1).upper() else m.group(1).replace("`", "")
        rows.append({"id": ident, after_col: raw.strip()})
    if not rows:
        raise Refusal(
            f"{path}: no `### <id> — …` section carrying a **`{after_col}`: …** line was "
            f"found, so this file's edge set could not be read and NO acyclicity claim "
            f"can be made about it."
        )
    return rows


def cmd_check_acyclic(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        raise Refusal(f"{path}: missing")
    if path.suffix.lower() == ".md":
        rows = read_md_dag(path, args.after_col)
        id_col = "id"
    else:
        rows = read_csv(path)
        id_col = args.id_col
    f = Findings()
    check_acyclic(rows, f, path, id_col=id_col, after_col=args.after_col)
    check_after_grammar(rows, f, path, id_col=id_col, after_col=args.after_col)
    # The edge count is REPORTED, not implied. "Clean" over an empty edge map is the
    # exact false green this subcommand exists to end — a reader must be able to see
    # that a graph was traversed, not merely that nothing was said about it.
    # Counted through the SAME extraction the traversal used (7.426) — a count from a
    # second reading is a number about a different graph than the one walked.
    edges = sum(len(after_pred_names(r[args.after_col])) for r in rows)
    print(f"check-acyclic: {path}")
    print(f"  {len(rows)} row(s) read, keyed on '{id_col}', edges from '{args.after_col}'")
    print(f"  {edges} edge(s) read" + ("  <-- NOTHING TO CHECK" if not edges else ""))
    for item in f.items:
        print(f"  FINDING [{item['check']}] {item['reason']}")
    if f.items:
        print(f"  {len(f.items)} finding(s) — NOT clean")
        return 1
    print("  clean: the after-graph is acyclic, every edge resolves, and every guard "
          "and alternate is well-formed")
    return 0


def lint_goal(root: Path, name: str) -> Findings:
    """READ-ONLY validation + dry-run emulation (CMP-14). Writes NOTHING, ever."""
    f = Findings()
    goal_dir = resolve_goal_dir(root, name)

    if not goal_dir.is_dir():
        f.add("goal exists", str(goal_dir), "no such goal folder")
        return f

    # --- 1. descriptor: parses, identity fields, name ≡ folder, status enum
    fm: dict = {}
    try:
        fm, body = read_goal_md(goal_dir)
        declared = str(fm.get("name", "")).strip()
        if declared != name:
            f.add("folder name == goal.md name", str(goal_dir / "goal.md"),
                  f"folder is '{name}' but goal.md declares '{declared}'")
        if not GOAL_NAME_RE.match(name):
            f.add("goal name well-formed", str(goal_dir),
                  f"'{name}' is not lowercase kebab-case")
        for field in ("name", "creation-date", "type", "status"):
            if not str(fm.get(field, "")).strip():
                f.add("identity fields present", str(goal_dir / "goal.md"),
                      f"frontmatter '{field}' is missing or empty")
        status = str(fm.get("status", "")).strip()
        if status and status not in GOAL_STATUSES:
            f.add("thin goal state in enum", str(goal_dir / "goal.md"),
                  f"status '{status}' is not one of {', '.join(GOAL_STATUSES)}")
        gtype = str(fm.get("type", "")).strip()
        if gtype and gtype not in GOAL_TYPES:
            f.add("goal type in enum", str(goal_dir / "goal.md"),
                  f"type '{gtype}' is not one of {', '.join(GOAL_TYPES)}")
        # OPTIONAL field (d-owner-batch1 (2)) — so the enum is checked and presence is NOT.
        # The `gkind and` guard is the whole backward-compatibility story: every goal scaffolded
        # before this field existed carries no key, reads as empty, skips the check, and lints
        # green. Adding `goal-kind` to the identity-fields tuple above would retroactively fail
        # all of them, which is why it is absent from that tuple by construction.
        gkind = str(fm.get("goal-kind", "")).strip()
        if gkind and gkind not in GOAL_KINDS:
            f.add("goal kind in enum", str(goal_dir / "goal.md"),
                  f"goal-kind '{gkind}' is not one of {', '.join(GOAL_KINDS)}")
        if not body.strip():
            f.add("goal-radius contract present", str(goal_dir / "goal.md"),
                  "body is empty — the descriptor carries the goal-radius contract")
    except Refusal as exc:
        f.add("goal.md parses", str(goal_dir / "goal.md"), str(exc))

    # --- 2. cross-goal uniqueness of the declared name
    if fm.get("name"):
        for other in sorted(p for p in root.iterdir() if p.is_dir() and p.name != name):
            if not (other / "goal.md").is_file():
                continue
            try:
                ofm, _ = read_goal_md(other)
            except Refusal:
                continue
            if str(ofm.get("name", "")).strip() == str(fm.get("name")).strip():
                f.add("cross-goal name uniqueness", str(other / "goal.md"),
                      f"goal '{other.name}' declares the same name '{fm.get('name')}'")

    # --- 3. CMP-4 layout at goal level
    for required in ("goal.md", "decisions.md", "runs.csv", "threads.sql"):
        if not (goal_dir / required).exists():
            f.add("CMP-4 goal-level layout", str(goal_dir / required),
                  "required by the CMP-4 layout, absent")
    try:
        if (goal_dir / "runs.csv").is_file():
            read_csv(goal_dir / "runs.csv")
    except Refusal as exc:
        f.add("runs.csv parses", str(goal_dir / "runs.csv"), str(exc))

    # --- 4. the current run's plan
    run_dir = current_run_dir(goal_dir, f)
    if run_dir is None:
        f.add("current run resolves", str(goal_dir / "runs"),
              "no run compartment found — nothing to validate or emulate")
        return f

    tf_path = run_dir / "taskforce.csv"
    ms_path = run_dir / "milestones.csv"

    if not ms_path.is_file():
        f.add("milestones.csv parses", str(ms_path), "absent")
    else:
        try:
            read_csv(ms_path)
        except Refusal as exc:
            f.add("milestones.csv parses", str(ms_path), str(exc))

    if not tf_path.is_file():
        f.add("taskforce.csv parses", str(tf_path), "absent — no taskforce to validate")
        return f
    try:
        rows = read_csv(tf_path)
    except Refusal as exc:
        f.add("taskforce.csv parses", str(tf_path), str(exc))
        return f

    check_acyclic(rows, f, tf_path)
    check_after_grammar(rows, f, tf_path)

    seats_dir = run_dir / "seats"
    for row in rows:
        seat = (row.get("seat") or "").strip()
        if not seat:
            f.add("taskforce row names a seat", str(tf_path),
                  f"a row carries no seat: {row}")
            continue

        # every taskforce.csv row resolves to a REAL seat (CMP-14's core check)
        seat_dir = seats_dir / seat
        seat_md = seat_dir / "seat.md"
        if not seat_dir.is_dir():
            f.add("taskforce row resolves to a real seat", str(seat_dir),
                  f"seat '{seat}' has no seat folder (run goal-materialize)")
            continue
        if not seat_md.is_file():
            f.add("seat.md exists", str(seat_md),
                  f"seat '{seat}' has no seat-descriptor (run goal-materialize)")
            continue

        try:
            sfm, sbody = split_frontmatter(seat_md.read_text(encoding="utf-8"), seat_md)
        except Refusal as exc:
            f.add("seat.md parses", str(seat_md), str(exc))
            continue

        # dry-run dispatch emulation: WOULD this seat launch under its resolved
        # harness + model + effort? No launch, no LLM call — resolution only.
        for key in ("harness", "model"):
            if not str(sfm.get(key, "")).strip():
                f.add("dispatch would launch", str(seat_md),
                      f"binding '{key}' missing — the dispatcher could not launch this seat")
        # binding agrees with the taskforce row it was copied from
        for col in BINDING_COLUMNS:
            declared = str(row.get(col, "") or "").strip()
            assembled = str(sfm.get(col, "") or "").strip()
            if declared and assembled and declared != assembled:
                f.add("binding matches taskforce.csv", str(seat_md),
                      f"'{col}': taskforce.csv says '{declared}', seat.md says '{assembled}'")

        # every cognitive-unit reference resolves. Post-materialize the assembled
        # body is the evidence: each frontmatter ref must have its block present.
        refs = []
        for key, val in sfm.items():
            if key in ("id", "seat", "description", "cwd", "agent_type",
                       "mode", "window", "senders", "close", "auto-wake",
                       "ephemeral", "broadcast", "component",
                       *BINDING_COLUMNS):
                continue
            # Widened with _refs_of (d-spec-open-points-ruled Q10): bare ids
            # qualify, not just cu-prefixed ones. Assembled refs carry a FROZEN
            # version segment (`@latest+standin-sha256:<digest>`, registry
            # divergence 5), so only the id part before `@` is grammar-checked.
            # Discrimination from non-ref keys rests on the exclusion list
            # above — any non-ref SCALAR key a future emitted-schema change
            # adds (provenance stamps, dates) MUST be added there, or a
            # token-shaped value false-positives as an unresolved ref.
            # dag-04 (2026-07-29) added exactly that: the emitted descriptor
            # schema's scalar keys (seat/cwd/agent_type/mode/window/senders/
            # close/auto-wake/ephemeral/broadcast/component) — proven to
            # false-positive before the widening, and the dangling-ref
            # control stays red-able (materialize-seats.py selftest).
            if isinstance(val, str) and _UNIT_ID_RE.match(val.strip().split("@", 1)[0]):
                refs.append((key, val.strip()))
            elif isinstance(val, list):
                refs.extend((key, v.strip()) for v in val
                            if isinstance(v, str)
                            and _UNIT_ID_RE.match(v.strip().split("@", 1)[0]))
        for kind, ref in refs:
            unit_id = ref.split("@", 1)[0]
            if f'id="{unit_id}"' not in sbody:
                f.add("cognitive-unit reference resolves", str(seat_md),
                      f"frontmatter ref '{ref}' has no assembled block in the body")

        # permissions well-formed: the seat declares a permissions unit, and it
        # was assembled rather than left dangling.
        if not any(k == "permissions" for k, _ in refs):
            f.add("permissions well-formed", str(seat_md),
                  "seat declares no permissions unit")

    return f


def cmd_lint(args) -> int:
    root = resolve_goals_root(args.root)
    f = lint_goal(root, args.goal_name)
    if args.json:
        print(json.dumps(
            {"ok": not bool(f), "goal": args.goal_name, "root": str(root),
             "findings": f.items}, indent=2))
    else:
        if f:
            print(f"goal-lint {args.goal_name}: {len(f.items)} finding(s) — gate BLOCKS")
            for item in f.items:
                print(f"  [{item['check']}] {item['file']}\n      {item['reason']}")
        else:
            print(f"goal-lint {args.goal_name}: clean — gate OPEN")
    return 1 if f else 0


# ------------------------------------------------------------ gate-key check
#
# The planning-time check that REFUSES a plan landing a keyless gate.
# Owner ruling: `.rbtv/goals/build-core-daemon-mvp/decisions.md`
#   `#r-gate-ships-with-its-own-key`.
# Specification: `runs/run-3/planning/briefing-gate-ships-with-its-own-key-check/
#   gate-key-check-spec.md`, ACCEPTED at sha256/16 9c5e4a09dbaed6b5. Section
#   numbers below cite that document; each clause states a READ the check does.
#
# This check is itself a gate, so `r-gate-ships-with-its-own-key` binds it: its
# own key (the § 6a K3 ships-dark path and the § 6b recorded `--override`) lands
# in this same change. A mechanism whose own repair path it blocks reproduces
# the failure it was built to stop.

GATE_KEY_DECLARATION_NAME = "gate-key-declaration.csv"
GATE_KEY_OVERRIDE_NAME = "gate-key-override.md"

# § 1 — the header is EXACTLY these seven names in this order. A mismatch is a
# REFUSAL, never a repair: a check that silently accepts a renamed column reads
# a different file than the one it reports on.
GATE_KEY_COLUMNS = ("task-id", "lands-mechanism", "defers-classes", "key-form",
                    "key-ref", "ships-dark-default", "note")

# § 4 — the three key forms. § 5 — the six reason codes, a CLOSED set.
GATE_KEY_FORMS = ("K1", "K2", "K3")
GATE_KEY_REASON_CODES = ("blank-declaration", "uncovered-class", "key-unresolved",
                         "dark-not-dark", "class-not-in-source", "schema-violation")

# § 2b — the nine words, MEASURED over 323 rows and published UNTUNED: 15.0 %
# precision, 68.8 % recall, and an exhaustive 511-subset search proving no
# subset does better than 28.6 % at 12.5 % recall (§ 9). Arm 2 therefore FLAGS
# and never refuses (§ 2c; ruled OPEN-2). Arm 1 carries the whole rule.
GATE_KEY_LEXICON = ("refuse", "admit", "defer", "gate", "filter", "block",
                    "deny", "precondition", "guard")
_GATE_KEY_TAIL = r"(s|d|r|rs|ed|es|ing|al|als|ion|ions)?"


def gate_key_lexicon_hits(text: str) -> list[str]:
    """§ 2b's matcher, stated exactly: case-insensitive, word-boundary anchored,
    with a bounded inflection tail.

    SUBSTRING matching is refused as an implementation — measured, it fires on
    13 additional rows purely as a matcher artefact (`gateway`x53,
    `aggregate`x7, `unblock`x6).
    """
    low = (text or "").lower()
    return [w for w in GATE_KEY_LEXICON
            if re.search(r"\b" + re.escape(w) + _GATE_KEY_TAIL + r"\b", low)]


def _module_level_literals(py_source: str) -> dict:
    """{name: value} for every module-level assignment carrying a literal.

    AST only, never `import` — `coord.py` is not importable from an arbitrary
    cwd (it imports `budget` from its own directory), the failure this run
    recorded four times as a mutation that "proved" nothing.
    """
    out: dict = {}
    for node in ast.parse(py_source).body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.value is not None:
            targets = [node.target]
        for t in targets:
            try:
                out[t.id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError, TypeError):
                pass
    return out


def _module_level_names(py_source: str) -> set[str]:
    """Every module-level def/class/assignment NAME — § 4's K2 read.

    A definition or assignment resolved by AST, NEVER a substring hit, which a
    comment or a docstring would satisfy.
    """
    names: set[str] = set()
    for node in ast.parse(py_source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def coord_source_path() -> Path:
    """The ONE legal literal of § 3c — the PATH to `coord.py`.

    Resolved relative to THIS file, never to a caller's cwd: the same anchor
    `materialize-seats.py` uses to reach this module from the other direction.
    """
    return Path(__file__).resolve().parents[3] / "team-kit" / "coord.py"


def read_live_classes(coord_path: Path) -> tuple[set | None, set | None, str | None]:
    """§ 3a — LIVE_CLASSES / LIVE_LIMBS read FROM SOURCE at check time.

    § 3c FORBIDS a literal list of the eleven class names, the seven limb names
    or the four dispositions anywhere in this file — not in code, not in a
    constant, not in a docstring used as data, not in a test fixture. A copied
    list is a second home for a policy set and every copy drifts: all three line
    numbers this check's own inputs carried for these symbols had drifted within
    one day of being written.

    The first term is VALUES, not keys: `_DEFERRAL_BY_DISPOSITION`'s KEYS are
    dispositions, not classes, and taking them yields a 15-element mongrel set
    (§ 0.3). The union is kept even though the first term is today a subset of
    the second, because it stays correct if a disposition class is ever added
    without a verdict entry.

    Returns (classes, limbs, problem). A problem is REPORTED by the caller and
    never silently degraded to the § 3b arm.
    """
    try:
        src = Path(coord_path).read_text(encoding="utf-8")
    except OSError as exc:
        return None, None, f"{coord_path}: unreadable ({exc.__class__.__name__})"
    try:
        lits = _module_level_literals(src)
    except SyntaxError as exc:
        return None, None, f"{coord_path}: does not parse ({exc})"
    missing = [n for n in ("_DEFERRAL_BY_DISPOSITION", "CLASS_TO_VERDICT",
                           "ADMISSION_LIMBS") if n not in lits]
    if missing:
        return None, None, (f"{coord_path}: module-level symbol(s) absent or "
                            f"non-literal: {', '.join(missing)}")
    try:
        classes = set(lits["_DEFERRAL_BY_DISPOSITION"].values()) | set(lits["CLASS_TO_VERDICT"])
        limbs = set(lits["ADMISSION_LIMBS"])
    except (AttributeError, TypeError) as exc:
        return None, None, f"{coord_path}: symbol shape unusable ({exc})"
    return classes, limbs, None


def _gate_key_workspace(goals_root: Path) -> Path:
    """The anchor a RELATIVE `key-ref` path resolves against.

    `<workspace>/.rbtv/goals` is the settled root shape, so the workspace is two
    levels up from it; anything else anchors at the root itself.
    """
    if goals_root.name == "goals" and goals_root.parent.name == ".rbtv":
        return goals_root.parents[1]
    return goals_root


def _resolve_key_path(raw: str, workspace: Path, pass_dir: Path) -> tuple[Path | None, list[str]]:
    """An absolute path is used as given; a relative one is tried against the
    workspace root, then this pass's own folder. Both anchors are reported when
    neither resolves — a path the check could not find must never look like a
    path it chose not to read."""
    p = Path(raw).expanduser()
    if p.is_absolute():
        return (p if p.is_file() else None), [str(p)]
    tried = []
    for anchor in (workspace, pass_dir):
        cand = anchor / p
        tried.append(str(cand))
        if cand.is_file():
            return cand, tried
    return None, tried


def _split_key_ref(raw: str) -> tuple[str, str] | None:
    """`<path>#<symbol>` — split on the LAST `#`, since a path may not carry one
    but a symbol never does."""
    if "#" not in raw:
        return None
    path, _, symbol = raw.rpartition("#")
    if not path.strip() or not symbol.strip():
        return None
    return path.strip(), symbol.strip()


def _verify_k2(key_ref: str, workspace: Path, pass_dir: Path) -> str | None:
    """§ 4 K2 — the path exists and is readable AND `<symbol>` occurs in it. For
    a `.py` path the occurrence MUST be a module-level definition or assignment
    resolved by AST. Returns None when verified, else the specific finding.

    The read is BY SYMBOL, never by line number: had this check been written
    against a carried line number it would already be broken (§ 4a).
    """
    parts = _split_key_ref(key_ref)
    if parts is None:
        return f"key-ref '{key_ref}' is not the K2 shape <path>#<symbol>"
    rel, symbol = parts
    path, tried = _resolve_key_path(rel, workspace, pass_dir)
    if path is None:
        return f"path '{rel}' does not resolve to a file; tried: {', '.join(tried)}"
    try:
        src = path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"{path}: unreadable ({exc.__class__.__name__})"
    if path.suffix == ".py":
        try:
            names = _module_level_names(src)
        except SyntaxError as exc:
            return f"{path}: does not parse ({exc})"
        if symbol not in names:
            return (f"{path}: '{symbol}' is not a module-level definition or "
                    f"assignment (AST read — a comment or docstring hit is not a key)")
    elif symbol not in src:
        return f"{path}: '{symbol}' does not occur in the file"
    return None


def _verify_k3(key_ref: str, declared_default: str, workspace: Path,
               pass_dir: Path) -> tuple[str | None, str | None]:
    """§ 4 K3 — the symbol exists by the same AST read as K2, AND its literal
    default equals `ships-dark-default`, AND that value is FALSY.

    A K3 whose default is truthy is REFUSED: a mechanism declared dark that
    ships lit is worse than one that ships lit honestly.

    Returns (key_unresolved_finding, dark_not_dark_finding) — at most one set.
    """
    parts = _split_key_ref(key_ref)
    if parts is None:
        return f"key-ref '{key_ref}' is not the K3 shape <path>#<symbol>", None
    rel, symbol = parts
    path, tried = _resolve_key_path(rel, workspace, pass_dir)
    if path is None:
        return f"path '{rel}' does not resolve to a file; tried: {', '.join(tried)}", None
    if path.suffix != ".py":
        return (f"{path}: K3 reads a literal default, which only a python source "
                f"carries; '{path.suffix or 'no'}' suffix is not readable that way"), None
    try:
        lits = _module_level_literals(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return f"{path}: unreadable or unparseable ({exc.__class__.__name__})", None
    if symbol not in lits:
        return (f"{path}: '{symbol}' carries no module-level literal default "
                f"(AST read)"), None
    value = lits[symbol]
    want = declared_default.strip()
    try:
        parsed = ast.literal_eval(want)
        matched = parsed == value
    except (ValueError, SyntaxError):
        parsed, matched = want, str(value) == want
    if not matched:
        return None, (f"{path}: '{symbol}' default is {value!r}, but the row declares "
                      f"ships-dark-default {want!r} — the declaration and the source "
                      f"disagree about what dark means")
    if value:
        return None, (f"{path}: '{symbol}' default {value!r} is TRUTHY — declared dark, "
                      f"ships lit")
    return None, None


def _gate_key_block(task_id: str, code: str, finding: str, uncovered: list,
                    closes: str) -> str:
    """§ 5's refusal block. `uncovered classes:` is NEVER abbreviated to a count —
    an operator told "2 classes uncovered" must re-derive which two, which is the
    work the refusal was supposed to save."""
    names = ", ".join(uncovered) if uncovered else "-"
    return (f"REFUSED  {task_id}  {code}\n"
            f"  {finding}\n"
            f"  uncovered classes: {names}\n"
            f"  what closes it: {closes}")


def gate_key_check(root: Path, goal_name: str, pass_folder: str,
                   f: Findings, coord_path: Path | None = None) -> dict:
    """Read a pass's `gate-key-declaration.csv` and return the check's result.

    Returns {"refusals": [block…], "flags": [line…], "reports": [line…]}.
    Writes NOTHING — the only write this verb ever makes is § 6b's override
    record, and that is the caller's.
    """
    refusals: list[str] = []
    flags: list[str] = []
    reports: list[str] = []

    def refuse(task_id, code, finding, uncovered=(), closes="") -> None:
        refusals.append(_gate_key_block(task_id, code, finding, list(uncovered), closes))
        f.add(f"gate-key: {code}", str(task_id), finding)

    goal_dir = resolve_goal_dir(root, goal_name)
    run_dir = current_run_dir(goal_dir, f)
    if run_dir is None:
        refuse("-", "schema-violation", f"{goal_dir}: no run folder resolves",
               closes="a run folder with an open row in runs.csv")
        return {"refusals": refusals, "flags": flags, "reports": reports}
    pass_dir = run_dir / "planning" / pass_folder
    decl_path = pass_dir / GATE_KEY_DECLARATION_NAME
    if not decl_path.is_file():
        refuse("-", "schema-violation",
               f"{decl_path}: absent — a pass that declares nothing declares no gate",
               closes="the pass emits its gate-key-declaration.csv")
        return {"refusals": refusals, "flags": flags, "reports": reports}

    with decl_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = tuple(reader.fieldnames or ())
        rows = [dict(r) for r in reader]
    if header != GATE_KEY_COLUMNS:
        refuse("-", "schema-violation",
               f"{decl_path}: header is {list(header)}, not {list(GATE_KEY_COLUMNS)}",
               closes="the exact seven-column header, in order")
        return {"refusals": refusals, "flags": flags, "reports": reports}

    live_classes, live_limbs, problem = read_live_classes(
        coord_path if coord_path is not None else coord_source_path())
    if problem:
        # § 3a: reported, NEVER silently degraded to the § 3b arm.
        reports.append(f"source-enumeration-unreadable: {problem}; the § 3a "
                       f"exhaustiveness arm did NOT run for any row")
        flags.append(f"source-enumeration-unreadable: {problem}")
    else:
        reports.append(f"source-enumeration: {len(live_classes)} class(es) / "
                       f"{len(live_limbs)} limb(s) read from "
                       f"{coord_path if coord_path is not None else coord_source_path()}")

    declared_ids = {(r.get("task-id") or "").strip()
                    for r in rows if (r.get("task-id") or "").strip()}

    def cell(r, name):
        return (r.get(name) or "").strip()

    for idx, r in enumerate(rows, start=2):  # line 1 is the header
        tid = cell(r, "task-id")
        where = tid or f"<blank task-id, line {idx}>"
        if not tid:
            refuse(where, "schema-violation", f"line {idx}: task-id is blank",
                   closes="a task-id in the pass's own id-space")
            continue

        lands = cell(r, "lands-mechanism").lower()
        if not lands:
            # § 2a — blank is REFUSED. No default, no inference, no "empty
            # means no". A mandatory field with a refused blank makes OMISSION
            # impossible, and that is arm 1's entire job.
            refuse(tid, "blank-declaration", "lands-mechanism is blank",
                   closes="declare lands-mechanism explicitly: yes or no")
            continue
        if lands not in ("yes", "no"):
            refuse(tid, "schema-violation",
                   f"lands-mechanism is '{lands}', not yes|no",
                   closes="declare lands-mechanism explicitly: yes or no")
            continue

        classes = [c.strip() for c in cell(r, "defers-classes").split(";") if c.strip()]
        form = cell(r, "key-form")
        key_ref = cell(r, "key-ref")
        dark_default = cell(r, "ships-dark-default")

        if lands == "yes" and not classes:
            refuse(tid, "schema-violation",
                   "lands-mechanism: yes with no defers-classes — an empty class "
                   "set is legal only when lands-mechanism: no",
                   closes="name the class(es) this task defers")
            continue
        if not classes:
            if form or key_ref:
                refuse(tid, "schema-violation",
                       f"no defers-classes, but key-form '{form}' / key-ref "
                       f"'{key_ref}' is populated",
                       closes="leave key-form and key-ref empty when no class is deferred")
            continue

        # § 3a vs § 3b — a row is under the source-verified arm when it names at
        # least one class the live enumeration knows. A row naming none sits on
        # another lifecycle path and gets § 3b's mandatory report line instead.
        if live_classes is not None:
            known = [c for c in classes if c in live_classes]
            if known:
                unknown = [c for c in classes if c not in live_classes]
                if unknown:
                    refuse(tid, "class-not-in-source",
                           f"class(es) absent from the live enumeration: "
                           f"{', '.join(unknown)}",
                           uncovered=unknown,
                           closes="name a class the source enumerates, or move the "
                                  "row to a non-coord.py lifecycle path")
            else:
                reports.append(
                    f"partition-unverified: {tid} declares {len(classes)} class(es) "
                    f"against no source enumeration; exhaustiveness NOT checked. "
                    f"Classes: {', '.join(classes)}")
                flags.append(f"partition-unverified: {tid}")

        if not form:
            # § 5 — "a declared class carries no key form". The most specific of
            # the two codes that could claim this row, and the one whose
            # `uncovered classes:` naming the acceptance bar demands.
            refuse(tid, "uncovered-class",
                   f"{len(classes)} class(es) declared with no key-form",
                   uncovered=classes,
                   closes="K1 (key in this plan), K2 (key already on disk), or "
                          "K3 (ships dark)")
            continue
        if form not in GATE_KEY_FORMS:
            refuse(tid, "schema-violation",
                   f"key-form '{form}' is not one of {', '.join(GATE_KEY_FORMS)}",
                   uncovered=classes,
                   closes=f"one of {', '.join(GATE_KEY_FORMS)}")
            continue
        if not key_ref:
            refuse(tid, "schema-violation",
                   f"key-form {form} with an empty key-ref",
                   uncovered=classes,
                   closes="the K-form's argument")
            continue

        if form == "K1":
            named = [x.strip() for x in key_ref.split(";") if x.strip()]
            if not named:
                refuse(tid, "key-unresolved", "K1 names no task-id",
                       uncovered=classes,
                       closes="at least one task-id of THIS declaration")
                continue
            absent = [x for x in named if x not in declared_ids]
            if absent:
                # § 0.4 / § 4 — membership in THIS declaration, NEVER a store
                # lookup: at fan-in the store rows do not exist yet, so a store
                # lookup would refuse every correct plan.
                refuse(tid, "key-unresolved",
                       f"K1 names {', '.join(absent)}, which are not task-ids of "
                       f"this declaration",
                       uncovered=classes,
                       closes="name task-ids this pass itself plans")
        elif form == "K2":
            problem2 = _verify_k2(key_ref, _gate_key_workspace(root), pass_dir)
            if problem2:
                refuse(tid, "key-unresolved", f"K2: {problem2}",
                       uncovered=classes,
                       closes="a <path>#<symbol> the check can resolve by AST")
        else:  # K3
            if not dark_default:
                refuse(tid, "schema-violation",
                       "key-form K3 with an empty ships-dark-default",
                       uncovered=classes,
                       closes="the literal the K3 symbol's default must evaluate to")
                continue
            unresolved, not_dark = _verify_k3(key_ref, dark_default,
                                              _gate_key_workspace(root), pass_dir)
            if unresolved:
                refuse(tid, "key-unresolved", f"K3: {unresolved}",
                       uncovered=classes,
                       closes="a <path>#<symbol> the check can resolve by AST")
            elif not_dark:
                refuse(tid, "dark-not-dark", f"K3: {not_dark}",
                       uncovered=classes,
                       closes="a falsy default, or an honest K1/K2 key")
            else:
                # § 7a AS AMENDED by the leader's ruling
                # `p-arm-iii-RULED-a-dark-gate-flags` (2026-08-03): a SATISFIED
                # K3 is an exit-3 source, so § 6a's "passes FLAGGED" survives and
                # § 7a's source list gains this arm. Ships-dark is a TEMPORARY
                # TRACKED state; a dark gate whose output cannot be told apart
                # from a keyed one makes that state silently permanent — the
                # failure this whole check exists to end, one level deeper.
                # MEASURED at 7.323 before the ruling: the two outputs were
                # byte-identical apart from the pass-folder name.
                flags.append(f"ships-dark: {tid} lands SWITCHED OFF behind "
                             f"{key_ref} (default {dark_default}) — the key is "
                             f"still owed for: {', '.join(classes)}")

    # § 2b — arm 2's matcher is landed (`gate_key_lexicon_hits`) and selftested,
    # but the text it scans is a task's STORE text, and at the fan-in stage
    # § 7b fixes this check to, the store rows do not exist yet (the same
    # collision § 0.4 cured for K1, uncured for arm 2). goal_cli.py resolves no
    # task store, and hard-coding one workspace's store path here is the second
    # home § 3c forbids. The arm is therefore NOT exercised, and says so on
    # every run rather than reporting itself exercised — routed to the leader.
    reports.append(
        f"lexicon-unexercised: arm 2's matcher is landed and proven, but no "
        f"scannable task text resolves at this stage for {len(declared_ids)} "
        f"declared task(s); arm 2 did NOT run. Arm 1 carries the rule (§ 2c).")

    return {"refusals": refusals, "flags": flags, "reports": reports}


def write_gate_key_override(pass_dir: Path, anchor: str, refusals: list) -> Path:
    """§ 6b — the override's record. Carries the anchor, the UTC timestamp, the
    refusals overridden VERBATIM, and the invoking seat.

    The check exits 0 only after this is on disk and re-read: a record it could
    not write is a refusal, not an override.
    """
    seat = os.environ.get("COORD_AGENT") or "unknown (no COORD_AGENT in the environment)"
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = [
        f"# gate-key-override — {stamp}",
        "",
        f"- **anchor:** `{anchor}`",
        f"- **invoked by:** {seat}",
        f"- **pass folder:** `{pass_dir.name}`",
        f"- **refusals overridden:** {len(refusals)}",
        "",
        "## The refusals, verbatim",
        "",
        "```",
    ]
    body.extend(refusals if refusals else ["(none — no refusal was outstanding)"])
    body.append("```")
    body.append("")
    path = pass_dir / GATE_KEY_OVERRIDE_NAME
    path.write_text("\n".join(body), encoding="utf-8")
    return path


def cmd_gate_key_check(args) -> int:
    """§ 7a — exit 0 clean · 1 REFUSED · 3 flagged-pass.

    Exit 2 is deliberately unused: argparse reserves it for usage errors, and a
    check whose flagged-pass is indistinguishable from a mistyped flag is a
    check nobody can gate on.
    """
    root = resolve_goals_root(args.root)
    f = Findings()
    result = gate_key_check(root, args.goal_name, args.pass_folder, f)
    refusals, flags, reports = result["refusals"], result["flags"], result["reports"]

    override = getattr(args, "override", None)
    override_ok = False
    override_path = None
    if override is not None:
        if not str(override).strip():
            msg = "--override carries an empty anchor"
            refusals.append(_gate_key_block("-", "schema-violation", msg, [],
                                            "a non-empty leader-ruling anchor"))
            f.add("gate-key: schema-violation", "--override", msg)
        else:
            goal_dir = resolve_goal_dir(root, args.goal_name)
            run_dir = current_run_dir(goal_dir, Findings())
            pass_dir = (run_dir / "planning" / args.pass_folder) if run_dir else None
            try:
                override_path = write_gate_key_override(pass_dir, str(override).strip(),
                                                        refusals)
                # re-read: a record it could not write is a refusal, not an override
                override_ok = bool(override_path.read_text(encoding="utf-8").strip())
            except (OSError, AttributeError, TypeError) as exc:
                msg = (f"--override could not write its § 6b record "
                       f"({exc.__class__.__name__}: {exc}) — a record it could not "
                       f"write is a refusal, not an override")
                refusals.append(_gate_key_block("-", "schema-violation", msg, [],
                                                "a writable pass folder"))
                f.add("gate-key: schema-violation", "--override", msg)

    if refusals and override_ok:
        rc = 0
    elif refusals:
        rc = 1
    elif flags:
        rc = 3
    else:
        rc = 0

    if getattr(args, "json", False):
        print(json.dumps({
            "ok": rc == 0, "exit": rc, "goal": args.goal_name,
            "pass-folder": args.pass_folder, "root": str(root),
            "findings": f.items, "flags": flags, "reports": reports,
            "override": {"anchor": str(override).strip() if override else None,
                         "recorded": override_ok,
                         "record": str(override_path) if override_path else None},
        }, indent=2))
    else:
        for line in reports:
            print(f"  {line}")
        for line in flags:
            print(f"FLAG  {line}")
        for block in refusals:
            print(block, file=sys.stderr)
        if refusals and not override_ok:
            print("  the recorded exit: gate-key-check --override <leader-anchor> "
                  "(§ 6b — never silent, always audited after)", file=sys.stderr)
        if override_ok:
            print(f"gate-key-check {args.pass_folder}: {len(refusals)} refusal(s) "
                  f"OVERRIDDEN, recorded at {override_path}")
        elif refusals:
            print(f"gate-key-check {args.pass_folder}: {len(refusals)} refusal(s) "
                  f"— the plan is redesigned")
        elif flags:
            print(f"gate-key-check {args.pass_folder}: flagged-pass — {len(flags)} "
                  f"flag(s), 0 refusal(s); the fan-in seat addresses every flag")
        else:
            print(f"gate-key-check {args.pass_folder}: clean")
    return rc


# ---------------------------------------------------------------- materialize


def index_units(catalog_root: Path) -> dict[str, dict]:
    """unit id -> {path, kind, block, digest} for every cognitive-unit file.

    The settled source form (d-cu-xml-wrapper) is a KIND-NAMED tag with NO
    attributes, with the id living in frontmatter only; the assembler stamps
    id (+ resolved version) attributes at assembly time. The office-scaffold
    prototype's `<cognitive-unit id kind>` form is superseded and is NOT read here.
    """
    units: dict[str, dict] = {}
    for path in sorted(catalog_root.rglob("*.md")):
        # A file under a `cognitive-units/` directory IS a unit and MUST index. Every
        # other .md under the catalog root (component.md, a workflow.md) is not one and
        # is skipped quietly. That one structural test is what makes the refusals below
        # DISCRIMINATING rather than merely loud, and it is measured, not assumed:
        # all 1314 indexed units live under such a directory and no non-unit file does.
        is_unit = "cognitive-units" in path.parts
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            if is_unit:
                raise Refusal(f"{path}: cognitive-unit file has no frontmatter block")
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as exc:
            # NEVER `continue` here. A skipped parse failure returns an index
            # one unit smaller with no output at all, and every downstream
            # check that counts what this returned agrees with it (7.170).
            raise Refusal(
                f"{path}: cognitive-unit frontmatter is not valid YAML — "
                f"{str(exc).strip()}"
            ) from exc
        if not isinstance(fm, dict) or not fm.get("id"):
            if is_unit:
                raise Refusal(f"{path}: cognitive-unit frontmatter carries no `id:`")
            continue
        body = text[m.end():]
        tag = re.search(r"<([a-z0-9-]+)>(.*?)</\1>", body, re.DOTALL)
        if not tag:
            # NEVER `continue` here either — the YAML branch above says so and this
            # branch used to disagree with it, dropping 20 files (two whole components,
            # one of them live) with no output at all (7.342, G-planner-0804-1735).
            if is_unit:
                raise Refusal(
                    f"{path}: cognitive-unit body carries no kind-named tag. The settled "
                    f"form (d-cu-xml-wrapper) wraps the body in `<kind>…</kind>` with no "
                    f"attributes and keeps the kind OUT of frontmatter; a `kind:` key with "
                    f"a bare body is the superseded form and does not index."
                )
            continue
        unit_id = str(fm["id"]).strip()
        if unit_id in units:
            raise Refusal(
                f"duplicate cognitive-unit id '{unit_id}' in {path} and {units[unit_id]['path']}"
            )
        units[unit_id] = {
            "path": path,
            "kind": tag.group(1),
            "content": tag.group(2).strip("\n"),
            "description": str(fm.get("description", "")).strip(),
            "entry_point": path,
            "digest": unit_digest(text),
        }
    return units


def load_catalogs(catalog_root: Path) -> tuple[dict, dict, dict]:
    """seats / prompts / tasks catalogs, keyed by id, merged across components.

    The settled model keeps the CATALOG INDIRECTION: a seat row names a
    prompt-id (or capability) and a task-id; the unit references live on the
    prompt/task rows. A seat never references units directly — the prototype's
    `.seat.json` shape is ruled against (d-seat-assembled-projection).
    """
    seats, prompts, tasks = {}, {}, {}
    for name, bucket, key in (
        ("seats.csv", seats, "seat-id"),
        ("prompts.csv", prompts, "prompt-id"),
        ("tasks.csv", tasks, "task-id"),
    ):
        for path in sorted(catalog_root.rglob(name)):
            for row in read_csv(path):
                ident = (row.get(key) or "").strip()
                if not ident:
                    continue
                if ident in bucket:
                    raise Refusal(f"duplicate {key} '{ident}' in {path}")
                row["__source__"] = path
                bucket[ident] = row
    return seats, prompts, tasks


_UNIT_REF_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(@[a-z0-9][a-z0-9-]*)?$")
# Id-only grammar for ASSEMBLED frontmatter refs, whose version segment is the
# frozen `latest+standin-sha256:<digest>` form _UNIT_REF_RE cannot carry.
_UNIT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Catalog columns that are NEVER unit references. Skipped BEFORE the grammar is
# applied, because the grammar cannot tell a short label from a short unit id.
# Two kinds live here, and the distinction IS the maintenance rule:
#
#   IDENTITY   seat-id, prompt-id, task-id, executor, description — the row's
#              own keys plus its free-prose label.
#   LABEL      design-id, store-task-id — cross-references OUT of the catalog
#              (to a milestone-task-dag row; to a task-store row). Their domain
#              is SHORT TOKENS, so one is eventually spelled inside the bare-id
#              grammar and read as a dangling unit reference. Measured
#              2026-08-03: 8 components carry design-id and 7 escaped only by
#              accident of casing or a dot (M4-38, E1, C1, U1.1, P1, C0.1);
#              admission-design-fork's t1..t27 were the first lowercase labels
#              and refused 27 of 27 rows.
#
# ANY NEW LABEL COLUMN IS ADDED HERE IN THE SAME ACT THAT ADDS IT TO A CATALOG
# SCHEMA. Two columns are deliberately NOT here: free-PROSE cells (`context`,
# `staffing-recommendations`) are left to the grammar, which is a sound
# discriminator for a domain of sentences and is the widening's own stated
# design; `capabilities` is a REAL reference column (invoked kind `capability`),
# proven by this file's own selftest — skipping it would break assembly.
NON_REF_COLUMNS = (
    "seat-id", "prompt-id", "task-id", "executor", "description",
    "design-id", "store-task-id",
)


def _refs_of(row: dict, skip: tuple[str, ...]) -> list[tuple[str, list[str]]]:
    """Per-kind unit references off a catalog row, in column order.

    A cell may hold several refs separated by ';' — plural kinds take LIST
    values in the assembled frontmatter (YAML forbids duplicate keys).

    Widened (decisions.md#d-spec-open-points-ruled Q10) to accept BARE unit
    ids, not just the `cu-`-prefixed convention: a token qualifies as a
    reference when it matches the unit-reference grammar `<id>` or
    `<id>@<version>` (`<id>` = `[a-z0-9][a-z0-9-]*`). The `cu-` prefix is an
    office-scaffold-prototype convention, not a requirement of any ratified
    record — do not restore it as a tightening. To keep this a widening and
    not "accept everything" (free-prose description/staffing-hint cells must
    still yield no refs), a cell is treated as a reference list only when
    EVERY ';'-separated part matches the grammar; if any part fails, the
    whole cell is rejected rather than partially parsed.

    The grammar cannot discriminate a short LABEL from a short unit id, so
    columns that never carry a reference are excluded by NAME before it runs —
    see NON_REF_COLUMNS above, which the one caller passes as `skip`.
    """
    out = []
    for col, cell in row.items():
        if col in skip or col.startswith("__") or not isinstance(cell, str):
            continue
        parts = [r.strip() for r in cell.split(";") if r.strip()]
        if parts and all(_UNIT_REF_RE.match(p) for p in parts):
            out.append((col, parts))
    return out


def assemble_seat(seat_id: str, binding: dict, seats: dict, prompts: dict,
                  tasks: dict, units: dict) -> str:
    """Build one seat.md: frontmatter = binding + resolved refs (the lockfile),
    body = XML-wrapped unit contents (invoked units as loader stubs)."""
    if seat_id not in seats:
        raise Refusal(f"seat '{seat_id}' resolves to no row in any seats.csv")
    srow = seats[seat_id]

    prompt_id = (srow.get("prompt-id") or srow.get("executor") or "").strip()
    task_id = (srow.get("task-id") or "").strip()

    parts: list[tuple[str, dict]] = []
    if prompt_id:
        if prompt_id not in prompts:
            raise Refusal(
                f"seat '{seat_id}' names executor '{prompt_id}', which resolves to no prompts.csv row"
            )
        parts.append(("executor prompt", prompts[prompt_id]))
    if task_id:
        if task_id not in tasks:
            raise Refusal(
                f"seat '{seat_id}' names task '{task_id}', which resolves to no tasks.csv row"
            )
        parts.append(("task", tasks[task_id]))
    if not parts:
        raise Refusal(f"seat '{seat_id}' names neither an executor nor a task")

    fm: dict = {
        # `seat:` is the roster key coord.py reads (FM_KEY["agent"] matches
        # `^(?:seat|agent):`). Emitting `id:` here produced descriptors the kit
        # could not resolve, leaving every materialized seat UNBUILT (M4-27).
        "seat": seat_id,
        "description": (srow.get("description") or "").strip(),
    }
    for col in BINDING_COLUMNS:
        if str(binding.get(col, "") or "").strip():
            fm[col] = str(binding[col]).strip()

    blocks: list[str] = []
    for label, row in parts:
        for kind_col, refs in _refs_of(row, NON_REF_COLUMNS):
            resolved: list[str] = []
            for ref in refs:
                unit_id, _, pinned = ref.partition("@")
                if unit_id not in units:
                    raise Refusal(
                        f"unit reference '{ref}' (seat '{seat_id}', {label}) resolves to no "
                        f"cognitive-unit file"
                    )
                u = units[unit_id]
                invoked = u["kind"] in INVOKED_KINDS
                if invoked:
                    # invoked kinds are always @latest and never frozen
                    version = "latest"
                else:
                    # @latest FREEZES here (the assembly-lockfile realization).
                    #
                    # STAND-IN CONVENTION — NOT THE SETTLED SCHEMA. CMP-5 resolves
                    # versions through a repo-root `cognitive-units-index.csv`
                    # mapping version-id -> (commit, filepath). That file does not
                    # exist (CMP-5 is status `draft` — designed, unbuilt), so the
                    # freeze is recorded as a content digest: the resolution stays
                    # pinned and re-checkable without inventing an index schema.
                    # Registry divergence 5. When the index lands this format is
                    # REPLACED by its version-ids, never grandfathered.
                    version = pinned if pinned and pinned != "latest" else \
                        f"latest+{STANDIN_VERSION_PREFIX}{u['digest']}"
                resolved.append(f"{unit_id}@{version}")

                if invoked:
                    body = (
                        f"{u['description']}\n\n"
                        f"Entry point: `{u['entry_point']}` — invoked on demand, not inlined."
                    )
                else:
                    body = u["content"]
                blocks.append(
                    f'<{u["kind"]} id="{unit_id}" version="{version}">\n{body}\n</{u["kind"]}>'
                )
            fm[kind_col] = resolved if len(resolved) > 1 else resolved[0]

    header = (
        "---\n"
        + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
        + "---\n"
    )
    intro = (
        "\n<!-- ASSEMBLED by rbtv-goal materialize — a projection, never the source.\n"
        "     Every word of unit content lives in its cognitive-unit file; edit there.\n"
        "\n"
        f"     VERSION STRINGS: `latest+{STANDIN_VERSION_PREFIX}<12>` is a STAND-IN, not the\n"
        "     settled schema. CMP-5's repo-root cognitive-units-index.csv (version-id ->\n"
        "     commit, filepath) does not exist yet — CMP-5 is status `draft`. The digest\n"
        "     keeps the lockfile pinned and re-checkable in the meantime. Registry\n"
        "     divergence 5: replaced by real version-ids when the index lands. -->\n\n"
    )
    return header + intro + "\n\n".join(blocks) + "\n"


def cmd_materialize(args) -> int:
    root = resolve_goals_root(args.root)
    goal_dir = resolve_goal_dir(root, args.goal_name)
    if not goal_dir.is_dir():
        raise Refusal(f"{goal_dir}: no such goal folder")

    f = Findings()
    run_dir = current_run_dir(goal_dir, f)
    if run_dir is None:
        raise Refusal(f"{goal_dir}: no run compartment — nothing to materialize")

    tf_path = run_dir / "taskforce.csv"
    rows = read_csv(tf_path)
    if not rows:
        raise Refusal(f"{tf_path}: no taskforce rows")

    seats_dir = run_dir / "seats"
    if seats_dir.exists() and any(seats_dir.iterdir()) and not args.force:
        raise Refusal(
            f"{seats_dir}: already materialized — refusing to regenerate. "
            "Re-assembly is deliberate: pass --force."
        )

    if not args.catalog_root:
        raise Refusal(
            "--catalog-root is required: seat assembly resolves cognitive units through "
            "the component catalogs (CMP-5), and this command will not guess a path. "
            "NOTE: the live rbtv repo carries no CMP-5 component-database yet "
            "(no cognitive-units-index.csv, no seats/prompts/tasks catalogs) — CMP-5 is "
            "status `draft`."
        )
    catalog_root = Path(args.catalog_root).expanduser().resolve()
    if not catalog_root.is_dir():
        raise Refusal(f"--catalog-root {catalog_root}: not a directory")

    units = index_units(catalog_root)
    seats, prompts, tasks = load_catalogs(catalog_root)
    if not seats:
        raise Refusal(f"{catalog_root}: no seats.csv rows found — nothing can be assembled")

    # 7.456 / MC14 — THE GUARD-GRAMMAR ARM FIRES AS PART OF THE REGISTRATION ACT.
    # Before this, the arm ran only where an AUTHOR remembered to run `lint` or
    # `check-acyclic`; a materialize of a manifest whose guards are inadmissible
    # succeeded and wrote every seat (measured at HEAD over four mutation classes).
    # A validation nothing makes unskippable is not a validation at registration.
    #
    # The SAME two functions `lint` and `check-acyclic` call, in the same order, on
    # the same rows: no copy, no new rule, no changed semantics — only this
    # invocation point is new. Both are needed and neither is redundant: an
    # inadmissible guard is `check_after_grammar`'s, a well-formed guard naming a
    # row that does not exist is `check_acyclic`'s resolution rule alone.
    #
    # A FRESH `Findings`: `f` above already passed through `current_run_dir`, which
    # adds findings of its own (e.g. "one live run per goal"), and a refusal must
    # name only the rules THIS manifest broke.
    #
    # Placed LAST in the refusal set deliberately — every pre-existing refusal keeps
    # its precedence, and this one is additive.
    graph = Findings()
    check_acyclic(rows, graph, tf_path)
    check_after_grammar(rows, graph, tf_path)
    if graph:
        raise Refusal(
            f"{tf_path}: the after-graph does not validate, so nothing is materialized "
            f"from it ({len(graph.items)} finding(s)):\n"
            + "\n".join(f"  [{i['check']}] {i['reason']}" for i in graph.items))

    # Assemble everything in memory FIRST: a mid-assembly failure must never
    # leave a half-materialized run on disk.
    assembled: dict[str, str] = {}
    for row in rows:
        seat = (row.get("seat") or "").strip()
        if not seat:
            raise Refusal(f"{tf_path}: a row carries no seat")
        assembled[seat] = assemble_seat(seat, row, seats, prompts, tasks, units)

    plan = {
        "goal": args.goal_name,
        "run": run_dir.name,
        "catalog_root": str(catalog_root),
        "seats": sorted(assembled),
        "writes": [str(seats_dir / s / "seat.md") for s in sorted(assembled)],
    }
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, **plan}, indent=2) if args.json
              else "dry-run: would assemble " + ", ".join(sorted(assembled))
                   + f" under {seats_dir}")
        return 0

    for seat, text in assembled.items():
        d = seats_dir / seat
        d.mkdir(parents=True, exist_ok=True)
        p = d / "seat.md"
        p.write_text(text, encoding="utf-8", newline="\n")
        p.chmod(0o644)   # permissions written with the descriptor
        d.chmod(0o755)

    if args.json:
        print(json.dumps({"ok": True, **plan}, indent=2))
    else:
        print(f"materialized {len(assembled)} seat(s) under {seats_dir}")
        for seat in sorted(assembled):
            print(f"  {seat} -> {seats_dir / seat / 'seat.md'}")
    return 0


# ---------------------------------------------------------------- selftest


def cmd_selftest(args) -> int:
    """End-to-end exercise on a throwaway tree. Never touches a real package."""
    import tempfile

    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"  ok   {label}")
        else:
            failures.append(f"{label}{': ' + detail if detail else ''}")
            print(f"  FAIL {label}{': ' + detail if detail else ''}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        root = tmp / ".rbtv" / "goals"
        root.mkdir(parents=True)
        contract = tmp / "contract.md"
        contract.write_text("Ship the thing, verified at the edge.\n", encoding="utf-8")

        ns = argparse.Namespace(root=str(root), json=False, dry_run=False)

        print("scaffold")
        rc = cmd_scaffold(argparse.Namespace(
            goal_name="demo-goal", type="one-shot", due="2026-09-01",
            contract=str(contract), **vars(ns)))
        check("scaffold exits 0", rc == 0)
        gd = root / "demo-goal"
        for fname in ("goal.md", "decisions.md", "runs.csv", "threads.sql"):
            check(f"creates {fname}", (gd / fname).is_file())
        idx = list(csv.DictReader((root / "goals.csv").open(encoding="utf-8")))
        check("goals.csv carries the row", len(idx) == 1 and idx[0]["name"] == "demo-goal",
              str(idx))
        check("status is briefed", idx and idx[0]["status"] == "briefed")

        # goal-kind (d-owner-batch1 (2)). demo-goal above named NO kind, so it is the
        # absence arm; the enum default is spelled out as a LITERAL rather than read from
        # GOAL_KIND_DEFAULT — a check whose expectation reads the constant under test moves
        # with any edit to it and can never go red.
        print("goal-kind")
        demo_fm, _ = read_goal_md(gd)
        check("absent --kind stamps the default", demo_fm.get("goal-kind") == "interactive",
              str(demo_fm.get("goal-kind")))
        check("goals.csv carries the goal-kind column",
              idx and idx[0].get("goal-kind") == "interactive", str(idx))

        rc = cmd_scaffold(argparse.Namespace(
            goal_name="kinded-goal", type="one-shot", kind="non-interactive", due=None,
            contract=str(contract), **vars(ns)))
        kfm, _ = read_goal_md(root / "kinded-goal")
        check("explicit --kind round-trips to frontmatter",
              rc == 0 and kfm.get("goal-kind") == "non-interactive", str(kfm.get("goal-kind")))

        # The lint pair, and it is a PAIR on purpose: "legacy goal lints clean" alone would
        # also pass if the enum check never fired at all. The bad-kind arm is what proves the
        # check is live, so the clean arm means backward-compatible rather than unreachable.
        legacy = root / "legacy-goal"
        legacy.mkdir()
        (legacy / "goal.md").write_text(
            "---\nname: legacy-goal\ncreation-date: 2026-01-01\ntype: one-shot\n"
            "status: briefed\n---\n\ncontract\n", encoding="utf-8")
        badkind = root / "badkind-goal"
        badkind.mkdir()
        (badkind / "goal.md").write_text(
            "---\nname: badkind-goal\ncreation-date: 2026-01-01\ntype: one-shot\n"
            "goal-kind: nonsense\nstatus: briefed\n---\n\ncontract\n", encoding="utf-8")
        kind_finding = lambda items: any(i["check"] == "goal kind in enum" for i in items)
        check("a pre-existing goal with no goal-kind key raises no kind finding",
              not kind_finding(lint_goal(root, "legacy-goal").items))
        check("a goal-kind outside the enum IS a lint finding",
              kind_finding(lint_goal(root, "badkind-goal").items))

        print("scaffold refusals")
        for label, kwargs in (
            ("re-scaffold refused (create-only)",
             dict(goal_name="demo-goal", type="one-shot", due=None, contract=str(contract))),
            ("bad name refused",
             dict(goal_name="Bad_Name", type="one-shot", due=None, contract=str(contract))),
            ("bad type refused",
             dict(goal_name="other-goal", type="nonsense", due=None, contract=str(contract))),
            ("bad kind refused",
             dict(goal_name="other-goal", type="one-shot", kind="nonsense", due=None,
                  contract=str(contract))),
        ):
            try:
                cmd_scaffold(argparse.Namespace(**kwargs, **vars(ns)))
                check(label, False, "did not refuse")
            except Refusal:
                check(label, True)

        # G-118 regression. An unreadable `--contract` takes the Refusal path, never a crash.
        # `main()` catches `Refusal` ONLY, so a raw OSError from this read reached the operator
        # as a traceback and broke the never-a-crash contract of the README's exit-code table.
        # OSError is caught SEPARATELY from Refusal on purpose: with the guard removed this arm
        # reports FAIL naming the defect, instead of aborting the whole selftest with the very
        # traceback under test — a red arm has to stay legible when it goes red.
        # Both arms scaffold a goal that does NOT exist, so the refusal comes from the contract
        # read and from nothing earlier, and neither arm writes anything.
        print("contract read (G-118)")
        for label, bad in (("a missing file", tmp / "no-such-contract.md"),
                           ("a directory", tmp)):
            arm = f"unreadable --contract ({label}) refuses instead of crashing"
            try:
                cmd_scaffold(argparse.Namespace(
                    goal_name="contract-goal", type="one-shot", due=None,
                    contract=str(bad), **vars(ns)))
                check(arm, False, "did not refuse")
            except Refusal:
                check(arm, True)
            except OSError as exc:
                check(arm, False, f"G-118: a raw {type(exc).__name__} escaped as a crash")

        # G-117 regression. The no-open-row fallback returns the NUMERICALLY highest run: a
        # lexicographic sort on the folder name returned `run-9` while `run-11` existed.
        # THE FIXTURE SPANS THE SINGLE/DOUBLE-DIGIT BOUNDARY BECAUSE THAT IS THE ONLY PLACE THE
        # TWO ORDERINGS DIFFER — over runs 1..9 alone the broken sort and the correct one agree
        # and this check would pass against the defect. Built outside the goals root: it needs a
        # goal_dir and a `runs/` listing, and nothing here should add a goal the index then sees.
        print("run ordering (G-117)")
        order_goal = tmp / "runorder-goal"
        (order_goal / "runs").mkdir(parents=True)
        for n in (2, 9, 11):
            (order_goal / "runs" / f"run-{n}").mkdir()
        picked = current_run_dir(order_goal, Findings())
        check("no-open-row fallback picks the numerically highest run",
              picked is not None and picked.name == "run-11",
              f"picked {picked.name if picked else None} — lexicographic order returns run-9")

        print("lint")
        f = lint_goal(root, "demo-goal")
        check("lint finds the unstaffed run (no run compartment)", bool(f))
        f2 = lint_goal(root, "no-such-goal")
        check("lint refuses an absent goal", bool(f2))

        # name/layout violation: folder and goal.md disagree
        bad = root / "mismatch-goal"
        bad.mkdir()
        (bad / "goal.md").write_text(
            "---\nname: something-else\ncreation-date: 2026-01-01\ntype: one-shot\n"
            "status: briefed\n---\n\ncontract\n", encoding="utf-8")
        (bad / "decisions.md").write_text("x\n", encoding="utf-8")
        write_csv(bad / "runs.csv", RUNS_COLUMNS, [])
        (bad / "threads.sql").write_text(THREADS_SCHEMA, encoding="utf-8")
        f3 = lint_goal(root, "mismatch-goal")
        check("lint rejects a name violation",
              any(i["check"] == "folder name == goal.md name" for i in f3.items),
              str(f3.items))

        print("lint is read-only")
        before = {p: p.stat().st_mtime_ns for p in sorted(root.rglob("*")) if p.is_file()}
        lint_goal(root, "demo-goal")
        after = {p: p.stat().st_mtime_ns for p in sorted(root.rglob("*")) if p.is_file()}
        check("lint wrote nothing", before == after)

        print("materialize")
        # a minimal component database in the settled shape
        comp = tmp / "catalog" / "mod" / "comp"
        (comp / "prompts" / "cognitive-units" / "persona").mkdir(parents=True)
        (comp / "prompts" / "cognitive-units" / "permissions").mkdir(parents=True)
        (comp / "tasks" / "cognitive-units" / "task-goal").mkdir(parents=True)
        (comp / "capabilities" / "grep-it").mkdir(parents=True)
        (comp / "prompts" / "cognitive-units" / "persona" / "p.md").write_text(
            "---\nid: cu-persona-demo\ndescription: demo persona\n---\n\n"
            "<persona>\nYou are the demo seat.\n</persona>\n", encoding="utf-8")
        (comp / "prompts" / "cognitive-units" / "permissions" / "perm.md").write_text(
            "---\nid: cu-permissions-demo\ndescription: demo permissions\n---\n\n"
            "<permissions>\nRead the tree. Write nothing.\n</permissions>\n", encoding="utf-8")
        (comp / "tasks" / "cognitive-units" / "task-goal" / "g.md").write_text(
            "---\nid: cu-task-goal-demo\ndescription: demo goal\n---\n\n"
            "<task-goal>\nProve the assembly.\n</task-goal>\n", encoding="utf-8")
        (comp / "capabilities" / "grep-it" / "grep-it.md").write_text(
            "---\nid: cu-capability-grep-it\ndescription: find things\n---\n\n"
            "<capability>\nLong procedure that must NOT be inlined.\n</capability>\n",
            encoding="utf-8")
        (comp / "prompts.csv").write_text(
            "prompt-id,persona,permissions,description\n"
            "prompt-demo,cu-persona-demo@latest,cu-permissions-demo@latest,demo prompt\n",
            encoding="utf-8")
        # The task row deliberately carries BOTH label columns, spelled inside
        # the bare-id grammar: `t1` is the shape that refused all 27 rows of
        # admission-design-fork (2026-08-03), `7` the latent store-id shape that
        # escapes today only because real store ids carry a dot. The whole
        # end-to-end below therefore runs WITH the collision present — a
        # regression in NON_REF_COLUMNS turns the assembly checks red, not just
        # the two dedicated ones.
        tasks_csv = comp / "tasks.csv"
        tasks_csv.write_text(
            "task-id,store-task-id,design-id,task-goal,capabilities,description\n"
            "task-demo,7,t1,cu-task-goal-demo@latest,cu-capability-grep-it,demo task\n",
            encoding="utf-8")
        (comp / "seats.csv").write_text(
            "seat-id,prompt-id,task-id,description\n"
            "w-demo,prompt-demo,task-demo,the demo seat\n", encoding="utf-8")

        print("label columns are not unit references")
        label_row = next(csv.DictReader(tasks_csv.open(encoding="utf-8")))
        kept = [c for c, _ in _refs_of(label_row, NON_REF_COLUMNS)]
        check("a label cell yields no unit reference",
              kept == ["task-goal", "capabilities"], str(kept))
        # RED CONTROL — the check above must be able to FAIL. Drop the two label
        # names from the skip list and the SAME row must yield them as refs; a
        # green that survives this mutation is measuring nothing.
        unskipped = tuple(c for c in NON_REF_COLUMNS
                          if c not in ("design-id", "store-task-id"))
        red = [c for c, _ in _refs_of(label_row, unskipped)]
        check("red control: unskipped, the labels ARE read as refs",
              red == ["store-task-id", "design-id", "task-goal", "capabilities"],
              str(red))

        run = gd / "runs" / "run-1"
        run.mkdir(parents=True)
        write_csv(gd / "runs.csv", RUNS_COLUMNS, [{
            "run-id": "run-1", "type": "fresh", "state": "planning",
            "taskforce-id(s)": "tf-1", "opened": _today(), "closed": ""}])
        (run / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,w-demo,,claude,claude-opus-5,medium,50,m1\n", encoding="utf-8")
        write_csv(run / "milestones.csv", ["milestone-id", "name", "status"],
                  [{"milestone-id": "m1", "name": "prove it", "status": "pending"}])

        mns = argparse.Namespace(root=str(root), json=False, goal_name="demo-goal",
                                 catalog_root=str(tmp / "catalog"), force=False)
        rc = cmd_materialize(argparse.Namespace(dry_run=True, **vars(mns)))
        check("materialize --dry-run exits 0", rc == 0)
        check("dry-run wrote no seat folder", not (run / "seats").exists())

        rc = cmd_materialize(argparse.Namespace(dry_run=False, **vars(mns)))
        check("materialize exits 0", rc == 0)
        seat_md = run / "seats" / "w-demo" / "seat.md"
        check("seat.md written", seat_md.is_file())

        text = seat_md.read_text(encoding="utf-8")
        sfm, sbody = split_frontmatter(text, seat_md)
        check("frontmatter carries the binding",
              sfm.get("harness") == "claude" and sfm.get("model") == "claude-opus-5"
              and sfm.get("effort") == "medium" and str(sfm.get("ctx-refresh")) == "50",
              json.dumps(sfm))
        check("assembled ref is FROZEN (lockfile)",
              str(sfm.get("persona", "")).startswith(f"cu-persona-demo@latest+{STANDIN_VERSION_PREFIX}"),
              str(sfm.get("persona")))
        check("invoked ref stays @latest",
              str(sfm.get("capabilities", "")) == "cu-capability-grep-it@latest",
              str(sfm.get("capabilities")))
        check("body carries the kind-named block with stamped id",
              f'<persona id="cu-persona-demo" version="latest+{STANDIN_VERSION_PREFIX}' in sbody)
        check("assembled unit content is inlined", "You are the demo seat." in sbody)
        check("invoked unit is a loader STUB, not inlined",
              "Long procedure that must NOT be inlined." not in sbody
              and "Entry point:" in sbody)
        check("permissions unit assembled", '<permissions id="cu-permissions-demo"' in sbody)
        check("a label column emits no frontmatter ref key",
              "design-id" not in sfm and "store-task-id" not in sfm,
              json.dumps(sfm))

        try:
            cmd_materialize(argparse.Namespace(dry_run=False, **vars(mns)))
            check("re-materialize refused without --force", False, "did not refuse")
        except Refusal:
            check("re-materialize refused without --force", True)

        forced = dict(vars(mns))
        forced["force"] = True
        rc = cmd_materialize(argparse.Namespace(dry_run=False, **forced))
        check("--force regenerates", rc == 0)

        nocat = dict(vars(mns))
        nocat["catalog_root"] = None
        try:
            cmd_materialize(argparse.Namespace(dry_run=False, **nocat))
            check("materialize refuses without --catalog-root", False, "did not refuse")
        except Refusal:
            check("materialize refuses without --catalog-root", True)

        # The scanner's PURPOSE must survive the skip list: a genuinely dangling
        # reference in a REAL reference column still refuses. Same row, same
        # command — only the ref column's value changes.
        good_tasks = tasks_csv.read_text(encoding="utf-8")
        tasks_csv.write_text(
            "task-id,store-task-id,design-id,task-goal,capabilities,description\n"
            "task-demo,7,t1,cu-task-goal-absent@latest,cu-capability-grep-it,demo task\n",
            encoding="utf-8")
        try:
            cmd_materialize(argparse.Namespace(dry_run=True, **forced))
            check("a dangling unit ref STILL refuses", False, "did not refuse")
        except Refusal as exc:
            check("a dangling unit ref STILL refuses",
                  "cu-task-goal-absent" in str(exc), str(exc))
        tasks_csv.write_text(good_tasks, encoding="utf-8")

        print("lint after materialize")
        f4 = lint_goal(root, "demo-goal")
        check("a materialized goal lints CLEAN (gate open)", not bool(f4),
              json.dumps(f4.items, indent=2))

        print("lint catches a cycle")
        (run / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,a,b,claude,claude-opus-5,medium,50,m1\n"
            "tf-1,b,a,claude,claude-opus-5,medium,50,m1\n", encoding="utf-8")
        f5 = lint_goal(root, "demo-goal")
        check("lint rejects a cyclic after-graph",
              any(i["check"] == "after graph acyclic" for i in f5.items))

        # ------------------------------- the arm fires at the ACT (7.456 / MC14)
        # The four mutation classes the prior wave pre-computed, each ONE token off
        # a WELL-FORMED guarded manifest, driven through `materialize` itself.
        #
        # ⚠ EVERY ARM ASSERTS THE RULE NAME, never merely "it refused". Measured:
        # with these two rows unassemblable, the mutant that removes the wiring
        # ALSO refuses — on `seat 'p-demo' resolves to no row in any seats.csv` —
        # and an arm that accepted any `Refusal` passed under the mutant. So
        # `p-demo` is a seats.csv row BEFORE the loop: the manifest is assemblable,
        # and the ONLY thing left to refuse is the after-graph.
        print("materialize refuses a manifest whose after-graph does not validate")
        (comp / "seats.csv").write_text(
            "seat-id,prompt-id,task-id,description\n"
            "w-demo,prompt-demo,task-demo,the demo seat\n"
            "p-demo,prompt-demo,task-demo,the predecessor seat\n", encoding="utf-8")
        tf = run / "taskforce.csv"
        HEAD_ROW = "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        BODY = ("tf-1,p-demo,,claude,claude-opus-5,medium,50,m1\n"
                "tf-1,w-demo,{cell},claude,claude-opus-5,medium,50,m1\n")
        for label, cell, rule in (
            ("`p-demo[verdict]` (no =value)", "p-demo[verdict]", RULE_GUARD_GRAMMAR),
            ("`p-demo|` (empty limb)", "p-demo|", RULE_ALTERNATE_GRAMMAR),
            ("`p-demo[verdict=pass` (unclosed)", "p-demo[verdict=pass", RULE_GUARD_GRAMMAR),
            ("`ghost[verdict=pass]` (well-formed, unresolvable)", "ghost[verdict=pass]",
             "after edge resolves"),
        ):
            tf.write_text(HEAD_ROW + BODY.format(cell=cell), encoding="utf-8")
            # the ACT, and the no-write path: both unskippable, both naming the rule
            for dry in (False, True):
                arm = "--dry-run" if dry else "materialize"
                try:
                    cmd_materialize(argparse.Namespace(dry_run=dry, **forced))
                    check(f"{arm} refuses {label}", False, "did not refuse")
                except Refusal as exc:
                    check(f"{arm} refuses {label}, naming [{rule}]",
                          rule in str(exc), str(exc))

        # THE KEY, in the same change (`r-gate-ships-with-its-own-key`): the SAME
        # cell shape, well-formed and resolvable, still materializes. Without this
        # arm the eight above are satisfied by a materialize that refuses everything.
        tf.write_text(HEAD_ROW + BODY.format(cell="p-demo[verdict=pass]"), encoding="utf-8")
        rc = cmd_materialize(argparse.Namespace(dry_run=False, **forced))
        check("a WELL-FORMED guarded manifest still materializes", rc == 0)
        check("both seats written",
              (run / "seats" / "w-demo" / "seat.md").is_file()
              and (run / "seats" / "p-demo" / "seat.md").is_file())

        # ------------------------------------------------ gate-key check
        # Spec: runs/run-3/planning/briefing-gate-ships-with-its-own-key-check/
        # gate-key-check-spec.md (ACCEPTED, sha256/16 9c5e4a09dbaed6b5).
        #
        # The fixture's class and limb names are INVENTED (cls-*, limb-*), never
        # the live ones: § 3c forbids a literal copy of the eleven classes, the
        # seven limbs or the four dispositions anywhere in this file, test
        # fixtures explicitly included. The fixture proves the READER; the live
        # enumeration is exercised against the real source, asserting only
        # relations it computes there, never values copied to here.
        print("gate-key check — the source-enumeration reader (§ 3a)")
        fixture = tmp / "fixture"
        fixture.mkdir(parents=True, exist_ok=True)
        fake_coord = fixture / "coord.py"
        fake_coord.write_text(
            "_DEFERRAL_BY_DISPOSITION = {'d1': 'cls-alpha', 'd2': 'cls-beta'}\n"
            "CLASS_TO_VERDICT = {'cls-alpha': 'A', 'cls-beta': 'B', 'cls-gamma': 'C'}\n"
            "ADMISSION_LIMBS = ('limb-one', 'limb-two')\n"
            "SHIPS_DARK = False\n"
            "SHIPS_LIT = True\n"
            "SHIPS_EMPTY = ''\n"
            "# GHOST_SYMBOL is named ONLY in this comment.\n"
            '"""GHOST_SYMBOL is named again here, in a docstring."""\n',
            encoding="utf-8")

        fclasses, flimbs, fproblem = read_live_classes(fake_coord)
        check("§3a reader: the union takes VALUES of the disposition map, not keys",
              fproblem is None and fclasses == {"cls-alpha", "cls-beta", "cls-gamma"}
              and "d1" not in fclasses, f"{fproblem} {sorted(fclasses or [])}")
        check("§3a reader: limbs read from source", flimbs == {"limb-one", "limb-two"},
              str(sorted(flimbs or [])))
        # RED CONTROL — a source missing a symbol must be REPORTED, never
        # silently degraded to the § 3b arm.
        maimed = fixture / "coord-maimed.py"
        maimed.write_text("_DEFERRAL_BY_DISPOSITION = {}\nCLASS_TO_VERDICT = {}\n",
                          encoding="utf-8")
        mc, ml, mp = read_live_classes(maimed)
        check("red control: an absent symbol is REPORTED, not degraded",
              mc is None and ml is None and mp is not None
              and "ADMISSION_LIMBS" in mp, str(mp))
        mc2, _, mp2 = read_live_classes(fixture / "nope.py")
        check("red control: an unreadable source is REPORTED",
              mc2 is None and mp2 is not None and "unreadable" in mp2, str(mp2))

        # The reader against the LIVE source — the integration arm. It asserts
        # RELATIONS computed there, never a value copied to here.
        lclasses, llimbs, lproblem = read_live_classes(coord_source_path())
        if lproblem is None:
            live_lits = _module_level_literals(
                coord_source_path().read_text(encoding="utf-8"))
            check("§3a live: the union is a superset of the disposition VALUES",
                  set(live_lits["_DEFERRAL_BY_DISPOSITION"].values()) <= lclasses
                  and bool(lclasses) and bool(llimbs),
                  f"{len(lclasses)} classes / {len(llimbs)} limbs")
            check("§3a live: FABRICATED control — an invented class is ABSENT",
                  "cls-fabricated-control" not in lclasses)
        else:
            check("§3a live: the live source reads", False, str(lproblem))

        print("gate-key check — arm 2's matcher (§ 2b)")
        hits = gate_key_lexicon_hits("This gate refuses to admit it, and defers the guard.")
        check("§2b matcher: word-boundary hits, with the inflection tail",
              set(hits) == {"gate", "refuse", "admit", "defer", "guard"}, str(hits))
        # RED CONTROL — substring matching is REFUSED as an implementation:
        # measured, it fires on gateway x53, aggregate x7, unblock x6 purely as
        # a matcher artefact. Under a substring matcher this line returns hits.
        contam = gate_key_lexicon_hits("The gateway aggregates and unblocks the ungated.")
        check("red control: substring contamination yields NO hit", contam == [],
              str(contam))

        print("gate-key check — the declaration (§ 1) and the refusals (§ 5)")
        pass_dir = run / "planning" / "pass-demo"
        pass_dir.mkdir(parents=True, exist_ok=True)
        decl = pass_dir / GATE_KEY_DECLARATION_NAME
        head = ",".join(GATE_KEY_COLUMNS) + "\n"

        def gk(body: str, coord=fake_coord) -> dict:
            decl.write_text(head + body, encoding="utf-8")
            return gate_key_check(root, "demo-goal", "pass-demo", Findings(),
                                  coord_path=coord)

        def codes(res: dict) -> list[str]:
            return [b.split("\n")[0].split()[-1] for b in res["refusals"]]

        r = gk("t1,,,,,,\n")
        check("§2a: a blank lands-mechanism is REFUSED",
              codes(r) == ["blank-declaration"], str(codes(r)))
        # RED CONTROL — the same row declared explicitly must NOT refuse.
        r = gk("t1,no,,,,,\n")
        check("red control: an explicit 'no' is not refused", codes(r) == [], str(codes(r)))

        r = gk("t1,yes,cls-alpha;cls-beta,,,,\n")
        check("§5: a declared class with no key-form is uncovered-class",
              codes(r) == ["uncovered-class"], str(codes(r)))
        check("§5: uncovered classes are NAMED, never counted",
              "uncovered classes: cls-alpha, cls-beta" in r["refusals"][0],
              r["refusals"][0] if r["refusals"] else "")

        r = gk("t1,yes,cls-alpha,K1,t2,,\nt2,no,,,,,\n")
        check("§4 K1: an id of THIS declaration verifies (never a store lookup)",
              codes(r) == [], str(codes(r)))
        r = gk("t1,yes,cls-alpha,K1,7.999,,\n")
        check("red control: K1 naming a non-member is key-unresolved",
              codes(r) == ["key-unresolved"], str(codes(r)))

        r = gk("t1,yes,cls-alpha,K2,fixture/coord.py#SHIPS_LIT,,\n")
        check("§4 K2: a module-level assignment resolves", codes(r) == [], str(codes(r)))
        # RED CONTROL — the K2 read is by AST, so a symbol living only in a
        # comment or a docstring is NOT a key. A substring read would pass this.
        r = gk("t1,yes,cls-alpha,K2,fixture/coord.py#GHOST_SYMBOL,,\n")
        check("red control: a comment/docstring-only symbol is NOT a K2 key",
              codes(r) == ["key-unresolved"], str(codes(r)))
        r = gk("t1,yes,cls-alpha,K2,fixture/absent.py#SHIPS_DARK,,\n")
        check("red control: an unresolvable K2 path is key-unresolved",
              codes(r) == ["key-unresolved"], str(codes(r)))

        # § 6a — the check's OWN key: the K3 ships-dark path.
        r = gk("t1,yes,cls-alpha,K3,fixture/coord.py#SHIPS_DARK,False,\n")
        check("§4 K3: a falsy default matching the declaration verifies",
              codes(r) == [], str(codes(r)))
        r = gk("t1,yes,cls-alpha,K3,fixture/coord.py#SHIPS_EMPTY,'',\n")
        check("§4 K3: an empty-string default is falsy and verifies",
              codes(r) == [], str(codes(r)))
        # § 7a AS AMENDED (p-arm-iii-RULED-a-dark-gate-flags): a SATISFIED K3
        # FLAGS, so a plan landing a dark gate never reads like a keyed one.
        # 7.323 measured the unamended behaviour: the two outputs were
        # byte-identical, which is what the ruling closes.
        r = gk("t1,yes,cls-alpha,K3,fixture/coord.py#SHIPS_DARK,False,\n")
        check("§7a: a satisfied K3 FLAGS — a dark gate is never silent",
              any(x.startswith("ships-dark: t1") for x in r["flags"]), str(r["flags"]))
        check("the ships-dark flag NAMES the class whose key is still owed",
              any("cls-alpha" in x for x in r["flags"] if x.startswith("ships-dark:")),
              str(r["flags"]))
        # RED CONTROL — a KEYED gate (K1, same class, same row shape) must raise
        # NO dark flag, or the flag is not discriminating darkness at all.
        r = gk("t1,yes,cls-alpha,K1,t1,,\n")
        check("red control: a keyed gate raises NO ships-dark flag",
              not any(x.startswith("ships-dark:") for x in r["flags"]), str(r["flags"]))
        # RED CONTROL — a REFUSED K3 must not also flag: a refusal is not a
        # tracked dark state, and exit 1 must never be softened to 3.
        r = gk("t1,yes,cls-alpha,K3,fixture/coord.py#SHIPS_LIT,True,\n")
        check("red control: a REFUSED K3 raises no ships-dark flag",
              not any(x.startswith("ships-dark:") for x in r["flags"]), str(r["flags"]))

        # RED CONTROL — declared dark, ships LIT.
        r = gk("t1,yes,cls-alpha,K3,fixture/coord.py#SHIPS_LIT,True,\n")
        check("red control: a TRUTHY K3 default is dark-not-dark",
              codes(r) == ["dark-not-dark"], str(codes(r)))
        r = gk("t1,yes,cls-alpha,K3,fixture/coord.py#SHIPS_DARK,True,\n")
        check("red control: source and declaration disagreeing is dark-not-dark",
              codes(r) == ["dark-not-dark"], str(codes(r)))
        r = gk("t1,yes,cls-alpha,K3,fixture/coord.py#SHIPS_DARK,,\n")
        check("red control: K3 with no ships-dark-default is schema-violation",
              codes(r) == ["schema-violation"], str(codes(r)))

        # The § 3a arm engages on a row naming at least one class the live
        # enumeration knows; the unknown one beside it is then refused. A row
        # naming NO known class is § 3b's, two rows below — which is what makes
        # this code reachable instead of vacuous.
        r = gk("t1,yes,cls-alpha;cls-nowhere,K1,t1,,\n")
        check("§5: a class absent from the live enumeration is class-not-in-source",
              codes(r) == ["class-not-in-source"], str(codes(r)))
        check("class-not-in-source NAMES the class",
              "uncovered classes: cls-nowhere" in r["refusals"][0], str(r["refusals"]))
        # § 3b — a row naming no known class sits on another lifecycle path: the
        # partition-unverified line is mandatory, and it FLAGS rather than refuses.
        r = gk("t1,yes,planning-pass-refused,K1,t1,,\n")
        check("§3b: an off-enumeration partition is reported, not refused",
              codes(r) == [] and any(x.startswith("partition-unverified: t1")
                                     for x in r["reports"]), str(r["reports"]))
        check("§3b: the unverified partition FLAGS", any("partition-unverified" in x
                                                         for x in r["flags"]),
              str(r["flags"]))
        # § 3a — an unreadable source is REPORTED and does not degrade to § 3b.
        r = gk("t1,yes,cls-alpha,K1,t1,,\n", coord=fixture / "nope.py")
        check("§3a: an unreadable source reports and flags, never degrades silently",
              any("source-enumeration-unreadable" in x for x in r["flags"])
              and codes(r) == [], f"{r['flags']} {codes(r)}")

        # § 2b — arm 2 is landed but NOT exercised: at fan-in the store rows do
        # not exist, so no scannable task text resolves. It says so on every run.
        r = gk("t1,no,,,,,\n")
        check("§2b: arm 2 reports itself UNexercised on every run",
              any(x.startswith("lexicon-unexercised:") for x in r["reports"]),
              str(r["reports"]))

        decl.write_text("task-id,lands-mechanism,defers-classes\nt1,yes,cls-alpha\n",
                        encoding="utf-8")
        r = gate_key_check(root, "demo-goal", "pass-demo", Findings(), coord_path=fake_coord)
        check("§1: a header mismatch is REFUSED, never repaired",
              codes(r) == ["schema-violation"], str(codes(r)))
        (pass_dir / GATE_KEY_DECLARATION_NAME).unlink()
        r = gate_key_check(root, "demo-goal", "pass-demo", Findings(), coord_path=fake_coord)
        check("§1: an absent declaration is REFUSED",
              codes(r) == ["schema-violation"], str(codes(r)))

        print("gate-key check — the exit-code contract (§ 7a) at the real invocation")
        # Driven through main() so build_parser's registration is exercised too.
        # These declarations never depend on the live enumeration's CONTENT:
        # a no-class row flags under neither arm, and an off-enumeration class
        # flags under § 3b whether or not the live source reads.
        decl.write_text(head + "t1,no,,,,,\n", encoding="utf-8")
        rc = main(["--root", str(root), "gate-key-check", "demo-goal",
                   "--pass-folder", "pass-demo"])
        check("§7a: exit 0 — clean", rc == 0, str(rc))
        decl.write_text(head + "t1,yes,off-enumeration-class,K1,t1,,\n", encoding="utf-8")
        rc = main(["--root", str(root), "gate-key-check", "demo-goal",
                   "--pass-folder", "pass-demo"])
        check("§7a: exit 3 — flagged-pass, never 2 (argparse owns 2)", rc == 3, str(rc))
        # § 7a as amended — the ships-dark arm END-TO-END, and UNCONFOUNDED: the
        # class is COMPUTED from the live source at run time (§ 3c forbids a
        # literal class name here, test fixtures included), so § 3b's
        # partition-unverified CANNOT fire and the dark flag is the only one
        # left. Two flag sources reaching one exit code would measure neither.
        if lproblem is None and lclasses:
            live_cls = sorted(lclasses)[0]
            (pass_dir / "dark_switch.py").write_text("SHIPS_DARK = False\n",
                                                     encoding="utf-8")
            decl.write_text(
                head + f"t1,yes,{live_cls},K3,dark_switch.py#SHIPS_DARK,False,\n",
                encoding="utf-8")
            rc = main(["--root", str(root), "gate-key-check", "demo-goal",
                       "--pass-folder", "pass-demo"])
            check("§7a: exit 3 — a satisfied K3 flags end-to-end", rc == 3, str(rc))
            # RED CONTROL — the SAME row, same class, KEYED instead of dark,
            # exits 0. That is what attributes the 3 above to the dark flag.
            decl.write_text(head + f"t1,yes,{live_cls},K1,t1,,\n", encoding="utf-8")
            rc = main(["--root", str(root), "gate-key-check", "demo-goal",
                       "--pass-folder", "pass-demo"])
            check("red control: the same row KEYED exits 0 — the 3 was the dark flag",
                  rc == 0, str(rc))
        decl.write_text(head + "t1,,,,,,\n", encoding="utf-8")
        rc = main(["--root", str(root), "gate-key-check", "demo-goal",
                   "--pass-folder", "pass-demo"])
        check("§7a: exit 1 — REFUSED", rc == 1, str(rc))

        # § 7b — --json is exit-code-preserving. A caller gating on the envelope
        # and a caller gating on the exit code must never disagree.
        buf = io.StringIO()
        _stdout = sys.stdout
        try:
            sys.stdout = buf
            rc_json = main(["--root", str(root), "--json", "gate-key-check",
                            "demo-goal", "--pass-folder", "pass-demo"])
        finally:
            sys.stdout = _stdout
        env = json.loads(buf.getvalue())
        check("§7b: the --json envelope agrees with the exit code",
              env["exit"] == rc_json == 1 and env["ok"] is False
              and any(i["check"] == "gate-key: blank-declaration" for i in env["findings"]),
              buf.getvalue()[:400])

        # § 6b — the check's OWN key: the explicit RECORDED override. Auditable
        # AFTER, never gated before; a record it could not write is a refusal.
        print("gate-key check — the check's own key (§ 6b)")
        ovr = argparse.Namespace(root=str(root), json=False, goal_name="demo-goal",
                                 pass_folder="pass-demo", override="p-some-leader-anchor")
        rc = cmd_gate_key_check(ovr)
        rec = pass_dir / GATE_KEY_OVERRIDE_NAME
        check("§6b: an override turns a refusal into exit 0", rc == 0, str(rc))
        check("§6b: the override RECORD is on disk", rec.is_file())
        rec_text = rec.read_text(encoding="utf-8") if rec.is_file() else ""
        check("§6b: the record carries the anchor and the refusal VERBATIM",
              "p-some-leader-anchor" in rec_text
              and "REFUSED  t1  blank-declaration" in rec_text, rec_text[:300])
        # RED CONTROL — an empty anchor is not an override.
        rec.unlink()
        ovr_blank = argparse.Namespace(root=str(root), json=False, goal_name="demo-goal",
                                       pass_folder="pass-demo", override="   ")
        rc = cmd_gate_key_check(ovr_blank)
        check("red control: an empty anchor does NOT override", rc == 1, str(rc))
        check("red control: an empty anchor writes no record", not rec.is_file())
        # RED CONTROL — an unwritable pass folder: the override FAILS CLOSED.
        decl_body = decl.read_text(encoding="utf-8")
        ovr_gone = argparse.Namespace(root=str(root), json=False, goal_name="demo-goal",
                                      pass_folder="pass-absent",
                                      override="p-some-leader-anchor")
        buf2 = io.StringIO()
        _err = sys.stderr
        try:
            sys.stderr = buf2
            rc = cmd_gate_key_check(ovr_gone)
        finally:
            sys.stderr = _err
        # rc==1 alone would be confounded — the absent declaration refuses this
        # folder anyway. The discriminating read is the override's OWN block.
        check("red control: an unwritable record is a REFUSAL, not an override",
              rc == 1 and "a record it could not write is a refusal" in buf2.getvalue(),
              f"{rc} {buf2.getvalue()[:300]}")
        decl.write_text(decl_body, encoding="utf-8")

        # 7.342 — the two silent skips. Each case is a RED CONTROL kept: the fix is
        # only evidence if the pre-fix behaviour is shown failing for the right reason,
        # and a control that lives in an ephemeral seat folder dies with the seat.
        print("check-acyclic (7.342: the vacuous-clean paths)")
        ca = tmp / "ca"
        ca.mkdir()
        (ca / "cyclic-nonseat.csv").write_text(
            "milestone-id,after\nm-a,m-b\nm-b,m-a\n", encoding="utf-8")
        (ca / "acyclic-nonseat.csv").write_text(
            "milestone-id,after\nm-a,\nm-b,m-a\n", encoding="utf-8")
        (ca / "dag.md").write_text(
            "### 9.001 — `alpha`\n**`after`: `9.002`** — one.\n\n"
            "### 9.002 — `beta`\n**`after`: `9.001`** — closes the loop.\n", encoding="utf-8")

        def ca_run(name: str, **kw) -> int:
            return cmd_check_acyclic(argparse.Namespace(
                file=str(ca / name), id_col=kw.get("id_col", "seat"),
                after_col=kw.get("after_col", "after"), **vars(ns)))

        for label, name, kw in (
            ("an ABSENT id column REFUSES (was: empty edge map, clean)",
             "cyclic-nonseat.csv", {}),
            ("an ABSENT after column REFUSES (a typo cannot read clean)",
             "cyclic-nonseat.csv", {"id_col": "milestone-id", "after_col": "predecessors"}),
        ):
            try:
                ca_run(name, **kw)
                check(label, False, "no Refusal raised")
            except Refusal:
                check(label, True)
        check("the same cyclic graph is REPORTED once its columns are named",
              ca_run("cyclic-nonseat.csv", id_col="milestone-id") == 1)
        check("red control: an ACYCLIC graph on the same key is still CLEAN",
              ca_run("acyclic-nonseat.csv", id_col="milestone-id") == 0)
        check("a markdown task DAG's edge set is read, and its cycle REPORTED",
              ca_run("dag.md") == 1)

        # 7.426 (W3) — the guard-grammar arm, on the surface a manifest is registered
        # through. Each row is paired with the control that makes it discriminating:
        # a green over a file the arm could not have refused proves nothing.
        print("after-member grammar (7.426: guards and alternates at registration)")
        (ca / "guards-ok.csv").write_text(
            "Seat/workflow,after\n"
            "a,\n"
            "b,\n"
            "c,a[verdict=accepted]\n"          # a guard
            "d,a|b\n"                          # an alternate join
            "e,\"c, d[ok=y|n]\"\n",            # a `|` INSIDE a guard value
            encoding="utf-8")
        (ca / "guard-malformed.csv").write_text(
            "Seat/workflow,after\na,\nb,a[nokey]\n", encoding="utf-8")
        (ca / "alt-empty-limb.csv").write_text(
            "Seat/workflow,after\na,\nb,a|\n", encoding="utf-8")
        (ca / "cycle-via-limb.csv").write_text(
            "Seat/workflow,after\na,b[g=y]|c\nb,\nc,a\n", encoding="utf-8")

        def ca_out(name: str, **kw) -> tuple[int, str]:
            buf, _o = io.StringIO(), sys.stdout
            sys.stdout = buf
            try:
                rc = ca_run(name, id_col="Seat/workflow", **kw)
            finally:
                sys.stdout = _o
            return rc, buf.getvalue()

        rc, out = ca_out("guards-ok.csv")
        # 5 edges, computed from the file before running it: c<-a, d<-a, d<-b, e<-c,
        # e<-d. The `|` inside `d[ok=y|n]` is a guard VALUE and contributes ONE edge,
        # not two — a strip-then-split reading would report 6.
        check("a well-formed guarded manifest validates CLEAN", rc == 0 and "clean" in out,
              f"{rc} {out}")
        check("a `|` inside a guard VALUE is not an alternate (5 edges, not 6)",
              "5 edge(s) read" in out, out)
        rc, out = ca_out("guard-malformed.csv")
        check("a MALFORMED guard is refused, naming the guard-grammar rule",
              rc == 1 and RULE_GUARD_GRAMMAR in out and "a[nokey]" in out, f"{rc} {out}")
        rc, out = ca_out("alt-empty-limb.csv")
        check("an EMPTY alternate limb is refused, naming the alternate rule",
              rc == 1 and RULE_ALTERNATE_GRAMMAR in out, f"{rc} {out}")
        rc, out = ca_out("cycle-via-limb.csv")
        # The strip-then-split control: the ONLY path from a back to a runs through
        # limb `c` of `b[g=y]|c`. Truncating at the first bracket loses it and this
        # file reads CLEAN — which is what this row would have said before 7.426.
        check("a cycle through an ALTERNATE LIMB is reported (strip-then-split closed)",
              rc == 1 and "after graph acyclic" in out, f"{rc} {out}")
        check("red control: the grammar arm is not firing on the clean file",
              RULE_GUARD_GRAMMAR not in ca_out("guards-ok.csv")[1])

        print("index_units (7.342: the silent tag drop)")
        cat = tmp / "cat" / "demo" / "prompts" / "cognitive-units" / "roles"
        cat.mkdir(parents=True)
        (cat / "good.md").write_text(
            "---\nid: demo-role\n---\n\n<role>\nbody\n</role>\n", encoding="utf-8")
        check("a well-formed unit indexes", len(index_units(tmp / "cat")) == 1)
        (cat / "bare.md").write_text(
            "---\nid: demo-bare\nkind: role\n---\n\nbody with no wrapper\n", encoding="utf-8")
        try:
            index_units(tmp / "cat")
            check("an untagged UNIT file is REPORTED (was: dropped in silence)", False,
                  "no Refusal raised")
        except Refusal as exc:
            check("an untagged UNIT file is REPORTED (was: dropped in silence)",
                  "bare.md" in str(exc), str(exc))
        (cat / "bare.md").unlink()
        (tmp / "cat" / "demo" / "component.md").write_text(
            "---\nid: demo\n---\n\nno kind tag here, and none is owed\n", encoding="utf-8")
        check("red control: a NON-unit file with no tag is still skipped SILENTLY",
              len(index_units(tmp / "cat")) == 1)

        print("reindex")
        rc = cmd_reindex(argparse.Namespace(root=str(root), json=False))
        check("reindex exits 0", rc == 0)
        idx2 = list(csv.DictReader((root / "goals.csv").open(encoding="utf-8")))
        # 5 = demo-goal + kinded-goal + legacy-goal + badkind-goal + mismatch-goal. The count is
        # spelled out rather than derived from the tree, because deriving it from the same
        # directory listing the projection walks would pass whatever the projection did.
        check("reindex projects every goal", len(idx2) == 5, str(len(idx2)))
        check("reindex columns are the goals-index schema",
              list(idx2[0].keys()) == GOALS_INDEX_COLUMNS, str(list(idx2[0].keys())))

        (root / "broken" ).mkdir()
        (root / "broken" / "goal.md").write_text("---\nname: [unclosed\n---\nx\n",
                                                 encoding="utf-8")
        before_idx = (root / "goals.csv").read_text(encoding="utf-8")
        try:
            cmd_reindex(argparse.Namespace(root=str(root), json=False))
            check("reindex fails loud on an unparseable goal.md", False, "did not refuse")
        except Refusal:
            check("reindex fails loud on an unparseable goal.md", True)
        check("failed reindex left goals.csv untouched",
              (root / "goals.csv").read_text(encoding="utf-8") == before_idx)

    print()
    if failures:
        print(f"selftest: {len(failures)} FAILURE(S)")
        for x in failures:
            print(f"  - {x}")
        return 1
    print("selftest: PASS — 0 failures")
    return 0


# ---------------------------------------------------------------- cli


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="rbtv-goal",
        description="The goals-tree machinery: scaffold, reindex, lint, materialize "
                    "(CMP-4 / CMP-14 / CMP-5).",
    )
    ap.add_argument("--root", default=None,
                    help="the .rbtv/goals root (default: walk up from the working "
                         "directory). Pass it explicitly to aim a write verb at a test tree.")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope")
    sub = ap.add_subparsers(dest="verb", required=True)

    def add_common(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """--root/--json accepted on either side of the verb.

        SUPPRESS is load-bearing: without it an omitted post-verb flag would
        store its default and silently overwrite the pre-verb one.
        """
        p.add_argument("--root", default=argparse.SUPPRESS)
        p.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        return p

    p = add_common(sub.add_parser("scaffold", help="create a goal folder (create-only) + reindex"))
    p.add_argument("goal_name")
    p.add_argument("--type", default="one-shot", choices=list(GOAL_TYPES))
    p.add_argument("--kind", default=GOAL_KIND_DEFAULT, choices=list(GOAL_KINDS),
                   help="the goal-kind stamped into goal.md frontmatter "
                        f"(default: {GOAL_KIND_DEFAULT}, owner ruling d-owner-batch1)")
    p.add_argument("--due", default=None)
    p.add_argument("--contract", required=True,
                   help="FILE, or - for stdin: the goal-radius contract prose")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_scaffold)

    p = add_common(sub.add_parser("reindex", help="rebuild goals.csv from every goal.md frontmatter"))
    p.set_defaults(func=cmd_reindex)

    p = add_common(sub.add_parser("lint", help="read-only validate + dry-run emulate (exit 0/1)"))
    p.add_argument("goal_name")
    p.set_defaults(func=cmd_lint)

    p = add_common(sub.add_parser("materialize", help="create seat folders + assemble each seat.md"))
    p.add_argument("goal_name")
    p.add_argument("--catalog-root", default=None,
                   help="root of the component databases (CMP-5) the units resolve through")
    p.add_argument("--force", action="store_true",
                   help="regenerate an already-materialized run")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_materialize)

    # § 7b — the invocation shape the specification fixes. Registered through
    # add_common like every other verb, so --root/--json work on either side of
    # the verb; SUPPRESS is load-bearing (see add_common's own docstring).
    p = add_common(sub.add_parser(
        "gate-key-check",
        help="refuse a plan landing a keyless gate (exit 0 clean / 1 refused / 3 flagged)"))
    p.add_argument("goal_name")
    p.add_argument("--pass-folder", required=True,
                   help="the pass folder NAME under runs/<current-run>/planning/, "
                        "never a path")
    p.add_argument("--override", default=None,
                   help="a leader-ruling anchor: the check's OWN key (§ 6b). "
                        "Auditable AFTER, never gated before — it writes "
                        "gate-key-override.md and is never silent")
    p.set_defaults(func=cmd_gate_key_check)

    # The room's ONLY sanctioned acyclicity check, exposed (Rule 9 forbids a hand-rolled
    # walk, and three ordered callers needed one). Reachable only from `lint` before 7.342.
    p = add_common(sub.add_parser(
        "check-acyclic",
        help="the after-graph of a csv or a markdown task DAG is acyclic (exit 0/1)"))
    p.add_argument("file", help="a .csv (taskforce, milestones, a manifest) or a .md task DAG")
    p.add_argument("--id-col", default="seat",
                   help="the column naming each node (csv only; default: seat). "
                        "milestones.csv is milestone-id, a manifest is 'Seat/workflow'")
    p.add_argument("--after-col", default="after",
                   help="the column (or markdown label) carrying each node's predecessors")
    p.set_defaults(func=cmd_check_acyclic)

    # MC8 / 7.450 — mint a branch's home at the registry's settled path. Create-only:
    # it makes the folder and nothing else; MC10's materialization fills it.
    p = add_common(sub.add_parser(
        "branch-home",
        help="mint a branch home under a run (or under another branch), create-only"))
    p.add_argument("goal_name")
    p.add_argument("--parent", default=None,
                   help="the parent run or branch folder, as a path RELATIVE to the goal "
                        "folder (e.g. runs/run-1/branches/branch-1). Default: the goal's "
                        "current run, resolved through runs.csv")
    p.add_argument("--branch", default=None,
                   help="name the branch folder explicitly (`branch-<m>`). Default: the "
                        "next number under the parent's branches/")
    p.add_argument("--dry-run", action="store_true",
                   help="report the path the numbering rule returns; create nothing")
    p.set_defaults(func=cmd_branch_home)

    p = add_common(sub.add_parser("selftest", help="end-to-end exercise on a throwaway tree"))
    p.set_defaults(func=cmd_selftest)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
