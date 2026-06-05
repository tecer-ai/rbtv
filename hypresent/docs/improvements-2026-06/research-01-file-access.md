# Research 01 — Native File Dialog for Hypresent

**Date:** 2026-06-03
**Scope:** Replace the current absolute-path text input with a native file picker dialog.
**App context:** Python stdlib `ThreadingHTTPServer` on `127.0.0.1:8765`; parent shell + same-origin iframe; Chrome on Windows 11; single user, server and browser on the same machine.

---

## Architecture A — Browser File System Access API

### A1. Secure-Context Status on `http://127.0.0.1`

Both `http://127.0.0.1` and `http://localhost` are "potentially trustworthy origins" per the W3C Secure Contexts specification [1]. The spec states explicitly: "Locally-delivered resources such as those with `http://127.0.0.1` … are not delivered using HTTPS, but they can be considered to have been delivered securely because they are on the same device as the browser." Chrome implements this — `http://127.0.0.1:8765` qualifies as a secure context and `showOpenFilePicker` / `showSaveFilePicker` are available without HTTPS. [2]

**Analysis:** No TLS setup required for this app.

### A2. User-Gesture Requirement

Both picker methods require **transient user activation** — they must be called synchronously from within a click (or equivalent) event handler [3]. Calling them from async callbacks, timers, or after `await` breaks the activation chain and throws `SecurityError: Must be handling a user gesture to show a file picker`. The existing Open button click handler in `file-controls.js` is already the correct insertion point. Save-As works analogously.

### A3. File Type Accept Filter for `.html`

```javascript
const opts = {
  types: [{ description: 'HTML files', accept: { 'text/html': ['.html'] } }],
  excludeAcceptAllOption: false,
};
const [handle] = await window.showOpenFilePicker(opts);
```

Chrome renders this as a native filter dropdown in the dialog [4].

### A4. AbortError / Cancel Handling

When the user dismisses the dialog without selecting, a `DOMException` with `name === 'AbortError'` is thrown. The same error fires if the browser judges any selected file too sensitive. Correct handling:

```javascript
try {
  const [handle] = await window.showOpenFilePicker(opts);
} catch (err) {
  if (err.name === 'AbortError') return; // user cancelled — silent
  throw err; // re-throw unexpected errors
}
```

### A5. Handle Reuse for Silent Re-Save ("Save")

After the first `showSaveFilePicker` call, store the returned `FileSystemFileHandle` in memory. Subsequent "Save" (not "Save As") operations call `handle.createWritable()` directly — no dialog appears, no re-prompt, because write permission was already granted [4][5].

Permission persists until the last tab for the origin is closed. As of Chrome 122, users can optionally grant **persistent permission** ("Allow on every visit"), surviving tab/session close; this stores the handle in IndexedDB and re-requests permission on next open without a picker [5].

**Analysis:** Silent re-save fully supported. For Hypresent's use case (single user, localhost) the in-memory handle is sufficient; IndexedDB persistence is a free future enhancement.

### A6. The Critical Constraint: No Absolute Path Exposed

**The File System Access API deliberately does not expose the real on-disk path of a selected file.** [6][7] `FileSystemFileHandle` has no `.path` property. The spec's position (WICG issue #145, now closed) is that exposing paths would leak filesystem structure and enable malware enumeration; this will not change [7].

**Why this breaks the current Hypresent architecture:**

The current open flow (recon.md §4) is:
1. Client POSTs `{path: absolutePathString}` to `/api/open`
2. Server reads the file and — critically — calls `set_doc_root(file.parent)`, re-pointing `/doc/` to serve the document's parent directory
3. Client sets `iframe.src = '/doc/' + filename`, so the browser fetches the HTML **via the server**
4. All `<link href="style.css">`, `<img src="images/banner.png">` etc. in the document resolve against `/doc/`, which the server serves from the real directory

Without an absolute path, step 1 cannot happen as designed. The file content can be read using `handle.getFile()` → `file.text()`, but the server never learns the directory, so `/doc/` cannot be re-pointed, and relative assets in the document (`<link>`, `<img>`, `<script>`) will 404.

**Known workaround attempts and why they fail for this app:**

