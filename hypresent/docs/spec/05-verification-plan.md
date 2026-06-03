# Hypresent — Verification Plan (05)

Per-feature test cases executable via the Chrome DevTools MCP against BOTH test HTML files, with concrete pass/fail criteria, a regression checklist, and the Save-As validity gate. Test IDs (`V*`) are referenced as acceptance criteria by tasks in `docs/spec/04-implementation-plan.md`.

---

## 1. Test Harness

- **Server up:** `python server/server.py` (defaults `127.0.0.1:8765`). Health: `GET /app/` returns the shell.
- **Fixtures (the two profiled files, in this workspace; see `docs/fixture-profiles.md`):**
  - **DECK** = the deck fixture (slide deck; zero JS; `:root` tokens; no ids/`data-*`; relative `assets/`).
  - **REPORT** = the report fixture (scrolling report; own IIFE JS; native ids + native `data-*`; inline SVG; inline-`style` colors + `position:absolute` content nodes).
- **MCP tools used:** `new_page`/`navigate_page`, `take_snapshot`, `click`, `fill`/`type_text`, `evaluate_script`, `take_screenshot`, `wait_for`, `list_console_messages`.
- **Iframe access pattern:** tests run `evaluate_script` in the parent, reaching the document via `document.querySelector('iframe').contentWindow` / `.contentDocument` (same-origin). Assertions read live DOM and the runtime's `window.hyp`.
- **Snapshot discipline:** capture a baseline DOM signature (outerHTML hash of `documentElement` minus `hyp-` nodes) before each op group to support undo-equivalence checks.

---

## 2. Per-Feature Test Cases

