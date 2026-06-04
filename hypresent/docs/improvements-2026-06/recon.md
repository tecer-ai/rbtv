# hypresent — Reconnaissance Report

**Date:** 2026-06-03
**Scope:** Full read-only inventory of `hypresent/` and the rbtv repo root CLAUDE.md.
**No files were modified; this file is the sole write.**

---

## 1. rbtv Repo Conventions (from CLAUDE.md)

The rbtv CLAUDE.md has one hard rule relevant to hypresent:

> "When you create, rename, delete, or materially change ANY component (skill, command, rule, subagent, persona, workflow, task), you MUST in the SAME change update `README.md`, the relevant `modules/` file, and `admin/install/module-manifest.json`."

hypresent is a standalone tool sub-directory, not an installable RBTV component, so the module-manifest rule does not apply to it directly. No naming, docs, or placement conventions specific to hypresent are stated in CLAUDE.md beyond the general component conventions.

---

## 2. File Inventory

### `hypresent/` root

| File / Dir | ~Lines | Purpose |
|---|---|---|
| `app/` | — | Editor app shell (parent page, CSS, JS) |
| `docs/` | — | All project documentation |
| `runtime/` | — | Edit-runtime injected into the iframe |
| `server/` | — | Python HTTP server |
| `tecer-gsmm-introduction.html` | 2235 | Sample deck fixture: 10-slide presentation for Tecer × GSMM pitch, class-based layout with `:root` CSS variables, no inline `<script>` |

### `app/`

| File | ~Lines | Purpose |
|---|---|---|
| `index.html` | 61 | Parent shell: toolbar, iframe mount, side panel (outline + comments) |
| `css/shell.css` | 252 | App-shell styling; never enters the document |
| `js/main.js` | 480 | Shell bootstrap: wires bridge, file-controls, color-popover, format/comment/undo buttons |
| `js/api-client.js` | 32 | `fetch` wrappers for `/api/open` and `/api/save-as` |
| `js/bridge/bridge-parent.js` | 119 | Parent side of postMessage protocol; command dispatch + event subscription |
| `js/shell/file-controls.js` | 41 | Opens a file: POSTs to `/api/open`, sets `iframe.src`, injects runtime script |
| `js/shell/color-popover.js` | 254 | Palette token list + per-element Text/Background color UI (Coloris) rendered inside the side panel |
| `js/vendor/moveable.min.js` | — | Vendored Moveable.js (UMD) |
| `js/vendor/coloris.min.js` | — | Vendored Coloris (ES module export) |
| `js/vendor/coloris.css` | — | Coloris CSS |
| `js/vendor/purify.min.js` | — | Vendored DOMPurify (optional; never imported by serializer) |

### `runtime/js/`

| File | ~Lines | Purpose |
|---|---|---|
| `runtime-main.js` | 202 | Iframe bootstrap: tags elements, registers all bridge commands, exposes `window.hyp`, emits `ready` |
| `bridge-iframe.js` | 75 | Iframe side of postMessage protocol: `register(type,fn)` + `emit(type,payload)` |
| `element-registry.js` | 266 | Detects + tags editable elements with `data-hyp-id`; `roleOf`, `regions`, `stripIds` |
| `selection.js` | 216 | Selection state + blue `hyp-selection-ring`; click delegation; `select/clear/current` |
| `history.js` | 114 | Unified undo/redo stack for ALL ops; Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y keyboard shortcuts |
| `commands.js` | 193 | Pure command factory: `text/format/resize/move/colorToken/colorElement/comment` → `{do,undo,label}` |
| `text-edit.js` | 182 | Double-click → `contenteditable` lifecycle; commit on blur/Esc |
| `text-format.js` | 148 | Bold/italic/fontInc/fontDec via `execCommand` + custom font-size span logic |
| `resize.js` | 329 | Flow-aware resize via Moveable in-iframe; role-aware (`flex-child`, `grid-child`, `absolute`, `block`); emits `geometry-changed` |
| `move.js` | 306 | Transform-translate drag via Moveable in-iframe; writes only `transform: translate()`; emits `out-of-flow` |
| `color.js` | 165 | `:root` token mutation + per-element inline-style color; `readPalette/applyToken/applyElement` |
| `comments.js` | 510 | Comment store, 5-field anchor key, JSON island read/write, floating markers, reply/resolve |
| `serializer.js` | 257 | Clone → strip `hyp-`chrome + `data-hyp-*` + runtime script → re-embed comment island → node-count guard → standalone HTML |

