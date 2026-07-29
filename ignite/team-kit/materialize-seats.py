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
Named extension points for the follow-on tasks:

    append_taskforce_rows  -> dag-05  (registry append: topological order,
                                       acyclicity via goal_cli.check_acyclic,
                                       --force-partial byte-match completion)
    create_run_package     -> dag-06  (bootstrap run-package creation,
                                       d-bootstrap-mechanics-ruled (b))
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
    Refusal as CatalogRefusal,
    assemble_seat,
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
    if not package.is_dir():
        create_run_package(package)  # dag-06 extension point (refuses today)
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


def resolve_added(args, catalog_root: Path, seats_catalog: dict) -> tuple[list[str], dict]:
    """Resolve the seat set this run materializes.

    --seat resolves against the SEAT CATALOG (seats.csv), never the manifest —
    a cataloged seat that no manifest row references is legal by construction.
    --workflow resolves against the workflow manifest
    {catalog-root}/<component>/workflows/<W>/<W>.csv.

    Returns (added seat ids in manifest order, internal after map).
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
        return [args.seat], {args.seat: []}

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
            preds = [p.strip() for p in (row.get(MANIFEST_AFTER_COLUMN) or "").split(",")
                     if p.strip()]
            added.append(seat)
            internal_after[seat] = preds
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
    return added, internal_after


def validate_after(args, package: Path) -> list[str]:
    """The insertion point: every --after member must resolve to an existing
    taskforce.csv row — a dangling predecessor is an edge that never fires."""
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
               attach_after: list[str], assembled: dict, bindings: dict,
               args) -> dict:
    """The write plan: descriptors first, then the registry append — never the
    reverse (orphan folders are the strictly safer half-state)."""
    writes = [
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
        "added_seats": list(added),
        "internal_after": internal_after,
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
    count is the PLANNED append."""
    return {
        "ok": True,
        "dry_run": dry_run,
        "package": plan["package"],
        "added_seats": plan["added_seats"],
        "writes": plan["writes"],
        "taskforce_rows_appended": len(plan["added_seats"]),
        "warnings": plan["warnings"],
    }


# ------------------------------------------------- extension points (stubs)
# Each stub REFUSES loudly rather than reporting work it did not do — a green
# from a command that materialized nothing is the defect class this tree
# measures for.


def create_run_package(package: Path) -> None:
    """dag-06 extension point — bootstrap run-package creation
    (d-bootstrap-mechanics-ruled (b)): create runs/run-N/ and its
    state/coordination surfaces when absent, so the MASTER can materialize at
    bootstrap. Until dag-06 lands, an absent package refuses."""
    raise Refuse(
        "package-absent",
        "the run package does not exist and run-package creation lands in "
        "dag-06 — nothing materialized",
        str(package),
    )


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


def append_taskforce_rows(plan: dict) -> int:
    """dag-05 extension point — the registry append: one row per added seat in
    topological order of the added subgraph, acyclicity via
    goal_cli.check_acyclic (never a hand-rolled walk), atomic
    read → append → replace, --force-partial byte-match completion. Until
    dag-05 lands, this path refuses, writing nothing."""
    raise Refuse(
        "not-implemented",
        f"the {TASKFORCE_NAME} append lands in dag-05 — nothing materialized",
    )


def run_sc_acceptance(check, fixture: dict) -> None:
    """dag-07 extension point — the SC-1..SC-16 acceptance rows land here,
    inside the selftest, each with the control arm that must FAIL."""


# ---------------------------------------------------------------- run


