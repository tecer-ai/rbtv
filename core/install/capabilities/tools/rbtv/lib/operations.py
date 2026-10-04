"""Performing one install or one uninstall over a chosen set."""
from __future__ import annotations

import copy
from contextlib import nullcontext
from pathlib import Path

from discovery import Refuse

from .constants import (
    EXCLUDE_REL,
    GUIDANCE_NAMES,
    HARNESSES,
    LEGACY_MARKS,
    MANAGED_MARK,
    MATRIX,
    STATE_REL,
)
from .catalog import _unit_specs, catalog_units_map
from .claims import _block_set, _claim_id, owned_fence_claims
from .guidance import plan_mirror, resolve_basis
from .pathlinks import (
    _path_rows_from_report,
    _write_shell_path,
    bin_dir,
    booked_path_names,
    plan_path_links,
)
from .shared_links import (
    preflight_shared_links,
    reconcile_shared,
    shared_mutation_lock,
    installation_mutation_lock,
)
from .state import (
    _rebuild_claim,
    installed_harnesses,
    known_files,
    read_state,
    upgrade_book,
    write_state,
    is_agent_target,
    state_path,
)
from .planning import plan_files
from .recovery import shell_quote, vanished_component_message
from .apply import _clean_bases, _prune, apply


def _rebook(state: dict, records: dict, files: dict, owners: dict,
            claims: list[dict], report: dict,
            path_owners: dict[str, tuple[str, str]] | None = None,
            keep_cids: set[str] | None = None) -> None:
    keep_cids = set(keep_cids or ())
    for cid, rec in records.items():
        parts = rec.setdefault("units", {})
        rec_names: list[str] = []
        for pid, part in parts.items():
            part["files"] = sorted(
                rel for rel, own in owners.items() if (cid, pid) in own)
            owned = sorted(
                _claim_id(c["path"], c["key"], c.get("label"))
                for c in claims if c.get("owner") == (cid, pid))
            if owned:
                part["claims"] = owned
            else:
                part.pop("claims", None)
            if path_owners is not None and cid not in keep_cids:
                ln = sorted(n for n, own in path_owners.items()
                            if own == (cid, pid))
                if ln:
                    part["links"] = ln
                    rec_names.extend(ln)
                else:
                    part.pop("links", None)
            elif part.get("links"):
                rec_names.extend(part["links"])
            if not part.get("links"):
                part.pop("links", None)
        if path_owners is not None and cid not in keep_cids:
            if rec_names:
                rec["path_links"] = sorted(set(rec_names))
            else:
                rec.pop("path_links", None)
        rec.pop("files", None)
    state["components"] = records
    state["guidance_files"] = sorted(
        rel for rel, own in owners.items() if own == ["<aggregate>"])
    state["shared_claims"] = sorted(
        _claim_id(c["path"], c["key"], c.get("label")) for c in claims)
    state["shared_files"] = report["shared_files"]
    state.pop("prefix", None)


def _add_mirror(target: Path, state: dict, files: dict, owners: dict,
                report: dict, override: str | None, harnesses,
                exclude_override: list[str] | None = None,
                preserve_destination_block: bool = False) -> frozenset[str]:
    """Fold the D13 mirror into the planned set — booked as an aggregate file,
    so collision-gating, idempotence and uninstall come from the same machinery
    every other installer-owned file uses.

    Returns the paths `apply` must never delete: EVERY directory's CURRENT basis
    (D13 is recursive). The book can hold those same names from an earlier run
    when they were the generated mirrors (the flip: yesterday's mirror is
    today's hand-authored basis), and deleting one as stale would destroy
    user-authored guidance. The book itself is corrected by `_rebook`, which
    recomputes `guidance_files` from the new plan.
    """
    basis = resolve_basis(state.get("guidance_basis"), override)
    excludes = (list(exclude_override) if exclude_override is not None
                else list(state.get("guidance_excludes") or []))
    mirrors, bases, stripped, targets, debanner = plan_mirror(
        target, basis, harnesses, excludes,
        preserve_destination_block=preserve_destination_block)
    # Carried privately: these are writes OUTSIDE the booked-file machinery
    # (booking a basis would put it on a later uninstall's delete set).
    report["_debanner"] = debanner
    for rel, content in mirrors.items():
        files[rel] = content
        owners[rel] = ["<aggregate>"]
    report["guidance_mirror"] = (
        {"basis": basis, "targets": targets,
         "count": len(mirrors), "excludes": excludes,
         "banner_stripped": stripped} if basis
        else {"basis": None, "targets": []})
    return bases


