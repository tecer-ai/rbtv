# V4-T4 Post-Commit Review — R12 Alt-symmetric resize (`ff9cab7`)

**Reviewer:** post-commit judge (read-only on code; sole write = this file).
**Commit:** `ff9cab79dfdd07c30383706d4a3e599c64bf1526` "V4-T4: R12 Alt symmetric resize, selection guard, docs".
**Baseline:** R10 `0381c47` reviewed CLEAN.
**Inputs read:** `git show ff9cab7`; `spec.md` (R12 + ADX-1..4); `adx4-probe.md`; `v4-t4-BUG.md`; `test_r12_alt_symmetric.py` (on-disk == committed); `interaction.js` (current); `selection.js`; `element-registry.js::roleOf`; `commands.js` surface (via probe §2); `decision-log.md` D1/D2/D7/D12/D14 + Distinct-CSS-surfaces row; `v4-t4-run.txt`.
**Anchor discipline:** line numbers are hints against the tree as read 2026-06-05; edits located by quoted content.

**OVERALL VERDICT: FIX-NEEDED (one LOW-severity bounded deviation + two NOTES).** The committed code is functionally green (5/5 R12, 9/9 R10, full suite 129 passed / 1 skipped / 0 failed) and is correct for every geometry any current fixture or the tecer decks exercise. The single fix is a forward-looking robustness gap (start-aligned flex-grow under Alt) that no test covers and that ADX-4 would have closed had it been followed verbatim. Ship-blocking only if start-aligned flex rows are in scope for R12; otherwise land as a documented bounded case + a one-line follow-up.

---

## Finding 1 — flex-child translate-skip deviation — **FIX-NEEDED (LOW / bounded)**

**Evidence.** `interaction.js:241` gates the center-shift write `if (resizeAltActive && role !== "absolute" && role !== "flex-child")`, and `:245` writes `el.style.translate = ${baseTranslateResize[0] - e.dist[0]/2}px ${baseTranslateResize[1] - e.dist[1]/2}px`. So **flex-child is excluded from the translate write**; block/grid-child receive it; absolute is handled separately via left/top (`:146-148`). Kimi's rationale (commit body + `v4-t4-run.txt:42`): "NO translate for flex-child because flex layout's justify-content:center already symmetrically re-centers."

**The rationale is TRUE only for auto-centering parents.** For a `flex-child` row the R10 write (`applyVisualResize` `:132-134`) sets `flex-grow:0; flex-shrink:0; flex-basis = beforeRect.width + dist[0]`, i.e. the main-axis box grows by `dist[0]` (= 2Δ). Where that growth lands is the parent's `justify-content` decision:
- `justify-content:center` (both fixtures, `flow-grow.html:4`) → the flex line re-centers → both edges move symmetrically → **center fixed with NO translate.** Adding `−dist/2` here would double-compensate (the exact failure the rationale cites). Correct to skip.
- `justify-content:flex-start` → line packs from the start edge → **left edge pinned, grows right-only → center drifts +Δ.** No compensation is applied → the element resizes one-sided under Alt.
- `justify-content:flex-end` → right edge pinned, grows left → center drifts −Δ.

**Contract impact.** R12 contract-1 ("dragged edge tracks cursor, opposite edge mirrors, width 2Δ on ANY element") and D1's "the user must have BOTH options, predictably, not as a layout accident" are violated for a start-aligned flex-grow child: Alt produces the SAME one-sided growth the S2/R12 complaint was filed to kill. **`adx4-probe.md` §3.1 + ADX-4 (binding amendment) BOTH prescribe writing `e.drag.beforeTranslate` for every flow role with `role !== "absolute"` — which INCLUDES flex-child.** The committed code deviates from ADX-4 on two axes: (a) it hand-computes `−dist/2` instead of reading Moveable's `beforeTranslate` (probe §3.0 PRIMITIVE: "do NOT hand-compute the shift; read e.drag.beforeTranslate"); (b) it drops flex-child from the write entirely.

**Why the deviation is currently invisible (and why severity is LOW).** Every flex parent in every committed fixture is `justify-content:center`; the only flex-grow Alt test (E-R12-4, `node-accent`) runs under center, where skip == correct. The live tecer decks (per spec G0/diagnosis) are center/coupled flow rows. So **no current test nor known deck path is red.** ADX-2 also sanctions "layout-honest mirroring in centered/coupled contexts," which covers the center case the deviation happens to land on.

