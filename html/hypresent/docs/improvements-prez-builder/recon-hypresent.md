# Hypresent Codebase Recon — prez-builder orchestrator report

Date: 2026-06-06  
Analyst: recon sub-agent (Claude Sonnet 4.6)  
Workspace studied: `html/hypresent/` (relative to rbtv repo root)  
Parent module mapped: `html/` (one level only)  
rbtv repo root mapped: top-level structure + conventions docs

---

## 1. APP ARCHITECTURE

### Entry point and shell boot

Single HTML entry point: `app/index.html` served at `GET /app/` → `GET /app/index.html` (directory index fallback in `_serve_static`).

```html
<!-- app/index.html line 58 -->
<script type="module" src="/app/js/main.js"></script>
```

`main.js` is the shell bootstrap. It imports:

```js
// app/js/main.js lines 1-6
import Coloris from "/app/js/vendor/coloris.min.js";
import { createBridge } from "/app/js/bridge/bridge-parent.js";
import { openViaDialog } from "/app/js/shell/file-controls.js";
import { createColorPopover } from "/app/js/shell/color-popover.js";
import { openComposer } from "/app/js/shell/comment-composer.js";
import { dialogSaveAs, save } from "/app/js/api-client.js";
```

Shell boot sequence:
1. `DOMContentLoaded` in `main.js` — Coloris init, button event wiring.
2. User clicks **Open…** → `openViaDialog(iframe)` in `file-controls.js`.
3. `file-controls.js` calls `apiClient.dialogOpen()` → `POST /api/dialog-open` → returns `{html, dir, name}`.
4. Shell sets `iframe.src = '/doc/' + encodeURIComponent(name)`.
5. On iframe `load`, `file-controls.js` injects the runtime script into the iframe document.
6. Runtime boot (`runtime-main.js`) runs inside iframe: tags elements, parses comment island, reads `:root` tokens, emits `ready`.
7. Shell enables controls on `ready`.

### How the editor loads a deck file

**URL params: NONE.** No query-string routing. Opening is entirely UI-driven (dialog) or programmatic via POST API.

**Loading a file by known path (programmatic):**

```js
// app/js/shell/file-controls.js
export async function openFile(path, iframe) {
  const result = await apiClient.open(path);  // POST /api/open {path}
  await loadIntoIframe(result.name, iframe);
}
```

```js
// file-controls.js — loadIntoIframe (lines 3-19)
function loadIntoIframe(name, iframe) {
  return new Promise((resolve) => {
    const onLoad = () => {
      const doc = iframe.contentDocument;
      if (!doc) { resolve(); return; }
      const existing = doc.querySelector('script[src="/runtime/js/runtime-main.js"]');
      if (!existing) {
        const script = doc.createElement('script');
        script.type = 'module';
        script.src = '/runtime/js/runtime-main.js';
        (doc.head || doc.documentElement).appendChild(script);
      }
      resolve();
    };
    iframe.addEventListener('load', onLoad, { once: true });
    iframe.src = '/doc/' + encodeURIComponent(name);
  });
}
```

### Mechanisms a second page (prez-builder) could use

**Multiple HTML entry points (confirmed viable):** The server's static routing is path-prefix based (`/app/*` → `APP_ROOT`). `APP_ROOT` is `REPO_ROOT/app/`. A second HTML file placed at `app/builder.html` would be served at `GET /app/builder.html` — no server changes needed.

**No client-side router:** The app has no SPA router, no hash routing, no history API usage. Navigation between pages requires loading a new HTML document.

**Shared API:** Any page served from the same origin can call `POST /api/open`, `POST /api/save-as`, `POST /api/save`, `POST /api/dialog-open`, `POST /api/dialog-save-as` via `fetch`. All endpoints are same-origin only (no CORS headers emitted by the server — see Section 2).

**Shared runtime:** `GET /runtime/*` is a fixed static route. Any page can inject `runtime-main.js` into an iframe using the same injection pattern.

---

## 2. SERVER

### Framework

Python standard library only — `http.server.ThreadingHTTPServer`. **No Flask, no dependencies.**