| Workaround | What breaks |
|------------|-------------|
| Inject HTML as `iframe.srcdoc` | Relative asset URLs in the document resolve against the parent page origin (`/`), not a filesystem directory. `<link href="fonts/foo.css">` becomes a request to `/fonts/foo.css` on the server — 404 unless the document happens to have no relative assets. The sample fixture `tecer-gsmm-introduction.html` uses CDN URLs only, so it would work today, but this is an architectural assumption the editor cannot make. |
| Create a `Blob URL` for the HTML, set `iframe.src` to it | Same problem: blob URL origin is `null` for cross-origin or opaque, and relative URLs resolve against nothing useful. Relative assets still 404. |
| `showDirectoryPicker` — user picks the directory, client reads both directory handle and file handle | Client can enumerate and read the directory's files in-browser. But to serve them over HTTP via `/doc/`, the server still needs the real path. The API does not expose it from a directory handle either. Possible workaround: client re-uploads every asset file to the server via a new `/api/serve-asset` endpoint. This is a significant architectural change: the client would need to enumerate all relative assets referenced by the document, read each one via the directory handle, and POST them to the server before setting `iframe.src`. Correctness is hard (CSS `@import`, lazy-loaded images, nested references) and the approach is fragile. |
| Service Worker intercept | A service worker could intercept `/doc/asset.png` requests and fulfill them from an in-memory cache populated from directory handle reads. Functionally equivalent to the re-upload approach, with additional complexity. Requires service worker registration at `http://127.0.0.1:8765`, which requires a localhost-scoped registration, feasible in Chrome but adds a non-trivial deployment step. |

**Summary of A's constraint:** Architecture A provides a native open/save dialog but severs the server's ability to know the file's directory, which is load-bearing for relative-asset serving via `/doc/`. Restoring relative-asset functionality requires one of the complex workarounds above, each of which either has correctness gaps or adds significant code.

### A7. `browser-fs-access` Wrapper

GoogleChromeLabs `browser-fs-access` [8] wraps the native API with an `<input type=file>` fallback for non-supporting browsers. Latest release: **v0.38.0** (June 2024). Maintenance is minimal — 3 releases in 2024, none visible in 2025-2026 [8]. For Hypresent the fallback is useless (Chrome-only, localhost), and the wrapper adds no value this app needs. It also does not solve the path-exposure problem.

**Verdict on A7:** Do not use. Zero value, mildly stale.

---

## Architecture B — Server-Side Native OS Dialog

The key insight: Hypresent's server is a Python process running on the same Windows desktop as the browser. The server can show a native dialog, capture the path, and return it in the API response. The browser never needs a file handle — it already has the proven POST `/api/open` path-based flow.

### B1. Python `tkinter.filedialog` from a `ThreadingHTTPServer` Handler Thread

`tkinter` is a Python stdlib module (no new dependencies). `filedialog.askopenfilename()` and `asksaveasfilename()` show the native Windows file picker.

**Thread safety reality on Windows:**

Tkinter is explicitly not thread-safe [9]. The Python bug tracker contains multiple open issues: "Tkinter hangs if using multiple threads and event handlers" (migrated to github.com/python/cpython/issues/77593) [9][10]. Calling any Tkinter function from a non-main thread — including `askopenfilename()` — can raise `RuntimeError: main thread is not in main loop` or cause a deadlock. `ThreadingHTTPServer` dispatches each request to a new thread; calling `askopenfilename()` directly in the handler will crash or hang.

**The hidden-root + `-topmost` pattern:**

