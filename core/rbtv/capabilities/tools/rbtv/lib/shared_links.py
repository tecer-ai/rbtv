"""Machine-local shared shortcut ownership and mutation serialization."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from contextlib import contextmanager, nullcontext
from pathlib import Path

from discovery import Refuse

from .fsio import write_file
from .locks import mutation_lock
from .pathlinks import (
    _forbid_local_bin,
    _owned,
    gate_path_links,
    link_one,
    link_path,
    link_points_at,
    unlink_one,
)

_OWNER_SCHEMA = 1
_INSTALLATION_LOCKS = threading.local()


def owner_file(bindir: Path) -> Path:
    """The machine-local record for shortcuts created under D25."""
    return bindir.parent / "path-owners.json"


@contextmanager
def shared_mutation_lock(bindir: Path):
    """Serialize the shared shortcut record and links."""
    with mutation_lock(owner_file(bindir).parent / "path-owners.lock"):
        yield


@contextmanager
def installation_mutation_lock(target: Path):
    """Serialize one installation mutation from its first state read onward."""
    key = str(target.resolve())
    held = getattr(_INSTALLATION_LOCKS, "held", {})
    if held.get(key, 0):
        held[key] += 1
        try:
            yield
        finally:
            held[key] -= 1
        return
    held[key] = 1
    _INSTALLATION_LOCKS.held = held
    try:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        path = Path(tempfile.gettempdir()) / "rbtv-installer-locks" / \
            f"{digest}.lock"
        with mutation_lock(path):
            yield
    finally:
        held.pop(key, None)


def _read_owners(bindir: Path) -> dict:
    path = owner_file(bindir)
    if not path.is_file():
        return {"schema": _OWNER_SCHEMA, "links": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refuse("path-owners-unreadable",
                     f"cannot read shared PATH ownership record; repair {path} before changing shortcuts ({exc})",
                     str(path)) from exc
    schema = data.get("schema", _OWNER_SCHEMA) if isinstance(data, dict) else None
    if schema != _OWNER_SCHEMA:
        raise Refuse("path-owners-unreadable",
                     f"unsupported shared PATH ownership schema in {path}: {schema!r}",
                     str(path))
    links = data.get("links") if isinstance(data, dict) else None
    if not isinstance(links, dict):
        raise Refuse("path-owners-unreadable",
                     f"shared PATH ownership record must contain a links object: {path}",
                     str(path))
    for name, entry in links.items():
        if not isinstance(name, str) or not name or \
                Path(name).name != name or not isinstance(entry, dict) or \
                not isinstance(entry.get("target"), str) or \
                not isinstance(entry.get("owners"), list) or \
                not entry["owners"] or not all(
                    isinstance(owner, str) and Path(owner).is_absolute()
                    for owner in entry["owners"]) or \
                not Path(entry["target"]).is_absolute():
            raise Refuse("path-owners-unreadable",
                         f"shared PATH ownership record has an invalid entry for {name!r}",
                         str(path))
    return {"schema": _OWNER_SCHEMA, "links": links}


def _write_owners(bindir: Path, data: dict) -> None:
    path = owner_file(bindir)
    if not data["links"]:
        if path.is_file():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        write_file(temp, json.dumps(data, indent=2, sort_keys=True) + "\n")
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink()
        except OSError:
            pass
        raise Refuse("path-owners-write-failed",
                     f"could not atomically update shared PATH ownership record: {exc}",
                     str(path)) from exc


def path_ownership_status(bindir: Path) -> dict:
    """Read-only ownership health for doctor and explicit operator repair."""
    data = _read_owners(bindir)
    orphaned, unreadable = [], []
    for name, entry in sorted(data["links"].items()):
        missing = []
        for owner in entry["owners"]:
            try:
                Path(owner).stat()
            except FileNotFoundError:
                missing.append(owner)
            except OSError as exc:
                unreadable.append({"name": name, "owner": owner,
                                   "error": str(exc)})
        if missing:
            orphaned.append({"name": name, "target": entry["target"],
                             "owners": missing})
    return {"record": str(owner_file(bindir)), "links": len(data["links"]),
            "orphaned": orphaned, "unreadable": unreadable,
            "names": sorted(data["links"])}


def _installation_key(target: Path) -> str:
    return str(target.resolve())


def _legacy_owned_link(path: Path, dest: Path) -> bool:
    return ((path.exists() or path.is_symlink()) and _owned(path)
            and link_points_at(path, dest))


def _recorded_target_missing(entry: dict) -> bool:
    """A vanished target cannot reserve a shared shortcut."""
    return not Path(entry["target"]).exists()


def preflight_shared_links(bindir: Path, desired: dict[str, Path],
                           booked: set[str], target: Path) -> dict:
    """Refuse shared shortcut conflicts before target files are touched."""
    _forbid_local_bin(bindir)
    data = _read_owners(bindir)
    installation = _installation_key(target)
    for name, dest in sorted(desired.items()):
        entry = data["links"].get(name)
        path = link_path(bindir, name)
        if entry and entry["target"] != str(dest) and \
                not _recorded_target_missing(entry):
            if set(entry["owners"]) != {installation}:
                owners = ", ".join(entry["owners"]) or "an unknown installation"
                raise Refuse("path-owner-conflict",
                             f"PATH shortcut {name} already serves {entry['target']} for {owners}; it cannot also serve {dest}",
                             str(path))
        if not entry and _legacy_owned_link(path, dest):
            continue
        if not entry and (path.exists() or path.is_symlink()) and _owned(path):
            raise Refuse("path-legacy-conflict",
                         f"PATH shortcut {name} is an untracked legacy link with a different target; preserve it or remove it manually before installing {dest}",
                         str(path))
    gate_path_links(bindir, desired, booked - set(desired))
    return data


def reconcile_shared(bindir: Path, desired: dict[str, Path], booked: set[str],
                     target: Path, *, dry: bool, locked: bool = False) -> dict:
    """Reconcile shortcuts and their D25 owners under one machine-local lock."""
    report = {"linked": [], "relinked": [], "ok": [], "unlinked": [],
              "unbooked": [], "dangling": [], "kept_shared": [],
              "legacy_preserved": []}
    installation = _installation_key(target)
    @contextmanager
    def held():
        if dry or locked:
            yield
        else:
            with shared_mutation_lock(bindir):
                yield

    with held():
        data = preflight_shared_links(bindir, desired, booked, target)
        links = data["links"]
        for name, dest in sorted(desired.items()):
            if not dest.is_file():
                report["dangling"].append(name)
                raise Refuse("entry-point-missing",
                             f"PATH target for {name} is gone: {dest}", str(dest))
            entry = links.get(name)
            path = link_path(bindir, name)
            if entry is None and _legacy_owned_link(path, dest):
                report["legacy_preserved"].append(name)
                continue
            status = link_one(bindir, name, dest, dry=dry)
            report[status].append(name)
            if entry is None:
                links[name] = {"target": str(dest), "owners": [installation]}
            elif entry["target"] != str(dest):
                entry["target"] = str(dest)
            elif installation not in entry["owners"]:
                entry["owners"].append(installation)
                entry["owners"].sort()
        for name in sorted(booked - set(desired)):
            entry = links.get(name)
            if entry is None:
                path = link_path(bindir, name)
                if path.exists() or path.is_symlink():
                    report["legacy_preserved"].append(name)
                continue
            if _recorded_target_missing(entry):
                status = unlink_one(bindir, name, dry=dry)
                if status == "unlinked":
                    report["unlinked"].append(name)
                links.pop(name, None)
                continue
            owners = [owner for owner in entry["owners"] if owner != installation]
            if owners:
                entry["owners"] = owners
                report["kept_shared"].append(name)
                continue
            status = unlink_one(bindir, name, dry=dry)
            if status == "unlinked":
                report["unlinked"].append(name)
            links.pop(name, None)
        if not dry:
            _write_owners(bindir, data)
        if bindir.is_dir():
            for path in bindir.iterdir():
                name = path.name[:-4] if os.name == "nt" and path.name.lower().endswith(".cmd") else path.name
                if name not in desired and name not in booked:
                    report["unbooked"].append(path.name)
            if not dry and not any(bindir.iterdir()):
                bindir.rmdir()
    return report


def release_installation_links(bindir: Path, target: Path, *, dry: bool) -> dict:
    """Release only an explicitly named missing installation's D25 link claims."""
    report = {"released": [], "unlinked": [], "kept_shared": [],
              "legacy_preserved": []}
    installation = _installation_key(target)
    locked = nullcontext() if dry else shared_mutation_lock(bindir)
    with locked:
        data = _read_owners(bindir)
        for name, entry in list(data["links"].items()):
            if installation not in entry["owners"]:
                continue
            report["released"].append(name)
            owners = [owner for owner in entry["owners"] if owner != installation]
            if owners:
                entry["owners"] = owners
                report["kept_shared"].append(name)
                continue
            status = unlink_one(bindir, name, dry=dry)
            if status == "unlinked":
                report["unlinked"].append(name)
            data["links"].pop(name, None)
        if not dry:
            _write_owners(bindir, data)
    return report
