# Hypresent — Build Log

Append-only record of the foundation build (Phase 1: T1–T4). One entry per task: task id, kimi prompt summary, files, verification method + result, deviations. All hypresent code is authored by the `kimi` CLI; the build-lead authors only this log.

---

## T1 — Stdlib HTTP server + open/save-as JSON API

- **Status:** PASS (VERIFIED — pre-existing code from prior lead; not rebuilt).
- **Kimi prompt summary:** N/A — `server/server.py` + `server/api.py` already existed on disk (authored by the prior lead before the crash). No kimi re-drive needed; the code satisfied the T1 contract on verification, so no fix prompt was dispatched.
- **Files:** `server/server.py`, `server/api.py` (both pre-existing, unchanged by this lead).
- **Verification method:** started the server in the background (`python server/server.py 127.0.0.1 8765`), then probed every route class with `curl`, then `Stop-Process`'d the server and confirmed port 8765 freed.
- **Verification result (all PASS):**
  - `POST /api/open {path}` → HTTP 200, body keys exactly `{html, dir, name}`; `html` equals the fixture on disk byte-for-byte (79902 chars); `dir` resolves to the opened file's own directory (mutable `/doc/` root re-pointed there).
  - `GET /doc/<name>` after open → HTTP 200, `Content-Type: text/html`, 84912 bytes = on-disk size (served bytes identical to disk).
  - `POST /api/save-as {path, html}` → HTTP 200, body `{ok:true, path}`; temp file written and read back equal (round-trip).
  - `GET /runtime/js/runtime-main.js` → HTTP 404 JSON (file not built until T3) — proves the FIXED `/runtime/*` static root is wired and distinct from the mutable `/doc/` root (confirmed by reading `server.py`: `RUNTIME_ROOT` anchored at the repo's own `runtime/` dir, never re-pointed).
  - `GET /app/` → HTTP 404 JSON (file not built until T2) — proves the FIXED `/app/*` static root is wired.
  - `POST /api/open` with a nonexistent path → HTTP 404 JSON `{error}` per architecture §7.
- **Contract conformance:** stdlib only (`http.server`, `json`, `mimetypes`, `pathlib`, `urllib`), no Flask (A10); never executes file content; directory-traversal guard rejects `..` and out-of-root resolution; three roots correct (`/app/*` fixed, `/runtime/*` fixed from the app's own `runtime/` dir, `/doc/*` mutable per open). Matches `04` T1 row, `01` §1/§8, `03` §2.
- **Deviations:** none. `save-as` does not auto-create missing parent directories (returns 500 if parent absent) — within contract ("validate writable target").

---

## T2 — App-shell parent page + static assets + vendored libs

- **Status:** PASS (kimi-authored).
- **Vendored libs (fetched by build-lead via curl — dependency acquisition, all MIT/Apache, all dependency-free / zero bare imports):**
  - `app/js/vendor/moveable.min.js` — Moveable 0.53.0, **UMD** self-contained bundle (245551 B). Source: `https://cdn.jsdelivr.net/npm/moveable@0.53.0/dist/moveable.min.js`. DECISION: chose the UMD build, not the ESM build — Moveable's `dist/moveable.esm.js` pulls a bare-import dependency tree (`framework-utils`, `croact`, `croact-moveable`, `@daybrush/utils`) that cannot resolve in a no-build browser. The invariant "prefer self-contained UMD/standalone bundles to avoid dependency graphs" applies directly. UMD sets `window.Moveable`; the shell loads it via a classic `<script>` (NOT `type=module`).
  - `app/js/vendor/coloris.min.js` — Coloris (`@melloware/coloris`) 0.25.0, **native ESM** build (43104 B, `export default Coloris`, zero bare imports). Source: `https://cdn.jsdelivr.net/npm/@melloware/coloris@0.25.0/dist/esm/coloris.js` (saved under the contract filename `coloris.min.js`).
  - `app/js/vendor/coloris.css` — 10943 B. Source: `https://cdn.jsdelivr.net/npm/@melloware/coloris@0.25.0/dist/coloris.css`.
  - `app/js/vendor/purify.min.js` — DOMPurify 3.4.8, **native ESM** build (86547 B, `export { purify as default }`). Source: `https://cdn.jsdelivr.net/npm/dompurify@3.4.8/dist/purify.es.mjs` (saved under the contract filename `purify.min.js`). OPTIONAL per A11 — shell imports it defensively (dynamic `import()` in try/catch) so its absence can never break boot.
- **Kimi prompt summary:** one foreground `kimi --quiet --max-ralph-iterations 30` call. Self-contained prompt: scope-locked to the three files; inlined no-build/native-ESM/Python-stdlib invariants, the `/app/`-rooted route/origin rules, the exact vendor filenames + their module format (Moveable UMD→classic script + `window.Moveable`; Coloris ESM→`import default`; DOMPurify optional defensive dynamic import), the public contract (toolbar placeholders B/I/A+/A-, Open/Save As, Undo/Redo; empty iframe mount; bootstrap stub with zero console/network errors), the namespacing mandate (no `hyp-` names — `hyp-` reserved for the runtime, not the shell), and acceptance.
- **Files (CREATE):** `app/index.html`, `app/css/shell.css`, `app/js/main.js`.
- **Verification method:** directory-delta confinement check (only the 3 declared files created, no stray writes); read all 3 files; `node --check app/js/main.js` (syntax PASS); `hyp-` leakage grep (NONE); import-path audit (all absolute `/app/`-rooted); then started the server and `curl`-probed the shell + every vendor asset for HTTP 200 + content-type; then stopped the server.
- **Verification result (all PASS):**
  - `GET /app/` and `/app/index.html` → 200 `text/html`; markup contains `shell-toolbar`, 8 `tool-btn`, `doc-frame` mount.
  - `GET /app/css/shell.css` → 200 `text/css`; `GET /app/js/main.js` → 200 `text/javascript`.
  - `GET` each vendor asset → 200 with correct content-type, ZERO 404s: `moveable.min.js` (text/javascript), `coloris.min.js` (text/javascript), `coloris.css` (text/css), `purify.min.js` (text/javascript).
  - `main.js`: ESM `import Coloris from '/app/js/vendor/coloris.min.js'`; reads `window.Moveable` (UMD global); DOMPurify via defensive dynamic `import()` in try/catch (optional). No `hyp-` names anywhere.
- **Deferred to browser checkpoint (CP1/T18, per spec):** definitive confirmation that the Coloris ESM `import` resolves at runtime and `window.Moveable` is a function in-browser. At the HTTP/syntax layer all preconditions are met (valid syntax, correct JS content-type, clean `export default`, no 404s).
- **Deviations:** Coloris and DOMPurify are saved under the contract's `*.min.js` filenames but their CONTENT is the self-contained ESM build (the ESM is the dependency-free, native-import-friendly form the T2 contract requires; the `.min` suffix is a filename, not a format claim). Moveable remains UMD under `moveable.min.js` (its only dependency-free form). No other deviations; scope confined to the 3 declared files.

---

## T3 — Iframe load + runtime boot stub

- **Status:** PASS (kimi-authored). Browser-level acceptance (V-OPEN-1/2: iframe render + document-JS run + `ready` round-trip) deferred to the CP1/T18 browser checkpoint per plan; static/syntax/route layer fully verified here.
- **Kimi prompt summary:** one foreground `kimi --quiet --max-ralph-iterations 30` call. Self-contained prompt: scope-locked to the three files (explicit "do NOT modify main.js/index.html/server/vendor"); inlined the exact route table (`/app/*`, fixed `/runtime/*`, mutable `/doc/*`, `/api/open`, `/api/save-as`), same-origin iframe model, the A12 namespacing rule, and the three public contracts verbatim — `api-client.open/saveAs` (POST JSON, throw `Error(server.error||statusText)` on non-2xx), `file-controls.openFile(path,iframe)` (call open → set `iframe.src=/doc/<name>` → `{once:true}` post-load listener injects `<script type="module" src="/runtime/js/runtime-main.js">` ABSOLUTE into the iframe doc, double-injection-guarded, no import-time side effects), and `runtime-main.js` boot stub (boot now if `readyState!=='loading'` else on DOMContentLoaded; set `window.hyp` stub; emit `ready` via `postMessage({source:'hyp',type:'ready',payload:{tokens:[],sections:[]}}, location.origin)`; import-free; no `hyp-` DOM artifacts).
- **Files (CREATE):** `app/js/api-client.js`, `app/js/shell/file-controls.js`, `runtime/js/runtime-main.js`.
- **Verification method:** directory-delta + mtime confinement check (proved T2's `index.html`/`shell.css`/`main.js` were NOT modified — their mtimes predate the T3 run and `main.js` still imports only Coloris/purify; only the 3 declared files written); read all 3; `node --check` on all 3 (syntax PASS); `hyp-` DOM-artifact scan (only `window.hyp` + `source:'hyp'` protocol tag — both allowed; zero `hyp-` classes/ids/attrs on document elements; zero `classList`/`setAttribute`/`.id=` doc mutations); absolute-URL audit; then HTTP-probed the new routes and stopped the server.
- **Verification result (all PASS):**
  - `GET /runtime/js/runtime-main.js` → 200 `text/javascript` (was 404 in T1; now serves the real boot stub). Body contains `window.hyp`, `postMessage`, `source:'hyp'`, `type:'ready'`.
  - `GET /app/js/api-client.js` and `GET /app/js/shell/file-controls.js` → 200 `text/javascript`.
  - **Fixed-route independence proof:** after `POST /api/open` re-points `/doc/` to the fixture's directory, `GET /runtime/js/runtime-main.js` STILL returns 200 — `/runtime/*` is anchored at the app's own dir, never affected by the `/doc/` re-point (matches `01` §8, A10). The runtime `<script>` src is ABSOLUTE `/runtime/...`, so its load + import chain resolve regardless of which document is open.
  - `node --check`: all 3 syntactically valid ES modules.
- **Note (not a defect):** with THIS fixture, `GET /doc/runtime/js/runtime-main.js` also returns 200 — only because the fixture happens to live at the hypresent repo root, so `/doc/` (re-pointed there) coincidentally contains a `runtime/` dir on disk. Irrelevant to correctness: the runtime is injected via the ABSOLUTE `/runtime/` src, never a `/doc/`-relative path, so loading is always from the fixed route. For a document outside the repo root, `/doc/runtime/...` would 404 while `/runtime/...` keeps serving.
- **Deviations:** none. Scope confined to the 3 declared files; T2 files untouched. `openFile` returns a promise resolving on iframe load (does not wait for `ready`, per contract). `initOpenControl` helper added as the contract's optional, side-effect-free export; nothing auto-runs on import.

---

## T4 — Parent ↔ iframe bridge

- **Status:** PASS (kimi-authored). Live command/event round-trip (parent `command('ping')`→`{pong:true}`; iframe `emit`→parent `on` handler; cross-origin/non-`hyp` drop) requires two live windows + postMessage — deferred to the CP1 browser checkpoint. Static/syntax/protocol/route layer fully verified here.
- **Kimi prompt summary:** one foreground `kimi --quiet --max-ralph-iterations 30` call. Self-contained prompt: scope-locked to the two files (explicit do-not-touch list of all 6 prior foundation files + server/docs/vendor); inlined the same-origin rule (all `postMessage` use `location.origin`; all inbound filtered by `event.origin===location.origin && event.data.source==='hyp'`), the A12 namespacing tag (`source:'hyp'`, no DOM mutation), and the full §3 protocol with exact envelopes — direction A parent→iframe COMMANDS as request/response correlated by a unique `id` (`{source:'hyp',kind:'command',id,type,payload}` → `{source:'hyp',kind:'response',id,ok,result|error}`), direction B iframe→parent EVENTS fire-and-forget (`{source:'hyp',kind:'event',type,payload}`); plus the two test handlers (`noop`, `ping`→`{pong:true}`), `register(type,handler)`, `emit(type,payload)`, and the acceptance cases.
- **Files (CREATE):** `app/js/bridge/bridge-parent.js`, `runtime/js/bridge-iframe.js`.
- **Verification method:** mtime confinement check (only the 2 declared files written at 11:43; all 6 prior foundation files have earlier mtimes — untouched); read both; `node --check` both (syntax PASS); DOM-mutation scan (NONE — no `classList`/`setAttribute`/`createElement`/`innerHTML`/`appendChild`/`querySelector`/`.id=`; pure messaging plumbing); protocol-envelope consistency grep (parent sends `kind:'command'`, handles `response`/`event`; iframe sends `kind:'event'`/`kind:'response'`, handles `command`; both filter origin + `source:'hyp'`; symmetric `id` echo); then HTTP-probed both routes + ran the full integration smoke; then stopped the server.
- **Verification result (all PASS):**
  - `GET /app/js/bridge/bridge-parent.js` → 200 `text/javascript`; exports `createBridge` returning `{command, on, off, destroy}`; `command` correlates by unique id with a 10s timeout cleared on response; `on` supports multiple handlers per type + returns unsubscribe; single `message` listener silently drops wrong-origin / non-`hyp` messages, resolves/rejects by id on `response`, dispatches to handlers on `event`. No import-time side effects (listener attaches only inside `createBridge`).
  - `GET /runtime/js/bridge-iframe.js` → 200 `text/javascript`; dispatch table seeded `noop`→undefined, `ping`→`{pong:true}`; `register` overwrites; `emit` posts `kind:'event'` to parent; single `message` listener drops wrong-origin / non-`hyp` / non-`command`, posts `{ok:false,error:'unknown command: ...'}` on missing handler, awaits handler in try/catch posting `{ok:true,result}` / `{ok:false,error}` with the same id. Listener attaches on load (correct — it is the command receiver).
  - `node --check`: both syntactically valid ES modules.
- **Deviations:** none. Scope confined to the 2 declared files; all prior foundation files untouched. Parent `command` includes an optional 10s timeout (contract marked it nice-to-have); cleared on response/destroy.

---

## Phase 1b — Part A: foundation boot-path wiring fixes (A1, A2, A3)

Three integration gaps from `docs/verification/foundation-smoke/result.md` (Notes 1–3) fixed in ONE foreground kimi call (the three gaps share the boot bootstrap across `main.js`/`runtime-main.js`/`index.html`, so a single sequential call avoids concurrent-edit conflict while keeping per-fix acceptance verifiable). All hypresent code authored by kimi; build-lead authored only this entry.

- **Status:** A1 FIXED · A2 FIXED · A3 FIXED (kimi-authored). Static/HTTP/syntax layer fully verified here; the live two-window bridge round-trip + `ready` reception are owned by the next browser pass (CP1/T18) per plan — see deferred note below.
- **Kimi prompt summary:** one `kimi --quiet --max-ralph-iterations 40` call with `--agent-file` stripping web tools (`.kimi-agent/code-agent.yaml`). Scope-locked to exactly 4 files (`app/index.html`, `app/js/main.js`, `app/js/shell/file-controls.js`, `runtime/js/runtime-main.js`); inlined the no-build/native-ESM/absolute-import invariants, the A12 namespacing rule (shell uses NO `hyp-` names; `hyp-` reserved for the runtime), the full verbatim current contents of all 4 files, the read-only interfaces of `api-client`/`bridge-parent`/`bridge-iframe`, the three protocol envelopes (`command`/`response`/`event`), and the three fixes with exact code shapes + per-fix acceptance.
- **Files (MODIFIED):** `app/index.html` (1357→1451 B), `app/js/main.js` (810→1686 B), `runtime/js/runtime-main.js` (414→384 B). `app/js/shell/file-controls.js` UNCHANGED (its `openFile`/`initOpenControl` were already correct; `main.js` does the click wiring directly so the bridge can be (re)bound after open).
- **A1 — Open control wired:** `index.html` adds `<input id="open-path-input">` + `id="open-btn"` on the existing "Open…" button (class `tool-btn` and label preserved; no `hyp-` names). `main.js` wires the click → `openFile(path, iframe)` → `apiClient.open` (POST `/api/open`) → `iframe.src="/doc/<name>"` → runtime injected on iframe `load`. Real-UI path; no `evaluate_script` fallback. Empty path is a no-op; open failure logs `console.error` and does not throw.
- **A2 — bridge auto-init on live load:** runtime side — `runtime-main.js` now `import { emit } from "/runtime/js/bridge-iframe.js"` (the import's side effect attaches the iframe command listener on a real page load, no harness). Parent side — `main.js` imports `createBridge` and defines `ensureBridge(iframe)` (destroys any prior bridge, creates a fresh one bound to the just-loaded iframe window, registers `on("ready")`); called immediately after `await openFile` resolves. The `on("ready")` listener is registered synchronously before the runtime module finishes loading, so the later `emit("ready")` is never missed (listener-before-emit ordering verified by reading both files).
- **A3 — `ready` envelope aligned:** `runtime-main.js` replaced the raw `window.parent.postMessage({source:'hyp',type:'ready',...})` (which lacked `kind` and was dropped by `bridge-parent.onMessage`) with `emit("ready", {tokens:[],sections:[]})`. The event shape now has a single source of truth — `bridge-iframe.emit` — producing `{source:'hyp',kind:'event',type:'ready',payload}`, which `bridge-parent` dispatches to `on('ready')`. `window.hyp` retained.
- **Verification method:** (1) file-manifest delta — exactly the 3 expected files changed, zero stray writes (`file-controls.js`, server, vendor, docs all untouched). (2) `node --check` on `main.js`, `runtime-main.js`, `file-controls.js` — all syntactically-valid ES modules. (3) read all 3 modified files + confirmed interface/acceptance/namespacing by inspection. (4) started the server (port 8765 freed first), HTTP-probed the boot path, asserted wiring present in SERVED bytes, exercised the real open flow, then `Stop-Process`'d the server and confirmed port 8765 free.
- **Verification result (all PASS):**
  - 6 boot-path routes 200 `text/javascript`/`text/html`: `/app/`, `/app/index.html`, `/app/js/main.js`, `/app/js/bridge/bridge-parent.js`, `/runtime/js/runtime-main.js`, `/runtime/js/bridge-iframe.js`.
  - Served-byte assertions: shell carries `id="open-btn"` + `id="open-path-input"`; `main.js` contains `createBridge` + `ensureBridge(iframe)`; `runtime-main.js` imports `bridge-iframe.js`, contains `emit("ready"`, and contains NO `postMessage` (the raw call is gone).
  - Real open flow: `POST /api/open {path:<abs fixture>}` → 200, `name=<deck fixture>`, html 79902 chars; `GET /doc/<name>` → 200 `text/html` 82000 B; `GET /runtime/js/runtime-main.js` STILL 200 after the `/doc/` re-point (fixed-route independence intact).
- **Deferred to the next browser pass (CP1/T18, NOT a blocker):** with a real document open in a browser, confirm (a) A2 — parent `bridge.command('ping')` resolves to `{pong:true}` after a normal open; (b) A3 — `bridge.on('ready')` actually fires on load. Both require two live windows + postMessage; every layer verifiable without a browser passed. This supersedes foundation-smoke Notes 1–3 (open button, bridge boot, `ready` envelope) — all three are now wired into the boot path.
- **Deviations:** none. Scope confined to the declared files; `file-controls.js` intentionally left unchanged (already correct).

---

## Integration HTTP smoke (T1–T4 combined)

- **Result:** PASS. Started the server; `POST /api/open` pointed `/doc/` at the workspace deck fixture; confirmed all three required route classes return 200:
  - App-shell route `GET /app/` → 200 `text/html`.
  - `GET /doc/<deck fixture>` → 200 `text/html`, 84912 B (= disk size).
  - `GET /runtime/js/runtime-main.js` and `GET /runtime/js/bridge-iframe.js` → 200 `text/javascript`.
- **Full foundation reachability sweep:** all 13 foundation assets (shell html/css/js, api-client, file-controls, bridge-parent, 4 vendored libs, runtime-main, bridge-iframe) return 200 — zero 404s.
- **Server lifecycle:** the server was started as a background process for each HTTP test and `Stop-Process`'d before every transition and before return; port 8765 confirmed free at the end; no orphaned python processes remain.

---

## Browser checkpoint (CP1) — deferred items (NOT a foundation blocker)

These require Chrome DevTools MCP (two live windows + real module resolution + postMessage) and are owned by CP1 / T18 per `04-implementation-plan.md`. They are NOT regressions — every layer verifiable without a browser passed:
- T2: confirm the Coloris ESM `import` resolves and `window.Moveable` is a function in-browser.
- T3: V-OPEN-1/2 — both fixtures render, the REPORT's own JS runs, the runtime module + its imports load from `/runtime/` and `/app/js/vendor/` with no 404, and the `ready` postMessage reaches the parent.
- T4: parent `command('ping')` resolves to `{pong:true}`; iframe `emit` fires a parent `on` handler; cross-origin / non-`hyp` messages are ignored by both bridges.

## T5 — Element registry

- **Status:** PASS (kimi-authored). Verified at CP1 (`docs/verification/cp1/result.md`): 337 (REPORT) / 345 (DECK) `[data-hyp-id]` tagged, native ids + native `data-*` untouched.
- **Kimi prompt summary:** one focused kimi run, scope-locked to `runtime/js/element-registry.js`; inlined the `02` §1/§4 detection rules, the additive-`data-hyp-id` + record-original-state contract, and the A12 never-touch-native mandate.
- **Files (CREATE):** `runtime/js/element-registry.js`.
- **Public surface:** `tag()`, `byId`, `idOf`, `roleOf`, `regions()`, `stripIds(clone)`.
- **Verification:** `node --check` PASS; browser-confirmed at CP1 (TAGGING row GREEN both fixtures — V-BOOT-3).

---

## T6 — Selection

- **Status:** PASS (kimi-authored). Verified at CP1: click → `hyp-` selection ring, exactly one ring (no dup), zero `hyp-` class tokens on the document's own elements.
- **Kimi prompt summary:** one focused kimi run, scope-locked to `runtime/js/selection.js`; inlined the `hyp-`-only ring rule and the `selection-changed` event contract.
- **Files (CREATE):** `runtime/js/selection.js`.
- **Public surface:** `select(hypId)`, `clear()`, `current()→{hypId,role,rect,isText}`; emits `selection-changed`.
- **Verification:** `node --check` PASS; browser-confirmed at CP1 (SELECTION row GREEN both fixtures — V-SEL-1/2/3; the self-activating click listener was confirmed live).

---

## T7 — Command factory

- **Status:** PASS (kimi-authored).
- **Kimi prompt summary:** one focused kimi run, scope-locked to `runtime/js/commands.js`; inlined the per-op factory list and the capture-inverse-at-creation contract (pure; applies nothing itself).
- **Files (CREATE):** `runtime/js/commands.js`.
- **Public surface:** `text/format/resize/move/colorToken/colorElement/comment(...)→{do,undo,label}`.
- **Verification:** `node --check` PASS; exercised live through `history` at CP1 (undo/redo command surface GREEN) and across every Phase-2 feature at CP2.

---

## T8 — Unified history

- **Status:** PASS (kimi-authored). Verified at CP1: `undo`/`redo` return `{cursor:-1,canUndo:false,canRedo:false}` on the empty stack (no feature ops yet), both `ok:true`, no error.
- **Kimi prompt summary:** one focused kimi run, scope-locked to `runtime/js/history.js`; inlined the single-linear-stack-across-ALL-ops mandate (A7), cursor + redo-tail truncation, and the `history-changed` event.
- **Files (CREATE):** `runtime/js/history.js`.
- **Public surface:** `push(cmd)` (runs `do()`), `undo()`, `redo()`, `state()→{cursor,canUndo,canRedo}`; emits `history-changed`.
- **Verification:** `node --check` PASS; browser-confirmed empty-stack behavior at CP1; full mixed-op LIFO/FIFO undo/redo confirmed at CP2 (REPORT Undo ×3 / Redo ×3 row GREEN).

---

## T9 — Serializer (strip-only)

- **Status:** PASS after CP1 fix (kimi-authored). Strip-only, namespace-stripping serializer per `01` §5 / A8 / A11 — NO whole-document DOMPurify pass.
- **Kimi prompt summary:** one focused kimi run, scope-locked to `runtime/js/serializer.js`; inlined the strict `01` §5 order (clone → strip ALL `hyp-` chrome + `data-hyp-*` + injected inline styles → restore original `contenteditable` → re-embed `#hyp-comments` island → node-count guard → emit), the explicit "DOMPurify is NOT imported here" rule, and the T9-scoped acceptance (chrome-free output, REPORT IIFE retained byte-for-byte, DECK gains no `<script>`).
- **Files (CREATE):** `runtime/js/serializer.js`.
- **Public surface:** `serialize()→htmlString`.
- **Verification + CP1 fix:** `node --check` PASS. CP1 browser pass exposed the only defect — `serialize()` returned `null` on BOTH fixtures because `countAllNodes()` used a `createTreeWalker` that EXCLUDES the subtree root, undercounting each removed top-level node (the injected runtime `<script>`, the selection ring) by 1 → node-count guard aborted. Root cause + fix in `docs/verification/cp1/result.md`: kimi fixed by counting the root (count starts at 1 per subtree). Re-verified GREEN at CP2 / final re-verify.

---

## Core-wiring step — runtime-main as boot orchestrator

- **Status:** PASS (kimi-authored). Makes `runtime/js/runtime-main.js` the real boot orchestrator over the foundation modules T5–T9.
- **Kimi prompt summary:** one focused kimi run on `runtime/js/runtime-main.js`; wired boot to call `tag()` (registry) and registered the bridge command surface — `serialize`, `undo`, `redo`, `get-selection`, `select`, `clear-selection` — over the iframe `bridge-iframe` dispatch table.
- **Files (UPDATE):** `runtime/js/runtime-main.js`.
- **Orchestration note:** the orchestrator drove kimi DIRECTLY for this and the subsequent feature runs. Build-lead sub-agents repeatedly returned mid-flight on long kimi calls — kimi runs exceeding ~10 min detach from the sub-agent's Bash shell — so the fix was orchestrator-level background runs.
- **Verification:** `node --check` PASS; the full command surface (`serialize`/`undo`/`redo`/`get-selection`/`select`/`clear-selection`) exercised live at CP1 over the documented `{source:'hyp',kind:'command'}` envelope.

---

## Browser checkpoint CP1 — foundation end-to-end

- **Stage:** `docs/verification/cp1/result.md`. Verdict: GREEN after the one fix below.
- **Result:** foundation, boot wiring, tagging, selection, doc-JS coexistence, and the undo/redo command surface PASS on BOTH fixtures. REPORT: 337 tagged, scroll-spy + progress bar survive; DECK: 345 tagged, 10 slides render. The single failure was the serializer (see T9) — `serialize()` returned `null` from a node-count guard off-by-one (`countAllNodes` TreeWalker excluded subtree roots, undercounting each removed subtree by 1). Kimi fixed (count starts at 1); re-verified GREEN downstream.

---

## T10 — Text edit

- **Status:** PASS (kimi-authored). Verified at CP2: real double-click set `contenteditable=true`, typed text committed on blur, `contenteditable` removed.
- **Kimi prompt summary:** one focused kimi run, scope-locked to `runtime/js/text-edit.js`; inlined the double-click lifecycle, SVG text/path exclusion, and commit-via-`commands.text`+`history`.
- **Files (CREATE):** `runtime/js/text-edit.js`.
- **Verification:** `node --check` PASS; browser-confirmed at CP2 (REPORT + DECK TEXT EDIT rows GREEN — V-TXT-1/2).

---

## T11 — Text format + toolbar wiring

- **Status:** PASS after CP2 re-run fix (kimi-authored). Bold/italic/font-size via `execCommand` + Selection within an active edit.
- **Kimi prompt summary:** one focused kimi run on `runtime/js/text-format.js` plus the toolbar wiring; inlined `apply(op)` for `bold/italic/fontInc/fontDec` and the push-format-command-to-history contract.
- **Files (CREATE):** `runtime/js/text-format.js`. **Toolbar wiring** landed in `app/js/main.js` + `app/index.html` (the B/I/A+/A- buttons), NOT in a separate `app/js/shell/toolbar.js` — the planned `toolbar.js` module was consolidated into `main.js`. DEVIATION from `03`/`04`'s file list; behavior contract unchanged.
- **Verification:** `node --check` PASS; browser-confirmed at CP2 (FORMAT row GREEN — `<b>`/`<i>`/font-size spans applied via the real toolbar). Residual font-size nesting on consecutive A-/A+ fixed in the CP2 re-run (see re-verify entry).

---

## T12 — Resize (flow-aware, D1)

- **Status:** PASS (kimi-authored). Moveable mounted in-iframe; `roleOf`-driven sizing; no absolute conversion.
- **Kimi prompt summary:** one focused kimi run on `runtime/js/resize.js`; inlined D1 (write `width`/`height`/`flex-basis`/grid track from layout role; NEVER force `position:absolute`), the in-iframe Moveable mount (A5), and the `geometry-changed` + resize-command contract.
- **Files (CREATE):** `runtime/js/resize.js`. (Resize tool wiring consolidated into `main.js`, not `toolbar.js`.)
- **Verification:** `node --check` PASS; browser-confirmed at CP2 (REPORT flex-child → `flex-basis:520px`, `position` stayed `static`; DECK flex-child → `flex-basis:300px` — V-RSZ-1/2/3, V-RSZ-NEG). Moveable handle drags driven via the documented `resize-commit` command (synthetic pointer events cannot satisfy gesto's pointer capture).

---

## T13 — Move (D2)

- **Status:** PASS (kimi-authored). Writes ONLY `transform: translate()`.
- **Kimi prompt summary:** one focused kimi run on `runtime/js/move.js`; inlined D2 (transform-translate only; no `top`/`left`/`margin`), the out-of-flow computation + `out-of-flow` event, and the move-command contract.
- **Files (CREATE):** `runtime/js/move.js`. (Move tool wiring consolidated into `main.js`.)
- **Verification:** `node --check` PASS; browser-confirmed at CP2 (REPORT `move-commit` wrote `transform: translate(60px, 40px)`, `position` stayed `static` — V-MOV-1/2/3/4). Drag driven via the documented `move-commit` command.

---

## T14 — Recolor (D6)

- **Status:** PASS (kimi-authored). CSS-var token mutation + per-element override + inline-style color; Coloris-backed popover.
- **Kimi prompt summary:** one focused kimi run on `runtime/js/color.js` + `app/js/shell/color-popover.js`; inlined D6 (token via `documentElement.style.setProperty`; per-element inline override; mutate inline `style=` colors outside `:root`), the `readPalette()` color-token filter (H9 fallback), and the color-command contract.
- **Files (CREATE):** `runtime/js/color.js`, `app/js/shell/color-popover.js`.
- **Verification:** `node --check` PASS; browser-confirmed at CP2 (REPORT `--blue` token recolored 45 elements in one op; per-element `color:#008800` scoped to one element, sibling unchanged; real Coloris picker opens — V-COL-1/2/3/4/5). The color popover wiped the shared side panel at first CP2 pass — fixed in the re-run (see re-verify entry).

---

## T15 — Comments (D4)

- **Status:** PASS after CP2 + re-run fixes (kimi-authored). Anchor-key per `01` §6.1; JSON island; name-once; add/reply/resolve; markers + panel.
- **Kimi prompt summary:** one focused kimi run on `runtime/js/comments.js` plus the comment-panel UI; inlined the verbatim 5-field collision-resistant anchor key (`01` §6.1) with its 4-rule match priority + never-lossy "unanchored" fallback, the `#hyp-comments` JSON island read/write, `textContent` rendering (XSS-safe), one-time author name in `localStorage`, and undoable mutations.
- **Files (CREATE):** `runtime/js/comments.js`. **Comment panel UI** (thread list, reply/resolve, name prompt, unanchored group) landed in `app/js/main.js` + `app/index.html`, NOT a separate `app/js/shell/comment-panel.js` — the planned `comment-panel.js` module was consolidated into `main.js`. DEVIATION from `03`/`04`'s file list; behavior contract unchanged.
- **Verification:** `node --check` PASS; browser-confirmed at CP2 + re-verify (name asked once → `localStorage`; markers anchor to elements; reply + resolve; second comment no re-prompt; commented Save-As round-trips and re-anchors on reopen — V-CMT-1/2/3/4/5). Two CP2 defects fixed in the re-run: a duplicate `threads` identifier (SyntaxError) and the island node-count (see CP2 + re-verify entries).

---

## T17 — Save-As wiring

- **Status:** PASS after CP2 re-run (kimi-authored). End-to-end Save As: `serialize` → `/api/save-as` → disk.
- **Kimi prompt summary:** one focused kimi run on the save path; inlined `bridge.command('serialize')` → `api-client.saveAs(path,html)`, dirty-state reflection, and 500 handling per `01` §7.
- **Files (UPDATE):** `app/js/shell/file-controls.js` (save path) + `app/js/main.js`.
- **Verification:** `node --check` PASS; browser-confirmed at CP2 re-verify (REPORT + DECK commented Save-As round-trip GREEN — file written, reopened, runtime re-booted, edits + comments persisted — V-SAVE-1/2/3). Blocked at first CP2 pass by the serializer island off-by-one (B-SERIALIZE); GREEN after fix.

---

## T16 — Outline navigator

- **Status:** PASS after CP2 re-run (kimi-authored). Region navigator wired to runtime regions; click → select.
- **Kimi prompt summary:** one focused kimi run; inlined render-`regions()` + click → `select`, fed by the `ready` event's regions.
- **Files:** outline render + click-to-select landed in `app/js/main.js` + `app/index.html` (`#outline-list`), NOT a separate `app/js/shell/outline.js` — the planned `outline.js` module was consolidated into `main.js`. `runtime/js/runtime-main.js` emits regions on `ready`. DEVIATION from `03`/`04`'s file list; behavior contract unchanged.
- **Verification:** `node --check` PASS; browser-confirmed at CP2 re-verify (outline lists 13 items for REPORT and survives the color-popover open — POPOVER-COEXIST row GREEN). Outline panel was hidden at first CP2 pass by the B-PANEL color-popover regression; GREEN after fix.

---

## Browser checkpoint CP2 — all features, first pass (RED)

- **Stage:** `docs/verification/cp2/result.md` (top section). Verdict: RED — three boot/integration defects, all kimi-fixed.
- **Defects + fixes (kimi-authored):**
  1. `runtime/js/comments.js` declared a duplicate identifier `threads` → SyntaxError killed the entire runtime module graph. Fixed by renaming the store to `threadStore`.
  2. `app/js/main.js` `Coloris.init()` threw and aborted `DOMContentLoaded`. Fixed by wrapping init in try/catch + correcting the Coloris init call.
  3. Undo/Redo toolbar buttons were unwired. Fixed by wiring them in `main.js`.
- **Note:** ESM duplicate-identifier (defect 1) is NOT caught by `node --check` on a `.js` file parsed as CommonJS — it surfaced only at browser ESM load. Lesson captured in `docs/learnings.md`.

---

## Browser checkpoint CP2 — re-run + residual fixes (GREEN)

- **Stage:** `docs/verification/cp2/result.md` (second RED block + final RE-VERIFY GREEN block). After the 3 boot fixes, all in-canvas features passed on the real UI; two residual Save-As defects + one cosmetic, all kimi-fixed:
  1. **B-SERIALIZE** — the serializer hardcoded the re-embedded comment island's node count to `1`, but the island is 2 nodes (`<script>` + its text node), so `serialize()` returned `null` on ANY commented document. Fixed: `islandCount = countAllNodes(island)` (=2).
  2. **B-PANEL** — the color popover did `panelEl.innerHTML = …` on the whole `.shell-panel`, wiping the sibling comment + outline panels. Fixed: the popover renders into its own dedicated `.hyp-color-popover-container` child (`insertBefore`), never the panel root.
  3. **Font-size (cosmetic)** — consecutive A-/A+ created a new nested font-size span. Fixed: `text-format.js` walks the ancestor chain and reuses the existing font-size span in place before falling back to wrapping.
- **Verification:** all four modified files pass `node --check`; focused browser re-run GREEN (see next entry).

---

## Final re-verify — GREEN across the board

- **Stage:** `docs/verification/cp2/result.md` RE-VERIFY section. Verdict: GREEN.
- **Result:** commented Save-As round-trips on BOTH fixtures — REPORT and DECK (each saved to a new `-edited.html` Save-As output); on-disk output is chrome-free (`data-hyp-`=0, `/runtime/`=0, `hyp-` class tokens=0, markers=0) with exactly ONE `id="hyp-comments"` island. The document's own JS is preserved and running in the reopened file (REPORT's `IntersectionObserver` scroll-spy sets `#s4` active on scroll). Comment panel + color popover coexist in the shared `.shell-panel`; font-size produces a single span (19→21→23px, not nested). Zero console errors (DECK's `/doc/assets/*` 404s are the fixture's own missing images). The CP2 re-verify supersedes the CP2 RED verdict.

---

## Run command (for reference)

```
python server/server.py            # serves http://127.0.0.1:8765 (defaults 127.0.0.1:8765)
python server/server.py 127.0.0.1 9000   # custom host/port
```
Open the app shell at `http://127.0.0.1:8765/app/`. Open a document by clicking **Open…**; the document then loads in the iframe from `/doc/<name>` and the runtime injects from `/runtime/js/runtime-main.js`.

---

## v2 improvement cycle (improvements-2026-06)

- **Scope:** F1 native OS open/save dialogs · F2 modeless interaction + alignment guides · F3 move/reorder/re-parent on drop (FLIP) · F4 border color · F5 agent-tagged comments + derived head instruction block · G1/G2 verified (already fixed in v1 CP2) + hardened.
- **Key changes:**
  - Server: new `/api/dialog-open`, `/api/dialog-save-as`, `/api/save`; PowerShell `-STA` dialog launcher with an injectable seam (`api.set_dialog_launcher`); open-path tracking. Toolbar lost both path inputs; gained a Save button.
  - Runtime: NEW `interaction.js` (one combined Moveable: drag+resize+Slides snapping/guides; on-drop hit-test → reorder/re-parent/keep-translate with FLIP); NEW pure `reorder.js`; `resize.js` + `move.js` REMOVED (folded in). Moves now write the CSS `translate` property (D6/D2-letter supersession).
  - Comments: `agentInstruction` flag, `setAgentInstruction`, derived `buildAgentBlock` (head-first-child HTML comment, `-->`→`--&gt;`), `reanchorAfterMove` after DOM moves.
  - Serializer: agent block inserted as first child of `<head>`; node-count guard extended with an `agentBlockCount` term + a pre-existing-block sweep (prevents duplication on re-save).
  - Color: per-element Border row with auto-`1px solid` on borderless elements (U6) and a `mixed` state for differing per-side colors.
  - Shell: NEW `comment-composer.js` anchored popover (replaces `prompt()` for add + reply); per-thread "For agents" toggle.
- **Tests:** stdlib `unittest` server suites + Playwright (Python, headless Chromium) behavioral suites per feature; full suite green per `docs/verification/v2/result.md`. Dev-only deps: `playwright` (app stays dependency-free).
- **Note:** G1 (panel survival) and G2 (serializer island count) were already fixed during v1 CP2 re-verify; v2 locked them with regression tests and extended the serializer guard for the new agent block. The v1 recon/scorecard rows for G1/G2 were stale.
