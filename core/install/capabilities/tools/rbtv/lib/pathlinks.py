"""The ~/.rbtv/bin shortcut links and user shell PATH setup.

POSIX: each shortcut is a bare symlink; the kernel honours the target's
shebang. Windows has no shebang layer and an extensionless name is not
executable, so there each shortcut is a generated `<name>.cmd` shim — a
regular file (no symlink privilege needed) that spawns the interpreter the
target's shebang names. Interpreter resolution follows the decisions
delegate.js winShebang settled (memory 20260824-i-rbtv-direct-delegates-
unrunnab): `python3` is not a name on a stock Windows PATH (spawn `python`),
and PATH `bash` is usually WSL's, which cannot see `C:` paths (spawn git's
own bash, with the script path forward-slashed).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from discovery import Refuse

from .constants import (
    PATH_BOOTSTRAP,
    LEGACY_PATH_FENCE,
    PATH_FENCE_END,
    PATH_FENCE_START,
    STATE_REL,
    WS_PREFIX,
    _RUNTIME,
)
from .fsio import write_file
from .target import is_user_home

_WIN = os.name == "nt"

# First line of every shim — the ownership marker (D12: ownership is a marker
# in the file) AND the recorded target, standing in for readlink().
_SHIM_MARK = "@rem rbtv-shim -> "


def local_bin() -> Path:
    override = _RUNTIME.get("local")
    return Path(override) if override is not None else Path.home() / ".local" / "bin"


def bin_dir() -> Path:
    override = _RUNTIME.get("bin")
    return Path(override) if override is not None else Path.home() / ".rbtv" / "bin"


def shell_profiles() -> tuple[Path, ...]:
    override = _RUNTIME.get("rc")
    if override is not None:
        return (Path(override),)
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if shell.endswith("zsh"):
        return home / ".zshrc", home / ".zprofile"
    login = next((home / name for name in
                  (".bash_profile", ".bash_login", ".profile")
                  if (home / name).is_file()), home / ".profile")
    return home / ".bashrc", login


def link_path(bindir: Path, name: str) -> Path:
    """Where the shortcut for `name` lives: `<name>.cmd` on Windows."""
    return bindir / (name + ".cmd") if _WIN else bindir / name


def _win_bash() -> str:
    """Git's bash, resolved through git's own install — PATH order is what
    produces WSL's bash, which exits 127 on any Windows script path."""
    try:
        out = subprocess.run(["where", "git"], capture_output=True,
                             text=True, timeout=15)
    except OSError:
        return "bash"
    for line in (out.stdout or "").splitlines():
        bash = Path(line.strip()).parent.parent / "bin" / "bash.exe"
        if bash.is_file():
            return str(bash)
    return "bash"


def _win_interp(dest: Path) -> str:
    try:
        head = dest.read_bytes()[:256].decode("utf-8", "replace")
    except OSError:
        head = ""
    name = ""
    if head.startswith("#!"):
        parts = head.splitlines()[0][2:].strip().split()
        if parts:
            name = Path(parts[0]).name
            if name == "env" and len(parts) > 1:
                name = parts[1]
    if not name:
        name = {".py": "python3", ".js": "node",
                ".sh": "bash"}.get(dest.suffix.lower(), "")
    if name in ("python3", "python"):
        return "python"
    if name in ("bash", "sh"):
        return _win_bash()
    if name:
        return name
    raise Refuse("path-link-failed",
                 f"no interpreter for {dest} — no shebang and no known "
                 "extension", str(dest))


def _shim_text(dest: Path) -> str:
    interp = _win_interp(dest)
    arg = str(dest)
    if Path(interp).name.lower() in ("bash.exe", "bash", "sh"):
        arg = arg.replace("\\", "/")
    return f'{_SHIM_MARK}{dest}\n@"{interp}" "{arg}" %*\n'


def _sh_text(dest: Path) -> str:
    """The extensionless twin of a `.cmd` shim: git bash resolves only the
    exact name, never `<name>.cmd`, so without it agents in bash see nothing."""
    interp = _win_interp(dest).replace("\\", "/")
    return (f"#!/bin/sh\n# rbtv-shim -> {dest}\n"
            f'exec "{interp}" "{str(dest).replace(chr(92), "/")}" "$@"\n')


def _sh_twin(path: Path) -> Path | None:
    """The bash twin beside a Windows `.cmd` shim; None off Windows."""
    return path.with_suffix("") if _WIN and path.suffix.lower() == ".cmd" \
        else None


def _twin_owned(twin: Path) -> bool:
    try:
        return twin.read_text(encoding="utf-8").splitlines()[1] \
            .startswith("# rbtv-shim -> ")
    except (OSError, IndexError, UnicodeDecodeError):
        return False


