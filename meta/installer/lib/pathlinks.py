"""The ~/.rbtv/bin shortcut links and the one PATH line in the shell
profile.
"""
from __future__ import annotations

import os
from pathlib import Path

from discovery import Refuse

from .constants import (
    PATH_BOOTSTRAP,
    PATH_FENCE_END,
    PATH_FENCE_START,
    WS_PREFIX,
    _RUNTIME,
)


def local_bin() -> Path:
    override = _RUNTIME.get("local")
    return Path(override) if override is not None else Path.home() / ".local" / "bin"


def bin_dir() -> Path:
    override = _RUNTIME.get("bin")
    return Path(override) if override is not None else Path.home() / ".rbtv" / "bin"


def shell_rc() -> Path:
    override = _RUNTIME.get("rc")
    if override is not None:
        return Path(override)
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if shell.endswith("zsh"):
        return home / ".zshrc"
    return home / ".bashrc"


def _forbid_local_bin(bindir: Path) -> None:
    try:
        if bindir.resolve() == (Path.home() / ".local" / "bin").resolve():
            raise Refuse("path-forbidden",
                         "this installer never touches ~/.local/bin",
                         str(bindir))
    except OSError:
        return


def workspace_root(start: Path) -> Path:
    here = start.resolve()
    for p in (here, *here.parents):
        if (p / ".rbtv" / "config").is_dir():
            return p
    return here


def resolve_path_entry(target: Path, comp_dir: Path, entry: str) -> Path:
    raw = (entry or "").split("#", 1)[0].strip()
    if not raw:
        raise Refuse("entry-point-missing", "path row declares no entry-point")
    if raw.startswith(WS_PREFIX):
        body = raw[len(WS_PREFIX):]
        dest = workspace_root(target) / body
    else:
        body = raw
        dest = comp_dir / body
    if Path(body).is_absolute() or ".." in Path(body).parts:
        raise Refuse("entry-point-escape",
                     f"entry-point {raw!r} climbs with .. — use ws:<path>",
                     str(comp_dir))
    if dest.exists():
        dest = dest.resolve()
    if not dest.is_file():
        raise Refuse("entry-point-missing",
                     f"{raw!r} resolves to no file", str(dest))
    return dest


def link_name(pid: str) -> str:
    name = (pid or "").strip()
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise Refuse("path-name-invalid", f"part-id {pid!r} is not a PATH name")
    return name


def _points_at(link: Path, dest: Path) -> bool:
    try:
        return link.readlink() == dest or link.resolve() == dest.resolve()
    except OSError:
        return False


def link_one(bindir: Path, name: str, dest: Path, *, dry: bool) -> str:
    """ok | linked | relinked. Refuse path-collision on a non-symlink."""
    _forbid_local_bin(bindir)
    path = bindir / name
    if path.is_symlink():
        if _points_at(path, dest):
            return "ok"
        if dry:
            return "relinked"
        path.unlink()
        try:
            path.symlink_to(dest)
        except OSError as exc:
            raise Refuse("path-link-failed",
                         f"could not link {path} -> {dest}: {exc}",
                         str(path)) from exc
        return "relinked"
    if path.exists():
        raise Refuse("path-collision",
                     f"{path} exists and is not a symlink — not ours",
                     str(path))
    if dry:
        return "linked"
    bindir.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(dest)
    except OSError as exc:
        raise Refuse("path-link-failed",
                     f"could not link {path} -> {dest}: {exc}",
                     str(path)) from exc
    return "linked"


def unlink_one(bindir: Path, name: str, *, dry: bool) -> str:
    """gone | unlinked. A non-symlink at a booked name is left (path-collision)."""
    _forbid_local_bin(bindir)
    path = bindir / name
    if not path.exists() and not path.is_symlink():
        return "gone"
    if not path.is_symlink():
        raise Refuse("path-collision",
                     f"{path} is not a symlink — refusing to delete a file "
                     "this installer did not create", str(path))
    if not dry:
        path.unlink()
    return "unlinked"


