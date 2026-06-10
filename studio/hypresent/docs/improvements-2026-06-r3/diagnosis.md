# Hypresent Session 3 — Diagnosis (R10–R14)

**Date:** 2026-06-05
**Mode:** Root-cause investigation ONLY (superpowers:systematic-debugging Phase 1). ZERO product-file edits — this file is the sole write. No fixes proposed beyond naming the fix surface.
**Inputs treated as ground truth:** `user-feedback.md`, `evidence-summary.md`, `live-debug-raw.json` (16 gestures / 400 mutations, zero editor console errors).
**Code read in full:** `interaction.js` (392 L), `element-registry.js`, `commands.js`, `history.js`, `comments.js`, `serializer.js`, `runtime-main.js`, `app/js/main.js`, `comment-composer.js`. Moveable internals extracted directly from `app/js/vendor/moveable.min.js` (v0.53.0). Tests inventoried (`tests/e2e/`, `tests/unit/`).

**Anchor discipline:** every `file:line` below is a hint against the source as read this session. Downstream tasks MUST re-locate by quoted code content, not line number (per r2-spec §Anchor discipline — the live tree drifts).

**Load-bearing primary evidence — the Moveable resize event payload** (extracted from `moveable.min.js` @102359–102387):

```js
// inside Moveable's resize compute:
U = boundingWidth (current),  D = boundingWidth at start
W = U - D              // == distWidth  (cumulative px the dragged edge moved)
j = $ - C              // == distHeight
rt = g + W             // final frame width = startFrameWidth + distWidth
// event object emitted to onResize:
{ width: rt, height: it, offsetWidth: round(U), offsetHeight: round($),
  boundingWidth: U, boundingHeight: $, direction: Y, dist:[W,j], delta:Q, drag, isPinch }
```

**Therefore: `e.dist[0]` is exactly the 1:1 cursor-tracking delta** (the px the handle moved from drag start), and `e.width === startWidth + e.dist[0]`. The current handler consumes `e.width`/`e.height` only and **never reads `e.dist`** — this single fact underwrites R10a, R10b, R10c.

---

## Per-symptom root cause

### R10a — flex-basis amplification (G0: cursor +66 → basis +183 = 2.77×)

**Mechanism.** `onResize` (`interaction.js:201`) calls `applyVisualResize(el, role, e.width, e.height, e.direction)`. For a flex-row child (`role==='flex-child'`, parent `display:flex`), `applyVisualResize` (`interaction.js:109-111`) executes:

```js
if (isFlexRow) { if (width != null) el.style.flexBasis = width + "px"; ... }
```

It writes Moveable's requested **rendered** width (`e.width = rt`) directly into `flex-basis`. But on a `flex-grow:1.4` item in a `justify-content:center` row with slack, the browser's flex algorithm recomputes rendered width as `basis + grow_share(free_space)`. Setting `flex-basis := currentRenderedWidth` does NOT pin rendered width to that value — it re-enters the grow solver with a larger basis, and the item grows AGAIN by its grow share of the (now different) free space.

Trace proof (G0, `live-debug-raw.json` gesture 0): cursor ΔX +66 (E handle, down x=1541 → up x=1607). Moveable computed `e.width ≈ rendered+Δ`; handler wrote `flex-basis 1141px → 1324px` (`trackedStyleAfter.flexBasis`). Rendered width went 1289.2 → 1322.8 (**+33.6**), x shifted −33.6 (centered, grows both sides). So basis moved +183 while the edge the user dragged moved +33.6 — and even +33.6 ≠ the +66 cursor delta. **Two compounding errors:** (1) basis is set from a value that the grow solver then re-inflates (the +183 basis jump), and (2) the rendered edge under the cursor moves by only the grow-share fraction of intent, not 1:1.

**The 2.77× is the basis-vs-cursor ratio** (183/66). It is not a fixed constant; it is `Δbasis/Δcursor` for this specific slack+grow configuration, which is exactly why the symptom is "context-dependent."

**Why `e.width` itself is already wrong here:** Moveable derived `rt = startFrameWidth + distWidth` treating the element as if its own box tracks the handle. For a grow item, the handle drag and the box width are decoupled by the flex solver, so feeding `e.width` back as basis double-applies grow.

**Confidence: HIGH.** Code math + trace numbers agree exactly (basis 1141→1324 is recorded; grow:1.4, justify-center recorded; rendered +33.6 / x −33.6 recorded).

**Fix surface:** `applyVisualResize` (`interaction.js:105-121`), specifically the `role==='flex-child' && isFlexRow` branch (`:110`) and its column twin (`:111`). The handler must drive the **rendered** width by `e.dist[0]`, not assign `e.width` to basis. The correct primitive for a grow item is to remove grow from the equation on the resized axis (write an explicit basis/width = `startRenderedWidth + e.dist[axis]` AND neutralize `flex-grow` so the solver stops refilling), captured/restored by the resize command. `onResize` (`:201`) must start passing `e.dist` (and `e.direction`) through; `onResizeStart` (`:194-200`) already captures `beforeRect` (the start rendered rect) which is the needed `startRenderedWidth` baseline.

