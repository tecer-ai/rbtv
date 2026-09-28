#!/usr/bin/env python3
"""validate-seams — machine-verify the transcript-summarizer seam set.

Deterministic: file reads, JSON Schema validation, string scans. No network, no
model call. Run with --help for the full command surface.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
from pathlib import Path

TOOL_FILE = Path(__file__).resolve()
TOOL_DIR = TOOL_FILE.parent

# ---------------------------------------------------------------- the 20 entries
# Hardcoded on purpose: coverage is the milestone threshold (16 crossings +
# 4 stores), so the expected set lives in the checker, never in the checked file.
# `artifact-content` joined the set at m6, which is the milestone the design
# assigns the one missing seam to (S-10 #5, the artifact-content reader
# protocol): adding a crossing therefore means raising this count with it.
CROSSINGS = (
    "verified-source-map",
    "findings-payload",
    "attestation-boundary",
    "window-contract",
    "transcript-record",
    "meeting-key-and-source-set",
    "per-meeting-job",
    "destination-repo-set",
    "failure-event-and-outcome",
    "meeting-message-payload",
    "doubt-flag-marker",
    "glossary-artifact",
    "owner-answer",
    "deferred-filed-note",
    "completion-record",
    "artifact-content",
)
STORES = (
    "processed-transcript-store",
    "poll-watermark-store",
    "thread-meeting-map-store",
    "glossary-store",
)
CONSTRAINT_ID = "attestation-boundary"  # counts as a crossing for coverage
CONSTRAINT_DOC = "attestation-boundary.md"

EXPECTED_KIND = {entry: "crossing" for entry in CROSSINGS}
EXPECTED_KIND.update({entry: "store" for entry in STORES})
EXPECTED_KIND[CONSTRAINT_ID] = "constraint"
EXPECTED_IDS = frozenset(EXPECTED_KIND)
KINDS = ("crossing", "store", "constraint")

INDEX_NAME = "index.csv"
INDEX_HEADER = ["entry-id", "kind", "schema-file", "instance-files"]
# instance-files holds one or more paths; every plausible authoring is accepted.
LIST_SEP = re.compile(r"[;,|\s]+")

DRAFT_URI = "https://json-schema.org/draft/2020-12/schema"

# Owner attestation (goal.md clause 17) settles the Workspace edition and the
# Tactiq volume cap. Code that probes either is a defect, not a safeguard.
FORBIDDEN_PATTERNS = (
    ("workspace-edition", re.compile(r"workspace edition", re.I)),
    ("edition-check", re.compile(r"edition check", re.I)),
    ("tactiq-volume-cap", re.compile(r"tactiq.*(volume|cap|quota|limit)", re.I)),
    ("plan-tier-gate", re.compile(r"plan.*(tier|gate)", re.I)),
)
SKIP_DIRS = frozenset({".git", "__pycache__", ".mypy_cache"})

ARMS = ("coverage", "refs", "instances", "mutation", "grep", "constraint")

SCHEMA_GLOB = "*.schema.json"

EXIT_OK = 0
EXIT_VERDICT = 1  # ran fine, seam set is not valid
EXIT_REFUSED = 2  # could not run

_JSON_MODE = False


# ------------------------------------------------------------------- plumbing
def refuse(what: str, why: str, fix: str, escape: str) -> None:
    """Teaching refusal: what happened, why, how to fix, what the escape is."""
    if _JSON_MODE:
        json.dump(
            {"ok": False, "error": {"what": what, "why": why, "fix": fix, "escape": escape}},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(f"refused: {what}", file=sys.stderr)
        print(f"  why:    {why}", file=sys.stderr)
        print(f"  fix:    {fix}", file=sys.stderr)
        print(f"  escape: {escape}", file=sys.stderr)
    sys.exit(EXIT_REFUSED)


def load_validator():
    """Return jsonschema's Draft 2020-12 validator class, or refuse."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - environment refusal
        refuse(
            what="the jsonschema library is not importable",
            why=str(exc),
            fix="install it for this interpreter: python3 -m pip install jsonschema",
            escape="none — this tool never vendors a validator; every verdict it "
            "emits must come from a real draft 2020-12 implementation",
        )
    return Draft202012Validator


