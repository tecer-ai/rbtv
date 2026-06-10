# V4-T6 Post-Commit Review — R12 justify gate (`4efff64`) + R11 equal-size snap (`d4618e5`)

**Reviewer:** post-commit judge (read-only on code; sole write = this file). Read-only git only; no web.
**Commits reviewed (both on `master`, HEAD = `d4618e5`):**
- `4efff64` "[v4-t4-fix] R12: justify-aware flex-child center-shift gate + absolute/undo test coverage"
- `d4618e5` "[v4-t6] R11: equal-size snap + size hints (move-parity guides verified)"

**Inputs read:** `git show 4efff64`, `git show d4618e5`; `spec.md` (R11/R12 + ADX-1..6, lines 76–101, 183–334, 482–490); `v4-t4-review.md` (the review mandating the justify gate — Finding 1 §28–32 provides the gate logic, Finding 4 §81 mandates the Alt-snap recompute); `v4-t5-red.txt` (UTF-16 red-first run) + `v4-t6-run.txt`; current `runtime/js/interaction.js`; `runtime/js/serializer.js`; vendored `app/js/vendor/moveable.min.js` (post-handler dist-consumption flow); `tests/e2e/test_r11_resize_guides_equal_size.py` + `test_r12_alt_symmetric.py` (both on-disk == committed, verified via `git diff <sha>` → empty); `tests/e2e/fixtures/flow-grow.html`.

**Anchor discipline:** line numbers are hints against the tree as read 2026-06-05; every edit located by quoted content.

**OVERALL VERDICT: CLEAN (two LOW/MINOR notes + one untested-triple gap at MINOR).** Both commits are functionally green (R11 6/6, R10 9/9, R12 7/7, combined 22/22 per `v4-t6-run.txt`). The justify gate matches the v4-t4 review's prescribed logic; the ADX-6b Alt-snap recompute is implemented exactly as Finding 4 demanded; the dist-mutation override is architecturally SAFE (verified against the vendored bundle — Moveable does not read `e.dist` after the handler returns). The candidate exclusion is broader than spec S3-7 in a strictly-safer direction. No ship blocker. The only residue is a known-bounded composition gap (Alt + snap + non-centering flex parent) that no fixture exercises, identical in class to the v4-t4 Finding 1 bound.

---

## Finding 1 — Justify-aware center-shift gate (`4efff64`) — **CLEAN (matches the v4-t4 review's prescribed logic) + one MINOR keyword-coverage note**

**Evidence.** `interaction.js:289–298` computes the skip flag at `onResizeStart`:
```
flexChildCenterShiftSkip = false;
if (role === "flex-child" && el.parentElement) {
  const cp = getComputedStyle(el.parentElement);
  const j = cp.justifyContent;
  if (j === "center" || j === "space-around" || j === "space-evenly") { flexChildCenterShiftSkip = true; }
  if (cs.marginLeft === "auto" || cs.marginRight === "auto") { flexChildCenterShiftSkip = true; }
}
```
and `onResize:357–359` gates the write `if (resizeAltActive && role !== "absolute")` → `const isFlex = role === "flex-child"; if (!isFlex || !flexChildCenterShiftSkip)` → writes `base − d/2`. So a flex-child is skipped ONLY when its parent auto-centers (`center`/`space-around`/`space-evenly`) OR the child has a horizontal auto-margin; **every other flex child now receives the standard `base − dist/2` translate**, exactly as block/grid-child. This is a verbatim implementation of ADX-6a (spec:490) and of the v4-t4 review Fix-1 (`v4-t4-review.md:28–32, 136`).

**Four justify cases (the v4-t4 Finding 1 §18–20 enumeration), each handled:**

