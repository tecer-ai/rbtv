"""Performing one install or one uninstall over a chosen set."""
from __future__ import annotations

from pathlib import Path

from discovery import EXPOSURE_NAME, Refuse

from .constants import (
    GUIDANCE_FILE,
    GUIDANCE_NAMES,
    HARNESSES,
    PATH_BOOTSTRAP,
    STATE_REL,
)
from .catalog import _part_specs, catalog_parts_map
from .claims import _claim_id
from .content import _exposure_block
from .guidance import plan_mirror, resolve_basis
from .pathlinks import (
    _path_rows_from_report,
    _remove_shell_path,
    _write_shell_path,
    bin_dir,
    booked_path_names,
    gate_path_links,
    plan_path_links,
    reconcile,
)
from .state import (
    _rebuild_claim,
    installed_harnesses,
    known_files,
    read_state,
    upgrade_book,
    write_state,
)
from .planning import plan_files
from .apply import _clean_bases, _prune, apply


def _rebook(state: dict, records: dict, files: dict, owners: dict,
            claims: list[dict], report: dict,
            path_owners: dict[str, tuple[str, str]] | None = None,
            keep_cids: set[str] | None = None) -> None:
    keep_cids = set(keep_cids or ())
    for cid, rec in records.items():
        parts = rec.setdefault("parts", {})
        rec_names: list[str] = []
        for pid, part in parts.items():
            part["files"] = sorted(
                rel for rel, own in owners.items() if (cid, pid) in own)
            owned = sorted(
                _claim_id(c["path"], c["key"])
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
        _claim_id(c["path"], c["key"]) for c in claims)
    state["shared_files"] = report["shared_files"]
    state.pop("prefix", None)


def _add_mirror(target: Path, state: dict, files: dict, owners: dict,
                report: dict, override: str | None, harnesses,
                exclude_override: list[str] | None = None) -> frozenset[str]:
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
    blocks = {name: _exposure_block(name, list(harnesses),
                                    report.get("agents_parts") or [],
                                    report.get("rule_parts") or [])
              for name in GUIDANCE_NAMES}
    mirrors, bases, stripped, targets, debanner = plan_mirror(
        target, basis, harnesses, excludes, blocks)
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
    # D8 — every guidance file an installed harness reads that this run does NOT
    # write (the basis, or all of them when the mirror is off) needs its block
    # placed by hand. Reported, never written.
    needed = {GUIDANCE_FILE[h] for h in harnesses if h in GUIDANCE_FILE}
    report["guidance_manual"] = {
        name: block for name, block in blocks.items()
        if block and name in needed and name not in targets}
    return bases


GITIGNORE_NOTE = (
    "install.py artifacts — MACHINE-LOCAL, never committed: the "
    "loaders bake\nabsolute entry-point paths and the book records an absolute "
    "target, so a committed copy\nis wrong on every other machine "
    "(d-s15-installer2-artifacts-machine-local). Generated from\nthe book on "
    "every install and uninstall — edit nothing between the fences; re-run the\n"
    "installer instead. The guidance mirror is deliberately absent: it is "
    "workspace content.")


def _add_gitignore(target: Path, owners: dict[str, list], claims: list[dict],
                   report: dict) -> None:
    """Claim the `.gitignore` block that keeps our artifacts out of git (D14).

    Listed: every per-component file (the `<aggregate>` owner is the guidance
    mirror, which is workspace content and stays committable) plus the book.
    Skipped entirely off a git repo. Files git ALREADY TRACKS are reported,
    because no ignore rule reaches one."""
    if not (target / ".git").exists():
        report["gitignore"] = {"claimed": False, "reason": "not a git repo"}
        return
    paths = sorted([rel for rel, own in owners.items() if own != ["<aggregate>"]]
                   + [STATE_REL.as_posix()])
    if len(paths) == 1:                       # the book alone — nothing installed
        report["gitignore"] = {"claimed": False, "reason": "nothing installed"}
        return
    claims.append({"path": ".gitignore", "fmt": "text", "comment": "#",
                   "key": None,
                   "value": "\n".join("# " + ln for ln in
                                      GITIGNORE_NOTE.split("\n"))
                            + "\n" + "\n".join(paths)})
    report["gitignore"] = {"claimed": True, "count": len(paths),
                           "tracked": _tracked(target, paths)}


