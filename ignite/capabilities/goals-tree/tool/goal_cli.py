#!/usr/bin/env python3
"""rbtv-goal — the goals-tree machinery (task 7.63).

The verbs over the CMP-4 goals tree — LOCAL file operations, with ONE stated
exception (they work with the daemon down, which is why they live on the rbtv
side and never on ignite):

    rbtv-goal scaffold <goal-name> --contract FILE|- --lane daemon | --lane console
                                   [--type T] [--kind K] [--due DATE] [--dry-run]
    rbtv-goal reindex
    rbtv-goal lint <goal-name>
    rbtv-goal materialize <goal-name> [--catalog-root DIR] [--force] [--dry-run]
    rbtv-goal lane <goal-name> [--set daemon | --set console]
    rbtv-goal pause <goal-name>            # stash the lane assignment (issue S-33)
    rbtv-goal resume <goal-name>           # …and hand it back, byte for byte
    rbtv-goal relaunch <goal-name> --seat X # authorize ONE more attempt at a seat that failed
    rbtv-goal dag <goal-name>              # the graph + each seat's derived state
    rbtv-goal add-seat <goal-name> --seat X --after a[,b] [--before x[,y]] --bindings SHEET
                                   --catalog-root DIR [--splice-only] [--dry-run]
    rbtv-goal teardown <goal-name> [--yes] [--dry-run]   # ⚠ NEEDS THE DAEMON UP (IPH-27)
    rbtv-goal gate-key-check <goal-name> --pass-folder NAME [--override ANCHOR]
    rbtv-goal check-acyclic <file> [--id-col C] [--after-col C]

⚠ `teardown` IS THE EXCEPTION TO THE LOCAL-ONLY PROPERTY ABOVE, and it cannot be
otherwise: what it reclaims is the job CATALOGUE, which lives in the machine's
`heart.db` and is served only by the gateway (ignite/CLAUDE.md § State layout —
"the jobs catalogue is not readable without the daemon"). It refuses typed
(`daemon-unreachable`) rather than half-working, and it changes no file in the
goals tree — it deletes catalogue rows and leaves the goal FOLDER alone
(owner-ruled 2026-08-12; see the verb's own header for why).

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

# ── The goal's LANE ASSIGNMENT (owner ruling d-daemon-lane-button, 2026-08-10) ────────────────
#
# One word in a small file at the goal root — the `execution-mode` file's precedent exactly —
# saying which lane currently runs this goal. It is THE DAEMON'S PICKUP TRIGGER: the daemon's
# watch pass (`ignite/engine/lane-watch.js`) reads it once a cadence and seeds the goals assigned
# to it, so flipping this file is how a goal starts in one lane and finishes in the other.
#
# ⚠ NAMING. The marker's TERM is **lane assignment**, values `daemon | console` — MINTED
# registry-side 2026-08-10 (system-definition/decisions.md#d-lane-assignment,
# concepts/lane-assignment.md), per PRIN-10; this build coined no noun and the mint is now the
# definition's one home. The filename stays descriptive. `console` (an ASSIGNMENT: who SHOULD run
# the goal) and `attached` (an EXECUTION RECORD row: how it RAN) are ruled the SAME lane's two
# readings — the equivalence lives in that concept file and is never restated here.
#
# ⚠ ABSENT MEANS `console`. The daemon adopts ONLY goals explicitly assigned to it — the reader's
# whole argument is in lane-watch.js's header, and this writer must not disagree with it.
#
# ⚠ THE MARKER IS ONE WORD — `daemon` or `console` (owner ruling `#d-abolish-profile-names`
# sub-ruling 3, 2026-08-12). It used to admit an optional SECOND token naming a fallback launch
# profile, which existed because `launch-agent` structurally required a `profile` argument. That
# requirement is deleted, so the token has nothing to fill and a marker that could name what a seat
# runs on is a marker that could contradict the seat's own cast.
#
# What replaces the old `--profile` demand is the ruling itself: `--set daemon` REFUSES a goal with
# any uncast seat, and NAMES them (`_uncast_seats`, which asks the launch's own reader rather than
# parsing anything here). "Any workflow reaching a taskforce MUST be cast first; an uncast seat is
# a NAMED refusal at materialize/lane time." Refused at the door where the operator is standing
# rather than at 03:00 in a daemon journal.
#
# ⚠ A MARKER STILL CARRYING TWO TOKENS is a LEGACY marker: it does not parse as `daemon`, so both
# readers resolve it to `console` (fail-closed) and `lane-watch.js` shouts the one-line fix once.
# `rbtv-goal lane <goal> --set daemon` rewrites it.
LANE_FILE = "execution-lane"
LANES = ("daemon", "console")

# ── PAUSE: the lane marker's STASH prefix (issue S-33, growing a live goal's roster) ───────────
#
# `pause <goal>` rewrites the marker to `paused ` + WHATEVER IT SAID BEFORE, byte for byte;
# `resume` strips exactly that prefix and writes the remainder back. Nothing else in the system
# learns a new word, and that is the whole design: BOTH lane readers — `read_lane` below and
# `engine/lane-watch.js#readLane` — already resolve any first token that is not `daemon` to
# `console`, so a paused marker reads as "not assigned to the daemon" on both sides with ZERO
# reader change. The daemon lets go on its next pass; the stashed assignment is still on disk.
#
# ⚠ IT BOUNDS SEEDING, NOT EXECUTION. Pausing stops the daemon from SEEDING new seats for this
# goal. It does not stop a session that is already running, and it does not touch an attached
# `rbtv run` (which reads the marker for nothing). "Nothing new starts" is the guarantee; "nothing
# is running" is not, and `add-seat`'s quiescence gate is what checks the second.
LANE_PAUSED = "paused"
# `paused` as the FIRST token, followed by a space or end-of-text. `pausedfoo` is not a pause
# marker, and treating it as one would strip a prefix off a word the operator meant literally.
LANE_PAUSED_RE = re.compile(r"^\s*" + LANE_PAUSED + r"(?: |$)")

# ── The goal's EXECUTION MODE (owner ruling 2026-08-10) ───────────────────────────────────────
#
# The per-goal OWNER-CONTACT policy — registry concept `execution mode`, `sd-graph show "execution
# mode"`. One word in a file at the goal root, read at delivery time by the chat ferry: gate 2 of
# all agent-INITIATED owner contact (the sending seat's `human-interactive` flag being gate 1).
#
# ⚠ ABSENT READS `autonomous`, AND THAT IS THE MODEL'S DEFAULT RATHER THAN A STAND-IN FOR ONE —
# so the default below is not a guess about what the caller meant, it is the same value the
# reader would have reached had this verb written nothing. What changed on 2026-08-10 is that
# NO creation path wrote the file at all, so every created goal was born mode-less and the
# question "was this goal meant to be autonomous?" had no answer on disk. This verb now always
# writes it, and a caller who knows better passes `--execution-mode`.
#
# ⚠ THIS VERB DERIVES NOTHING. The workflow-level default (a workflow's declared
# `default-execution-mode:`, else derived from its manifest's Modality column) is resolved by the
# REQUEST LAYER, which is the layer that knows which workflow a goal is being created for
# (`goal_creation_request.py#resolve_execution_mode`) and passes the resolved word here. A goal
# scaffolded by hand names no workflow, so there is nothing here to derive from.
EXECUTION_MODE_FILE = "execution-mode"
EXECUTION_MODES = ("interactive", "autonomous")
EXECUTION_MODE_DEFAULT = "autonomous"

# goals-index schema (concept goals-index § file schema)
#
# ⚠ DIVERGENCE TO TRANSCRIBE, NOT A DRIFT: the registry's `concepts/goals-index.md` file-schema
# block enumerates five columns and is marked `design-intent` — it was written before `goal-kind`
# existed. Its DEFINITION ("a FULL deterministic projection of each goal's goal.md frontmatter")
# is what governs here: a frontmatter field the projection omits would make the index partial.
# The column list needs a registry-side update; the registry is never edited from this build.
GOALS_INDEX_COLUMNS = ["name", "creation date", "due date", "type", "goal-kind", "status"]
# threads-store schema (concept threads-store § file schema)
THREADS_SCHEMA = """\
-- threads.sql — the goal-scoped message/completion store (concept: threads-store).
-- One row per message sent or received under this goal. Created empty at scaffold.
CREATE TABLE IF NOT EXISTS threads (
    message_id  TEXT PRIMARY KEY,
    reply_to    TEXT,            -- answer rows only: the message-id answered
    session_id  TEXT,            -- tracing column; resolves the session via sessions.csv
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

# ------------------------------------- standard goal-folder artifacts (7.582 / R21)
#
# Owner ruling R21 (2026-08-08, `build/meta-workflow/interview-findings.md`; meta-planner-v4
# §9 and §11.12): goal creation writes the standard goal-folder artifacts from DETERMINISTIC
# TEMPLATES — no agent in the path — and writes the router for EVERY supported harness, so an
# agent landing on any harness is routed.
#
# ⚠ TEMPLATES ARE CODE HERE, NOT DATA FILES. `THREADS_SCHEMA` above already sets that precedent
# in this file: fixed text one verb emits. A template FILE would add a path to resolve, a
# shipping surface, and a second place the router's table could disagree with the file set.
#
# ROUTER_FILENAMES IS MEASURED, NOT ASSUMED. It is the distinct set of `guidance_file.convention`
# values across every model package manifest (`orchestration/models/*/manifest.yaml`, the
# enumerator for "which harnesses this system serves"):
#     CLAUDE.md  — claude-code-cli
#     AGENTS.md  — codex-cli, kimi-code-cli, opencode
# The three API packages (deepseek/gemini/manus) and claude-code-native OMIT `guidance_file`
# DELIBERATELY — those workers load no workspace guidance file at all, so no router of any name
# would reach them. TWO is therefore the whole measured set as of 2026-08-09; a package that
# adopts a third convention adds its filename to this tuple and nothing else changes.
ROUTER_FILENAMES = ("CLAUDE.md", "AGENTS.md")

# The FIVE write-if-something files, filename -> what an agent has when it writes there. R21 named
# four; owner ruling Q16 (2026-08-09, `build/subagent-closeout/decisions.md#d-owner-batch-q12-q19-0809`
# item 5) added `ideas.md`, so a created goal matches the live goal's three-ledger shape
# (issues/decisions/ideas).
# The router's table below is RENDERED FROM THIS MAPPING, so the routing an agent reads and the
# files that exist can never drift apart — a router naming a file nobody wrote (or missing one
# that was) is the one way a router fails without anything noticing.
WRITE_IF_SOMETHING = {
    "issues.md": "a defect, blocker, or open problem in the work",
    "decisions.md": "a settled decision, and the reason it was settled that way",
    "doubts.md": "a question only the owner can answer",
    "gotchas.md": "a validated pattern or trap worth carrying forward",
    "ideas.md": "an improvement worth framing that nobody has ruled on",
}

# Where a TOOLING-GAP finding goes — owner ruling 2026-08-10 (issue `i-wrote-outside-own-seat-first`,
# `_channel-master/issues.md`): the goal OWNING the tooling first, this goal's own `issues.md` as
# the fallback when that one is unreachable — the observed failure was a read-only mount plus a dead
# coordination log. The ruling's second half is that the destination is MATERIALIZED into the docs a
# seat reads, never left to memory, so it lands in both carriages: the router below (inherited by
# every seat under this goal — `cage.js` masks path-up instruction files EXCEPT inside `.rbtv/goals`)
# and the per-seat `AGENTS.md`, which `team-kit/materialize-seats.py` renders from THIS constant
# rather than restating it. `{issues}` is the caller's concrete fallback path.
TOOLING_FINDING_BLOCK = """\
## A tooling gap goes in an issues ledger, never in chat

Hit a defect, gap, or trap in a TOOL while working? File it in the `issues.md` of the goal that
OWNS that tooling — that is where whoever fixes it looks. Unreachable, or it refuses your write?
Fall back to {issues}, name the destination it was meant for, and route it on as a follow-up.
A finding left in chat dies with the sitting.
"""

# The write-if-something sentence EXEMPTS `decisions.md`: owner ruling Q22 (2026-08-09,
# `build/subagent-closeout/decisions.md#d-owner-batch4-partial-0809`) — Q19 gave that file an
# append-only body (DECISIONS_TEMPLATE below), so a blanket "these are NOT logs" contradicted it.
# ⚠ THE CLAUSE SITS INSIDE THE NOT-LOGS HALF ON PURPOSE. Trailing it after both halves scopes the
# exception over "reporting obligation" too, which says decisions.md IS one — contradicting that
# file's OWN scaffolded body ("Nothing obliges an entry"). Q22 exempted the log claim, nothing else.
GOAL_ROUTER_TEMPLATE = """\
# {name}/ — goal folder

Router for any agent working under this goal folder. It carries NO content of its own: it says
where things are and where to write. What this goal IS lives in `goal.md`.

| File | What it holds |
|------|---------------|
| `goal.md` | the goal-descriptor — identity frontmatter plus the goal-radius done contract |
| `taskforce.csv` | the taskforce descriptor — one row per seat of this goal |
| `seats/<seat>/` | a seat folder — that seat's workspace, and it is GOAL-DURABLE: the same seat boots from the same folder every time this goal executes |
| `coordination/` | the coordination bus — the message log every seat reads and writes |
| `threads.sql` | the goal-scoped message/completion store schema |

## Write-if-something files

These are NOT logs — except `decisions.md`, which IS an append-only record — and none of them is
a reporting obligation. Write to one ONLY when you have something to note; an agent with nothing
to note writes nothing.

{table}

{finding}
Scaffolded at goal creation from a deterministic template (owner ruling R21) — no agent was in
the path that produced this file.
"""

# Only the NON-`CLAUDE.md` routers carry this. The vault convention is that `CLAUDE.md` is the
# source and every equivalent is its mirror, so a mirror must say so in its own first line — a
# reader who edits the mirror instead of the source loses the edit.
ROUTER_MIRROR_HEADER = """\
<!-- AUTO-GENERATED MIRROR — DO NOT EDIT. `CLAUDE.md` in this folder is the source of truth. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This `{filename}` mirrors this folder's `CLAUDE.md`, emitted for the harnesses that natively
> load `{filename}` rather than `CLAUDE.md`. To change these instructions, edit `CLAUDE.md` in
> this folder — hand-edits here are not the source of truth.

---

"""

WRITE_IF_SOMETHING_TEMPLATE = """\
# {file} — {name}

Write here when you have {what}.

Write-if-something, NOT a log: nothing obliges an entry, and an agent with nothing to note
writes nothing. Append at the moment you have it — one entry, dated, stating the thing and why
it matters. The goal folder's routing is in `CLAUDE.md`.
"""

# `decisions.md` gets its OWN body instead of the shared one: owner ruling Q19 (2026-08-09,
# `d-owner-batch-q12-q19-0809` item 8) made the DURABILITY SPLIT a general rbtv convention that a
# created goal must carry from birth, and pinned the entry shape to `decisions-discipline.md` BY
# CITATION. The entry rules are NOT restated here — a second copy of them is a second thing to
# drift (the same reason the router's table is rendered from one mapping).
DECISIONS_TEMPLATE = """\
# decisions.md — {name}

Write here when you have a settled decision, and the reason it was settled that way. Nothing
obliges an entry.

## Anchor classes — and NOTHING here is mortal

THIS file is the goal's ONE decision record, and every entry in it is DURABLE. Three anchor
classes still say what KIND of ruling an entry is — `r-*` a standing rule, `d-*` a settled
design decision, `p-*` a PROVISIONAL ruling about this goal's processes, tools, or conduct —
but the class no longer sets a lifetime. There is no run to die with: the goal folder IS the
workspace, and it persists across every execution of this goal.

`p-*` anchors are therefore DURABLE and are PRUNED BY HAND (owner ruling,
`decisions.md#d-extinguishment-design-lock` item 6: no automatic mortality boundary; ledger
hygiene is human housekeeping). Nothing sweeps them, and no sweep may be invented — an entry
that has stopped being true is deleted by a person who read it. A `p-*` that proved goal-durable
is PROMOTED by re-anchoring it `d-*` or `r-*` in place.

Entries are frozen history — never moved, reclassified, or rewritten, except the two acts named
above (hand-pruning a spent `p-*`, promoting one).

## Entry shape — adopted BY CITATION

Every entry in this file follows
`orchestration/workflows/_shared/authoring/decisions-discipline.md` in the rbtv repo (its path is
`rbtv_path` in the workspace's `rbtv.json`). That file is the ONE source of the entry rules; this
one restates none of them — read it before your first entry.

The goal folder's routing is in `CLAUDE.md`.
"""


def _write_if_something_table() -> str:
    return "\n".join(
        ["| File | Write here when you have… |",
         "|------|---------------------------|"]
        + [f"| `{f}` | {what} |" for f, what in WRITE_IF_SOMETHING.items()]
    )


def standard_artifacts(name: str) -> dict:
    """{filename: content} — every standard goal-folder file R21 rules, for goal `name`.

    ONE mapping so a caller can never write a partial set it does not know is partial: the
    routers are the same body (mirrors carry a header saying so), and the write-if-something
    files come off the same dict the router's table is rendered from.
    """
    body = GOAL_ROUTER_TEMPLATE.format(
        name=name, table=_write_if_something_table(),
        finding=TOOLING_FINDING_BLOCK.format(issues="`issues.md` in this folder"))
    files = {fn: (body if fn == "CLAUDE.md"
                  else ROUTER_MIRROR_HEADER.format(filename=fn) + body)
             for fn in ROUTER_FILENAMES}
    for fn, what in WRITE_IF_SOMETHING.items():
        files[fn] = (DECISIONS_TEMPLATE.format(name=name) if fn == "decisions.md"
                     else WRITE_IF_SOMETHING_TEMPLATE.format(file=fn, name=name, what=what))
    return files


def write_standard_artifacts(goal_dir: Path, name: str) -> list:
    """Write every standard artifact NOT already on disk. Returns the filenames written.

    SKIP-IF-EXISTS, PER FILE, and the property lives HERE rather than in the caller. `cmd_scaffold`
    refuses an existing goal folder outright, so today this never meets a file — but these are the
    files agents WRITE INTO, so an overwrite is data loss, and a guard that a future caller has to
    remember is a guard that eventually is not there. Re-running this over a goal whose
    `issues.md` carries fifty issues writes nothing.
    """
    written = []
    for fn, text in standard_artifacts(name).items():
        path = goal_dir / fn
        if path.exists():
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(fn)
    return written


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
    """Exit 1 — a refusal, gate-fail, or not-found. Never a crash.

    `code` is OPTIONAL and additive: every pre-existing raise passes a message alone and
    keeps working. A coded refusal is one a CALLER (a selftest arm, a probe, an agent
    reading `--json`) must be able to key on WITHOUT matching prose — message text is
    edited freely, a code is a contract. `materialize-seats.py`'s own `Refuse` carries the
    same field for the same reason; this is that discipline reaching the verbs added by the
    live-roster-growth arm, not a second refusal vocabulary.
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


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
    # A cwd already INSIDE a goals tree resolves to THAT tree, and this scan runs
    # BEFORE the child scan below. Order is load-bearing: a stray `.rbtv/goals`
    # nested under a seat folder (mkdir'd by a cwd-relative inbox path, measured
    # 2026-08-12 — the seat's next scaffold landed a real goal inside it) would
    # otherwise win the child scan from every seat cwd.
    for cand in (here, *here.parents):
        if cand.name == "goals" and cand.parent.name == ".rbtv":
            return cand
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

    # Same `getattr` reason as `kind` above: hand-built Namespaces reach this function from the
    # selftest and from the request handler, and argparse's `choices` does not run on those.
    mode = getattr(args, "execution_mode", None) or EXECUTION_MODE_DEFAULT
    if mode not in EXECUTION_MODES:
        raise Refusal(f"--execution-mode {mode}: must be one of {', '.join(EXECUTION_MODES)}")

    # ── 7.777: A GOAL DECLARES ITS LANE AT BIRTH ─────────────────────────────────────────────
    # Same `getattr` reason as `kind` and `execution_mode` above — hand-built Namespaces reach
    # this function and argparse's validation never runs on them, so the check lives here and the
    # subparser declares neither `required=` nor `choices=` (argparse's error text cannot carry
    # the wording below).
    #
    # ⚠ REFUSED BEFORE THE FIRST WRITE, AND THAT PLACEMENT IS THE WHOLE POINT. The first
    # filesystem mutation in this function is `goal_dir.mkdir(parents=True)` some sixty lines
    # down; nothing here rolls back, and `goal_creation_request.py` rules that a failure past the
    # scaffold seam leaves the goal standing ("no unwind is built, and none may be added"). A gate
    # placed any later trades a refusal for a half-built goal that then refuses re-creation as
    # already existing.
    lane = getattr(args, "lane", None)
    if lane not in LANES:
        raise Refusal(
            "this goal needs a lane: pass `--lane daemon` if the daemon runs it unattended, or "
            "`--lane console` if you run it when you type `rbtv run`. Nothing was created — the "
            "lane is declared at birth precisely so a goal is never silently one of them."
            + (f" (got {lane!r})" if lane else ""),
            "lane-absent")
    # NAME-only. Whether any seat still NEEDS this fallback is unanswerable here: no seat exists
    # yet (`materialize-seats` runs later, as its own act), so `uncastSeats` on a fresh goal can
    # only say "unknown". Cast coverage keeps its one home — `lane-watch.js` skips an uncast goal
    # at seeding time with a named warning.

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

    # The FULL set, named in one place so the dry-run plan, the writes and the report can never
    # be three different answers to "what does creating a goal produce". `decisions.md` is no
    # longer written here: it is one of the five write-if-something files and comes off
    # `standard_artifacts` with the other four (its old body called itself a "decision log",
    # which is the exact word §9 rules these files are NOT).
    created_names = ["goal.md", "threads.sql", EXECUTION_MODE_FILE, LANE_FILE, "milestones.csv",
                     "planning/", *standard_artifacts(name)]
    plan = {
        "goal": name,
        "root": str(root),
        "creates": [str(goal_dir / f) for f in created_names],
        "then": f"reindex {root / 'goals.csv'}",
    }
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, **plan}, indent=2)
              if args.json else
              f"dry-run: would create {goal_dir}/ "
              f"({', '.join(created_names)}) then reindex")
        return 0

    goal_dir.mkdir(parents=True)
    (goal_dir / "goal.md").write_text(goal_md, encoding="utf-8", newline="\n")
    (goal_dir / "threads.sql").write_text(THREADS_SCHEMA, encoding="utf-8", newline="\n")
    # ONE WORD PLUS A NEWLINE, and no more: the ferry's reader trims and compares the whole
    # file, so a comment or a header line here would read as "not interactive" and silently
    # make every goal autonomous.
    (goal_dir / EXECUTION_MODE_FILE).write_text(mode + "\n", encoding="utf-8", newline="\n")
    # The lane marker, through the SAME composer and the SAME writer `lane --set` uses — one
    # grammar, one tmp+rename, so a goal born daemon and a goal moved to daemon are byte-identical.
    write_lane_raw(goal_dir, lane_text(lane))
    # 7.136 / d-0811lp-milestones-flow-writes: `lint` requires milestones.csv on EVERY goal, and
    # until now its only writer was the selftest — so every goal born through the creation flow
    # failed its own lint gate. Header-only: a goal is born with no milestones, and the spine is
    # filled in by planning. Same columns the lint reader and the selftest fixture expect.
    write_csv(goal_dir / "milestones.csv", ["milestone-id", "name", "status"], [])
    # R21 (+ Q16): the per-harness routers + the five write-if-something files, from deterministic
    # templates. Written LAST so the routers describe a folder that already holds what they name.
    write_standard_artifacts(goal_dir, name)
    # d-s31-planning-workspace-shared-rw: the per-milestone planning workspace, the one surface a
    # multi-seat planning phase hands artifacts across. Born empty with the goal because the seat
    # cage's `bind-try:{goalDir}/planning` needs an existing mountpoint — the goal root is
    # read-only inside the cage, so no seat can create it.
    (goal_dir / "planning").mkdir()

    write_csv(root / "goals.csv", GOALS_INDEX_COLUMNS, project_goals(root))

    if args.json:
        print(json.dumps({"ok": True, **plan}, indent=2))
    else:
        print(f"scaffolded {goal_dir} — {', '.join(created_names)}")
        print(f"reindexed {root / 'goals.csv'}")
    return 0


# ---------------------------------------------------------------- lane


def read_lane(goal_dir: Path) -> tuple[str, bool]:
    """(lane, legacy) — the SAME grammar `engine/lane-watch.js#readLane` reads with.

    ⚠ ONE WORD, WHOLE (`#d-abolish-profile-names` sub-ruling 3, 2026-08-12). The whole trimmed text
    must BE the lane word. Trimmed, case-insensitive, and everything else is `console`: a missing
    file, an unreadable one and a junk word are ONE answer.

    `legacy` is True for a marker whose FIRST token is `daemon` but which carries more — the retired
    `daemon <profile-name>` grammar. It resolves `console` like any other unparseable marker
    (fail-closed), and is reported separately so a caller can say WHY a goal that was handed to the
    daemon is not being picked up, instead of showing it as one somebody parked deliberately.

    Two languages read this file (this CLI writes and shows it; the daemon's watch pass acts on it)
    and the grammar is four lines, so it is stated twice and cross-checked by
    probe-daemon-lane-watch.js rather than bridged. THE TWO CHANGE TOGETHER, ALWAYS (DEC-1).
    """
    try:
        raw = (goal_dir / LANE_FILE).read_text(encoding="utf-8")
    except OSError:
        return "console", False
    text = raw.strip()
    if text.lower() == "daemon":
        return "daemon", False
    return "console", text.split()[:1] == ["daemon"] if text else False


def read_lane_raw(goal_dir: Path) -> str:
    """The marker's RAW TEXT — the byte-preserving read `pause`/`resume` round-trip through.

    `read_lane` above answers "which lane", which is a four-line normalisation that throws the
    bytes away. Pause has to put them back exactly, so it reads them here instead. An absent or
    unreadable file is `console\\n` — the SAME answer `read_lane` gives it, spelled as the text a
    resume would restore (owner ruling: previous text = `console` when the file is absent).
    """
    try:
        return (goal_dir / LANE_FILE).read_text(encoding="utf-8")
    except OSError:
        return "console\n"


def lane_is_paused(raw: str) -> bool:
    return bool(LANE_PAUSED_RE.match(raw))


def lane_text(target: str) -> str:
    """THE ONE composer of the marker's grammar — `lane --set` and `scaffold --lane` both write
    through it, because a second speller of the marker is drift `readLane` would misparse in
    silence. ONE WORD since `#d-abolish-profile-names`: there is nothing else a marker may say."""
    return "daemon\n" if target == "daemon" else "console\n"


def write_lane_raw(goal_dir: Path, text: str) -> None:
    """tmp + replace, `cmd_lane`'s own discipline: a truncate-then-write leaves a window where
    the marker reads EMPTY, which the daemon's reader resolves as `console` — silently dropping
    a goal mid-assignment. One writer, one construct."""
    tmp = goal_dir / f"{LANE_FILE}.tmp"
    tmp.write_text(text, encoding="utf-8", newline="")
    tmp.replace(goal_dir / LANE_FILE)


def _lane_goal_dir(args) -> tuple[Path, Path, str]:
    """(root, goal_dir, name) for the three marker verbs — `cmd_lane`'s own gate, once."""
    root = resolve_goals_root(args.root)
    name = args.goal_name
    if not GOAL_NAME_RE.match(name):
        raise Refusal(
            f"goal name '{name}' violates the naming rule — lowercase kebab-case "
            "([a-z0-9] words joined by single hyphens)", "goal-name-invalid")
    goal_dir = root / name
    if not goal_dir.is_dir():
        raise Refusal(f"{goal_dir}: no such goal", "goal-absent")
    return root, goal_dir, name


def cmd_pause(args) -> int:
    """Stash the lane assignment behind `paused ` — nothing new is seeded until `resume`."""
    _root, goal_dir, name = _lane_goal_dir(args)
    raw = read_lane_raw(goal_dir)
    already = lane_is_paused(raw)
    if not already:
        # `paused ` + the previous text VERBATIM. Not re-rendered, not normalised: `resume` is
        # required to hand back the exact bytes, and the only way to promise that is to keep them.
        write_lane_raw(goal_dir, f"{LANE_PAUSED} {raw}")
    stashed = LANE_PAUSED_RE.sub("", read_lane_raw(goal_dir), count=1)
    if getattr(args, "json", False):
        print(json.dumps({"ok": True, "goal": name, "paused": True,
                          "already_paused": already, "paused_from": stashed.strip(),
                          "file": str(goal_dir / LANE_FILE)}, indent=2))
    else:
        print(f"{name}: PAUSED"
              + (" (already)" if already else "")
              + f" — stashed lane assignment: {stashed.strip()!r}. "
                "Nothing new is SEEDED for this goal until `rbtv-goal resume`; a session already "
                "running is untouched.")
    return 0


def cmd_resume(args) -> int:
    """Unstash: strip the `paused ` prefix and write the remainder back byte for byte."""
    _root, goal_dir, name = _lane_goal_dir(args)
    raw = read_lane_raw(goal_dir)
    if not lane_is_paused(raw):
        raise Refusal(
            f"{goal_dir / LANE_FILE}: the lane marker does not start with `{LANE_PAUSED}` "
            f"(it reads {raw.strip()!r}) — `resume` unstashes a PAUSE, and stripping a prefix "
            "that is not there would rewrite an assignment nobody paused. Use `lane --set` to "
            "assign a lane.", "not-paused")
    write_lane_raw(goal_dir, LANE_PAUSED_RE.sub("", raw, count=1))
    lane, legacy = read_lane(goal_dir)
    if getattr(args, "json", False):
        print(json.dumps({"ok": True, "goal": name, "paused": False,
                          "lane": lane, "legacy_marker": legacy,
                          "file": str(goal_dir / LANE_FILE)}, indent=2))
    else:
        print(f"{name}: RESUMED — lane assignment restored to {lane.upper()}"
              + (" ⚠ (the restored marker uses the RETIRED two-token grammar and therefore reads "
                 "CONSOLE — re-run `lane --set daemon` to repair it)" if legacy else "")
              + f" ({goal_dir / LANE_FILE})")
    return 0


# ---------------------------------------------------------------- relaunch
#
# THE OPERATOR'S ACT THAT AUTHORIZES ONE MORE ATTEMPT (task 7.776). A seat that ended `failed` or
# exited is not retried on its own — the grant is what buys it one more run, and it is spent by
# the pass that acts on it, so a second failure needs a second grant.
#
# ⚠ ONE BARE SEAT NAME PER LINE, no header and no csv. The reader on the other side (the seeding
# pass) parses exactly that; columns would be a schema two languages have to agree on, for a file
# whose whole content is a list of names.


RELAUNCH_GRANTS_FILE = "relaunch-grants"


def read_relaunch_grants(goal_dir: Path) -> list[str]:
    """The seats holding an UNSPENT grant. Absent file = none — the same shape `read_lane`
    gives its own missing marker."""
    try:
        raw = (goal_dir / RELAUNCH_GRANTS_FILE).read_text(encoding="utf-8")
    except OSError:
        return []
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]


def cmd_relaunch(args) -> int:
    """Grant ONE more attempt at a seat of this goal."""
    _root, goal_dir, name = _lane_goal_dir(args)
    seat = args.seat.strip()

    # The seat must be one this goal HAS. A typo that lands in the file is a grant nothing will
    # ever spend, and the operator's only signal would be the seat never running.
    tf_path = goal_dir / "taskforce.csv"
    if not tf_path.is_file():
        raise Refusal(
            f"{tf_path}: this goal has no taskforce yet, so it has no seat to relaunch — staff it "
            f"first (`rbtv-goal materialize {name}`).", "taskforce-absent")
    seats = [s for s in ((r.get("seat") or "").strip() for r in read_csv(tf_path)) if s]
    if seat not in seats:
        raise Refusal(
            f"--seat {seat}: this goal has no such seat. Its seats are: "
            f"{', '.join(seats) or '(none)'}.", "seat-absent")

    granted = read_relaunch_grants(goal_dir)
    if seat in granted:
        raise Refusal(
            f"--seat {seat}: an unspent relaunch grant for this seat is already standing in "
            f"{goal_dir / RELAUNCH_GRANTS_FILE}. One grant buys one attempt; it is spent when the "
            "seat runs, and only then does a second one mean anything.", "grant-duplicate")

    # tmp + rename for `write_lane_raw`'s reason, on a file read by the same kind of unlocked
    # reader: a truncate-then-write leaves a window where this file reads EMPTY, and empty here
    # means "no grant" — the seat would be skipped and the operator's act silently lost.
    tmp = goal_dir / f"{RELAUNCH_GRANTS_FILE}.tmp"
    tmp.write_text("".join(f"{s}\n" for s in [*granted, seat]), encoding="utf-8", newline="\n")
    tmp.replace(goal_dir / RELAUNCH_GRANTS_FILE)

    lane, _profile = read_lane(goal_dir)
    happens = ("the daemon will run this seat again on its next pass" if lane == "daemon"
               else f"the next `rbtv run {goal_dir}` will run this seat again")
    if getattr(args, "json", False):
        print(json.dumps({"ok": True, "goal": name, "seat": seat, "lane": lane,
                          "granted": [*granted, seat],
                          "file": str(goal_dir / RELAUNCH_GRANTS_FILE)}, indent=2))
    else:
        print(f"{name}/{seat}: relaunch GRANTED — {happens}. The grant is spent by that run; a "
              f"further attempt needs a further grant ({goal_dir / RELAUNCH_GRANTS_FILE})")
    return 0


# ---------------------------------------------------------------- retry threshold
#
# THE MILESTONE RETRY THRESHOLD (IPH-11, owner ruling 2026-08-11 — `build/decisions.md` D32/D34).
#
# The bar the dod-judge's escalation fires at. `coord.py#resolve_retry_threshold` is the
# AUTHORITY: it is the code the gate calls, and everything below writes the two files that
# resolver reads. The ladder is stated here a second time, deliberately and with the same three
# rungs — a per-milestone cell, a per-goal file, then 2 — because this CLI must run with no
# `--package` and coord.py is not importable from an arbitrary cwd (its own module body imports
# siblings; `_module_level_literals` above exists for exactly that reason). The selftest CROSS-
# CHECKS the three literals against coord.py's own source rather than bridging them, the same
# treatment `ATTACHED_RUN_LOCK` and `read_lane`'s grammar already get.
#
# ⚠ THE GOAL FOLDER IS THE HOME, because `coord.py` reads `base.parent` and `base_dir` builds
# base as `<goal>/coordination`. A goal whose coordination folder sits under `runs/<run>/`
# instead (the older layout — `build-core-daemon-mvp`) resolves against THAT folder, so `show`
# prints the path it answered from rather than asserting one.
RETRY_THRESHOLD_FILE = "retry-threshold"
RETRY_THRESHOLD_COLUMN = "retry-threshold"
RETRY_THRESHOLD_DEFAULT = 2
MILESTONES_FILE = "milestones.csv"
MILESTONE_ID_COLUMN = "milestone-id"


def _csv_field_spans(line: str) -> list[tuple[int, int]]:
    """(start, end) of every field in ONE csv line, quotes respected.

    The offsets a LINE-PRECISE edit splices into. This is not a parse and produces no values:
    everything between the spans — delimiters, quoting, spacing — goes back to the file
    untouched. `milestones.csv` carries quoted multi-clause `done-when` prose, and a csv
    round trip re-renders every cell in the file to satisfy one of them (the reason
    `goal-launch-delay` edits its own hand-authored config line-precisely too).
    """
    spans, start, i, n, inq = [], 0, 0, len(line), False
    while i < n:
        ch = line[i]
        if inq:
            if ch == '"':
                if i + 1 < n and line[i + 1] == '"':
                    i += 1          # an escaped quote INSIDE a quoted field
                else:
                    inq = False
        elif ch == '"':
            inq = True
        elif ch == ",":
            spans.append((start, i))
            start = i + 1
        i += 1
    spans.append((start, n))
    return spans


def _split_eol(line: str) -> tuple[str, str]:
    """(text, line-ending) — CRLF preserved. The live goal files on the Windows vault are
    CRLF-terminated and an edit that normalises them rewrites every line it did not touch."""
    for eol in ("\r\n", "\n", "\r"):
        if line.endswith(eol):
            return line[:-len(eol)], eol
    return line, ""


def _milestone_cells(path: Path) -> tuple[list[str], int | None, dict[str, int]]:
    """(raw lines with endings, retry-threshold column index or None, {milestone-id: line no}).

    Read for a WRITE, so it reads the bytes rather than a DictReader's values.
    """
    lines = path.read_text(encoding="utf-8", newline="").splitlines(keepends=True)
    if not lines:
        raise Refusal(f"{path}: empty — no header to write a column into", "milestones-empty")
    head, _ = _split_eol(lines[0])
    cols = [head[a:b].strip().strip('"') for a, b in _csv_field_spans(head)]
    col = cols.index(RETRY_THRESHOLD_COLUMN) if RETRY_THRESHOLD_COLUMN in cols else None
    idc = cols.index(MILESTONE_ID_COLUMN) if MILESTONE_ID_COLUMN in cols else 0
    rows: dict[str, int] = {}
    for n, raw in enumerate(lines[1:], start=1):
        text, _ = _split_eol(raw)
        if not text.strip():
            continue
        spans = _csv_field_spans(text)
        if idc < len(spans):
            a, b = spans[idc]
            rows.setdefault(text[a:b].strip().strip('"'), n)
    return lines, col, rows


def read_retry_threshold(goal_dir: Path, milestone: str | None) -> tuple[int, str, Path | None]:
    """(threshold, source, path) — the same three rungs `coord.py` enforces, in the same order.

    A value that is not an integer >= 1 is IGNORED and the next rung answers. `show` is a
    READ: it never repairs and never refuses a bad file, because the reader that matters
    (the escalation gate) does not either — it warns and falls back, so the safety fails
    CLOSED. `--set` is where a bad value is refused, loudly.
    """
    if milestone:
        ms = goal_dir / MILESTONES_FILE
        if ms.is_file():
            with ms.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    if (row.get(MILESTONE_ID_COLUMN) or "").strip() != milestone:
                        continue
                    cell = (row.get(RETRY_THRESHOLD_COLUMN) or "").strip()
                    if cell.isdigit() and int(cell) >= 1:
                        return int(cell), "milestone", ms
                    break
    marker = goal_dir / RETRY_THRESHOLD_FILE
    try:
        raw = marker.read_text(encoding="utf-8").strip()
    except OSError:
        raw = ""
    if raw.isdigit() and int(raw) >= 1:
        return int(raw), "goal", marker
    return RETRY_THRESHOLD_DEFAULT, "default", None


def _retry_write_gate(goal_dir: Path, goal_name: str) -> None:
    """Owner ruling 11: a `--set` REFUSES while a planning pass is open.

    `check-unblocked`'s done contract asserts `milestones.csv` is byte-identical before and
    after its own pass, so a write landing mid-pass fails a criterion the writer never sees.
    The signal is the one `add-seat`'s gate (b) already uses — an execution row with an empty
    outcome — rather than a second notion of "open".
    """
    open_rows = [r for r in read_executions(goal_dir) if not (r.get("outcome") or "").strip()]
    if open_rows:
        raise Refusal(
            f"{goal_dir / EXECUTIONS_FILE}: "
            + ", ".join(sorted({(r.get('seat') or '?').strip() for r in open_rows}))
            + " still carry an OPEN execution row (empty outcome), so a planning pass is "
              "running. Its done contract asserts milestones.csv is byte-identical across the "
              f"pass — a write now fails a criterion the seat cannot see. Wait for the record "
              f"to close, then set the threshold (`rbtv-goal dag {goal_name}` shows who is "
              "still open).", "pass-open")


def cmd_retry_threshold(args) -> int:
    """Show or set the milestone retry threshold — the bar the escalation fires at."""
    _root, goal_dir, name = _lane_goal_dir(args)
    milestone = getattr(args, "milestone", None)
    target = getattr(args, "set", None)
    unset = getattr(args, "unset", False)
    if target is not None and unset:
        raise Refusal("--set and --unset say opposite things — pass one", "set-and-unset")

    if target is not None or unset:
        value = ""
        if target is not None:
            try:
                n = int(target.strip())
            except (ValueError, AttributeError):
                n = None
            if n is None or n < 1:
                raise Refusal(
                    f"--set {target!r}: the threshold is an integer >= 1. The FLOOR IS 1, not 0: "
                    "the gate reads `count < bar`, so a bar of 0 is never true and the goal "
                    "would escalate on ZERO FAILs — the safety switched off by a value that "
                    "looks like it tightened it.", "retry-threshold-invalid")
            value = str(n)
        _retry_write_gate(goal_dir, name)
        if milestone:
            ms = goal_dir / MILESTONES_FILE
            if not ms.is_file():
                raise Refusal(f"{ms}: absent — no milestone rows to carry an override",
                              "milestones-absent")
            lines, col, rows = _milestone_cells(ms)
            if milestone not in rows:
                raise Refusal(
                    f"--milestone {milestone}: no row in {ms}. Known: "
                    + (", ".join(sorted(rows)) or "(none)"), "milestone-unknown")
            if col is None:
                # The column is APPENDED to every line — the one structural edit that adds
                # bytes and rewrites none. Every existing cell, quote and line ending survives.
                out = []
                for i, raw in enumerate(lines):
                    text, eol = _split_eol(raw)
                    if not text.strip() and i:
                        out.append(raw)
                        continue
                    add = RETRY_THRESHOLD_COLUMN if i == 0 else (value if i == rows[milestone]
                                                                 else "")
                    out.append(f"{text},{add}{eol}")
                ms.write_text("".join(out), encoding="utf-8", newline="")
            else:
                text, eol = _split_eol(lines[rows[milestone]])
                spans = _csv_field_spans(text)
                if col >= len(spans):          # a short row: pad to the column, add nothing else
                    text = text + "," * (col - len(spans) + 1)
                    spans = _csv_field_spans(text)
                a, b = spans[col]
                lines[rows[milestone]] = f"{text[:a]}{value}{text[b:]}{eol}"
                ms.write_text("".join(lines), encoding="utf-8", newline="")
        else:
            marker = goal_dir / RETRY_THRESHOLD_FILE
            if unset:
                marker.unlink(missing_ok=True)
            else:
                # tmp + replace, `write_lane_raw`'s discipline: a truncate-then-write leaves a
                # window where the file reads EMPTY, and coord.py resolves empty as ABSENT —
                # silently dropping the goal back to 2 mid-write.
                tmp = goal_dir / f"{RETRY_THRESHOLD_FILE}.tmp"
                tmp.write_text(f"{value}\n", encoding="utf-8", newline="\n")
                tmp.replace(marker)

    threshold, source, path = read_retry_threshold(goal_dir, milestone)
    payload = {"goal": name, "milestone": milestone, "threshold": threshold,
               "source": source, "path": str(path) if path else None}
    if getattr(args, "json", False):
        print(json.dumps({"ok": True, **payload}, indent=2))
    else:
        where = {"milestone": f"the milestone's own cell in {path}",
                 "goal": f"the goal default at {path}",
                 "default": "the built-in default (nothing configured)"}[source]
        scope = f"{name}/{milestone}" if milestone else name
        print(f"{scope}: retry threshold {threshold} — from {where}")
        print(f"  the dod-judge escalates to the owner on FAIL #{threshold}; "
              f"a PASS resets the count by construction")
    return 0


# ⚠ `_spawn_profile_names()` IS DELETED (`#d-abolish-profile-names`, 2026-08-12). It took the KEYS
# of `profiles:` so `--profile NAME` could be validated against them. Both the flag and the flat
# name-keyed section are gone; the castable set now has ONE derivation — `launch-specs:`' keys, read
# by `capabilities/bindings/tool/bindings.py#catalog` and by `launch-profiles/catalog.js#catalogOf`
# — and this file asks neither, because it no longer has a name to check. DEC-1's no-second-reader
# rule is satisfied by having no reader here at all.


class _CastUnknown(RuntimeError):
    """The goal's seats could not be inspected, so "is every seat cast" is
    UNKNOWN — which is never the same answer as `no`. Its own type because the door refuses
    differently for it than for a measured `some`."""


# ── WHICH SEATS ARE NOT CAST — ASKED, NEVER RE-DERIVED ────────────────────────────────────────
#
# ⚠ THE ANSWER IS NOT COMPUTED HERE, AND NOT COMPUTED IN PYTHON AT ALL. `engine/seeding.js`
# exports `uncastSeats`, which reads what the LAUNCH reads through the launch's own reader
# (`spawn.js#seatDeclaresValue` over `seats/<seat>/seat.md`) and answers with the catalog's own
# predicate (`launch-profiles/catalog.js#declaresBinding`). One home, two callers: the daemon's
# watch pass asks the same function, so what this door accepts and what that pass seeds cannot
# disagree. A python re-implementation would be a second reader of the same fact — the drift
# DEC-1 § Shared launch-spec source forbids, and the precedent is `probe-bindings.py`'s "one `node`
# call covers the whole matrix — never a python re-implementation".
#
# ⚠ AND IT IS `seat.md`, NOT `taskforce.csv`, THOUGH BOTH CARRY harness/model/effort. The launch
# reads the descriptor; `lint`'s own "binding matches taskforce.csv" finding exists because the
# two CAN disagree, and a gate reading the other surface could refuse a launch that would work.
# Reading the csv here would also have to be quote-aware — a multi-predecessor `after` cell is
# written QUOTED, and a naive split shifts every column to its right onto the wrong field.
#
# ⚠ FAIL-CLOSED, AND THE FAILURE IS TYPED. Anything that stops the answer arriving — no `node`, a
# goal with no `taskforce.csv` yet, an unreadable one — raises `_CastUnknown`, never an empty
# list. "I could not ask" and "nobody needs it" are different claims, and only the second may
# lift a requirement.
def _uncast_seats(goal_dir: Path) -> list[str]:
    """The seats of this goal that declare NO harness+model cast. Raises `_CastUnknown`."""
    import subprocess

    seeding = Path(__file__).resolve().parents[3] / "engine" / "seeding.js"
    try:
        proc = subprocess.run(
            ["node", "-e",
             "process.stdout.write(JSON.stringify("
             "require(process.argv[1]).uncastSeats(process.argv[2])))",
             str(seeding), str(goal_dir)],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise _CastUnknown(f"the launch's own seat reader could not be run: {exc}") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        lines = err.splitlines() or ["no output"]
        # node prints the throw site and a stack around the message; the message is the line that
        # names the error class. Falling back to the last line would quote a stack frame.
        raise _CastUnknown(next((ln.strip() for ln in lines if re.match(r"^\w*Error\b", ln.strip())),
                                lines[-1].strip())[:400])
    try:
        return list(json.loads(proc.stdout))
    except (ValueError, TypeError) as exc:
        raise _CastUnknown(f"unreadable answer: {proc.stdout[:200]!r}") from exc


def cmd_lane(args) -> int:
    root = resolve_goals_root(args.root)
    name = args.goal_name
    # The same name gate every other verb applies — it is also what keeps a `../..` from
    # resolving this write outside the goals root.
    if not GOAL_NAME_RE.match(name):
        raise Refusal(
            f"goal name '{name}' violates the naming rule — lowercase kebab-case "
            "([a-z0-9] words joined by single hyphens)"
        )
    goal_dir = root / name
    if not goal_dir.is_dir():
        raise Refusal(f"{goal_dir}: no such goal — `lane` assigns an EXISTING goal, never creates one")

    target = getattr(args, "set", None)
    if target:
        # THE STASH IS PROTECTED. `--set` writes the marker WHOLE, so setting a lane while a
        # pause is in force would overwrite the stashed assignment with no trace of what it was —
        # and the operator would believe the goal is paused while the daemon reads it as assigned.
        if lane_is_paused(read_lane_raw(goal_dir)):
            raise Refusal(
                f"{goal_dir / LANE_FILE}: this goal is PAUSED and `--set` writes the marker "
                "whole, which would discard the stashed assignment behind the pause. Run "
                f"`rbtv-goal resume {name}` first, then set the lane.", "lane-paused")
        if target not in LANES:
            raise Refusal(f"--set {target}: must be one of {', '.join(LANES)}")
        if target == "daemon":
            # ⚠ EVERY SEAT MUST BE CAST (`#d-abolish-profile-names` sub-ruling 3). This used to
            # demand `--profile <name>` here and only for goals that had an uncast seat; the flag
            # is gone and the uncast seat is now the refusal itself. There is nothing left to
            # launch such a seat ON, so handing the goal to the daemon would queue rows whose only
            # possible outcome is `E_UNCAST_SEAT` at spawn — refused here, where the operator is
            # standing, rather than at 03:00 in a journal.
            #
            # ⚠ THE UNMATERIALIZED GOAL IS RULED, NOT FALLEN INTO. A lane may legitimately be
            # assigned BEFORE `materialize` — `lane-watch.js` treats "assigned, no taskforce.csv
            # yet" as normal and quiet — and at that moment NO seat exists to inspect. UNKNOWN is
            # not `none`, so it is its own refusal, naming materialize as the way out.
            try:
                uncast = _uncast_seats(goal_dir)
            except _CastUnknown as exc:
                raise Refusal(
                    f"--set daemon: this goal's seats cannot be read, so whether ANY of them is "
                    f"uncast is unknown — which is not the same as 'none' ({exc}). If the goal is "
                    f"simply not materialized yet, run `rbtv-goal materialize {name}` and re-run "
                    f"this.",
                    "lane-cast-unknown") from exc
            if uncast:
                raise Refusal(
                    f"--set daemon REFUSED: {len(uncast)} seat(s) declare no harness+model cast in "
                    f"their seat.md — {', '.join(uncast)}. Bindings are the ONE source of truth for "
                    f"what a seat runs (`#d-abolish-profile-names`), and there is no fallback left "
                    f"to launch an uncast seat on. Cast them with `rbtv-bindings set "
                    f"<workflow.csv> <seat> <harness> <model> [effort]`, re-materialize, then set "
                    f"the lane.",
                    "lane-uncast-seats")
        write_lane_raw(goal_dir, lane_text(target))

    lane, legacy = read_lane(goal_dir)
    present = (goal_dir / LANE_FILE).exists()
    raw = read_lane_raw(goal_dir)
    paused = lane_is_paused(raw)
    paused_from = LANE_PAUSED_RE.sub("", raw, count=1).strip() if paused else None
    if args.json:
        print(json.dumps({
            "ok": True, "goal": name, "file": str(goal_dir / LANE_FILE),
            "assigned": present, "lane": lane, "legacy_marker": legacy,
            "paused": paused, "paused_from": paused_from,
        }, indent=2))
    else:
        where = f"{goal_dir / LANE_FILE}"
        if paused:
            # Printed BEFORE the lane line, not instead of it: `lane` reads CONSOLE while paused
            # (both readers resolve it that way) and a reader who saw only that would conclude the
            # daemon assignment was thrown away.
            print(f"{name}: PAUSED — stashed lane assignment {paused_from!r}; nothing new is "
                  f"seeded until `rbtv-goal resume {name}` ({where})")
        if legacy:
            print(f"{name}: ⚠ LEGACY MARKER — {raw.strip()!r} uses the RETIRED `daemon <profile>` "
                  f"grammar (`#d-abolish-profile-names` made the marker ONE WORD), so it does NOT "
                  f"parse as daemon and this goal reads CONSOLE. Repair: `rbtv-goal lane {name} "
                  f"--set daemon` ({where})")
        elif lane == "daemon":
            print(f"{name}: DAEMON lane — every seat runs its own cast; the daemon's watch pass "
                  f"picks it up ({where})")
        elif present:
            print(f"{name}: CONSOLE lane — run it with `rbtv run {goal_dir}` ({where})")
        else:
            print(f"{name}: CONSOLE lane (no assignment file — absent means console, and the "
                  f"daemon adopts only goals explicitly assigned to it)")
    return 0


# ---------------------------------------------------------------- lint


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, check: str, file: str, reason: str) -> None:
        self.items.append({"check": check, "file": file, "reason": reason})

    def __bool__(self) -> bool:
        return bool(self.items)


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

_COORD_GRAMMAR = None


def _coord_grammar():
    """`coord.py`, imported once. Refuses rather than degrading.

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
    global _COORD_GRAMMAR
    if _COORD_GRAMMAR is not None:
        return _COORD_GRAMMAR
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
    for name in ("parse_after_member", "after_member_limbs"):
        if not callable(getattr(mod, name, None)):
            raise Refusal(
                f"{coord_path}: `{name}` is absent or not callable — the grammar "
                f"this check imports has moved or been renamed; NO claim can be made.")
    _COORD_GRAMMAR = mod
    return mod


def after_member_grammar():
    """`coord.py`'s `parse_after_member`, imported. The MEMBER half of the grammar."""
    return _coord_grammar().parse_after_member


def after_cell_members(raw: str) -> list[str]:
    """The CELL grammar: comma-separated members, exactly as `taskforce_after` splits."""
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


def after_member_limbs(member: str) -> list[str]:
    """`coord.py`'s `after_member_limbs`, imported. The ALTERNATE half of the grammar.

    ⚠ IT USED TO BE A BYTE-IDENTICAL SECOND COPY, and that was the same defect W1 closed
    one function over — two readings of an `after` cell free to drift. Re-pointed at
    coord through the SAME bridge `after_member_grammar` already used
    (`build/one-readiness-predicate.md`); coord's own docstring carries the order rule
    (bracketed content neutralised BEFORE the alternate split, so a `|` inside a guard
    value never reads as an alternate — the strip-then-split defect #3386) and the
    reason the blanking is positional.
    """
    return _coord_grammar().after_member_limbs(member)


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


def substitute_after_ids(raw: str, mapping: dict[str, str]) -> str:
    """An `after` cell with its MEMBER IDS substituted and NOTHING else touched.

    Bracketed guard spans pass through untouched: a guard's field or value may spell a seat
    id, and substituting inside one would rewrite a CONDITION rather than a member. Outside
    the brackets the only tokens are member ids and the `,`/`|` joins, so a blanket id
    substitution there is exactly the rename.

    ⚠ ONE HOME, TWO CALLERS, and this is it. `materialize-seats.py#rename_after_cell` — the
    nested-instance rename (Rule 13's "verbatim apart from the instance renaming") — now
    DELEGATES here; `add-seat`'s splice is the second caller, substituting a predecessor for
    the freshly inserted seat. The grammar this walks is already this module's (`after_cell_
    members` / `after_member_limbs` / the imported `parse_after_member`), so a second copy in
    the team-kit was a second reading of an `after` cell waiting to drift.
    """
    return "".join(
        part if part.startswith("[")
        else re.sub(r"[a-z0-9][a-z0-9-]*",
                    lambda m: mapping.get(m.group(0), m.group(0)), part)
        for part in re.split(r"(\[[^\]]*\])", raw))


def render_csv_line(values: list[str]) -> str:
    """One registry line, csv-quoted exactly as the taskforce.csv append writes it (a
    multi-predecessor `after` cell carries commas and must quote).

    ⚠ THE CANONICAL FORM, and `add-seat`'s splice depends on it being the SAME one the
    append uses — its canonical-form guard re-renders every UNMUTATED row through this
    function and refuses unless the result is byte-identical to the file. Rendering through
    a second writer would let the guard pass on a file the append would have written
    differently. `materialize-seats.py#_render_csv_line` delegates here.
    """
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(values)
    return buf.getvalue()[:-1]


# The rules, stated once. A refusal message NAMES the rule it violated: the `check`
# string IS the rule, and the reason carries the offending token.
RULE_GUARD_GRAMMAR = "guard grammar `ref[field=value]`"
RULE_ALTERNATE_GRAMMAR = "alternate grammar `a|b`"


def check_after_grammar(rows: list[dict], f: Findings, path: Path,
                        id_col: str = "seat", after_col: str = "after") -> None:
    """Guard grammar + alternates, validated ON TOP OF acyclicity (7.426 / W3).

    `check_acyclic` answers "is this graph acyclic and do its edges resolve". It says
    nothing about whether a guard is ADMISSIBLE: `a[nokey]` is not a guarded member at
    all — `parse_after_member` hands it back whole and the evaluator treats it as a
    seat name that cannot exist, so the edge is permanently unmet and nothing says why.
    This arm refuses it at registration instead, naming the rule.

    Grammar-only. It rules on ADMISSIBILITY, never on whether a guard is satisfied —
    that is `coord.ready_seat_rows`' evaluation, against the ruling recorded in
    `coordination/guard-values.csv`, and no verdict about it is implied here.
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
    for required in ("goal.md", "decisions.md", "threads.sql"):
        if not (goal_dir / required).exists():
            f.add("CMP-4 goal-level layout", str(goal_dir / required),
                  "required by the CMP-4 layout, absent")

    # --- 4. the goal's plan (7.607 E2a: GOAL-LEVEL — the run compartment is extinguished, so
    # the taskforce descriptor, the milestone spine and the seats tree sit directly under the
    # goal folder. There is no longer a compartment to resolve, hence no resolution finding.)
    tf_path = goal_dir / "taskforce.csv"
    ms_path = goal_dir / "milestones.csv"

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

    seats_dir = goal_dir / "seats"
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
            if key in LINT_NON_REF_KEYS or key in BINDING_COLUMNS:
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

        # permissions well-formed: the seat declares permissions, and they were
        # assembled rather than left dangling.
        #
        # TWO layouts, ONE question. A csv-catalog seat carries a `permissions:` REF in
        # frontmatter; a d-prompt-task-files seat carries no refs at all — its permissions
        # live only as a `<permissions>` SECTION in the body, because the pool file's sections
        # ARE the assembled units. Asking only the frontmatter marked every pool-assembled seat
        # as permission-less (measured: 16 of 16 on a planning goal) while the body said
        # otherwise. The body scan is the same predicate materialize-seats.py's HARD GATE uses
        # to refuse such a seat, imported from here rather than restated.
        has_permissions = (
            any(k == "permissions" for k, _ in refs)
            or any(m.group(1) == "permissions" for m in SECTION_RE.finditer(sbody))
        )
        if not has_permissions:
            f.add("permissions well-formed", str(seat_md),
                  "seat declares no permissions — neither a frontmatter ref nor a "
                  "<permissions> section in the assembled body")

    # --- 5. the MIRROR of the row-without-folder finding above: a seat FOLDER with no
    # taskforce.csv row. That is exactly the half-state a crash between materialize-seats'
    # step 1 (seat descriptors) and step 2 (registry rows) leaves behind — and the loop
    # above, which walks ROWS and never folders, cannot see it by construction (measured:
    # 0 findings on a fixture carrying two orphan folders, dag-05 2026-07-29). Nothing
    # launches such a folder, so it is inert rather than dangerous; it is named because an
    # invisible half-state is otherwise indistinguishable from a finished materialize.
    named = {(row.get("seat") or "").strip() for row in rows}
    if seats_dir.is_dir():
        for seat_dir in sorted(p for p in seats_dir.iterdir() if p.is_dir()):
            if seat_dir.name not in named:
                f.add("seat folder resolves to a taskforce row", str(seat_dir),
                      f"orphan seat folder '{seat_dir.name}' — no taskforce.csv row names "
                      "it (a half-finished materialize: nothing will ever launch it)")

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
    if not goal_dir.is_dir():
        refuse("-", "schema-violation", f"{goal_dir}: no such goal folder",
               closes="the goal folder exists")
        return {"refusals": refusals, "flags": flags, "reports": reports}
    pass_dir = goal_dir / "planning" / pass_folder
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
            pass_dir = ((goal_dir / "planning" / args.pass_folder)
                        if goal_dir.is_dir() else None)
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
        if not is_unit and path.parent.name in ("prompts", "tasks"):
            # d-prompt-task-files: a FLAT pool file is a whole prompt/task, not
            # a cognitive unit. It carries frontmatter and kind-named sections
            # and would otherwise index as a unit named after the prompt.
            continue
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

    # d-prompt-task-files (2026-08-08): prompts.csv/tasks.csv are DROPPED — a
    # whole prompt lives at `<component>/prompts/<prompt-id>.md` and a whole
    # task at `<component>/tasks/<task-id>.md`, frontmatter carrying the card
    # data over kind-named XML sections. Both layouts load here so a catalog
    # root may hold either (the migration of the old components is task 7.565).
    for pool, bucket, key in (("prompts", prompts, "prompt-id"),
                              ("tasks", tasks, "task-id")):
        for path in sorted(catalog_root.rglob(f"{pool}/*.md")):
            if "cognitive-units" in path.parts:
                continue
            row = _pool_file_row(path, key)
            if row is None:
                continue
            ident = row[key]
            if ident in bucket:
                raise Refusal(f"duplicate {key} '{ident}' in {path}")
            bucket[ident] = row
    return seats, prompts, tasks


def _pool_file_row(path: Path, key: str) -> dict | None:
    """One prompt/task-file read as a catalog row (d-prompt-task-files), or
    None when the file is not a DEFINITION.

    `__body__` carries the file's kind-named sections verbatim — they ARE the
    assembled units, so nothing is resolved through a unit index.

    A flat `prompts/*.md` is not automatically a definition: the transitional
    whole-file prompt CARD (frontmatter `exposes:` over prose, read by
    materialize-seats' `_prompt_exposes`) lives at the same path and its
    definition is still a `prompts.csv` row elsewhere in the catalog root.
    The discriminator is the kind-named section — the one thing a definition
    has and a card does not. A card returns None; a definition that is
    MALFORMED still refuses, because a definition read as a card would go
    missing in silence.
    """
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    body = text[m.end():]
    if not re.search(r"<([a-z0-9-]+)(?:\s[^>\n]*)?>.*?</\1>", body, re.DOTALL):
        return None                      # a card, not a definition
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise Refusal(
            f"{path}: prompt/task frontmatter is not valid YAML — "
            f"{str(exc).strip()}"
        ) from exc
    if not isinstance(fm, dict) or not str(fm.get("id", "")).strip():
        raise Refusal(
            f"{path}: prompt/task file carries kind-named sections but no "
            f"`id:` in frontmatter — it is a definition nothing can name"
        )
    row = dict(fm)
    row[key] = str(fm["id"]).strip()
    row["description"] = str(fm.get("description", "")).strip()
    row["__source__"] = path
    row["__body__"] = body
    return row


# A kind-named section in an assembled body. TWO forms, both live: the assembler's
# `<kind id="…" version="…">` form (unit-file layout) and the bare/attributed `<kind>` /
# `<kind source="…">` form d-prompt-task-files made the section markup. Groups: (1) kind
# (2) id or None (3) version or None (4) body.
#
# ONE definition, two consumers: this file's `permissions well-formed` lint and
# materialize-seats.py's hard permissions gate, which imports it. They must agree by
# construction — a lint that answers "does this seat declare permissions?" differently from the
# gate that refused to materialize it without them is a lint nobody can act on.
SECTION_RE = re.compile(
    r'<([a-z0-9-]+)(?: id="([^"]+)")?(?: version="([^"]+)")?[^>\n]*>\n'
    r'(.*?)\n</\1>', re.DOTALL)

# Emitted seat.md frontmatter keys that are NEVER cognitive-unit references — the lint's
# exclusion list, NAMED so the selftest can assert membership instead of trusting a comment.
#
# ⚠ ANY NEW NON-REF SCALAR KEY THE EMITTED SCHEMA GAINS MUST BE ADDED HERE, in the same change
# that adds it. Discrimination rests entirely on this list: the ref grammar is `[a-z0-9-]+` and
# CANNOT tell a short value from a short unit id, so a token-shaped value that is not listed
# false-positives as an unresolved reference. Measured, both times:
#   dag-04 (2026-07-29) — the descriptor scalars (seat/cwd/agent_type/mode/window/senders/
#     close/auto-wake/ephemeral/broadcast/component).
#   d-prompt-task-files (2026-08-10) — the pool pass-throughs below: 'block-and-queue' from
#     `fallback` and 4x 'capability-cards' from `capabilities` on a 16-seat planning goal.
# The dangling-ref control stays red-able (materialize-seats.py selftest).
LINT_NON_REF_KEYS = (
    "id", "seat", "description", "cwd", "agent_type", "mode", "window", "senders",
    "close", "auto-wake", "ephemeral", "broadcast", "component",
    "human-interactive", "fallback", "capabilities", "context",
)

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
        if "__body__" in row:
            # d-prompt-task-files — the file's sections ARE the assembled
            # units: copied verbatim, no ids, no versions, no lockfile
            # (versioning is the file's git history).
            blocks.append(row["__body__"].strip("\n"))
            # PASS-THROUGH frontmatter keys. `human-interactive:` (+ its
            # required `fallback:`) is the D14 two-gate flag the engine reads
            # to decide a seat needs the owner live — it must reach seat.md or
            # the gate is unreadable at dispatch (d-goal-channels-v1-
            # transcription). Emitted only when the definition declares it.
            hi = row.get("human-interactive")
            if hi not in (None, ""):
                # THE VALUE IS CANON-CHECKED, and this is the only place it can be.
                # The consumer (bridges/chat/bus-ferry.js seatIsHumanInteractive) matches
                # `^human-interactive:[ \t]*(.+?)[ \t]*$` ON THE RAW FRONTMATTER TEXT — a
                # REGEX, not a YAML parse — lowercases the capture and compares it to
                # `yes`/`true`. Anything else answers FALSE, with no refusal anywhere: no
                # held-for-user line, the chat-bridge owner-contact gate silently shut, and
                # nothing said so. `maybe`, `1`, `on` and every typo land there. Refuse them
                # here instead, at materialize time.
                hi_norm = str(hi).strip().lower()
                if hi_norm not in ("yes", "true", "no", "false"):
                    raise Refusal(
                        f"{row['__source__']}: `human-interactive: {hi}` is not a "
                        f"canonical value — one of yes | true | no | false. The reader "
                        f"answers FALSE for anything else WITHOUT refusing, so an "
                        f"uncanonical value would silently close the owner-contact gate."
                    )
                if hi_norm in ("yes", "true"):
                    fb = str(row.get("fallback", "") or "").strip()
                    if fb not in ("park", "default-and-disclose", "block-and-queue"):
                        raise Refusal(
                            f"{row['__source__']}: `human-interactive: {hi}` "
                            f"declares fallback '{fb or '(absent)'}' — required, "
                            f"one of park | default-and-disclose | block-and-queue"
                        )
                    # EMITTED AS THE BOOLEAN, never the source spelling, and that choice
                    # is load-bearing: `yaml.safe_dump` renders the STRING "yes" as
                    # `'yes'` — QUOTED, so it cannot re-parse as a boolean — and the
                    # consumer's regex captures the quotes, lowercases `'yes'`, and
                    # answers FALSE. Measured end to end through
                    # bus-ferry.seatIsHumanInteractive: quoted -> false, bare -> true.
                    # `True` dumps as the bare token `true`, which is what the regex
                    # needs. A "normalize it to a string" instinct here reintroduces the
                    # exact silent-false this canon check exists to kill.
                    fm["human-interactive"] = True
                    fm["fallback"] = fb
            # `capabilities:`/`context:` are carried VERBATIM, never dropped:
            # a declared capability or forced read that vanished at assembly is
            # a seat promised a means it never receives. Rendering them as
            # resolved blocks is a separate, unbuilt design step.
            for col in ("capabilities", "context"):
                val = row.get(col)
                if val:
                    fm[col] = val
            continue
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
    tf_path = goal_dir / "taskforce.csv"
    if not tf_path.is_file():
        raise Refusal(f"{tf_path}: absent — nothing to materialize")

    rows = read_csv(tf_path)
    if not rows:
        raise Refusal(f"{tf_path}: no taskforce rows")

    seats_dir = goal_dir / "seats"
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
    # A FRESH `Findings`: `f` above may already carry findings of its own, and a
    # refusal must name only the rules THIS manifest broke.
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
    # leave a half-materialized goal on disk.
    assembled: dict[str, str] = {}
    for row in rows:
        seat = (row.get("seat") or "").strip()
        if not seat:
            raise Refusal(f"{tf_path}: a row carries no seat")
        assembled[seat] = assemble_seat(seat, row, seats, prompts, tasks, units)

    plan = {
        "goal": args.goal_name,
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


# ------------------------------------------------------- dag / add-seat (issue S-33)
#
# GROWING A LIVE GOAL'S SEAT ROSTER. Both verbs below serve one owner requirement: a goal that
# is already running turns out to need a seat nobody planned, and the only honest way to add it
# is to (1) let an agent SEE the graph without reading four files, and (2) insert the seat with
# every edge rewired in one atomic act that refuses anything it cannot do safely.

EXECUTIONS_FILE = "executions.csv"
# `engine/attached-execution.js#RUN_LOCK`. Stated, not imported — it is one filename across a
# language boundary and there is no bridge, so BOTH sides hold their own literal.
# ⚠ THE PIN IS NOT IN THIS FILE, AND A SELFTEST CANNOT BE IT: a Python arm comparing this literal
# to itself proves nothing about the JS side, which is what it was doing. The real pin is
# `probes/probe-goal-splice.py`'s cross-language arm — it evaluates
# `require('engine/attached-execution').RUN_LOCK` in node and asserts equality with this constant,
# so a rename on either side surfaces as a red arm rather than a gate that silently stops firing.
ATTACHED_RUN_LOCK = ".attached-run.lock"


def read_executions(goal_dir: Path) -> list[dict]:
    """The goal's execution record, or `[]` when it has never run.

    ABSENT IS EMPTY, deliberately: a goal that has never run has no record file, and that is
    the quiescent case rather than a failure. `read_csv` refuses a missing file (right for a
    registry, wrong for a ledger that is born on first execution).
    """
    p = goal_dir / EXECUTIONS_FILE
    if not p.is_file():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def seat_states(goal_dir: Path) -> dict[str, dict]:
    """Per-seat execution state, DERIVED from the execution record — never stored.

    Three answers, in the record's own vocabulary:
      never-ran  no row names this seat
      open       its LAST row carries an EMPTY outcome (`ended` unstamped: still going, as far
                 as the lane that wrote it knows)
      done       its LAST row is stamped; the outcome reported is that row's

    ⚠ THE LAST ROW DECIDES, IN FILE ORDER — never "any row is open". The record is append-only
    and the engine keys on exactly this (`engine/execution-record.js`: "the seat's LAST word in
    the record is what every reader keys on"; `engine/seeding.js#recordView` takes the last row
    per seat in file order and calls a seat with an unstamped last row not-finished). A seat with
    rows [done, open] read `open` here while a seat with [open, done] read `open` too — so a
    revived seat that finished still reported as running, and the two readers disagreed about the
    same file. File order, not `started`, because that is the ordering the engine uses; sorting
    by `started` here would re-introduce the disagreement in the other direction.
    """
    by_seat: dict[str, list[dict]] = {}
    for row in read_executions(goal_dir):
        seat = (row.get("seat") or "").strip()
        if seat:
            by_seat.setdefault(seat, []).append(row)
    states: dict[str, dict] = {}
    for seat, rows in by_seat.items():
        outcome = (rows[-1].get("outcome") or "").strip()
        states[seat] = {"state": "done" if outcome else "open",
                        "outcome": outcome, "runs": len(rows)}
    return states


def topo_order(rows: list[dict]) -> list[str]:
    """Seats in dependency order — predecessors first, registry order among ready seats.

    Acyclicity is NOT proven here and is not this function's claim (`check_acyclic` is the
    room's only sanctioned walk, Rule 9). Anything still pending when no seat is ready is
    appended in registry order rather than dropped: `dag` is a READ verb, and a listing that
    silently omits the seats caught in a cycle would hide the very thing worth seeing.
    """
    order, placed = [], set()
    seats = [(r.get("seat") or "").strip() for r in rows]
    preds = {(r.get("seat") or "").strip(): after_pred_names(r.get("after") or "")
             for r in rows}
    pending = [s for s in seats if s]
    while pending:
        ready = [s for s in pending
                 if all(p not in preds or p in placed for p in preds[s])]
        if not ready:
            return order + pending
        for s in ready:
            order.append(s)
            placed.add(s)
            pending.remove(s)
    return order


def cmd_dag(args) -> int:
    """The goal's graph in ONE read — seats, their predecessors, and where each one stands.

    Owner requirement R6: an agent deciding where a new seat belongs should not have to open
    `taskforce.csv`, `executions.csv` and `seats/` and join them in its head. Everything here
    is DERIVED from those three; this verb stores nothing and writes nothing.
    """
    root = resolve_goals_root(args.root)
    goal_dir = resolve_goal_dir(root, args.goal_name)
    if not goal_dir.is_dir():
        raise Refusal(f"{goal_dir}: no such goal folder", "goal-absent")
    tf_path = goal_dir / "taskforce.csv"
    if not tf_path.is_file():
        raise Refusal(f"{tf_path}: absent — this goal has no seat registry to graph",
                      "registry-absent")
    rows = read_csv(tf_path)
    states = seat_states(goal_dir)
    by_seat = {(r.get("seat") or "").strip(): r for r in rows if (r.get("seat") or "").strip()}

    seats_dir = goal_dir / "seats"
    materialized = {p.name for p in seats_dir.iterdir() if p.is_dir()} if seats_dir.is_dir() else set()
    # DRIFT, both directions. A folder with no row is a seat nothing will ever schedule; a row
    # with no folder is a seat that cannot launch. Neither is a refusal here — `dag` reports.
    orphan_folders = sorted(materialized - set(by_seat))
    unmaterialized = sorted(set(by_seat) - materialized)

    nodes = []
    for seat in topo_order(rows):
        row = by_seat[seat]
        st = states.get(seat, {"state": "never-ran", "outcome": "", "runs": 0})
        nodes.append({
            "seat": seat,
            "after": (row.get("after") or "").strip(),
            "predecessors": after_pred_names(row.get("after") or ""),
            "state": st["state"],
            "outcome": st["outcome"],
            "runs": st["runs"],
            "materialized": seat in materialized,
        })

    if args.json:
        print(json.dumps({"ok": True, "goal": args.goal_name, "nodes": nodes,
                          "orphan_seat_folders": orphan_folders,
                          "unmaterialized_rows": unmaterialized}, indent=2))
        return 0

    print(f"goal-dag {args.goal_name}  ({len(nodes)} seat row(s), dependency order)")
    for n in nodes:
        state = n["state"] + (f"={n['outcome']}" if n["outcome"] else "")
        preds = ", ".join(n["predecessors"]) or "(root)"
        flag = "" if n["materialized"] else "   <-- no seat folder"
        print(f"  {n['seat']:<28} after: {preds:<34} {state}{flag}")
        if n["after"] and n["after"] != ", ".join(n["predecessors"]):
            # The RAW cell, whenever guards or alternates make it differ from the plain
            # predecessor list — that is the text `add-seat` would rewrite.
            print(f"  {'':<28} cell: {n['after']}")
    for name in orphan_folders:
        print(f"  DRIFT: seats/{name}/ exists with no taskforce.csv row")
    if not nodes:
        print("  (no rows)")
    return 0


# ------------------------------------- add-seat: the splice
#
# ⚠ THE WRITE ORDER IS MINT-THEN-SPLICE, NEVER THE REVERSE. `materialize-seats.py` writes the
# seat's descriptors BEFORE its registry row (its own discipline: a refusal on the last seat
# leaves zero rows). Splicing first would point live `after` cells at a seat that does not yet
# exist — a window in which the daemon could seed against an unresolvable edge. Minting first
# leaves the opposite window, which is harmless: a seat with a row and no successor pointing at
# it is simply a seat nothing waits for. `--splice-only` is the crash-resume for the gap.


def _split_seat_list(raw: str | None) -> list[str]:
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def _read_registry_raw(path: Path) -> str:
    """The registry's bytes as text, with NO newline translation.

    ⚠ `read_text()` UNIVERSAL-NEWLINES a CRLF registry into LF before the canonical-form guard
    can see it, so the guard passed — and the atomic write then replaced the file with LF
    throughout. Every line changed, which is exactly the damage that guard exists to refuse, and
    it was invisible because the reader had already destroyed the evidence. Read the bytes.
    """
    with path.open(encoding="utf-8", newline="") as fh:
        return fh.read()


def _parse_registry(text: str) -> tuple[list[str], list[str], int, int, list, dict]:
    """The registry's raw lines, parsed cells and seat index — with every WHOLE-FILE precondition
    already refused: unterminated tail, empty, header drift, CRLF, non-canonical form.

    ONE reader, TWO callers, and that is the point: `_preflight_splice` runs it PRE-MINT so a
    refusable splice costs nothing, and `splice_new_seat` runs it again on the post-mint baseline
    it actually rewrites. A second reading here would be two answers to "is this file spliceable".
    """
    if text and not text.endswith("\n"):
        raise Refusal(
            "taskforce.csv does not end in a newline — a partial trailing line is unparseable "
            "by every consumer at once; repair the registry before splicing",
            "taskforce-tail-unterminated")
    # CRLF, NAMED. Without this the canonical-form guard below fires on EVERY line (each carries a
    # trailing `\r` the writer never emits) and told the operator to "repair the registry" without
    # saying what was wrong with it. The precondition is LF-only, so say so; normalizing silently
    # would rewrite every byte of a file this verb promises to leave alone.
    if "\r\n" in text:
        raise Refusal(
            "taskforce.csv has CRLF line endings — the registry's canonical form is LF-only "
            "(every writer emits `\\n`), so a splice through it would rewrite every line's "
            "terminator. Convert the file to LF and re-run; nothing is normalized for you.",
            "taskforce-noncanonical")
    lines = text.split("\n")[:-1]
    if not lines:
        raise Refusal("taskforce.csv is empty — there is no registry to splice into",
                      "taskforce-empty")
    header = next(csv.reader([lines[0]]))
    if "seat" not in header or "after" not in header:
        raise Refusal(
            f"taskforce.csv header is {lines[0]!r} — a splice needs the 'seat' and 'after' "
            "columns and will not guess which is which", "taskforce-header-drift")
    seat_at, after_at = header.index("seat"), header.index("after")

    cells = [next(csv.reader([ln])) if ln.strip() else None for ln in lines[1:]]
    index = {}
    for i, cs in enumerate(cells):
        if cs is None:
            continue
        s = cs[seat_at].strip() if seat_at < len(cs) else ""
        if s:
            index.setdefault(s, i)

    # ── THE CANONICAL-FORM GUARD ──────────────────────────────────────────────────────────────
    #
    # Re-render EVERY row through the same writer the append uses and require byte-equality
    # BEFORE mutating anything. Without it, a hand-edited registry (an unquoted cell, a stray
    # space after a comma, CRLF) would come back through this splice REWRITTEN — every line
    # changed, the diff unreviewable, and the operator unable to tell the splice from the
    # reformatting. Refusing keeps the promise `add-seat` actually makes: every line but the
    # rewritten ones is byte-unchanged.
    for i, cs in enumerate(cells):
        if cs is None:
            continue
        if render_csv_line(cs) != lines[i + 1]:
            raise Refusal(
                f"taskforce.csv line {i + 2} is not in the registry's canonical csv form "
                f"({lines[i + 1]!r} re-renders as {render_csv_line(cs)!r}) — a splice rewrites "
                "ONLY the rows it re-parents and cannot promise that over a file whose other "
                "rows would be reformatted on the way through. Repair the registry first.",
                "taskforce-noncanonical")
    if render_csv_line(header) != lines[0]:
        raise Refusal(
            f"taskforce.csv header line is not in canonical csv form ({lines[0]!r}) — "
            "repair the registry before splicing", "taskforce-noncanonical")
    return lines, header, seat_at, after_at, cells, index


def _check_before(target: str, index: dict, cells: list, after_at: int,
                  after: list[str]) -> tuple[int, list, str]:
    """One `--before` seat ruled on: it exists, and it actually WAITS on something in `--after`.

    Returns `(row index, its cells, its current after cell)`. Both refusals are computable from
    the registry alone, which is why the preflight can fire them before a single byte is minted.
    """
    if target not in index:
        raise Refusal(
            f"--before {target}: no taskforce.csv row carries that seat — the insertion "
            f"point must be a seat that exists. Known seats: {', '.join(sorted(index))}",
            "splice-before-unknown")
    i = index[target]
    cs = list(cells[i])
    old = cs[after_at] if after_at < len(cs) else ""
    after_set = set(after)
    if not [m for m in after_cell_members(old)
            if any(n in after_set for n in after_pred_names(m))]:
        raise Refusal(
            f"--before {target}: its `after` cell is {old!r}, which shares no member with "
            f"--after ({', '.join(after) or 'none'}) — the new seat would not be BETWEEN "
            "anything, so this is not an insertion. Name a successor that actually waits "
            "on one of the --after seats.", "splice-not-an-insertion")
    return i, cs, old


def _preflight_splice(text: str, after: list[str], before: list[str]) -> None:
    """Every splice refusal computable BEFORE the mint, fired from the gate block.

    ⚠ THIS IS WHY IT EXISTS. `splice_new_seat` runs after the mint, so a registry that was never
    spliceable — an unknown `--before`, a `--before` that is not an insertion point, a
    non-canonical file — used to refuse with the seat's row ALREADY APPENDED and `seats/<seat>/`
    ALREADY ASSEMBLED: a half-grown goal produced by a gate. Every one of those answers is a pure
    function of the pre-mint registry, so it is ruled on here, where refusing costs nothing.

    `splice-no-row` is deliberately NOT here: pre-mint the new seat has no row BY CONSTRUCTION,
    and that check belongs to the post-mint baseline alone.
    """
    _lines, _header, _seat_at, after_at, cells, index = _parse_registry(text)
    for target in before:
        _check_before(target, index, cells, after_at, after)


def splice_new_seat(text: str, new_seat: str, after: list[str],
                    before: list[str]) -> tuple[str, list[dict]]:
    """PURE. `taskforce.csv` raw text in, spliced raw text + the rewrite log out.

    For each `--before` seat: the members of its `after` cell that are in the `--after` set are
    substituted with `new_seat` — so `x after a` becomes `x after new-seat` when the new seat was
    inserted after `a`. Members NOT in the `--after` set stay exactly where they are: an
    insertion re-parents only the edges it sits on.

    Every refusal here fires BEFORE any byte is produced, and the caller writes the result in
    ONE atomic replace, so a refusal at the last row leaves the registry untouched. Every check
    but `splice-no-row` ALSO fired pre-mint through `_preflight_splice`; they re-run here because
    the baseline is a different file (the mint appended to it) — a passing preflight is not a
    licence to skip the real one.
    """
    lines, _header, _seat_at, after_at, cells, index = _parse_registry(text)

    if new_seat not in index:
        raise Refusal(
            f"taskforce.csv carries no row for seat '{new_seat}' — the splice re-parents edges "
            "onto a registered seat, and there is nothing to point at. Mint the seat first "
            "(drop --splice-only, or run materialize-seats.py --seat directly).",
            "splice-no-row")

    after_set = set(after)
    rewrites: list[dict] = []
    for target in before:
        i, cs, old = _check_before(target, index, cells, after_at, after)
        # Substitute through the ONE after-grammar substitution (guard spans untouched), then
        # dedupe order-preserving: `a,b` both replaced collapses to a single `new-seat` member
        # rather than listing it twice.
        substituted = substitute_after_ids(old, {a: new_seat for a in after_set})
        seen, members = set(), []
        for m in after_cell_members(substituted):
            if m not in seen:
                seen.add(m)
                members.append(m)
        new_cell = ",".join(members)
        cs[after_at] = new_cell
        cells[i] = cs
        rewrites.append({"seat": target, "old_after": old, "new_after": new_cell})

    out = [lines[0]] + [render_csv_line(cs) if cs is not None else lines[i + 1]
                        for i, cs in enumerate(cells)]
    return "\n".join(out) + "\n", rewrites


def cmd_add_seat(args) -> int:
    """Grow a LIVE goal's roster: gate, mint the seat, splice it into the graph.

    Every gate below fires BEFORE any write, and every one of them fires under `--dry-run` too —
    a dry run that skipped the gates would be a rehearsal of a different act. Gate (g) extends
    that to the SPLICE: the checks computable from the pre-mint registry are ruled on here, so a
    refusable splice never leaves a half-grown goal. Only `splice-no-row`, the mutated-graph
    validation and the changed-underfoot re-read stay post-mint — each needs the file the mint
    wrote.
    """
    import subprocess
    import tempfile

    root = resolve_goals_root(args.root)
    goal_dir = resolve_goal_dir(root, args.goal_name)
    if not goal_dir.is_dir():
        raise Refusal(f"{goal_dir}: no such goal folder", "goal-absent")
    tf_path = goal_dir / "taskforce.csv"
    if not tf_path.is_file():
        raise Refusal(f"{tf_path}: absent — nothing to splice into", "registry-absent")

    seat = args.seat
    after = _split_seat_list(args.after)
    before = _split_seat_list(args.before)
    if not after:
        raise Refusal("--after names the predecessor(s) the new seat waits on and is required — "
                      "an omitted insertion point never defaults to root", "after-required")

    # ── GATE (a): the goal is PAUSED ──────────────────────────────────────────────────────────
    # Not a formality. Splicing a live goal's graph while the daemon is free to seed means the
    # seeder can read `taskforce.csv` mid-rewrite, or seed a successor whose `after` cell is
    # about to change under it. Pause is the one thing that makes the window unreachable.
    if not lane_is_paused(read_lane_raw(goal_dir)):
        raise Refusal(
            f"{goal_dir / LANE_FILE}: this goal is NOT paused. Growing a live roster rewrites "
            "`after` cells the seeder reads every cadence, so the daemon must be let go of "
            f"first: run `rbtv-goal pause {args.goal_name}`, add the seat, then "
            f"`rbtv-goal resume {args.goal_name}`.", "goal-not-paused")

    # ── GATE (b): QUIESCENT — no seat's LAST execution is still open ──────────────────────────
    # Read through `seat_states`, so this gate and `dag` answer the same question the same way,
    # and both answer it the way the engine does (`seeding.js#recordView`: a seat's LAST row is
    # its state; an earlier open row that a later row superseded is spent, not live).
    executions = read_executions(goal_dir)
    still_open = {s for s, st in seat_states(goal_dir).items() if st["state"] == "open"}
    open_rows = [r for r in executions if not (r.get("outcome") or "").strip()
                 and (r.get("seat") or "").strip() in still_open]
    if open_rows and not args.allow_open_execution:
        # ⚠ NAME THE ROWS. A killed run leaves its row open FOREVER — nothing ever closes it —
        # so "wait for the record to close" described an event that would never happen, and this
        # gate became a permanent refusal with no way past it. The operator now gets the exact
        # rows to judge, plus the escape.
        detail = "; ".join(
            f"seat {(r.get('seat') or '?').strip()} session {(r.get('session-id') or '?').strip()}"
            f" started {(r.get('started') or '?').strip()}"
            for r in open_rows)
        raise Refusal(
            f"{goal_dir / EXECUTIONS_FILE}: {detail} — open execution row(s) (empty outcome). "
            "Pause stops new SEEDING; it does not stop a session already running, and "
            "re-parenting the graph under a running seat changes what its successors wait on "
            "mid-turn. Wait for the record to close — or, if the session is GONE (a killed run "
            "never closes its row), pass --allow-open-execution to proceed deliberately.",
            "goal-not-quiescent")

    # ── GATE (c): no --before seat has EVER run ───────────────────────────────────────────────
    # A seat that has already run resolved its `after` cell once. Re-parenting it now means the
    # graph no longer describes the run that happened, and a resume would re-derive readiness
    # from an edge set that never gated anything.
    ran = {(r.get("seat") or "").strip() for r in executions}
    already = [b for b in before if b in ran]
    if already:
        raise Refusal(
            "--before " + ", ".join(already) + ": already carries execution-record row(s), so "
            "its `after` cell has already been resolved once — re-parenting it now would make "
            "the registry describe a graph that never ran. Attach the new seat before a "
            "successor that has not started.", "splice-target-has-run")

    # ── GATE (d): no attached run holds this goal ─────────────────────────────────────────────
    if (goal_dir / ATTACHED_RUN_LOCK).exists():
        raise Refusal(
            f"{goal_dir / ATTACHED_RUN_LOCK}: an ATTACHED run (`rbtv run`) holds this goal — its "
            "engine is advancing the same graph this splice rewrites. Let the run finish or "
            "stop it, then add the seat. (A lock whose runner is gone is cleared by the runner "
            "itself on the next `rbtv run`.)", "attached-run-live")

    # ── GATE (e): the shared bindings sheet actually carries this seat ────────────────────────
    # The materializer refuses this too (`bindings-missing-seat`), but it does so after a
    # subprocess hop, and its message is about "the set being materialized" — which reads as a
    # workflow problem. Checked here, where the answer is one line: your sheet has no seat 'X'.
    sheet_path = Path(args.bindings).expanduser().resolve()
    try:
        sheet = json.loads(sheet_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refusal(f"--bindings {sheet_path}: unreadable ({exc})", "bindings-unreadable")
    if not isinstance(sheet, dict) or not isinstance(sheet.get("seats"), dict):
        raise Refusal(f"--bindings {sheet_path}: must be a JSON object carrying a 'seats' mapping",
                      "bindings-schema")
    if seat not in sheet["seats"]:
        raise Refusal(
            f"--bindings {sheet_path}: carries no entry for seat '{seat}' — a missing binding is "
            "a refusal, never a default (which harness, model and effort the seat runs on has "
            f"no honest guess). Known seats: {', '.join(sorted(sheet['seats'])) or '(none)'}",
            "bindings-missing-seat")

    # The PRE-MINT graph — what the gates rule on. The new seat is deliberately not in it yet.
    rows = read_csv(tf_path)

    # ── GATE (f): a COMPLEX cell + a stashed DAEMON lane ──────────────────────────────────────
    # Every cell this run would WRITE — the new seat's own `after` and each rewritten cell.
    # Multi-member or guarded cells are exactly the shapes the daemon seeder's readiness read
    # handles least well; combined with a stashed `daemon` assignment, resuming would hand the
    # seeder a cell class the parallel seeder fix is being built to cover.
    stashed = LANE_PAUSED_RE.sub("", read_lane_raw(goal_dir), count=1).strip()
    stashed_daemon = stashed.split()[:1] == ["daemon"]
    by_seat = {(r.get("seat") or "").strip(): r for r in rows}
    written_cells = {seat: ",".join(after)}
    for b in before:
        if b in by_seat:
            written_cells[b] = (by_seat[b].get("after") or "").strip()
    complex_cells = {s: c for s, c in written_cells.items()
                     if len(after_cell_members(c)) > 1 or "[" in c}
    if complex_cells and stashed_daemon:
        detail = "; ".join(f"{s}: {c!r}" for s, c in sorted(complex_cells.items()))
        if args.dry_run:
            print(f"WARNING daemon-complex-cell: {detail} — multi-member or guarded cell(s) on a "
                  "goal whose stashed lane is `daemon`. The real run refuses this unless "
                  "--allow-daemon-complex-cell is passed.")
        elif not args.allow_daemon_complex_cell:
            raise Refusal(
                f"{detail} — this splice writes multi-member or guarded `after` cell(s) and the "
                f"stashed lane assignment is `{stashed}`, so resuming hands the daemon seeder "
                "exactly the cell class it reads least reliably today. The parallel seeder fix "
                "(engine/seeding.js) lifts this concern once deployed; until then, either resume "
                "into the console lane (`rbtv-goal resume`, then `lane --set console`) or pass "
                "--allow-daemon-complex-cell to accept the risk deliberately.",
                "daemon-complex-cell")

    # ── GATE (g): the splice this run WOULD perform is possible at all ────────────────────────
    # Ruled on the PRE-MINT registry, so an impossible splice never mints. Before this gate the
    # splice validations lived only after the mint, and a bad `--before` — or a non-canonical
    # registry — refused with the row already appended and `seats/<seat>/` already assembled.
    _preflight_splice(_read_registry_raw(tf_path), after, before)

    # ── SCOPED SHEET ──────────────────────────────────────────────────────────────────────────
    # The materializer refuses a sheet naming any seat OUTSIDE the set being materialized
    # (`bindings-extra-seat`), and the goal's shared sheet names every seat of the workflow. So
    # a one-seat sheet is written for the subprocess. OUTSIDE the goal folder on purpose: a
    # temp file inside it would be a stray artifact under the very tree this verb is auditing,
    # and a crash between mint and splice would leave it there.
    scoped = None
    minted = None
    try:
        if not args.splice_only:
            fd, scoped_name = tempfile.mkstemp(prefix=f"add-seat-{seat}-", suffix=".json")
            scoped = Path(scoped_name)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"defaults": sheet.get("defaults", {}),
                           "seats": {seat: sheet["seats"][seat]}}, fh, indent=2)
            materializer = Path(__file__).resolve().parents[3] / "team-kit" / "materialize-seats.py"
            if not materializer.is_file():
                raise Refusal(f"{materializer}: the seat materializer is absent — this verb mints "
                              "through it and never re-implements assembly", "materializer-absent")
            cmd = [sys.executable, str(materializer),
                   "--package", str(goal_dir), "--seat", seat,
                   "--after", ",".join(after),
                   "--catalog-root", str(Path(args.catalog_root).expanduser().resolve()),
                   "--bindings", str(scoped), "--json"]
            # ⚠ NO `--taskforce-id` IS PASSED, and that is the materializer's own contract, not an
            # omission: the append reads the run's taskforce-id "from the file, never argv"
            # (`materialize-seats.py`, the `registry-absent` refusal). The flag does not exist
            # there, and passing it made every mint fail on an unrecognised argument.
            if args.dry_run:
                cmd.append("--dry-run")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            minted = {"cmd": cmd[1:], "returncode": proc.returncode,
                      "stdout": proc.stdout, "stderr": proc.stderr}
            if proc.returncode != 0:
                hint = ""
                if "seat-exists" in (proc.stdout + proc.stderr):
                    hint = ("\nThe seat is ALREADY minted. If a previous `add-seat` died between "
                            "the mint and the splice, re-run with --splice-only to finish it.")
                raise Refusal(
                    f"the seat mint refused (exit {proc.returncode}):\n"
                    + (proc.stderr.strip() or proc.stdout.strip()) + hint, "mint-refused")
    finally:
        if scoped is not None:
            scoped.unlink(missing_ok=True)

    # ── SPLICE ────────────────────────────────────────────────────────────────────────────────
    if args.dry_run:
        # Nothing was minted, so the new seat's row does not exist yet and `splice_new_seat`
        # would refuse `splice-no-row`. The REVIEW SURFACE is the local graph instead: what the
        # operator is being asked to approve is which edges move.
        preview = []
        for b in before:
            old = (by_seat.get(b, {}).get("after") or "").strip()
            hit = [m for m in after_cell_members(old)
                   if any(n in set(after) for n in after_pred_names(m))]
            preview.append({"seat": b, "old_after": old,
                            "would_become": ",".join(dict.fromkeys(after_cell_members(
                                substitute_after_ids(old, {a: seat for a in after})))),
                            "members_replaced": hit})
        plan = {"ok": True, "dry_run": True, "goal": args.goal_name, "seat": seat,
                "after": after, "before": before, "rewrites": preview, "mint": minted}
        if args.json:
            print(json.dumps(plan, indent=2))
        else:
            print(f"dry-run add-seat {seat} into {args.goal_name}")
            print(f"  predecessors -> {', '.join(after)}")
            print(f"  {' ' * 14} -> {seat}")
            for p in preview:
                print(f"  {seat} -> {p['seat']}   after: {p['old_after']!r} "
                      f"becomes {p['would_become']!r}")
            if not before:
                print(f"  (no --before: {seat} is a LEAF — nothing waits on it)")
        return 0

    # ⚠ READ AFTER THE MINT, never before. The mint APPENDS the new seat's registry row through a
    # subprocess, so a snapshot taken before it does not contain the row the splice re-parents
    # onto — measured: splicing the pre-mint text refuses `splice-no-row` on a run that had just
    # minted the seat successfully, leaving the goal in exactly the half-done state
    # `--splice-only` exists to resume. This read is also the baseline the changed-underfoot
    # guard below compares against, which is what makes that guard mean "another writer", rather
    # than "the mint wrote, as instructed".
    raw_text = _read_registry_raw(tf_path)
    spliced, rewrites = splice_new_seat(raw_text, seat, after, before)

    # Validate the MUTATED rowset through the SAME two functions, in the SAME order,
    # `cmd_materialize` uses — no copy, no second walk, no new rule.
    mutated_rows = list(csv.DictReader(io.StringIO(spliced)))
    graph = Findings()
    check_acyclic(mutated_rows, graph, tf_path)
    check_after_grammar(mutated_rows, graph, tf_path)
    if graph:
        raise Refusal(
            f"{tf_path}: the SPLICED after-graph does not validate, so nothing was written "
            f"({len(graph.items)} finding(s)):\n"
            + "\n".join(f"  [{i['check']}] {i['reason']}" for i in graph.items),
            "spliced-graph-invalid")

    # CHANGED-UNDERFOOT. `spliced` was computed from the post-mint snapshot; validating the
    # mutated graph is not instantaneous, and a parallel writer could have appended in the
    # meantime. Re-read and refuse rather than clobbering whatever landed.
    if _read_registry_raw(tf_path) != raw_text:
        raise Refusal(
            f"{tf_path}: changed on disk between the read and the write. The mint's own append "
            "is already inside the snapshot this splice was computed from, so this means "
            "ANOTHER writer touched the registry. Nothing was written — re-run with "
            "--splice-only.", "taskforce-changed-underfoot")

    tmp = tf_path.with_suffix(tf_path.suffix + ".tmp")
    tmp.write_text(spliced, encoding="utf-8", newline="")
    tmp.replace(tf_path)

    if args.json:
        print(json.dumps({"ok": True, "goal": args.goal_name, "seat": seat, "after": after,
                          "rewrites": rewrites, "mint": minted,
                          "taskforce": str(tf_path)}, indent=2))
    else:
        print(f"add-seat: {seat} spliced into {args.goal_name}")
        print(f"  after: {', '.join(after)}")
        for r in rewrites:
            print(f"  rewired {r['seat']}: {r['old_after']!r} -> {r['new_after']!r}")
        if not rewrites:
            print(f"  {seat} is a LEAF — no successor was re-parented")
        print(f"  resume the goal with `rbtv-goal resume {args.goal_name}`")
    return 0


# ---------------------------------------------------------------- teardown


# ⚠⚠ THE ONE VERB IN THIS FILE THAT NEEDS THE DAEMON UP (see the module docstring's amendment).
# Every other verb here is a local file operation precisely so it works with the daemon down; this
# one cannot be, because the thing it reclaims — the job CATALOGUE — lives in `heart.db` under the
# machine's state root and is reachable only through the gateway (ignite/CLAUDE.md § State layout:
# "the jobs catalogue is not readable without the daemon", an accepted consequence of the ruling
# that the store stays ONE per-machine file). It refuses typed when the daemon is unreachable
# rather than half-working.
#
# WHY IT EXISTS (IPH-27). Scaffolding a goal WRITES catalogue rows — `<goal>-workflow-start` from
# `capabilities/goal-creation-request`, and one `seat-<goal>-<seat>` per seat from
# `engine/seeding.js#seedTaskforce` on the goal's first seed. Deleting the goal folder removed none
# of them, and registration is create-only, so the goal's NAME was burnt: 18 stranded rows for one
# goal, and a same-name re-scaffold refused `E_JOB_EXISTS`. `deregister-job --purge` made the rows
# reclaimable; this verb is what CALLS it, so a teardown is one command instead of an undocumented
# 3-step-per-row sequence whose ordering is easy to get wrong.
#
# ⚠ IT DOES NOT DELETE THE GOAL FOLDER, and that is owner-ruled (2026-08-12), not an omission. It
# is the same reasoning `goal_creation_request.py` records for building no unwind on a failed
# scaffold: this tool cannot prove it alone created that directory, so removing it would be a
# destructive act taken on an assumption. Teardown cleans the DAEMON's side and tells you the
# folder is yours. Run it BEFORE deleting the folder — that is the order the exact-id path needs.

_WORKFLOW_START_SUFFIX = "-workflow-start"
# The non-terminal turn statuses, spelled here because this process cannot import the store's set.
# ⚠ Keep in step with `TURN_STATUSES - TERMINAL_TURN_STATUSES` in `server/heart/heart-store.js`.
# A status DROPPED from this list is the dangerous direction: teardown would stop seeing a live
# turn it should have refused on. `--dry-run` prints what it saw, so a drift is visible.
_LIVE_STATUSES = ("launching", "running", "stalled")


def _ignite_bin(explicit: str | None) -> list[str]:
    """The argv prefix that runs the ignite client.

    NAMED, never resolved on PATH — the same fact every daemon-fired entry in
    `config/spawn-profiles.yaml` states: a systemd --user manager's PATH does not carry
    `~/.local/bin`, so a bare `ignite` resolves interactively and nowhere else.
    """
    if explicit:
        # A `.js` path needs an interpreter; anything else (a symlink on PATH, a wrapper) is
        # already executable and is run as given.
        return ["node", explicit] if explicit.endswith(".js") else [explicit]
    return ["node", str(Path(__file__).resolve().parents[3] / "cli" / "ignite.js")]


def _ignite(prefix: list[str], *argv: str) -> dict:
    """One `ignite --json` call. Returns the gateway envelope; raises Refusal on transport death.

    ⚠ THE TRANSPORT FAILURE IS ITS OWN REFUSAL, never folded into "the daemon said no". Exit 5 is
    `CLI_TRANSPORT_ERROR` — the daemon is down or unreachable — and a teardown that reported
    "nothing to purge" because it could not ASK would be the worst possible answer here: it reads
    as a clean teardown over a catalogue it never saw.
    """
    import subprocess

    try:
        proc = subprocess.run([*prefix, "--json", *argv], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refusal(f"could not run the ignite client ({' '.join(prefix)}): {exc}",
                      "ignite-unrunnable") from exc
    if proc.returncode == 5:
        raise Refusal(
            "the ignite daemon is unreachable, so the job catalogue cannot be read. Unlike every "
            "other `rbtv-goal` verb, teardown NEEDS the daemon up — the catalogue lives in the "
            "machine's heart.db and only the gateway serves it. Start it "
            "(`rbtv ignite daemon start`) and re-run. Nothing was changed.",
            "daemon-unreachable")
    try:
        return json.loads(proc.stdout)
    except ValueError:
        raise Refusal(
            f"the ignite client answered nothing parseable to `{' '.join(argv)}` "
            f"(exit {proc.returncode}): {(proc.stderr or proc.stdout or '').strip()[:400]}",
            "ignite-unparseable")


def _ignite_result(env: dict, what: str) -> dict:
    if not env.get("ok"):
        err = env.get("error") or {}
        raise Refusal(f"{what} refused by the daemon [{err.get('code')}]: {err.get('message')}",
                      "daemon-refused")
    return env.get("result") or {}


def cmd_teardown(args) -> int:
    """Reclaim a goal's catalogue rows so its NAME is free again. Leaves the folder alone."""
    root = resolve_goals_root(args.root)
    goal_dir = resolve_goal_dir(root, args.goal_name)
    goal = args.goal_name
    prefix = _ignite_bin(getattr(args, "ignite_bin", None))

    # ── Which rows belong to this goal? TWO paths, and the difference is not cosmetic ──────────
    # EXACT (the folder is still here): the goal's own `taskforce.csv` is the same list
    # `seedTaskforce` composed the ids from, so `seat-<goal>-<seat>` is reconstructed, never
    # guessed. This is why teardown is meant to run BEFORE the folder is deleted.
    #
    # PREFIX-SCAN (the folder is already gone): there is nothing left to read, so the ids are
    # matched by name. ⚠ THIS IS THE UNSAFE PATH AND IT IS GATED FOR A MEASURED REASON — a goal
    # name can be a PREFIX of another goal's name, and this box carries a live pair today
    # (`throwaway-0811-settle` / `throwaway-0811-settle-kill`), so `seat-throwaway-0811-settle-`
    # matches the OTHER goal's seat rows. The owner ruling (2026-08-12) is that the matches are
    # PRINTED and confirmed rather than deleted on trust, and the shadow warning below names the
    # collision outright instead of leaving it for a tired reader to spot in a list.
    tf_path = goal_dir / "taskforce.csv"
    shadowed: list[str] = []
    excluded: list[str] = []
    # ONE catalogue read, reused by both paths below and by the presence check — a second read
    # would be a second snapshot, and the two could disagree about a row minted between them.
    catalogue = {r["job_id"]: r for r in
                 (_ignite_result(_ignite(prefix, "inspect", "jobs"), "inspect jobs").get("rows") or [])}
    if tf_path.is_file():
        # The EXACT path needs no collision handling at all: every id is composed from THIS goal's
        # own seat registry, so another goal's row can never enter the set in the first place.
        source = "taskforce"
        seats = [(r.get("seat") or "").strip() for r in read_csv(tf_path)]
        wanted = [f"{goal}{_WORKFLOW_START_SUFFIX}"] + [f"seat-{goal}-{s}" for s in seats if s]
    else:
        source = "prefix-scan"
        if goal_dir.is_dir():
            raise Refusal(
                f"{tf_path}: absent, but {goal_dir} still exists. Teardown reads the goal's own "
                "seat registry to compose exact job ids; without it the only alternative is a "
                "name-prefix match, which this verb will not do while the folder is there to be "
                "repaired. Restore taskforce.csv, or delete the folder and re-run to get the "
                "confirm-first orphan path.", "registry-absent")
        seat_prefix = f"seat-{goal}-"
        matched = sorted(j for j in catalogue
                         if j == f"{goal}{_WORKFLOW_START_SUFFIX}" or j.startswith(seat_prefix))
        # ── THE PREFIX COLLISION, EXCLUDED rather than merely warned about ────────────────────
        # A goal name can be a PREFIX of another goal's name — this box carries a live pair
        # (`throwaway-0811-settle` / `throwaway-0811-settle-kill`) — so `seat-throwaway-0811-
        # settle-` matches the OTHER goal's seat rows and the sweep would delete them.
        #
        # ⚠ THIS WAS A REFUSAL GATED ON `not args.yes` AND THAT WAS A DEFECT, caught by
        # `probes/probe-goal-teardown.js` on its first run: `--yes` is the operator saying "the
        # orphan list is right", and it was ALSO waiving a completely different and stronger
        # hazard, so `teardown orphan --yes` silently purged `orphan-kill`'s seat row. A guard a
        # caller can switch off with a flag meant for something else is not a guard.
        #
        # Excluding is better than refusing on both counts: the sweep becomes CORRECT rather than
        # merely blocked, and there is no flag interaction left to get wrong. What it CANNOT see
        # is a shadowing goal whose folder is ALSO gone — nothing in `seat-<goal>-<seat>` says
        # where the goal name ends (seat names carry `-` too: `seat-meeting-digest-plan-check-
        # edges`), so that case is genuinely undecidable from the data and is what the printed
        # confirm-first list below is for.
        shadowed = sorted(p.name for p in root.iterdir()
                          if p.is_dir() and p.name.startswith(f"{goal}-"))
        theirs = {j for s in shadowed for j in matched
                  if j == f"{s}{_WORKFLOW_START_SUFFIX}" or j.startswith(f"seat-{s}-")}
        wanted = [j for j in matched if j not in theirs]
        excluded = sorted(theirs)

    # Absent is NORMAL, not an error: a seat row is only registered once the goal is first seeded,
    # so a goal that never ran has the workflow-start row and nothing else.
    present = [j for j in wanted if j in catalogue]
    absent = [j for j in wanted if j not in catalogue]

    queue_rows = _ignite_result(_ignite(prefix, "inspect", "queue"), "inspect queue").get("rows") or []
    doomed_queue = [q for q in queue_rows if q.get("job_id") in set(present)]

    # ── The live-turn gate, checked for the WHOLE set before anything is touched ───────────────
    # The store refuses a purge with a live execution anyway; asking here first is what makes the
    # refusal ATOMIC. Discovering it mid-loop would leave some rows purged, some disabled and some
    # untouched — a half-torn-down goal is harder to reason about than an untouched one.
    live: list[dict] = []
    for status in _LIVE_STATUSES:
        for row in (_ignite_result(_ignite(prefix, "inspect", "executions", "--status", status),
                                   f"inspect executions --status {status}").get("rows") or []):
            if row.get("job_id") in set(present):
                live.append({"exec_id": row.get("exec_id"), "job_id": row.get("job_id"),
                             "status": status})
    if live:
        named = ", ".join(f"{r['job_id']} (exec {r['exec_id']}, {r['status']})" for r in live)
        raise Refusal(
            f"{len(live)} execution(s) of this goal are still running: {named}. Nothing was "
            "changed — a teardown does not kill live work. Let them finish, or "
            "`ignite kill <session-id>` them, then re-run.", "live-executions")

    plan = {"goal": goal, "source": source, "purge": present, "not_registered": absent,
            "remove_queue_rows": [q["queue_id"] for q in doomed_queue],
            "prefix_shadowed_goals": shadowed, "excluded_as_another_goals": excluded}

    # THE confirm-first gate, and the ONLY one — the shadow hazard is handled by EXCLUSION above,
    # never by a second refusal a flag could waive (that interaction was the defect).
    if source == "prefix-scan" and not args.dry_run and not args.yes:
        raise Refusal(
            f"{goal}: the goal folder is gone, so these {len(present)} row(s) were matched by "
            "NAME, not read from the goal's registry:\n  " + ("\n  ".join(present) or "(none)")
            + (f"\n({len(excluded)} row(s) were already excluded as belonging to "
               f"{', '.join(shadowed)}.)" if excluded else "")
            + "\nRe-run with --yes to purge them, or --dry-run to see the full plan.",
            "confirm-required")

    if args.dry_run:
        if args.json:
            print(json.dumps({"ok": True, "dry_run": True, **plan}, indent=2))
        else:
            _print_teardown_plan(plan, goal_dir)
        return 0

    # ── The act, in the ONE order the purge guards admit ──────────────────────────────────────
    # queue rows first (a pending row refuses the purge), then disable, then purge. Never forced:
    # if a step refuses, the refusal is reported against that id and the rest still run — by this
    # point the atomic gate above has already cleared the only failure worth aborting for.
    removed, purged, failed = [], [], []
    for q in doomed_queue:
        env = _ignite(prefix, "remove-job", str(q["queue_id"]))
        (removed if env.get("ok") else failed).append(
            q["queue_id"] if env.get("ok")
            else {"queue_id": q["queue_id"], "error": (env.get("error") or {}).get("message")})
    for job_id in present:
        env = _ignite(prefix, "deregister-job", job_id)
        if not env.get("ok"):
            failed.append({"job_id": job_id, "step": "deregister",
                           "error": (env.get("error") or {}).get("message")})
            continue
        env = _ignite(prefix, "deregister-job", job_id, "--purge")
        if env.get("ok"):
            purged.append(job_id)
        else:
            failed.append({"job_id": job_id, "step": "purge",
                           "error": (env.get("error") or {}).get("message")})

    out = {"ok": not failed, "goal": goal, "source": source, "purged": purged,
           "queue_rows_removed": removed, "not_registered": absent, "failed": failed,
           "goal_dir": str(goal_dir), "goal_dir_exists": goal_dir.is_dir()}
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"teardown {goal}: purged {len(purged)} catalogue row(s)"
              + (f", removed {len(removed)} queued row(s)" if removed else "")
              + (f", {len(absent)} never registered" if absent else ""))
        for j in purged:
            print(f"  purged  {j}")
        for f in failed:
            print(f"  FAILED  {f.get('job_id') or f.get('queue_id')}: {f.get('error')}")
        print(f"  the goal NAME '{goal}' is now free — `ignite register-job` can take its ids again")
        if goal_dir.is_dir():
            print(f"  THE FOLDER IS UNTOUCHED and is yours to remove: {goal_dir}")
    return 1 if failed else 0


def _print_teardown_plan(plan: dict, goal_dir: Path) -> None:
    print(f"teardown {plan['goal']} — DRY RUN, nothing changed  (ids from: {plan['source']})")
    for j in plan["purge"]:
        print(f"  would purge   {j}")
    for q in plan["remove_queue_rows"]:
        print(f"  would remove  queue row {q}")
    for j in plan["not_registered"]:
        print(f"  skip          {j} (never registered)")
    for j in plan["excluded_as_another_goals"]:
        print(f"  EXCLUDED      {j} (belongs to a goal whose name extends this one)")
    if plan["prefix_shadowed_goals"]:
        print(f"  ⚠ '{plan['goal']}' is a name prefix of: {', '.join(plan['prefix_shadowed_goals'])}"
              " — their rows are excluded above. A shadowing goal whose FOLDER IS ALSO GONE cannot"
              " be detected; check the purge list for ids that are not this goal's seats")
    print(f"  the folder would be left alone: {goal_dir}")


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
            goal_name="demo-goal", type="one-shot", due="2026-09-01", lane="console",
            contract=str(contract), **vars(ns)))
        check("scaffold exits 0", rc == 0)
        gd = root / "demo-goal"
        # The nine files a created goal carries, spelled as LITERALS rather than read from
        # ROUTER_FILENAMES/WRITE_IF_SOMETHING — an expectation that reads the constant under test
        # moves with any edit to it and can never go red (7.582; the goal-kind arm below states
        # the same rule for the same reason). The probe carries the content proof; this arm is
        # the selftest's own enumerator staying complete.
        for fname in ("goal.md", "threads.sql", "milestones.csv", "CLAUDE.md", "AGENTS.md",
                      "issues.md", "decisions.md", "doubts.md", "gotchas.md", "ideas.md"):
            check(f"creates {fname}", (gd / fname).is_file())
        # d-s31-planning-workspace-shared-rw: the ONE directory a created goal carries. It is the
        # mountpoint the seat cage's `bind-try:{goalDir}/planning` needs — absent it, every seat
        # silently loses the planning workspace instead of failing to spawn.
        check("creates planning/", (gd / "planning").is_dir())
        idx = list(csv.DictReader((root / "goals.csv").open(encoding="utf-8")))
        check("goals.csv carries the row", len(idx) == 1 and idx[0]["name"] == "demo-goal",
              str(idx))
        check("status is briefed", idx and idx[0]["status"] == "briefed")

        # 7.136: a goal born through scaffold carries a milestones.csv the lint gate accepts.
        # The header is spelled as a LITERAL for the same reason the file list above is: an
        # expectation that reads the writer's own argument can never go red.
        ms_text = ((gd / "milestones.csv").read_text(encoding="utf-8")
                   if (gd / "milestones.csv").is_file() else None)
        check("scaffold writes a header-only milestones.csv",
              ms_text == "milestone-id,name,status\n", repr(ms_text))
        check("a freshly scaffolded goal raises NO milestones finding",
              not any(i["check"] == "milestones.csv parses"
                      for i in lint_goal(root, "demo-goal").items),
              str([i for i in lint_goal(root, "demo-goal").items
                   if i["check"] == "milestones.csv parses"]))

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
            lane="console", contract=str(contract), **vars(ns)))
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
        # Every row names a lane, so each arm refuses for ITS OWN reason: the 7.777 lane gate sits
        # ahead of the create-only check, and an arm that omitted the flag would go on passing
        # while testing nothing but the lane gate.
        for label, kwargs in (
            ("re-scaffold refused (create-only)",
             dict(goal_name="demo-goal", type="one-shot", due=None, lane="console",
                  contract=str(contract))),
            ("bad name refused",
             dict(goal_name="Bad_Name", type="one-shot", due=None, lane="console",
                  contract=str(contract))),
            ("bad type refused",
             dict(goal_name="other-goal", type="nonsense", due=None, lane="console",
                  contract=str(contract))),
            ("bad kind refused",
             dict(goal_name="other-goal", type="one-shot", kind="nonsense", due=None,
                  lane="console", contract=str(contract))),
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
                    goal_name="contract-goal", type="one-shot", due=None, lane="console",
                    contract=str(bad), **vars(ns)))
                check(arm, False, "did not refuse")
            except Refusal:
                check(arm, True)
            except OSError as exc:
                check(arm, False, f"G-118: a raw {type(exc).__name__} escaped as a crash")

        # The G-117 run-ordering arm is DELETED WITH ITS SUBJECT (7.607 E2a): it exercised
        # `current_run_dir`'s numerically-highest-run fallback, and there is no run folder left
        # to order. Recorded here rather than silently dropped — the defect it guarded
        # (a lexicographic sort returning `run-9` while `run-11` existed) cannot recur in a
        # layout with no numbered compartments.

        print("lint")
        f = lint_goal(root, "demo-goal")
        check("lint finds the unstaffed goal (no taskforce)", bool(f))
        f2 = lint_goal(root, "no-such-goal")
        check("lint refuses an absent goal", bool(f2))

        # name/layout violation: folder and goal.md disagree
        bad = root / "mismatch-goal"
        bad.mkdir()
        (bad / "goal.md").write_text(
            "---\nname: something-else\ncreation-date: 2026-01-01\ntype: one-shot\n"
            "status: briefed\n---\n\ncontract\n", encoding="utf-8")
        (bad / "decisions.md").write_text("x\n", encoding="utf-8")
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

        # 7.607 E2a — the plan is GOAL-DIRECT: no run folder, no register row. The goal dir
        # itself carries taskforce.csv / milestones.csv / seats/.
        (gd / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,w-demo,,claude,claude-opus-5,medium,50,m1\n", encoding="utf-8")
        write_csv(gd / "milestones.csv", ["milestone-id", "name", "status"],
                  [{"milestone-id": "m1", "name": "prove it", "status": "pending"}])

        mns = argparse.Namespace(root=str(root), json=False, goal_name="demo-goal",
                                 catalog_root=str(tmp / "catalog"), force=False)
        rc = cmd_materialize(argparse.Namespace(dry_run=True, **vars(mns)))
        check("materialize --dry-run exits 0", rc == 0)
        check("dry-run wrote no seat folder", not (gd / "seats").exists())

        rc = cmd_materialize(argparse.Namespace(dry_run=False, **vars(mns)))
        check("materialize exits 0", rc == 0)
        seat_md = gd / "seats" / "w-demo" / "seat.md"
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

        # ---- the orphan-seat-folder control (7.98). RED ARM: the check above is the
        # negative half (a fully materialized goal names NO orphan), this is the positive
        # half — delete the folder sweep in `lint_goal` and this arm reds, because the
        # row loop walks rows and can never reach a folder no row names.
        print("lint names an orphan seat folder")
        orphan = gd / "seats" / "ghost-seat"
        orphan.mkdir(parents=True)
        (orphan / "seat.md").write_text("---\nseat: ghost-seat\n---\n\nx\n", encoding="utf-8")
        f4b = lint_goal(root, "demo-goal")
        check("lint names a seat folder with no taskforce row",
              any(i["check"] == "seat folder resolves to a taskforce row"
                  and "ghost-seat" in i["reason"] for i in f4b.items),
              json.dumps(f4b.items, indent=2))
        (orphan / "seat.md").unlink()
        orphan.rmdir()
        check("removing the orphan folder restores a clean lint",
              not bool(lint_goal(root, "demo-goal")))

        print("lint catches a cycle")
        (gd / "taskforce.csv").write_text(
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
        tf = gd / "taskforce.csv"
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
              (gd / "seats" / "w-demo" / "seat.md").is_file()
              and (gd / "seats" / "p-demo" / "seat.md").is_file())

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
        pass_dir = gd / "planning" / "pass-demo"
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

        print("d-prompt-task-files pools (flat prompt/task files, no csv catalogs)")
        pc = tmp / "poolcat" / "pcomp"
        (pc / "prompts").mkdir(parents=True)
        (pc / "tasks").mkdir(parents=True)
        (pc / "seats.csv").write_text(
            "seat-id,prompt-id,task-id,staffing-hints,description\n"
            "ps,pp,pt,,a pool seat\n", encoding="utf-8")
        (pc / "prompts" / "pp.md").write_text(
            "---\nid: pp\ndescription: pool prompt\n"
            "human-interactive: yes\nfallback: block-and-queue\n---\n\n"
            "<role>\nrole body\n</role>\n\n"
            "<permissions>\nRead: everything\n</permissions>\n", encoding="utf-8")
        (pc / "tasks" / "pt.md").write_text(
            "---\nid: pt\ndescription: pool task\ncapabilities: [cc]\n---\n\n"
            "<task-goal>\ngoal body\n</task-goal>\n", encoding="utf-8")
        # The transitional whole-file CARD: same folder, no kind-named section.
        (pc / "prompts" / "card.md").write_text(
            "---\nid: card\nexposes:\n  skill: [x]\n---\n\nprose only\n",
            encoding="utf-8")
        s_c, p_c, t_c = load_catalogs(tmp / "poolcat")
        check("a flat prompt/task file loads as a catalog row",
              sorted(p_c) == ["pp"] and sorted(t_c) == ["pt"],
              f"{sorted(p_c)} {sorted(t_c)}")
        check("a whole-file CARD (no kind-named section) is NOT a definition",
              "card" not in p_c)
        check("flat pool files do NOT index as cognitive units",
              index_units(tmp / "poolcat") == {})
        asm = assemble_seat("ps", {}, s_c, p_c, t_c, {})
        afm = yaml.safe_load(FRONTMATTER_RE.match(asm).group(1))
        check("human-interactive + fallback reach the assembled frontmatter",
              afm.get("human-interactive") is True
              and afm.get("fallback") == "block-and-queue", str(afm))
        check("a declared capability is carried, never dropped",
              afm.get("capabilities") == ["cc"], str(afm))
        check("the file's kind-named sections ARE the body, verbatim",
              "<role>\nrole body\n</role>" in asm
              and "<task-goal>\ngoal body\n</task-goal>" in asm, asm)
        # THE EMITTED SPELLING IS PART OF THE CONTRACT, not cosmetics. The consumer
        # (bus-ferry.js seatIsHumanInteractive) regex-matches the RAW frontmatter line and
        # lowercase-compares the capture to yes/true. `yaml.safe_dump` renders the STRING
        # "yes" as `'yes'` — quotes included — which that regex captures and rejects, so a
        # seat that IS human-interactive reads as false with no refusal anywhere. The literal
        # is spelled out here rather than derived, so this row cannot move with the code.
        check("the emitted line is the BARE token the consumer's regex needs",
              "\nhuman-interactive: true\n" in asm,
              repr([l for l in asm.split("\n") if "human-interactive" in l]))
        # `permissions` reaches the lint through the BODY here — a pool seat has no
        # frontmatter refs at all, and asking only the frontmatter marked 16 of 16 planning
        # seats permission-less while their bodies said otherwise.
        check("SECTION_RE finds the <permissions> section the lint falls back to",
              any(m.group(1) == "permissions"
                  for m in SECTION_RE.finditer(asm)), asm[:200])
        # …AND THE LINT ITSELF MUST ACCEPT IT. Asserting SECTION_RE alone is vacuous: it
        # passes whether or not `permissions well-formed` consults the body. This arm drives
        # lint_goal over a real pool-assembled seat.md, which is where 16 of 16 planning
        # seats were failing. Only the ONE check is asserted — other findings (milestones,
        # bindings) belong to the fixture, not to this question.
        cmd_scaffold(argparse.Namespace(
            root=str(root), json=False, goal_name="pool-goal", type="one-shot",
            due=None, kind=None, lane="console", contract=str(contract), dry_run=False))
        pg = root / "pool-goal"
        (pg / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,ps,,claude,claude-opus-5,medium,50,m1\n", encoding="utf-8")
        (pg / "seats" / "ps").mkdir(parents=True, exist_ok=True)
        (pg / "seats" / "ps" / "seat.md").write_text(
            "---\nseat: ps\nharness: claude\nmodel: claude-opus-5\n---\n" + asm.split("---\n", 2)[2],
            encoding="utf-8")
        pool_lint = lint_goal(root, "pool-goal").items
        check("a POOL-assembled seat passes `permissions well-formed` (body fallback)",
              not any(i["check"] == "permissions well-formed" for i in pool_lint),
              json.dumps([i for i in pool_lint if i["check"] == "permissions well-formed"]))
        check("…and its pass-through keys raise NO dangling-ref finding",
              not any(i["check"] == "cognitive-unit reference resolves" for i in pool_lint),
              json.dumps([i for i in pool_lint
                          if i["check"] == "cognitive-unit reference resolves"]))
        # RED CONTROL, same lint, same call: a seat with NEITHER a permissions ref NOR a
        # <permissions> section must STILL be caught. Without this the arm above would pass
        # if the check were simply deleted.
        (pg / "seats" / "ps" / "seat.md").write_text(
            "---\nseat: ps\nharness: claude\nmodel: claude-opus-5\n---\n\n"
            "<role>\nno permissions anywhere\n</role>\n", encoding="utf-8")
        check("red control: a seat with no permissions ANYWHERE is still caught",
              any(i["check"] == "permissions well-formed"
                  for i in lint_goal(root, "pool-goal").items))

        # Every pass-through must be OUT of the ref grammar's reach: `fallback`,
        # `capabilities` and `context` values are token-shaped, so each one false-positived
        # as a dangling cognitive-unit ref before it was excluded.
        for key in ("human-interactive", "fallback", "capabilities", "context"):
            check(f"`{key}` is excluded from the unit-ref grammar",
                  key in LINT_NON_REF_KEYS)

        (pc / "prompts" / "pp.md").write_text(
            "---\nid: pp\ndescription: pool prompt\nhuman-interactive: yes\n---\n\n"
            "<role>\nrole body\n</role>\n", encoding="utf-8")
        try:
            s2, p2, t2 = load_catalogs(tmp / "poolcat")
            assemble_seat("ps", {}, s2, p2, t2, {})
            check("human-interactive without a fallback REFUSES", False,
                  "no Refusal raised")
        except Refusal as exc:
            check("human-interactive without a fallback REFUSES",
                  "fallback" in str(exc), str(exc))
        # RED ARM for the canon check: an uncanonical value reads FALSE at the consumer
        # with no refusal on any path, so the refusal has to happen here or nowhere.
        (pc / "prompts" / "pp.md").write_text(
            "---\nid: pp\ndescription: pool prompt\nhuman-interactive: maybe\n"
            "fallback: block-and-queue\n---\n\n"
            "<role>\nrole body\n</role>\n", encoding="utf-8")
        try:
            s3, p3, t3 = load_catalogs(tmp / "poolcat")
            assemble_seat("ps", {}, s3, p3, t3, {})
            check("an UNCANONICAL human-interactive value REFUSES", False,
                  "no Refusal raised — 'maybe' would read FALSE in silence")
        except Refusal as exc:
            check("an UNCANONICAL human-interactive value REFUSES",
                  "canonical" in str(exc), str(exc))
        # GREEN CONTROL for the same check: an explicit `no` is canonical, needs no
        # fallback, and emits nothing — without this the arm above would also pass if the
        # check simply refused everything.
        (pc / "prompts" / "pp.md").write_text(
            "---\nid: pp\ndescription: pool prompt\nhuman-interactive: no\n---\n\n"
            "<role>\nrole body\n</role>\n", encoding="utf-8")
        s4, p4, t4 = load_catalogs(tmp / "poolcat")
        asm4 = assemble_seat("ps", {}, s4, p4, t4, {})
        check("an explicit `no` is canonical, needs no fallback, and emits nothing",
              "human-interactive" not in FRONTMATTER_RE.match(asm4).group(1))

        print("reindex")
        rc = cmd_reindex(argparse.Namespace(root=str(root), json=False))
        check("reindex exits 0", rc == 0)
        idx2 = list(csv.DictReader((root / "goals.csv").open(encoding="utf-8")))
        # 6 = demo-goal + kinded-goal + legacy-goal + badkind-goal + mismatch-goal + pool-goal
        # (the d-prompt-task-files lint fixture). The count is spelled out rather than derived
        # from the tree, because deriving it from the same directory listing the projection
        # walks would pass whatever the projection did.
        check("reindex projects every goal", len(idx2) == 6, str(len(idx2)))
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

        # ── pause / resume / dag / add-seat (issue S-33) ──────────────────────────────────────
        #
        # Its own goals root, deliberately: the reindex arms above count goals, and a fixture
        # added to `root` would make that count a moving target.
        import contextlib

        print("pause / resume")
        s33 = tmp / "s33" / ".rbtv" / "goals"
        s33.mkdir(parents=True)
        live = s33 / "live-goal"
        live.mkdir()

        def _ns(**kw):
            base = dict(root=str(s33), json=False, goal_name="live-goal")
            base.update(kw)
            return argparse.Namespace(**base)

        def _code(fn, ns):
            """The refusal CODE, or None when the call did not refuse. Every gate arm below
            asserts on this rather than on message text — prose is edited, a code is a
            contract, and an arm keyed on prose goes green the day someone rewords it."""
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    fn(ns)
                return None
            except Refusal as exc:
                return getattr(exc, "code", None)

        # BYTE-EXACT ROUND TRIP is the whole promise: whatever the marker said must come back
        # identical, or a resume silently changes which lane the goal is on.
        original = "daemon\n"
        (live / LANE_FILE).write_text(original, encoding="utf-8", newline="")
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_pause(_ns())
        check("pause stashes the marker behind `paused `",
              (live / LANE_FILE).read_text(encoding="utf-8") == "paused daemon\n",
              repr((live / LANE_FILE).read_text(encoding="utf-8")))
        check("a paused marker reads as CONSOLE to the unchanged lane reader",
              read_lane(live) == ("console", False), str(read_lane(live)))
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_pause(_ns())
        check("pause is IDEMPOTENT — a second pause does not double the prefix",
              (live / LANE_FILE).read_text(encoding="utf-8") == "paused daemon\n",
              repr((live / LANE_FILE).read_text(encoding="utf-8")))
        check("`lane --set` REFUSES while paused (the stash is protected)",
              _code(cmd_lane, _ns(set="console")) == "lane-paused")
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_resume(_ns())
        check("resume round-trips the marker BYTE-EXACTLY",
              (live / LANE_FILE).read_text(encoding="utf-8") == original,
              repr((live / LANE_FILE).read_text(encoding="utf-8")))
        check("resume on a NOT-paused goal refuses `not-paused`",
              _code(cmd_resume, _ns()) == "not-paused")
        # The absent-file branch: `console` is the previous text a resume must restore.
        (live / LANE_FILE).unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_pause(_ns())
        check("pausing a goal with NO marker stashes `console`",
              (live / LANE_FILE).read_text(encoding="utf-8") == "paused console\n",
              repr((live / LANE_FILE).read_text(encoding="utf-8")))

        print("splice (pure)")
        TF_HEAD = ["taskforce-id", "seat", "after", "harness", "model", "effort",
                   "ctx-refresh", "milestone-id"]

        def _tf(*rows):
            return "\n".join([render_csv_line(TF_HEAD)]
                             + [render_csv_line(["tf-1", s, a, "claude", "claude-opus-5",
                                                 "medium", "50", "m1"]) for s, a in rows]) + "\n"

        base_text = _tf(("a", ""), ("b", "a"), ("c", "a,b"), ("d", "a[gate=b]"), ("new", "a"))
        spliced, rewrites = splice_new_seat(base_text, "new", ["a"], ["b"])
        check("splice re-parents the --before row onto the new seat",
              rewrites == [{"seat": "b", "old_after": "a", "new_after": "new"}], str(rewrites))
        untouched_before = [ln for ln in base_text.split("\n") if not ln.startswith("tf-1,b,")]
        untouched_after = [ln for ln in spliced.split("\n") if not ln.startswith("tf-1,b,")]
        check("splice leaves every OTHER line byte-unchanged",
              untouched_before == untouched_after,
              str([x for x in untouched_after if x not in untouched_before]))
        # GUARD PRESERVATION: `a[gate=b]` with BOTH a and b in the --after set. The member id
        # outside the brackets is substituted; the `b` INSIDE the guard is a condition, not a
        # member, and substituting it would rewrite what the edge tests for.
        _s2, rw2 = splice_new_seat(base_text, "new", ["a", "b"], ["d"])
        check("a `[key=value]` guard span survives the splice untouched",
              rw2[0]["new_after"] == "new[gate=b]", str(rw2))
        # ALTERNATE + DEDUPE: `a,b` with both replaced must collapse to ONE member, not `new,new`.
        _s3, rw3 = splice_new_seat(base_text, "new", ["a", "b"], ["c"])
        check("two replaced members collapse to one (order-preserving dedupe)",
              rw3[0]["new_after"] == "new", str(rw3))
        check("--before naming no row refuses `splice-before-unknown`",
              _code(lambda _: splice_new_seat(base_text, "new", ["a"], ["nope"]), None)
              == "splice-before-unknown")
        check("a --before row sharing no member with --after refuses `splice-not-an-insertion`",
              _code(lambda _: splice_new_seat(base_text, "new", ["b"], ["b"]), None)
              == "splice-not-an-insertion")
        check("a new seat with no registry row refuses `splice-no-row`",
              _code(lambda _: splice_new_seat(base_text, "ghost", ["a"], ["b"]), None)
              == "splice-no-row")
        # CANONICAL-FORM GUARD: an unnecessarily quoted cell re-renders differently, so the
        # splice would silently reformat the whole file on its way through. Refused.
        noncanon = base_text.replace('tf-1,a,', 'tf-1,"a",', 1)
        check("a non-canonical registry refuses `taskforce-noncanonical`",
              _code(lambda _: splice_new_seat(noncanon, "new", ["a"], ["b"]), None)
              == "taskforce-noncanonical")
        # CRLF names ITSELF rather than surfacing as a per-line "repair the registry".
        check("a CRLF registry refuses `taskforce-noncanonical` NAMING the line endings",
              _code(lambda _: splice_new_seat(base_text.replace("\n", "\r\n"), "new",
                                              ["a"], ["b"]), None) == "taskforce-noncanonical")
        _crlf_msg = ""
        try:
            splice_new_seat(base_text.replace("\n", "\r\n"), "new", ["a"], ["b"])
        except Refusal as exc:
            _crlf_msg = str(exc)
        check("…and the message says CRLF, not just 'repair the registry'",
              "CRLF" in _crlf_msg and "LF-only" in _crlf_msg, _crlf_msg[:200])

        # THE PREFLIGHT — the same three answers, computable with NO row for the new seat, which
        # is what lets the gate block fire them before the mint.
        premint = _tf(("a", ""), ("b", "a"), ("c", "a,b"), ("d", "a[gate=b]"))   # no `new` row
        check("preflight refuses `splice-before-unknown` with no row for the new seat",
              _code(lambda _: _preflight_splice(premint, ["a"], ["nope"]), None)
              == "splice-before-unknown")
        check("preflight refuses `splice-not-an-insertion` with no row for the new seat",
              _code(lambda _: _preflight_splice(premint, ["b"], ["b"]), None)
              == "splice-not-an-insertion")
        check("preflight refuses `taskforce-noncanonical` with no row for the new seat",
              _code(lambda _: _preflight_splice(
                  premint.replace('tf-1,a,', 'tf-1,"a",', 1), ["a"], ["b"]), None)
              == "taskforce-noncanonical")
        check("preflight PASSES the legal splice it will later perform — it never refuses "
              "`splice-no-row`, which is the post-mint baseline's alone",
              _code(lambda _: _preflight_splice(premint, ["a"], ["b"]), None) is None)

        print("add-seat gates + dag")
        (live / "taskforce.csv").write_text(base_text, encoding="utf-8", newline="")
        sheet = tmp / "bindings.json"
        sheet.write_text(json.dumps({"defaults": {"harness": "claude"},
                                     "seats": {"new": {"model": "claude-opus-5"}}}),
                         encoding="utf-8")

        def _add(**kw):
            base = dict(seat="new", after="a", before="b", bindings=str(sheet),
                        catalog_root=str(tmp), splice_only=True,
                        allow_daemon_complex_cell=False, allow_open_execution=False,
                        dry_run=False)
            base.update(kw)
            return _ns(**base)

        (live / LANE_FILE).write_text("console\n", encoding="utf-8", newline="")
        check("add-seat on an UNPAUSED goal refuses `goal-not-paused`",
              _code(cmd_add_seat, _add()) == "goal-not-paused")
        (live / LANE_FILE).write_text("paused console\n", encoding="utf-8", newline="")
        (live / EXECUTIONS_FILE).write_text(
            "seat,session-id,lane,started,ended,outcome\n"
            "a,s1,attached,t0,,\n", encoding="utf-8", newline="")
        check("an OPEN execution row refuses `goal-not-quiescent`",
              _code(cmd_add_seat, _add()) == "goal-not-quiescent")
        # THE DEADLOCK ESCAPE. A killed run's row is never closed by anything, so without a flag
        # this refusal is permanent. The refusal NAMES the row so the operator can judge it.
        _q = ""
        try:
            cmd_add_seat(_add())
        except Refusal as exc:
            _q = str(exc)
        check("…and the refusal names the offending seat, session and start",
              "seat a" in _q and "session s1" in _q and "started t0" in _q, _q[:250])
        (live / "taskforce.csv").write_text(base_text, encoding="utf-8", newline="")
        check("--allow-open-execution is the deliberate escape past a never-closing row",
              _code(cmd_add_seat, _add(allow_open_execution=True)) is None)
        # A SUPERSEDED open row is NOT live: the seat's LAST row decides, as the engine reads it.
        (live / "taskforce.csv").write_text(base_text, encoding="utf-8", newline="")
        (live / EXECUTIONS_FILE).write_text(
            "seat,session-id,lane,started,ended,outcome\n"
            "a,s1,attached,t0,,\n"
            "a,s2,attached,t1,t2,done\n", encoding="utf-8", newline="")
        check("a seat whose LAST row is stamped is quiescent even with an earlier OPEN row",
              _code(cmd_add_seat, _add()) is None)
        check("…and `seat_states` reports it `done`, not `open`",
              seat_states(live)["a"] == {"state": "done", "outcome": "done", "runs": 2},
              str(seat_states(live)))
        (live / "taskforce.csv").write_text(base_text, encoding="utf-8", newline="")
        (live / EXECUTIONS_FILE).write_text(
            "seat,session-id,lane,started,ended,outcome\n"
            "b,s1,attached,t0,t1,done\n", encoding="utf-8", newline="")
        check("a --before seat that has already RUN refuses `splice-target-has-run`",
              _code(cmd_add_seat, _add()) == "splice-target-has-run")
        (live / EXECUTIONS_FILE).write_text(
            "seat,session-id,lane,started,ended,outcome\n"
            "a,s1,attached,t0,t1,done\n", encoding="utf-8", newline="")
        (live / ATTACHED_RUN_LOCK).write_text("pid\n", encoding="utf-8")
        check("a live attached run refuses `attached-run-live`",
              _code(cmd_add_seat, _add()) == "attached-run-live")
        (live / ATTACHED_RUN_LOCK).unlink()
        check("a seat absent from the shared sheet refuses `bindings-missing-seat`",
              _code(cmd_add_seat, _add(seat="absent")) == "bindings-missing-seat")
        # daemon-complex-cell: --before c carries `a,b` (multi-member) and the STASHED lane is
        # `daemon`. Refused on the real run; the flag is the deliberate acceptance.
        (live / LANE_FILE).write_text("paused daemon\n", encoding="utf-8",
                                      newline="")
        check("a multi-member cell + a stashed DAEMON lane refuses `daemon-complex-cell`",
              _code(cmd_add_seat, _add(before="c", after="a,b")) == "daemon-complex-cell")
        check("--allow-daemon-complex-cell is the deliberate escape",
              _code(cmd_add_seat, _add(before="c", after="a,b",
                                       allow_daemon_complex_cell=True)) is None)
        # …and the console lane never trips it at all (the green discriminator: without this
        # the arm above would also pass if the gate simply refused every complex cell).
        (live / "taskforce.csv").write_text(base_text, encoding="utf-8", newline="")
        (live / LANE_FILE).write_text("paused console\n", encoding="utf-8", newline="")
        check("the same complex cell on a stashed CONSOLE lane is NOT refused",
              _code(cmd_add_seat, _add(before="c", after="a,b")) is None)

        (live / "taskforce.csv").write_text(base_text, encoding="utf-8", newline="")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_add_seat(_add(json=True))
        payload = json.loads(buf.getvalue())
        check("add-seat --splice-only writes the spliced registry", rc == 0 and payload["ok"])
        check("…and the registry now names the new seat as b's predecessor",
              "tf-1,b,new," in (live / "taskforce.csv").read_text(encoding="utf-8"),
              (live / "taskforce.csv").read_text(encoding="utf-8"))

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_dag(_ns(json=True))
        dag = json.loads(buf.getvalue())
        seats_seen = [n["seat"] for n in dag["nodes"]]
        check("dag exits 0 and lists every registry row", rc == 0 and len(seats_seen) == 5,
              str(seats_seen))
        check("dag orders predecessors before their successors",
              seats_seen.index("a") < seats_seen.index("new") < seats_seen.index("b"),
              str(seats_seen))
        by = {n["seat"]: n for n in dag["nodes"]}
        check("dag derives execution state from executions.csv",
              by["a"]["state"] == "done" and by["a"]["outcome"] == "done"
              and by["c"]["state"] == "never-ran", json.dumps(by["a"]))
        check("dag reports the new seat's predecessors through the after grammar",
              by["b"]["predecessors"] == ["new"], str(by["b"]))

        # ---- IPH-11: the retry threshold -------------------------------------------------
        # The fixture is the HARD milestones.csv, not a tidy one: the second live header shape,
        # a quoted multi-clause `done-when`, an embedded doubled quote, and CRLF endings. A csv
        # round trip re-renders every one of those to satisfy the one cell being written, which
        # is the failure this verb's line-precise edit exists to make impossible.
        print("retry-threshold")
        rt = s33 / "rt-goal"
        (rt / "seats").mkdir(parents=True)
        MS_CRLF = (
            b'milestone-id,title,done-when,state\r\n'
            b'm1,First,"a, quoted; multi-clause done-when with an ""inner"" quote",open\r\n'
            b'm2,Second,"another, quoted clause",open\r\n')
        (rt / MILESTONES_FILE).write_bytes(MS_CRLF)

        def _rt(**kw):
            base = dict(root=str(s33), json=False, goal_name="rt-goal",
                        milestone=None, unset=False)
            base.setdefault("set", None)
            base.update(kw)
            ns_rt = argparse.Namespace(**{k: v for k, v in base.items() if k != "set"})
            setattr(ns_rt, "set", base["set"])
            return ns_rt

        def _rt_show(**kw):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cmd_retry_threshold(_rt(json=True, **kw))
            return json.loads(buf.getvalue())

        check("nothing configured resolves the built-in default, source `default`",
              _rt_show()["threshold"] == RETRY_THRESHOLD_DEFAULT
              and _rt_show()["source"] == "default"
              and _rt_show()["path"] is None)

        # THE CROSS-CHECK, not a bridge: coord.py owns the ENFORCED ladder and is not importable
        # from an arbitrary cwd, so the three literals are pinned against its own source. A
        # rename there turns this arm red instead of silently splitting the authority in two.
        _coord_lits = _module_level_literals(coord_source_path().read_text(encoding="utf-8"))
        check("the ladder's three literals match coord.py's enforcing copy",
              _coord_lits.get("RETRY_THRESHOLD_DEFAULT") == RETRY_THRESHOLD_DEFAULT
              and _coord_lits.get("RETRY_THRESHOLD_FILE") == RETRY_THRESHOLD_FILE
              and _coord_lits.get("RETRY_THRESHOLD_COLUMN") == RETRY_THRESHOLD_COLUMN,
              str({k: v for k, v in _coord_lits.items() if k.startswith("RETRY_")}))

        for bad in ("abc", "0", "-1", "", "2.5"):
            check(f"--set {bad!r} refuses `retry-threshold-invalid` and writes nothing",
                  _code(cmd_retry_threshold, _rt(**{"set": bad})) == "retry-threshold-invalid"
                  and not (rt / RETRY_THRESHOLD_FILE).exists()
                  and (rt / MILESTONES_FILE).read_bytes() == MS_CRLF)
        check("--set on an unknown --milestone refuses `milestone-unknown`, writing nothing",
              _code(cmd_retry_threshold,
                    _rt(milestone="m9", **{"set": "3"})) == "milestone-unknown"
              and (rt / MILESTONES_FILE).read_bytes() == MS_CRLF)
        check("--set and --unset together refuse `set-and-unset`",
              _code(cmd_retry_threshold, _rt(unset=True, **{"set": "3"})) == "set-and-unset")

        check("--set 3 writes the per-goal default and show sources it `goal`",
              _code(cmd_retry_threshold, _rt(**{"set": "3"})) is None
              and (rt / RETRY_THRESHOLD_FILE).read_text(encoding="utf-8") == "3\n"
              and _rt_show()["threshold"] == 3 and _rt_show()["source"] == "goal")

        # ARM 11 — the line-precise write. Every OTHER byte identical, quoted prose included.
        check("--set --milestone appends the column and leaves every other byte alone",
              _code(cmd_retry_threshold, _rt(milestone="m1", **{"set": "4"})) is None
              and (rt / MILESTONES_FILE).read_bytes() == (
                  b'milestone-id,title,done-when,state,retry-threshold\r\n'
                  b'm1,First,"a, quoted; multi-clause done-when with an ""inner"" quote",'
                  b'open,4\r\n'
                  b'm2,Second,"another, quoted clause",open,\r\n'),
              (rt / MILESTONES_FILE).read_text(encoding="utf-8", newline=""))
        check("the override wins for its own milestone and does NOT leak to its sibling",
              _rt_show(milestone="m1")["threshold"] == 4
              and _rt_show(milestone="m1")["source"] == "milestone"
              and _rt_show(milestone="m2")["threshold"] == 3
              and _rt_show(milestone="m2")["source"] == "goal")

        _rt_before = (rt / MILESTONES_FILE).read_bytes()
        check("a SECOND --set on an existing column rewrites that cell alone",
              _code(cmd_retry_threshold, _rt(milestone="m1", **{"set": "7"})) is None
              and (rt / MILESTONES_FILE).read_bytes()
              == _rt_before.replace(b'open,4\r\n', b'open,7\r\n'),
              (rt / MILESTONES_FILE).read_text(encoding="utf-8", newline=""))
        check("--unset --milestone clears the cell and the goal default answers again",
              _code(cmd_retry_threshold, _rt(milestone="m1", unset=True)) is None
              and _rt_show(milestone="m1")["threshold"] == 3
              and (rt / MILESTONES_FILE).read_bytes()
              == _rt_before.replace(b'open,4\r\n', b'open,\r\n'))
        check("--unset at goal scope removes the file and the default answers",
              _code(cmd_retry_threshold, _rt(unset=True)) is None
              and not (rt / RETRY_THRESHOLD_FILE).exists()
              and _rt_show()["source"] == "default")

        # Owner ruling 11 — the write refuses while a planning pass is OPEN.
        (rt / EXECUTIONS_FILE).write_text(
            "seat,session-id,lane,started,ended,outcome\n"
            "plan-dod-judge,s1,daemon,t0,,\n", encoding="utf-8", newline="")
        _rt_open_before = (rt / MILESTONES_FILE).read_bytes()
        check("--set REFUSES `pass-open` while an execution row is still open, writing nothing",
              _code(cmd_retry_threshold, _rt(**{"set": "5"})) == "pass-open"
              and _code(cmd_retry_threshold,
                        _rt(milestone="m1", **{"set": "5"})) == "pass-open"
              and not (rt / RETRY_THRESHOLD_FILE).exists()
              and (rt / MILESTONES_FILE).read_bytes() == _rt_open_before)
        check("…and SHOW still answers while the pass is open — the gate is on the write only",
              _rt_show()["threshold"] == RETRY_THRESHOLD_DEFAULT)
        (rt / EXECUTIONS_FILE).write_text(
            "seat,session-id,lane,started,ended,outcome\n"
            "plan-dod-judge,s1,daemon,t0,t1,done\n", encoding="utf-8", newline="")
        check("a CLOSED record lets the same --set through — a HALTED goal is exactly when the "
              "owner raises the bar, so the gate must not bar that case",
              _code(cmd_retry_threshold, _rt(**{"set": "5"})) is None
              and _rt_show()["threshold"] == 5)

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
    p.add_argument("--execution-mode", default=EXECUTION_MODE_DEFAULT,
                   choices=list(EXECUTION_MODES),
                   help="the per-goal owner-contact policy written to the goal's "
                        f"{EXECUTION_MODE_FILE} file (default: {EXECUTION_MODE_DEFAULT}, which "
                        "is what an absent file already reads as). The workflow-level default is "
                        "resolved by the request layer and passed here — this verb derives none")
    # NO `required=`/`choices=` on purpose: the gate lives in `cmd_scaffold` (hand-built
    # Namespaces reach it without argparse), and argparse's error text cannot carry the operator
    # wording the refusal there owes the person who typed the command.
    p.add_argument("--lane", default=None,
                   help="which lane runs this goal — `daemon` (the daemon runs it unattended) or "
                        "`console` (you run it when you type `rbtv run`). REQUIRED: a goal born "
                        "without a lane is silently a console goal")
    p.add_argument("--due", default=None)
    p.add_argument("--contract", required=True,
                   help="FILE, or - for stdin: the goal-radius contract prose")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_scaffold)

    p = add_common(sub.add_parser("reindex", help="rebuild goals.csv from every goal.md frontmatter"))
    p.set_defaults(func=cmd_reindex)

    # THE DAEMON'S PICKUP BUTTON (owner ruling d-daemon-lane-button). Read-only with no --set,
    # so `lane <goal>` is also the orientation verb: "which lane is running this right now".
    # Works DAEMON-DOWN by construction — it is a file read and a file write, and that is the
    # whole reason the trigger is a file rather than a gateway intent.
    p = add_common(sub.add_parser(
        "lane",
        help="show or set which lane runs a goal — daemon (the daemon picks it up) or console"))
    p.add_argument("goal_name")
    p.add_argument("--set", default=None, choices=list(LANES),
                   help="assign the goal to a lane. Flipping it MID-GOAL is supported and is the "
                        "point: the execution record makes the other lane skip what this one finished")
    p.set_defaults(func=cmd_lane)

    # The PAUSE pair (issue S-33). `pause` stashes the lane assignment behind a `paused ` prefix
    # both lane readers already resolve to `console`; `resume` hands the exact bytes back.
    p = add_common(sub.add_parser(
        "pause",
        help="stash the lane assignment — nothing NEW is seeded for this goal until `resume`"))
    p.add_argument("goal_name")
    p.set_defaults(func=cmd_pause)

    p = add_common(sub.add_parser(
        "resume", help="unstash the lane assignment a `pause` put away, byte for byte"))
    p.add_argument("goal_name")
    p.set_defaults(func=cmd_resume)

    # Task 7.776 — the operator's one-more-attempt act, in the lane family because it is the same
    # kind of thing: a file in the goal folder that the next pass reads before it seeds.
    p = add_common(sub.add_parser(
        "relaunch",
        help="authorize ONE more attempt at a seat that ended failed — spent by the run it buys"))
    p.add_argument("goal_name")
    p.add_argument("--seat", required=True,
                   help="the seat, by name, exactly as this goal's taskforce.csv spells it")
    p.set_defaults(func=cmd_relaunch)

    # IPH-11 — the escalation bar as CONFIGURATION. Bare, it is read-only: `retry-threshold
    # <goal>` is also the orientation verb ("what will the judge escalate at").
    p = add_common(sub.add_parser(
        "retry-threshold",
        help="show or set the consecutive-FAIL bar the dod-judge escalates to the owner at"))
    p.add_argument("goal_name")
    p.add_argument("--milestone", default=None,
                   help="scope to ONE milestone: show resolves that milestone's ladder, and "
                        "--set writes the `retry-threshold` column of its milestones.csv row "
                        "(line-precisely — every other byte of the file is left alone)")
    p.add_argument("--set", default=None, metavar="N",
                   help="the new threshold, an integer >= 1. The floor is 1, not 0: the gate "
                        "reads `count < bar`, so 0 would escalate on zero FAILs")
    p.add_argument("--unset", action="store_true",
                   help="remove the override at this scope so the next rung answers")
    p.set_defaults(func=cmd_retry_threshold)

    # R6 — the one-shot graph view. Read-only: it opens taskforce.csv, executions.csv and
    # seats/, and joins them so an agent does not have to.
    p = add_common(sub.add_parser(
        "dag", help="the goal's seat graph + each seat's execution state (read-only)"))
    p.add_argument("goal_name")
    p.set_defaults(func=cmd_dag)

    p = add_common(sub.add_parser(
        "add-seat",
        help="grow a PAUSED goal's roster: mint a seat and splice it into the after-graph"))
    p.add_argument("goal_name")
    p.add_argument("--seat", required=True, help="the catalog seat id to mint and splice")
    p.add_argument("--after", required=True,
                   help="comma-separated predecessor seat(s) the new seat waits on "
                        "(an omitted insertion point never defaults to root)")
    p.add_argument("--before", default=None,
                   help="comma-separated successor seat(s) to RE-PARENT onto the new seat. "
                        "Only the members they share with --after are substituted; omit it to "
                        "attach the new seat as a leaf")
    p.add_argument("--bindings", required=True,
                   help="the goal's SHARED bindings sheet (JSON). A one-seat scoped copy is "
                        "written outside the goal folder for the mint and removed after")
    p.add_argument("--catalog-root", required=True,
                   help="root of the component databases the seat definition resolves through")
    p.add_argument("--splice-only", action="store_true",
                   help="skip the mint and splice only — the crash-resume for a run that died "
                        "between minting the seat and rewiring the graph")
    p.add_argument("--allow-daemon-complex-cell", action="store_true",
                   help="accept writing a multi-member or guarded `after` cell on a goal whose "
                        "stashed lane is `daemon` (refused by default)")
    p.add_argument("--allow-open-execution", action="store_true",
                   help="proceed even though a seat's LAST execution row is still open. The "
                        "escape for a KILLED run, whose row nothing will ever close — never for "
                        "a session that is actually alive (refused by default)")
    p.add_argument("--dry-run", action="store_true",
                   help="run every gate and print the local graph around the new seat; "
                        "touch nothing")
    p.set_defaults(func=cmd_add_seat)

    p = add_common(sub.add_parser(
        "teardown",
        help="reclaim a goal's job-catalogue rows so its NAME is free again (NEEDS the daemon up; "
             "leaves the goal folder alone)"))
    p.add_argument("goal_name")
    p.add_argument("--ignite-bin", default=None,
                   help="path to the ignite client (default: this repo's cli/ignite.js under node). "
                        "Auth and gateway address come from the environment the client already "
                        "reads — IGNITE_SENDER_TOKEN and IGNITE_GATEWAY_ADDR / server.json")
    p.add_argument("--yes", action="store_true",
                   help="confirm the ORPHAN path, where the goal folder is already gone and ids "
                        "were matched by NAME rather than read from the goal's own registry. "
                        "Never needed when taskforce.csv is present")
    p.add_argument("--dry-run", action="store_true",
                   help="print the plan — every row that would be purged and every queue row that "
                        "would be removed — and change nothing")
    p.set_defaults(func=cmd_teardown)

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

    p = add_common(sub.add_parser("selftest", help="end-to-end exercise on a throwaway tree"))
    p.set_defaults(func=cmd_selftest)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Refusal as exc:
        code = getattr(exc, "code", None)
        print(f"refused{f' ({code})' if code else ''}: {exc}", file=sys.stderr)
        # A coded refusal is machine-readable under --json — an agent keys on the code, never
        # on the prose. Uncoded refusals keep the stderr-only shape they have always had.
        if code and getattr(args, "json", False):
            print(json.dumps({"ok": False,
                              "refusal": {"code": code, "message": str(exc)}}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
