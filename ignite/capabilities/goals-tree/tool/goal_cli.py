#!/usr/bin/env python3
"""rbtv-goal — the goals-tree machinery (task 7.63).

Four verbs over the CMP-4 goals tree, all LOCAL file operations (they work with
the daemon down, which is why they live on the rbtv side and never on ignite):

    rbtv-goal scaffold <goal-name> --contract FILE|-  [--type T] [--due DATE] [--dry-run]
    rbtv-goal reindex
    rbtv-goal lint <goal-name>
    rbtv-goal materialize <goal-name> [--catalog-root DIR] [--force] [--dry-run]

Grammar is owner-ruled (r-763-grammar-ruled, all four items at their recommended
defaults) and is implemented here, not re-derived. Exit codes follow the sd-graph
convention: 0 success/clean, 1 refusal/gate-fail/not-found, 2 usage error.

v1 ships standalone; it folds into `rbtv goal <verb>` verbatim when task 7.65
lands (the operator-surface stand-in pattern — no contract change at fold-in).
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------- constants

GOAL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

GOAL_TYPES = ("one-shot", "recurring")
GOAL_STATUSES = ("briefed", "active", "standing", "completed", "abandoned")

# goals-index schema (concept goals-index § file schema)
GOALS_INDEX_COLUMNS = ["name", "creation date", "due date", "type", "status"]
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

    goal_dir = root / name
    if goal_dir.exists():
        raise Refusal(
            f"{goal_dir}: already exists — scaffold is create-only and never overwrites"
        )

    contract = (
        sys.stdin.read() if args.contract == "-"
        else Path(args.contract).read_text(encoding="utf-8")
    )
    if not contract.strip():
        raise Refusal("--contract resolved to empty text — a goal is born with its contract")

    fm = {
        "name": name,
        "creation-date": _today(),
        "due-date": args.due or "",
        "type": args.type,
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
    folders = sorted(
        (p for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith("run-")),
        key=lambda p: p.name,
    )
    return folders[-1] if folders else None


def check_acyclic(rows: list[dict], f: Findings, path: Path) -> None:
    """The after-graph MUST be acyclic (taskforce-descriptor; goal-lint rejects a cycle)."""
    edges: dict[str, list[str]] = {}
    for row in rows:
        seat = (row.get("seat") or "").strip()
        if not seat:
            continue
        raw = (row.get("after") or "").strip()
        preds = []
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            # strip a guard `ref[field=value]`; alternates a|b are a whichever-ran join
            entry = entry.split("[", 1)[0]
            preds.extend(p.strip() for p in entry.split("|") if p.strip())
        edges[seat] = preds

    for seat, preds in edges.items():
        for p in preds:
            if p not in edges:
                f.add("after edge resolves", str(path),
                      f"seat '{seat}' lists predecessor '{p}', which is not a seat row")

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


def lint_goal(root: Path, name: str) -> Findings:
    """READ-ONLY validation + dry-run emulation (CMP-14). Writes NOTHING, ever."""
    f = Findings()
    goal_dir = root / name

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
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict) or not fm.get("id"):
            continue
        body = text[m.end():]
        tag = re.search(r"<([a-z0-9-]+)>(.*?)</\1>", body, re.DOTALL)
        if not tag:
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
        "id": seat_id,
        "description": (srow.get("description") or "").strip(),
    }
    for col in BINDING_COLUMNS:
        if str(binding.get(col, "") or "").strip():
            fm[col] = str(binding[col]).strip()

    blocks: list[str] = []
    skip = ("seat-id", "prompt-id", "task-id", "executor", "description")
    for label, row in parts:
        for kind_col, refs in _refs_of(row, skip):
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
    goal_dir = root / args.goal_name
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

        print("scaffold refusals")
        for label, kwargs in (
            ("re-scaffold refused (create-only)",
             dict(goal_name="demo-goal", type="one-shot", due=None, contract=str(contract))),
            ("bad name refused",
             dict(goal_name="Bad_Name", type="one-shot", due=None, contract=str(contract))),
            ("bad type refused",
             dict(goal_name="other-goal", type="nonsense", due=None, contract=str(contract))),
        ):
            try:
                cmd_scaffold(argparse.Namespace(**kwargs, **vars(ns)))
                check(label, False, "did not refuse")
            except Refusal:
                check(label, True)

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
        (comp / "tasks.csv").write_text(
            "task-id,task-goal,capabilities,description\n"
            "task-demo,cu-task-goal-demo@latest,cu-capability-grep-it,demo task\n",
            encoding="utf-8")
        (comp / "seats.csv").write_text(
            "seat-id,prompt-id,task-id,description\n"
            "w-demo,prompt-demo,task-demo,the demo seat\n", encoding="utf-8")

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

        print("reindex")
        rc = cmd_reindex(argparse.Namespace(root=str(root), json=False))
        check("reindex exits 0", rc == 0)
        idx2 = list(csv.DictReader((root / "goals.csv").open(encoding="utf-8")))
        check("reindex projects every goal", len(idx2) == 2, str(len(idx2)))
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
