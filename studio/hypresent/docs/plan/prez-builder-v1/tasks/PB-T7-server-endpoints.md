You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate code by the exact strings quoted here, NEVER line numbers.

# PB-T7 — Builder server endpoints (new module + additive routes)

## Objective
Create a NEW server module `server/builder_api.py` with 4 handlers and wire 4 POST routes into `server/server.py` ADDITIVELY (existing routes untouched). Handlers shell out to the target library's vendored engine for parsing (ADX-2 — the server NEVER parses manifests itself). Stdlib only.

## FILE ALLOWLIST
- ✚ create `html/hypresent/server/builder_api.py`
- ✎ modify `html/hypresent/server/server.py` (ADD imports + 4 elif routes + 1 test-seam route only)
- ✗ nothing else.

## Live server contract you must match (facts)
Handlers return `(status_int, dict)` tuples; the router calls `self._send_json(status, resp)`. The existing `do_POST` dispatch in `server/server.py` is EXACTLY:
```python
    def do_POST(self):
        try:
            path = unquote(self.path.split("?", 1)[0])
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body) if body else {}

            if path == "/api/_test/set-dialog" and os.environ.get("HYP_TEST_DIALOG") == "1":
                # Test seam: install a fake dialog launcher returning a fixed path (or None).
                fake_path = payload.get("path")  # null => cancel
                api.set_dialog_launcher(lambda kind: fake_path)
                self._send_json(200, {"ok": True})
                return

            if path == "/api/open":
                status, resp = api.handle_open(payload)
                self._send_json(status, resp)
            elif path == "/api/save-as":
                status, resp = api.handle_save_as(payload)
                self._send_json(status, resp)
            elif path == "/api/dialog-open":
                status, resp = api.handle_dialog_open()
                self._send_json(status, resp)
            elif path == "/api/dialog-save-as":
                status, resp = api.handle_dialog_save_as(payload)
                self._send_json(status, resp)
            elif path == "/api/save":
                status, resp = api.handle_save(payload)
                self._send_json(status, resp)
            else:
                self._send_json(404, {"error": "Not found"})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})
```
The top of `server/server.py` imports api like this:
```python
try:
    from . import api
except ImportError:
    import api
```

### Your ONLY edits to server.py
(a) After the `api` import block above, add the SAME shape for the new module:
```python
try:
    from . import builder_api
except ImportError:
    import builder_api
```
(b) Inside `do_POST`, locate the block reading `elif path == "/api/save":` ... `self._send_json(status, resp)` and ADD these elif branches immediately after it (and before the `else:`):
```python
            elif path == "/api/dialog-folder":
                status, resp = builder_api.handle_dialog_folder()
                self._send_json(status, resp)
            elif path == "/api/library-load":
                status, resp = builder_api.handle_library_load(payload)
                self._send_json(status, resp)
            elif path == "/api/library-asset":
                status, resp = builder_api.handle_library_asset(payload)
                self._send_json(status, resp)
            elif path == "/api/assemble":
                status, resp = builder_api.handle_assemble(payload)
                self._send_json(status, resp)
```
(c) Add a folder-dialog test seam so e2e can inject a fake folder. Locate the block reading `if path == "/api/_test/set-dialog" and os.environ.get("HYP_TEST_DIALOG") == "1":` and add, IMMEDIATELY AFTER its closing `return`, a second seam:
```python
            if path == "/api/_test/set-folder-dialog" and os.environ.get("HYP_TEST_DIALOG") == "1":
                fake_path = payload.get("path")  # null => cancel
                builder_api.set_folder_dialog_launcher(lambda: fake_path)
                self._send_json(200, {"ok": True})
                return
```
Change NOTHING else in server.py. The existing 5 routes + the existing test seam stay byte-identical (build-spec S-B9.5 zero regression).

## builder_api.py — create the module
Stdlib only (`json, os, pathlib, subprocess, sys, threading`). Handlers return `(status_int, dict)`.

### Folder dialog (build-spec S-B9.1) — mirror the live file-dialog idiom
The live `server/api.py` spawns PowerShell file dialogs with a hidden TopMost owner Form, `-STA -NoProfile -NonInteractive -Command <script>`, `pwsh` then `powershell.exe` fallback, serialized by a `threading.Lock`, and supports an injectable launcher for tests. Reproduce that EXACT idiom for a FolderBrowserDialog:
```python
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
```

### Engine subprocess helper (ADX-2)
Pin `cwd=library_path` defensively (RV2-11): the engine resolves `LIBRARY = Path(__file__).resolve().parent` so cwd is not load-bearing today, but pinning it makes the subprocess's working directory deterministic and guards any future relative-path use in the engine.
```python
def _run_engine(library_path, args):
    """Run the library's vendored engine; return (returncode, stdout, stderr)."""
    engine = os.path.join(library_path, "assemble.py")
    if not os.path.isfile(engine):
        return (None, "", f"no assemble.py in library: {library_path}")
    proc = subprocess.run([sys.executable, engine, *args],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=library_path)
    return (proc.returncode, proc.stdout, proc.stderr)
```

### handle_library_load (build-spec S-B9.2) — passthrough of the engine envelope
```python
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
```

### handle_library_asset (build-spec S-B9.3) — serve theme.css / slides/{id}.html for previews, with a traversal guard
Mirror the live `_serve_static` traversal guard (reject `..` components; ensure the resolved path stays inside the library root):
```python
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
```

### handle_assemble (build-spec S-B9.4) — passthrough of the engine assemble envelope
```python
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
```

## Acceptance criteria (self-verifiable)
1. `python -c "import importlib.util; spec=importlib.util.spec_from_file_location('b', r'html/hypresent/server/builder_api.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('OK', bool(m.handle_assemble) and bool(m.handle_library_load))"` prints `OK True`.
2. `python -c "import ast; ast.parse(open(r'html/hypresent/server/server.py',encoding='utf-8').read()); print('server.py parses')"` succeeds.
3. Confirm `server/server.py` still contains the exact strings `elif path == "/api/save":` and `elif path == "/api/dialog-save-as":` (existing routes intact) AND now contains `elif path == "/api/assemble":` and `if path == "/api/_test/set-folder-dialog"`.
4. Smoke the library-load + assemble path WITHOUT a dialog: copy the fixture library + shared-brand into a temp parent, copy `html/slide-library/engine/assemble.py` into the temp `fixture-library/`, start the server (port 8807), `curl -s -X POST http://127.0.0.1:8807/api/library-load -H "Content-Type: application/json" -d "{\"path\":\"<temp fixture-library abs path>\"}"` → response JSON has `ok` and `catalog_data` with 9 slides. Then POST `/api/assemble` with `{path, slides:["cover-nimbus.en","closing-nimbus"], out:"<tmp>/d.html"}` → response has `ok:true`, `output`, `assets_copied`; and `<tmp>/d.html` exists on disk. Stop the server. (If the engine/fixture are not present, SKIP this probe with the exact reason string.)

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/builder-endpoints-result.md`: the 4 probe results + `git status --porcelain html/hypresent/server/`.

DONE means: module created, server.py edited additively, probes 1–3 pass, probe 4 passes if engine+fixture present (else noted), evidence written. Failure → BLOCKED + stop.
