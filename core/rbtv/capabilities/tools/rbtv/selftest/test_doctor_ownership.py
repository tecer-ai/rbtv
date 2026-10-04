"""Read-only doctor coverage for a selected installation's shared shortcuts."""
from __future__ import annotations

import json
import os
from pathlib import Path

from lib.constants import STATE_REL, _RUNTIME
from lib.doctor import do_doctor
from lib.operations import do_install, do_uninstall
from lib.pathlinks import bin_dir, link_one, link_path, unlink_one
from lib.shared_links import owner_file


def _snapshot(*roots: Path) -> tuple:
    entries = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            rel = f"{root}::{path.relative_to(root).as_posix()}"
            if path.is_symlink():
                entries.append((rel, "link", str(path.readlink())))
            elif path.is_file():
                entries.append((rel, "file", path.read_bytes()))
            else:
                entries.append((rel, "dir", ""))
    return tuple(entries)


def _checks(target: Path, catalog: dict, tree: Path, *,
           cleanup_audit: bool = False) -> dict[str, dict]:
    return {row["name"]: row for row in do_doctor(
        target, "fixture", catalog, [], tree, target / ".rbtv" / "mirror",
        cleanup_audit=cleanup_audit)["checks"]}


def _capture_shortcut(bindir: Path, name: str) -> dict:
    """The ACTUAL shortcut this platform created at `name`: a POSIX symlink
    to its target, or a Windows shim (a regular `.cmd` file plus its bash
    twin). Restoring must recreate the same KIND — writing a symlink's
    (dereferenced) bytes back as a plain file silently turns a real symlink
    into a foreign regular file, which the next `link_one` then refuses as
    a collision."""
    shim = link_path(bindir, name)
    if os.name != "nt":
        return {"kind": "posix", "target": shim.readlink()}
    twin = shim.with_suffix("")
    return {"kind": "win", "shim_bytes": shim.read_bytes(),
            "twin_bytes": twin.read_bytes() if twin.is_file() else None}


def _restore_shortcut(bindir: Path, name: str, saved: dict) -> None:
    shim = link_path(bindir, name)
    if shim.exists() or shim.is_symlink():
        shim.unlink()
    if saved["kind"] == "posix":
        shim.symlink_to(saved["target"])
        return
    shim.write_bytes(saved["shim_bytes"])
    twin = shim.with_suffix("")
    if twin.exists() or twin.is_symlink():
        twin.unlink()
    if saved["twin_bytes"] is not None:
        twin.write_bytes(saved["twin_bytes"])