**No test covers a start-aligned flex parent** (verified: zero `justify-content:flex-start|start` across `tests/`; the only flex fixtures are the two `justify-content:center` files). So the deviation is structurally untested, not test-covered-and-passing.

**VERDICT: accept-as-bounded for THIS commit, but record FIX-NEEDED as a tracked follow-up** (the honest reading: it is a real ADX-4 deviation, kept out of scope only because no in-scope geometry triggers it). Exact justify-aware fix:

> In `onResize`, extend the center-shift to `flex-child` BUT gate on the parent's main-axis packing. Compute once at `onResizeStart` from the parent: `const j = getComputedStyle(parent).justifyContent;` and the child's auto-margin state. Apply the `−dist/axis/2` translate write to a flex-child ONLY when the parent does NOT auto-center the child on the resized main axis — i.e. when `justifyContent` resolves to a start/end pack (`flex-start`/`start`/`left`, or `flex-end`/`end`/`right`) AND the child has no `auto` margin on that axis. For `center`/`space-around`/`space-evenly`/`space-between`-with-single-item (auto-centering), SKIP (current behavior). Sign: start-pack needs `translate -= dist/2`; end-pack needs `translate += dist/2`. (This is precisely the per-frame-vs-reflow subtlety that made `beforeTranslate` non-trivial for flex — Moveable's transform-space `beforeTranslate` is computed pre-reflow and does not see the flex re-solve, which is why the justify-aware host computation, not the raw `beforeTranslate`, is the correct flex fix. Block/grid have no reflow re-solve, so their `−dist/2` == `beforeTranslate` and is already correct.)

Until then, document in the R12 non-goals: "Alt on a start-aligned (`justify-content:flex-start/flex-end`) flex-grow child grows one-sided (center drifts ±Δ); auto-centered flex parents are symmetric. Bounded deviation, ADX-2-class."

---

## Finding 2 — the "selection guard" hunk — **NOTE (commit-message drift) + the real guard is CLEAN**

**The commit message is wrong about where the guard lives.** It claims "selection.js: add early-return in select() when re-selecting same element to prevent spurious remount." **selection.js is NOT in commit `ff9cab7`** (`--stat` lists only `interaction.js`, the test, and 3 docs). The `select()` early-return (`selection.js:147-151`, `if (selectedHypId === hypId) { updateRing(); return; }`) has existed since `822c1e5` (the v1 build) — confirmed via `git log -L 146,151:selection.js` → first/only touch is `822c1e5`. So the message describes a pre-existing guard as if newly added; **no selection.js change shipped in this commit.**

**The ACTUAL net-new guard-adjacent change is in interaction.js:** `onDragEnd`'s no-op-move ("none") branch gained `remount(activeHypId)` at `:308` (the diff hunk `beforeTranslate = ""; baseTranslate = [0,0]; dragDist = 0; + remount(activeHypId); return;`). The diff also stripped three inline comments from `onDrag` (`:270-274`) — cosmetic, no behavior change.

**What `remount(activeHypId)` at `:308` does and why it is correct, minimal, R12-scoped.** The "none" branch fires when a drag exceeded `DRAG_THRESHOLD` but the drop hit-test classified no reorder/reparent (a free move that keeps its translate). Before this commit, the Moveable control box was left pointing at the element's PRE-move rect (the wrapper/handles did not follow the translated element), because only the reorder path (`commitDrop` `:368`) and resize path remount. After R12, a free move writes a non-zero `translate`, and a SUBSEQUENT Alt-resize reads `baseTranslateResize = parseTranslate(el.style.translate)` at `onResizeStart:234` — so the Moveable frame MUST be re-seeded to the post-move geometry or the next resize's handles/center-shift baseline desync. `remount` (`:409-421`) re-points `moveable.target`, refreshes `elementGuidelines`, and calls `updateRect()` — exactly the re-seed needed. It is symmetric with the reorder branch (which already remounts) and the resize path; the "none" branch was the one drop outcome that previously skipped it.

**Scope-creep / drag-endangerment check — none found.** `remount` does NOT teardown/rebuild Moveable (that is `mount`/`unmount`); it only updates target+rect on the existing instance, so no drag state is lost and no handler is re-wired. The R2 pointer-events rule, the R05 zero-distance guard (`:283-288`, a SEPARATE earlier branch that returns before reaching `:308`), and FLIP are untouched (I5 holds). The R2 suite passing 8/8 and the full suite green (`v4-t4-run.txt:36`) confirm no drag regression. **The change is correct, minimal, and properly R12-coupled (it exists because R12 made resize read the live translate baseline).**

**NOTE severity only:** the commit message's "selection.js ... early-return" line is a factual misattribution (drift between message and diff). It does not affect code correctness but should be corrected in the convention log — see Commit-message NOTE at the end.

---

## Finding 3 — Absolute branch — **CLEAN (the prompt's "MISSING?" premise is FALSE)**

The prompt asks whether ADX-4's left/top `−dw/2 / −dh/2` compensation for absolute-under-Alt is "implemented elsewhere or MISSING." **It is implemented**, in `applyVisualResize` (`interaction.js:143-152`):

```
if (role === "absolute") {
  const dw = width != null ? width - beforeRect.width : 0;
  const dh = height != null ? height - beforeRect.height : 0;
  if (resizeAltActive) {
    if (dw !== 0) el.style.left = originalLeft - dw / 2 + "px";
    if (dh !== 0) el.style.top  = originalTop  - dh / 2 + "px";
  } else { /* unchanged one-sided -dw / -dh at direction===-1 */ }
}
```

This matches `adx4-probe.md` §3.3 verbatim (the `dw/2` per-side shift; `dw = e.width − beforeRect.width` is the doubled total growth under `fixedDirection:[0,0]`, so `dw/2` = per-side). The commit message's "absolute branch compensates left/top by -dw/2 -dh/2" is accurate here (unlike its selection.js claim). The `onResize:241` guard correctly EXCLUDES absolute from the translate write (`role !== "absolute"`), so absolute uses left/top exclusively — no double-write. `captureSizingState` absolute branch (`:96-98`) captures `top`/`left` (NOT `translate`) → undo restores position atomically via the same resize command (probe §3.3, I1-compliant: absolute resize legally edits top/left per decision-log "Absolute-positioned targets" row).

**No test asserts Alt-on-absolute** (verified: zero absolute+Alt coverage in `tests/`). The implementation is present and matches the contract, but the `/2` assumption flagged in probe §3.3-Note ("verify `e.width` is doubled for an absolute target; drop `/2` if not") and the probe verification-checklist item 2 are **UNVERIFIED by any committed test.** Code is correct-by-contract; verdict CLEAN, with one residual:

> **Residual (LOW):** add an Alt-on-absolute E2E (start-pinned absolute element, Alt E-drag +Δ, assert center fixed ±3 and left == originalLeft − Δ) to convert the probe-checklist-item-2 assumption into a guard. Not blocking (no absolute deck path in R12 scope), but the only untested branch of the Alt feature.

---

## Finding 4 — Shift-math equivalence (`base − dist/2` vs probe `beforeTranslate`) — **CLEAN (equivalent; R11 interplay flagged)**

The committed block/grid write `el.style.translate = baseTranslateResize[axis] − e.dist[axis]/2` (`:245`) vs the probe's prescribed `e.drag.beforeTranslate` (probe §3.1):

**They are algebraically identical for the no-snap case.** Probe §1-C/§1-D: `beforeTranslate = G = startValue + conjugateOffset`, where `startValue` is the element's translate at gesture start (== `baseTranslateResize`, captured identically at `onResizeStart:234`) and the conjugate center offset under `fixedDirection:[0,0]` is exactly `−growth/2 = −dist/2` (dist arrives doubled = total growth). So `beforeTranslate[axis] == baseTranslateResize[axis] − dist[axis]/2`. The committed formula reproduces `beforeTranslate` by recomputation.

**Snap-perturbation distinction (the load-bearing point for R11):** the probe (§1-B field map) draws a sharp line — `beforeTranslate` (= `G`) is the **BEFORE-snap** translate; `translate` (= `k`) is the **SNAPPED** value, and it explicitly warns "snap can perturb it; do NOT use for symmetric math." The committed `baseTranslateResize − dist/2` equals the **before-snap** `G`, NOT the snapped `k`. **This is the safe choice:** it is snap-independent by construction (it never reads a Moveable-snapped number), so a position-snap firing mid-Alt-resize cannot perturb the center-shift. E-R12-5 (prior-translate edge) passes because the formula folds the pre-existing move via `baseTranslateResize` (= `parseTranslate(el.style.translate)` = `80px` → `after_tx ≈ 80 − 60 = 20`, asserted `:234`).

**Flag for the R11 implementer (equal-size snap lands next per AD7 R10→R12→R11):** R11's equal-size override (S3-8) REPLACES the dist-derived size target with a matched candidate dimension BEFORE the write. When that fires under Alt, the size written (`flexBasis`/`width`) lands on the matched value, but the committed center-shift at `:245` still uses the RAW `e.dist[0]/2` (the un-snapped distance), NOT the matched-size-derived growth. **Interplay risk:** if equal-size snap changes the effective growth from `dist[0]` to `matched − beforeRect.width`, the translate center-shift (`−dist/2`) will be computed off the pre-snap growth → the box centers around the wrong point by `(dist[0] − (matched−beforeRect.width))/2`. **R11 MUST recompute the center-shift from the FINAL applied size delta, not raw `e.dist`, whenever an equal-size override is active under Alt.** Position-snap (Moveable's own) is already safe (before-snap `G` is used); only the NET-NEW equal-size override introduces this coupling. Recommend R11 derive the shift as `−(appliedSizeDelta[axis])/2` composed onto `baseTranslateResize`, replacing the `e.dist[axis]/2` term for the Alt path.