def run(args) -> dict:
    package = validate_package(args.package)
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
    added, internal_after = resolve_added(args, catalog_root, catalogs[0])
    check_bindings_cover(bindings, added)
    attach_after = validate_after(args, package)
    validate_milestone(args, package)
    check_collisions(package, added, args.force_partial)
    units = index_units(catalog_root)
    assembled = assemble_all(added, bindings, catalogs, units)
    plan = build_plan(package, added, internal_after, attach_after,
                      assembled, bindings, args)
    # dag-04: every emission gate fires HERE — before the dry-run return and
    # before any write, so a refusal always leaves zero files and zero rows.
    render_descriptors(plan, catalogs[0], units)
    if args.dry_run:
        return result_of(plan, dry_run=True)
    # Descriptors FIRST, then rows — never the reverse.
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
        "beta,beta-prompt,beta-task,,the beta seat\n", encoding="utf-8")
    wf_dir = comp / "workflows" / "demo-flow"
    wf_dir.mkdir(parents=True)
    wf_dir.joinpath("demo-flow.csv").write_text(
        'Seat/workflow,after,i/o,Modality\n'
        'alpha,,"in: run inputs; out: alpha-notes.md",agentic\n'
        'beta,alpha,"in: alpha-notes.md; out: beta-report.md",agentic\n',
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
    pkg.joinpath(TASKFORCE_NAME).write_text(taskforce, encoding="utf-8")
    pkg.joinpath(MILESTONES_NAME).write_text(milestones, encoding="utf-8")
    # A second package with seat alpha already materialized — the collision arm.
    pkg9 = tmp / "goals" / "demo-goal" / "runs" / "run-9"
    (pkg9 / "seats" / "alpha").mkdir(parents=True)
    pkg9.joinpath(TASKFORCE_NAME).write_text(taskforce, encoding="utf-8")
    pkg9.joinpath(MILESTONES_NAME).write_text(milestones, encoding="utf-8")

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

    return {
        "tmp": tmp,
        "catalog": str(tmp / "catalog"),
        "pkg": str(pkg),
        "pkg9": str(pkg9),
        "pkg_absent": str(tmp / "goals" / "demo-goal" / "runs" / "run-7"),
        "b_both": str(bdir / "both.json"),
        "b_alpha": str(bdir / "alpha.json"),
        "b_missing": str(bdir / "missing.json"),
        "b_extra": str(bdir / "extra.json"),
        "b_badafter": str(bdir / "badafter.json"),
        "b_broken": str(bdir / "broken.json"),
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
        ("red: absent package refuses at the dag-06 extension point",
         wf(**{"--package": fx["pkg_absent"]}), 1, "package-absent"),
        ("red: unreadable bindings JSON",
         wf(**{"--bindings": fx["b_broken"]}), 1, "bindings-unreadable"),
        ("red: dangling --after member",
         [a if a != "chief" else "ghost" for a in seat_argv], 1,
         "after-unresolved"),
        ("red: collision with an existing seat folder",
         ["--package", fx["pkg9"], "--seat", "alpha", "--catalog-root",
          fx["catalog"], "--after", "chief", "--bindings", fx["b_alpha"],
          "--dry-run", "--json"], 1, "seat-exists"),
        ("red: --force-partial passes the collision gate, emits the missing "
         "descriptor, then the dag-05 half is unbuilt",
         ["--package", fx["pkg9"], "--seat", "alpha", "--catalog-root",
          fx["catalog"], "--after", "chief", "--bindings", fx["b_alpha"],
          "--force-partial", "--json"], 1, "not-implemented"),
        ("red: a non-dry run emits descriptors (dag-04), then refuses at the "
         "dag-05 extension point",
         wf(flags=["--root", "--json"]), 1, "not-implemented"),
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
            # SK-5 (amended at dag-04): dry runs and refusals still write
            # NOTHING; the only disk deltas are the descriptor emissions the
            # two non-dry scenarios legitimately perform before dag-05's
            # unbuilt half refuses. Exactly those files, nothing else, and
            # every pre-existing file byte-unchanged.
            post = _hash_tree(tmp)
            expected_new = {
                str((Path(fx["pkg"]) / "seats" / s / "seat.md")
                    .relative_to(tmp)) for s in ("alpha", "beta")
            } | {
                str((Path(fx["pkg9"]) / "seats" / "alpha" / "seat.md")
                    .relative_to(tmp)),
            }
            check("SK-5: the only writes are the dag-04 descriptor emissions",
                  set(post) - set(pre) == expected_new
                  and all(post[k] == v for k, v in pre.items()),
                  f"unexpected delta: {sorted(set(post) ^ set(pre))[:6]}")
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
        check("dag-04 setup: non-dry emit lands both descriptors "
              "(dag-05 half still refuses)",
              cp.returncode == 1
              and _refusal(cp).get("code") == "not-implemented"
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
              "writes all 5 descriptors",
              cp.returncode == 1
              and _refusal(cp).get("code") == "not-implemented"
              and all(p.is_file() for p in smds),
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
        cp = _invoke(["--package", str(run1), "--workflow", "demo-flow",
                      "--catalog-root", fx["catalog"], "--bindings",
                      fx["b_both"], "--root", "--json"], env)
        check("lint setup: descriptors emitted into the goal fixture",
              (run1 / "seats" / "alpha" / "seat.md").is_file()
              and (run1 / "seats" / "beta" / "seat.md").is_file(),
              cp.stdout.strip()[:200])
        # dag-05 is unbuilt — hand-write the registry rows the lint reads.
        (run1 / TASKFORCE_NAME).write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh\n"
            "tf-a,alpha,,claude,claude-opus-5,high,50\n"
            "tf-b,beta,alpha,claude,claude-opus-5,high,50\n",
            encoding="utf-8")
        from goal_cli import lint_goal
        f = lint_goal(groot, "demo-goal")
        check("goal_cli lint: the emitted package lints CLEAN — no scalar "
              "key false-positives as an unresolved ref",
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

    print(f"\n{'PASS' if not failures else 'FAIL'} — "
          f"{len(failures)} failure(s)")
    for f in failures:
        print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