### `server/`

| File | ~Lines | Purpose |
|---|---|---|
| `server.py` | 167 | stdlib `ThreadingHTTPServer`; routes `GET /app/*`, `GET /runtime/*`, `GET /doc/*`, `POST /api/open`, `POST /api/save-as` |
| `api.py` | 73 | Pure handlers: `handle_open(payload)` reads file, re-points `/doc/` root; `handle_save_as(payload)` writes file |

### `docs/`

| File / Dir | ~Lines | Purpose |
|---|---|---|
| `build-log.md` | 287 | Chronological build progress log |
| `decision-log.md` | 60 | Locked architectural decisions (A1–A12, D1–D6) |
| `fixture-profiles.md` | — | Analysis of the two test fixtures (DECK + REPORT) |
| `kimi-cheatsheet.md` | — | Dispatch instructions for kimi coding agents |
| `learnings.md` | 19 | Post-build learnings (compounded) |
| `research-oss.md` | — | OSS library research (Moveable, Coloris, DOMPurify) |
| `spec/01-architecture.md` | — | Component diagram, isolation model, routes |
| `spec/02-html-convention.md` | — | HTML fixture conventions, detection heuristics |
| `spec/03-module-map.md` | — | Full file tree with public contracts |
| `spec/04-implementation-plan.md` | 102 | **Original plan document.** Phased task table T1–T21, status column, acceptance criteria |
| `spec/05-verification-plan.md` | — | Verification case definitions (V-*) |
| `spec/review-log.md` | — | Spec review notes |
| `plan/hypresent-v1/hypresent-v1-plan.md` | 111 | **Execution index** for the v1 plan; dependency graph; task list with status checkboxes |
| `plan/hypresent-v1/shape.md` | — | Context, decisions, discoveries (append-only) |
| `plan/hypresent-v1/learnings.md` | — | Phase-level learnings |
| `plan/hypresent-v1/phase-1/` | — | Task files T1, T3–T5, T8, T9 + CP1 |
| `plan/hypresent-v1/phase-2/` | — | Task files T10, T12–T15 + CP2 |
| `plan/hypresent-v1/phase-3/` | — | Task files T17, T18 + CP3 |
| `plan/hypresent-v1/phase-final/` | — | FINAL CP task file |
| `verification/foundation-smoke/result.md` | — | Foundation smoke test results |
| `verification/cp1/result.md` | — | CP1 verification results |
| `verification/cp2/result.md` | — | CP2 verification results (dated 2026-06-03) |

---

## 3. Runtime Architecture

### 3a. How the editor loads / renders user HTML

The user document is loaded into a **same-origin `<iframe>`** (never the parent document). Flow:

1. User types an absolute path into `#open-path-input` and clicks Open.
2. `main.js` calls `file-controls.js:openFile(path, iframe)`.
3. `openFile` POSTs `{path}` to `/api/open`; the server reads the file from disk, sets `/doc/` root to the file's parent directory, and returns `{html, dir, name}`.
4. `openFile` sets `iframe.src = '/doc/' + encodeURIComponent(name)` — the browser fetches the document via the server's `/doc/` static route.
5. On `iframe load`, a `<script type="module" src="/runtime/js/runtime-main.js">` is injected into `iframe.contentDocument.head`. The absolute `/runtime/` path ensures the runtime's ES-module import chain resolves against the server origin, not the document's `/doc/` directory.
6. `runtime-main.js` boots: calls `tag()` (element-registry), registers bridge commands, loads the comment island, and emits `ready`.

