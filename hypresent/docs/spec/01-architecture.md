# Hypresent — Architecture (01)

Defines the isolation model, component layout, parent↔iframe protocol, data flow, serialization flow, error handling, and coexistence/namespacing rules. Decisions referenced here are locked in `docs/decision-log.md` (A1–A12).

---

## 1. Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│ BROWSER TAB (parent page, served by Python server at /app/)                │
│                                                                            │
│  ┌──────────────────────────── APP SHELL (parent DOM) ──────────────────┐ │
│  │  Toolbar          File controls        Color popover   Comment panel  │ │
│  │  [B][I][A+/A-]    [Open…][Save As…]     (Coloris)       (thread list)  │ │
│  └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │ commands ↓     ↑ events                 │
│                          ┌────────┴───────────────────────┐                │
│                          │  bridge (parent side)           │                │
│                          │  - postMessage send/recv        │                │
│                          │  - direct contentWindow calls   │                │
│                          └────────┬───────────────────────┘                │
│                                   │  (same-origin)                          │
│  ┌────────────────────────────────┴─────────────────────────────────────┐ │
│  │  <iframe src="/doc/<file>"> (same-origin, doc's own directory)        │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐│ │
│  │  │  USER DOCUMENT (its own HTML + CSS + its own JS run normally)     ││ │
│  │  │   …flex/grid/absolute content, inline SVG, native data-* …        ││ │
│  │  └──────────────────────────────────────────────────────────────────┘│ │
│  │  ┌──────────── INJECTED EDIT-RUNTIME (hyp- namespaced) ──────────────┐│ │
│  │  │ element-registry  selection  resize(Moveable)  move(Moveable)     ││ │
│  │  │ text-edit  text-format  color-apply  comment-anchors  bridge(iframe)││
│  │  └──────────────────────────────────────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
                                   │ JSON API (fetch)
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PYTHON SERVER (stdlib http.server)                                          │
│  GET  /app/*            → static app shell (parent page, JS, vendor, css)   │
│  GET  /runtime/*        → static edit-runtime from the app's OWN dir (fixed) │
│  GET  /doc/*            → files from the OPEN document's directory (assets)  │
│  POST /api/open         → {path} → reads file from disk, returns html+meta   │
│  POST /api/save-as      → {path, html} → writes standalone html to disk      │
│  GET  /api/pick? (opt)  → returns recent/known paths (no native dialog)      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Isolation Model (A1–A3, A5)

| Layer | Where it runs | Holds |
|-------|---------------|-------|
| App shell | Parent page DOM | Toolbar, file controls, color popover, comment side-panel. NEVER injected into the document. |
| Edit-runtime | Inside the iframe, on the document's `window`/`document` | Selection, `contenteditable`, resize/move handles, `data-hyp-id` tagging, comment anchor markers. All `hyp-`namespaced. Injected as a `<script type="module" src="/runtime/js/runtime-main.js">` (absolute, served from the FIXED `/runtime/*` route — see §8), so its ES-module `import` chain resolves against the runtime's own origin, not the opened document's `/doc/` directory. |
| User document | Inside the iframe | Loads from `/doc/<file>` so relative `assets/` and CDN refs resolve; the document's own JS executes normally. |

**Why same-origin iframe (A1):** the server serves the document's own directory under `/doc/`, so `<img src="assets/x.png">` and `<link href="...cdn...">` resolve exactly as on disk, and the document's IIFE JS (report file) runs unmodified. Same-origin lets the parent reach `iframe.contentWindow.document` directly for synchronous reads.

**Why Moveable runs inside the iframe (A5):** the resize/move target lives in iframe-local coordinates that shift on scroll, responsive reflow, and the document's own animations. Mounting Moveable on the iframe's document gives it native correct coordinates with no parent↔iframe coordinate mapping. The parent only issues `resize:begin`/`move:begin` commands and receives committed geometry deltas for the history stack. Moveable's control box is a `hyp-`namespaced overlay appended inside the iframe document, removed at serialization time.

---

## 3. Parent ↔ Iframe Protocol

Two channels, both same-origin:

1. **Direct calls (parent → iframe):** the parent obtains `iframe.contentWindow.hyp` (the runtime's exported command object) for synchronous reads and command dispatch. Used when the parent needs an immediate return value (e.g., "get selected element's current color").
2. **Events (iframe → parent):** the runtime calls `window.parent.postMessage({source:'hyp', type, payload}, location.origin)` for asynchronous notifications. The parent filters on `event.origin === location.origin && data.source === 'hyp'`.

### Command set (parent → iframe `hyp.command(type, payload)`)

| Command | Payload | Effect | Returns |
|---------|---------|--------|---------|
| `select` | `{hypId}` | Select element by id; mount handles per current tool | `{hypId, role, rect}` |
| `clear-selection` | — | Deselect; unmount handles | — |
| `set-tool` | `{tool}` (`edit`/`resize`/`move`/`comment`) | Switch active interaction tool | — |
| `format` | `{op}` (`bold`/`italic`/`fontInc`/`fontDec`) | Apply format to current text selection | `{applied}` |
| `apply-color` | `{scope, target, value}` (`scope`=`token`/`element`, `target`=token name or `hypId`, `value`=color) | Apply recolor | `{undoToken}` |
| `palette-read` | — | Return the document's `:root` variable map + detected inline-color sites | `{tokens[], inlineSites[]}` |
| `resize-commit` / `move-commit` | `{hypId, before, after}` | Push committed geometry to history (runtime calls this itself on Moveable end; exposed for tests) | `{undoToken}` |
| `undo` / `redo` | — | Step the unified history stack | `{cursor}` |
| `add-comment` | `{hypId, body, author}` | Create a comment thread anchored to element | `{commentId}` |
| `reply-comment` / `resolve-comment` | `{commentId, …}` | Mutate a thread | `{commentId}` |
| `comments-read` | — | Return all threads (for panel render) | `{threads[]}` |
| `serialize` | — | Produce the standalone HTML string | `{html}` |

### Event set (iframe → parent `postMessage`)

| Event `type` | Payload | Parent reaction |
|--------------|---------|-----------------|
| `ready` | `{tokens[], sections[]}` | Enable toolbar; render palette + outline |
| `selection-changed` | `{hypId, role, rect, isText}` | Update toolbar enabled state; position context affordances |
| `geometry-changed` | `{hypId, prop, before, after}` | Reflect in any inspector; mark dirty |
| `out-of-flow` | `{hypId, bool}` | Show/hide the Move "out of flow" badge |
| `comment-anchor-clicked` | `{commentId, rect}` | Open the thread popover at rect |
| `comment-requested` | `{hypId, rect}` | Open "new comment" popover |
| `history-changed` | `{cursor, canUndo, canRedo}` | Enable/disable undo/redo buttons |
| `dirty-changed` | `{dirty}` | Toggle unsaved-changes indicator |
| `error` | `{scope, message}` | Surface non-blocking toast |

---

## 4. Data Flow

### Open
1. User triggers Open in the shell; shell `POST /api/open {path}`.
2. Server reads the file, returns `{html, dir, name}` and ensures `/doc/` is rooted at `dir`.
3. Shell sets `iframe.src = /doc/<name>`. Browser loads the document (assets + its own JS run).
4. Runtime boots on `DOMContentLoaded` of the iframe doc: element-registry assigns `data-hyp-id`, parses any existing `#hyp-comments` island, reads `:root` tokens, emits `ready`.

### Edit (any operation)
1. User interacts in the iframe (click→select, double-click→edit, drag handle→resize/move, etc.) OR clicks a shell control.
2. The owning feature module produces a **command** with a captured inverse, applies it to the iframe DOM, and pushes it onto the unified history stack.
3. Runtime emits `geometry-changed`/`selection-changed`/`history-changed`/`dirty-changed` as applicable; shell updates chrome.

### Save As
1. User triggers Save As; shell asks the iframe to `serialize` (§5).
2. Shell `POST /api/save-as {path, html}`.
3. Server writes the standalone HTML to disk; returns `{ok, path}`. Shell clears dirty state.

---

## 5. Serialization Flow (A8, A11)

Strict order — the serializer module runs entirely inside the iframe runtime. Editor-chrome removal is done SOLELY by NAMESPACE STRIPPING. There is NO whole-document DOMPurify / sanitizer pass: the opened document is the USER'S OWN file (not untrusted), and DOMPurify cannot distinguish the document's own scripts from injected ones by provenance, so any document-body script-strip would either break the report's IIFE or be security theater. The document's own `<script>`/inline handlers/IIFE are PRESERVED simply by not touching them.

1. **Clone** `document.documentElement` (deep). Never mutate the live editing DOM.
2. **Strip ALL `hyp-` artifacts from the clone** (this is the entire chrome-removal mechanism):
   - Remove every element whose `id` or any class token is `hyp-`prefixed (handles, overlays, selection ring, comment markers, the injected edit-runtime `<script type="module">`, any injected `<style>`).
   - Remove every `data-hyp-*` attribute from all surviving elements (including `data-hyp-id` — it is an editor handle, never document content; comment anchoring uses a separate stable key persisted in the island, so the attribute is always stripped — see §6).
   - Remove every `hyp-`prefixed class TOKEN from `class` attributes that also carry document-native tokens (e.g., a node the editor added a `hyp-selected` token to keeps its native classes, loses only the `hyp-` token); delete the `class` attribute entirely only if it becomes empty.
   - Remove any injected inline style the editor added (transient selection/handle styling). Per-element COLOR overrides written by the recolor feature (D6) are document content and are KEPT (they are plain CSS color properties, not `hyp-` namespaced).
   - Remove any `contenteditable` attribute the editor added; restore any the document originally had (registry records original state).
   - The document's own `<script>`, inline event handlers, `<style>`, SVG, and native `data-*` are NOT touched by any step above — they are preserved by omission.
3. **Re-embed comments:** serialize the in-memory comment store to JSON and write it into a single `<script type="application/json" id="hyp-comments">…</script>` placed at end of `<body>`. This id is the ONE intentional `hyp-` survivor (see §6 rationale). The island is `type="application/json"`, so it is inert (browsers neither execute nor render it). Re-embed AFTER the strip so step 2's `hyp-`id removal does not delete it.
4. **Guard:** compute a pre/post node-count delta on the clone (before strip vs after strip + re-embed). The expected delta equals the count of removed `hyp-` chrome nodes plus the re-embedded island. A delta outside that expected band signals the strip removed document content by mistake → abort with an `error` event; never emit a damaged file (§7).
5. **Emit** `<!doctype html>\n` + cloned `documentElement.outerHTML` as the standalone string.

> Namespace stripping (step 2) is the SOLE integrity mechanism and the SOLE chrome-removal mechanism: zero editor leakage, full preservation of the document's own scripts. DOMPurify is NOT part of this flow. Its only v1 role is OPTIONAL defense-in-depth on COMMENT-TEXT rendering inside the editor (comment text is the sole untrusted input; v1 renders it via `textContent`, which is already XSS-safe — A11).

---

## 6. Coexistence & Namespacing Rules (A12)

| Rule | Statement |
|------|-----------|
| Attribute namespace | Every injected attribute MUST be `data-hyp-*`. The editor NEVER writes a non-`hyp` attribute onto a document element. |
| Class/id namespace | Every injected class and id MUST be `hyp-`prefixed. The editor NEVER adds, removes, or toggles a class/id that is not `hyp-`prefixed. |
| Read-only on native hooks | The document's own classes (`.active`/`.open`/`.in`/etc.), ids, and native `data-*` are READ-ONLY to the editor. The editor never mutates them; it only reads them for context (e.g., layout role). |
| No selector presupposition | The editor NEVER assumes `.slide`, `.block`, or any document class. Editable sections/elements are detected from the live DOM (element-registry §03 module map). |
| Native `data-*` preservation | The report fixture's native `data-*` attributes carry semantic content; the editor must distinguish them from `data-hyp-*` by prefix and never overwrite them. |
| Existing ids respected | When an element already has an `id`, the registry does NOT replace it; `data-hyp-id` is an ADDITIVE handle, stripped on save. |
| Comment anchor key | Comment threads are keyed by a stable, collision-resistant anchor key stored INSIDE the island record (NOT `data-hyp-id`), so it survives the strip. The exact key structure, build, match, and fallback are the contract in §6.1. On open, anchors are re-resolved to live elements; unresolvable threads move to an "unanchored" list and are never lost. This is why the JSON island is the only `hyp-` survivor in serialized output. |
| The document owns the DOM | The document's own JS may mutate the DOM at any time (IntersectionObserver adding `.in`, click toggling `.open`). The runtime must tolerate concurrent mutation: it re-reads element rects lazily and never caches a node reference across a tool switch without re-validation via `data-hyp-id`. |

### 6.1 Comment Anchor Key — concrete contract (D4, A12)

The bare structural fingerprint of "tag + nth-of-type chain + nearest native id" COLLIDES on repeated identical siblings, which BOTH fixtures contain (the deck fixture and the report fixture each have repeated identical sibling cards with no id). The anchor key below adds a content hash and a same-key sibling index to disambiguate them. This is a contract, not a guideline — `comments.js` (T15) implements it verbatim.

**Anchor key fields (all five, in this order):**

| Field | Definition |
|-------|------------|
| `hook` | The element's `data-hyp-hook` value (convention hint H1) if present, else `null`. When non-null, `hook` ALONE is the match key (it is author-declared stable) and the remaining fields are advisory tie-breakers only. |
| `path` | The element's structural path from the nearest ancestor carrying a native `id` (or from `documentElement` if none): a `/`-joined chain of `tagName:nth-of-type` segments (lowercased tag; `nth-of-type` is 1-based among same-tag siblings). |
| `nativeId` | The `id` of the nearest ancestor-or-self that has a document-native `id`, else `null`. Anchors the `path` to a stable subtree even if the document is restructured above it. |
| `contentHash` | A short stable hash (e.g. FNV-1a → 8 hex chars) of the first 32 characters of the element's OWN `textContent` after normalization (collapse runs of whitespace to one space, trim). Empty/whitespace-only text → hash of the empty string. Distinguishes sibling cards whose only difference is their text. |
| `siblingIndex` | The element's 0-based index among the set of same-parent siblings that share the SAME `{path-tail-tag, primary class signature}` — i.e. the index among siblings that would otherwise produce an identical key. Disambiguates truly identical repeated siblings (same tag, same class, same/empty text). |

**Build (on `add-comment`):** compute all five fields from the live target element and store the tuple as the thread's `anchor` in the island record. Also store `contextText` = the normalized first ~80 chars of `textContent` for the "unanchored" panel display.

**Match (on open / re-anchor), in priority order — first hit wins:**

1. If `anchor.hook` is non-null: select the unique element with `[data-hyp-hook="<hook>"]`. If exactly one matches → anchored. If zero or >1 → fall through.
2. Resolve `anchor.nativeId` (or `documentElement`) as the base node; from it, walk `anchor.path`. If it resolves to exactly one element AND that element's recomputed `contentHash` equals `anchor.contentHash` → anchored.
3. If the path resolves to a set of same-key siblings (repeated-sibling case), pick the member at `anchor.siblingIndex` whose recomputed `contentHash` matches; if the indexed member matches → anchored.
4. Relaxed fallback: among all elements matching `anchor.path`'s tail tag + class signature anywhere under the `nativeId` base, if exactly one has a matching `contentHash` → anchored (tolerates minor structural drift above the element).

**Unanchored fallback (graceful, never lossy):** if no rule resolves a unique element, the thread is retained, marked `unanchored: true`, and surfaced in the comment side panel under an "Unanchored" group showing its `contextText` and body. It is re-serialized into the island unchanged (so a later open, after the document is edited back, may re-anchor it). A comment is NEVER discarded (D4 portability; §7 row "Comment anchor cannot be re-resolved on open").

---

## 7. Error Handling

| Failure | Handling |
|---------|----------|
| `/api/open` path missing/unreadable | Server returns 404 + JSON `{error}`; shell shows blocking modal, no iframe load. |
| `/api/save-as` write fails (permissions, bad dir) | Server returns 500 + JSON `{error}`; shell keeps dirty state, shows error, offers retry/alternate path. |
| Document's own JS throws on load | Runtime boot is wrapped; a document error does NOT abort the runtime. Runtime logs via `error` event; editing continues on whatever DOM exists. |
| Element disappears (document JS removed it) mid-edit | On next command, registry re-resolves `data-hyp-id`; if gone, the command is rejected with an `error` event and the history entry is not pushed. |
| Strip pass removes unexpected content | Serializer's node-count guard (§5 step 4) compares pre/post counts against the expected `hyp-` chrome delta; an out-of-band drop triggers an `error` event and the save is aborted pending user confirm (never silently emit a damaged file). |
| Comment anchor cannot be re-resolved on open | Thread is kept and shown in the panel as "unanchored" with its last-known context text; never discarded (D4 portability). |
| Non-conforming file (no hints) | Editor degrades per `docs/spec/02-html-convention.md`; never errors out — reduced capability, not failure. |

---

## 8. Boot Sequence

1. Parent page (`/app/`) loads shell modules.
2. User opens a file → iframe `src` set to `/doc/<name>`.
3. Iframe document loads (assets + own JS) from its own directory under `/doc/`.
4. Parent injects the runtime into the iframe once the iframe `load` event fires: it creates a `<script type="module">` in the iframe document and sets its `src` to the ABSOLUTE runtime URL `/runtime/js/runtime-main.js` (origin = the server origin, e.g. `http://127.0.0.1:8765/runtime/js/runtime-main.js`), NOT a `/doc/`-relative path. Because the iframe is same-origin with `/app/` and `/runtime/`, the module loads and its ES-module `import` statements (e.g. `import { ... } from './bridge-iframe.js'`) resolve against the `/runtime/js/` origin — the runtime's own sibling modules, never the opened document's directory. The runtime's `import` of vendored libs uses absolute `/app/js/vendor/...` paths for the same reason.
5. Runtime: build registry → tag elements → parse comment island → read tokens → emit `ready`.
6. Shell enables controls on `ready`.

Injection-after-load (not server-side injection) keeps the served `/doc/` bytes identical to disk, so the document behaves exactly as it will after "Save As". Serving the runtime from the fixed `/runtime/*` route (separate from the mutable `/doc/` root) is what makes its absolute `src` and import chain resolvable regardless of which file/directory is open (A10).