```python
# server/server.py line 169-173
def run(host="127.0.0.1", port=8765):
    """Start the threaded HTTP server and block forever."""
    with http.server.ThreadingHTTPServer((host, port), Handler) as server:
        print(f"Serving on http://{host}:{port}")
        server.serve_forever()
```

Default: `127.0.0.1:8765`. Custom host/port via CLI args: `python server/server.py <host> <port>`.

### Every endpoint

```
GET  /app/*                   → static from REPO_ROOT/app/  (fixed root)
GET  /runtime/*               → static from REPO_ROOT/runtime/  (fixed root)
GET  /doc/*                   → static from currently-open file's directory  (mutable root, re-pointed on each /api/open)
POST /api/open                → {path} → reads file, returns {html, dir, name}; re-points /doc/ root
POST /api/save-as             → {path, html} → writes html to path on disk
POST /api/dialog-open         → spawns PowerShell OpenFileDialog; on selection delegates to handle_open
POST /api/dialog-save-as      → {html}; spawns PowerShell SaveFileDialog; on confirm delegates to handle_save_as
POST /api/save                → {html}; silent overwrite of currently-open file; returns {no_open_file:true} if none open
POST /api/_test/set-dialog    → test seam only (requires HYP_TEST_DIALOG=1 env var)
```

Full route dispatch in `server/server.py` lines 145-163.

### Static serving

Three explicit roots, NO directory listing, path traversal blocked:

```python
# server/server.py lines 114-127
if path.startswith("/app/"):
    self._serve_static(APP_ROOT, path[len("/app/"):])
elif path.startswith("/runtime/"):
    self._serve_static(RUNTIME_ROOT, path[len("/runtime/"):])
elif path.startswith("/doc/"):
    doc_root = _doc_root["path"]
    if doc_root is None:
        self._send_json(404, {"error": "No document open"})
        return
    self._serve_static(doc_root, path[len("/doc/"):])
else:
    self._send_json(404, {"error": "Not found"})
```

`_serve_static` falls through to `index.html` for directory requests (line 98): `if target.is_dir(): target = target / "index.html"`.

### File open/save mechanism

**Open:** `POST /api/open {path}` → reads file by absolute path from disk → returns `{html, dir, name}` → re-points `/doc/` root to `p.parent`.

**Save:** `POST /api/save-as {path, html}` → writes to absolute path; parent directory must already exist (no auto-mkdir).

**Dialog:** PowerShell `System.Windows.Forms.OpenFileDialog` / `SaveFileDialog` spawned as subprocess, `pwsh` first then `powershell.exe` fallback. Dialog is Windows-only. A `threading.Lock` serializes dialog calls.

### Filesystem-pick mechanism (folder picker)

**No folder picker exists.** Only file pickers (`OpenFileDialog` for HTML files, `SaveFileDialog` for HTML). The builder page would need either: (a) a new server endpoint for folder picking, or (b) a text-input path entry.

### CORS / iframe considerations

**No CORS headers emitted.** The server sends only `Content-Type` and `Content-Length`. All pages and iframes must be same-origin (`127.0.0.1:<port>`). Cross-origin requests from a different port would be blocked by the browser.

**Iframe sandboxing:** The iframe in `app/index.html` has **no `sandbox` attribute** — it is a fully trusted same-origin iframe. The builder page's preview iframes would need the same treatment if previewing real deck files. Using `srcdoc=` to preview assembled HTML would be treated as same-origin too (about:srcdoc inherits the parent origin in Chrome).

---

## 3. EDITOR HANDOFF

To programmatically open a given `.html` deck file in the editor today, the builder page must:

1. **Navigate** the user to `/app/` (or open it in a new tab), AND
2. **Pre-open the file** via `POST /api/open {path}` so the server's `/doc/` root is set, AND
3. **Trigger the iframe load** by setting `iframe.src = '/doc/' + encodeURIComponent(name)`.

Steps 2+3 are inseparable because the iframe's `src` depends on the filename returned by the server after the open call.

**Exact code path (the builder would replicate or call this):**