The parent creates a `bridge` object (one per document load) via `createBridge(iframe)`. All subsequent interactions go through `bridge.command(type, payload)` postMessage round-trips.

### 3b. Selection model

Click-to-select: `selection.js` attaches a `document.addEventListener('click', ...)` in the iframe that walks up from the event target to the nearest `data-hyp-id` element and calls `select(hypId)`. Selection draws an absolutely-positioned `div.hyp-selection-ring` (blue 2px outline overlay). `clear()` / `select()` emit `selection-changed` to the parent bridge.

Text edit: double-click triggers `text-edit.js`, which calls `enterEdit(hypId)` → sets `contenteditable="true"` → commits on blur/Esc.

Resize / move tool: activated via `bridge.command('set-tool', {tool:'resize'|'move'})`. The Undo/Redo toolbar buttons send `bridge.command('undo'/'redo')`. There is no toolbar button for `set-tool` in the current `index.html` — the parent shell exposes no UI affordance to switch between the edit, resize, and move tools.

### 3c. Event wiring

- `bridge-parent.js`: parent listens for `postMessage` with `{source:'hyp', kind:'response'|'event'}`.
- `bridge-iframe.js`: iframe listens for `{source:'hyp', kind:'command'}` and dispatches to the registered handler.
- Events from the iframe to parent: `ready`, `selection-changed`, `dirty-changed`, `history-changed`, `comment-anchor-clicked`, `geometry-changed`, `out-of-flow`, `error`.
- All messages are origin-filtered (`event.origin !== location.origin → return`).

### 3d. Module layout

Multi-module, not monolithic. Two domains:

- **Shell (parent):** `main.js`, `bridge-parent.js`, `file-controls.js`, `color-popover.js`, `api-client.js` — plus `shell.css` and `index.html`.
- **Runtime (iframe):** 13 single-purpose ES modules imported by `runtime-main.js`. Each module has a declared public contract per `docs/spec/03-module-map.md`.

### 3e. JS libraries used

| Library | How delivered | Used in |
|---|---|---|
| Moveable.js | Vendored UMD at `app/js/vendor/moveable.min.js` | Parent: loaded in `index.html` `<head>` (`window.Moveable`). Runtime: both `resize.js` and `move.js` inject the same script into the iframe via dynamic `<script src="/app/js/vendor/moveable.min.js">` on demand. |
| Coloris | Vendored ES module at `app/js/vendor/coloris.min.js` + `coloris.css` | Parent: imported by `main.js` and `color-popover.js`. `Coloris.init()` called once; `Coloris.wrap('.hyp-coloris-input')` called after rendering each color input batch. |
| DOMPurify | Vendored at `app/js/vendor/purify.min.js` | Dynamically imported in `main.js` (optional; non-critical). NOT used by the serializer. Intended for optional comment text sanitisation. |

No package.json, no build step, no CDN references in the app itself. All libraries are vendored and served locally.

---

## 4. Open / Save

### Open

- **UI:** text input `#open-path-input` + "Open…" button in the toolbar.
- **Flow:** `POST /api/open` with `{path: absolutePathString}`. Server reads the file with `pathlib.Path(path_str).read_text(encoding='utf-8')`, re-points `_doc_root` to the file's parent directory, returns `{html, dir, name}`. Client then sets `iframe.src = '/doc/' + name`.
- **No file picker dialog.** The user must type or paste the absolute path.

### Save As

- **UI:** text input `#save-as-path-input` (auto-populated with `<dir>/<name>-edited.html` on open) + "Save As…" button.
- **Flow:** `bridge.command('serialize')` → `POST /api/save-as` with `{path, html}`. Server writes via `pathlib.Path(path_str).write_text(html, encoding='utf-8')`. Parent directory must already exist.

