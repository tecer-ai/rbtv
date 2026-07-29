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

This file is the dag-03 SKELETON: argument parsing, resolution, refusal
plumbing, JSON result, environment scrub, selftest harness + fixture builder.
Named extension points for the follow-on tasks:

    emit_seat_descriptors  -> dag-04  (descriptor emission: `seat:` frontmatter
                                       surface, mode/ctx-refresh/close rules,
                                       validate_seat batch gate before any write,
                                       empty-assembly refusal)
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

# goal_cli.py is the goals-tree capability sibling of this team-kit — resolved
# relative to this file, never from a hardcoded workspace path.
_GOAL_CLI_DIR = Path(__file__).resolve().parent.parent / "capabilities" / "goals-tree" / "tool"
if str(_GOAL_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(_GOAL_CLI_DIR))

from goal_cli import (  # noqa: E402 — path bound just above
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


def assemble_all(added: list[str], bindings: dict, catalog_root: Path,
                 catalogs: tuple[dict, dict, dict]) -> dict[str, str]:
    """Assemble every added seat IN MEMORY first (a refusal on seat 7 of 7
    must leave zero files) — through goal_cli's ONE assembler."""
    seats_cat, prompts_cat, tasks_cat = catalogs
    units = index_units(catalog_root)
    return {
        seat: assemble_seat(seat, effective_binding(bindings, seat),
                            seats_cat, prompts_cat, tasks_cat, units)
        for seat in added
    }


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
    """dag-04 extension point — descriptor emission: write each assembled
    seat.md with the `seat:` (never `id:`) frontmatter surface, the
    mode/ctx-refresh/close rules, and the validate_seat whole-batch gate
    BEFORE any write; refuse an assembly with no cognitive-unit block. Until
    dag-04 lands, a non-dry run refuses here, writing nothing."""
    raise Refuse(
        "not-implemented",
        "descriptor emission lands in dag-04 — nothing materialized; run "
        "with --dry-run to see the write plan",
    )


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
    added, internal_after = resolve_added(args, catalog_root, catalogs[0])
    check_bindings_cover(bindings, added)
    attach_after = validate_after(args, package)
    validate_milestone(args, package)
    check_collisions(package, added, args.force_partial)
    assembled = assemble_all(added, bindings, catalog_root, catalogs)
    plan = build_plan(package, added, internal_after, attach_after,
                      assembled, bindings, args)
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
    role_dir = comp / "prompts" / "cognitive-units" / "role"
    perm_dir = comp / "prompts" / "cognitive-units" / "permissions"
    proc_dir = comp / "tasks" / "cognitive-units" / "procedure"
    for d in (role_dir, perm_dir, proc_dir):
        d.mkdir(parents=True)
    role_dir.joinpath("alpha-role.md").write_text(
        "---\nid: alpha-role\ndescription: alpha role\n---\n\n"
        "<role>\nYou are alpha.\n</role>\n", encoding="utf-8")
    role_dir.joinpath("beta-role.md").write_text(
        "---\nid: beta-role\ndescription: beta role\n---\n\n"
        "<role>\nYou are beta.\n</role>\n", encoding="utf-8")
    perm_dir.joinpath("common-permissions.md").write_text(
        "---\nid: common-permissions\ndescription: common permissions\n---\n\n"
        "<permissions>\nRead the fixture tree. Write only your outputs.\n"
        "</permissions>\n", encoding="utf-8")
    proc_dir.joinpath("alpha-procedure.md").write_text(
        "---\nid: alpha-procedure\ndescription: alpha procedure\n---\n\n"
        "<procedure>\nProduce alpha-notes.md.\n</procedure>\n", encoding="utf-8")
    proc_dir.joinpath("beta-procedure.md").write_text(
        "---\nid: beta-procedure\ndescription: beta procedure\n---\n\n"
        "<procedure>\nProduce beta-report.md.\n</procedure>\n", encoding="utf-8")
    comp.joinpath("prompts.csv").write_text(
        "prompt-id,role,permissions,description\n"
        "alpha-prompt,alpha-role@latest,common-permissions,alpha prompt\n"
        "beta-prompt,beta-role,common-permissions@latest,beta prompt\n",
        encoding="utf-8")
    comp.joinpath("tasks.csv").write_text(
        "task-id,procedure,description\n"
        "alpha-task,alpha-procedure,alpha task\n"
        "beta-task,beta-procedure,beta task\n", encoding="utf-8")
    comp.joinpath("seats.csv").write_text(
        "seat-id,prompt-id,task-id,description\n"
        "alpha,alpha-prompt,alpha-task,the alpha seat\n"
        "beta,beta-prompt,beta-task,the beta seat\n", encoding="utf-8")
    wf_dir = comp / "workflows" / "demo-flow"
    wf_dir.mkdir(parents=True)
    wf_dir.joinpath("demo-flow.csv").write_text(
        'Seat/workflow,after,i/o,Modality\n'
        'alpha,,"in: run inputs; out: alpha-notes.md",agentic\n'
        'beta,alpha,"in: alpha-notes.md; out: beta-report.md",agentic\n',
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
        ("red: --force-partial passes the collision gate, then the dag-05 "
         "half is unbuilt",
         ["--package", fx["pkg9"], "--seat", "alpha", "--catalog-root",
          fx["catalog"], "--after", "chief", "--bindings", fx["b_alpha"],
          "--force-partial", "--json"], 1, "not-implemented"),
        ("red: a non-dry run refuses at the dag-04 extension point",
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
            # SK-5: nothing in the fixture tree changed — dry runs, refusals,
            # and the unbuilt write path alike wrote NOTHING.
            check("SK-5: no scenario wrote anything (tree hashes identical)",
                  _hash_tree(tmp) == pre)
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

    print(f"\n{'PASS' if not failures else 'FAIL'} — "
          f"{len(failures)} failure(s)")
    for f in failures:
        print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