A frequently cited workaround is:
```python
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()          # hide the root window
root.attributes('-topmost', True)
path = filedialog.askopenfilename(parent=root)
root.destroy()
```
This pattern has documented failures: (a) calling it before the window is drawn causes focus issues on Windows (Python bug #34253, closed as "third party", unresolved at the Tcl/Tk level) [11]; (b) third-party shell extensions (Dropbox, TortoiseGit, TortoiseHG) injected into Windows file dialogs have caused `askopenfilename()` to freeze Python 3.8+ (bug #38974, unresolved) [12]; (c) the root-withdraw pattern fails entirely when called from a background thread — `root.mainloop()` is not running, so Tk has no event loop to service the dialog [9].

**Serialization with a lock:**

Even if Tkinter calls were thread-safe, multiple concurrent HTTP requests could each attempt to open a dialog. A `threading.Lock` can serialize calls, but this does not fix the fundamental issue that Tk operations must run on the main thread.

**Verdict on B1:** Unreliable. The thread-safety issue is a known, unfixed Python/Tcl bug. The hidden-root pattern has multiple documented failure modes on Windows, precisely the platform targeted. Requires Tk to run on the main thread, which means rearchitecting the server's threading model or using `queue`/`after()` to bounce calls to a dedicated Tk main loop thread — high complexity, fragile.

### B2. PowerShell Subprocess (`System.Windows.Forms.OpenFileDialog`)

Spawn a PowerShell child process from the HTTP handler thread, have it show the native dialog and print the selected path to stdout, read stdout, return path in the JSON response. PowerShell ships on all Windows 11 machines — no new dependencies.

**Pattern:**

```python
import subprocess, threading

_dialog_lock = threading.Lock()

OPEN_SCRIPT = r"""
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Filter = 'HTML files (*.html)|*.html|All files (*.*)|*.*'
$d.Title = 'Open Presentation'
if ($d.ShowDialog() -eq 'OK') { Write-Output $d.FileName }
"""

def show_open_dialog():
    with _dialog_lock:
        result = subprocess.run(
            ['powershell', '-NonInteractive', '-NoProfile', '-STA', '-Command', OPEN_SCRIPT],
            capture_output=True, text=True, timeout=120
        )
    path = result.stdout.strip()
    return path if path else None
```

**STA-thread requirement:**

`System.Windows.Forms.OpenFileDialog` is a COM-based dialog. COM file dialogs require Single-Threaded Apartment (STA) initialization (`CoInitializeEx` with `COINIT_APARTMENTTHREADED`). The `-STA` flag in `pwsh` / `powershell` starts PowerShell in STA mode, satisfying this requirement [13][14]. Without `-STA`, `ShowDialog()` may fail or behave unpredictably (random `RPC_E_WRONG_THREAD` errors are documented with `IFileOpenDialog` from MTA threads) [14].

**Process isolation avoids the parent threading problem entirely:**

The dialog runs in the PowerShell process. Python's `subprocess.run()` blocks the HTTP handler thread (which is a worker thread from `ThreadingHTTPServer`'s thread pool — blocking one worker is correct, since the browser is waiting for the API response). The server's main thread and other handler threads are unaffected. No Tkinter event loop, no `queue`, no `after()` mechanism needed.

**Dialog-behind-window issues and fixes:**

When the dialog is spawned from a background process with no visible window, it may appear behind the Chrome window. The standard fix is to pass a window handle (`hwnd`) to `ShowDialog()` or to set `$d.ShowHelp = $true` (known workaround that forces foreground rendering in some .NET versions). A more reliable approach is to bring the PowerShell process to the foreground programmatically:

```powershell
$d.ShowHelp = $true   # legacy workaround; works on most Windows versions
```

Or using the `[Microsoft.VisualBasic.Interaction]::AppActivate` trick. In practice, on Windows 11 with a single-user localhost app, the dialog appears in the taskbar and is focused on click; this is acceptable UX.

**Reliability:**

PowerShell is a stable, long-lived Windows component. `System.Windows.Forms.OpenFileDialog` is a battle-tested WinForms control. The subprocess approach is used in production by tools like VS Code (for some extension interactions) and various Python desktop scripts. It is the standard pattern recommended when `tkinter` threading is problematic [13].

**Timeout:**

`subprocess.run(..., timeout=120)` prevents indefinite hang if the user leaves the dialog open. The HTTP response will 504 on the browser side if the user takes more than 120 s — acceptable for a file-open UX.

**Encoding:**

On Windows 11, `powershell` (Windows PowerShell 5.1) uses `cp1252` for stdout by default unless instructed otherwise. Add `-OutputEncoding utf8` or use `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` at the top of the script to handle non-ASCII paths correctly. `pwsh` (PowerShell 7) defaults to UTF-8 — prefer `pwsh` if available.

**Save-As dialog:**

```powershell
$d = New-Object System.Windows.Forms.SaveFileDialog
$d.Filter = 'HTML files (*.html)|*.html'
$d.DefaultExt = 'html'
$d.OverwritePrompt = $true
if ($d.ShowDialog() -eq 'OK') { Write-Output $d.FileName }
```

### B3. `windialog` — Python ctypes, No New Runtime Dependencies

`windialog` [15] is a single-file Python module using only `ctypes` to call `IFileOpenDialog` / `IFileSaveDialog` (Vista-era COM shell API). No installation required — copy the file. API:

```python
from windialog import getfile, getsave
paths = getfile(("HTML files", "*.html"), title="Open Presentation")  # [] on cancel
path  = getsave(("HTML files", "*.html"), title="Save As")            # '' on cancel
```

Returns absolute paths directly.

**COM/STA thread risk:**

`windialog` calls `IFileOpenDialog` via ctypes. The underlying COM object (`CLSID_FileOpenDialog`) has `ThreadingModel=Apartment` — it requires STA. The `windialog` source does not document whether it calls `CoInitializeEx` with `COINIT_APARTMENTTHREADED` before creating the dialog. If it does not, and if `ThreadingHTTPServer`'s handler thread is not an STA thread (it is not — Python threads do not call `CoInitialize` by default), the COM runtime will marshal the call to an implicit STA, which can cause random `RPC_E_WRONG_THREAD` failures [14]. The project has 3 total commits and no stated production usage, making this risk hard to validate. The library is effectively unmaintained.