### Python server

- **File:** `server/server.py`
- **Framework:** Python stdlib only — `http.server.ThreadingHTTPServer` + `http.server.BaseHTTPRequestHandler`. No Flask, no third-party dependencies.
- **Routes:** `GET /app/*`, `GET /runtime/*`, `GET /doc/*` (static), `POST /api/open`, `POST /api/save-as`.
- **Start command:** `python server/server.py` (default `127.0.0.1:8765`). Optional args: `python server/server.py <host> <port>`.
- **api.py:** pure request handlers, no HTTP logic; registered via callback to avoid circular imports.

---

## 5. Element Move / Resize

Both features are fully implemented and have passed verification (with the caveats noted in CP2 result).

### Resize (`runtime/js/resize.js`, ~329 lines)

**Mechanism:** Moveable (UMD) is loaded into the iframe on demand via dynamic `<script>` injection. On `begin(hypId)`, a `div.hyp-moveable-wrapper` (fixed, full-viewport, pointer-events:none, z-index:999998) is appended to `document.body` and a `new window.Moveable(wrapper, {target:el, resizable:true, edge:true, throttleResize:1})` is created. Moveable handles are rendered over the target element.

**Sizing logic (flow-aware):** On `resizeEnd`, `roleOf(el)` determines the sizing strategy:
- `flex-child` in a row flex container → writes `flex-basis` (main axis) and `height`.
- `flex-child` in a column flex container → writes `flex-basis` and `width`.
- `absolute` → writes `width`, `height`, and adjusts `top`/`left` when resizing from the NW/N/W handles (delta correction).
- `block`/`grid-child` → writes `width` and `height`.

**Never converts to absolute positioning** (constraint D1). Commits a `resize` command to `history.push`.

**Selection polling:** a 150ms `setInterval` polls `current()` to update the Moveable target when the user clicks a different element while the resize tool is active.

**Snapping / alignment guidelines:** none. No snap-to-grid, no snap-to-sibling, no alignment guides implemented.

**Known issues from CP2:** none blocking for resize itself. The `set-tool` bridge command works; the missing piece is the parent shell UI (no toolbar button to activate resize/move mode).

### Move (`runtime/js/move.js`, ~306 lines)

**Mechanism:** Same Moveable injection pattern. `new window.Moveable(wrapper, {target:el, draggable:true, resizable:false})`. On drag, writes `transform: translate(newX px, newY px)` to `el.style`. Existing translate is parsed (handles `translate()`, `translateX/Y()`, `translate3d()`) and accumulated additively (`baseTranslate + e.translate`).

**Writes only `transform: translate()`** (constraint D2). Does not modify `top`/`left`/`margin`. Emits `out-of-flow {bool}` when the translate is non-zero.

**Snapping / alignment guidelines:** none.

**Assessment:** both resize and move implementations are complete at the code level. The interaction flow (Moveable library, event capture, command+history integration) is sound. Two structural gaps:
1. No toolbar buttons expose `set-tool` in the parent shell — the tool must be activated programmatically.
2. There is no "return to edit mode" affordance in the UI after activating resize/move.

---

## 6. Color Editing

**Token (palette) path:** `color.js:readPalette()` scans all `document.styleSheets` for `:root` rules and collects CSS custom properties whose value parses as a valid color (canvas fillStyle test). Also reads `document.documentElement.style` for runtime overrides. Exposed in the color panel as a list of token inputs.

**`applyToken(name, value)`:** sets `document.documentElement.style.setProperty(name, value)`. Creates a `colorToken` command (captures prior inline value for undo).

**Per-element path:** `color.js:applyElement(hypId, prop, value)` — sets `el.style.setProperty(prop, value)`. The `color-popover.js` panel exposes two per-element rows: **Text** (`prop = color`) and **Background** (`prop = background-color`).

