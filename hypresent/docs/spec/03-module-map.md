# Hypresent — Module Map (03)

Full file/folder tree with a one-line purpose and the public interface (inputs/outputs) per module. Every module is small, single-purpose, and independently testable. No monolith (decision A6). Module boundaries are the unit of work for kimi tasks in `docs/spec/04-implementation-plan.md`.

Convention: parent-side modules run in the app shell; iframe-side modules run inside the document iframe (decisions A2/A3). All iframe-injected classes/ids are `hyp-`prefixed; all injected attributes are `data-hyp-*` (A12).

---

## 1. File / Folder Tree

```
hypresent/
├─ server/
│  ├─ server.py              # stdlib http.server: static app + /doc/ + JSON API + `/api/dialog-open`, `/api/dialog-save-as`, `/api/save` routes (+ test-only `/api/_test/set-dialog`)
│  └─ api.py                 # request handlers: open, save-as, (optional) pick + dialog handlers, open-path tracking, injectable dialog launcher
├─ app/                      # the editor app shell (parent page), served at /app/
│  ├─ index.html             # parent page: toolbar, panels, iframe mount
│  ├─ css/
│  │  └─ shell.css           # app-shell styling (parent only; never enters document)
│  └─ js/
│     ├─ main.js             # shell bootstrap: wires shell modules + bridge
│     ├─ shell/
│     │  ├─ toolbar.js        # toolbar UI: tool switch, B/I/font, undo/redo buttons
│     │  ├─ file-controls.js  # Open / Save As UI + calls to server API
│     │  ├─ color-popover.js  # palette editor + per-element color UI (wraps Coloris)
│     │  ├─ comment-composer.js # anchored comment composer popover (textarea + For-agents toggle + Save/Cancel); replaces prompt()
│     │  ├─ comment-panel.js  # side panel: thread list, popover open/close
│     │  └─ outline.js        # region/outline navigator (from runtime `ready` regions)
│     ├─ bridge/
│     │  └─ bridge-parent.js  # parent side of parent↔iframe protocol (cmd + events)
│     ├─ api-client.js        # fetch wrappers for /api/open, /api/save-as
│     └─ vendor/              # copied OSS, no build step, native ES modules
│        ├─ moveable.min.js
│        ├─ coloris.min.js
│        ├─ coloris.css
│        └─ purify.min.js
├─ runtime/                  # injected into the iframe (the edit-runtime)
│  └─ js/
│     ├─ runtime-main.js      # runtime bootstrap inside iframe; exposes window.hyp
│     ├─ bridge-iframe.js     # iframe side of the protocol (cmd dispatch + event emit)
│     ├─ element-registry.js  # detects editable elements, assigns/strips data-hyp-id
│     ├─ selection.js         # current selection state + visual hyp- selection ring
│     ├─ history.js           # unified command/inverse undo-redo stack (ALL ops)
│     ├─ commands.js          # command factory: builds {do, undo} for each op type + `reorder`, `colorBorder`; `move` now writes the CSS `translate` property
│     ├─ text-edit.js         # contenteditable lifecycle (double-click → edit → commit)
│     ├─ text-format.js       # bold/italic/font-size via execCommand + Selection
│     ├─ interaction.js       # single combined Moveable (drag+resize+snap+Slides guides); on-drop hit-test → reorder/re-parent/keep-translate (FLIP); commits one history command. begin via `mount(hypId)`; `unmount/suspend/resume/remount`
│     ├─ reorder.js           # pure drop-classification helpers: `classifyDrop`, `isContainer`, `dominantAxis`, `midpointBefore`, `axisFromDisplay`
│     ├─ resize.js            # flow-aware resize (Moveable) per D1 — REMOVED in v2 (folded into interaction.js)
│     ├─ move.js              # transform-translate move (Moveable) per D2 + out-of-flow flag — REMOVED in v2 (folded into interaction.js)
│     ├─ color.js             # palette token mutation + per-element + inline-style color (D6) + border-color routing (auto-1px, U6), `readElementBorder`/`readElementColors`
│     ├─ comments.js          # comment store, anchors, JSON island read/write (D4) + `agentInstruction` flag, `setAgentInstruction`, `buildAgentBlock`, `reanchorAfterMove`
│     └─ serializer.js        # clone → strip ALL hyp chrome → re-embed island → guard → standalone html (A8/A11; no doc-body sanitizer) + agent-block head insertion + revised node-count guard (agentBlockCount + pre-existing-block sweep)
├─ docs/                     # specs, plan, decision log (this folder)
└─ README.md                 # run command + overview (created in plan)
```

