"""Builder API handlers — stdlib only.

Handlers shell out to the slide-library engine; the server never parses manifests.
"""

import json
import os
import pathlib
import subprocess
import sys
import threading

# ---------------------------------------------------------------------------
# Folder dialog (build-spec S-B9.1) — mirror the live file-dialog idiom
# ---------------------------------------------------------------------------
_FOLDER_LOCK = threading.Lock()
_folder_dialog_launcher = None  # tests inject via set_folder_dialog_launcher


def set_folder_dialog_launcher(fn):
    """Inject a fake launcher fn() -> path:str|None."""
    global _folder_dialog_launcher
    _folder_dialog_launcher = fn


_FOLDER_PS = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.WindowState = 'Minimized'
$owner.Opacity = 0
$owner.Show()
try {
  $d = New-Object System.Windows.Forms.FolderBrowserDialog
  $d.Description = 'Select slide library folder'
  if ($d.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.SelectedPath }
} finally {
  $owner.Close()
  $owner.Dispose()
}
"""


def _run_folder_dialog_default():
    candidates = ["pwsh", "powershell.exe"] if sys.platform == "win32" else ["pwsh"]
    last_exc = None
    with _FOLDER_LOCK:
        for exe in candidates:
            try:
                r = subprocess.run([exe, "-STA", "-NoProfile", "-NonInteractive", "-Command", _FOLDER_PS],
                                   capture_output=True, text=True, encoding="utf-8", timeout=300)
            except FileNotFoundError as exc:
                last_exc = exc
                continue
            path = (r.stdout or "").strip()
            return path if path else None
    raise last_exc if last_exc is not None else FileNotFoundError("No PowerShell executable found")


def _launch_folder_dialog():
    fn = _folder_dialog_launcher if _folder_dialog_launcher is not None else _run_folder_dialog_default
    return fn()


def handle_dialog_folder():
    try:
        path = _launch_folder_dialog()
    except Exception as exc:
        return (500, {"error": f"Dialog failed: {exc}"})
    if not path:
        return (200, {"cancelled": True})
    return (200, {"path": path})


# ---------------------------------------------------------------------------
# Engine subprocess helper (ADX-2)
# ---------------------------------------------------------------------------
def _run_engine(library_path, args):
    """Run the library's vendored engine; return (returncode, stdout, stderr)."""
    engine = os.path.join(library_path, "assemble.py")
    if not os.path.isfile(engine):
        return (None, "", f"no assemble.py in library: {library_path}")
    proc = subprocess.run([sys.executable, engine, *args],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=library_path)
    return (proc.returncode, proc.stdout, proc.stderr)


# ---------------------------------------------------------------------------
# handle_library_load (build-spec S-B9.2) — passthrough of the engine envelope
# ---------------------------------------------------------------------------
def handle_library_load(payload):
    path = payload.get("path")
    if not path:
        return (500, {"error": "Missing 'path'"})
    rc, out, err = _run_engine(path, ["--catalog-data", "--json"])
    if rc is None:
        return (500, {"error": err})
    try:
        envelope = json.loads(out)
    except Exception:
        return (500, {"error": f"engine did not return JSON: {err or out[:200]}"})
    return (200, envelope)  # ok:false (invalid library) passes through as 200; the GUI shows it


# ---------------------------------------------------------------------------
# handle_library_asset (build-spec S-B9.3) — serve theme.css / slides/{id}.html
# ---------------------------------------------------------------------------
def handle_library_asset(payload):
    path = payload.get("path"); name = payload.get("name")
    if not path or not name:
        return (500, {"error": "Missing 'path' or 'name'"})
    if ".." in name.replace("\\", "/").split("/"):
        return (400, {"error": "Invalid name"})
    root = pathlib.Path(path).resolve()
    target = (root / name).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return (400, {"error": "Path traversal blocked"})
    if not target.is_file():
        return (404, {"error": f"Not found: {name}"})
    return (200, {"content": target.read_text(encoding="utf-8")})


# ---------------------------------------------------------------------------
# handle_assemble (build-spec S-B9.4) — passthrough of the engine assemble envelope
# ---------------------------------------------------------------------------
def handle_assemble(payload):
    path = payload.get("path"); slides = payload.get("slides"); out = payload.get("out")
    if not path or not slides or not out:
        return (500, {"error": "Missing 'path', 'slides', or 'out'"})
    args = ["--slides", ",".join(slides), "--out", out, "--json"]
    for flag, key in (("--lang","lang"),("--title","title"),("--accent","accent"),("--client-logo","client_logo")):
        if payload.get(key):
            args += [flag, payload[key]]
    rc, eout, err = _run_engine(path, args)
    if rc is None:
        return (500, {"error": err})
    try:
        envelope = json.loads(eout)
    except Exception:
        return (500, {"error": f"engine did not return JSON: {err or eout[:200]}"})
    return (200, envelope)  # engine ok:false passes through
