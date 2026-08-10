#!/usr/bin/env python3
"""materialize-seats — materialize a seat or a whole workflow into a goal package.

The command MATERIALIZES seats incrementally into an EXISTING run: it resolves
the added seat set (a seat catalog `seats.csv` row for --seat; a workflow
manifest `<component>/workflows/<W>/<W>.csv` for --workflow), validates the
per-seat executor bindings, and plans three kinds of write in this order — per
seat, its `{package}/seats/<seat>/seat.md` descriptor and then the
`{package}/seats/<seat>/AGENTS.md` POINTER to that descriptor (owner ruling
2026-08-07; see `_SEAT_AGENTS_MD` for why a pointer and not a copy, and why the
`agents-md` mirror cannot own it), and finally `{package}/taskforce.csv` row
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
folder `rbtv-goal scaffold` minted.) The three CONTENT surfaces
— conduct.md, CLAUDE.md, budget.json — arrive as CALLER-SUPPLIED input files
(--conduct / --claude-md / --budget-json, byte-copied), per
`d-run3-seeds-from-run2-amended`: run-2's versions as amended by the authored
designs, CARRIED BY THE CALLER (dag-16's bootstrap job). This command never
invents run conventions, never defaults a floor — a missing input REFUSES
loudly (`create-inputs-missing`) naming the input and the remedy. Creation is
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

    # run from THIS file's own directory (ignite/team-kit); the target must be
    # absolute, because a symlink stores the text it was given
    ln -s "$(pwd)/materialize-seats.py" ~/.local/bin/scaffold-seats
    command -v scaffold-seats   # rc=0 once it resolves

The exec bit and the shebang are already on this file; the symlink needs no
chmod. Every path this file derives goes through Path(__file__).resolve(), so
invocation through the symlink resolves the kit dir, not ~/.local/bin.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime
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

# goal_cli.py is the goals-tree capability sibling of this team-kit — resolved
# relative to this file, never from a hardcoded workspace path.
_GOAL_CLI_DIR = Path(__file__).resolve().parent.parent / "capabilities" / "goals-tree" / "tool"
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
    SECTION_RE,
)

# ---------------------------------------------------------------- constants

# The env scrub (ignite-job shape): read none of these, unset all of them at
# entry regardless — a detached loop inherits TMUX_PANE and every send is
# refused against the wrong pane.
SCRUBBED_ENV_VARS = ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET")

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# The goals-tree folder the goal-direct package bar keys on (7.607 E2b, design-lock
# item 8: the PACKAGE IS THE GOAL FOLDER). Positional, exactly like the daemon-side
# grammar in `server/seat-identity/seat-folder.js` — no second reading of goal
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
# the ruled run-3 authoring input (`r-stage0-state-cursor-interim-convention`
# (a), goal decisions.md — the ONE ledger this line is consumed from). HEADER
# ONLY: the first real row is the leader's at bootstrap, never this command's
# (clause (b)); run-2's off-schema cursor is frozen history, never repaired.
STATE_CSV_NAME = "state.csv"
STATE_CSV_HEADER = "stamped-at,run-state,seat,session-id,note"

# The caller-supplied content surfaces of a created package
# (`d-run3-seeds-from-run2-amended`): surface name -> the argv option whose
# FILE carries the base text. VALUES never cross argv (R-10,
# r-floor-single-source) — the option is a path, a reference, not a copy.
CREATION_INPUTS = (
    ("conduct.md", "--conduct", "conduct"),
    ("CLAUDE.md", "--claude-md", "claude_md"),
    ("budget.json", "--budget-json", "budget_json"),
)

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
# `ignite/server/spawn/spawn.js` from keys it reads OUT OF `seat.md`'s
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


def derive_taskforce_id(package: Path) -> str:
    """The taskforce-id a zero-data-row registry carries: a COUNTER read from the
    goal's own `taskforce.csv` — `max existing + 1` (design-lock item 10 / D3).

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
        m = re.fullmatch(r"tf-(\d+)", (row.get("taskforce-id") or "").strip())
        if m:
            top = max(top, int(m.group(1)))
    return f"tf-{top + 1}"


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


def check_bindings_cover(bindings: dict, added: list[str]) -> None:
    """The bindings `seats` keys MUST equal the resolved set — a missing or
    extra key is a REFUSAL, never a default (the G-51 silent-default lesson)."""
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
    extra = [s for s in bindings["seats"] if s not in added]
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
            raise Refuse(
                "seat-unknown",
                f"seat '{args.seat}' resolves to no row in any seats.csv "
                f"under {catalog_root} — nothing materialized",
                str(catalog_root),
            )
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