def _section_paths(claims: list[dict]) -> list[str]:
    """The instruction files that carry a managed section in this plan."""
    return sorted({c["path"] for c in claims
                   if c["fmt"] == "text" and c["comment"] == "<!--"})


GITIGNORE_NOTE = (
    "install.py artifacts — MACHINE-LOCAL, never committed: the "
    "loaders bake\nabsolute entry-point paths and the book records an absolute "
    "target, so a committed copy\nis wrong on every other machine "
    "(d-s15-installer2-artifacts-machine-local). Generated from\nthe book and "
    "the marked files on disk on every install and uninstall — edit nothing\n"
    "between the fences; re-run the installer instead. This file is per clone "
    "(D14),\nso each machine keeps its own list.")


def _add_gitignore(target: Path, owners: dict[str, list], claims: list[dict],
                   report: dict, booked: set[str]) -> None:
    """Claim the `.git/info/exclude` block that keeps our artifacts out of git
    (D14) — the per-clone ignore file, so machines sharing a repo never
    overwrite each other's lists.

    Listed: every per-component file (the `<aggregate>` owner is the guidance
    mirror, which is installation content and stays committable), the book, and
    every STRAY artifact on disk (`_stray_artifacts`). Skipped entirely off a
    git repo, and when `.git` is a FILE (a linked worktree or submodule keeps
    its exclude elsewhere). Files git ALREADY TRACKS are reported, because no
    ignore rule reaches one."""
    if not (target / ".git").exists():
        report["gitignore"] = {"claimed": False, "reason": "not a git repo"}
        return
    if not (target / ".git").is_dir():
        report["gitignore"] = {"claimed": False,
                               "reason": ".git is a file, not a clone's own folder"}
        return
    paths = sorted({rel for rel, own in owners.items() if own != ["<aggregate>"]}
                   | {STATE_REL.as_posix()} | _stray_artifacts(target, booked))
    if len(paths) == 1:                       # the book alone — nothing installed
        report["gitignore"] = {"claimed": False, "reason": "nothing installed"}
        return
    claims.append({"path": EXCLUDE_REL, "fmt": "text", "comment": "#",
                   "key": None,
                   "value": "\n".join("# " + ln for ln in
                                      GITIGNORE_NOTE.split("\n"))
                            + "\n" + "\n".join(paths)})
    report["gitignore"] = {"claimed": True, "count": len(paths),
                           "tracked": _tracked(target, paths)}


def _stray_artifacts(target: Path, booked: set[str]) -> set[str]:
    """Marked artifacts on disk that the book does not know — output of an
    earlier run whose record entry was lost, which the book alone would leave
    out of the block and so up for commit (D14, 2026-09-27). A booked file is
    left to `owners`: this run either re-plans it or prunes it. A skill is
    listed as its FOLDER, the unit D15 owns."""
    out = set()
    for template in {t for row in MATRIX.values() for t in row.values() if t}:
        skill = template.endswith("/{name}/SKILL.md")
        for path in target.glob(template.replace("{name}", "*")):
            rel = path.relative_to(target).as_posix()
            if rel in booked:
                continue
            try:
                head = path.read_text(encoding="utf-8")[:2000]
                marked = any(m in head for m in (MANAGED_MARK, *LEGACY_MARKS))
            except (OSError, UnicodeDecodeError):
                continue
            if marked:
                out.add(rel.rsplit("/", 1)[0] + "/" if skill else rel)
    return out