def _twin_foreign(path: Path) -> bool:
    twin = _sh_twin(path)
    return (twin is not None and twin.exists() and not twin.is_symlink()
            and not _twin_owned(twin))


def _shim_target(path: Path) -> Path | None:
    if not _WIN or path.suffix.lower() != ".cmd" or not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            first = fh.readline()
    except OSError:
        return None
    if first.startswith(_SHIM_MARK):
        return Path(first[len(_SHIM_MARK):].strip())
    return None


def _owned(path: Path) -> bool:
    """Ours: a symlink, or a shim carrying our marker line."""
    return path.is_symlink() or _shim_target(path) is not None


def _forbid_local_bin(bindir: Path) -> None:
    try:
        if bindir.resolve() == (Path.home() / ".local" / "bin").resolve():
            raise Refuse("path-forbidden",
                         "rbtv never touches ~/.local/bin",
                         str(bindir))
    except OSError:
        return


def installation_root(start: Path) -> Path:
    here = start.resolve()
    for p in (here, *here.parents):
        if (p / STATE_REL).is_file() or (
                (p / ".rbtv" / "config").is_dir() and not is_user_home(p)):
            return p
    return here


def resolve_path_entry(target: Path, comp_dir: Path, entry: str) -> Path:
    """The program a tool places on PATH: its entry, relative to the component,
    or `ws:` and a path from the installation root."""
    if entry.startswith(WS_PREFIX):
        dest = installation_root(target) / entry[len(WS_PREFIX):]
    else:
        dest = comp_dir / entry
    if dest.exists():
        dest = dest.resolve()
    if not dest.is_file():
        raise Refuse("entry-point-missing",
                     f"{entry!r} resolves to no file", str(dest))
    return dest


def link_name(pid: str) -> str:
    name = (pid or "").strip()
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise Refuse("path-name-invalid", f"tool name {pid!r} is not a PATH name")
    return name


def link_points_at(link: Path, dest: Path) -> bool:
    try:
        if link.is_symlink():
            return link.readlink() == dest or link.resolve() == dest.resolve()
        # Shim: whole-text compare, so an interpreter change (edited shebang)
        # also reads as stale and gets relinked. A missing bash twin is stale
        # too, which is how pre-twin installs heal on the next run.
        twin = _sh_twin(link)
        if twin is not None and (not twin.is_file() or
                                 twin.read_bytes().decode("utf-8")
                                 != _sh_text(dest)):
            return False
        return link.read_text(encoding="utf-8") == _shim_text(dest)
    except (OSError, Refuse):
        return False


def _make_link(path: Path, dest: Path) -> None:
    try:
        if _WIN:
            twin = _sh_twin(path)
            if _twin_foreign(path):
                raise Refuse("path-collision",
                             f"{twin} exists and is not ours", str(twin))
            write_file(path, _shim_text(dest))
            if twin.is_symlink():
                twin.unlink()
            # Bytes, not text: text mode would write CRLF, which sh rejects.
            write_file(twin, _sh_text(dest).encode("utf-8"))
        else:
            path.symlink_to(dest)
    except OSError as exc:
        raise Refuse("path-link-failed",
                     f"could not link {path} -> {dest}: {exc}",
                     str(path)) from exc


def link_one(bindir: Path, name: str, dest: Path, *, dry: bool) -> str:
    """ok | linked | relinked. Refuse path-collision on a file not ours."""
    _forbid_local_bin(bindir)
    path = link_path(bindir, name)
    if _WIN and not dry:
        # A bare symlink at the unsuffixed name is a leftover from a POSIX-
        # style run on this machine — inert (not executable) but clutter.
        stale = bindir / name
        if stale.is_symlink():
            stale.unlink()
    if _owned(path):
        if link_points_at(path, dest):
            return "ok"
        if dry:
            return "relinked"
        path.unlink()
        _make_link(path, dest)
        return "relinked"
    if path.exists():
        raise Refuse("path-collision",
                     f"{path} exists and is not ours",
                     str(path))
    if dry:
        return "linked"
    bindir.mkdir(parents=True, exist_ok=True)
    _make_link(path, dest)
    return "linked"


def unlink_one(bindir: Path, name: str, *, dry: bool) -> str:
    """gone | unlinked. A foreign file at a booked name is left (path-collision)."""
    _forbid_local_bin(bindir)
    path = link_path(bindir, name)
    if not path.exists() and not path.is_symlink():
        return "gone"
    if not _owned(path):
        raise Refuse("path-collision",
                     f"{path} is not ours — refusing to delete a file "
                     "rbtv did not create", str(path))
    if not dry:
        path.unlink()
        twin = _sh_twin(path)
        if twin is not None and twin.is_file() and _twin_owned(twin):
            twin.unlink()
    return "unlinked"


