# CP1 — Browser Verification (integrated runtime)

Date: 2026-06-03 · Server: `python server/server.py` @ http://127.0.0.1:8765 · Chrome DevTools MCP
Method: app shell at `/app/`, REPORT + DECK opened via the real Open control (path input + Open button). Bridge commands issued by hand-built `hyp` postMessage from parent → iframe.contentWindow, listening on parent window for `{source:'hyp',kind:'response'}` (parent's own bridge is module-local, not on `window`).

## Overall: RED

Foundation, boot wiring, tagging, selection, doc-JS coexistence, undo/redo command surface, and the strip pass all work on BOTH files. The **serializer (T9) is broken**: `serialize` returns `null` every time because its node-count guard miscounts removed subtrees. Save-As (the core deliverable) can never produce output. Must fix before features T10–T15.

### Single most important fix
`runtime/js/serializer.js` → `countAllNodes(root)` (lines 58–65) uses `createTreeWalker(root, SHOW_ALL)` + `while(walker.nextNode())`, which **excludes the root node**. So each removed top-level element (the injected runtime `<script>`, the selection ring) is undercounted by 1. `removedNodeCount` comes out 0 while N elements are actually detached → `postCount !== expectedPostCount` → guard aborts, `serialize()` returns `null`. Fix: count the root (e.g. start count at 1, or `let c = 1` per subtree, or switch to `root.querySelectorAll('*').length + textNodes`), so the guard math balances. Verified empirically: a leaf `<div>` counts 0 (should be 1); `<div><span>x</span></div>` counts 2 (should be 3).

---

## REPORT — the report fixture

| Check | Verdict | Evidence |
|-------|---------|----------|
| RENDER | PASS | Report renders in iframe; all 6 runtime modules + /doc + /api/open = 200. Only 404 = favicon (benign). (screenshot removed — private fixture) |
| READY-BRIDGE | PASS | `get-selection` → `{ok:true,result:null}`; `runtime ready` console event; `window.hyp` stub present (v0.0.0-stub). |
| TAGGING | PASS | 337 `[data-hyp-id]` elements (>0). Doc own nodes intact (native nav, sidebar, progress-bar element, nav link `data-target`). ZERO `hyp-` class tokens on doc's own elements. |
| SELECTION | PASS | Clicked a section h2 → `hyp-47`, `.hyp-selection-ring` appears (cyan 2px, sized to el). Clicked 2nd h2 → moves to `hyp-55`, exactly 1 ring (no dup). selection.js click listener self-activated. (screenshot removed — private fixture) |
| DOC-JS-SURVIVES | PASS | Scrolled down → report's own IntersectionObserver scroll-spy moved the active nav link to a later section; own progress bar updated to 40.9%. (screenshot removed — private fixture) |
| SERIALIZER | **FAIL** | `serialize` → `{ok:true, result:{html:null}}`. Emitted error: `node-count guard failed: expected 1094 nodes, got 1093. Pre=1094, removed=0, island=0`. Even with selection cleared (ring gone), off-by-1 = the single injected runtime `<script>`. Could NOT verify (i)/(ii)/(iii) because no HTML string is ever returned. `report-serialize-checks.json` |
| UNDO-REDO | PASS | `undo` → `{cursor:-1,canUndo:false,canRedo:false}`; `redo` same. Both `ok:true`, no error. Empty stack expected (no feature ops yet). |
| CONSOLE | PASS | 4 info (shell + Moveable/Coloris/DOMPurify available), `runtime ready`, 1 error = favicon 404 (benign). No JS exceptions. |

## DECK — the deck fixture

| Check | Verdict | Evidence |
|-------|---------|----------|
| RENDER | PASS | All slides render. Runtime modules reloaded (200). 404s = favicon + expected `assets/*` images (no assets dir). (screenshot removed — private fixture) |
| READY-BRIDGE | PASS | `get-selection` → `{ok:true,result:null}`; `runtime ready` console event; `window.hyp` stub present. |
| TAGGING | PASS | 345 `[data-hyp-id]` elements. Doc own classes intact (slide cover + heading classes). ZERO `hyp-` class tokens on doc's own elements. |
| SELECTION | PASS | Clicked a slide heading element → `hyp-13`, ring appears (cyan 2px, 831x38). Original class preserved. (screenshot removed — private fixture) |
| DOC-JS-SURVIVES | N/A | Deck has zero own JS (0 inline scripts) — nothing to preserve, per task. |
| SERIALIZER | **FAIL** | `serialize` → `null`. Error: `expected 1041, got 1040, removed=0`. Deck has 0 own scripts, so off-by-1 = the single injected runtime `<script>` alone. Same guard bug. Standalone/chrome-free unverifiable (no output). |
| UNDO-REDO | PASS | `undo`/`redo` both `{cursor:-1,canUndo:false,canRedo:false}`, ok:true. |
| CONSOLE | PASS | `runtime ready` fired. Errors only 404s (favicon + missing deck assets, expected/benign). No JS exceptions. (screenshot removed — private fixture) |

## Real console errors (verbatim)
- `Failed to load resource: the server responded with a status of 404 (Not Found)` — favicon.ico (both runs) + the deck fixture's own `assets/*` images. ALL benign per task scope.
- No uncaught JS exceptions on either file.

## Serializer error events (verbatim, emitted as `hyp` events not console)
- REPORT: `Serializer node-count guard failed: expected 1094 nodes, got 1093. Pre=1094, removed=0, island=0. Aborting save to avoid data loss.`
- DECK: `Serializer node-count guard failed: expected 1041 nodes, got 1040. Pre=1041, removed=0, island=0. Aborting save to avoid data loss.`