**Border / edge color:** `color.js` declares `COLOR_PROPERTIES` including `border-color`, `border-top-color`, `border-right-color`, `border-bottom-color`, `border-left-color`, `fill`, and `stroke` — these are used in `discoverInlineSites()` to find existing inline color values, but the `color-popover.js` UI **only renders Text and Background inputs** for the selected element. There is no UI to set border colors per-element. The `apply-color` bridge command accepts any `prop` string, so border color can be applied programmatically but has no shell UI affordance.

---

## 7. Comments Feature

**Creation:** user selects an element (click), presses "💬" in the toolbar, enters comment text in a `prompt()` dialog. Author name is stored in `localStorage` (one-time `prompt()` on first use).

**Storage format:** a `<script type="application/json" id="hyp-comments">` island element embedded in the document `<body>`. Contains a JSON array of thread objects. Structure per thread:

```json
{
  "id": "1",
  "anchor": { "hook": null, "path": "div:1/p:2", "nativeId": "section-id", "contentHash": "abc12345", "siblingIndex": 0 },
  "contextText": "first 80 chars of element textContent",
  "author": "Name",
  "createdAt": "2026-06-03T...",
  "body": "comment text",
  "resolved": false,
  "replies": [{ "author": "...", "body": "...", "createdAt": "..." }]
}
```

**Anchor key:** 5-field collision-resistant key: `data-hyp-hook` attribute (explicit hook, highest priority) > nearest-native-id + DOM path (tag:nth-of-type) + content hash (FNV-1a of first 32 chars of textContent) + sibling index.

**Persistence:** `writeIsland()` is called on every mutation (add/reply/resolve). Serializer re-embeds the island after stripping `hyp-` chrome, so comments survive a Save-As round-trip.

**Visual markers:** `div.hyp-comment-marker` (20px circle, absolute-positioned, appended to `document.body`) floats over the anchored element. Yellow = open, grey = resolved. Click on marker emits `comment-anchor-clicked` to parent.

**Side panel:** `main.js` renders thread objects into `#comment-threads` and `#comment-unanchored` divs. Unresolvable threads are shown in an "Unanchored" section.

**Undo/redo:** all comment mutations (add, reply, resolve) go through `history.push` with captured do/undo closures.

**Known bug (CP2 B-PANEL):** `createColorPopover` replaces the entire `.shell-panel` innerHTML with the color panel, destroying the `#comment-threads`, `#comment-unanchored`, and `#outline-list` DOM nodes. Comment data and markers are correct; only the panel UI is invisible. The fix — use a dedicated child container — was identified in CP2 but not yet applied.

---

## 8. Undo / Redo

**Implementation:** `runtime/js/history.js` — single linear stack (`stack[]`) with a cursor integer. One stack for ALL operation types: text edit, text format, resize, move, color token, color element, comment add/reply/resolve.

**`push(cmd)`:** runs `cmd.do()`, appends to stack, advances cursor, truncates redo tail.
**`undo()`/`redo()`:** invoke `cmd.undo()`/`cmd.do()` at the appropriate cursor position.
**`state()` → `{cursor, canUndo, canRedo}`** — emitted as `history-changed` event; parent wires Undo/Redo button `disabled` state.

**Keyboard:** `Ctrl+Z` (undo), `Ctrl+Shift+Z` and `Ctrl+Y` (redo) — scoped to skip native form controls (`input`, `textarea`, `select`).

**Toolbar buttons:** "Undo" and "Redo" buttons exist in `index.html` but have no `id` attributes; `main.js` locates them by `textContent` scan (`Array.from(querySelectorAll).find(b => b.textContent.trim() === 'Undo')`). Both are wired and functional per CP2 verification.

---

## 9. Docs Inventory

