# CP2 — Comprehensive Browser Verification (RE-RUN after boot fixes)

**Date:** 2026-06-03
**Verdict: RED — one blocker remains (Save-As gate fails whenever comments exist) plus a shell-panel regression that hides the comment/outline panels.**

The two prior boot crashes are FIXED and confirmed: `comments.js` now uses `threadStore` (no duplicate `threads` identifier); `app/js/main.js` wraps `Coloris.init()`+`Coloris({...})` in try/catch and wires Undo/Redo. The runtime boots, all in-canvas features work. But the **Save-As round-trip gate fails** (serializer node-count guard off-by-one on the comment island) and a **new shell bug** wipes the comment + outline panels.

---

## Blocker / High-severity bugs (ranked)

### B-SERIALIZE — FATAL for the Save-As gate: node-count guard off-by-one on the comment island
- **File:line:** `runtime/js/serializer.js` ~L225-243. The re-embedded comment island is a `<script>` with a `.textContent` text-node child = **2 DOM nodes**, but `islandCount` is hardcoded to **1** (L235). The guard `postCount === preCount - removedNodeCount + islandCount` is therefore always 1 short, so `serialize()` returns `null` and the save aborts.
- **Trigger:** ANY document that has a `#hyp-comments` island in the live DOM — i.e. the moment a first comment is added (`writeIsland()` creates it), and it persists even after all comments are undone (the empty `[]` island remains and `getCommentJson()` re-embeds it).
- **Symptom (verbatim):** `Serializer node-count guard failed: expected 1104 nodes, got 1105. Pre=1112, removed=9, island=1. Aborting save to avoid data loss.` (REPORT) / `expected 1042 … got 1043 … island=1` (DECK).
- **Proof of isolation:** a FRESH document with NO island (text+resize only, never commented) **saves successfully** — DECK saved to its `-edited.html` Save-As output, reopened, runtime re-booted (345 tagged), text edit persisted, on-disk file had **0** `data-hyp-`, **0** `/runtime/`, **0** `hyp-` class tokens, **0** leftover island. So the strip itself is correct; only the guard math is wrong.
- **Fix:** set `islandCount = countAllNodes(island)` (=2) — or `islandCount = 2` — at the re-embed site.

### B-PANEL — HIGH: color popover overwrites the entire side panel, destroying the comment + outline panels
- **File:line:** `app/js/main.js:287-289` passes the whole `.shell-panel` as `panelEl` to `createColorPopover`; `app/js/shell/color-popover.js:21` does `panelEl.innerHTML = \`…\``, deleting the sibling `.outline-panel` and `.comment-panel` (incl. `#comment-threads`, `#comment-unanchored`, `#outline-list`).
- **Impact:** comment threads NEVER render in the panel (author/time/body invisible); the outline is permanently empty. Comment DATA, markers, and anchoring are all correct underneath — only the panel UI is gone.
- **Fix:** give the popover its own child container (e.g. a dedicated `<div>` inside the panel), not the panel root.