def validate_milestone(args, package: Path) -> None:
    """--milestone-id must resolve to a milestones.csv row or the run refuses."""
    if not args.milestone_id:
        return
    mpath = package / MILESTONES_NAME
    rows = _csv_rows(mpath)
    if not any((r.get("milestone-id") or "").strip() == args.milestone_id for r in rows):
        raise Refuse(
            "milestone-unresolved",
            f"--milestone-id '{args.milestone_id}' resolves to no "
            f"{MILESTONES_NAME} row — nothing materialized",
            str(mpath),
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
    rendered one, atomically (tmp in the same directory + os.replace, the
    discipline every other writer here uses). Nothing else is touched — no
    registry row, no run register, no package surface."""
    written: list[str] = []
    for seat in plan["added_seats"]:
        target = seat_home(Path(plan["package"]), seat) / "seat.md"
        _atomic_replace(target, plan["descriptors"][seat])
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
    kit_dir = Path(__file__).resolve().parent
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
        # F8 — cmd_close spawns a claude closer regardless of the closed
        # seat's harness; a memoryless one-shot worker gets the mechanical
        # close (G-23, no memory.md) by construction.
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

        tail = ""
        if fm["mode"] == "one-shot":
            # F10 — a one-shot pays for CLI discovery inside its single
            # session; carry the two exact command strings VERBATIM.
            tail = (
                "\n<!-- one-shot boot (F10): the two exact coordination "
                "commands for this seat, verbatim. -->\n\n"
                "One-shot boot — run these two commands exactly:\n\n"
                f"    coordinate --package {package} --as {seat} checkin\n"
                f"    coordinate --package {package} --as {seat} checkout\n"
            )

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
        writes.append({"kind": "seat-agents-pointer", "seat": seat,
                       "path": str(seat_home(package, seat) / "AGENTS.md")})
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
      conduct.md      CALLER-SUPPLIED (--conduct)      \\  d-run3-seeds-
      CLAUDE.md       CALLER-SUPPLIED (--claude-md)     } from-run2-amended:
      budget.json     CALLER-SUPPLIED (--budget-json)  /  never invented here

    Ask-(f) RULING ENCODED (`d-run3-seeds-from-run2-amended`, 2026-07-29):
    all three content surfaces arrive as caller-supplied input FILES — run-2's
    versions as amended by the authored designs, carried by the caller
    (dag-16's bootstrap job). budget.json takes the caller-supplied-file
    option of the dag-06 task (consistent with that ruling): a missing input
    REFUSES loudly naming it; a silently-defaulted floor or an invented
    conduct/CLAUDE surface is the failure this refusal exists to prevent.

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
    all three inputs (this is the bootstrap path, and it is the same code path
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
        if entry.get("dir"):
            target.mkdir(parents=True, exist_ok=True)
            target.chmod(0o755)
        else:
            with open(target, "xb") as fh:
                fh.write(entry["data"])
            target.chmod(0o644)
        written.append(str(target))
    return written


# ── The seat's AGENTS.md — a POINTER, never a copy (owner ruling 2026-08-07) ──────────
#
# WHY IT EXISTS. A daemon-spawned `claude` seat receives its descriptor in the SYSTEM
# PROMPT (`server/spawn/spawn.py`… `composeArgv` appends `--append-system-prompt-file
# <workdir>/seat.md`), so nothing needs to tell it to read the file — it already has it.
# `codex` and `opencode` have NO system-prompt flag: measured 2026-08-07 on this box,
# `codex exec --help` offers only `-c/--config` and `-p/--profile`, and `opencode run
# --help` (read through a PTY, since its help writes zero bytes into a pipe) offers none
# at all. What BOTH of them do read, automatically, is an `AGENTS.md` in the working
# directory — verified live: a temp dir holding an AGENTS.md that said "reply MANGO" made
# each of them reply MANGO. That auto-read file is therefore the ONE carriage that reaches
# them, and this is it.
#
# ⚑ A POINTER, NOT THE CONTENT — owner-ruled. Inlining seat.md here would fork the
# descriptor into two files that drift, and a seat's descriptor has exactly one home.
#
# ⚑ WHY IT CANNOT BE THE `agents-md` MIRROR'S JOB. That driver
# (`orchestration/models/mirror/driver/guidance.py`) writes each AGENTS.md as banner + the
# body of its SIBLING CLAUDE.md, verbatim — a derived copy that by construction cannot say
# anything its CLAUDE.md does not. The ruling needs the two to DIVERGE (CLAUDE.md must not
# mention seat.md; AGENTS.md must). A seat folder has no CLAUDE.md, so the mirror has no
# source to walk here and never touches this file — which is exactly what makes the
# divergence possible instead of a fight.
_SEAT_AGENTS_MD = """\
# AGENTS.md — {seat}

> Generated by `materialize-seats.py` beside this seat's `seat.md`. Not a mirror of any
> CLAUDE.md, and not a copy of the descriptor: a pointer to it.

## Before your first word — read `seat.md` in this folder and FOLLOW it

`seat.md` is a MUST-READ AND MUST-FOLLOW file, not a reference. Its directives bind this
sitting from its first action: the seat's task, identity, instruments, rhythm, format
duties, and its bounds. Read it before you answer anything — including a question that
looks trivial, which is exactly where it gets skipped.

NEVER ask whether to read it. By the time you write your first word you have already read
it.

Why this file exists at all: a `claude` seat launched by the daemon receives `seat.md` in
its system prompt and needs no pointer. Your harness has no such flag, so this pointer is
the only thing that tells you the descriptor is there. Nothing else will.
"""

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


def _write_seat_agents_md(folder: Path, seat: str,
                          rules: list[tuple[str, str]] = ()) -> str | None:
    """Write (or refresh) the seat's AGENTS.md pointer. Returns the path if written.

    Regenerated freely — unlike `seat.md` this is fixed boilerplate with no per-run
    content (plus, when the seat exposes rules, the forced-read preamble naming each
    materialized copy), so there is no drift to preserve and no reason to refuse an
    overwrite."""
    target = folder / "AGENTS.md"
    text = _SEAT_AGENTS_MD.format(seat=seat)
    if rules:
        text += _SEAT_RULES_BLOCK.format(rows="\n".join(
            f"- `.agents/behavior-rules/{pid}.md` — {desc}"
            for pid, desc in rules))
    if target.exists() and target.read_text(encoding="utf-8") == text:
        return None
    target.write_text(text, encoding="utf-8", newline="\n")
    target.chmod(0o644)
    return str(target)


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
#   sub-agent  .claude/agents/<id>.md + .opencode/agents/<id>.md — thin
#              loaders; codex has no confirmed-native definition (CMP-12)
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


def _exposure_rows(comp_dir: Path) -> dict[str, dict]:
    """part-id -> exposure.csv row of ONE component ({} when no manifest).

    `#`-led lines are DROPPED before the header is read. Exposure manifests
    carry a prose header block by convention (the `orchestration/exposure.csv`
    and `web/browse/exposure.csv` headers are the live shape), and a plain
    DictReader takes that first comment line for the header — every part-id
    then reads as absent, which surfaces as `exposes-ref-dangling` against a
    manifest that plainly contains the row."""
    path = comp_dir / EXPOSURE_NAME
    if not path.is_file():
        return {}
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
             if not ln.lstrip().startswith("#")]
    rows: dict[str, dict] = {}
    for row in csv.DictReader(lines):
        pid = (row.get("part-id") or "").strip()
        if pid:
            rows[pid] = row
    return rows


def _rbtv_repo_root(comp_dir: Path) -> Path:
    """The rbtv REPO tree — the second resolution root a `rbtv:`-prefixed
    reference addresses (owner ruling, 2026-08-10).

    The catalog root and the repo are DIFFERENT TREES: a mirror component
    (`.rbtv/mirror/<module>/<component>/`) cannot reach the repo with the
    3-segment grammar, whose arithmetic is relative to the referencing
    component's own position. The entry book is `.rbtv/config/install.json`
    (install2's record) — found by walking UP from the referencing component,
    so the workspace is derived, never guessed. install.json records the
    workspace as `target` but carries NO repo source path; the repo path is
    `rbtv.json`'s `rbtv_path` at that workspace root (the same book
    `{rbtv_path}` is resolved from everywhere else). Both books must be
    present and carry their field, else REFUSE with what was found."""
    book = None
    for parent in (comp_dir, *comp_dir.parents):
        cand = parent / ".rbtv" / "config" / "install.json"
        if cand.is_file():
            book = cand
            break
    if book is None:
        raise Refuse(
            "exposes-repo-root-underivable",
            "a `rbtv:` reference resolves through the install book and no "
            ".rbtv/config/install.json exists at or above the referencing "
            "component — nothing addresses the repo tree",
            str(comp_dir))
    try:
        data = json.loads(book.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refuse(
            "exposes-repo-root-underivable",
            f"install book is not readable JSON — {exc}",
            str(book)) from exc
    target = str((data or {}).get("target") or "").strip()
    workspace = Path(target) if target else book.parent.parent.parent
    rbtv_book = workspace / "rbtv.json"
    if not rbtv_book.is_file():
        raise Refuse(
            "exposes-repo-root-underivable",
            "install.json carries no repo source path (its keys: "
            + ", ".join(sorted((data or {}).keys()))
            + f") and {rbtv_book} — the book that records `rbtv_path` — does "
            "not exist; a `rbtv:` reference has no tree to resolve against",
            str(book))
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
                # `rbtv:ignite/team-kit/coordinate` after the CMP-5 move,
                # same line). Unprefixed references are untouched.
                if ref.startswith("rbtv:"):
                    segs = ref[len("rbtv:"):].split("/")
                    if len(segs) < 2 or not all(s.strip() for s in segs):
                        raise Refuse(
                            "exposes-invalid",
                            f"seat '{seat}' exposes '{ref}' ({method}) — a "
                            "`rbtv:` reference is "
                            "`rbtv:<path-under-the-repo>/<part>` and needs at "
                            "least one directory segment before the part-id",
                        )
                    ref_dir = _rbtv_repo_root(comp_dir).joinpath(*segs[:-1])
                else:
                    segs = ref.split("/")
                    if not all(s.strip() for s in segs) or len(segs) > 3:
                        raise Refuse(
                            "exposes-invalid",
                            f"seat '{seat}' exposes '{ref}' ({method}) — a "
                            "reference is `part`, `component/part`, or "
                            "`module/component/part`; empty segments or "
                            "deeper nesting are not expressible",
                        )
                    if len(segs) == 1:
                        ref_dir = comp_dir
                    elif len(segs) == 2:
                        ref_dir = comp_dir.parent / segs[0]
                    else:
                        ref_dir = comp_dir.parent.parent / segs[0] / segs[1]
                pid = segs[-1]
                rows = _exposure_rows(ref_dir)
                if pid not in rows:
                    raise Refuse(
                        "exposes-ref-dangling",
                        f"seat '{seat}' exposes '{ref}' ({method}) — no "
                        f"exposure.csv row '{pid}' under "
                        f"{ref_dir / EXPOSURE_NAME}; a dead reference must "
                        "not reach a materialized seat (grammar: `part` · "
                        "`component/part` · `module/component/part`)",
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
                    raise Refuse(
                        "exposes-entry-missing",
                        f"seat '{seat}' exposes '{ref}' ({method}) whose "
                        f"entry-point '{entry or '(empty)'}' resolves to no "
                        "file under its component — nothing to realize",
                        str(ref_dir / EXPOSURE_NAME))
                parts.append((method, pid, rows[pid], ref_dir))
        plan["exposes"][seat] = exposes
        plan["expose_parts"][seat] = parts


def render_seat_exposures(plan: dict) -> None:
    """Plan the per-seat loader files for the resolved `exposes:` parts
    (validation already fired in resolve_seat_exposes) and DECLARE each in
    writes[]. Hooks MERGE into the .claude/settings.json the plugin/MCP
    surface may already carry — one writer per file, never two."""
    plan["seat_exposures"] = {}
    plan["seat_rules"] = {}
    for seat, parts in (plan.get("expose_parts") or {}).items():
        files: dict[str, str] = {}
        rules: list[tuple[str, str]] = []
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
                rules.append((pid, desc))
            elif method == "sub-agent":
                text = _loader_md(pid, desc, entry, "sub-agent", named=True)
                files[f".claude/agents/{pid}.md"] = text
                files[f".opencode/agents/{pid}.md"] = text
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
        if rules:
            plan["seat_rules"][seat] = rules
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

    Each seat also gets an `AGENTS.md` POINTER to its descriptor — the carriage for
    the harnesses that have no system-prompt flag (see `_SEAT_AGENTS_MD`)."""
    written: list[str] = []
    for seat in plan["added_seats"]:
        text = plan["descriptors"][seat]
        folder = seat_home(Path(plan["package"]), seat)
        target = folder / "seat.md"
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
            # The descriptor is already correct; the POINTER may still be missing —
            # completing a partial failure has to complete both halves.
            also = _write_seat_agents_md(
                folder, seat, (plan.get("seat_rules") or {}).get(seat, ()))
            if also:
                written.append(also)
            continue
        folder.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        target.chmod(0o644)
        folder.chmod(0o755)
        written.append(str(target))
        also = _write_seat_agents_md(
            folder, seat, (plan.get("seat_rules") or {}).get(seat, ()))
        if also:
            written.append(also)
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
    multi-predecessor `after` cell carries commas and must quote)."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(values)
    return buf.getvalue()[:-1]