**Verdict on B3:** Interesting concept, but unvalidated STA handling, minimal maintenance, and unknown threading behavior in an HTTP server context make it a liability vs. the PowerShell approach. Not recommended.

---

## Decision Matrix

| Criterion | A: File System Access API | B1: tkinter.filedialog | B2: PowerShell subprocess | B3: windialog |
|-----------|:-------------------------:|:----------------------:|:-------------------------:|:-------------:|
| Native dialog fidelity | Full (OS native) | Full (OS native) | Full (OS native) | Full (OS native) |
| Relative-asset preservation via `/doc/` | **Broken** (no path exposed) | Preserved | Preserved | Preserved |
| Silent re-save ("Save") without re-prompt | Yes (handle reuse) | N/A | Yes (path in memory) | N/A |
| Implementation risk | HIGH — requires rearchitecting asset serving or accepting asset-only-CDN constraint | HIGH — known threading deadlock on Windows, unfixed Python bug | LOW — process isolation, proven pattern, STA satisfied by `-STA` flag | MEDIUM — unvalidated STA behavior, unmaintained |
| Code size (new code, approx.) | ~50 lines JS + ~200 lines server (if asset-re-upload chosen) | ~20 lines Python + lock + queue plumbing | ~30 lines Python (handler + lock + script constant) | ~20 lines Python |
| Zero new runtime dependencies | Yes | Yes (stdlib) | Requires PowerShell (ships on all Win 11) | Requires vendoring windialog (~200 lines) |
| Path returned to server | No — fundamental constraint | Yes | Yes | Yes |
| Known production usage at scale | Yes (VS Code, Excalidraw, etc.) | Widespread (non-server context) | Common desktop automation pattern | Unknown |

---

## Recommendation

**Use Architecture B2 (PowerShell subprocess).**

Rationale:

1. **Preserves the load-bearing `/doc/` path architecture.** The server receives the absolute path in the API response, `set_doc_root()` runs as today, and relative assets load without any code change to the iframe loading flow.

2. **Process isolation is the correct solution to the threading problem.** `subprocess.run()` from a `ThreadingHTTPServer` handler thread is well-defined and safe. It blocks one worker thread (correct — the browser is awaiting the response) and leaves the server's main thread entirely untouched.

3. **STA is satisfied at the subprocess level.** The `-STA` PowerShell flag calls `CoInitializeEx(COINIT_APARTMENTTHREADED)` for the process, which is the required model for `System.Windows.Forms` dialogs. This is documented and reliable.

4. **Minimal new code.** The change is ~30 lines in `api.py` / `server.py`, a new `/api/dialog-open` and `/api/dialog-save` endpoint, and a small JS change in `file-controls.js` to call those endpoints instead of reading from text inputs.

5. **Architecture A is ruled out by a fundamental constraint.** The File System Access API will never expose the real filesystem path. Implementing asset serving from in-browser file handles is a significant architectural change with correctness risks; it is not worth pursuing for a single-user localhost tool.

6. **B1 (tkinter) is ruled out by an unfixed Python bug.** Calling `askopenfilename()` from a `ThreadingHTTPServer` handler thread is documented to hang or crash on Windows. The fix requires bouncing the call to a Tk main-loop thread via `queue.Queue` — 3× the code complexity of B2 with worse reliability.

---

## Implementation Sketch for B2

### Server side (new endpoint `/api/dialog-open`)

```python
# api.py additions
import subprocess, threading, sys

_DIALOG_LOCK = threading.Lock()

_OPEN_PS = """
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Filter = 'HTML files (*.html)|*.html|All files (*.*)|*.*'
$d.Title = 'Open Presentation'
$d.ShowHelp = $true
if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $d.FileName
}
"""

_SAVE_PS = """
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.SaveFileDialog
$d.Filter = 'HTML files (*.html)|*.html'
$d.DefaultExt = 'html'
$d.OverwritePrompt = $true
$d.Title = 'Save As'
$d.ShowHelp = $true
if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $d.FileName
}
"""

def _run_ps_dialog(script):
    """Run a PowerShell dialog script and return the chosen path, or None."""
    exe = 'pwsh' if sys.platform == 'win32' else 'powershell'
    with _DIALOG_LOCK:
        r = subprocess.run(
            [exe, '-NonInteractive', '-NoProfile', '-STA', '-Command', script],
            capture_output=True, text=True, encoding='utf-8', timeout=300
        )
    path = r.stdout.strip()
    return path if path else None

def handle_dialog_open():
    path = _run_ps_dialog(_OPEN_PS)
    if not path:
        return (200, {'cancelled': True})
    return handle_open({'path': path})

def handle_dialog_save_as(payload):
    path = _run_ps_dialog(_SAVE_PS)
    if not path:
        return (200, {'cancelled': True})
    payload['path'] = path
    return handle_save_as(payload)
```