```js
// app/js/shell/file-controls.js — openFile (lines 22-25)
export async function openFile(path, iframe) {
  const result = await apiClient.open(path);
  // result = {html, dir, name}
  await loadIntoIframe(result.name, iframe);
}
```

```js
// app/js/api-client.js — open (lines 1-15)
export async function open(path) {
  const response = await fetch('/api/open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}
```

**Cross-page handoff (builder → editor):** If the builder is a separate HTML page at `/app/builder.html`, it cannot directly set the iframe src of the editor page's iframe. The cleanest mechanisms are:

- **Option A (URL param + editor modified):** Add `?file=<encoded-path>` handling to the editor's `main.js` boot sequence. No such handling exists today — would require adding it.
- **Option B (sessionStorage / localStorage):** Builder writes the assembled file path to `localStorage`; editor reads on load. Not currently implemented.
- **Option C (server-side state):** The server already tracks `_open_path` in `api.py`. A new `GET /api/current-file` endpoint could expose it. Not currently implemented.
- **Option D (single page):** Builder and editor coexist in one page — builder assembles, then calls `openFile(path, iframe)` programmatically on the existing editor iframe. **This is the lowest-friction path given current architecture.**

---

## 4. RUNTIME

### What runtime/ is

The edit-runtime is injected into the user's document iframe after load. It is NOT embedded in the document on disk — it is dynamically injected by `file-controls.js`:

```js
// file-controls.js lines 7-12
const script = doc.createElement('script');
script.type = 'module';
script.src = '/runtime/js/runtime-main.js';
(doc.head || doc.documentElement).appendChild(script);
```

Served from the fixed `/runtime/` route, so its ES-module `import` chain resolves against `/runtime/js/`, never the opened document's `/doc/` directory.

### How decks are structured for editing

**No `{{TOKENS}}` template syntax.** No special tokens in the HTML. The editor works on raw HTML:

- **`data-hyp-id`** — assigned at runtime to every editable element; stripped on save. Format: `hyp-<N>` (integer).
- **`data-hyp-hook`** — OPTIONAL stable author hint; comment anchors prefer it over the path-based key.
- **`data-hyp-region`** — OPTIONAL region marker for content areas.
- **`data-hyp-decorative`** — marks elements the editor should skip.
- **`data-hyp-text`**, **`data-hyp-resize`**, **`data-hyp-move`** — opt-in/out hints.
- **`data-hyp-agent`** — stamped transiently on save (stripped from live DOM after); survives in the saved file to enable agent targeting.

All `data-hyp-*` attributes are stripped on Save As except `data-hyp-agent` (which is intentionally preserved in the saved output for machine-readability).

### Slide sections

Slides are detected heuristically — **no `.slide` class assumption.** The region detection algorithm (spec `02-html-convention.md` §4):

1. Find the element with most text-bearing descendants among `<body>` children.
2. Within that root, a "region" is a direct child that is a sectioning element (`<section>`, `<article>`, etc.) OR a repeated sibling sharing tag+class signature with ≥1 peer.
3. Decorative nodes excluded.

The existing fixture (`tecer-gsmm-introduction.html`) uses `<section>` elements as slides. The builder must emit `<section>` elements (or repeated divs with a shared class) as top-level children of the content root for the editor's region detection to work.

### Comment island

Comments are persisted as:
```html
<script type="application/json" id="hyp-comments">[...]</script>
```
at end of `<body>`. Inert (not executed). Survives Save As. The builder-assembled deck should NOT include this tag — the runtime creates it when the first comment is added.

### Palette manifest (optional hint)

```html
<script type="application/json" id="hyp-palette">{"tokens": ["--accent", ...]}</script>
```
Lists which `:root` custom properties are user-facing color tokens. If absent, the editor auto-discovers all color-valued `:root` properties.

---

## 5. PREVIEW PRECEDENT

