"""The ~/.rbtv/bin shortcut links and the one PATH line in the shell
profile.

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
    PATH_FENCE_END,
    PATH_FENCE_START,
    WS_PREFIX,
    _RUNTIME,
)

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


def shell_rc() -> Path:
    override = _RUNTIME.get("rc")
    if override is not None:
        return Path(override)
    if _WIN:
        return _powershell_profile()
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if shell.endswith("zsh"):
        return home / ".zshrc"
    return home / ".bashrc"


def _powershell_profile() -> Path:
    """$PROFILE as PowerShell itself reports it — Documents may be
    OneDrive-redirected, so guessing the path is wrong on real machines."""
    for exe in ("pwsh", "powershell"):
        try:
            out = subprocess.run([exe, "-NoProfile", "-Command", "$PROFILE"],
                                 capture_output=True, text=True, timeout=15)
        except OSError:
            continue
        line = (out.stdout or "").strip()
        if out.returncode == 0 and line:
            return Path(line)
    return (Path.home() / "Documents" / "PowerShell"
            / "Microsoft.PowerShell_profile.ps1")


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


def link_points_at(link: Path, dest: Path) -> bool:
    try:
        if link.is_symlink():
            return link.readlink() == dest or link.resolve() == dest.resolve()
        # Shim: whole-text compare, so an interpreter change (edited shebang)
        # also reads as stale and gets relinked.
        return link.read_text(encoding="utf-8") == _shim_text(dest)
    except (OSError, Refuse):
        return False


def _make_link(path: Path, dest: Path) -> None:
    try:
        if _WIN:
            path.write_text(_shim_text(dest), encoding="utf-8")
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
        path = link_path(bindir, name)
        if path.exists() and not _owned(path):
            raise Refuse("path-collision",
                         f"{path} exists and is not ours",
                         str(path))
    for name in sorted(drop):
        path = link_path(bindir, name)
        if (path.exists() or path.is_symlink()) and not _owned(path):
            raise Refuse("path-collision",
                         f"{path} is not ours — refusing to delete a file "
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
            name = p.name[:-4] if _WIN and p.name.lower().endswith(".cmd") \
                else p.name
            if name not in desired and name not in booked and name not in keep:
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