| Path | Summary |
|---|---|
| `docs/spec/01-architecture.md` | Component diagram, isolation model, server routes, serialization flow, coexistence rules |
| `docs/spec/02-html-convention.md` | HTML fixture conventions, element detection heuristics (H1–H9), data-hyp-* attribute contracts |
| `docs/spec/03-module-map.md` | Full file tree with one-line purpose and public contract per module |
| `docs/spec/04-implementation-plan.md` | **ORIGINAL PLAN DOCUMENT.** Phased task table T1–T21 with Goal, Files, Depends-on, Public-Contract, Acceptance, Parallel-safe, Status. All tasks DONE. Authoritative contract for every task. |
| `docs/spec/05-verification-plan.md` | Verification case definitions (V-BOOT, V-SEL, V-TXT, V-FMT, V-RSZ, V-MOV, V-COL, V-CMT, V-HIST, V-OPEN, V-SAVE) |
| `docs/spec/review-log.md` | Spec review notes |
| `docs/decision-log.md` | Locked decisions A1–A12 (architectural) and D1–D6 (feature choices) |
| `docs/build-log.md` | Chronological agent-driven build log |
| `docs/learnings.md` | Post-build learnings (trimmed, compounded) |
| `docs/fixture-profiles.md` | Analysis of DECK and REPORT fixtures |
| `docs/kimi-cheatsheet.md` | How to dispatch kimi coding agents for this project |
| `docs/research-oss.md` | OSS library research backing D3/D5 decisions |
| `docs/plan/hypresent-v1/hypresent-v1-plan.md` | Execution index; dependency Mermaid graph; task list (all DONE) |
| `docs/plan/hypresent-v1/shape.md` | Context, locked decisions, discovery log (append-only) |
| `docs/plan/hypresent-v1/learnings.md` | Phase-level learnings |
| `docs/verification/foundation-smoke/result.md` | Foundation smoke test pass |
| `docs/verification/cp1/result.md` | CP1 (Foundation) verification pass |
| `docs/verification/cp2/result.md` | CP2 (All features) verification — dated 2026-06-03, verdict RED: 2 bugs open (B-SERIALIZE, B-PANEL) |

**Original plan document:** `docs/spec/04-implementation-plan.md` — this is the single authoritative contract document; task files under `plan/` are supplementary execution wrappers.

### Plan features: implemented vs partial vs missing

| Feature | Status | Notes |
|---|---|---|
| Server (open + save-as JSON API) | **Implemented (DONE)** | T1 — passes V-OPEN, V-SAVE (without comments island) |
| App shell (toolbar, iframe, panels) | **Implemented (DONE)** | T2 |
| Iframe load + runtime injection | **Implemented (DONE)** | T3 |
| Parent↔iframe bridge | **Implemented (DONE)** | T4 |
| Element registry + data-hyp-id | **Implemented (DONE)** | T5 |
| Selection + visual ring | **Implemented (DONE)** | T6 |
| Command factory | **Implemented (DONE)** | T7 |
| Unified undo/redo history | **Implemented (DONE)** | T8; Ctrl+Z / toolbar wired |
| Serializer (strip + standalone HTML) | **Partial** | T9 — strip is correct and saves clean files; **B-SERIALIZE**: node-count guard off-by-one when a comment island exists (islandCount=1 should be 2); save aborts for any commented document |
| Text edit (double-click contenteditable) | **Implemented (DONE)** | T10 |
| Text format (bold/italic/font-size) | **Implemented (DONE)** | T11; minor cosmetic bug: consecutive A+/A- nests new spans instead of updating existing |
| Resize (flow-aware, Moveable) | **Implemented (DONE)** | T12; no toolbar button to activate resize mode in current shell |
| Move (transform-translate, Moveable) | **Implemented (DONE)** | T13; no toolbar button to activate move mode in current shell |
| Color editing (tokens + per-element) | **Implemented (DONE)** | T14 — text/background color in panel; border color detection exists but no panel UI |
| Comments (anchored, island, markers, panel) | **Partial** | T15 — data layer, markers, anchoring, undo all correct; **B-PANEL**: color-popover.js overwrites `.shell-panel` innerHTML, destroying `#comment-threads` / `#outline-list` DOM nodes; panel UI invisible |
| Outline / region navigator | **Implemented (DONE)** | T16 — data layer works; invisible due to B-PANEL |
| Save-As end-to-end wiring | **Partial** | T17 — wired; blocked for commented documents by B-SERIALIZE |
| README | **Implemented (DONE)** | T19 |