def plan_path_links(target: Path,
                    rows: list[tuple[str, str, Path, str]]
                    ) -> tuple[dict[str, Path], dict[str, tuple[str, str]]]:
    """rows = (component_id, unit_id, comp_dir, entry). One name → one dest."""
    desired: dict[str, Path] = {}
    owners: dict[str, tuple[str, str]] = {}
    seen: dict[str, str] = {}
    for cid, pid, comp_dir, entry in rows:
        name = link_name(pid)
        dest = resolve_path_entry(target, comp_dir, entry)
        # The shebang is required on every system: a program Windows would
        # run by its extension alone cannot run on Linux (owner ruling, unit 7).
        try:
            with dest.open("rb") as fh:
                shebang = fh.read(2) == b"#!"
        except OSError as exc:
            raise Refuse("path-not-runnable",
                         f"{name}: cannot read {dest}: {exc}",
                         str(dest)) from exc
        if not shebang:
            raise Refuse("path-not-runnable",
                         f"{name}: {dest} needs a shebang (#!) first line — "
                         "every system requires it", str(dest))
        if _WIN:
            _win_interp(dest)
        elif not os.access(dest, os.X_OK):
            raise Refuse("path-not-runnable",
                         f"{name}: {dest} needs execute permission", str(dest))
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
        for part in (rec.get("units") or {}).values():
            if isinstance(part, dict):
                names.update(part.get("links") or [])
    return names


def gate_path_links(bindir: Path, desired: dict[str, Path],
                    drop: set[str]) -> None:
    """Refuse path-collision before any write (D6)."""
    _forbid_local_bin(bindir)
    for name in sorted(desired):
        path = link_path(bindir, name)
        if path.exists() and not _owned(path):
            raise Refuse("path-collision",
                         f"{path} exists and is not ours",
                         str(path))
        if _twin_foreign(path):
            raise Refuse("path-collision",
                         f"{_sh_twin(path)} exists and is not ours",
                         str(path))
    for name in sorted(drop):
        path = link_path(bindir, name)
        if (path.exists() or path.is_symlink()) and not _owned(path):
            raise Refuse("path-collision",
                         f"{path} is not ours — refusing to delete a file "
                         "rbtv did not create", str(path))


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
            name = p.name[:-4] if _WIN and p.name.lower().endswith(".cmd") \
                else p.name
            if name not in desired and name not in booked and name not in keep:
                report["unbooked"].append(p.name)
        if not dry and not any(bindir.iterdir()):
            bindir.rmdir()
    return report


def _write_shell_path() -> None:
    if _WIN and _RUNTIME.get("rc") is None:
        _write_windows_user_path()
        return
    block = f"{PATH_FENCE_START}\n{PATH_BOOTSTRAP}\n{PATH_FENCE_END}\n"
    for rc in shell_profiles():
        text = rc.read_text(encoding="utf-8") if rc.is_file() else ""
        fence = next(((a, b) for a, b in
                      ((PATH_FENCE_START, PATH_FENCE_END), LEGACY_PATH_FENCE)
                      if a in text and b in text), None)
        if fence:
            head = text.split(fence[0], 1)[0]
            tail = text.split(fence[1], 1)[1].lstrip("\n")
            text = head + block + tail
        else:
            text = (text.rstrip() + "\n\n" if text.strip() else "") + block
        rc.parent.mkdir(parents=True, exist_ok=True)
        write_file(rc, text)


def _write_windows_user_path() -> None:
    """Persist PATH for PowerShell, cmd.exe and Git Bash without setx truncation."""
    import ctypes
    import winreg

    entry = str(bin_dir())
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, "Environment", 0,
                            winreg.KEY_READ | winreg.KEY_WRITE) as key:
        try:
            current, kind = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, kind = "", winreg.REG_EXPAND_SZ
        if any(unit.strip('"').replace("/", "\\").casefold()
               == entry.replace("/", "\\").casefold()
               for unit in current.split(";")):
            return
        winreg.SetValueEx(key, "Path", 0, kind,
                          current.rstrip(";") + ";" + entry if current else entry)
    # Tell the desktop to pass the updated user environment to new terminals.
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0,
                                              "Environment", 0x0002, 5000, None)


def _path_rows_from_report(report: dict) -> list[tuple[str, str, Path, str]]:
    return [(r["component"], r["part"], Path(r["comp_dir"]), r["entry_point"])
            for r in report.get("path_rows") or []]