| Parent `justify-content` (computed) | Pre-fix (v4-t4) | This commit |
|--------------------------------------|-----------------|-------------|
| `center` | skip (correct) | skip → CORRECT (re-centers itself; `−dist/2` would double-compensate) |
| `flex-start` | skip (WRONG — one-sided drift, the v4-t4 bug) | **now writes `base − dist/2`** → FIXED |
| `flex-end` | skip (WRONG) | **now writes `base − dist/2`** → FIXED |
| `space-around`/`space-evenly` | skip (correct) | skip → CORRECT (named in gate) |
| auto horizontal margin | (not handled) | skip → CORRECT (ADX-6a's auto-margin clause) |

**The two new tests are present and are hard kills (test file on-disk == committed):**
- **E-R12-6 `test_e_r12_6_alt_on_absolute`** (`test_r12_alt_symmetric.py:267–290`): forces `#twin` to `position:absolute; left:100; top:80`, Alt SE-drag, asserts BOTH centers fixed ±3 AND `after["left"] == before["left"] − dw/2 ±3` AND `after["top"] == before["top"] − dh/2 ±3`. This is the absolute-branch `−dw/2 / −dh/2` assertion ADX-6c and the v4-t4 Finding 3 residual called for. ✔
- **E-R12-7 `test_e_r12_7_combined_undo`** (`:293–319`): seeds `translate='40px 20px'`, Alt E-drag, asserts width AND translate both changed, then ONE `bridge_command(undo)` restores `undone["w"] == before_w ±2` AND `undone["translate"] == before_tx` (exact string). This is the single-undo-restores-size+translate assertion ADX-6c and v4-t4 Finding 5 demanded. ✔ The new `bridge_command` helper (`:56–84`) is a faithful postMessage round-trip mirroring the existing `bridge_get_selection`.

**MINOR note — computed-keyword coverage is incomplete (untested, no fixture triggers it).** The gate matches the literal computed strings `"center"`, `"space-around"`, `"space-evenly"`. It does NOT cover: (a) `space-between` with a single flex item — the v4-t4 review §30 explicitly lists "`space-between`-with-single-item (auto-centering)" as a SKIP case, and ADX-6a's intent is "re-centers on its own"; a lone item under `space-between` packs to the start edge (does NOT auto-center), so OMITTING it from the skip set is actually CORRECT (it should get `−dist/2`), contradicting the v4-t4 review's parenthetical — the commit's behavior is right, the review's aside was wrong; (b) logical/keyword-resolved values `start`/`end`/`left`/`right` — `getComputedStyle().justifyContent` on Chromium returns `flex-start`/`flex-end`/`center` for the physical cases here, but CSS `justify-content: start` resolves to computed `"start"`, which is NOT in the gate. A `justify-content:start` parent would (correctly) fall through to the `−dist/2` write — but a `justify-content: safe center` or `space-between`-single-item that the author INTENDED to auto-center would not skip. No committed fixture uses any of these (grep over `tests/`: zero `start`/`flex-start`/`safe`/`space-between`), so this is structurally untested, not test-covered-and-passing. **Severity MINOR:** the only auto-centering values any fixture or the tecer decks produce are `center` (handled). Recommend a one-line comment noting the gate keys on the three physical auto-centering computed values + auto-margin, and that logical-keyword `start`/`end` resolve to the non-skip path by design.

---

## Finding 2 — dist-mutation override wiring (`d4618e5`) — **CLEAN (mutation is SAFE — verified against the vendored bundle; axis-scoped correctly)**

**Evidence.** `onResize:325` copies the event array (`let dist = [...e.dist]`) — it mutates a COPY, never `e.dist` itself. The equal-size override (`:341–352`) writes back to this copy only for the flex-child main axis:
```
const wMatch = snapEqualSize(snapWidth, "width");
if (wMatch.match) { width = wMatch.value; if (role === "flex-child" && isFlexRow) dist[0] = width - beforeRect.width; activeSizeMatch = wMatch.match; }
const hMatch = snapEqualSize(snapHeight, "height");
if (hMatch.match) { height = hMatch.value; if (role === "flex-child" && !isFlexRow) dist[1] = height - beforeRect.height; ... }
```
then `applyVisualResize(el, role, width, height, e.direction, dist)` (`:355`) consumes the snapped `dist`. For a flex-child, `applyVisualResize` (`:137`) writes `flexBasis = beforeRect[mainDim] + dist[mainAxisIdx]` — so the snapped main-axis value lands exactly on the matched candidate. **Axis-scoping is correct:** width-match touches `dist[0]` only when `isFlexRow` (main axis = horizontal); height-match touches `dist[1]` only when `!isFlexRow` (main axis = vertical). The cross axis is never mutated by the override (it is a plain `width`/`height` write in `applyVisualResize`, which for the flex-child cross-axis already reads `beforeRect + dist` for the non-overridden cross dimension — consistent).

**Is mutating Moveable's event payload safe? YES — confirmed by bundle inspection (the load-bearing architectural check).** The override mutates a COPY of `e.dist`, but even mutating `e.dist` directly would be safe. In `moveable.min.js` (line 9, minified) the resize dispatch is:
```
…transform:nt},et,e)));return !p && la(t,"onResize",ot), ot
```
`ot` is the resize event object (carries `dist`); `la(t,"onResize",ot)` (`la = function(t,e,n,r,i){return t.triggerEvent(e,n,r,i)}`) dispatches it synchronously to the user handler, then `ot` is RETURNED and the function ends — there is **no read-back of `ot.dist` after dispatch**. The next pointer-move frame runs the internal compute `at()` → `Ra(X,H,r,e)` (`function Ra(t,e,n,r){…l=r.distX,f=r.distY…g=n.fixedDirection…}`), which RECOMPUTES `distWidth`/`distHeight` from raw pointer deltas (`r.distX/distY`) and internal state (`fixedDirection`, `ratio`, start offsets) — never from the previously-dispatched event's `dist`. There is **no `resizeAfter` hook** (grep: absent; drag has `dragAfter`, resize does not). Conclusion: **Moveable treats each frame's event as fire-and-forget; mutating `e.dist` cannot corrupt its state.** The `[...e.dist]` copy is belt-and-suspenders, not load-bearing.

**Cleaner-equivalent? The chosen approach is the correct one (note-level only — behavior is correct).** The spec change map (S3-8, spec:314) prescribes overriding the *applied size target* `t` and applying it in "the existing write." The commit does exactly that for block/grid (via `width`/`height`). For flex-child it ALSO mutates `dist` because `applyVisualResize`'s flex branch is driven by `beforeRect + dist`, not by `width` — the run-evidence conclusion (`v4-t6-run.txt:48–49`) documents this precisely ("via dist mutation … rather than e.width, which Moveable perturbs for flex layouts"). An alternative would be to pass an explicit `appliedMainSize` parameter into `applyVisualResize` rather than back-deriving `dist[axis] = matched − beforeRect`, which would avoid the round-trip through dist arithmetic. But the current form is algebraically exact (`flexBasis = beforeRect[mainDim] + (matched − beforeRect[mainDim]) = matched`) and keeps `applyVisualResize`'s signature stable. **No correctness issue; the dist-mutation is the minimal wiring given the existing flex write path.**

---

## Finding 3 — ADX-6b: Alt center-shift recomputed from FINAL applied size delta — **CLEAN (implemented exactly as v4-t4 Finding 4 mandated; asserted under Alt)**

**Evidence (the exact code path).** `onResize:357–371`:
```
if (resizeAltActive && role !== "absolute") {
  const isFlex = role === "flex-child";
  if (!isFlex || !flexChildCenterShiftSkip) {
    let dx, dy;
    if (activeSizeMatch) {
      const dw = width != null ? width - beforeRect.width : 0;
      const dh = height != null ? height - beforeRect.height : 0;
      dx = dw / 2; dy = dh / 2;
    } else {
      dx = e.dist[0] / 2; dy = e.dist[1] / 2;
    }
    el.style.translate = `${baseTranslateResize[0] - dx}px ${baseTranslateResize[1] - dy}px`;
  }
}
```
When an equal-size snap is active (`activeSizeMatch`), the center-shift is derived from `width − beforeRect.width` and `height − beforeRect.height` — i.e. the **FINAL POST-SNAP applied size delta** (`width`/`height` are already the snapped values at this point, set at `:343`/`:349`). Only when no snap is active does it fall back to raw `e.dist/2`. This is verbatim ADX-6b (spec:490) and the precise fix v4-t4 Finding 4 prescribed (`v4-t4-review.md:81`: "derive the shift as `−(appliedSizeDelta[axis])/2` … replacing the `e.dist[axis]/2` term for the Alt path"). The mis-centering-by-half-the-snap-correction hazard is closed. ✔

**A test asserts centered-snap correctness under Alt.** **E-R11-6 `test_e_r11_6_alt_equal_size_snap_center_fixed`** (`test_r11_resize_guides_equal_size.py:269–301`): injects a `match-target` div at width 304, Alt E-drags `#twin` past 304 so the snap pulls it to exactly 304, then asserts BOTH `after["w"] == 304 ±0.5` (snap landed) AND `center_after_x == center_before_x ±3` (center held under Alt + snap-corrected shift). This exercises the `activeSizeMatch` branch of the center-shift recompute under Alt. ✔

---

## Finding 4 — Hint overlay (`hyp-size-hint` / `-badge`) — **CLEAN (fully namespaced, pointer-events:none, triple-torn-down, serializer-stripped)**

**Evidence.**
- **Fully hyp-namespaced:** `showSizeHint` (`:251`, `:258`) sets `className = "hyp-size-hint"` and badge `"hyp-size-hint-badge"`. ✔
- **pointer-events:none:** both the outline (`:253`) and the badge (`:264`) set `pointerEvents = "none"`. The overlay cannot block Moveable handles. ✔ (E-R11-3 `:301` asserts computed `pointerEvents === "none"`.)
- **Lives inside the wrapper:** `wrapper.appendChild(sizeHintEl)` (`:266`) — the hint is a child of `hyp-interaction-wrapper` (itself `document.body`-appended, `pointer-events:none`, `position:absolute`). Positioned with scroll offset (`:268–269`, `rect.left + window.scrollX` / `rect.top + window.scrollY`) per spec S3-9/G5. ✔
- **Torn down at resizeEnd AND on teardown/unmount:** `clearSizeHint()` is called at `onResizeEnd` in BOTH the early-return (no-element) path (`:381`) AND the normal path (`:394`), and in `teardown()` (`:531`, reached by `unmount`). `clearSizeHint` (`:275–278`) removes the node and nulls the ref. So the hint cannot survive a gesture end or a selection change. ✔ (E-R11-3 `:308` asserts `hint_after == 0` post-gesture.)
- **Cannot leak into saves — serializer strip reaches it (triple-protected).** `serializer.js:9–11, 31, 39` removes "every element whose id or any class token is `hyp-` prefixed" via `startsWith("hyp-")` — the `hyp-size-hint`/`-badge` classes are caught DIRECTLY by the class-prefix strip, independent of the wrapper. Additionally the wrapper is `hyp-` prefixed and body-appended → stripped transitively (spec L6/S3-13). Additionally `clearSizeHint()` at resizeEnd removes it from the live DOM before any serialize even runs. **E-R11-4** (`:200–224`) empirically saves after an equal-size gesture and asserts `"hyp-size-hint" not in text` AND `re.findall(r'class="[^"]*hyp-size-hint', text) == []`. ✔

---

## Finding 5 — Candidate exclusion: ALL `flex-grow>0` excluded — **CLEAN (broader than spec S3-7, strictly safer; no legitimate target lost; no phantom)**

**Evidence.** `onResizeStart:300–315` builds `sizeCandidates` from `slideRoot.querySelectorAll("[data-hyp-id]")` (independent of `getElementGuidelines`), filters to `c !== el` and non-zero rect, then the F5 exclusion (`:305–313`):
```
const pd = getComputedStyle(cand.parentElement).display;
if ((pd === "flex" || pd === "inline-flex") && parseFloat(getComputedStyle(cand).flexGrow) > 0) { return false; }
```

**This is BROADER than spec S3-7** (spec:42), which excludes a candidate ONLY when `c.parentElement === el.parentElement` (same-parent sibling) AND that shared parent is flex AND `flexGrow > 0`. The commit drops the same-parent qualifier: it excludes ANY flex item with `flexGrow > 0` in ANY flex container across the slide.

**Judged correct both ways:**
- **Does it exclude legitimate stable-size targets?** No. The rule fires ONLY on `flexGrow > 0`. A `flex-grow:0` item in a grow row parses `flexGrow` to `0` → `0 > 0` is false → **NOT excluded** → remains a candidate. So author-sized items in flex rows (the legitimate equal-size targets) are correctly retained. On `flow-grow.html` concretely: `node-a`/`node-b`/`node-accent` (grow 1/1/1.4) → excluded (solver-derived, correct); `twin` (grow:0, explicit `width:300`) → included (the intended match, correct). ✔
- **Does the broadening leave any solver-derived phantom?** No — it does the opposite: it removes MORE solver-derived sizes than the spec's same-parent rule. A `flex-grow>0` item's rendered size is the solver's grow-share output regardless of WHICH flex container it sits in, so it is an equally-meaningless equal-size target everywhere. Excluding it globally eliminates cross-container phantom snaps the same-parent rule would have admitted. **The broadening is a strict improvement** (spec's own S3-7 rationale: "flex-grow rendered width is the solver's output, not an author-set size"). E-R11-5 (`:227–254`) guards the no-phantom contract: it overshoots a grow sibling and asserts `abs(accW1 − siblW) > 1.0` AND `hint == 0`. ✔

