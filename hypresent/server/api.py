"""Pure handlers for the hypresent API — stdlib only, no HTTP logic."""

import os
import pathlib
import subprocess
import sys
import threading

# ---------------------------------------------------------------------------
# Shared-state callback
# ---------------------------------------------------------------------------
# server.py registers this callback so we can re-point the /doc/ root without
# importing server at the top level (avoids circular imports).
_set_doc_root = None

_open_path = {"path": None}


def set_open_path(p):
    _open_path["path"] = p


def get_open_path():
    return _open_path["path"]


def register_set_doc_root(fn):
    global _set_doc_root
    _set_doc_root = fn


# ---------------------------------------------------------------------------
# Native dialog launcher (injectable for tests)
# ---------------------------------------------------------------------------
_DIALOG_LOCK = threading.Lock()
_dialog_launcher = None  # tests set this via set_dialog_launcher


def set_dialog_launcher(fn):
    """Inject a fake launcher. fn(kind:str) -> path:str|None. kind in {'open','save'}."""
    global _dialog_launcher
    _dialog_launcher = fn


_OPEN_PS = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Filter = 'HTML files (*.html;*.htm)|*.html;*.htm|All files (*.*)|*.*'
$d.Title = 'Open Presentation'
$d.ShowHelp = $true
if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.FileName }
"""

_SAVE_PS = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.SaveFileDialog
$d.Filter = 'HTML files (*.html;*.htm)|*.html;*.htm|All files (*.*)|*.*'
$d.DefaultExt = 'html'
$d.OverwritePrompt = $true
$d.Title = 'Save As'
$d.ShowHelp = $true
if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.FileName }
"""


def _ps_args(exe, script):
    """Build the argv for a PowerShell dialog invocation (STA, no profile, non-interactive)."""
    return [exe, "-STA", "-NoProfile", "-NonInteractive", "-Command", script]


def _run_ps_dialog_default(kind):
    """Default launcher: spawn a PowerShell -STA dialog and return the chosen path or None.

    Tries PowerShell 7 (`pwsh`) first; if it is not installed (FileNotFoundError),
    falls back to inbox Windows PowerShell (`powershell.exe`). Both are invoked with
    identical flags: -STA -NoProfile -NonInteractive -Command <script>.
    """
    script = _OPEN_PS if kind == "open" else _SAVE_PS
    candidates = ["pwsh", "powershell.exe"] if sys.platform == "win32" else ["pwsh"]
    last_exc = None
    with _DIALOG_LOCK:
        for exe in candidates:
            try:
                r = subprocess.run(
                    _ps_args(exe, script),
                    capture_output=True, text=True, encoding="utf-8", timeout=300,
                )
            except FileNotFoundError as exc:
                last_exc = exc
                continue  # this PowerShell flavor is absent; try the next candidate
            path = (r.stdout or "").strip()
            return path if path else None
    # No PowerShell flavor was found at all.
    raise last_exc if last_exc is not None else FileNotFoundError("No PowerShell executable found")


def _launch_dialog(kind):
    fn = _dialog_launcher if _dialog_launcher is not None else _run_ps_dialog_default
    return fn(kind)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
def handle_open(payload):
    """Open an HTML file and point /doc/ at its parent directory.

    Returns a (status_int, response_dict) tuple.
    """
    path_str = payload.get("path")
    if not path_str:
        return (404, {"error": "Missing 'path'"})

    p = pathlib.Path(path_str)
    if not p.exists() or not p.is_file():
        return (404, {"error": f"File not found or not readable: {path_str}"})

    try:
        html = p.read_text(encoding="utf-8")
    except Exception as exc:
        return (500, {"error": f"Failed to read file: {exc}"})

    parent = p.parent.resolve()
    if _set_doc_root is not None:
        _set_doc_root(str(parent))

    set_open_path(str(p.resolve()))

    return (200, {
        "html": html,
        "dir": str(parent),
        "name": p.name,
    })


def handle_save_as(payload):
    """Save HTML string to an absolute path.

    Returns a (status_int, response_dict) tuple.
    """
    path_str = payload.get("path")
    html = payload.get("html")
    if path_str is None or html is None:
        return (500, {"error": "Missing 'path' or 'html'"})

    target = pathlib.Path(path_str)
    parent = target.parent

    # v1 has no allow-root restriction, but we only write if the parent
    # directory already exists (we do not auto-create missing directories).
    if not parent.exists():
        return (500, {"error": f"Parent directory does not exist: {parent}"})

    try:
        target.write_text(html, encoding="utf-8")
    except Exception as exc:
        return (500, {"error": str(exc)})

    return (200, {"ok": True, "path": path_str})


def handle_dialog_open():
    """Show a native open dialog; on selection delegate to handle_open."""
    try:
        path = _launch_dialog("open")
    except Exception as exc:
        return (500, {"error": f"Dialog failed: {exc}"})
    if not path:
        return (200, {"cancelled": True})
    return handle_open({"path": path})


def handle_dialog_save_as(payload):
    """Show a native save dialog; on confirm delegate to handle_save_as."""
    html = payload.get("html")
    if html is None:
        return (500, {"error": "Missing 'html'"})
    try:
        path = _launch_dialog("save")
    except Exception as exc:
        return (500, {"error": f"Dialog failed: {exc}"})
    if not path:
        return (200, {"cancelled": True})
    result = handle_save_as({"path": path, "html": html})
    # On a successful write, this path becomes the currently-open file.
    if result[0] == 200 and result[1].get("ok"):
        set_open_path(str(pathlib.Path(path).resolve()))
    return result


def handle_save(payload):
    """Silent overwrite of the currently-open file. If none open, signal fallback."""
    html = payload.get("html")
    if html is None:
        return (500, {"error": "Missing 'html'"})
    open_path = get_open_path()
    if not open_path:
        return (200, {"no_open_file": True})
    return handle_save_as({"path": open_path, "html": html})
