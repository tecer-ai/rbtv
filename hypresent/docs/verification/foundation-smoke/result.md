# Foundation Smoke — Browser Verification (CP1)

Independent real-browser verification of the T1–T4 foundation via Chrome DevTools MCP.
Server: `python server/server.py 127.0.0.1 8765`. App shell: `http://127.0.0.1:8765/app/`.
Open path driven by the app's OWN module `file-controls.openFile()` (the toolbar "Open…" button is not yet wired to it in `main.js` — see Notes). Date: 2026-06-03.

Overall verdict: **GREEN** — proceed to build the editing core.

---

## Verdict matrix

| Check | REPORT (the report fixture) | DECK (the deck fixture) |
|-------|------------------------------------------------|------------------------------------------|
| RENDER | PASS — full render: sidebar TOC, hero, stat cards; Google Fonts 200. (screenshot removed — private fixture) | PASS — cover slide renders, heading + subheading text, Outfit font. (screenshot removed — private fixture) |
| RUNTIME-BOOT | PASS — `iframe.contentWindow.hyp` = object, keys `[command, version]`; runtime `<script>` injected; `ready` emitted | PASS — `hyp` present, keys `[command, version]`; runtime `<script>` injected |
| DOC-JS-SURVIVES | PASS — own IIFE IntersectionObserver scroll-spy alive: active nav `null` (top) → a later section nav link after scroll to 72%. (screenshot removed — private fixture) | N/A — zero-JS document (nothing to break) |
| BRIDGE | PASS — direct `hyp.command('ping')`→`{ack,...}`; postMessage `command('ping')`→`{pong:true}`; unknown cmd rejected; event `emit`→parent `.on` received; non-`hyp`/no-`kind` msgs dropped | PASS — direct→`{ack,...}`; `command('ping')`→`{pong:true}`; unknown rejected; event received `{deck:true}` |
| CONSOLE | PASS — 4 benign shell-boot info logs + 1 `/favicon.ico` 404 (browser auto-request). No JS errors | PASS — 4 benign info logs + 404 ×9 (favicon + 8 missing `assets/*` images). No JS errors |
| NO-LEAKAGE | PASS — 388 elements: 0 `hyp-` classes, 0 `hyp-` ids, 0 `data-hyp-*`. Native `active` class intact + doc-owned. Only artifact = injected runtime `<script>` | PASS — 357 elements: 0 `hyp-` classes, 0 `hyp-` ids, 0 `data-hyp-*`. Only artifact = injected runtime `<script>` |

---

## Resolved deferred checks (build-log CP1 items)

- T2: Coloris ESM `import` resolves in-browser (`typeof Coloris === 'function'`); `window.Moveable === function`; DOMPurify dynamic import = function. All confirmed at boot.
- T3: V-OPEN-1/2 — both fixtures render; REPORT's own JS runs; runtime module + imports load from `/runtime/` + `/app/js/vendor/` with zero 404; `ready` postMessage reaches parent.
- T4: `command('ping')`→`{pong:true}`; `emit`→parent `on` fires; non-`hyp` messages ignored by both bridges.

## Network

- REPORT: all assets 200 (incl. 2 Google-Fonts woff2). Only non-200 = `/favicon.ico` (benign).
- DECK: Google Fonts + Font Awesome CDN (css + webfonts) all 200. 8 relative `assets/*.png|.jpeg` = 404 — EXPECTED: no `assets/` dir exists on disk in the workspace (verified). Requests resolve to the correct `/doc/assets/...` same-origin path, proving the `/doc/` route serves the doc's sibling dir; the files are simply absent. Not a defect.

## Notes / observations (non-blocking)

1. **Open UI not wired:** `main.js` never calls `initOpenControl`, and the shell has no path-input field, so the toolbar "Open…" button does nothing yet. Verification used the documented fallback: `file-controls.openFile(path, iframe)` via evaluate_script. The open data-flow itself (POST `/api/open` → `iframe.src=/doc/<name>` → runtime injection on load) works end-to-end.
2. **Bridge not auto-wired into the runtime:** `runtime-main.js` sets `window.hyp` and posts `ready`, but does NOT import `bridge-iframe.js`; `main.js` does not call `createBridge`. So the T4 postMessage command listener is not attached on a plain open. The round-trip was exercised by importing `bridge-iframe.js` into the iframe + `createBridge` in the parent as a test harness — both modules function correctly. Wiring them into the boot path is a later-task integration, not a foundation break.
3. **`ready` envelope divergence:** `runtime-main.js` posts `{source:'hyp', type:'ready', payload}` with NO `kind` field, whereas the T4 bridge events use `{source:'hyp', kind:'event', type, payload}`. `bridge-parent.js`'s `onMessage` only dispatches messages with `kind==='response'|'event'`, so the current `ready` message would be silently dropped by a parent bridge. Harmless today (parent doesn't consume `ready` yet) but must be reconciled when the shell starts listening for `ready` to enable the toolbar (arch §3 event set lists `ready`).

## Biggest risk

None at the foundation layer. The riskiest architectural claim — same-origin iframe + injected `hyp-` runtime COEXISTS with the document's own JS, and the parent↔iframe bridge round-trips — is PROVEN on both fixtures (report's live IntersectionObserver survived; bridge ping/event round-tripped; zero namespace leakage). The only items to track are integration wiring (open button, bridge boot, `ready` envelope reconciliation), all owned by later tasks.