**NOTE (independence from `getElementGuidelines`):** spec S3-7/change-map (spec:313) said to build candidates via `getElementGuidelines(el).map(...)`. The commit instead queries `[data-hyp-id]` under `slideRoot` directly. This is a deliberate, documented deviation (`v4-t6-run.txt:46–47`: candidates "built independently from all data-hyp-id elements") and is the correct call given Finding 7 (reverting `getElementGuidelines` to sibling-only would have STARVED the candidate set of the cross-container `twin`, which is the primary equal-size target). The two concerns — position guides vs size candidates — are now correctly decoupled. ✔

---

## Finding 6 — E-R11-6 `raw_target` (304−4 → 304+4) — **CLEAN (legitimate trajectory correction, NOT an assertion weakening)**

**Before/after intent (git-traced).** The R11 test file was added in a SINGLE commit (`d4618e5`); `git log -p --all` over the file shows `raw_target = 304 + 4` is the ONLY value ever committed — there is no `304 - 4` in git history. The red-first snapshot `v4-t5-red.txt` (UTF-16) contains only **five** tests (E-R11-1..5); **E-R11-6 did not exist red-first** (it was authored during the green pass to assert ADX-6b). So the "304−4 → 304+4" change was an in-development tuning of the NEW E-R11-6 fixture trajectory, never a regression of a previously-red assertion.