Each case: ID · feature · file(s) · steps · PASS criteria. FAIL = any PASS criterion unmet OR any uncaught console error from the editor (the document's own logs are ignored).

### Open / Boot

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-OPEN-1 | DECK | Open via `/api/open`; wait for iframe `ready` | iframe shows the deck; `assets/` images load or hit their `onerror` fallback (no broken layout); `ready` event received; toolbar enabled |
| V-OPEN-2 | REPORT | Open; wait `ready` | report renders; the document's own JS runs (scroll-spy class `.active` appears on a nav link when scrolled); `ready` received |
| V-BOOT-3 | both | After `ready`, `evaluate_script` count of `[data-hyp-id]` | every detected editable element tagged; REPORT's native `id`s unchanged; REPORT's native `data-*` content attributes unchanged |

### Selection

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-SEL-1 | DECK | Click a slide heading element | `selection-changed` fires with its `hypId`; a `hyp-`selection ring is present; no document class added/removed |
| V-SEL-2 | REPORT | Click a semantic absolutely-positioned node | role reported `absolute`; selection works; the node's inline `left:%` unchanged |
| V-SEL-3 | REPORT | Click inside the hero inline `<svg>` | selecting the SVG element does NOT make `<path>` text-editable; no path geometry altered |

### Text Edit + Format

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-TXT-1 | DECK | Double-click a slide subheading element, type new text, blur | text updated; element still has its original class; a single history entry created |
| V-TXT-2 | REPORT | Double-click a `<p class="lead">`, edit, blur | text updated; `.reveal`/`.in` classes from the document's own JS untouched |
| V-FMT-1 | DECK | Select word in an editable node, apply Bold then Italic | `<b>`/`<i>` (or equivalent) wrap the selection; visual weight/style changes |
| V-FMT-2 | DECK | Apply font-size increase twice, then undo twice | size grows then returns exactly to original; two history entries reverted |
| V-TXT-NEG | REPORT | Attempt to edit a `.chip` label and an `.n` counter | not offered as editable (H4 fallback flags auto-detected; counters excluded) OR editable but cleanly undoable with no JS-state breakage |

### Resize (D1 — flow-aware)

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-RSZ-1 | DECK | Resize a grid-child card wider | the grid track / `flex-basis`/`width` changes; `getComputedStyle(el).position` is NOT `absolute`; siblings reflow responsively |
| V-RSZ-2 | DECK | Resize a flex-row child | `flex-basis` (or `width`) mutated on the correct axis; layout stays responsive |
| V-RSZ-3 | REPORT | Resize a semantic absolutely-positioned node (absolute content) | because role=absolute, `width`/`height` (and `top`/`left` if dragged) may change; element remains `position:absolute`; the `left:%` semantic anchor not destroyed unless explicitly resized |
| V-RSZ-NEG | both | Inspect any resized element | NO element was force-converted to `position:absolute` by resize |

### Move (D2 — transform translate)

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-MOV-1 | DECK | Move a flow-child element a small amount | ONLY `transform: translate(...)` changed; no `top/left/margin` written; siblings do NOT reflow |
| V-MOV-2 | DECK | Move it far enough to leave its flow box | `out-of-flow` event fires `true`; UI badge shown |
| V-MOV-3 | both | Move then undo | `transform` returns to its prior value exactly (empty or original) |
| V-MOV-4 | REPORT | Move an element that the document's JS observes (`.reveal`) | move applies; the document's `.in` toggling still functions |

### Recolor (D6 — both paths + inline)

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-COL-1 | DECK | Palette: change `--primary` | every element using `var(--primary)` recolors in one operation; single history entry |
| V-COL-2 | DECK | Per-element: override one card's color | only that card changes; the token and other cards unchanged |
| V-COL-3 | REPORT | Recolor a legend swatch set via inline `style="background:…"` | the inline `style` value is updated (NOT only the token); swatch visibly changes |
| V-COL-4 | REPORT | Palette read | palette lists `:root` color tokens only (non-color vars like `--nav-w`/`--r` filtered by value, H9 fallback) |
| V-COL-5 | both | Undo a token recolor | all affected elements revert together |

### Comments (D4)

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-CMT-1 | DECK | First comment prompts author name once; add comment on a slide heading element | name stored in `localStorage`; marker appears anchored to the element; thread visible in side panel |
| V-CMT-2 | DECK | Reply, then resolve | thread shows reply; resolved state reflected; subsequent comments do NOT re-ask the name |
| V-CMT-3 | both | Add comment, Save As, re-open the saved file | `#hyp-comments` island present in saved file; on re-open the thread re-anchors to the same element |
| V-CMT-4 | both | View saved file WITHOUT the editor (plain browser open) | comment island is invisible (no rendered UI); document looks normal |
| V-CMT-5 | REPORT | Add comment to an element, then have the document JS mutate classes; reload editor | anchor re-resolves; if element truly gone, thread shown as "unanchored", never lost |

### Undo/Redo (unified — A7)

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-HIST-1 | DECK | Perform text→format→resize→move→color in sequence; undo 5× | DOM signature returns to baseline (minus `hyp-` nodes) exactly; redo 5× restores |
| V-HIST-2 | both | Undo past an op, then perform a new op | redo tail truncated; stack consistent; `history-changed` reflects `canRedo:false` |

### Save As (gate — see §4)

| ID | File | Steps | PASS |
|----|------|-------|------|
| V-SAVE-1 | DECK | Edit + Save As to a new path | file written; opens standalone; ZERO `hyp-`/`data-hyp-` artifacts (except the inert `#hyp-comments` island) |
| V-SAVE-2 | REPORT | Save As | the document's own `<script>` IIFE retained and runs in the saved file; scroll-spy/reveal still work |
| V-SAVE-3 | both | Diff saved vs original (no edits made) | only additions are the comment island (if any) and applied edits; no editor chrome, no reflow regressions |

---

## 3. Regression Checklist (run after EVERY feature task)

- [ ] No `hyp-`prefixed class/id or `data-hyp-*` attribute leaks into a Save-As output (except `#hyp-comments`).
- [ ] No document-native class (`.active`/`.open`/`.in`/`.slide`/`.block`/etc.), native id, or native `data-*` was added, removed, or modified by the editor.
- [ ] DECK still renders (zero JS) and REPORT's own JS still runs (scroll-spy, reveal, expand/collapse, mobile nav, progress bar) inside the iframe.
- [ ] Inline SVG paths are byte-identical after any edit that did not explicitly target them.
- [ ] Undo of the most recent op restores the exact prior DOM signature.
- [ ] No editor-origin uncaught exceptions in the console (`list_console_messages`).
- [ ] Resize never produced a `position:absolute` conversion; Move only ever wrote `transform`.
- [ ] Relative `assets/` and CDN refs still resolve after open (DECK images; both files' Google Fonts).

---

## 4. Save-As Validity Gate ("chrome-free, runnable HTML")

A Save-As output PASSES the gate only if ALL hold (verified via MCP by opening the saved file directly, no editor):

1. **Parses & renders:** `new_page` on the saved file renders without layout collapse; `take_screenshot` visually matches the edited state.
2. **Chrome-free:** `evaluate_script` finds ZERO elements matching `[class^="hyp-"],[class*=" hyp-"],[id^="hyp-"]` and ZERO attributes matching `data-hyp-` — EXCEPT exactly one `script#hyp-comments[type="application/json"]` when comments exist.
3. **Comment island inert & invisible:** the island renders nothing; `JSON.parse` of its text content succeeds and matches the in-editor thread state.
4. **Document JS preserved & runnable:** for REPORT, the IIFE runs (assert `.active` appears on scroll; `.in` appears on reveal). For DECK, no script was added.
5. **Standalone:** the file references only its original relative `assets/` and original CDN URLs; the editor added NO new `<script src>`, `<link>`, or inline editor script.
6. **Strip non-destructive (node-count guard):** the serializer removes ONLY `hyp-` chrome (no document-body sanitizer pass — A8/A11); its pre/post node-count delta equals the removed `hyp-` chrome plus the re-embedded comment island; an out-of-band drop aborts the save (no damaged file emitted).
7. **Re-editable:** re-opening the saved file in the editor reaches `ready` and re-anchors comments — the output is a valid hypresent input (round-trip stable).

The gate is a hard release blocker: any feature is "done" only when its edits survive this gate on BOTH fixtures.
