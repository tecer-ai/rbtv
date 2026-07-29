#!/usr/bin/env python3
"""materialize-seats — materialize a seat or a whole workflow into a run package.

The command MATERIALIZES seats incrementally into an EXISTING run: it resolves
the added seat set (a seat catalog `seats.csv` row for --seat; a workflow
manifest `<component>/workflows/<W>/<W>.csv` for --workflow), validates the
per-seat executor bindings, and plans two kinds of write in this order —
`{package}/seats/<seat>/seat.md` descriptors first, then `{package}/taskforce.csv`
row appends. It is an ignite-job: argv-only, environment-free, exit codes
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
`relays:` is DELIBERATELY not emitted and refused as an input: owner ask A-40
is OPEN — do not add it here without that ruling.

The dag-05 REGISTRY HALF is landed — render_taskforce_rows/append_taskforce_rows:
the taskforce.csv append in topological order of the added subgraph, the three
pre-write validations (acyclicity of the RESULTING graph via
goal_cli.check_acyclic; every --after member resolves; no status column —
Rules 9/8/14 of the workflow.md DAG-authoring block), the frozen-copy `after`
cells (Rule 13), taskforce-id read from the file (never argv), atomic
read → append → os.replace (never an open-append), and the --force-partial
rows half (byte-match completion of ONLY the missing rows).
The dag-06 CREATE-RUN-PACKAGE STEP is landed — plan_package_creation/
create_run_package (d-bootstrap-mechanics-ruled (b)): an absent --package that
passes the runs/run-N bar is CREATED — `runs/run-N/` plus the surfaces a run
needs before a seat can check in (seats/, coordination/, header-only
taskforce.csv, the ruled header-only state.csv) — so the MASTER can
materialize at bootstrap, before the team exists. The three CONTENT surfaces
— conduct.md, CLAUDE.md, budget.json — arrive as CALLER-SUPPLIED input files
(--conduct / --claude-md / --budget-json, byte-copied), per
`d-run3-seeds-from-run2-amended`: run-2's versions as amended by the authored
designs, CARRIED BY THE CALLER (dag-16's bootstrap job). This command never
invents run conventions, never defaults a floor — a missing input REFUSES
loudly (`create-inputs-missing`) naming the input and the remedy. Creation is
announced in `writes[]` (kind `package-surface`), planned-not-written under
--dry-run, idempotent against an existing package, and COMPLETES a partial
one. A freshly created registry has no taskforce-id to read, so the first
append derives it from the compartment name (`run-N` -> `tf-N`) —
deterministic, never argv (see render_taskforce_rows).

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

Named extension point for the follow-on task:

    run_sc_acceptance      -> dag-07  (the SC-1..SC-16 acceptance rows inside
                                       the selftest)

Assembly is goal_cli's — `index_units` / `load_catalogs` / `assemble_seat`
imported from the goals-tree tool. ONE assembler; this file must never grow a
local unit emitter (SK-7).

No policy number crosses this boundary (R-10, r-floor-single-source): no RAM
floor, no pane cap, no model default — the bindings file states what to bind.

Selftest: `materialize-seats.py --selftest` materializes ONLY against a
throwaway fixture in tempfile.TemporaryDirectory(); it never points at a real
run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

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
    assemble_seat,
    check_acyclic,
    index_units,
    load_catalogs,
)

# ---------------------------------------------------------------- constants

# The env scrub (ignite-job shape): read none of these, unset all of them at
# entry regardless — a detached loop inherits TMUX_PANE and every send is
# refused against the wrong pane.
SCRUBBED_ENV_VARS = ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET")

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
RUN_NAME_RE = re.compile(r"^run-[a-z0-9][a-z0-9-]*$")
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

# ---- dag-06 create-run-package constants ----

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

# ---- dag-04 descriptor-surface constants ----

# F5 — the `mode:` enum, and its fail-closed emission defaults when a bindings
# row carries no explicit mode. `one-shot` for opencode preserves today's
# behaviour (harness_command hardcodes `run --auto`); `interactive` for
# claude. ANY other harness — codex included — has NO default: the row is
# REFUSED at emission (s4-04's fail-closed adjudication: an undecidable mode
# is refused loudly, never defaulted).
DESCRIPTOR_MODES = ("one-shot", "interactive")
MODE_DEFAULTS = {"opencode": "one-shot", "claude": "interactive"}

AGENT_TYPES = ("staff", "worker")

# Contract §1 (seatmd-render-contract.md) — the FIXED kind order the emitted
# file carries, NEVER the catalog's CSV column order. Kinds outside this list
# (invoked-unit stubs: capability, reference) keep assembler order after it.
KIND_ORDER = ("role", "procedure", "permissions", "restrictions", "constraints",
              "io-spec", "resources", "task-goal", "scope", "done-contract")

# Per-seat bindings keys this command understands. Anything else is a refusal
# (a typo'd key must never pass silently). `class` and `relays` are refused
# with their own messages: `class:` is the WITHDRAWN spelling of agent_type
# (r-agent-type-field-name, G-217); `relays:` has no row in the ruled emitted
# key set — owner ask A-40 is OPEN, so emitting OR silently dropping it would
# both be wrong.
ALLOWED_BINDING_KEYS = frozenset((
    "after", "cwd-mode", "description", "agent_type", "harness", "model",
    "effort", "mode", "ctx-refresh", "window", "senders", "close",
    "auto-wake", "ephemeral", "broadcast", "component",
))

# The assembled projection's shapes this file READS (it never emits a block
# itself — SK-7): the assembler's frontmatter fence and its attributed
# kind-tag blocks. The block pattern deliberately starts `<(` so SK-7's
# local-emitter detector cannot match it.
_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_BLOCK_RE = re.compile(
    r'<([a-z0-9-]+) id="([^"]+)" version="([^"]+)">\n(.*?)\n</\1>', re.DOTALL)

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


def validate_package(raw: str) -> Path:
    """The absolute runs/run-N compartment this command materializes into."""
    package = Path(raw)
    if not package.is_absolute():
        raise Refuse(
            "package-not-absolute",
            "--package must be an ABSOLUTE run-package path — never inferred",
            raw,
        )
    if package.parent.name != "runs" or not RUN_NAME_RE.match(package.name):
        raise Refuse(
            "package-not-a-run",
            "--package must resolve to a runs/run-N compartment — seats "
            "materialize into the run folder, never beside their definitions "
            "(d-all-seats-in-run-folder)",
            str(package),
        )
    # An ABSENT package no longer refuses here: dag-06's creation step plans
    # it (plan_package_creation) and creates it AFTER every gate has passed
    # (create_run_package in run()'s write phase) — the bar above still
    # refuses BEFORE any creation, so nothing is ever created off-compartment.
    return package


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
            preds = [p.strip() for p in raw.split(",") if p.strip()]
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


def check_collisions(package: Path, added: list[str], force_partial: bool) -> None:
    """Materialize never overwrites, never merges. A re-run after a partial
    failure is the deliberate --force-partial (its byte-match completion is
    dag-05's; the skeleton only lets the flag pass these gates)."""
    if force_partial:
        return
    rows = {(r.get("seat") or "").strip() for r in _csv_rows(package / TASKFORCE_NAME)}
    for seat in added:
        folder = package / "seats" / seat
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


def _descriptor_frontmatter(seat: str, b: dict, package: str,
                            seats_cat: dict, plan: dict) -> dict:
    """The ruled emitted key set, in its ruled order (d-seatmd-keys-dag04-
    schema; the table in dag-04's task file). `seat:` — never `id:` (B3).
    `class:` and `relays:` never emitted, refused as inputs."""
    for key in b:
        if key == "class":
            raise Refuse(
                "class-withdrawn",
                f"bindings for seat '{seat}' carry 'class:' — the WITHDRAWN "
                "spelling (r-agent-type-field-name, G-217); write "
                "agent_type: staff|worker instead",
            )
        if key == "relays":
            raise Refuse(
                "relays-unruled",
                f"bindings for seat '{seat}' carry 'relays:' — the ruled "
                "emitted key set has no relays row and owner ask A-40 is "
                "OPEN; refusing rather than inventing or silently dropping "
                "the key",
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
    if not effort:
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
    cwd = f"{package}/seats/{seat}/"

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
    for key in ("auto-wake", "ephemeral", "broadcast", "component"):
        val = b.get(key)
        if val not in (None, ""):
            fm[key] = val
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
        plan["descriptors"][seat] = (
            header + intro + "\n\n".join(text for _, text in blocks)
            + "\n" + tail)


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
    writes += [
        {"kind": "seat-descriptor", "seat": seat,
         "path": str(package / "seats" / seat / "seat.md")}
        for seat in added
    ]
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
    return {
        "ok": True,
        "dry_run": dry_run,
        "package": plan["package"],
        "added_seats": plan["added_seats"],
        "writes": plan["writes"],
        "taskforce_rows_appended": appended,
        "warnings": plan["warnings"],
    }


# ------------------------------------------- dag-06 run-package creation


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
    """dag-06 — plan the run-package creation/completion WITHOUT writing
    (d-bootstrap-mechanics-ruled (b)): at the opening of a brand-new goal the
    run does not exist, so the MASTER's bootstrap materialize must create
    `runs/run-N/` and the surfaces a run needs before a seat can check in.
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

    Modes: an ABSENT package (bar already passed) plans full creation and
    requires all three inputs; an existing package missing taskforce.csv is a
    CREATION-PARTIAL half-state and is completed the same way (all inputs
    required — closes the crash-then-flagless-retry window); an existing
    package WITH taskforce.csv (run-2 and every legacy run) completes only
    the structural dirs seats/ and coordination/, plus any caller-input
    surface whose option was explicitly supplied and whose file is missing.
    Existing surfaces are NEVER touched, compared, or overwritten."""
    creating = not package.is_dir()
    if creating:
        goal = package.parent.parent
        if not goal.is_dir():
            raise Refuse(
                "goal-folder-absent",
                f"the goal folder {goal} does not exist — this command "
                "creates a RUN PACKAGE inside an EXISTING goal folder; "
                "creating a goal is rbtv-goal's act, never this command's",
                str(package),
            )
    creation_partial = (not creating
                        and not (package / TASKFORCE_NAME).is_file())
    full = creating or creation_partial

    plan: list[dict] = []
    if creating:
        plan.append({"surface": ".", "path": str(package), "dir": True})

    missing_inputs = []
    for surface, opt, attr in CREATION_INPUTS:
        supplied = getattr(args, attr, None)
        present = (package / surface).is_file() if not creating else False
        if present:
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
            "creating (or completing) this run package needs the "
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
        if creating or not (package / d).is_dir():
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


def emit_seat_descriptors(plan: dict) -> list[str]:
    """dag-04 — write the rendered descriptors: file mode 0644, folder 0755.
    Every gate already fired in render_descriptors (before any write); under
    --force-partial an existing seat.md must byte-match the freshly rendered
    one (completing a partial failure, never overwriting drift)."""
    written: list[str] = []
    for seat in plan["added_seats"]:
        text = plan["descriptors"][seat]
        folder = Path(plan["package"]) / "seats" / seat
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
            continue
        folder.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        target.chmod(0o644)
        folder.chmod(0o755)
        written.append(str(target))
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
    TWO surfaces, both under .rbtv/mirror/meta/planner-workflow/ —
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
            f"the run package carries no {TASKFORCE_NAME} — the append needs "
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

    # taskforce-id: the run's EXISTING id, read from the file — never argv.
    # dag-06 bootstrap story: a registry with ZERO data rows (a freshly
    # created, header-only taskforce.csv — first materialize into a created
    # package) carries no id to read, so the id is DERIVED from the
    # runs/run-N compartment name the package bar already proved: run-N ->
    # tf-N. Deterministic — a pure function of the package path, the same at
    # creation and on every later empty-registry call — never argv, never
    # guessed per call. The derivation fires ONLY on zero data rows: a
    # registry that HAS rows but no readable id still refuses (red arm), and
    # an id read from rows always wins over the derivation.
    ids = {(r.get("taskforce-id") or "").strip() for r in existing_rows}
    ids.discard("")
    if not existing_rows:
        tf_id = "tf-" + Path(plan["package"]).name[len("run-"):]
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
    }


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
    fd, tmp_name = tempfile.mkstemp(dir=str(tf_path.parent),
                                    prefix=f".{TASKFORCE_NAME}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        os.chmod(tmp_name, os.stat(tf_path).st_mode & 0o7777)
        os.replace(tmp_name, tf_path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    plan["rows_appended"] = len(reg["append_lines"])
    return plan["rows_appended"]


def run_sc_acceptance(check, fixture: dict) -> None:
    """dag-07 extension point — the SC-1..SC-16 acceptance rows land here,
    inside the selftest, each with the control arm that must FAIL."""


# ---------------------------------------------------------------- run


def run(args) -> dict:
    package = validate_package(args.package)
    creation = plan_package_creation(package, args)  # dag-06 (plans, no write)
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
    check_collisions(package, added, args.force_partial)
    units = index_units(catalog_root)
    assembled = assemble_all(added, bindings, catalogs, units)
    plan = build_plan(package, added, internal_after, internal_after_raw,
                      attach_after, assembled, bindings, args, creation)
    # dag-04 + dag-05: EVERY gate fires HERE — the emission gates, then the
    # three registry validations — before the dry-run return and before any
    # write, so a refusal always leaves zero files and zero rows.
    render_descriptors(plan, catalogs[0], units)
    render_taskforce_rows(plan)
    if args.dry_run:
        return result_of(plan, dry_run=True)
    # Package surfaces FIRST (dag-06), descriptors SECOND, rows LAST — never
    # another order (the descriptor/rows rationale lives on
    # append_taskforce_rows' docstring; creation must precede both because
    # descriptors land in seats/ and the append re-reads taskforce.csv).
    create_run_package(package, creation)  # dag-06
    emit_seat_descriptors(plan)   # dag-04
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
                   help="absolute run-package path to materialize into "
                        "(runs/run-N). Required, never inferred.")
    what = p.add_mutually_exclusive_group(required=True)
    what.add_argument("--seat",
                      help="materialize ONE cataloged seat (seats.csv row)")
    what.add_argument("--workflow",
                      help="materialize a whole workflow "
                           "(<component>/workflows/<W>/<W>.csv manifest)")
    p.add_argument("--catalog-root", required=True, dest="catalog_root",
                   help="component catalog root the definitions are read from")
    where = p.add_mutually_exclusive_group(required=True)
    where.add_argument("--after",
                       help="comma-separated predecessors the materialized "
                            "root row(s) attach after")
    where.add_argument("--root", action="store_true",
                       help="the materialized row(s) are DAG roots (an "
                            "omitted insertion point never defaults to root)")
    p.add_argument("--bindings", required=True,
                   help="JSON file: per-seat executor binding + descriptor "
                        "surface to materialize with")
    p.add_argument("--milestone-id", dest="milestone_id",
                   help="written to every materialized row; must resolve to a "
                        "milestones.csv row")
    p.add_argument("--conduct", dest="conduct",
                   help="caller-supplied conduct.md BASE-TEXT file, byte-"
                        "copied into a CREATED run package (d-run3-seeds-"
                        "from-run2-amended — this command never invents run "
                        "conventions). Required when creating/completing")
    p.add_argument("--claude-md", dest="claude_md",
                   help="caller-supplied run CLAUDE.md base-text file, byte-"
                        "copied into a CREATED run package (same ruling as "
                        "--conduct). Required when creating/completing")
    p.add_argument("--budget-json", dest="budget_json",
                   help="caller-supplied budget.json file, byte-copied into "
                        "a CREATED run package. A PATH, never a value: the "
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
    args = build_parser().parse_args(argv)  # exits 2 on usage violations
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
    """A throwaway catalog + run package + bindings set, in the settled
    component shape (kind-named XML unit bodies, id in frontmatter; bare and
    @latest unit refs both exercised — the dag-01 widened grammar)."""
    # catalog-root/<component>/... — one level, mirroring the live shape
    # (catalog-root .rbtv/mirror/meta, component planner-workflow).
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

    taskforce = (
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        "tf-1,chief,,claude,claude-opus-5,high,,m1\n"
    )
    milestones = "milestone-id,name,status\nm1,prove the fixture,pending\n"
    pkg = tmp / "goals" / "demo-goal" / "runs" / "run-1"
    (pkg / "seats").mkdir(parents=True)
    (pkg / "coordination").mkdir()  # a run package carries it (coord.py home)
    pkg.joinpath(TASKFORCE_NAME).write_text(taskforce, encoding="utf-8")
    pkg.joinpath(MILESTONES_NAME).write_text(milestones, encoding="utf-8")
    # A second package with seat alpha already materialized — the collision arm.
    pkg9 = tmp / "goals" / "demo-goal" / "runs" / "run-9"
    (pkg9 / "seats" / "alpha").mkdir(parents=True)
    (pkg9 / "coordination").mkdir()
    pkg9.joinpath(TASKFORCE_NAME).write_text(taskforce, encoding="utf-8")
    pkg9.joinpath(MILESTONES_NAME).write_text(milestones, encoding="utf-8")
    # SC-10 control fixture: a registry whose header ALREADY carries `status`.
    pkg_status = tmp / "goals" / "demo-goal" / "runs" / "run-8"
    (pkg_status / "seats").mkdir(parents=True)
    (pkg_status / "coordination").mkdir()
    pkg_status.joinpath(TASKFORCE_NAME).write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,"
        "milestone-id,status\n"
        "tf-1,chief,,claude,claude-opus-5,high,,m1,queued\n", encoding="utf-8")
    # SC-21 fixture: the REPAIRED spine — m4 present, `bootstrap` absent
    # (dag-15's live repair is parked; this spine is the fixture's own).
    pkg_spine = tmp / "goals" / "demo-goal" / "runs" / "run-31"
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
        "pkg_absent": str(tmp / "goals" / "demo-goal" / "runs" / "run-7"),
        "b_both": str(bdir / "both.json"),
        "b_alpha": str(bdir / "alpha.json"),
        "b_missing": str(bdir / "missing.json"),
        "b_extra": str(bdir / "extra.json"),
        "b_badafter": str(bdir / "badafter.json"),
        "b_broken": str(bdir / "broken.json"),
        "b_scramble": str(bdir / "scramble.json"),
        "b_b2": str(bdir / "b2.json"),
        "b_beta": str(bdir / "beta.json"),
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
        ("red: package outside a runs/run-N compartment",
         wf(**{"--package": fx["catalog"]}), 1, "package-not-a-run"),
        ("red: package not absolute",
         wf(**{"--package": "runs/run-1"}), 1, "package-not-absolute"),
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
            elif want_rc == 0 and not green_json:
                green_json = json.loads(cp.stdout)
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
            check("plan: writes name both descriptors and the registry append",
                  len(paths) == 3
                  and paths[0].endswith("seats/alpha/seat.md")
                  and paths[1].endswith("seats/beta/seat.md")
                  and paths[2].endswith(TASKFORCE_NAME),
                  str(paths))
            check("plan: planned append count is 2, warnings plumbed empty",
                  green_json.get("taskforce_rows_appended") == 2
                  and green_json.get("warnings") == [], str(green_json)[:200])
            # SK-5 (amended at dag-05): dry runs and refusals still write
            # NOTHING; the only disk deltas are what the two non-dry green
            # scenarios legitimately materialize — their seat descriptors
            # (new files) plus their registry appends (the ONLY modified
            # pre-existing files). Exactly those, nothing else.
            post = _hash_tree(tmp)
            expected_new = {
                str((Path(fx["pkg"]) / "seats" / s / "seat.md")
                    .relative_to(tmp)) for s in ("alpha", "beta")
            } | {
                str((Path(fx["pkg9"]) / "seats" / "alpha" / "seat.md")
                    .relative_to(tmp)),
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
            run_sc_acceptance(check, fx)  # dag-07 lands SC-1..SC-16 here
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
    #      SC-17 class:, relays (A-40), senders, SC-19 window ------------
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

        def s1_bindings(name: str, extra: dict) -> str:
            entry = {"model": "deepseek/deepseek-chat", "after": [], **extra}
            p = bdir / name
            p.write_text(json.dumps({"version": 1, "defaults": wide_defaults,
                                     "seats": {"s1": entry}}),
                         encoding="utf-8")
            return str(p)

        def s1_argv(b: str, dry: bool = True) -> list[str]:
            base = ["--package", fx["pkg9"], "--seat", "s1",
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
        cp = _invoke(s1_argv(s1_bindings("relays.json",
                                         {"relays": "master"})), env)
        check("relays: refused as an input — A-40 is OPEN, never invented "
              "or silently dropped",
              cp.returncode == 1
              and _refusal(cp).get("code") == "relays-unruled"
              and "A-40" in _refusal(cp).get("message", ""),
              cp.stdout.strip()[:200])
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

    # ---- group 4: goal_cli lint over an emitted package (the dag-01
    #      guard-comment contract: no scalar key false-positives) --------
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        fx = build_fixture(tmp)
        groot = tmp / "lintgoals"
        gdir = groot / "demo-goal"
        run1 = gdir / "runs" / "run-1"
        (run1 / "seats").mkdir(parents=True)
        (run1 / "coordination").mkdir()
        (gdir / "goal.md").write_text(
            "---\nname: demo-goal\ncreation-date: 2026-07-29\n"
            "type: one-shot\nstatus: active\n---\n\n"
            "Prove the emitted descriptor surface lints clean.\n",
            encoding="utf-8")
        (gdir / "decisions.md").write_text("# decisions\n", encoding="utf-8")
        (gdir / "threads.sql").write_text("-- threads\n", encoding="utf-8")
        (gdir / "runs.csv").write_text(
            "run-id,type,state,taskforce-id(s),opened,closed\n"
            "run-1,build,active,tf-1,2026-07-29,\n", encoding="utf-8")
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
        for seat in ("alpha", "beta"):
            cpl = coord(["--package", fx["pkg"], "--as", "chief-of-staff",
                         "launch", "--dry-run", "--only", seat])
            check(f"SC-1: coordinate launch --dry-run --only {seat} resolves "
                  "a harness command",
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
              "run folder, never the catalog (d-all-seats-in-run-folder)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "package-not-a-run",
              cp.stdout.strip()[:200])
        cp = _invoke(["--package", fx["pkg_spine"], "--seat", "alpha",
                      "--catalog-root", fx["catalog"], "--after", "chief",
                      "--bindings", fx["b_alpha"], "--dry-run", "--json"], env)
        check("SC-15 control: a real run package is accepted",
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
        groot = tmp / "lintgoals"
        gdir = groot / "demo-goal"
        run1 = gdir / "runs" / "run-1"
        (run1 / "seats").mkdir(parents=True)
        (run1 / "coordination").mkdir()
        (gdir / "goal.md").write_text(
            "---\nname: demo-goal\ncreation-date: 2026-07-29\n"
            "type: one-shot\nstatus: active\n---\n\nProve SC-8.\n",
            encoding="utf-8")
        (gdir / "decisions.md").write_text("# decisions\n", encoding="utf-8")
        (gdir / "threads.sql").write_text("-- threads\n", encoding="utf-8")
        (gdir / "runs.csv").write_text(
            "run-id,type,state,taskforce-id(s),opened,closed\n"
            "run-1,build,active,tf-1,2026-07-29,\n", encoding="utf-8")
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
        goal = tmp / "g6-goal"
        goal.mkdir()
        pkg = goal / "runs" / "run-1"  # live-held tag: register declines

        def create_argv(seat, bindings, extra=()):
            return ["--package", str(pkg), "--seat", seat,
                    "--catalog-root", fx["catalog"], "--root",
                    "--bindings", bindings,
                    "--conduct", fx["src_conduct"],
                    "--claude-md", fx["src_claude"],
                    "--budget-json", fx["src_budget"], "--json", *extra]

        # CP-7: --dry-run against the ABSENT package — plan printed, nothing
        # on disk.
        cp = _invoke(create_argv("alpha", fx["b_alpha"], ("--dry-run",)), env)
        plan_writes = (json.loads(cp.stdout)
                       if cp.returncode == 0 else {}).get("writes", [])
        planned = {w.get("surface") for w in plan_writes
                   if w["kind"] == "package-surface"}
        check("CP-7: dry-run against an absent package exits 0 and the "
              "printed plan names every created surface",
              cp.returncode == 0
              and {".", "conduct.md", "CLAUDE.md", "budget.json",
                   TASKFORCE_NAME, STATE_CSV_NAME, "seats",
                   "coordination"} <= planned,
              (cp.stdout + cp.stderr).strip()[:200])
        check("CP-7: ...and writes NOTHING — neither the package nor runs/ "
              "exists after the dry-run",
              not pkg.exists() and not (goal / "runs").exists())

        # CP-1 green: the same argv without --dry-run CREATES + materializes.
        cp = _invoke(create_argv("alpha", fx["b_alpha"]), env)
        created = json.loads(cp.stdout) if cp.returncode == 0 else {}
        surfaces = {w.get("surface") for w in created.get("writes", [])
                    if w["kind"] == "package-surface"}
        check("CP-1: a materialize against a NON-EXISTENT --package creates "
              "the package and materializes into it, announcing every "
              "created surface in writes[]",
              cp.returncode == 0
              and (pkg / "seats" / "alpha" / "seat.md").is_file()
              and (pkg / "coordination").is_dir()
              and (pkg / TASKFORCE_NAME).is_file()
              and (pkg / STATE_CSV_NAME).is_file()
              and {".", "conduct.md", "CLAUDE.md", "budget.json"} <= surfaces,
              (cp.stdout + cp.stderr).strip()[:200])
        check("CP-7 control: the dry flag is the discriminator — the same "
              "argv without it created the package", pkg.is_dir())
        check("state.csv: the created cursor carries EXACTLY the ruled "
              "header, header only (r-stage0-state-cursor-interim-convention)",
              (pkg / STATE_CSV_NAME).read_text(encoding="utf-8")
              == STATE_CSV_HEADER + "\n")

        rows = list(csv.DictReader(
            (pkg / TASKFORCE_NAME).read_text(encoding="utf-8").splitlines()))
        check("tf-id: the first materialize into a created package derives "
              "the id from the compartment (run-1 -> tf-1), never argv",
              [r["taskforce-id"] for r in rows] == ["tf-1"]
              and rows[0]["seat"] == "alpha", str(rows))

        # CP-1 control: the SAME call with the create step disabled refuses.
        pkg2 = goal / "runs" / "run-2"
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
              refused and not pkg2.exists())

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
        goal = tmp / "g6-goal"
        goal.mkdir()

        def argv_for(pkg, seat, bindings, extra=()):
            return ["--package", str(pkg), "--seat", seat,
                    "--catalog-root", fx["catalog"], "--root",
                    "--bindings", bindings,
                    "--conduct", fx["src_conduct"],
                    "--claude-md", fx["src_claude"],
                    "--budget-json", fx["src_budget"], "--json", *extra]

        # CP-4: an absent path OUTSIDE runs/run-N refuses with NOTHING
        # created — creation never bypasses SC-15's bar.
        outside = tmp / "whatever"
        cp = _invoke(argv_for(outside, "alpha", fx["b_alpha"]), env)
        check("CP-4: --package <absent, outside runs/run-N> refuses "
              "(package-not-a-run) and creates nothing on disk",
              cp.returncode == 1
              and _refusal(cp).get("code") == "package-not-a-run"
              and not outside.exists())
        nogoal_pkg = tmp / "no-goal" / "runs" / "run-1"
        cp = _invoke(argv_for(nogoal_pkg, "alpha", fx["b_alpha"]), env)
        check("CP-4: an absent GOAL folder refuses (goal-folder-absent — "
              "goal creation is rbtv-goal's) and creates nothing",
              cp.returncode == 1
              and _refusal(cp).get("code") == "goal-folder-absent"
              and not (tmp / "no-goal").exists())
        # CP-4 control: <goal>/runs/run-9 (absent, correct shape) IS created.
        pkg9 = goal / "runs" / "run-9"
        cp = _invoke(argv_for(pkg9, "alpha", fx["b_alpha"]), env)
        rows9 = (list(csv.DictReader((pkg9 / TASKFORCE_NAME).read_text(
            encoding="utf-8").splitlines())) if pkg9.is_dir() else [])
        check("CP-4 control: <goal>/runs/run-9 (absent) IS created and "
              "materialized",
              cp.returncode == 0
              and (pkg9 / "seats" / "alpha" / "seat.md").is_file())
        check("tf-id: the run-9 compartment derives tf-9",
              [r["taskforce-id"] for r in rows9] == ["tf-9"], str(rows9))

        # Creation is gated like every write: a later-gate refusal on an
        # absent package leaves NOTHING created.
        pkg5 = goal / "runs" / "run-5"
        cp = _invoke(argv_for(pkg5, "beta", fx["b_alpha"]), env)
        check("gated creation: a bindings refusal against an absent package "
              "leaves nothing created (creation fires after every gate)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "bindings-missing-seat"
              and not pkg5.exists())

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
              and not pkg5.exists())
        argv8 = argv_for(pkg5, "alpha", fx["b_alpha"])
        i = argv8.index("--budget-json")
        del argv8[i:i + 2]
        cp = _invoke(argv8, env)
        check("CP-6/CP-8 red: omitting the budget source REFUSES naming "
              "--budget-json — a floor is never defaulted (R-10)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "create-inputs-missing"
              and "--budget-json" in _refusal(cp).get("message", "")
              and not pkg5.exists())
        argvb = argv_for(pkg5, "alpha", fx["b_alpha"])
        argvb[argvb.index("--budget-json") + 1] = fx["src_budget_broken"]
        cp = _invoke(argvb, env)
        check("budget-source red: a caller budget.json with no "
              "floors.launch_refuse_mb refuses at creation "
              "(create-input-invalid), before any write",
              cp.returncode == 1
              and _refusal(cp).get("code") == "create-input-invalid"
              and not pkg5.exists())

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
        pkg6 = goal / "runs" / "run-6"
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
        pkg7 = goal / "runs" / "run-7"
        (pkg7 / "seats").mkdir(parents=True)
        (pkg7 / "coordination").mkdir()
        (pkg7 / TASKFORCE_NAME).write_text(
            ",".join(TASKFORCE_HEADER) + "\n"
            ",chief,,claude,claude-opus-5,high,,\n", encoding="utf-8")
        cp = _invoke(["--package", str(pkg7), "--seat", "alpha",
                      "--catalog-root", fx["catalog"], "--root",
                      "--bindings", fx["b_alpha"], "--json"], env)
        check("tf-id red: a registry WITH rows but no readable id refuses "
              "(taskforce-id-unreadable) — the compartment derivation never "
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
        check("tf-id: an id READ FROM THE FILE (tf-1) wins over the run-7 "
              "compartment derivation — the appended row carries tf-1",
              cp.returncode == 0
              and [r["taskforce-id"] for r in rows7] == ["tf-1", "tf-1"],
              str(rows7))


def run_selftest() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
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

    print("dag-04 acceptance pass (SC rows, each with its failing control)")
    run_dag04_acceptance(check, clean_env)

    print("dag-05 acceptance pass (SC-1/5/6/8/9/10/15/20/21, both arms each)")
    run_dag05_acceptance(check, clean_env)

    print("dag-06 acceptance pass (CP-1..CP-8, both arms each)")
    run_dag06_acceptance(check, clean_env)

    print(f"\n{'PASS' if not failures else 'FAIL'} — "
          f"{len(failures)} failure(s)")
    for f in failures:
        print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