---

## 10. Sample / Test HTML Files

| File | Location | Structure |
|---|---|---|
| `tecer-gsmm-introduction.html` | `hypresent/` root | 10 `<section class="slide ...">` elements. Cover, 8 content slides, closing. All styles inline in a `<style>` block (no external CSS). Uses Google Fonts (CDN), Font Awesome (CDN), CSS custom properties (`--primary`, `--navy`, etc.) at `:root`. No `<script>`. Layout: mix of CSS Grid (`grid-2`, `grid-3`, `grid-4`), Flexbox (`.slide`, `.flow-diagram`, `.timeline`), and `position:absolute` (`.slide-number`, `.closing-wordmark`). Print media query for 1280×720 page size. |

There is no second fixture (REPORT) in this directory. The CP2 verification references a "REPORT" fixture that is not present in `hypresent/` — it was likely a separate file used during testing and not committed here.

---

## 11. Tests / Automation

No test files, test scripts, test framework configuration, or CI configuration exists in the `hypresent/` directory or visible in the rbtv repo root. Verification was performed manually via Chrome DevTools MCP during the plan execution phases. Results are documented in `docs/verification/cp1/result.md`, `docs/verification/cp2/result.md`, and `docs/verification/foundation-smoke/result.md`.

---

## 12. Git State

| Item | Value |
|---|---|
| Repo | `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv` |
| Current branch | `master` |
| Dirty state | One untracked file: `hypresent/tecer-gsmm-introduction.html` |
| Modified files | None |

The working tree is clean except for the untracked sample HTML file.

---

## 13. `docs/improvements-2026-06/` — Why This Location

The `docs/` directory already contains all project documentation. The plan phases used `docs/verification/` for test results and `docs/plan/` for planning artifacts. A session-scoped work folder under `docs/improvements-2026-06/` follows the same convention without creating a peer directory at the same level as `docs/` itself, which would violate the project's single-docs-root pattern. No `docs/work/` convention exists in the repo; the closest analogue is the verification result folders.

---

## 14. Top 3 Risks for Adding Drag / Resize / Reorder

### Risk 1 — No shell UI to activate resize/move mode; tool switching is headless

`resize.js` and `move.js` are fully implemented and verified, but `index.html` has no toolbar buttons for `set-tool`. Any new drag/resize feature work must add a tool-mode UI (toggle buttons, keyboard shortcuts, or always-on handles) to the parent shell. The current UX puts the user permanently in "edit text" mode with no visible affordance to switch tools. Adding reorder would require a third tool mode and a clear mode-indicator in the shell.

### Risk 2 — `color-popover.js` destroys the side panel on each bridge `ready` event (B-PANEL)

The color popover replaces `panelEl.innerHTML` with its own markup, wiping `#comment-threads`, `#comment-unanchored`, and `#outline-list`. Any new panel feature (e.g., a reorder or layer panel) added to `.shell-panel` will also be destroyed until B-PANEL is fixed. This is a prerequisite fix before any panel UI work.

### Risk 3 — Move writes `transform: translate()` additively over any existing transform on the element

`move.js` parses the existing `transform` style to extract the current translate and accumulates drag deltas. If the document's HTML already uses `transform` on an element for other purposes (rotate, scale, skew, matrix), the move implementation will read only the translate component and lose the rest on `onDrag` (it overwrites `el.style.transform` with a plain `translate()`). A reorder feature based on DOM mutation (moving elements in the tree) would need to handle the interaction between existing transforms and the editor's translate overlay. The current `serialize/undo` contracts assume `transform` is editor-owned; any document that uses `transform` natively will have silent data loss on move + save.
