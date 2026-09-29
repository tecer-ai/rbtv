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
    PATH_FENCE_END,
    PATH_FENCE_START,
    SCHEMA,
    STATE_REL,
    VERSION,
    _RUNTIME,
)
from .catalog import catalog_parts_map, is_installable
from .claims import _claim_id, _fence, _jget
from .content import _is_ours
from .pathlinks import (
    _owned,
    _shim_target,
    bin_dir,
    booked_path_names,
    link_name,
    link_path,
    local_bin,
    shell_profiles,
)
from .shared_links import path_ownership_status
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
from .recovery import shell_quote


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


def inspect_bindir(bindir: Path, booked: set[str], desired: set[str],
                   registered: set[str]) -> dict:
    out = {"unbooked": [], "collision": [], "not_exec": [],
           "legacy": []}
    if not bindir.is_dir():
        return out
    for path in bindir.iterdir():
        # A Windows shortcut has both `name.cmd` and its bash twin `name`.
        # The twin belongs to a managed .cmd shim, so it is not an unbooked
        # file in its own right.
        if os.name == "nt" and path.suffix.lower() != ".cmd" and \
                _owned(link_path(bindir, path.name)):
            continue
        name = path.stem if os.name == "nt" and \
            path.suffix.lower() == ".cmd" else path.name
        if name in booked or name in registered:
            continue
        if _owned(path):
            out["legacy"].append(path.name)
        else:
            out["unbooked"].append(path.name)
    for name in sorted(desired):
        p = link_path(bindir, name)
        if (p.exists() or p.is_symlink()) and not _owned(p):
            out["collision"].append(str(p))
            continue
        if _owned(p):
            try:
                dest = _shim_target(p) or p.resolve()
            except OSError:
                dest = p
            if os.name != "nt" and dest.is_file() and not os.access(dest, os.X_OK):
                out["not_exec"].append(f"{name} → {dest}")
    out["unbooked"].sort()
    out["legacy"].sort()
    return out


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right


def _persistent_path_status(bindir: Path) -> tuple[bool | None, str | None]:
    """Whether setup persists beyond this process; None means unreadable."""
    if os.name == "nt" and _RUNTIME.get("rc") is None:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                                winreg.KEY_READ) as key:
                raw = winreg.QueryValueEx(key, "Path")[0]
        except FileNotFoundError:
            return False, None
        except OSError as exc:
            return None, str(exc)
        entries = (Path(os.path.expandvars(part)).expanduser()
                   for part in str(raw).split(";") if part)
        return any(_same_path(entry, bindir) for entry in entries), None
    for profile in shell_profiles():
        try:
            text = profile.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except OSError as exc:
            return None, f"cannot read {profile}: {exc}"
        if PATH_FENCE_START in text and PATH_FENCE_END in text:
            return True, None
    return False, None


def _quote_target(target: Path) -> str:
    return shell_quote(target)


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
        files, owners, claims, report = plan_files(records, catalog, target)
        _add_mirror(target, state, files, owners, report, None,
                    installed_harnesses(records))
        _add_gitignore(target, owners, claims, report, known_files(state))
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
        except (ValueError, OSError, json.JSONDecodeError, Refuse) as exc:
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
        persisted, persistent_error = _persistent_path_status(bindir)
        if persisted:
            detail = ("not on current PATH; persistent user PATH setup exists — "
                      "open a new terminal")
        elif persistent_error:
            detail = ("not on current PATH; could not read persistent PATH "
                      f"setup: {persistent_error}")
        elif os.name == "nt":
            detail = ("not on current PATH or persistent user PATH — rerun an "
                      "install containing a PATH tool where user PATH writes "
                      "are permitted")
        else:
            detail = ("not on current PATH or shell profile — rerun an install "
                      "containing a PATH tool, then open a new shell")
        checks.append(_check(
            "bin-on-path", "warn", detail))
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
    ownership = None
    try:
        ownership = path_ownership_status(bindir)
    except Refuse as exc:
        checks.append(_check("path-ownership", "fail",
                             f"unreadable: {exc}"))
    sh = shadows(bindir, booked)
    if sh:
        checks.append(_check("local-bin-shadow", "warn", ", ".join(sh)))
    else:
        checks.append(_check("local-bin-shadow", "ok", "none"))

    registered = set((ownership or {}).get("names") or [])
    insp = inspect_bindir(bindir, booked, desired, registered)
    if ownership is not None:
        missing = sorted({Path(owner) for row in ownership["orphaned"]
                          for owner in row["owners"]}, key=str)
        if missing:
            commands = "; ".join(
                "rbtv install remove --all --yes --target "
                + _quote_target(owner) for owner in missing)
            checks.append(_check(
                "path-ownership", "warn",
                "orphaned workspace owner(s): " + ", ".join(map(str, missing))
                + "; cleanup: " + commands))
        elif ownership["unreadable"]:
            detail = "; ".join(
                f"{row['owner']}: {row['error']}" for row in ownership["unreadable"])
            checks.append(_check("path-ownership", "warn",
                                 "owner path could not be checked: " + detail))
        elif insp["legacy"]:
            checks.append(_check(
                "path-ownership", "warn",
                "unregistered managed shortcut(s) preserved: "
                + ", ".join(insp["legacy"])))
        else:
            checks.append(_check("path-ownership", "ok",
                                 f"{ownership['links']} registered shortcut(s)"))
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
                f"{', '.join(insp['collision'])} exists and is not a managed "
                f"shortcut — next add refuses"))
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