def load_referencing():
    """Return (Registry, Resource, DRAFT202012, Unresolvable), or refuse.

    `referencing` is jsonschema's own dependency since 4.18, so it is present
    wherever the validator is — but say so plainly if it ever is not.
    """
    try:
        from referencing import Registry, Resource
        from referencing.exceptions import Unresolvable
        from referencing.jsonschema import DRAFT202012
    except ImportError as exc:  # pragma: no cover - environment refusal
        refuse(
            what="the referencing library is not importable",
            why=str(exc),
            fix="install it for this interpreter: python3 -m pip install referencing",
            escape="none — cross-file $ref resolution needs a real reference registry; "
            "this tool never resolves references by hand",
        )
    return Registry, Resource, DRAFT202012, Unresolvable


def build_registry(seams_dir: Path):
    """Preload every schema file under the seams dir so cross-file $ref resolves.

    Each schema is registered under BOTH its bare filename and its path relative
    to the seams dir, because either is a legitimate way to write the $ref:
    `{"$ref": "meeting-key.schema.json"}` and `{"$ref": "shared/meeting-key.schema.json"}`
    are both valid draft 2020-12 and both must resolve.
    """
    Registry, Resource, DRAFT202012, _ = load_referencing()
    registry = Registry()
    keys: list[str] = []
    for path in sorted(seams_dir.rglob(SCHEMA_GLOB)):
        if not path.is_file() or SKIP_DIRS & set(path.parts):
            continue
        contents, error = read_json(path)
        if error or not isinstance(contents, dict):
            continue  # an unparseable schema is the instances arm's finding, not ours
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        relative = path.relative_to(seams_dir).as_posix()
        pair = {path.name, relative}
        registry = registry.with_resources([(key, resource) for key in sorted(pair)])
        keys += sorted(pair)
    return registry, sorted(set(keys))


def read_json(path: Path):
    """(value, error-string). Never raises."""
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError:
        return None, f"file not found: {path}"
    except UnicodeDecodeError as exc:
        return None, f"not utf-8: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"not valid JSON: {exc}"


def split_list(cell: str) -> list[str]:
    return [item for item in LIST_SEP.split(cell.strip()) if item]


# ----------------------------------------------------------------- index read
def read_index(seams_dir: Path):
    """(rows, fatal). rows are dicts keyed by INDEX_HEADER, in file order."""
    index_path = seams_dir / INDEX_NAME
    if not index_path.is_file():
        return [], f"no {INDEX_NAME} at {index_path}"
    try:
        text = index_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [], f"cannot read {index_path}: {exc}"
    reader = csv.reader(text.splitlines())
    try:
        header = next(reader)
    except StopIteration:
        return [], f"{index_path} is empty"
    header = [column.strip() for column in header]
    if header != INDEX_HEADER:
        return [], f"{index_path} header is {header}, expected {INDEX_HEADER}"
    rows = []
    for number, raw in enumerate(reader, start=2):
        if not any(cell.strip() for cell in raw):
            continue
        if len(raw) != len(INDEX_HEADER):
            return [], f"{index_path}:{number} has {len(raw)} cells, expected {len(INDEX_HEADER)}"
        row = {column: cell.strip() for column, cell in zip(INDEX_HEADER, raw)}
        row["line"] = number
        rows.append(row)
    return rows, None


# --------------------------------------------------------------- the five arms
def arm_coverage(rows: list[dict]) -> dict:
    """The entry-id set must be EXACTLY the hardcoded 19."""
    seen: dict[str, list[int]] = {}
    for row in rows:
        seen.setdefault(row["entry-id"], []).append(row["line"])
    missing = sorted(EXPECTED_IDS - set(seen))
    extra = sorted(set(seen) - EXPECTED_IDS)
    duplicated = sorted(entry for entry, lines in seen.items() if len(lines) > 1)
    bad_kind = []
    for row in rows:
        entry = row["entry-id"]
        if row["kind"] not in KINDS:
            bad_kind.append(f"{entry}: kind '{row['kind']}' is not one of {list(KINDS)}")
        elif entry in EXPECTED_KIND and row["kind"] != EXPECTED_KIND[entry]:
            bad_kind.append(
                f"{entry}: kind '{row['kind']}' declared, expected '{EXPECTED_KIND[entry]}'"
            )
    crossings_present = sum(1 for entry in CROSSINGS if entry in seen)
    stores_present = sum(1 for entry in STORES if entry in seen)
    problems = []
    problems += [f"coverage: missing entry-id '{entry}'" for entry in missing]
    problems += [f"coverage: unexpected entry-id '{entry}'" for entry in extra]
    problems += [
        f"coverage: duplicated entry-id '{entry}' (lines {seen[entry]})" for entry in duplicated
    ]
    problems += [f"coverage: {message}" for message in bad_kind]
    return {
        "crossings": f"{crossings_present}/{len(CROSSINGS)}",
        "stores": f"{stores_present}/{len(STORES)}",
        "missing": missing,
        "extra": extra,
        "duplicated": duplicated,
        "kind-mismatches": bad_kind,
        "problems": problems,
        "ok": not problems,
    }