**No existing thumbnail/catalog/preview rendering in hypresent.** There is no component that renders scaled previews, thumbnails, or a catalog of slides. The app has exactly one iframe (the editor's `<iframe class="doc-frame">`), which loads the full document.

**What does exist that the builder could draw on:**

The iframe injection pattern in `file-controls.js` is the closest precedent for loading HTML into an iframe:

```js
// file-controls.js lines 3-19
function loadIntoIframe(name, iframe) {
  return new Promise((resolve) => {
    const onLoad = () => { /* injects runtime */ resolve(); };
    iframe.addEventListener('load', onLoad, { once: true });
    iframe.src = '/doc/' + encodeURIComponent(name);
  });
}
```

For preview iframes in the builder, `srcdoc` with the assembled HTML string would avoid requiring the file to be on disk first, but `srcdoc` iframes are same-origin so cross-frame communication would still work. CSS `transform: scale()` on the iframe wrapper is the standard approach for scaled "thumbnail" rendering — nothing in the codebase establishes a precedent for or against it.

**NONE of the following exist in hypresent:** slide thumbnails, slide catalog, deck navigator, multi-slide preview, PDF preview, print preview.

---

## 6. TESTS

### Framework and organization

- **e2e tests:** Playwright via Python `unittest.TestCase`. Located in `tests/e2e/`. Each test file launches a real server subprocess and a headless Chromium browser via `sync_playwright`.
- **unit tests:** Python `unittest` (no Playwright). Located in `tests/unit/`. Test the server API directly via `urllib.request`.

### How suites run

```python
# tests/e2e/conftest_helpers.py — start_server (lines 16-33)
def start_server(port, test_dialog=False):
    env = dict(os.environ)
    if test_dialog:
        env["HYP_TEST_DIALOG"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "server/server.py", "127.0.0.1", str(port)],
        cwd=REPO, env=env,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 6
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/app/", timeout=1):
                return proc, base
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError(f"server did not start on {port}")
```

Each test class starts its own server instance on a fixed port. `HYP_TEST_DIALOG=1` enables the `/api/_test/set-dialog` seam for injecting a fake dialog launcher that returns a programmatic path.

### Ports used

| Test file | PORT constant |
|-----------|---------------|
| `test_exit_smoke.py` | 8788 |
| `test_f1_dialogs.py` | (not yet read — uses own port) |
| Others | ports from 8781 upward (historically); each file uses one dedicated port |

The current suite is **155 tests** (as of session 3 close: "suite 155p/1s(historical)/0f" — changelog row 224).

### conftest_helpers.py key exports

```python
start_server(port, test_dialog=False) → (proc, base_url)
stop_server(proc)
copy_fixture() → abs_path_of_copy  # copies tecer-gsmm-introduction.html to tempdir
copy_synthetic(name) → abs_path    # copies from tests/e2e/fixtures/
post_json(base, path, payload) → (status, data)
set_fake_dialog(base, path_or_none)
preset_author(page)  # seeds localStorage so comment-author prompt never blocks
open_via_dialog_ui(page, base, file_path)
wait_runtime_ready(page, timeout=15000)
doc_eval(page, expr)  # evaluate JS in the iframe doc
```

### .kimi-agent/code-agent.yaml

```yaml
version: 1
agent:
  extend: default
  exclude_tools:
    - "kimi_cli.tools.web:SearchWeb"
    - "kimi_cli.tools.web:FetchURL"
```

Web search and URL fetch are excluded. All other default tools (file read/write, bash, etc.) are inherited. This file disables network access for the coding agent — consistent with the orchestration pattern where the orchestrator does research and the executor only touches local files.

---

## 7. DOCS

### docs/ top-level files

| File | Content |
|------|---------|
| `build-log.md` | Session-by-session build registrar (230 rows as of session 3 close). The canonical history of all dispatches, results, and commits. |
| `decision-log.md` | Locked decisions D1–D19 + architecture choices A1–A12. APPEND-ONLY by convention. |
| `fixture-profiles.md` | Analysis of the two test fixture HTML files (deck and report), their structure, and how the editor handles each. |
| `kimi-cheatsheet.md` | Orchestration cheat-sheet for dispatching Kimi tasks. |
| `learnings.md` | Session learnings (agent behavior, test patterns). |
| `research-oss.md` | Pre-build OSS research: Moveable, Coloris, DOMPurify evaluation. |

### docs/spec/ — spec files

| File | Coverage |
|------|---------|
| `01-architecture.md` | Component diagram, isolation model, parent↔iframe protocol (command set + event set), data flow (open/edit/save), serialization flow (5 steps), coexistence/namespacing rules, comment anchor key contract (5 fields), error handling, boot sequence. |
| `02-html-convention.md` | Format-agnostic editability hints (H1–H9), graceful-degradation rules per hint, region detection heuristic, generator checklist. |
| `03-module-map.md` | Full file/folder tree with one-line purpose and public interface per module. Server modules, app-shell modules, iframe runtime modules, testability matrix. |
| `04-implementation-plan.md` | Original v1 task breakdown. |
| `05-verification-plan.md` | Per-module pass/fail criteria. |
| `review-log.md` | Pre-build spec review log. |

### docs/plan/

| Directory | Content |
|-----------|---------|
| `hypresent-v1/` | Original v1 plan + phase task files (T1–T18). |
| `hypresent-v2/` | Session-1 improvement plan (V2-T0–T21). |
| `hypresent-v3/` | Session-2 improvement plan (V3-T1–T19): R1–R9 (resize, color, delete, alignment, comments panel). |
| `hypresent-v4/` | Session-3 improvement plan (V4-T1–T11): R10–R14 (resize 1:1, symmetric resize, equal-size guides, comment edit/delete, agent stamping). |

### docs/improvements-2026-06*, docs/verification/

Improvement cycle specs, diagnosis docs, test plans, and verification results for sessions 1–3. Current verified state: session 3 closed, `docs/verification/v4/result.md` confirms 155p/1s/0f suite.

### Anything about slide libraries, catalogs, deck assembly, second page

**Nothing.** No document in `docs/` mentions slide catalogs, deck assembly pipelines, presentation builders, or a second HTML page. The prez-builder is entirely new territory with no existing design artifacts in this repo.

---

## 8. GIT

### Current branch

`master` (per plan `hypresent-v4-plan.md`: "Branch: `master` continues").

### Last 5 commits (rbtv repo)

```
8e7bc89 fix(core): commit workflow — stage explicit file paths, never directories
1d32b39 feat(coding): add done-gate rule — evidence-gated done for coding tasks
82a6181 refactor(html): move hypresent into the html module folder
b02d5c7 [v4-close] registrar: session 3 close row (230)
613cee1 [v4-close] session 3 registrar: changelog, r3 design docs + errata, plan v4, review evidence
```

### Dirty files (rbtv repo working tree)

```
M html/hypresent/changelog.md
```

One dirty file: `changelog.md` in hypresent. No other dirty files. The changelog is the orchestrator's session log — expected to be modified during active sessions.

---

## 9. CONVENTIONS

### JS conventions (app/ and runtime/)

- **Vanilla ES modules throughout.** `import`/`export` syntax, `type="module"` script tags. No CommonJS, no bundler, no transpiler.
- **No framework.** No React, Vue, or any component library. Pure DOM manipulation.
- **No TypeScript.** Plain `.js` files.
- **Module style:** each file has a single responsibility, exports a narrow public API. Side effects only in `runtime-main.js` (boot orchestrator).
- **Error handling:** `try/catch` at the bridge level; modules throw; callers catch. No global error handlers.
- **Naming:** `camelCase` for functions and variables. Files use `kebab-case`.
- **No build artifacts.** Vendor libs are pre-built files copied into `app/js/vendor/`. Nothing is compiled.

### Python conventions (server/)

- **Standard library only** (A10 locked). No pip dependencies.
- **File naming:** `snake_case` for Python files and functions.
- **No type annotations** visible in the read files.
- **Threading:** `ThreadingHTTPServer` for concurrency; `threading.Lock` for the dialog serialization.
- **Error pattern:** handler functions return `(status_int, response_dict)` tuples; the router calls `_send_json(status, resp)`.

### rbtv repo module conventions (relevant to placing hypresent siblings)

The `html/` module contains:

```
html/
├─ commands/      # RBTV commands (shell commands, not HTTP)
├─ hypresent/     # the hypresent tool (the tool being studied)
├─ personas/      # RBTV personas
├─ skills/        # RBTV skills
└─ workflows/     # RBTV workflows
```

`hypresent/` was moved into `html/` in commit `82a6181` (`refactor(html): move hypresent into the html module folder`). It lives alongside RBTV component directories (`commands/`, `skills/`, etc.) as a **tool** within the html module.

**No `tools/` subdirectory exists under `html/`.** Tools like hypresent sit directly under the module folder. A sibling tool (prez-builder) would go at `html/prez-builder/` following the same pattern.

**RBTV module manifest:** `admin/install/module-manifest.json` lists installable components. A new tool placed at `html/prez-builder/` would need an entry there if it ships installed RBTV components (skills/commands/rules). If prez-builder is a standalone app like hypresent (not an RBTV component), it does not need a manifest entry — hypresent itself has no manifest entry (it is a tool, not an installable component).

**CLAUDE.md rule:** any component creation/rename/delete requires updating `readme.md`, the relevant `modules/` file, and `admin/install/module-manifest.json` in the same change.

---

## 10. RISKS / GAPS

### R1 — Single-file-at-a-time assumption baked into the server

`_doc_root["path"]` and `_open_path["path"]` are module-level singletons. The server serves exactly ONE document's directory at `/doc/` at any time. Opening a second file changes the `/doc/` root for ALL concurrent clients.

**Builder impact:** If the builder page has multiple slide previews in iframes (each pointing to a different file), only one `/doc/` root can be active at a time. Workarounds: (a) use `srcdoc` with the full HTML content instead of `/doc/` paths (no server state required), or (b) extend the server with named doc sessions (not trivial — would require path-keyed routing).

### R2 — Absolute path handling (Windows separators)

`api.py` uses `pathlib.Path` throughout, which handles Windows backslashes correctly on the server side. However, the filename returned in `handle_open` response is `p.name` (basename only), and the `dir` is `str(parent)` using the OS path separator.

The iframe is loaded via:
```js
iframe.src = '/doc/' + encodeURIComponent(name);
```
`name` is the basename only — the full path is never exposed to the browser. This is correct. But the builder, when assembling a deck, must write the assembled file to disk first (or use `srcdoc`) before opening it in the editor, since the editor only opens by absolute path via the server.

### R3 — No URL-param or deep-link mechanism to pre-open a file

The editor has no `?file=...` query string handling. A builder page that assembles a deck and wants to hand off to the editor page must either: modify the editor to support URL params (new feature), use localStorage/sessionStorage for cross-page state, or combine builder and editor into a single page.

### R4 — PowerShell dialog is Windows-only

`_run_ps_dialog_default` in `api.py` spawns PowerShell. On non-Windows the fallback is `candidates = ["pwsh"]` only. In a builder flow that saves assembled decks without a user dialog, the builder can call `POST /api/save-as {path, html}` directly (no dialog), which is platform-independent. The dialog is only needed for user-initiated save flows.

### R5 — Asset path resolution in the editor

When the editor loads a file via `/doc/<name>`, relative assets (`assets/logo.png`) resolve against `/doc/`. This works because `/doc/` is re-rooted to the opened file's parent directory. For builder-assembled decks:
- Assets referenced by relative path must exist in the same directory the assembled file is written to, or be referenced by absolute URL.
- If the builder assembles from slide library assets in a different directory, relative paths in the assembled HTML will break when opened in the editor (unless the server's `/doc/` root is the library's asset directory).

### R6 — No iframe sandbox attribute (intentional, but relevant for builder preview)

The editor's `<iframe class="doc-frame">` has no `sandbox` attribute — the document's own JS runs. For builder previews showing user-assembled slides, this is a security consideration if slides contain arbitrary JS. The existing app's threat model assumes the opened file is the user's own (not untrusted). A builder showing previews of library-provided slide templates shares this assumption.

### R7 — No existing second-page routing or navigation pattern

The codebase has no `history.pushState`, no `<a href>` navigation, no multi-page pattern. A builder page is entirely new infrastructure. The closest precedent is the server's directory-fallback for `index.html` — a `builder.html` would need no server change.

### R8 — `src` vs `srcdoc` for preview iframes

Using `iframe.src = '/doc/...'` for preview requires the server to have the file on disk. Using `srcdoc` with the full assembled HTML avoids this but means relative asset paths in the preview HTML won't resolve (the `srcdoc` iframe's base URL is `about:srcdoc`). For library-sourced templates with CDN or absolute asset references, `srcdoc` works fine. For templates with relative `assets/` references, `/doc/`-served iframes are required.