**Quoted intent — it is a cursor-trajectory correction.** E-R11-6 (`:280–284`):
```
# Alt-resize east: target just past 304 so snap pulls it to exactly 304
raw_target = 304 + 4
target_travel = raw_target - twinW0
```
The comment states the intent: drive the cursor JUST PAST the 304 candidate so the snap band (`|t − 304| ≤ 4`) is crossed and the override fires, landing width on exactly 304. `304 − 4 = 300` would stop the cursor SHORT of (or AT the near edge of) the candidate; `304 + 4 = 308` carries the cursor through the band so the snap reliably engages. **This is a zero-travel/trajectory correction — moving where the cursor RESTS relative to the snap target — not a relaxation of any kill.** The two assertions are unchanged and strict: `after["w"] == 304 ±0.5` (snap lands ON the value, not merely within band) AND `center_after_x == center_before_x ±3` (center held under Alt). Both deltas (±0.5, ±3) are identical to what a kill assertion requires; neither was widened. Correctness of the chosen target is empirically settled by the green run (`v4-t6-run.txt`: E-R11-6 PASSED). ✔

---

## Finding 7 — `getElementGuidelines` revert to sibling-only — **CLEAN (revert is complete, no half-state; position-guide scope intact)**

**Evidence.** `getElementGuidelines` (`:160–183`) builds candidates from `parent.children` siblings (`:162–163`) + `parent` (`:167`) + `slideRoot` (`:168`), deletes `targetEl` (`:169`), caps at 30 by nearest-center (`:171–181`). This is the ORIGINAL sibling+parent+slide-root scope — there is NO residue of any expanded "all `[data-hyp-id]` in slide" scope inside `getElementGuidelines` itself. The expanded query now lives EXCLUSIVELY in `onResizeStart`'s `sizeCandidates` block (`:300–315`), fully separated from the position-guide path. **No half-state:** `buildMoveable:517` and `remount:559` both call `getElementGuidelines(el)` (the reverted sibling-only function) for `elementGuidelines`; `sizeCandidates` is the independent equal-size path. The two are cleanly decoupled, exactly as `v4-t6-run.txt:45–47` claims ("getElementGuidelines reverted to original sibling-only scope to avoid perturbing Moveable position snap for existing R10/R12 tests").