def render_taskforce_rows(plan: dict) -> None:
    """dag-05 — plan the registry append WITHOUT writing: read taskforce.csv,
    run the three validations, and render the rows in topological order of the
    added subgraph into plan['registry']. Fires BEFORE any write (descriptors
    included) and before the --dry-run return, so a refusal here always leaves
    zero files and zero rows.

    Q8 second-carrier note (d-spec-open-points-ruled Q8; verified at dag-05
    implementation): the verbatim 15-rule DAG-authoring block is carried by
    TWO surfaces, both under .rbtv/mirror/meta/planning-deprecated/ (pre-rename planner-workflow) —
    (1) workflows/planning/workflow.md § "DAG-authoring rules" (the source),
    (2) prompts/cognitive-units/procedures/workflow-designer.md § "The
    DAG-authoring rules — carried VERBATIM" (the byte-identical copy).
    Of the 15 rules, THIS command enforces MECHANICALLY:
      Rule 8  — validation 2 (every `after` member resolves: validate_after
                for the --after argv, check_acyclic's edge-resolution findings
                for the resulting graph),
      Rule 9  — validation 1 (acyclicity of the RESULTING graph, via
                goal_cli.check_acyclic — never a hand-rolled walk),
      Rule 13 — the frozen-copy `after` cells below (manifest cells verbatim;
                the --after/--root insertion point only on the added roots),
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
            "re-run with --conduct/--claude-md/--budget-json so the missing "
            "surfaces can be created from caller-supplied content",
            str(tf_path),
        )
    else:
        text = tf_path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
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
    ids = {(r.get("taskforce-id") or "").strip() for r in existing_rows}
    ids.discard("")
    if not existing_rows:
        tf_id = derive_taskforce_id(Path(plan["package"]))
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
    # own cell VERBATIM; the added subgraph's roots take the --after set (or
    # empty with --root). Nothing else ever computes an edge.
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


def _atomic_replace(path: Path, new_text: str) -> None:
    """Replace a csv's whole content atomically: tmp file in the SAME directory
    + os.replace, carrying the live file's mode. NEVER an open-append — a
    partial line in a csv is unparseable by every consumer at once. Shared by
    both append writers (the taskforce registry and the run register) so the
    two can never drift into two different write disciplines."""
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent),
                                    prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        os.chmod(tmp_name, os.stat(path).st_mode & 0o7777)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def append_taskforce_rows(plan: dict) -> int:
    """dag-05 — the registry append, from the plan render_taskforce_rows
    validated: read → append → ATOMIC write (tmp in the same directory +
    os.replace), NEVER an open-append — a partial line in the run's registry
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
    _atomic_replace(tf_path, new_text)
    plan["rows_appended"] = len(reg["append_lines"])
    return plan["rows_appended"]


# ---------------------------------------------------------------- run