def collect_refs(node, found: list[str]) -> list[str]:
    """Every cross-file `$ref` in a schema, in document order. Local `#...` refs skipped."""
    if isinstance(node, dict):
        target = node.get("$ref")
        if isinstance(target, str) and target and not target.startswith("#"):
            found.append(target)
        for value in node.values():
            collect_refs(value, found)
    elif isinstance(node, list):
        for item in node:
            collect_refs(item, found)
    return found


def arm_refs(rows: list[dict], seams_dir: Path, registry) -> dict:
    """Every cross-file $ref a schema declares must resolve in the registry.

    Checked directly against the registry rather than as a side effect of
    validating an instance: a reference inside a branch no instance happens to
    exercise is still a broken seam set, and it must be reported as a finding
    rather than surfacing later as a traceback.
    """
    _, _, _, Unresolvable = load_referencing()
    resolver = registry.resolver()
    problems: list[str] = []
    references: list[dict] = []
    seen_schemas: set[str] = set()
    for row in rows:
        name = row["schema-file"]
        if not name or name in seen_schemas:
            continue
        seen_schemas.add(name)
        schema, error = read_json(seams_dir / name)
        if error or not isinstance(schema, dict):
            continue  # the instances arm owns unparseable schemas
        for target in collect_refs(schema, []):
            record = {"schema": name, "ref": target, "resolved": True}
            try:
                resolver.lookup(target)
            except Unresolvable as exc:
                record["resolved"] = False
                record["error"] = str(exc).splitlines()[0]
                problems.append(
                    f"refs: {name} declares $ref '{target}' which resolves to nothing "
                    f"({record['error']})"
                )
            references.append(record)
    return {
        "cross-file-refs": len(references),
        "references": references,
        "unresolvable": [record for record in references if not record["resolved"]],
        "problems": problems,
        "ok": not problems,
    }


def required_of(schema: dict) -> list[str]:
    value = schema.get("required")
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def check_schema_shape(schema, validator_cls) -> list[str]:
    """A schema must be draft 2020-12 and must require something to be droppable."""
    problems = []
    if not isinstance(schema, dict):
        return ["schema is not a JSON object"]
    declared = schema.get("$schema")
    if declared is not None and str(declared).rstrip("#") != DRAFT_URI:
        problems.append(f"$schema is '{declared}', expected '{DRAFT_URI}'")
    try:
        validator_cls.check_schema(schema)
    except Exception as exc:  # jsonschema.SchemaError and friends
        problems.append(f"not a valid draft 2020-12 schema: {str(exc).splitlines()[0]}")
        return problems
    variants = schema.get("oneOf")
    if required_of(schema):
        return problems
    if isinstance(variants, list) and variants:
        weak = [
            index
            for index, variant in enumerate(variants)
            if not (isinstance(variant, dict) and required_of(variant))
        ]
        if weak:
            problems.append(
                f"oneOf variants {weak} declare no `required` property "
                "(every union variant must require at least one)"
            )
        return problems
    problems.append("declares no `required` property at the top level and is not a oneOf union")
    return problems