def doctor_ownership(ctx) -> None:
    """The selected installation's shared shortcuts diagnose safely, name the
    exact failure, and never mix in another installation's inventory unasked."""
    check, skip, tmp, tree = ctx.check, ctx.skip, ctx.tmp, ctx.tree
    catalog = ctx.frame()[0]

    # ---- machine-local ownership-record hygiene (no real selection yet) ----
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
        bad_target = tmp / "doctor-bad-book"
        (bad_target / STATE_REL).parent.mkdir(parents=True)
        (bad_target / STATE_REL).write_text("{broken", encoding="utf-8")
        bad_book = _checks(bad_target, {}, tree)
        check("DO-corrupt-book — doctor reports structured state refusal",
              bad_book["Saved selection"]["level"] == "fail"
              and "cannot read rbtv state" in bad_book["Saved selection"]["detail"],
              bad_book["Saved selection"]["detail"])

        (bad_target / STATE_REL).write_text(
            json.dumps({"components": []}), encoding="utf-8")
        malformed_book = _checks(bad_target, {}, tree)
        check("DO-structural-book — valid JSON with invalid records is refused",
              malformed_book["Saved selection"]["level"] == "fail"
              and "invalid structure" in malformed_book["Saved selection"]["detail"],
              malformed_book["Saved selection"]["detail"])

        owner_file(bindir).write_text("{broken", encoding="utf-8")
        bad_registry = _checks(target, {}, tree)
        check("DO-empty-target-no-registry-noise — a target with no selected "
              "PATH parts never even reads the (corrupt) shared registry",
              "Shared shortcut ownership" not in bad_registry
              and all(row["level"] != "fail" for row in bad_registry.values()),
              str({k: v["level"] for k, v in bad_registry.items()}))
    finally:
        _RUNTIME["bin"] = saved_bin

    # ---- a real selected installation, with one real PATH-exposed shortcut ----
    real_root = tmp / "doctor-real"
    ws = tmp / "doctor-ws"
    ws.mkdir()
    saved_runtime = dict(_RUNTIME)
    _RUNTIME["bin"] = real_root / "bin"
    _RUNTIME["rc"] = real_root / "rc"
    _RUNTIME["local"] = real_root / "local"
    saved_path = os.environ.get("PATH", "")
    os.environ["PATH"] = str(bin_dir()) + os.pathsep + saved_path
    try:
        do_install(ws, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False,
                  parts=["fixskill", "fixtool"])
        before = _snapshot(real_root, ws)
        healthy = _checks(ws, catalog, tree)
        check("DO-healthy — a live selected shortcut resolves clean end to end",
              healthy["Selected shortcut: fixtool"]["level"] == "ok"
              and healthy["Command lookup: fixtool"]["level"] == "ok"
              and healthy["Selected files"]["level"] == "ok"
              and healthy["Saved selection"]["level"] == "ok",
              str({k: healthy[k]["detail"] for k in
                   ("Selected shortcut: fixtool", "Command lookup: fixtool")}))
        check("DO-read-only-healthy — doctor changes no installed or shared bytes",
              _snapshot(real_root, ws) == before, "fixture changed")

        # DO-missing-selected-link — the shim itself is gone (owner record
        # still names this installation as its owner).
        saved_shortcut = _capture_shortcut(bin_dir(), "fixtool")
        shim = link_path(bin_dir(), "fixtool")
        shim.unlink()
        if os.name == "nt":
            twin = shim.with_suffix("")
            if twin.is_file():
                twin.unlink()
        missing = _checks(ws, catalog, tree)
        check("DO-missing-selected-link — a deleted shortcut is named, not "
              "silently skipped the way the old collision-or-non-exec probe "
              "left it, with a concrete preview-then-apply recovery",
              missing["Selected shortcut: fixtool"]["level"] == "fail"
              and "missing" in missing["Selected shortcut: fixtool"]["detail"].lower()
              and "update scaffolding --dry-run --target" in
              missing["Selected shortcut: fixtool"]["detail"]
              and "update scaffolding --target" in
              missing["Selected shortcut: fixtool"]["detail"]
              and str(ws) in missing["Selected shortcut: fixtool"]["detail"]
              and missing["Command lookup: fixtool"]["level"] == "fail",
              missing["Selected shortcut: fixtool"]["detail"])
        _restore_shortcut(bin_dir(), "fixtool", saved_shortcut)

        # DO-wrong-target — the shim now points at a different real tool.
        # The owner record still says the ORIGINAL target, so this only
        # catches if doctor verifies against the current catalog, not the
        # (unchanged, therefore misleading) ownership record.
        other = tmp / "doctor-other-tool.py"
        other.write_text("#!/usr/bin/env python3\nprint('other')\n",
                         encoding="utf-8")
        other.chmod(0o755)
        link_one(bin_dir(), "fixtool", other, dry=False)
        wrong = _checks(ws, catalog, tree)
        check("DO-wrong-target — a shim relinked to a different tool is "
              "caught against the CURRENT selected source, with a concrete "
              "preview-then-apply recovery",
              wrong["Selected shortcut: fixtool"]["level"] == "fail"
              and "elsewhere" in wrong["Selected shortcut: fixtool"]["detail"]
              and "update scaffolding --dry-run --target" in
              wrong["Selected shortcut: fixtool"]["detail"]
              and "update scaffolding --target" in
              wrong["Selected shortcut: fixtool"]["detail"],
              wrong["Selected shortcut: fixtool"]["detail"])
        do_install(ws, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False,
                  parts=["fixskill", "fixtool"])  # repair for the next arm

        # DO-foreign-shortcut — a regular file (never ours) sits at the
        # selected name. Doctor must send the operator to look at it, never
        # promise a silent overwrite.
        saved_shortcut = _capture_shortcut(bin_dir(), "fixtool")
        shim = link_path(bin_dir(), "fixtool")
        shim.unlink()
        if os.name == "nt":
            twin = shim.with_suffix("")
            if twin.is_file():
                twin.unlink()
        shim.write_text("not ours\n", encoding="utf-8")
        foreign = _checks(ws, catalog, tree)
        check("DO-foreign-shortcut — an unmanaged file at the selected name "
              "is named for manual inspection, never promised a silent "
              "overwrite",
              foreign["Selected shortcut: fixtool"]["level"] == "fail"
              and "not a managed shortcut" in
              foreign["Selected shortcut: fixtool"]["detail"]
              and "move or remove it yourself" in
              foreign["Selected shortcut: fixtool"]["detail"]
              and "never overwrites" in
              foreign["Selected shortcut: fixtool"]["detail"],
              foreign["Selected shortcut: fixtool"]["detail"])
        shim.unlink()
        _restore_shortcut(bin_dir(), "fixtool", saved_shortcut)

        # DO-ownership-not-this-installation — the link and the file are both
        # fine, but the shared registry does not list THIS installation as an
        # owner: a different installation's removal could delete it out from
        # under this one with no warning today, so "some entry exists" must
        # not read as healthy.
        owners_doc = json.loads(owner_file(bin_dir()).read_text(encoding="utf-8"))
        real_owners = owners_doc["links"]["fixtool"]["owners"]
        other_ws = tmp / "doctor-some-other-ws"
        owners_doc["links"]["fixtool"]["owners"] = [str(other_ws)]
        owner_file(bin_dir()).write_text(json.dumps(owners_doc), encoding="utf-8")
        unowned = _checks(ws, catalog, tree)
        check("DO-ownership-not-this-installation — an entry owned only by "
              "another installation does not prove THIS installation is tracked",
              unowned["Shared shortcut ownership"]["level"] == "fail"
              and "not this one" in unowned["Shared shortcut ownership"]["detail"]
              and "update scaffolding" in
              unowned["Shared shortcut ownership"]["detail"]
              # the shim itself is still fine — a separate concern
              and unowned["Selected shortcut: fixtool"]["level"] == "ok",
              unowned["Shared shortcut ownership"]["detail"])
        owners_doc["links"]["fixtool"]["owners"] = real_owners
        owner_file(bin_dir()).write_text(json.dumps(owners_doc), encoding="utf-8")

        # DO-posix-exec-permission — the selected CLI's CURRENT source file
        # lost its execute bit. `plan_path_links` re-validates every desired
        # row's destination on every doctor run, so this surfaces as a
        # planning failure (labelled Selected source / Local RBTV source,
        # not a shortcut or PATH problem) with a truthful chmod recovery —
        # distinct from a missing/foreign shortcut or a PATH shadow, all of
        # which leave the source itself alone. A real temp file under the
        # throwaway fixture tree is chmod'd and restored; the real repo is
        # never touched.
        if os.name == "nt":
            skip("DO-posix-exec-permission — a lost execute bit is reported "
                 "as a selected-source problem with a chmod recovery",
                 "POSIX-only: Windows has no execute bit")
        else:
            perm_ws = tmp / "doctor-posix-exec-ws"
            perm_ws.mkdir()
            do_install(perm_ws, catalog, ["fixmod/goodcomp"], ["claude"],
                      dry_run=False, parts=["fixskill", "fixtool"])
            entry = (tree / "fixmod" / "goodcomp" / "capabilities" / "tools"
                     / "fixtool" / "thing.py")
            before_mode = entry.stat().st_mode
            entry.chmod(0o644)
            try:
                broken_perm = _checks(perm_ws, catalog, tree)
            finally:
                entry.chmod(before_mode)
            check("DO-posix-exec-permission — a lost execute bit is reported "
                  "as a selected-source problem with a chmod recovery, "
                  "distinct from PATH absence or shadowing",
                  "Selected source" in broken_perm
                  and broken_perm["Selected source"]["level"] == "fail"
                  and broken_perm["Selected source"]["scope"]
                  == "Local RBTV source"
                  and "execute permission" in
                  broken_perm["Selected source"]["detail"]
                  and "chmod +x" in broken_perm["Selected source"]["detail"]
                  and "Selected shortcut: fixtool" not in broken_perm
                  and "Command lookup: fixtool" not in broken_perm,
                  broken_perm.get("Selected source", {}).get(
                      "detail", "(missing)"))
            do_uninstall(perm_ws, catalog, ["fixmod/goodcomp"], dry_run=False)

        # DO-path-shadow — an earlier PATH entry answers first.
        shadow_dir = tmp / "doctor-shadow"
        shadow_dir.mkdir()
        shadow_name = "fixtool.cmd" if os.name == "nt" else "fixtool"
        shadow = shadow_dir / shadow_name
        if os.name == "nt":
            shadow.write_text("@echo shadow\r\n", encoding="utf-8")
        else:
            shadow.write_text("#!/bin/sh\necho shadow\n", encoding="utf-8")
            shadow.chmod(0o755)
        os.environ["PATH"] = str(shadow_dir) + os.pathsep + os.environ["PATH"]
        try:
            shadowed = _checks(ws, catalog, tree)
        finally:
            os.environ["PATH"] = str(bin_dir()) + os.pathsep + saved_path
        check("DO-path-shadow — any earlier PATH executable is named (not "
              "only one sitting in ~/.local/bin), naming both the winner "
              "and the intended directory without promising a repair "
              "command for the foreign entry",
              shadowed["Selected shortcut: fixtool"]["level"] == "ok"
              and shadowed["Command lookup: fixtool"]["level"] == "fail"
              and str(shadow_dir).lower() in
              shadowed["Command lookup: fixtool"]["detail"].lower()
              and str(bin_dir()) in shadowed["Command lookup: fixtool"]["detail"]
              and "new terminal" in shadowed["Command lookup: fixtool"]["detail"]
              and "update scaffolding" not in
              shadowed["Command lookup: fixtool"]["detail"],
              shadowed["Command lookup: fixtool"]["detail"])

        # DO-empty-target-noise-suppression — a skill-only selection exposes
        # no PATH name; unrelated bindir clutter must not fail it.
        skill_ws = tmp / "doctor-skill-only-ws"
        skill_ws.mkdir()
        (bin_dir() / "unrelated-clutter").write_text("x\n", encoding="utf-8")
        do_install(skill_ws, catalog, ["fixmod/goodcomp"], ["claude"],
                  dry_run=False, parts=["fixskill"])
        skill_only = do_doctor(skill_ws, "fixture", catalog, [], tree,
                               skill_ws / ".rbtv" / "mirror")
        skill_names = {c["name"] for c in skill_only["checks"]}
        check("DO-empty-target-noise-suppression — a skill-only selection "
              "carries no shared-command checks and is not failed by "
              "unrelated bindir clutter",
              skill_only["ok"]
              and not any(name.startswith(("Selected shortcut", "Command lookup",
                                           "Shared shortcut ownership"))
                         for name in skill_names),
              str(sorted(skill_names)))

        # DO-cleanup-audit — off by default; opt-in names a safe two-step
        # recovery (preview, then release) for an absent installation, as a
        # warning that never fails a healthy target.
        missing_owner = tmp / "doctor-missing-owner-ws"
        elsewhere_tool = tmp / "doctor-elsewhere-tool.py"
        elsewhere_tool.write_text("#!/usr/bin/env python3\nprint(1)\n",
                                  encoding="utf-8")
        elsewhere_tool.chmod(0o755)
        link_one(bin_dir(), "managed-elsewhere", elsewhere_tool, dry=False)
        owners_doc = json.loads(owner_file(bin_dir()).read_text(encoding="utf-8"))
        owners_doc["links"]["managed-elsewhere"] = {
            "target": str(elsewhere_tool), "owners": [str(missing_owner)]}
        owner_file(bin_dir()).write_text(json.dumps(owners_doc), encoding="utf-8")

        default_run = do_doctor(ws, "fixture", catalog, [], tree,
                                ws / ".rbtv" / "mirror")
        check("DO-cleanup-audit-off-by-default — no unrelated-installation rows "
              "without --cleanup-audit",
              not any(c["scope"] == "Other installation"
                     for c in default_run["checks"])
              and default_run["ok"],
              str([c["name"] for c in default_run["checks"]]))

        audited = do_doctor(ws, "fixture", catalog, [], tree,
                            ws / ".rbtv" / "mirror", cleanup_audit=True)
        stale_rows = [c for c in audited["checks"]
                     if c["name"] == "Stale owner claim"
                     and str(missing_owner) in c["detail"]]
        check("DO-cleanup-audit — names a safe dry-run then a release "
              "command for the absent installation, as a warning only",
              len(stale_rows) == 1
              and stale_rows[0]["level"] == "warn"
              and stale_rows[0]["scope"] == "Other installation"
              and "--dry-run" in stale_rows[0]["detail"]
              and "--yes" in stale_rows[0]["detail"]
              and stale_rows[0]["detail"].index("--dry-run")
              < stale_rows[0]["detail"].index("--yes")
              and audited["ok"],
              stale_rows[0]["detail"] if stale_rows else "no row")

        before_audit = _snapshot(real_root, ws)
        do_doctor(ws, "fixture", catalog, [], tree, ws / ".rbtv" / "mirror",
                 cleanup_audit=True)
        check("DO-read-only-cleanup-audit — the optional audit changes no bytes",
              _snapshot(real_root, ws) == before_audit,
              "cleanup-audit run changed bytes")

        unlink_one(bin_dir(), "managed-elsewhere", dry=False)
        owners_doc = json.loads(owner_file(bin_dir()).read_text(encoding="utf-8"))
        owners_doc["links"].pop("managed-elsewhere", None)
        owner_file(bin_dir()).write_text(json.dumps(owners_doc), encoding="utf-8")

        # DO-guidance-counterpart-missing — Maintained guidance only checks
        # the human-authored basis; a GENERATED counterpart it never looks
        # at (a codex AGENTS.md mirror of a claude CLAUDE.md basis) must
        # still be caught by Selected files, or a broken codex-side rule
        # exposure would read as healthy.
        guide_ws = tmp / "doctor-guidance-ws"
        guide_ws.mkdir()
        (guide_ws / "CLAUDE.md").write_text("# project guidance\n",
                                            encoding="utf-8")
        do_install(guide_ws, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                  dry_run=False, guidance_basis="CLAUDE.md", parts=["fixskill"])
        counterparts = json.loads(
            (guide_ws / STATE_REL).read_text(encoding="utf-8")
        ).get("guidance_files") or []
        check("DO-guidance-counterpart-recorded — the fixture actually "
              "produced a generated counterpart to test against",
              "AGENTS.md" in counterparts, str(counterparts))
        before_guide = _snapshot(guide_ws)
        healthy_guide = _checks(guide_ws, catalog, tree)
        check("DO-guidance-counterpart-healthy — present counterpart, "
              "present basis: both checks pass",
              healthy_guide["Selected files"]["level"] == "ok"
              and healthy_guide["Maintained guidance"]["level"] == "ok",
              str({k: healthy_guide[k]["level"]
                   for k in ("Selected files", "Maintained guidance")}))
        (guide_ws / "AGENTS.md").unlink()
        broken_guide = _checks(guide_ws, catalog, tree)
        check("DO-guidance-counterpart-missing — a deleted GENERATED "
              "counterpart fails Selected files even though the basis "
              "(and therefore Maintained guidance) is untouched, without "
              "doctor modifying anything",
              broken_guide["Selected files"]["level"] == "fail"
              and "AGENTS.md" in broken_guide["Selected files"]["detail"]
              and broken_guide["Maintained guidance"]["level"] == "ok"
              and _snapshot(guide_ws) == tuple(
                  e for e in before_guide if not e[0].endswith("::AGENTS.md")),
              broken_guide["Selected files"]["detail"])
        do_uninstall(guide_ws, catalog, ["fixmod/goodcomp"], dry_run=False)

        # DO-configure-first — `configure` (via `_replan_all`, which calls
        # `do_install` with an EMPTY picked list) can write generated
        # guidance copies before any component is ever added. Selected
        # files must not skip past that with "nothing to check" just
        # because `state["components"]` is empty.
        configure_ws = tmp / "doctor-configure-first-ws"
        configure_ws.mkdir()
        (configure_ws / "CLAUDE.md").write_text("# project guidance\n",
                                                 encoding="utf-8")
        do_install(configure_ws, catalog, [], ["claude", "codex"],
                  dry_run=False, guidance_basis="CLAUDE.md")
        configure_state = json.loads(
            (configure_ws / STATE_REL).read_text(encoding="utf-8"))
        check("DO-configure-first-recorded — configure-before-first-add "
              "really produces a generated counterpart with zero booked "
              "components",
              not (configure_state.get("components") or {})
              and "AGENTS.md" in (configure_state.get("guidance_files") or []),
              str(configure_state.get("guidance_files")))
        before_cfg = _snapshot(configure_ws)
        healthy_cfg = _checks(configure_ws, catalog, tree)
        check("DO-configure-first-healthy — Selected files checks generated "
              "copies even with an empty component set",
              healthy_cfg["Selected files"]["level"] == "ok",
              healthy_cfg["Selected files"]["detail"])
        (configure_ws / "AGENTS.md").unlink()
        broken_cfg = _checks(configure_ws, catalog, tree)
        check("DO-configure-first-missing-counterpart — a deleted generated "
              "copy fails Selected files even with zero booked components, "
              "without doctor modifying anything",
              broken_cfg["Selected files"]["level"] == "fail"
              and "AGENTS.md" in broken_cfg["Selected files"]["detail"]
              and _snapshot(configure_ws) == tuple(
                  e for e in before_cfg if not e[0].endswith("::AGENTS.md")),
              broken_cfg["Selected files"]["detail"])

        # DO-truthful-count-labels — a component count is labelled
        # "components", not the item-classification word "units" (D8's
        # module/component/item vocabulary is not interchangeable).
        labelled = _checks(ws, catalog, tree)
        check("DO-truthful-count-labels — Saved selection and Source "
              "catalog label what they actually counted",
              "component" in labelled["Saved selection"]["detail"]
              and "item" not in labelled["Saved selection"]["detail"]
              and "component" in labelled["Source catalog"]["detail"]
              and "item" not in labelled["Source catalog"]["detail"],
              str({k: labelled[k]["detail"]
                   for k in ("Saved selection", "Source catalog")}))

        do_uninstall(skill_ws, catalog, ["fixmod/goodcomp"], dry_run=False)
        do_uninstall(ws, catalog, ["fixmod/goodcomp"], dry_run=False)
    finally:
        os.environ["PATH"] = saved_path
        _RUNTIME["bin"] = saved_runtime["bin"]
        _RUNTIME["rc"] = saved_runtime["rc"]
        _RUNTIME["local"] = saved_runtime["local"]