def run_refresh(args) -> dict:
    """--refresh — bring an ALREADY SET-UP seat folder up to the definition's
    current shape, writing ONLY the DERIVED surfaces: the `AGENTS.md` pointer
    and the `exposes:` loaders. It creates no seat, appends no registry row,
    and touches no package surface.

    ⚠ IT DOES NOT RE-RENDER `seat.md`, deliberately. A descriptor is the one
    file here that can carry authored content the catalog does not hold — the
    live standing-seat descriptors carry cage keys (`rw-paths`, `read-root`,
    `bus-write`, `local-bin`, …) that `_descriptor_frontmatter` does not emit,
    so a re-render would silently DELETE them. Re-rendering a descriptor is
    `--repass`, which is the caller stating that loss is intended. The split
    is what makes this mode safe to run on anything: every file it writes is
    declared derived and content-free, so a byte-identical result is a skip
    and a changed result is a fix.

    The seat folder is `seats/<seat>/` in a goal package and the package
    ITSELF in a standing-seat home (`standing_seat`)."""
    catalog_root = Path(args.catalog_root)
    if not catalog_root.is_dir():
        raise Refuse(
            "catalog-root-missing",
            "--catalog-root is not a directory — no catalog to refresh from",
            str(catalog_root),
        )
    package = validate_package(args.package)
    catalogs = load_catalogs(catalog_root)
    normalize_seat_rows(catalogs[0])
    added, _, _ = resolve_added(args, catalog_root, catalogs[0])
    for seat in added:
        folder = seat_home(package, seat)
        if not folder.is_dir():
            raise Refuse(
                "refresh-no-seat-folder",
                f"--refresh updates an EXISTING seat folder and {folder.name}"
                " does not exist — materializing a new seat is the plain run",
                str(folder),
            )
    plan = {"package": str(package), "added_seats": added, "writes": [],
            "warnings": [], "rows_appended": 0}
    resolve_seat_exposes(plan, catalogs[0])
    render_seat_exposures(plan)
    for seat in added:
        plan["writes"].append({"kind": "seat-agents-pointer", "seat": seat,
                               "path": str(seat_home(package, seat)
                                           / "AGENTS.md")})
    if args.dry_run:
        plan["descriptors"] = {}
        return result_of(plan, dry_run=True)
    emit_seat_exposures(plan)
    for seat in added:
        _write_seat_agents_md(seat_home(package, seat), seat,
                              (plan.get("seat_rules") or {}).get(seat, ()))
    return result_of(plan, dry_run=False)


def run(args) -> dict:
    if getattr(args, "refresh", False):
        return run_refresh(args)
    package = validate_package(args.package)
    repass = bool(getattr(args, "repass", False))
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
    bindings = load_bindings(Path(args.bindings))
    catalogs = load_catalogs(catalog_root)
    normalize_seat_rows(catalogs[0])
    added, internal_after, internal_after_raw = resolve_added(
        args, catalog_root, catalogs[0])
    check_bindings_cover(bindings, added)
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
    # Seat-exposure resolution fires for BOTH paths (its gates are pre-write,
    # and the descriptor frontmatter carries the validated mapping); the
    # loader FILES are planned only on the materialize path below — a repass
    # replaces descriptors, nothing else.
    resolve_seat_exposes(plan, catalogs[0])
    if repass:
        # A repass renders and REPLACES descriptors, nothing else: the
        # registry row, the run register and every package surface are the
        # previous materialize's and stay byte-untouched.
        plan["writes"] = [
            {"kind": "seat-descriptor-repass", "seat": seat,
             "path": str(seat_home(package, seat) / "seat.md")}
            for seat in added
        ]
        plan["rows_appended"] = 0
        render_descriptors(plan, catalogs[0], units)
        if args.dry_run:
            return result_of(plan, dry_run=True)
        repass_descriptors(plan)
        return result_of(plan, dry_run=False)
    # dag-04 + dag-05: EVERY gate fires HERE — the emission gates, then the
    # three registry validations — before the dry-run return and before any
    # write, so a refusal always leaves zero files and zero rows.
    render_descriptors(plan, catalogs[0], units)
    render_harness_configs(plan, catalogs[0])  # plugin/MCP config files
    render_seat_exposures(plan)   # seat-exposure loaders (five methods)
    render_taskforce_rows(plan)
    if args.dry_run:
        return result_of(plan, dry_run=True)
    # Package surfaces FIRST (dag-06), descriptors SECOND, rows LAST — never
    # another order (the descriptor/rows rationale lives on
    # append_taskforce_rows' docstring; creation must precede both because
    # descriptors land in seats/ and the append re-reads taskforce.csv).
    create_run_package(package, creation)  # dag-06
    emit_seat_descriptors(plan)   # dag-04
    emit_harness_configs(plan)    # plugin/MCP config files
    emit_seat_exposures(plan)     # seat-exposure loaders (five methods)
    append_taskforce_rows(plan)   # dag-05
    return result_of(plan, dry_run=False)


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
                      help="materialize ONE cataloged seat (seats.csv row)")
    what.add_argument("--workflow",
                      help="materialize a whole workflow "
                           "(<component>/workflows/<W>/<W>.csv manifest)")
    p.add_argument("--catalog-root", required=True, dest="catalog_root",
                   help="component catalog root the definitions are read from")
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
    p.add_argument("--conduct", dest="conduct",
                   help="caller-supplied conduct.md BASE-TEXT file, byte-"
                        "copied into a CREATED goal package (d-run3-seeds-"
                        "from-run2-amended — this command never invents run "
                        "conventions). Required when creating/completing")
    p.add_argument("--claude-md", dest="claude_md",
                   help="caller-supplied run CLAUDE.md base-text file, byte-"
                        "copied into a CREATED goal package (same ruling as "
                        "--conduct). Required when creating/completing")
    p.add_argument("--budget-json", dest="budget_json",
                   help="caller-supplied budget.json file, byte-copied into "
                        "a CREATED goal package. A PATH, never a value: the "
                        "floor lives in the file (R-10, r-floor-single-"
                        "source). Required when creating/completing")
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
                        "definition's current shape: rewrites only the "
                        "DERIVED surfaces (AGENTS.md pointer + the "
                        "prompt-card `exposes:` loaders), never seat.md — "
                        "a descriptor can carry authored keys the catalog "
                        "does not hold, and re-rendering one is the "
                        "deliberate --repass. Needs no --bindings and no "
                        "insertion point; works on a goal package and on a "
                        "standing-seat home (.rbtv/goals/_<seat>/) alike.")
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
        for warn in result["warnings"]:
            print(f"  warning: {warn}")
    return 0


# ---------------------------------------------------------------- selftest


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def _norm(text: str, tmp: Path) -> str:
    return text.replace(str(tmp), "<TMP>")


def _invoke(argv: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), *argv],
        capture_output=True, text=True, env=env,
    )