---

## 2. Server Modules

### server/server.py — static + doc serving + API router
- **Purpose:** stdlib-only HTTP server; serves the app shell, serves the injected edit-runtime, serves the open document's directory under `/doc/`, routes the JSON API. No Flask (A10).
- **Inputs:** CLI: host/port (defaults `127.0.0.1:8765`). Runtime: HTTP requests.
- **Outputs:** static files; delegates `/api/*` to `api.py`. `/app/*` and `/runtime/*` are FIXED static roots anchored at the app's install dir (`app/` and `runtime/` respectively); `/doc/*` is a MUTABLE root re-pointed to the currently-open file's directory on each `open`.
- **Public surface:** `run(host, port)`; route table `GET /app/*` (static app shell), `GET /runtime/*` (static edit-runtime from the app's own `runtime/` dir — NEVER from `/doc/`), `GET /doc/*` (open file's dir), `POST /api/open`, `POST /api/save-as`, optional `GET /api/pick`. The `/runtime/*` route is what lets the iframe-injected `<script type="module" src="/runtime/js/runtime-main.js">` and its `import` chain resolve regardless of which document is open (`01` §8).

### server/api.py — open / save-as handlers
- **Purpose:** read a file from disk by absolute path; write a standalone HTML to disk by absolute path.
- **Inputs:** `open` → `{path}`; `save-as` → `{path, html}`.
- **Outputs:** `open` → `{html, dir, name}` (200) or `{error}` (404/500); `save-as` → `{ok, path}` (200) or `{error}` (500). Sets the server's `/doc/` base to the opened file's dir.
- **Contract:** path is validated as an existing readable file (open) / writable target (save-as); never executes file content; rejects directory traversal outside an allowed root if one is configured.

---

## 3. App-Shell Modules (parent page)

### app/js/main.js — shell bootstrap
- **Purpose:** instantiate shell modules, create the bridge, mount the iframe, wire events.
- **In/Out:** in: DOM ready; out: a live editor session. No business logic of its own.

### app/js/shell/toolbar.js — toolbar UI
- **Purpose:** tool switch (edit/resize/move/comment), B/I/font±, undo/redo buttons.
- **Inputs:** user clicks; `selection-changed`/`history-changed` events (to set enabled state).
- **Outputs:** bridge commands `set-tool`, `format`, `undo`, `redo`.

### app/js/shell/file-controls.js — Open / Save As UI
- **Purpose:** drive open and save flows.
- **Inputs:** user actions; a path string (from a text field or `/api/pick`).
- **Outputs:** `api-client.open(path)` then sets iframe src; `bridge.command('serialize')` then `api-client.saveAs(path, html)`. Reflects `dirty-changed`.

### app/js/shell/color-popover.js — color UI (wraps Coloris)
- **Purpose:** palette editor (token list → color inputs) and per-element override input.
- **Inputs:** `palette-read` result (tokens + inline sites); user color choices.
- **Outputs:** bridge `apply-color {scope:'token'|'element', target, value}`.

### app/js/shell/comment-panel.js — comment side panel + popover
- **Purpose:** render thread list, open/close anchored popovers, capture add/reply/resolve and the one-time author name.
- **Inputs:** `comments-read` result; `comment-anchor-clicked`/`comment-requested` events; `localStorage` author name.
- **Outputs:** bridge `add-comment`/`reply-comment`/`resolve-comment`.

### app/js/shell/outline.js — region navigator
- **Purpose:** list detected regions; clicking scrolls/selects in the iframe.
- **Inputs:** `ready` event regions; user clicks.
- **Outputs:** bridge `select {hypId}`.

