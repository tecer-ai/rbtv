#!/usr/bin/env python3
"""materialize-seats — materialize a seat or a whole workflow into a goal package.

The command MATERIALIZES seats incrementally into an EXISTING run: it resolves
the added seat set (a seat catalog `seats.csv` row for --seat; a workflow
manifest `<component>/workflows/<W>/<W>.csv` for --workflow), validates the
per-seat executor bindings, and plans three kinds of write in this order — per
seat, its `{package}/seats/<seat>/seat.md` descriptor and then its GUIDANCE
PAIR — `CLAUDE.md` + `AGENTS.md`, one body under each harness's native name
(owner ruling `d-uniform-descriptor-carriage`, 2026-08-12; see
`_SEAT_GUIDANCE_MD` for the stance and why the `agents-md` mirror cannot own
it), and finally `{package}/taskforce.csv` row
appends. It is an ignite-job: argv-only, environment-free, exit codes
0 success / 1 refusal / 2 usage, machine-readable `--json` result, no bus
writes, no messages, no pane — announcing what was materialized is the
CALLER's act, never this command's.

This file carries the dag-03 SKELETON (argument parsing, resolution, refusal
plumbing, JSON result, environment scrub, selftest harness + fixture builder)
plus the dag-04 DESCRIPTOR SURFACE — render_descriptors/emit_seat_descriptors:
the `seat:` (never `id:`) frontmatter schema in its ruled key order
(d-seatmd-keys-dag04-schema — this schema IS the single source of truth for a
materialized seat.md's frontmatter), the mode/ctx-refresh/close fail-closed
rules (F4/F5/F8), the coord.validate_seat whole-batch gate before any write
(F6), the one-shot boot text (F10), the empty-assembly and no-permissions
hard gates, the contract §1 fixed block-kind reorder, and inline
`Reference: <id>@latest` body resolution (d-run3-assembled-shape (i)).
`relays:` is a PASS-THROUGH — emitted when, and only when, the mirror
definition declares it (owner ask A-40 ruled (a),
`d-relays-frontmatter-passthrough`). `relays: <token>` declares that this seat
CARRIES THE RELAY PATH for a role word: it is how an abstract role word
resolves to a concrete seat, so a message addressed to `master` reaches
whichever seat declares `relays: master` (coord.py `inbox_decls` ->
`relay_seats`). The reap exemption is a SECOND, DERIVED consequence of the
same declaration (watch.py builds `door_seats` from it, on the standing ruling
that a seat carrying a relay path to a HUMAN is never closed mechanically), so
dropping the key on materialization would cost BOTH properties. `class:` is
the one key still refused as an input (never emitted).

The dag-05 REGISTRY HALF is landed — render_taskforce_rows/append_taskforce_rows:
the taskforce.csv append in topological order of the added subgraph, the three
pre-write validations (acyclicity of the RESULTING graph via
goal_cli.check_acyclic; every --after member resolves; no status column —
Rules 9/8/14 of the workflow.md DAG-authoring block), the frozen-copy `after`
cells (Rule 13), taskforce-id read from the file (never argv), atomic
read → append → os.replace (never an open-append), and the --force-partial
rows half (byte-match completion of ONLY the missing rows).
The dag-06 CREATE-PACKAGE STEP is landed — plan_package_creation/
create_run_package (d-bootstrap-mechanics-ruled (b)): the surfaces a goal needs
before a seat can check in (seats/, coordination/, header-only taskforce.csv,
the ruled header-only state.csv) are CREATED under the goal folder that passes
the package bar — so the MASTER can materialize at bootstrap, before the team
exists. (7.607 E2b: the package IS the goal folder — design-lock item 8 — so
this step no longer mints a `runs/run-N/` compartment; it completes the goal
folder `rbtv-goal scaffold` minted.) The two CONTENT surfaces
— CLAUDE.md, budget.json — arrive as CALLER-SUPPLIED input files
(--claude-md / --budget-json, byte-copied), per
`d-run3-seeds-from-run2-amended`: run-2's versions as amended by the authored
designs, CARRIED BY THE CALLER (dag-16's bootstrap job). This command never
invents run conventions, never defaults a floor — a missing input REFUSES
loudly (`create-inputs-missing`) naming the input and the remedy. A THIRD,
OPTIONAL surface joins them (7.569): `addressable.csv`, the register that makes
the standing owner door a legal address in a goal nobody has staffed yet.
`--addressable` byte-copies a
caller's register; without it a bootstrap creation DERIVES the rows from the
standing-seat homes whose OWN descriptor declares `addressable: non-member`,
and creates nothing when none does. Optional, not required, deliberately: a
fourth REQUIRED entry would make every caller that does not pass the new flag
— including the ARMED goal-creation loop — start refusing, which is an outage
rather than a build. Creation is
announced in `writes[]` (kind `package-surface`), planned-not-written under
--dry-run, idempotent against an existing package, and COMPLETES a partial
one. A freshly created registry has no taskforce-id to read, so the first
append derives it from the goal's OWN taskforce.csv counter (max existing + 1,
design-lock item 10) — deterministic, never argv (see render_taskforce_rows).

⚠ THE RUN REGISTER IS EXTINGUISHED (7.607 E2b, design-lock item 8). This
command was the ONE writer of `<goal>/runs.csv`'s opening half
(render_run_register / append_run_register_row) and both are DELETED with the
run layer, along with `--run-type`. Its idempotence-on-refire guarantee is
re-stated against the goal-direct creation act — see the constants section.

Bootstrap call shape (the master's one call, d-master-scaffolds-at-bootstrap):
the planning workflow's ENTRY SEATS are DECLARED ROOTS at authoring time
(d-bootstrap-mechanics-ruled (c) — planning.csv's elicitator row carries an
empty, declared `after`), so a bootstrap call passes `--root`, never
`--after`. The bootstrap BINDINGS come from the workflow definition's OWN
staffing hints (clause (d): seats.csv `staffing-hints` / prompts.csv
`staffing-recommendations`, ratified by d-staffing-hints-stand): the CALLER
produces the --bindings JSON from those hints — by hand or via a helper that
emits and prints a bindings file — and this command still reads a file. The
contract stays "bindings arrive as a file"; the command NEVER guesses a
binding. The staffer stage re-binds as usual once it exists.

The dag-07 ACCEPTANCE ROLLUP is landed — ROW_ARMS/rollup_rows in the selftest:
every acceptance row (SK-1..SK-7, SC-1..SC-21, CP-1..CP-8, contract-order,
topo-order, tf-id, creation-partial, AS-2/AS-4) reports ONE line naming both
arms, and the suite exits 0 only when every row passes BOTH arms — a row whose
red arm is missing or failing is a suite failure, never a green (R-6, AS-2).

The plugin/MCP REGISTRATION SURFACE is landed (d-mcp-registration-is-config,
2026-08-08) — render_harness_configs/emit_harness_configs: a component's
exposure.csv row (`method: config`, entry-point → an `mcpServers`-shape
declaration file) materializes per seat as the three supported harnesses'
registration files (`.mcp.json` + `.claude/settings.json` approval flag ·
`.codex/config.toml` `[mcp_servers.*]` · `opencode.json` `"mcp"`), realization
per CMP-12 § config. Derived files, regenerated freely; a broken declaration
refuses pre-write. Acceptance row MCP-1.

The SEAT-EXPOSURE LOADER SURFACE is landed (d-materializer-seat-loaders;
shape owner-ruled 2026-08-09, d-seat-exposes-frontmatter) —
resolve_seat_exposes/render_seat_exposures/emit_seat_exposures: a prompt
file's frontmatter `exposes:` mapping (method -> exposure.csv part-ids,
`<component>/<part-id>` for a sibling component's row) materializes per seat
as thin loaders / verbatim copies for the five seat-authorable methods
(skill, command, rule, hook, sub-agent), realization per CMP-12's matrix;
the validated mapping is also emitted into the descriptor frontmatter, and
rule exposure appends a forced-read preamble to the seat's AGENTS.md. The
manifest stays the one home of the part -> method binding (PRIN-11): a
mismatched group key refuses. Derived files, regenerated freely; every gate
fires pre-write. Acceptance row EXP-1; full spec: the block comment above
resolve_seat_exposes.

Assembly is goal_cli's — `index_units` / `load_catalogs` / `assemble_seat`
imported from the goals-tree tool. ONE assembler; this file must never grow a
local unit emitter (SK-7).

No policy number crosses this boundary (R-10, r-floor-single-source): no RAM
floor, no pane cap, no model default — the bindings file states what to bind.

Selftest: `materialize-seats.py --selftest` materializes ONLY against a
throwaway fixture in tempfile.TemporaryDirectory(); it never points at a real
run.

Ruled command name: `scaffold-seats`. The planning workflow and the rulings
that reach for this tool name it `scaffold-seats` (planning-deprecated — pre-rename
planner-workflow — workflow.md: "scaffold-seats --workflow planning" / "scaffold-seats --seat
planner"); this FILE keeps its own name, and the ruled name is EXPOSED, never
substituted (d-materialize-term keeps the spec token deliberately; run-3
p-the-scaffold-seats-fix-is-NOT-a-text-alignment forbids a rename). Exposure is
a PER-MACHINE symlink, never synced by git — the same form `coordinate` uses
for coord.py, so on a box where nobody has run it the ruled name resolves to
nothing and this paragraph is the only record that it exists:

    # run from THIS file's own directory (ignite/planning); the target must be
    # absolute, because a symlink stores the text it was given
    ln -s "$(pwd)/materialize-seats.py" ~/.local/bin/scaffold-seats
    command -v scaffold-seats   # rc=0 once it resolves

The exec bit and the shebang are already on this file; the symlink needs no
chmod. Every path this file derives goes through Path(__file__).resolve(), so
invocation through the symlink resolves the kit dir, not ~/.local/bin.
"""

from __future__ import annotations

import os as _os, sys as _sys, pathlib as _pl  # task 7.630: solo-run tmux isolation, FIRST
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "coord" / "self_isolate.py").is_file()) / "coord"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()
# The derived-tree write refusal (spec-component-map §4). Imported from the
# module that DEFINES it — `coord/records.py`, already on sys.path from the line
# above — rather than re-implemented here: a second parent-walk is a second place
# the marker convention can drift. Not routed through `coord.py` because that
# shim reads its sixteen split files at import; this predicate is stdlib-only.
from records import (refuse_if_derived as _refuse_if_derived,
                     DerivedTreeRefusal as _DerivedTreeRefusal,
                     DERIVED_MARKER as DERIVED_MARKER_NAME)

import argparse
import collections
import csv
import datetime
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

import yaml

# The ONE Python reading of `cage.SeatBinds` — it lives in `ignite/envelope/` since the
# component-first move, so its folder is bound here rather than riding the kit's sys.path
# entry. ⚠ It used to be shared with the edge-runner's enqueue-time admission check; that
# check is now `envelope/cage-admission.js`, which drives `cage.js` LIVE instead of
# mirroring it (`build/one-readiness-predicate.md` § D5), so what the two gates share is
# the TEMPLATE, not this evaluator.
_ENVELOPE_DIR = _pl.Path(__file__).resolve().parent.parent / "envelope"
if str(_ENVELOPE_DIR) not in _sys.path:
    _sys.path.insert(0, str(_ENVELOPE_DIR))
import cagespec  # noqa: E402 — envelope/ bound just above

# goal_cli.py is the goals-tree surface under `ignite/operator/` — resolved
# relative to this file, never from a hardcoded workspace path.
_GOAL_CLI_DIR = Path(__file__).resolve().parent.parent / "operator" / "goals-tree" / "tool"
if str(_GOAL_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(_GOAL_CLI_DIR))

from goal_cli import (  # noqa: E402 — path bound just above
    BINDING_COLUMNS,
    Findings,
    Refusal as CatalogRefusal,
    after_member_grammar,
    assemble_seat,
    check_acyclic,
    index_units,
    load_catalogs,
    render_csv_line,
    substitute_after_ids,
    SECTION_RE,
    TOOLING_FINDING_BLOCK,
    WRITE_IF_SOMETHING,
)

# ---------------------------------------------------------------- constants

# The env scrub (ignite-job shape): read none of these, unset all of them at
# entry regardless — a detached loop inherits TMUX_PANE and every send is
# refused against the wrong pane.
SCRUBBED_ENV_VARS = ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET")

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# The goals-tree folder the goal-direct package bar keys on (7.607 E2b, design-lock
# item 8: the PACKAGE IS THE GOAL FOLDER). Positional, exactly like the daemon-side
# grammar in `runtime/seat-identity/seat-folder.js` — no second reading of goal
# identity, and it answers for a folder that does not exist yet.
GOALS_DIR_NAME = "goals"
MANIFEST_SEAT_COLUMN = "Seat/workflow"
MANIFEST_AFTER_COLUMN = "after"
TASKFORCE_NAME = "taskforce.csv"
MILESTONES_NAME = "milestones.csv"

# ---- dag-05 registry constants ----

# The registry's ONE header — run-2's live shape, verified 2026-07-28 (dag-05
# task file). Read from the file and preserved on write; NEVER extended here.
# In particular no `status` column: run-state is DERIVED from the check-out
# record + declared outputs (KG `taskforce-descriptor`; workflow.md
# DAG-authoring Rule 14) — a status column is a second ledger and is refused.
TASKFORCE_HEADER = ("taskforce-id", "seat", "after", "harness", "model",
                    "effort", "ctx-refresh", "milestone-id")

# ---- dag-06 create-package constants ----

# The state-cursor header a CREATED package's state.csv carries — byte-exact,
# the KG `state-cursor` record's column list (`sd-graph show state-cursor`;
# file-schema block). HEADER ONLY: the first real row is the leader's at
# bootstrap, never this command's; run-2's off-schema cursor is frozen
# history, never repaired.
#
# ⚠ THE ACCEPTANCE, RECORDED WHERE THE NEXT BUILDER LOOKS. This line and the
# KG record are the SAME contract in two repos and nothing joins them: the KG
# lives in the vault (`1-projects/rbtv-sb-merge-refactor/system-definition/
# concepts/state-cursor.md`), outside this repo, and a path to it here would
# break the no-hardcoded-workspace-paths rule (root CLAUDE.md). They diverged
# once already — the 5-column `stamped-at,run-state,seat,session-id,note`
# form survived here after owner ruling `d-runs-extinguished-transcription`
# (2026-08-09) ADDED `execution-stamp` and RENAMED `run-state` -> `goal-state`.
# CHANGING THIS LINE MEANS THE KG RECORD CHANGED: re-read it first, and update
# the literal in the selftest arm that pins this constant (search
# STATE_CSV_HEADER) in the same change — that arm is the tripwire that stops a
# silent edit. `coord.py#append_state_advance` is header-agnostic (it builds
# rows BY NAME off the on-disk header), so nothing else catches drift.
# ponytail: a prose acceptance, not a machine check — a real cross-repo
# comparison becomes possible only if the KG record ships into this repo.
STATE_CSV_NAME = "state.csv"
STATE_CSV_HEADER = "stamped-at,execution-stamp,goal-state,seat,session-id,note"

# The caller-supplied content surfaces of a created package
# (`d-run3-seeds-from-run2-amended`): surface name -> the argv option whose
# FILE carries the base text. VALUES never cross argv (R-10,
# r-floor-single-source) — the option is a path, a reference, not a copy.
CREATION_INPUTS = (
    ("CLAUDE.md", "--claude-md", "claude_md"),
    ("budget.json", "--budget-json", "budget_json"),
)

# ---- the ONE OPTIONAL creation surface: the addressable register (7.569) ----
#
# WHY IT IS NOT A THIRD `CREATION_INPUTS` ENTRY (a FOURTH until F7 abolished
# the `conduct.md` input, 2026-08-17). That tuple is the REQUIRED
# set: a member absent and unsupplied refuses `create-inputs-missing` in the
# full/bootstrap mode. Adding this file there would make every caller that does
# not pass a new option start refusing — including the ARMED goal-creation loop
# (`envelope/spawn-profiles.yaml`'s fire-tool argv, which fires on a cadence). A
# change that turns the live creation path into a refusal is an outage, not a
# build, so the register lands as an OPTIONAL input instead: supplied by the
# caller when it wants a specific register, DERIVED FROM DISK when it does not,
# and simply absent when the goals root offers nobody to admit.
#
# WHY DERIVING IS NOT "INVENTING A RUN CONVENTION" (the refusal above exists to
# stop exactly that). The register carries NO content of its own — it is a
# PATH, and the name and role word are read from the descriptor the
# correspondent itself owns (coord.py `load_addressable`, constraint 1). The
# grant is TWO-SIDED and the other side is the one that decides: this step
# points only at a standing-seat home whose OWN descriptor already declares
# `addressable: non-member`. So nothing here grants an address that the
# addressee has not already offered, and a goals root with no such door yields
# NO FILE — the mechanism ships inert exactly as it does today.
ADDRESSABLE_NAME = "addressable.csv"
ADDRESSABLE_HEADER = "descriptor,admitted-by,admitted"

# ---- the run register is EXTINGUISHED (7.607 E2b, design-lock item 8) -------
#
# ⚠ THE ONE RUN-REGISTER WRITER USED TO LIVE HERE and it is DELETED, not
# re-pointed: `RUNS_CSV_NAME` / `RUN_REGISTER_HEADER` / its two header spellings
# / `RUN_TYPES` / `RUN_STATE_OPEN` / `RUN_OPENED_FORMAT`, and the
# `render_run_register` + `append_run_register_row` pair (inventory #32 — the
# SINGLE home of the opening half, PRIN-11). The register recorded a RUN's
# state; there are no runs. `--run-type` goes with it: run type was csv DATA of
# a row that no longer exists, so there is nothing left to refuse a default for.
#
# ⚠ ITS IDEMPOTENCE-ON-REFIRE GUARANTEE IS NOT LOST — it is RE-STATED against
# the goal-direct creation act, which is now the only thing this command opens.
# The register's guarantee was "a second fire appends no second row, and every
# existing row passes through byte-unchanged". The creation act's equivalent, and
# it is STRONGER because it is enforced by the filesystem rather than by a scan:
# `plan_package_creation` plans only the surfaces that are ABSENT and
# `create_run_package` writes them EXCLUSIVELY (mode `xb`) — so a re-fire against
# a complete goal plans nothing and writes nothing, a re-fire against a partial
# one completes exactly the missing surfaces, and a surface appearing between
# plan and write fails loudly instead of being overwritten. Acceptance rows
# `creation` / `creation-partial` are that guarantee's arms.

# ---- dag-04 descriptor-surface constants ----

# F5 — the `mode:` enum, and its fail-closed emission defaults when a bindings
# row carries no explicit mode. `one-shot` for opencode preserves today's
# behaviour (harness_command hardcodes `run --auto`); `interactive` for
# claude. ANY other harness — codex included — has NO default: the row is
# REFUSED at emission (s4-04's fail-closed adjudication: an undecidable mode
# is refused loudly, never defaulted).
DESCRIPTOR_MODES = ("one-shot", "interactive")
MODE_DEFAULTS = {"opencode": "one-shot", "claude": "interactive"}

# The KG's FULL agent-type TOP set (`concepts/agent-type.md` — the four-member
# top set; `staff` is itself the grouping node the seven staff types sit under).
# The registry GOVERNS: this is the emitter brought into line with it, never a
# convention of its own (d-agent-type-widened-to-the-kg-top-set). The emitter
# allowed only staff|worker, so `dag-24` — REQUIRED to materialize the `master`
# seat — had NO truthful value: `staff` lists `master` as an explicit
# NON-example, and run-2's live descriptor already carries `agent_type: master`.
# Widened to the whole set, not to `master` alone: `verifier` is already valid
# per the registry, and the accepted cost — `verifier` accepted before anything
# emits one — is recorded in that ruling. `class:` stays REFUSED (G-217).
AGENT_TYPES = ("master", "staff", "worker", "verifier")

# Contract §1 (seatmd-render-contract.md) — the FIXED kind order the emitted
# file carries, NEVER the catalog's CSV column order. Kinds outside this list
# (invoked-unit stubs: capability, reference) keep assembler order after it.
KIND_ORDER = ("role", "procedure", "permissions", "restrictions", "constraints",
              "io-spec", "resources", "task-goal", "scope", "done-contract")

# Per-seat bindings keys this command understands. Anything else is a refusal
# (a typo'd key must never pass silently). `class` is refused with its own
# message: it is the WITHDRAWN spelling of agent_type (r-agent-type-field-name,
# G-217). `relays` is ACCEPTED and passes through to the emitted frontmatter —
# the ruled key set gained that one row (d-relays-frontmatter-passthrough,
# extending d-seatmd-keys-dag04-schema); see the module docstring for what the
# declaration means and what dropping it would cost.
ALLOWED_BINDING_KEYS = frozenset((
    "after", "cwd-mode", "description", "agent_type", "harness", "model",
    "effort", "mode", "ctx-refresh", "window", "senders", "close",
    "auto-wake", "ephemeral", "broadcast", "component", "relays",
    "addressable", "pass-folder",
))

# ---- the SEAT CAGE declaration (owner-ruled 2026-08-10) ----
#
# The bwrap sandbox a daemon-spawned seat runs inside is composed by
# `ignite/supervisor/spawn/spawn.js` from keys it reads OUT OF `seat.md`'s
# frontmatter at spawn time (`seatDeclares` / `seatDeclaresList`). Until this
# ruling those keys had NO SOURCE: they were typed into the live descriptors by
# hand and existed nowhere else, so nothing could re-render a seat.md without
# silently deleting the seat's whole sandbox. Absence is the mechanism there —
# a key that is not present is a mount that is never made — so the loss is
# silent and CRIPPLING rather than permissive: the channel master would come up
# unable to read the vault, write anything, reach any run's bus, or execute the
# CLIs its own skills route to.
#
# The ruled home is the SEAT CATALOG ROW — these are properties of what the
# seat IS (the same seat wants ~/.local/bin on any machine), not of how one
# launch happens to be configured, which is what `bindings` carries. Two
# columns, never one per grant: `cage-grants` names which grants the seat
# wants, and the cage TEMPLATE in spawn-profiles.yaml already knows what each
# one means.
#
#   seats.csv:  cage-grants          "read-root bus-write local-bin"
#               rw-paths             "1-projects,2-areas"
#
# `exposed-clis:` is DELIBERATELY NOT HERE. It is the sandbox realization of a
# prompt card's `exposes: path:` declaration, so it is DERIVED from the card
# like every other loader — a seat that could hand-declare it in the catalog
# would be a second, disagreeing home for the same fact.
CAGE_GRANTS = (
    "read-root", "keep-instruction-files", "bus-write", "goals-write",
    "local-bin", "gateway-env", "tmux-socket",
)
CAGE_RW_COLUMN = "rw-paths"
CAGE_GRANTS_COLUMN = "cage-grants"

# ---- `goal-writes` — the seat's ONE declared output (owner ruling D9) ----
#
# `rw-paths` cannot express "let this seat write its own goal's goal.md": it
# REFUSES every entry under `.rbtv/goals` by design, and rightly — that subtree
# holds every sessions.csv and every seat.md. So the seat's actual work product
# had no expressible grant at all, and the plan-interviewer discovered that
# after a full night of interviewing, by meeting EROFS on the one file it
# existed to produce (2026-08-09).
#
#   seats.csv:  goal-writes          "goal.md"
#
# ONE path, relative to the seat's own GOAL folder — not the workspace, which is
# what `rw-paths` is relative to. Emitted as a one-item LIST so spawn.js reads it
# with `seatDeclaresList`, the same reader `rw-paths` already goes through.
CAGE_GOAL_WRITES_COLUMN = "goal-writes"

# ---- `on-fail-relaunch` — a judge seat's declared loop route (owner ruling 2026-08-12) ----
#
# The FAIL-verdict loop re-fire (`concepts/loop.md`): the seats this judge's FAIL re-dispatches
# on their slots, below the retry bar. Declared per seat in the CATALOG (the loop's shape differs
# per workflow and per judge), emitted into seat.md frontmatter, read at verdict time by
# `coord.py#on_fail_relaunch_route` — deterministic routing at the edge, never an agent's act.
#
#   seats.csv:  on-fail-relaunch     "forg-builder,forg-judge"
ON_FAIL_RELAUNCH_COLUMN = "on-fail-relaunch"

# The cage template's home — `ignite/envelope/` since the component-first move,
# resolved relative to THIS file exactly as goal_cli's tool dir is above.
_SPAWN_PROFILES = Path(__file__).resolve().parent.parent / "envelope" / "spawn-profiles.yaml"

def _cage_rw_covers(rel: str) -> bool:
    """True when the seat cage composes a READ-WRITE opening over `rel`, a path
    relative to the goal folder.

    THE GENERATION-TIME PREFLIGHT (owner ruling D13). Read out of
    `envelope/spawn-profiles.yaml`'s `cage.SeatBinds` — the very list spawn.js
    composes the sandbox from — so what a seat is told it may write and what the
    kernel will actually let it write cannot drift into disagreeing. That
    disagreement, with nothing anywhere comparing the two surfaces, is the whole
    defect: sixteen seats carried a permissions block claiming a write the cage
    denied, and the first one to run found out the hard way.

    The reading is cage.js's own and must stay it: input order is output order,
    and the LAST entry covering a path decides what that path IS — so a `tmpfs`
    or a `ro-bind` placed after an opening takes it back. D3 (2026-08-19): the
    goal folder is RW, so `sessions.csv` / `state.csv` / ledgers / planning /
    coordination answer True via `bind:{goalDir}`. Peer seat folders stay
    absent under the `seats` tmpfs; `seat.md` stays RO under its carve.

    ⚠ THE READING ITSELF LIVES IN `cagespec.py` SINCE IPH-2, not here. This gate
    keeps only its own load of the live template. (The enqueue-time admission
    check it once shared that evaluator with is now `envelope/cage-admission.js`,
    driving `cage.js` live.) `rel` is passed as the goal-writes
    declaration because that is what it IS at every call site — the line
    `bind-try:{grant:goalWrite}` is the one this declaration fills.
    `cagespec.PEER` is the occupant: no real seat name can equal it, so no
    `{seatDir}` opening can ever make a `seats/...` declaration read writable —
    the same answer this gate gave before the evaluator was shared. Anything
    underivable evaluates `undecided`, which is not `writable`, so the refusal
    stays fail-closed."""
    verdict, _entry = cagespec.evaluate(_seat_binds(), rel, seat=cagespec.PEER,
                                        goal_writes=[rel])
    return verdict == cagespec.WRITABLE


def _seat_binds() -> list:
    """The live `cage.SeatBinds` template, read fresh. One loader for both
    readers below so a template change cannot reach one and not the other."""
    return ((yaml.safe_load(_SPAWN_PROFILES.read_text(encoding="utf-8")) or {})
            .get("cage") or {}).get("SeatBinds") or []


# The uncaged-staff roster's ONE home is `envelope/launch.js` — the `STAFF` set
# `isStaffUncaged` answers from, which spawn.js consults BEFORE it composes any cage at
# all. Read here rather than restated, for the same reason `_seat_binds` reads the live
# template instead of copying it: a second copy of the roster lets a role join or leave
# the uncaged set in JS while this file keeps describing a sandbox that role no longer
# has, with nothing anywhere comparing the two — the exact drift shape D13 exists to end.
# ⚠ NOT `coord.STAFF_SEATS`. That tuple is deliberately `("leader",)` (D24, asserted by
# coord_selftest) and answers a different question: which chair joins the first
# taskforce. Conflating the two puts `goal-master` on the wrong side of both.
_LAUNCH_JS = Path(__file__).resolve().parent.parent / "envelope" / "launch.js"
_STAFF_SET_RE = re.compile(r"const\s+STAFF\s*=\s*new\s+Set\(\s*\[([^\]]*)\]")


def _staff_uncaged_seats(src=None) -> frozenset:
    """The seat ids `envelope/launch.js#isStaffUncaged` answers True for, read fresh
    out of that file.

    REFUSES rather than defaults. The tempting fallback on an unreadable or reshaped
    roster — "assume caged" — is precisely the defect this reader exists to end: it
    would quietly hand a staff seat the worker template's enumeration again, and that
    section outranks the prose above it, so the wrong half would win in silence.

    `src` exists ONLY so the selftest can hand this a reshaped source and prove the
    refusal fires — the same knob, for the same reason, as `_cage_write_surface`'s
    `binds`. Every real caller reads the live file."""
    if src is None:
        try:
            src = _LAUNCH_JS.read_text(encoding="utf-8")
        except OSError as exc:
            raise Refuse(
                "uncaged-roster-unreadable",
                f"cannot read the uncaged-staff roster at {_LAUNCH_JS} ({exc}) — "
                "every descriptor's write-surface section is chosen by it, and "
                "guessing produces a seat that is told about a cage it does not have",
                str(_LAUNCH_JS),
            )
    match = _STAFF_SET_RE.search(src)
    names = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)) if match else []
    if not names:
        raise Refuse(
            "uncaged-roster-unparseable",
            f"the uncaged-staff roster in {_LAUNCH_JS} is not the expected "
            "`const STAFF = new Set([...])` form, or is empty — this file reads it to "
            "decide which write-surface section a descriptor carries; a reshaped "
            "roster is a refusal here, never a silent fall back to the caged text",
            str(_LAUNCH_JS),
        )
    return frozenset(names)


def _cage_write_surface(seat: str, goal_writes: list, binds=None) -> list:
    """The goal-relative paths this seat's cage actually opens READ-WRITE, in
    template order — DERIVED, never restated.

    `_cage_rw_covers` above answers "is the DECLARED path writable". D3 made the
    whole goal folder RW, so the old file-inside-ro-directory EROFS trap is
    gone for records. Shadowing is still respected: a later `ro-bind` carve
    (`seat.md`) must not appear here.

    Openings that compose OUTSIDE the goal folder (worktrees, `~/.local/bin`,
    the tmux socket) are absent by construction — `cagespec` drops them — which
    is why the rendered heading says "inside your goal folder" and means it.

    `binds` exists ONLY so the selftest's red arms can mutate the template and
    prove the controls fail — the same knob, for the same reason, as
    `render_descriptors`'s `resolve_inline`/`reorder`. Every real caller reads
    the live file."""
    binds = _seat_binds() if binds is None else binds
    spec = cagespec.compose(binds, seat=seat, goal_writes=goal_writes) or []
    out: list = []
    for verb, rel in spec:
        if rel == "":
            if verb in cagespec.RW_VERBS and "." not in out:
                out.append(".")
            continue
        if rel in out:
            continue
        if cagespec.evaluate(binds, rel, seat=seat,
                             goal_writes=goal_writes)[0] == cagespec.WRITABLE:
            out.append(rel)
    return out


# The derived write-surface section every descriptor carries. `{rows}` is the
# only slot; the trap paragraph is CONSTANT because the trap is — a single-file
# RW opening inside a read-only directory is what the template composes for
# EVERY seat, whether the file is a `goal-writes` product or one of the five
# ledgers the router sends every seat to.
_WRITE_SURFACE_BLOCK = """\

<!-- DERIVED at materialize from envelope/spawn-profiles.yaml's `cage.SeatBinds` — the
     very list spawn.js composes your sandbox from, read through the one evaluator
     (cagespec.py) the materializer's own refusal gate uses. WHERE ANY PROSE ABOVE
     DISAGREES WITH THIS SECTION, THIS SECTION IS RIGHT: the prose is authored, this
     is measured. -->

## Your write surface — what the kernel will actually answer

Read-write inside your goal folder (D3, 2026-08-19 — the whole folder, including
ledgers, planning, coordination, sessions.csv). `.` is the goal folder itself.
Peer seat folders are absent. `seat.md`
stays read-only — a wall-control surface, not a record:

{rows}

This list is scoped to your goal folder and is not your whole grant: openings that compose
OUTSIDE it — a worktree, another goal's coordination dir, `~/.local/bin`, the tmux socket —
are granted separately by your `seat.md` frontmatter and are not enumerated here.

## Your read surface — the workspace, minus the private scope

You read the WHOLE workspace (owner ruling D-1) — no declaration, no per-CLI carve-out.
Subtracted from it is the `private scope`, the workspace's own deny list at
`.rbtv/config/private.json` plus a pattern floor beneath it: those paths list EMPTY and
refuse writes, which is a mask and not a missing grant — asking for one changes nothing,
and `.rbtv/config/.env` and the list itself are unpierceable by construction.

⚠ **A PIERCE — a grant of yours that names a path INSIDE a denied entry — is disclosed at
SPAWN, not here.** This section is derived at materialize time, and the deny list is read
at DISPATCH, so the materializer cannot know it: the per-spawn `private-scope PIERCE` /
`pierce REFUSED` lines in the daemon log are the only complete account of what your cage
actually opened. A merely broader grant does not pierce; the entry stays masked.
"""


# The same section for a seat the sandbox is never composed for. NOT a variant of the
# block above with different rows: an uncaged seat has NO bind list, so an enumeration
# is the wrong SHAPE of answer, and enumerating one from the worker template is exactly
# how the three staff roles came to be told they may not write surfaces they own —
# under a header that outranks the (correct) prose above it. The header keeps its
# priority claim, because it is still the measured half; what changed is that what it
# measures is `launch.js`'s roster rather than a bind list that does not exist.
_UNCAGED_WRITE_SURFACE_BLOCK = """\

<!-- DERIVED at materialize from envelope/launch.js's `STAFF` set — the roster
     `isStaffUncaged` answers from, which spawn.js consults BEFORE it composes any
     sandbox. This seat is ON it, so no cage is built for this sitting and there is no
     `cage.SeatBinds` list to enumerate. WHERE ANY PROSE ABOVE DISAGREES WITH THIS
     SECTION, THIS SECTION IS RIGHT: the prose is authored, this is measured. -->

## Your write surface — what the kernel will actually answer

**This seat runs UNCAGED.** `spawn.js` returns at `isStaffUncaged` before a single bind
is composed, so no path is fenced off from you by a sandbox: you may write anywhere your
user account can write — this goal folder in full, any other goal's folder, the rbtv
repo, and paths outside the workspace entirely. There is no list here because there is
no cage to enumerate, and an empty list would read as a denial.

Two things still hold, and neither of them is a wall:

- Staying out of a peer seat's folder is a working NORM you keep, not a wall that keeps
  you. The same goes for another goal's coordination dir. Nothing will stop you.
- A refusal you actually hit is a real error — a missing file, a read-only mount, a
  permission bit, a file another process holds. Read it as one and fix it. Never
  conclude from it that you lack a grant, and never abandon a fix on that basis.

## Your read surface — the whole workspace

You read the WHOLE workspace (owner ruling D-1) — no declaration, no per-CLI carve-out.
An uncaged sitting composes no `private scope` mask either, so paths
`.rbtv/config/private.json` hides from a caged seat are readable from here. That is a
property of running without a sandbox, not a licence to put a secret into a message, a
command argument, or a file.
"""


def _write_surface_section(seat: str, goal_writes: list) -> str:
    """The derived write-surface section for ONE seat: the caged enumeration or the
    uncaged statement, chosen by the SAME roster spawn.js chooses by.

    The section itself is unconditional — every descriptor carries a measured statement
    of what the kernel will answer, and that is what earns it priority over the prose
    above. Its CONTENT is not: composing the caged enumeration for a seat that gets no
    cage told `goal-master`, `channel-master` and `leader` that `seat.md` was read-only
    and that their write surface was two paths, which is false in every direction, and
    the priority sentence made the false half win."""
    if seat in _staff_uncaged_seats():
        return _UNCAGED_WRITE_SURFACE_BLOCK
    surface = _cage_write_surface(seat, goal_writes)
    return _WRITE_SURFACE_BLOCK.format(
        rows="\n".join(f"- `{p}`" for p in surface) if surface else
        "- (nothing — this seat's cage opens no read-write path inside its "
        "goal folder)")


def open_binding(seat: str, b: dict, package: Path) -> bool:
    """True when this seat's harness·model·effort triple is deliberately
    UNBOUND, so the descriptor omits all three (owner-ruled 2026-08-10).

    Only a STANDING-SEAT home can do this, and only by declaring none of the
    three. Two things make it sound exactly there and nowhere else: the triple
    normally exists to agree with the seat's `taskforce.csv` row, and a
    standing-seat home HAS no registry for it to agree with; and the seat that
    needs it says so in its own definition — the channel master's harness and
    model are named by the chat bridge at spawn time
    (`harnessOf(profile)` — the spawner never reads them from `seat.md`), so a
    concrete value here is inert AND states the opposite of
    `d-master-harness-agnostic` to the occupant reading the file.

    ALL THREE OR NONE. A partial declaration is refused rather than half-honoured:
    a descriptor carrying a harness but no model reads as a binding that was
    made, and would send a reader looking for the missing half."""
    if not standing_seat(package):
        return False
    declared = [k for k in ("harness", "model", "effort")
                if str(b.get(k, "") or "").strip()]
    if not declared:
        return True
    if len(declared) < 3:
        raise Refuse(
            "open-binding-partial",
            f"standing seat '{seat}' declares " + ", ".join(declared)
            + " but not the whole harness·model·effort triple — a standing "
            "seat's binding is open (all three omitted) or bound (all three "
            "present), never half of one",
        )
    return False


def _cage_frontmatter(seat: str, seats_cat: dict) -> dict:
    """The seat's cage declaration, read off its catalog row, ready to emit
    into the descriptor frontmatter. `{}` when the row declares none — a seat
    with no cage keys is the normal case (an uncaged tmux seat), never a
    defect.

    Both columns REFUSE rather than skip on a bad value. spawn.js warns and
    drops a bad `rw-paths` entry, which is right at spawn time (one bad line
    must not take the seat down) and wrong at authoring time: a dropped grant
    surfaces as a seat that mysteriously cannot write, hours later, in a log
    nobody is reading. Here the author is still holding the file."""
    row = seats_cat.get(seat) or {}
    fm: dict = {}
    raw = str(row.get(CAGE_GRANTS_COLUMN, "") or "").replace(",", " ").split()
    for grant in raw:
        if grant not in CAGE_GRANTS:
            raise Refuse(
                "cage-grant-unknown",
                f"seat '{seat}' declares cage-grant '{grant}' — the sandbox "
                "composes only " + " | ".join(CAGE_GRANTS)
                + "; an unknown grant is a refusal, never a silently-dropped "
                "mount (`exposed-clis` is DERIVED from the prompt card's "
                "`exposes: path:` and is never declared here)",
            )
    for grant in CAGE_GRANTS:          # canonical order, never the row's
        if grant in raw:
            fm[grant] = True
    rw = [e.strip() for e in
          str(row.get(CAGE_RW_COLUMN, "") or "").split(",") if e.strip()]
    for entry in rw:
        # The three spawn.js rejects, applied where the author can still act.
        if PurePosixPath(entry).is_absolute():
            raise Refuse(
                "cage-rw-path-absolute",
                f"seat '{seat}' declares rw-path '{entry}' — rw-paths entries "
                "are WORKSPACE-RELATIVE; spawn.js drops an absolute one with "
                "a warning nobody reads",
            )
        parts = PurePosixPath(entry).parts
        if ".." in parts:
            raise Refuse(
                "cage-rw-path-escapes",
                f"seat '{seat}' declares rw-path '{entry}' — an entry that "
                "climbs out of the workspace root resolves to a grant the "
                "sandbox refuses",
            )
        if parts[:2] == (".rbtv", "goals"):
            raise Refuse(
                "cage-rw-path-ground-truth",
                f"seat '{seat}' declares rw-path '{entry}' — .rbtv/goals is "
                "where the identity ground truth lives (sessions.csv, every "
                "seat.md); a cage whose occupant can rewrite the gate's own "
                "input is decoration, and spawn.js refuses this entry too",
            )
    if rw:
        fm[CAGE_RW_COLUMN] = rw
    declared = str(row.get(CAGE_GOAL_WRITES_COLUMN, "") or "").strip()
    if declared:
        parts = PurePosixPath(declared).parts
        if PurePosixPath(declared).is_absolute() or ".." in parts:
            raise Refuse(
                "cage-goal-writes-shape",
                f"seat '{seat}' declares goal-writes '{declared}' — the column "
                "names ONE path RELATIVE TO THE SEAT'S OWN GOAL FOLDER (note: "
                "not to the workspace, which is what rw-paths is relative to); "
                "an absolute path, or one that climbs out with '..', is a grant "
                "the cage cannot compose",
            )
        if not _cage_rw_covers(declared):
            raise Refuse(
                "cage-goal-writes-ungranted",
                f"seat '{seat}' declares goal-writes '{declared}' but "
                f"{_SPAWN_PROFILES.name}'s cage composes NO read-write opening "
                "over it — materializing this seat would hand its occupant a "
                "briefing that promises a write the kernel answers EROFS to, "
                "which is exactly how the plan-interviewer lost a night's work "
                "(2026-08-09). Ground truth is refused here by construction and "
                "stays refused: sessions.csv and state.csv sit under the "
                "read-only goal floor, another seat's folder under the seats "
                "tmpfs, and seat.md under its own read-only carve",
            )
        fm[CAGE_GOAL_WRITES_COLUMN] = [declared]
    route = [e.strip() for e in
             str(row.get(ON_FAIL_RELAUNCH_COLUMN, "") or "").split(",") if e.strip()]
    for entry in route:
        if entry not in seats_cat:
            raise Refuse(
                "on-fail-relaunch-unknown-seat",
                f"seat '{seat}' declares on-fail-relaunch '{entry}' — no such seat in the "
                "catalog; a loop routed at a seat that cannot exist is a loop that stalls "
                "silently at its first FAIL, hours later, in a grant file nobody reads",
            )
    if route:
        fm[ON_FAIL_RELAUNCH_COLUMN] = route
    return fm

# ---- pass-folder substitution (B4, B5, G-planner-0804-1502) ----

# The chief-of-staff's pass registry (r-progress-governor): one row per
# planning pass, `closed` empty while the pass is OPEN.
PASSES_NAME = "passes.csv"

# The TWO legal pass forms, SIBLINGS directly under `planning/` — a briefing
# folder is never nested inside a milestone folder:
#   planning/m{N}-{milestone-name}/  MILESTONE pass (d-milestone-id-and-folder-form)
#   planning/briefing-<name>/        BRIEFING pass  (r-briefing-pass-planning-home)
# Both are admitted, and the briefing form is the COMMON case (run-3's planning
# surface holds 26 folders, 25 of them `briefing-*`). Capture 1/2 is the pass
# TAG — what the per-pass artifact names are built from (`manifest-<tag>.csv`).
PASS_FOLDER_RE = re.compile(
    r"\Aplanning/(?:(m\d+)-[A-Za-z0-9][A-Za-z0-9._-]*"
    r"|briefing-([a-z0-9][a-z0-9-]*))/\Z")

# The pass-scoped placeholders a unit body carries. LONGEST FIRST: the two path
# forms contain the bare `m{N}`, so substituting the bare token first would
# leave a half-rewritten path. A survivor in an emitted descriptor is the
# defect this substitution exists to close — the executor derives its own write
# path, which is the hunt P3 forbids.
PASS_PLACEHOLDERS = (
    "planning/m{N}-{milestone-name}/",
    "planning/<pass-folder>/",
    "m{N}",
)

# The EXPLICIT opt-out. A substituter cannot tell a placeholder being USED (a
# write surface the executor must be handed) from one being MENTIONED (a unit
# whose subject matter IS the placeholder — every unit of this very wave quotes
# `m{N}` while specifying the substitution). Substituting a mention corrupts
# the specification; refusing it blocks the seat. So the author DECLARES it,
# and the declaration is greppable: `pass-folder: none` says "these are
# mentions, this seat names no pass surface". Silence stays a refusal — the
# defect being closed is the SILENT placeholder, never the declared one.
PASS_FOLDER_NONE = "none"

# The assembled projection's shapes this file READS (it never emits a block
# itself — SK-7): the assembler's frontmatter fence and its attributed
# kind-tag blocks. The block pattern deliberately starts `<(` so SK-7's
# local-emitter detector cannot match it.
_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
# A kind-named section, in BOTH live forms (assembler id+version · bare/attributed
# d-prompt-task-files). Groups (1) kind (2) id or None (3) version or None (4) body —
# the selftest reads 4. IMPORTED, not restated: goal_cli's `permissions well-formed`
# lint asks this exact question of this exact text, and the lint and this HARD GATE
# disagreeing is a seat that materializes and then cannot pass its own lint.
_BLOCK_RE = SECTION_RE

# D36 (2026-08-20) — ONE `Write:` BULLET of a task's `<scope>` block, from its dash to the next
# top-level bullet (or the block's end). The `Read:` bullet beside it backticks input paths and
# must never be harvested, which is why this matches the LABEL and not the block. Bold and plain
# spellings both occur in the live catalog (`- Write:` and `- **Write:**`).
# ⚠ THIS IS A BULLET FINDER, NOT A PATH GRAMMAR. Which backticked token inside the bullet counts
# is decided by coord.py's own `_IOSPEC_PATHISH` (`_coord_iospec_grammar`) and by nothing here —
# a token this file admitted and the check-out could not resolve would be a declaration the gate
# still refuses, which is the whole defect D36 exists to close.
_SCOPE_WRITE_RE = re.compile(
    r"^[ \t]*[-*][ \t]*\**Write\**:[\s\S]*?(?=\n[ \t]*[-*][ \t]|\Z)", re.MULTILINE)

# The projected bullet, verbatim. It says WHERE it came from because a reader of the rendered
# descriptor must be able to tell prompt-authored schema (reusable, use-case-neutral) from
# instance data the materializer computed — the KG's own split.
_PROJECTED_OUTPUT_BULLET = (
    "- Destination (projected from the task's scope Write clause): `{token}`")

# D5 (seed-gates, 2026-08-19) — a done-contract line NAMING a probe lane the
# seat must be able to run once caged: `probe lane: `<command …>`` (hyphen or
# space, optional list dash, command backticked). The first word of the
# command is the CLI the lane needs on PATH; render_descriptors derives a
# `## Requires-reach` io-spec entry from it (see the emission site).
_PROBE_LANE_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?probe[ -]lane:[ \t]*`([^`\n]+)`",
    re.IGNORECASE | re.MULTILINE)

# d-run3-assembled-shape (i) — a `Reference: <id>@latest` line INSIDE a unit
# body (the io-spec mandate references; written with or without backticks,
# with an optional list dash and trailing period). The assembly lockfile only
# freezes catalog-row refs, so these would survive as dead pointers unless the
# emitter inlines the referenced unit's body at the line.
_INLINE_REF_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?Reference:[ \t]*`?"
    r"([a-z0-9][a-z0-9-]*)@latest`?\.?[ \t]*$",
    re.MULTILINE)


class Refuse(Exception):
    """Exit 1 — a refusal with a machine-readable code. Never a crash.

    Every refusal prints to stderr AND appears in the --json result as
    {ok: false, refusal: {code, message, path}} — a job whose failure is only
    human-readable cannot be consumed by a queue.
    """

    def __init__(self, code: str, message: str, path: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path


# ---------------------------------------------------------------- env scrub


def scrub_environment() -> None:
    """Unset every pane/identity variable at entry — argv-only, environment-free."""
    for var in SCRUBBED_ENV_VARS:
        os.environ.pop(var, None)


# ---------------------------------------------------------------- helpers


def _csv_rows(path: Path) -> list[dict]:
    """Rows of a csv, [] when the file does not exist (bootstrap-tolerant read)."""
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


# ---------------------------------------------------------------- validation


# ------------------------------------------- the package IS the goal folder
#
# 7.607 E2b, `decisions.md#d-extinguishment-design-lock` item 8 (D9). There is
# no run compartment and no branch compartment: a goal's working content sits
# DIRECTLY under `<ws>/.rbtv/goals/<goal>/`, so `--package` names the goal
# folder and nothing else.
#
# ⚠ `package_kind` IS DELETED, not re-keyed to one value. It existed to tell a
# run from a branch; with both gone it would have had a single kind and a single
# caller — a classifier that classifies nothing. The bar it fed is inlined in
# `validate_package` below, which is now its only reader.
#
# ⚠ BRANCH PACKAGES ARE DELETED, not migrated (design-lock item 9, owner + KG):
# `materialize_branch`, `--branch-of`/`--branch`, and the four `goal_cli` branch
# imports are gone. The registry deleted the branch FOLDER on 2026-08-07
# (`r-branch-folder-deleted-nested-seats-are-ordinary-run-seats`): `branch` is a
# ROLE with NO file home, and a nested workflow's seats are ordinary seats of the
# parent goal. Re-founding the nested-workflow LAUNCH on that shape is a design
# act and is NOT performed here — see the findings' measured boundary.


# The BARE goal taskforce-id. A NESTED instance's id (`tf-<n>-<prefix><m>`) is a
# SECOND NAMESPACE in the same column and is deliberately not matched here: the
# counter counts goal taskforces, and a nested id read as one would advance it.
BARE_TF_RE = re.compile(r"tf-(\d+)")
# ...and the nested id, so a reader of the column can subtract that namespace.
# Deliberately NOT the complement of BARE_TF_RE: a goal's id may legitimately be
# neither (a hand-authored `tf-a` exists in the wild), and treating "not bare" as
# "nested" would silently unread it.
NESTED_TF_RE = re.compile(r"tf-\d+-[a-z]{4}\d+")


def derive_taskforce_id(package: Path, prefix: str = "",
                        ordinal: int = 0) -> str:
    """The taskforce-id a zero-data-row registry carries: a COUNTER read from the
    goal's own `taskforce.csv` — `max existing + 1` (design-lock item 10 / D3).

    With `prefix`/`ordinal` (the NESTED path) it composes the owner's ruled
    nested shape instead — `tf-<n>-<prefix><m>`, e.g. `tf-2-rsch1`
    (`d-r2-tfid-structured-counter`, 2026-08-10). `n` is this same counter, the
    prefix is the workflow's declared four letters and `m` is the instance
    ordinal, so the id names WHICH instance minted the rows. The former
    `tf-<run>-<prefix><n>` form is STRUCK: the run layer is extinguished and
    `<run>` has no input left.

    NO FOLDER-NAME INPUT, and that is the whole change. The id used to be the run
    ordinal (`runs/run-3` -> `tf-3`), which was only ever available because the
    package path carried a compartment number. The package is now the goal folder
    and its name is the goal, so the ordinal has one honest source left: the ids
    already in the file. An unparseable or non-`tf-N` id contributes nothing to
    the max rather than raising — this function's contract is to produce the NEXT
    id, and a registry it cannot fully read still has a defensible next value.

    `package` is the goal folder. The file may not exist (the creation act's
    first call); an absent or header-only registry yields `tf-1`.
    """
    top = 0
    for row in _csv_rows(package / TASKFORCE_NAME):
        m = BARE_TF_RE.fullmatch((row.get("taskforce-id") or "").strip())
        if m:
            top = max(top, int(m.group(1)))
    n = top + 1
    return f"tf-{n}-{prefix}{ordinal}" if prefix else f"tf-{n}"


def validate_package(raw: str) -> Path:
    """The absolute GOAL FOLDER this command materializes into."""
    package = Path(raw)
    if not package.is_absolute():
        raise Refuse(
            "package-not-absolute",
            "--package must be an ABSOLUTE goal-folder path — never inferred",
            raw,
        )
    if not (package.parent.name == GOALS_DIR_NAME
            and ID_RE.match(package.name.lstrip("_"))
            and not package.name.startswith("__")):
        raise Refuse(
            "package-not-a-goal",
            "--package must resolve to a GOAL FOLDER — "
            f"<workspace>/.rbtv/{GOALS_DIR_NAME}/<goal> (design-lock item 8: "
            "the package IS the goal folder; the runs/run-N compartment and "
            "the branches/branch-M home are both extinguished) — seats "
            "materialize into the goal folder, never beside their definitions "
            "(d-all-seats-in-run-folder)",
            str(package),
        )
    # An ABSENT package no longer refuses here: dag-06's creation step plans
    # it (plan_package_creation) and creates it AFTER every gate has passed
    # (create_run_package in run()'s write phase) — the bar above still
    # refuses BEFORE any creation, so nothing is ever created off-compartment.
    return package


def standing_seat(package: Path) -> str | None:
    """The seat id a STANDING-SEAT package is the home of, or None.

    A standing seat is one seat with many sessions and no goal apparatus
    around it — `.rbtv/goals/_channel-master/` (r-master-seat-homes). The
    leading underscore IS the marker, and the rest of the folder name IS the
    seat id, so the shape is decidable from the path alone with nothing to
    configure and nothing to keep in sync.

    Consequences everywhere below, all of them following from "the package IS
    the seat folder": the descriptor and its harness surfaces sit at the
    package root rather than under `seats/<id>/`, and the goal-package
    surfaces (`conduct.md`, run `CLAUDE.md`, `budget.json`, `taskforce.csv`)
    are neither expected nor created — there is no goal here to run."""
    return package.name[1:] if package.name.startswith("_") else None


def seat_home(package: Path, seat: str) -> Path:
    """Where seat `seat`'s folder is inside `package` — the package itself
    for that seat's own standing-seat home, else `seats/<seat>/`."""
    return package if standing_seat(package) == seat else package / "seats" / seat


# ------------------------------------- the INSTANCE-ORDINAL seat name (7.545)
#
# ONE function composes a nested-instance seat name and ONE function reads one
# back. Anything that ever needs either goes through these — a second spelling
# of the shape is two definitions of what a seat is called, and the failure
# that produces is a folder one half of the system can name and the other
# cannot find.
#
# THE SHAPE — owner ruling `d-owner-7545-7551-design-rulings-0808` criterion 1,
# AMENDING the registry's `r-branch-seat-name-carries-the-instance-ordinal`:
#
#     first instance    ->  <four-letters>-<seat>       e.g. rsch-researcher
#     second onward     ->  <four-letters>-<n>-<seat>   e.g. rsch-2-researcher
#
# The ordinal appears FROM THE SECOND INSTANCE ONWARD, never on the first. The
# superseded reading — ordinal ALWAYS present, `rsch-1-researcher` — is the one
# that ruling explicitly invited a correction to in one word, and this IS that
# correction. Two consequences the owner accepted, neither of which a later
# reader may "tidy away":
#   - TWO name shapes exist, so anything PARSING a seat name handles both;
#     `parse_instance_seat_name` below is this file's only reader of one.
#   - NO RENAME EVER OCCURS when a second instance appears. The first instance
#     keeps its bare-ordinal name for the life of the goal, so the composition
#     is stable and a name already written to disk is never rewritten.
#
# TOP-LEVEL SEATS KEEP BARE NAMES — no prefix, no ordinal (dossier §7 Q2 (a),
# ruled KEPT). The asymmetry is deliberate rather than an oversight: a
# top-level seat has no enclosing workflow instance to be the Nth of.
#
# ⚠ A COMPOSED NAME IS A DISK NAME, NEVER A CATALOG KEY (criterion 7, the real
# build cost and invisible in the rulings). A seat id is TODAY also the key
# into `seats.csv` and into the bindings file, and `check_bindings_cover`
# demands the bindings keys EQUAL the resolved set. A composed name reaching
# either lookup fails every live bindings file with `bindings-missing-seat`.
# The two names are therefore kept apart BY CONSTRUCTION: the CATALOG ID
# resolves a catalog row and a binding; the COMPOSED NAME names a folder, a
# `taskforce.csv` seat cell, an `after` member and a descriptor's `seat:` key.
# Nothing below ever feeds a composed name back into a catalog lookup.
#
# THE CALLER IS `--nested` (re-founded 2026-08-10, the design act 7.607 E2b
# reserved). `--workflow W --nested` materializes W as an INSTANCE of the
# parent goal: `nested_instance` below re-keys the resolved set through
# `compose_seat_name` and everything downstream — folders, descriptors,
# `taskforce.csv` seat cells and `after` cells — carries the composed name with
# no second spelling. `--workflow W` alone is unchanged and still materializes
# bare catalog ids, which is what a goal's OWN workflow is.

WORKFLOW_DESCRIPTOR_NAME = "workflow.md"
# The key a workflow folder DECLARES its four letters under (dossier §2 option
# B). DECLARED, never derived and never defaulted: derivation was measured to
# COLLIDE on 2 of 40 real workflow ids, so a derived prefix silently merges two
# workflows' instances into one ordinal series. Required only where a nested
# instance is composed, which is why the existing manifests need no edit.
WORKFLOW_PREFIX_KEY = "four-letters"
FOUR_LETTERS_RE = re.compile(r"^[a-z]{4}$")
# Reads BOTH ruled shapes. The ordinal alternative starts at 2 deliberately —
# `<prefix>-1-<seat>` is the SUPERSEDED shape and is never composed here, so
# admitting it as instance 1 would quietly re-legalize the reading the owner
# reversed.
INSTANCE_SEAT_RE = re.compile(r"^([a-z]{4})-(?:([2-9][0-9]*)-)?([a-z0-9][a-z0-9-]*)$")


def read_workflow_prefix(workflow_dir: Path) -> str:
    """The FOUR LETTERS a workflow declares for its nested instances.

    Read from `<workflow folder>/workflow.md`'s YAML frontmatter. TYPED
    REFUSAL on absence — never derived from the workflow id, never defaulted.
    A regex read of one frontmatter key, matching the idiom the daemon-side
    readers use: a full parse to answer a one-word question buys a dependency
    for nothing, and this must answer for a descriptor authored by hand."""
    desc = workflow_dir / WORKFLOW_DESCRIPTOR_NAME
    try:
        text = desc.read_text(encoding="utf-8")
    except OSError:
        raise Refuse(
            "workflow-prefix-undeclared",
            f"the workflow folder carries no readable {WORKFLOW_DESCRIPTOR_NAME}, "
            f"so its `{WORKFLOW_PREFIX_KEY}:` cannot be read — a nested instance "
            "is named from a DECLARED prefix, never one derived from the "
            "workflow id (derivation collides)",
            str(desc),
        ) from None
    fm = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    declared = (re.search(rf"^{WORKFLOW_PREFIX_KEY}:[ \t]*(\S+)[ \t]*$",
                          fm.group(1), re.M) if fm else None)
    if not declared:
        raise Refuse(
            "workflow-prefix-undeclared",
            f"{WORKFLOW_DESCRIPTOR_NAME} declares no `{WORKFLOW_PREFIX_KEY}:` key "
            "— a workflow that can be nested declares its own four letters, and "
            "an absent declaration is a refusal rather than a derived default",
            str(desc),
        )
    value = declared.group(1).strip().strip("'\"")
    if not FOUR_LETTERS_RE.match(value):
        raise Refuse(
            "workflow-prefix-invalid",
            f"`{WORKFLOW_PREFIX_KEY}: {value}` is not FOUR lowercase letters — the "
            "prefix is a fixed-width segment of every composed seat name and a "
            "variable-width one makes the name unparseable",
            str(desc),
        )
    return value


def parse_instance_seat_name(name: str) -> tuple[str, int, str] | None:
    """`(prefix, ordinal, seat-id)` of a composed name, or None.

    A SHAPE reader, and only meaningful where a composed name is expected: a
    bare top-level seat literally named `rsch-researcher` reads as instance 1
    of `rsch`, because the amended shape makes the two indistinguishable. That
    ambiguity is the accepted cost of dropping the first ordinal, and the
    caller supplies the context this cannot — never the other way round."""
    m = INSTANCE_SEAT_RE.match(name or "")
    if not m:
        return None
    return m.group(1), int(m.group(2) or 1), m.group(3)


def next_instance_ordinal(package: Path, prefix: str) -> int:
    """Which instance of `prefix`'s workflow a materialization into `package`
    would be — 1 for the first, 2 for the second, and so on.

    WITHIN THE GOAL, and that is now the only radius there is: the run
    compartment the ordinal was once scoped to is extinguished (7.607 E2b),
    so the goal's own `taskforce.csv` is the roster of every seat it has ever
    materialized and the one honest source for the count.

    MAX + 1, never COUNT + 1. A goal whose second instance was materialized
    and whose first was later removed must not hand the next instance an
    ordinal already spent — the composition is stable precisely because a name
    once written is never reused and never rewritten."""
    top = 0
    for row in _csv_rows(package / TASKFORCE_NAME):
        parsed = parse_instance_seat_name((row.get("seat") or "").strip())
        if parsed and parsed[0] == prefix:
            top = max(top, parsed[1])
    return top + 1


def compose_seat_name(prefix: str, ordinal: int, seat: str) -> str:
    """THE seat-name composer — the single function every nested-instance name
    goes through (criterion 8's "the SAME single naming function")."""
    if not FOUR_LETTERS_RE.match(prefix or ""):
        raise Refuse(
            "workflow-prefix-invalid",
            f"cannot compose a seat name from prefix {prefix!r} — the declared "
            "prefix is FOUR lowercase letters",
        )
    if not ID_RE.match(seat or ""):
        raise Refuse(
            "seat-invalid",
            f"cannot compose a seat name for {seat!r} — the seat id must be a "
            "legal id (lowercase kebab-case)",
        )
    if not isinstance(ordinal, int) or ordinal < 1:
        raise Refuse(
            "instance-ordinal-invalid",
            f"instance ordinal {ordinal!r} is not a positive integer — the first "
            "instance is 1 and carries NO ordinal in its name",
        )
    return f"{prefix}-{seat}" if ordinal == 1 else f"{prefix}-{ordinal}-{seat}"


def rename_after_cell(raw: str, rename: dict[str, str]) -> str:
    """A frozen `after` cell with its MEMBERS renamed and NOTHING else touched —
    Rule 13's "verbatim apart from the instance renaming" (criterion 8).

    ⚠ DELEGATES. `goal_cli.substitute_after_ids` is the ONE reading of an `after`
    cell's member ids; `add-seat`'s splice is its other caller. A second copy of
    the guard-span walk here was a second grammar waiting to drift."""
    return substitute_after_ids(raw, rename)


def nested_instance(package: Path, catalog_root: Path, workflow: str,
                    added: list[str]) -> dict:
    """`{prefix, ordinal, rename}` for materializing `workflow` as a NESTED
    INSTANCE into `package` — the catalog-id -> composed-name map every other
    surface of this run is re-keyed through.

    On the --workflow path `resolve_added` has already refused an absent or
    ambiguous manifest, so the glob below resolves exactly one folder. On the
    SINGLE-SEAT path (W7: `--seat <seat> --nested <workflow>`) it has NOT — the
    seat is resolved against seats.csv and the named workflow is never touched —
    so the glob is guarded here rather than raising IndexError out of a helper."""
    hits = sorted(catalog_root.glob(f"*/workflows/{workflow}/{workflow}.csv"))
    if not hits:
        raise Refuse(
            "nested-workflow-unresolvable",
            f"--nested names the instance series '{workflow}', and no "
            f"<component>/workflows/{workflow}/{workflow}.csv exists under the "
            "catalog root — there is no workflow to be the Nth of",
            str(catalog_root),
        )
    wf_dir = hits[0].parent
    prefix = read_workflow_prefix(wf_dir)
    ordinal = next_instance_ordinal(package, prefix)
    return {"prefix": prefix, "ordinal": ordinal, "workflow": workflow,
            "rename": {s: compose_seat_name(prefix, ordinal, s) for s in added}}


def rekey_bindings(bindings: dict, rename: dict[str, str]) -> None:
    """Re-key the LOADED bindings onto the composed names, IN MEMORY.

    ⚠ THE TWO-NAME MODEL, and the one place it is enforced (criterion 7). The
    bindings FILE stays keyed by CATALOG ID — nothing on disk is rewritten, so
    every live bindings file keeps working and `bindings-missing-seat` cannot
    fire on a composed name. The composed name exists only from here on, and
    only as a DISK name. Re-keyed rather than ALIASED because
    `check_bindings_cover` refuses an EXTRA key, and an alias set would be
    exactly that."""
    bindings["seats"] = {
        rename.get(seat, seat):
            (dict(entry, after=[rename.get(a, a) for a in entry["after"]])
             if isinstance(entry, dict) and isinstance(entry.get("after"), list)
             else entry)
        for seat, entry in bindings["seats"].items()}


def load_bindings(path: Path) -> dict:
    """Parse the --bindings JSON: per-seat executor binding + descriptor surface."""
    if not path.is_file():
        raise Refuse(
            "bindings-unreadable",
            "cannot read the bindings file this materialize run was given",
            str(path),
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refuse(
            "bindings-unreadable",
            f"bindings file is not valid JSON — {exc}",
            str(path),
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("seats"), dict):
        raise Refuse(
            "bindings-schema",
            "bindings file must be a JSON object carrying a 'seats' mapping "
            "(per-seat executor binding to materialize with)",
            str(path),
        )
    defaults = data.get("defaults", {})
    if not isinstance(defaults, dict):
        raise Refuse(
            "bindings-schema",
            "bindings 'defaults' must be a mapping when present",
            str(path),
        )
    return {"defaults": defaults, "seats": data["seats"], "path": str(path)}


def check_bindings_cover(bindings: dict, added: list[str],
                         whole_set: bool = True) -> None:
    """The bindings `seats` keys MUST cover the resolved set — a MISSING key is
    always a REFUSAL, never a default (the G-51 silent-default lesson).

    An EXTRA key is a refusal only when this run materializes a WHOLE set
    (`--workflow`), where the sheet and the manifest are meant to be the same
    set and a leftover key is a typo. A single-seat run (`--seat`) is cast by
    the sheet of the workflow that seat belongs to — `plan.json` casts all 17
    planning seats — so on that path every seat but one is legitimately
    "extra", and refusing made the collapsed wave-re-entry pass (which is
    exactly `--seat plan-planner --nested planning --bindings plan.json`)
    impossible to run at all. Measured live 2026-08-14 on the flagship goal:
    `bindings-extra-seat` naming all 16 other planning seats.
    # ponytail: the check that WOULD hold on the --seat path is "the sheet's
    # keys are a subset of that workflow's manifest" — it needs the manifest
    # read here, which this function has no access to. Missing-key protection
    # is unchanged and is what catches a typo in the seat actually being built.
    """
    missing = [s for s in added if s not in bindings["seats"]]
    if missing:
        raise Refuse(
            "bindings-missing-seat",
            "bindings file misses seat(s) "
            + ", ".join(f"'{s}'" for s in missing)
            + " of the set being materialized — a missing key is a refusal, "
            "never a default",
            bindings["path"],
        )
    extra = [s for s in bindings["seats"] if s not in added] if whole_set else []
    if extra:
        raise Refuse(
            "bindings-extra-seat",
            "bindings file names seat(s) "
            + ", ".join(f"'{s}'" for s in extra)
            + " outside the set being materialized — an extra key is a "
            "refusal, never ignored (a typo'd seat id must not pass silently)",
            bindings["path"],
        )
    for seat, entry in bindings["seats"].items():
        if not isinstance(entry, dict):
            raise Refuse(
                "bindings-schema",
                f"bindings entry for seat '{seat}' must be a mapping",
                bindings["path"],
            )
        internal = entry.get("after", [])
        if not isinstance(internal, list):
            raise Refuse(
                "bindings-schema",
                f"bindings 'after' for seat '{seat}' must be a list",
                bindings["path"],
            )
        unknown = [a for a in internal if a not in added]
        if unknown:
            raise Refuse(
                "bindings-after-unknown",
                f"bindings 'after' for seat '{seat}' names "
                + ", ".join(f"'{a}'" for a in unknown)
                + " outside the set being materialized — a per-seat 'after' is "
                "INTERNAL to the added workflow",
                bindings["path"],
            )


def effective_binding(bindings: dict, seat: str) -> dict:
    """defaults ∪ per-seat entry. Nothing is defaulted by CODE — every value
    comes from the bindings file (R-10: no policy number crosses this boundary)."""
    merged = dict(bindings["defaults"])
    merged.update(bindings["seats"][seat])
    return merged


def _manifest_after_ids(raw: str) -> list[str]:
    """Bare predecessor ids of a manifest `after` cell — the MEMBERSHIP and
    ordering view only; the frozen copy always writes the raw cell verbatim
    (Rule 13). A member may carry a `[guard]` suffix and a cell may join
    alternates with `|` (p-materializer-guard-suffix: the definition is
    legal; the tool parses it). Bracketed content is removed BEFORE the
    alternate split, so a `|` inside a guard value never splits — and an
    alternate after a bracketed guard is never dropped (the check_acyclic
    strip-then-split defect, #3386, is not replicated here)."""
    out: list[str] = []
    for part in raw.split(","):
        for alt in re.sub(r"\[[^\]]*\]", "", part).split("|"):
            alt = alt.strip()
            if alt:
                out.append(alt)
    return out


# ------------------------------------------- MC9 / 7.451: the row classifier
#
# A manifest row's `Seat/workflow` cell names a seat-id "or, instead of a seat, a
# nested workflow" (registry concept `workflow manifest`; workflows can call
# workflows). The two are THE SAME SHAPE — a lowercase-kebab id — so nothing in
# the member GRAMMAR separates them, and this file has until now read every row
# as a seat (`resolve_added` below: `ID_RE.match(seat)` then straight into the
# added set).
#
# ⚠ THAT IS NOT F-9a, AND THE DISTINCTION IS THE WHOLE RULE. The design's F-9a
# arm — "the grammar cannot distinguish the two kinds without a new manifest
# column" — reads the shape as the discriminator. It is not: the two kinds live
# in two different NAMESPACES, both already resolved a few lines below, and
# RESOLUTION decides what the shape cannot. Seat catalog only -> `seat`. Workflow
# manifest only -> `nested_workflow`. NEITHER -> refuse. BOTH -> refuse, and THAT
# input is the one a column would settle (F-9a's real radius: one colliding id,
# not the form).
#
# ⚠ THE BARE NAME COMES FROM THE ONE DECOMPOSITION, NEVER FROM A LOCAL STRIP.
# `after_member_grammar()` is goal_cli's import bridge to `coord.parse_after_member`
# (7.424/W1, the only reading of `name[key=value]` in this system). A guard does not
# change WHAT a reference names, so the guard is read and carried, never
# interpreted here. `_manifest_after_ids` above predates this and still strips
# brackets locally — it is a MEMBERSHIP view over an `after` cell, not a
# classification, and collapsing it is outside this task's grant; it stands as a
# finding, and it is this classifier's own copy-detector control (SK-9).

ManifestReference = collections.namedtuple(
    "ManifestReference", "kind name key value source")


def classify_manifest_reference(token: str, catalog_root: Path,
                                seats_catalog: dict | None = None
                                ) -> ManifestReference:
    """Classify ONE manifest row reference: `seat` or `nested_workflow`.

    REFUSES rather than defaulting to either class. An unresolvable reference read
    as a seat materializes a seat folder for a workflow that was never expanded;
    read as a workflow it globs for a manifest that does not exist. Both fail late,
    somewhere else, and neither says why — so the refusal happens here, named.
    """
    name, key, value, unsupported = after_member_grammar()(token)
    if unsupported:
        raise Refuse(
            "reference-alternate",
            f"manifest reference {token!r} is an OR-alternate — a row names ONE "
            "seat or ONE nested workflow, and `a|b` names neither. Alternates are "
            "an `after`-cell join, not a reference",
            str(catalog_root))
    if not name or not ID_RE.match(name):
        raise Refuse(
            "reference-invalid",
            f"manifest reference {token!r} decomposes to {name!r}, which is not a "
            "legal id (lowercase kebab-case). A bracketed token that is not the "
            "guard grammar `ref[field=value]` comes back whole and lands here — "
            "unparseable, never classified",
            str(catalog_root))
    if seats_catalog is None:
        seats_catalog = load_catalogs(catalog_root)[0]
    # The SAME resolution `resolve_added` performs for --seat and --workflow —
    # one namespace each, no second lookup rule invented for classification.
    seat_row = seats_catalog.get(name)
    manifests = sorted(catalog_root.glob(f"*/workflows/{name}/{name}.csv"))
    if seat_row is not None and manifests:
        raise Refuse(
            "reference-ambiguous",
            f"manifest reference {name!r} resolves BOTH as a seat-id "
            f"({seat_row.get('__source__')}) and as a workflow manifest "
            f"({manifests[0]}) — one column, two namespaces, and nothing in the "
            "row says which. This is the input a new manifest column would "
            "settle; a column is a registry shape change and is not this "
            "classifier's to introduce",
            str(catalog_root))
    if seat_row is not None:
        return ManifestReference("seat", name, key, value,
                                 str(seat_row.get("__source__") or ""))
    if len(manifests) > 1:
        raise Refuse(
            "workflow-ambiguous",
            f"manifest reference {name!r} resolves to {len(manifests)} workflow "
            "manifests: " + ", ".join(str(m) for m in manifests),
            str(catalog_root))
    if manifests:
        return ManifestReference("nested_workflow", name, key, value,
                                 str(manifests[0]))
    raise Refuse(
        "reference-unresolvable",
        f"manifest reference {name!r} resolves to NO seats.csv row and NO "
        f"<component>/workflows/{name}/{name}.csv under {catalog_root} — refused "
        "rather than defaulted to either class",
        str(catalog_root))


def resolve_added(args, catalog_root: Path,
                  seats_catalog: dict) -> tuple[list[str], dict, dict]:
    """Resolve the seat set this run materializes.

    --seat resolves against the SEAT CATALOG (seats.csv), never the manifest —
    a cataloged seat that no manifest row references is legal by construction.
    --workflow resolves against the workflow manifest
    {catalog-root}/<component>/workflows/<W>/<W>.csv.

    Returns (added seat ids in manifest order, internal after map, RAW manifest
    `after` cells — the byte-verbatim text the frozen copy writes, Rule 13).
    """
    if args.seat:
        if not ID_RE.match(args.seat):
            raise Refuse(
                "seat-invalid",
                f"seat id '{args.seat}' is not a legal id (lowercase "
                "kebab-case) — nothing materialized",
            )
        if args.seat not in seats_catalog:
            # ⚠ THE INSTANCE-NAMED COMPLETION, and it is the ONLY lane that
            # completes one. A composed name (`plan-6-plan-dod-judge`) is a
            # DISK name and never a catalog key (§ the two-name model above),
            # so a row already carrying one has no lane back to its
            # definition: `--nested` mints the NEXT ordinal, so it cannot
            # complete an EXISTING plan-6 row, and this refusal was what left
            # the daemon's unbuilt-seat repair (`queue-request.js`) unable to
            # build any nested-instance row at all. Under --force-partial —
            # the flag that means "the row exists, complete its missing half"
            # — the catalog row is resolved through the BASE name and ALIASED
            # onto the composed one, exactly as the `--nested` path aliases
            # its own rename map. Everything downstream (folder, descriptor,
            # registry byte-match) then carries the composed name unchanged.
            # ⚠ D37 (2026-08-20) ADDS THE REFRESH LANE TO THIS SAME ALIAS, and it is ONE
            # PREDICATE, not a second branch. `--refresh` sets `repass=True`, and
            # repass+force-partial is refused (`repass-with-force-partial`), so before this
            # line NO argv combination reached a composed name with `--refresh`: every
            # `plan-4-*` sheet on the two live goals was unrefreshable BY STRUCTURE, which is
            # the whole of loose-end L133. The two flags mean the same thing HERE — "the row
            # already exists under its composed name; resolve its DEFINITION through the base"
            # — and differ only in what they then do with it, which this function does not
            # decide. `refresh-would-drop-keys` and `repass-with-force-partial` are untouched.
            parsed = parse_instance_seat_name(args.seat)
            base = parsed[2] if parsed else ""
            if not ((getattr(args, "force_partial", False)
                     or getattr(args, "refresh", False))
                    and base and base in seats_catalog):
                raise Refuse(
                    "seat-unknown",
                    f"seat '{args.seat}' resolves to no row in any seats.csv "
                    f"under {catalog_root} — nothing materialized",
                    str(catalog_root),
                )
            seats_catalog[args.seat] = seats_catalog[base]
        return [args.seat], {args.seat: []}, {args.seat: ""}

    wf = args.workflow
    if not ID_RE.match(wf):
        raise Refuse(
            "workflow-invalid",
            f"workflow id '{wf}' is not a legal id (lowercase kebab-case) — "
            "nothing materialized",
        )
    manifests = sorted(catalog_root.glob(f"*/workflows/{wf}/{wf}.csv"))
    if not manifests:
        raise Refuse(
            "workflow-unknown",
            f"workflow '{wf}' resolves to no manifest "
            f"<component>/workflows/{wf}/{wf}.csv under {catalog_root} — "
            "nothing materialized",
            str(catalog_root),
        )
    if len(manifests) > 1:
        raise Refuse(
            "workflow-ambiguous",
            f"workflow '{wf}' resolves to {len(manifests)} manifests: "
            + ", ".join(str(m) for m in manifests),
        )
    mpath = manifests[0]
    with mpath.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        if MANIFEST_SEAT_COLUMN not in fields or MANIFEST_AFTER_COLUMN not in fields:
            raise Refuse(
                "manifest-header",
                f"workflow manifest lacks the required "
                f"'{MANIFEST_SEAT_COLUMN}'/'{MANIFEST_AFTER_COLUMN}' columns",
                str(mpath),
            )
        added: list[str] = []
        internal_after: dict[str, list[str]] = {}
        internal_after_raw: dict[str, str] = {}
        for row in reader:
            seat = (row.get(MANIFEST_SEAT_COLUMN) or "").strip()
            if not seat:
                continue
            if not ID_RE.match(seat):
                raise Refuse(
                    "manifest-seat-invalid",
                    f"manifest row '{seat}' is not a legal seat id",
                    str(mpath),
                )
            if seat in internal_after:
                raise Refuse(
                    "manifest-duplicate-seat",
                    f"manifest lists seat '{seat}' twice",
                    str(mpath),
                )
            raw = (row.get(MANIFEST_AFTER_COLUMN) or "").strip()
            preds = _manifest_after_ids(raw)
            added.append(seat)
            internal_after[seat] = preds
            internal_after_raw[seat] = raw
    if not added:
        raise Refuse(
            "manifest-empty",
            f"workflow manifest carries no seat rows — nothing to materialize",
            str(mpath),
        )
    for seat, preds in internal_after.items():
        unknown = [p for p in preds if p not in internal_after]
        if unknown:
            raise Refuse(
                "manifest-after-unknown",
                f"manifest row '{seat}' lists predecessor(s) "
                + ", ".join(f"'{p}'" for p in unknown)
                + " outside the materialized set — a manifest 'after' is "
                "internal to the workflow",
                str(mpath),
            )
    return added, internal_after, internal_after_raw


def validate_after(args, package: Path, added: list[str]) -> list[str]:
    """VALIDATION 2 of the dag-05 trio (workflow.md DAG-authoring Rule 8, run
    side): every --after member must resolve to an existing taskforce.csv row —
    a dangling predecessor is an edge that never fires and the seat sits
    READY-never, silently. A member naming a seat of the ADDED set resolves too
    (its row lands in this same act); that form is legal HERE and is then
    refused by validation 1 when it closes a cycle — SC-5's descendant-attach
    arm reaches check_acyclic, never this refusal."""
    if args.root:
        return []
    members = [m.strip() for m in args.after.split(",") if m.strip()]
    if not members:
        raise Refuse(
            "after-empty",
            "--after carries no member — pass --root to materialize a DAG "
            "root, never an empty list",
        )
    existing = {(r.get("seat") or "").strip()
                for r in _csv_rows(package / TASKFORCE_NAME)}
    existing |= set(added)
    unresolved = [m for m in members if m not in existing]
    if unresolved:
        raise Refuse(
            "after-unresolved",
            "--after member(s) "
            + ", ".join(f"'{m}'" for m in unresolved)
            + f" resolve to no {TASKFORCE_NAME} row — the seat would sit "
            "READY-never, silently; nothing materialized",
            str(package / TASKFORCE_NAME),
        )
    return members


def resolved_milestones(package: Path) -> set[str]:
    """The milestone-ids `milestones.csv` resolves — the ONE predicate BOTH
    milestone guards read (`--milestone-id` here, a MILESTONE pass folder's
    m{N} in `_pass_values`), so the two can never drift into disagreeing
    about what a resolvable milestone is (task 7.678)."""
    return {(r.get("milestone-id") or "").strip()
            for r in _csv_rows(package / MILESTONES_NAME)}


def validate_milestone(args, package: Path) -> None:
    """--milestone-id must resolve to a milestones.csv row or the run refuses."""
    if not args.milestone_id:
        return
    if args.milestone_id not in resolved_milestones(package):
        raise Refuse(
            "milestone-unresolved",
            f"--milestone-id '{args.milestone_id}' resolves to no "
            f"{MILESTONES_NAME} row — nothing materialized",
            str(package / MILESTONES_NAME),
        )


def check_repass(package: Path, added: list[str]) -> None:
    """--repass INVERTS check_collisions: the seat folder AND its registry row
    must ALREADY exist, because a repass re-renders a descriptor a previous
    materialize wrote — it never mints a seat.

    This is G-planner-0804-1502's chosen fix (alternative (a), re-materialize
    the descriptor when a pass opens). Until it existed the act was impossible:
    check_collisions hard-refuses an existing seat and --force-partial demands
    a BYTE-MATCH, so an ephemeral seat relaunched into a new pass could only
    keep booting on the previous pass's render."""
    rows = {(r.get("seat") or "").strip()
            for r in _csv_rows(package / TASKFORCE_NAME)}
    for seat in added:
        target = seat_home(package, seat) / "seat.md"
        if not target.is_file():
            raise Refuse(
                "repass-no-descriptor",
                f"--repass re-renders an EXISTING descriptor and "
                f"seats/{seat}/seat.md does not exist — materializing a new "
                "seat is the plain run, never --repass",
                str(target),
            )
        if seat not in rows and not standing_seat(package):
            # A standing-seat home has no taskforce.csv to disagree with.
            raise Refuse(
                "repass-no-row",
                f"--repass leaves the registry untouched and {TASKFORCE_NAME} "
                f"carries no row for seat '{seat}' — the descriptor and the "
                "row would disagree from the first launch",
                str(package / TASKFORCE_NAME),
            )


def repass_descriptors(plan: dict) -> list[str]:
    """The --repass write: REPLACE each existing seat.md with the freshly
    rendered one, in place (`_rewrite_in_place`, the discipline every other
    writer here uses). Nothing else is touched — no registry row, no run
    register, no package surface."""
    written: list[str] = []
    for seat in plan["added_seats"]:
        target = seat_home(Path(plan["package"]), seat) / "seat.md"
        _rewrite_in_place(target, plan["descriptors"][seat])
        written.append(str(target))
    return written


def check_collisions(package: Path, added: list[str], force_partial: bool) -> None:
    """Materialize never overwrites, never merges. A re-run after a partial
    failure is the deliberate --force-partial (its byte-match completion is
    dag-05's; the skeleton only lets the flag pass these gates)."""
    if force_partial:
        return
    rows = {(r.get("seat") or "").strip() for r in _csv_rows(package / TASKFORCE_NAME)}
    for seat in added:
        folder = seat_home(package, seat)
        if folder.exists():
            raise Refuse(
                "seat-exists",
                f"seats/{seat}/ already exists — materialize never "
                "overwrites; completing a partial failure is the deliberate "
                "--force-partial",
                str(folder),
            )
        if seat in rows:
            raise Refuse(
                "registry-row-exists",
                f"a {TASKFORCE_NAME} row for seat '{seat}' already exists — "
                "materialize never duplicates a registry row",
                str(package / TASKFORCE_NAME),
            )


# ── THE GOAL-LOCAL SEAT INPUT LANE (W7, R7 · adv C75) ────────────────────────
#
# THE DEFECT IT CLOSES (D5 defect 1). A planning pass AUTHORS its milestone's
# build team inside the goal: `planning/current/manifest.csv` names the seats
# and `planning/current/seats/<seat>/` holds each one's prompt+task pair. The
# binder then REGISTERS those seats as `taskforce.csv` rows — and nothing can
# build them, because this script's only input lane was the COMPONENT catalog
# and a goal-authored seat is in no component. The rows exist, the folders do
# not, and the goal's next hop never happens. Measured on the flagship: `tf-2`
# carries `seam-toolsmith` and `seam-author`, seats no `seats.csv` anywhere
# names.
#
# WHAT THIS LANE IS, AND WHY IT IS A SYNTHESIS RATHER THAN A SECOND LOADER.
# The goal-authored files are ALREADY in the catalog's whole-file pool form —
# frontmatter `id:` over one kind-named section (`<role>` for a prompt,
# `<task-goal>` for a task), which is exactly what `goal_cli._pool_file_row`
# reads. So this lane does NOT parse them, does not assemble them, and holds no
# second opinion about what a seat is. It SHAPES the goal's own product into a
# component catalog and hands it to the one existing pipeline: `load_catalogs`,
# `resolve_added`, `assemble_seat`, the atomic append, `check_acyclic` — all
# unchanged, all still the single implementation. A second loader would be a
# second answer to "what is this seat", and the two would drift.
#
# ⚠ THE CHECKS BELOW ARE THIS LANE'S OWN, AND THEY EXIST BECAUSE COMPONENT-LINT
# NEVER SEES THESE FILES (adv, C75). Lint runs over the component catalog; a
# goal-authored seat is born after lint and dies with the goal, so every
# structural guarantee lint provides has to be re-established here or it simply
# is not there. Two classes, named as the ruling names them:
#   · DANGLING REFERENCE — a manifest seat with no definition folder, a
#     definition folder missing its prompt or its task half, an `after` member
#     naming nothing that exists.
#   · COLLISION — one id used twice inside the lane, or a lane id that SHADOWS
#     a component-catalog id. Nothing guarded the second case anywhere in this
#     system before now: a goal that named its seat `plan-binder` would have
#     silently out-ranked (or been out-ranked by) the cataloged one, depending
#     on `rglob` order.
# W6 unifies these with component-lint later; until then they live here, in the
# lane that needs them.
#
# ⚠ THE LANE IS A DERIVED INDEX AND IS REBUILT ON EVERY INVOCATION, INCLUDING
# UNDER `--dry-run`. It carries no fact of its own — every byte is a copy of
# `planning/current/` — so a persisted lane would be a second home for one fact
# and stale exactly when the pass re-authors a seat. It is written INSIDE the
# goal rather than into a temp dir for one mechanical reason: `rbtv:`-prefixed
# `exposes` references resolve through `_rbtv_repo_root(comp_dir)`, which walks
# UP from the component directory looking for the workspace, and a /tmp path has
# no workspace above it. `--dry-run`'s contract — append no registry row, create
# no seat folder — is untouched; rebuilding a derived index is not a mutation of
# the goal's product, and doing it under --dry-run is what makes the dry run a
# real LINT rather than a guess about one.
GOAL_LOCAL_SOURCE = ("planning", "current")   # what the planning pass writes
GOAL_LOCAL_LANE = "seat-lane"                 # the synthesized TREE root
GOAL_LOCAL_MODULE = "goal-local"              # the one module inside the tree
GOAL_LOCAL_COMPONENT = "goal-local"           # the one component inside it
# ⚠ THE MODULE LEVEL IS LOAD-BEARING, not decoration. `_ref_target` resolves a
# `module/component/part` reference as `comp_dir.parent.parent/<module>/
# <component>` — "the tree root above the modules", identical arithmetic for
# the mirror and the rbtv repo, both `<tree>/<module>/<component>/`. A lane
# shaped `<tree>/<component>/` puts that arithmetic one level too high: it
# lands in the goal's own `planning/current/`, where no module lives, so EVERY
# cross-module reference a goal-authored seat carries dies with
# `exposes-ref-dangling`. Measured 2026-08-15: the flagship's interactive seat
# took that refusal on the `meta/master/slack-message-format` skill the
# interactive-seat injection folds in, and it refused the WHOLE lane on every
# cadence. The mirror's module dirs are SYMLINKED in beside the module below so
# the resolution finds them — outside the returned catalog root, because
# `load_catalogs` rglobs it and a merge of the two catalogs is ruled against.
GOAL_LOCAL_WORKFLOW = "goal-local"            # …and the one workflow manifest
GOAL_LOCAL_REUSE = "source.md"                # "this seat is CATALOGED, not local"
# The discriminator between the two halves of a seat pair. It is the kind-named
# section, the same thing `_pool_file_row` keys on — never the filename, which
# the authoring seat chooses freely (`toolsmith.md` + `build-validate-seams.md`
# on the flagship). Measured against the live catalog before being relied on:
# 19/19 prompts carry `<role>` and none carries `<task-goal>`; 29/29 tasks carry
# `<task-goal>` and none carries `<role>`.
GOAL_LOCAL_HALVES = (("prompts", "role"), ("tasks", "task-goal"))


def _goal_local_frontmatter(path: Path) -> dict:
    """The parsed frontmatter of a goal-authored prompt/task, or a refusal.

    Shared by the id check and the seats.csv writer so a cage key is copied
    from the file the author wrote, never invented. The loader is not used:
    its refusal would name a path inside the synthesized lane."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        raise Refuse(
            "goal-local-frontmatter-missing",
            f"'{path.name}' has no frontmatter block, so it declares no `id:` — "
            "a goal-authored prompt or task is a whole-file definition and the "
            "id is the only thing that names it",
            str(path))
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise Refuse(
            "goal-local-frontmatter-unparseable",
            f"'{path.name}' frontmatter is not valid YAML — {str(exc).strip()}. "
            "An unquoted `description:` carrying a colon is the usual cause",
            str(path))
    ident = str(fm.get("id") or "").strip()
    if not ID_RE.match(ident):
        raise Refuse(
            "goal-local-id-missing",
            f"'{path.name}' declares id {ident or '(none)'!r}, which is not a "
            "legal id (lowercase kebab-case) — nothing materialized",
            str(path))
    return fm


def _goal_local_id(path: Path) -> str:
    return str(_goal_local_frontmatter(path).get("id") or "").strip()


def _goal_local_csv_cell(fm: dict, key: str) -> str:
    """Copy a prompt-half cage key into a seats.csv cell.

    A YAML list joins comma-separated — the format `_cage_frontmatter` splits."""
    val = fm.get(key)
    if val is None or val == "":
        return ""
    if isinstance(val, list):
        return ",".join(str(x).strip() for x in val if str(x).strip())
    return str(val).strip()


def _goal_local_pair(seat_dir: Path) -> dict | None:
    """`{prompt: (id, path), task: (id, path)}` for ONE goal-authored seat, or
    None when the folder declares itself a CATALOGED REUSE.

    A reuse folder holds `source.md` — a pointer at cataloged definitions, never
    a definition — so the seat belongs to the COMPONENT lane and this lane must
    not shadow it with a copy. That is the flagship's `plan-dod-judge`."""
    files = sorted(p for p in seat_dir.glob("*.md") if p.name != GOAL_LOCAL_REUSE)
    if not files:
        if (seat_dir / GOAL_LOCAL_REUSE).is_file():
            return None
        raise Refuse(
            "goal-local-definition-empty",
            f"'{seat_dir.name}' has a definition folder carrying no .md file at "
            "all — neither a prompt/task pair nor a `source.md` naming the "
            "cataloged definitions it reuses",
            str(seat_dir))
    found = {}
    for pool, section in GOAL_LOCAL_HALVES:
        hits = [p for p in files
                if re.search(rf"<{section}>.*?</{section}>",
                             p.read_text(encoding="utf-8"), re.S)]
        if len(hits) != 1:
            raise Refuse(
                "goal-local-definition-ambiguous",
                f"'{seat_dir.name}' resolves {len(hits)} <{section}> file(s) and "
                f"a seat is exactly ONE prompt and ONE task — "
                + (", ".join(p.name for p in hits) or "none found")
                + f". The half is identified by its <{section}> section, never "
                "by filename",
                str(seat_dir))
        found[pool] = (_goal_local_id(hits[0]), hits[0])
    return found


def build_goal_local_lane(package: Path, component_root: Path) -> Path:
    """Shape the goal's OWN planning product into a component catalog and return
    its root. Every refusal below is a check component-lint would have made."""
    src = package.joinpath(*GOAL_LOCAL_SOURCE)
    manifest = src / "manifest.csv"
    if not manifest.is_file():
        raise Refuse(
            "goal-local-manifest-missing",
            f"--goal-local reads the goal's own planning product and there is no "
            f"{'/'.join(GOAL_LOCAL_SOURCE)}/manifest.csv — this goal has run no "
            "planning pass, so it authored no seats and there is nothing to "
            "build from",
            str(manifest))
    rows = _csv_rows(manifest)
    if MANIFEST_SEAT_COLUMN not in (rows[0] if rows else {}):
        raise Refuse(
            "goal-local-manifest-header",
            f"the goal's manifest lacks the '{MANIFEST_SEAT_COLUMN}' column",
            str(manifest))
    # ---- read the lane, one seat at a time -----------------------------------
    lane, after_raw, order = {}, {}, []
    for row in rows:
        seat = (row.get(MANIFEST_SEAT_COLUMN) or "").strip()
        if not seat:
            continue
        if seat in after_raw:
            raise Refuse(
                "goal-local-duplicate-seat",
                f"the goal's manifest lists seat '{seat}' twice",
                str(manifest))
        after_raw[seat] = (row.get(MANIFEST_AFTER_COLUMN) or "").strip()
        order.append(seat)
        seat_dir = src / "seats" / seat
        if not seat_dir.is_dir():
            raise Refuse(
                "goal-local-definition-missing",
                f"the goal's manifest names seat '{seat}' and "
                f"{'/'.join(GOAL_LOCAL_SOURCE)}/seats/{seat}/ does not exist — "
                "the pass registered a seat it never authored, which is exactly "
                "the registered-but-unbuilt state this lane exists to end",
                str(seat_dir))
        pair = _goal_local_pair(seat_dir)
        if pair is not None:                  # None = cataloged reuse, not ours
            lane[seat] = pair
    if not lane:
        raise Refuse(
            "goal-local-empty",
            "every seat in the goal's manifest is a CATALOGED REUSE (a "
            f"`{GOAL_LOCAL_REUSE}` pointer) — this lane would synthesize an "
            "empty catalog, and the component lane already serves those seats",
            str(src))
    # ---- COLLISION, both directions (adv C75) --------------------------------
    catalog_ids = set()
    try:
        cat_seats, cat_prompts, cat_tasks = load_catalogs(component_root)
        catalog_ids = set(cat_seats) | set(cat_prompts) | set(cat_tasks)
    except CatalogRefusal:
        # A broken COMPONENT catalog is not this lane's failure to report — the
        # run reaches `load_catalogs` again a few lines later and refuses there,
        # with the component lane's own words. Degrading to "check nothing"
        # would be worse than useless, so it is DISCLOSED rather than silent:
        # the shadow check below simply has no catalog to compare against.
        catalog_ids = set()
    seen: dict[str, str] = {}
    for seat, pair in lane.items():
        for pool, (ident, path) in pair.items():
            if ident in seen:
                raise Refuse(
                    "goal-local-id-collision",
                    f"id '{ident}' is declared twice inside the goal's own "
                    f"seats — by {seen[ident]} and by {seat}/{path.name}. One "
                    "name, one meaning: the catalog is a dict and the second "
                    "one would silently replace the first",
                    str(path))
            seen[ident] = f"{seat}/{path.name}"
            if ident in catalog_ids:
                raise Refuse(
                    "goal-local-shadows-catalog",
                    f"'{seat}' declares id '{ident}', which the COMPONENT "
                    f"catalog already carries. A goal-authored definition may "
                    "never shadow a cataloged one — which of the two wins would "
                    "be decided by rglob order, i.e. by nothing",
                    str(path))
        if seat in catalog_ids:
            raise Refuse(
                "goal-local-shadows-catalog",
                f"the goal authored a seat named '{seat}' and the COMPONENT "
                "catalog already carries that seat id — rename the goal's seat; "
                "a cataloged seat is reused through a "
                f"`{GOAL_LOCAL_REUSE}` pointer, never re-authored under its name",
                str(src / "seats" / seat))
    # ---- DANGLING REFERENCE: every `after` member must resolve ---------------
    registry = {(r.get("seat") or "").strip()
                for r in _csv_rows(package / TASKFORCE_NAME)}
    known = set(order) | registry | catalog_ids
    for seat in order:
        for member in _manifest_after_ids(after_raw[seat]):
            if member not in known:
                raise Refuse(
                    "goal-local-after-dangling",
                    f"the goal's manifest says '{seat}' comes after '{member}', "
                    f"and '{member}' is neither a seat of this manifest, nor a "
                    f"row already in {TASKFORCE_NAME}, nor a cataloged seat — "
                    "the edge points at nothing and the seat would never become "
                    "ready",
                    str(manifest))
    # ---- SHAPE it into a catalog, atomically ---------------------------------
    root = src / GOAL_LOCAL_LANE
    staging = src / f".{GOAL_LOCAL_LANE}.tmp"
    if staging.exists():
        shutil.rmtree(staging)
    scomp = staging / GOAL_LOCAL_MODULE / GOAL_LOCAL_COMPONENT
    (scomp / "prompts").mkdir(parents=True)
    (scomp / "tasks").mkdir(parents=True)
    (scomp / "workflows" / GOAL_LOCAL_WORKFLOW).mkdir(parents=True)
    # THE DERIVED MARKER, planted by the regenerator (spec-component-map §4).
    # The lane root is goal-instantiated — it exists only once a materialize has
    # run — so there is no template to plant it in: the builder that creates the
    # root is the only thing that can carry it, and it writes it into STAGING so
    # the marker lands in the same atomic replace as the tree it describes.
    # `source: ..` is this marker's own parent, `planning/current/`, which is the
    # ONE home of every byte below.
    (staging / DERIVED_MARKER_NAME).write_text(
        "source: ..\n"
        "regenerator: materialize-seats.py — the goal-local lane builder "
        f"(`{GOAL_LOCAL_LANE}`, rmtree + restage)\n"
        "\n"
        "This whole tree is a DERIVED index of the parent directory "
        "`planning/current/`, rebuilt from scratch on every materialize "
        "(including `--dry-run`). It carries no fact of its own. An edit made "
        "here is silently lost on the next pass — apply it to the source and "
        "let the pass regenerate this copy.\n",
        encoding="utf-8")
    # The sibling modules a goal-authored `exposes:` may reach across (see the
    # constant block). `component_root` is the MODULE the component lane is
    # read from (`.rbtv/mirror/meta`), so its PARENT is the tree root above the
    # modules — the same level `_ref_target` counts back to. Symlinks, not
    # copies: the mirror is the one home, and `rglob` does not recurse
    # symlinked dirs, so even a future catalog scan that reached this level
    # would not swallow the component lane.
    # ⚠ MODULE DIRS ONLY. Since the catalogs moved into the rbtv REPO (2026-08-22), the tree
    # root above the modules is the repo root, whose `.git`, `.pytest_cache`, `__pycache__`
    # are directories too. A symlinked `.git` inside the goal collides with the cage's
    # `**/.git` private-scope mask — bwrap cannot bind a cover onto a symlink and the seat
    # dies at launch (measured 2026-08-22 15:30Z on meet's leader: every launch into the
    # goal failed with `Can't bind mount … seat-lane/.git: No such file or directory`).
    for mod in sorted(p for p in component_root.parent.iterdir()
                      if p.is_dir() and not p.name.startswith('.') and p.name != '__pycache__'):
        if mod.name != GOAL_LOCAL_MODULE:
            (staging / mod.name).symlink_to(mod.resolve(), target_is_directory=True)
    (scomp / "component.md").write_text(
        "---\ndescription: \"Seats this goal's own planning pass authored — a "
        "DERIVED index of planning/current/, rebuilt on every materialize and "
        "never edited by hand.\"\n---\n\n# goal-local\n", encoding="utf-8")
    for pool, _section in GOAL_LOCAL_HALVES:
        for seat, pair in lane.items():
            ident, path = pair[pool]
            shutil.copyfile(path, scomp / pool / f"{ident}.md")
    with (scomp / "seats.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["seat-id", "executor", "task", "staffing-hints",
                    "description", "goal-writes", "cage-grants", "rw-paths",
                    "on-fail-relaunch"])
        for seat in order:
            if seat not in lane:
                continue
            pfm = _goal_local_frontmatter(lane[seat]["prompts"][1])
            w.writerow([seat, lane[seat]["prompts"][0], lane[seat]["tasks"][0],
                        "", f"goal-authored seat ({seat})",
                        _goal_local_csv_cell(pfm, CAGE_GOAL_WRITES_COLUMN),
                        _goal_local_csv_cell(pfm, CAGE_GRANTS_COLUMN),
                        _goal_local_csv_cell(pfm, CAGE_RW_COLUMN),
                        _goal_local_csv_cell(pfm, ON_FAIL_RELAUNCH_COLUMN)])
    with (scomp / "workflows" / GOAL_LOCAL_WORKFLOW /
          f"{GOAL_LOCAL_WORKFLOW}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([MANIFEST_SEAT_COLUMN, MANIFEST_AFTER_COLUMN, "i/o", "Modality"])
        for seat in order:
            if seat not in lane:
                continue
            # The `after` cell is copied VERBATIM — the same Rule 13 discipline
            # the nested path uses. A cell re-derived here would be a second
            # rendering of the goal's own DAG.
            w.writerow([seat, after_raw[seat], "", ""])
    # Replaced, never merged: a lane rebuilt on top of a previous one would keep
    # a seat the pass has since deleted, and that seat would still materialize.
    if root.exists():
        shutil.rmtree(root)
    staging.replace(root)
    return root / GOAL_LOCAL_MODULE


def normalize_seat_rows(seats_cat: dict) -> None:
    """The ruled mirror seats.csv header pairs `executor` with `task`
    (topic-2-authoring-contract.md § 2); goal_cli's assemble_seat reads
    `prompt-id`/`executor` and `task-id` only, so a ruled-shape row would
    silently lose its whole TASK half (task-goal/scope/done-contract — the
    seat's done contract, contract § 2). Alias task -> task-id on the DATA
    before the one assembler runs — row normalization, not a second
    assembler (SK-7)."""
    for row in seats_cat.values():
        if not (row.get("task-id") or "").strip() and (row.get("task") or "").strip():
            row["task-id"] = row["task"]


def assemble_all(added: list[str], bindings: dict,
                 catalogs: tuple[dict, dict, dict], units: dict) -> dict[str, str]:
    """Assemble every added seat IN MEMORY first (a refusal on seat 7 of 7
    must leave zero files) — through goal_cli's ONE assembler."""
    seats_cat, prompts_cat, tasks_cat = catalogs
    return {
        seat: assemble_seat(seat, effective_binding(bindings, seat),
                            seats_cat, prompts_cat, tasks_cat, units)
        for seat in added
    }


# ------------------------------------------------ dag-04: descriptor surface


def _coord_validate_seat():
    """The ONE import this command takes from coord.py (F6): the launch-time
    harness+model predicate, imported so the two checks can never drift.
    coord.py's import is side-effect-free (constants, regexes, function
    definitions — verified at dag-04) and drags no runtime state; if that
    ever changes, THIS IMPORT FAILING LOUDLY is the correct outcome. NEVER
    re-implement the predicate here — a second copy is the drift the rule
    exists to prevent."""
    # The kit is `ignite/coord/` since the component-first move — a SIBLING component
    # of this one, no longer this file's own directory.
    kit_dir = Path(__file__).resolve().parent.parent / "coord"
    if str(kit_dir) not in sys.path:
        sys.path.insert(0, str(kit_dir))
    try:
        from coord import validate_seat
    except Exception as exc:  # loud, machine-readable — never a crash
        raise Refuse(
            "coord-import",
            f"cannot import validate_seat from coord.py — {exc}; refusing "
            "rather than re-implementing the predicate (F6)",
        ) from exc
    return validate_seat


def _coord_iospec_outputs():
    """coord.py's shared declared-outputs resolver (D3, outputs-unify) — imported for F6's
    reason: the io-spec `## Outputs` block is graded at check-out by `iospec_outputs`, and a
    materialize-time reading made by a SECOND parser is how a seat materializes clean and then
    refuses at its own ending. NEVER re-implement the grammar here."""
    # The kit is `ignite/coord/` since the component-first move — a SIBLING component
    # of this one, no longer this file's own directory.
    kit_dir = Path(__file__).resolve().parent.parent / "coord"
    if str(kit_dir) not in sys.path:
        sys.path.insert(0, str(kit_dir))
    try:
        from coord import iospec_outputs
    except Exception as exc:  # loud, machine-readable — never a crash
        raise Refuse(
            "coord-import",
            f"cannot import iospec_outputs from coord.py — {exc}; refusing "
            "rather than re-implementing the resolver (D3)",
        ) from exc
    return iospec_outputs


def _coord_iospec_grammar():
    """coord.py's `## Outputs` SECTION regex and its path-token regex — the same two objects
    `iospec_outputs` itself runs (D36, 2026-08-20). Imported for F6's reason and D3's: the
    projection below has to find the section it appends to, and to decide which backticked
    token in a `<scope>` `Write:` bullet is a token the GATE will resolve. A second copy of
    either grammar here is a descriptor that projects what the check-out cannot read.
    NEVER re-implement them."""
    # The kit is `ignite/coord/` since the component-first move — a SIBLING component
    # of this one, no longer this file's own directory.
    kit_dir = Path(__file__).resolve().parent.parent / "coord"
    if str(kit_dir) not in sys.path:
        sys.path.insert(0, str(kit_dir))
    try:
        from coord import _IOSPEC_OUTPUTS_SECTION, _IOSPEC_PATHISH
    except Exception as exc:  # loud, machine-readable — never a crash
        raise Refuse(
            "coord-import",
            f"cannot import the io-spec grammars from coord.py — {exc}; refusing "
            "rather than re-implementing them (D3/D36)",
        ) from exc
    return _IOSPEC_OUTPUTS_SECTION, _IOSPEC_PATHISH


def _resolve_inline_refs(text: str, units: dict, seat: str) -> str:
    """Inline every `Reference: <id>@latest` line inside a block body with the
    referenced unit's body (d-run3-assembled-shape (i)); iterate so a
    referenced body's own references resolve too, with a depth cap so a
    reference cycle refuses instead of spinning."""
    for _ in range(10):
        if not _INLINE_REF_RE.search(text):
            return text

        def _sub(m: re.Match) -> str:
            uid = m.group(1)
            if uid not in units:
                raise Refuse(
                    "inline-ref-dangling",
                    f"inline reference '{uid}@latest' inside a unit body of "
                    f"seat '{seat}' resolves to no cognitive-unit file — a "
                    "dead pointer must not reach the emitted descriptor",
                )
            return units[uid]["content"]

        text = _INLINE_REF_RE.sub(_sub, text)
    raise Refuse(
        "inline-ref-depth",
        f"inline references in seat '{seat}' did not resolve within 10 "
        "passes — a reference cycle among unit bodies",
    )


def _pass_values(seat: str, b: dict, package: str) -> tuple[str, str]:
    """(pass folder, pass tag) for this seat's binding — ("", "") when the
    binding declares no `pass-folder`.

    The pass folder is a per-PASS value and a descriptor is a per-SEAT
    artifact: freezing one into the other at materialization and never
    refreshing it is the single root cause under B4, B5 and
    G-planner-0804-1502. So it arrives as a BINDING (per materialize run),
    is validated against the two legal forms, and is checked against the
    run's OPEN passes before a single character of it reaches a descriptor.
    """
    raw = str(b.get("pass-folder", "") or "").strip()
    if not raw:
        return "", ""
    if raw == PASS_FOLDER_NONE:
        return PASS_FOLDER_NONE, ""
    folder = raw if raw.endswith("/") else raw + "/"
    m = PASS_FOLDER_RE.match(folder)
    if not m:
        raise Refuse(
            "pass-folder-invalid",
            f"bindings for seat '{seat}' carry pass-folder '{raw}' — the only "
            "legal forms are 'planning/m{N}-{milestone-name}/' (a MILESTONE "
            "pass, d-milestone-id-and-folder-form) and 'planning/briefing-"
            "<name>/' (a BRIEFING pass, r-briefing-pass-planning-home); a "
            "wrong write path is worse than an absent one, so it is refused, "
            "never coerced",
        )
    pass_id = folder[len("planning/"):-1]

    # Task 7.678 — the ROW half. A MILESTONE pass folder names an m{N}; that
    # m{N} must resolve to a milestones.csv ROW, the SAME guarantee
    # --milestone-id carries (validate_milestone), through the same predicate
    # and the same refusal code. Shape was validated above and the pass may be
    # open, and neither says the milestone EXISTS: a planning pass ran live
    # under `m0-bootstrapping` against a ZERO-ROW milestones.csv and nothing
    # objected.
    #
    # ⚠ REFUSED HARD — no `if rows:` bootstrap tolerance like the passes.csv
    # guard below. That tolerance is not a precedent to copy here, it is the
    # mechanism of the incident: an empty registry is exactly the state the
    # unbacked pass ran in, so tolerating it re-opens the hole this closes.
    # The m{N} NAME stays fully legitimate (`d-planning-is-milestone-zero` —
    # planning IS milestone zero); what is required is the ROW, and writing it
    # is the remedy the refusal names.
    mid = m.group(1)
    if mid and mid not in resolved_milestones(Path(package)):
        raise Refuse(
            "milestone-unresolved",
            f"seat '{seat}' would be rendered for pass folder '{raw}', whose "
            f"milestone '{mid}' resolves to no {MILESTONES_NAME} row — the "
            "same guarantee --milestone-id carries. The m{N} naming is legal "
            "(d-planning-is-milestone-zero); the ROW is what is missing, so "
            f"write '{mid}' into {MILESTONES_NAME} and re-run. Refused with "
            "no bootstrap tolerance: an empty registry is the state the "
            "unbacked planning pass ran in",
            str(Path(package) / MILESTONES_NAME),
        )

    # G-planner-0804-1502, the staleness half: the pass a descriptor is
    # rendered FOR must be a pass this run has OPEN. A package carrying no
    # passes.csv gets NO check (bootstrap-tolerant — the registry was minted
    # 2026-08-04 and older packages predate it); that absence is a missing
    # guard, never a silently satisfied one.
    rows = _csv_rows(Path(package) / PASSES_NAME)
    if rows:
        open_ids = [(r.get("pass-id") or "").strip() for r in rows
                    if not (r.get("closed") or "").strip()]
        if pass_id not in open_ids:
            raise Refuse(
                "pass-not-open",
                f"seat '{seat}' would be rendered for pass '{pass_id}', which "
                f"is not an OPEN row of {PASSES_NAME} (open: "
                + (", ".join(open_ids) or "none")
                + ") — a descriptor rendered for a closed or unknown pass is "
                "the stale render G-planner-0804-1502 measured three times, "
                "the third one behaviorally",
                str(Path(package) / PASSES_NAME),
            )
    return folder, (m.group(1) or m.group(2))


def substitute_pass(text: str, seat: str, folder: str, tag: str) -> str:
    """Substitute the resolved pass folder into a rendered descriptor — and
    REFUSE when a placeholder would survive with no pass folder bound.

    Silently emitting the placeholder is the current behaviour and it IS the
    defect: it produces a descriptor that looks complete and hands its reader
    a hunt. A binding that carries no pass-folder is fine for a seat whose
    units name no pass surface; it is a refusal the moment one does."""
    if folder == PASS_FOLDER_NONE:
        return text
    if not folder:
        hit = next((p for p in PASS_PLACEHOLDERS if p in text), None)
        if hit is None:
            return text
        raise Refuse(
            "pass-folder-missing",
            f"seat '{seat}' renders the pass placeholder '{hit}' and its "
            "bindings carry no 'pass-folder' — the executor would derive its "
            "own write path (the hunt P3 forbids). Declare pass-folder: "
            "'planning/<pass folder>/' for this pass, or pass-folder: "
            f"'{PASS_FOLDER_NONE}' when the unit MENTIONS the placeholder "
            "rather than naming a write surface with it",
        )
    for token in PASS_PLACEHOLDERS[:-1]:
        text = text.replace(token, folder)
    return text.replace(PASS_PLACEHOLDERS[-1], tag)


def _descriptor_frontmatter(seat: str, b: dict, package: str,
                            seats_cat: dict, plan: dict) -> dict:
    """The ruled emitted key set, in its ruled order (d-seatmd-keys-dag04-
    schema; the table in dag-04's task file). `seat:` — never `id:` (B3).
    `class:` is never emitted and is refused as an input; `relays:` IS
    emitted — a pass-through, present only when the bindings declare it
    (d-relays-frontmatter-passthrough)."""
    for key in b:
        if key == "class":
            raise Refuse(
                "class-withdrawn",
                f"bindings for seat '{seat}' carry 'class:' — the WITHDRAWN "
                "spelling (r-agent-type-field-name, G-217); write "
                "agent_type: " + "|".join(AGENT_TYPES) + " instead",
            )
        if key not in ALLOWED_BINDING_KEYS:
            raise Refuse(
                "binding-key-unknown",
                f"bindings for seat '{seat}' carry unknown key '{key}' — an "
                "unknown key is a refusal, never ignored",
            )

    harness = str(b.get("harness", "") or "").strip()
    model = str(b.get("model", "") or "").strip()
    effort = str(b.get("effort", "") or "").strip()
    unbound = open_binding(seat, b, Path(package))
    if not effort and not unbound:
        raise Refuse(
            "effort-missing",
            f"bindings for seat '{seat}' carry no 'effort' — the "
            "harness·model·effort triple is required (check_bindings "
            "compares it against the taskforce.csv row)",
        )

    agent_type = str(b.get("agent_type", "") or "").strip()
    if agent_type not in AGENT_TYPES:
        raise Refuse(
            "agent-type-invalid",
            f"bindings for seat '{seat}' carry agent_type "
            f"'{agent_type or '(absent)'}' — required, one of "
            + "|".join(AGENT_TYPES),
        )

    description = str(b.get("description", "") or "").strip() \
        or str((seats_cat.get(seat) or {}).get("description", "") or "").strip()
    if not description:
        raise Refuse(
            "description-missing",
            f"seat '{seat}' resolves no description from bindings or the "
            "seat catalog row — required, one line",
        )

    cwd_mode = str(b.get("cwd-mode", "") or "").strip()
    if cwd_mode != "seat-folder":
        raise Refuse(
            "cwd-mode-undecidable",
            f"bindings for seat '{seat}' carry cwd-mode "
            f"'{cwd_mode or '(absent)'}' — the only ruled mode is "
            "'seat-folder' ({package}/seats/<seat>/); an undecidable cwd is "
            "refused, never defaulted",
        )
    cwd = str(seat_home(Path(package), seat)) + "/"

    mode = str(b.get("mode", "") or "").strip()
    if mode and mode not in DESCRIPTOR_MODES:
        raise Refuse(
            "mode-invalid",
            f"bindings for seat '{seat}' carry mode '{mode}' — one of "
            + "|".join(DESCRIPTOR_MODES),
        )
    if not mode:
        mode = MODE_DEFAULTS.get(harness, "")
        if not mode:
            raise Refuse(
                "mode-undecidable",
                f"seat '{seat}' carries no explicit mode: and harness "
                f"'{harness}' has no ruled emission default (only opencode -> "
                "one-shot, claude -> interactive; codex included has NONE) — "
                "an undecidable mode is refused loudly, never defaulted (F5)",
            )

    ctx_raw = b.get("ctx-refresh")
    ctx: int | None = None
    if ctx_raw not in (None, ""):
        if mode == "one-shot":
            raise Refuse(
                "ctx-refresh-on-one-shot",
                f"seat '{seat}' is mode: one-shot and carries "
                f"ctx-refresh: {ctx_raw} — a one-shot never reaches a "
                "mid-session threshold, so the key is a permanently dead "
                "control that reads as a live one; refused (F4)",
            )
        try:
            ctx = int(str(ctx_raw))
        except ValueError:
            raise Refuse(
                "ctx-refresh-invalid",
                f"seat '{seat}' carries non-integer ctx-refresh "
                f"'{ctx_raw}'",
            ) from None

    window = str(b.get("window", "") or "").strip()
    if window:
        plan["warnings"].append(
            f"seat '{seat}': window: '{window}' disables in-place renew "
            "(G-154, seat_placement) — consequence printed per seat; the "
            "tradeoff stays the binding author's",
        )

    senders_raw = b.get("senders")
    senders = ""
    if senders_raw not in (None, ""):
        parts = [str(p).strip() for p in
                 (senders_raw if isinstance(senders_raw, list)
                  else str(senders_raw).split(","))]
        parts = [p for p in parts if p]
        kept = [p for p in parts if p != "engineer"]
        if len(kept) != len(parts):
            plan["warnings"].append(
                f"seat '{seat}': senders entry 'engineer' dropped — never "
                "emitted (d-engineer-retired)",
            )
        if parts and not kept:
            raise Refuse(
                "senders-empty",
                f"seat '{seat}' senders allow-list is empty after dropping "
                "'engineer' (d-engineer-retired) — emitting nothing would "
                "silently flip the seat to UNBOUNDED; state the intended "
                "allow-list or remove the key deliberately",
            )
        senders = ",".join(kept)

    close = str(b.get("close", "") or "").strip()
    if not close and mode == "one-shot" and agent_type == "worker":
        # F8 — a memoryless one-shot worker gets the mechanical close (G-23, no memory.md) by
        # construction, so `close-seat` never has anything to write for it. (The rationale this
        # comment used to cite — that the deleted `cmd_close` spawned a claude closer regardless
        # of the closed seat's harness — no longer applies: that verb and its closer-seat spawn
        # path were deleted whole [T2-R9].)
        close = "mechanical"

    fm: dict = {
        "seat": seat,            # `seat:`, never `id:` — closes B3
        "description": description,
        "cwd": cwd,
        "agent_type": agent_type,
    }
    # The pass this descriptor was rendered FOR, present only when the binding
    # declares it. It is what makes a stale descriptor DETECTABLE by its own
    # occupant: before this key, "which pass is this seat on?" was inferred
    # from a description string, and G-planner-0804-1502 is what that costs.
    pass_folder, _ = _pass_values(seat, b, package)
    if pass_folder:
        fm["pass"] = pass_folder
    if unbound:
        # The three are ABSENT, never empty: an empty value reads as a binding
        # that failed, and `mode` stays because the seat's rhythm is its own.
        fm["mode"] = mode
    else:
        fm |= {
            "harness": harness,
            "model": model,
            "effort": effort,
            "mode": mode,
        }
    if ctx is not None:
        fm["ctx-refresh"] = ctx
    if window:
        fm["window"] = window
    if senders:
        fm["senders"] = senders
    if close:
        fm["close"] = close
    # The PASS-THROUGH keys: emitted verbatim when the definition declares
    # them, ABSENT (never empty) when it does not. `relays` joined this set
    # when A-40 was ruled (a) — d-relays-frontmatter-passthrough; it is the
    # seat's relay-path declaration for a role word, and both the addressing
    # resolution and the reap exemption hang off it (module docstring).
    for key in ("auto-wake", "ephemeral", "broadcast", "component",
                "relays", "addressable"):
        val = b.get(key)
        if val not in (None, ""):
            fm[key] = val
    # The SEAT CAGE, last: the bwrap sandbox spawn.js composes by reading these
    # very keys back out of the emitted file (owner-ruled 2026-08-10).
    fm |= _cage_frontmatter(seat, seats_cat)
    return fm


def render_descriptors(plan: dict, seats_cat: dict, units: dict, *,
                       resolve_inline: bool = True,
                       reorder: bool = True) -> None:
    """dag-04 — build every emitted descriptor text into plan['descriptors'],
    refusing the WHOLE batch (nothing on disk yet) on any bad row. The
    `resolve_inline`/`reorder` knobs exist ONLY so the selftest's red arms
    can prove their controls fail; every real caller uses the defaults."""
    package = plan["package"]

    # F6 — the whole-batch model/harness gate, BEFORE any write, through
    # coord.py's own predicate (never a re-implementation).
    validate_fn = _coord_validate_seat()
    bad: list[str] = []
    for seat in plan["added_seats"]:
        b = plan["bindings"][seat]
        if open_binding(seat, b, Path(package)):
            continue  # nothing to validate: the triple is deliberately absent
        reason = validate_fn({
            "agent": seat,
            "harness": str(b.get("harness", "") or "").strip(),
            "model": str(b.get("model", "") or "").strip(),
        })
        if reason:
            bad.append(f"seat '{seat}': {reason}")
    if bad:
        raise Refuse(
            "model-invalid",
            "validate_seat refuses the WHOLE batch before any write (F6): "
            + "; ".join(bad)
            + " — zero folders, zero registry rows",
        )

    kind_rank = {k: i for i, k in enumerate(KIND_ORDER)}
    plan["descriptors"] = {}
    for seat in plan["added_seats"]:
        b = plan["bindings"][seat]
        fm = _descriptor_frontmatter(seat, b, package, seats_cat, plan)

        assembled = plan["assembled"][seat]
        fm_m = _FM_RE.match(assembled)
        if not fm_m:
            raise Refuse(
                "assembled-unparseable",
                f"assembled projection for seat '{seat}' carries no "
                "frontmatter fence — assembler drift",
            )
        body = assembled[fm_m.end():]
        matches = list(_BLOCK_RE.finditer(body))
        if not matches:
            # The PRECONDITION, not a side effect: a catalog that cannot
            # produce a non-empty body refuses (B1/B2 silent-empty class).
            raise Refuse(
                "empty-assembly",
                f"no cognitive-unit block assembled for seat '{seat}'",
            )
        blocks = [(m.group(1), m.group(0)) for m in matches]
        if not any(kind == "permissions" for kind, _ in blocks):
            raise Refuse(
                "no-permissions",
                f"seat '{seat}' resolves no permissions unit — a seat that "
                "boots with no permissions block is a live seat with "
                "undeclared authority; HARD GATE, refused",
            )
        intro = body[:matches[0].start()]

        if resolve_inline:
            blocks = [(kind, _resolve_inline_refs(text, units, seat))
                      for kind, text in blocks]
        if reorder:
            # Contract §1 fixed kind order — never CSV column order. The
            # sort is stable: same-kind blocks and unlisted kinds keep the
            # assembler's relative order (unlisted kinds after the listed).
            blocks = sorted(
                blocks, key=lambda kt: kind_rank.get(kt[0], len(KIND_ORDER)))

        # D5 (seed-gates, 2026-08-19): REQUIRES-REACH, derived from the
        # done-contract's NAMED probe lane. A contract line
        # `probe lane: `<command …>`` names a lane the seat must be able to
        # RUN once caged; the stools DoD judge burned two waves because that
        # requirement lived in prose and nothing that admits a launch read
        # it. The first word of each named lane becomes a machine-readable
        # `- cli `<name>`` entry in the io-spec's `## Requires-reach`
        # section — the D3 single-surface idiom — which the pre-enqueue gate
        # (`envelope/cage-admission.js#admitLaneReach`) checks against the
        # seat's `exposed-clis:` declarations. `path` entries are authorable
        # in the io-spec unit directly; nothing here derives them. A
        # hand-authored section is respected: derivation only ADDS entries
        # whose cli name is not already declared in it.
        lane_cmds = []
        for kind, text in blocks:
            if kind == "done-contract":
                lane_cmds += _PROBE_LANE_RE.findall(text)
        lane_clis = []
        for cmd in lane_cmds:
            first = cmd.strip().split()[0] if cmd.strip() else ""
            if first and first not in lane_clis:
                lane_clis.append(first)
        if lane_clis:
            io_idx = next((i for i, kt in enumerate(blocks)
                           if kt[0] == "io-spec"), None)
            io_text = blocks[io_idx][1] if io_idx is not None else ""
            if io_idx is None or "</io-spec>" not in io_text:
                plan["warnings"].append(
                    f"seat '{seat}': requires-reach underivable — its done "
                    f"contract names probe lane(s) {lane_cmds!r} but the "
                    "seat resolves no io-spec block to carry the "
                    "`## Requires-reach` section; the pre-enqueue gate "
                    "cannot check the lane (D5, 2026-08-19)")
            else:
                fresh = [c for c in lane_clis
                         if f"cli `{c}`" not in io_text]
                if fresh:
                    if "## Requires-reach" in io_text:
                        section = "".join(f"- cli `{c}`\n" for c in fresh)
                        new_text = io_text.replace(
                            "## Requires-reach\n",
                            "## Requires-reach\n" + section, 1)
                    else:
                        section = ("\n## Requires-reach\n"
                                   + "".join(f"- cli `{c}`\n"
                                             for c in fresh))
                        new_text = io_text.replace(
                            "</io-spec>", section + "</io-spec>", 1)
                    blocks[io_idx] = (blocks[io_idx][0], new_text)

        # ---- D36 (2026-08-20): THE CONCRETE DESTINATION, PROJECTED FROM THE TASK ------------
        #
        # THE DEFECT, measured: the reusable PROMPT owns `<io-spec>` and MUST stay use-case
        # neutral (`references/kind-io-spec.md` point 5 — one `checker.md` serves check-clarity,
        # check-scope, check-edges…), so its `## Outputs` is schema prose. The per-instance TASK
        # owns `<scope>` and names the real file (`Write: … at `planning/current/findings-
        # clarity.md``). Both render into ONE seat.md — and the done gate reads only the first.
        # Result: 94 of 101 live seats were real file producers whose `done` the D5 gate refused
        # every sitting, and the catalog's own reference doc contradicted itself (point 2: "the
        # Outputs section IS READ BY MACHINE — declare the artifact by its path").
        #
        # The fix is a PROJECTION, not an authoring campaign: schema + description stay the
        # prompt's words verbatim; the concrete destination is INSTANCE data, so the renderer —
        # the one actor that holds prompt and task at once — writes it into the surface the gate
        # reads. KG-consistent (`concepts/output.md`): an i/o spec output is schema + purpose; a
        # destination is a fact about THIS seat.
        #
        # ⚠ ADDITIVE, AND ONLY INTO A SECTION THAT RESOLVES NOTHING. A seat whose `## Outputs`
        # already yields tokens is left byte-untouched (its author declared, and a projection
        # beside a declaration is two authorities); a `chat` seat declares a non-file product
        # and needs no destination; a scope with no `Write:` token projects nothing at all.
        # ⚠ AND IT MAKES THE GATE STRONGER, NEVER WEAKER: every projected token is a path the
        # check-out will now REQUIRE on disk. A seat that declared nothing and did nothing used
        # to record `unverified` for want of a declaration; it now records `unverified` for want
        # of the file — the honest reason.
        io_idx = next((i for i, kt in enumerate(blocks) if kt[0] == "io-spec"), None)
        if io_idx is not None:
            io_text = blocks[io_idx][1]
            _decl, _toks, _chat = _coord_iospec_outputs()(io_text)
            _sect_re, _path_re = _coord_iospec_grammar()
            _sect = _sect_re.search(io_text)
            if _decl and not _toks and not _chat and _sect:
                scope_text = next(
                    (text for kind, text in blocks if kind == "scope"), "")
                projected: list[str] = []
                for bullet in _SCOPE_WRITE_RE.findall(scope_text):
                    for tok in _path_re.findall(bullet):
                        if tok not in projected:
                            projected.append(tok)
                if projected:
                    rows = "\n".join(_PROJECTED_OUTPUT_BULLET.format(token=tok)
                                     for tok in projected)
                    body = _sect.group(1)
                    # The LAST section of the block swallows the closing tag (its `\Z`
                    # boundary); the bullets go INSIDE the block, never after it.
                    cut = body.find("</io-spec>")
                    head, tail = (body[:cut], body[cut:]) if cut != -1 else (body, "")
                    new_body = (head.rstrip("\n") + "\n" + rows
                                + ("\n" + tail if tail else ""))
                    blocks[io_idx] = (
                        blocks[io_idx][0],
                        io_text[:_sect.start(1)] + new_body + io_text[_sect.end(1):])

        # The assembly-lockfile refs (frozen `<unit-id>@<version>` values)
        # carry over from the assembler's frontmatter, after the scalars.
        try:
            afm = yaml.safe_load(fm_m.group(1)) or {}
        except yaml.YAMLError as exc:
            raise Refuse(
                "assembled-unparseable",
                f"assembled frontmatter for seat '{seat}' is not YAML — "
                f"{exc}",
            ) from exc
        for key, val in afm.items():
            if key in ("id", "description", *BINDING_COLUMNS):
                continue
            fm[key] = val

        # D3 (outputs-unify, 2026-08-18): the `outputs:` frontmatter key is RETIRED — the
        # io-spec `## Outputs` block is the ONE declared-outputs surface. The bindings door
        # already refuses it as an unknown key; this closes the one hole left, the assembled-
        # frontmatter carry-over above. Refused LOUDLY, never emitted, never dropped silently:
        # a descriptor materialized with the key would be refused again at its own check-out
        # (`coord.declared_outputs`), one seat too late.
        if "outputs" in fm:
            raise Refuse(
                "outputs-key-retired",
                f"seat '{seat}' would materialize with an `outputs:` frontmatter key — "
                "RETIRED (D3, 2026-08-18). Declare each output in the io-spec `## Outputs` "
                "block as a backticked goal-relative token carrying a `/` and an extension "
                "(`seats/<seat>/plan.md`, or `./plan.md`); the block is the one surface both "
                "the cage-admission gate and the done-contract grading read",
            )

        # The seat's harness-materialized instruments, grouped by method
        # (d-seat-exposes-frontmatter) — already validated against
        # exposure.csv by resolve_seat_exposes, emitted so the descriptor
        # itself shows what was minted beside it.
        exp = (plan.get("exposes") or {}).get(seat)
        if exp:
            fm["exposes"] = exp

        # …and the SANDBOX-realized half (d-path-exposes-authorable): the
        # `path` parts resolved to `<part-id> <abs entry point>`. The cage's
        # ONE declaration reader (spawn.js seatDeclaresList) consumes this
        # key, so the enabled-CLI set rides the seat.md surface every other
        # grant class rides — an occupant cannot widen it, because seat.md is
        # ro-carved inside the cage. It is emitted HERE and not by the
        # derived-surface pass on purpose: a file beside seat.md is WRITABLE
        # from inside the seat, which would make a grant self-grantable.
        clis = [f"{pid} {(rdir / (row.get('entry-point') or '').strip()).resolve()}"
                for m, pid, row, rdir
                in (plan.get("expose_parts") or {}).get(seat, ())
                if m == "path"]
        if clis:
            fm["exposed-clis"] = clis

        # W6 — the CLI-DERIVED WRITE ROOTS, resolution variant B: the
        # materializer walked seat -> skills -> CLIs -> roots, so spawn.js only
        # reads. Emitted HERE for the same reason as `exposed-clis:` above —
        # seat.md is ro-carved in-cage, so a grant that lands here is not
        # self-grantable, and a file beside it would be.
        # ⚠ It is NOT a pierce and never becomes one: private.json's deny list
        # is applied AFTER every grant at spawn, and `resolve_cli_write_roots`
        # already refused any root landing on a private entry.
        # ⚠ STALENESS: these roots are resolved from exposure.csv AT
        # MATERIALIZE, so an edit to a `write-roots` cell reaches a live seat
        # only through `materialize-seats.py --repass`. A resolved-AT stamp was
        # considered and REFUSED: a timestamp in the descriptor makes every
        # repass emit a different file, which destroys the byte-identical skip
        # this whole emitter is built on. The baked LIST is the observable — a
        # repass that changes it is exactly the staleness signal, and a
        # `--dry-run` repass reports it without writing.
        cli_roots = (plan.get("cli_write_roots") or {}).get(seat)
        if cli_roots:
            fm["cli-write-roots"] = cli_roots

        tail = ""
        if fm["mode"] == "one-shot":
            # F10 — a one-shot pays for CLI discovery inside its single
            # session; carry the exact command string VERBATIM.
            #
            # ⚠ CHECK-IN IS DELIBERATELY NOT HERE, and its absence is still
            # the fix, not an omission — but the REASON has changed. It is no
            # longer lane-dependent: since F1 (owner ruling 2026-08-17) BOTH
            # lanes check in, the daemon lane's check-in simply being PANELESS
            # (it registers against the seat's own open `sessions.csv` row
            # instead of a tmux pane). What stands is the placement: the boot
            # prompt is composed on EVERY boot and already carries the check-in
            # sentence with the lane's amendment, while this file is LANE-BLIND
            # — a seat is materialized before its lane is known. One
            # instruction, one home, the one that knows.
            #
            # ⚠ CHECK-OUT STAYS, on both lanes, and now actually WORKS on both:
            # it gates on the ACTIVE roster row a check-in writes, which the
            # daemon lane had no way to produce until F1. It is the sole
            # producer of `incomplete` and of the leader route flag.
            tail = (
                "\n<!-- one-shot boot (F10): the exact coordination command "
                "for this seat, verbatim. Check-IN is ordered by the boot "
                "prompt, which knows the lane and its amendment; this file "
                "does not. -->\n\n"
                "One-shot boot — end your session with this command exactly "
                "(check in first — your boot prompt orders it):"
                "\n\n"
                f"    coordinate --package {package} --as {seat} checkout\n"
            )

        # The DERIVED write surface, on EVERY descriptor. Unconditional on
        # purpose: the trap is a property of the cage template, not of any one
        # seat's declaration, so a seat with no `goal-writes` still meets it on
        # the five ledgers the router sends every seat to. WHICH of the two
        # sections it carries is NOT unconditional — an uncaged staff seat has
        # no cage to enumerate; `_write_surface_section` owns that choice.
        tail += _write_surface_section(
            seat, fm.get(CAGE_GOAL_WRITES_COLUMN) or [])

        # Same yaml.safe_dump call goal_cli uses at cmd_materialize — an
        # unparseable descriptor is unproducible by construction (G-256).
        header = ("---\n"
                  + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
                  + "---\n")
        # B4/B5 — the substitution fires on the WHOLE emitted text, the last
        # act before it becomes the descriptor: a fix judged at the source
        # instead of at the render is the failure this exists to prevent.
        folder, tag = _pass_values(seat, b, package)
        plan["descriptors"][seat] = substitute_pass(
            header + intro + "\n\n".join(text for _, text in blocks)
            + "\n" + tail, seat, folder, tag)

        # D3 planner extension: a ZERO-TOKEN `## Outputs` block is a LOUD condition at
        # materialize — the seat's `done` will grade `outputs-undeclarable` (nothing
        # verifiable), and the author is told NOW, while the block is still cheap to fix.
        # A WARNING rather than a refusal, deliberately: live workflow io-specs are prose
        # today, and refusing them would freeze every existing definition to unblock a
        # grading nicety — the loud check-out classification is the enforcing half.
        # ⚠ D36 (2026-08-20) RE-RULED THIS AND IT IS STILL A WARNING, on MEASURED ground, not
        # on the old habit. After the projection above, 63 of the 101 live seats of the two
        # production goals resolve a token and 32 non-chair seats still do not — their tasks
        # name their destinations SLASHLESS (`task-dag.md` under a separately-named
        # `planning/current/`), which `_IOSPEC_PATHISH` does not resolve and this file will not
        # guess at. A refusal would therefore refuse to re-render 32 LIVE descriptors and to
        # mint m4's taskforce at all — freezing production to enforce a grading nicety, which
        # is exactly the trade the D3 note already refused. The RED half lives in `--selftest`
        # (`OUTPROJ-3`): the warning must FIRE, by name, on a seat that still resolves nothing.
        # ⚠ A `chat` seat is DECLARED and silent here — the check-out admits its `done`.
        _decl, _toks, _chat = _coord_iospec_outputs()(plan["descriptors"][seat])
        if _decl and not _toks and not _chat:
            plan["warnings"].append(
                f"seat '{seat}': outputs-undeclarable — its io-spec `## Outputs` section "
                f"yields ZERO resolvable path tokens (a token is backticked, carries a `/` "
                f"and an extension: `seats/<seat>/plan.md`) and its task's `<scope>` "
                f"`Write:` clause named none to project (D36, 2026-08-20). Its `done` will "
                f"be recorded `outputs-undeclarable`, i.e. NOTHING VERIFIED (D3, "
                f"2026-08-18) — unless this seat produces no file at all, in which case "
                f"declare `- Schema: chat` in that block")


# ---------------------------------------------------------------- plan


def build_plan(package: Path, added: list[str], internal_after: dict,
               internal_after_raw: dict, attach_after: list[str],
               assembled: dict, bindings: dict, args,
               creation: list[dict]) -> dict:
    """The write plan: created package surfaces first (dag-06), then
    descriptors, then the registry append — never another order (orphan
    folders are the strictly safer half-state)."""
    writes = [
        {"kind": "package-surface", "surface": c["surface"],
         "path": c["path"]}
        for c in creation
    ]
    # Descriptor AND its AGENTS.md pointer, per seat, in the order
    # emit_seat_descriptors writes them. The pointer is DECLARED here rather than
    # left as an undisclosed side effect: this file's own rule is that a command
    # which cannot show you what it would emit forces review of the source instead
    # of the render, and a --dry-run that under-reports its own writes is that
    # failure in miniature.
    for seat in added:
        writes.append({"kind": "seat-descriptor", "seat": seat,
                       "path": str(seat_home(package, seat) / "seat.md")})
        for name in ("CLAUDE.md", "AGENTS.md"):
            writes.append({"kind": "seat-guidance", "seat": seat,
                           "path": str(seat_home(package, seat) / name)})
    writes.append({
        "kind": "taskforce-append",
        "path": str(package / TASKFORCE_NAME),
        "rows": len(added),
    })
    return {
        "package": str(package),
        "creation": creation,
        "added_seats": list(added),
        "internal_after": internal_after,
        "internal_after_raw": internal_after_raw,
        "attach_after": attach_after,
        "root": bool(args.root),
        "milestone_id": args.milestone_id or "",
        "force_partial": bool(args.force_partial),
        "bindings": {seat: effective_binding(bindings, seat) for seat in added},
        "assembled": assembled,
        "writes": writes,
        "warnings": [],
    }


def result_of(plan: dict, dry_run: bool) -> dict:
    """The --json return value: {ok, package, added_seats[], writes[],
    taskforce_rows_appended, warnings[]}. In a --dry-run result the appended
    count is the PLANNED append (under --force-partial: only the MISSING rows)."""
    registry = plan.get("registry") or {}
    appended = plan.get("rows_appended")
    if appended is None:
        appended = len(registry.get("append_lines", plan["added_seats"]))
    result = {
        "ok": True,
        "dry_run": dry_run,
        "package": plan["package"],
        "added_seats": plan["added_seats"],
        "writes": plan["writes"],
        "taskforce_rows_appended": appended,
        "warnings": plan["warnings"],
    }
    if dry_run:
        # The RENDER, not just the write plan. A command that cannot show you
        # what it would emit forces every review to judge the SOURCE instead
        # of the render — which is exactly how 43 pass placeholders survived
        # into every descriptor unnoticed (B4).
        result["descriptors"] = plan["descriptors"]
    return result


# ------------------------------------------- dag-06 goal-package creation


def _read_creation_source(surface: str, opt: str, raw: str) -> bytes:
    """The caller-supplied base text for one created surface — read and
    validated, NEVER invented or defaulted. budget.json must already carry
    the floor the launch gate will read (budget.py read_floor's own checks,
    restated here so a floor-less budget fails at CREATION, not at the first
    launch) — the CHECK is structural; no floor NUMBER exists in this file
    (R-10, r-floor-single-source)."""
    path = Path(raw)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise Refuse(
            "create-input-unreadable",
            f"{opt} names a file this run cannot read ({exc}) — the created "
            f"{surface} is a byte-copy of it, so nothing was created",
            raw,
        ) from exc
    if not data.strip():
        raise Refuse(
            "create-input-empty",
            f"{opt} names an empty file — an empty {surface} is the "
            "silent-default failure this step exists to refuse",
            raw,
        )
    if surface == "budget.json":
        try:
            floors = (json.loads(data.decode("utf-8")).get("floors") or {})
            floor = floors.get("launch_refuse_mb")
        except (ValueError, AttributeError, UnicodeDecodeError) as exc:
            raise Refuse(
                "create-input-invalid",
                f"{opt} is not a JSON object ({exc}) — the launch gate reads "
                "the created budget.json (r-floor-single-source), so a "
                "broken copy would refuse every launch",
                raw,
            ) from exc
        if not isinstance(floor, int) or isinstance(floor, bool) or floor <= 0:
            raise Refuse(
                "create-input-invalid",
                f"{opt} declares no positive-integer floors.launch_refuse_mb "
                f"(found {floor!r}) — every launch against the created "
                "package would refuse FloorUndeclared/FloorUnreadable; this "
                "command copies the caller's declaration and NEVER supplies "
                "a floor of its own (R-10, r-floor-single-source)",
                raw,
            )
    return data


def derive_addressable_register(package: Path) -> bytes | None:
    """The addressable register this goal is born with, or None (7.569).

    A goal folder's siblings under the goals root include the STANDING-SEAT
    homes (`_<seat>/`, `standing_seat` above — `.rbtv/goals/_channel-master/`
    is the live one). Each such home's `seat.md` states for itself whether it
    accepts mail from outside its own package. Every home that declares
    `addressable: non-member` becomes ONE ROW, in sorted order, as a path
    RELATIVE to the created package — which is what coord.py resolves the row
    against (`load_addressable`).

    A path, never a name: the name and the role word are read from the
    descriptor at use time, so this file cannot claim an address on anybody's
    behalf. No door, or a door that never opted in -> None, and no register is
    created: the run then behaves exactly as every run behaves today.

    ⚠ THE RELATIVE PATH IS COMPUTED, NEVER CARRIED. Since 7.607 E2b the
    package IS the goal folder, so the door is ONE level up; a register text
    written for the extinct `runs/run-N/` compartment points three levels up
    and resolves to nothing. Deriving it here is what keeps the two halves in
    step with the layout instead of with a frozen string."""
    rows = []
    try:
        siblings = sorted(package.parent.iterdir())
    except OSError:
        return None
    for home in siblings:
        if not home.name.startswith("_") or not home.is_dir():
            continue
        try:
            text = (home / "seat.md").read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        fm = text[:end] if end != -1 else text
        if not re.search(r"^addressable:\s*non-member\s*$", fm, re.M):
            continue
        rel = PurePosixPath(os.path.relpath(home / "seat.md", package).replace(os.sep, "/"))
        rows.append(f"{rel},scaffold,at-run-creation")
    if not rows:
        return None
    return (ADDRESSABLE_HEADER + "\n" + "\n".join(rows) + "\n").encode()


def plan_package_creation(package: Path, args) -> list[dict]:
    """dag-06 — plan the package creation/completion WITHOUT writing
    (d-bootstrap-mechanics-ruled (b)): at the opening of a brand-new goal the
    working surfaces do not exist, so the MASTER's bootstrap materialize must
    create the surfaces a goal needs before a seat can check in. (7.607 E2b:
    the package IS the goal folder — there is no `runs/run-N/` to mint.)
    Derived from the live run-2 package + coord.py's own expectations:

      seats/          coord.py workers_dir + package discovery
      coordination/   coord.py's state home (its files land on demand)
      taskforce.csv   header-only, the run-2 live header — the registry the
                      launch gate's check_bindings reads
      state.csv       header-only, the ruled run-3 state-cursor header
                      (r-stage0-state-cursor-interim-convention (a)/(b))
      CLAUDE.md       CALLER-SUPPLIED (--claude-md)     \\  d-run3-seeds-
      budget.json     CALLER-SUPPLIED (--budget-json)  /  from-run2-amended:
                                                       never invented here
      addressable.csv OPTIONAL (7.569): --addressable byte-copies a supplied
                      register; a bootstrap creation without one DERIVES the
                      rows from the standing-seat doors that declare
                      `addressable: non-member` themselves, and creates
                      nothing when none does

    Ask-(f) RULING ENCODED (`d-run3-seeds-from-run2-amended`, 2026-07-29):
    both content surfaces arrive as caller-supplied input FILES — run-2's
    versions as amended by the authored designs, carried by the caller
    (dag-16's bootstrap job). budget.json takes the caller-supplied-file
    option of the dag-06 task (consistent with that ruling): a missing input
    REFUSES loudly naming it; a silently-defaulted floor or an invented
    CLAUDE surface is the failure this refusal exists to prevent.

    DELIBERATELY NOT CREATED (each has its own writer/author):
      sessions.csv / messages.md / workers.md / state.json — coord.py and
      team-monitor create them on demand (script-managed state);
      milestones.csv / seed.md / planning/ / bars.md and the other run-2
      accretions — authored content owned by the goal machinery and the
      authoring tasks, never command-invented.

    ⚠ 7.607 E2b — THE "CREATE THE PACKAGE FOLDER" MODE IS DELETED, and it is
    the ruling below that deletes it rather than a simplification. The package
    IS the goal folder (design-lock item 8), and this command has always
    refused to create a goal: "creating a goal is rbtv-goal's act, never this
    command's". With the compartment gone, creating an absent package WOULD BE
    creating a goal, so an absent package is now exactly the refusal that
    sentence already named. What survives — and it is the whole bootstrap
    story, unchanged in effect — is COMPLETION: `rbtv-goal scaffold` mints the
    goal folder and its authored artifacts, and this command completes the
    WORKING surfaces (seats/, coordination/, header-only taskforce.csv, the
    ruled header-only state.csv, the three caller-supplied content files).

    Modes: a goal folder missing taskforce.csv is completed FULLY and requires
    both inputs (this is the bootstrap path, and it is the same code path
    that closed the crash-then-flagless-retry window); a goal folder WITH
    taskforce.csv completes only the structural dirs seats/ and coordination/,
    plus any caller-input surface whose option was explicitly supplied and
    whose file is missing. Existing surfaces are NEVER touched, compared, or
    overwritten."""
    if not package.is_dir():
        raise Refuse(
            "goal-folder-absent",
            f"the goal folder {package} does not exist — this command "
            "completes the WORKING surfaces of an EXISTING goal folder; "
            "creating a goal is rbtv-goal's act, never this command's",
            str(package),
        )
    full = not (package / TASKFORCE_NAME).is_file()

    plan: list[dict] = []

    missing_inputs = []
    for surface, opt, attr in CREATION_INPUTS:
        supplied = getattr(args, attr, None)
        if (package / surface).is_file():
            continue
        if supplied is None:
            if full:
                missing_inputs.append((surface, opt))
            continue
        plan.append({"surface": surface, "path": str(package / surface),
                     "data": _read_creation_source(surface, opt, supplied),
                     "source": supplied})
    if missing_inputs:
        raise Refuse(
            "create-inputs-missing",
            "creating (or completing) this goal package needs the "
            "caller-supplied base text for: "
            + ", ".join(f"{s} (pass {o} <file>)" for s, o in missing_inputs)
            + " — d-run3-seeds-from-run2-amended: the content is run-2's "
            "version as amended by the authored designs, CARRIED BY THE "
            "CALLER; this command never invents run conventions and never "
            "defaults a floor. Nothing was created",
            str(package),
        )

    # The OPTIONAL creation surface (7.569) — see ADDRESSABLE_NAME's block.
    # `--addressable` byte-copies a caller's register when one is supplied (in
    # any mode, like every other input option); otherwise a BOOTSTRAP creation
    # derives it from the standing-seat doors that opted in. Never for a goal
    # that already carries one, and never retro-fitted onto a legacy package.
    if not (package / ADDRESSABLE_NAME).is_file():
        supplied = getattr(args, "addressable", None)
        if supplied is not None:
            plan.append({"surface": ADDRESSABLE_NAME,
                         "path": str(package / ADDRESSABLE_NAME),
                         "data": _read_creation_source(
                             ADDRESSABLE_NAME, "--addressable", supplied),
                         "source": supplied})
        elif full:
            derived = derive_addressable_register(package)
            if derived:
                plan.append({"surface": ADDRESSABLE_NAME,
                             "path": str(package / ADDRESSABLE_NAME),
                             "data": derived, "source": "derived"})

    if full:
        # By construction only the full modes reach here with these missing:
        # legacy mode means taskforce.csv is present, and legacy packages
        # keep their own state-cursor story (run-2's frozen file is present
        # and NEVER repaired; a legacy package without one is not retrofitted).
        if not (package / TASKFORCE_NAME).is_file():
            plan.append({"surface": TASKFORCE_NAME,
                         "path": str(package / TASKFORCE_NAME),
                         "data": (",".join(TASKFORCE_HEADER) + "\n").encode()})
        if not (package / STATE_CSV_NAME).is_file():
            plan.append({"surface": STATE_CSV_NAME,
                         "path": str(package / STATE_CSV_NAME),
                         "data": (STATE_CSV_HEADER + "\n").encode()})
    for d in ("seats", "coordination"):
        if not (package / d).is_dir():
            plan.append({"surface": d, "path": str(package / d), "dir": True})
    return plan


def create_run_package(package: Path, creation: list[dict]) -> list[str]:
    """dag-06 — WRITE the planned creation surfaces, in plan order (content
    surfaces before the structural markers, so a crash mid-creation leaves a
    package that still lacks taskforce.csv and is completed as a
    CREATION-PARTIAL on retry — inputs re-required, nothing silently
    tolerated). Fires AFTER every gate (like every other write): a refusal
    anywhere leaves zero created surfaces. Files are created EXCLUSIVELY
    (mode 'xb') — this step never overwrites; a surface appearing between
    plan and write fails loudly."""
    written: list[str] = []
    for entry in creation:
        target = Path(entry["path"])
        # A declared write-root that resolves under a marked DERIVED tree would
        # put the seat's product in a copy the next regenerate erases (C10).
        _refuse_derived_target(target, f"the surface plan names {target}")
        if entry.get("dir"):
            target.mkdir(parents=True, exist_ok=True)
            target.chmod(0o755)
        else:
            with open(target, "xb") as fh:
                fh.write(entry["data"])
            target.chmod(0o644)
        written.append(str(target))
    return written


# ── The seat's guidance pair — CLAUDE.md + AGENTS.md, ONE body (owner ruling ─────────
#    `d-uniform-descriptor-carriage`, 2026-08-12; supersedes the 2026-08-07 pointer ruling)
#
# WHY ONE BODY UNDER TWO NAMES. The descriptor now ARRIVES AT SPAWN on every harness —
# claude in the system prompt (`composeArgv` appends `--append-system-prompt-file
# <workdir>/seat.md`), every other harness as the head of its first stdin message (same
# function; carriage measured 2026-08-12 on this box: codex 0.144.5 `exec -`, opencode
# 1.17.18 `run`, kimi 1.48.0 `-p`). With delivery uniform, the 2026-08-07 reason for the
# two guidance files to DIVERGE (claude must not be told to re-read what its system prompt
# carries; codex/opencode needed a pointer) is gone: every daemon-launched sitting already
# holds seat.md, so BOTH files now say the same thing — don't re-read it — under each
# harness's native guidance name. What the files add beyond that stance is the seat
# folder's standing knowledge: the standard surfaces, the goal-folder write mechanics,
# and (when the seat exposes rules) the forced-read rules preamble.
#
# ⚑ THE DON'T-READ CLAUSE IS CONDITIONAL, owner-ruled (Q2a, 2026-08-12): a session opened
# BY HAND in the seat folder received no descriptor, and an absolute "never read seat.md"
# would order it to run the seat blind. The exception paragraph is that session's one
# recovery path — never delete it.
#
# ⚑ STILL NOT THE `agents-md` MIRROR'S JOB. That driver
# (`orchestration/models/mirror/driver/guidance.py`) renders AGENTS.md from a SIBLING
# CLAUDE.md it finds by walking the tree; seat folders are written HERE, by the act that
# materializes the seat, so the pair is complete the moment the seat exists and no mirror
# pass is a dependency of a launch. `_write_seat_guidance`'s banner guard is what keeps
# the two writers from fighting: this tool only ever overwrites what carries its own
# generated banner.
_SEAT_GUIDANCE_MD = """\
# {seat} — seat folder guidance

> Generated by `materialize-seats.py` beside this seat's `seat.md`. `CLAUDE.md` and
> `AGENTS.md` carry this SAME body — one text under each harness's native guidance name
> (`d-uniform-descriptor-carriage`). Regenerated freely; never hand-edit it.

## Your descriptor is `seat.md` — and it already arrived with your launch

A daemon-launched sitting receives this seat's `seat.md` AT SPAWN, on every harness: a
`claude` session carries it in its system prompt; every other harness receives it as the
head of its first message, above the wake payload. Its directives bind this sitting from
its first action: the seat's task, identity, instruments, rhythm, format duties, and its
bounds. Do NOT read `seat.md` again — you have already read it, and a second copy buys
one tool call and nothing else.

**The ONE exception — no descriptor in your context.** If you can find no seat descriptor
in what you received (a session opened BY HAND in this folder, not launched by the
daemon), then `seat.md` is a MUST-READ, NOW, before your first word — including before a
question that looks trivial, which is exactly where it gets skipped.

## Your standard surfaces — fixed names, so nothing has to be guessed

| Surface | What goes there |
|---------|-----------------|
| `memory.md` — THIS folder | your dated working state: the half of your resume contract that is not `seat.md` |
| {ledgers} — the GOAL folder | the five write-if-something ledgers. Every seat may append to all five; nothing obliges an entry |
| the path `seat.md`'s `goal-writes` names | your role's ONE product in the goal folder. No `goal-writes` line means your role produces nothing there, and your work stays in THIS folder |
| `downloads/` · `scratchpad/` · `outputs/` — THIS folder | fetched files · working scratch · finished artifacts |

**The three folders do not exist yet — CREATE ONE THE FIRST TIME YOU NEED IT**, and do not
create the others speculatively. The names are standard so that a human and the next
sitting find your files where they expect them; three empty directories in every seat
folder forever buy nothing the name alone does not.

Never mint a fourth name for one of these, and never write inside another seat's folder —
{peer_folder_note}

## Writing into the GOAL folder — read this BEFORE you conclude you lack permission

{write_surface_note}
"""

# The peer-folder and write-surface paragraphs of `_SEAT_GUIDANCE_MD`, in their CAGED
# form: true for a seat `spawn.js` builds a sandbox for, where the cage itself is what
# makes a peer folder ABSENT.
_SEAT_GUIDANCE_PEER_FOLDER_CAGED = (
    "the cage makes peer seat folders ABSENT, so an attempt fails rather than lands.")
_SEAT_GUIDANCE_WRITE_SURFACE_CAGED = """\
`seat.md`'s "Your write surface" section lists the paths your cage opens read-write; it is
derived from the cage itself, so it beats any prose that disagrees with it.

**The whole folder is writable** (D3, 2026-08-19) — ledgers, planning, coordination,
sessions.csv included. Atomic writers (`Write` / `Edit`) work. `seat.md`
stays read-only (a wall-control surface). Peer seat
folders are absent."""

# The same two paragraphs, UNCAGED form: for a seat on `launch.js`'s STAFF roster
# (`_staff_uncaged_seats()`), no sandbox is composed at all, so "the cage makes X
# absent" is false — nothing mechanically stops this seat from writing anywhere its
# user account can reach. The true bound is a NORM, matching `_UNCAGED_WRITE_SURFACE_BLOCK`
# above (B15's fix for the same false-cage framing on the derived section).
_SEAT_GUIDANCE_PEER_FOLDER_UNCAGED = (
    "you run UNCAGED, so no cage stops you; staying out of a peer's folder is a "
    "working NORM you keep, not a wall that keeps you.")
_SEAT_GUIDANCE_WRITE_SURFACE_UNCAGED = """\
`seat.md`'s "Your write surface" section states what the kernel will actually answer; for
this UNCAGED seat it says you may write anywhere your user account can reach — this goal
folder, any other goal's folder, the rbtv repo, and paths outside the workspace — because
no cage is composed for you at all, so it beats any prose above that speaks as if a cage
narrowed you.

**The whole folder is writable** (D3, 2026-08-19), and so is everywhere else your account
can reach — you run UNCAGED. Atomic writers (`Write` / `Edit`) work. `seat.md` stays
read-only by norm, not by a cage. Peer seat folders are NOT absent; staying out of them
is a norm you keep, not a wall that stops you."""

# The forced-read preamble for rule exposure (d-materializer-seat-loaders;
# CMP-12's fallback row: codex auto-injects no rule folder, so the guidance
# file must FORCE the read by naming the specific files).
_SEAT_RULES_BLOCK = """\

## Always-on rules — binding for this whole sitting

This seat carries always-on behavior rules, materialized beside this file twice:
`.claude/rules/` (auto-loaded by Claude Code) and `.agents/behavior-rules/` (verbatim
copies for harnesses that auto-load no rule folder). If your harness did not auto-inject
them, read EVERY file below NOW — before seat.md's task work — and follow each as binding:

{rows}
"""


# The banner substring the guard below keys on — present in `_SEAT_GUIDANCE_MD` (and in the
# retired pointer template, so pre-ruling generated AGENTS.md files regenerate cleanly).
_GUIDANCE_BANNER = "Generated by `materialize-seats.py`"


def _seat_guidance_notes(seat: str) -> tuple[str, str]:
    """The (peer_folder_note, write_surface_note) pair `_SEAT_GUIDANCE_MD` fills in,
    chosen by the SAME roster `_write_surface_section` chooses the derived block by —
    an uncaged staff seat gets the truthful counterpart, never the caged wording that
    told it a nonexistent cage was what stopped it."""
    if seat in _staff_uncaged_seats():
        return _SEAT_GUIDANCE_PEER_FOLDER_UNCAGED, _SEAT_GUIDANCE_WRITE_SURFACE_UNCAGED
    return _SEAT_GUIDANCE_PEER_FOLDER_CAGED, _SEAT_GUIDANCE_WRITE_SURFACE_CAGED


def _write_seat_guidance(folder: Path, seat: str, package: Path,
                         rules: list[tuple[str, str]] = ()) -> list[str]:
    """Write (or refresh) the seat's guidance pair — `CLAUDE.md` + `AGENTS.md`, ONE body
    under each harness's native guidance name (`d-uniform-descriptor-carriage`). Returns
    the paths written (byte-identical targets are skipped).

    Regenerated freely — fixed boilerplate with no per-run content (plus, when the seat
    exposes rules, the forced-read preamble naming each materialized copy), so there is
    no drift to preserve. ⚑ EXCEPT A HAND-AUTHORED FILE: a target that exists WITHOUT the
    generated banner is left byte-untouched (the standing master seat's own CLAUDE.md is
    the live case) — regenerate-freely is a property of what THIS tool generated, never a
    license over an owner's file.

    It also carries the tooling-gap filing block (owner ruling 2026-08-10), rendered
    from goal_cli's ONE constant — the goal router carries the same text, and a second
    copy of it here would be a second thing to drift. The fallback path is the PACKAGE's
    `issues.md`, not the seat folder's: for a standing seat the two are the same folder,
    and for every other seat the goal's ledger is the one that exists."""
    # The five ledger names come from goal_cli's ONE dictionary — the same one that
    # creates the files and renders the goal router's table. Restating them here is
    # how `gotchas.md` came to be scaffolded but named nowhere a seat reads.
    peer_folder_note, write_surface_note = _seat_guidance_notes(seat)
    text = _SEAT_GUIDANCE_MD.format(
        seat=seat,
        ledgers=" · ".join(f"`{f}`" for f in WRITE_IF_SOMETHING),
        peer_folder_note=peer_folder_note,
        write_surface_note=write_surface_note)
    if rules:
        text += _SEAT_RULES_BLOCK.format(rows="\n".join(
            f"- `.agents/behavior-rules/{pid}.md` — {desc}"
            for pid, desc in rules))
    text += "\n" + TOOLING_FINDING_BLOCK.format(
        issues=f"`{package / 'issues.md'}` (this seat's own goal ledger)")
    written: list[str] = []
    for name in ("CLAUDE.md", "AGENTS.md"):
        target = folder / name
        _refuse_derived_target(target, f"the guidance pair of seat '{seat}'")
        if target.exists():
            current = target.read_text(encoding="utf-8")
            if current == text:
                continue
            if _GUIDANCE_BANNER not in current:
                continue  # hand-authored — never clobbered
        target.write_text(text, encoding="utf-8", newline="\n")
        target.chmod(0o644)
        written.append(str(target))
    return written


# ── plugin/MCP registration files — the `config` method (d-mcp-registration-is-config) ──
#
# A component declares a plugin/MCP registration ONCE, as an exposure.csv row
# (`method: config`) whose entry-point names a server-declaration file in the
# `mcpServers` JSON shape — rbtv's neutral schema (owner ruling 2026-08-08).
# Materializing a seat realizes that declaration for EVERY supported harness
# (CON-2: claude, codex, opencode) in the seat folder, per CMP-12 § config:
#
#   .mcp.json               claude — the neutral shape verbatim, PLUS
#   .claude/settings.json   "enableAllProjectMcpServers": true (measured
#                           2026-08-08, claude 2.1.226: without the flag every
#                           project server sits "Pending approval")
#   .codex/config.toml      codex 0.144.5 — [mcp_servers.<name>] tables;
#                           url= for http/sse, command/args/env for stdio
#   opencode.json           opencode 1.17.18 — "mcp" key; remote/url ·
#                           local/command+environment
#
# All three harnesses read these PROJECT-LOCALLY from the seat's working root
# (cwd-scoping control-verified on codex). Registration is NOT authentication:
# an OAuth server still needs a one-time human login per harness per box
# (`codex mcp login` / `opencode mcp auth` / claude's own flow) — the caveat
# lives on the KG `harness config` schema key.
#
# The generated files are DERIVED and per-run content-free, so like AGENTS.md
# they are regenerated freely (byte-identical → skipped) — never a collision
# refusal. A component with no exposure.csv, or none of its rows `config`,
# generates nothing: absence is normal.

EXPOSURE_NAME = "exposure.csv"


def load_mcp_servers(comp_dir: Path) -> dict:
    """The component's merged plugin/MCP declaration: every exposure.csv row
    with `method: config` whose entry-point file carries an `mcpServers`
    object. {} when the component declares none. A config row whose payload
    parses but carries NO `mcpServers` key is another config payload kind and
    is skipped here; an unreadable/unparseable payload REFUSES (pre-write)."""
    exposure = comp_dir / EXPOSURE_NAME
    if not exposure.is_file():
        return {}
    servers: dict = {}
    with exposure.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("method") or "").strip() != "config":
                continue
            entry = (row.get("entry-point") or "").strip()
            if not entry:
                raise Refuse(
                    "mcp-entry-point-missing",
                    f"exposure.csv row '{(row.get('part-id') or '').strip()}' "
                    "declares method `config` with an empty entry-point — the "
                    "entry-point names the declaration file the generated "
                    "harness config carries, so there is nothing to realize",
                    str(exposure))
            path = comp_dir / entry
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise Refuse(
                    "mcp-declaration-invalid",
                    f"config entry-point {entry!r} is not readable JSON "
                    f"({exc}) — refusing before any write; a seat folder "
                    "carrying a half-generated registration set would look "
                    "materialized and fail at launch",
                    str(path)) from exc
            decl = data.get("mcpServers") if isinstance(data, dict) else None
            if decl is None:
                continue
            if not isinstance(decl, dict) or not all(
                    isinstance(v, dict) for v in decl.values()):
                raise Refuse(
                    "mcp-declaration-invalid",
                    f"config entry-point {entry!r} carries an `mcpServers` "
                    "that is not an object of server objects — not the "
                    "neutral schema (d-mcp-registration-is-config)",
                    str(path))
            for name, spec in decl.items():
                if name in servers:
                    raise Refuse(
                        "mcp-server-duplicate",
                        f"server {name!r} is declared by more than one "
                        "config row of this component — one registration, "
                        "one home",
                        str(exposure))
                servers[name] = spec
    return servers


def _codex_mcp_toml(servers: dict) -> str:
    """`.codex/config.toml` [mcp_servers.*] tables from the neutral shape.
    json.dumps of a str/list is valid TOML for both, so no TOML writer is
    needed (stdlib has none)."""
    lines = ["# Generated by materialize-seats.py from the component's "
             "plugin/MCP declaration", "# (exposure.csv `method: config`) — "
             "regenerated freely, never hand-edited.", ""]
    for name in sorted(servers):
        spec = servers[name]
        lines.append(f"[mcp_servers.{name}]")
        if spec.get("url"):
            lines.append(f"url = {json.dumps(str(spec['url']))}")
        else:
            lines.append(f"command = {json.dumps(str(spec.get('command', '')))}")
            if spec.get("args"):
                lines.append(
                    "args = "
                    + json.dumps([str(a) for a in spec["args"]]))
            env = spec.get("env") or {}
            if env:
                lines.append("")
                lines.append(f"[mcp_servers.{name}.env]")
                for k in sorted(env):
                    lines.append(f"{k} = {json.dumps(str(env[k]))}")
        lines.append("")
    return "\n".join(lines)


def _opencode_mcp_json(servers: dict) -> str:
    """`opencode.json` from the neutral shape: url → remote, else local
    (command array = command + args; env key is `environment`)."""
    mcp: dict = {}
    for name, spec in servers.items():
        if spec.get("url"):
            mcp[name] = {"type": "remote", "url": str(spec["url"]),
                         "enabled": True}
        else:
            entry: dict = {
                "type": "local",
                "command": [str(spec.get("command", ""))]
                + [str(a) for a in (spec.get("args") or [])],
                "enabled": True,
            }
            env = spec.get("env") or {}
            if env:
                entry["environment"] = {k: str(v) for k, v in env.items()}
            mcp[name] = entry
    return json.dumps({"$schema": "https://opencode.ai/config.json",
                       "mcp": mcp}, indent=2, sort_keys=True) + "\n"


def render_harness_configs(plan: dict, seats_cat: dict) -> None:
    """Plan the per-seat harness registration files (all gates fire HERE,
    before the dry-run return and before any write) and DECLARE them in
    writes[] — an undisclosed write is the --dry-run under-report failure the
    plan exists to refuse."""
    configs: dict[str, dict[str, str]] = {}
    for seat in plan["added_seats"]:
        source = str((seats_cat.get(seat) or {}).get("__source__") or "")
        if not source:
            continue
        servers = load_mcp_servers(Path(source).parent)
        if not servers:
            continue
        files = {
            ".mcp.json": json.dumps({"mcpServers": servers}, indent=2,
                                    sort_keys=True) + "\n",
            ".claude/settings.json": json.dumps(
                {"enableAllProjectMcpServers": True}, indent=2) + "\n",
            ".codex/config.toml": _codex_mcp_toml(servers),
            "opencode.json": _opencode_mcp_json(servers),
        }
        configs[seat] = files
        for rel in files:
            plan["writes"].append({
                "kind": "seat-harness-config", "seat": seat,
                "path": str(seat_home(Path(plan["package"]), seat) / rel)})
    plan["harness_configs"] = configs


def emit_harness_configs(plan: dict) -> list[str]:
    """Write the planned registration files — AGENTS.md semantics (derived,
    deterministic, regenerated freely; byte-identical → skipped)."""
    written: list[str] = []
    for seat, files in (plan.get("harness_configs") or {}).items():
        folder = seat_home(Path(plan["package"]), seat)
        for rel, text in files.items():
            target = folder / rel
            _refuse_derived_target(
                target, f"the harness registration files of seat '{seat}'")
            if target.exists() and target.read_text(encoding="utf-8") == text:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
            target.chmod(0o644)
            written.append(str(target))
    return written


# ── seat-folder exposure loaders — the five seat-authorable methods
#    (d-materializer-seat-loaders; shape owner-ruled 2026-08-09,
#    d-seat-exposes-frontmatter) ──
#
# A seat DECLARES what must be materialized beside its seat.md in its prompt
# file's frontmatter (`<component>/prompts/<executor>.md`):
#
#   exposes:
#     skill: [brws, other-comp/xsk]
#     rule: [house-style]
#     sub-agent: [researcher]
#
# The mapping is grouped by canonical exposure method for readability, but
# exposure.csv REMAINS the one home of the part -> method binding (PRIN-11):
# a group key that disagrees with the referenced row's `method` column is a
# refusal, never a silent override. Ref grammar (segment count decides):
# `part` = the seat's own component's exposure.csv · `component/part` = a
# sibling component, same module · `module/component/part` = another
# module's component (owner-ruled 2026-08-09: cross-module must exist) —
# resolved from the referencing component's position in the tree, so the
# same grammar works for the mirror and the rbtv repo, both shaped
# `<tree>/<module>/<component>/`. The prose <resources> unit is NOT
# replaced by this: it keeps naming conditional reads, references, and CLI
# commands — `exposes:` carries only what the harness must materialize.
# Realization per harness follows CMP-12's matrix and nowhere else:
#
#   skill      .claude/skills/<id>/SKILL.md (claude; opencode reads .claude/)
#              + .agents/skills/<id>/SKILL.md (codex) — thin loaders
#   command    .claude/commands/<id>.md + .codex/prompts/<id>.md
#              + .opencode/commands/<id>.md — thin loaders
#   rule       .claude/rules/<id>.md + .agents/behavior-rules/<id>.md —
#              VERBATIM copies; the seat AGENTS.md gains a forced-read
#              preamble naming each copy (codex auto-injects no rule folder)
#   hook       entry-point names a JSON file carrying a claude-shape `hooks`
#              object (rbtv's neutral shape adopts Claude Code's namings, the
#              same move d-mcp-registration-is-config made for mcpServers);
#              merged into .claude/settings.json and carried verbatim into
#              .codex/hooks.json — MEASURED, not assumed: codex-cli 0.144.5
#              reads project-local `.codex/hooks.json` whose `hooks` object
#              uses the claude event/matcher/handler shape verbatim, plus an
#              optional top-level `description` (codex manual § Hooks,
#              read 2026-08-09; extra per-handler fields: timeout seconds,
#              statusMessage, additionalContextLimit). ⚠ Codex TRUST-GATES
#              them: project-local hooks load only when the `.codex` layer
#              is trusted AND each hook definition is trusted by hash
#              (`/hooks`), or the launch passes
#              `--dangerously-bypass-hook-trust` — a materialized file that
#              fires nothing until the launch profile carries that; see the
#              core-build issues ledger. opencode has no hook surface
#              (CMP-12)
#   sub-agent  .claude/agents/<id>.md + .opencode/agents/<id>.md thin loaders
#              + .codex/agents/<id>.toml (measured 2026-08-12, codex 0.147.0:
#              project-local, field `developer_instructions` — INERT until the
#              seat folder is trusted in ~/.codex/config.toml; trust is a
#              deployment act, tracked in the core-build task file)
#
# `agents.md` and `config` are NOT seat-authorable here — the seat AGENTS.md
# pointer and the plugin/MCP registration files are materialized by their own
# surfaces above. Like those files, every loader is DERIVED and per-run
# content-free: regenerated freely (byte-identical -> skipped), never a
# collision refusal. A prompt with no `exposes:` (or no prompt FILE at all —
# csv-shaped prompts, tool seats) generates nothing: absence is normal.

#   path       NO harness cell (CMP-12 keeps none) — the SANDBOX realizes it
#              (d-path-exposes-authorable, owner 2026-08-10). Nothing is
#              written beside seat.md; instead the resolved entry point lands
#              in the DESCRIPTOR frontmatter as `exposed-clis:` (one
#              `<part-id> <abs entry path>` per line), which the cage's one
#              declaration reader picks up and binds read-only — the code tree
#              at its real path plus a sandbox symlink carrying the installed
#              NAME, both ends of the host symlink. An UNCAGED seat's
#              declaration realizes nothing, exactly as before.
#              ⚠ Its `entry-point` column is the ONE that may leave the
#              component, and `ws:` is the ONLY way it may (owner 2026-08-11,
#              IPH-6 / D33): `ws:<path-from-the-workspace-root>` resolves
#              against the first ancestor holding `.rbtv/config/`, which is
#              how a MIRROR-resident seat reaches a workspace-resident tool
#              (`ws:3-resources/tools/stools/stools.py` is the live instance).
#              Legal on `method=path` rows ONLY — the installer copies every
#              other method's entry-point out of the component, and a
#              workspace path is not inside it. A `..`-climbing entry-point is
#              REFUSED at generation time on EVERY method, prefixed or not, so
#              the rule cannot be reintroduced by copying an old example.
SEAT_EXPOSE_METHODS = ("skill", "command", "rule", "hook", "sub-agent", "path")

_LOADER_NOTE = ("Generated by materialize-seats.py from the component's "
                "exposure manifest (d-materializer-seat-loaders) — a thin "
                "loader, regenerated freely, never hand-edited.")


def _yq(text: str) -> str:
    """A YAML-safe quoted scalar (json.dumps quoting is valid YAML — the
    colon-space-in-description failure class); unicode kept readable."""
    return json.dumps(str(text), ensure_ascii=False)


def _loader_md(part: str, desc: str, entry_abs: str, what: str,
               named: bool) -> str:
    """A thin-loader markdown file pointing at the exposed part's entry
    point. `named` adds the `name:` key (skills, sub-agents)."""
    name_line = f"name: {part}\n" if named else ""
    return (f"---\n{name_line}description: {_yq(desc)}\n---\n\n"
            + _LOADER_NOTE + "\n\n"
            f"Read `{entry_abs}` NOW and follow it as this {what}'s full "
            "instructions.\n")


def _prompt_exposes(comp_dir: Path, executor: str, seat: str) -> dict:
    """The `exposes:` mapping off the seat's prompt-file frontmatter
    (`prompts/<executor>.md`) — {} when the file or the key is absent."""
    path = comp_dir / "prompts" / f"{executor}.md"
    if not executor or not path.is_file():
        return {}
    m = _FM_RE.match(path.read_text(encoding="utf-8"))
    if not m:
        return {}
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise Refuse(
            "exposes-invalid",
            f"prompt file for seat '{seat}' carries frontmatter that is not "
            f"YAML — {exc}",
            str(path)) from exc
    raw = fm.get("exposes") if isinstance(fm, dict) else None
    if raw in (None, "", {}):
        return {}
    if not isinstance(raw, dict):
        raise Refuse(
            "exposes-invalid",
            f"seat '{seat}': `exposes:` must be a mapping of method -> "
            "part-id list",
            str(path))
    out: dict[str, list[str]] = {}
    for method, refs in raw.items():
        if method not in SEAT_EXPOSE_METHODS:
            raise Refuse(
                "exposes-method-unknown",
                f"seat '{seat}': `exposes:` key '{method}' is not a "
                "seat-authorable method — one of "
                + "|".join(SEAT_EXPOSE_METHODS)
                + " (agents.md and config are materialized by their own "
                "surfaces; anything else is outside the canon)",
                str(path))
        if isinstance(refs, str):
            refs = [refs]
        if not isinstance(refs, list) or not refs or not all(
                isinstance(r, str) and r.strip() for r in refs):
            raise Refuse(
                "exposes-invalid",
                f"seat '{seat}': `exposes: {method}:` must be a non-empty "
                "list of part-id strings",
                str(path))
        out[method] = [r.strip() for r in refs]
    return out


# The INTERACTIVE-SEAT injection (F5; owner rulings D11 + D15, 2026-08-10).
# A seat the catalog marks `human-interactive:` gets extra SKILL parts folded
# into its exposure set exactly as if its prompt frontmatter had declared them
# — so the owner-facing etiquette a user-facing seat must follow arrives by
# materialization instead of by nine remembered frontmatter edits.
#
# WHICH parts is INSTANCE policy and lives nowhere in this file: the list is
# read from the workspace config convention `.rbtv/config/modules/<module>/
# <component>/…` (D15) at this component's own address. Absent file, absent
# `.rbtv/config`, or an empty list injects NOTHING — an install without the
# convention renders byte-identically to before. A listed part that does not
# resolve takes the ordinary `exposes-ref-dangling` refusal below, at
# generation time, like any authored reference.
INTERACTIVE_EXPOSES_REL = Path(
    ".rbtv", "config", "modules", "ignite", "team-kit",
    "interactive-exposes.json")


def _interactive_expose_refs(comp_dir: Path) -> list[str]:
    """The configured skill part refs for interactive seats — [] when the
    workspace carries no such file. The workspace is DERIVED, never guessed:
    `_workspace_root`, which since IPH-6 / D33 is LITERALLY the same walk
    `_rbtv_repo_root` does rather than merely claiming to be. Only THAT
    workspace's file is read, so a grandparent tree can never leak its policy
    in. An underivable workspace injects NOTHING rather than refusing — the
    block comment above rules that an install without the convention renders
    byte-identically to before, and that predates any prefixed reference."""
    try:
        parent = _workspace_root(comp_dir)
    except Refuse:
        return []
    book = parent / INTERACTIVE_EXPOSES_REL
    if not book.is_file():
        return []
    try:
        refs = json.loads(book.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refuse(
            "interactive-exposes-invalid",
            f"the interactive-seat expose list is not readable JSON — {exc}",
            str(book)) from exc
    if not isinstance(refs, list) or not all(
            isinstance(r, str) and r.strip() for r in refs):
        raise Refuse(
            "interactive-exposes-invalid",
            "the interactive-seat expose list must be a JSON list of "
            "part-ref strings (the `exposes:` reference grammar)",
            str(book))
    return [r.strip() for r in refs]


def _assembled_is_interactive(assembled: str) -> bool:
    """Whether the seat's ASSEMBLED frontmatter declares `human-interactive:`
    — the one marker the code already carries for "a human is on the other end"
    (goal_cli#assemble_seat reads it off the prompt definition and passes it
    through; see EMITTER_OWNED_KEYS). Tolerances match the daemon's reader
    (`supervisor/spawn/live-sessions.js`): `yes`/`true`, quoted or not."""
    m = _FM_RE.match(assembled or "")
    if not m:
        return False
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return False
    val = fm.get("human-interactive") if isinstance(fm, dict) else None
    return str(val).strip().strip('"').lower() in ("yes", "true")


WS_PREFIX = "ws:"
ENTRY_AUTHORED = "__entry-point-authored__"

# ── W6 · `write-roots` — the SEVENTH exposure.csv column ─────────────────────
#
# A `method=path` row may declare the directories its CLI must WRITE to (gtools
# refreshing an OAuth token, a tool keeping a cache). The cell is
# `;`-separated; each entry takes the ENTRY-POINT grammar (component-relative,
# or `ws:<path-from-the-workspace-root>`) and inherits the `..` refusal, both
# normalized by `_exposure_rows` — the ONE reader — exactly like `entry-point`.
#
# ⚠ EVERY entry carries the DANGER SIGIL `!` and a write grant is NEVER
# INFERRED (owner ruling, W6/R2). The sigil is not decoration: it is the whole
# reason this column cannot grow a write grant by accident. An unmarked entry
# is a REFUSAL at component-lint and at materialize alike — one rule, two
# doors, so an author meets it while still holding the file.
#
# The header stays SEVEN columns: the marker is IN-CELL, never an eighth
# column, because it qualifies one entry and not the row.
WRITE_ROOTS_COLUMN = "write-roots"
WRITE_ROOTS_RESOLVED = "__write-roots-resolved__"
DANGER_SIGIL = "!"

# The DISCOVERY layer's key (owner ruling, W6/R2): the file a `method=skill`
# row's `entry-point` NAMES carries a flat `exposes-cli:` list — the CLIs that
# skill routes to, in the `resolve_seat_exposes` reference grammar. It is NOT
# "SKILL.md": 10 of the 11 live skill rows point at some other file.
#
# A seat that exposes the skill therefore inherits those CLIs' write-roots
# without having to know them. exposure.csv stays the DECLARATION layer — the
# refs here resolve to `method=path` rows or REFUSE (`skill-cli-dangling`).
EXPOSES_CLI_KEY = "exposes-cli"


def _workspace_root(start: Path) -> Path:
    """The WORKSPACE rooting `start` — the first ancestor holding a
    `.rbtv/config/` DIRECTORY. THE one walk this file does: the base a `ws:`
    entry-point resolves against, the root `_rbtv_repo_root` finds `rbtv.json`
    at, and the anchor `_interactive_expose_refs` reads its policy from
    (owner ruling, 2026-08-11, IPH-6 / D33 — the `install.json` walk that used
    to be a second, disagreeing derivation is gone).

    The directory walk is the ONE derivation correct in both production and
    the selftest fixture: no `parents[n]` rule off `--package` or
    `--catalog-root` is right in both trees, and this one needs neither.

    ⚠ `ws:` is NOT a sibling of `rbtv:` and shares no dispatch with it.
    `rbtv:` prefixes a REFERENCE in a seat's `exposes:` frontmatter and picks
    WHICH COMPONENT DIRECTORY a manifest is read from; `ws:` prefixes the
    ENTRY-POINT COLUMN of one manifest row and picks the BASE a file path
    resolves against. Different inputs, different sites, different return
    types — they meet only at the workspace root."""
    for parent in (start, *start.parents):
        if (parent / ".rbtv" / "config").is_dir():
            return parent
    raise Refuse(
        "ws-root-underivable",
        "the workspace is underivable: no `.rbtv/config/` directory exists at "
        "or above the referencing component, so a `ws:` entry-point has no "
        "base and a `rbtv:` reference has no root to find `rbtv.json` at — "
        "searched " + " · ".join(str(p) for p in (start, *start.parents)),
        str(start))


def _exposure_rows(comp_dir: Path) -> dict[str, dict]:
    """part-id -> exposure.csv row of ONE component ({} when no manifest).

    `#`-led lines are DROPPED before the header is read. Exposure manifests
    carry a prose header block by convention (the `orchestration/exposure.csv`
    and `web/browse/exposure.csv` headers are the live shape), and a plain
    DictReader takes that first comment line for the header — every part-id
    then reads as absent, which surfaces as `exposes-ref-dangling` against a
    manifest that plainly contains the row.

    The `entry-point` cell is NORMALIZED here, at the ONE reader every
    entry-point consumer goes through (the `exposed-clis` render, the
    existence gate, the loader target and the rule-body read all take their
    row from this function), so the four join sites need no edit and cannot
    drift apart. Two rules, in this order:

      1. a `ws:`-prefixed cell — legal on `method=path` rows ONLY — becomes
         its absolute resolution against `_workspace_root(comp_dir)`. pathlib
         discards the left operand of a join whose right side is absolute, so
         every `ref_dir / entry` join downstream keeps working unchanged.
      2. a cell with ANY `..` path component is REFUSED. Applying the ban
         AFTER the prefix strip means `ws:../outside` and a bare `../outside`
         take ONE rule, and the climb cannot be reintroduced by copying an old
         example (owner ruling, IPH-6 / D33).

    The gate on rule 1 is load-bearing, not cosmetic: `install2.py` treats
    `path` and `pool` as INVENTORY and skips its entry-point existence check
    for them, so the installer never meets a `ws:` cell — on any other method
    it would try to copy a file at a literal `ws:…` path.

    ⚠ CONTRACT: the returned row's `entry-point` is the RESOLVED cell, not the
    authored one. The authored text stays under `ENTRY_AUTHORED` so a
    downstream refusal quotes what the author typed."""
    path = comp_dir / EXPOSURE_NAME
    if not path.is_file():
        return {}
    disc = _discovery()
    try:
        raw_rows = disc.exposure_rows({"path": str(comp_dir)})
    except disc.Refuse as exc:
        raise Refuse(exc.code, exc.message, exc.path or str(path)) from exc
    rows: dict[str, dict] = {}
    for row in raw_rows:
        pid = (row.get("part-id") or "").strip()
        if not pid:
            continue
        raw = (row.get("entry-point") or "").strip()
        entry = raw
        if raw.startswith(WS_PREFIX):
            method = (row.get("method") or "").strip()
            if method != "path":
                raise Refuse(
                    "exposes-entry-invalid",
                    f"part '{pid}' declares entry-point '{raw}' on a "
                    f"method={method or '(empty)'} row — `ws:` is legal on "
                    "`method=path` rows ONLY, because every other method's "
                    "entry-point is COPIED out of the component by the "
                    "installer and a workspace path is not inside it",
                    str(path))
            entry = str(_workspace_root(comp_dir) / raw[len(WS_PREFIX):])
        if ".." in Path(entry).parts:
            raise Refuse(
                "exposes-entry-escape",
                f"part '{pid}' declares entry-point '{raw}', which climbs out "
                "of its component with `..` — an entry point never leaves the "
                "component by counting directories. Reach a tool elsewhere in "
                "the workspace with the `ws:` prefix instead "
                "(`ws:<path-from-the-workspace-root>`)",
                str(path))
        row["entry-point"] = entry
        row[ENTRY_AUTHORED] = raw
        row[WRITE_ROOTS_RESOLVED] = _write_roots(row, pid, comp_dir, path)
        rows[pid] = row
    return rows


def _write_roots(row: dict, pid: str, comp_dir: Path, manifest: Path) -> list[str]:
    """The `write-roots` cell, resolved to absolute paths — [] when empty.

    Normalized HERE, beside `entry-point`, for the reason stated on
    `_exposure_rows`: one reader, so the join sites cannot drift. Same two
    rules in the same order (`ws:` expansion, then the `..` refusal), plus the
    danger sigil every entry must carry."""
    cell = (row.get(WRITE_ROOTS_COLUMN) or "").strip()
    if not cell:
        return []
    method = (row.get("method") or "").strip()
    if method != "path":
        raise Refuse(
            "write-root-invalid",
            f"part '{pid}' declares write-roots on a method={method or '(empty)'} "
            "row — a write root belongs to a CLI, so the column is legal on "
            "`method=path` rows ONLY",
            str(manifest))
    out: list[str] = []
    for authored in (e.strip() for e in cell.split(";")):
        if not authored:
            continue
        if not authored.startswith(DANGER_SIGIL):
            raise Refuse(
                "write-root-unmarked",
                f"part '{pid}' declares write-root '{authored}' without the "
                f"danger marker — every entry is written '{DANGER_SIGIL}<path>'. "
                "A write grant reaches a seat only because an author typed the "
                "marker; it is never inferred from a path that merely looks "
                "writable",
                str(manifest))
        body = authored[len(DANGER_SIGIL):].strip()
        if not body:
            raise Refuse(
                "write-root-invalid",
                f"part '{pid}' declares write-root '{authored}' — the marker "
                "carries no path",
                str(manifest))
        # The prefix is stripped BEFORE the `..` test — same order as the
        # entry-point rule, so `!ws:../outside` and a bare `!../outside` take
        # ONE rule and the climb cannot be reintroduced by prefixing it.
        prefixed = body.startswith(WS_PREFIX)
        rel = body[len(WS_PREFIX):] if prefixed else body
        if ".." in PurePosixPath(rel).parts:
            raise Refuse(
                "write-root-escape",
                f"part '{pid}' declares write-root '{authored}', which climbs "
                "with `..` — reach a path elsewhere in the workspace with "
                "`ws:<path-from-the-workspace-root>` instead",
                str(manifest))
        base = _workspace_root(comp_dir) if prefixed else comp_dir
        out.append(str((base / rel).resolve()))
    return out


def _rbtv_repo_root(comp_dir: Path) -> Path:
    """The rbtv REPO tree — the second resolution root a `rbtv:`-prefixed
    reference addresses (owner ruling, 2026-08-10).

    The catalog root and the repo are DIFFERENT TREES: a mirror component
    (`.rbtv/mirror/<module>/<component>/`) cannot reach the repo with the
    3-segment grammar, whose arithmetic is relative to the referencing
    component's own position. So the workspace is derived by
    `_workspace_root` — ONE walk, shared with `ws:` — and the repo path is
    `rbtv.json`'s `rbtv_path` at that root (the same book `{rbtv_path}` is
    resolved from everywhere else). That book must be present and carry its
    field, else REFUSE with what was found.

    ⚠ `.rbtv/config/install.json` is NO LONGER READ (owner ruling 2026-08-11,
    IPH-6 / D33). Its `target` was redundant with the book's OWN location —
    install2 writes `target.resolve()` into `target/.rbtv/config/`, so the two
    can only agree (measured equal on the live install before this landed),
    and the walk-derived value was already the fallback whenever `target` was
    absent. Dropping it deletes a second walk that disagreed with this one
    (file vs directory), a second failure mode, and the reason `rbtv:` could
    not resolve on any workspace that had never run install2."""
    workspace = _workspace_root(comp_dir)
    rbtv_book = workspace / "rbtv.json"
    if not rbtv_book.is_file():
        raise Refuse(
            "exposes-repo-root-underivable",
            f"{rbtv_book} — the book that records `rbtv_path` — does not "
            "exist; a `rbtv:` reference has no tree to resolve against",
            str(workspace))
    try:
        rbtv_path = str((json.loads(rbtv_book.read_text(encoding="utf-8"))
                         or {}).get("rbtv_path") or "").strip()
    except (OSError, ValueError) as exc:
        raise Refuse(
            "exposes-repo-root-underivable",
            f"rbtv.json is not readable JSON — {exc}",
            str(rbtv_book)) from exc
    if not rbtv_path:
        raise Refuse(
            "exposes-repo-root-underivable",
            "rbtv.json carries no `rbtv_path` — a `rbtv:` reference has no "
            "tree to resolve against",
            str(rbtv_book))
    root = Path(rbtv_path)
    if not root.is_absolute():
        root = workspace / root
    if not root.is_dir():
        raise Refuse(
            "exposes-repo-root-underivable",
            f"rbtv.json's `rbtv_path` resolves to {root}, which is not a "
            "directory",
            str(rbtv_book))
    return root


def _refuse_derived_target(path, subject: str) -> None:
    """`refuse_if_derived` spoken in this module's refusal vocabulary.

    The predicate is coord's (`records.refuse_if_derived`) and is never
    re-implemented here; this only re-raises its typed error as a `Refuse` so a
    caller reading machine-readable refusal codes sees one, and so the marker's
    `source:` value survives into the message a seat actually reads."""
    try:
        _refuse_if_derived(path)
    except _DerivedTreeRefusal as exc:
        raise Refuse(
            "target-under-derived-tree",
            f"{subject} — {exc}",
            str(path)) from exc


def _ref_target(comp_dir: Path, ref: str, subject: str) -> tuple[Path, str]:
    """(component dir, part-id) for one reference in the `exposes:` grammar.

    ONE home for the grammar, shared by `resolve_seat_exposes` and W6's
    `exposes-cli:` chain — a second copy is a second place the arithmetic can
    drift. `subject` is the caller's already-composed "who did what" clause, so
    a refusal reads the same from either door.

    Grammar, disambiguated by segment count (owner-ruled 2026-08-09,
    cross-module must exist): `part` = own component · `component/part` =
    sibling component, same module · `module/component/part` = another
    module's component, resolved from the referencing component's position
    (comp_dir.parent.parent = the tree root above the modules) — identical
    arithmetic for the mirror and the rbtv repo, both `<tree>/<module>/
    <component>/`. …plus the SECOND ROOT (owner-ruled 2026-08-10): a `rbtv:`
    reference resolves against the rbtv REPO tree instead."""
    if ref.startswith("rbtv:"):
        segs = ref[len("rbtv:"):].split("/")
        if len(segs) < 2 or not all(s.strip() for s in segs):
            raise Refuse(
                "exposes-invalid",
                f"{subject} — a `rbtv:` reference is "
                "`rbtv:<path-under-the-repo>/<part>` and needs at least one "
                "directory segment before the part-id",
            )
        target = _rbtv_repo_root(comp_dir).joinpath(*segs[:-1])
        _refuse_derived_target(target, subject)
        return target, segs[-1]
    segs = ref.split("/")
    if not all(s.strip() for s in segs) or len(segs) > 3:
        raise Refuse(
            "exposes-invalid",
            f"{subject} — a reference is `part`, `component/part`, or "
            "`module/component/part`; empty segments or deeper nesting are "
            "not expressible",
        )
    catalog, mirror, repo = _scan_all(comp_dir)
    # ⚠ `own` IS RESOLVED INSIDE THE BRANCHES THAT READ IT, AND THAT IS
    # LOAD-BEARING. `_own_component_id` REFUSES any referencing dir that is not
    # a depth-2 component of the mirror or the repo, and the goal-local lane
    # (`<goal>/planning/current/seat-lane/goal-local/goal-local`) is neither, by
    # construction. A THREE-segment reference is fully qualified and never reads
    # `own`, so resolving it up front refused every goal-authored seat over an
    # identity its own reference does not use — it froze two live goals for
    # hours (meet-transcript-summarizer, stools-canvas-audio-elevenlabs) after
    # `0563266b` replaced this function's root-agnostic path arithmetic with the
    # two-root lookup. The 1- and 2-segment forms ARE defined in terms of the
    # referencing component's own identity, so they still refuse from the lane:
    # that refusal is CORRECT and is the ruling
    # `p-goal-local-seats-cannot-use-bare-part-ids-2026-08-23`. Do not hoist.
    if len(segs) == 1:
        cid, pid = _own_component_id(comp_dir, catalog, mirror, repo), segs[0]
    elif len(segs) == 2:
        own = _own_component_id(comp_dir, catalog, mirror, repo)
        cid, pid = f"{own.split('/', 1)[0]}/{segs[0]}", segs[1]
    else:
        cid, pid = f"{segs[0]}/{segs[1]}", segs[2]
    rec = catalog.get(cid)
    if rec is None:
        raise Refuse(
            "exposes-ref-dangling",
            f"{subject} — no component {cid!r} in scan_all "
            f"(mirror={mirror} · repo={repo})",
        )
    # C10 (bind-into-lane): a reference whose target resolves at or under a
    # marked DERIVED root would bind the seat to a copy the next materialize
    # rewrites. The lane REGENERATOR is exempt by construction — it writes
    # `GOAL_LOCAL_LANE` through its own staging path and never through this
    # grammar — so the refusal reaches only a seat reaching INTO the lane.
    target = Path(rec["path"])
    _refuse_derived_target(target, subject)
    return target, pid


def _own_component_id(comp_dir: Path, catalog: dict, mirror: Path,
                      repo: Path) -> str:
    """`<module>/<component>` of the referencing dir, via scan_all or relpath."""
    resolved = comp_dir.resolve()
    for cid, rec in catalog.items():
        if rec.get("kind") == "hub":
            continue
        try:
            if Path(rec["path"]).resolve() == resolved:
                return cid
        except OSError:
            continue
    for root in (mirror, repo):
        try:
            rel = resolved.relative_to(root.resolve())
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    raise Refuse(
        "exposes-ref-dangling",
        f"referencing dir {comp_dir} is not a depth-2 component in scan_all "
        f"(mirror={mirror} · repo={repo})",
        str(comp_dir),
    )


def _frontmatter(path: Path) -> dict:
    """A file's YAML frontmatter as a dict — {} when the file is absent or
    carries none. Refuses on unparseable YAML rather than reading a broken
    card as an empty one."""
    try:
        m = _FM_RE.match(path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise Refuse("frontmatter-unparseable",
                     f"{path}: frontmatter is not YAML — {exc}",
                     str(path)) from exc


def _skill_cli_refs(entry_file: Path) -> list[str]:
    """The flat `exposes-cli:` list off a skill entry-point file's frontmatter
    — [] when the file carries no frontmatter or no key. Absence is normal: a
    skill that routes to no CLI declares nothing."""
    fm = _frontmatter(entry_file)
    raw = fm.get(EXPOSES_CLI_KEY) if isinstance(fm, dict) else None
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(r, str) and r.strip()
                                            for r in raw):
        raise Refuse(
            "skill-cli-invalid",
            f"{entry_file}: `{EXPOSES_CLI_KEY}:` must be a flat list of "
            "non-empty part references (the `exposes:` reference grammar)",
            str(entry_file))
    return [r.strip() for r in raw]


def resolve_cli_write_roots(plan: dict) -> None:
    """W6 · resolution variant B — the MATERIALIZER walks seat → skills → CLIs
    → write-roots and bakes the result into seat.md; spawn.js only reads.

    plan['cli_write_roots'][seat] = sorted absolute roots, deduped BY TARGET.
    The dedup is not tidiness: two identical `--bind` lines for one path are
    what bwrap errors on, and a seat can reach the same CLI twice (directly
    through `exposes: path:` and again through a skill that routes to it).

    Three gates, all at generation time where the author is still holding the
    file:
      · `skill-cli-dangling` — a ref resolving to no row, or to a row whose
        method is not `path`. Enforced HERE and at component-lint both.
      · `exposed-cli-collision` — one part-id reaching two different entry
        points through two different components; the seat would otherwise get
        whichever bind landed last.
      · `write-root-private` — a CLI-derived root landing on a private-scope
        entry. A baked CLI grant is NOT a pierce and may never become one by
        accident: the deny list wins, always, and the refusal says so here
        rather than letting the seat meet a silently masked mount at spawn."""
    plan["cli_write_roots"] = {}
    for seat, parts in (plan.get("expose_parts") or {}).items():
        roots: dict[str, list[str]] = {}     # root -> provenance chain
        entries: dict[str, str] = {}         # cli part-id -> resolved entry
        ws_hint = None
        for method, pid, row, ref_dir in parts:
            ws_hint = ws_hint or ref_dir
            if method != "skill":
                continue
            entry_file = ref_dir / (row.get("entry-point") or "").strip()
            for ref in _skill_cli_refs(entry_file):
                subject = (f"seat '{seat}' exposes skill '{pid}', which routes "
                           f"to CLI '{ref}'")
                cli_dir, cli_pid = _ref_target(ref_dir, ref, subject)
                cli_rows = _exposure_rows(cli_dir)
                cli = cli_rows.get(cli_pid)
                if cli is None or (cli.get("method") or "").strip() != "path":
                    raise Refuse(
                        "skill-cli-dangling",
                        f"{subject} — no `method=path` row '{cli_pid}' under "
                        f"{cli_dir / EXPOSURE_NAME}. A skill is the DISCOVERY "
                        "layer; exposure.csv stays the declaration layer, and "
                        "a dead skill->CLI reference must not reach a "
                        "materialized seat",
                        str(entry_file))
                target = str(Path((cli.get("entry-point") or "").strip()))
                if entries.setdefault(cli_pid, target) != target:
                    raise Refuse(
                        "exposed-cli-collision",
                        f"seat '{seat}' reaches CLI '{cli_pid}' at two "
                        f"different entry points ({entries[cli_pid]} and "
                        f"{target}) — one name cannot bind two targets",
                        str(entry_file))
                for root in cli.get(WRITE_ROOTS_RESOLVED) or ():
                    roots.setdefault(
                        root, [seat, pid, cli_pid])
        if not roots:
            continue
        try:
            private = _private_deny(_workspace_root(ws_hint))
        except Refuse:
            private = []
        for root, chain in sorted(roots.items()):
            for entry in private:
                if root == entry or root.startswith(entry + os.sep):
                    raise Refuse(
                        "write-root-private",
                        f"seat '{chain[0]}' would receive write-root {root} "
                        f"through skill '{chain[1]}' -> CLI '{chain[2]}', and "
                        f"it lands on the private-scope entry {entry}. A "
                        "CLI-derived root is never a pierce: the deny list "
                        "wins. Drop the declaration, or move the CLI's state "
                        "out of the private path",
                    )
            plan["warnings"].append(
                f"write-root GRANTED to seat '{chain[0]}': {root} "
                f"(seat -> skill '{chain[1]}' -> CLI '{chain[2]}' -> root)")
        plan["cli_write_roots"][seat] = sorted(roots)


def _private_deny(workspace_root) -> list[str]:
    """The workspace's private-scope deny entries as absolute paths — [] when
    there is no list. Read here ONLY to REFUSE; `private-scope.js` at spawn
    stays the one authority on what is actually masked (it also owns the
    pattern floor and the realpath aliasing rules)."""
    if not workspace_root:
        return []
    book = Path(workspace_root) / ".rbtv" / "config" / "private.json"
    try:
        deny = (json.loads(book.read_text(encoding="utf-8")) or {}).get("deny")
    except (OSError, ValueError):
        return []
    if not isinstance(deny, list):
        return []
    return [str((Path(workspace_root) / str(e).strip().rstrip("/")).resolve())
            for e in deny if str(e).strip()]


def resolve_seat_exposes(plan: dict, seats_cat: dict) -> None:
    """Resolve + validate every added seat's `exposes:` declaration (ALL
    gates fire here, before any render and any write):
    plan['exposes'][seat] = the authored mapping (normalized), emitted into
    the descriptor frontmatter; plan['expose_parts'][seat] = the resolved
    [(method, part-id, row, component dir)] the loader render consumes.
    Every reference must resolve to an exposure.csv row whose `method`
    column EQUALS its group key and whose entry-point file exists."""
    plan["exposes"], plan["expose_parts"] = {}, {}
    for seat in plan["added_seats"]:
        source = str((seats_cat.get(seat) or {}).get("__source__") or "")
        if not source:
            continue
        comp_dir = Path(source).parent
        srow = seats_cat.get(seat) or {}
        executor = (srow.get("prompt-id") or srow.get("executor") or "").strip()
        exposes = _prompt_exposes(comp_dir, executor, seat)
        # F5: a user-facing seat's configured skill parts join its declared
        # set here, BEFORE the gates below — an injected reference is held to
        # exactly the same resolution, method and entry-point checks as an
        # authored one, and nothing downstream can tell them apart.
        if _assembled_is_interactive((plan.get("assembled") or {}).get(seat)):
            extra = [r for r in _interactive_expose_refs(comp_dir)
                     if r not in exposes.get("skill", [])]
            if extra:
                exposes = {**exposes,
                           "skill": [*exposes.get("skill", []), *extra]}
        if not exposes:
            continue
        parts: list[tuple[str, str, dict, Path]] = []
        for method, refs in exposes.items():
            for ref in refs:
                # Ref grammar, disambiguated by segment count (owner-ruled
                # 2026-08-09, cross-module must exist): `part` = own
                # component · `component/part` = sibling component, same
                # module · `module/component/part` = another module's
                # component, resolved from the referencing component's
                # position (comp_dir.parent.parent = the tree root above
                # the modules) — identical arithmetic for the mirror and
                # the rbtv repo, both `<tree>/<module>/<component>/`.
                # …plus the SECOND ROOT (owner-ruled 2026-08-10): a
                # `rbtv:`-prefixed reference resolves against the rbtv REPO
                # tree instead of the referencing component's own tree —
                # `rbtv:<component>/<part>` at whatever depth the repo puts
                # the manifest (`rbtv:ignite/coordinate` today, module root;
                # `rbtv:ignite/coord/coordinate` after the CMP-5 move,
                # same line). Unprefixed references are untouched.
                ref_dir, pid = _ref_target(
                    comp_dir, ref, f"seat '{seat}' exposes '{ref}' ({method})")
                rows = _exposure_rows(ref_dir)
                if pid not in rows:
                    extra = ""
                    if not ref.startswith("rbtv:"):
                        try:
                            _, mirror, repo = _scan_all(comp_dir)
                            extra = (f"; scanned scan_all(mirror={mirror} · "
                                     f"repo={repo})")
                        except Refuse:
                            extra = ""
                    raise Refuse(
                        "exposes-ref-dangling",
                        f"seat '{seat}' exposes '{ref}' ({method}) — no "
                        f"exposure.csv row '{pid}' under "
                        f"{ref_dir / EXPOSURE_NAME}{extra}; a dead reference "
                        "must not reach a materialized seat (grammar: `part` "
                        "· `component/part` · `module/component/part`)",
                    )
                declared = (rows[pid].get("method") or "").strip()
                if declared != method:
                    raise Refuse(
                        "exposes-method-mismatch",
                        f"seat '{seat}' exposes '{ref}' under '{method}' but "
                        f"its exposure.csv row declares method "
                        f"'{declared or '(empty)'}' — the manifest is the "
                        "one home of the part -> method binding (PRIN-11); "
                        "fix the frontmatter or the manifest",
                        str(ref_dir / EXPOSURE_NAME))
                entry = (rows[pid].get("entry-point") or "").strip()
                if not entry or not (ref_dir / entry).is_file():
                    # The AUTHORED cell is quoted, not the normalized one — a
                    # `ws:` row's resolved absolute path is not what anyone
                    # typed, so the fix is unfindable from it; the resolution
                    # rides alongside so the join base stays visible.
                    authored = rows[pid].get(ENTRY_AUTHORED) or entry
                    raise Refuse(
                        "exposes-entry-missing",
                        f"seat '{seat}' exposes '{ref}' ({method}) whose "
                        f"entry-point '{authored or '(empty)'}' resolves to no "
                        f"file ({ref_dir / entry}) — nothing to realize",
                        str(ref_dir / EXPOSURE_NAME))
                parts.append((method, pid, rows[pid], ref_dir))
        plan["exposes"][seat] = exposes
        plan["expose_parts"][seat] = parts


def _seat_rules_from_parts(plan: dict) -> dict[str, list[tuple[str, str]]]:
    """The rule-method subset of each seat's resolved exposes — the ONE derivation the
    guidance preamble renders from, shared by the materialize, --repass and --refresh
    paths (a plain repass re-renders the guidance pair without planning loader files,
    so the preamble list cannot live inside render_seat_exposures alone)."""
    out: dict[str, list[tuple[str, str]]] = {}
    for seat, parts in (plan.get("expose_parts") or {}).items():
        rules = [(pid, (row.get("description") or "").strip()
                  or f"{pid} — exposed via {ref_dir.name}/exposure.csv")
                 for method, pid, row, ref_dir in parts if method == "rule"]
        if rules:
            out[seat] = rules
    return out


def render_seat_exposures(plan: dict) -> None:
    """Plan the per-seat loader files for the resolved `exposes:` parts
    (validation already fired in resolve_seat_exposes) and DECLARE each in
    writes[]. Hooks MERGE into the .claude/settings.json the plugin/MCP
    surface may already carry — one writer per file, never two."""
    plan["seat_exposures"] = {}
    plan["seat_rules"] = _seat_rules_from_parts(plan)
    for seat, parts in (plan.get("expose_parts") or {}).items():
        files: dict[str, str] = {}
        hooks: dict = {}
        for method, pid, row, ref_dir in parts:
            entry = str((ref_dir / (row.get("entry-point") or "").strip())
                        .resolve())
            desc = (row.get("description") or "").strip() \
                or f"{pid} — exposed via {ref_dir.name}/exposure.csv"
            if method == "skill":
                text = _loader_md(pid, desc, entry, "skill", named=True)
                files[f".claude/skills/{pid}/SKILL.md"] = text
                files[f".agents/skills/{pid}/SKILL.md"] = text
            elif method == "command":
                text = _loader_md(pid, desc, entry, "command", named=False)
                files[f".claude/commands/{pid}.md"] = text
                files[f".opencode/commands/{pid}.md"] = text
                # codex prompt files are plain markdown — no frontmatter.
                files[f".codex/prompts/{pid}.md"] = (
                    _LOADER_NOTE + "\n\n"
                    f"Read `{entry}` NOW and follow it as this command's "
                    "full instructions.\n")
            elif method == "rule":
                body = (ref_dir / row["entry-point"].strip()).read_text(
                    encoding="utf-8")
                files[f".claude/rules/{pid}.md"] = body
                files[f".agents/behavior-rules/{pid}.md"] = body
                # (the guidance preamble's (pid, desc) list is derived once, in
                # _seat_rules_from_parts — never accumulated here a second time)
            elif method == "sub-agent":
                text = _loader_md(pid, desc, entry, "sub-agent", named=True)
                files[f".claude/agents/{pid}.md"] = text
                files[f".opencode/agents/{pid}.md"] = text
                # codex sub-agent definition — MEASURED 2026-08-12 on codex-cli
                # 0.147.0 (d-uniform-descriptor-carriage, second measurement
                # amendment): `.codex/agents/<name>.toml` is read PROJECT-LOCALLY
                # and its honored instruction field is `developer_instructions`
                # (token test; `instructions` and `description` never reached the
                # agent) — but ONLY when the folder is trusted in the user's
                # `~/.codex/config.toml` ([projects."<dir>"] trust_level =
                # "trusted"; an argv `-c` override does NOT unlock it). This file
                # is therefore INERT until the seat folder is trusted — trust
                # management is a deployment act, tracked separately; writing the
                # definition here keeps the seat complete the day it is.
                # json.dumps output is a valid TOML basic string for this text.
                files[f".codex/agents/{pid}.toml"] = (
                    f"# {_LOADER_NOTE}\n"
                    f"name = {json.dumps(pid)}\n"
                    f"description = {json.dumps(desc)}\n"
                    "developer_instructions = "
                    + json.dumps(f"Read `{entry}` NOW and follow it as this "
                                 "sub-agent's full instructions.") + "\n")
            elif method == "hook":
                try:
                    data = json.loads(Path(entry).read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise Refuse(
                        "hook-declaration-invalid",
                        f"hook entry-point for '{pid}' (seat '{seat}') is "
                        f"not readable JSON ({exc}) — refusing before any "
                        "write",
                        entry) from exc
                decl = data.get("hooks") if isinstance(data, dict) else None
                if not isinstance(decl, dict):
                    raise Refuse(
                        "hook-declaration-invalid",
                        f"hook entry-point for '{pid}' (seat '{seat}') "
                        "carries no `hooks` object — the neutral shape is "
                        "claude's settings `hooks` block",
                        entry)
                for event, entries in decl.items():
                    hooks.setdefault(event, []).extend(
                        entries if isinstance(entries, list) else [entries])
        if hooks:
            mcp_files = (plan.get("harness_configs") or {}).get(seat)
            settings: dict = {}
            if mcp_files and ".claude/settings.json" in mcp_files:
                settings = json.loads(mcp_files[".claude/settings.json"])
            settings["hooks"] = hooks
            text = json.dumps(settings, indent=2, sort_keys=True) + "\n"
            if mcp_files and ".claude/settings.json" in mcp_files:
                # already planned AND declared by the plugin/MCP surface —
                # replace its content, add no second writes[] row.
                mcp_files[".claude/settings.json"] = text
            else:
                files[".claude/settings.json"] = text
            # codex 0.144.5 measured shape: the claude `hooks` object
            # verbatim + an optional top-level `description` (provenance).
            files[".codex/hooks.json"] = json.dumps(
                {"description": f"Generated by materialize-seats.py for "
                                f"seat '{seat}' from its component's "
                                "exposure manifest — regenerated freely, "
                                "never hand-edited.",
                 "hooks": hooks}, indent=2, sort_keys=True) + "\n"
        if files:
            plan["seat_exposures"][seat] = files
            for rel in sorted(files):
                plan["writes"].append({
                    "kind": "seat-exposure", "seat": seat,
                    "path": str(seat_home(Path(plan["package"]), seat)
                                / rel)})


def emit_seat_exposures(plan: dict) -> list[str]:
    """Write the planned loaders — AGENTS.md semantics (derived,
    deterministic, regenerated freely; byte-identical → skipped)."""
    written: list[str] = []
    for seat, files in (plan.get("seat_exposures") or {}).items():
        folder = seat_home(Path(plan["package"]), seat)
        for rel, text in files.items():
            target = folder / rel
            _refuse_derived_target(
                target, f"the exposure loaders of seat '{seat}'")
            if target.exists() and target.read_text(encoding="utf-8") == text:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
            target.chmod(0o644)
            written.append(str(target))
    return written


def emit_seat_descriptors(plan: dict) -> list[str]:
    """dag-04 — write the rendered descriptors: file mode 0644, folder 0755.
    Every gate already fired in render_descriptors (before any write); under
    --force-partial an existing seat.md must byte-match the freshly rendered
    one (completing a partial failure, never overwriting drift).

    Each seat also gets its GUIDANCE PAIR — `CLAUDE.md` + `AGENTS.md`, one body under
    each harness's native guidance name (see `_SEAT_GUIDANCE_MD`)."""
    written: list[str] = []
    for seat in plan["added_seats"]:
        text = plan["descriptors"][seat]
        folder = seat_home(Path(plan["package"]), seat)
        target = folder / "seat.md"
        _refuse_derived_target(target, f"the descriptor of seat '{seat}'")
        if target.exists():
            if not plan["force_partial"]:
                raise Refuse(  # unreachable past check_collisions; kept loud
                    "seat-exists",
                    f"seats/{seat}/seat.md already exists — materialize "
                    "never overwrites",
                    str(target),
                )
            if target.read_text(encoding="utf-8") != text:
                raise Refuse(
                    "partial-descriptor-mismatch",
                    f"seats/{seat}/seat.md exists and does not byte-match "
                    "the freshly assembled descriptor — --force-partial "
                    "completes a partial failure, never overwrites drift",
                    str(target),
                )
            # The descriptor is already correct; the GUIDANCE PAIR may still be missing —
            # completing a partial failure has to complete both halves.
            written.extend(_write_seat_guidance(
                folder, seat, Path(plan["package"]),
                (plan.get("seat_rules") or {}).get(seat, ())))
            continue
        folder.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        target.chmod(0o644)
        folder.chmod(0o755)
        written.append(str(target))
        written.extend(_write_seat_guidance(
            folder, seat, Path(plan["package"]),
            (plan.get("seat_rules") or {}).get(seat, ())))
    return written


def _descriptor_binding(plan: dict, seat: str) -> dict:
    """harness/model/effort/ctx-refresh EXACTLY as the emitted descriptor
    carries them — parsed back OUT of the rendered descriptor text, never
    re-derived from the bindings file, so the registry row cannot drift from
    the file `check_bindings` (coord.py) compares it against. This equality IS
    what check_bindings asserts at launch."""
    fm = yaml.safe_load(_FM_RE.match(plan["descriptors"][seat]).group(1))
    ctx = fm.get("ctx-refresh")
    return {
        "harness": str(fm.get("harness", "") or ""),
        "model": str(fm.get("model", "") or ""),
        "effort": str(fm.get("effort", "") or ""),
        "ctx-refresh": "" if ctx in (None, "") else str(ctx),
    }


def _render_csv_line(values: list[str]) -> str:
    """One registry line, csv-quoted exactly as the append writes it (a
    multi-predecessor `after` cell carries commas and must quote).

    ⚠ DELEGATES to `goal_cli.render_csv_line` — THE canonical form, and the
    single-writer claim `add-seat`'s canonical-form guard depends on: that guard
    re-renders every untouched row through goal_cli's writer and requires
    byte-equality with what THIS append produced. Two writers would let the
    guard pass on a file the append would have written differently."""
    return render_csv_line(values)


def render_taskforce_rows(plan: dict) -> None:
    """dag-05 — plan the registry append WITHOUT writing: read taskforce.csv,
    run the three validations, and render the rows in topological order of the
    added subgraph into plan['registry']. Fires BEFORE any write (descriptors
    included) and before the --dry-run return, so a refusal here always leaves
    zero files and zero rows.

    THE MULTI-TASKFORCE ANSWER (`d-staff-chair-joins-first-taskforce`, owner
    2026-08-14). A goal whose registry carries more than one bare taskforce-id
    refuses `taskforce-id-unreadable` for every ordinary seat — which taskforce a
    workflow node joins is not this command's to guess. It is ANSWERED for a
    STAFF CHAIR alone: the chair takes the goal's FIRST taskforce-id (the earliest
    row carrying a bare id), because a chair holds no workflow node and its id is
    read by nothing. See the ⚠ block at the gate for the evidence.

    Q8 second-carrier note (d-spec-open-points-ruled Q8; verified at dag-05
    implementation): the verbatim 15-rule DAG-authoring block is carried by
    TWO surfaces, both under .rbtv/mirror/meta/planning-deprecated/ (pre-rename planner-workflow) —
    (1) that DELETED component's own workflows/planning/workflow.md § "DAG-authoring
        rules" (the source; git history only — unrelated to the live meta/planning
        component, whose workflow is plan-console since the 2026-08-24 rename),
    (2) prompts/cognitive-units/procedures/workflow-designer.md § "The
    DAG-authoring rules — carried VERBATIM" (the byte-identical copy).
    Of the 15 rules, THIS command enforces MECHANICALLY:
      Rule 8  — validation 2 (every `after` member resolves: validate_after
                for the --after argv, check_acyclic's edge-resolution findings
                for the resulting graph),
      Rule 9  — validation 1 (acyclicity of the RESULTING graph, via
                goal_cli.check_acyclic — never a hand-rolled walk),
      Rule 13 — the frozen-copy `after` cells below (manifest cells VERBATIM
                APART FROM THE INSTANCE RENAMING — the amended wording, owner
                ruling `d-owner-7545-7551-design-rulings-0808` criterion 8 /
                dossier §7 Q3 (a); the --after/--root insertion point only on
                the added roots),
      Rule 14 — validation 3 (no status column; TASKFORCE_HEADER check),
      and Rule 7 (root declared, never defaulted — the --after/--root
      mutually-exclusive required group) plus Rule 11's registry half (a
      duplicate seat row/folder refuses: check_collisions,
      registry-duplicate-row).
    Rules 1–6, 10, 12, 15 (and Rule 5's pure-chain justification, Rule 11's
    concurrent-pair naming) are carried as the DOCUMENTATION block only —
    authoring-time judgment this command cannot check."""
    tf_path = Path(plan["package"]) / TASKFORCE_NAME
    creating_tf = any(c["surface"] == TASKFORCE_NAME
                      for c in plan.get("creation", ()))
    if creating_tf:
        # dag-06: the registry does not exist yet — every validation below
        # runs against the header-only content create_run_package writes in
        # this same act (append_taskforce_rows re-reads and compares, so a
        # divergence between plan and disk still refuses loudly).
        text = ",".join(TASKFORCE_HEADER) + "\n"
    elif not tf_path.is_file():
        raise Refuse(
            "registry-absent",
            f"the goal package carries no {TASKFORCE_NAME} — the append needs "
            "the run's registry (its taskforce-id is read from the file, "
            "never argv). Completing this package is dag-06's creation step: "
            "re-run with --claude-md/--budget-json so the missing "
            "surfaces can be created from caller-supplied content",
            str(tf_path),
        )
    else:
        text = tf_path.read_text(encoding="utf-8")
    # D-2: `if text` — a ZERO-BYTE registry is not an unterminated tail. It carries no partial
    # trailing line to be unparseable, so diagnosing it as corruption sent the operator to repair
    # a file that has nothing to repair. Empty now falls through to the header check, which names
    # the header it lacks.
    # ponytail: the empty file lands on `registry-header-drift`, not the `registry-absent` it
    # reads like — `registry-absent` and `plan_package_creation` both gate on `is_file()`, so
    # routing it there would print creation advice that cannot fire. Upgrade path: teach BOTH
    # those `is_file()` tests to treat a zero-byte registry as absent, in one change.
    if text and not text.endswith("\n"):
        raise Refuse(
            "registry-tail-unterminated",
            f"{TASKFORCE_NAME} does not end in a newline — a partial trailing "
            "line is unparseable by every consumer at once; repair the "
            "registry before materializing",
            str(tf_path),
        )
    lines = text.split("\n")[:-1]
    header_line = lines[0] if lines else ""
    header = [h.strip() for h in (next(csv.reader([header_line]))
                                  if header_line else [])]

    # VALIDATION 3 (Rule 14): no status column is introduced — and none is
    # PROPAGATED: a fixture header already carrying `status` refuses rather
    # than being copied forward. Run-state is DERIVED from the check-out
    # record + declared outputs; a status column here is a second ledger.
    if "status" in header:
        raise Refuse(
            "status-column",
            f"{TASKFORCE_NAME} header carries a 'status' column — run-state "
            "is DERIVED from the check-out record + declared outputs (KG "
            "taskforce-descriptor; workflow.md DAG-authoring Rule 14); a "
            "status column is a second ledger, refused rather than propagated",
            str(tf_path),
        )
    if header != list(TASKFORCE_HEADER):
        raise Refuse(
            "registry-header-drift",
            f"{TASKFORCE_NAME} header is {header_line!r}, not the run-2 live "
            "shape '" + ",".join(TASKFORCE_HEADER) + "' — the written header "
            "must equal the read header exactly, so a drifted header refuses "
            "rather than being silently rewritten or extended",
            str(tf_path),
        )

    existing_rows: list[dict] = []
    raw_by_seat: dict[str, str] = {}
    tf_by_seat: dict[str, str] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        row = dict(zip(header, next(csv.reader([line]))))
        existing_rows.append(row)
        seat = (row.get("seat") or "").strip()
        if not seat:
            continue
        if seat in raw_by_seat:
            raise Refuse(
                "registry-duplicate-row",
                f"{TASKFORCE_NAME} carries two rows for seat '{seat}' — "
                "repair the registry before materializing (Rule 11: a seat id "
                "is unique)",
                str(tf_path),
            )
        raw_by_seat[seat] = line
        tf_by_seat[seat] = (row.get("taskforce-id") or "").strip()

    # taskforce-id: the taskforce's EXISTING id, read from the file — never
    # argv. dag-06 bootstrap story: a registry with ZERO data rows (a freshly
    # created, header-only taskforce.csv — first materialize into a created
    # package) carries no id to read, so the id is DERIVED by the COUNTER in
    # the goal's own taskforce.csv — max existing + 1, design-lock item 10
    # (derive_taskforce_id). No folder-name input: the package is the goal
    # folder and its name is the goal, so the ordinal's one honest source is
    # the file. Deterministic and never argv.
    # ⚠ BOUNDARY, DISCLOSED: the derivation still fires ONLY on zero data rows,
    # so on a goal-durable registry the counter is exercised exactly once. WHEN
    # a second taskforce is minted inside one goal (a recurring goal's next
    # execution) is an unsettled design question the lock does not answer, and
    # inventing a rule for it here would be a design act. Until it is ruled, a
    # registry that HAS rows still yields their one id. A
    # registry that HAS rows but no readable id still refuses (red arm), and
    # an id read from rows always wins over the derivation.
    #
    # ⚠ TWO CASES OF THAT QUESTION ARE NOW RULED, and only two: the STAFF CHAIR
    # (`d-staff-chair-joins-first-taskforce`, owner 2026-08-14) and the SUMMONED
    # SEAT (D24 / roles sitting 3, 2026-08-20). A chair holds no workflow node,
    # so its id has NO mechanical consequence anywhere — nothing routes, wakes
    # or verdicts on it (`coord.py#is_staff_seat`, `staff_route_target`,
    # both key on the seat NAME); the only other reader in the
    # system is `coord.py#taskforce_ids`, a display accessor. Refusing the chair
    # over a value nothing reads left the flagship goal — two taskforces —
    # permanently unstaffable, which is the exact empty-chair defect the staff
    # pass exists to end. A summoned seat (`goal-master`) is the same shape:
    # no workflow node, D24 already excludes it from READY, and the live goals
    # this seat must inhabit carry many bare ids. The ruled answer is the
    # goal's FIRST taskforce: the id of the earliest row carrying a bare id,
    # i.e. the taskforce that existed when the goal was first materialized.
    # File order, not `max`/`min` of the ordinals: an id may legitimately be
    # non-numeric (`tf-a` in the wild, see BARE_TF_RE) and a rule that cannot
    # rank those is a rule with a hole in it.
    # The AMBIGUITY THE GATE PROTECTS IS UNTOUCHED FOR EVERY OTHER SEAT: an
    # ordinary seat is a workflow node, its id says which taskforce it belongs
    # to, and guessing that is exactly the design act this gate refuses. The lift
    # is keyed on the ADDED SET being first-taskforce joiners (staff ∪ summoned)
    # and nothing else. STAFF_SEATS is not widened.
    #
    # ⚠ THE NESTED PATH TAKES NEITHER BRANCH. A nested instance mints its OWN
    # id (`tf-<n>-<prefix><m>`, owner ruling `d-r2-tfid-structured-counter`) so
    # the roster can tell one instance's rows from another's — which is the
    # IDENTITY the deleted branch package used to carry in its folder name. Two
    # consequences, both deliberate: the goal's bare id is READ past those rows
    # (the filter below — nested ids are a second namespace in one column), and
    # a registry carrying ONLY nested rows still refuses `taskforce-id-
    # unreadable`, since a nested instance always attaches after a parent row.
    #
    # ⚠ F1 IS N/A FOR THE SPLICE PATH, AND THAT WAS VERIFIED, NOT ASSUMED (W7).
    # F1 is "the materializer refuses any multi-taskforce registry" — the
    # `len(ids) != 1` arm below, which is what made D5's queue-fired
    # materialization impossible on a goal that already carries more than one
    # taskforce. W7's wave re-entry does not meet it: the `if nested:` branch
    # immediately below is evaluated FIRST and returns, so a nested splice never
    # reaches the arm no matter how many ids the registry carries. No fix is
    # applied to the flat arm and that is the RULING, not an omission — for an
    # ORDINARY seat the id says which taskforce the seat belongs to, and picking
    # one from an ambiguous set is the design act this gate exists to refuse
    # (see the paragraph above). Manual and scratch materializes still hit it,
    # deliberately; the answer for them is `--nested`, which names the series
    # instead of guessing it.
    #
    # ⚠ ONE MORE ARM DOES NOT REACH IT, for the same reason `--nested` does not:
    # a `--force-partial` run whose seats ALREADY HAVE ROWS reads their id off
    # those rows (the branch below). Not a lift of the gate — the gate refuses
    # GUESSING which taskforce a seat joins, and a seat that has a row has
    # already joined one; the run appends nothing and only completes the
    # descriptor half. This is what the W7 goal-local lane does on EVERY
    # invocation, and refusing it left the flagship's own authored seats
    # unbuildable over a value written in the very file being read.
    # ⚠ AND IT IS NOT GATED ON THE SET BEING AMBIGUOUS. It once fired only when
    # `len(ids) != 1`, which read as "only step in where the guess is
    # impossible" and was wrong in the other direction: a registry carrying ONE
    # bare id plus nested ones (`tf-1` + `tf-2-plan1`) fell through to the
    # single-id `else` and completed a NESTED row under the bare id — a
    # `partial-row-mismatch` on a run that had the right answer written in the
    # row it was completing. A seat that already has a row never guesses,
    # whatever the rest of the file carries; where the two agree the value is
    # identical either way, so the narrower gate bought nothing.
    ids = {(r.get("taskforce-id") or "").strip() for r in existing_rows}
    ids.discard("")
    ids = {i for i in ids if not NESTED_TF_RE.fullmatch(i)}
    nested = plan.get("nested")
    if nested:
        tf_id = derive_taskforce_id(Path(plan["package"]),
                                    nested["prefix"], nested["ordinal"])
    elif not existing_rows:
        tf_id = derive_taskforce_id(Path(plan["package"]))
    elif len(ids) > 1 and set(plan["added_seats"]) <= _first_taskforce_joiners():
        tf_id = next(i for r in existing_rows
                     if (i := (r.get("taskforce-id") or "").strip()) in ids)
    elif (plan["force_partial"]
          and set(plan["added_seats"]) <= set(tf_by_seat)):
        # ⚠ THE PURE COMPLETION — NOT A SECOND LIFT OF THE GATE. Every seat of
        # this run ALREADY has a registry row, so the run appends NOTHING: the
        # rows below are rendered only to be byte-compared against the ones on
        # disk (`partial-row-mismatch`), and the descriptor is the half being
        # completed. The id is therefore READ from those very rows — the same
        # "never argv, always the file" source the gate protects — and no
        # taskforce is chosen for any seat. Refusing here refused a run that had
        # nothing to guess: it is what left the flagship's goal-local seats
        # (tf-2 in a tf-1+tf-2 registry) unbuildable by the W7 lane, whose
        # every invocation is exactly this completion. If the held rows
        # DISAGREE the ambiguity is real again and the refusal below stands.
        held = {tf_by_seat[s] for s in plan["added_seats"]}
        if len(held) == 1:
            tf_id = next(iter(held))
        else:
            raise Refuse(
                "taskforce-id-unreadable",
                f"the run completes existing {TASKFORCE_NAME} rows and those "
                f"rows carry {len(held)} distinct id(s) ("
                + (", ".join(sorted(held)) or "none") + ") — one run writes "
                "one taskforce's rows; nothing materialized",
                str(tf_path),
            )
    elif len(ids) != 1:
        raise Refuse(
            "taskforce-id-unreadable",
            f"the run's taskforce-id is read from existing {TASKFORCE_NAME} "
            f"rows, never argv, and the file carries {len(ids)} distinct "
            "id(s) (" + (", ".join(sorted(ids)) or "none") + ") — nothing "
            "materialized",
            str(tf_path),
        )
    else:
        tf_id = next(iter(ids))

    # The `after` cells — the FROZEN DAG copy (Rule 13, KG
    # taskforce-descriptor): an internal row copies the workflow manifest's
    # own cell VERBATIM APART FROM THE INSTANCE RENAMING; the added subgraph's
    # roots take the --after set (or empty with --root). Nothing else ever
    # computes an edge.
    #
    # ⚠ THE AMENDMENT, and the divergence it records (owner ruling
    # `d-owner-7545-7551-design-rulings-0808` criterion 8, overriding this
    # copy's former "verbatim, nothing else ever computes an edge"). On the
    # NESTED path a cell's members are seat ids of the instance being
    # materialized, so a byte-verbatim copy would point every internal edge at
    # the BARE ids — which name the sibling instance's rows, or nothing. The
    # members are therefore mapped through `compose_seat_name` — the SAME
    # single naming function every other name goes through — and that is a
    # MECHANICAL RENAME, not an authored edge: the membership, the ordering,
    # the guards and the alternates are untouched. It affects the nested path
    # ONLY; ordinary goal materialization still copies the cell byte-for-byte,
    # which is what the loop below does and all it does. The rename happens
    # ONCE, in `run`'s `--nested` re-key (`rename_after_cell`), so by the time
    # the cell reaches this loop it is already the instance's own — this loop
    # copies verbatim on both paths and knows nothing about instances.
    attach_cell = ",".join(plan["attach_after"])
    after_cells = {
        seat: (plan["internal_after_raw"][seat]
               if plan["internal_after"][seat] else attach_cell)
        for seat in plan["added_seats"]
    }

    # VALIDATION 1 (Rule 9): acyclicity of the RESULTING graph — existing
    # rows plus the rows this run would append — through goal_cli's own
    # check_acyclic, NEVER a hand-rolled walk. Its edge-resolution findings
    # double as validation 2's resulting-graph arm (Rule 8): unreachable for
    # the added rows by construction, kept as a loud backstop.
    combined = [{"seat": (r.get("seat") or "").strip(),
                 "after": (r.get("after") or "").strip()}
                for r in existing_rows]
    combined += [{"seat": s, "after": after_cells[s]}
                 for s in plan["added_seats"]]
    findings = Findings()
    check_acyclic(combined, findings, tf_path)
    cycles = [i["reason"] for i in findings.items
              if i["check"] == "after graph acyclic"]
    if cycles:
        raise Refuse(
            "cycle-introduced",
            "the RESULTING after-graph is not acyclic "
            "(goal_cli.check_acyclic, workflow.md DAG-authoring Rule 9): "
            + "; ".join(cycles) + " — nothing materialized",
            str(tf_path),
        )
    dangling = [i["reason"] for i in findings.items
                if i["check"] == "after edge resolves"
                and any(f"seat '{s}'" in i["reason"]
                        for s in plan["added_seats"])]
    if dangling:
        raise Refuse("after-unresolved", "; ".join(dangling), str(tf_path))

    # Topological order of the added subgraph (stable: manifest order among
    # ready seats). Acyclicity is already proven above; the no-progress
    # refusal is a loud unreachable, never the cycle check (Rule 9's check is
    # check_acyclic alone).
    ordered: list[str] = []
    placed: set[str] = set()
    pending = list(plan["added_seats"])
    while pending:
        ready = [s for s in pending
                 if all(p in placed for p in plan["internal_after"][s])]
        if not ready:
            raise Refuse(
                "cycle-introduced",
                "the added subgraph does not topologically order: "
                + ", ".join(pending),
            )
        for seat in ready:
            ordered.append(seat)
            placed.add(seat)
            pending.remove(seat)

    # Render every row IN MEMORY (cmd_materialize's own discipline — a refusal
    # on seat 7 of 7 leaves zero rows). Under --force-partial an EXISTING row
    # must byte-match the row this run would write — completing a partial
    # failure, never overwriting drift; only the MISSING rows are appended.
    append_lines: list[str] = []
    matched: list[str] = []
    for seat in ordered:
        b = _descriptor_binding(plan, seat)
        line = _render_csv_line([
            tf_id, seat, after_cells[seat], b["harness"], b["model"],
            b["effort"], b["ctx-refresh"], plan["milestone_id"],
        ])
        held = raw_by_seat.get(seat)
        if held is not None:
            # Reachable only under --force-partial: check_collisions refused
            # the non-force collision before any rendering began.
            if held != line:
                raise Refuse(
                    "partial-row-mismatch",
                    f"{TASKFORCE_NAME} row for seat '{seat}' exists and does "
                    "not byte-match the row this run would write — "
                    "--force-partial completes a partial failure, never "
                    f"overwrites drift (existing: {held!r}; would write: "
                    f"{line!r})",
                    str(tf_path),
                )
            matched.append(seat)
            continue
        append_lines.append(line)
    plan["registry"] = {
        "path": str(tf_path),
        "text": text,
        "header": header_line,
        "append_lines": append_lines,
        "matched_seats": matched,
        "ordered": ordered,
        # The run's taskforce-id, published so the run-register row carries the
        # SAME value this append writes — derived ONCE, read by both surfaces,
        # never recomputed per surface (PRIN-11).
        "taskforce_id": tf_id,
    }


def _rewrite_in_place(path: Path, new_text: str) -> None:
    """Replace a csv's whole content IN PLACE — same inode, one `pwrite` under
    an exclusive `flock`. NEVER an open-append (a partial line in a csv is
    unparseable by every consumer at once), and — since task 08 — never
    `tmp + os.replace` either. Shared by both append writers (the taskforce
    registry and the run register) so the two can never drift into two
    different write disciplines.

    WHY NOT os.replace, measured 2026-08-15 (task 08 / the 2026-08-14
    `plan-2-plan-planner` EROFS). A single-file bind mount attaches to a
    DENTRY, not to a pathname. `os.replace` unlinks the file a seat's cage
    bound and puts a NEW inode under the same name; the seat's next lookup
    resolves a fresh dentry carrying no mount override, falls through the
    cage's enclosing `--ro-bind / /` floor, and every write fails EROFS. That
    is one shared `composeCageFor` path, so a splice here locked out EVERY
    seat declaring `goal-writes` on the spliced file — and it locked out this
    very function when the caller is itself inside the cage, because
    `os.replace` over a bind mountpoint cannot work at all. Keeping the inode
    keeps the bind. (The alternative — widening the cage bind to the
    CONTAINING DIRECTORY — survives the replace but hands a seat the whole
    goal folder and needs a companion carve to take back what it must not
    have; this is the smaller and sharper fix, and it needs no cage change.)

    The property the old discipline bought is kept: `os.pwrite` is ONE
    syscall, so a concurrent reader sees the file whole-or-unchanged and never
    a half-written row.
    """
    # ponytail: in-place is not crash-atomic — a power loss mid-write leaves a
    # truncated registry where os.replace left the old file intact. Acceptable:
    # the writer re-reads and refuses `registry-changed-underfoot`, and the
    # cage bind is the property that must hold. If it ever bites, add a sidecar
    # journal — do NOT go back to os.replace.
    data = new_text.encode("utf-8")
    fd = os.open(str(path), os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.pwrite(fd, data, 0)
        os.ftruncate(fd, len(data))
    finally:
        os.close(fd)


def append_taskforce_rows(plan: dict) -> int:
    """dag-05 — the registry append, from the plan render_taskforce_rows
    validated: read → append → single-syscall IN-PLACE write (same inode, see
    `_rewrite_in_place` for why the inode is load-bearing), NEVER an
    open-append — a partial line in the run's registry
    is unparseable by every consumer at once. The existing bytes (header
    included) pass through unchanged; only whole rendered lines are added.

    WRITE ORDER (never the reverse — keep this comment so a later reader does
    not "optimize" it): seat descriptors land FIRST (emit_seat_descriptors),
    these rows SECOND. The two refusal shapes already in the tree decide it:
    goal_cli's lint reports "seat has no seat folder (run goal-materialize)"
    for a row with no folder — a recoverable, self-explaining state — while
    check_bindings (coord.py) REFUSES a launch when the two surfaces disagree.
    A crash between the steps leaves orphan folders that nothing launches; a
    crash the other way leaves rows the kit tries to launch and cannot.
    Descriptors first is the strictly safer half-state."""
    reg = plan["registry"]
    tf_path = Path(reg["path"])
    if not reg["append_lines"]:
        plan["rows_appended"] = 0
        return 0
    current = tf_path.read_text(encoding="utf-8")
    if current != reg["text"]:
        raise Refuse(
            "registry-changed-underfoot",
            f"{TASKFORCE_NAME} changed between validation and write — "
            "re-run so the validations see the file that is actually there",
            str(tf_path),
        )
    new_text = current + "".join(line + "\n" for line in reg["append_lines"])
    _rewrite_in_place(tf_path, new_text)
    plan["rows_appended"] = len(reg["append_lines"])
    return plan["rows_appended"]


# ---------------------------------------------------------------- run


# ---- --refresh: bindings recovered from the descriptor, and the drop guard ----
#
# A descriptor holds every binding-carried value it was rendered from, so the
# file --refresh is about to replace IS the record of its own bindings. That is
# what lets the mode run with no `--bindings` argument and still be honest:
# nothing is invented, the seat's current binding is carried forward, and what
# moves is the CATALOG. (`--repass` is the other act — the caller DECLARING new
# bindings for a new pass.)
#
# `cwd-mode` is reconstructed rather than read: `seat-folder` is the only ruled
# mode, and the descriptor stores the resolved `cwd`, not the mode that chose it.
_REFRESH_BINDING_KEYS = (
    "description", "agent_type", "harness", "model", "effort", "mode",
    "ctx-refresh", "window", "senders", "close", "auto-wake", "ephemeral",
    "broadcast", "component", "relays", "addressable",
)

# Every frontmatter key the EMITTER itself knows how to produce. A key in this
# set may appear and disappear freely: it is written when it applies and left
# out when it does not, so its absence is the emitter working, never a loss.
#
# This is the distinction the drop guard below turns on, and getting it wrong
# in the safe-looking direction is what the first version of that guard did:
# comparing key PRESENCE alone treats "the catalog no longer grants this seat
# tmux access" — a deliberate removal the operator just made — as if it were
# the accidental loss of a hand-typed line, and refuses to apply it.
#
# It is kept as a spelled-out literal rather than derived from the emitter, and
# `SC-EMIT` below proves it COVERS a real render: a check whose expectation is
# computed from the code under test moves with that code and passes any change
# to it. A newly emitted key that nobody adds here turns that row red.
EMITTER_OWNED_KEYS = frozenset((
    "seat", "description", "cwd", "agent_type", "pass",
    "harness", "model", "effort", "mode",
    "ctx-refresh", "window", "senders", "close",
    "auto-wake", "ephemeral", "broadcast", "component", "relays",
    "addressable", "exposes", "exposed-clis", "cli-write-roots",
    # `human-interactive` (+ its required `fallback`) arrive via the
    # assembler's frontmatter pass-through (goal_cli.py#assemble_seat reads
    # them off the prompt card, canon-checks the value, and carries them into
    # the descriptor) — never via a binding — so a deliberate un-declaration
    # in the catalog must APPLY on --refresh, not refuse as hand-authored.
    "human-interactive", "fallback",
    *CAGE_GRANTS, CAGE_RW_COLUMN, CAGE_GOAL_WRITES_COLUMN,
    # The per-unit reference keys. The emitter still writes these for an
    # OLD-LAYOUT catalog (it carries the assembler's frontmatter through), and
    # stops for a whole-file one (`d-prompt-task-files` retired unit
    # references) — so they are conditional, not retired, and a catalog
    # migration must not need a --repass to land. Both spellings occur in the
    # wild: the assembler emits `task goal` / `i/o spec` / `done contract`
    # spaced, and older descriptors carry `done-contract` hyphenated.
    "role", "procedure", "resources", "permissions", "restrictions",
    "constraints", "scope", "outcome",
    "i/o spec", "task goal", "done contract",
    "io-spec", "task-goal", "done-contract",
))

# Keys the emitter never writes but a re-render is still allowed to drop:
# `launch-home` and `artifact-home` have NO code reader anywhere in the repo and
# were dropped by owner ruling 2026-08-10. This set is deliberately tiny — the
# conditional keys live in EMITTER_OWNED_KEYS above, and anything in NEITHER set
# can only have been typed by a human, which is exactly what the guard defends.
# …joined 2026-08-14 by `context` (W6/R3): the task-schema field is DELETED, so
# the emitter no longer carries it through. It is here and NOT in
# EMITTER_OWNED_KEYS on purpose — live descriptors still carry it (13 on the
# flagship goal), and a re-render must be allowed to DROP it rather than read it
# as a hand-authored key and refuse.
RETIRED_DESCRIPTOR_KEYS = frozenset(("launch-home", "artifact-home", "context"))


def _descriptor_fm(path: Path) -> dict:
    """An existing descriptor's frontmatter as a dict ({} when absent)."""
    if not path.is_file():
        return {}
    m = _FM_RE.match(path.read_text(encoding="utf-8"))
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise Refuse(
            "refresh-descriptor-unparseable",
            f"the descriptor at {path} carries frontmatter that is not YAML "
            f"— {exc}; a refresh recovers this seat's bindings FROM it and "
            "cannot proceed on a file it cannot read",
            str(path)) from exc


def bindings_from_descriptors(package: Path, added: list[str]) -> dict:
    """The `--bindings` a refresh runs with, recovered from each seat's own
    existing descriptor. Refuses a seat with no descriptor: a refresh updates
    what is there, and inventing a binding is the one thing this must not do."""
    seats: dict[str, dict] = {}
    for seat in added:
        path = seat_home(package, seat) / "seat.md"
        fm = _descriptor_fm(path)
        if not fm:
            raise Refuse(
                "refresh-no-descriptor",
                f"--refresh recovers seat '{seat}'s bindings from its EXISTING "
                "seat.md and there is none to read — materializing a new seat "
                "is the plain run, never a refresh",
                str(path))
        entry = {"cwd-mode": "seat-folder"}
        for key in _REFRESH_BINDING_KEYS:
            val = fm.get(key)
            if val not in (None, ""):
                entry[key] = val
        if fm.get("pass"):
            entry["pass-folder"] = fm["pass"]
        seats[seat] = entry
    return {"defaults": {}, "seats": seats, "path": "<recovered from seat.md>"}


def check_refresh_drops(package: Path, plan: dict) -> None:
    """REFUSE a refresh that would remove a frontmatter key the emitter cannot
    produce at all — a key that can only have been typed by a human.

    A key the EMITTER owns (`EMITTER_OWNED_KEYS`) may come and go freely: it is
    written when it applies and omitted when it does not, so removing a cage
    grant from `seats.csv` APPLIES rather than refusing. A named retired key
    (`RETIRED_DESCRIPTOR_KEYS`) may go too. Everything else is authored, and
    authored is the only thing a re-render can genuinely lose.

    This is what makes overwriting a descriptor safe BY CONSTRUCTION rather
    than by policy. The hazard is specific and was real here: a descriptor can
    carry an authored key the catalog has no way to express — the seat cage
    was exactly that until it was given a home — and a re-render drops such a
    key SILENTLY, with the loss surfacing much later as a seat that
    mysteriously cannot do something. A named refusal costs one run; a silent
    drop cost this system a Slack route that read as working (`daf2f140b`)."""
    for seat, text in plan["descriptors"].items():
        old = _descriptor_fm(seat_home(package, seat) / "seat.md")
        m = _FM_RE.match(text)
        new = yaml.safe_load(m.group(1)) if m else {}
        lost = [k for k in old
                if k not in (new or {})
                and k not in EMITTER_OWNED_KEYS
                and k not in RETIRED_DESCRIPTOR_KEYS]
        if lost:
            raise Refuse(
                "refresh-would-drop-keys",
                f"refreshing seat '{seat}' would REMOVE frontmatter key(s) "
                + ", ".join(f"'{k}'" for k in lost)
                + " that its current descriptor carries and the catalog does "
                "not produce — refused rather than dropped silently. Give the "
                "key a home in the catalog (the seat cage's own fix), or "
                "re-render deliberately with --repass",
                str(seat_home(package, seat) / "seat.md"))


# ─── W3 · THE STAFF CHAIRS, MINTED WITH THE GOAL ──────────────────────────────
#
# Every silent stall this program closes was a correct signal delivered to an
# EMPTY CHAIR: the incident goal's `leader` row did not exist, so the routed
# FAIL, the mid-run ask and the closer's staff mail all resolved to a known name
# with nobody in it. A chair is a `taskforce.csv` row — nothing else in this
# system is a seat — so "the leader exists" means exactly "the goal's registry
# carries its row", and the ONE act that appends rows is this command.
#
# Shape, and why it is a SECOND PASS rather than two more members of `added`:
# a staff chair holds NO workflow node, so its `after` cell must be EMPTY. The
# added subgraph's roots all take `--after` verbatim (Rule 13, `after_cells`),
# and teaching that one composition a per-seat exception would put a branch in
# the frozen-DAG copy — the one place in this file that must stay dumb. A second
# `run()` with `--root` gets the empty cell from the rule that already exists.
# It also inherits every gate (cast validation, exposure resolution, collision,
# acyclicity) with no second spelling, and the recursion is bounded by its own
# first line: a run whose `--seat` IS a staff chair never injects.
#
# Ordering is load-bearing: the staff pass runs AFTER the main append, never
# before. `derive_taskforce_id` fires only on a ZERO-row registry (max + 1), so
# a staff-first mint would take tf-1 and hand the goal's own seats tf-2.
#
# It is also the BACKFILL (adv, C35): the guard is "the registry has no such
# row", not "the package was created in this run", so an already-materialized
# goal gets its chairs from the next materialize that touches it — including an
# `add-seat` splice, which is the one verb that reaches a live goal.
STAFF_BINDINGS_DIR = "bindings"


def _live_import(dir_path: Path, module: str):
    """ONE sys.path dance for live-tree siblings (coord, discovery)."""
    if str(dir_path) not in sys.path:
        sys.path.insert(0, str(dir_path))
    return __import__(module)


def _coord_import(name: str):
    """Import one coord.py vocabulary set. NEVER re-list the names here (F6)."""
    try:
        # coord.py is `ignite/coord/`'s since the component-first move — a SIBLING
        # component of this one, no longer this file's own directory.
        _coord = _live_import(Path(__file__).resolve().parent.parent / "coord", "coord")
        return tuple(getattr(_coord, name))
    except Exception as exc:  # loud, machine-readable — never a crash
        raise Refuse(
            "coord-import",
            f"cannot import {name} from coord.py — {exc}; refusing rather "
            "than re-listing the names here (F6)",
        ) from exc


def _discovery():
    """The installer's discovery module, from the repo that ships this file."""
    inst = Path(__file__).resolve().parents[2] / "meta" / "installer"
    try:
        return _live_import(inst, "discovery")
    except Exception as exc:
        raise Refuse(
            "discovery-import",
            f"cannot import discovery from {inst} — {exc}",
            str(inst),
        ) from exc


_DISCOVERY_SCAN: dict[tuple[str, str], tuple] = {}


def _clear_discovery_cache() -> None:
    _DISCOVERY_SCAN.clear()


def _scan_all(comp_dir: Path):
    """One scan_all per (mirror, repo) pair per materialize run."""
    ws = _workspace_root(comp_dir)
    mirror = ws / ".rbtv" / "mirror"
    repo = _rbtv_repo_root(comp_dir)
    key = (str(mirror.resolve()), str(repo.resolve()))
    hit = _DISCOVERY_SCAN.get(key)
    if hit is None:
        hit = _discovery().scan_all(mirror, repo)
        _DISCOVERY_SCAN[key] = hit
    catalog, _shadowed = hit
    return catalog, mirror, repo


def _coord_staff_seats() -> tuple[str, ...]:
    """`coord.STAFF_SEATS` — the room's OWN vocabulary of which seat ids are
    staff chairs, imported for the same reason `validate_seat` is (F6): the
    verdict that spawns these rows (`ready-seats`' IDLE branch), the closer's
    mail router and this minter must never disagree about the set. NEVER
    re-list the names here."""
    return _coord_import("STAFF_SEATS")


def _coord_summoned_seats() -> tuple[str, ...]:
    """`coord.SUMMONED_SEATS` (D24) — imported, never re-listed. A summoned
    seat holds no workflow node; minting it into a multi-taskforce goal is
    the same ambiguity the staff-chair lift already answers."""
    return _coord_import("SUMMONED_SEATS")


def _first_taskforce_joiners() -> set[str]:
    """Seats that may join a multi-taskforce goal's FIRST bare id: staff
    chairs (`d-staff-chair-joins-first-taskforce`) and summoned seats (D24
    / roles sitting 3). Ordinary workflow nodes still refuse."""
    return set(_coord_staff_seats()) | set(_coord_summoned_seats())


def staff_sheet_path(seat_row: dict, seat: str) -> Path | None:
    """The casting sheet for one staff chair, or None when the workspace is
    underivable.

    DERIVED from the catalog row's own home, never a hardcoded component name:
    a seats.csv at `<catalog-root>/<component>/seats.csv` under a mirror
    `.rbtv/mirror/<module>/` casts from `.rbtv/config/modules/<module>/
    <component>/bindings/<seat>.json` — the same address `rbtv-bindings` writes
    a workflow's sheet to, with the seat id for a name because a staff chair
    belongs to no workflow (the standing-seat spelling, `channel-master.json`).
    """
    source = seat_row.get("__source__")
    if not source:
        return None
    comp_dir = Path(source).parent
    try:
        workspace = _workspace_root(comp_dir)
    except Refuse:
        return None
    return (workspace / ".rbtv" / "config" / "modules" / comp_dir.parent.name
            / comp_dir.name / STAFF_BINDINGS_DIR / f"{seat}.json")


# ── THE STANDING-ENDING GATE, ONE READER FOR BOTH CHAIR LOOPS ─────────────────
#
# A chair minted over an ending that already stands under its NAME inherits it:
# the goal's readiness derivation reads that row as the chair's OWN, and `done`
# is absorbing, so the chair exists and can never sit. Measured 2026-08-14 on
# `meet-transcript-summarizer` — a freshly minted `leader` read `done` from a
# record a hand-driven console sitting had left behind, and it was found only
# because a Definition of done demanded the chair read IDLE.
#
# THE SURFACE MOVED, THE GATE DID NOT. The gate used to read
# `coordination/awaiting-close.json` — a debt ledger settled by `close-seat` /
# `reap`. spec-state-store §4.1 Row A deleted that file with the second ending
# writer (see `coord/closeout.py`, `coord/ready.py`, `coord/checkout.py`, all
# three of which record it as gone), and spec-component-map §3 gives the
# `AWAITING-CLOSE debt` banner no landing module: the LEDGER and its settlement
# vocabulary are dead. The QUESTION survives, retargeted at the ONE ending
# store — "does a current ending already stand under this name?" — which is
# what a chair would inherit.
#
# ⚠ ONE READER, DELIBERATELY. This was two copies of one gate, and the §4.1
# retarget updated the staff copy while the summoned copy stayed bound to the
# deleted ledger's variable — a `NameError` on every goal that declares a
# summoned chair. Both loops now call this; a future retarget cannot reach one
# and miss the other.
#
# ⚠ THE ROW IS NOT THIS PASS'S TO CLEAR, dead sitting or live one. The store's
# writers are the check-out door and the system stamper; a minter that deleted
# endings would be a second writer of the one surface that records them. So
# this SKIPS and WARNS — no chair is better than a dead chair, because a
# warning is read and an absorbing `done` is not.
def _es():
    """The kit's ending-store door, imported not re-implemented (F6).

    Takes no `sys.path` priming of its own: this module's import header already
    puts `ignite/coord/` on the path unconditionally (it has to — `self_isolate`
    is imported from there before anything else runs). Named as a function
    rather than imported at module scope so the store stays a lazy dependency,
    the way every other coord door here is."""
    import ending_store
    return ending_store


def _chair_current_ending(package: Path, seat: str) -> dict | None:
    """The ending standing under `seat` in this goal's store, or None.

    Imported from the kit rather than re-read here for the same reason
    `STAFF_SEATS` is (F6): the store the chair's own verdict reads and the store
    this gate reads must be ONE reader. `sys.path` is primed by
    `_coord_staff_seats`, which every caller runs first.

    An UNREACHABLE store reads as "no ending", by the same contract the deleted
    ledger carried: a fixture or foreign catalog with no `state-store` beside it
    must materialize exactly as it did before, and a gate that refused whenever
    it could not answer would block every one of them."""
    store = _es()
    try:
        ending = store.get_current_ending(package, seat)
    except store.EndingStoreError:
        return None
    return ending if isinstance(ending, dict) else None


def _chair_ending_warning(kind: str, seat: str, ending: dict) -> str:
    """The skip warning for either chair — one sentence, so the two cannot drift.

    It names the ending and its stamp because the reader's next act is to find
    the sitting that left it; it does NOT name a verb that settles it, because
    §4.1 deleted the settlement vocabulary along with the ledger."""
    return (f"{kind} chair '{seat}' NOT minted: this goal already carries a "
            f"CURRENT ENDING under that name in the ending store (ending "
            f"`{ending.get('ending')}`, stamped "
            f"{ending.get('stamped_at') or '(unstamped)'}). A chair minted over "
            f"it reads that row as its OWN ending and is born terminal — it "
            f"would exist and never sit. Re-run this materialize once that row "
            f"is no longer the current ending for '{seat}'")


def mint_staff_chairs(result: dict, package: Path, args,
                      seats_catalog: dict) -> dict:
    """Append the goal's staff rows if they are absent, and return `result`
    carrying what that did (`result['staff']`). SUMMONED chairs
    (`_coord_summoned_seats()`, today `goal-master`) ride the same pass
    (D79) and land in `result['summoned']` — never in `STAFF_SEATS`.

    Every skip is one of FOUR, and only the first is silent:
      · the chair already has a row — the goal is already staffed;
      · the catalog carries no such seat — this is a foreign or fixture catalog
        with no staff component in it, and a materialize against it must render
        exactly as it did before (the `_interactive_expose_refs` precedent);
      · the chair has no casting sheet — a WARNING for the `leader`, which the
        wake path requires (the `consultant` chair this branch used to fall
        silent for is deleted [T2-R17, D-7-ruling] — `leader` is the only
        member of `STAFF_SEATS` now); a summoned chair with no sheet is also
        a WARNING (the owner-message path has nobody to sit);
      · a CURRENT ENDING already stands under this chair's name in the ending
        store — a WARNING for either chair, see the gate below.
    A refusal from the staff pass itself degrades to a warning for one reason:
    the main rows are already on disk by then, and exiting non-zero over a
    chair would make the caller's retry impossible (`seat-exists`) while
    leaving the goal materialized anyway."""
    staff = _coord_staff_seats()
    summoned = _coord_summoned_seats()
    # ⚠ A CHAIR IS A CATALOGED SEAT, SO IT IS READ FROM THE COMPONENT CATALOG — NEVER FROM A
    # GOAL-LOCAL LANE. `--goal-local` SWAPS the catalog for one synthesized out of the goal's own
    # planning product, and that lane carries the goal's authored seats and nothing else by
    # construction. Handed that lane, this pass finds no row for `leader` or `goal-master` and
    # takes the "foreign or fixture catalog" skip for both — silently, because that skip is the
    # one of the four that is silent. On a LIVE goal the skip is invisible: the chairs are already
    # registered, so the loop would have `continue`d on `existing` anyway. On a BIRTH it is fatal,
    # and it was measured that way on 2026-08-27 — the first daemon-lane birth minted the plan's
    # two seats and no chairs at all, and reported success. `args.catalog_root` is the COMPONENT
    # root the caller named; the swap only rebound a local in `run`, never the argument.
    if getattr(args, "goal_local", False):
        try:
            component_seats = load_catalogs(Path(args.catalog_root))[0]
        except CatalogRefusal as exc:
            result["warnings"].append(
                f"staff and summoned chairs NOT minted: the component catalog at "
                f"{args.catalog_root} did not load ({exc}) — a --goal-local run reads its chairs "
                f"from there, because the goal-local lane carries only the seats the goal itself "
                f"authored")
            return result
        normalize_seat_rows(component_seats)
        seats_catalog = component_seats
    # Staff chairs stay on the original early return. Summoned chairs join it
    # so `--seat goal-master` (and a dry-run of that mint) cannot recurse:
    # dry-run writes no row, so `existing` would never skip the chair.
    if (getattr(args, "seat", None) in staff
            or getattr(args, "seat", None) in summoned
            or getattr(args, "nested", False)):
        return result
    existing = {(r.get("seat") or "").strip()
                for r in _csv_rows(package / TASKFORCE_NAME)}
    minted = []
    for seat in staff:
        if seat in existing:
            continue
        row = seats_catalog.get(seat)
        if row is None:
            continue
        ending = _chair_current_ending(package, seat)
        if ending is not None:
            result["warnings"].append(_chair_ending_warning("staff", seat, ending))
            continue
        sheet = staff_sheet_path(row, seat)
        if sheet is None or not sheet.is_file():
            if seat == staff[0]:
                result["warnings"].append(
                    f"staff chair '{seat}' NOT minted: no casting sheet at "
                    f"{sheet} — the goal has no chair for a routed FAIL, a "
                    f"mid-run ask or the session-closer's staff mail to reach, "
                    f"and every one of those will resolve to a name with "
                    f"nobody in it. Cast it and re-run this materialize")
            continue
        sub = argparse.Namespace(**vars(args))
        sub.seat, sub.workflow, sub.nested = seat, None, False
        sub.root, sub.after = True, None
        sub.bindings = str(sheet)
        sub.milestone_id = ""          # a staff chair holds no workflow node
        sub.force_partial = sub.repass = sub.refresh = False
        # …and it is minted from the COMPONENT catalog, so the sub-run must not rebuild the lane:
        # `run` would swap the catalog again and refuse to resolve a chair the lane cannot carry.
        sub.goal_local = False
        try:
            minted.append(run(sub))
        except (Refuse, CatalogRefusal) as exc:
            code = getattr(exc, "code", "catalog")
            result["warnings"].append(
                f"staff chair '{seat}' NOT minted: the mint refused "
                f"[{code}] {exc} — the goal is materialized WITHOUT the chair")
    if minted:
        result["staff"] = minted
    # D79 — SUMMONED chairs (goal-master) mint here, beside staff, with the
    # same four skips. They stay out of STAFF_SEATS: readiness IDLE, woken
    # only by an owner message. result['summoned'] is a sibling of
    # result['staff'] so SM-1's staff disclosure stays leader-only.
    summoned_minted = []
    for seat in summoned:
        if seat in existing:
            continue
        row = seats_catalog.get(seat)
        if row is None:
            continue
        ending = _chair_current_ending(package, seat)
        if ending is not None:
            result["warnings"].append(_chair_ending_warning("summoned", seat, ending))
            continue
        sheet = staff_sheet_path(row, seat)
        if sheet is None or not sheet.is_file():
            result["warnings"].append(
                f"summoned chair '{seat}' NOT minted: no casting sheet at "
                f"{sheet} — the goal has no chair for an owner message in "
                f"its channel to sit, and every resolveGoalSeat will resolve "
                f"to a name with nobody in it. Cast it and re-run this "
                f"materialize")
            continue
        sub = argparse.Namespace(**vars(args))
        sub.seat, sub.workflow, sub.nested = seat, None, False
        sub.root, sub.after = True, None
        sub.bindings = str(sheet)
        sub.milestone_id = ""
        sub.force_partial = sub.repass = sub.refresh = False
        sub.goal_local = False         # same reason as the staff loop above

        try:
            summoned_minted.append(run(sub))
        except (Refuse, CatalogRefusal) as exc:
            code = getattr(exc, "code", "catalog")
            result["warnings"].append(
                f"summoned chair '{seat}' NOT minted: the mint refused "
                f"[{code}] {exc} — the goal is materialized WITHOUT the chair")
    if summoned_minted:
        result["summoned"] = summoned_minted
    return result


def run(args) -> dict:
    package = validate_package(args.package)
    # --refresh IS a repass — one code path renders the descriptor, so a mode
    # cannot quietly update most of a seat and leave the descriptor behind
    # (owner-corrected 2026-08-10). What separates them is WHERE the bindings
    # come from and what the act is allowed to lose: refresh RECOVERS the
    # seat's current bindings from the file it replaces and refuses to drop a
    # key; repass is the caller DECLARING new bindings for a new pass.
    refresh = bool(getattr(args, "refresh", False))
    repass = bool(getattr(args, "repass", False)) or refresh
    if refresh:
        args.root = True          # inert on this path: it appends no rows
    if repass:
        if args.after:
            raise Refuse(
                "repass-with-after",
                "--repass never changes an edge — the registry row it "
                "re-renders against is left byte-untouched; pass --root",
            )
        if args.force_partial:
            raise Refuse(
                "repass-with-force-partial",
                "--repass and --force-partial are opposite acts: one REPLACES "
                "a descriptor deliberately, the other refuses anything that "
                "does not byte-match",
            )
    # ⚠ THE SINGLE-SEAT NESTED VARIANT IS A DELIBERATE, DOCUMENTED CONTRACT
    # CHANGE (W7, owner-ruled D-6). Until W7 `--seat` + `--nested` was a hard
    # refusal, on the reasoning that "a single --seat has no workflow to be the
    # Nth of". That reasoning holds for a seat materialized on its own account
    # and FAILS for the case W7 has: a `collapsed`-stamped milestone runs
    # `plan-planner` ALONE, and that lone seat IS a planning pass — the Nth
    # instance of the planning workflow, needing the same composed name and the
    # same `tf-<n>-<prefix><m>` id as a full-mode pass, or the second collapsed
    # milestone re-splices `plan-planner` onto a name that already exists and
    # hits the pinned `seat-exists` refusal forever.
    #
    # So `--nested` NAMES the instance series when `--seat` is used, and stays
    # bare when `--workflow` is (the workflow is its own series). No new flag:
    # one flag whose value answers exactly the question the refusal below asks.
    nested_workflow = None
    if getattr(args, "nested", False):
        nested_workflow = (args.workflow if args.nested is True
                           else str(args.nested))
        if args.workflow and args.nested is not True \
                and str(args.nested) != args.workflow:
            raise Refuse(
                "nested-workflow-mismatch",
                f"--workflow names '{args.workflow}' and --nested names "
                f"'{args.nested}' — with --workflow the instance series IS "
                "that workflow, so --nested takes no value there",
            )
        if not nested_workflow:
            raise Refuse(
                "nested-without-workflow",
                "--nested names an INSTANCE of a workflow — a bare --nested "
                "beside a single --seat says which seat but not which instance "
                "series it joins, and top-level seats keep bare names. Pass the "
                "workflow: --seat <seat> --nested <workflow>",
            )
        if repass:
            raise Refuse(
                "nested-with-repass",
                "--repass/--refresh re-render seats that ALREADY exist and are "
                "already named; --nested mints a new instance's names. Pass "
                "the composed seat names to --repass instead",
            )
    if standing_seat(package):
        # A standing-seat home is ONE seat with many sessions and no goal
        # around it (r-master-seat-homes): no conduct.md, no budget.json, no
        # taskforce.csv, no run register. Demanding those surfaces here is
        # what refused every attempt to re-render the channel master's
        # descriptor. It also may not be MINTED from here — a plain
        # materialize appends a registry row, and there is no registry.
        if not (repass or getattr(args, "refresh", False)):
            raise Refuse(
                "standing-seat-plain-materialize",
                f"package '{package.name}' is a STANDING-SEAT home (one seat, "
                "many sessions, no goal apparatus) — it is UPDATED with "
                "--refresh or re-rendered with --repass, never minted by a "
                "plain materialize, which would append a taskforce.csv row to "
                "a package that has no registry",
                str(package),
            )
        creation = []
    else:
        creation = plan_package_creation(package, args)  # dag-06 (plans, no write)
    if repass and creation:
        raise Refuse(
            "repass-incomplete-package",
            "--repass re-renders inside an EXISTING goal package and this one "
            "is missing "
            + ", ".join(c["surface"] for c in creation)
            + " — complete the package with a plain materialize first",
            str(package),
        )
    catalog_root = Path(args.catalog_root)
    if not catalog_root.is_dir():
        raise Refuse(
            "catalog-root-missing",
            "--catalog-root is not a directory — no catalog to materialize from",
            str(catalog_root),
        )
    # ⚠ THE LANE SWAP, AND IT IS A SWAP RATHER THAN A MERGE. `--goal-local`
    # shapes the goal's own planning product into a catalog and materializes
    # FROM THAT, with the component catalog kept only as the set the collision
    # check compares against. Merging the two roots was refused: `load_catalogs`
    # is a dict keyed by id, so a merge makes "which definition wins" an rglob
    # ordering question, and the shadow check inside the lane exists precisely
    # to make that unrepresentable. One run, one lane.
    if getattr(args, "goal_local", False):
        catalog_root = build_goal_local_lane(package, catalog_root)
    catalogs = load_catalogs(catalog_root)
    normalize_seat_rows(catalogs[0])
    added, internal_after, internal_after_raw = resolve_added(
        args, catalog_root, catalogs[0])
    # THE NESTED PATH. One re-key, here, and every surface below is unchanged:
    # the composed name IS the seat id from this line on, so folders,
    # descriptors, the registry seat cell and the frozen `after` cells all
    # carry it with no second spelling and no per-site translation.
    nested = None
    if getattr(args, "nested", False):
        # `nested_workflow` (not `args.workflow`) — on the single-seat variant
        # there IS no --workflow, and the series is the one --nested named.
        nested = nested_instance(package, catalog_root, nested_workflow, added)
        rename = nested["rename"]
        added = [rename[s] for s in added]
        internal_after = {rename[s]: [rename[p] for p in preds]
                          for s, preds in internal_after.items()}
        # Criterion 8 / Rule 13: the frozen copy is mapped through the SAME
        # single naming function everything else goes through.
        internal_after_raw = {rename[s]: rename_after_cell(raw, rename)
                              for s, raw in internal_after_raw.items()}
        # The seat CATALOG is aliased, never re-keyed: it is a read-only lookup
        # shared with every other seat in the root, and the composed name must
        # resolve the SAME row the catalog id does.
        for cid, name in rename.items():
            if cid in catalogs[0]:
                catalogs[0][name] = catalogs[0][cid]
    # The seat set is resolved FIRST because a refresh reads its bindings out
    # of those seats' own existing descriptors.
    bindings = (load_bindings(Path(args.bindings)) if args.bindings
                else bindings_from_descriptors(package, added))
    if nested:
        rekey_bindings(bindings, nested["rename"])
    elif args.seat and args.seat not in bindings["seats"]:
        # The instance-named completion resolved in `resolve_added`: the sheet
        # that CASTS the seat is keyed by the base name (that is what the real
        # per-seat sheets — `bindings/plan-dod-judge.json`, the standing-seat
        # spelling — carry), and the run is keyed by the composed one. Same
        # re-key, same single function; a sheet already keyed by the composed
        # name is untouched because the branch never fires for it.
        parsed = parse_instance_seat_name(args.seat)
        if parsed and parsed[2] in bindings["seats"]:
            rekey_bindings(bindings, {parsed[2]: args.seat})
    # `whole_set` is FALSE on a single-seat run: the sheet that casts one seat
    # is its WORKFLOW's sheet, so its other seats are not stray keys.
    check_bindings_cover(bindings, added, whole_set=not args.seat)
    attach_after = validate_after(args, package, added)
    validate_milestone(args, package)
    if repass:
        check_repass(package, added)
    else:
        check_collisions(package, added, args.force_partial)
    units = index_units(catalog_root)
    assembled = assemble_all(added, bindings, catalogs, units)
    plan = build_plan(package, added, internal_after, internal_after_raw,
                      attach_after, assembled, bindings, args, creation)
    plan["nested"] = nested
    # Seat-exposure resolution fires for BOTH paths (its gates are pre-write,
    # and the descriptor frontmatter carries the validated mapping); the
    # loader FILES are planned only on the materialize path below — a repass
    # replaces descriptors, nothing else.
    resolve_seat_exposes(plan, catalogs[0])
    resolve_cli_write_roots(plan)
    if repass:
        # A repass renders and REPLACES descriptors — plus the seat's GUIDANCE
        # PAIR, which is pure derived boilerplate regenerated with the same
        # freedom as the descriptor (`d-uniform-descriptor-carriage`): the
        # registry row, the run register and every package surface are the
        # previous materialize's and stay byte-untouched. The exposure LOADER
        # files remain --refresh's alone: dropping a previously-exposed part
        # needs check_refresh_drops' nothing-is-lost gate, which a plain
        # repass deliberately does not run.
        plan["writes"] = [
            {"kind": "seat-descriptor-repass", "seat": seat,
             "path": str(seat_home(package, seat) / "seat.md")}
            for seat in added
        ]
        plan["rows_appended"] = 0
        render_descriptors(plan, catalogs[0], units)
        plan["seat_rules"] = _seat_rules_from_parts(plan)
        if refresh:
            # Every gate before any write: nothing is lost, THEN the
            # seat-folder surfaces are planned beside the descriptor.
            check_refresh_drops(package, plan)
            render_seat_exposures(plan)
        for seat in added:
            for name in ("CLAUDE.md", "AGENTS.md"):
                plan["writes"].append(
                    {"kind": "seat-guidance", "seat": seat,
                     "path": str(seat_home(package, seat) / name)})
        if args.dry_run:
            return result_of(plan, dry_run=True)
        repass_descriptors(plan)
        if refresh:
            emit_seat_exposures(plan)
        for seat in added:
            _write_seat_guidance(
                seat_home(package, seat), seat, package,
                (plan.get("seat_rules") or {}).get(seat, ()))
        return result_of(plan, dry_run=False)
    # dag-04 + dag-05: EVERY gate fires HERE — the emission gates, then the
    # three registry validations — before the dry-run return and before any
    # write, so a refusal always leaves zero files and zero rows.
    render_descriptors(plan, catalogs[0], units)
    render_harness_configs(plan, catalogs[0])  # plugin/MCP config files
    render_seat_exposures(plan)   # seat-exposure loaders (five methods)
    render_taskforce_rows(plan)
    if args.dry_run:
        # The staff pass previews too — a --dry-run that under-reports its own
        # writes is the same defect as an emitter that hides one.
        return mint_staff_chairs(result_of(plan, dry_run=True), package, args,
                                 catalogs[0])
    # Package surfaces FIRST (dag-06), descriptors SECOND, rows LAST — never
    # another order (the descriptor/rows rationale lives on
    # append_taskforce_rows' docstring; creation must precede both because
    # descriptors land in seats/ and the append re-reads taskforce.csv).
    create_run_package(package, creation)  # dag-06
    emit_seat_descriptors(plan)   # dag-04
    emit_harness_configs(plan)    # plugin/MCP config files
    emit_seat_exposures(plan)     # seat-exposure loaders (five methods)
    append_taskforce_rows(plan)   # dag-05
    # LAST, and after the append on purpose — see the staff block above for why
    # a staff-first mint would take the goal's own taskforce-id.
    return mint_staff_chairs(result_of(plan, dry_run=False), package, args,
                             catalogs[0])


# ---------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="materialize-seats.py",
        description="Materialize a seat or a whole workflow into a run "
                    "package: seat descriptors first, then taskforce.csv rows.",
        epilog="materialize-seats.py --selftest materializes only against a "
               "throwaway fixture and exits 0/1.",
    )
    p.add_argument("--package", required=True,
                   help="absolute GOAL-FOLDER path to materialize into "
                        "(<workspace>/.rbtv/goals/<goal> — the package IS the "
                        "goal folder, design-lock item 8). Never inferred.")
    what = p.add_mutually_exclusive_group(required=True)
    what.add_argument("--seat",
                      help="materialize ONE cataloged seat (seats.csv row). "
                           "With --force-partial it also accepts an INSTANCE "
                           "name (<four-letters>-<n>-<seat>) to COMPLETE the "
                           "missing folder of a row that already carries one: "
                           "the catalog row and the bindings entry resolve "
                           "through the BASE seat, the folder and descriptor "
                           "carry the composed name. Minting a NEW instance "
                           "stays --nested's act")
    what.add_argument("--workflow",
                      help="materialize a whole workflow "
                           "(<component>/workflows/<W>/<W>.csv manifest)")
    p.add_argument("--nested", nargs="?", const=True, default=False,
                   metavar="WORKFLOW",
                   help="materialize as a NESTED INSTANCE of the parent goal — "
                        "every seat named <four-letters>-<seat> (first "
                        "instance) or <four-letters>-<n>-<seat> (second "
                        "onward), from the prefix the workflow's own "
                        "workflow.md DECLARES. The seats are ORDINARY seats of "
                        "the parent goal (r-branch-folder-deleted-nested-seats-"
                        "are-ordinary-run-seats): one seats/, one "
                        "taskforce.csv, no branches/ tree. The rows carry the "
                        "instance's own taskforce-id (tf-<n>-<prefix><m>). "
                        "BARE with --workflow (the workflow IS the instance "
                        "series); with --seat it TAKES the workflow name whose "
                        "instance series the single seat joins — the collapsed "
                        "mode of a per-milestone planning pass, where one seat "
                        "is the whole pass")
    p.add_argument("--catalog-root", required=True, dest="catalog_root",
                   help="component catalog root the definitions are read from")
    p.add_argument("--goal-local", action="store_true", dest="goal_local",
                   help="materialize seats the GOAL'S OWN planning pass "
                        "authored — read from planning/current/ (manifest.csv "
                        "plus seats/<seat>/ prompt+task pairs) instead of the "
                        "component catalog, which carries no row for them. "
                        "It requires those two surfaces and a --bindings "
                        "sheet that casts every manifest seat, and NOTHING "
                        "else: the repair case it was built for is a "
                        "binder-REGISTERED seat whose folder was never built, "
                        "but a taskforce row is not a precondition — an "
                        "execution-goal BIRTH mints a package with no registry "
                        "at all through this same lane. --catalog-root is still "
                        "required and is still read: it is the set this lane's "
                        "SHADOW check compares against, since a goal-authored "
                        "id may never collide with a cataloged one. Pair with "
                        "--dry-run to LINT the goal's authored seats (dangling "
                        "refs and collisions) without materializing any")
    where = p.add_mutually_exclusive_group()
    where.add_argument("--after",
                       help="comma-separated predecessors the materialized "
                            "root row(s) attach after")
    where.add_argument("--root", action="store_true",
                       help="the materialized row(s) are DAG roots (an "
                            "omitted insertion point never defaults to root)")
    p.add_argument("--bindings",
                   help="JSON file: per-seat executor binding + descriptor "
                        "surface to materialize with")
    p.add_argument("--milestone-id", dest="milestone_id",
                   help="written to every materialized row; must resolve to a "
                        "milestones.csv row")
    p.add_argument("--claude-md", dest="claude_md",
                   help="caller-supplied run CLAUDE.md base-text file, byte-"
                        "copied into a CREATED goal package (d-run3-seeds-"
                        "from-run2-amended — this command never invents run "
                        "conventions). Required when creating/completing")
    p.add_argument("--budget-json", dest="budget_json",
                   help="caller-supplied budget.json file, byte-copied into "
                        "a CREATED goal package. A PATH, never a value: the "
                        "floor lives in the file (R-10, r-floor-single-"
                        "source). Required when creating/completing")
    p.add_argument("--addressable",
                   help="OPTIONAL (7.569): caller-supplied addressable.csv "
                        "register, byte-copied into a CREATED goal package. "
                        "Omitted, a BOOTSTRAP creation DERIVES it from the "
                        "standing-seat homes whose own seat.md declares "
                        "`addressable: non-member`, and creates nothing when "
                        "none does — so the armed creation loop never starts "
                        "refusing for want of a flag")
    p.add_argument("--dry-run", action="store_true", dest="dry_run",
                   help="print the full materialize write plan as JSON; "
                        "touch nothing")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="machine-readable materialize result on stdout")
    p.add_argument("--force-partial", action="store_true", dest="force_partial",
                   help="complete only the MISSING half of a partial "
                        "materialize failure (asserts the existing half "
                        "matches byte for byte)")
    p.add_argument("--repass", action="store_true", dest="repass",
                   help="RE-RENDER the descriptor(s) of seat(s) that already "
                        "exist, for the pass the bindings now declare — the "
                        "act a new pass opening on a reused ephemeral seat "
                        "needs (G-planner-0804-1502). Replaces seat.md and "
                        "NOTHING else: no registry row, no run register, no "
                        "package surface. Requires --root.")
    p.add_argument("--refresh", action="store_true", dest="refresh",
                   help="UPDATE an already-set-up seat folder to the "
                        "definition's current shape: seat.md, the AGENTS.md "
                        "pointer, and the prompt-card `exposes:` loaders. "
                        "Bindings are RECOVERED from each seat's existing "
                        "seat.md, so no --bindings and no insertion point are "
                        "needed and nothing is invented; a refresh that would "
                        "REMOVE any frontmatter key the current descriptor "
                        "carries REFUSES instead (refresh-would-drop-keys) — "
                        "declaring new bindings for a new pass is --repass. "
                        "Works on a goal package and on a standing-seat home "
                        "(.rbtv/goals/_<seat>/) alike.")
    return p


def _emit_refusal(r: Refuse, as_json: bool) -> None:
    where = f" [{r.path}]" if r.path else ""
    print(f"materialize-seats refused ({r.code}): {r.message}{where}",
          file=sys.stderr)
    if as_json:
        print(json.dumps({"ok": False, "refusal": {
            "code": r.code, "message": r.message, "path": r.path}}, indent=2))


def main(argv: list[str] | None = None) -> int:
    scrub_environment()
    _clear_discovery_cache()
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)  # exits 2 on usage violations
    # Conditionally-required flags, enforced HERE so a usage violation keeps
    # exiting 2 (argparse cannot express "required unless --refresh").
    if not args.refresh:
        if not args.bindings:
            parser.error("--bindings is required (optional only with "
                         "--refresh, which writes no bindings-derived file)")
        if not (args.after or args.root):
            parser.error("one of --after/--root is required (an omitted "
                         "insertion point never defaults to root); "
                         "--refresh needs neither")
    try:
        result = run(args)
    except Refuse as r:
        _emit_refusal(r, args.as_json)
        return 1
    except CatalogRefusal as exc:
        _emit_refusal(Refuse("catalog", str(exc)), args.as_json)
        return 1
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        verb = "would materialize" if result["dry_run"] else "materialized"
        print(f"{verb} {len(result['added_seats'])} seat(s) into "
              f"{result['package']}: " + ", ".join(result["added_seats"]))
        for w in result["writes"]:
            print(f"  {w['kind']}: {w['path']}")
        for sub in result.get("staff", ()):
            # The chairs are DISCLOSED on the human surface too: they are rows
            # this run appended that the caller did not name, and a write a
            # command does not print is a write nobody reviews.
            print(f"  {verb} staff chair(s): " + ", ".join(sub["added_seats"]))
        for sub in result.get("summoned", ()):
            # D79 — the summoned chair (goal-master) is disclosed the same way:
            # a silent mint reads as "not minted" to whoever audits the plan.
            print(f"  {verb} summoned chair(s): " + ", ".join(sub["added_seats"]))
        for warn in result["warnings"]:
            print(f"  warning: {warn}")
    return 0


# ---------------------------------------------------------------- selftest


def _refusal_code(fn) -> str | None:
    """The `Refuse.code` an in-process call raises, or None when it returns.

    In-process, deliberately: the arms that use it exercise a GATE rather than
    the CLI, and a subprocess would report exit 1 for every refusal alike."""
    try:
        fn()
    except Refuse as exc:
        return exc.code
    return None


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def _norm(text: str, tmp: Path) -> str:
    """Erase the run's tempdir so two runs of the same scenario compare equal
    (SK-4/SC-11/AS-4 compare whole stdouts across two environments).

    The path appears in `--json` stdout in TWO spellings, and on POSIX they
    coincide — `/tmp/x` is its own JSON escaping — which is why one
    replacement sufficed for years. On Windows they diverge: the raw path is
    `C:\\Users\\...` and its JSON form is `C:\\\\Users\\\\...`, so the single
    raw replacement left every `writes[].path` un-normalized and SK-4's
    identical-suite comparison saw two different tempdirs, not an environment
    effect. Escaped form first: it is the longer of the two."""
    return (text.replace(json.dumps(str(tmp))[1:-1], "<TMP>")
                .replace(str(tmp), "<TMP>"))


def _sep(text: str) -> str:
    """A path rendered separator-blind, for arms only.

    Every expectation in this suite is written POSIX-style because the kit's
    home is a POSIX box, but the tool emits NATIVE paths (correctly — a
    descriptor's `cwd:` is consumed by spawn.js on the box that runs it). An
    arm that hardcodes `/` is asserting the platform, not the behaviour."""
    return text.replace("\\", "/")


def _check_emission_bits(check, label: str, file_path: Path) -> None:
    """dag-04's mode-bit arm, once, for both of its call sites.

    POSIX mode bits do not exist on Windows: the filesystem carries a
    read-only flag and nothing else, so `chmod(0o644)` lands as 0o666 and a
    directory as 0o777 whatever was asked. Asserting 0644/0755 there measures
    the OS, not this emitter. On Windows the arm REDUCES — loudly, in its own
    printed label — to the one bit Windows does carry: the emitted file is
    user-readable and user-writable, i.e. the emitter did not leave it
    read-only. The full 0644/0755 assertion still runs everywhere else."""
    import stat as _stat
    mode = _stat.S_IMODE(file_path.stat().st_mode)
    dmode = _stat.S_IMODE(file_path.parent.stat().st_mode)
    detail = f"file={oct(mode)} folder={oct(dmode)}"
    if os.name == "nt":
        check(f"{label}  [REDUCED-ON-WINDOWS: this filesystem carries no "
              f"POSIX mode bits — asserting user-rw instead of 0644/0755]",
              bool(mode & _stat.S_IRUSR) and bool(mode & _stat.S_IWUSR)
              and bool(dmode & _stat.S_IWUSR), detail)
        return
    check(label, mode == 0o644 and dmode == 0o755, detail)


def _invoke(argv: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), *argv],
        capture_output=True, text=True, env=env,
    )


def build_fixture(tmp: Path) -> dict:
    """A throwaway catalog + goal package + bindings set, in the settled
    component shape (kind-named XML unit bodies, id in frontmatter; bare and
    @latest unit refs both exercised — the dag-01 widened grammar)."""
    # catalog-root/<component>/... at installer depth 2 under the workspace
    # mirror: `<ws>/.rbtv/mirror/<module>/<component>/` (D86 / D2).
    (tmp / ".rbtv" / "config").mkdir(parents=True)
    comp = tmp / ".rbtv" / "mirror" / "catalog" / "demo-comp"

    def unit(rel: str, uid: str, body: str) -> None:
        path = comp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nid: {uid}\ndescription: {uid}\n---\n\n{body}\n",
                        encoding="utf-8")

    unit("prompts/cognitive-units/roles/alpha-role.md", "alpha-role",
         "<role>\nYou are alpha.\n<persona>\nTerse and exact.\n</persona>\n"
         "<agent-type>\nworker\n</agent-type>\n</role>")
    unit("prompts/cognitive-units/roles/beta-role.md", "beta-role",
         "<role>\nYou are beta.\n</role>")
    unit("prompts/cognitive-units/permissions/common-permissions.md",
         "common-permissions",
         "<permissions>\nRead the fixture tree. Write only your outputs.\n"
         "</permissions>")
    unit("prompts/cognitive-units/procedures/alpha-procedure.md",
         "alpha-procedure",
         "<procedure>\nProduce alpha-notes.md.\n</procedure>")
    unit("prompts/cognitive-units/procedures/beta-procedure.md",
         "beta-procedure",
         "<procedure>\nProduce beta-report.md.\n</procedure>")
    # io-spec whose body carries an INLINE outcome reference — the
    # d-run3-assembled-shape (i) resolution target (SC-20).
    unit("prompts/cognitive-units/io-specs/alpha-io.md", "alpha-io",
         "<io-spec>\n## Input\nRun inputs.\n## Outcome\n"
         "- Reference: `alpha-outcome@latest`.\n## Outputs\n`./alpha-notes.md`\n"
         "</io-spec>")
    unit("prompts/cognitive-units/outcomes/alpha-outcome.md", "alpha-outcome",
         "<outcome>\nNotes that let beta act without re-reading the run.\n"
         "</outcome>")
    unit("tasks/cognitive-units/task-goals/demo-task-goal.md",
         "demo-task-goal", "<task-goal>\nProve the fixture flow.\n</task-goal>")
    unit("tasks/cognitive-units/scopes/demo-scope.md", "demo-scope",
         "<scope>\nThe fixture tree only.\n</scope>")
    unit("tasks/cognitive-units/done-contracts/demo-done.md", "demo-done",
         "<done-contract>\nOutputs exist and are non-empty.\n</done-contract>")

    # Column order DELIBERATELY scrambled against the contract §1 kind order
    # (io-spec and permissions before role; done contract before task goal) —
    # the reorder control's shuffled input.
    comp.joinpath("prompts.csv").write_text(
        "prompt-id,i/o spec,permissions,role,procedure,description\n"
        "alpha-prompt,alpha-io@latest,common-permissions,alpha-role@latest,"
        "alpha-procedure,alpha prompt\n"
        "beta-prompt,,common-permissions@latest,beta-role,beta-procedure,"
        "beta prompt\n",
        encoding="utf-8")
    comp.joinpath("tasks.csv").write_text(
        "task-id,done contract,scope,task goal,description\n"
        "alpha-task,demo-done,demo-scope,demo-task-goal,alpha task\n"
        "beta-task,demo-done,demo-scope,demo-task-goal,beta task\n",
        encoding="utf-8")
    # The RULED mirror header (topic-2-authoring-contract §2): executor+task —
    # exercises normalize_seat_rows' task -> task-id alias on every run.
    comp.joinpath("seats.csv").write_text(
        "seat-id,executor,task,staffing-hints,description\n"
        "alpha,alpha-prompt,alpha-task,,the alpha seat\n"
        "beta,beta-prompt,beta-task,,the beta seat\n"
        "a2,alpha-prompt,alpha-task,,the a2 seat\n"
        "b2,beta-prompt,beta-task,,the b2 seat\n", encoding="utf-8")
    wf_dir = comp / "workflows" / "demo-flow"
    wf_dir.mkdir(parents=True)
    wf_dir.joinpath("demo-flow.csv").write_text(
        'Seat/workflow,after,i/o,Modality\n'
        'alpha,,"in: run inputs; out: alpha-notes.md",agentic\n'
        'beta,alpha,"in: alpha-notes.md; out: beta-report.md",agentic\n',
        encoding="utf-8")
    # The four letters this workflow DECLARES for its nested instances
    # (criterion 2, dossier §2 option B). Only the nested path reads it, which
    # is why the 40 live manifests need no edit.
    wf_dir.joinpath(WORKFLOW_DESCRIPTOR_NAME).write_text(
        "---\nid: demo-flow\nfour-letters: demo\n---\n\nThe demo flow.\n",
        encoding="utf-8")
    # A manifest whose ROW ORDER is deliberately anti-topological (the
    # dependent b2 listed before its root a2) — the dag-05 topo-order proof.
    sc_dir = comp / "workflows" / "scramble-flow"
    sc_dir.mkdir(parents=True)
    sc_dir.joinpath("scramble-flow.csv").write_text(
        'Seat/workflow,after,i/o,Modality\n'
        'b2,a2,"in: a2-notes.md; out: b2-report.md",agentic\n'
        'a2,,"in: run inputs; out: a2-notes.md",agentic\n',
        encoding="utf-8")

    # A second component: five cheap one-shot workers sharing one
    # prompt/task pair — the SC-13 whole-batch gate and F8/F10 fixtures.
    wide = tmp / ".rbtv" / "mirror" / "catalog" / "wide-comp"

    def wunit(rel: str, uid: str, body: str) -> None:
        path = wide / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nid: {uid}\ndescription: {uid}\n---\n\n{body}\n",
                        encoding="utf-8")

    wunit("prompts/cognitive-units/roles/wide-role.md", "wide-role",
          "<role>\nYou are a wide worker.\n</role>")
    wunit("prompts/cognitive-units/permissions/wide-permissions.md",
          "wide-permissions",
          "<permissions>\nRead the fixture tree.\n</permissions>")
    wunit("prompts/cognitive-units/procedures/wide-procedure.md",
          "wide-procedure", "<procedure>\nDo one bounded thing.\n</procedure>")
    wide.joinpath("prompts.csv").write_text(
        "prompt-id,role,procedure,permissions,description\n"
        "wide-prompt,wide-role,wide-procedure,wide-permissions,wide prompt\n",
        encoding="utf-8")
    wide.joinpath("tasks.csv").write_text(
        "task-id,task goal,scope,done contract,description\n"
        "wide-task,demo-task-goal,demo-scope,demo-done,wide task\n",
        encoding="utf-8")
    wide.joinpath("seats.csv").write_text(
        "seat-id,executor,task,staffing-hints,description\n"
        + "".join(f"s{i},wide-prompt,wide-task,,wide worker {i}\n"
                  for i in range(1, 6)),
        encoding="utf-8")
    wwf = wide / "workflows" / "wide-flow"
    wwf.mkdir(parents=True)
    wwf.joinpath("wide-flow.csv").write_text(
        "Seat/workflow,after,i/o,Modality\n"
        + "".join(f"s{i},,,agentic\n" for i in range(1, 6)),
        encoding="utf-8")
    # Guarded/alternate after-cell shapes (p-materializer-guard-suffix): a
    # guard suffix, both guard arms, and a cell mixing a top-level alternate
    # with a '|' INSIDE a bracket (which must never split).
    gwf = wide / "workflows" / "guard-flow"
    gwf.mkdir(parents=True)
    gwf.joinpath("guard-flow.csv").write_text(
        "Seat/workflow,after,i/o,Modality\n"
        "s1,,,agentic\n"
        "s2,s1[go=yes],,agentic\n"
        "s3,s1[go=no],,agentic\n"
        "s4,\"s2|s3,s1[g=a|b]\",,agentic\n",
        encoding="utf-8")

    taskforce = (
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        "tf-1,chief,,claude,claude-opus-5,high,,m1\n"
    )
    milestones = "milestone-id,name,status\nm1,prove the fixture,pending\n"
    pkg = tmp / "goals" / "demo-goal"
    (pkg / "seats").mkdir(parents=True)
    (pkg / "coordination").mkdir()  # a goal package carries it (coord.py home)
    pkg.joinpath(TASKFORCE_NAME).write_text(taskforce, encoding="utf-8")
    pkg.joinpath(MILESTONES_NAME).write_text(milestones, encoding="utf-8")
    # A second package with seat alpha already materialized — the collision arm.
    # A SECOND GOAL now (7.607 E2b): the package is the goal folder, so two
    # packages are two goals — never two compartments of one.
    pkg9 = tmp / "goals" / "demo-goal-9"
    (pkg9 / "seats" / "alpha").mkdir(parents=True)
    (pkg9 / "coordination").mkdir()
    pkg9.joinpath(TASKFORCE_NAME).write_text(taskforce, encoding="utf-8")
    pkg9.joinpath(MILESTONES_NAME).write_text(milestones, encoding="utf-8")
    # SC-10 control fixture: a registry whose header ALREADY carries `status`.
    pkg_status = tmp / "goals" / "demo-goal-8"
    (pkg_status / "seats").mkdir(parents=True)
    (pkg_status / "coordination").mkdir()
    pkg_status.joinpath(TASKFORCE_NAME).write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,"
        "milestone-id,status\n"
        "tf-1,chief,,claude,claude-opus-5,high,,m1,queued\n", encoding="utf-8")
    # The UNCOMPLETED goal folder (what `rbtv-goal scaffold` leaves): the
    # creation/completion arms' target. 7.607 E2b — this used to be an ABSENT
    # runs/run-7 compartment; a goal folder is never created by this command,
    # so the fixture scaffolds it and leaves it bare.
    pkg_uncompleted = tmp / "goals" / "demo-goal-7"
    pkg_uncompleted.mkdir(parents=True)
    # SC-21 fixture: the REPAIRED spine — m4 present, `bootstrap` absent
    # (dag-15's live repair is parked; this spine is the fixture's own).
    pkg_spine = tmp / "goals" / "demo-goal-31"
    (pkg_spine / "seats").mkdir(parents=True)
    (pkg_spine / "coordination").mkdir()
    pkg_spine.joinpath(TASKFORCE_NAME).write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,"
        "milestone-id\n"
        "tf-1,chief,,claude,claude-opus-5,high,,m3\n", encoding="utf-8")
    pkg_spine.joinpath(MILESTONES_NAME).write_text(
        "milestone-id,name,status\n"
        + "".join(f"m{i},milestone {i},pending\n" for i in range(3, 8)),
        encoding="utf-8")

    # A third component carrying a plugin/MCP declaration (MCP-1): its own
    # component so no other arm's write set changes; its seat reuses
    # demo-comp's prompt/task units (catalogs merge across the catalog root).
    mcpc = tmp / ".rbtv" / "mirror" / "catalog" / "mcp-comp"
    mcpc.mkdir(parents=True)
    mcpc.joinpath("seats.csv").write_text(
        "seat-id,executor,task,staffing-hints,description\n"
        "mcp-seat,alpha-prompt,alpha-task,,the mcp seat\n", encoding="utf-8")
    mcpc.joinpath("exposure.csv").write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "demo-mcp,plugin/MCP,config,,mcp.json,demo MCP declaration,\n",
        encoding="utf-8")
    mcpc.joinpath("mcp.json").write_text(json.dumps({"mcpServers": {
        "demo-http": {"type": "http", "url": "https://mcp.example.test"},
        "demo-stdio": {"command": "demo-mcp-server", "args": ["--flag"],
                       "env": {"DEMO_KEY": "x"}},
    }}, indent=2) + "\n", encoding="utf-8")
    # A cross-component skill row (EXP-1's `<component>/<part-id>` arm) —
    # method `skill`, so load_mcp_servers (config-only) never reads it and
    # MCP-1's write set is unchanged.
    mcpc.joinpath("xsk.md").write_text("# xsk\n\nCross skill content.\n",
                                       encoding="utf-8")
    with mcpc.joinpath("exposure.csv").open("a", encoding="utf-8") as fh:
        fh.write("xsk,reference,skill,,xsk.md,cross-component skill,\n")

    # A fourth component whose seat DECLARES exposure in its prompt-file
    # frontmatter (EXP-1, d-materializer-seat-loaders /
    # d-seat-exposes-frontmatter): its own component so no other arm's write
    # set changes; assembly reuses demo-comp's prompt/task rows (catalogs
    # merge across the root), while the `exposes:` declaration lives on THIS
    # component's own whole-file prompt card.
    expc = tmp / ".rbtv" / "mirror" / "catalog" / "exp-comp"
    expc.mkdir(parents=True)
    expc.joinpath("seats.csv").write_text(
        "seat-id,executor,task,staffing-hints,description,cage-grants,"
        "rw-paths\n"
        "exp-seat,alpha-prompt,alpha-task,,the exposure seat,"
        "read-root bus-write local-bin,1-projects\n",
        encoding="utf-8")
    expc.joinpath("exposure.csv").write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "brws,capability,skill,,skills/brws.md,browse the fixture web,\n"
        "cmd1,workflow,command,,commands/cmd1.md,run the demo flow,\n"
        "rul1,reference,rule,,rules/rul1.md,house style rule,\n"
        "hk1,capability,hook,,hooks/hk1.json,post-write lint,\n"
        "res1,prompt,sub-agent,,prompts/res1.md,fixture researcher,\n"
        # The WORKSPACE root (IPH-6 / D33): a `ws:` entry-point resolves
        # against the first ancestor holding `.rbtv/config/` — `tmp` here,
        # created just below — so the tool lands OUTSIDE the component
        # without a single `..`, which is now refused.
        "wstool,tool,path,,ws:wsbin/wstool.py,,!ws:wsbin\n",
        encoding="utf-8")
    (tmp / "wsbin").mkdir()
    (tmp / "wsbin" / "wstool.py").write_text(
        "#!/usr/bin/env python3\nprint('wstool')\n", encoding="utf-8")
    # The SECOND RESOLUTION ROOT (d-path-exposes-authorable): a `rbtv:` ref
    # addresses the rbtv REPO tree, found by walking up from the referencing
    # component to the `.rbtv/config/` DIRECTORY and reading `rbtv.json`'s
    # `rbtv_path` at that workspace root. `tmp` stands in for the workspace;
    # `tmp/repo` for the rbtv repo, module manifest at module root exactly as
    # `ignite/exposure.csv` sits today.
    #
    # ⚠ NO `install.json` IS WRITTEN (IPH-6 / D33). Its absence is not an
    # oversight to be repaired — it is the PROOF that the install book is no
    # longer consulted: every `rbtv:` arm below resolves without it, and
    # restoring the file would silently retire that proof. The DIRECTORY is
    # still required — it is what the one walk looks for.
    (tmp / "rbtv.json").write_text(
        json.dumps({"rbtv_version": "0.0.0-fixture", "rbtv_path": "repo"})
        + "\n", encoding="utf-8")
    repo_mod = tmp / "repo" / "ignite"
    (repo_mod / "team-kit").mkdir(parents=True)
    repo_mod.joinpath("exposure.csv").write_text(
        "# a prose header line — `#`-led lines are dropped before the header\n"
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "coordfix,tool,path,,team-kit/coordfix.py,,\n"
        "skillish,capability,skill,,team-kit/skillish.md,a skill row,\n",
        encoding="utf-8")
    repo_mod.joinpath("team-kit", "coordfix.py").write_text(
        "#!/usr/bin/env python3\nprint('coordfix')\n", encoding="utf-8")
    repo_mod.joinpath("team-kit", "skillish.md").write_text(
        "# skillish\n", encoding="utf-8")
    for rel, body in (
            ("skills/brws.md", "---\nexposes-cli:\n  - wstool\n---\n\n# brws\n\nBrowse skill content.\n"),
            ("commands/cmd1.md", "# cmd1\n\nCommand content.\n"),
            ("rules/rul1.md", "# rul1\n\nAlways-on fixture rule.\n"),
            ("prompts/res1.md",
             "---\nid: res1\ndescription: fixture researcher\n---\n\n"
             "<role>\nResearcher.\n</role>\n"),
            ("hooks/hk1.json", json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Write", "hooks": [
                    {"type": "command", "command": "demo-lint"}]}]}},
                indent=2) + "\n"),
            ("prompts/alpha-prompt.md",
             "---\nid: alpha-prompt\ndescription: exp fixture prompt card\n"
             "exposes:\n"
             "  skill: [brws, mcp-comp/xsk, xmod/xmodc/xms]\n"
             "  command: [cmd1]\n"
             "  rule: [rul1]\n"
             "  hook: [hk1]\n"
             "  sub-agent: [res1]\n"
             "  path: [rbtv:ignite/coordfix, wstool]\n"
             "---\n\nWhole-file prompt card — read for `exposes:`; assembly "
             "still resolves the catalog prompt row.\n")):
        p = expc / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    # A component in ANOTHER MODULE (the `module/component/part` ref arm):
    # installer identity `xmod/xmodc` at depth 2 of the mirror tree.
    xmodc = tmp / ".rbtv" / "mirror" / "xmod" / "xmodc"
    xmodc.mkdir(parents=True)
    xmodc.joinpath("exposure.csv").write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "xms,capability,skill,,xms.md,cross-module skill,\n",
        encoding="utf-8")
    xmodc.joinpath("xms.md").write_text(
        "# xms\n\nCross-module skill content.\n", encoding="utf-8")

    # D86 — depth-2 components in BOTH trees so unprefixed refs resolve
    # through scan_all (mirror wins on a shared id).
    hdr = ("part-id,part-kind,method,rbtv-cli,entry-point,description,"
           "write-roots\n")
    cap = tmp / ".rbtv" / "mirror" / "web" / "capture"
    cap.mkdir(parents=True)
    cap.joinpath("exposure.csv").write_text(
        hdr + "capture,capability,skill,,capture.md,mirror capture,\n",
        encoding="utf-8")
    cap.joinpath("capture.md").write_text("# capture\n", encoding="utf-8")
    brw = tmp / "repo" / "web" / "browse"
    brw.mkdir(parents=True)
    brw.joinpath("exposure.csv").write_text(
        hdr + "browse,capability,skill,,browse.md,repo browse,\n",
        encoding="utf-8")
    brw.joinpath("browse.md").write_text("# browse\n", encoding="utf-8")
    dup_m = tmp / ".rbtv" / "mirror" / "dup" / "comp"
    dup_r = tmp / "repo" / "dup" / "comp"
    dup_m.mkdir(parents=True)
    dup_r.mkdir(parents=True)
    dup_m.joinpath("exposure.csv").write_text(
        hdr + "dpart,capability,skill,,mirror.md,mirror winner,\n",
        encoding="utf-8")
    dup_m.joinpath("mirror.md").write_text("# mirror-dup\n", encoding="utf-8")
    dup_r.joinpath("exposure.csv").write_text(
        hdr + "dpart,capability,skill,,repo.md,repo shadowed,\n",
        encoding="utf-8")
    dup_r.joinpath("repo.md").write_text("# repo-dup\n", encoding="utf-8")

    def _mini_comp(root: Path, seat: str, prompt: str, exposes: str) -> Path:
        root.mkdir(parents=True)
        tag = seat.replace("-", "")
        for rel, uid, body in (
                (f"prompts/cognitive-units/roles/{tag}-r.md", f"{tag}-r",
                 "<role>\nX.\n</role>"),
                (f"prompts/cognitive-units/permissions/{tag}-p.md",
                 f"{tag}-p", "<permissions>\nP.\n</permissions>"),
                (f"prompts/cognitive-units/procedures/{tag}-pr.md",
                 f"{tag}-pr", "<procedure>\nDo.\n</procedure>"),
                (f"tasks/cognitive-units/task-goals/{tag}-g.md", f"{tag}-g",
                 "<task-goal>\nG.\n</task-goal>"),
                (f"tasks/cognitive-units/scopes/{tag}-s.md", f"{tag}-s",
                 "<scope>\nS.\n</scope>"),
                (f"tasks/cognitive-units/done-contracts/{tag}-d.md",
                 f"{tag}-d", "<done-contract>\nD.\n</done-contract>")):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"---\nid: {uid}\ndescription: {uid}\n---\n\n{body}\n",
                         encoding="utf-8")
        root.joinpath("prompts.csv").write_text(
            "prompt-id,role,permissions,procedure,description\n"
            f"{prompt},{tag}-r,{tag}-p,{tag}-pr,x\n", encoding="utf-8")
        root.joinpath("tasks.csv").write_text(
            "task-id,task goal,scope,done contract,description\n"
            f"{tag}-t,{tag}-g,{tag}-s,{tag}-d,x\n", encoding="utf-8")
        root.joinpath("seats.csv").write_text(
            "seat-id,executor,task,staffing-hints,description\n"
            f"{seat},{prompt},{tag}-t,,cross-tree seat\n", encoding="utf-8")
        root.joinpath("prompts", f"{prompt}.md").write_text(
            f"---\nid: {prompt}\ndescription: x\nexposes:\n"
            f"  skill: [{exposes}]\n---\n\nCard.\n", encoding="utf-8")
        return root

    repo_x = _mini_comp(tmp / "repo" / "xtree" / "from-repo",
                        "repo-xseat", "rxp", "web/capture/capture")
    mir_x = _mini_comp(tmp / ".rbtv" / "mirror" / "xtree" / "from-mirror",
                       "mir-xseat", "mxp", "web/browse/browse")
    win_x = _mini_comp(tmp / ".rbtv" / "mirror" / "xtree" / "dup-seat",
                       "dup-xseat", "dxp", "dup/comp/dpart")
    miss_x = _mini_comp(tmp / ".rbtv" / "mirror" / "xtree" / "miss-seat",
                        "miss-xseat", "nxp", "ghost/mod/gone")

    bdir = tmp / "bindings"
    bdir.mkdir()
    seat_binding = {
        "harness": "claude", "model": "claude-opus-5", "effort": "high",
        "ctx-refresh": 50, "agent_type": "staff",
        "description": "a fixture seat",
    }
    both = {
        "version": 1,
        "defaults": {"harness": "claude", "cwd-mode": "seat-folder",
                     "agent_type": "staff"},
        "seats": {
            "alpha": {**seat_binding, "after": []},
            "beta": {**seat_binding, "after": ["alpha"]},
        },
    }
    bdir.joinpath("both.json").write_text(json.dumps(both), encoding="utf-8")
    alpha_only = {"version": 1, "defaults": both["defaults"],
                  "seats": {"alpha": {**seat_binding, "after": []}}}
    bdir.joinpath("alpha.json").write_text(json.dumps(alpha_only), encoding="utf-8")
    bdir.joinpath("missing.json").write_text(json.dumps(alpha_only), encoding="utf-8")
    extra = {"version": 1, "defaults": both["defaults"],
             "seats": {**both["seats"], "ghost": dict(seat_binding)}}
    bdir.joinpath("extra.json").write_text(json.dumps(extra), encoding="utf-8")
    badafter = {"version": 1, "defaults": both["defaults"],
                "seats": {"alpha": {**seat_binding, "after": []},
                          "beta": {**seat_binding, "after": ["ghost"]}}}
    bdir.joinpath("badafter.json").write_text(json.dumps(badafter), encoding="utf-8")
    bdir.joinpath("broken.json").write_text("{not json", encoding="utf-8")
    scramble = {"version": 1, "defaults": both["defaults"],
                "seats": {"a2": {**seat_binding, "after": []},
                          "b2": {**seat_binding, "after": ["a2"]}}}
    bdir.joinpath("scramble.json").write_text(json.dumps(scramble),
                                              encoding="utf-8")
    b2_only = {"version": 1, "defaults": both["defaults"],
               "seats": {"b2": {**seat_binding, "after": []}}}
    bdir.joinpath("b2.json").write_text(json.dumps(b2_only), encoding="utf-8")
    beta_only = {"version": 1, "defaults": both["defaults"],
                 "seats": {"beta": {**seat_binding, "after": []}}}
    bdir.joinpath("beta.json").write_text(json.dumps(beta_only),
                                          encoding="utf-8")
    mcp_only = {"version": 1, "defaults": both["defaults"],
                "seats": {"mcp-seat": {**seat_binding, "after": []}}}
    bdir.joinpath("mcp-seat.json").write_text(json.dumps(mcp_only),
                                              encoding="utf-8")
    exp_only = {"version": 1, "defaults": both["defaults"],
                "seats": {"exp-seat": {**seat_binding, "after": []}}}
    bdir.joinpath("exp-seat.json").write_text(json.dumps(exp_only),
                                              encoding="utf-8")
    for sid in ("repo-xseat", "mir-xseat", "dup-xseat", "miss-xseat"):
        bdir.joinpath(f"{sid}.json").write_text(json.dumps({
            "version": 1, "defaults": both["defaults"],
            "seats": {sid: {**seat_binding, "after": []}},
        }), encoding="utf-8")
    guard = {"version": 1, "defaults": both["defaults"],
             "seats": {f"s{i}": dict(seat_binding) for i in range(1, 5)}}
    bdir.joinpath("guard.json").write_text(json.dumps(guard),
                                           encoding="utf-8")

    # dag-06 creation inputs — the CALLER-SUPPLIED pair
    # (d-run3-seeds-from-run2-amended). Fixture stand-ins for the amended
    # run-2 base texts dag-16 carries; the floor value is FIXTURE data inside
    # a caller file, never a number this command holds (R-10).
    seeds = tmp / "run-seeds"
    seeds.mkdir()
    (seeds / "CLAUDE.md").write_text(
        "# run\n\nFixture run CLAUDE.md base text (caller-supplied).\n",
        encoding="utf-8")
    (seeds / "budget.json").write_text(json.dumps(
        {"floors": {"launch_refuse_mb": 64},
         "cap": {"agent_panes": 4},
         "counting": {"counts_toward_cap": ["worker"]}}, indent=1) + "\n",
        encoding="utf-8")
    (seeds / "broken-budget.json").write_text(
        json.dumps({"note": "no floors key at all"}), encoding="utf-8")

    return {
        "tmp": tmp,
        "catalog": str(tmp / ".rbtv" / "mirror" / "catalog"),
        "repo_xtree": str(tmp / "repo" / "xtree"),
        "mirror_xtree": str(tmp / ".rbtv" / "mirror" / "xtree"),
        "b_repo_x": str(bdir / "repo-xseat.json"),
        "b_mir_x": str(bdir / "mir-xseat.json"),
        "b_dup_x": str(bdir / "dup-xseat.json"),
        "b_miss_x": str(bdir / "miss-xseat.json"),
        "pkg": str(pkg),
        "pkg9": str(pkg9),
        "pkg_status": str(pkg_status),
        "pkg_spine": str(pkg_spine),
        "pkg_absent": str(pkg_uncompleted),
        "b_both": str(bdir / "both.json"),
        "b_alpha": str(bdir / "alpha.json"),
        "b_missing": str(bdir / "missing.json"),
        "b_extra": str(bdir / "extra.json"),
        "b_badafter": str(bdir / "badafter.json"),
        "b_broken": str(bdir / "broken.json"),
        "b_guard": str(bdir / "guard.json"),
        "b_scramble": str(bdir / "scramble.json"),
        "b_b2": str(bdir / "b2.json"),
        "b_beta": str(bdir / "beta.json"),
        "b_mcp": str(bdir / "mcp-seat.json"),
        "b_exp": str(bdir / "exp-seat.json"),
        "exp_prompt": str(expc / "prompts" / "alpha-prompt.md"),
        "repo_mod": str(repo_mod),
        "mcp_decl": str(mcpc / "mcp.json"),
        "src_claude": str(seeds / "CLAUDE.md"),
        "src_budget": str(seeds / "budget.json"),
        "src_budget_broken": str(seeds / "broken-budget.json"),
    }


def selftest_scenarios(fx: dict) -> list[tuple[str, list[str], int, str | None]]:
    """(label, argv, expected rc, expected refusal code or None)."""
    def wf(**over) -> list[str]:
        base = {
            "--package": fx["pkg"], "--workflow": "demo-flow",
            "--catalog-root": fx["catalog"], "--bindings": fx["b_both"],
            "--milestone-id": "m1",
        }
        flags = over.pop("flags", ["--root", "--dry-run", "--json"])
        base.update(over)
        argv: list[str] = []
        for k, v in base.items():
            if v is not None:
                argv.extend([k, v])
        return argv + flags

    seat_argv = ["--package", fx["pkg"], "--seat", "alpha",
                 "--catalog-root", fx["catalog"], "--after", "chief",
                 "--bindings", fx["b_alpha"], "--dry-run", "--json"]
    return [
        ("green: dry-run materializes the whole workflow plan",
         wf(), 0, None),
        ("green: dry-run materializes one cataloged seat with --after",
         seat_argv, 0, None),
        ("SK-1 red: no insertion point is usage, never a root default",
         wf(flags=["--dry-run", "--json"]), 2, None),
        ("SK-2 red: --seat and --workflow together",
         wf() + ["--seat", "alpha"], 2, None),
        ("SK-2 red: neither --seat nor --workflow",
         [a for a in wf() if a not in ("--workflow", "demo-flow")], 2, None),
        ("SK-3 red: bindings missing a resolved seat",
         wf(**{"--bindings": fx["b_missing"]}), 1, "bindings-missing-seat"),
        ("SK-3 red: bindings carrying an extra seat",
         wf(**{"--bindings": fx["b_extra"]}), 1, "bindings-extra-seat"),
        # The pair above/below is the whole `whole_set` ruling: the SAME kind of
        # sheet refuses on a --workflow run and is accepted on a --seat one.
        # `b_both` casts alpha AND beta; building alpha alone out of it is what
        # the collapsed wave-re-entry pass does with the planning sheet.
        ("green: ONE seat built out of its WORKFLOW's whole sheet — every other "
         "seat of that sheet is not a stray key on a --seat run",
         [a if a != fx["b_alpha"] else fx["b_both"] for a in seat_argv], 0, None),
        ("red: bindings internal after outside the set",
         wf(**{"--bindings": fx["b_badafter"]}), 1, "bindings-after-unknown"),
        ("red: unknown seat id",
         ["--package", fx["pkg"], "--seat", "ghost", "--catalog-root",
          fx["catalog"], "--after", "chief", "--bindings", fx["b_alpha"],
          "--dry-run", "--json"], 1, "seat-unknown"),
        ("red: unknown workflow id",
         wf(**{"--workflow": "no-flow"}), 1, "workflow-unknown"),
        ("red: milestone-id resolves to no milestones.csv row",
         wf(**{"--milestone-id": "m9"}), 1, "milestone-unresolved"),
        ("red: package that is not a goal folder (not under goals/)",
         wf(**{"--package": fx["catalog"]}), 1, "package-not-a-goal"),
        ("red: package not absolute",
         wf(**{"--package": "goals/demo-goal"}), 1, "package-not-absolute"),
        ("red: absent package with NO creation inputs refuses naming them "
         "(dag-06 — an absent input is a refusal, never a default)",
         wf(**{"--package": fx["pkg_absent"]}), 1, "create-inputs-missing"),
        ("red: unreadable bindings JSON",
         wf(**{"--bindings": fx["b_broken"]}), 1, "bindings-unreadable"),
        ("red: dangling --after member",
         [a if a != "chief" else "ghost" for a in seat_argv], 1,
         "after-unresolved"),
        ("red: collision with an existing seat folder",
         ["--package", fx["pkg9"], "--seat", "alpha", "--catalog-root",
          fx["catalog"], "--after", "chief", "--bindings", fx["b_alpha"],
          "--dry-run", "--json"], 1, "seat-exists"),
        ("green: --force-partial completes the missing halves for a seat "
         "whose folder already exists (descriptor + registry row)",
         ["--package", fx["pkg9"], "--seat", "alpha", "--catalog-root",
          fx["catalog"], "--after", "chief", "--bindings", fx["b_alpha"],
          "--force-partial", "--json"], 0, None),
        ("green: guarded + alternate after cells resolve membership — guard "
         "suffix stripped, alternates split, '|' inside a bracket never "
         "splits (p-materializer-guard-suffix)",
         ["--package", fx["pkg"], "--workflow", "guard-flow",
          "--catalog-root", fx["catalog"], "--bindings", fx["b_guard"],
          "--root", "--dry-run", "--json"], 0, None),
        ("green: a non-dry run emits descriptors (dag-04) then appends the "
         "registry rows (dag-05)",
         wf(flags=["--root", "--json"]), 0, None),
    ]


def run_scenario_suite(env: dict, check=None) -> list[tuple[str, int, str]]:
    """Run every scenario in a fresh fixture; return normalized (label, rc,
    stdout) triples for the SK-4 cross-environment comparison. With `check`,
    also assert every expectation (the functional pass)."""
    results: list[tuple[str, int, str]] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        pre = _hash_tree(tmp)
        green_json: dict = {}
        real_json: dict = {}
        for label, argv, want_rc, want_code in selftest_scenarios(fx):
            cp = _invoke(argv, env)
            results.append((label, cp.returncode, _norm(cp.stdout, tmp)))
            if check is None:
                continue
            check(f"rc={want_rc}  {label}", cp.returncode == want_rc,
                  f"rc={cp.returncode} stderr={cp.stderr.strip()[:200]}")
            if want_code is not None:
                try:
                    obj = json.loads(cp.stdout)
                except ValueError:
                    obj = {}
                check(f"SK-6 machine-readable refusal  {label}",
                      obj.get("ok") is False
                      and obj.get("refusal", {}).get("code") == want_code
                      and bool(obj.get("refusal", {}).get("message")),
                      f"stdout={cp.stdout.strip()[:200]}")
            elif want_rc == 0:
                obj = json.loads(cp.stdout)
                if not green_json:
                    green_json = obj  # the dry-run workflow plan
                if label.startswith("green: a non-dry run emits"):
                    real_json = obj  # the SAME argv, real (SC-12 half 2)
        if check is not None:
            # SK-6 control arm: a success carries ok:true and NO refusal key.
            check("SK-6 control: success JSON has ok:true and no refusal key",
                  green_json.get("ok") is True and "refusal" not in green_json,
                  str(green_json)[:200])
            # Plan content — the green arms must not pass vacuously.
            check("plan: workflow resolves to [alpha, beta] in manifest order",
                  green_json.get("added_seats") == ["alpha", "beta"],
                  str(green_json.get("added_seats")))
            # `_sep`: writes[] carries NATIVE paths — the suffixes below are
            # POSIX-spelled, so the comparison is made separator-blind rather
            # than the emitter made POSIX-only.
            paths = [_sep(w["path"]) for w in green_json.get("writes", [])]
            kinds = [w["kind"] for w in green_json.get("writes", [])]
            # Per seat: descriptor THEN its guidance pair (CLAUDE.md + AGENTS.md,
            # d-uniform-descriptor-carriage), in emit order; then the one registry
            # append. Kinds are asserted too — a path set alone would still pass
            # if entries claimed the wrong kind.
            check("plan: writes name both descriptors, each seat's guidance "
                  "pair, and the registry append",
                  len(paths) == 7
                  and paths[0].endswith("seats/alpha/seat.md")
                  and paths[1].endswith("seats/alpha/CLAUDE.md")
                  and paths[2].endswith("seats/alpha/AGENTS.md")
                  and paths[3].endswith("seats/beta/seat.md")
                  and paths[4].endswith("seats/beta/CLAUDE.md")
                  and paths[5].endswith("seats/beta/AGENTS.md")
                  and paths[6].endswith(TASKFORCE_NAME)
                  and kinds == ["seat-descriptor", "seat-guidance",
                                "seat-guidance",
                                "seat-descriptor", "seat-guidance",
                                "seat-guidance",
                                "taskforce-append"],
                  f"{paths} {kinds}")
            check("plan: planned append count is 2, warnings plumbed empty",
                  green_json.get("taskforce_rows_appended") == 2
                  and green_json.get("warnings") == [], str(green_json)[:200])
            # SK-5/SC-12 second half (dag-07): the dry-run PLAN equals what
            # the real run then produces — same writes[], kind and path.
            check("SK-5: the dry-run plan's writes[] equals the real run's "
                  "writes[] kind-for-kind, path-for-path (spec SC-12 half 2)",
                  bool(real_json.get("writes"))
                  and [(w["kind"], w["path"])
                       for w in green_json.get("writes", [])]
                  == [(w["kind"], w["path"])
                      for w in real_json.get("writes", [])],
                  f"dry={green_json.get('writes')} "
                  f"real={real_json.get('writes')}")
            # SK-5 (amended at dag-05): dry runs and refusals still write
            # NOTHING; the only disk deltas are what the two non-dry green
            # scenarios legitimately materialize — their seat descriptors
            # (new files) plus their registry appends (the ONLY modified
            # pre-existing files). Exactly those, nothing else.
            post = _hash_tree(tmp)
            # Each materialized seat contributes THREE new files: its descriptor and
            # its guidance pair (CLAUDE.md + AGENTS.md, d-uniform-descriptor-carriage).
            # All are named here, so the write set stays exact: adding a fourth
            # artifact still fails this check.
            expected_new = {
                str((Path(fx["pkg"]) / "seats" / s / name).relative_to(tmp))
                for s in ("alpha", "beta")
                for name in ("seat.md", "CLAUDE.md", "AGENTS.md")
            } | {
                str((Path(fx["pkg9"]) / "seats" / "alpha" / name)
                    .relative_to(tmp))
                for name in ("seat.md", "CLAUDE.md", "AGENTS.md")
            }
            expected_modified = {
                str((Path(fx["pkg"]) / TASKFORCE_NAME).relative_to(tmp)),
                str((Path(fx["pkg9"]) / TASKFORCE_NAME).relative_to(tmp)),
            }
            modified = {k for k, v in pre.items() if post.get(k) != v}
            check("SK-5: the only writes are the two green materializations — "
                  "new seat.mds plus exactly their registry appends",
                  set(post) - set(pre) == expected_new
                  and modified == expected_modified,
                  f"new: {sorted(set(post) - set(pre))[:6]} "
                  f"modified: {sorted(modified)[:6]}")
            # dag-04 emission bits: file 0644, folder 0755.
            alpha_md = Path(fx["pkg"]) / "seats" / "alpha" / "seat.md"
            _check_emission_bits(
                check, "dag-04: emitted seat.md is 0644 and its folder 0755",
                alpha_md)
            # The tooling-gap filing block (owner ruling 2026-08-10). Both halves: the rule,
            # and the CONCRETE fallback path — a block naming no path routes nobody.
            alpha_agents = (alpha_md.parent / "AGENTS.md").read_text(encoding="utf-8")
            check("dag-04: the seat AGENTS.md carries the tooling-gap filing block, with "
                  "the package's own issues.md as the named fallback",
                  "OWNS that tooling" in alpha_agents
                  and str(Path(fx["pkg"]) / "issues.md") in alpha_agents,
                  alpha_agents[-500:])
            # d-uniform-descriptor-carriage: ONE body under both native names —
            # byte-identical, carrying the don't-re-read stance AND its hand-opened
            # exception (Q2a: absolute wording would run a hand-opened session blind).
            alpha_claude = (alpha_md.parent / "CLAUDE.md").read_text(
                encoding="utf-8")
            check("dag-04: the guidance pair is ONE body (CLAUDE.md == AGENTS.md) "
                  "with the don't-re-read stance and its hand-opened exception",
                  alpha_claude == alpha_agents
                  and "Do NOT read `seat.md` again" in alpha_claude
                  and "no descriptor in your context" in alpha_claude
                  and _GUIDANCE_BANNER in alpha_claude,
                  alpha_claude[:400])
            pre = post  # canary control baselines on the post-suite tree
            # SK-5 control arm: the hash comparison CAN go red.
            canary = tmp / "canary.txt"
            canary.write_text("x", encoding="utf-8")
            check("SK-5 control: the hash detector goes red on a real write",
                  _hash_tree(tmp) != pre)
            canary.unlink()
            check("SK-5 control: canary removed, tree restored",
                  _hash_tree(tmp) == pre)
    return results


def run_dag04_acceptance(check, env: dict) -> None:
    """dag-04's SC rows, each with the control that must be able to FAIL.
    Fixture-only (tempfile.TemporaryDirectory) — never a real run. The
    in-process red arms use render_descriptors' selftest-only knobs."""

    def _refusal(cp):
        try:
            return json.loads(cp.stdout).get("refusal") or {}
        except ValueError:
            return {}

    # ---- group 1: the emitted surface (SC-2, SC-14/16 halves, SC-18,
    #      SC-20 + reorder, key set/order, F10 control) -------------------
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        cp = _invoke(["--package", fx["pkg"], "--workflow", "demo-flow",
                      "--catalog-root", fx["catalog"], "--bindings",
                      fx["b_both"], "--milestone-id", "m1", "--root",
                      "--json"], env)
        alpha_md = Path(fx["pkg"]) / "seats" / "alpha" / "seat.md"
        beta_md = Path(fx["pkg"]) / "seats" / "beta" / "seat.md"
        check("dag-04 setup: non-dry emit lands both descriptors and the "
              "dag-05 rows half completes",
              cp.returncode == 0
              and alpha_md.is_file() and beta_md.is_file(),
              cp.stdout.strip()[:200])
        atext = alpha_md.read_text(encoding="utf-8")
        btext = beta_md.read_text(encoding="utf-8")
        afm = yaml.safe_load(_FM_RE.match(atext).group(1))
        bfm = yaml.safe_load(_FM_RE.match(btext).group(1))

        # The kit is `ignite/coord/` since the component-first move — a SIBLING
        # component of this one, no longer this file's own directory.
        kit_dir = Path(__file__).resolve().parent.parent / "coord"
        if str(kit_dir) not in sys.path:
            sys.path.insert(0, str(kit_dir))
        # Selftest-only import: SC-2's stated control IS discover_workers;
        # the COMMAND itself imports only validate_seat from coord.py.
        from coord import discover_workers
        seats_dir = Path(fx["pkg"]) / "seats"
        found = {w["agent"]: w for w in discover_workers(seats_dir)}
        check("SC-2: descriptor carries seat: and discover_workers finds it",
              afm.get("seat") == "alpha" and "alpha" in found
              and found["alpha"]["briefing"] == alpha_md
              and found["alpha"]["harness"] == "claude"
              and found["alpha"]["ctx_refresh"] == 50,
              str(sorted(found)))
        alpha_md.write_text(atext.replace("seat: alpha", "id: alpha", 1),
                            encoding="utf-8")
        found_red = {w["agent"] for w in discover_workers(seats_dir)}
        check("SC-2 red: with id: instead of seat: (B3) the seat is "
              "returned not at all",
              "alpha" not in found_red, str(sorted(found_red)))
        alpha_md.write_text(atext, encoding="utf-8")

        # D3 (outputs-unify, 2026-08-18): the emitted descriptor carries NO
        # `outputs:` frontmatter key (retired surface), its io-spec
        # `## Outputs` block is the one declared-outputs surface, and coord's
        # OWN grading parse (discover_workers -> iospec_outputs) reads the
        # token off the emitted BODY — the whole-pipeline agreement, not a
        # regex hope.
        check("D3: emitted descriptor carries the `## Outputs` block, no "
              "`outputs:` key, and coord's grading parse reads the token",
              "outputs" not in afm and "## Outputs" in atext
              and found["alpha"]["outputs"] == ["./alpha-notes.md"]
              and found["alpha"]["outputs_declared"] is True
              and found["alpha"]["outputs_defect"] == "",
              f"outputs={found['alpha'].get('outputs')!r}")

        check("SC-18: every emitted frontmatter parses via yaml.safe_load",
              isinstance(afm, dict) and isinstance(bfm, dict))
        try:
            yaml.safe_load("description: G-256: the colon-space defect\n")
            raised = False
        except yaml.YAMLError:
            raised = True
        check("SC-18 red: an unquoted colon-space description raises in "
              "the loader (the check can fail)", raised)

        kinds = [m.group(1) for m in _BLOCK_RE.finditer(atext)]
        contract_order = ["role", "procedure", "permissions", "io-spec",
                          "task-goal", "scope", "done-contract"]
        check("contract §1: blocks in the FIXED kind order despite "
              "scrambled CSV columns", kinds == contract_order, str(kinds))

        bodies = "\n".join(m.group(4) for m in _BLOCK_RE.finditer(atext))
        check("SC-20: inline Reference resolved — outcome body inlined, "
              "zero @latest in block bodies",
              "Notes that let beta act" in bodies
              and "@latest" not in bodies)

        def render_one(seat, **knobs):
            catalogs = load_catalogs(Path(fx["catalog"]))
            normalize_seat_rows(catalogs[0])
            units = index_units(Path(fx["catalog"]))
            b = load_bindings(Path(fx["b_both"]))
            binding = effective_binding(b, seat)
            plan = {"package": fx["pkg"], "added_seats": [seat],
                    "bindings": {seat: binding}, "warnings": [],
                    "force_partial": False,
                    "assembled": {seat: assemble_seat(
                        seat, binding, *catalogs, units)}}
            render_descriptors(plan, catalogs[0], units, **knobs)
            return plan["descriptors"][seat]

        red20 = render_one("alpha", resolve_inline=False)
        red20_bodies = "\n".join(
            m.group(4) for m in _BLOCK_RE.finditer(red20))
        check("SC-20 red: with resolution disabled the @latest grep "
              "control goes RED", "@latest" in red20_bodies)
        red_order = [m.group(1)
                     for m in _BLOCK_RE.finditer(render_one("alpha",
                                                            reorder=False))]
        check("reorder red: with reorder disabled the order follows CSV "
              "columns and violates the contract",
              red_order != contract_order
              and red_order == ["io-spec", "permissions", "role",
                                "procedure", "done-contract", "scope",
                                "task-goal"],
              str(red_order))

        # D3 red + warn arms, in-process. The bindings door already refuses
        # `outputs` as an unknown binding key; the assembled-frontmatter
        # carry-over is the one hole left, so the red arm drives exactly it.
        def render_mutated(mutate):
            catalogs = load_catalogs(Path(fx["catalog"]))
            normalize_seat_rows(catalogs[0])
            units = index_units(Path(fx["catalog"]))
            binding = effective_binding(load_bindings(Path(fx["b_both"])),
                                        "alpha")
            plan = {"package": fx["pkg"], "added_seats": ["alpha"],
                    "bindings": {"alpha": binding}, "warnings": [],
                    "force_partial": False,
                    "assembled": {"alpha": mutate(assemble_seat(
                        "alpha", binding, *catalogs, units))}}
            try:
                render_descriptors(plan, catalogs[0], units)
            except Refuse as exc:
                return plan, exc.code
            return plan, None

        check("D3 red: assembled frontmatter smuggling the RETIRED "
              "`outputs:` key is refused `outputs-key-retired` at "
              "materialize — loudly, by name, before any write",
              render_mutated(lambda a: a.replace(
                  "---\n", "---\noutputs: plan.md\n", 1))[1]
              == "outputs-key-retired")
        _d3_prose, _d3_pcode = render_mutated(lambda a: a.replace(
            "`./alpha-notes.md`", "prose only, no path token"))
        check("D3 warn: a ZERO-TOKEN `## Outputs` block warns LOUDLY at "
              "materialize (`outputs-undeclarable` — the check-out will "
              "verify nothing), and a token-bearing block does not",
              _d3_pcode is None
              and any("outputs-undeclarable" in w
                      for w in _d3_prose["warnings"])
              and render_mutated(lambda a: a)[0]["warnings"] == [],
              str(_d3_prose["warnings"])[:200])

        # ---- D36 (2026-08-20): THE PROJECTION, ITS CONTROL, AND ITS RED ------------------
        # Four arms over ONE fixture, each one fact apart from the next, so no arm can pass
        # for another arm's reason. `_op_scope` rewrites the fixture's `<scope>` body; the
        # io-spec mutation decides what the block already declares.
        def _op(io_mut, scope_body):
            return render_mutated(
                lambda a: io_mut(a).replace("The fixture tree only.", scope_body))
        _OP_PROSE = lambda a: a.replace("`./alpha-notes.md`", "prose only, no path token")
        _OP_CHAT = lambda a: a.replace(
            "## Outputs\n`./alpha-notes.md`",
            "## Outputs\n- Schema: chat — the answer, spoken on the bus.")
        _op_read = _coord_iospec_outputs()

        _op1, _op1c = _op(_OP_PROSE, "- Write: the notes at `./alpha-notes.md`.")
        _op1_txt = "" if _op1c else _op1["descriptors"]["alpha"]
        check("D36 (2026-08-20) THE DESTINATION IS PROJECTED FROM THE TASK'S `<scope>` INTO "
              "THE ONE SURFACE THE GATE READS. The prompt's `## Outputs` is prose (schema, "
              "no path — the shape 94 of 101 live seats carry); the task's `Write:` bullet "
              "names the file; the rendered descriptor now declares it, coord's OWN resolver "
              "reads the token off the emitted body, and the zero-token warning is silent. "
              "This is the whole of RC-3: same two blocks, one of them finally machine-read",
              _op1c is None
              and "- Destination (projected from the task's scope Write clause): "
                  "`./alpha-notes.md`" in _op1_txt
              and _op_read(_op1_txt)[1] == ["./alpha-notes.md"]
              and _op1["warnings"] == [],
              str(_op1["warnings"])[:200] + _op1_txt[-300:] if _op1c is None else _op1c)

        _op2, _op2c = _op(lambda a: a, "- Write: the log at `./other/run.log`.")
        _op2_txt = "" if _op2c else _op2["descriptors"]["alpha"]
        check("D36 NO SECOND AUTHORITY: a `## Outputs` block that ALREADY resolves a token is "
              "left byte-untouched — the task's `Write:` bullet names a DIFFERENT file "
              "(`./other/run.log`) and nothing is projected. An author who declared is the "
              "authority; a projection beside a declaration would be two of them, and the "
              "check-out would start demanding a file the seat never promised",
              _op2c is None
              and "Destination (projected" not in _op2_txt
              and _op_read(_op2_txt)[1] == ["./alpha-notes.md"],
              _op2_txt[-300:] if _op2c is None else _op2c)

        _op3, _op3c = _op(_OP_PROSE, "- Write: somewhere on the run surface, unnamed.")
        check("D36 RED (the zero-token check still bites): prose `## Outputs` AND a `Write:` "
              "bullet naming no resolvable token warns `outputs-undeclarable` BY NAME — the "
              "projection rescues nothing it cannot resolve, and this is the arm that would "
              "go green if the warning were ever quietly dropped. It stays a WARNING and not "
              "a refusal on measured ground: 26 non-chair live seats of the two production "
              "goals still land here, and refusing them would freeze re-render and m4's mint",
              _op3c is None
              and any("outputs-undeclarable" in w for w in _op3["warnings"])
              and "Destination (projected" not in _op3["descriptors"]["alpha"],
              str(_op3["warnings"])[:200])

        _op4, _op4c = _op(_OP_CHAT, "- Write: the notes at `./alpha-notes.md`.")
        _op4_txt = "" if _op4c else _op4["descriptors"]["alpha"]
        check("D36 THE TYPED `chat` OUTPUT IS A DECLARATION: a block opening `- Schema: chat` "
              "declares a NON-FILE product, so NOTHING is projected into it (its `Write:` "
              "bullet names a real token and is still ignored) and the zero-token warning "
              "stays silent — the same fact coord's check-out reads to let that `done` stand",
              _op4c is None
              and "Destination (projected" not in _op4_txt
              and _op_read(_op4_txt)[2] is True
              and _op4["warnings"] == [],
              str(_op4["warnings"])[:200])

        # D5 (seed-gates, 2026-08-19): a done-contract NAMING a probe lane
        # (`probe lane: `stools workspaces``) emits a machine-readable
        # `- cli `stools`` entry under `## Requires-reach` INSIDE the io-spec
        # block — the surface `envelope/cage-admission.js#admitLaneReach` reads
        # at the pre-enqueue gate — and the unmutated control emits none.
        _d5_plan, _d5_code = render_mutated(lambda a: a.replace(
            "Outputs exist and are non-empty.",
            "Outputs exist and are non-empty.\n"
            "probe lane: `stools workspaces`"))
        _d5_text = ("" if _d5_code is not None
                    else _d5_plan["descriptors"]["alpha"])
        _d5_io = next((m.group(0) for m in _BLOCK_RE.finditer(_d5_text)
                       if m.group(1) == "io-spec"), "")
        check("D5: a done-contract `probe lane:` line emits `- cli "
              "`stools`` under `## Requires-reach` inside the io-spec "
              "block, and the lane-less control emits no section",
              _d5_code is None and "## Requires-reach" in _d5_io
              and "- cli `stools`" in _d5_io
              and "## Requires-reach" not in
              render_mutated(lambda a: a)[0]["descriptors"]["alpha"],
              (_d5_io[-260:] if _d5_io else f"refused {_d5_code}"))

        check("emitted key set opens in the ruled order "
              "(seat..description..cwd..agent_type..triple..mode)",
              list(afm)[:8] == ["seat", "description", "cwd", "agent_type",
                                "harness", "model", "effort", "mode"],
              str(list(afm)[:9]))
        check("B4 closed: cwd is the seat folder; ctx-refresh emitted in "
              "interactive mode",
              _sep(afm.get("cwd") or "") == _sep(f"{fx['pkg']}/seats/alpha/")
              and afm.get("ctx-refresh") == 50,
              f"cwd={afm.get('cwd')!r} ctx-refresh={afm.get('ctx-refresh')!r}")
        check("SC-14 (first arm): mode: emitted on every descriptor",
              afm.get("mode") == "interactive"
              and bfm.get("mode") == "interactive")
        check("SC-16 control: an interactive staff seat gets NO close: key",
              "close" not in afm and "close" not in bfm)
        check("task half emitted (ruled executor+task header aliased to "
              "the assembler's task-id)",
              all(k in kinds for k in ("task-goal", "scope",
                                       "done-contract")))
        # ⚠ RE-STATED, not deleted (the one-shot tail dropped its `checkin`
        # line). It still keys on `checkout` and on the boot-tail MARKER, so an
        # interactive seat that started carrying the tail goes red here; the
        # `checkin` half is kept as the standing assertion that no descriptor
        # of any mode re-issues a lane-dependent order this file cannot resolve.
        check("F10 control: an interactive seat carries no one-shot boot "
              "text — no marker, no checkout order, and no checkin anywhere",
              "one-shot boot (F10)" not in atext
              and "checkout" not in atext and "checkin" not in atext)
        _check_emission_bits(
            check, "dag-04: emission bits are 0644 file / 0755 folder",
            alpha_md)

    # ---- group 2: SC-4 (permissions hard gate) + SC-3 (empty assembly) --
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        comp = Path(fx["catalog"]) / "demo-comp"
        good_prompts = (comp / "prompts.csv").read_text(encoding="utf-8")
        argv = ["--package", fx["pkg"], "--seat", "alpha", "--catalog-root",
                fx["catalog"], "--after", "chief", "--bindings",
                fx["b_alpha"], "--dry-run", "--json"]

        (comp / "prompts.csv").write_text(good_prompts.replace(
            "alpha-prompt,alpha-io@latest,common-permissions,",
            "alpha-prompt,alpha-io@latest,,"), encoding="utf-8")
        cp = _invoke(argv, env)
        check("SC-4: a seat with no resolvable permissions unit is refused",
              cp.returncode == 1
              and _refusal(cp).get("code") == "no-permissions"
              and "alpha" in _refusal(cp).get("message", ""),
              cp.stdout.strip()[:200])
        (comp / "prompts.csv").write_text(good_prompts, encoding="utf-8")
        cp = _invoke(argv, env)
        check("SC-4 control: the same seat WITH its permissions unit "
              "exits 0", cp.returncode == 0, cp.stderr.strip()[:200])

        (comp / "prompts.csv").write_text(
            "prompt-id,i/o spec,permissions,role,procedure,description\n"
            "alpha-prompt,free prose here,more prose here,other prose "
            "here,also prose here,alpha prompt\n"
            "beta-prompt,,x y z,z w v,v u t,beta prompt\n",
            encoding="utf-8")
        (comp / "tasks.csv").write_text(
            "task-id,done contract,scope,task goal,description\n"
            "alpha-task,p q r,r s t,t u v,alpha task\n"
            "beta-task,p q r,r s t,t u v,beta task\n", encoding="utf-8")
        cp = _invoke(argv, env)
        check("SC-3: a catalog assembling an empty body refuses with the "
              "exact message",
              cp.returncode == 1
              and _refusal(cp).get("code") == "empty-assembly"
              and _refusal(cp).get("message")
              == "no cognitive-unit block assembled for seat 'alpha'",
              cp.stdout.strip()[:200])

    # ---- group 3: SC-13 batch gate, SC-14/16 one-shot arms, F5 codex,
    #      SC-17 class:, relays pass-through, senders, SC-19 window -------
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        bdir = tmp / "bindings"
        wide_defaults = {"harness": "opencode", "cwd-mode": "seat-folder",
                         "agent_type": "worker", "effort": "low",
                         "description": "a wide one-shot worker"}

        def wide_bindings(name: str, bad_seat: str | None = None) -> str:
            seats = {f"s{i}": {"model": "deepseek/deepseek-chat",
                               "after": []} for i in range(1, 6)}
            if bad_seat:
                seats[bad_seat]["model"] = "deepseek-chat"
            p = bdir / name
            p.write_text(json.dumps({"version": 1, "defaults": wide_defaults,
                                     "seats": seats}), encoding="utf-8")
            return str(p)

        def wf_argv(b: str) -> list[str]:
            return ["--package", fx["pkg"], "--workflow", "wide-flow",
                    "--catalog-root", fx["catalog"], "--bindings", b,
                    "--root", "--json"]

        tf_before = (Path(fx["pkg"]) / TASKFORCE_NAME).read_bytes()
        cp = _invoke(wf_argv(wide_bindings("wide-bad.json", "s3")), env)
        folders = sorted(p.name
                         for p in (Path(fx["pkg"]) / "seats").iterdir())
        check("SC-13: ONE bad model slug refuses the WHOLE 5-seat batch — "
              "zero folders, zero rows (F6, never a per-seat skip)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "model-invalid"
              and "s3" in _refusal(cp).get("message", "")
              and folders == []
              and (Path(fx["pkg"]) / TASKFORCE_NAME).read_bytes()
              == tf_before,
              cp.stdout.strip()[:200])
        cp = _invoke(wf_argv(wide_bindings("wide-good.json")), env)
        smds = [Path(fx["pkg"]) / "seats" / f"s{i}" / "seat.md"
                for i in range(1, 6)]
        check("SC-13 control: the same batch with provider/model slugs "
              "writes all 5 descriptors and appends all 5 rows",
              cp.returncode == 0
              and all(p.is_file() for p in smds)
              and json.loads(cp.stdout).get("taskforce_rows_appended") == 5,
              cp.stdout.strip()[:200])
        s1_text = smds[0].read_text(encoding="utf-8")
        s1_fm = yaml.safe_load(_FM_RE.match(s1_text).group(1))
        check("SC-14: opencode default is mode: one-shot, emitted, with "
              "NO ctx-refresh key",
              s1_fm.get("mode") == "one-shot"
              and "ctx-refresh" not in s1_fm)
        check("SC-16: a cheap one-shot worker gets close: mechanical (F8)",
              s1_fm.get("close") == "mechanical")
        # ⚠ RE-STATED, not deleted. It used to demand BOTH command strings;
        # it now demands the check-OUT string verbatim and REFUSES the
        # check-IN one — this file is lane-blind, and a hardcoded `checkin`
        # re-issues on the daemon lane the order `coord.py#boot_prompt`
        # withdrew there (W1 C4). Both halves are load-bearing: without the
        # positive half a change that dropped check-out entirely would pass,
        # and check-out is the sole producer of `incomplete`.
        check("F10: a one-shot descriptor carries the check-OUT command "
              "string verbatim and orders NO check-in (lane-blind: check-in "
              "is the boot prompt's, which knows the lane)",
              f"coordinate --package {fx['pkg']} --as s1 checkout" in s1_text
              and "checkin" not in s1_text)

        def s1_bindings(name: str, extra: dict, seat: str = "s1") -> str:
            entry = {"model": "deepseek/deepseek-chat", "after": [], **extra}
            p = bdir / name
            p.write_text(json.dumps({"version": 1, "defaults": wide_defaults,
                                     "seats": {seat: entry}}),
                         encoding="utf-8")
            return str(p)

        def s1_argv(b: str, dry: bool = True, seat: str = "s1") -> list[str]:
            base = ["--package", fx["pkg9"], "--seat", seat,
                    "--catalog-root", fx["catalog"], "--bindings", b,
                    "--root", "--json"]
            return base + (["--dry-run"] if dry else [])

        cp = _invoke(s1_argv(s1_bindings("ctx-oneshot.json",
                                         {"ctx-refresh": 50})), env)
        check("SC-14: mode: one-shot with ctx-refresh refuses, naming the "
              "key (F4)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "ctx-refresh-on-one-shot"
              and "ctx-refresh" in _refusal(cp).get("message", ""),
              cp.stdout.strip()[:200])
        cp = _invoke(s1_argv(s1_bindings(
            "ctx-interactive.json",
            {"ctx-refresh": 50, "mode": "interactive"})), env)
        check("SC-14 control: the same seat in mode: interactive is "
              "accepted", cp.returncode == 0, cp.stderr.strip()[:200])
        cp = _invoke(s1_argv(s1_bindings(
            "codex.json", {"harness": "codex", "model": "gpt-5.5-codex"})),
            env)
        check("F5: codex with no explicit mode: is REFUSED at emission "
              "(no default)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "mode-undecidable"
              and "codex" in _refusal(cp).get("message", ""),
              cp.stdout.strip()[:200])
        cp = _invoke(s1_argv(s1_bindings("class.json",
                                         {"class": "worker"})), env)
        check("SC-17: class: is refused naming the withdrawn spelling "
              "(G-217)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "class-withdrawn"
              and "class:" in _refusal(cp).get("message", "")
              and "withdrawn" in _refusal(cp).get("message", "").lower(),
              cp.stdout.strip()[:200])
        cp = _invoke(s1_argv(s1_bindings("plain.json", {})), env)
        plain = json.loads(cp.stdout)
        check("SC-17 control: agent_type: worker is accepted",
              cp.returncode == 0, cp.stderr.strip()[:200])
        check("SC-19 control: no window: value, no renew-consequence line",
              plain.get("warnings") == [], str(plain.get("warnings")))
        # relays — the ONE pass-through row the ruled key set gained when
        # owner ask A-40 was ruled (a) (d-relays-frontmatter-passthrough,
        # task 7.104). This row's POLARITY was INVERTED here: it used to
        # assert the refusal `relays-unruled`. GREEN = a declared relays:
        # reaches the emitted frontmatter; RED (the counter-case) = a
        # definition declaring none emits NO relays: key. `class:` above is
        # UNCHANGED and still refused (r-agent-type-field-name, G-217).
        # Written into seat s2 so the senders arm below still owns s1.
        cp = _invoke(s1_argv(s1_bindings("relays.json", {"relays": "master"},
                                         seat="s2"), dry=False, seat="s2"),
                     env)
        s2_md = Path(fx["pkg9"]) / "seats" / "s2" / "seat.md"
        s2_fm = (yaml.safe_load(
            _FM_RE.match(s2_md.read_text(encoding="utf-8")).group(1))
            if cp.returncode == 0 and s2_md.is_file() else {})
        check("relays: a declared relays: passes THROUGH to the emitted "
              "descriptor's frontmatter (d-relays-frontmatter-passthrough)",
              cp.returncode == 0 and s2_fm.get("relays") == "master",
              cp.stdout.strip()[:200] or str(s2_fm))
        check("relays counter-case: a definition declaring NO relays: emits "
              "no relays: key at all — absent, never empty",
              "relays" not in s1_fm, str(list(s1_fm)))
        cp = _invoke(s1_argv(s1_bindings("window.json",
                                         {"window": "main"})), env)
        wobj = json.loads(cp.stdout)
        check("SC-19: a window: value prints the seat and its renew "
              "consequence",
              cp.returncode == 0
              and any("s1" in w and "in-place renew" in w
                      for w in wobj.get("warnings", [])),
              str(wobj.get("warnings")))
        cp = _invoke(s1_argv(s1_bindings("senders-engineer-only.json",
                                         {"senders": "engineer"})), env)
        check("senders: an allow-list emptied by the engineer drop refuses "
              "loudly (d-engineer-retired)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "senders-empty",
              cp.stdout.strip()[:200])
        cp = _invoke(s1_argv(s1_bindings("senders.json",
                                         {"senders": "leader,engineer"}),
                             dry=False), env)
        s1_pkg9 = Path(fx["pkg9"]) / "seats" / "s1" / "seat.md"
        s1_pkg9_fm = yaml.safe_load(
            _FM_RE.match(s1_pkg9.read_text(encoding="utf-8")).group(1))
        check("senders: 'engineer' is never emitted; the rest of the "
              "allow-list survives",
              s1_pkg9_fm.get("senders") == "leader",
              str(s1_pkg9_fm.get("senders")))
        # agent-type — the PERMANENT guard on the widened AGENT_TYPES
        # (d-agent-type-widened-to-the-kg-top-set). SC-17 above covers only
        # `worker` acceptance, so a future re-narrowing to staff|worker would
        # have passed the suite green. Green arm: `master` is accepted AND
        # reaches the emitted frontmatter, `verifier` is accepted. Red arm: an
        # invalid value is STILL refused and its message names ALL FOUR valid
        # values (the arm that catches a re-narrowing), and an absent value is
        # STILL refused — a widened set that accepted everything would make
        # the green meaningless.
        cp = _invoke(s1_argv(s1_bindings("agent-type-master.json",
                                         {"agent_type": "master"}, seat="s3"),
                             dry=False, seat="s3"), env)
        s3_md = Path(fx["pkg9"]) / "seats" / "s3" / "seat.md"
        s3_fm = (yaml.safe_load(
            _FM_RE.match(s3_md.read_text(encoding="utf-8")).group(1))
            if cp.returncode == 0 and s3_md.is_file() else {})
        check("agent-type: agent_type: master is ACCEPTED and reaches the "
              "emitted descriptor's frontmatter as master",
              cp.returncode == 0 and s3_fm.get("agent_type") == "master",
              cp.stdout.strip()[:200] or str(s3_fm))
        cp = _invoke(s1_argv(s1_bindings("agent-type-verifier.json",
                                         {"agent_type": "verifier"},
                                         seat="s4"), seat="s4"), env)
        check("agent-type: agent_type: verifier is ACCEPTED",
              cp.returncode == 0, cp.stderr.strip()[:200])
        cp = _invoke(s1_argv(s1_bindings("agent-type-bogus.json",
                                         {"agent_type": "operator"},
                                         seat="s5"), seat="s5"), env)
        # The four values are written out LITERALLY here, deliberately: a
        # check that reads AGENT_TYPES cannot detect a change to AGENT_TYPES
        # — it would move with the code and pass a re-narrowing green
        # (measured while landing this row). This literal IS the guard.
        check("agent-type red: an invalid agent_type is REFUSED and the "
              "refusal names ALL FOUR ruled values (master staff worker "
              "verifier)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "agent-type-invalid"
              and all(v in _refusal(cp).get("message", "")
                      for v in ("master", "staff", "worker", "verifier")),
              cp.stdout.strip()[:200])
        p_absent = bdir / "agent-type-absent.json"
        p_absent.write_text(json.dumps(
            {"version": 1,
             "defaults": {k: v for k, v in wide_defaults.items()
                          if k != "agent_type"},
             "seats": {"s5": {"model": "deepseek/deepseek-chat",
                              "after": []}}}), encoding="utf-8")
        cp = _invoke(s1_argv(str(p_absent), seat="s5"), env)
        check("agent-type red: an ABSENT agent_type is REFUSED naming it "
              "(absent) — required, never defaulted",
              cp.returncode == 1
              and _refusal(cp).get("code") == "agent-type-invalid"
              and "(absent)" in _refusal(cp).get("message", ""),
              cp.stdout.strip()[:200])

    # ---- group 4: goal_cli lint over an emitted package (the dag-01
    #      guard-comment contract: no scalar key false-positives) --------
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        # 7.607 E2b: the package IS the goal folder, and the bar is positional
        # (`.../goals/<goal>`, the seat-folder.js grammar) — so the lint tree's
        # goals root is literally named `goals`, under its own parent so it
        # cannot collide with the shared fixture's.
        groot = tmp / "lint" / "goals"
        gdir = groot / "demo-goal"
        run1 = gdir
        (run1 / "seats").mkdir(parents=True)
        (run1 / "coordination").mkdir()
        (gdir / "goal.md").write_text(
            "---\nname: demo-goal\ncreation-date: 2026-07-29\n"
            "type: one-shot\nstatus: active\n---\n\n"
            "Prove the emitted descriptor surface lints clean.\n",
            encoding="utf-8")
        (gdir / "decisions.md").write_text("# decisions\n", encoding="utf-8")
        (gdir / "threads.sql").write_text("-- threads\n", encoding="utf-8")
        (run1 / MILESTONES_NAME).write_text(
            "milestone-id,name,status\nm1,prove,pending\n", encoding="utf-8")
        # dag-05: seed the registry (canonical header + the run's existing
        # row) so the append has a taskforce-id to read — the appended rows
        # are now the REAL rows the lint reads, not hand-written stand-ins.
        (run1 / TASKFORCE_NAME).write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,"
            "milestone-id\n"
            "tf-a,chief,,claude,claude-opus-5,high,50,\n", encoding="utf-8")
        cp = _invoke(["--package", str(run1), "--workflow", "demo-flow",
                      "--catalog-root", fx["catalog"], "--bindings",
                      fx["b_both"], "--root", "--json"], env)
        check("lint setup: descriptors emitted + rows appended into the "
              "goal fixture",
              cp.returncode == 0
              and (run1 / "seats" / "alpha" / "seat.md").is_file()
              and (run1 / "seats" / "beta" / "seat.md").is_file(),
              cp.stdout.strip()[:200])
        # The seeded chief row needs a lint-clean folder: reuse the emitted
        # alpha descriptor verbatim (goal-lint checks bindings + refs, not
        # the seat: name) — fixture furniture, not a mechanic under test.
        chief_dir = run1 / "seats" / "chief"
        chief_dir.mkdir()
        (chief_dir / "seat.md").write_text(
            (run1 / "seats" / "alpha" / "seat.md").read_text(encoding="utf-8"),
            encoding="utf-8")
        from goal_cli import lint_goal
        f = lint_goal(groot, "demo-goal")
        check("goal_cli lint: the emitted package (real appended rows "
              "included) lints CLEAN — no scalar key false-positives",
              not bool(f), str(f.items[:4]))
        amd = run1 / "seats" / "alpha" / "seat.md"
        orig = amd.read_text(encoding="utf-8")
        amd.write_text(orig.replace("---\n", "---\nbogus-ref: no-such-unit\n",
                                    1), encoding="utf-8")
        f2 = lint_goal(groot, "demo-goal")
        check("lint control: a genuinely dangling ref is STILL flagged "
              "(exclusion list not over-wide)",
              any("no-such-unit" in i["reason"] for i in f2.items),
              str([i["reason"] for i in f2.items][:3]))
        amd.write_text(orig, encoding="utf-8")


def run_dag05_acceptance(check, env: dict) -> None:
    """dag-05's SC rows (spec §1.8: SC-1, SC-5, SC-6, SC-8, SC-9, SC-10,
    SC-15, SC-20, SC-21), each with the control that must be able to FAIL.
    Fixture-only (tempfile.TemporaryDirectory) — never a real run. SC-1's
    launch coupling runs coord.py's OWN `launch --dry-run` / `descriptors`
    against the throwaway package; the coord.py md5 under test is printed as
    evidence. Registration side note: coord.py auto-registers packages by
    folder-name tag in ~/.config/rbtv/coordinate-runs.json — the fixture
    packages are named run-1, a tag held by a live run, so the register
    declines (never stolen) and nothing durable is written."""
    import shutil

    def _refusal(cp):
        try:
            return json.loads(cp.stdout).get("refusal") or {}
        except ValueError:
            return {}

    # coord.py is `ignite/coord/`'s since the component-first move — a SIBLING
    # component of this one, no longer this file's own directory.
    coord_py = Path(__file__).resolve().parent.parent / "coord" / "coord.py"
    coord_md5 = hashlib.md5(coord_py.read_bytes()).hexdigest()
    print(f"  info SC-1: coord.py under test — md5 {coord_md5}")

    def coord(argv):
        return subprocess.run([sys.executable, str(coord_py), *argv],
                              capture_output=True, text=True, env=env)

    # ⚠ THE OTHER DOOR. `launch`, `descriptors` and the rest of the remedial surface left
    # `coordinate` for `supervise` when the entry point split by audience (owner ruling
    # 2026-08-25); driving them through `coord.py` would exercise a refusal, not the verb.
    supervise_py = coord_py.parent.parent / "supervisor" / "supervise.py"

    def supervise(argv):
        return subprocess.run([sys.executable, str(supervise_py), *argv],
                              capture_output=True, text=True, env=env)

    # ---- group 1: SC-1 (full add + launch coupling), SC-9, SC-10 arm 1,
    #      topo order ---------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        fx = build_fixture(Path(td))
        pkg = Path(fx["pkg"])
        tf = pkg / TASKFORCE_NAME
        header_before = tf.read_text(encoding="utf-8").split("\n")[0]
        rows_before = len(tf.read_text(encoding="utf-8").splitlines())
        ino_before = tf.stat().st_ino
        argv = ["--package", fx["pkg"], "--workflow", "demo-flow",
                "--catalog-root", fx["catalog"], "--bindings", fx["b_both"],
                "--milestone-id", "m1", "--root", "--json"]
        cp = _invoke(argv, env)
        tf_lines = tf.read_text(encoding="utf-8").splitlines()
        check("SC-1: a full-workflow add creates N seat folders with N "
              "seat.md and appends exactly N rows",
              cp.returncode == 0
              and json.loads(cp.stdout).get("taskforce_rows_appended") == 2
              and (pkg / "seats" / "alpha" / "seat.md").is_file()
              and (pkg / "seats" / "beta" / "seat.md").is_file()
              and len(tf_lines) == rows_before + 2,
              (cp.stdout + cp.stderr).strip()[:200])
        check("SC-10: the written header equals the read header exactly",
              tf_lines[0] == header_before, tf_lines[0])
        # SC-22 (task 08) — the registry splice KEEPS THE INODE. A single-file
        # bind mount attaches to a dentry, so an inode swap here is what gave a
        # live seat EROFS on its own `goal-writes` grant. Spelled as the raw
        # st_ino rather than "the writer used pwrite" so it stays a check on the
        # OBSERVABLE property, not on the implementation that provides it: any
        # future return to tmp+os.replace turns this row red.
        check("SC-22: the append rewrites taskforce.csv IN PLACE — same inode "
              "before and after, so a cage's single-file bind survives it",
              tf.stat().st_ino == ino_before,
              f"{ino_before} -> {tf.stat().st_ino}")
        rows = {r["seat"]: r for r in csv.DictReader(tf_lines)}
        afm = yaml.safe_load(_FM_RE.match(
            (pkg / "seats" / "alpha" / "seat.md")
            .read_text(encoding="utf-8")).group(1))
        check("rows: frozen `after` copy (alpha root '', beta 'alpha'), "
              "milestone m1, taskforce-id READ FROM THE FILE (tf-1)",
              rows["alpha"]["after"] == "" and rows["beta"]["after"] == "alpha"
              and rows["alpha"]["milestone-id"] == "m1"
              and rows["beta"]["milestone-id"] == "m1"
              and rows["alpha"]["taskforce-id"] == "tf-1"
              and rows["beta"]["taskforce-id"] == "tf-1",
              str({s: dict(r) for s, r in rows.items()})[:200])
        check("rows: the binding quadruple equals the DESCRIPTOR's — the "
              "equality check_bindings asserts",
              all(rows["alpha"][k] == str(afm.get(k, ""))
                  for k in ("harness", "model", "effort"))
              and rows["alpha"]["ctx-refresh"] == str(afm.get("ctx-refresh")),
              str(dict(rows["alpha"])))
        # SC-1's launch coupling, SEQUENCED — and the order is load-bearing in
        # BOTH directions. `alpha` is a root and admits now; `beta` names it in
        # `after`, so the launch-admission filter defers `beta` until `alpha`
        # has checked out `done`. Hoisting that check-out ahead of `alpha`'s own
        # dry-run does not repair the row — it classes `alpha` `finished` and
        # defers `alpha`'s arm instead. The dependent arm is kept (rather than
        # dropped to a root-only arm, which CP-6 already covers) because it is
        # the suite's ONLY exercise of the materialize -> launch coupling on a
        # NON-ROOT seat.
        #
        # ⚠ IDENTITY CORRECTED (task 7.738). Every `launch` arm below used to
        # claim `--as chief-of-staff`; that role is RETIRED and, at the time, was
        # removed from `coord.py#is_authorized_launcher` (since itself deleted whole,
        # along with every per-verb role predicate [T2-R10, D24, F-simplicity-7] —
        # `launch` carries no role gate at all anymore). `leader` is kept as the
        # claim here regardless, and `--as` on a DRY RUN is admitted (F17's entry
        # bound refuses an uncorroborated claim only on a non-dry run — see CP-6's
        # own note below). The claim stays because no role gate is what these
        # rows assert; they assert the materialize -> launch coupling.
        cpl = supervise(["--package", fx["pkg"], "--as", "leader",
                     "launch", "--dry-run", "--only", "alpha"])
        check("SC-1: supervise launch --dry-run --only alpha resolves "
              "a harness command (root seat, before its own check-out)",
              cpl.returncode == 0
              and "claude --model claude-opus-5" in cpl.stdout
              and "REFUSED" not in cpl.stdout,
              (cpl.stdout + cpl.stderr).strip()[:200])
        # SC-1 control (unmet-predecessor half): while the predecessor has NOT
        # checked out, the dependent seat is refused BY CLASS — the term that
        # makes the green arm below a coupling rather than a second root.
        cpu = supervise(["--package", fx["pkg"], "--as", "leader",
                     "launch", "--dry-run", "--only", "beta"])
        check("SC-1 control: with its predecessor not checked out, the "
              "dependent seat is DEFERRED with class unmet-predecessor",
              cpu.returncode != 0
              and "unmet-predecessor" in cpu.stderr
              and "{'seat': 'alpha', 'state': 'no-check-out'}" in cpu.stderr
              and "NO pane was opened." in cpu.stderr,
              (cpu.stdout + cpu.stderr).strip()[:200])
        # THEN the predecessor checks out `done` — read back from the surviving
        # artifact, never from checkout's own success line.
        coord(["--package", fx["pkg"], "--as", "alpha", "checkin", "alpha",
               "SC-1 fixture predecessor"])
        # D3: alpha's descriptor DECLARES `./alpha-notes.md` (io-spec
        # `## Outputs`), so its `done` check-out verifies it — produce it
        # first, which is the contract doing its job, not a workaround.
        (Path(fx["pkg"]) / "seats" / "alpha" / "alpha-notes.md").write_text(
            "SC-1 fixture notes\n", encoding="utf-8")
        coord(["--package", fx["pkg"], "--as", "alpha", "checkout"])
        # Read the ending back from THE ONE ENDING STORE, which is where
        # check-out has landed it since spec-state-store §4.1 Row A deleted the
        # second writer `coordination/awaiting-close.json`. Read DEFENSIVELY: an
        # unreachable store must RED this check, never raise out of the suite —
        # a check that aborts the run takes every row after it down with it and
        # reports nothing.
        landed = _chair_current_ending(pkg, "alpha")
        check("SC-1 setup: alpha's check-out lands ending `done` in the "
              "ending store",
              (landed or {}).get("ending") == "done",
              str(landed)[:200])
        cpl = supervise(["--package", fx["pkg"], "--as", "leader",
                     "launch", "--dry-run", "--only", "beta"])
        check("SC-1: supervise launch --dry-run --only beta resolves "
              "a harness command (dependent seat, predecessor done)",
              cpl.returncode == 0
              and "claude --model claude-opus-5" in cpl.stdout
              and "REFUSED" not in cpl.stdout,
              (cpl.stdout + cpl.stderr).strip()[:200])
        # SC-1 control (check_bindings half): a row that DISAGREES with the
        # descriptor refuses the same dry-run.
        text = tf.read_text(encoding="utf-8")
        mutated = text.replace("beta,alpha,claude,claude-opus-5",
                               "beta,alpha,claude,claude-opus-4")
        check("SC-1 control setup: the beta row mutation actually lands",
              mutated != text)
        tf.write_text(mutated, encoding="utf-8")
        cpl = supervise(["--package", fx["pkg"], "--as", "leader",
                     "launch", "--dry-run", "--only", "beta"])
        check("SC-1 control: a divergent registry row REFUSES the dry-run "
              "through check_bindings",
              cpl.returncode != 0
              and "fail the run's registry check" in cpl.stderr,
              (cpl.stdout + cpl.stderr).strip()[:200])
        # SC-1 control (no-registry-row half): DELETE the beta row.
        deleted = "\n".join(l for l in text.splitlines()
                            if not l.startswith("tf-1,beta")) + "\n"
        tf.write_text(deleted, encoding="utf-8")
        cpd = supervise(["--package", fx["pkg"], "descriptors"])
        check("SC-1 control: a deleted row is NAMED by the descriptor audit "
              "(no-registry-row) and the audit exits nonzero",
              cpd.returncode == 1 and "no-registry-row" in cpd.stdout
              and "beta" in cpd.stdout,
              (cpd.stdout + cpd.stderr).strip()[:200])
        cpl = supervise(["--package", fx["pkg"], "--as", "leader",
                     "launch", "--dry-run", "--only", "beta"])
        # MEASURED, not asserted as policy: check_bindings compares only rows
        # that EXIST, so launch --dry-run does NOT refuse a deleted row — the
        # deleted-row refusal lives in the descriptors audit above. Recorded
        # as a coupling gap in coord.py (read-only for dag-05).
        print(f"  info SC-1 measured: launch --dry-run with beta's row "
              f"DELETED exits {cpl.returncode} (check_bindings skips a "
              f"missing row; the naming surface is `descriptors`)")
        tf.write_text(text, encoding="utf-8")
        # SC-9: the SAME call twice — second refuses naming the path, and the
        # registry is byte-identical after the second call.
        bytes_after_first = tf.read_bytes()
        cp2 = _invoke(argv, env)
        check("SC-9: re-running on an existing seat refuses (exit 1) naming "
              "the existing path; registry byte-identical",
              cp2.returncode == 1
              and _refusal(cp2).get("code") == "seat-exists"
              and "seats/alpha" in _sep(_refusal(cp2).get("path") or "")
              and tf.read_bytes() == bytes_after_first,
              cp2.stdout.strip()[:200])
        # Topological order: scramble-flow's manifest lists b2 BEFORE its
        # root a2 — the appended rows must land a2 first anyway.
        cp = _invoke(["--package", fx["pkg"], "--workflow", "scramble-flow",
                      "--catalog-root", fx["catalog"], "--bindings",
                      fx["b_scramble"], "--root", "--json"], env)
        seats_col = [r["seat"] for r in csv.DictReader(
            tf.read_text(encoding="utf-8").splitlines())]
        check("topo: rows append in TOPOLOGICAL order of the added subgraph",
              cp.returncode == 0 and seats_col[-2:] == ["a2", "b2"],
              str(seats_col))
        check("topo control: the manifest resolves b2 FIRST — file order "
              "diverging from manifest order proves the sort acted",
              json.loads(cp.stdout).get("added_seats") == ["b2", "a2"],
              cp.stdout.strip()[:120])

    # ---- group 2: SC-5 (cycle), SC-6 (dangling member), SC-15 (target
    #      path bar) ----------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        fx = build_fixture(Path(td))
        pkg = Path(fx["pkg"])
        tf_before = (pkg / TASKFORCE_NAME).read_bytes()

        def wf_after(after, extra=()):
            return ["--package", fx["pkg"], "--workflow", "demo-flow",
                    "--catalog-root", fx["catalog"], "--bindings",
                    fx["b_both"], "--milestone-id", "m1", "--after", after,
                    "--json", *extra]

        cp = _invoke(wf_after("beta"), env)
        check("SC-5: --after naming a descendant of the added set is refused "
              "by check_acyclic — zero folders, zero rows",
              cp.returncode == 1
              and _refusal(cp).get("code") == "cycle-introduced"
              and "cycle" in _refusal(cp).get("message", "")
              and not any((pkg / "seats").iterdir())
              and (pkg / TASKFORCE_NAME).read_bytes() == tf_before,
              cp.stdout.strip()[:200])
        cp = _invoke(wf_after("chief"), env)
        check("SC-5/SC-6 control: the acyclic form with an existing --after "
              "member exits 0 and materializes",
              cp.returncode == 0
              and json.loads(cp.stdout).get("taskforce_rows_appended") == 2,
              (cp.stdout + cp.stderr).strip()[:200])
        cp = _invoke(["--package", fx["pkg9"], "--seat", "alpha",
                      "--catalog-root", fx["catalog"], "--after",
                      "nonexistent-seat", "--bindings", fx["b_alpha"],
                      "--dry-run", "--json"], env)
        check("SC-6: a dangling --after member is refused NAMING the member",
              cp.returncode == 1
              and _refusal(cp).get("code") == "after-unresolved"
              and "nonexistent-seat" in _refusal(cp).get("message", ""),
              cp.stdout.strip()[:200])
        mirror_pkg = Path(td) / "mirror" / "meta" / "planner-workflow"
        mirror_pkg.mkdir(parents=True)
        cp = _invoke(["--package", str(mirror_pkg), "--seat", "alpha",
                      "--catalog-root", fx["catalog"], "--root",
                      "--bindings", fx["b_alpha"], "--json"], env)
        check("SC-15: a catalog/mirror path is refused — the target is the "
              "goal folder, never the catalog (d-all-seats-in-run-folder)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "package-not-a-goal",
              cp.stdout.strip()[:200])
        cp = _invoke(["--package", fx["pkg_spine"], "--seat", "alpha",
                      "--catalog-root", fx["catalog"], "--after", "chief",
                      "--bindings", fx["b_alpha"], "--dry-run", "--json"], env)
        check("SC-15 control: a real goal package is accepted",
              cp.returncode == 0, (cp.stdout + cp.stderr).strip()[:200])

    # ---- group 3: SC-10 control (status column) + SC-21 (spine) --------
    with tempfile.TemporaryDirectory() as td:
        fx = build_fixture(Path(td))
        pkg_status = Path(fx["pkg_status"])
        tf_before = (pkg_status / TASKFORCE_NAME).read_bytes()
        cp = _invoke(["--package", fx["pkg_status"], "--workflow",
                      "demo-flow", "--catalog-root", fx["catalog"],
                      "--bindings", fx["b_both"], "--root", "--json"], env)
        check("SC-10 control: a registry whose header already carries "
              "`status` REFUSES rather than propagating it — pre-write, so "
              "zero folders and the file untouched",
              cp.returncode == 1
              and _refusal(cp).get("code") == "status-column"
              and not any((pkg_status / "seats").iterdir())
              and (pkg_status / TASKFORCE_NAME).read_bytes() == tf_before,
              cp.stdout.strip()[:200])
        spine = Path(fx["pkg_spine"])

        def spine_argv(mid, extra=()):
            return ["--package", fx["pkg_spine"], "--workflow", "demo-flow",
                    "--catalog-root", fx["catalog"], "--bindings",
                    fx["b_both"], "--root", "--milestone-id", mid,
                    "--json", *extra]

        cp = _invoke(spine_argv("bootstrap"), env)
        check("SC-21: --milestone-id bootstrap against the REPAIRED spine "
              "is refused (milestone-unresolved)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "milestone-unresolved"
              and "bootstrap" in _refusal(cp).get("message", ""),
              cp.stdout.strip()[:200])
        cp = _invoke(spine_argv("m4"), env)
        rows = {r["seat"]: r for r in csv.DictReader(
            (spine / TASKFORCE_NAME).read_text(encoding="utf-8").splitlines())}
        check("SC-21 control: --milestone-id m4 is accepted and the appended "
              "rows carry it",
              cp.returncode == 0
              and rows["alpha"]["milestone-id"] == "m4"
              and rows["beta"]["milestone-id"] == "m4",
              (cp.stdout + cp.stderr).strip()[:200])

    # ---- group 4: SC-8 (crash ordering, both arms) + SC-20 (force-partial
    #      completes ONLY the missing half, all red arms) — in-process ----
    class _Boom(Exception):
        pass

    def _crash(_plan):
        raise _Boom()

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        # 7.607 E2b: the package IS the goal folder, and the bar is positional
        # (`.../goals/<goal>`, the seat-folder.js grammar) — so the lint tree's
        # goals root is literally named `goals`, under its own parent so it
        # cannot collide with the shared fixture's.
        groot = tmp / "lint" / "goals"
        gdir = groot / "demo-goal"
        run1 = gdir
        (run1 / "seats").mkdir(parents=True)
        (run1 / "coordination").mkdir()
        (gdir / "goal.md").write_text(
            "---\nname: demo-goal\ncreation-date: 2026-07-29\n"
            "type: one-shot\nstatus: active\n---\n\nProve SC-8.\n",
            encoding="utf-8")
        (gdir / "decisions.md").write_text("# decisions\n", encoding="utf-8")
        (gdir / "threads.sql").write_text("-- threads\n", encoding="utf-8")
        (run1 / MILESTONES_NAME).write_text(
            "milestone-id,name,status\nm1,prove,pending\n", encoding="utf-8")
        seed_text = ("taskforce-id,seat,after,harness,model,effort,"
                     "ctx-refresh,milestone-id\n"
                     "tf-1,chief,,claude,claude-opus-5,high,,m1\n")
        (run1 / TASKFORCE_NAME).write_text(seed_text, encoding="utf-8")
        argv = ["--package", str(run1), "--workflow", "demo-flow",
                "--catalog-root", fx["catalog"], "--bindings", fx["b_both"],
                "--milestone-id", "m1", "--root"]
        args = build_parser().parse_args(argv)

        # SC-8 arm 2 FIRST: abort BEFORE step 1 — nothing on disk at all.
        pre = _hash_tree(run1)
        orig_emit = globals()["emit_seat_descriptors"]
        globals()["emit_seat_descriptors"] = _crash
        try:
            raised = False
            try:
                run(args)
            except _Boom:
                raised = True
        finally:
            globals()["emit_seat_descriptors"] = orig_emit
        check("SC-8 arm 2: an abort BEFORE step 1 leaves NOTHING on disk",
              raised and _hash_tree(run1) == pre)

        # SC-8 arm 1: abort AFTER step 1 (descriptors written, append never
        # ran) — orphan folders exist, ZERO rows appended.
        orig_append = globals()["append_taskforce_rows"]
        globals()["append_taskforce_rows"] = _crash
        try:
            raised = False
            try:
                run(args)
            except _Boom:
                raised = True
        finally:
            globals()["append_taskforce_rows"] = orig_append
        check("SC-8 arm 1: an abort between the steps leaves orphan seat "
              "folders and ZERO appended rows",
              raised
              and (run1 / "seats" / "alpha" / "seat.md").is_file()
              and (run1 / "seats" / "beta" / "seat.md").is_file()
              and (run1 / TASKFORCE_NAME).read_text(encoding="utf-8")
              == seed_text)
        from goal_cli import lint_goal
        f = lint_goal(groot, "demo-goal")
        lint_named = [i for i in f.items
                      if "alpha" in i["reason"] or "beta" in i["reason"]]
        # MEASURED GAP AS OF dag-05 (2026-07-29) AND SINCE CLOSED — scoped
        # historically rather than deleted, because the print below still
        # reports the count and a reader needs to know what it once meant.
        # It was measured BEFORE the 7.98 lint sweep landed: goal-lint then
        # iterated ROWS only, so an orphan FOLDER with no row was invisible to
        # it. 7.98 added the orphan-seat-folder walk (`goal_cli.py`, the
        # `orphan seat folder '<name>' — no taskforce.csv row names it`
        # finding, with its own red arm), so the gap no longer stands. The
        # surface asserted below is still coord.py's `descriptors` audit
        # (no-registry-row) — this arm's subject, deliberately unchanged.
        print(f"  info SC-8 measured: goal-lint findings naming the orphan "
              f"folders: {len(lint_named)} (rows-only walk — the naming "
              f"surface is coord.py `descriptors`)")
        cpd = supervise(["--package", str(run1), "descriptors"])
        check("SC-8: the orphan-folder half-state IS named — coord "
              "descriptors reports no-registry-row for both added seats",
              cpd.returncode == 1
              and cpd.stdout.count("no-registry-row") >= 2
              and "alpha" in cpd.stdout and "beta" in cpd.stdout,
              (cpd.stdout + cpd.stderr).strip()[:200])

        # SC-20: --force-partial completes ONLY the missing rows half —
        # descriptors untouched (hashed before/after), rows appended.
        pre_seats = _hash_tree(run1 / "seats")
        cp = _invoke([*argv, "--force-partial", "--json"], env)
        seats_now = [r["seat"] for r in csv.DictReader(
            (run1 / TASKFORCE_NAME).read_text(encoding="utf-8").splitlines())]
        check("SC-20: --force-partial appends the missing rows and touches "
              "no descriptor",
              cp.returncode == 0
              and json.loads(cp.stdout).get("taskforce_rows_appended") == 2
              and _hash_tree(run1 / "seats") == pre_seats
              and seats_now == ["chief", "alpha", "beta"],
              (cp.stdout + cp.stderr).strip()[:200])

        # SC-20 control: mutate one existing descriptor, re-create the
        # missing-rows state — the byte-for-byte assertion REFUSES.
        amd = run1 / "seats" / "alpha" / "seat.md"
        orig_alpha = amd.read_text(encoding="utf-8")
        (run1 / TASKFORCE_NAME).write_text(seed_text, encoding="utf-8")
        amd.write_text(orig_alpha + "\n<!-- drift -->\n", encoding="utf-8")
        cp = _invoke([*argv, "--force-partial", "--json"], env)
        check("SC-20 control: a mutated descriptor REFUSES --force-partial "
              "on the byte-for-byte assertion, appending nothing",
              cp.returncode == 1
              and _refusal(cp).get("code") == "partial-descriptor-mismatch"
              and (run1 / TASKFORCE_NAME).read_text(encoding="utf-8")
              == seed_text,
              cp.stdout.strip()[:200])

        # SC-20 rows-half red arm: an existing row that DIVERGES from what
        # this run would write refuses (partial-row-mismatch), file untouched.
        amd.write_text(orig_alpha, encoding="utf-8")
        drifted = seed_text + "tf-1,alpha,,claude,claude-opus-5,low,50,m1\n"
        (run1 / TASKFORCE_NAME).write_text(drifted, encoding="utf-8")
        cp = _invoke([*argv, "--force-partial", "--json"], env)
        check("SC-20 rows-half control: a divergent existing row REFUSES "
              "(partial-row-mismatch), file untouched",
              cp.returncode == 1
              and _refusal(cp).get("code") == "partial-row-mismatch"
              and (run1 / TASKFORCE_NAME).read_text(encoding="utf-8")
              == drifted,
              cp.stdout.strip()[:200])

        # Collision's registry half: a row with NO folder refuses
        # (registry-row-exists) without --force-partial.
        shutil.rmtree(run1 / "seats" / "alpha")
        shutil.rmtree(run1 / "seats" / "beta")
        cp = _invoke([*argv, "--json"], env)
        check("SC-9 registry half: an existing row with no folder refuses "
              "(registry-row-exists)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "registry-row-exists",
              cp.stdout.strip()[:200])


def run_dag06_acceptance(check, env: dict) -> None:
    """dag-06's CP rows (CP-1..CP-8), each with the control that must be able
    to FAIL. Fixture-only (tempfile.TemporaryDirectory) — never a real run.
    CP-6's launch coupling runs coord.py's OWN launch gates against a freshly
    CREATED throwaway package; the coord.py md5 under test is printed as
    evidence. The coord-visible created package is named run-1 — a tag held
    by a live run — so coord.py's auto-register declines (never stolen) and
    nothing durable is written."""
    import shutil

    def _refusal(cp):
        try:
            return json.loads(cp.stdout).get("refusal") or {}
        except ValueError:
            return {}

    # coord.py is `ignite/coord/`'s since the component-first move — a SIBLING
    # component of this one, no longer this file's own directory.
    coord_py = Path(__file__).resolve().parent.parent / "coord" / "coord.py"
    coord_md5 = hashlib.md5(coord_py.read_bytes()).hexdigest()
    print(f"  info CP-6: coord.py under test — md5 {coord_md5}")

    def coord(argv):
        return subprocess.run([sys.executable, str(coord_py), *argv],
                              capture_output=True, text=True, env=env)

    # ⚠ THE OTHER DOOR — see the same pair in the SC-1 suite above. `launch` and `descriptors`
    # left `coordinate` for `supervise` when the entry point split by audience (2026-08-25).
    supervise_py = coord_py.parent.parent / "supervisor" / "supervise.py"

    def supervise(argv):
        return subprocess.run([sys.executable, str(supervise_py), *argv],
                              capture_output=True, text=True, env=env)

    # ---- group 1: creation + launch coupling (CP-1/2/5/6/7/8) ----------
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        # The package IS the goal folder (7.607 E2b): scaffold's act is the
        # bare goal folder, and this command completes its WORKING surfaces.
        pkg = tmp / "g6" / "goals" / "g6-goal"
        pkg.mkdir(parents=True)

        def create_argv(seat, bindings, extra=()):
            return ["--package", str(pkg), "--seat", seat,
                    "--catalog-root", fx["catalog"], "--root",
                    "--bindings", bindings,
                    "--claude-md", fx["src_claude"],
                    "--budget-json", fx["src_budget"],
                    "--json", *extra]
        # CP-7: --dry-run against the UNCOMPLETED goal folder — plan printed,
        # nothing on disk.
        cp = _invoke(create_argv("alpha", fx["b_alpha"], ("--dry-run",)), env)
        plan_writes = (json.loads(cp.stdout)
                       if cp.returncode == 0 else {}).get("writes", [])
        planned = {w.get("surface") for w in plan_writes
                   if w["kind"] == "package-surface"}
        check("CP-7: dry-run against an uncompleted goal folder exits 0 and "
              "the printed plan names every created surface",
              cp.returncode == 0
              and {"CLAUDE.md", "budget.json",
                   TASKFORCE_NAME, STATE_CSV_NAME, "seats",
                   "coordination"} <= planned,
              (cp.stdout + cp.stderr).strip()[:200])
        check("CP-7: ...and writes NOTHING — not one working surface exists "
              "after the dry-run",
              list(pkg.iterdir()) == [])

        # CP-1 green: the same argv without --dry-run CREATES + materializes.
        cp = _invoke(create_argv("alpha", fx["b_alpha"]), env)
        created = json.loads(cp.stdout) if cp.returncode == 0 else {}
        surfaces = {w.get("surface") for w in created.get("writes", [])
                    if w["kind"] == "package-surface"}
        check("CP-1: a materialize against a goal folder with no working "
              "surfaces creates them and materializes into it, announcing "
              "every created surface in writes[]",
              cp.returncode == 0
              and (pkg / "seats" / "alpha" / "seat.md").is_file()
              and (pkg / "coordination").is_dir()
              and (pkg / TASKFORCE_NAME).is_file()
              and (pkg / STATE_CSV_NAME).is_file()
              and {"CLAUDE.md", "budget.json"} <= surfaces,
              (cp.stdout + cp.stderr).strip()[:200])
        check("CP-7 control: the dry flag is the discriminator — the same "
              "argv without it completed the package",
              (pkg / TASKFORCE_NAME).is_file())
        check("state.csv: the created cursor carries EXACTLY the ruled "
              "header, header only (KG `state-cursor` file-schema)",
              (pkg / STATE_CSV_NAME).read_text(encoding="utf-8")
              == STATE_CSV_HEADER + "\n")
        # The DIVERGENCE TRIPWIRE. Every other arm compares against the
        # constant, so all of them stay green while the constant drifts away
        # from the KG record — which is exactly how the 5-column form survived
        # `d-runs-extinguished-transcription`. This one pins the literal, so
        # editing the constant reddens the suite and sends the editor to the
        # acceptance note above it (which says: re-read the KG record first).
        check("state.csv: STATE_CSV_HEADER still equals the KG `state-cursor` "
              "column list — edit both or neither (see the acceptance note at "
              "the constant)",
              STATE_CSV_HEADER
              == "stamped-at,execution-stamp,goal-state,seat,session-id,note",
              STATE_CSV_HEADER)

        rows = list(csv.DictReader(
            (pkg / TASKFORCE_NAME).read_text(encoding="utf-8").splitlines()))
        check("tf-id: the first materialize into a completed package derives "
              "the id from the goal's OWN taskforce.csv counter (empty -> "
              "tf-1, design-lock item 10), never argv and never a folder name",
              [r["taskforce-id"] for r in rows] == ["tf-1"]
              and rows[0]["seat"] == "alpha", str(rows))

        # CP-1 control: the SAME call with the create step disabled refuses.
        pkg2 = tmp / "g6" / "goals" / "g6-goal-2"
        pkg2.mkdir(parents=True)
        args2 = build_parser().parse_args(
            [a if a != str(pkg) else str(pkg2)
             for a in create_argv("alpha", fx["b_alpha"])])
        orig_plan = globals()["plan_package_creation"]

        def _stub(package, args):
            raise Refuse("package-absent",
                         "create step disabled (CP-1 control)", str(package))

        globals()["plan_package_creation"] = _stub
        try:
            refused = False
            try:
                run(args2)
            except Refuse as r:
                refused = r.code == "package-absent"
        finally:
            globals()["plan_package_creation"] = orig_plan
        check("CP-1 control: the SAME call with the create step disabled "
              "refuses (package-absent) and creates nothing",
              refused and list(pkg2.iterdir()) == [])

        # CP-5: no policy number on the argument surface; the caller's
        # budget.json IS read and reaches the created package unchanged.
        numeric_defaults = [a.option_strings for a in build_parser()._actions
                            if isinstance(a.default, (int, float))
                            and not isinstance(a.default, bool)]
        check("CP-5: the argument surface carries NO numeric default — no "
              "floor, cap, or model number (R-10, r-floor-single-source)",
              numeric_defaults == [], str(numeric_defaults))
        probe = argparse.ArgumentParser()
        probe.add_argument("--mem-floor-mb", type=int, default=1200)
        check("CP-5 control: the numeric-default detector fires on a parser "
              "that DOES carry one",
              any(isinstance(a.default, (int, float))
                  and not isinstance(a.default, bool)
                  for a in probe._actions))
        src_budget = Path(fx["src_budget"]).read_bytes()
        made_budget = (pkg / "budget.json").read_bytes()
        check("CP-5 control: the caller-supplied budget.json IS read — the "
              "created copy is byte-identical and its floor (64) arrives "
              "unchanged",
              made_budget == src_budget
              and json.loads(made_budget)["floors"]["launch_refuse_mb"] == 64)
        check("CP-5 comparator control: the byte comparator can fail (a "
              "different source diverges)",
              Path(fx["src_claude"]).read_bytes() != made_budget)

        # CP-8 green: CLAUDE.md byte-identical to the source.
        check("CP-8: created CLAUDE.md is byte-identical to "
              "the caller-supplied base text",
              (pkg / "CLAUDE.md").read_bytes()
              == Path(fx["src_claude"]).read_bytes())

        # CP-2 arm 1: the IDENTICAL call again — collision refusal on the
        # materialize half, whole tree byte-identical (nothing recreated).
        tree_before = _hash_tree(pkg)
        cp = _invoke(create_argv("alpha", fx["b_alpha"]), env)
        check("CP-2: the identical call again creates and changes NOTHING "
              "(seat-exists refusal, tree byte-identical)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "seat-exists"
              and _hash_tree(pkg) == tree_before)
        # CP-2 arm 2: a DIFFERENT seat into the now-existing package — zero
        # creation entries, every created surface byte-identical.
        cp = _invoke(create_argv("b2", fx["b_b2"]), env)
        res = json.loads(cp.stdout) if cp.returncode == 0 else {}
        check("CP-2: a later materialize into the created package carries "
              "ZERO creation entries and leaves every created surface "
              "byte-identical",
              cp.returncode == 0
              and [w for w in res.get("writes", [])
                   if w["kind"] == "package-surface"] == []
              and (pkg / "CLAUDE.md").read_bytes()
              == Path(fx["src_claude"]).read_bytes()
              and (pkg / "budget.json").read_bytes() == src_budget
              and (pkg / STATE_CSV_NAME).read_text(encoding="utf-8")
              == STATE_CSV_HEADER + "\n",
              (cp.stdout + cp.stderr).strip()[:200])

        # CP-6: the created package is LAUNCHABLE.
        cpl = supervise(["--package", str(pkg), "--as", "leader",
                     "launch", "--dry-run", "--only", "alpha"])
        check("CP-6: supervise launch --dry-run --only alpha resolves a "
              "harness command against the freshly created package",
              cpl.returncode == 0
              and "claude --model claude-opus-5" in cpl.stdout
              and "REFUSED" not in cpl.stdout,
              (cpl.stdout + cpl.stderr).strip()[:200])
        # CP-6 green (real-launch form): with budget.json present the floor
        # gate PASSES reading the created file (provenance names 64) and the
        # launch fails only on the absent tmux pane — proving the FLOOR read
        # hits the created surface on the real path the control below flips.
        #
        # ⚠ ARGV CORRECTED (task 7.634). This pair used to pass
        # `--as chief-of-staff`, and was UNSATISFIABLE ON EVERY PLATFORM once
        # coord.py's F17 entry bound landed: `cmd_launch`'s FIRST statement
        # refuses an uncorroborated `--as` on any non-dry run, before it reads
        # the package at all — and corroboration needs a registered roster row
        # for a real tmux pane, which this hermetic suite can never have
        # (SCRUBBED_ENV_VARS strips TMUX/TMUX_PANE from every child). So the
        # arm was refused at the identity gate and never reached the floor
        # read it exists to prove. The identity claim was never load-bearing
        # for CP-6 — dropping it resolves 'no identity', and `--force` carries
        # the ROLE gate and, by its own refusal text, nothing else: the memory
        # gate still reads the created budget.json for real, and the launch
        # still dies at the absent-tmux-pane gate, which is exactly what this
        # row asserts. Gate verdicts print on stdout and the refusal on
        # stderr, so both arms read the COMBINED output.
        cpl = supervise(["--package", str(pkg),
                     "launch", "--only", "alpha", "--force"])
        check("CP-6: a REAL launch reads the created budget.json (floor "
              "provenance = 64) and refuses only for the absent tmux pane",
              cpl.returncode != 0
              and "floors.launch_refuse_mb = 64" in (cpl.stdout + cpl.stderr)
              and "not inside tmux" in (cpl.stdout + cpl.stderr),
              (cpl.stdout + cpl.stderr).strip()[:300])
        # CP-6 control: remove budget.json — the SAME real launch now
        # refuses for the undeclared floor. The surface list is load-bearing.
        (pkg / "budget.json").unlink()
        cpl = supervise(["--package", str(pkg),
                     "launch", "--only", "alpha", "--force"])
        check("CP-6 control: without budget.json the launch gate REFUSES "
              "for the undeclared floor (FloorUndeclared, "
              "r-floor-single-source)",
              cpl.returncode != 0
              and "no budget.json" in (cpl.stdout + cpl.stderr)
              and "r-floor-single-source" in (cpl.stdout + cpl.stderr)
              # the discriminator: the floor is NOT read, so the green arm's
              # provenance line is absent and the pane gate is never reached.
              and "floors.launch_refuse_mb = 64" not in (cpl.stdout + cpl.stderr),
              (cpl.stdout + cpl.stderr).strip()[:300])

    # ---- group 2: CP-3 completion, CP-4 bar, tf-id red arms, gated
    #      creation ------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        groot = tmp / "g6" / "goals"

        def mkgoal(name):
            """A scaffolded-but-uncompleted goal folder: what `rbtv-goal
            scaffold` leaves behind, and this command's only creatable state."""
            g = groot / name
            g.mkdir(parents=True)
            return g

        def argv_for(pkg, seat, bindings, extra=()):
            return ["--package", str(pkg), "--seat", seat,
                    "--catalog-root", fx["catalog"], "--root",
                    "--bindings", bindings,
                    "--claude-md", fx["src_claude"],
                    "--budget-json", fx["src_budget"],
                    "--json", *extra]

        # CP-4: a path that is not a goal folder refuses with NOTHING
        # created — completion never bypasses SC-15's bar.
        outside = tmp / "whatever"
        cp = _invoke(argv_for(outside, "alpha", fx["b_alpha"]), env)
        check("CP-4: --package <not under goals/> refuses "
              "(package-not-a-goal) and creates nothing on disk",
              cp.returncode == 1
              and _refusal(cp).get("code") == "package-not-a-goal"
              and not outside.exists())
        nogoal_pkg = groot / "never-scaffolded"
        cp = _invoke(argv_for(nogoal_pkg, "alpha", fx["b_alpha"]), env)
        check("CP-4: an ABSENT goal folder refuses (goal-folder-absent — "
              "goal creation is rbtv-goal's) and creates nothing",
              cp.returncode == 1
              and _refusal(cp).get("code") == "goal-folder-absent"
              and not nogoal_pkg.exists())
        # CP-4 control: a scaffolded, uncompleted goal folder IS completed.
        pkg9 = mkgoal("g6-goal-9")
        cp = _invoke(argv_for(pkg9, "alpha", fx["b_alpha"]), env)
        rows9 = (list(csv.DictReader((pkg9 / TASKFORCE_NAME).read_text(
            encoding="utf-8").splitlines()))
            if (pkg9 / TASKFORCE_NAME).is_file() else [])
        check("CP-4 control: a scaffolded goal folder IS completed and "
              "materialized",
              cp.returncode == 0
              and (pkg9 / "seats" / "alpha" / "seat.md").is_file())
        check("tf-id: an empty registry derives tf-1 from the COUNTER, and "
              "the goal folder's name contributes nothing to it",
              [r["taskforce-id"] for r in rows9] == ["tf-1"], str(rows9))

        # Completion is gated like every write: a later-gate refusal on an
        # uncompleted goal folder leaves NOTHING created.
        pkg5 = mkgoal("g6-goal-5")
        cp = _invoke(argv_for(pkg5, "beta", fx["b_alpha"]), env)
        check("gated creation: a bindings refusal against an uncompleted "
              "goal folder leaves nothing created (creation fires after "
              "every gate)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "bindings-missing-seat"
              and list(pkg5.iterdir()) == [])

        argv8 = argv_for(pkg5, "alpha", fx["b_alpha"])
        i = argv8.index("--budget-json")
        del argv8[i:i + 2]
        cp = _invoke(argv8, env)
        check("CP-6/CP-8 red: omitting the budget source REFUSES naming "
              "--budget-json — a floor is never defaulted (R-10)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "create-inputs-missing"
              and "--budget-json" in _refusal(cp).get("message", "")
              and list(pkg5.iterdir()) == [])
        argvb = argv_for(pkg5, "alpha", fx["b_alpha"])
        argvb[argvb.index("--budget-json") + 1] = fx["src_budget_broken"]
        cp = _invoke(argvb, env)
        check("budget-source red: a caller budget.json with no "
              "floors.launch_refuse_mb refuses at creation "
              "(create-input-invalid), before any write",
              cp.returncode == 1
              and _refusal(cp).get("code") == "create-input-invalid"
              and list(pkg5.iterdir()) == [])

        # CP-3: a partially-present package is COMPLETED, never refused.
        shutil.rmtree(pkg9 / "coordination")
        cp = _invoke(["--package", str(pkg9), "--seat", "b2",
                      "--catalog-root", fx["catalog"], "--root",
                      "--bindings", fx["b_b2"], "--json"], env)
        res = json.loads(cp.stdout) if cp.returncode == 0 else {}
        creations = [w.get("surface") for w in res.get("writes", [])
                     if w["kind"] == "package-surface"]
        check("CP-3: deleting coordination/ → the next run recreates ONLY "
              "that surface and names it in writes[]",
              cp.returncode == 0 and creations == ["coordination"]
              and (pkg9 / "coordination").is_dir(),
              (cp.stdout + cp.stderr).strip()[:200])
        # CP-3 control: delete nothing → zero creation entries.
        cp = _invoke(["--package", str(pkg9), "--seat", "beta",
                      "--catalog-root", fx["catalog"], "--root",
                      "--bindings", fx["b_beta"], "--json"], env)
        res = json.loads(cp.stdout) if cp.returncode == 0 else {}
        check("CP-3 control: with nothing deleted a run carries ZERO "
              "creation entries",
              cp.returncode == 0
              and [w for w in res.get("writes", [])
                   if w["kind"] == "package-surface"] == [],
              (cp.stdout + cp.stderr).strip()[:200])

        # CREATION-PARTIAL half-state: an existing dir WITHOUT taskforce.csv
        # re-requires the full input trio (closes the crash-then-flagless-
        # retry window), then completes.
        pkg6 = mkgoal("g6-goal-6")
        (pkg6 / "seats").mkdir(parents=True)
        cp = _invoke(["--package", str(pkg6), "--seat", "alpha",
                      "--catalog-root", fx["catalog"], "--root",
                      "--bindings", fx["b_alpha"], "--json"], env)
        check("creation-partial: an existing dir with NO taskforce.csv and "
              "no inputs refuses create-inputs-missing (a crashed creation "
              "is completed loudly, never tolerated)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "create-inputs-missing")
        cp = _invoke(argv_for(pkg6, "alpha", fx["b_alpha"]), env)
        check("creation-partial control: the same call WITH the inputs "
              "completes every missing surface and materializes",
              cp.returncode == 0
              and (pkg6 / "CLAUDE.md").is_file()
              and (pkg6 / "budget.json").is_file()
              and (pkg6 / TASKFORCE_NAME).is_file()
              and (pkg6 / STATE_CSV_NAME).is_file()
              and (pkg6 / "coordination").is_dir(),
              (cp.stdout + cp.stderr).strip()[:200])

        # tf-id red arm: rows that exist with NO readable id still refuse —
        # the derivation fires only on a zero-row registry.
        pkg7 = mkgoal("g6-goal-7")
        (pkg7 / "seats").mkdir(parents=True)
        (pkg7 / "coordination").mkdir()
        (pkg7 / TASKFORCE_NAME).write_text(
            ",".join(TASKFORCE_HEADER) + "\n"
            ",chief,,claude,claude-opus-5,high,,\n", encoding="utf-8")
        cp = _invoke(["--package", str(pkg7), "--seat", "alpha",
                      "--catalog-root", fx["catalog"], "--root",
                      "--bindings", fx["b_alpha"], "--json"], env)
        check("tf-id red: a registry WITH rows but no readable id refuses "
              "(taskforce-id-unreadable) — the counter derivation never "
              "papers over it",
              cp.returncode == 1
              and _refusal(cp).get("code") == "taskforce-id-unreadable")
        # tf-id file-wins arm: an id read from rows beats the derivation.
        (pkg7 / TASKFORCE_NAME).write_text(
            ",".join(TASKFORCE_HEADER) + "\n"
            "tf-1,chief,,claude,claude-opus-5,high,,\n", encoding="utf-8")
        cp = _invoke(["--package", str(pkg7), "--seat", "alpha",
                      "--catalog-root", fx["catalog"], "--root",
                      "--bindings", fx["b_alpha"], "--json"], env)
        rows7 = list(csv.DictReader((pkg7 / TASKFORCE_NAME).read_text(
            encoding="utf-8").splitlines()))
        check("tf-id: an id READ FROM THE FILE (tf-1) wins over the counter "
              "derivation — the appended row carries tf-1",
              cp.returncode == 0
              and [r["taskforce-id"] for r in rows7] == ["tf-1", "tf-1"],
              str(rows7))

        # ---- 7.569 the OPTIONAL addressable register ----------------------
        # RED FIRST, and it is free: every goal born above (pkg9, pkg6) was
        # born under a goals root with NO addressable door, and none of them
        # carries a register. That is the inert ship, not an omission.
        check("7.569 red: a goals root offering NO addressable door births a "
              "goal with NO register — the mechanism ships inert",
              not (pkg9 / ADDRESSABLE_NAME).exists()
              and not (pkg6 / ADDRESSABLE_NAME).exists())
        door = groot / "_channel-master"
        door.mkdir()
        (door / "seat.md").write_text(
            "---\nseat: channel-master\naddressable: non-member\n"
            "relays: master\n---\n\nthe standing owner door\n",
            encoding="utf-8")
        shut = groot / "_shut-door"
        shut.mkdir()
        (shut / "seat.md").write_text(
            "---\nseat: shut-door\n---\n\ndeclares nothing\n",
            encoding="utf-8")
        pkga = mkgoal("g6-goal-addr")
        cp = _invoke(argv_for(pkga, "alpha", fx["b_alpha"]), env)
        reg = (pkga / ADDRESSABLE_NAME)
        text = reg.read_text(encoding="utf-8") if reg.is_file() else ""
        check("7.569 green: with a door present the SAME call births the "
              "register, one row, a RELATIVE path resolving to the door's "
              "own seat.md (coord.load_addressable resolves it against the "
              "package)",
              cp.returncode == 0
              and text.splitlines() == [
                  ADDRESSABLE_HEADER,
                  "../_channel-master/seat.md,scaffold,at-run-creation"]
              and (pkga / "../_channel-master/seat.md").resolve()
              == (door / "seat.md").resolve(),
              text)
        check("7.569 two-sided: a standing-seat home that does NOT declare "
              "`addressable: non-member` in its own descriptor is NOT "
              "admitted — the scaffold grants nothing on its behalf",
              "_shut-door" not in text)
        check("7.569: the created register is announced in writes[] like "
              "every other created surface",
              ADDRESSABLE_NAME in [
                  w.get("surface") for w in
                  (json.loads(cp.stdout) if cp.returncode == 0 else {}
                   ).get("writes", []) if w["kind"] == "package-surface"],
              (cp.stdout + cp.stderr).strip()[:200])
        # Supplied wins over derived — and it is a byte-copy, like the trio.
        src_reg = tmp / "supplied-addressable.csv"
        src_reg.write_text(ADDRESSABLE_HEADER + "\n../elsewhere/seat.md,"
                           "owner,by-hand\n", encoding="utf-8")
        pkgs = mkgoal("g6-goal-addr-supplied")
        cp = _invoke(argv_for(pkgs, "alpha", fx["b_alpha"],
                              ("--addressable", str(src_reg))), env)
        check("7.569: --addressable BYTE-COPIES the caller's register and "
              "the derivation stands down",
              cp.returncode == 0
              and (pkgs / ADDRESSABLE_NAME).read_bytes()
              == src_reg.read_bytes())
        # Red arm on the optional input itself: supplied-but-unreadable is a
        # refusal, never a silent fall-back to the derivation.
        pkgu = mkgoal("g6-goal-addr-unreadable")
        cp = _invoke(argv_for(pkgu, "alpha", fx["b_alpha"],
                              ("--addressable", str(tmp / "nope.csv"))), env)
        check("7.569 red: --addressable naming an unreadable file REFUSES "
              "(create-input-unreadable) — never a silent fall-back to the "
              "derived register, and nothing is created",
              cp.returncode == 1
              and _refusal(cp).get("code") == "create-input-unreadable"
              and list(pkgu.iterdir()) == [])
        # A goal that already carries one is never touched.
        before = (pkga / ADDRESSABLE_NAME).read_bytes()
        cp = _invoke(argv_for(pkga, "beta", fx["b_beta"]), env)
        check("7.569: an existing register is never re-derived or "
              "overwritten on a later run",
              (pkga / ADDRESSABLE_NAME).read_bytes() == before)


# dag-07 — the per-ROW rollup table. Every acceptance row of the command
# (dag-03 SK-1..SK-7, dag-04+dag-05 SC-1..SC-21, dag-06 CP-1..CP-8, plus the
# named rows the same tasks landed) maps to the check labels carrying its arms:
#   green arm — the behaviour on conforming input;
#   red arm   — the case that MUST be able to fail (a refusal, a mutation, a
#               counter-case): R-6's proof the green is not vacuous.
# Patterns are substrings matched against EXECUTED check labels; a pattern
# matching nothing fails the row loudly (arm MISSING) — label drift breaks a
# row, it never silently narrows one. Alias rows re-report checks carried by
# another id so every spec id prints: SC-7=SK-1 (spec §1.8), SC-11=SK-4,
# SC-12=SK-5, AS-4=SK-4 (the suite-level junk-env form; its one-time
# whole-process evidence is in the dag-07 task return). A check may serve two
# rows (e.g. one green materialization grounds SC-8/SC-9's green arms) — the
# arms stay honest because each row's RED arm is its own.
ROW_ARMS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "SK-1": (("green: dry-run materializes the whole workflow plan",),
             ("SK-1 red",)),
    "SK-2": (("green: dry-run materializes one cataloged seat",),
             ("SK-2 red",)),
    "SK-3": (("green: dry-run materializes the whole workflow plan",),
             ("SK-3 red",)),
    "SK-4": (("SK-4: the whole suite is identical",), ("SK-4 control",)),
    "SK-5": (("SK-5: the only writes", "SK-5: the dry-run plan's writes[]"),
             ("SK-5 control: the hash detector goes red",)),
    "SK-6": (("SK-6 control",), ("SK-6 machine-readable refusal",)),
    "SK-7": (("SK-7: no local unit emitter",
              "SK-7: assemble_seat is imported"), ("SK-7 control",)),
    "SC-1": (("SC-1: a full-workflow add creates",
              "SC-1: supervise launch --dry-run --only"),
             ("SC-1 control: a divergent registry row",
              "SC-1 control: a deleted row",
              "SC-1 control: with its predecessor not checked out")),
    "SC-2": (("SC-2: descriptor carries seat:",), ("SC-2 red",)),
    "SC-3": (("green: a non-dry run emits descriptors",),
             ("SC-3: a catalog assembling an empty body",)),
    "SC-4": (("SC-4 control",),
             ("SC-4: a seat with no resolvable permissions",)),
    "SC-5": (("SC-5/SC-6 control",),
             ("SC-5: --after naming a descendant",)),
    "SC-6": (("SC-5/SC-6 control",),
             ("SC-6: a dangling --after member",)),
    "SC-7": (("green: dry-run materializes the whole workflow plan",),
             ("SK-1 red",)),
    "SC-8": (("SC-1: a full-workflow add creates",),
             ("SC-8 arm 2", "SC-8 arm 1",
              "SC-8: the orphan-folder half-state")),
    "SC-9": (("SC-1: a full-workflow add creates",),
             ("SC-9: re-running on an existing seat",
              "SC-9 registry half")),
    "SC-10": (("SC-10: the written header equals",), ("SC-10 control",)),
    "SC-11": (("SK-4: the whole suite is identical",), ("SK-4 control",)),
    "SC-12": (("SK-5: the only writes",
               "SK-5: the dry-run plan's writes[]"),
              ("SK-5 control: the hash detector goes red",)),
    "SC-13": (("SC-13 control",), ("SC-13: ONE bad model slug",)),
    "SC-14": (("SC-14 (first arm)", "SC-14: opencode default",
               "SC-14 control"),
              ("SC-14: mode: one-shot with ctx-refresh refuses",)),
    "SC-15": (("SC-15 control",),
              ("SC-15: a catalog/mirror path is refused",)),
    "SC-16": (("SC-16: a cheap one-shot worker",), ("SC-16 control",)),
    "SC-17": (("SC-17 control",), ("SC-17: class: is refused",)),
    # d-agent-type-widened-to-the-kg-top-set — the widening's permanent guard.
    # Green: master accepted + emitted, verifier accepted. Red: an invalid
    # value refused naming all four, an absent one refused.
    "agent-type": (("agent-type: agent_type: master is ACCEPTED",
                    "agent-type: agent_type: verifier is ACCEPTED"),
                   ("agent-type red: an invalid agent_type",
                    "agent-type red: an ABSENT agent_type")),
    # 7.104 — the pass-through row (d-relays-frontmatter-passthrough). Its
    # red arm is the counter-case: no declaration -> no key.
    "relays": (("relays: a declared relays: passes THROUGH",),
               ("relays counter-case",)),
    "SC-18": (("SC-18: every emitted frontmatter parses",), ("SC-18 red",)),
    "SC-19": (("SC-19: a window: value prints",), ("SC-19 control",)),
    "SC-20": (("SC-20: inline Reference resolved",
               "SC-20: --force-partial appends"),
              ("SC-20 red", "SC-20 control: a mutated descriptor",
               "SC-20 rows-half control")),
    "SC-21": (("SC-21 control",), ("SC-21: --milestone-id bootstrap",)),
    "CP-1": (("CP-1: a materialize against a goal folder",),
             ("CP-1 control",)),
    "CP-2": (("CP-2: a later materialize",),
             ("CP-2: the identical call again",)),
    "CP-3": (("CP-3: deleting coordination/",), ("CP-3 control",)),
    "CP-4": (("CP-4 control",),
             ("CP-4: --package <not under goals/>",
              "CP-4: an ABSENT goal folder")),
    "CP-5": (("CP-5: the argument surface carries NO numeric default",
              "CP-5 control: the caller-supplied budget.json IS read"),
             ("CP-5 control: the numeric-default detector fires",
              "CP-5 comparator control")),
    "CP-6": (("CP-6: supervise launch --dry-run --only alpha resolves",
              "CP-6: a REAL launch reads the created budget.json"),
             ("CP-6 control: without budget.json", "CP-6/CP-8 red")),
    "CP-7": (("CP-7: dry-run against an uncompleted goal folder exits 0",
              "CP-7: ...and writes NOTHING"), ("CP-7 control",)),
    "CP-8": (("CP-8: created CLAUDE.md",),
             ("CP-6/CP-8 red",)),
    "contract-order": (("contract §1: blocks in the FIXED kind order",),
                       ("reorder red",)),
    "topo-order": (("topo: rows append in TOPOLOGICAL order",),
                   ("topo control",)),
    "tf-id": (("tf-id: the first materialize",
               "tf-id: an id READ FROM THE FILE",
               "tf-id: the run-9 compartment derives tf-9"),
              ("tf-id red",)),
    "creation-partial": (("creation-partial control",),
                         ("creation-partial: an existing dir with NO "
                          "taskforce.csv",)),
    "AS-2": (("AS-2 green",), ("AS-2 control",)),
    "AS-4": (("SK-4: the whole suite is identical",), ("SK-4 control",)),
    # The plugin/MCP registration row (d-mcp-registration-is-config).
    "MCP-1": (("MCP-1 green",), ("MCP-1 red",)),
    "EXP-1": (("EXP-1 green",), ("EXP-1 red",)),
    # The --refresh update mode (derived surfaces only; standing-seat home).
    "RF-1": (("RF-1 green",), ("RF-1 red",)),
    # D50 — the master-prompt access-wide/file-don't-fix sentence replaces
    # D49's retired execute/write phrasing, pinned on every --refresh.
    "D50": (("D50 green",), ("D50 red",)),
    # The seat-cage declaration (owner-ruled 2026-08-10).
    "CG-1": (("CG-1 green",), ("CG-1 red",)),
    # The derived write surface (D3: goal folder RW).
    "CG-2": (("CG-2 green",), ("CG-2 red",)),
    # The UNCAGED branch of that section (B15; OQ-1a/OQ-2a/F-129 — all three
    # staff roles ratified uncaged).
    "CG-3": (("CG-3 green",), ("CG-3 red",)),
    # The pass-folder substitution rows (B4, B5, G-planner-0804-1502).
    "PF-1": (("PF-1 green",), ("PF-1 red",)),
    "PF-2": (("PF-2 green",), ("PF-2 red",)),
    "PF-3": (("PF-3 green",), ("PF-3 red",)),
    # The pass folder's m{N} row-check (task 7.678).
    "PF-4": (("PF-4 green",), ("PF-4 red",)),
    # The nested-workflow materialization path (task 7.615).
    "NEST-1": (("NEST-1 green", "NEST-1: the frozen-cell rename"),
               ("NEST-1 red",)),
    # The SINGLE-SEAT nested variant — W7's collapsed planning mode.
    "NEST-2": (("NEST-2 green",), ("NEST-2 red",)),
    # Completing an EXISTING instance-named row — the daemon's unbuilt-seat
    # repair lane, which `--nested` (which mints the NEXT ordinal) cannot serve.
    "INST-1": (("INST-1 green",), ("INST-1 red",)),
    # The goal-local seat input lane and the checks component-lint never makes.
    "GL-1": (("GL-1 green",), ("GL-1 red",)),
    # The staff chairs minted with the goal (W3) — ONE row over SM-1..SM-5:
    # the four green arms are one behaviour observed at four moments (mint,
    # backfill, re-run, self-materialize), and SM-5 is its only red.
    "staff-mint": (("SM-1 green", "SM-2 green", "SM-3 green", "SM-4 green"),
                   ("SM-5 red",)),
    # The multi-taskforce answer (`d-staff-chair-joins-first-taskforce`) — its
    # OWN row, not more arms on `staff-mint`: SM-1..SM-5 are all measured on a
    # single-taskforce registry and that premise is unchanged, while these two
    # are a matched pair (the chair passes / the ordinary seat still refuses) on
    # a registry no other arm builds. A row that passes only when BOTH fire is
    # exactly the shape the lift needs — widen the gate and the red goes.
    "staff-mint-multi-tf": (("SM-6 green", "SM-13 green"), ("SM-7 red",)),
    # The STANDING-ENDING gate (task 05 defect B) — its own row for the same
    # reason the multi-tf pair is: it is measured on a goal no other arm builds
    # (one already carrying a current ending under a chair's name), and it
    # passes only when BOTH sides fire — the ending blocks BOTH chair classes,
    # and an empty store still mints. Widen the gate and the control alone
    # would keep it green. The row name predates spec-state-store §4.1, which
    # replaced the debt ledger it was named for; it is left alone because the
    # name is a rollup key readers already know, not a claim about a surface.
    "staff-mint-debt": (("SM-12 control",),
                        ("SM-10 red", "SM-10b red", "SM-11 red")),
    # D79 — auto-mint of SUMMONED chairs at materialize. Own row: SM-1..SM-5
    # stay the staff-chair contract (SM-1's added_seats==[["leader"]] is
    # unchanged because summoned lands in result['summoned'], not staff).
    "staff-mint-summoned": (("SM-14 green",), ("SM-15 red",)),
}


def rollup_rows(records: list[tuple[str, bool]]
                ) -> tuple[list[str], dict[str, str]]:
    """dag-07 — fold the executed checks into ONE verdict line per acceptance
    row: id, verdict, and on failure WHICH ARM failed (green or red) and how
    (a matched check failed vs no check matched at all). A row passes ONLY
    when both arms matched at least one check and every matched check passed
    — a green-only row is a failure, never a pass (AS-2)."""
    lines: list[str] = []
    failing: dict[str, str] = {}
    for row, (green, red) in ROW_ARMS.items():
        parts: list[str] = []
        bad: list[str] = []
        for arm, pats in (("green", green), ("red", red)):
            hits = [ok for label, ok in records
                    if any(p in label for p in pats)]
            if not hits:
                parts.append(f"{arm} MISSING")
                bad.append(f"{arm} arm: no check matched")
            else:
                parts.append(f"{arm} {sum(hits)}/{len(hits)}")
                if not all(hits):
                    bad.append(f"{arm} arm: "
                               f"{len(hits) - sum(hits)} check(s) failed")
        verdict = "PASS" if not bad else "FAIL"
        lines.append(f"  row {row:<16} {verdict}  " + "  ".join(parts)
                     + (f"  <- {'; '.join(bad)}" if bad else ""))
        if bad:
            failing[row] = "; ".join(bad)
    return lines, failing


def _pf_fixture(root: Path) -> dict:
    """A hermetic catalog + package for the pass-folder rows. Its OWN tmp tree,
    deliberately outside the shared fixture's: SK-5 hashes that one and asserts
    the exact disk delta, and PF-3's green arm legitimately REPLACES a file."""
    comp = root / "catalog" / "pf-comp"

    def unit(rel: str, uid: str, body: str) -> None:
        p = comp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\nid: {uid}\ndescription: {uid}\n---\n\n{body}\n",
                     encoding="utf-8")

    # The one unit that NAMES a pass surface — every placeholder spelling.
    unit("prompts/cognitive-units/roles/pf-role.md", "pf-role",
         "<role>\nYou are the pass seat.\n</role>")
    unit("prompts/cognitive-units/permissions/pf-permissions.md",
         "pf-permissions", "<permissions>\nWrite your own outputs.\n"
                           "</permissions>")
    unit("prompts/cognitive-units/procedures/pf-procedure.md", "pf-procedure",
         "<procedure>\nWrite `planning/m{N}-{milestone-name}/brief.md` and "
         "the manifest `manifest-m{N}.csv`.\nRead "
         "`planning/<pass-folder>/spine.md`.\n</procedure>")
    unit("tasks/cognitive-units/task-goals/pf-goal.md", "pf-goal",
         "<task-goal>\nProve the substitution.\n</task-goal>")
    unit("tasks/cognitive-units/scopes/pf-scope.md", "pf-scope",
         "<scope>\nThe fixture tree.\n</scope>")
    unit("tasks/cognitive-units/done-contracts/pf-done.md", "pf-done",
         "<done-contract>\nThe brief exists.\n</done-contract>")
    comp.joinpath("prompts.csv").write_text(
        "prompt-id,role,permissions,procedure,description\n"
        "pf-prompt,pf-role,pf-permissions,pf-procedure,pf prompt\n",
        encoding="utf-8")
    comp.joinpath("tasks.csv").write_text(
        "task-id,task goal,scope,done contract,description\n"
        "pf-task,pf-goal,pf-scope,pf-done,pf task\n", encoding="utf-8")
    comp.joinpath("seats.csv").write_text(
        "seat-id,executor,task,staffing-hints,description\n"
        "pf,pf-prompt,pf-task,,the pass seat\n", encoding="utf-8")

    pkg = root / "goals" / "pf-goal"
    (pkg / "seats").mkdir(parents=True)
    (pkg / "coordination").mkdir()
    (pkg / TASKFORCE_NAME).write_text(",".join(TASKFORCE_HEADER) + "\n",
                                      encoding="utf-8")
    (pkg / STATE_CSV_NAME).write_text(STATE_CSV_HEADER + "\n",
                                      encoding="utf-8")
    (pkg / "conduct.md").write_text("conduct\n", encoding="utf-8")
    (pkg / "CLAUDE.md").write_text("claude\n", encoding="utf-8")
    (pkg / "budget.json").write_text(
        json.dumps({"floors": {"context-floor-pct": 20}}), encoding="utf-8")
    (pkg / PASSES_NAME).write_text(
        "pass-id,clause-tag,declared-budget,opened,closed,outcome\n"
        "m1-first-milestone,PRODUCT,seats=1;rounds=1,2026-01-01 00:00,,\n"
        "m0-bootstrapping,PRODUCT,seats=1;rounds=1,2026-01-01 00:00,,\n"
        "m9-unbacked-milestone,PRODUCT,seats=1;rounds=1,2026-01-01 00:00,,\n"
        "briefing-a-briefing,META,seats=1;rounds=1,2026-01-02 00:00,,\n"
        "briefing-closed-one,META,seats=1;rounds=1,2026-01-01 00:00,"
        "2026-01-01 12:00,ACCEPTED\n", encoding="utf-8")
    # PF-4's substrate: the milestone ROWS. `m9-unbacked-milestone` is a
    # deliberately OPEN pass with NO row here, so PF-4's red arm can only be
    # the milestone guard — never pass-not-open wearing its coat.
    (pkg / MILESTONES_NAME).write_text(
        "milestone-id,name,status\n"
        "m0,planning,open\n"
        "m1,first milestone,pending\n", encoding="utf-8")

    bdir = root / "bindings"
    bdir.mkdir()
    base = {"agent_type": "worker", "harness": "claude",
            "model": "claude-opus-5", "effort": "high", "mode": "interactive"}
    paths = {}
    for name, pf_value in (("ms", "planning/m1-first-milestone/"),
                           ("br", "planning/briefing-a-briefing/"),
                           ("none", PASS_FOLDER_NONE),
                           ("bad", "planning/a-briefing/"),
                           ("closed", "planning/briefing-closed-one/"),
                           ("m0", "planning/m0-bootstrapping/"),
                           ("m9", "planning/m9-unbacked-milestone/"),
                           ("absent", None)):
        entry = dict(base)
        if pf_value is not None:
            entry["pass-folder"] = pf_value
        p = bdir / f"{name}.json"
        p.write_text(json.dumps({"defaults": {"cwd-mode": "seat-folder"},
                                 "seats": {"pf": entry}}), encoding="utf-8")
        paths[name] = str(p)
    return {"catalog": str(root / "catalog"), "pkg": pkg, "b": paths}


def _staff_fixture(root: Path) -> dict:
    """A hermetic WORKSPACE — mirror catalog, `.rbtv/config` tree and goal
    package — for the staff-chair rows (SM-1..SM-5). Its own tmp tree for the
    same reason `_pf_fixture` has one, plus a second: the shared fixture's
    catalog carries no staff seat, and adding one there would change the write
    set of every other arm in the suite.

    The layout is the LIVE one, not a convenient one: the catalog sits at
    `<ws>/.rbtv/mirror/<module>/<component>` and the casting sheets at
    `<ws>/.rbtv/config/modules/<module>/<component>/bindings/<seat>.json`,
    because the address under test is DERIVED from the catalog row's own home
    (`staff_sheet_path`) and a flat fixture would prove nothing about it."""
    ws = root / "ws"
    comp = ws / ".rbtv" / "mirror" / "meta" / "staff-comp"

    def unit(rel: str, uid: str, body: str) -> None:
        p = comp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\nid: {uid}\ndescription: {uid}\n---\n\n{body}\n",
                     encoding="utf-8")

    unit("prompts/cognitive-units/roles/sm-role.md", "sm-role",
         "<role>\nYou are the fixture seat.\n</role>")
    unit("prompts/cognitive-units/permissions/sm-permissions.md",
         "sm-permissions", "<permissions>\nWrite your own outputs.\n"
                           "</permissions>")
    unit("prompts/cognitive-units/procedures/sm-procedure.md", "sm-procedure",
         "<procedure>\nDo the fixture work.\n</procedure>")
    unit("tasks/cognitive-units/task-goals/sm-goal.md", "sm-goal",
         "<task-goal>\nProve the mint.\n</task-goal>")
    unit("tasks/cognitive-units/scopes/sm-scope.md", "sm-scope",
         "<scope>\nThe fixture tree.\n</scope>")
    unit("tasks/cognitive-units/done-contracts/sm-done.md", "sm-done",
         "<done-contract>\nThe outputs exist.\n</done-contract>")
    comp.joinpath("prompts.csv").write_text(
        "prompt-id,role,permissions,procedure,description\n"
        "sm-prompt,sm-role,sm-permissions,sm-procedure,sm prompt\n",
        encoding="utf-8")
    comp.joinpath("tasks.csv").write_text(
        "task-id,task goal,scope,done contract,description\n"
        "sm-task,sm-goal,sm-scope,sm-done,sm task\n", encoding="utf-8")
    # The staff chair is an ORDINARY catalog row — nothing about the row shape
    # marks it, which is the point: `coord.STAFF_SEATS` is the one vocabulary.
    comp.joinpath("seats.csv").write_text(
        "seat-id,executor,task,staffing-hints,description\n"
        "w1,sm-prompt,sm-task,,the fixture worker\n"
        "w2,sm-prompt,sm-task,,the second fixture worker\n"
        "leader,sm-prompt,sm-task,,the fixture goal's unblocker\n"
        "goal-master,sm-prompt,sm-task,,the fixture summoned seat\n",
        encoding="utf-8")
    wf_dir = comp / "workflows" / "sm-flow"
    wf_dir.mkdir(parents=True)
    wf_dir.joinpath("sm-flow.csv").write_text(
        "Seat/workflow,after,i/o,Modality\n"
        "w1,,,agentic\n", encoding="utf-8")
    wf_dir.joinpath("workflow.md").write_text(
        "---\nid: sm-flow\nfour-letters: smfl\n---\n\nThe staff-mint fixture flow.\n",
        encoding="utf-8")

    (ws / ".rbtv" / "config").mkdir(parents=True)
    sheets = ws / ".rbtv/config/modules/meta/staff-comp/bindings"
    sheets.mkdir(parents=True)
    base = {"agent_type": "worker", "harness": "claude",
            "model": "claude-opus-5", "effort": "high", "mode": "interactive"}
    leader_sheet = sheets / "leader.json"
    leader_sheet.write_text(json.dumps(
        {"defaults": {"cwd-mode": "seat-folder"},
         "seats": {"leader": dict(base, agent_type="staff")}}),
        encoding="utf-8")
    goal_master_sheet = sheets / "goal-master.json"
    goal_master_sheet.write_text(json.dumps(
        {"defaults": {"cwd-mode": "seat-folder"},
         "seats": {"goal-master": dict(base, agent_type="master")}}),
        encoding="utf-8")
    worker_sheets = {}
    for seat in ("w1", "w2"):
        p = root / f"{seat}.json"
        p.write_text(json.dumps({"defaults": {"cwd-mode": "seat-folder"},
                                 "seats": {seat: dict(base)}}),
                     encoding="utf-8")
        worker_sheets[seat] = str(p)

    pkg = ws / ".rbtv" / GOALS_DIR_NAME / "sm-goal"
    (pkg / "seats").mkdir(parents=True)
    (pkg / "coordination").mkdir()
    (pkg / TASKFORCE_NAME).write_text(",".join(TASKFORCE_HEADER) + "\n",
                                      encoding="utf-8")
    (pkg / STATE_CSV_NAME).write_text(STATE_CSV_HEADER + "\n",
                                      encoding="utf-8")
    (pkg / "conduct.md").write_text("conduct\n", encoding="utf-8")
    (pkg / "CLAUDE.md").write_text("claude\n", encoding="utf-8")
    (pkg / "budget.json").write_text(
        json.dumps({"floors": {"context-floor-pct": 20}}), encoding="utf-8")
    return {"catalog": str(ws / ".rbtv" / "mirror" / "meta"), "pkg": pkg,
            "b": worker_sheets, "leader_sheet": leader_sheet,
            "goal_master_sheet": goal_master_sheet}


def _staff_run(fx: dict, seat: str, **over):
    """One in-process materialize against the staff fixture; the result dict,
    or the Refuse it raised."""
    args = argparse.Namespace(
        package=str(fx["pkg"]), seat=seat, workflow=None,
        catalog_root=fx["catalog"], after=None, root=True,
        bindings=fx["b"].get(seat), milestone_id=None,
        claude_md=None, budget_json=None, dry_run=False,
        as_json=False, force_partial=False, repass=False)
    for k, v in over.items():
        setattr(args, k, v)
    try:
        return run(args)
    except Refuse as r:
        return r


def _staff_rows(fx: dict) -> list[dict]:
    return _csv_rows(fx["pkg"] / TASKFORCE_NAME)


def run_staff_mint_acceptance(check) -> None:
    """SM-1..SM-9 — the staff chairs are minted WITH the goal (W3); SM-6/SM-7 add
    the multi-taskforce answer; SM-8/SM-9 the pure-completion id read (W7) (`d-staff-chair-joins-first-taskforce`).

    The defect these guard is the one the whole silent-stall program exists
    for: a routed FAIL, a mid-run ask and the session-closer's staff mail all
    resolve to `leader`, and on the incident goal that name had NO ROW. The
    arms are written against the ROW — not against a helper's return value —
    because the row is what `ready-seats` reads and what the daemon spawns."""
    root = Path(tempfile.mkdtemp(prefix="ms-sm-"))
    try:
        fx = _staff_fixture(root)

        # ---- SM-1: the mint itself, on an ordinary materialize.
        res = _staff_run(fx, "w1")
        rows = {r["seat"]: r for r in _staff_rows(fx)}
        check("SM-1 green: an ordinary --root materialize ALSO mints the "
              "`leader` chair — the row exists without anyone naming it",
              not isinstance(res, Refuse) and "leader" in rows,
              str(res)[:200] or str(list(rows)))
        check("SM-1 green: the chair carries an EMPTY after cell and the "
              "goal's OWN taskforce-id — it holds no workflow node and is "
              "not a second taskforce",
              rows.get("leader", {}).get("after", "x") == ""
              and rows.get("leader", {}).get("taskforce-id")
              == rows.get("w1", {}).get("taskforce-id"),
              str(rows.get("leader")))
        check("SM-1 green: the chair is a materialized SEAT, not a bare row — "
              "its descriptor is on disk",
              (fx["pkg"] / "seats" / "leader" / "seat.md").is_file(),
              str(fx["pkg"] / "seats" / "leader"))
        check("SM-1 green: the mint is DISCLOSED in the result the caller "
              "reads, never a silent extra row",
              [s["added_seats"] for s in (res or {}).get("staff", ())]
              == [["leader"]], str((res or {}).get("staff")))

        # ---- SM-2 (adv, C35): the BACKFILL, and the one thing an
        # inject-into-`added` implementation gets wrong. A chair minted beside
        # a seat that carries `--after` must NOT inherit that edge: the added
        # subgraph's roots all take the --after cell verbatim (Rule 13), and a
        # chair that waits on a workflow node is a chair that cannot be woken
        # until that node completes — precisely when it is needed least.
        rows_before = [r for r in _staff_rows(fx) if r["seat"] != "leader"]
        (fx["pkg"] / TASKFORCE_NAME).write_text(
            ",".join(TASKFORCE_HEADER) + "\n"
            + "".join(_render_csv_line([r[c] for c in TASKFORCE_HEADER]) + "\n"
                      for r in rows_before), encoding="utf-8")
        # `ignore_errors` so a suite run whose mint is BROKEN reports reds
        # rather than exploding in the fixture teardown — a harness that
        # crashes on the failing path hides the arms behind it.
        shutil.rmtree(fx["pkg"] / "seats" / "leader", ignore_errors=True)
        _staff_run(fx, "w2", root=False, after="w1")
        rows = {r["seat"]: r for r in _staff_rows(fx)}
        check("SM-2 green (C35 backfill): a materialize into an ALREADY-"
              "populated registry with no chair mints one — the chair reaches "
              "goals that were materialized before it existed",
              "leader" in rows, str(list(rows)))
        check("SM-2 green: the backfilled chair's after cell is EMPTY, never "
              "the --after set the run was given",
              rows.get("leader", {}).get("after", "x") == ""
              and rows.get("w2", {}).get("after") == "w1",
              str(rows.get("leader")) + str(rows.get("w2")))

        # ---- SM-3: idempotent. A goal's chair is minted ONCE.
        res = _staff_run(fx, "w1", force_partial=True)
        seats = [r["seat"] for r in _staff_rows(fx)]
        check("SM-3 green: a later materialize does NOT re-mint — exactly one "
              "`leader` row survives N materializes",
              seats.count("leader") == 1 and "staff" not in (res or {}),
              str(seats))

        # ---- SM-4: the recursion bound, stated as behaviour.
        res = _staff_run(fx, "leader", bindings=str(fx["leader_sheet"]),
                         force_partial=True)
        check("SM-4 green: materializing the chair ITSELF does not recurse — "
              "the run returns and no second row appears",
              not isinstance(res, Refuse)
              and [r["seat"] for r in _staff_rows(fx)].count("leader") == 1,
              str(res)[:200])

        # ---- SM-5 RED: no casting sheet, no chair — and it is LOUD. This is
        # the arm that fails if the skip ever becomes silent; a chair that
        # vanishes without a word is the failure mode this whole package
        # exists to end.
        fx2 = _staff_fixture(Path(tempfile.mkdtemp(prefix="ms-sm2-")))
        fx2["leader_sheet"].unlink()
        res = _staff_run(fx2, "w1")
        warned = [w for w in (res or {}).get("warnings", ())
                  if "leader" in w and "casting sheet" in w]
        check("SM-5 red: an UNCAST chair is not minted, the goal still "
              "materializes, and the result carries a warning naming the "
              "sheet path the workspace lacks",
              not isinstance(res, Refuse)
              and "leader" not in [r["seat"] for r in _staff_rows(fx2)]
              and len(warned) == 1
              and str(fx2["leader_sheet"]) in warned[0],
              str((res or {}).get("warnings"))[:300])
        shutil.rmtree(fx2["pkg"].parents[2].parent, ignore_errors=True)

        # ---- SM-6/SM-7: the MULTI-TASKFORCE goal
        # (`d-staff-chair-joins-first-taskforce`). The flagship
        # `meet-transcript-summarizer` carries tf-1 (the planning wave) and tf-2
        # (the m1 seam), and the id gate refused its chair on the FILE'S state
        # before any value was chosen — so the one goal the staff pass was built
        # for was the one goal it could not staff. The two arms are a pair on
        # purpose: the chair passes, the ordinary seat still refuses.
        fx3 = _staff_fixture(Path(tempfile.mkdtemp(prefix="ms-sm3-")))
        rows2 = [("tf-1", "w1"), ("tf-2", "x2")]
        (fx3["pkg"] / TASKFORCE_NAME).write_text(
            ",".join(TASKFORCE_HEADER) + "\n"
            + "".join(_render_csv_line(
                [tf, seat, "", "claude", "claude-opus-5", "high", "", ""]) + "\n"
                for tf, seat in rows2), encoding="utf-8")

        res = _staff_run(fx3, "leader", bindings=str(fx3["leader_sheet"]))
        rows = {r["seat"]: r for r in _staff_rows(fx3)}
        check("SM-6 green (multi-taskforce): a goal carrying TWO taskforce-ids "
              "can still be staffed — the chair is minted instead of refused",
              not isinstance(res, Refuse) and "leader" in rows,
              str(res)[:200] or str(list(rows)))
        check("SM-6 green: the chair joins the goal's FIRST taskforce (the "
              "earliest bare id in the file), and its after cell is still empty",
              rows.get("leader", {}).get("taskforce-id") == "tf-1"
              and rows.get("leader", {}).get("after", "x") == "",
              str(rows.get("leader")))

        res = _staff_run(fx3, "w2")
        check("SM-7 red: an ORDINARY seat against the same two-taskforce "
              "registry still refuses `taskforce-id-unreadable` — the lift is "
              "staff ∪ summoned, never a hole in the gate",
              isinstance(res, Refuse) and res.code == "taskforce-id-unreadable"
              and "w2" not in [r["seat"] for r in _staff_rows(fx3)],
              f"{type(res).__name__} {getattr(res, 'code', '')} {str(res)[:160]}")
        res = _staff_run(fx3, "goal-master",
                         bindings=str(fx3["goal_master_sheet"]))
        rows = {r["seat"]: r for r in _staff_rows(fx3)}
        check("SM-13 green (multi-taskforce summoned): goal-master is minted "
              "into a two-taskforce registry and joins the FIRST taskforce",
              not isinstance(res, Refuse)
              and rows.get("goal-master", {}).get("taskforce-id") == "tf-1"
              and rows.get("goal-master", {}).get("after", "x") == "",
              f"{type(res).__name__} {getattr(res, 'code', '')} {str(rows.get('goal-master'))[:200]}")
        shutil.rmtree(fx3["pkg"].parents[2].parent, ignore_errors=True)

        # ---- SM-8/SM-9: the PURE COMPLETION. A `--force-partial` run whose
        # seats ALREADY HAVE ROWS appends nothing — the rows are rendered only
        # to be byte-compared — so its id is READ off those rows and no
        # taskforce is chosen for anything. This is what W7's goal-local lane
        # does on EVERY invocation (a goal-authored seat is registered by the
        # binder and built later), and refusing it left the flagship's own
        # `seam-*` seats unbuildable over a value written in the file being
        # read. The fixture derives the held row by MATERIALIZING it, so the
        # byte-match is against a row this code actually writes, never a
        # hand-typed guess at its shape.
        fx4 = _staff_fixture(Path(tempfile.mkdtemp(prefix="ms-sm4-")))
        _staff_run(fx4, "w1")
        held = [r for r in _staff_rows(fx4) if r["seat"] == "w1"]
        tf_path4 = fx4["pkg"] / TASKFORCE_NAME
        # A SECOND taskforce joins the registry, which is what arms the gate.
        tf_path4.write_text(tf_path4.read_text(encoding="utf-8") + _render_csv_line(
            ["tf-2", "x9", "", "claude", "claude-opus-5", "high", "", ""]) + "\n",
            encoding="utf-8")
        before4 = tf_path4.read_text(encoding="utf-8")
        shutil.rmtree(fx4["pkg"] / "seats" / "w1", ignore_errors=True)
        check("SM-8 CONTROL: the registry carries TWO ids and w1's row survives "
              "with its folder gone — the exact half-state --force-partial "
              "completes",
              len(held) == 1 and held[0]["taskforce-id"] == "tf-1"
              and not (fx4["pkg"] / "seats" / "w1").exists(),
              str(held))
        res = _staff_run(fx4, "w1", force_partial=True)
        check("SM-8 green: the completion SUCCEEDS on a two-taskforce registry "
              "— the id comes off the seat's OWN row, so nothing is guessed",
              not isinstance(res, Refuse)
              and (fx4["pkg"] / "seats" / "w1" / "seat.md").exists(),
              f"{type(res).__name__} {getattr(res, 'code', '')} {str(res)[:200]}")
        check("SM-8 green: it APPENDED NOTHING — the registry is byte-identical, "
              "which is what makes reading the id off it honest rather than a "
              "second lift of the gate",
              tf_path4.read_text(encoding="utf-8") == before4)
        # SM-9 RED: the twin. A seat with NO row on the same registry has no id
        # to read and is still refused — the gate is intact for every seat this
        # branch does not cover.
        res = _staff_run(fx4, "w2", force_partial=True)
        check("SM-9 red: a seat with NO existing row on the same two-taskforce "
              "registry still refuses `taskforce-id-unreadable` — the branch "
              "reads an id, it never picks one",
              isinstance(res, Refuse) and res.code == "taskforce-id-unreadable"
              and "w2" not in [r["seat"] for r in _staff_rows(fx4)],
              f"{type(res).__name__} {getattr(res, 'code', '')} {str(res)[:160]}")
        shutil.rmtree(fx4["pkg"].parents[2].parent, ignore_errors=True)

        # ---- SM-10..SM-12: THE BORN-TERMINAL CHAIR (task 05 defect B).
        # A chair minted over an ending that already stands under its NAME
        # inherits it — the readiness derivation reads that row as the chair's
        # own — so the chair exists and can never sit, and nothing detects it:
        # the flagship's was found only because a Definition of done demanded
        # the chair read IDLE. The surface these arms interrogate MOVED with
        # spec-state-store §4.1 Row A: the debt ledger `awaiting-close.json` is
        # deleted, and the standing ending lives in the ONE ending store. So the
        # arms are stated in the store's vocabulary — a `done` ending, a
        # non-`done` ending, and a chair of the OTHER class — never in panes and
        # pids, which are the supervisor registry's facts and not an ending's
        # [T4-R8].
        fx5 = _staff_fixture(Path(tempfile.mkdtemp(prefix="ms-sm5-")))
        # The flagship's own shape, in the surviving vocabulary: a predecessor
        # sitting checked out `done` under the chair's name before the chair
        # existed.
        _es().stamp_seat_declare(fx5["pkg"], "leader", "done")
        res = _staff_run(fx5, "w1")
        warned = [w for w in (res or {}).get("warnings", ())
                  if "leader" in w and "CURRENT ENDING" in w]
        check("SM-10 red: a materialize against a goal already carrying a "
              "CURRENT ENDING under the chair's name does NOT mint the chair — "
              "the goal still materializes, and the warning names the ending "
              "and its stamp. Without this gate the chair is minted and reads "
              "that row as its own: born terminal and unwakeable. It names NO "
              "settlement verb, because §4.1 deleted the ledger that had one",
              not isinstance(res, Refuse)
              and "leader" not in [r["seat"] for r in _staff_rows(fx5)]
              and len(warned) == 1 and "`done`" in warned[0]
              and "close-seat" not in warned[0],
              str((res or {}).get("warnings"))[:400])

        # SM-11: a NON-`done` ending blocks the mint too. Stated as its own arm
        # because the gate must stay keyed on an ending STANDING and never on
        # which ending it is: `incomplete` + `armed` is just as inheritable, and
        # a guard narrowed to `done` would mint a chair born mid-relaunch. This
        # is the arm the pre-§4.1 suite spent on dead-vs-live panes — liveness
        # is the supervisor registry's fact, not an ending's, so the
        # discrimination moved here rather than being dropped.
        _es().stamp_system(fx5["pkg"], "leader", "incomplete", armed=1,
                           diagnostic="context full")
        res = _staff_run(fx5, "w2", root=False, after="w1")
        check("SM-11 red: a NON-`done` current ending (`incomplete`, armed) "
              "blocks the mint too — the gate is keyed on an ending STANDING, "
              "never on which ending it is, because every one of them is "
              "inherited by a chair minted over it",
              not isinstance(res, Refuse)
              and "leader" not in [r["seat"] for r in _staff_rows(fx5)]
              and any("CURRENT ENDING" in w and "`incomplete`" in w
                      for w in (res or {}).get("warnings", ())),
              str((res or {}).get("warnings"))[:300])

        # SM-10b: THE SUMMONED chair takes the SAME gate. This arm exists
        # because its absence is what shipped a defect: §4.1's retarget moved
        # the staff loop onto the ending store and left the summoned loop bound
        # to the deleted ledger's variable, so every goal declaring a summoned
        # chair died on a `NameError` and no row here noticed. Both loops read
        # one helper now, and this arm is what keeps that true.
        fx5s = _staff_fixture(Path(tempfile.mkdtemp(prefix="ms-sm5s-")))
        summoned_chair = _coord_summoned_seats()[0]
        _es().stamp_seat_declare(fx5s["pkg"], summoned_chair, "done")
        res = _staff_run(fx5s, "w1")
        check("SM-10b red: a CURRENT ENDING under the SUMMONED chair's name "
              f"('{summoned_chair}') blocks its mint with the same warning the "
              "staff chair gets — one gate, one reader, both loops",
              not isinstance(res, Refuse)
              and summoned_chair not in [r["seat"] for r in _staff_rows(fx5s)]
              and any(summoned_chair in w and "CURRENT ENDING" in w
                      for w in (res or {}).get("warnings", ())),
              str((res or {}).get("warnings"))[:400])
        shutil.rmtree(fx5s["pkg"].parents[2].parent, ignore_errors=True)

        # SM-12 CONTROL: the same fixture SHAPE with an empty store mints the
        # chair. Without this arm the three reds pass for any reason the chair
        # fails to appear. A FRESH fixture rather than a cleared one: the store
        # is append-only by design and a minter that deleted endings would be a
        # second writer of the surface that records them — exactly what the
        # gate's own comment forbids.
        fx5c = _staff_fixture(Path(tempfile.mkdtemp(prefix="ms-sm5c-")))
        res = _staff_run(fx5c, "w1")
        check("SM-12 control: the same fixture with NO current ending mints "
              "the chair — so the three arms above discriminate the "
              "standing-ending gate from every other reason a chair can fail "
              "to appear",
              not isinstance(res, Refuse)
              and "leader" in [r["seat"] for r in _staff_rows(fx5c)],
              str(res)[:200] or str([r["seat"] for r in _staff_rows(fx5c)]))
        shutil.rmtree(fx5c["pkg"].parents[2].parent, ignore_errors=True)
        shutil.rmtree(fx5["pkg"].parents[2].parent, ignore_errors=True)

        # ---- SM-14/SM-15: D79 auto-mint of the summoned chair on the
        # `--root --workflow` path (the same invocation the creation job
        # and a console materialize both take). The fixture already carries
        # a goal-master sheet; SM-1 keeps asserting staff added_seats ==
        # [["leader"]] because summoned is a sibling key, not a staff rewrite.
        fx6 = _staff_fixture(Path(tempfile.mkdtemp(prefix="ms-sm6-")))
        res = _staff_run(fx6, None, workflow="sm-flow",
                         bindings=fx6["b"]["w1"])
        rows = {r["seat"]: r for r in _staff_rows(fx6)}
        summoned = _coord_summoned_seats()
        staff_ids = _coord_staff_seats()
        check("SM-14 green: a --root --workflow materialize ALSO mints the "
              "`goal-master` chair — seats/goal-master/seat.md exists, the "
              "row's after cell is empty and it joins the first taskforce",
              not isinstance(res, Refuse)
              and (fx6["pkg"] / "seats" / "goal-master" / "seat.md").is_file()
              and rows.get("goal-master", {}).get("after", "x") == ""
              and rows.get("goal-master", {}).get("taskforce-id")
              == rows.get("w1", {}).get("taskforce-id")
              and "goal-master" in summoned
              and "goal-master" not in staff_ids,
              str(res)[:240] if not isinstance(res, dict) else
              str(rows.get("goal-master")))
        check("SM-14 green: the summoned mint is DISCLOSED in result"
              "['summoned'], never silently and never inside result['staff']",
              [s["added_seats"] for s in (res or {}).get("summoned", ())]
              == [["goal-master"]]
              and [s["added_seats"] for s in (res or {}).get("staff", ())]
              == [["leader"]],
              str({k: (res or {}).get(k) for k in ("staff", "summoned")}))
        shutil.rmtree(fx6["pkg"].parents[2].parent, ignore_errors=True)

        fx7 = _staff_fixture(Path(tempfile.mkdtemp(prefix="ms-sm7-")))
        fx7["goal_master_sheet"].unlink()
        res = _staff_run(fx7, None, workflow="sm-flow",
                         bindings=fx7["b"]["w1"])
        warned = [w for w in (res or {}).get("warnings", ())
                  if "goal-master" in w and "casting sheet" in w]
        check("SM-15 red: the same --root --workflow fixture WITHOUT the "
              "goal-master sheet yields no chair plus a warning naming the "
              "sheet path",
              not isinstance(res, Refuse)
              and "goal-master" not in [r["seat"] for r in _staff_rows(fx7)]
              and not (fx7["pkg"] / "seats" / "goal-master").exists()
              and len(warned) == 1
              and str(fx7["goal_master_sheet"]) in warned[0],
              str((res or {}).get("warnings"))[:400])
        shutil.rmtree(fx7["pkg"].parents[2].parent, ignore_errors=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _pf_run(fx: dict, binding: str, **over):
    """One in-process materialize against the PF fixture; returns the result
    dict, or the Refuse it raised."""
    args = argparse.Namespace(
        package=str(fx["pkg"]), seat="pf", workflow=None,
        catalog_root=fx["catalog"], after=None, root=True,
        bindings=fx["b"][binding], milestone_id=None,
        claude_md=None, budget_json=None, dry_run=True,
        as_json=False, force_partial=False, repass=False)
    for k, v in over.items():
        setattr(args, k, v)
    try:
        return run(args)
    except Refuse as r:
        return r


def run_pass_substitution_acceptance(check) -> None:
    """PF-1..PF-4 — B4, B5, G-planner-0804-1502 and task 7.678's milestone
    row-check, both arms each."""
    root = Path(tempfile.mkdtemp(prefix="ms-pf-"))
    try:
        fx = _pf_fixture(root)

        # ---- PF-1: the substitution itself, in BOTH legal pass forms.
        ms = _pf_run(fx, "ms")["descriptors"]["pf"]
        br = _pf_run(fx, "br")["descriptors"]["pf"]
        check("PF-1 green: a MILESTONE-pass render carries the resolved "
              "folder and ZERO literal m{N}",
              "planning/m1-first-milestone/brief.md" in ms
              and "manifest-m1.csv" in ms
              and "m{N}" not in ms and "{milestone-name}" not in ms, ms[:400])
        check("PF-1 green: a BRIEFING-pass render resolves the "
              "briefing-<name>/ write path in both placeholder spellings",
              "planning/briefing-a-briefing/brief.md" in br
              and "planning/briefing-a-briefing/spine.md" in br
              and "manifest-a-briefing.csv" in br
              and "m{N}" not in br, br[:400])
        check("PF-1 green: the emitted frontmatter DECLARES the pass it was "
              "rendered for",
              "pass: planning/briefing-a-briefing/" in br, br[:200])
        absent = _pf_run(fx, "absent")
        check("PF-1 red: a binding that OMITS pass-folder is REFUSED, never "
              "rendered with the placeholder intact",
              isinstance(absent, Refuse)
              and absent.code == "pass-folder-missing", str(absent)[:300])

        # ---- PF-2: the two legal forms are the ONLY ones, and the pass must
        # be OPEN. The `none` opt-out is the declared mention case.
        none = _pf_run(fx, "none")["descriptors"]["pf"]
        check("PF-2 green: pass-folder: none renders, preserving the "
              "placeholder VERBATIM (a unit that MENTIONS it, declared)",
              "planning/m{N}-{milestone-name}/brief.md" in none
              and "pass: none" in none, none[:400])
        bad, closed = _pf_run(fx, "bad"), _pf_run(fx, "closed")
        check("PF-2 red: a pass folder in neither legal form is refused, "
              "never coerced",
              isinstance(bad, Refuse) and bad.code == "pass-folder-invalid",
              str(bad)[:300])
        check("PF-2 red: a pass folder naming a CLOSED pass is refused "
              "(G-planner-0804-1502's staleness guard)",
              isinstance(closed, Refuse) and closed.code == "pass-not-open",
              str(closed)[:300])

        # ---- PF-4 (task 7.678): a MILESTONE pass folder's m{N} must resolve
        # to a milestones.csv ROW — the same guarantee --milestone-id carries
        # (validate_milestone), through the same predicate and the same
        # refusal code. Runs BEFORE PF-3 deliberately: PF-3 materializes for
        # real, and every arm here wants the pristine (dry-run) package.
        m0 = _pf_run(fx, "m0")
        check("PF-4 green: the m0 NAMING CONVENTION still works where the row "
              "exists — d-planning-is-milestone-zero is not broken; the row "
              "is what is required, never the name",
              not isinstance(m0, Refuse)
              and "planning/m0-bootstrapping/brief.md" in m0["descriptors"]["pf"]
              and "m{N}" not in m0["descriptors"]["pf"], str(m0)[:300])
        m9 = _pf_run(fx, "m9")
        check("PF-4 red: a pass folder naming m9, whose pass row is OPEN but "
              "which resolves to no milestones.csv row, is refused "
              "milestone-unresolved — the sibling --milestone-id guarantee, "
              "now carried by the pass folder too",
              isinstance(m9, Refuse) and m9.code == "milestone-unresolved",
              str(m9)[:300])
        # The observed incident, exactly: a planning pass under `m0-*` against
        # a milestones.csv with ZERO rows. A bootstrap-tolerant `if rows:`
        # skip (the _pass_values passes.csv guard's shape) passes this arm
        # green — which is precisely why the refusal is HARD.
        ms_file = fx["pkg"] / MILESTONES_NAME
        ms_text = ms_file.read_text(encoding="utf-8")
        ms_file.write_text("milestone-id,name,status\n", encoding="utf-8")
        empty = _pf_run(fx, "m0")
        ms_file.write_text(ms_text, encoding="utf-8")
        check("PF-4 red: a ZERO-ROW milestones.csv refuses HARD — no "
              "bootstrap tolerance, because that tolerance is how the live "
              "m0-bootstrapping pass ran unbacked and nothing objected",
              isinstance(empty, Refuse)
              and empty.code == "milestone-unresolved", str(empty)[:300])

        # ---- PF-3: --repass, the chosen G-planner-0804-1502 fix. Materialize
        # for the milestone pass, CLOSE it, then re-render for the open one.
        _pf_run(fx, "ms", dry_run=False)
        smd = fx["pkg"] / "seats" / "pf" / "seat.md"
        before = smd.read_text(encoding="utf-8")
        tf_before = (fx["pkg"] / TASKFORCE_NAME).read_text(encoding="utf-8")
        (fx["pkg"] / PASSES_NAME).write_text(
            (fx["pkg"] / PASSES_NAME).read_text(encoding="utf-8")
            .replace("m1-first-milestone,PRODUCT,seats=1;rounds=1,"
                     "2026-01-01 00:00,,",
                     "m1-first-milestone,PRODUCT,seats=1;rounds=1,"
                     "2026-01-01 00:00,2026-01-03 00:00,ACCEPTED"),
            encoding="utf-8")
        stale = _pf_run(fx, "ms", dry_run=False, repass=True)
        check("PF-3 red: --repass carrying the now-CLOSED pass is refused "
              "and the descriptor on disk is byte-unchanged",
              isinstance(stale, Refuse) and stale.code == "pass-not-open"
              and smd.read_text(encoding="utf-8") == before, str(stale)[:300])
        res = _pf_run(fx, "br", dry_run=False, repass=True)
        after = smd.read_text(encoding="utf-8")
        check("PF-3 green: --repass RE-RENDERS the existing descriptor for "
              "the newly open pass — the stale pass folder is gone",
              not isinstance(res, Refuse)
              and "pass: planning/briefing-a-briefing/" in after
              and "planning/m1-first-milestone/" not in after
              and [w["kind"] for w in res["writes"]]
              == ["seat-descriptor-repass",
                  "seat-guidance", "seat-guidance"], str(res)[:300])
        check("PF-3 green: --repass leaves the registry row BYTE-IDENTICAL "
              "(it re-renders a descriptor, it never re-registers a seat)",
              (fx["pkg"] / TASKFORCE_NAME).read_text(encoding="utf-8")
              == tf_before)
        ghost = _pf_run(fx, "br", dry_run=False, repass=True,
                        package=str(fx["pkg"]), seat="pf",
                        after="somebody")
        check("PF-3 red: --repass never changes an edge — --after is refused",
              isinstance(ghost, Refuse) and ghost.code == "repass-with-after",
              str(ghost)[:300])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_selftest() -> int:
    _clear_discovery_cache()
    failures: list[str] = []
    records: list[tuple[str, bool]] = []  # dag-07 — the rollup's input

    def check(label: str, cond: bool, detail: str = "") -> None:
        records.append((label, bool(cond)))
        if cond:
            print(f"  ok   {label}")
        else:
            failures.append(label)
            print(f"  FAIL {label}{': ' + detail if detail else ''}")

    print("functional pass (clean environment)")
    clean_env = {k: v for k, v in os.environ.items()
                 if k not in SCRUBBED_ENV_VARS}
    res_clean = run_scenario_suite(clean_env, check=check)

    print("SK-4 environment-independence pass (junk pane/identity vars)")
    junk_env = dict(clean_env)
    for var in SCRUBBED_ENV_VARS:
        junk_env[var] = f"junk-{var}"
    # Control arm first: the junk values must actually REACH a child process,
    # or the identical-results comparison is vacuous.
    probe = subprocess.run(
        [sys.executable, "-c",
         "import os, json; print(json.dumps([os.environ.get(v) for v in "
         + repr(SCRUBBED_ENV_VARS) + "]))"],
        capture_output=True, text=True, env=junk_env)
    check("SK-4 control: junk values are SET in the child environment",
          json.loads(probe.stdout) == [f"junk-{v}" for v in SCRUBBED_ENV_VARS],
          probe.stdout.strip())
    res_junk = run_scenario_suite(junk_env)
    check("SK-4: the whole suite is identical under the junk environment",
          [(l, rc, out) for l, rc, out in res_clean]
          == [(l, rc, out) for l, rc, out in res_junk])

    print("SK-7 one-assembler pass")
    own_src = Path(__file__).resolve().read_text(encoding="utf-8")
    cli_src = (_GOAL_CLI_DIR / "goal_cli.py").read_text(encoding="utf-8")
    emitter = re.compile("<" + r"\{[^}]*\bkind\b" + "|"
                         + "<" + r"[a-z0-9-]+ id=")
    check("SK-7: no local unit emitter in this file",
          emitter.search(own_src) is None)
    check("SK-7 control: the detector fires on goal_cli's real emitter",
          emitter.search(cli_src) is not None)
    check("SK-7: assemble_seat is imported from goal_cli",
          assemble_seat.__module__ == "goal_cli"
          and index_units.__module__ == "goal_cli"
          and load_catalogs.__module__ == "goal_cli")
    check("F6: validate_seat is imported from the kit, never re-implemented — it is defined in "
          "`supervisor/launch.py` since the 2026-08-25 split and re-exported by `coord.py`'s §3 "
          "shim, so the name this file imports is the launch composer's OWN predicate",
          _coord_validate_seat().__module__ == "launch")

    print("SK-9 manifest-reference classifier pass (MC9 / 7.451)")
    import inspect as _mc9_inspect
    # The copy-detector: the two textual idioms of every LOCAL reading of the
    # member grammar in this repo — the bracket strip and the alternate split.
    mc9_copy = re.compile("|".join(re.escape(s) for s in (
        r"[^\]]*", '.split("|")', 'split("[", 1)')))
    check("SK-9: the classifier authors no second reading of the member grammar",
          mc9_copy.search(
              _mc9_inspect.getsource(classify_manifest_reference)) is None)
    check("SK-9 control: the detector fires on this file's own local strip "
          "(_manifest_after_ids) — an absence proven by a detector that can fire",
          mc9_copy.search(_mc9_inspect.getsource(_manifest_after_ids)) is not None)
    check("SK-9: the classifier reaches the ONE decomposition by import "
          "(goal_cli.after_member_grammar -> coord.parse_after_member)",
          after_member_grammar.__module__ == "goal_cli"
          and after_member_grammar()("a[k=v]") == ("a", "k", "v", False))
    # Driven off the REAL fixture catalog, never off hand-typed namespaces: the
    # seat ids and workflow names below are `build_fixture`'s own, read back
    # through `load_catalogs` and the same glob `resolve_added` uses.
    with tempfile.TemporaryDirectory() as mc9_td:
        mc9_root = Path(build_fixture(Path(mc9_td))["catalog"])
        mc9_seats = load_catalogs(mc9_root)[0]
        check("SK-9 control: the fixture supplies BOTH namespaces non-empty",
              {"alpha", "s3"} <= set(mc9_seats)
              and {p.parent.name for p in mc9_root.glob("*/workflows/*/*.csv")}
              >= {"demo-flow", "guard-flow"})
        for token, kind in (("alpha", "seat"), ("s3", "seat"),
                            ("demo-flow", "nested_workflow"),
                            ("guard-flow", "nested_workflow"),
                            ("alpha[go=yes]", "seat"),
                            ("demo-flow[go=yes]", "nested_workflow")):
            ref = classify_manifest_reference(token, mc9_root, mc9_seats)
            check(f"SK-9: {token!r} classifies as {kind}", ref.kind == kind,
                  f"got {ref.kind} (name={ref.name!r})")
        check("SK-9: a guard does not change the classification",
              classify_manifest_reference("alpha", mc9_root, mc9_seats).kind
              == classify_manifest_reference("alpha[go=yes]", mc9_root,
                                             mc9_seats).kind)
        for token, code in (("no-such-thing", "reference-unresolvable"),
                            ("alpha|demo-flow", "reference-alternate"),
                            ("alpha[nokey]", "reference-invalid"),
                            ("Alpha", "reference-invalid")):
            try:
                got = classify_manifest_reference(
                    token, mc9_root, mc9_seats).kind
            except Refuse as exc:
                got = exc.code
            check(f"SK-9: {token!r} is REFUSED as {code}, never defaulted",
                  got == code, f"got {got}")
        # The one input a new manifest column would settle (design F-9a): ONE id
        # minted into BOTH namespaces. Built here rather than in `build_fixture`,
        # which no other arm may see a collision in.
        (mc9_root / "demo-comp" / "workflows" / "alpha").mkdir(parents=True)
        (mc9_root / "demo-comp" / "workflows" / "alpha" / "alpha.csv").write_text(
            "Seat/workflow,after,i/o,Modality\nbeta,,,agentic\n", encoding="utf-8")
        try:
            got = classify_manifest_reference("alpha", mc9_root, mc9_seats).kind
        except Refuse as exc:
            got = exc.code
        check("SK-9: an id in BOTH namespaces is REFUSED as reference-ambiguous "
              "(F-9a's real radius — one colliding id, not the manifest form)",
              got == "reference-ambiguous", f"got {got}")

    print("IO-1 instance-ordinal seat naming pass (7.545)")
    with tempfile.TemporaryDirectory() as io_td:
        io_tmp = Path(io_td)
        # ---- criterion 1: the AMENDED shape, both arms -------------------
        check("IO-1: the FIRST instance carries NO ordinal (rsch-researcher) "
              "— the owner's amendment to r-branch-seat-name-carries-the-"
              "instance-ordinal",
              compose_seat_name("rsch", 1, "researcher") == "rsch-researcher",
              compose_seat_name("rsch", 1, "researcher"))
        check("IO-1: the SECOND instance onward carries it "
              "(rsch-2-researcher, rsch-10-researcher)",
              compose_seat_name("rsch", 2, "researcher") == "rsch-2-researcher"
              and compose_seat_name("rsch", 10, "researcher")
              == "rsch-10-researcher")
        check("IO-1 red: the SUPERSEDED always-present shape is never "
              "composed — nothing this function returns spells `-1-`",
              "-1-" not in compose_seat_name("rsch", 1, "researcher"))
        check("IO-1: NO RENAME — composing the second instance leaves the "
              "first instance's name unchanged (the composition is a pure "
              "function of its own ordinal)",
              compose_seat_name("rsch", 1, "researcher")
              == "rsch-researcher"
              and compose_seat_name("rsch", 1, "researcher")
              != compose_seat_name("rsch", 2, "researcher"))
        for prefix, ordinal, seat, code in (
                ("rs", 1, "researcher", "workflow-prefix-invalid"),
                ("rsch5", 1, "researcher", "workflow-prefix-invalid"),
                ("rsch", 1, "Researcher", "seat-invalid"),
                ("rsch", 0, "researcher", "instance-ordinal-invalid")):
            try:
                got = compose_seat_name(prefix, ordinal, seat)
            except Refuse as exc:
                got = exc.code
            check(f"IO-1 red: compose({prefix!r}, {ordinal}, {seat!r}) is "
                  f"REFUSED as {code}, never patched into a name",
                  got == code, f"got {got}")
        # ---- the reader handles BOTH shapes (the accepted consequence) ----
        check("IO-1: the parser reads both ruled shapes back",
              parse_instance_seat_name("rsch-researcher")
              == ("rsch", 1, "researcher")
              and parse_instance_seat_name("rsch-2-researcher")
              == ("rsch", 2, "researcher"))
        check("IO-1 red: `rsch-1-researcher` (the SUPERSEDED shape) does NOT "
              "read as instance 1 — admitting it would re-legalize the "
              "reading the owner reversed",
              parse_instance_seat_name("rsch-1-researcher")
              != ("rsch", 1, "researcher"))
        # ---- criterion 2: the prefix is DECLARED, never derived ----------
        wf = io_tmp / "workflows" / "research"
        wf.mkdir(parents=True)
        for label, body, want in (
                ("undeclared", "---\nname: research\n---\n\nx\n",
                 "workflow-prefix-undeclared"),
                ("not four letters",
                 "---\nname: research\nfour-letters: rs\n---\n\nx\n",
                 "workflow-prefix-invalid"),
                ("declared", "---\nname: research\nfour-letters: rsch\n---\n\nx\n",
                 "rsch")):
            (wf / WORKFLOW_DESCRIPTOR_NAME).write_text(body, encoding="utf-8")
            try:
                got = read_workflow_prefix(wf)
            except Refuse as exc:
                got = exc.code
            check(f"IO-1: a workflow.md that is {label} yields {want}",
                  got == want, f"got {got}")
        (wf / WORKFLOW_DESCRIPTOR_NAME).unlink()
        try:
            got = read_workflow_prefix(wf)
        except Refuse as exc:
            got = exc.code
        check("IO-1 red: NO workflow.md at all REFUSES "
              "(workflow-prefix-undeclared) rather than deriving the prefix "
              "from the workflow id — derivation was measured to COLLIDE on "
              "2 of 40 real ids",
              got == "workflow-prefix-undeclared", f"got {got}")
        # ---- the ordinal is derived WITHIN THE GOAL, from its roster -----
        pkg = io_tmp / "goals" / "io-goal"
        pkg.mkdir(parents=True)
        tf = pkg / TASKFORCE_NAME
        check("IO-1: a goal that has never hosted the workflow gives the "
              "FIRST instance (no taskforce.csv at all)",
              next_instance_ordinal(pkg, "rsch") == 1)
        tf.write_text(",".join(TASKFORCE_HEADER) + "\n", encoding="utf-8")
        row = "tf-1,{seat},,claude,opus,high,,\n"
        tf.write_text(tf.read_text(encoding="utf-8")
                      + row.format(seat="rsch-researcher")
                      + row.format(seat="planner"), encoding="utf-8")
        check("IO-1: with the FIRST instance on the roster the next is 2 — "
              "and a bare top-level seat contributes nothing",
              next_instance_ordinal(pkg, "rsch") == 2)
        tf.write_text(tf.read_text(encoding="utf-8")
                      + row.format(seat="rsch-2-researcher"), encoding="utf-8")
        check("IO-1: MAX+1, not COUNT+1 — the second instance on the roster "
              "gives 3, and an ordinal once spent is never reused",
              next_instance_ordinal(pkg, "rsch") == 3)
        check("IO-1: the series is PER PREFIX — another workflow's seats "
              "never advance this one's ordinal",
              next_instance_ordinal(pkg, "plan") == 1)
        # ---- criterion 3: two instances, two DISTINCT seat folders -------
        names = [compose_seat_name("rsch", n, "researcher") for n in (1, 2)]
        homes = [seat_home(pkg, n) for n in names]
        check("IO-1: two instances of ONE workflow in ONE goal resolve to "
              "DISTINCT seat folders — the one-folder collision is closed",
              homes[0] != homes[1]
              and [h.name for h in homes]
              == ["rsch-researcher", "rsch-2-researcher"],
              str(homes))
        for home in homes:
            home.mkdir(parents=True)
        check("IO-1 red (cut-guard): the SAME arm on the BARE name collides — "
              "check_collisions refuses `seat-exists` for a name already on "
              "disk, which is exactly what one folder for two instances is",
              _refusal_code(lambda: check_collisions(pkg, [names[0]], False))
              == "seat-exists")
        check("IO-1 control: an unmaterialized composed name passes the same "
              "gate — the red arm above measures the collision, not the gate",
              _refusal_code(lambda: check_collisions(
                  pkg, [compose_seat_name("rsch", 3, "researcher")], False))
              is None)
        # ---- criterion 7: a composed name is a DISK name, never a key ----
        naming_src = "\n".join(
            _mc9_inspect.getsource(f) for f in
            (compose_seat_name, next_instance_ordinal,
             parse_instance_seat_name, read_workflow_prefix))
        check("IO-1 (criterion 7): no composed name is ever fed back into a "
              "catalog or bindings lookup — the naming surface names no "
              "catalog and no bindings at all",
              not any(tok in naming_src for tok in
                      ("seats_cat", "bindings", "assemble_seat")))

    print("NEST-1 nested-workflow materialization pass (7.615)")
    with tempfile.TemporaryDirectory() as nest_td:
        nfx = build_fixture(Path(nest_td))
        npkg = Path(nfx["pkg"])
        bindings_before = Path(nfx["b_both"]).read_bytes()

        def nest(*extra) -> subprocess.CompletedProcess:
            return _invoke(["--package", nfx["pkg"], "--workflow", "demo-flow",
                            "--catalog-root", nfx["catalog"], "--bindings",
                            nfx["b_both"], "--milestone-id", "m1", "--after",
                            "chief", "--json", *extra], clean_env)

        def code(cp) -> str:
            try:
                return (json.loads(cp.stdout).get("refusal") or {}).get("code", "")
            except ValueError:
                return ""

        def rows_by_seat() -> dict:
            return {(r.get("seat") or "").strip(): r
                    for r in _csv_rows(npkg / TASKFORCE_NAME)}

        # ---- RED FIRST: the collision the composed names close -----------
        bare_1, bare_2 = nest(), nest()
        check("NEST-1 red (the pre-fix collision, pinned BEFORE the fix is "
              "exercised): a SECOND materialization of one workflow into one "
              "goal WITHOUT --nested refuses `seat-exists` — bare catalog ids "
              "give two instances ONE folder",
              bare_1.returncode == 0 and bare_2.returncode == 1
              and code(bare_2) == "seat-exists",
              f"first rc={bare_1.returncode} second={code(bare_2)!r}")
        # ---- GREEN: two instances, end to end ----------------------------
        nest_1, nest_2 = nest("--nested"), nest("--nested")
        try:
            added_1 = json.loads(nest_1.stdout).get("added_seats")
            added_2 = json.loads(nest_2.stdout).get("added_seats")
        except ValueError:
            added_1 = added_2 = None
        check("NEST-1 green: the FIRST nested instance materializes with BARE "
              "composed names (demo-alpha, demo-beta) and the SECOND carries "
              "the ordinal (demo-2-alpha, demo-2-beta) — the same call twice, "
              "no rename of the first",
              added_1 == ["demo-alpha", "demo-beta"]
              and added_2 == ["demo-2-alpha", "demo-2-beta"],
              f"{added_1} then {added_2} "
              f"[{nest_1.stderr.strip()}|{nest_2.stderr.strip()}]")
        check("NEST-1 green: all four seat folders exist and are DISTINCT — "
              "the one-folder collision above is closed on disk",
              all((npkg / "seats" / s).is_dir() for s in
                  ("demo-alpha", "demo-beta", "demo-2-alpha", "demo-2-beta")))
        rows = rows_by_seat()
        check("NEST-1 green (criterion 8 / Rule 13): the frozen `after` cell "
              "is copied VERBATIM APART FROM THE INSTANCE RENAMING — each "
              "instance's internal edge points at ITS OWN root, never the "
              "sibling's and never the bare id",
              (rows.get("demo-beta") or {}).get("after") == "demo-alpha"
              and (rows.get("demo-2-beta") or {}).get("after") == "demo-2-alpha"
              and (rows.get("demo-2-alpha") or {}).get("after") == "chief",
              str({k: v.get("after") for k, v in rows.items()}))
        check("NEST-1 green (the tf-id ruling d-r2-tfid-structured-counter): "
              "each instance's rows carry tf-<n>-<prefix><m> — counter, "
              "declared prefix, instance ordinal, and NO run segment",
              {(rows.get(s) or {}).get("taskforce-id")
               for s in ("demo-alpha", "demo-beta")} == {"tf-2-demo1"}
              and {(rows.get(s) or {}).get("taskforce-id")
                   for s in ("demo-2-alpha", "demo-2-beta")} == {"tf-2-demo2"},
              str({k: v.get("taskforce-id") for k, v in rows.items()}))
        check("NEST-1 green (criterion 5, the door's input): the descriptor's "
              "`seat:` key carries the COMPOSED name — the heart-store door "
              "keys on the stored seat name, so two instances derive two keys",
              _descriptor_fm(npkg / "seats" / "demo-2-alpha" / "seat.md")
              .get("seat") == "demo-2-alpha")
        check("NEST-1 green (criterion 7, the two-name model): the bindings "
              "FILE is byte-unchanged and still keyed by CATALOG ID — the "
              "composed name is a DISK name and never becomes a lookup key",
              Path(nfx["b_both"]).read_bytes() == bindings_before
              and set(json.loads(bindings_before)["seats"]) == {"alpha", "beta"})
        # ---- the red arms of the flag itself -----------------------------
        check("NEST-1 red: --nested with a single --seat is REFUSED "
              "(nested-without-workflow) — a top-level seat has no workflow "
              "instance to be the Nth of, and its name stays bare",
              code(_invoke(["--package", nfx["pkg"], "--seat", "a2",
                            "--catalog-root", nfx["catalog"], "--bindings",
                            nfx["b_both"], "--after", "chief", "--nested",
                            "--json"], clean_env)) == "nested-without-workflow")
        check("NEST-1 red: a workflow whose workflow.md declares NO "
              "`four-letters:` REFUSES (workflow-prefix-undeclared) rather "
              "than deriving a prefix — derivation collides on 2 of 40 ids",
              code(_invoke(["--package", nfx["pkg"], "--workflow",
                            "scramble-flow", "--catalog-root", nfx["catalog"],
                            "--bindings", nfx["b_scramble"], "--after",
                            "chief", "--nested", "--json"], clean_env))
              == "workflow-prefix-undeclared")
        check("NEST-1: the frozen-cell rename touches MEMBERS only — a guard "
              "span passes through byte-verbatim, alternates and ordering "
              "intact",
              rename_after_cell("s2|s3,s1[g=a|b]",
                                {"s1": "demo-s1", "s2": "demo-s2",
                                 "s3": "demo-s3"})
              == "demo-s2|demo-s3,demo-s1[g=a|b]",
              rename_after_cell("s2|s3,s1[g=a|b]", {"s1": "demo-s1"}))

        # ---- NEST-2: the SINGLE-SEAT nested variant (W7) ------------------
        # The collapsed planning mode: ONE seat IS the whole pass, so it needs
        # the same composed name and the same instance id a full-mode pass
        # gets. `--nested` TAKES the workflow name here; bare it still refuses
        # (the red arm two checks above, unchanged and still green).
        solo = _invoke(["--package", nfx["pkg"], "--seat", "alpha",
                        "--catalog-root", nfx["catalog"], "--bindings",
                        nfx["b_alpha"], "--milestone-id", "m1", "--after",
                        "chief", "--nested", "demo-flow", "--json"], clean_env)
        try:
            solo_added = json.loads(solo.stdout).get("added_seats")
        except ValueError:
            solo_added = None
        solo_rows = rows_by_seat()
        check("NEST-2 green (W7, the deliberate contract change): `--seat "
              "<seat> --nested <workflow>` mints the seat as the NEXT instance "
              "of that workflow — composed name and instance taskforce-id, the "
              "same two things a full-mode pass gets, because a collapsed "
              "milestone's lone seat IS a pass. Two demo instances already "
              "exist above, so this one is the THIRD",
              solo.returncode == 0 and solo_added == ["demo-3-alpha"]
              and (npkg / "seats" / "demo-3-alpha").is_dir()
              and (solo_rows.get("demo-3-alpha") or {}).get("taskforce-id")
              == "tf-2-demo3",
              f"rc={solo.returncode} added={solo_added} "
              f"tf={(solo_rows.get('demo-3-alpha') or {}).get('taskforce-id')!r}"
              f" [{solo.stderr.strip()}]")
        check("NEST-2 red: `--seat <seat> --nested <workflow>` naming a "
              "workflow the catalog does not carry REFUSES "
              "(nested-workflow-unresolvable) instead of raising IndexError "
              "out of the glob — the single-seat path never went through "
              "resolve_added's manifest check, so the guard lives at the glob",
              code(_invoke(["--package", nfx["pkg"], "--seat", "alpha",
                            "--catalog-root", nfx["catalog"], "--bindings",
                            nfx["b_alpha"], "--after", "chief", "--nested",
                            "no-such-flow", "--json"], clean_env))
              == "nested-workflow-unresolvable")
        check("NEST-2 red: `--workflow W --nested V` with V != W REFUSES "
              "(nested-workflow-mismatch) — with --workflow the instance "
              "series IS that workflow, so a second, different name there is a "
              "contradiction and never a silent winner",
              code(nest("--nested", "scramble-flow")) == "nested-workflow-mismatch")

        # ---- INST-1: COMPLETING an EXISTING instance-named row ------------
        # The daemon's unbuilt-seat repair (`queue-request.js#buildUnbuiltSeats`)
        # meets rows whose seat is a COMPOSED name and whose folder is missing —
        # the registry half landed, the folder half did not. `--nested` cannot
        # serve it: it mints the NEXT ordinal, so it can never complete an
        # EXISTING demo-3 row. Measured live 2026-08-17 on the flagship goal:
        # two `plan-6-*` rows with no folder, the whole goal unseeded every
        # 10 s tick. NEST-2 above just built `demo-3-alpha` — deleting its
        # FOLDER reproduces the half-state exactly.
        inst_tf = (npkg / TASKFORCE_NAME).read_bytes()
        shutil.rmtree(npkg / "seats" / "demo-3-alpha")

        def inst(seat, *extra) -> subprocess.CompletedProcess:
            return _invoke(["--package", nfx["pkg"], "--seat", seat,
                            "--catalog-root", nfx["catalog"], "--bindings",
                            nfx["b_alpha"], "--milestone-id", "m1", "--after",
                            "chief", "--force-partial", "--json", *extra],
                           clean_env)

        cp = inst("demo-3-alpha")
        check("INST-1 green: `--seat demo-3-alpha --force-partial` COMPLETES "
              "the existing row — the catalog row is resolved through the BASE "
              "seat, the sheet keyed by that base casts it, the folder is "
              "built under the COMPOSED name, and NOT ONE BYTE of the registry "
              "moves (the id is read off the row being completed)",
              cp.returncode == 0
              and (npkg / "seats" / "demo-3-alpha" / "seat.md").is_file()
              and (npkg / TASKFORCE_NAME).read_bytes() == inst_tf,
              f"rc={cp.returncode} {(cp.stdout + cp.stderr).strip()[:300]}")
        check("INST-1 green: the completed descriptor names the COMPOSED seat, "
              "never the base it was cataloged and cast under",
              "seat: demo-3-alpha" in (npkg / "seats" / "demo-3-alpha"
                                       / "seat.md").read_text(encoding="utf-8"))
        shutil.rmtree(npkg / "seats" / "demo-3-alpha")
        check("INST-1 red: WITHOUT --force-partial the same composed name is "
              "`seat-unknown` — this is a COMPLETION lane and nothing else; a "
              "composed name is not a catalog key, and minting a new instance "
              "is `--nested`'s act",
              code(_invoke(["--package", nfx["pkg"], "--seat", "demo-3-alpha",
                            "--catalog-root", nfx["catalog"], "--bindings",
                            nfx["b_alpha"], "--milestone-id", "m1", "--after",
                            "chief", "--json"], clean_env)) == "seat-unknown")
        check("INST-1 red: a composed name whose BASE is in no seats.csv is "
              "still `seat-unknown` — the base is RESOLVED against the "
              "catalog, never assumed from the shape of the name",
              code(inst("demo-3-nosuchseat")) == "seat-unknown")
        check("INST-1 red: a sheet carrying neither the composed name nor the "
              "base REFUSES (bindings-missing-seat) — the re-key finds a cast "
              "or the run stops; a missing binding is never defaulted",
              code(inst("demo-3-beta")) == "bindings-missing-seat")

        # ---- INST-2 / D37 (2026-08-20): THE REFRESH LANE REACHES A COMPOSED NAME ---------
        # BEFORE this ruling no argv combination did. `--refresh` sets repass=True, and
        # repass + --force-partial is refused (`repass-with-force-partial`), while the alias
        # above fired ONLY under --force-partial — so every `plan-4-*` sheet on the two live
        # production goals was unrefreshable BY STRUCTURE (loose-end L133), which is also
        # what would have made D37's refresh-before-launch a no-op on exactly the seats that
        # needed it most. The alias is now ONE predicate over both flags: they agree that the
        # row exists under its composed name and its DEFINITION lives under the base.
        inst("demo-3-alpha")          # rebuild the folder the red arms above removed
        _r37_tf = (npkg / TASKFORCE_NAME).read_bytes()
        _r37 = _invoke(["--package", nfx["pkg"], "--seat", "demo-3-alpha",
                        "--catalog-root", nfx["catalog"], "--refresh", "--root",
                        "--json"], clean_env)
        check("INST-2 green (D37): `--seat demo-3-alpha --refresh --root` RESOLVES the "
              "composed name through its base row and re-renders the descriptor in place — "
              "the seat keeps its composed name, the registry does not move a byte, and no "
              "row is appended. Its control is the INST-1 red arm two rows up: the SAME "
              "composed name with neither flag is still `seat-unknown`",
              _r37.returncode == 0
              and "seat: demo-3-alpha" in (npkg / "seats" / "demo-3-alpha"
                                           / "seat.md").read_text(encoding="utf-8")
              and (npkg / TASKFORCE_NAME).read_bytes() == _r37_tf
              and json.loads(_r37.stdout).get("taskforce_rows_appended") == 0,
              f"rc={_r37.returncode} {(_r37.stdout + _r37.stderr).strip()[:300]}")
        check("INST-2 red (D37): `--refresh` AND `--force-partial` together are STILL "
              "refused `repass-with-force-partial` — widening the alias to the refresh lane "
              "did not merge the two flags. One REPLACES a descriptor deliberately, the "
              "other refuses anything that does not byte-match; they agree about the NAME "
              "and about nothing else",
              code(_invoke(["--package", nfx["pkg"], "--seat", "demo-3-alpha",
                            "--catalog-root", nfx["catalog"], "--refresh", "--root",
                            "--force-partial", "--json"], clean_env))
              == "repass-with-force-partial")

    print("GL-1 the GOAL-LOCAL seat input lane (W7 R7, adv C75)")
    with tempfile.TemporaryDirectory() as gl_td:
        glfx = build_fixture(Path(gl_td))
        gl_cat = glfx["catalog"]

        def gl_goal(name, seats, manifest_rows) -> Path:
            """A goal whose OWN planning pass authored `seats`.

            `seats` maps seat -> list of (filename, section, id) — the section
            is what makes a file the prompt half or the task half, and the
            FILENAMES are deliberately unrelated to the ids, because on the
            flagship they are (`toolsmith.md` declares id `toolsmith`, but
            `build-validate-seams.md` sits beside it and the pair is resolved by
            <role>/<task-goal>, never by name)."""
            g = Path(gl_td) / "goals" / name
            (g / "seats").mkdir(parents=True)
            (g / "coordination").mkdir(parents=True)
            (g / TASKFORCE_NAME).write_text(
                "taskforce-id,seat,after,harness,model,effort,ctx-refresh,"
                "milestone-id\ntf-1,chief,,claude,claude-opus-5,high,35,\n",
                encoding="utf-8")
            cur = g.joinpath(*GOAL_LOCAL_SOURCE)
            (cur / "seats").mkdir(parents=True)
            with (cur / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow([MANIFEST_SEAT_COLUMN, MANIFEST_AFTER_COLUMN, "i/o",
                            "Modality"])
                for seat, after in manifest_rows:
                    w.writerow([seat, after, "", ""])
            for seat, files in seats.items():
                d = cur / "seats" / seat
                d.mkdir(parents=True)
                for spec in files:
                    fname, section, ident = spec[0], spec[1], spec[2]
                    extra_fm = spec[3] if len(spec) > 3 else ""
                    if section is None:                    # a cataloged reuse
                        (d / fname).write_text(
                            f"# {seat} — reused definition, no copy\n",
                            encoding="utf-8")
                        continue
                    # The prompt half carries <permissions> beside <role> and
                    # the task half its contract sections: assembly HARD-GATES
                    # a seat with no permissions unit, and a fixture that
                    # skipped them would grade the lane against a shape no real
                    # goal-authored seat has (the flagship's do carry them).
                    extra_sections = {
                        "role": ("permissions", "outcome"),
                        "task-goal": ("scope", "done-contract"),
                    }[section]
                    body = "".join(
                        f"<{s}>\n{s} of {ident}\n</{s}>\n\n"
                        for s in (section, *extra_sections))
                    (d / fname).write_text(
                        f"---\nid: {ident}\ndescription: \"the {section} half\"\n"
                        f"{extra_fm}"
                        f"---\n\n{body}", encoding="utf-8")
            # The lane's OWN bindings sheet — the goal's seats are not in the
            # component's, and `check_bindings_cover` refuses an extra key, so
            # a shared sheet could never serve both lanes.
            gb = {"harness": "claude", "model": "claude-opus-5",
                  "effort": "high", "ctx-refresh": 50, "agent_type": "staff",
                  "description": "a goal-authored fixture seat"}
            (g / "bindings.json").write_text(json.dumps({
                "version": 1,
                "defaults": {"harness": "claude", "cwd-mode": "seat-folder",
                             "agent_type": "staff"},
                "seats": {s: {**gb, "after": [x for x in [a] if x]}
                          for s, a in manifest_rows
                          if (cur / "seats" / s / GOAL_LOCAL_REUSE).is_file()
                          is False and (cur / "seats" / s).is_dir()},
            }), encoding="utf-8")
            return g

        def gl_run(g, *extra):
            return _invoke(["--package", str(g), "--workflow",
                            GOAL_LOCAL_WORKFLOW, "--goal-local",
                            "--catalog-root", gl_cat, "--root", "--bindings",
                            str(g / "bindings.json"), "--dry-run", "--json",
                            *extra], clean_env)

        def gl_code(cp) -> str:
            try:
                return (json.loads(cp.stdout).get("refusal") or {}).get("code", "")
            except ValueError:
                return ""

        # ---- GREEN: the flagship's exact shape, reduced to two seats ---------
        g_ok = gl_goal(
            "gl-ok",
            {"tool-seat": [("smith.md", "role", "smithy"),
                           ("do-the-thing.md", "task-goal", "the-thing")],
             "next-seat": [("writer.md", "role", "scribe"),
                           ("write-it.md", "task-goal", "write-it")],
             "reused-seat": [(GOAL_LOCAL_REUSE, None, None)]},
            [("tool-seat", ""), ("next-seat", "tool-seat"),
             ("reused-seat", "next-seat")])
        cp_ok = gl_run(g_ok)
        lane = (g_ok.joinpath(*GOAL_LOCAL_SOURCE) / GOAL_LOCAL_LANE
                / GOAL_LOCAL_MODULE / GOAL_LOCAL_COMPONENT)
        gl_seats = {r["seat-id"]: r for r in _csv_rows(lane / "seats.csv")}
        gl_mf = {r[MANIFEST_SEAT_COLUMN]: r[MANIFEST_AFTER_COLUMN]
                 for r in _csv_rows(lane / "workflows" / GOAL_LOCAL_WORKFLOW
                                    / f"{GOAL_LOCAL_WORKFLOW}.csv")}
        check("GL-1 green: the goal's OWN planning product materializes — the "
              "prompt half and the task half of each seat are resolved by their "
              "<role>/<task-goal> SECTION (the filenames deliberately do not "
              "match the ids), the seats.csv is synthesized with those ids, the "
              "manifest's `after` cell is copied VERBATIM, and the CATALOGED-"
              "REUSE seat (a source.md pointer) is EXCLUDED — it belongs to the "
              "component lane and a copy here would shadow it",
              cp_ok.returncode == 0
              and set(gl_seats) == {"tool-seat", "next-seat"}
              and gl_seats["tool-seat"]["executor"] == "smithy"
              and gl_seats["tool-seat"]["task"] == "the-thing"
              and gl_seats["next-seat"]["executor"] == "scribe"
              and gl_mf == {"tool-seat": "", "next-seat": "tool-seat"},
              f"rc={cp_ok.returncode} seats={list(gl_seats)} mf={gl_mf} "
              f"[{cp_ok.stderr.strip()[:200]}]")
        check("GL-1 green: and the run assembles those seats END TO END — two "
              "descriptors and two registry rows planned, from definitions no "
              "seats.csv anywhere in the component catalog carries. That is the "
              "registered-but-unbuilt state closed at its source",
              (json.loads(cp_ok.stdout).get("added_seats")
               == ["tool-seat", "next-seat"])
              and json.loads(cp_ok.stdout).get("taskforce_rows_appended") == 2,
              cp_ok.stdout[:200])
        # ---- RED: the four checks component-lint would have made ------------
        g_miss = gl_goal("gl-miss",
                         {"tool-seat": [("s.md", "role", "smithy"),
                                        ("t.md", "task-goal", "the-thing")]},
                         [("tool-seat", ""), ("ghost-seat", "tool-seat")])
        check("GL-1 red: a manifest seat with NO definition folder REFUSES "
              "(goal-local-definition-missing) — the pass registered a seat it "
              "never authored, which is the very state this lane exists to end; "
              "materializing the rest and skipping it would rebuild it",
              gl_code(gl_run(g_miss)) == "goal-local-definition-missing")
        g_shadow = gl_goal("gl-shadow",
                           {"alpha": [("s.md", "role", "gl-smithy"),
                                      ("t.md", "task-goal", "gl-thing")]},
                           [("alpha", "")])
        check("GL-1 red: a goal-authored seat whose id the COMPONENT CATALOG "
              "already carries REFUSES (goal-local-shadows-catalog). Nothing in "
              "this system guarded that before W7: which definition won would "
              "have been decided by rglob ordering",
              gl_code(gl_run(g_shadow)) == "goal-local-shadows-catalog")
        g_dangle = gl_goal("gl-dangle",
                           {"tool-seat": [("s.md", "role", "smithy"),
                                          ("t.md", "task-goal", "the-thing")]},
                           [("tool-seat", "nobody-at-all")])
        check("GL-1 red: an `after` member naming nothing that exists REFUSES "
              "(goal-local-after-dangling) — not a lane seat, not a "
              f"{TASKFORCE_NAME} row, not a cataloged seat. The edge points at "
              "nothing and the seat would sit BLOCKED forever, which reads as a "
              "healthy waiting goal",
              gl_code(gl_run(g_dangle)) == "goal-local-after-dangling")
        g_amb = gl_goal("gl-amb",
                        {"tool-seat": [("s.md", "role", "smithy"),
                                       ("s2.md", "role", "smithy-two"),
                                       ("t.md", "task-goal", "the-thing")]},
                        [("tool-seat", "")])
        check("GL-1 red: a definition folder carrying TWO <role> files REFUSES "
              "(goal-local-definition-ambiguous) rather than picking the first "
              "— a seat is exactly one prompt and one task, and 'whichever "
              "sorted first' is not a rule",
              gl_code(gl_run(g_amb)) == "goal-local-definition-ambiguous")
        g_colide = gl_goal("gl-collide",
                           {"tool-seat": [("s.md", "role", "smithy"),
                                          ("t.md", "task-goal", "the-thing")],
                            "next-seat": [("s.md", "role", "smithy"),
                                          ("t.md", "task-goal", "other-thing")]},
                           [("tool-seat", ""), ("next-seat", "tool-seat")])
        check("GL-1 red: one id declared by TWO goal-authored seats REFUSES "
              "(goal-local-id-collision) — the catalog is a dict, so the second "
              "would silently replace the first and one seat would be assembled "
              "from the other's prompt",
              gl_code(gl_run(g_colide)) == "goal-local-id-collision")

        def gl_run_write(g, *extra):
            return _invoke(["--package", str(g), "--workflow",
                            GOAL_LOCAL_WORKFLOW, "--goal-local",
                            "--catalog-root", gl_cat, "--root", "--bindings",
                            str(g / "bindings.json"), "--json",
                            *extra], clean_env)

        g_rw = gl_goal(
            "gl-rw",
            {"rw-seat": [("p.md", "role", "rw-prompt",
                          "rw-paths:\n- some/existing/rel\n"),
                         ("t.md", "task-goal", "rw-task")]},
            [("rw-seat", "")])
        cp_rw = gl_run_write(g_rw)
        rw_lane = (g_rw.joinpath(*GOAL_LOCAL_SOURCE) / GOAL_LOCAL_LANE
                   / GOAL_LOCAL_MODULE / GOAL_LOCAL_COMPONENT)
        rw_row = {r["seat-id"]: r for r in _csv_rows(rw_lane / "seats.csv")}
        rw_md = g_rw / "seats" / "rw-seat" / "seat.md"
        rw_head = (rw_md.read_text(encoding="utf-8").split("\n---", 1)[0]
                   if rw_md.is_file() else "")
        check("GL-1 green: a fixture prompt with rw-paths lands that cell and "
              "the assembled seat.md carries it",
              cp_rw.returncode == 0
              and (rw_row.get("rw-seat") or {}).get("rw-paths")
              == "some/existing/rel"
              and "rw-paths:" in rw_head
              and "- some/existing/rel" in rw_head,
              f"rc={cp_rw.returncode} cell={(rw_row.get('rw-seat') or {}).get('rw-paths')!r} "
              f"head={rw_head[:200]!r} [{cp_rw.stderr.strip()[:200]}]")
        g_gt = gl_goal(
            "gl-rw-gt",
            {"rw-seat": [("p.md", "role", "gt-prompt",
                          "rw-paths:\n- .rbtv/goals/x\n"),
                         ("t.md", "task-goal", "gt-task")]},
            [("rw-seat", "")])
        cp_gt = gl_run_write(g_gt)
        check("GL-1 red: an rw-paths entry under .rbtv/goals is "
              "cage-rw-path-ground-truth at assemble, nothing materialized",
              gl_code(cp_gt) == "cage-rw-path-ground-truth"
              and not (g_gt / "seats" / "rw-seat").exists(),
              f"code={gl_code(cp_gt)!r} exists={(g_gt / 'seats' / 'rw-seat').exists()} "
              f"[{cp_gt.stderr.strip()[:200]}]")
        g_abs = gl_goal(
            "gl-rw-abs",
            {"rw-seat": [("p.md", "role", "abs-prompt",
                          "rw-paths:\n- /tmp/abs\n"),
                         ("t.md", "task-goal", "abs-task")]},
            [("rw-seat", "")])
        cp_abs = gl_run_write(g_abs)
        check("GL-1 red: an absolute rw-paths entry is cage-rw-path-absolute "
              "at assemble, nothing materialized",
              gl_code(cp_abs) == "cage-rw-path-absolute"
              and not (g_abs / "seats" / "rw-seat").exists(),
              f"code={gl_code(cp_abs)!r} exists={(g_abs / 'seats' / 'rw-seat').exists()} "
              f"[{cp_abs.stderr.strip()[:200]}]")

    print("MCP-1 plugin/MCP registration pass (d-mcp-registration-is-config)")
    with tempfile.TemporaryDirectory() as mcp_td:
        fxm = build_fixture(Path(mcp_td))
        common_m = ["--catalog-root", fxm["catalog"], "--root", "--json"]
        pm = _invoke(["--package", fxm["pkg"], "--seat", "mcp-seat",
                      "--bindings", fxm["b_mcp"]] + common_m, clean_env)
        seat_dir = Path(fxm["pkg"]) / "seats" / "mcp-seat"
        gen = {rel: seat_dir / rel for rel in
               (".mcp.json", ".claude/settings.json", ".codex/config.toml",
                "opencode.json")}
        check("MCP-1 green: a config-declaring component materializes all "
              "FOUR harness registration files",
              pm.returncode == 0 and all(p.is_file() for p in gen.values()),
              pm.stderr.strip()[:300])
        decl = json.loads(Path(fxm["mcp_decl"]).read_text(encoding="utf-8"))
        check("MCP-1 green: .mcp.json carries the declaration's mcpServers "
              "verbatim (the neutral shape is claude's)",
              json.loads(gen[".mcp.json"].read_text(encoding="utf-8"))
              == {"mcpServers": decl["mcpServers"]})
        check("MCP-1 green: .claude/settings.json carries the approval flag",
              json.loads(gen[".claude/settings.json"].read_text(
                  encoding="utf-8")).get("enableAllProjectMcpServers") is True)
        toml_text = gen[".codex/config.toml"].read_text(encoding="utf-8")
        check("MCP-1 green: .codex/config.toml carries the http server as "
              "url= and the stdio server as command/args/env",
              "[mcp_servers.demo-http]" in toml_text
              and 'url = "https://mcp.example.test"' in toml_text
              and "[mcp_servers.demo-stdio]" in toml_text
              and 'command = "demo-mcp-server"' in toml_text
              and 'args = ["--flag"]' in toml_text
              and "[mcp_servers.demo-stdio.env]" in toml_text
              and 'DEMO_KEY = "x"' in toml_text, toml_text[:400])
        oc = json.loads(gen["opencode.json"].read_text(encoding="utf-8"))
        check("MCP-1 green: opencode.json maps url -> remote and "
              "command -> local with `environment`",
              oc.get("mcp", {}).get("demo-http")
              == {"type": "remote", "url": "https://mcp.example.test",
                  "enabled": True}
              and oc.get("mcp", {}).get("demo-stdio")
              == {"type": "local",
                  "command": ["demo-mcp-server", "--flag"],
                  "environment": {"DEMO_KEY": "x"}, "enabled": True},
              json.dumps(oc)[:300])
        res_m = json.loads(pm.stdout) if pm.stdout.strip() else {}
        check("MCP-1 green: every generated file is DECLARED in writes[] "
              "(kind seat-harness-config) — no undisclosed write",
              {w["path"] for w in res_m.get("writes", [])
               if w.get("kind") == "seat-harness-config"}
              == {str(p) for p in gen.values()})
        pa = _invoke(["--package", fxm["pkg"], "--seat", "alpha",
                      "--bindings", fxm["b_alpha"]] + common_m, clean_env)
        check("MCP-1 green: a component with NO config declaration "
              "generates nothing (absence is normal)",
              pa.returncode == 0
              and not (Path(fxm["pkg"]) / "seats" / "alpha"
                       / ".mcp.json").exists(),
              pa.stderr.strip()[:200])
        # RED ARM — a broken declaration REFUSES pre-write: rc 1, the named
        # code, and NO seat surface materialized (zero-files refusal).
        Path(fxm["mcp_decl"]).write_text("{not json", encoding="utf-8")
        pr = _invoke(["--package", fxm["pkg9"], "--seat", "mcp-seat",
                      "--bindings", fxm["b_mcp"]] + common_m, clean_env)
        check("MCP-1 red: an unparseable declaration refuses "
              "mcp-declaration-invalid and writes NOTHING",
              pr.returncode == 1 and "mcp-declaration-invalid" in pr.stderr
              and not (Path(fxm["pkg9"]) / "seats" / "mcp-seat").exists(),
              pr.stderr.strip()[:200])

    print("EXP-1 seat-exposure loaders pass (d-materializer-seat-loaders / "
          "d-seat-exposes-frontmatter)")
    with tempfile.TemporaryDirectory() as exp_td:
        fxe = build_fixture(Path(exp_td))
        common_e = ["--catalog-root", fxe["catalog"], "--root", "--json"]
        pe = _invoke(["--package", fxe["pkg"], "--seat", "exp-seat",
                      "--bindings", fxe["b_exp"]] + common_e, clean_env)
        sd = Path(fxe["pkg"]) / "seats" / "exp-seat"
        expected = [
            ".claude/skills/brws/SKILL.md", ".agents/skills/brws/SKILL.md",
            ".claude/skills/xsk/SKILL.md", ".agents/skills/xsk/SKILL.md",
            ".claude/skills/xms/SKILL.md", ".agents/skills/xms/SKILL.md",
            ".claude/commands/cmd1.md", ".codex/prompts/cmd1.md",
            ".opencode/commands/cmd1.md",
            ".claude/rules/rul1.md", ".agents/behavior-rules/rul1.md",
            ".claude/settings.json", ".codex/hooks.json",
            ".claude/agents/res1.md", ".opencode/agents/res1.md",
            ".codex/agents/res1.toml",
        ]
        check("EXP-1 green: every declared method materializes its "
              "per-harness realization (CMP-12), sibling-component AND "
              "cross-module refs included",
              pe.returncode == 0
              and all((sd / rel).is_file() for rel in expected),
              (pe.stderr.strip()[:300]
               or str([r for r in expected if not (sd / r).is_file()])))
        check("EXP-1 green: the skill loader points at the entry file "
              "and the rule copy is VERBATIM",
              str((Path(fxe["catalog"]) / "exp-comp" / "skills"
                   / "brws.md").resolve())
              in (sd / ".claude/skills/brws/SKILL.md").read_text(
                  encoding="utf-8")
              and (sd / ".claude/rules/rul1.md").read_text(encoding="utf-8")
              == (Path(fxe["catalog"]) / "exp-comp" / "rules"
                  / "rul1.md").read_text(encoding="utf-8"))
        codex_hooks = json.loads((sd / ".codex/hooks.json").read_text(
            encoding="utf-8"))
        check("EXP-1 green: the hook declaration lands in "
              ".claude/settings.json and in .codex/hooks.json (measured "
              "codex 0.144.5 shape: claude hooks object verbatim + "
              "top-level description)",
              bool(json.loads((sd / ".claude/settings.json").read_text(
                  encoding="utf-8")).get("hooks", {}).get("PostToolUse"))
              and bool(codex_hooks.get("hooks", {}).get("PostToolUse"))
              and bool(codex_hooks.get("description")))
        check("EXP-1 green: AGENTS.md carries the forced-read rules "
              "preamble naming the behavior-rules copy",
              ".agents/behavior-rules/rul1.md"
              in (sd / "AGENTS.md").read_text(encoding="utf-8"))
        check("EXP-1 green: seat.md frontmatter carries the validated "
              "`exposes:` mapping",
              "exposes:" in (sd / "seat.md").read_text(encoding="utf-8"))
        # ── `path` — the SANDBOX-realized method (d-path-exposes-authorable) ──
        sfm = yaml.safe_load(
            _FM_RE.match((sd / "seat.md").read_text(encoding="utf-8")).group(1))
        coordfix = str(Path(fxe["repo_mod"]) / "team-kit" / "coordfix.py")
        wstool = str(Path(fxe["tmp"]) / "wsbin" / "wstool.py")
        check("EXP-1 green: a `rbtv:`-prefixed `path` ref resolves through the "
              "`.rbtv/config/` walk + rbtv.json — WITH NO install.json IN THE "
              "FIXTURE, which is the proof the install book is no longer read "
              "(IPH-6 / D33) — and lands in seat.md as `exposed-clis:`: "
              "`<part-id> <absolute entry point>`, the cage's grant surface",
              f"coordfix {coordfix}" in (sfm.get("exposed-clis") or []),
              repr(sfm.get("exposed-clis")))
        check("EXP-1 green: a `ws:`-prefixed ENTRY-POINT resolves against the "
              "WORKSPACE root (first ancestor holding .rbtv/config/) and lands "
              "absolute in `exposed-clis:` — the sanctioned way out of the "
              "component, replacing the `..` climb the ban now refuses "
              "(IPH-6 / D33). Both prefixes render one list: `rbtv:` picked a "
              "component directory, `ws:` picked a path base",
              sfm.get("exposed-clis") == [f"coordfix {coordfix}",
                                          f"wstool {wstool}"],
              repr(sfm.get("exposed-clis")))
        check("EXP-1 green: the declaration is readable by the cage's LIST "
              "reader shape (a block list of scalars under the key)",
              "\nexposed-clis:\n- coordfix "
              in (sd / "seat.md").read_text(encoding="utf-8"),
              (sd / "seat.md").read_text(encoding="utf-8")[:600])
        check("EXP-1 green: `path` mints NO harness loader — CMP-12 keeps no "
              "cell for it, so nothing is written beside seat.md for coordfix",
              not any(p.name.startswith("coordfix")
                      for p in sd.rglob("*") if p.is_file()),
              str([str(p) for p in sd.rglob("coordfix*")]))
        # ── W6 · seat -> skill -> CLI -> write-root (resolution variant B) ──
        res_e_w = json.loads(pe.stdout) if pe.stdout.strip() else {}
        wsbin = str((Path(fxe["tmp"]) / "wsbin").resolve())
        check("EXP-1 green (W6): the seat exposes skill `brws`, whose "
              "`exposes-cli:` names the `wstool` CLI, whose exposure row "
              "declares `!ws:wsbin` — and the MATERIALIZER walked that whole "
              "chain into seat.md's `cli-write-roots:`. The seat's own prompt "
              "card never names the root",
              sfm.get("cli-write-roots") == [wsbin],
              repr(sfm.get("cli-write-roots")))
        check("EXP-1 green (W6): the chain is DISCLOSED with its provenance "
              "(seat -> skill -> CLI -> root), symmetric with the pierce "
              "disclosure — a grant nobody can read is not auditable",
              any("write-root GRANTED" in w and "brws" in w and "wstool" in w
                  for w in res_e_w.get("warnings", ())),
              repr(res_e_w.get("warnings")))
        check("EXP-1 green (W6): the declaration is readable by the cage's "
              "LIST reader shape (a block list of scalars under the key)",
              f"\ncli-write-roots:\n- {wsbin}\n"
              in (sd / "seat.md").read_text(encoding="utf-8"),
              (sd / "seat.md").read_text(encoding="utf-8")[:800])
        res_e = json.loads(pe.stdout) if pe.stdout.strip() else {}
        declared = {w["path"] for w in res_e.get("writes", [])
                    if w.get("kind") == "seat-exposure"}
        on_disk = {str(sd / rel) for rel in expected}
        check("EXP-1 green: every loader is DECLARED in writes[] (kind "
              "seat-exposure) — no undisclosed write",
              declared == on_disk, str(declared ^ on_disk))
        pa = _invoke(["--package", fxe["pkg"], "--seat", "alpha",
                      "--bindings", fxe["b_alpha"]] + common_e, clean_env)
        check("EXP-1 green: a seat whose prompt declares no `exposes:` "
              "generates nothing (absence is normal)",
              pa.returncode == 0
              and not (Path(fxe["pkg"]) / "seats" / "alpha"
                       / ".claude" / "skills").exists(),
              pa.stderr.strip()[:200])
        # RED ARMS — both refuse pre-write: rc 1, the named code, NO seat
        # surface materialized (zero-files refusal).
        prompt_path = Path(fxe["exp_prompt"])
        orig = prompt_path.read_text(encoding="utf-8")
        prompt_path.write_text(orig.replace("hook: [hk1]", "hook: [rul1]"),
                               encoding="utf-8")
        pr1 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red: a group key disagreeing with the manifest's "
              "method column refuses exposes-method-mismatch and writes "
              "NOTHING (PRIN-11 — the manifest stays the one home)",
              pr1.returncode == 1 and "exposes-method-mismatch" in pr1.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pr1.stderr.strip()[:200])
        prompt_path.write_text(orig.replace("sub-agent: [res1]",
                                            "sub-agent: [ghost]"),
                               encoding="utf-8")
        pr2 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red: a dangling reference refuses exposes-ref-dangling "
              "and writes NOTHING",
              pr2.returncode == 1 and "exposes-ref-dangling" in pr2.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pr2.stderr.strip()[:200])
        # …and the SAME two refusals across the second root: a `rbtv:` ref is
        # not a bypass of the gates the own-tree grammar fires.
        prompt_path.write_text(
            orig.replace("rbtv:ignite/coordfix",
                         "rbtv:ignite/ghostcli"), encoding="utf-8")
        pr3 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red: a dangling `rbtv:` reference refuses "
              "exposes-ref-dangling and writes NOTHING",
              pr3.returncode == 1 and "exposes-ref-dangling" in pr3.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pr3.stderr.strip()[:200])
        prompt_path.write_text(
            orig.replace("rbtv:ignite/coordfix",
                         "rbtv:ignite/skillish"), encoding="utf-8")
        pr4 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red: a `rbtv:` ref whose row declares method 'skill' "
              "refuses exposes-method-mismatch under `path:` and writes "
              "NOTHING",
              pr4.returncode == 1 and "exposes-method-mismatch" in pr4.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pr4.stderr.strip()[:200])
        prompt_path.write_text(
            orig.replace("rbtv:ignite/coordfix",
                         "rbtv:coordfix"), encoding="utf-8")
        pr5 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red: a `rbtv:` ref with no directory segment refuses "
              "exposes-invalid and writes NOTHING",
              pr5.returncode == 1 and "exposes-invalid" in pr5.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pr5.stderr.strip()[:200])
        prompt_path.write_text(orig, encoding="utf-8")
        # ── W6 RED ARMS — the discovery layer and the seventh column ────────
        expc_dir = Path(fxe["catalog"]) / "exp-comp"
        skill_file = expc_dir / "skills" / "brws.md"
        orig_skill = skill_file.read_text(encoding="utf-8")
        for label, ref, code in (
                ("resolving to no row", "ghostcli", "skill-cli-dangling"),
                ("resolving to a row whose method is not `path`", "brws",
                 "skill-cli-dangling")):
            skill_file.write_text(
                orig_skill.replace("- wstool", f"- {ref}"), encoding="utf-8")
            pw = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                          "--bindings", fxe["b_exp"]] + common_e, clean_env)
            check(f"EXP-1 red (W6): an `exposes-cli:` ref {label} refuses "
                  f"{code} and writes NOTHING — the skill is the DISCOVERY "
                  "layer, exposure.csv the DECLARATION layer, and a dead "
                  "reference between them never reaches a seat",
                  pw.returncode == 1 and code in pw.stderr
                  and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
                  pw.stderr.strip()[:200])
        skill_file.write_text(orig_skill, encoding="utf-8")
        exp_manifest = expc_dir / EXPOSURE_NAME
        orig_exp_manifest = exp_manifest.read_text(encoding="utf-8")
        exp_manifest.write_text(
            orig_exp_manifest.replace(",!ws:wsbin", ",ws:wsbin"),
            encoding="utf-8")
        pwm = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red (W6): a write-root without the DANGER MARKER refuses "
              "write-root-unmarked and writes NOTHING — a write grant reaches "
              "a seat only because an author typed the marker, never because a "
              "path looked writable",
              pwm.returncode == 1 and "write-root-unmarked" in pwm.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pwm.stderr.strip()[:200])
        exp_manifest.write_text(
            orig_exp_manifest.replace(",!ws:wsbin", ",!ws:../outside"),
            encoding="utf-8")
        pwe = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red (W6): a `..`-climbing write-root refuses "
              "write-root-escape — the seventh column inherits the entry "
              "point's ban, in the same reader",
              pwe.returncode == 1 and "write-root-escape" in pwe.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pwe.stderr.strip()[:200])
        exp_manifest.write_text(orig_exp_manifest, encoding="utf-8")
        private_book = Path(fxe["tmp"]) / ".rbtv" / "config" / "private.json"
        private_book.write_text(json.dumps({"deny": ["wsbin/"]}),
                                encoding="utf-8")
        pwp = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        private_book.unlink()
        check("EXP-1 red (W6): a CLI-derived root landing on a PRIVATE-SCOPE "
              "entry refuses write-root-private and writes NOTHING — the deny "
              "list wins over a baked grant ALWAYS, and a CLI-derived root is "
              "never a pierce",
              pwp.returncode == 1 and "write-root-private" in pwp.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pwp.stderr.strip()[:200])
        # ── the `..` BAN (IPH-6 / D33) — enforced in _exposure_rows, AFTER the
        # prefix strip, so the bare climb and the prefixed climb take ONE rule.
        # The mutation is on the MANIFEST, not the prompt card: the ban covers
        # every row of every manifest read, not merely the referenced ones.
        manifest = Path(fxe["catalog"]) / "exp-comp" / EXPOSURE_NAME
        orig_manifest = manifest.read_text(encoding="utf-8")
        for label, cell in (("a bare", "../outside/x.py"),
                            ("a `ws:`-prefixed", "ws:../outside/x.py")):
            manifest.write_text(
                orig_manifest.replace("ws:wsbin/wstool.py", cell),
                encoding="utf-8")
            pr6 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                           "--bindings", fxe["b_exp"]] + common_e, clean_env)
            check(f"EXP-1 red: {label} `..`-climbing entry-point refuses "
                  "exposes-entry-escape at GENERATION time, names `ws:` as the "
                  "fix, and writes NOTHING — one rule covers both forms",
                  pr6.returncode == 1
                  and "exposes-entry-escape" in pr6.stderr
                  and "ws:" in pr6.stderr
                  and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
                  pr6.stderr.strip()[:250])
        manifest.write_text(orig_manifest, encoding="utf-8")
        # …and the root itself: a `ws:` cell under a component with no
        # `.rbtv/config/` ANYWHERE above it. Read directly — a whole materialize
        # needs a catalog, and what is under test is the one derivation.
        with tempfile.TemporaryDirectory() as ws_td:
            lone = Path(ws_td) / "lone-comp"
            lone.mkdir()
            (lone / EXPOSURE_NAME).write_text(
                "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
                "lonely,tool,path,,ws:wsbin/wstool.py,\n", encoding="utf-8")
            try:
                _exposure_rows(lone)
                ws_code = "(no refusal — the row resolved)"
            except Refuse as exc:
                ws_code = exc.code
            check("EXP-1 red: a `ws:` entry-point under a component with no "
                  "`.rbtv/config/` above it refuses ws-root-underivable — the "
                  "workspace is DERIVED, never guessed, and an underivable one "
                  "is a refusal rather than a silent join against nothing",
                  ws_code == "ws-root-underivable", ws_code)
            # …and the OTHER prefix takes the SAME walk since IPH-6 / D33.
            # This is the arm that fails if `_rbtv_repo_root` ever grows a
            # second derivation back: before the collapse it walked for the
            # install.json FILE and answered `exposes-repo-root-underivable`
            # here; one walk means one answer.
            try:
                _rbtv_repo_root(lone)
                repo_code = "(no refusal — the repo root resolved)"
            except Refuse as exc:
                repo_code = exc.code
            check("EXP-1 red: a `rbtv:` reference under that same component "
                  "takes the SAME ws-root-underivable refusal — both prefixes "
                  "share ONE workspace walk, and no install.json is consulted "
                  "to reach it",
                  repo_code == "ws-root-underivable", repo_code)
        # D86 — unprefixed refs resolve through installer scan_all (both trees).
        pxr = _invoke(["--package", fxe["pkg"], "--seat", "repo-xseat",
                       "--catalog-root", fxe["repo_xtree"], "--root", "--json",
                       "--bindings", fxe["b_repo_x"]], clean_env)
        check("EXP-1 green (D86): a repo-resident component referencing a "
              "mirror component by module/component/part resolves",
              pxr.returncode == 0
              and (Path(fxe["pkg"]) / "seats" / "repo-xseat"
                   / ".claude/skills/capture/SKILL.md").is_file(),
              pxr.stderr.strip()[:300])
        pxm = _invoke(["--package", fxe["pkg"], "--seat", "mir-xseat",
                       "--catalog-root", fxe["mirror_xtree"], "--root",
                       "--json", "--bindings", fxe["b_mir_x"]], clean_env)
        check("EXP-1 green (D86): a mirror component referencing a repo "
              "component by module/component/part resolves",
              pxm.returncode == 0
              and (Path(fxe["pkg"]) / "seats" / "mir-xseat"
                   / ".claude/skills/browse/SKILL.md").is_file(),
              pxm.stderr.strip()[:300])
        pxd = _invoke(["--package", fxe["pkg"], "--seat", "dup-xseat",
                       "--catalog-root", fxe["mirror_xtree"], "--root",
                       "--json", "--bindings", fxe["b_dup_x"]], clean_env)
        dup_skill = (Path(fxe["pkg"]) / "seats" / "dup-xseat"
                     / ".claude/skills/dpart/SKILL.md")
        mirror_entry = str((Path(fxe["tmp"]) / ".rbtv" / "mirror" / "dup"
                            / "comp" / "mirror.md").resolve())
        repo_entry = str((Path(fxe["tmp"]) / "repo" / "dup" / "comp"
                          / "repo.md").resolve())
        check("EXP-1 green (D86): a duplicate id in both trees resolves to "
              "the MIRROR copy",
              pxd.returncode == 0 and dup_skill.is_file()
              and mirror_entry in dup_skill.read_text(encoding="utf-8")
              and repo_entry not in dup_skill.read_text(encoding="utf-8"),
              (pxd.stderr.strip()[:300]
               or (dup_skill.read_text(encoding="utf-8")[:240]
                   if dup_skill.is_file() else "missing")))
        pxg = _invoke(["--package", fxe["pkg9"], "--seat", "miss-xseat",
                       "--catalog-root", fxe["mirror_xtree"], "--root",
                       "--json", "--bindings", fxe["b_miss_x"]], clean_env)
        check("EXP-1 red (D86): a reference to an id in neither tree refuses "
              "naming both roots",
              pxg.returncode == 1 and "exposes-ref-dangling" in pxg.stderr
              and "ghost/mod" in pxg.stderr
              and ".rbtv/mirror" in pxg.stderr
              and "repo" in pxg.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "miss-xseat").exists(),
              pxg.stderr.strip()[:350])

    print("RF-1 --refresh: bring an existing seat folder to the catalog's shape")
    with tempfile.TemporaryDirectory() as rf_td:
        tmp_rf = Path(rf_td)
        fxr = build_fixture(tmp_rf)
        common_r = ["--catalog-root", fxr["catalog"], "--seat", "exp-seat",
                    "--refresh", "--json"]
        # A STANDING-SEAT home: the package IS the seat folder, named `_<seat>`
        # (.rbtv/goals/_channel-master/ is the live one). Its descriptor carries
        # the bindings the refresh RECOVERS — no --bindings argument is passed
        # anywhere in this row, deliberately.
        home = tmp_rf / "goals" / "_exp-seat"
        home.mkdir(parents=True)
        authored = (
            "---\n"
            "seat: exp-seat\n"
            "description: the exposure seat\n"
            f"cwd: {home}/\n"
            "agent_type: worker\n"
            "mode: one-shot\n"
            "relays: alpha\n"
            "---\n\n<role>\nstale body\n</role>\n")
        (home / "seat.md").write_text(authored, encoding="utf-8")
        pr = _invoke(["--package", str(home)] + common_r, clean_env)
        loaders = [".claude/skills/brws/SKILL.md",
                   ".agents/skills/brws/SKILL.md", "AGENTS.md", "seat.md"]
        fresh = (home / "seat.md").read_text(encoding="utf-8")
        check("RF-1 green: --refresh rewrites seat.md AND the seat-folder "
              "surfaces at the STANDING-SEAT package root, with no --bindings "
              "and no insertion point",
              pr.returncode == 0
              and all((home / rel).is_file() for rel in loaders)
              and fresh != authored and "stale body" not in fresh,
              (pr.stderr.strip()[:300]
               or str([r for r in loaders if not (home / r).is_file()])))
        check("RF-1 green: the bindings were RECOVERED from the descriptor it "
              "replaced — nothing invented, and a value only the old file "
              "held survives the render",
              "relays: alpha" in fresh and "agent_type: worker" in fresh
              and "mode: one-shot" in fresh,
              fresh.split("\n---", 1)[0][:300])
        stamps = {rel: (home / rel).read_bytes() for rel in loaders
                  if (home / rel).is_file()}
        pr_again = _invoke(["--package", str(home)] + common_r, clean_env)
        check("RF-1 green: a second --refresh is byte-identical — the act is "
              "idempotent, never a collision refusal",
              pr_again.returncode == 0
              and all((home / rel).read_bytes() == b
                      for rel, b in stamps.items()),
              pr_again.stderr.strip()[:200])
        # THE GUARD. A descriptor may carry an authored key the catalog cannot
        # produce — the seat cage was exactly that until it was given a home —
        # and a silent drop is how a Slack route came to read as working while
        # being inert (daf2f140b). Refuse, naming the key.
        held = fresh.replace("relays: alpha\n",
                             "relays: alpha\nhand-authored-knob: keep-me\n")
        (home / "seat.md").write_text(held, encoding="utf-8")
        pr_drop = _invoke(["--package", str(home)] + common_r, clean_env)
        check("RF-1 red: a refresh that would REMOVE a key the descriptor "
              "carries refuses refresh-would-drop-keys, NAMES it, and leaves "
              "the file byte-untouched",
              pr_drop.returncode == 1
              and "refresh-would-drop-keys" in pr_drop.stderr
              and "hand-authored-knob" in pr_drop.stderr
              and (home / "seat.md").read_text(encoding="utf-8") == held,
              pr_drop.stderr.strip()[:250])
        (home / "seat.md").write_text(fresh, encoding="utf-8")
        # SC-EMIT — the anti-drift arm: EMITTER_OWNED_KEYS is a hand-written
        # literal, so it is only worth anything if it COVERS what the emitter
        # actually writes. Measured against a real render, not against the
        # emitter's own source.
        emitted = set(yaml.safe_load(fresh.split("\n---", 1)[0]
                                     .lstrip("-\n")) or {})
        check("RF-1 green: EMITTER_OWNED_KEYS covers every key a real render "
              "emits — an emitted key nobody listed turns this red",
              emitted <= EMITTER_OWNED_KEYS,
              str(sorted(emitted - EMITTER_OWNED_KEYS)))
        # The case the first guard got wrong: a DELIBERATE removal in the
        # catalog must APPLY, not refuse. Drop a cage grant and refresh.
        cat_seats = Path(fxr["catalog"]) / "exp-comp" / "seats.csv"
        seats_before = cat_seats.read_text(encoding="utf-8")
        assert "local-bin" in fresh, fresh[:200]
        cat_seats.write_text(
            seats_before.replace("read-root bus-write local-bin",
                                 "read-root bus-write"), encoding="utf-8")
        pr_rm = _invoke(["--package", str(home)] + common_r, clean_env)
        after_rm = (home / "seat.md").read_text(encoding="utf-8")
        check("RF-1 green: removing a grant from the CATALOG applies — an "
              "emitter-owned key may come and go, and refusing a deliberate "
              "removal is what the first version of this guard did",
              pr_rm.returncode == 0
              and "local-bin" not in after_rm.split("\n---", 1)[0]
              and "bus-write: true" in after_rm,
              (pr_rm.stderr.strip()[:200] or after_rm.split("\n---", 1)[0][:300]))
        cat_seats.write_text(seats_before, encoding="utf-8")
        _invoke(["--package", str(home)] + common_r, clean_env)
        # SC-EMIT-HI (task 7.640): `human-interactive`/`fallback` arrive via
        # the assembler's frontmatter pass-through (goal_cli.py#assemble_seat
        # reads them off a `d-prompt-task-files` whole-file prompt card, never
        # via a binding) — the same shape as the cage-grant case above, so a
        # DELIBERATE un-declaration in the catalog's own prompt card must
        # APPLY on --refresh, never refuse as if a human had hand-typed the
        # line. Own dedicated pool component: the whole-file `exposes:` CARD
        # `exp-comp/prompts/alpha-prompt.md` uses above is NOT a definition
        # (no kind-named section — `_pool_file_row` returns it as a card, and
        # assembly still resolves the CSV-driven `alpha-prompt` row for exp-
        # seat's actual content) — human-interactive is only ever read off a
        # d-prompt-task-files DEFINITION file, so this arm needs its own.
        hi_comp = Path(fxr["catalog"]) / "hi-comp"
        (hi_comp / "prompts").mkdir(parents=True)
        (hi_comp / "tasks").mkdir(parents=True)
        (hi_comp / "seats.csv").write_text(
            "seat-id,prompt-id,task-id,staffing-hints,description\n"
            "hi-seat,hi-prompt,hi-task,,the hi seat\n",
            encoding="utf-8")
        hi_prompt = hi_comp / "prompts" / "hi-prompt.md"
        hi_declared = (
            "---\nid: hi-prompt\ndescription: hi fixture prompt\n"
            "human-interactive: yes\nfallback: block-and-queue\n---\n\n"
            "<role>\nYou are the hi seat.\n</role>\n\n"
            "<permissions>\nRead the fixture tree.\n</permissions>\n")
        hi_prompt.write_text(hi_declared, encoding="utf-8")
        (hi_comp / "tasks" / "hi-task.md").write_text(
            "---\nid: hi-task\ndescription: hi fixture task\n---\n\n"
            "<task-goal>\nProve the human-interactive pass-through.\n"
            "</task-goal>\n", encoding="utf-8")
        hi_home = tmp_rf / "goals" / "_hi-seat"
        hi_home.mkdir(parents=True)
        (hi_home / "seat.md").write_text(
            "---\nseat: hi-seat\ndescription: the hi seat\n"
            f"cwd: {hi_home}/\nagent_type: worker\nmode: one-shot\n"
            "---\n\n<role>\nstale body\n</role>\n", encoding="utf-8")
        common_hi = ["--catalog-root", fxr["catalog"], "--seat", "hi-seat",
                     "--refresh", "--json"]
        pr_hi0 = _invoke(["--package", str(hi_home)] + common_hi, clean_env)
        with_hi = (hi_home / "seat.md").read_text(encoding="utf-8")
        check("RF-1 green: a seat whose catalog prompt declares "
              "human-interactive carries it (+ fallback) into the emitted "
              "descriptor — the pass-through EMITTER_OWNED_KEYS now covers",
              pr_hi0.returncode == 0
              and "human-interactive: true" in with_hi.split("\n---", 1)[0]
              and "fallback: block-and-queue" in with_hi.split("\n---", 1)[0],
              (pr_hi0.stderr.strip()[:200]
               or with_hi.split("\n---", 1)[0][:300]))
        emitted_hi = set(yaml.safe_load(with_hi.split("\n---", 1)[0]
                                        .lstrip("-\n")) or {})
        check("SC-EMIT-HI: EMITTER_OWNED_KEYS covers this render too — "
              "extends SC-EMIT's coverage to the human-interactive/fallback "
              "pair now that a fixture actually declares them (task 7.640)",
              emitted_hi <= EMITTER_OWNED_KEYS,
              str(sorted(emitted_hi - EMITTER_OWNED_KEYS)))
        # Now the deliberate un-declaration: drop it from the CATALOG's
        # prompt card and refresh — this MUST apply, not refuse.
        hi_prompt.write_text(
            "---\nid: hi-prompt\ndescription: hi fixture prompt\n---\n\n"
            "<role>\nYou are the hi seat.\n</role>\n\n"
            "<permissions>\nRead the fixture tree.\n</permissions>\n",
            encoding="utf-8")
        pr_hi = _invoke(["--package", str(hi_home)] + common_hi, clean_env)
        after_hi = (hi_home / "seat.md").read_text(encoding="utf-8")
        check("RF-1 green: un-declaring human-interactive in the catalog's "
              "prompt card APPLIES on --refresh (exit 0, key + fallback "
              "gone) instead of refusing refresh-would-drop-keys — the "
              "misclassification the guard was corrected for with the cage "
              "grants, now proven for this pair too (task 7.640)",
              pr_hi.returncode == 0
              and "human-interactive:" not in after_hi.split("\n---", 1)[0]
              and "fallback:" not in after_hi.split("\n---", 1)[0],
              (pr_hi.stderr.strip()[:200]
               or after_hi.split("\n---", 1)[0][:300]))
        hi_prompt.write_text(hi_declared, encoding="utf-8")
        # ── F5: the INTERACTIVE-SEAT expose injection ──────────────────────
        # A seat marked human-interactive picks up the WORKSPACE-configured
        # skill parts with nothing added to its own frontmatter, and an
        # install carrying no such config renders BYTE-IDENTICALLY to before —
        # the two halves of the acceptance criterion, proven against the same
        # descriptor rather than against two counts of it.
        (hi_comp / "references").mkdir(parents=True, exist_ok=True)
        (hi_comp / "references" / "etq.md").write_text(
            "# etq\n\nFixture etiquette reference.\n", encoding="utf-8")
        (hi_comp / EXPOSURE_NAME).write_text(
            "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
            "etq,reference,skill,,references/etq.md,fixture etiquette\n",
            encoding="utf-8")
        _invoke(["--package", str(hi_home)] + common_hi, clean_env)
        base_hi = (hi_home / "seat.md").read_text(encoding="utf-8")
        book = tmp_rf / INTERACTIVE_EXPOSES_REL
        book.parent.mkdir(parents=True, exist_ok=True)
        book.write_text(json.dumps(["hi-comp/etq"]) + "\n", encoding="utf-8")
        pr_f5 = _invoke(["--package", str(hi_home)] + common_hi, clean_env)
        inj_hi = (hi_home / "seat.md").read_text(encoding="utf-8")
        loader = hi_home / ".claude" / "skills" / "etq" / "SKILL.md"
        check("F5-ETQ: an interactive seat with the workspace config present "
              "gets the configured skill part injected — it reaches the "
              "emitted `exposes:` and mints its loader, with NOTHING declared "
              "in the seat's own prompt frontmatter",
              pr_f5.returncode == 0
              and "hi-comp/etq" in (yaml.safe_load(
                  inj_hi.split("\n---", 1)[0].lstrip("-\n")) or {}
                  ).get("exposes", {}).get("skill", [])
              and loader.is_file()
              and str((hi_comp / "references" / "etq.md").resolve())
              in loader.read_text(encoding="utf-8"),
              (pr_f5.stderr.strip()[:200]
               or inj_hi.split("\n---", 1)[0][:300]))
        # The DISCRIMINATOR: the injection is keyed on the marker, not applied
        # to every seat. exp-seat is not interactive and the same config is in
        # place — without this arm, "inject into everything" passes too.
        _invoke(["--package", str(home)] + common_r, clean_env)
        check("F5-ETQ control: a NON-interactive seat gets no injection "
              "while the "
              "same config is present — the `human-interactive:` marker is "
              "what keys it",
              "etq" not in (Path(home) / "seat.md").read_text(
                  encoding="utf-8").split("\n---", 1)[0],
              (Path(home) / "seat.md").read_text(
                  encoding="utf-8").split("\n---", 1)[0][:300])
        book.unlink()
        pr_f5o = _invoke(["--package", str(hi_home)] + common_hi, clean_env)
        check("F5-ETQ: config ABSENT is a silent no-op — the descriptor is "
              "byte-identical to the pre-config render, so an install without "
              "the convention keeps today's behaviour exactly",
              pr_f5o.returncode == 0
              and (hi_home / "seat.md").read_text(encoding="utf-8") == base_hi,
              (pr_f5o.stderr.strip()[:200] or "descriptor drifted"))
        # The manifest-comment control: browse/exposure.csv leads with a prose
        # header block, and a plain DictReader takes that line for the header —
        # every part-id then reads absent and the ref refuses as dangling.
        comp = tmp_rf / "commented-comp"
        comp.mkdir()
        (comp / EXPOSURE_NAME).write_text(
            "# a prose header block, the live exposure-manifest shape\n"
            "# second comment line\n"
            "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
            "brws,capability,skill,,skills/brws.md,browse\n", encoding="utf-8")
        check("RF-1 green: an exposure manifest led by `#` comment lines "
              "still resolves its part-ids (a DictReader that reads the "
              "comment as the header reports every row absent)",
              list(_exposure_rows(comp)) == ["brws"],
              str(list(_exposure_rows(comp))))
        ghost = tmp_rf / "goals" / "_ghost-seat"
        ghost.mkdir(parents=True)
        pr_red = _invoke(["--package", str(ghost), "--catalog-root",
                          fxr["catalog"], "--seat", "exp-seat", "--refresh",
                          "--json"], clean_env)
        check("RF-1 red: --refresh RECOVERS bindings from an existing "
              "descriptor — with none to read it refuses refresh-no-descriptor "
              "and writes NOTHING, rather than inventing a binding",
              pr_red.returncode == 1
              and "refresh-no-descriptor" in pr_red.stderr
              and not (ghost / "seat.md").exists()
              and not (ghost / ".claude").exists(),
              pr_red.stderr.strip()[:200])
        pr_mint = _invoke(["--package", str(home), "--catalog-root",
                           fxr["catalog"], "--seat", "exp-seat", "--root",
                           "--bindings", fxr["b_exp"], "--json"], clean_env)
        check("RF-1 red: a PLAIN materialize into a standing-seat home is "
              "refused — it would append a taskforce.csv row to a package "
              "that has no registry",
              pr_mint.returncode == 1
              and "standing-seat-plain-materialize" in pr_mint.stderr,
              pr_mint.stderr.strip()[:200])
        # ── the OPEN BINDING: a standing seat may omit harness·model·effort.
        # The recovered binding above already omits all three (the authored
        # descriptor never carried them), so the rendered file must too.
        rfm = (home / "seat.md").read_text(encoding="utf-8").split("\n---", 1)[0]
        check("RF-1 green: a standing seat's OPEN binding omits harness, "
              "model and effort from the descriptor ENTIRELY — absent, never "
              "empty, because an empty value reads as a binding that failed",
              not any(re.search(rf"^{k}:", rfm, re.M)
                      for k in ("harness", "model", "effort"))
              and re.search(r"^mode:", rfm, re.M) is not None,
              rfm[:300])
        raw = json.loads(Path(fxr["b_exp"]).read_text(encoding="utf-8"))
        entry = raw["seats"]["exp-seat"]
        for k in ("model", "effort", "ctx-refresh"):
            entry.pop(k, None)
        raw.get("defaults", {}).pop("harness", None)
        entry["harness"], entry["mode"] = "claude", "one-shot"
        b_half = tmp_rf / "b-half.json"
        b_half.write_text(json.dumps(raw), encoding="utf-8")
        before_half = (home / "seat.md").read_text(encoding="utf-8")
        pr_half = _invoke(["--package", str(home), "--catalog-root",
                           fxr["catalog"], "--seat", "exp-seat", "--root",
                           "--bindings", str(b_half), "--repass", "--json"],
                          clean_env)
        check("RF-1 red: HALF a triple is refused open-binding-partial — a "
              "descriptor carrying a harness but no model reads as a binding "
              "that was made, and sends a reader hunting the missing half",
              pr_half.returncode == 1
              and "open-binding-partial" in pr_half.stderr
              and (home / "seat.md").read_text(encoding="utf-8") == before_half,
              pr_half.stderr.strip()[:200])

    print("D50 master-prompt: access-wide/file-don't-fix sentence is pinned by refresh")
    with tempfile.TemporaryDirectory() as d50_td:
        # A master-shaped fixture, standing in for the real deployed
        # `.rbtv/mirror/meta/master/prompts/*.md` catalog this scenario
        # exists to pin (decisions.md D50/D62) — this repo carries no
        # per-instance workspace paths (root CLAUDE.md § "RBTV Content Must
        # Be General"), so the pin is proven against a portable fixture that
        # reproduces the exact retired phrasing and the exact replacement
        # shape, never against one deployment's real files.
        tmp_d50 = Path(d50_td)
        d50_catalog = tmp_d50 / "catalog"
        d50_comp = d50_catalog / "d50-master-comp"
        (d50_comp / "prompts").mkdir(parents=True)
        (d50_comp / "tasks").mkdir(parents=True)
        (d50_comp / "seats.csv").write_text(
            "seat-id,prompt-id,task-id,staffing-hints,description\n"
            "d50-seat,d50-prompt,d50-task,,the D50 fixture master seat\n",
            encoding="utf-8")
        (d50_comp / "tasks" / "d50-task.md").write_text(
            "---\nid: d50-task\ndescription: D50 fixture task\n---\n\n"
            "<task-goal>\nProve the D50 access/procedure sentence is pinned.\n"
            "</task-goal>\n", encoding="utf-8")
        d50_prompt = d50_comp / "prompts" / "d50-prompt.md"
        # The retired D49 "sentence pair" (decisions.md#d50 quotes it
        # verbatim: "Write the whole workspace … the rbtv repo"; "owner-ruled
        # descriptor/config edits you EXECUTE") — reproduced here as fixture
        # text, split across <permissions> and <constraints> exactly as the
        # real goal-master-prompt.md / channel-master-prompt.md carried it.
        old_declared = (
            "---\nid: d50-prompt\ndescription: D50 fixture prompt, pre-fix\n"
            "---\n\n<role>\nYou are the D50 fixture master seat.\n</role>\n\n"
            "<permissions>\n"
            "- Write the whole workspace: this goal's seats and descriptors, "
            "permission files, config, the rbtv repo.\n"
            "- When the owner rules a descriptor or config edit, EXECUTE it "
            "yourself.\n"
            "</permissions>\n\n"
            "<constraints>\nOwner-ruled descriptor/config edits you EXECUTE; "
            "do not route those to the owner's hands.\n</constraints>\n")
        new_declared = (
            "---\nid: d50-prompt\ndescription: D50 fixture prompt, post-fix\n"
            "---\n\n<role>\nYou are the D50 fixture master seat.\n</role>\n\n"
            "<permissions>\n"
            "- You may read and write anywhere in the workspace, including "
            "the rbtv repo, but you do NOT edit ignite/daemon code unless "
            "explicitly instructed by the owner; your standard procedure on "
            "a system defect is to file it at: `/example/workspace/"
            "loose-ends.md`.\n"
            "</permissions>\n\n"
            "<constraints>\nNone beyond the permissions above.\n"
            "</constraints>\n")
        d50_prompt.write_text(old_declared, encoding="utf-8")
        home = tmp_d50 / "goals" / "_d50-seat"
        home.mkdir(parents=True)
        (home / "seat.md").write_text(
            "---\nseat: d50-seat\ndescription: the D50 fixture master seat\n"
            f"cwd: {home}/\nagent_type: master\nmode: one-shot\n"
            "---\n\n<role>\nstale body\n</role>\n", encoding="utf-8")
        common_d50 = ["--catalog-root", str(d50_catalog), "--seat", "d50-seat",
                      "--refresh", "--json"]
        pr_old = _invoke(["--package", str(home)] + common_d50, clean_env)
        rendered_old = (home / "seat.md").read_text(encoding="utf-8")
        forbidden = ("Write the whole workspace", "you EXECUTE")
        check("D50 red: a master-shaped seat still carrying the retired D49 "
              "'Write the whole workspace' / '...you EXECUTE' phrasing after "
              "--refresh is CAUGHT — this is the regression D50's own fix "
              "closed, and the case this scenario exists to pin (D62)",
              pr_old.returncode == 0
              and any(p in rendered_old for p in forbidden)
              and "file it at:" not in rendered_old,
              rendered_old[:300])
        d50_prompt.write_text(new_declared, encoding="utf-8")
        pr_new = _invoke(["--package", str(home)] + common_d50, clean_env)
        rendered_new = (home / "seat.md").read_text(encoding="utf-8")
        check("D50 green: replacing the catalog's D49 execute/write phrasing "
              "with the ruled access-wide/file-don't-fix sentence clears on "
              "--refresh — the new sentence lands and neither retired phrase "
              "survives",
              pr_new.returncode == 0
              and not any(p in rendered_new for p in forbidden)
              and "file it at:" in rendered_new,
              rendered_new[:300])

    print("CG-1 seat cage: the sandbox declaration emitted from the catalog row")
    with tempfile.TemporaryDirectory() as cg_td:
        tmp_cg = Path(cg_td)
        fxc = build_fixture(tmp_cg)
        common_c = ["--catalog-root", fxc["catalog"], "--seat", "exp-seat",
                    "--root", "--json"]
        seats_csv = Path(fxc["catalog"]) / "exp-comp" / "seats.csv"
        base = seats_csv.read_text(encoding="utf-8")
        pc = _invoke(["--package", fxc["pkg"], "--bindings", fxc["b_exp"]]
                     + common_c, clean_env)
        md = (Path(fxc["pkg"]) / "seats" / "exp-seat" / "seat.md")
        head = md.read_text(encoding="utf-8").split("\n---", 1)[0] \
            if md.is_file() else ""
        # The emitted file IS the spawner's input: spawn.js reads these keys
        # back out of it with `^<key>:\s*true$` and a `^\s*-\s*(.*)$` block
        # list. Declared grants present, undeclared ones ABSENT — absence is
        # the mechanism, so a stray `true` is a mount nobody asked for.
        want = ["read-root: true", "bus-write: true", "local-bin: true",
                "rw-paths:", "- 1-projects"]
        unwanted = ["goals-write:", "tmux-socket:", "gateway-env:",
                    "keep-instruction-files:"]
        check("CG-1 green: the cage the seat's catalog row declares is emitted "
              "into seat.md in the shape spawn.js parses, and the grants it "
              "does NOT declare are ABSENT rather than false",
              pc.returncode == 0
              and all(w in head for w in want)
              and not any(u in head for u in unwanted),
              (pc.stderr.strip()[:200]
               or str([w for w in want if w not in head])
               + str([u for u in unwanted if u in head]))) 
        check("CG-1 green: a standing-seat descriptor's cwd is the PACKAGE "
              "itself, not <package>/seats/<seat>/",
              str(seat_home(Path(tmp_cg) / "goals" / "_exp-seat", "exp-seat"))
              == str(Path(tmp_cg) / "goals" / "_exp-seat"),
              str(seat_home(Path(tmp_cg) / "goals" / "_exp-seat", "exp-seat")))
        # The generation-time preflight, asserted against the LIVE cage template
        # rather than a fixture: the gate is worth exactly as much as its
        # agreement with `envelope/spawn-profiles.yaml`, so this row goes red the
        # day the ledger carve, the goal-writes line or the ground-truth carve
        # leaves that file — which is the one way the gate could start passing
        # seats the sandbox will refuse.
        gw_writable = [*WRITE_IF_SOMETHING, "goal.md", "taskforce.csv",
                       "sessions.csv", "state.csv", "coordination/messages.md"]
        gw_refused = ["seats/peer/seat.md", "seats/peer/outputs/x.md"]
        check("CG-1 green: the preflight reads the live cage template — D3: the "
              "goal folder (ledgers, sessions.csv, coordination) is RW; a peer "
              "seat's folder is still ABSENT",
              all(_cage_rw_covers(p) for p in gw_writable)
              and not any(_cage_rw_covers(p) for p in gw_refused),
              str([p for p in gw_writable if not _cage_rw_covers(p)])
              + str([p for p in gw_refused if _cage_rw_covers(p)]))
        # d-s31-planning-workspace-shared-rw: the cage template opens the planning workspace
        # read-write. Read through the SAME preflight a goal-writes declaration goes through,
        # against the LIVE spawn-profiles.yaml — deleting or shadowing the line turns this red
        # rather than turning a seat's workspace silently absent at spawn.
        check("CG-1 green: the planning workspace is READ-WRITE in the seat cage",
              _cage_rw_covers("planning/current/findings-edges.md"))
        for bad, code in (
                ("read-root ghost-grant,1-projects", "cage-grant-unknown"),
                ("read-root,/abs/path", "cage-rw-path-absolute"),
                ("read-root,.rbtv/goals/x", "cage-rw-path-ground-truth")):
            seats_csv.write_text(
                base.replace("read-root bus-write local-bin,1-projects", bad),
                encoding="utf-8")
            pr = _invoke(["--package", fxc["pkg9"], "--bindings", fxc["b_exp"]]
                         + common_c, clean_env)
            check(f"CG-1 red: a bad cage declaration refuses {code} and "
                  "writes NOTHING — spawn.js only warns-and-drops, which is "
                  "right at spawn time and blind at authoring time",
                  pr.returncode == 1 and code in pr.stderr
                  and not (Path(fxc["pkg9"]) / "seats" / "exp-seat").exists(),
                  pr.stderr.strip()[:200])
        seats_csv.write_text(base, encoding="utf-8")

        # ── CG-2: the DERIVED write surface reaches the occupant ────────────
        # `_cage_rw_covers` (CG-1 above) proves the DECLARED path is writable.
        # That gate held and the plan-interviewer still lost a night to EROFS
        # (2026-08-11), because a file bound inside `ro-bind:{goalDir}` cannot
        # take the sibling temp file `Write`/`Edit` create. These arms assert
        # the descriptor now HANDS the occupant both halves: which paths are
        # writable, and what the temp-file EROFS actually means.
        body = md.read_text(encoding="utf-8") if md.is_file() else ""
        agents_md = md.parent / "AGENTS.md"
        pointer = agents_md.read_text(encoding="utf-8") \
            if agents_md.is_file() else ""
        surface = _cage_write_surface("exp-seat", [])
        check("CG-2 green: seat.md carries the DERIVED write surface — D3: the "
              "goal folder itself (`.`) and the seat's own folder, read out of "
              "the live cage template",
              all(p in surface for p in (".", "seats/exp-seat"))
              and all(f"- `{p}`" in body for p in surface),
              str(surface))
        check("CG-2 green: ...and sessions.csv IS writable via the goal-folder "
              "opening (D3: record forgery is a non-goal)",
              _cage_rw_covers("sessions.csv") and _cage_rw_covers("state.csv"),
              str(surface))
        check("CG-2 green: BOTH surfaces name the D3 goal-folder opening — the "
              "descriptor and the AGENTS.md pointer",
              "whole folder" in body
              and "whole folder" in pointer,
              f"seat.md={'whole folder' in body} "
              f"AGENTS.md={'whole folder' in pointer}")
        carved = list(_seat_binds()) + ["ro-bind-try:{goalDir}/sessions.csv"]
        carved_verdict = cagespec.evaluate(carved, "sessions.csv",
                                           seat="exp-seat")[0]
        check("CG-2 red: a sessions.csv ro-carve AFTER the goal-folder bind "
              "takes the write back — last-bind-wins still holds",
              carved_verdict != cagespec.WRITABLE,
              str(carved_verdict))
        check("CG-2 red: a template that composes nothing yields an EMPTY "
              "surface — the 'nothing' branch is reachable, so a non-empty "
              "list above is a measurement and not the only possible output",
              _cage_write_surface("exp-seat", [], binds=[]) == []
              and _cage_write_surface("exp-seat", [],
                                      binds=["bind:{grant:unknownThing}"]) == [])

        # ── CG-3: the UNCAGED branch of that same section ───────────────────
        # B15. The block above is composed from the WORKER template, and it was
        # emitted for EVERY seat — including the three the sandbox is never
        # built for. A `goal-master` read that its write surface was `.` plus
        # its own folder and that `seat.md` was read-only, under a header
        # saying the section outranks any prose that disagrees; the prose that
        # disagreed (D49: "you may read and write anywhere in the workspace")
        # was the true half. These arms assert the two branches exist, that the
        # chooser DISCRIMINATES, and that the roster is read and not restated.
        roster = _staff_uncaged_seats()
        uncaged = {s_: _write_surface_section(s_, []) for s_ in sorted(roster)}
        caged = _write_surface_section("exp-seat", [])
        check("CG-3 green: the uncaged roster is READ from envelope/launch.js "
              "and carries all three staff roles — not restated here, and not "
              "coord.STAFF_SEATS (which is ('leader',) by D24)",
              roster >= {"leader", "goal-master", "channel-master"},
              str(sorted(roster)))
        check("CG-3 green: every uncaged staff seat's section says UNCAGED and "
              "forbids NOTHING — no bind enumeration, no read-only seat.md, no "
              "absent peer folders",
              all("runs UNCAGED" in t
                  and "- `.`" not in t
                  and "stays read-only" not in t
                  and "Peer seat folders are absent" not in t
                  for t in uncaged.values()),
              str([s_ for s_, t in uncaged.items()
                   if "runs UNCAGED" not in t]))
        check("CG-3 green: it still carries the priority sentence, because it "
              "is still the measured half — and now the prose it outranks "
              "AGREES with it",
              all("THIS SECTION IS RIGHT" in t for t in uncaged.values()))
        check("CG-3 red: a CAGED seat still gets the enumerated block — the "
              "chooser discriminates, so the uncaged text is not simply always "
              "emitted",
              "runs UNCAGED" not in caged
              and "- `.`" in caged and "stays read-only" in caged,
              caged[:120])
        refusals = []
        for bad in ("const STAFF = 1;", "const STAFF = new Set([]);"):
            try:
                _staff_uncaged_seats(src=bad)
                refusals.append("NO REFUSAL")
            except Refuse as exc:
                refusals.append(exc.code)
        check("CG-3 red: a reshaped or empty roster REFUSES rather than "
              "falling back to the caged text — the silent fallback IS the "
              "defect, so it must not be reachable",
              refusals == ["uncaged-roster-unparseable"] * 2,
              str(refusals))

        # ── CG-4: the SAME false-cage framing, in the seat GUIDANCE file ────
        # `_SEAT_GUIDANCE_MD` (CLAUDE.md/AGENTS.md) told every seat, uncaged
        # staff included, that "the cage makes peer seat folders ABSENT" and
        # that the write-surface section is "derived from the cage itself" —
        # both false for a seat no cage is ever composed for (CG-3 already
        # proved the DERIVED section knows better). `_seat_guidance_notes`
        # is the chooser; these arms prove it discriminates the same way.
        guidance_uncaged = {s_: _seat_guidance_notes(s_) for s_ in sorted(roster)}
        guidance_caged = _seat_guidance_notes("exp-seat")
        check("CG-4 green: every uncaged staff seat's guidance says UNCAGED "
              "and never blames a cage for the peer-folder norm or the "
              "write-surface section",
              all("UNCAGED" in peer and "UNCAGED" in surface
                  and "the cage makes peer seat folders ABSENT" not in peer
                  and "derived from the cage itself" not in surface
                  and "Peer seat folders are absent" not in surface
                  for peer, surface in guidance_uncaged.values()),
              str([s_ for s_, (peer, surface) in guidance_uncaged.items()
                   if "UNCAGED" not in peer or "UNCAGED" not in surface]))
        check("CG-4 red: a CAGED seat still gets the cage-attributed wording "
              "— the chooser discriminates, so the uncaged text is not "
              "simply always emitted",
              "UNCAGED" not in guidance_caged[0]
              and "the cage makes peer seat folders ABSENT" in guidance_caged[0]
              and "derived from the cage itself" in guidance_caged[1],
              str(guidance_caged)[:160])

    print("dag-04 acceptance pass (SC rows, each with its failing control)")
    run_dag04_acceptance(check, clean_env)

    print("dag-05 acceptance pass (SC-1/5/6/8/9/10/15/20/21, both arms each)")
    run_dag05_acceptance(check, clean_env)

    print("dag-06 acceptance pass (CP-1..CP-8, both arms each)")
    run_dag06_acceptance(check, clean_env)

    print("pass-folder acceptance pass (PF-1/PF-2/PF-3/PF-4 — B4, B5, "
          "G-planner-0804-1502, task 7.678; both arms each)")
    run_pass_substitution_acceptance(check)

    print("staff-chair acceptance pass (SM-1..SM-9 — W3: the chair a stalled "
          "seat reaches is a taskforce row, minted with the goal; SM-8/SM-9 "
          "add the pure-completion id read W7's goal-local lane needs)")
    run_staff_mint_acceptance(check)

    print("\ndag-07 row rollup — one line per acceptance row; a row passes "
          "only when BOTH arms pass (R-6/AS-2)")
    _, pre_failing = rollup_rows(records)
    # AS-2 green arm: no row reports a single verdict — every row's two arms
    # each matched at least one executed check (the AS-2 row itself is
    # excluded here: its own two checks are the two being run right now).
    check("AS-2 green: every rollup row reports BOTH arms — no green-only "
          "row, no arm without a matching check",
          not any("no check matched" in why
                  for row, why in pre_failing.items() if row != "AS-2"),
          str({row: why for row, why in pre_failing.items()
               if row != "AS-2" and "no check matched" in why}))
    # AS-2 control: strip SC-2's red-arm checks from a COPY of the record —
    # the rollup MUST fail row SC-2 naming its red arm. A rollup that cannot
    # go red on a one-armed row proves nothing (R-6).
    _, synth = rollup_rows([r for r in records if "SC-2 red" not in r[0]])
    check("AS-2 control: the rollup goes RED on a row stripped of its red "
          "arm (SC-2 minus its red check -> FAIL naming the red arm)",
          "red arm" in synth.get("SC-2", ""), str(synth.get("SC-2")))
    lines, failing_rows = rollup_rows(records)
    for line in lines:
        print(line)
    print(f"  rows: {len(ROW_ARMS) - len(failing_rows)}/{len(ROW_ARMS)} "
          "pass both arms")
    print("  info SC-1 LOUD (spec § Could not pin): the launch arm is REAL "
          "up to the LAST PRE-SPAWN GATE only — launch --dry-run resolves "
          "the harness command for every assembled descriptor (SC-1, CP-6) "
          "and a REAL launch reads the created budget.json floor and is "
          "refused solely on the absent tmux pane (CP-6). The pane spawn + "
          "harness exec of an assembled descriptor remains an INFERENCE: "
          "this hermetic suite has no tmux, and the pane gate fires before "
          "any harness command would run, so a stub harness cannot cross it.")
    print("  info AS-1/AS-3 are one-time evidence recorded at dag-07 "
          "landing, not per-invocation rows: AS-1 (scratch-copy seat:->id: "
          "mutation -> suite exit 1 naming SC-2; pristine copy -> exit 0) "
          "and AS-3 (workspace-.rbtv hash snapshot identical around a full "
          "run; detector proven on a scratch stand-in — a permanent row "
          "would hardcode one workspace's vault path into a general "
          "command). AS-4's permanent form is the SK-4 pass (row AS-4).")

    ok = not failures and not failing_rows
    print(f"\n{'PASS' if ok else 'FAIL'} — {len(failures)} failed "
          f"check(s), {len(failing_rows)} failed row(s) of {len(ROW_ARMS)}")
    for f in failures:
        print(f"  - {f}")
    for row, why in failing_rows.items():
        print(f"  - row {row}: {why}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