### Client side

Replace `#open-path-input` text input + button with a single "Open…" button that calls `POST /api/dialog-open` (no body). On success, use the returned `{html, dir, name}` exactly as today. Remove `#save-as-path-input` text input; replace "Save As…" button with a call to `POST /api/dialog-save-as` (body: `{html}`). A "Save" (silent) button caches the last-used path in JS and calls the existing `POST /api/save-as` directly.

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

[1] Secure Contexts — MDN Web Docs — https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts — 2026-06-03 — 2025 — TS:9.3 (AT:10 TR:9 TM:9)

[2] Treat `http://localhost` as a secure context — Chrome Platform Status — https://chromestatus.com/feature/6269417340010496 — 2026-06-03 — 2024 — TS:9.7 (AT:10 TR:10 TM:9)

[3] Window: showOpenFilePicker() method — MDN Web Docs — https://developer.mozilla.org/en-US/docs/Web/API/Window/showOpenFilePicker — 2026-06-03 — 2025 — TS:9.3 (AT:10 TR:9 TM:9)

[4] The File System Access API: simplifying access to local files — Chrome for Developers — https://developer.chrome.com/docs/capabilities/web-apis/file-system-access — 2026-06-03 — 2025 — TS:9.7 (AT:10 TR:10 TM:9)

[5] Persistent permissions for the File System Access API — Chrome Developers Blog — https://developer.chrome.com/blog/persistent-permissions-for-the-file-system-access-api — 2026-06-03 — 2024-01 (Chrome 122) — TS:9.3 (AT:10 TR:9 TM:9)

[6] File System API — MDN Web Docs — https://developer.mozilla.org/en-US/docs/Web/API/File_System_API — 2026-06-03 — 2025 — TS:9.3 (AT:10 TR:9 TM:9)

[7] The API should allow working with absolute paths (WICG Issue #145) — https://github.com/WICG/native-file-system/issues/145 — 2026-06-03 — 2020 (closed) — TS:8.7 (AT:9 TR:9 TM:8)

[8] browser-fs-access Releases — GoogleChromeLabs — https://github.com/GoogleChromeLabs/browser-fs-access/releases — 2026-06-03 — 2024-06 (v0.38.0) — TS:8.7 (AT:9 TR:9 TM:8)

[9] Issue 11077: Tkinter is not thread safe — Python Bug Tracker — https://bugs.python.org/issue11077 — 2026-06-03 — open — TS:9.3 (AT:10 TR:9 TM:9)

[10] Issue 33412: Tkinter hangs if using multiple threads and event handlers — Python Bug Tracker — https://bugs.python.org/issue33412 — 2026-06-03 — open — TS:9.3 (AT:10 TR:9 TM:9)

[11] Issue 34253: Tkinter filedialog/messagebox before window drawn causes focus issues — Python Bug Tracker — https://bugs.python.org/issue34253 — 2026-06-03 — closed as third-party — TS:9.0 (AT:10 TR:9 TM:8)

[12] Issue 38974: tkinter.filedialog.askopenfilename() freezes Python 3.8 — Python Bug Tracker — https://bugs.python.org/issue38974 — 2026-06-03 — open — TS:9.0 (AT:10 TR:9 TM:8)

[13] Using OpenFileDialog in PowerShell — Rich Hopkins — https://souladin.wordpress.com/2013/08/29/using-openfiledialog-in-powershell/ — 2026-06-03 — 2013 — TS:6.7 (AT:7 TR:6 TM:7)

[14] C# WinForm's OpenFileDialog with MTAThread — Acharya's Blog — https://acharyarajasekhar.wordpress.com/2015/04/10/c-winforms-openfiledialog-with-mtathread/ — 2026-06-03 — 2015 — TS:6.3 (AT:6 TR:6 TM:7) — confirms MTA→STA marshalling issues with IFileOpenDialog

[15] windialog — MissingNo42 / PyPI — https://github.com/MissingNo42/windialog — 2026-06-03 — 2023 (3 commits) — TS:5.7 (AT:5 TR:6 TM:6)

## Sources Discarded

| Source | TS | Reason |
|--------|----|--------|
| [windialog — PyPI listing](https://pypi.org/project/windialog/) | 5.7 | Minimal maintenance (3 commits, no date), no STA handling documentation, unknown production usage; kept as B3 candidate but not recommended |