---

## Finding 5 — Undo atomicity (translate folded into resize command) — **CLEAN**

`captureSizingState` now captures `translate` for both flow branches: `:104` (flex-child) and `:107` (block/grid `else`), `m.translate = s.getPropertyValue("translate") || ""`. Absolute branch (`:96-98`) correctly does NOT capture translate (uses top/left). `onResizeEnd:251` diffs `for (const k of Object.keys(after)) if (beforeSizing[k] !== after[k])` over the WHOLE map → `translate` is automatically in the change-detection and in `makeResizeCommand(activeHypId, beforeSizing, after)` (`:253`). One `historyPush`, one command. Per probe §3.2, `applyStyleMap` maps `""`→`removeProperty` and a string→`setProperty`, so **absent-inline restores to absent** and a prior-move string restores exactly. `kebabCase("translate") == "translate"` (no transform needed).

**Kill assertion (quoted, E-R12-5 `:230-237`):**
```
after = self.rendered("twin")
after_tx = parse_px(after["translate"].split()[0]) ...
self.assertAlmostEqual(after_tx, move_tx - 60, delta=5)   # translate folded + composed onto prior move
center_after_x = (after["left"] + after["right"]) / 2
self.assertAlmostEqual(center_after_x, center_before_x, delta=3)  # one gesture keeps center fixed
```
This proves translate is written and composes onto the prior move. **Coverage gap (NOTE, not a defect):** no R12 test performs an explicit `Ctrl+Z` and asserts BOTH size AND translate revert in one step, nor the absent-inline-restores-to-absent path (E3/E2 in probe §4). The MECHANISM is correct by inspection (translate rides the same map as `flex-basis`/`width`/`height`; `applyStyleMap` `""`-handling is exercised by the R10 undo tests for the flex longhands, same code path), but the explicit single-undo-restores-both assertion the probe checklist item 3 calls for is absent. Recommend adding it in R11/R13 test passes. Verdict CLEAN (atomicity is structurally guaranteed; the gap is test-coverage, not behavior).