**Position-guide tests still assert the original scope.** **E-R11-1 `test_e_r11_1_position_guides_fire_on_flex_grow`** (`:155–180`) asserts `.moveable-line` renders during a real flex-grow resize AND width changes — the move-parity guide contract (spec R11 contract 1), on the sibling-scoped guideline set. The committed run confirms R10 (9/9, includes the E-F2/`test_f2_select_guides` position-guide regressions) and R12 (7/7) stay green AFTER the revert (`v4-t6-run.txt:30–38`) — i.e. the revert restored the position-snap behavior those suites depend on. The claim that the EXPANDED scope perturbed position snap (causing R10/R12 regressions) and was therefore reverted is consistent with the evidence: the independent `sizeCandidates` path carries the equal-size feature without feeding the expanded set into Moveable's `elementGuidelines`. ✔ (Note: I did not re-run the suite — read-only on code; I rely on the committed `v4-t6-run.txt` evidence + structural inspection of the decoupling.)

---

## Finding 8 — Cross-compose: R12 justify gate × R11 Alt-snap recompute — **CLEAN for the covered geometry; MINOR untested-triple gap (Alt + snap + non-centering flex parent)**

**Do they compose?** By construction, yes — the two features touch the same `onResize` block (`:357–371`) and are independent:
- The justify gate decides WHETHER a flex-child gets a center-shift write (`!isFlex || !flexChildCenterShiftSkip`).
- The Alt-snap recompute decides the MAGNITUDE of that write (`activeSizeMatch ? (width−beforeRect.width)/2 : e.dist[0]/2`).
For a flex-child under a NON-centering parent (`flex-start`/`flex-end`) with Alt held AND an equal-size snap active, the gate would (correctly, post-`4efff64`) take the write path, and the magnitude would (correctly, per ADX-6b) be derived from the post-snap size delta. The composition is logically sound: `flexChildCenterShiftSkip` is computed once at `onResizeStart` (gate), `activeSizeMatch` per-frame (magnitude); they do not interfere.