---

## CONTRADICTIONS

### C1 — `docs/spec/01-architecture.md` mentions `GET /api/pick` (optional); live code does not implement it

From `01-architecture.md` line 45:
```
GET  /api/pick? (opt)  → returns recent/known paths (no native dialog)
```

The live `server/server.py` has no `GET` handler for `/api/pick`. Only `POST` endpoints are routed. The spec lists this as optional (`(opt)`) and the live implementation simply omitted it.

**Flag:** Not a blocker, but the builder may want a path picker and cannot rely on this endpoint existing.

### C2 — `docs/spec/03-module-map.md` lists `toolbar.js`, `comment-panel.js`, `outline.js` as separate shell modules; live `app/js/shell/` does not contain all of them

The module map lists:
- `app/js/shell/toolbar.js`
- `app/js/shell/file-controls.js`
- `app/js/shell/color-popover.js`
- `app/js/shell/comment-panel.js` (comment side panel)
- `app/js/shell/outline.js` (outline navigator — removed per D8)

Live `app/js/shell/` contains: `color-popover.js`, `comment-composer.js`, `file-controls.js`. No `toolbar.js`, no `comment-panel.js`, no `outline.js`.

The toolbar and comment panel logic is inlined in `main.js` (20KB). The module map is partially stale — it reflects intended modularization that was never split out (or was merged back into `main.js`).

