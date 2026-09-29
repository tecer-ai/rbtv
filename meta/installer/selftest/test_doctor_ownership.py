"""Read-only doctor coverage for machine-local shortcut ownership."""
from __future__ import annotations

import json
from pathlib import Path

from lib.constants import STATE_REL, _RUNTIME
from lib.doctor import do_doctor
from lib.pathlinks import link_one, link_path
from lib.shared_links import owner_file


def _snapshot(root: Path) -> tuple:
    entries = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append((rel, "link", str(path.readlink())))
        elif path.is_file():
            entries.append((rel, "file", path.read_bytes()))
        else:
            entries.append((rel, "dir", ""))
    return tuple(entries)


def doctor_ownership(ctx) -> None:
    """Ownership records diagnose safely and recognize the managed shim."""
    check, tmp, tree = ctx.check, ctx.tmp, ctx.tree
    bindir = tmp / "doctor-owners" / "bin"
    owner_ws = tmp / "doctor-owner"
    owner_ws.mkdir()
    target = tmp / "doctor-target"
    target.mkdir()
    executable = tmp / "doctor-tool.py"
    executable.write_text("#!/usr/bin/env python3\nprint('doctor')\n",
                          encoding="utf-8")
    executable.chmod(0o755)
    link_one(bindir, "managed", executable, dry=False)
    owner_file(bindir).write_text(json.dumps({
        "schema": 1,
        "links": {"managed": {"target": str(executable),
                                "owners": [str(owner_ws)]}},
    }), encoding="utf-8")

    saved_bin = _RUNTIME["bin"]
    _RUNTIME["bin"] = bindir
    try:
        before = _snapshot(tmp)
        checks = {row["name"]: row for row in do_doctor(
            target, "fixture", {}, [], tree, target / ".rbtv" / "mirror"
        )["checks"]}
        check("DO-owner-shim — registered Windows shim is not a file collision",
              checks["path-ownership"]["level"] == "ok"
              and checks["path-unbooked"]["level"] == "ok"
              and checks["path-collision"]["level"] == "ok"
              and link_path(bindir, "managed").exists(),
              str({key: checks[key]["detail"] for key in (
                  "path-ownership", "path-unbooked", "path-collision")}))
        check("DO-read-only — doctor changes no ownership or workspace files",
              _snapshot(tmp) == before, "ownership fixture changed")

        missing = tmp / "missing workspace"
        owner_file(bindir).write_text(json.dumps({
            "schema": 1,
            "links": {"managed": {"target": str(executable),
                                    "owners": [str(missing)]}},
        }), encoding="utf-8")
        orphan = {row["name"]: row for row in do_doctor(
            target, "fixture", {}, [], tree, target / ".rbtv" / "mirror"
        )["checks"]}["path-ownership"]
        cleanup = "rbtv install remove --all --yes --target "
        check("DO-orphan-cleanup — missing owner gives explicit safe cleanup",
              orphan["level"] == "warn" and cleanup in orphan["detail"]
              and str(missing) in orphan["detail"], orphan["detail"])

        bad_target = tmp / "doctor-bad-book"
        (bad_target / STATE_REL).parent.mkdir(parents=True)
        (bad_target / STATE_REL).write_text("{broken", encoding="utf-8")
        bad_book = {row["name"]: row for row in do_doctor(
            bad_target, "fixture", {}, [], tree,
            bad_target / ".rbtv" / "mirror"
        )["checks"]}
        check("DO-corrupt-book — doctor reports structured state refusal",
              bad_book["book"]["level"] == "fail"
              and "cannot read installer state" in bad_book["book"]["detail"],
              bad_book["book"]["detail"])

        (bad_target / STATE_REL).write_text(
            json.dumps({"components": []}), encoding="utf-8")
        malformed_book = {row["name"]: row for row in do_doctor(
            bad_target, "fixture", {}, [], tree,
            bad_target / ".rbtv" / "mirror"
        )["checks"]}
        check("DO-structural-book — valid JSON with invalid records is refused",
              malformed_book["book"]["level"] == "fail"
              and "invalid structure" in malformed_book["book"]["detail"],
              malformed_book["book"]["detail"])

        owner_file(bindir).write_text("{broken", encoding="utf-8")
        bad_registry = {row["name"]: row for row in do_doctor(
            target, "fixture", {}, [], tree, target / ".rbtv" / "mirror"
        )["checks"]}
        check("DO-corrupt-registry — doctor reports the ownership record",
              bad_registry["path-ownership"]["level"] == "fail"
              and "shared PATH ownership record" in
              bad_registry["path-ownership"]["detail"],
              bad_registry["path-ownership"]["detail"])
    finally:
        _RUNTIME["bin"] = saved_bin
