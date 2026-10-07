"""What `doctor`, `status` and `update` say about a record that needs the
operator's eye: a key under both of its names, a runtime dependency, a
guidance exclusion whose folder is gone, and a selected file whose name moved
to another component."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path

from discovery import scan_all

from lib.commands import _HANDLERS
from lib.constants import STATE_REL
from lib.doctor import do_doctor, doctor_exit
from lib.parser import build_parser

from .fixture import _component, _file_md, _w
from .test_doctor_ownership import _snapshot


def _run(target: Path, catalog: dict, *argv: str) -> tuple[int, str]:
    """The exit code and the printed text, on one line, of one rbtv command."""
    args = build_parser().parse_args(list(argv))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = _HANDLERS[args.verb](args, target, catalog, [])
    return code, " ".join(out.getvalue().split())


def _record(target: Path) -> dict:
    return json.loads((target / STATE_REL).read_text(encoding="utf-8"))


def _doctor(target: Path, catalog: dict, tree: Path) -> dict:
    return do_doctor(target, "fixture", catalog, [], tree, target / ".rbtv" / "mirror")


def _warned(data: dict, name: str) -> str:
    """The detail of the WARN check called `name`, or "" when there is none."""
    return next((c["detail"] for c in data["checks"]
                 if c["name"] == name and c["level"] == "warn"), "")


def rulings_ops(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    print("\nRO — doctor, status and update name what the record alone hides")
    source, mirror = tmp / "rulings-source", tmp / "rulings-mirror"
    first = _component(source, "modr", "first")
    second = _component(source, "modr", "second")
    _file_md(first / "rules/stays.md", "stays", "Stays", "body\n")
    _file_md(first / "rules/moves.md", "moves", "Moves", "body\n")
    _file_md(first / "rules/ends.md", "ends", "Ends", "body\n")
    _file_md(second / "rules/other.md", "other", "Other", "body\n")
    bindir = tmp / "rulings-bin"
    command = bindir / ("rbtv-dep-here.cmd" if os.name == "nt" else "rbtv-dep-here")
    _w(command, "@echo off\n" if os.name == "nt" else "#!/bin/sh\n")
    command.chmod(0o755)
    _w(first / "first.json", json.dumps({
        "description": "The first component",
        "dependencies": ["rbtv-dep-here", "rbtv-dep-nowhere"]}))
    catalog, _ = scan_all(mirror, source)

    root = tmp / "ws-rulings"
    root.mkdir()
    _run(root, catalog, "add", "modr/first#stays", "modr/first#moves",
         "modr/first#ends", "--harness", "claude", "--guidance", "none")
    book = root / STATE_REL

    # ---- R4: runtime dependencies, looked up and never run ----
    saved_path = os.environ.get("PATH", "")
    os.environ["PATH"] = str(bindir) + os.pathsep + saved_path
    try:
        before = _snapshot(root)
        data = _doctor(root, catalog, source)
        code, text = _run(root, catalog, "doctor")
    finally:
        os.environ["PATH"] = saved_path
    check("RO-deps — doctor reports each dependency an installed component "
          "names as present or absent",
          data["dependencies"] == [
              {"name": "rbtv-dep-here", "state": "present", "components": ["modr/first"]},
              {"name": "rbtv-dep-nowhere", "state": "absent", "components": ["modr/first"]}],
          str(data["dependencies"]))
    check("RO-deps-exit — an absent dependency leaves doctor's exit code 0 "
          "and the installation unwritten",
          doctor_exit(data["checks"]) == 0 and code == 0 and _snapshot(root) == before)
    check("RO-deps-text — doctor prints the dependency rows and no longer "
          "says dependencies were not tested",
          "rbtv-dep-here present modr/first" in text
          and "rbtv-dep-nowhere absent modr/first" in text
          and "Runtime dependencies and arbitrary" not in text, text)

    # ---- R2: a component entry with both `units` and `selected` ----
    check("RO-keys-clean — doctor has no key warning for a record with one name per key",
          not _warned(_doctor(root, catalog, source), "Record keys"))
    record = _record(root)
    record["components"]["modr/first"]["units"] = {}
    _w(book, json.dumps(record, indent=2, sort_keys=True) + "\n")
    data = _doctor(root, catalog, source)
    check("RO-keys-doctor — doctor names the component that carries both "
          "`units` and `selected`, as a warning",
          "`selected` and `units` under modr/first" in _warned(data, "Record keys")
          and doctor_exit(data["checks"]) == 0, _warned(data, "Record keys"))
    code, text = _run(root, catalog, "update", "scaffolding", "--dry-run")
    check("RO-keys-preview — an update preview says it would rewrite the "
          "record and leaves both names on disk",
          code == 0 and "Would rewrite the saved record" in text
          and "under modr/first" in text
          and "units" in _record(root)["components"]["modr/first"], text)
    code, text = _run(root, catalog, "update", "scaffolding")
    check("RO-keys-update — update rewrites the record with `selected` only "
          "and says so in one line",
          code == 0 and "Rewrote the saved record" in text
          and "under modr/first" in text
          and "units" not in _record(root)["components"]["modr/first"]
          and sorted(_record(root)["components"]["modr/first"]["selected"])
          == ["ends", "moves", "stays"], text)
    code, text = _run(root, catalog, "update", "scaffolding")
    check("RO-keys-once — the next update says nothing about the record's keys",
          code == 0 and "the saved record" not in text, text)

    # ---- R5: a guidance exclusion whose folder is gone ----
    (root / "vendor").mkdir()
    (root / "kept").mkdir()
    _run(root, catalog, "add", "guidance", "exclude", "vendor", "kept")
    code, text = _run(root, catalog, "status")
    check("RO-exclude-present — status marks no exclusion while its folder exists",
          code == 0 and "excluded from copying: kept, vendor" in text
          and "no longer exists" not in text, text)
    (root / "vendor").rename(root / "vendor-moved")
    code, text = _run(root, catalog, "status")
    code_json, as_json = _run(root, catalog, "status", "--json")
    check("RO-exclude-status — status marks the exclusion whose folder is gone "
          "and names the command that drops it",
          code == 0 and "kept, vendor (no longer exists)" in text
          and "rbtv update all --target" in text and code_json == 0
          and json.loads(as_json)["installation"]["guidance_excludes_missing"]
          == ["vendor"], text)
    data = _doctor(root, catalog, source)
    check("RO-exclude-doctor — doctor names it as a warning, exit code 0",
          "no longer in this installation: vendor." in _warned(data, "Guidance exclusions")
          and doctor_exit(data["checks"]) == 0, _warned(data, "Guidance exclusions"))
    code, text = _run(root, catalog, "update", "guidance", "--dry-run")
    check("RO-exclude-preview — an update preview says it would drop it and "
          "leaves the record as it is",
          code == 0 and "Would drop the guidance exclusion vendor" in text
          and _record(root)["guidance_excludes"] == ["kept", "vendor"], text)
    code, text = _run(root, catalog, "update", "guidance")
    check("RO-exclude-update — update drops it with one line and keeps the "
          "exclusion whose folder exists",
          code == 0 and "Dropped the guidance exclusion vendor" in text
          and _record(root)["guidance_excludes"] == ["kept"], text)
    code, text = _run(root, catalog, "update", "all")
    check("RO-exclude-once — the next update drops nothing and says nothing of it",
          code == 0 and "guidance exclusion" not in text
          and _record(root)["guidance_excludes"] == ["kept"], text)

    # ---- R7: a selected file whose name moved to another component ----
    (second / "rules").mkdir(exist_ok=True)
    (first / "rules/moves.md").rename(second / "rules/moves.md")
    (first / "rules/ends.md").unlink()
    moved, _ = scan_all(mirror, source)
    code, text = _run(root, moved, "update", "all", "--dry-run")
    check("RO-moved-preview — an update preview names the new id of the moved "
          "file and the exact command that selects it",
          code == 0 and "modr/first#moves would be removed" in text
          and "the same name exists as modr/second#moves" in text
          and "rbtv add modr/second#moves --target" in text, text)
    code, text = _run(root, moved, "update", "all")
    check("RO-moved-update — update removes the vanished id, names the new one "
          "and selects nothing in its place",
          code == 0 and "modr/first#moves was removed" in text
          and "rbtv add modr/second#moves --target" in text
          and _record(root)["files"] == ["modr/first#stays"]
          and "modr/second" not in _record(root)["components"], text)
    check("RO-moved-none — a vanished file with no same-named file elsewhere "
          "gets today's line only",
          "modr/first#ends" in text and "modr/first#ends was removed" not in text, text)