def _tracked(target: Path, paths: list[str]) -> list[str]:
    """The listed paths git already tracks — `.gitignore` cannot reach those.
    Empty when git is unavailable; this is a report, never a gate."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(target), "ls-files", "--", *paths],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    return sorted(set(out.stdout.split()) & set(paths))


def _parts_for_cid(cid: str, parts: list[str] | None) -> list[str] | None:
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


def _select_parts(comp: dict, existing_parts, requested: list[str] | None
                  ) -> dict:
    specs = {r["id"]: r["method"] for r in _part_specs(comp, strict=True)}
    if requested is None:
        if existing_parts is not None:
            return {pid: dict(p) for pid, p in existing_parts.items()}
        return {pid: {"method": method, "files": []}
                for pid, method in specs.items()}
    out = {pid: dict(p) for pid, p in (existing_parts or {}).items()}
    for pid in requested:
        if pid not in specs:
            raise Refuse(
                "part-unknown",
                f"{comp.get('id', '?')}: no part {pid!r} in the exposure "
                "manifest — refusing before any write",
                str(Path(comp["path"]) / EXPOSURE_NAME))
        if pid not in out:
            out[pid] = {"method": specs[pid], "files": []}
    return out


def do_install(target: Path, catalog: dict[str, dict], picked: list[str],
               harnesses: list[str], dry_run: bool,
               guidance_basis: str | None = None,
               guidance_excludes: list[str] | None = None,
               parts: list[str] | None = None,
               write_path: bool = False) -> dict:
    state = upgrade_book(read_state(target), catalog_parts_map(catalog))
    records = dict(state.get("components") or {})
    for cid in picked:
        c = catalog[cid]
        existing = records.get(cid) or {}
        rec = {"tree": c["tree"], "tree_root": c["tree_root"],
               "module": c["module"], "component": c["component"],
               "harnesses": [h for h in HARNESSES if h in harnesses],
                "parts": _select_parts(c, existing.get("parts"),
                                       _parts_for_cid(cid, parts))}
        if "files" in existing:
            rec["files"] = list(existing["files"])
        records[cid] = rec
    files, owners, claims, report = plan_files(records, catalog)
    desired, path_owners = plan_path_links(target, _path_rows_from_report(report))
    booked = booked_path_names(state)
    bindir = bin_dir()
    gate_path_links(bindir, desired, booked - set(desired))
    report["path_bootstrap"] = PATH_BOOTSTRAP
    protect = _add_mirror(target, state, files, owners, report, guidance_basis,
                          installed_harnesses(records), guidance_excludes)
    _add_gitignore(target, owners, claims, report)
    result = apply(target, files, claims, state, dry_run, protect)
    _clean_bases(target, report, dry_run)
    if not dry_run:
        _rebook(state, records, files, owners, claims, report,
                path_owners=path_owners)
        state["harnesses"] = [h for h in HARNESSES if h in harnesses]
        if guidance_basis is not None:
            state["guidance_basis"] = guidance_basis
        if guidance_excludes is not None:
            state["guidance_excludes"] = list(guidance_excludes)
        if write_path:
            state["path_bootstrap"] = True
        write_state(target, state)
        report["path"] = reconcile(bindir, desired, booked, dry=False)
        if write_path:
            _write_shell_path()
    else:
        report["path"] = reconcile(bindir, desired, booked, dry=True)
    return {"ok": True, "installed": picked, "harnesses": harnesses,
            "files": sorted(files), **result, "report": report}


def do_uninstall(target: Path, catalog: dict[str, dict], picked: list[str],
                 dry_run: bool, parts: list[str] | None = None) -> dict:
    state = upgrade_book(read_state(target), catalog_parts_map(catalog))
    records = dict(state.get("components") or {})
    missing = [cid for cid in picked if cid not in records]
    if missing:
        raise Refuse("not-installed",
                     "not installed at this target: " + ", ".join(missing))
    for cid in picked:
        rec = records[cid]
        want = _parts_for_cid(cid, parts)
        if want is None:
            records.pop(cid)
            continue
        if "parts" not in rec:
            name = rec.get("component") or cid.split("/")[-1]
            if set(want) <= {name}:
                records.pop(cid)
                continue
            raise Refuse(
                "part-unbooked",
                f"{cid} has no parts map (a vanished v1 record) — remove the "
                "whole component; files cannot be split across parts")
        for pid in want:
            rec["parts"].pop(pid, None)
        if not rec["parts"]:
            records.pop(cid)
    live = {cid: rec for cid, rec in records.items() if cid in catalog}
    stranded = {cid: rec for cid, rec in records.items() if cid not in catalog}
    blockers = [cid for cid, rec in stranded.items() if "parts" not in rec]
    if blockers:
        rec0 = stranded[blockers[0]]
        raise Refuse(
            "component-vanished",
            f"component {blockers[0]!r} is recorded as installed but no longer "
            f"exists under {rec0.get('tree_root')!r} (renamed or deleted "
            "upstream). Every run at this target refuses until the book "
            "agrees with the trees. Recover with EITHER: restore the "
            f"folder; or `uninstall --component {blockers[0]}`, which needs no "
            "tree — the book holds its files",
            str(rec0.get("tree_root", "")))
    files, owners, claims, report = plan_files(live, catalog)
    desired, path_owners = plan_path_links(target, _path_rows_from_report(report))
    booked = booked_path_names(state)
    keep_names = booked_path_names({"components": stranded})
    bindir = bin_dir()
    gate_path_links(bindir, desired, booked - set(desired) - keep_names)
    report["path_bootstrap"] = PATH_BOOTSTRAP
    keep_protect: set[str] = set()
    for cid, rec in stranded.items():
        for pid, part in rec["parts"].items():
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
        # Components remain → the mirror stays. A full uninstall takes it with
        # everything else (it is installer-owned output, not the basis).
        try:
            protect = protect | _add_mirror(
                target, state, files, owners, report, None,
                installed_harnesses(records))
        except Refuse as exc:
            # Removing a component must NEVER be blocked by a mirror problem
            # (a deleted basis, a hand-edited book). Skip the replan, and keep
            # EVERY guidance file the book holds, under either name and at any
            # depth, off the delete set — un-managed on disk beats deleted, and
            # the next install re-books whatever is real.
            protect = protect | frozenset(GUIDANCE_NAMES) | frozenset(
                rel for rel in known_files(state)
                if rel.rsplit("/", 1)[-1] in GUIDANCE_NAMES)
            report["guidance_mirror"] = {"basis": None, "targets": [],
                                         "skipped": exc.code}
    _add_gitignore(target, owners, claims, report)
    result = apply(target, files, claims, state, dry_run, protect)
    _clean_bases(target, report, dry_run)
    if not dry_run:
        if records:
            _rebook(state, records, files, owners, claims, report,
                    path_owners=path_owners, keep_cids=set(stranded))
            write_state(target, state)
        else:
            if state.get("path_bootstrap"):
                _remove_shell_path()
            # Nothing left of ours — take the book away too. Only OUR artifacts
            # were removed above; anything foreign at the root is still there.
            path = target / STATE_REL
            if path.is_file():
                path.unlink()
            _prune(target, path.parent)
        report["path"] = reconcile(bindir, desired, booked, dry=False,
                                   keep=keep_names)
    else:
        report["path"] = reconcile(bindir, desired, booked, dry=True,
                                   keep=keep_names)
    return {"ok": True, "uninstalled": picked,
            "remaining": sorted(records),
            **result, "report": report}