def plan_path_links(target: Path,
                    rows: list[tuple[str, str, Path, str]]
                    ) -> tuple[dict[str, Path], dict[str, tuple[str, str]]]:
    """rows = (component_id, part_id, comp_dir, entry). One name → one dest."""
    desired: dict[str, Path] = {}
    owners: dict[str, tuple[str, str]] = {}
    seen: dict[str, str] = {}
    for cid, pid, comp_dir, entry in rows:
        name = link_name(pid)
        dest = resolve_path_entry(target, comp_dir, entry)
        if name in desired and desired[name] != dest:
            raise Refuse("path-name-collision",
                         f"{name} claimed by {seen[name]} and {cid} "
                         f"({desired[name]} vs {dest}) — whole run", name)
        desired[name] = dest
        owners[name] = (cid, pid)
        seen[name] = cid
    return desired, owners


def booked_path_names(state: dict) -> set[str]:
    names: set[str] = set()
    for rec in (state.get("components") or {}).values():
        names.update(rec.get("path_links") or [])
        for part in (rec.get("parts") or {}).values():
            if isinstance(part, dict):
                names.update(part.get("links") or [])
    return names


def gate_path_links(bindir: Path, desired: dict[str, Path],
                    drop: set[str]) -> None:
    """Refuse path-collision before any write (D6)."""
    _forbid_local_bin(bindir)
    for name in sorted(desired):
        path = bindir / name
        if path.exists() and not path.is_symlink():
            raise Refuse("path-collision",
                         f"{path} exists and is not a symlink — not ours",
                         str(path))
    for name in sorted(drop):
        path = bindir / name
        if (path.exists() or path.is_symlink()) and not path.is_symlink():
            raise Refuse("path-collision",
                         f"{path} is not a symlink — refusing to delete a file "
                         "this installer did not create", str(path))


def reconcile(bindir: Path, desired: dict[str, Path], booked: set[str],
              *, dry: bool, keep: set[str] | None = None) -> dict:
    """Create/repair desired; unlink booked-but-not-desired. Leave the rest."""
    keep = set(keep or ())
    report = {"linked": [], "relinked": [], "ok": [], "unlinked": [],
              "unbooked": [], "dangling": []}
    _forbid_local_bin(bindir)
    if not dry:
        bindir.mkdir(parents=True, exist_ok=True)
    for name, dest in sorted(desired.items()):
        if not dest.is_file():
            report["dangling"].append(name)
            raise Refuse("entry-point-missing",
                         f"PATH target for {name} is gone: {dest}", str(dest))
        st = link_one(bindir, name, dest, dry=dry)
        report[st].append(name)
    for name in sorted(booked - set(desired) - keep):
        report["unlinked"].append(name)
        unlink_one(bindir, name, dry=dry)
    if bindir.is_dir():
        for p in bindir.iterdir():
            if p.name not in desired and p.name not in booked and p.name not in keep:
                report["unbooked"].append(p.name)
        if not dry and not any(bindir.iterdir()):
            bindir.rmdir()
    return report


def _write_shell_path() -> None:
    rc = shell_rc()
    block = f"{PATH_FENCE_START}\n{PATH_BOOTSTRAP}\n{PATH_FENCE_END}\n"
    text = rc.read_text(encoding="utf-8") if rc.is_file() else ""
    if PATH_FENCE_START in text and PATH_FENCE_END in text:
        head = text.split(PATH_FENCE_START, 1)[0]
        tail = text.split(PATH_FENCE_END, 1)[1].lstrip("\n")
        text = head + block + tail
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + block
    rc.parent.mkdir(parents=True, exist_ok=True)
    rc.write_text(text, encoding="utf-8")


def _remove_shell_path() -> None:
    rc = shell_rc()
    if not rc.is_file():
        return
    text = rc.read_text(encoding="utf-8")
    if PATH_FENCE_START not in text or PATH_FENCE_END not in text:
        return
    head = text.split(PATH_FENCE_START, 1)[0]
    tail = text.split(PATH_FENCE_END, 1)[1].lstrip("\n")
    new = (head.rstrip() + "\n" + tail) if head.strip() else tail
    rc.write_text(new, encoding="utf-8")


def _path_rows_from_report(report: dict) -> list[tuple[str, str, Path, str]]:
    return [(r["component"], r["part"], Path(r["comp_dir"]), r["entry_point"])
            for r in report.get("path_rows") or []]