**Flag:** If the builder reuses shell module patterns, follow `main.js` as the live source, not the module map's listed filenames.

### C3 — `docs/spec/01-architecture.md` §3 mentions `iframe.contentWindow.hyp` for direct calls; live code uses only `postMessage` bridge

The architecture doc says:
> "the parent obtains `iframe.contentWindow.hyp` (the runtime's exported command object) for synchronous reads and command dispatch"

The live `bridge-parent.js` exclusively uses `postMessage` via `iframe.contentWindow.postMessage(...)` — there is no direct `contentWindow.hyp.command()` call in the shell code. `window.hyp` exists in the runtime (runtime-main.js line 278) but is only used as a test/introspection hook (`window.hyp.comments.toJson`), not as the primary command channel.

**Flag:** Live architecture uses postMessage bridge only. The `window.hyp` direct-call path described in the spec is not the implementation's primary channel.

---

## ORCHESTRATOR NOTES

The 5 facts most likely to change the build plan:

1. **No URL-param routing exists.** The editor cannot be pre-loaded with a file from a URL. The builder must either (a) be a single-page app that embeds the editor iframe directly, calling `openFile(path, iframe)` after assembly, or (b) add URL param handling to the editor — which is a new feature requiring server or JS changes.

2. **`/doc/` is a singleton mutable root.** Only one file's directory can be served at `/doc/` at a time. Multi-slide preview iframes that point to files in different directories cannot all work via `/doc/` simultaneously. The builder should use `srcdoc` for previews of assembled HTML strings, or ensure all slide templates live in a single directory.

3. **A second HTML entry point requires zero server changes.** `app/builder.html` would be served at `GET /app/builder.html` with no modifications to `server.py`. The builder can share all existing API endpoints (`/api/open`, `/api/save-as`, etc.) from the same server instance.

4. **No folder-picker server endpoint.** `POST /api/dialog-open` picks a file, not a folder. If the builder needs the user to select a slide library directory, a new `POST /api/dialog-folder` endpoint using `FolderBrowserDialog` must be built. This is Windows-only (PowerShell WinForms).

5. **155 tests, all passing on `master`.** The test suite is healthy and uses port ranges starting at 8781. A builder page's own tests must use ports outside the existing range (above 8797 is safe) and should follow the `conftest_helpers.py` patterns: `start_server(port, test_dialog=False)`, `copy_fixture()`, `wait_runtime_ready(page)`.