### Non-blocking note
- DECK still emits `404 ×N` for `/doc/assets/*.png|jpeg` (the deck fixture's own image assets) — the DECK's OWN missing image assets, NOT a hypresent defect. All app/runtime resources serve 200.
- Toolbar A-/`fontDec` after A+/`fontInc` creates a NEW nested font-size span instead of editing the existing one (selection refocus on toolbar mousedown). Both ops still apply via the real buttons; cosmetic only.

---

## REPORT — full pass (the report fixture)

| Feature | Verdict | Evidence |
|---------|---------|----------|
| BOOT | **PASS** | No console errors; `runtime ready` fired; 337 `[data-hyp-id]`; `window.hyp` defined; bridge `ping`→`{pong:true}`; toolbar enabled (Bold/Italic/Undo/Redo not disabled). (screenshot removed — private fixture) |
| OPEN (real UI) | **PASS** | Filled path + clicked Open; `iframe.src=/doc/…`; runtime-main injected; doc title + h1 render; Save-As auto-defaulted to `-edited.html`. |
| TEXT EDIT | **PASS** | Real dblclick on hyp-47 set `contenteditable=true`+focus; `insertText` → "HYPCP2-EDIT"; blur committed; `contenteditable` removed; DOM = "HYPCP2-EDIT". (screenshot removed — private fixture) |
| FORMAT | **PASS** | Real toolbar: Bold→`<b>` wrapped the selection, Italic→`<i>` wrapped the selection, A+→`<span style="font-size:19px">` on the selection, A-→font-size span (15px). |
| RESIZE (flow-aware) | **PASS** | hyp-61 (flex-child): Moveable mounted (4 handles); `resize-commit` wrote `flex-basis:520px`, `position` stayed `static`, no inline `position`/absolute. (screenshot removed — private fixture) |
| MOVE (transform) | **PASS** | hyp-35: `move-commit` wrote `transform: translate(60px, 40px)`; `position` stayed `static` (transform-only). |
| COLOR — token | **PASS** | A theme token → #cc0000 recolored **45** elements simultaneously; `:root` inline override set. (screenshot removed — private fixture) |
| COLOR — element | **PASS** | hyp-56 per-element `color:#008800` (rgb 0,136,0); sibling hyp-62 unchanged (scoped, no cascade). Real 🎨 button opens Coloris `#clr-picker` (visible) with 11 swatch inputs. |
| COMMENTS | **PARTIAL** | First comment prompted ONCE for name → "CP2 Tester" (stored); add "first thread" anchored to hyp-47 (marker "1"); reply + resolve (marker "✓" gray); second comment NO re-prompt, anchored hyp-48 (2 markers). **Panel does NOT show author/time (B-PANEL).** (screenshot removed — private fixture) |
| UNDO / REDO | **PASS** | Toolbar Undo ×3 reverted in LIFO: add-comment#2 → resolve → reply; Redo ×3 re-applied in FIFO exactly; state restored (2 threads, 1 reply, resolved, 2 markers). (screenshot removed — private fixture) |
| SAVE-AS ROUND-TRIP (gate) | **FAIL** | Real Save As → "Document serialization returned null." No `-edited.html` written. B-SERIALIZE guard off-by-one (island=1). Round-trip/reopen/persistence/artifact-grep all BLOCKED. Strip itself verified clean via manual replay (0 `data-hyp-`, 0 `/runtime/`, REPORT's own `<script>`+IntersectionObserver preserved). (screenshot removed — private fixture) |
| CONSOLE | **PASS** | Zero JS errors (no SyntaxError, no TypeError). Only benign a11y `[issue]` advisories (Coloris inputs lack id/label). Serializer failure surfaces as a graceful bridge `error` event, not a throw. |
| COEXISTENCE | **PASS** | After scroll, REPORT's own scroll-spy set a later section nav link active, the progress-bar element width 80.9px, 3/7 reveal-animation elements activated — native IO/scroll JS unaffected by the editor. |

## DECK — condensed pass (the deck fixture)

| Feature | Verdict | Evidence |
|---------|---------|----------|
| OPEN/BOOT | **PASS** | 345 tagged; runtime-main injected; bridge live; Save-As defaulted `-edited.html`. |
| TEXT EDIT | **PASS** | Real dblclick on hyp-9 (a date label) → "HYPCP2-EDIT"/"HYPCP2-DECK-NOCMT"; commit removed `contenteditable`. |
| RESIZE | **PASS** | hyp-2 (flex-child): Moveable mounted (4 handles); `resize-commit` `flex-basis:300px`; `position` static. |
| COMMENT | **PARTIAL** | "deck comment thread" by "CP2 Tester" (no re-prompt), anchored hyp-13, 1 marker. Panel not shown (B-PANEL). |
| SAVE-AS ROUND-TRIP | **FAIL w/ comment → PASS w/o comment** | WITH comment: same B-SERIALIZE null. Fresh reload (no island), text+resize, Save As → **success**, file written; reopened → runtime re-booted (345), text persisted (hyp-9), doc renders. On-disk: 0 `data-hyp-`, 0 `/runtime/`, 0 `hyp-` classes, 0 island. (screenshot removed — private fixture) |
| CONSOLE | **PASS** | `runtime ready` each open; no app JS errors. 404s = DECK's own `/doc/assets/*` images (document content). |

---

## Notes on method
- Bridge command path (`select`, `set-tool`, `resize-commit`, `move-commit`, `apply-color`, comment cmds) was driven via the documented `{source:'hyp',kind:'command',…}` envelope. **Scripted-only cases (UI automation cannot reach):** (a) Moveable handle drags — gesto's pointer capture is not satisfied by synthetic pointer events, and MCP `drag` cannot target iframe-internal control handles by uid; the documented `*-commit` commands (exactly what `resize.js`/`move.js` call on drag-end) were used instead. (b) Tool switching has no toolbar button, so `set-tool` was issued via the bridge (the parent shell's own path). Text edit, format, color picker, comment, Save-As, Open, and Undo/Redo were all driven through the **real toolbar/UI**.

## Required fixes to reach GREEN (ranked)
1. **B-SERIALIZE** — `runtime/js/serializer.js`: count the re-embedded island's text node (`islandCount = 2` / `countAllNodes(island)`). Unblocks the Save-As gate for any commented document. **(gate blocker)**
2. **B-PANEL** — `app/js/main.js` + `app/js/shell/color-popover.js`: render the color popover into a dedicated child container, not the whole `.shell-panel`; restores the comment + outline panels.
3. **Minor** — `text-format.js` `adjustFontSize`: re-target the existing font-size span on consecutive A-/A+ (avoid nesting) — cosmetic.
4. **Re-run the Save-As round-trip on REPORT** after fix #1 (comment thread re-anchor + persistence + REPORT-own-script-in-reopened-file were the only sub-checks blocked).

---

# RE-VERIFY — focused re-run after 3 fixes (2026-06-03, later)

**Verdict: GREEN.** All three fixes confirmed working; no boot regression. The two prior blockers (B-SERIALIZE, B-PANEL) are resolved and the font-size nesting fix holds.

## Source confirmation (the 3 fixes)
- **B-SERIALIZE** — `runtime/js/serializer.js:234` now `islandCount = countAllNodes(island)` (=2, script node + text node). Guard math corrected.
- **B-PANEL** — `app/js/shell/color-popover.js:21-26` creates a dedicated `.hyp-color-popover-container` child (`insertBefore`) and writes its `innerHTML` to that container, never to `panelEl` (the `.shell-panel` root). `main.js:289` still passes the panel, but the popover no longer wipes siblings.
- **Font-size** — `runtime/js/text-format.js:64-81` walks the ancestor chain for an existing editor font-size `span` and updates it in place before falling back to wrapping.
- All four modified files pass `node --check`.

## Re-verify verdicts

| Check | Verdict | Evidence |
|-------|---------|----------|
| BOOT | **PASS** | REPORT opened via real UI; `iframe.src=/doc/…`; 337 `[data-hyp-id]`; `window.hyp` object; runtime script injected; Save-As auto-defaulted `-edited.html`; **zero console errors/warnings**. (screenshot removed — private fixture) |
| COMMENT-PANEL | **PASS** | localStorage had `CP2 Tester` → **no name re-prompt** (only the "Comment:" body prompt fired). Panel **shows the thread**: author "CP2 Tester" + body "first thread re-verify" + time "16:11:34"; marker "1" in iframe. Real **Reply** btn → reply renders (author+body+time); real **Resolve** btn → thread gets `comment-thread-resolved`, btn flips to "Reopen", marker → "✓". (screenshot removed — private fixture) |
| POPOVER-COEXIST | **PASS** | After clicking real 🎨: comment panel survives (1 thread, body intact), outline survives (13 items), `.hyp-color-popover-container` count = **1** (not duplicated), 9 palette token rows, Coloris `#clr-picker` present. Snapshot shows palette tokens AND comment thread rendered together in the same `.shell-panel`. (screenshot removed — private fixture) |
| FONT-SIZE | **PASS** | Edit mode on hyp-48; select word, fontInc ×3 with re-selection of the wrapped word between ops → **1 span, sizes climb 19→21→23px, NOT nested** (`childFs:0`, `hasNesting:false`). Method note below. (screenshot removed — private fixture) |
| REPORT-SAVEAS-ROUNDTRIP (gate) | **PASS** | With comment ("gate roundtrip comment" on hyp-47) + text edit "HYPFIX-EDIT" present: real **Save As** → status "Saved to …-edited.html" (success). **Serialize no longer null.** On-disk: `data-hyp-`=0, `/runtime/`=0, `hyp-` class tokens=0, markers=0, runtime-main=0, **exactly 1** `id="hyp-comments"` island. **2 `<script>` tags** = REPORT's own scroll-spy (3× `IntersectionObserver`) + island. REOPEN: re-booted (337), **text persisted** (hyp-47="HYPFIX-EDIT"), **comment re-anchored + shown in panel** (author+body+time), marker "1"; scroll down → REPORT's own scroll-spy set a later section nav link `class="active"` (siblings inactive). Zero console errors. (screenshot removed — private fixture) |
| DECK-SAVEAS-ROUNDTRIP | **PASS** | DECK opened (345 tagged); comment "deck gate comment" on hyp-7; real Save As → success. On-disk chrome-free: `data-hyp-`=0, `/runtime/`=0, `hyp-` classes=0, markers=0, runtime-main=0, **1** island (body "deck gate comment"). REOPEN: re-booted (345), comment persisted + re-anchored (author+body+time), marker "1". (screenshot removed — private fixture) |
| CONSOLE | **PASS** | Zero JS errors across REPORT boot, comment ops, popover, save, and reopen. DECK shows only **404s for its own `/doc/assets/*.png\|jpeg`** content images (the deck fixture's own image assets) — confirmed via network list; NOT a hypresent defect. All app/runtime resources served 200. |

## Method note — font-size
The fix dedups by walking from the live selection's `commonAncestorContainer` to find an existing font-size `span`. The `format` command's `do()` runs `el.innerHTML = afterHtml` (`commands.js:72`), which re-parses the element and resets a stale **collapsed caret** to the `<p>`. So consecutive fontInc with a held-stale caret produced 3 sibling 19px spans (still NOT nested — the fix's stated goal). With the realistic flow — re-select the (now-wrapped) word between ops, exactly as a user does — the ancestor-walk finds the span and updates it in place: **1 span, 19→21→23px**. Fix verified correct; the multi-span case is a synthetic-caret artifact, not a regression. (Pre-existing: the parent toolbar A+ button blurs the iframe contenteditable on mousedown, so synthetic toolbar clicks can't reach an active edit — `format` was driven via the documented bridge envelope, the same path the toolbar uses post-focus.)

## Outputs (app Save-As products + screenshots)
- REPORT Save-As output (`-edited.html`, 82071 bytes) — removed (private fixture output).
- DECK Save-As output (`-edited.html`, 82186 bytes) — removed (private fixture output).
- Re-verify screenshots — removed (private fixtures).

Server stopped; port 8765 confirmed free. Source files unchanged (read-only).