---

## Finding 6 — Test quality (5 R12 cases vs amended contracts) — **CLEAN (kill assertions intact, nothing weakened)**

All five cases carry hard kill assertions matching the (ADX-amended) contracts; none are xfailed/skipped/softened:

| Case | Kill assertions (quoted) | Contract |
|------|--------------------------|----------|
| E-R12-1 (`:135-137`) | `right−before.right == 60 ±3`; `before.left−after.left == 60 ±3`; `w grows 120 ±4` | C1 edge-tracks-cursor + mirror + 2Δ (block `#twin`) |
| E-R12-2 (`:152-153`) | `|left shift| ≤ 2`; `right == 60 ±3` | C2 no-Alt one-sided |
| E-R12-3 (`:179`) | post-Alt non-Alt gesture: `|left shift| ≤ 2` | resizeEnd reset (per-gesture `setFixedDirection` scope, ADX-3) |
| E-R12-4 (`:196-205`) | `right 60 ±3`; `left 60 ±3`; `w 120 ±4`; `inlGrow == 0.0`; `inlBasis == before.w + 120 − pad ±4` | C4 composes-with-R10; inlBasis is the **ADX-1 content-box-converted** value (correct per ADX-4 last line) |
| E-R12-5 (`:218,234,237`) | `move_tx == 80 ±5`; `after_tx == move_tx−60 ±5`; `center fixed ±3` | E1 prior-move edge (absolute beforeTranslate) |