**Is there a test for that triple? NO.** Grep over `tests/e2e/`: ZERO occurrences of `flex-start` / `justify-content:start` / non-centering `justifyContent`. Every flex fixture (`flow-grow.html`, `flow-grow-deadzone.html`) is `justify-content:center`. Therefore:
- E-R12-6/-7 cover Alt × absolute and Alt × undo, but on absolute/block roles.
- E-R11-6 covers Alt × snap × center-fixed, but on `#twin` (a block element, `role !== "flex-child"` → the gate is irrelevant; `flexChildCenterShiftSkip` is never set for a non-flex role).
- **No test runs Alt + equal-size snap on a flex-child under a non-centering parent** — the exact geometry where BOTH the `4efff64` gate-flip (skip→write) AND the `d4618e5` post-snap magnitude must be simultaneously correct.

**Severity judgment: MINOR (same class as the v4-t4 Finding 1 bound — structurally untested, not known-red).** The triple's correctness rests on two independently-tested mechanisms composing in an obvious way (gate sets a boolean at start; magnitude reads it per-frame). No committed fixture or known tecer deck path produces a non-centering flex parent (the decks are center/coupled per spec G0). The risk is a forward-looking robustness gap, not a live defect: if a future deck introduces a `justify-content:flex-start` flex row AND the user Alt-resizes a child into an equal-size band, the path is exercised for the first time with no guard. **Recommend (non-blocking) a single E2E:** `flow-grow.html` variant with `justify-content:flex-start` + an in-range equal-size candidate, Alt E-drag a flex-child into the snap band, assert width lands on the matched value AND center stays fixed (`center_after == center_before ±3`). This converts the obvious-by-inspection composition into a guard and closes the last untested corner of the combined R11+R12 Alt surface.

---

## Summary table

| # | Item | Verdict | Severity |
|---|------|---------|----------|
| 1 | Justify-aware gate (`4efff64`) matches v4-t4 logic; 4 cases handled; 2 new tests | CLEAN | MINOR note (computed-keyword `start`/`end`/`space-between`-single coverage untested; current behavior correct) |
| 2 | dist-mutation override safe + axis-scoped | CLEAN | — (bundle-verified: Moveable does not read `e.dist` post-handler; no `resizeAfter`) |
| 3 | ADX-6b Alt center-shift from post-snap delta; E-R11-6 asserts | CLEAN | — |
| 4 | Hint overlay namespaced, pointer-events:none, triple-torn-down, serializer-stripped | CLEAN | — |
| 5 | All `flex-grow>0` excluded (broader than S3-7) | CLEAN | — (strictly safer; grow:0 targets retained; no phantom) |
| 6 | E-R11-6 `304−4 → 304+4` | CLEAN | — (trajectory correction, not assertion weakening; ±0.5/±3 kills intact) |
| 7 | `getElementGuidelines` revert to sibling-only | CLEAN | — (complete, no half-state; position-guide scope intact) |
| 8 | R12 gate × R11 Alt-snap compose | CLEAN (covered geometry) | MINOR gap (Alt + snap + non-centering flex parent untested) |

## Fix list (none blocking; all LOW/MINOR follow-ups)

1. **(Finding 8, MINOR)** Add an E2E for the triple: `justify-content:flex-start` flex row + Alt + equal-size snap on a flex-child; assert snap lands AND center fixed. Closes the last untested corner of the combined Alt surface.
2. **(Finding 1, MINOR)** Add a one-line comment in `onResizeStart` noting the justify gate keys on the three physical auto-centering computed values + auto-margin, and that logical-keyword `start`/`end` and `space-between`-single-item resolve to the non-skip (`−dist/2`) path by design. (No code change — behavior is correct; the v4-t4 review's `space-between`-single-item-as-skip aside was itself incorrect.)