### app/js/bridge/bridge-parent.js — parent side of protocol
- **Purpose:** send commands into the iframe runtime; receive and dispatch runtime events (decision §3 of architecture).
- **Inputs:** command calls from shell modules; `message` events from the iframe.
- **Outputs:** `command(type, payload) → Promise<result>`; `on(eventType, handler)`. Filters by `origin` + `source:'hyp'`.

### app/js/api-client.js — server API wrappers
- **Purpose:** typed fetch wrappers.
- **In/Out:** `open(path) → {html,dir,name}`; `saveAs(path, html) → {ok,path}`; throws on non-2xx with server `{error}`.

---

## 4. Iframe Runtime Modules

### runtime/js/runtime-main.js — runtime bootstrap
- **Purpose:** boot inside the iframe, build registry, parse comment island, read tokens, expose `window.hyp`, emit `ready`.
- **In/Out:** in: iframe `load`; out: `window.hyp` command object + `ready` event.
- **Load origin:** injected by the parent as `<script type="module" src="/runtime/js/runtime-main.js">` (absolute, served by the fixed `/runtime/*` route — `01` §8). Its `import` statements reference sibling runtime modules by relative path (resolving against `/runtime/js/`) and vendored libs by absolute `/app/js/vendor/...`. Never imports from `/doc/`.

### runtime/js/bridge-iframe.js — iframe side of protocol
- **Purpose:** receive parent commands and dispatch to modules; emit events to parent.
- **In/Out:** `command(type, payload)`; `emit(type, payload)` → `postMessage`.

### runtime/js/element-registry.js — element detection + id tagging
- **Purpose:** detect editable elements (per `02-html-convention.md` §1/§4), assign additive `data-hyp-id`, record original `contenteditable`/id state, resolve id↔node, and strip `data-hyp-id` on demand.
- **Inputs:** the iframe `document`.
- **Outputs:** `tag()`, `byId(hypId) → Element|null`, `idOf(el) → hypId`, `roleOf(el) → 'flex-child'|'grid-child'|'absolute'|'block'`, `regions() → [{hypId,label}]`, `stripIds(clone)`. NEVER mutates non-`hyp` attributes.

### runtime/js/selection.js — selection state
- **Purpose:** track the selected element; draw a `hyp-`class selection ring; clear on demand.
- **In/Out:** `select(hypId)`, `clear()`, `current() → {hypId, role, rect, isText}`; emits `selection-changed`.

### runtime/js/history.js — unified undo/redo stack
- **Purpose:** single linear stack of commands covering text, format, resize, move, color, comments (A7). Cursor-based; truncates redo tail on new push.
- **In/Out:** `push(command)`, `undo()`, `redo()`, `state() → {cursor,canUndo,canRedo}`; emits `history-changed`. A `command` is `{do(), undo(), label}`.

### runtime/js/commands.js — command factory
- **Purpose:** build `{do, undo, label}` objects for each operation type, capturing the inverse at creation (e.g., previous text, previous style value, previous transform).
- **In/Out:** `text(...)`, `format(...)`, `resize(...)`, `move(...)`, `colorToken(...)`, `colorElement(...)`, `comment(...)` → command. Pure; applies nothing itself — `history` runs `do()`.

### runtime/js/text-edit.js — contenteditable editing
- **Purpose:** double-click a text-editable element → set `contenteditable` (recording prior state) → commit on blur/Esc as a text command.
- **In/Out:** in: selection + double-click; out: a text command pushed to history; emits nothing extra. Excludes SVG text/path (per convention).

### runtime/js/text-format.js — inline formatting
- **Purpose:** apply bold/italic/font-size to the current Selection via `execCommand` + Selection API fallback.
- **In/Out:** `apply(op)` where op ∈ {bold,italic,fontInc,fontDec}; produces a format command. Operates only within an active `contenteditable` text edit.

### runtime/js/resize.js — flow-aware resize (D1)
- **Purpose:** mount Moveable on the selected element (inside iframe, A5); on resize-end compute the correct sizing property from layout role and write `width`/`height`/`flex-basis`/grid track — NEVER convert to absolute.
- **In/Out:** `begin(hypId)`, `end()`; emits `geometry-changed`; pushes a resize command (before/after sizing values).