def _stray_artifact_files(target: Path, booked: set[str]) -> set[str]:
    """Expand the established marker audit into files `apply` can release."""
    files: set[str] = set()
    for rel in _stray_artifacts(target, booked):
        path = target / rel
        if path.is_dir():
            files.update(p.relative_to(target).as_posix()
                         for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            files.add(rel)
    return files


def _tracked(target: Path, paths: list[str]) -> list[str]:
    """The listed paths git already tracks — no ignore file reaches those.
    Empty when git is unavailable; this is a report, never a gate."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(target), "ls-files", "--", *paths],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    return sorted(set(out.stdout.split()) & set(paths))


def _units_for_cid(cid: str, parts: list[str] | None) -> list[str] | None:
    """None = all/refresh. Bare pids apply to every cid. `{cid}#{pid}` only to theirs."""
    if parts is None:
        return None
    keyed, bare = [], []
    for p in parts:
        if "#" in p:
            owner, pid = p.split("#", 1)
            if owner == cid:
                keyed.append(pid)
        else:
            bare.append(p)
    return bare + keyed if (bare or keyed or not any("#" in p for p in parts)) else []


def _scaffold_rbtv(target: Path) -> None:
    """An installation's `.rbtv/` holds its mirror, runtime data and memory
    folders, created empty on the first real run. An installed agent's folder
    (agent.md beside launch.json) is not an installation and gets none."""
    if is_agent_target(target):
        return
    for name in ("mirror", "runtime", "memory"):
        (target / ".rbtv" / name).mkdir(parents=True, exist_ok=True)


def _select_units(comp: dict, existing_parts, requested: list[str] | None
                  ) -> tuple[dict, list[str]]:
    """The component's selected units, and the booked ones whose source no
    longer exists. Those leave the record, so it always matches the files the
    plan keeps (owner ruling G1)."""
    specs = {r["id"]: r["method"] for r in _unit_specs(comp)}
    gone = sorted(pid for pid in (existing_parts or {}) if pid not in specs)
    kept = {pid: dict(p) for pid, p in (existing_parts or {}).items()
            if pid in specs}
    if requested is None:
        if existing_parts is not None:
            return kept, gone
        return {pid: {"method": method, "files": []}
                for pid, method in specs.items()}, gone
    out = kept
    for pid in requested:
        if pid not in specs:
            raise Refuse(
                "unit-unknown",
                f"{comp.get('id', '?')}: no unit {pid!r} in the component "
                "— refusing before any write",
                str(comp["path"]))
        if pid not in out:
            out[pid] = {"method": specs[pid], "files": []}
    return out, gone


def _do_install(target: Path, catalog: dict[str, dict], picked: list[str],
               harnesses: list[str], dry_run: bool,
               guidance_basis: str | None = None,
               guidance_excludes: list[str] | None = None,
               parts: list[str] | None = None,
               scope: str = "all", selected: list[str] | None = None) -> dict:
    state = upgrade_book(read_state(target), catalog_units_map(catalog))
    records = dict(state.get("components") or {})
    if scope == "guidance":
        report: dict = {}
        report["guidance_sections"] = []
        mirror_files: dict[str, str] = {}
        mirror_owners: dict[str, list] = {}
        protect = _add_mirror(target, state, mirror_files, mirror_owners,
                              report, guidance_basis,
                              harnesses, guidance_excludes,
                              preserve_destination_block=True)
        prior = {**state, "components": {}, "shared_claims": []}
        result = apply(target, mirror_files, [], prior, dry_run, protect)
        _clean_bases(target, report, dry_run)
        if not dry_run:
            state["guidance_files"] = sorted(mirror_files)
            write_state(target, state)
        return {"ok": True, "scope": scope, "installed": picked,
                "harnesses": harnesses, "files": sorted(mirror_files),
                **result, "report": report}
    if selected is not None:
        chosen: dict[str, list[str]] = {}
        for key in selected:
            cid, sep, pid = key.partition("#")
            if not sep or cid not in catalog:
                raise Refuse("component-vanished",
                             f"selected unit is unavailable from local source: {key}")
            chosen.setdefault(cid, []).append(pid)
        picked = sorted(chosen)
        parts = sorted(selected)
        old_records = records
        records = {}
    source_gone: list[str] = []
    for cid in picked:
        c = catalog[cid]
        existing = (old_records if selected is not None else records).get(cid) or {}
        if selected is not None:
            wanted = set(_units_for_cid(cid, parts) or [])
            existing = {**existing, "units": {
                pid: part for pid, part in (existing.get("units") or {}).items()
                if pid in wanted}}
        units, gone = _select_units(c, existing.get("units"),
                                    _units_for_cid(cid, parts))
        source_gone += [f"{cid}#{pid}" for pid in gone]
        rec = {"tree": c["tree"], "module": c["module"],
               "component": c["component"],
               "harnesses": [h for h in HARNESSES if h in harnesses],
                "units": units}
        if "files" in existing:
            rec["files"] = list(existing["files"])
        records[cid] = rec
    files, owners, claims, report = plan_files(records, catalog, target)
    report["source_gone"] = source_gone
    saved_guidance = list(state.get("guidance_files") or [])
    report["guidance_sections"] = _section_paths(claims)
    if scope == "scaffolding":
        # The instruction-file copies belong exclusively to update guidance.
        # Exclude them from both the plan and the old-file deletion set.
        apply_state = {**state, "guidance_files": []}
    else:
        apply_state = state
    desired, path_owners = plan_path_links(target, _path_rows_from_report(report))
    requested_parts = set(parts or ())
    selected_path_parts = sorted(
        f"{cid}#{pid}"
        for _name, (cid, pid) in path_owners.items()
        if cid in picked and (parts is None or pid in requested_parts
                              or f"{cid}#{pid}" in requested_parts))
    booked = booked_path_names(state)
    bindir = bin_dir()
    path_active = bool(desired or booked)
    lock = (nullcontext() if dry_run or not path_active else
            shared_mutation_lock(bindir))
    with lock:
        if path_active:
            preflight_shared_links(bindir, desired, booked - set(desired), target)
        protect = (_add_mirror(target, state, files, owners, report, guidance_basis,
                               harnesses, guidance_excludes)
                   if scope == "all" else frozenset())
        for claim in claims:
            rel = claim["path"]
            if rel in report.get("_debanner", {}) and claim["fmt"] == "text":
                report["_debanner"][rel] = _block_set(
                    report["_debanner"][rel], claim["value"], claim["comment"],
                    preserve_outside=(Path(rel).name in GUIDANCE_NAMES),
                    label=claim.get("label"))
            if (rel in files and Path(rel).name in GUIDANCE_NAMES
                    and claim["fmt"] == "text" and claim["comment"] == "<!--"):
                # The shared claim will still be booked, but comparing a copy
                # without its section to the finished file would rewrite it
                # on every identical run and overstate dry-run changes.
                files[rel] = _block_set(files[rel], claim["value"], "<!--",
                                        preserve_outside=True,
                                        label=claim.get("label"))
        copied = {rel for rel, owner in owners.items()
                  if owner == ["<aggregate>"]}
        if copied:
            apply_state = {**apply_state,
                           "shared_claims": [cid for cid in
                                             apply_state.get("shared_claims") or []
                                             if cid.partition("::")[0] not in copied]}
        _add_gitignore(target, owners, claims, report, known_files(state))
        extra_files = (_stray_artifact_files(target, known_files(state) | set(files))
                       if selected is not None else set())
        planned_claims = {_claim_id(c["path"], c["key"], c.get("label"))
                          for c in claims}
        extra_claims = (owned_fence_claims(target, planned_claims)
                        if selected is not None else set())
        result = apply(target, files, claims, apply_state, dry_run, protect,
                       extra_files=extra_files, extra_claims=extra_claims)
        _clean_bases(target, report, dry_run)
        if not dry_run:
            _rebook(state, records, files, owners, claims, report,
                    path_owners=path_owners)
            if scope == "scaffolding":
                state["guidance_files"] = saved_guidance
            if not is_agent_target(target):
                state["harnesses"] = [h for h in HARNESSES if h in harnesses]
            if guidance_basis is not None:
                state["guidance_basis"] = guidance_basis
            if guidance_excludes is not None:
                state["guidance_excludes"] = list(guidance_excludes)
            write_state(target, state)
            _scaffold_rbtv(target)
            report["path"] = (reconcile_shared(
                bindir, desired, booked, target, dry=False, locked=True)
                if path_active else {"linked": [], "relinked": [], "ok": [],
                                     "unlinked": [], "unbooked": [],
                                     "dangling": [], "kept_shared": [],
                                     "legacy_preserved": []})
            report["path_setup"] = {"attempted": False, "ok": None,
                                    "recovery": None}
            if selected_path_parts:
                report["path_setup"]["attempted"] = True
                try:
                    _write_shell_path()
                except OSError as exc:
                    warning = {
                        "code": "path-persist-failed", "message": str(exc),
                        "recovery": "rbtv add "
                        + selected_path_parts[0]
                        + " --target " + shell_quote(target),
                    }
                    report["path_warning"] = warning
                    report["path_setup"].update(ok=False,
                                                 recovery=warning["recovery"])
                else:
                    report["path_setup"]["ok"] = True
        else:
            report["path"] = (reconcile_shared(
                bindir, desired, booked, target, dry=True)
                if path_active else {"linked": [], "relinked": [], "ok": [],
                                     "unlinked": [], "unbooked": [],
                                     "dangling": [], "kept_shared": [],
                                     "legacy_preserved": []})
            report["path_setup"] = {"attempted": False, "ok": None,
                                    "recovery": "apply this install to persist PATH"}
    return {"ok": True, "scope": scope, "installed": picked, "harnesses": harnesses,
            "files": sorted(files), **result, "report": report}


def _do_uninstall(target: Path, catalog: dict[str, dict], picked: list[str],
                 dry_run: bool, parts: list[str] | None = None) -> dict:
    state = upgrade_book(read_state(target), catalog_units_map(catalog))
    # Deep copy: popping a part mutates the dict apply() later reads as the
    # previous book. A shallow copy left removed part files off the stale set,
    # so uninstall forgot them instead of deleting them.
    records = copy.deepcopy(state.get("components") or {})
    missing = [cid for cid in picked if cid not in records]
    if missing:
        raise Refuse("not-installed",
                     "not installed at this target: " + ", ".join(missing))
    for cid in picked:
        rec = records[cid]
        want = _units_for_cid(cid, parts)
        if want is None:
            records.pop(cid)
            continue
        if "units" not in rec:
            name = rec.get("component") or cid.split("/")[-1]
            if set(want) <= {name}:
                records.pop(cid)
                continue
            raise Refuse(
                "unit-unbooked",
                f"{cid} has no parts map (a vanished v1 record) — remove the "
                "whole component; files cannot be split across parts")
        for pid in want:
            rec["units"].pop(pid, None)
        if not rec["units"]:
            records.pop(cid)
    live = {cid: rec for cid, rec in records.items() if cid in catalog}
    stranded = {cid: rec for cid, rec in records.items() if cid not in catalog}
    blockers = [cid for cid, rec in stranded.items() if "units" not in rec]
    if blockers:
        rec0 = stranded[blockers[0]]
        raise Refuse(
            "component-vanished",
            vanished_component_message(blockers[0], rec0.get("tree"), target),
            str(target))
    files, owners, claims, report = plan_files(live, catalog, target)
    report["guidance_sections"] = _section_paths(claims)
    desired, path_owners = plan_path_links(target, _path_rows_from_report(report))
    booked = booked_path_names(state)
    keep_names = booked_path_names({"components": stranded})
    bindir = bin_dir()
    path_active = bool(desired or booked)
    lock = (nullcontext() if dry_run or not path_active else
            shared_mutation_lock(bindir))
    with lock:
        if path_active:
            preflight_shared_links(bindir, desired,
                                   booked - set(desired) - keep_names, target)
        keep_protect: set[str] = set()
        for cid, rec in stranded.items():
            for pid, part in rec["units"].items():
                for rel in part.get("files") or []:
                    keep_protect.add(rel)
                    owners.setdefault(rel, []).append((cid, pid))
                for claim_id in part.get("claims") or []:
                    rebuilt = _rebuild_claim(target, claim_id, (cid, pid))
                    if rebuilt:
                        claims.append(rebuilt)
        report["shared_files"] = sorted({c["path"] for c in claims})
        protect: frozenset[str] = frozenset(keep_protect)
        if records:
            # Components remain → the mirror stays. A full uninstall takes it
            # with everything else (it is installer-owned output, not the basis).
            try:
                protect = protect | _add_mirror(
                    target, state, files, owners, report, None,
                    installed_harnesses(records))
            except Refuse as exc:
                # Removing a component must NEVER be blocked by a mirror problem.
                protect = protect | frozenset(GUIDANCE_NAMES) | frozenset(
                    rel for rel in known_files(state)
                    if rel.rsplit("/", 1)[-1] in GUIDANCE_NAMES)
                report["guidance_mirror"] = {"basis": None, "targets": [],
                                             "skipped": exc.code}
        _add_gitignore(target, owners, claims, report, known_files(state))
        result = apply(target, files, claims, state, dry_run, protect)
        _clean_bases(target, report, dry_run)
        if not dry_run:
            if records:
                _rebook(state, records, files, owners, claims, report,
                        path_owners=path_owners, keep_cids=set(stranded))
                write_state(target, state)
            elif is_agent_target(target):
                # The authored agent record survives an empty selection.
                _rebook(state, records, files, owners, claims, report,
                        path_owners=path_owners)
                write_state(target, state)
            else:
                # Nothing left of ours — take the book away too.
                path = state_path(target)
                if path.is_file():
                    path.unlink()
                _prune(target, path.parent)
            report["path"] = (reconcile_shared(
                bindir, desired, booked - keep_names, target,
                dry=False, locked=True) if path_active else
                {"linked": [], "relinked": [], "ok": [], "unlinked": [],
                 "unbooked": [], "dangling": [], "kept_shared": [],
                 "legacy_preserved": []})
        else:
            report["path"] = (reconcile_shared(
                bindir, desired, booked - keep_names, target, dry=True)
                if path_active else {"linked": [], "relinked": [], "ok": [],
                                     "unlinked": [], "unbooked": [],
                                     "dangling": [], "kept_shared": [],
                                     "legacy_preserved": []})
    return {"ok": True, "uninstalled": picked,
            "remaining": sorted(records),
            **result, "report": report}


def do_install(target: Path, catalog: dict[str, dict], picked: list[str],
               harnesses: list[str], dry_run: bool,
               guidance_basis: str | None = None,
               guidance_excludes: list[str] | None = None,
               parts: list[str] | None = None,
               scope: str = "all", selected: list[str] | None = None) -> dict:
    """Serialize target state before building a plan from it."""
    if dry_run:
        return _do_install(target, catalog, picked, harnesses, dry_run,
                           guidance_basis, guidance_excludes, parts, scope, selected)
    with installation_mutation_lock(target):
        return _do_install(target, catalog, picked, harnesses, dry_run,
                           guidance_basis, guidance_excludes, parts, scope, selected)


def do_uninstall(target: Path, catalog: dict[str, dict], picked: list[str],
                 dry_run: bool, parts: list[str] | None = None) -> dict:
    """Serialize target state before deciding which booked parts to release."""
    if dry_run:
        return _do_uninstall(target, catalog, picked, dry_run, parts)
    with installation_mutation_lock(target):
        return _do_uninstall(target, catalog, picked, dry_run, parts)
