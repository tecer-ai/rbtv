"""The read-only health check: collisions, orphans, drift, and what each one
costs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from discovery import Refuse, scan_tree

from .constants import (
    ANSI,
    BASIS_NONE,
    FENCE_ID,
    GUIDANCE_NAMES,
    HARNESSES,
    SCHEMA,
    STATE_REL,
    VERSION,
)
from .catalog import catalog_parts_map, is_installable
from .claims import _claim_id, _fence, _jget
from .content import _is_ours
from .pathlinks import bin_dir, booked_path_names, link_name, local_bin
from .state import (
    installed_harnesses,
    known_claims,
    known_files,
    read_state,
    upgrade_book,
)
from .planning import plan_files
from .selection import iter_catalog_parts
from .operations import _add_gitignore, _add_mirror, _select_parts


def booked_links(state: dict) -> set[str]:
    return booked_path_names(state)


def _path_index(bindir: Path) -> int:
    want = bindir.expanduser()
    try:
        want_r = want.resolve()
    except OSError:
        want_r = want
    for i, raw in enumerate(os.environ.get("PATH", "").split(os.pathsep)):
        if not raw:
            continue
        p = Path(raw).expanduser()
        try:
            if p == want or p.resolve() == want_r:
                return i
        except OSError:
            if p == want:
                return i
    return -1


def collect_collisions(target: Path, files: dict, claims: list,
                       state: dict) -> list[tuple[str, str]]:
    ours_f, ours_c = known_files(state), known_claims(state)
    hits: list[tuple[str, str]] = []
    for rel in files:
        if rel in ours_f or not (target / rel).exists() or _is_ours(target, rel):
            continue
        hits.append((rel, "guidance-mirror-collision"
                     if rel.rsplit("/", 1)[-1] in GUIDANCE_NAMES
                     else "collision"))
    for claim in claims:
        cid = _claim_id(claim["path"], claim["key"])
        path = target / claim["path"]
        if cid in ours_c or not path.is_file():
            continue
        if claim["fmt"] == "json":
            try:
                doc = json.loads(path.read_text(encoding="utf-8") or "{}")
            except ValueError:
                hits.append((claim["path"], "shared-file-unparseable"))
                continue
            if _jget(doc, claim["key"])[1]:
                hits.append((claim["path"] + "::" + ".".join(claim["key"]),
                             "collision"))
        else:
            start, _ = _fence(claim["comment"])
            if start in path.read_text(encoding="utf-8"):
                hits.append((f"{claim['path']}::{FENCE_ID}-block", "collision"))
    return hits


def inspect_bindir(bindir: Path, booked: set[str],
                   desired: set[str]) -> dict:
    out = {"unbooked": [], "collision": [], "not_exec": []}
    if not bindir.is_dir():
        return out
    names = {p.name for p in bindir.iterdir()}
    out["unbooked"] = sorted(names - booked)
    for name in sorted(desired):
        p = bindir / name
        if p.exists() and not p.is_symlink():
            out["collision"].append(str(p))
            continue
        if p.is_symlink():
            try:
                dest = p.resolve()
            except OSError:
                dest = p
            if dest.is_file() and not os.access(dest, os.X_OK):
                out["not_exec"].append(f"{name} → {dest}")
    return out


def shadows(bindir: Path, booked: set[str]) -> list[str]:
    locdir = local_bin()
    if not locdir.is_dir():
        return []
    watch = set(booked)
    if bindir.is_dir():
        watch |= {p.name for p in bindir.iterdir()}
    hits = []
    for name in sorted(watch):
        loc = locdir / name
        if loc.exists() or loc.is_symlink():
            hits.append(f"{name} → {loc} shadows {bindir / name}")
    return hits


def render_doctor(checks: list[dict], *, pretty: bool = False) -> str:
    lines = []
    for c in checks:
        tok = {"ok": "ok  ", "warn": "warn", "fail": "FAIL"}[c["level"]]
        if pretty:
            tok = f"{ANSI[c['level']]}{tok}{ANSI['reset']}"
        lines.append(f"{tok}  {c['name']}: {c['detail']}")
    n_ok = sum(1 for c in checks if c["level"] == "ok")
    n_warn = sum(1 for c in checks if c["level"] == "warn")
    n_fail = sum(1 for c in checks if c["level"] == "fail")
    head = "FAIL" if n_fail else ("warn" if n_warn else "ok")
    extra = f" ({n_warn} warn)" if n_warn and not n_fail else ""
    lines.append("")
    lines.append(f"{head} — {n_ok}/{len(checks)} checks{extra}")
    nxt = ("next: rbtv install ls" if head == "ok" else
           f"next: fix the {head} lines above, then rerun `rbtv install doctor`")
    lines.append(nxt)
    return "\n".join(lines)


def doctor_exit(checks: list[dict]) -> int:
    return 1 if any(c["level"] == "fail" for c in checks) else 0


def _check(name: str, level: str, detail: str) -> dict:
    return {"name": name, "ok": level == "ok", "level": level, "detail": detail}


def _desired_path_names(catalog: dict, booked: set[str]) -> set[str]:
    names = set(booked)
    for p in iter_catalog_parts(catalog):
        if p["method"] != "path":
            continue
        try:
            names.add(link_name(p["part_id"]))
        except Refuse:
            continue
    return names


def _probe_add_collisions(target: Path, catalog: dict,
                          state: dict) -> tuple[list[tuple[str, str]], str]:
    installable = [cid for cid, c in catalog.items() if is_installable(c)]
    if not installable:
        return [], "no catalog — nothing to plan"
    try:
        records = dict(state.get("components") or {})
        for cid in installable:
            c = catalog[cid]
            existing = records.get(cid) or {}
            rec = {"tree": c.get("tree", ""),
                   "tree_root": c.get("tree_root", ""),
                   "module": c.get("module") or cid.split("/")[0],
                   "component": c.get("component") or cid.rsplit("/", 1)[-1],
                   "harnesses": existing.get("harnesses") or list(HARNESSES),
                   "parts": _select_parts(c, existing.get("parts"), None)}
            if "files" in existing:
                rec["files"] = list(existing["files"])
            records[cid] = rec
        files, owners, claims, report = plan_files(records, catalog)
        _add_mirror(target, state, files, owners, report, None,
                    installed_harnesses(records))
        _add_gitignore(target, owners, claims, report)
    except Refuse as exc:
        return [(exc.path or exc.code, exc.code)], ""
    return collect_collisions(target, files, claims, state), ""


def do_doctor(target: Path, why: str, catalog: dict, shadowed: list,
              repo_tree: Path, mirror_tree: Path) -> dict:
    checks: list[dict] = []
    if not target.is_dir():
        checks.append(_check("target", "fail",
                             f"{target} is not a directory"))
    else:
        checks.append(_check(
            "target", "ok",
            f"{target.resolve()}  (discovered by {why})"))

    book_path = target / STATE_REL
    state: dict = {"schema": SCHEMA, "components": {}}
    if not book_path.is_file():
        checks.append(_check("book", "ok", "no book (never installed)"))
    else:
        try:
            state = upgrade_book(read_state(target),
                                 catalog_parts_map(catalog))
            n = len(state.get("components") or {})
            checks.append(_check(
                "book", "ok",
                f"schema {state.get('schema')} · {n} components"))
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            checks.append(_check("book", "fail", f"unreadable: {exc}"))
            state = {"schema": SCHEMA, "components": {}}

    repo_found = scan_tree(repo_tree, "repo")
    checks.append(_check(
        "tree-repo", "ok",
        f"{repo_tree} — {len(repo_found)} components"))
    if mirror_tree.is_dir():
        mir_found = scan_tree(mirror_tree, "mirror")
        shadow_n = len(set(repo_found) & set(mir_found))
        extra = f" ({shadow_n} shadowing repo)" if shadow_n else ""
        checks.append(_check(
            "tree-mirror", "ok",
            f"{mirror_tree} — {len(mir_found)} components{extra}"))
    else:
        checks.append(_check(
            "tree-mirror", "ok",
            f"absent — 0 components"))

    bindir = bin_dir()
    if bindir.is_dir():
        checks.append(_check("bin-dir", "ok", f"{bindir} exists"))
    else:
        checks.append(_check(
            "bin-dir", "warn", f"{bindir} missing (add will mkdir)"))

    bidx = _path_index(bindir)
    lidx = _path_index(local_bin())
    if bidx < 0:
        checks.append(_check(
            "bin-on-path", "warn",
            f'not on PATH — add once: export PATH="$HOME/.rbtv/bin:$PATH"'))
    elif lidx >= 0 and lidx < bidx:
        checks.append(_check(
            "bin-on-path", "warn",
            f"on PATH at {bidx} but AFTER ~/.local/bin ({lidx}) "
            f"— stale local names win"))
    elif lidx < 0:
        checks.append(_check(
            "bin-on-path", "ok",
            f"{bindir} on PATH at {bidx}, ~/.local/bin absent"))
    else:
        checks.append(_check(
            "bin-on-path", "ok",
            f"{bindir} on PATH at index {bidx} (before ~/.local/bin)"))

    booked = booked_links(state)
    desired = _desired_path_names(catalog, booked)
    sh = shadows(bindir, booked)
    if sh:
        checks.append(_check("local-bin-shadow", "warn", ", ".join(sh)))
    else:
        checks.append(_check("local-bin-shadow", "ok", "none"))

    insp = inspect_bindir(bindir, booked, desired)
    if not bindir.is_dir():
        checks.append(_check("path-unbooked", "ok", "no directory"))
        checks.append(_check("path-collision", "ok", "no directory"))
        checks.append(_check("path-not-executable", "ok", "no directory"))
    else:
        if insp["unbooked"]:
            checks.append(_check(
                "path-unbooked", "warn",
                f"{', '.join(insp['unbooked'])} (left alone; next add "
                f"relinks only if desired+symlink)"))
        else:
            checks.append(_check("path-unbooked", "ok", "none"))
        if insp["collision"]:
            checks.append(_check(
                "path-collision", "warn",
                f"{', '.join(insp['collision'])} exists and is not a "
                f"symlink — next add refuses"))
        else:
            checks.append(_check("path-collision", "ok", "none"))
        if not desired and not booked:
            checks.append(_check("path-not-executable", "ok", "none booked"))
        elif insp["not_exec"]:
            checks.append(_check(
                "path-not-executable", "warn",
                ", ".join(f"{x} not executable (ok: python <path>)"
                          for x in insp["not_exec"])))
        else:
            checks.append(_check("path-not-executable", "ok",
                                 "all executable"))

    hits, empty_msg = _probe_add_collisions(target, catalog, state)
    if empty_msg:
        checks.append(_check("add-collisions", "ok", empty_msg))
    elif not hits:
        checks.append(_check("add-collisions", "ok",
                             "none — next add is clear"))
    else:
        rels = ", ".join(h[0] for h in hits)
        codes = sorted({h[1] for h in hits})
        checks.append(_check(
            "add-collisions", "warn",
            f"{rels} — next add refuses [{', '.join(codes)}]"))

    basis = state.get("guidance_basis")
    if basis is None:
        checks.append(_check("guidance-basis", "ok", "unset (no mirror)"))
    elif basis == BASIS_NONE:
        checks.append(_check("guidance-basis", "ok", "none (no mirror)"))
    elif basis in GUIDANCE_NAMES:
        checks.append(_check("guidance-basis", "ok", str(basis)))
    else:
        checks.append(_check(
            "guidance-basis", "warn",
            f"{basis!r} is neither none nor AGENTS.md · CLAUDE.md — "
            f"next add refuses [guidance-basis-invalid]"))

    failed = any(c["level"] == "fail" for c in checks)
    return {"ok": not failed, "version": VERSION,
            "target": str(target.resolve() if target.exists() else target),
            "why": why, "checks": checks}