def applicable_required(schema: dict, instance, validator_cls, registry) -> list[str]:
    """Required top-level properties this instance is actually held to."""
    _, _, _, Unresolvable = load_referencing()
    names = list(required_of(schema))
    variants = schema.get("oneOf")
    if isinstance(variants, list):
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            try:
                matched = validator_cls(variant, registry=registry).is_valid(instance)
            except Unresolvable:
                continue  # the refs arm names it; do not crash mid-mutation
            if matched:
                names += required_of(variant)
    seen = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def arm_entries(
    rows: list[dict], seams_dir: Path, validator_cls, registry
) -> tuple[dict, dict, list[str]]:
    """instances + mutation arms, per entry. Returns (entries, mutation, problems)."""
    _, _, _, Unresolvable = load_referencing()
    entries: dict[str, dict] = {}
    mutation_checks: list[dict] = []
    problems: list[str] = []
    for row in rows:
        entry = row["entry-id"]
        if entry in entries:
            continue  # duplicates are the coverage arm's business
        verdict = {
            "kind": row["kind"],
            "schema-file": row["schema-file"],
            "instance-files": split_list(row["instance-files"]),
            "problems": [],
            "instances": [],
            "ok": True,
        }
        entries[entry] = verdict
        if row["kind"] == "constraint":
            verdict["skipped"] = "constraint entry — no schema, no instances"
            continue
        if not row["schema-file"]:
            verdict["problems"].append("no schema-file declared")
            verdict["ok"] = False
            continue
        schema_path = seams_dir / row["schema-file"]
        schema, error = read_json(schema_path)
        if error:
            verdict["problems"].append(f"schema-file: {error}")
            verdict["ok"] = False
            continue
        shape_problems = check_schema_shape(schema, validator_cls)
        verdict["problems"] += [f"schema-file: {problem}" for problem in shape_problems]
        if shape_problems:
            verdict["ok"] = False
            continue
        if not verdict["instance-files"]:
            verdict["problems"].append("zero instance files declared")
            verdict["ok"] = False
            continue
        validator = validator_cls(schema, registry=registry)
        for name in verdict["instance-files"]:
            instance_path = seams_dir / name
            record = {"file": name, "valid": False, "errors": []}
            verdict["instances"].append(record)
            instance, error = read_json(instance_path)
            if error:
                record["errors"].append(error)
                verdict["ok"] = False
                continue
            try:
                errors = [
                    f"{'/'.join(str(part) for part in err.absolute_path) or '<root>'}: "
                    f"{err.message}"
                    for err in validator.iter_errors(instance)
                ]
            except Unresolvable as exc:
                # A broken cross-file reference is a finding, never a traceback.
                record["errors"].append(
                    f"unresolvable $ref while validating against {row['schema-file']}: "
                    f"{str(exc).splitlines()[0]}"
                )
                verdict["ok"] = False
                continue
            record["errors"] = errors
            record["valid"] = not errors
            if errors:
                verdict["ok"] = False
                continue
            if not isinstance(instance, dict):
                record["errors"].append(
                    "instance is not a JSON object — mutation arm cannot drop a property"
                )
                verdict["ok"] = False
                continue
            for prop in applicable_required(schema, instance, validator_cls, registry):
                if prop not in instance:
                    continue
                mutant = copy.deepcopy(instance)
                del mutant[prop]
                survived = validator.is_valid(mutant)
                mutation_checks.append(
                    {
                        "entry-id": entry,
                        "schema": row["schema-file"],
                        "instance": name,
                        "property": prop,
                        "survived": survived,
                    }
                )
    for entry, verdict in entries.items():
        problems += [f"{entry}: {problem}" for problem in verdict["problems"]]
        for record in verdict["instances"]:
            problems += [f"{entry}: instance {record['file']}: {error}" for error in record["errors"]]
    return entries, mutation_checks, problems


def arm_mutation(checks: list[dict]) -> dict:
    survivors = [check for check in checks if check["survived"]]
    return {
        "checked": len(checks),
        "checks": checks,
        "survivors": survivors,
        "problems": [
            "mutation: dropping required property '{property}' from {instance} "
            "still validates against {schema} (entry {entry-id})".format(**check)
            for check in survivors
        ],
        "ok": not survivors,
    }