def build_fixture(tmp: Path) -> dict:
    """A throwaway catalog + goal package + bindings set, in the settled
    component shape (kind-named XML unit bodies, id in frontmatter; bare and
    @latest unit refs both exercised — the dag-01 widened grammar)."""
    # catalog-root/<component>/... — one level, mirroring the live shape
    # (catalog-root .rbtv/mirror/meta, component planning-deprecated, pre-rename planner-workflow).
    comp = tmp / "catalog" / "demo-comp"

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
         "- Reference: `alpha-outcome@latest`.\n## Output\nalpha-notes.md\n"
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
    wide = tmp / "catalog" / "wide-comp"

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
    mcpc = tmp / "catalog" / "mcp-comp"
    mcpc.mkdir(parents=True)
    mcpc.joinpath("seats.csv").write_text(
        "seat-id,executor,task,staffing-hints,description\n"
        "mcp-seat,alpha-prompt,alpha-task,,the mcp seat\n", encoding="utf-8")
    mcpc.joinpath("exposure.csv").write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description\n"
        "demo-mcp,plugin/MCP,config,,mcp.json,demo MCP declaration\n",
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
        fh.write("xsk,reference,skill,,xsk.md,cross-component skill\n")

    # A fourth component whose seat DECLARES exposure in its prompt-file
    # frontmatter (EXP-1, d-materializer-seat-loaders /
    # d-seat-exposes-frontmatter): its own component so no other arm's write
    # set changes; assembly reuses demo-comp's prompt/task rows (catalogs
    # merge across the root), while the `exposes:` declaration lives on THIS
    # component's own whole-file prompt card.
    expc = tmp / "catalog" / "exp-comp"
    expc.mkdir(parents=True)
    expc.joinpath("seats.csv").write_text(
        "seat-id,executor,task,staffing-hints,description,cage-grants,"
        "rw-paths\n"
        "exp-seat,alpha-prompt,alpha-task,,the exposure seat,"
        "read-root bus-write local-bin,1-projects\n",
        encoding="utf-8")
    expc.joinpath("exposure.csv").write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description\n"
        "brws,capability,skill,,skills/brws.md,browse the fixture web\n"
        "cmd1,workflow,command,,commands/cmd1.md,run the demo flow\n"
        "rul1,reference,rule,,rules/rul1.md,house style rule\n"
        "hk1,capability,hook,,hooks/hk1.json,post-write lint\n"
        "res1,prompt,sub-agent,,prompts/res1.md,fixture researcher\n",
        encoding="utf-8")
    # The SECOND RESOLUTION ROOT (d-path-exposes-authorable): a `rbtv:` ref
    # addresses the rbtv REPO tree, found by walking up from the referencing
    # component to `.rbtv/config/install.json` and reading `rbtv.json`'s
    # `rbtv_path` at the workspace that book records. `tmp` stands in for the
    # workspace; `tmp/repo` for the rbtv repo, module manifest at module root
    # exactly as `ignite/exposure.csv` sits today.
    (tmp / ".rbtv" / "config").mkdir(parents=True)
    (tmp / ".rbtv" / "config" / "install.json").write_text(
        json.dumps({"schema": 1, "installer": "install2.py",
                    "target": str(tmp), "components": {}}) + "\n",
        encoding="utf-8")
    (tmp / "rbtv.json").write_text(
        json.dumps({"rbtv_version": "0.0.0-fixture", "rbtv_path": "repo"})
        + "\n", encoding="utf-8")
    repo_mod = tmp / "repo" / "ignite"
    (repo_mod / "team-kit").mkdir(parents=True)
    repo_mod.joinpath("exposure.csv").write_text(
        "# a prose header line — `#`-led lines are dropped before the header\n"
        "part-id,part-kind,method,rbtv-cli,entry-point,description\n"
        "coordfix,tool,path,,team-kit/coordfix.py,\n"
        "skillish,capability,skill,,team-kit/skillish.md,a skill row\n",
        encoding="utf-8")
    repo_mod.joinpath("team-kit", "coordfix.py").write_text(
        "#!/usr/bin/env python3\nprint('coordfix')\n", encoding="utf-8")
    repo_mod.joinpath("team-kit", "skillish.md").write_text(
        "# skillish\n", encoding="utf-8")
    for rel, body in (
            ("skills/brws.md", "# brws\n\nBrowse skill content.\n"),
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
             "  path: [rbtv:ignite/coordfix]\n"
             "---\n\nWhole-file prompt card — read for `exposes:`; assembly "
             "still resolves the catalog prompt row.\n")):
        p = expc / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    # A component in ANOTHER MODULE (the `module/component/part` ref arm,
    # owner-ruled: cross-module must exist): tmp/ stands in for the tree
    # root above the modules (catalog/ being the module the seats live in),
    # exactly the `<tree>/<module>/<component>/` shape of the mirror and
    # the rbtv repo.
    xmodc = tmp / "xmod" / "xmodc"
    xmodc.mkdir(parents=True)
    xmodc.joinpath("exposure.csv").write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description\n"
        "xms,capability,skill,,xms.md,cross-module skill\n",
        encoding="utf-8")
    xmodc.joinpath("xms.md").write_text(
        "# xms\n\nCross-module skill content.\n", encoding="utf-8")

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
    guard = {"version": 1, "defaults": both["defaults"],
             "seats": {f"s{i}": dict(seat_binding) for i in range(1, 5)}}
    bdir.joinpath("guard.json").write_text(json.dumps(guard),
                                           encoding="utf-8")

    # dag-06 creation inputs — the CALLER-SUPPLIED trio
    # (d-run3-seeds-from-run2-amended). Fixture stand-ins for the amended
    # run-2 base texts dag-16 carries; the floor value is FIXTURE data inside
    # a caller file, never a number this command holds (R-10).
    seeds = tmp / "run-seeds"
    seeds.mkdir()
    (seeds / "conduct.md").write_text(
        "# conduct\n\nFixture conduct base text (caller-supplied).\n",
        encoding="utf-8")
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
        "catalog": str(tmp / "catalog"),
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
        "src_conduct": str(seeds / "conduct.md"),
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
            paths = [w["path"] for w in green_json.get("writes", [])]
            kinds = [w["kind"] for w in green_json.get("writes", [])]
            # Per seat: descriptor THEN its AGENTS.md pointer, in emit order; then
            # the one registry append. Kinds are asserted too — a path pair alone
            # would still pass if both entries claimed to be descriptors.
            check("plan: writes name both descriptors, each seat's AGENTS.md "
                  "pointer, and the registry append",
                  len(paths) == 5
                  and paths[0].endswith("seats/alpha/seat.md")
                  and paths[1].endswith("seats/alpha/AGENTS.md")
                  and paths[2].endswith("seats/beta/seat.md")
                  and paths[3].endswith("seats/beta/AGENTS.md")
                  and paths[4].endswith(TASKFORCE_NAME)
                  and kinds == ["seat-descriptor", "seat-agents-pointer",
                                "seat-descriptor", "seat-agents-pointer",
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
            # Each materialized seat contributes TWO new files: its descriptor and
            # its AGENTS.md pointer (owner ruling 2026-08-07 — the carriage for the
            # harnesses with no system-prompt flag). Both are named here, so the
            # write set stays exact: adding a third artifact still fails this check.
            expected_new = {
                str((Path(fx["pkg"]) / "seats" / s / name).relative_to(tmp))
                for s in ("alpha", "beta") for name in ("seat.md", "AGENTS.md")
            } | {
                str((Path(fx["pkg9"]) / "seats" / "alpha" / name)
                    .relative_to(tmp)) for name in ("seat.md", "AGENTS.md")
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
            import stat as _stat
            alpha_md = Path(fx["pkg"]) / "seats" / "alpha" / "seat.md"
            check("dag-04: emitted seat.md is 0644 and its folder 0755",
                  _stat.S_IMODE(alpha_md.stat().st_mode) == 0o644
                  and _stat.S_IMODE(alpha_md.parent.stat().st_mode) == 0o755)
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
    import stat as _stat

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

        kit_dir = Path(__file__).resolve().parent
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

        check("emitted key set opens in the ruled order "
              "(seat..description..cwd..agent_type..triple..mode)",
              list(afm)[:8] == ["seat", "description", "cwd", "agent_type",
                                "harness", "model", "effort", "mode"],
              str(list(afm)[:9]))
        check("B4 closed: cwd is the seat folder; ctx-refresh emitted in "
              "interactive mode",
              afm.get("cwd") == f"{fx['pkg']}/seats/alpha/"
              and afm.get("ctx-refresh") == 50)
        check("SC-14 (first arm): mode: emitted on every descriptor",
              afm.get("mode") == "interactive"
              and bfm.get("mode") == "interactive")
        check("SC-16 control: an interactive staff seat gets NO close: key",
              "close" not in afm and "close" not in bfm)
        check("task half emitted (ruled executor+task header aliased to "
              "the assembler's task-id)",
              all(k in kinds for k in ("task-goal", "scope",
                                       "done-contract")))
        check("F10 control: an interactive seat carries no one-shot boot "
              "text", "checkin" not in atext and "checkout" not in atext)
        check("dag-04: emission bits are 0644 file / 0755 folder",
              _stat.S_IMODE(alpha_md.stat().st_mode) == 0o644
              and _stat.S_IMODE(alpha_md.parent.stat().st_mode) == 0o755)

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
        check("F10: a one-shot descriptor carries both exact coordinate "
              "command strings verbatim",
              f"coordinate --package {fx['pkg']} --as s1 checkin" in s1_text
              and f"coordinate --package {fx['pkg']} --as s1 checkout"
              in s1_text)

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

    coord_py = Path(__file__).resolve().parent / "coord.py"
    coord_md5 = hashlib.md5(coord_py.read_bytes()).hexdigest()
    print(f"  info SC-1: coord.py under test — md5 {coord_md5}")

    def coord(argv):
        return subprocess.run([sys.executable, str(coord_py), *argv],
                              capture_output=True, text=True, env=env)

    # ---- group 1: SC-1 (full add + launch coupling), SC-9, SC-10 arm 1,
    #      topo order ---------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        fx = build_fixture(Path(td))
        pkg = Path(fx["pkg"])
        tf = pkg / TASKFORCE_NAME
        header_before = tf.read_text(encoding="utf-8").split("\n")[0]
        rows_before = len(tf.read_text(encoding="utf-8").splitlines())
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
        cpl = coord(["--package", fx["pkg"], "--as", "chief-of-staff",
                     "launch", "--dry-run", "--only", "alpha"])
        check("SC-1: coordinate launch --dry-run --only alpha resolves "
              "a harness command (root seat, before its own check-out)",
              cpl.returncode == 0
              and "claude --model claude-opus-5" in cpl.stdout
              and "REFUSED" not in cpl.stdout,
              (cpl.stdout + cpl.stderr).strip()[:200])
        # SC-1 control (unmet-predecessor half): while the predecessor has NOT
        # checked out, the dependent seat is refused BY CLASS — the term that
        # makes the green arm below a coupling rather than a second root.
        cpu = coord(["--package", fx["pkg"], "--as", "chief-of-staff",
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
        coord(["--package", fx["pkg"], "--as", "alpha", "checkout"])
        # Read DEFENSIVELY: an absent artifact must RED this check, never raise
        # out of the suite — a check that aborts the run takes every row after
        # it down with it and reports nothing.
        acj = pkg / "coordination" / "awaiting-close.json"
        awaiting = (json.loads(acj.read_text(encoding="utf-8"))
                    if acj.is_file() else {})
        check("SC-1 setup: alpha's check-out lands disposition done on disk",
              awaiting.get("alpha", {}).get("disposition") == "done",
              str(awaiting)[:200])
        cpl = coord(["--package", fx["pkg"], "--as", "chief-of-staff",
                     "launch", "--dry-run", "--only", "beta"])
        check("SC-1: coordinate launch --dry-run --only beta resolves "
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
        cpl = coord(["--package", fx["pkg"], "--as", "chief-of-staff",
                     "launch", "--dry-run", "--only", "beta"])
        check("SC-1 control: a divergent registry row REFUSES the dry-run "
              "through check_bindings",
              cpl.returncode != 0
              and "disagree with the run's registry" in cpl.stderr,
              (cpl.stdout + cpl.stderr).strip()[:200])
        # SC-1 control (no-registry-row half): DELETE the beta row.
        deleted = "\n".join(l for l in text.splitlines()
                            if not l.startswith("tf-1,beta")) + "\n"
        tf.write_text(deleted, encoding="utf-8")
        cpd = coord(["--package", fx["pkg"], "descriptors"])
        check("SC-1 control: a deleted row is NAMED by the descriptor audit "
              "(no-registry-row) and the audit exits nonzero",
              cpd.returncode == 1 and "no-registry-row" in cpd.stdout
              and "beta" in cpd.stdout,
              (cpd.stdout + cpd.stderr).strip()[:200])
        cpl = coord(["--package", fx["pkg"], "--as", "chief-of-staff",
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
              and "seats/alpha" in (_refusal(cp2).get("path") or "")
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
        # MEASURED GAP, recorded not asserted: goal-lint iterates ROWS, so an
        # orphan FOLDER with no row is invisible to it — the surface that DOES
        # name the half-state is coord.py's `descriptors` audit
        # (no-registry-row), asserted below. goal_cli is read-only for dag-05;
        # the lint gap is surfaced in the task return.
        print(f"  info SC-8 measured: goal-lint findings naming the orphan "
              f"folders: {len(lint_named)} (rows-only walk — the naming "
              f"surface is coord.py `descriptors`)")
        cpd = coord(["--package", str(run1), "descriptors"])
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

    coord_py = Path(__file__).resolve().parent / "coord.py"
    coord_md5 = hashlib.md5(coord_py.read_bytes()).hexdigest()
    print(f"  info CP-6: coord.py under test — md5 {coord_md5}")

    def coord(argv):
        return subprocess.run([sys.executable, str(coord_py), *argv],
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
                    "--conduct", fx["src_conduct"],
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
              and {"conduct.md", "CLAUDE.md", "budget.json",
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
              and {"conduct.md", "CLAUDE.md", "budget.json"} <= surfaces,
              (cp.stdout + cp.stderr).strip()[:200])
        check("CP-7 control: the dry flag is the discriminator — the same "
              "argv without it completed the package",
              (pkg / TASKFORCE_NAME).is_file())
        check("state.csv: the created cursor carries EXACTLY the ruled "
              "header, header only (r-stage0-state-cursor-interim-convention)",
              (pkg / STATE_CSV_NAME).read_text(encoding="utf-8")
              == STATE_CSV_HEADER + "\n")

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
              Path(fx["src_conduct"]).read_bytes() != made_budget)

        # CP-8 green: conduct.md + CLAUDE.md byte-identical to the sources.
        check("CP-8: created conduct.md and CLAUDE.md are byte-identical to "
              "the caller-supplied base text",
              (pkg / "conduct.md").read_bytes()
              == Path(fx["src_conduct"]).read_bytes()
              and (pkg / "CLAUDE.md").read_bytes()
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
              and (pkg / "conduct.md").read_bytes()
              == Path(fx["src_conduct"]).read_bytes()
              and (pkg / "budget.json").read_bytes() == src_budget
              and (pkg / STATE_CSV_NAME).read_text(encoding="utf-8")
              == STATE_CSV_HEADER + "\n",
              (cp.stdout + cp.stderr).strip()[:200])

        # CP-6: the created package is LAUNCHABLE.
        cpl = coord(["--package", str(pkg), "--as", "chief-of-staff",
                     "launch", "--dry-run", "--only", "alpha"])
        check("CP-6: coordinate launch --dry-run --only alpha resolves a "
              "harness command against the freshly created package",
              cpl.returncode == 0
              and "claude --model claude-opus-5" in cpl.stdout
              and "REFUSED" not in cpl.stdout,
              (cpl.stdout + cpl.stderr).strip()[:200])
        # CP-6 green (real-launch form): with budget.json present the floor
        # gate PASSES reading the created file (provenance names 64) and the
        # launch fails only on the absent tmux pane — proving the FLOOR read
        # hits the created surface on the real path the control below flips.
        cpl = coord(["--package", str(pkg), "--as", "chief-of-staff",
                     "launch", "--only", "alpha"])
        check("CP-6: a REAL launch reads the created budget.json (floor "
              "provenance = 64) and refuses only for the absent tmux pane",
              cpl.returncode != 0
              and "floors.launch_refuse_mb = 64" in cpl.stderr
              and "not inside tmux" in cpl.stderr,
              (cpl.stdout + cpl.stderr).strip()[:300])
        # CP-6 control: remove budget.json — the SAME real launch now
        # refuses for the undeclared floor. The surface list is load-bearing.
        (pkg / "budget.json").unlink()
        cpl = coord(["--package", str(pkg), "--as", "chief-of-staff",
                     "launch", "--only", "alpha"])
        check("CP-6 control: without budget.json the launch gate REFUSES "
              "for the undeclared floor (FloorUndeclared, "
              "r-floor-single-source)",
              cpl.returncode != 0
              and "no budget.json" in cpl.stderr
              and "r-floor-single-source" in cpl.stderr,
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
                    "--conduct", fx["src_conduct"],
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

        # CP-8 red arm: omit --conduct → REFUSAL naming it, nothing created.
        argv8 = argv_for(pkg5, "alpha", fx["b_alpha"])
        i = argv8.index("--conduct")
        del argv8[i:i + 2]
        cp = _invoke(argv8, env)
        check("CP-8 red: omitting the conduct source REFUSES "
              "(create-inputs-missing naming --conduct) — never a silent "
              "package without it",
              cp.returncode == 1
              and _refusal(cp).get("code") == "create-inputs-missing"
              and "--conduct" in _refusal(cp).get("message", "")
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
              and (pkg6 / "conduct.md").is_file()
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
              "SC-1: coordinate launch --dry-run --only"),
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
    "CP-6": (("CP-6: coordinate launch --dry-run --only alpha resolves",
              "CP-6: a REAL launch reads the created budget.json"),
             ("CP-6 control: without budget.json", "CP-6/CP-8 red")),
    "CP-7": (("CP-7: dry-run against an uncompleted goal folder exits 0",
              "CP-7: ...and writes NOTHING"), ("CP-7 control",)),
    "CP-8": (("CP-8: created conduct.md",),
             ("CP-8 red", "CP-6/CP-8 red")),
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
    # The seat-cage declaration (owner-ruled 2026-08-10).
    "CG-1": (("CG-1 green",), ("CG-1 red",)),
    # The pass-folder substitution rows (B4, B5, G-planner-0804-1502).
    "PF-1": (("PF-1 green",), ("PF-1 red",)),
    "PF-2": (("PF-2 green",), ("PF-2 red",)),
    "PF-3": (("PF-3 green",), ("PF-3 red",)),
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
        "briefing-a-briefing,META,seats=1;rounds=1,2026-01-02 00:00,,\n"
        "briefing-closed-one,META,seats=1;rounds=1,2026-01-01 00:00,"
        "2026-01-01 12:00,ACCEPTED\n", encoding="utf-8")

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
                           ("absent", None)):
        entry = dict(base)
        if pf_value is not None:
            entry["pass-folder"] = pf_value
        p = bdir / f"{name}.json"
        p.write_text(json.dumps({"defaults": {"cwd-mode": "seat-folder"},
                                 "seats": {"pf": entry}}), encoding="utf-8")
        paths[name] = str(p)
    return {"catalog": str(root / "catalog"), "pkg": pkg, "b": paths}


def _pf_run(fx: dict, binding: str, **over):
    """One in-process materialize against the PF fixture; returns the result
    dict, or the Refuse it raised."""
    args = argparse.Namespace(
        package=str(fx["pkg"]), seat="pf", workflow=None,
        catalog_root=fx["catalog"], after=None, root=True,
        bindings=fx["b"][binding], milestone_id=None, conduct=None,
        claude_md=None, budget_json=None, dry_run=True,
        as_json=False, force_partial=False, repass=False)
    for k, v in over.items():
        setattr(args, k, v)
    try:
        return run(args)
    except Refuse as r:
        return r


def run_pass_substitution_acceptance(check) -> None:
    """PF-1..PF-3 — B4, B5 and G-planner-0804-1502, both arms each."""
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
              == ["seat-descriptor-repass"], str(res)[:300])
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
    check("F6: validate_seat is imported from coord, never re-implemented",
          _coord_validate_seat().__module__ == "coord")

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
        check("EXP-1 green: a `rbtv:`-prefixed `path` ref resolves through "
              "install.json/rbtv.json and lands in seat.md as `exposed-clis:` "
              "— `<part-id> <absolute entry point>`, the cage's grant surface",
              sfm.get("exposed-clis") == [f"coordfix {coordfix}"],
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
            orig.replace("path: [rbtv:ignite/coordfix]",
                         "path: [rbtv:ignite/ghostcli]"), encoding="utf-8")
        pr3 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red: a dangling `rbtv:` reference refuses "
              "exposes-ref-dangling and writes NOTHING",
              pr3.returncode == 1 and "exposes-ref-dangling" in pr3.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pr3.stderr.strip()[:200])
        prompt_path.write_text(
            orig.replace("path: [rbtv:ignite/coordfix]",
                         "path: [rbtv:ignite/skillish]"), encoding="utf-8")
        pr4 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red: a `rbtv:` ref whose row declares method 'skill' "
              "refuses exposes-method-mismatch under `path:` and writes "
              "NOTHING",
              pr4.returncode == 1 and "exposes-method-mismatch" in pr4.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pr4.stderr.strip()[:200])
        prompt_path.write_text(
            orig.replace("path: [rbtv:ignite/coordfix]",
                         "path: [rbtv:coordfix]"), encoding="utf-8")
        pr5 = _invoke(["--package", fxe["pkg9"], "--seat", "exp-seat",
                       "--bindings", fxe["b_exp"]] + common_e, clean_env)
        check("EXP-1 red: a `rbtv:` ref with no directory segment refuses "
              "exposes-invalid and writes NOTHING",
              pr5.returncode == 1 and "exposes-invalid" in pr5.stderr
              and not (Path(fxe["pkg9"]) / "seats" / "exp-seat").exists(),
              pr5.stderr.strip()[:200])
        prompt_path.write_text(orig, encoding="utf-8")

    print("RF-1 --refresh: derived surfaces only, standing-seat home included")
    with tempfile.TemporaryDirectory() as rf_td:
        tmp_rf = Path(rf_td)
        fxr = build_fixture(tmp_rf)
        common_r = ["--catalog-root", fxr["catalog"], "--seat", "exp-seat",
                    "--refresh", "--json"]
        # A STANDING-SEAT home: the package IS the seat folder, named `_<seat>`
        # (.rbtv/goals/_channel-master/ is the live one). It carries an
        # AUTHORED seat.md the catalog does not hold, which --refresh must
        # leave byte-untouched — that is the whole point of the mode.
        home = tmp_rf / "goals" / "_exp-seat"
        home.mkdir(parents=True)
        authored = "---\nseat: exp-seat\nrw-paths:\n  - hand/authored\n---\n"
        (home / "seat.md").write_text(authored, encoding="utf-8")
        pr = _invoke(["--package", str(home)] + common_r, clean_env)
        loaders = [".claude/skills/brws/SKILL.md",
                   ".agents/skills/brws/SKILL.md", "AGENTS.md"]
        check("RF-1 green: --refresh writes the derived surfaces at the "
              "STANDING-SEAT package root (the package IS the seat folder), "
              "with no --bindings and no insertion point",
              pr.returncode == 0
              and all((home / rel).is_file() for rel in loaders),
              (pr.stderr.strip()[:300]
               or str([r for r in loaders if not (home / r).is_file()])))
        check("RF-1 green: the AUTHORED seat.md is byte-untouched — a "
              "descriptor can carry keys the catalog does not hold, so "
              "re-rendering one is the deliberate --repass, never this mode",
              (home / "seat.md").read_text(encoding="utf-8") == authored,
              (home / "seat.md").read_text(encoding="utf-8")[:200])
        # `if is_file()` so a MUTANT reports red here instead of
        # crashing the harness before the row is scored.
        stamps = {rel: (home / rel).read_bytes() for rel in loaders
                  if (home / rel).is_file()}
        pr_again = _invoke(["--package", str(home)] + common_r, clean_env)
        check("RF-1 green: a second --refresh is byte-identical (every file "
              "it writes is DERIVED — idempotent, never a collision refusal)",
              pr_again.returncode == 0
              and all((home / rel).read_bytes() == b
                      for rel, b in stamps.items()),
              pr_again.stderr.strip()[:200])
        # The manifest-comment control: browse/exposure.csv leads with a prose
        # header block, and a plain DictReader takes that line for the header —
        # every part-id then reads absent and the ref refuses as dangling.
        comp = tmp_rf / "commented-comp"
        comp.mkdir()
        (comp / EXPOSURE_NAME).write_text(
            "# a prose header block, the live exposure-manifest shape\n"
            "# second comment line\n"
            "part-id,part-kind,method,rbtv-cli,entry-point,description\n"
            "brws,capability,skill,,skills/brws.md,browse\n", encoding="utf-8")
        check("RF-1 green: an exposure manifest led by `#` comment lines "
              "still resolves its part-ids (a DictReader that reads the "
              "comment as the header reports every row absent)",
              list(_exposure_rows(comp)) == ["brws"],
              str(list(_exposure_rows(comp))))
        ghost = tmp_rf / "goals" / "demo-goal-77"
        ghost.mkdir(parents=True)
        pr_red = _invoke(["--package", str(ghost)] + common_r, clean_env)
        check("RF-1 red: --refresh updates an EXISTING seat folder — an "
              "absent one refuses refresh-no-seat-folder and writes NOTHING",
              pr_red.returncode == 1
              and "refresh-no-seat-folder" in pr_red.stderr
              and not (ghost / "seats").exists()
              and not (ghost / ".claude").exists(),
              pr_red.stderr.strip()[:200])
        pr_mint = _invoke(["--package", str(home), "--catalog-root",
                           fxr["catalog"], "--seat", "exp-seat", "--root",
                           "--bindings", fxr["b_exp"], "--json"], clean_env)
        check("RF-1 red: a PLAIN materialize into a standing-seat home is "
              "refused — it would append a taskforce.csv row to a package "
              "that has no registry, and the authored seat.md is untouched",
              pr_mint.returncode == 1
              and "standing-seat-plain-materialize" in pr_mint.stderr
              and (home / "seat.md").read_text(encoding="utf-8") == authored,
              pr_mint.stderr.strip()[:200])
        # ── the OPEN BINDING (owner-ruled 2026-08-10): a standing seat may
        # omit harness·model·effort entirely, because it has no taskforce.csv
        # row for the triple to agree with and its harness is named by the
        # spawner's profile, not by this file.
        raw = json.loads(Path(fxr["b_exp"]).read_text(encoding="utf-8"))
        for entry in raw["seats"].values():
            for k in ("harness", "model", "effort"):
                entry.pop(k, None)
        raw.get("defaults", {}).pop("harness", None)
        entry = raw["seats"]["exp-seat"]
        entry["mode"] = "one-shot"
        entry.pop("ctx-refresh", None)   # dead control on a one-shot (F4)
        b_open = tmp_rf / "b-open.json"
        b_open.write_text(json.dumps(raw), encoding="utf-8")
        pr_open = _invoke(["--package", str(home), "--catalog-root",
                           fxr["catalog"], "--seat", "exp-seat", "--root",
                           "--bindings", str(b_open), "--repass", "--json"],
                          clean_env)
        rendered = (home / "seat.md").read_text(encoding="utf-8")
        rfm = rendered.split("\n---", 1)[0]
        check("RF-1 green: a standing seat's OPEN binding omits harness, "
              "model and effort from the descriptor ENTIRELY — absent, never "
              "empty, because an empty value reads as a binding that failed",
              pr_open.returncode == 0
              and not any(re.search(rf"^{k}:", rfm, re.M)
                          for k in ("harness", "model", "effort"))
              and re.search(r"^mode:", rfm, re.M) is not None,
              (pr_open.stderr.strip()[:200] or rfm[:300]))
        entry["harness"] = "claude"
        b_open.write_text(json.dumps(raw), encoding="utf-8")
        pr_half = _invoke(["--package", str(home), "--catalog-root",
                           fxr["catalog"], "--seat", "exp-seat", "--root",
                           "--bindings", str(b_open), "--repass", "--json"],
                          clean_env)
        check("RF-1 red: HALF a triple is refused open-binding-partial — a "
              "descriptor carrying a harness but no model reads as a binding "
              "that was made, and sends a reader hunting the missing half",
              pr_half.returncode == 1
              and "open-binding-partial" in pr_half.stderr
              and (home / "seat.md").read_text(encoding="utf-8") == rendered,
              pr_half.stderr.strip()[:200])

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

    print("dag-04 acceptance pass (SC rows, each with its failing control)")
    run_dag04_acceptance(check, clean_env)

    print("dag-05 acceptance pass (SC-1/5/6/8/9/10/15/20/21, both arms each)")
    run_dag05_acceptance(check, clean_env)

    print("dag-06 acceptance pass (CP-1..CP-8, both arms each)")
    run_dag06_acceptance(check, clean_env)

    print("pass-folder acceptance pass (PF-1/PF-2/PF-3 — B4, B5, "
          "G-planner-0804-1502; both arms each)")
    run_pass_substitution_acceptance(check)

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