### runtime/js/move.js — transform-translate move (D2)
- **Purpose:** mount Moveable in drag mode; write ONLY `transform: translate()`; compute and emit out-of-flow status after each drag.
- **In/Out:** `begin(hypId)`, `end()`; emits `geometry-changed` + `out-of-flow {bool}`; pushes a move command (before/after transform).

### runtime/js/color.js — recolor (D6)
- **Purpose:** (a) mutate a `:root` token via `documentElement.style.setProperty`; (b) per-element override via a `hyp-`scoped inline style; (c) mutate existing inline `style=` colors that sit outside the variable system.
- **In/Out:** `readPalette() → {tokens[], inlineSites[]}`; `applyToken(name,value)`; `applyElement(hypId, prop, value)`; each produces a color command. Per-element overrides are applied so they serialize cleanly (inline style on the element, not an injected stylesheet).

### runtime/js/comments.js — comment store + island (D4)
- **Purpose:** in-memory thread store; read/write the `<script type="application/json" id="hyp-comments">` island; resolve anchors to live elements using the collision-resistant anchor-key contract (`01` §6.1) — survives the `data-hyp-id` strip and disambiguates repeated identical siblings; manage add/reply/resolve; never lose a thread (unresolvable → "unanchored"). Comment text is rendered via `textContent` (XSS-safe); DOMPurify on comment text is OPTIONAL belt-and-suspenders only (A11), never a serialization step.
- **In/Out:** `load(islandJson)`, `toJson()`, `add(hypId,body,author)`, `reply(commentId,...)`, `resolve(commentId)`, `threads()`, `anchorRect(commentId)`; `buildAnchorKey(el)` and `matchAnchor(anchor)→Element|null` per `01` §6.1; emits `comment-anchor-clicked`/`comment-requested`. Each mutation produces a command (undoable).

### runtime/js/serializer.js — standalone HTML emit (A8/A11)
- **Purpose:** clone documentElement → strip ALL `hyp-`/editor chrome (`hyp-` ids/classes/nodes, `data-hyp-*` attrs, the injected runtime `<script>`/`<style>`, injected inline styles) → restore original `contenteditable` → re-embed comment island → guard → emit `<!doctype html>` + outerHTML. NO whole-document DOMPurify/sanitizer pass: the document's OWN scripts/handlers/IIFE, `<style>`, SVG, and native `data-*` are preserved by NOT touching them (A8/A11). DOMPurify is NOT a serializer dependency.
- **In/Out:** `serialize() → htmlString`. Guard: pre/post node-count delta must equal (removed `hyp-` chrome nodes + re-embedded island); a delta outside that band aborts with an `error` event (never emit a damaged file). Order + strip contract per `01` §5.

---

## 5. Independent Testability Matrix

| Module | Isolated test (Chrome DevTools MCP) |
|--------|-------------------------------------|
| server.py / api.py | Hit `/api/open` and `/api/save-as` with a temp file; assert disk read/write + JSON. |
| element-registry | `evaluate_script`: assert every editable element has a `data-hyp-id`; native ids untouched; `stripIds` removes all. |
| selection | Click element → assert `selection-changed` payload + `hyp-`ring present, no doc class changed. |
| history | Apply N ops → undo N → assert DOM identical to pre-op snapshot; redo restores. |
| text-edit/format | Edit text + bold → assert text + `<b>` wrapper; undo reverts. |
| resize | Resize a flex child → assert `flex-basis`/`width` changed, `position` still not absolute. |
| move | Drag element → assert ONLY `transform` changed; out-of-flow event fires when dragged past flow box. |
| color | Mutate token → assert all bound elements recolor; per-element override → assert only that element; inline-style site → assert inline value changed. |
| comments | Add/reply/resolve → assert island JSON; reload → threads re-anchor. |
| serializer | Serialize → assert zero `hyp-`/`data-hyp-` artifacts, island present, document's own `<script>` retained, output re-opens and runs. |

Full per-module pass/fail criteria: `docs/spec/05-verification-plan.md`.