- **Width 2Δ kill present** (E-R12-1/-4: `w − before.w == 120 ±4`). ✔
- **Edge tracks cursor ±3 present** (E-R12-1/-4: `right == 60 ±3` AND mirror `left == 60 ±3`). ✔
- **Center fixed ±3 present** (E-R12-5: `center_after_x == center_before_x ±3`). ✔
- **No-Alt regression** (E-R12-2/-3) guards that the Alt path does not leak into default resize. ✔

**E-R12-4's `inlBasis` expectation is CORRECT, not weakened.** `v4-t4-BUG.md:38,68` recorded that the FROZEN test expected `before.w + 120` (border-box) but `applyVisualResize`'s `toContent` subtracts padding for content-box → 547 vs 594.6. The committed test (`:200-205`) was AUTHORED to the ADX-1 reality: it computes `pad` live and asserts `inlBasis == before.w + 120 − pad ±4`. This is the right post-ADX-1 contract (ADX-4: "E-R12-4's flex-basis expectation is the ADX-1-CONVERTED value"), not a relaxation. Since these tests are NET-NEW in this commit (R12 is new, file added here), "FROZEN/cannot-edit" applied to the EARLIER red-first draft; the committed green version encodes the amended contract correctly. ✔

**Prior-move edge (E-R12-5) is a genuine kill, not synthetic-only.** It sets `translate='80px 0px'` + remount to seed Moveable from live transform state (E1 live-probe path), then asserts the composed result — exercising the real `baseTranslateResize` composition, not a stub. ✔

**One observation (not a defect):** E-R12-1 asserts the left edge mirrors on `#twin` (role=block) — this is the branch that DOES get the translate write, so it validates the block center-shift. The flex-child center-shift-SKIP (Finding 1) is validated ONLY under justify-center (E-R12-4), which is why the start-aligned gap is invisible. Tests are honest about what they cover; they simply do not cover the start-aligned flex geometry (Finding 1). No assertion is weakened to hide it.

---

## NOTE — Commit-message convention drift

Two message/diff mismatches (record per convention log; neither affects code):
1. **selection.js misattribution (Finding 2):** the message's "selection.js: add early-return in select()..." describes a guard that pre-exists since `822c1e5`; selection.js is not in this commit. The actual new guard-adjacent change is `remount(activeHypId)` in `interaction.js` `onDragEnd`'s "none" branch — undocumented in the message.
2. **flex-child framing (Finding 1):** the message says "skip translate for flex-child to avoid double-compensation with flex re-centering" — accurate ONLY for auto-centering parents; it reads as if universally justified. Recommend the message (and the R12 non-goals) state the bound: "skip for AUTO-CENTERED flex parents; start-aligned flex-grow under Alt is a known bounded one-sided case (follow-up)."

---

## Fix list (if FIX-NEEDED is actioned)

1. **(Finding 1, LOW/bounded)** Extend the `onResize:241` center-shift to `flex-child` gated on the parent's main-axis `justify-content` (apply `∓dist/2` for start/end packs with no auto margin; skip for center/space-auto). Document the bound in R12 non-goals until then. — REQUIRED only if start-aligned flex rows are in R12 scope; otherwise track as follow-up + doc.
2. **(Finding 3, LOW)** Add an Alt-on-absolute E2E asserting center-fixed + left/top `−Δ` (closes probe-checklist item 2; the only untested Alt branch).
3. **(Finding 5, LOW)** Add an explicit single-`Ctrl+Z`-restores-size+translate assertion incl. absent-inline→absent (closes probe-checklist item 3).
4. **(Finding 4, for the R11 implementer — not this commit)** Derive the Alt center-shift from the FINAL applied size delta when an equal-size override is active, not raw `e.dist` — else equal-size snap + Alt mis-centers by half the snap correction.
5. **(NOTE)** Correct the commit-message selection.js/flex-child claims in the convention log.
