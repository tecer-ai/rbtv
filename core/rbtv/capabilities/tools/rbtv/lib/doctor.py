"""The read-only health check for ONE selected installation: is its saved
selection intact, and do its selected shared command shortcuts resolve
through the current PATH (the system command lookup list) to the tool this
installation actually selected — never a stale ownership record.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from discovery import Refuse, scan_tree

from .constants import (
    BASIS_NONE,
    GUIDANCE_NAMES,
    LEGACY_PATH_FENCE,
    PATH_FENCE_END,
    PATH_FENCE_START,
    SCHEMA,
    STATE_REL,
    VERSION,
)
from .catalog import catalog_files_map
from .pathlinks import (
    _owned,
    _path_rows_from_report,
    bin_dir,
    booked_path_names,
    link_path,
    link_points_at,
    plan_path_links,
    shell_profiles,
)
from .planning import plan_files
from .shared_links import _read_owners, _installation_key, path_ownership_status
from .state import is_agent_target, known_claims, known_files, read_state, upgrade_book
from .recovery import shell_quote

_WIN = os.name == "nt"


def booked_links(state: dict) -> set[str]:
    return booked_path_names(state)


def _check(name: str, level: str, scope: str, detail: str) -> dict:
    return {"name": name, "ok": level == "ok", "level": level,
            "scope": scope, "detail": detail}


def _quote_target(target: Path) -> str:
    return shell_quote(target)


def _scaffolding_recovery(target: Path) -> str:
    q = _quote_target(target)
    return (f"preview: rbtv update scaffolding --dry-run --target {q}; "
            f"apply: rbtv update scaffolding --target {q}")


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right


def _persistent_path_status(bindir: Path) -> tuple[bool | None, str | None]:
    """Whether bindir is on PATH beyond this process; None means unreadable.

    Distinct from `os.environ["PATH"]`, which only tells us about THIS
    process — a persistent entry that exists but has not reached this shell
    needs "open a new terminal", not "rerun an install"."""
    if _WIN:
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
        if any(a in text and b in text for a, b in
               ((PATH_FENCE_START, PATH_FENCE_END), LEGACY_PATH_FENCE)):
            return True, None
    return False, None


def _selected_path_rows(target: Path, catalog: dict, state: dict
                        ) -> tuple[dict[str, Path], Refuse | None]:
    """PATH shortcut targets this installation's saved selection currently
    implies, resolved against the CURRENT local catalog (never the shared-
    ownership record, which can be stale)."""
    records = state.get("components") or {}
    if not records:
        return {}, None
    try:
        _, _, _, report = plan_files(records, catalog, target)
        desired, _owners = plan_path_links(target, _path_rows_from_report(report))
    except Refuse as exc:
        return {}, exc
    return desired, None


def _legacy_shortcuts(bindir: Path, booked: set[str],
                      registered: set[str]) -> list[str]:
    """Managed-format shortcuts on this machine that neither this installation's
    book nor the shared ownership record claims — cleanup-audit only."""
    if not bindir.is_dir():
        return []
    out = []
    for path in bindir.iterdir():
        if _WIN and path.suffix.lower() != ".cmd":
            continue  # the bash twin of a `.cmd` shim, not a shortcut of its own
        name = path.stem if _WIN else path.name
        if name in booked or name in registered:
            continue
        if _owned(path):
            out.append(name)
    return sorted(out)


def doctor_exit(checks: list[dict]) -> int:
    return 1 if any(c["level"] == "fail" for c in checks) else 0


def do_doctor(target: Path, why: str, catalog: dict, shadowed: list,
              repo_tree: Path, mirror_tree: Path, *,
              cleanup_audit: bool = False) -> dict:
    del shadowed  # unrelated to a single installation's selected-scope health
    checks: list[dict] = []
    state: dict = {"schema": SCHEMA, "components": {}}
    target_scope = "Agent" if is_agent_target(target) else "Installation"

    if not target.is_dir():
        checks.append(_check("Saved selection", "fail", target_scope,
                             f"{target} is not a directory"))
    else:
        book_path = target / STATE_REL
        if not book_path.is_file():
            checks.append(_check("Saved selection", "ok", target_scope,
                                 "no saved selection (never installed)"))
        else:
            try:
                state = upgrade_book(read_state(target), catalog_files_map(catalog))
                n = len(state.get("components") or {})
                checks.append(_check(
                    "Saved selection", "ok", target_scope,
                    f"{n} component{'s' if n != 1 else ''}; record readable"))
            except (ValueError, OSError, json.JSONDecodeError, Refuse) as exc:
                checks.append(_check("Saved selection", "fail", target_scope,
                                     f"unreadable: {exc}"))
                state = {"schema": SCHEMA, "components": {}}

        # Expected on disk: every file this selection booked (component AND
        # part level), every GENERATED guidance counterpart (the basis
        # itself is human-authored and covered separately below), and every
        # shared-file claim this selection holds — a rule/hook/config
        # exposure that only ever writes a KEY inside a shared file, never a
        # file of its own, is not "healthy" if that shared file is gone.
        # `configure` can write guidance copies (and claims) with an EMPTY
        # component set, so this is never gated on components being booked —
        # only on the resulting expected set actually being empty.
        expected: set[str] = set(known_files(state))
        for claim_id in known_claims(state):
            rel, _, _key = claim_id.partition("::")
            if rel:
                expected.add(rel)
        if not expected:
            checks.append(_check("Selected files", "ok", target_scope,
                                 "no selection — nothing to check"))
        else:
            missing = sorted(rel for rel in expected
                             if not (target / rel).is_file())
            if missing:
                checks.append({**_check("Selected files", "fail", target_scope,
                                        f"missing: {', '.join(missing)}"),
                               "repair": f"rbtv update scaffolding --target {_quote_target(target)}"})
            else:
                checks.append(_check("Selected files", "ok", target_scope,
                                     "Expected files present"))

        basis = state.get("guidance_basis")
        if basis is None or basis == BASIS_NONE:
            checks.append(_check("Maintained guidance", "ok", target_scope,
                                 "none (no mirror)"))
        elif basis in GUIDANCE_NAMES:
            if (target / basis).is_file():
                checks.append(_check("Maintained guidance", "ok", target_scope,
                                     f"{basis} present"))
            else:
                checks.append(_check("Maintained guidance", "fail", target_scope,
                                     f"{basis} missing"))
        else:
            checks.append(_check(
                "Maintained guidance", "fail", target_scope,
                f"{basis!r} is neither none nor {' · '.join(GUIDANCE_NAMES)}"))

    repo_found = scan_tree(repo_tree, "repo")
    detail = f"{len(repo_found)} components discovered"
    if mirror_tree.is_dir():
        mir_found = scan_tree(mirror_tree, "mirror")
        detail += f" ({len(mir_found)} mirrored)"
    checks.append(_check("Source catalog", "ok", "Local RBTV source", detail))

    desired, path_err = _selected_path_rows(target, catalog, state)
    bindir = bin_dir()
    installation_key = _installation_key(target) if target.exists() else str(target)
    if path_err is not None:
        # A planning failure (a vanished component, an unrunnable entry —
        # e.g. a POSIX target that lost its execute bit, caught here because
        # `plan_path_links` re-validates it against the CURRENT file on every
        # run) is a problem with the selected SOURCE, not with the shared
        # shortcut registry — a skill-only installation with a broken source
        # has no shortcut to blame this on.
        detail = f"cannot resolve selected shortcuts: {path_err}"
        if path_err.code == "path-not-runnable" and not _WIN:
            detail += (f"; chmod +x {shell_quote(path_err.path)} to restore "
                       "it, then rerun doctor")
        checks.append(_check("Selected source", "fail", "Local RBTV source",
                             detail))
    elif desired:
        try:
            owner_data = _read_owners(bindir)
            parts = []
            all_owned = True
            for name in sorted(desired):
                entry = owner_data["links"].get(name)
                owned_here = entry is not None and installation_key in entry["owners"]
                all_owned = all_owned and owned_here
                if entry is None:
                    parts.append(f"{name}: not tracked in shared ownership record")
                elif not owned_here:
                    n_owners = len(entry["owners"])
                    parts.append(
                        f"{name}: claimed by {n_owners} other "
                        f"installation{'s' if n_owners != 1 else ''}, not this one")
                else:
                    n_owners = len(entry["owners"])
                    parts.append(f"{name}: claimed by {n_owners} "
                                 f"installation{'s' if n_owners != 1 else ''}")
            level = "ok" if all_owned else "fail"
            recov = "" if all_owned else f"; {_scaffolding_recovery(target)}"
            checks.append(_check("Shared shortcut ownership", level,
                                 "Shared commands", "; ".join(parts) + recov))
        except Refuse as exc:
            checks.append(_check("Shared shortcut ownership", "fail",
                                 "Shared commands", f"unreadable: {exc}"))

        for name in sorted(desired):
            dest = desired[name]
            path = link_path(bindir, name)
            if not (path.exists() or path.is_symlink()):
                checks.append(_check(
                    f"Selected shortcut: {name}", "fail", "Shared commands",
                    f"Managed {name} shortcut missing; "
                    f"{_scaffolding_recovery(target)}"))
            elif not _owned(path):
                checks.append(_check(
                    f"Selected shortcut: {name}", "fail", "Shared commands",
                    f"{path} exists and is not a managed shortcut; inspect it "
                    f"and move or remove it yourself (doctor never overwrites "
                    f"a file it did not create), then rerun: "
                    f"{_scaffolding_recovery(target)}"))
            elif not link_points_at(path, dest):
                checks.append(_check(
                    f"Selected shortcut: {name}", "fail", "Shared commands",
                    f"{path} points elsewhere; intended target {dest}; "
                    f"{_scaffolding_recovery(target)}"))
            else:
                checks.append(_check(
                    f"Selected shortcut: {name}", "ok", "Shared commands",
                    "Link points to intended tool"))

            hit = shutil.which(name, path=os.environ.get("PATH", ""))
            if hit is None:
                persisted, err = _persistent_path_status(bindir)
                if persisted:
                    path_detail = (f"a persistent PATH entry for {bindir} "
                                   "exists — open a new terminal, then rerun "
                                   "doctor")
                elif err:
                    path_detail = (f"could not confirm persistent PATH for "
                                   f"{bindir}: {err}")
                else:
                    path_detail = (f"no persistent PATH entry for {bindir} "
                                   f"either; {_scaffolding_recovery(target)}, "
                                   "then open a new terminal")
                checks.append(_check(
                    f"Command lookup: {name}", "fail", "Current PATH",
                    f"No {name} command found on this PATH; {path_detail}"))
            elif _same_path(Path(hit), path):
                checks.append(_check(
                    f"Command lookup: {name}", "ok", "Current PATH",
                    f"Resolves to managed {name}"))
            else:
                checks.append(_check(
                    f"Command lookup: {name}", "fail", "Current PATH",
                    f"{hit} answers before {path}; move {bindir} earlier on "
                    f"PATH (or remove the earlier entry yourself — doctor "
                    "cannot repair another program's PATH placement), then "
                    "open a new terminal and rerun doctor"))

    if cleanup_audit:
        try:
            ownership = path_ownership_status(bindir)
        except Refuse as exc:
            checks.append(_check("Stale owner claim", "warn",
                                 "Other installation", f"unreadable: {exc}"))
            ownership = None
        if ownership is not None:
            missing = sorted({Path(owner) for row in ownership["orphaned"]
                              for owner in row["owners"]}, key=str)
            for owner in missing:
                checks.append(_check(
                    "Stale owner claim", "warn", "Other installation",
                    f"{owner} is absent; preview: rbtv remove --all "
                    f"--dry-run --target {_quote_target(owner)}; release: "
                    f"rbtv remove --all --yes --target "
                    f"{_quote_target(owner)}"))
            for row in ownership["unreadable"]:
                checks.append(_check(
                    "Stale owner claim", "warn", "Other installation",
                    f"{row['name']}: {row['owner']}: {row['error']}"))
            registered = set(ownership["names"])
            for name in _legacy_shortcuts(bindir, booked_links(state), registered):
                checks.append(_check(
                    "Legacy shortcut", "warn", "Other installation",
                    f"{name} is a managed shortcut with no installation or "
                    "shared-record owner"))

    failed = any(c["level"] == "fail" for c in checks)
    return {"ok": not failed, "version": VERSION,
            "target": str(target.resolve() if target.exists() else target),
            "why": why, "checks": checks}