---

### R10b — dead zone (G2–G10: drags of −800…+653 → basis ±1–2px, rendered width pinned)

**Mechanism.** Same code path, opposite slack condition. When the accent node already consumes all container leftover space (no slack, or shrink-pinned), Moveable's `e.width` barely changes because the *element's own bounding box* cannot move the edge — the flex solver holds the rendered width at the container leftover (1322.8px). `applyVisualResize` writes `flex-basis := e.width`, but since `e.width` ≈ unchanged (the box can't grow past leftovers and grow refills any decrease), basis oscillates ±1–2px and rendered width never moves.

Live forensic (`evidence-summary.md` §Live forensics): `.flow-diagram` is 1471px, flex, justify-center, gap 10; children = `flow-node{grow:1,basis:0%,w:104}`, `flow-arrow{w:14}`, `flow-node--accent{grow:1.4, basis:1323px, w:1322.81}`, `flow-arrow{w:0}`. The accent node is the dominant grower → **rendered width = container leftovers regardless of basis**: any basis decrease is refilled by grow; any increase can't exceed available leftovers. Trace G3 (gesture index 2): cursor swept −182px down to x=1359, basis 1324→1323 (−1), rendered pinned 1322.8. G5 (gesture 4, W handle): cursor swept +653, basis ±0, rendered pinned. Identical across G2/G3/G5/G8/G9 (E handle) and G4/G10 (W handle).

The user feels this as "cannot resize." It is the SAME bug as R10a — writing `flex-basis := e.width` on a grow item — observed in the no-slack regime instead of the slack regime.

**Confidence: HIGH.** The flex-leftover mechanism is arithmetically forced by the recorded container/child geometry, and 7 gestures show the identical pinned-rendered / ±1px-basis signature.

**Fix surface:** identical to R10a — `applyVisualResize` flex branch (`:110-111`) + `onResize` passing `e.dist`. Neutralizing grow on the resized axis (so the box stops being "container leftovers") is what makes both the slack (R10a) and no-slack (R10b) regimes track the cursor 1:1. The dead zone and the amplification are one root cause with two faces; a single fix resolves both.

---

### R10c — G7 corner anomaly (NE corner, dY +36 → height −6 = 0.17×, width unchanged)

**Mechanism.** G7 (gesture index 7) is the only corner-handle gesture: `handleCls = moveable-control moveable-direction moveable-ne moveable-resizable`. Down at (1541, 389.5/390.5) on the NE control; samples sweep down-left to (1481,425.5) — pointer Y went +36 (down). NE corner = direction `[1,-1]` (east x, **north** y). Dragging the NE corner DOWNWARD (pointer +Y) means dragging the TOP edge downward → the element should SHRINK in height. Recorded: height 94 → 88 (−6), `flex-basis` 1322→1323 (width axis pinned, as in R10b). So height DID move in the correct direction (shrink), just by far less than the 36px pointer travel.

This is **not a separate bug** — it is R10b on the height axis plus a top-edge (`direction[1]===-1`) compounding factor:

1. **Width axis (`x`):** NE includes east; this is the flex-basis dead zone (R10b) — basis ±1, rendered pinned. Consistent with every other accent-node gesture. Explains "width unchanged."
2. **Height axis (`y`):** the accent node's height is NOT flex-grow-controlled (it is a single flex row; cross-axis height is `align`/content-driven). `applyVisualResize` writes `el.style.height = e.height` (`:110`, the `height != null` clause runs in BOTH the flex-row and non-flex branches). Moveable computed `e.height = startHeight + distHeight`. For a NORTH-edge drag, `distHeight` is derived from the top edge moving while `fixedDirection` holds the bottom — but the rendered height is also constrained by the row's content/line-height (the node has a min content height ~88). So `e.height` resolved near the content floor (88), giving −6 not −36. The 0.17× is `Δheight(−6)/ΔpointerY(+36)`, i.e. the gesture hit the content-driven minimum height almost immediately.
3. **`applyVisualResize` does NOT compensate `top` for flex/grid roles.** The `direction[1]===-1` top-compensation (`:118-119`) runs ONLY for `role==='absolute'`. For the flex-child accent node, a north-edge resize writes height but never adjusts position — Moveable's own `fixedDirection`/`fixedPosition` (resize anchor) is what holds the bottom edge, and that is intact (recorded `rect.y` stayed 393.1). So no position anomaly; only the height-magnitude shortfall.

**The anomaly is therefore: corner resize on the accent node = (width dead-zone from R10b) + (height clamped to content-min). Not unexplained once the height path is read.** It is fully consistent with R10a/b being the single root cause; the height axis simply has a content floor the gesture immediately reached.

**Confidence: MED-HIGH.** The width axis is HIGH (identical to R10b). The exact −6 height value depends on the node's content min-height, which I infer from the recorded 88px floor and the row layout rather than measuring computed `min-content` directly (would need a live probe, out of scope this session). The DIRECTION (shrink on north-down) and the path (`e.height` clamped at content floor, no top-comp for flex) are HIGH-confidence from code.

**Fix surface:** same `applyVisualResize` (`:105-121`). The corner case needs the height axis to also track `e.dist[1]` from the start rendered height; and the fix must verify corner handles still let Moveable's resize anchor (`fixedDirection`) hold the opposite edge (it does today). NOTE: the height-content-floor (a real CSS min-content) is legitimate — the element genuinely cannot shrink below its text. A 1:1 fix tracks the cursor until the content floor; that residual clamp is correct, not a bug to remove.

**R10 — overall fix-surface statement (mandated by Q1):** the functions that constitute the fix surface for "dragged edge tracks cursor 1:1" are:
- `applyVisualResize(el, role, width, height, direction)` — `interaction.js:105-121` (the property-mapping core; the flex branch is wrong; absolute/block branches are correct — see Healthy paths).
- `onResize(e)` — `interaction.js:201` (must pass `e.dist` and `e.direction` through; today it passes only `e.width`/`e.height`).
- `onResizeStart(e)` — `interaction.js:194-200` (already captures `beforeRect` = start rendered rect, the baseline the dist-based math needs; likely unchanged but is part of the surface).
- The resize command capture (`captureSizingState`, `interaction.js:92-104`; `commands.resize`, `commands.js:90-102`) must capture/restore `flex-grow` too if the fix neutralizes grow — TODAY it captures only `flex-basis`/`width`/`height` for the flex role (`:97-99`), so undo would NOT restore a grow change. This is a fix-surface dependency, not an existing bug.

---

### R11 — no guide lines during resize (README §How-to-use line 34 claims move-parity)

**Finding: guides are WIRED for resize and DO render on healthy paths — the "zero guides" report is a downstream symptom of R10's dead zone, NOT a missing snap config. Equal-size matching (D2) is genuinely absent and is the only net-new wiring R11 needs.**

**Evidence 1 — config already enables resize snapping.** `buildMoveable` (`interaction.js:324-335`) constructs ONE Moveable with `draggable:true, resizable:true` AND `snappable:true` (boolean), `snapDirections`/`elementSnapDirections` with `center`/`middle` true, `elementGuidelines: getElementGuidelines(el)`. Per research-02 §2a, `snappable:true` enables snapping for ALL abilities.

**Evidence 2 — Moveable's snap-ability gate passes for resize.** Extracted from `moveable.min.js` @78348:
```js
return !(!r || !p || e && !0!==r && r.indexOf(e)<0) && ...
//          r=snappable  p=enableSnap  e=ability("resizable")
```
The guard blocks snapping only when `snappable` is an array that excludes the ability. With `snappable===true` the `e && !0!==r && ...` clause is short-circuited (`!0!==r` is `true!==true` = false) → snapping is ALLOWED for `"resizable"`. **So resize snapping is not gated off.**

**Evidence 3 — resize guides actually fire on the healthy path, asserted green.** `tests/e2e/test_f2_select_guides.py::test_resize_shows_guidelines` (E-F2-5, lines 154-236) selects `.research-card` (width-path element), real-drags the E/SE handle, and asserts `found_line` (a `.moveable-line` appeared) AND width changed by >2px. This test passing means resize guides DO render when the edge actually moves.

**Why the owner saw zero guides:** the owner resized the **`.flow-node--accent`** (R10 dead-zone element). Moveable renders a guideline only when a snap edge comes within `snapThreshold` (5px) of a guideline AND the rect is moving. In the dead zone (R10b) the rendered edges NEVER MOVE (pinned at container leftovers), so no edge ever approaches a guideline, so nothing renders. **R11's "regression" is mostly R10's dead zone in disguise.** Fixing R10 (edges track cursor) will make the existing resize guides appear on the flex node for free, because the edges will move.

**What R11 still genuinely needs (D2 equal-size matching):** Moveable's `elementGuidelines` snap edges/centers to **positions** (sibling left/right/top/bottom/center), NOT to **sizes**. There is no native "snap when my width equals a sibling's width" in v0.53.0 (research-02 enumerates the full snappable API; no size-equality option exists). So D2's "snap + visual hint when width/height equals a nearby element's" is net-new and must be computed in the resize handler: on each `onResize`, compare the candidate width/height against sibling rendered dimensions (the same `getElementGuidelines` candidate set, `interaction.js:124-147`), and when within threshold, quantize `e.dist` to land exactly on the matched size and render a custom hint line. Position-snap guides (sibling edges/centers, slide bounds) are already configured and need no change beyond R10 making edges mobile.

**Confidence: HIGH** that position-snap resize guides are wired and fire on healthy paths (test asserts it; ability-gate code confirms it). **HIGH** that equal-size matching is absent (full API enumerated in research-02; no size-snap option). **MED** that fixing R10 alone restores ALL the owner-visible guides on the flex node — it restores position-snap guides for certain (edges move → snap fires), but the owner's D2 also asks for equal-size hints which R10 does not provide.

**Fix surface:** (a) position guides — NO code change needed beyond R10 (config at `buildMoveable:329-333` is already correct; `getElementGuidelines:124-147` already feeds siblings/parent/slide-root; `remount:371` already refreshes guidelines on retarget). (b) equal-size matching — new logic in `onResize` (`:201`) reading the `getElementGuidelines` candidate rects and quantizing `e.dist`, plus a custom guide-line element (Moveable won't draw size-equality lines). Optional `refresh:true` on guideline entries (research-02 §6d) if sibling reflow during flex resize makes cached rects stale.

---

### R12 — Alt-held symmetric resize (grow from center on any element)

**Finding: Moveable v0.53.0 supports center-origin resize NATIVELY via `fixedDirection`. No manual resize math is required. Lowest-risk approach: toggle `fixedDirection` per gesture from the Alt key; do NOT hand-roll symmetric math.**

**Evidence — `fixedDirection`/`fixedPosition` are the resize anchor primitives.** Extracted from `moveable.min.js`:
- @73530: `fixedPosition`/`fixedDirection` drive the resize origin computation (`originalX/Y` derived from `fixedPosition`).
- @99992 (`onResizeStart` internal): `u.startFixedDirection = u.fixedDirection; u.startFixedPosition = u.fixedPosition;` — Moveable snapshots `fixedDirection` AT resize start. The default `fixedDirection` is the corner/edge OPPOSITE the dragged handle (so the opposite side stays put = one-sided growth). Setting `fixedDirection: [0,0]` pins the CENTER → both edges move symmetrically → grow-from-center.

So Alt-symmetric is achieved by setting `moveable.fixedDirection = [0,0]` while Alt is held and restoring the default (let Moveable pick the opposite edge) when released. The cleanest hook: read `e.inputEvent.altKey` in `onResizeStart`/`onResize` and assign `fixedDirection` before Moveable computes the frame. (Moveable also exposes the Alt-resize convention in some setups via its own key handling, but explicit `fixedDirection` assignment is the deterministic, version-safe path and does not depend on Moveable's internal key wiring.)

**Interaction with D1 honest-centering (already-centered elements mirror without Alt).** The trace already shows centered elements grow both sides WITHOUT Alt: G0 (justify-center flex, x shifts −33.6 both sides) and G6/G11 (grid-centered `.intro-anchor`, x shifts left by Δ/2). That is real layout (the element is centered, so adding width pushes both edges) — per D1 this stays as-is, NO compensation CSS. Alt adds EXPLICIT center-origin resize on top, for elements that are NOT auto-centered (e.g. start-pinned grid items G12-G15, which today grow one-sided). The two are independent: D1 honest-centering is a layout consequence; Alt `fixedDirection:[0,0]` is an explicit resize-anchor override.

**Recommended approach (least risk to healthy paths):** use native `fixedDirection`, set per-gesture from `altKey`, applied at `onResizeStart` (so `startFixedDirection` captures it). Do NOT compute symmetric deltas by hand in `applyVisualResize` — that would entangle R12 with the R10 fix-surface and risk the healthy width/grid paths. `fixedDirection` is orthogonal: it changes which edge Moveable holds, and `e.dist`/`e.width` arrive already correct for that anchor, so the R10 dist-based mapping works unchanged for both one-sided and symmetric modes.

**Confidence: HIGH.** `fixedDirection` is present in the vendored bundle and is the documented resize-origin mechanism; `startFixedDirection` snapshotting at resizeStart is confirmed in the minified source.

**Fix surface:** `onResizeStart` (`interaction.js:194-200`) and/or `onResize` (`:201`) to read `e.inputEvent.altKey` and assign `moveable.fixedDirection`. NO change to `applyVisualResize`'s property mapping for R12 (it consumes the resulting `e.dist` the same way). Coupled with R10 only in that both touch the resize handlers — sequence R10 first, then layer R12.

---

### R13 — comment edit + delete (comments AND replies), island + agent-block sync (D3)

**Finding: NO edit or delete operation exists anywhere for comments or replies. The store, the panel, the bridge, and the agent block are all add/reply/resolve-only. R13 is a clean addition across 4 layers, mirroring the existing `reply`/`resolve` undoable-command pattern.**

**Where bodies live (the data model).** `comments.js` — in-memory `threadStore` (`:23`), each thread: `{id, anchor, contextText, author, createdAt, body, resolved, replies:[{author,body,createdAt}], agentInstruction}` (shape built in `add`, `:412-422`; replies pushed in `reply`, `:451-454`). Root comment body = `thread.body`. Reply body = `thread.replies[i].body`. Persisted to the island by `writeIsland` (`:254-275`) and `toJson` (`:389-401`), both of which serialize `body` and `replies` verbatim.

**What UI exists.** Panel rendering lives in **`app/js/main.js`** (`createThreadEl`, `:46-186`) — there is NO separate `comment-panel.js` shell module despite the module-map listing one (the panel is folded into `main.js`). Each thread renders: header (author/time), `.comment-body` (`:67-70`, `textContent = thread.body`), replies (`:79-105`, each `.comment-reply-body` = `r.body`), and an `actions` row (`:107-175`) with **Reply**, **Resolve/Reopen**, and **For-agents** buttons ONLY. The composer (`comment-composer.js`) supports `mode:'new'|'reply'` (`:26`) — no `edit` mode. **No Edit button, no Delete button, on either root or reply.**

**What is missing (the full gap for D3).**
| Layer | File | Missing |
|-------|------|---------|
| Store ops | `comments.js` | `editComment(commentId, newBody)`, `deleteComment(commentId)`, `editReply(commentId, replyIndex, newBody)`, `deleteReply(commentId, replyIndex)` — each as an undoable `makeCommentCommand` (mirror `reply`/`resolve` do/undo closures, `:446-499`) that mutates `threadStore` then calls `writeIsland()` + `updateMarkerState`/`removeMarker` + `emit("dirty-changed")`. Delete-root must also `removeMarker(id)` and, if `agentInstruction`, the next serialize drops it from the agent block automatically (buildAgentBlock filters `resolved!==true`; delete removes the thread entirely). |
| Bridge | `runtime-main.js` | `register("edit-comment" / "delete-comment" / "edit-reply" / "delete-reply", …)` next to the existing comment registrations (`:212-243`). |
| Panel UI | `app/js/main.js` `createThreadEl` | Edit + Delete buttons on the root thread (near Reply/Resolve, `:107-151`) AND per-reply (inside the replies loop, `:82-103`). Edit opens the composer pre-filled (needs composer `edit` mode + initial text) or an inline editor; Delete calls the bridge then `refreshCommentPanel()`. |
| Composer | `comment-composer.js` | An `edit` mode (or an `initialText` param) so the textarea pre-fills the existing body; `openComposer` currently always starts empty (`textarea.value` unset, `:48-53`). |

**Island + agent-block sync (D3 propagation).** Edits/deletes flow to the JSON island automatically because every store mutation calls `writeIsland()` (`:254-275`) and the serializer reads the live store via `toJson` (`serializer.js:86-101` → `comments.js:389`). The agent `<head>` block is rebuilt from the store on every serialize (`buildAgentBlock`, `comments.js:526-556`, called by `serializer.js:74-80,281-288`), so an edited `body` re-emits as the new `instruction:` line and a deleted agent thread vanishes from the block — NO extra wiring needed for block sync beyond the store mutation. **One caveat:** `buildAgentBlock` filters `agentInstruction===true && resolved!==true` (`:527-529`); deleting a root removes it outright, editing changes `instruction:`/`reply:` lines — both correct. Replies are already emitted to the block (`:548-550`), so editing/deleting a reply correctly changes/drops its `reply:` line.

**Undo/history integration.** Every comment mutation already pushes through the unified stack via `makeCommentCommand(label, doFn, undoFn)` (`commands.js:378-384`) + `historyPush` (`comments.js:442,467,491,516`). The four new ops MUST follow the same pattern: capture pre-state (old body / old reply object + index) in the closure, `do()` mutates + `writeIsland()` + emit, `undo()` restores + `writeIsland()` + emit. **Delete-reply undo must restore at the SAME index** (`splice(i,0,saved)`), not push to the end (replies are ordered). **Edit undo restores the exact prior `body` string.** This mirrors `reply`'s pop-based undo but must be index-safe for mid-list deletes.

**Confidence: HIGH.** Grep for `editComment|deleteComment|editReply|deleteReply|edit-comment|delete-comment` across the whole repo → zero source hits. The store/panel/bridge/composer were all read in full; the add/reply/resolve pattern is explicit and directly extensible.

**Fix surface:** `comments.js` (4 new exported factories), `runtime-main.js` (4 new `register`), `app/js/main.js::createThreadEl` (Edit/Delete buttons, root + reply), `comment-composer.js` (edit/prefill mode). History is reused unchanged.

---

### R14 — agent-anchor robustness: `data-hyp-agent` stamping + rewritten head block + fresh-agent legibility (D4)

**Finding: `data-hyp-agent` does NOT exist in any source file (only in the three R3 docs). The current agent block emits the stale structural path `anchor: body:1/section:1/div:2 | id="" | "<ctx>"`. The D4 stamping is entirely unimplemented, AND the serializer's strip pass actively REMOVES all `data-hyp-*` attributes — which is the central design tension R14 must resolve.**

**Where the head block is emitted (today).** `comments.js::buildAgentBlock` (`:526-556`) builds the HTML comment. The anchor line (`:543-546`) is:
```js
const path = escapeAgentBlock((t.anchor && t.anchor.path) || "(root)");
const nid  = escapeAgentBlock((t.anchor && t.anchor.nativeId) || "");
lines.push(`anchor: ${path} | id="${nid}" | "${ctx}"`);
```
`anchor.path` is the `buildPath` structural path (`:101-130`, `tag:nth/tag:nth` relative to nearest native-id ancestor or `documentElement`). This is exactly the S4/D4 complaint: path notation is undefined for a consuming agent (nth-of-type vs nth-child — `buildPath` uses **nth-of-type by tag**, `:118-123`, but the block never says so), `id=""` is noise when no native id, and the path goes stale the instant the consuming agent's first edit shifts the DOM. The block is inserted into `<head>` by `serializer.js:281-288` (`insertAdjacentHTML("afterbegin", …)`).

**Where stamping must happen (D4) — and the strip-order conflict.** D4 requires `data-hyp-agent="<id>"` on the TARGET element in the SAVED file, with the block referencing it via `querySelector('[data-hyp-agent="<id>"]')`. The hard constraint: `serializer.js::stripClone` (`:171-199`) walks every element and removes EVERY attribute starting with `data-hyp-` (`:180-184`), and `stripIds` (`:169`) removes `data-hyp-id`. So any `data-hyp-agent` written to the LIVE DOM before serialize would be stripped from the clone. **Stamping must therefore be applied to the CLONE, AFTER `stripClone` runs, keyed off the still-resolvable anchor — OR the strip must explicitly exempt `data-hyp-agent`.** Two viable surfaces (decision for spec, not here):
1. Exempt `data-hyp-agent` from the `data-hyp-*` strip loop (`:181`) so a live-stamped attribute survives — but then it persists in the live editing DOM as residue between saves (D4 accepts "one attribute of residue per agent comment," so this is acceptable IF removed on resolve/delete).
2. Stamp on the clone post-strip: in `serialize()` (`serializer.js:251-309`), after `stripClone` and before `outerHTML`, for each agent thread resolve its target in the CLONE (via `resolveCloneNode`-style mapping from the live matched element, `:227-247`) and set `data-hyp-agent`. This keeps the live DOM clean but requires mapping live→clone for each agent thread.

**Attribute removal on resolve/delete (D4).** D4: the attribute is removed on save once the comment is resolved/deleted. `buildAgentBlock` already excludes `resolved===true` threads (`:527-529`), and R13's delete removes the thread — so the stamping logic (whichever surface) simply iterates `agentInstruction===true && !resolved` threads; a resolved/deleted thread is not in that set, so its element is never stamped on the next save. If approach (1) is chosen (live attribute), an explicit removal on the resolve/delete commands is needed so the LIVE DOM attribute disappears; if approach (2) (clone-only), there is nothing to remove (the live DOM was never stamped).

**Rewritten head block (D4 querySelector one-liner).** The anchor line must change from the structural path to a `data-hyp-agent` reference, e.g. `target: document.querySelector('[data-hyp-agent="<id>"]')` plus the human context string. `buildAgentBlock` (`:543-546`) is the single edit point. The `escapeAgentBlock` discipline (`:522-524`, HTML-comment `-->` safety) MUST wrap the new attribute value too.

**Fresh-agent legibility (D4 verification).** The block's preamble (`:533-539`) already explains it is auto-generated/regenerated; the new anchor line gives a deterministic `querySelector` that survives the agent's own DOM edits (an attribute selector is position-independent, unlike `buildPath`). This is the D4 payoff. Verification = a fresh agent, given only the saved file, can resolve each target via the stamped attribute and apply the instruction without guessing path semantics.

**Undo/history.** Stamping happens at SERIALIZE time (a save-side transform on the clone or a live-then-strip attribute), not as a user edit — it is NOT a history operation and must NOT push a command (serialize is side-effect-free on history today; `serializer.js` pushes nothing). If approach (1) writes to the live DOM, that write must ALSO be non-undoable (or be applied on a clone) to avoid polluting the undo stack — clone-side stamping (approach 2) avoids this entirely and is the cleaner fit with the existing "serialize never mutates live history" invariant.

**Confidence: HIGH.** `data-hyp-agent` grep → zero source hits (docs only). The strip loop removing `data-hyp-*` is explicit (`serializer.js:180-184`). The block's current stale-path emission is read verbatim (`comments.js:543-546`). The clone-mapping helper (`resolveCloneNode`) already exists for the contenteditable sweep, so clone-side stamping has a proven precedent.

**Fix surface:** `comments.js::buildAgentBlock` (`:526-556`, rewrite the anchor line) + `serializer.js` (either exempt `data-hyp-agent` from the strip at `:181` AND add live stamping on the agent-tag/save path with removal on resolve/delete, OR add clone-side stamping in `serialize()` after `:262` keyed off `matchAnchor`+`resolveCloneNode`). The agent-block head insertion point (`serializer.js:281-288`) is unchanged.

---

## Healthy paths to preserve

These resize paths are EXACT-1:1 today and the R10 fix MUST NOT touch them. The R10 fix is scoped to the `role==='flex-child'` branch of `applyVisualResize` (`interaction.js:110-111`); the branches below are the `else` (block/grid) and `absolute` paths (`:112-120`), which are provably correct.

| Path | Element / gesture | Code branch | Why healthy (proof) |
|------|-------------------|-------------|---------------------|
| **Inline `width` on grid middle column** | `.intro-anchor` (hyp-22), grid `408.5 606 408.5`, grid-centered. G6 +61→`width`+60.7; G11 +71→`width`+71 (`live-debug-raw.json` gestures 6, 11) | `applyVisualResize` else-branch `:113` `el.style.width = width+"px"` | Non-grow element: `e.width` IS the rendered width 1:1. Recorded inline `width` deltas equal cursor deltas exactly. x shifts Δ/2 = REAL grid centering (side columns absorb), not a bug — per D1 this is honest layout. |
| **Grid column, start-pinned** | `.heard-item` (hyp-59/69), grid `726.5 726.5`, `justify-items:normal`. G12 −160→`width`−159.5; G13 −161→−158 (gestures 12, 13) | else-branch `:113` | Explicit width start-aligns; x pinned at 80. Recorded width tracks cursor 1:1, one-sided. |
| **Grid `repeat(3, ~474px)`** | `.stage-card` (hyp-161/165). G14 −135→width tracks; G15 −147→width tracks, x pinned (gestures 14, 15) | else-branch `:113` | Same as above; the 2×2/3-col card grids the owner confirmed "worked correctly" (`user-feedback.md` S1 counter-example, screenshot 112531). |
| **Absolute width/height + edge compensation** | any `position:absolute` target (e.g. report fixture) | `:112-120` incl. `top`/`left` comp for `direction[*]===-1` | The ONLY branch with edge-position compensation; tied to `beforeRect`. `.research-card` (R2 test element) resizes here (`width`/`height`, no flex-basis per r2-diagnosis R2) and is asserted 1:1-within-tolerance by `test_r2_resize_real.py`. |

**Also preserve (non-resize):**
- **R2 pointer-events fix** (`interaction.js:157-170` `ensureInteractionStyle`, the `.moveable-control.moveable-direction`/`.moveable-line.moveable-direction` `pointer-events:auto` rule). R10/R12 touch handlers, not the wrapper/style; do not disturb.
- **R05 zero-distance drag guard** (`onDragEnd:236-241`) and the **drop hit-test pointer-events toggle** (`:245-251`) — orthogonal to resize.
- **FLIP reorder** (`commitDrop:271-321`) — orthogonal.
- **Move = CSS `translate` only** (D2/D7) — resize must never write `translate`; the two CSS surfaces stay disjoint (decision-log "Distinct CSS surfaces").

---

## Risks and invariants

| # | Hazard | Detail / guard |
|---|--------|----------------|
| 1 | **D1 flow-aware invariant** | R10 fix MUST stay within `width`/`height`/`flex-basis`/`flex-grow`/grid-track edits and NEVER force `position:absolute` (decision-log D1). Neutralizing `flex-grow` on the resized axis is D1-legal (D1 explicitly lists `flex-grow` as an editable property); converting to absolute is NOT. |
| 2 | **Resize undo completeness** | If the R10 fix writes `flex-grow` (to kill grow-refill), `captureSizingState` (`interaction.js:97-99`) and `commands.resize` MUST capture/restore `flex-grow` too — TODAY the flex role captures only `flex-basis`/`width`/`height`. Without this, undo leaves a mutated `flex-grow` → silent layout drift. This is the highest-value regression hazard. |
| 3 | **Serializer node-count guard** | `serialize()` (`serializer.js:294-305`) aborts if `postCount !== preCount - removed + island + agentBlock`. R14 `data-hyp-agent` stamping changes ATTRIBUTES not NODES, so the node count is unaffected (attributes are not nodes in `countAllNodes`, `:61-68`) — clone-side stamping is guard-safe. BUT if R14 exempts `data-hyp-agent` from the strip (approach 1) AND the agent block insertion adds a node, `agentBlockCount` (`:280-288`) already accounts for the one Comment node; verify no double-count. R13 comment delete REMOVES island content (fewer threads) but the island is ONE `<script>` node regardless of thread count, so `islandCount` is unchanged — guard-safe. |
| 4 | **r2 fixes (do-not-rebreak)** | R2 pointer-events rule, the `onDragEnd` drop-hit-test toggle, and the R8 font-span/snapshot logic (`text-format.js`) must be untouched. R12's `altKey` read must not collide with any existing key handling. The r2-spec C1 note: "R2 task MUST NOT touch the onDragEnd pointer-events block" — R10/R12 inherit this. |
| 5 | **Undo stack (unified) ordering** | All new ops (R13 four comment ops; R10's possibly-augmented resize capture) flow through the single linear stack (`history.js`, A7). R13 delete-reply undo MUST restore at the original index (`splice(i,0,obj)`), not append — replies are ordered and the agent block emits them in order (`comments.js:548-550`). Edit undo restores the exact prior string. |
| 6 | **116-test suite** | Re-run all of `tests/e2e/` + `tests/unit/`. Specific watch: `test_r2_resize_real.py` (resizes `.research-card`, the GRID/width healthy path; `delta=2` change asserts + a `>before-5` width-grows check — R10 fix must keep this path 1:1) and `test_f2_select_guides.py::test_resize_shows_guidelines` (asserts a `.moveable-line` renders during resize on `.research-card`; R11 must not regress position-snap guides). `test_f5_comments.py` + `test_g2_save_with_comments.py` exercise the comment store/island/agent-block — R13/R14 must keep their assertions green. |
| 7 | **Test masking risk (carry-over from r2)** | `test_r2_resize_real.py` uses `delta=2`/`delta=15`/`delta=20` tolerances and resizes the HEALTHY width element — it would NOT have caught the flex-basis dead zone or the 2.77× amplification (those live on `.flow-node--accent`, never tested). New R10 tests MUST assert 1:1 (`|Δrendered − Δcursor| ≤ small`) on a FLEX-GROW element specifically, and on the corner (height axis), or the fix is unverified. Use the PRISTINE twin `tecer-gsmm-introduction.html` (zero flex-basis residue) per `evidence-summary.md` §Test-file state. |
| 8 | **Equal-size matching (R11) custom guides** | If R11 adds size-equality hint lines, they must be `hyp-`namespaced (A12) so the serializer strips them, and `pointer-events:none` so they don't block handles. Moveable will NOT draw them — they are a custom overlay, a new strip-surface to verify. |
| 9 | **R12 × R10 coupling** | Both touch the resize handlers. `fixedDirection:[0,0]` (symmetric) changes which edge Moveable holds; the R10 `e.dist`-based mapping must work for BOTH anchors (it does — `e.dist` is anchor-relative). Sequence R10 first, verify 1:1 one-sided, THEN add R12; do not interleave. |
| 10 | **Centered-context UX (R12/D1)** | Do NOT add compensation CSS to "fix" the both-sides growth of centered elements (G0 flex-center, G6/G11 grid-center). D1 mandates honest layout: centered elements legitimately grow both sides; Alt adds EXPLICIT symmetric on top. Removing the natural centering would violate D1. |
| 11 | **`data-hyp-agent` live residue (R14 approach 1)** | If the attribute is written to the live DOM (strip-exemption approach), it MUST be removed on resolve/delete or it accumulates. D4 accepts one-attribute residue per UNRESOLVED agent comment, not unbounded growth. Clone-side stamping (approach 2) sidesteps this but needs live→clone mapping per thread. |
| 12 | **Composer edit-mode regression (R13)** | Adding `edit` mode to `comment-composer.js` must not break the `new`/`reply` viewport flip/clamp (D12, `:103-118`) or the `For-agents` checkbox (only present in `new` mode, `:55-64`). Edit mode should likely hide the agent checkbox (agent-tag is a separate toggle in the panel). |

---

## Open questions

1. **R10 fix primitive — which exactly?** Two viable: (a) `flex-grow:0` + explicit `flex-basis = startRendered + dist[0]` on the resized axis (kills refill, fully 1:1), vs (b) write `width`/`height` directly + `flex-basis:auto`. (a) is more invasive to the layout model but deterministic; (b) is lighter but `flex-grow` still present may re-inflate on container resize. Needs a spec decision; both require capturing `flex-grow` for undo (Risk 2). Recommend (a) for true 1:1, but flag the undo-capture dependency.
2. **R10c height content-floor** — the exact `min-content` height of `.flow-node--accent` (inferred ~88px from the trace) was not probed live this session (out of scope). A 1:1 fix tracks cursor until that floor; confirm the floor is content-driven (legitimate) and not another bug, with one live `getComputedStyle` probe during R10 implementation.
3. **R11 equal-size threshold & hint visual** — D2 asks for "snap + visual hint when width/height equals a nearby element's." Snap threshold (reuse the 5px `snapThreshold`?), which siblings count (the `getElementGuidelines` 30-candidate cap, `interaction.js:135-145`?), and the hint line's style/namespace are unspecified. Needs a spec decision.
4. **R12 Alt source** — `e.inputEvent.altKey` read in the resize handler vs Moveable's own key convention. Recommend explicit `fixedDirection` assignment (version-safe); confirm Moveable does not separately consume Alt in a way that conflicts.
5. **R14 stamping surface — approach 1 (strip-exempt + live attr + remove-on-resolve) vs approach 2 (clone-only post-strip).** Approach 2 keeps the live DOM clean and is history-safe but needs per-thread live→clone mapping; approach 1 is simpler to write but adds live residue requiring explicit removal. D4 accepts residue, leaning approach 1, but approach 2 better honors "serialize never mutates live state." Needs a spec decision.
6. **R14 multiple agent comments on the SAME element** — `data-hyp-agent="<id>"` is single-valued; if two unresolved agent threads anchor the same element, the attribute can hold only one id. Need a convention (space-separated id list? first-wins? per-thread distinct attribute?). The current path-based block has no such collision; the attribute approach introduces it.
7. **Stray re-parent observation (open, low priority)** — `evidence-summary.md` §Test-file state notes the live flow row showed only 4 children (trailing `flow-node` absent) after the 16 gestures, while the saved file is structurally complete. Possibly a corner-handle re-parent during today's session. Worth ONE look during R10 testing (could be a FLIP/reorder edge case on corner gestures), but not reproduced in the trace and not in R10–R14 scope unless it recurs.