def arm_grep(tree_root: Path, excludes) -> dict:
    """Any probe of the attested facts is a defect. Scans every file under the tree."""
    excluded = [Path(path).resolve() for path in excludes]
    hits = []
    scanned = 0
    if not tree_root.is_dir():
        return {
            "files-scanned": 0,
            "hits": [],
            "problems": [f"grep: no such tree to scan: {tree_root}"],
            "ok": False,
        }
    for path in sorted(tree_root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if SKIP_DIRS & set(path.parts):
            continue
        resolved = path.resolve()
        if any(resolved == item or item in resolved.parents for item in excluded):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            hits.append({"file": str(path), "line": 0, "pattern": "unreadable", "text": str(exc)})
            continue
        scanned += 1
        for number, line in enumerate(text.splitlines(), start=1):
            for name, pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    hits.append(
                        {
                            "file": str(path.relative_to(tree_root)),
                            "line": number,
                            "pattern": name,
                            "text": line.strip()[:200],
                        }
                    )
    problems = [
        "grep: {file}:{line} probes an owner-attested fact [{pattern}]: {text}".format(**hit)
        for hit in hits
    ]
    if not scanned:
        # A scan of nothing is a green that cannot go red. Refuse to report it as a pass.
        problems.append(f"grep: scanned 0 files under {tree_root} — nothing was checked")
    return {
        "files-scanned": scanned,
        "hits": hits,
        "problems": problems,
        "ok": not problems,
    }


def arm_constraint(rows: list[dict], seams_dir: Path) -> dict:
    row = next((row for row in rows if row["entry-id"] == CONSTRAINT_ID), None)
    if row is None:
        return {
            "entry-id": CONSTRAINT_ID,
            "problems": [],
            "skipped": "entry absent from the index — the coverage arm reports it",
            "ok": None,
        }
    problems = []
    if row["kind"] != "constraint":
        problems.append(f"constraint: kind is '{row['kind']}', expected 'constraint'")
    if row["schema-file"]:
        problems.append(f"constraint: schema-file must be empty, found '{row['schema-file']}'")
    if row["instance-files"]:
        problems.append(
            f"constraint: instance-files must be empty, found '{row['instance-files']}'"
        )
    doc = seams_dir / CONSTRAINT_DOC
    if not doc.is_file():
        problems.append(f"constraint: {CONSTRAINT_DOC} does not exist at {doc}")
    return {
        "entry-id": CONSTRAINT_ID,
        "doc": str(doc),
        "problems": problems,
        "ok": not problems,
    }


# --------------------------------------------------------------------- verdict
def validate(seams_dir: Path, tree_root: Path, excludes) -> dict:
    """Run all five arms in one pass. Pure function of the files on disk."""
    validator_cls = load_validator()
    result = {
        "tool": "validate-seams",
        "seams-dir": str(seams_dir),
        "tree-root": str(tree_root),
        "coverage": None,
        "refs": None,
        "entries": {},
        "mutation": None,
        "grep": None,
        "constraint": None,
        "arms": {arm: None for arm in ARMS},
        "problems": [],
        "ok": False,
    }
    rows, fatal = read_index(seams_dir)
    if fatal:
        result["error"] = fatal
        result["problems"] = [f"index: {fatal}"]
        return result

    registry, registry_keys = build_registry(seams_dir)
    result["registry-keys"] = registry_keys

    coverage = arm_coverage(rows)
    refs = arm_refs(rows, seams_dir, registry)
    entries, mutation_checks, entry_problems = arm_entries(rows, seams_dir, validator_cls, registry)
    mutation = arm_mutation(mutation_checks)
    grep = arm_grep(tree_root, excludes)
    constraint = arm_constraint(rows, seams_dir)

    result["coverage"] = coverage
    result["refs"] = refs
    result["entries"] = entries
    result["mutation"] = mutation
    result["grep"] = grep
    result["constraint"] = constraint
    result["arms"] = {
        "coverage": coverage["ok"],
        "refs": refs["ok"],
        "instances": not entry_problems,
        "mutation": mutation["ok"],
        "grep": grep["ok"],
        "constraint": constraint["ok"],
    }
    result["problems"] = (
        coverage["problems"]
        + refs["problems"]
        + [f"instances: {problem}" for problem in entry_problems]
        + mutation["problems"]
        + grep["problems"]
        + constraint["problems"]
    )
    result["ok"] = all(value is not False for value in result["arms"].values())
    return result


def print_report(result: dict) -> None:
    print(f"seams-dir: {result['seams-dir']}")
    if result.get("error"):
        print(f"error: {result['error']}")
    coverage = result.get("coverage")
    if coverage:
        print(f"coverage:  crossings {coverage['crossings']}  stores {coverage['stores']}")
    refs = result.get("refs")
    if refs:
        print(
            f"refs:      {refs['cross-file-refs']} cross-file $ref, "
            f"{len(refs['unresolvable'])} unresolvable"
        )
    mutation = result.get("mutation")
    if mutation:
        print(f"mutation:  {mutation['checked']} checks, {len(mutation['survivors'])} survivors")
    grep = result.get("grep")
    if grep:
        print(f"grep:      {grep['files-scanned']} files scanned, {len(grep['hits'])} hits")
    for arm, verdict in result["arms"].items():
        mark = {True: "PASS", False: "FAIL", None: "skip"}[verdict]
        print(f"  {arm:<11} {mark}")
    for problem in result["problems"]:
        print(f"  - {problem}")
    print("ok" if result["ok"] else "NOT ok")


# ------------------------------------------------------------------------ main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_seams.py",
        description=(
            "Machine-verify the transcript-summarizer seam set: 19 entries "
            "(15 crossings + 4 stores), their schemas, their reference instances, "
            "and the attestation boundary. Deterministic — no network, no model call."
        ),
        epilog=(
            "arms run by `validate`, all in one pass:\n"
            "  coverage    index.csv entry-ids are EXACTLY the 19 hardcoded here\n"
            "  refs        every cross-file $ref a schema declares resolves against the\n"
            "              registry preloaded from <seams-dir>/**/*.schema.json (keyed by\n"
            "              bare filename AND path relative to the seams dir); an\n"
            "              unresolvable reference is a named finding, never a traceback\n"
            "  instances   each non-constraint schema is draft 2020-12, requires\n"
            "              something, every declared instance validates, none has zero\n"
            "  mutation    dropping any required property from an instance MUST break\n"
            "              validation; a surviving mutant is a failure\n"
            "  grep        no file under the workflow tree probes the two facts settled\n"
            "              by owner attestation (goal.md clause 17)\n"
            "  constraint  attestation-boundary carries no schema/instance and\n"
            "              seams/attestation-boundary.md exists\n"
            "\n"
            "flags: --json (before or after the operation) · validate --seams DIR\n"
            "       (default ../seams beside this tool; its parent is the grep tree)\n"
            "\n"
            "index.csv columns: entry-id,kind,schema-file,instance-files · kind is\n"
            "  crossing|store|constraint · schema-file is relative to the seams dir and\n"
            "  empty for the constraint entry · instance-files takes one or more paths,\n"
            "  separated by ';' '|' whitespace, or commas inside a quoted CSV field\n"
            "\n"
            "exit codes: 0 verdict ok · 1 seam set not valid · 2 could not run\n"
            "\n"
            "examples:\n"
            "  validate_seams.py --json\n"
            "  validate_seams.py validate --seams ../seams\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit one JSON object on stdout (the surface a workflow edge reads)",
    )
    subparsers = parser.add_subparsers(dest="operation")
    validate_parser = subparsers.add_parser(
        "validate",
        help="check a seam set (default operation)",
        description="Run all five arms against a seams directory.",
    )
    validate_parser.add_argument(
        "--seams",
        metavar="DIR",
        default=None,
        help="seams directory to check (default: ../seams next to this tool). "
        "Its parent is the tree the grep arm scans.",
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str]) -> int:
    global _JSON_MODE
    parser = build_parser()
    known = {"validate"}
    asks_help = {"-h", "--help"} & set(argv)
    if not any(argument in known for argument in argv) and not asks_help:
        argv = ["validate"] + argv  # validate is the default operation
    args = parser.parse_args(argv)
    _JSON_MODE = args.json

    seams_dir = Path(args.seams).resolve() if args.seams else (TOOL_DIR.parent / "seams").resolve()
    if not seams_dir.is_dir():
        refuse(
            what=f"no seams directory at {seams_dir}",
            why="the coverage arm reads <seams-dir>/index.csv and there is no such directory",
            fix="author the seam set there, or point the tool at it: --seams DIR",
            escape="none — without a seam set there is nothing to check",
        )
    result = validate(seams_dir, seams_dir.parent, {TOOL_FILE})
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_report(result)
    if result.get("error"):
        return EXIT_REFUSED
    return EXIT_OK if result["ok"] else EXIT_VERDICT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
