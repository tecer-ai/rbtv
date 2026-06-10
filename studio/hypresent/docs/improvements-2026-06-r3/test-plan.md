# Hypresent v3 — Test Plan (Session 3, improvements-2026-06-r3)

Executor-ready test plan for **R10–R14** + the regression set + the R14 fresh-agent legibility verification. Pairs 1:1 with `spec.md` (same session). Every case is named, numbered, grouped by R, and carries a concrete fixture, a REAL-input action sequence, and exact assertions with tolerances. No TBDs.

**Harness conventions (binding — match exactly, from `tests/e2e/conftest_helpers.py` + existing suites):**
- `unittest.TestCase`; `setUpClass` starts the server (`H.start_server(PORT, test_dialog=True)`) + Chromium (`headless=True`); `tearDownClass` closes both.
- REAL input only: `page.mouse.move/down/up/click`, `page.keyboard.down/up/press`. NEVER `dispatchEvent` for the gesture under test.
- Iframe-scoped JS via `H.doc_eval(page, body)` (the body is a function receiving `(doc, win)`).
- On-screen coords: iframe origin (`getBoundingClientRect` of `iframe.doc-frame`) + element rect inside the iframe.
- **D14 selected==target guard (MANDATORY for every selection-dependent case):** after the selecting click, read `get-selection` via the bridge, resolve the intended target's `data-hyp-id` (by its native id), and `assertEqual(selected_hypId, target_hypId)` BEFORE any outcome assertion. Reference: `test_r2_resize_real.py::test_edge_handle_resize_changes_geometry` and `test_r7_alignment.py`.
- **Synthetic fixtures only (AD8):** the four committed fixtures — `H.copy_synthetic("flow-grow.html")` (R10 slack/R11/R12), `H.copy_synthetic("flow-grow-deadzone.html")` (R10 dead-zone red-first), `H.copy_synthetic("grid-healthy.html")` (R10 healthy-grid), `H.copy_synthetic("agent-comments.html")` (R13/R14) — opened via `H.open_via_dialog_ui(page, base, path)`. The new `copy_synthetic` helper + `SYN_DIR` guard are specified in `spec.md §Synthetic fixtures`. NEVER reference `tecer-gsmm-introduction*.html`.
- `H.preset_author(page)` to skip the comment-author prompt.

**Per-axis tolerance rationale:** R10 contracts assert 1:1 within **±2px** (sub-pixel rounding + `throttleResize:1`); the corner height axis uses **±3px** (content-floor proximity). R12 Alt assertions: each EDGE position tracks its target within **±3px** (the dragged edge tracks the cursor 1:1, the opposite edge mirrors by the same Δ — F1: under `fixedDirection:[0,0]` Moveable doubles `e.dist`, so width grows **2Δ**, asserted within **±4px** because the width sum accumulates both edges' rounding). These are TIGHTER than the masking `delta=15/20` tolerances in `test_r2_resize_real.py` — that suite resizes the HEALTHY width element and would NOT catch amplification/dead-zone (Risk-7); the R10 tests MUST assert tight 1:1 on the flex-grow element specifically.

**New test files (one per R, mirroring existing naming):**
`tests/e2e/test_r10_resize_flex.py`, `test_r11_resize_guides_equal_size.py`, `test_r12_alt_symmetric.py`, `test_r13_comment_edit_delete.py`, `test_r14_agent_stamping.py`, and `tests/e2e/test_r14_legibility.py` (the fresh-agent design harness).

---

## Shared helpers (reused across R10/R11/R12 cases)

These are COMPLETE, transcribable bodies — a non-reasoning implementer copies them verbatim. `iframe_origin` and `rect_in_iframe` are the module-level helpers `_iframe_origin`/`_rect_in_iframe` from `test_r2_resize_real.py` (copy them too). `_scroll_into_view` is copied from `test_r2_resize_real.py::_scroll_into_view`. `parse_px(s)` = `float((s or "0").replace("px","").strip() or 0)`.

```python
import re

def parse_px(s):
    return float((s or "0").replace("px", "").strip() or 0)

def bridge_get_selection(page):
    """postMessage get-selection round-trip — returns the selection result dict
    (a dict like {"hypId": "<id>"}, or None). Transcribed verbatim from test_r2_resize_real.py E-R2-8."""
    return page.evaluate(
        """
        async () => {
            const iframe = document.querySelector('iframe.doc-frame');
            return new Promise((resolve, reject) => {
                const id = 'probe-' + Date.now() + '-' + Math.random();
                const handler = (e) => {
                    if (e.origin !== location.origin) return;
                    if (e.data?.source !== 'hyp') return;
                    if (e.data?.kind === 'response' && e.data?.id === id) {
                        window.removeEventListener('message', handler);
                        if (e.data.ok) resolve(e.data.result);
                        else reject(new Error(e.data.error));
                    }
                };
                window.addEventListener('message', handler);
                iframe.contentWindow.postMessage(
                    { source: 'hyp', kind: 'command', id, type: 'get-selection' },
                    location.origin
                );
                setTimeout(() => {
                    window.removeEventListener('message', handler);
                    reject(new Error('bridge get-selection timed out'));
                }, 5000);
            });
        }
        """
    )

def select_by_native_id(self, native_id):
    """Click an element's on-screen center, then D14-assert the runtime selected it."""
    sel = f'#{native_id}'
    self._scroll_into_view(sel)               # copied from test_r2_resize_real
    origin = _iframe_origin(self.page)
    rect = _rect_in_iframe(self.page, sel)
    self.assertIsNotNone(rect, f"element {sel} not found for selection")
    self.page.mouse.click(origin["x"]+rect["x"]+5, origin["y"]+rect["y"]+5)  # +5 → target itself, not a child
    self.page.wait_for_timeout(300)
    info = bridge_get_selection(self.page)    # postMessage get-selection (pattern in test_r2_resize_real E-R2-8)
    target_id = H.doc_eval(self.page, f"const e=doc.querySelector('#{native_id}'); return e?e.getAttribute('data-hyp-id'):null;")
    self.assertEqual(info.get("hypId") if info else None, target_id,
                     f"selected {info.get('hypId') if info else None} but target is {target_id}")

# Moveable control/line class for each handle direction. The control box renders
# corner CONTROLS (.moveable-control.moveable-{e,se,ne,nw,sw}) and edge LINES
# (.moveable-line.moveable-{e,w,n,s}). Mapping (from test_r2_resize_real _handle_center
# / E-R2-8 edge-line probe + test_f2 line 185):
#   "e"  → east edge: .moveable-line.moveable-e (fallback corner .moveable-control.moveable-e)
#   "se" → SE corner control: .moveable-control.moveable-se (fallback .moveable-se)
#   "ne" → NE corner control: .moveable-control.moveable-ne (fallback .moveable-ne)
#   "w"  → west edge: .moveable-line.moveable-w (fallback .moveable-control.moveable-w)
_HANDLE_SELECTOR = {
    "e":  ".moveable-control-box .moveable-line.moveable-e, .moveable-control-box .moveable-control.moveable-e, .moveable-control-box .moveable-e",
    "se": ".moveable-control-box .moveable-control.moveable-se, .moveable-control-box .moveable-se",
    "ne": ".moveable-control-box .moveable-control.moveable-ne, .moveable-control-box .moveable-ne",
    "w":  ".moveable-control-box .moveable-line.moveable-w, .moveable-control-box .moveable-control.moveable-w, .moveable-control-box .moveable-w",
}

def edge_handle_screen(self, which):
    """On-screen (x,y) center of the requested Moveable handle inside the iframe;
    asserts the handle is rendered AND its center is within the iframe viewport.
    `which` in {"e","se","ne","w"}. Pattern: test_r2_resize_real::_handle_center."""
    sel = _HANDLE_SELECTOR[which]
    origin = _iframe_origin(self.page)
    h = H.doc_eval(
        self.page,
        f"const el=doc.querySelector({sel!r});"
        "if(!el) return null; const r=el.getBoundingClientRect();"
        "return {x:r.left,y:r.top,w:r.width,h:r.height,"
        " in_vp:(r.left+r.width/2>=0 && r.left+r.width/2<=win.innerWidth && r.top+r.height/2>=0 && r.top+r.height/2<=win.innerHeight)};",
    )
    self.assertIsNotNone(h, f"resize handle {which!r} ({sel}) not rendered after selection")
    self.assertTrue(h["in_vp"], f"resize handle {which!r} center is outside the iframe viewport — control box mis-placed")
    return origin["x"] + h["x"] + h["w"] / 2, origin["y"] + h["y"] + h["h"] / 2

def rendered(self, native_id):
    return H.doc_eval(self.page,
      f"const e=doc.querySelector('#{native_id}'); const r=e.getBoundingClientRect(); const cs=getComputedStyle(e);"
      f"return {{w:r.width,h:r.height,left:r.left,right:r.right,top:r.top,bottom:r.bottom,"
      f" basis:cs.flexBasis, grow:cs.flexGrow, shrink:cs.flexShrink,"
      f" inlBasis:e.style.flexBasis, inlGrow:e.style.flexGrow, inlShrink:e.style.flexShrink,"
      f" inlWidth:e.style.width, inlHeight:e.style.height}};")
```

---

## R10 — Resize 1:1 (`test_r10_resize_flex.py`, fixture `flow-grow.html`)

### E-R10-1 — Slack-row amplification killed (the G0 case)
- **Setup:** open `flow-grow.html`; `select_by_native_id("node-accent")` (D14).
- **Action:** record `before = rendered("node-accent")`. Locate the E edge handle (`edge_handle_screen("e")`). `mouse.move(hx,hy); mouse.down();` then 10 steps `mouse.move(hx + i*6, hy)` (total ΔX ≈ +60), `wait 30ms` each; `mouse.up()`. Record `after = rendered("node-accent")`.
- **Assertions:**
  - `assertAlmostEqual(after["right"] - before["right"], 60, delta=2)` — dragged (right) edge tracks cursor net travel (NOT 2.77×).
  - `assertAlmostEqual(after["w"] - before["w"], 60, delta=2)` — rendered width grew by cursor delta, not basis-inflated.
  - `assertEqual(float(after["inlGrow"]), 0.0)` — `flex-grow` neutralized inline.
  - `assertAlmostEqual(parse_px(after["inlBasis"]), before["w"] + 60, delta=2)` — inline basis = startRendered + dist.
- **Falsifies:** the 2.77× amplification (a regressed build writes basis 1141→1324 and right-edge moves ~+33 ≠ 60 → fails delta=2).

### E-R10-2 — No-slack dead zone killed (leftover-pinned accent shrinks 1:1) — TRUE red-first (F6)
- **Fixture:** `flow-grow-deadzone.html` (accent `grow:8` + inline `flex-basis:1100px` → leftover-pinned, the genuine R10b condition; the PRISTINE `flow-grow.html` accent has slack and would test amplification-in-reverse, not the dead zone — see spec §flow-grow-deadzone).
- **Setup:** open `flow-grow-deadzone.html`; `select_by_native_id("node-accent")`. (No priming gesture — the dead zone is reproduced on the FIRST gesture because the accent is already leftover-pinned.)
- **Action:** record `before = rendered("node-accent")`. E-handle drag −120 (10 steps of `mouse.move(hx - i*6, hy)`, net cursor ΔX ≈ −120); `mouse.up()`. Record `after`.
- **Assertions:**
  - `assertAlmostEqual(after["w"] - before["w"], -120, delta=2)` — rendered width shrank by the cursor delta (NOT pinned at container leftovers).
  - `assertAlmostEqual(after["right"] - before["right"], -120, delta=2)` — right edge tracked the cursor.
  - `assertEqual(float(after["inlGrow"]), 0.0)` — grow neutralized (the write that escapes the dead zone).
- **Red-first proof (PRE-fix, current master — from `evidence-summary.md` G2/G3/G5/G8/G9):** on master `applyVisualResize` writes `flexBasis = e.width`; with the accent leftover-pinned, `e.width` barely changes and grow refills any basis decrease, so `flex-basis` moves ±1px and **rendered width stays UNCHANGED (Δ ≈ 0)**. The assertion `|Δrendered − (−120)| ≤ 2` then FAILS on master by ≈120px. This is the dead-zone bug, reproduced for the RIGHT reason on this fixture.

### E-R10-2b — First-gesture escape on the leftover-pinned fixture (dead zone gone on fresh open) — red-first (F6)
- **Fixture:** `flow-grow-deadzone.html` (same leftover-pinned accent).
- **Setup:** open `flow-grow-deadzone.html`; `select_by_native_id("node-accent")`. (No prior gesture.)
- **Action:** record `before = rendered("node-accent")`. E-handle drag −100 on the FIRST gesture (net cursor ΔX ≈ −100). Record `after`.
- **Assertion:** `assertAlmostEqual(after["w"] - before["w"], -100, delta=3)` — the very first gesture escapes the dead zone because the write neutralizes grow within the same `onResize` stream.
- **Red-first proof (PRE-fix, current master):** identical mechanism to E-R10-2 — on master the leftover-pinned accent's rendered width is PINNED (Δ ≈ 0 for a −100 cursor sweep, per the recorded G2-G10 signature), so `|Δrendered − (−100)| ≤ 3` FAILS by ≈100px. Run this against master BEFORE writing the fix and record the observed Δ in the test-plan run log to demonstrate (not assume) red-first.

### E-R10-3 — Healthy block/grid width path UNCHANGED (1:1, no flex props)
- **Setup:** open `flow-grow.html`; `select_by_native_id("twin")` (a plain `width:300px; height:120px` block — `roleOf` → `block` because its parent `.slide` is not flex/grid).
- **Action:** record `before`. E-handle drag +50. Record `after`.
- **Assertions:**
  - `assertAlmostEqual(parse_px(after["inlWidth"]), 300 + 50, delta=2)` — inline `width` = prev + Δ (the `else` branch, unchanged).
  - `assertEqual(after["inlBasis"], "")` AND `assertEqual(after["inlGrow"], "")` — NO `flex-basis`/`flex-grow` written on a non-flex element.
- **Falsifies:** the R10 fix accidentally touching the healthy `else` branch.

> NOTE: `flow-grow.html`'s `twin` is a `block` element. E-R10-4/-5 below cover the grid-track healthy path with full fidelity on the COMMITTED `grid-healthy.html` fixture (spec §grid-healthy.html — `#grid-mid` in a centered `408px 606px 408px` row, `#grid-start` start-pinned in a `justify-items:normal` row, mirroring live G6/G11/G12).

### E-R10-4 — Healthy grid MIDDLE column unchanged (1:1, centered, no flex props)
- **Setup:** open `grid-healthy.html`; `select_by_native_id("grid-mid")` (a grid child of `.intro-grid`; equal side columns absorb → grid-centered).
- **Action:** record `before = rendered("grid-mid")`. E-handle drag +61 (net cursor ΔX ≈ +61). Record `after`.
- **Assertions:**
  - `assertAlmostEqual(after["w"] - before["w"], 61, delta=2)` — rendered width grew 1:1 (the `else`/grid branch, unchanged).
  - `assertEqual(after["inlBasis"], "")` AND `assertEqual(after["inlGrow"], "")` — NO `flex-basis`/`flex-grow` written on a grid child.
  - `assertAlmostEqual(before["left"] - after["left"], 30, delta=4)` — x shifted left by ≈Δ/2 (REAL grid centering, honest layout per D1 — NOT a bug).
- **Falsifies:** the R10 fix touching the grid `else` branch (writes a flex prop, or breaks the 1:1 width).

### E-R10-5 — Healthy grid START-PINNED column unchanged (1:1, one-sided, no flex props)
- **Setup:** open `grid-healthy.html`; `select_by_native_id("grid-start")` (a grid child of `.heard-grid`, `justify-items:normal` → start-pinned).
- **Action:** record `before = rendered("grid-start")`. E-handle drag −160 (net cursor ΔX ≈ −160). Record `after`.
- **Assertions:**
  - `assertAlmostEqual(after["w"] - before["w"], -160, delta=2)` — rendered width shrank 1:1.
  - `assertEqual(after["inlBasis"], "")` AND `assertEqual(after["inlGrow"], "")` — NO flex props written.
  - `assertLessEqual(abs(after["left"] - before["left"]), 3)` — x pinned (one-sided, start-aligned).
- **Falsifies:** the R10 fix perturbing the start-pinned grid path.

### E-R10-6 — Corner height axis tracks cursor to the content floor (AD2)
- **Setup:** open `flow-grow.html`; `select_by_native_id("node-accent")`.
- **Probe FIRST (before the gesture — G11: the content-floor probe MUTATES `style.height`, so it MUST run before selection's gesture capture, never interleaved mid-drag):** `content_floor = H.doc_eval(self.page, "const e=doc.querySelector('#node-accent'); const prev=e.style.height; e.style.height='0'; const f=e.getBoundingClientRect().height; e.style.height=prev; return f;")` — this sets height to 0, reads the content-min rect, then restores `prev` (an empty `prev` restores via `e.style.height = ""`, which removes the inline prop). Run this BEFORE `mouse.down()` so the gesture's `onResizeStart` capture sees the pristine element.
- **Action:** record `before = rendered("node-accent")`. Locate the NE corner control (`edge_handle_screen("ne")`). `mouse.move(hx,hy); mouse.down()`; 6 steps `mouse.move(hx, hy + i*6)` (pointer +ΔY ≈ +36, north edge dragged down → shrink). `mouse.up()`. Record `after = rendered("node-accent")`.
- **Assertions:**
  - `assertLess(after["h"], before["h"])` — height shrank (correct direction on north-down).
  - `assertGreaterEqual(after["h"], before["h"] - 40)` — bounded; tracks cursor toward the content floor, does not overshoot.
  - `self.assertTrue(abs((before["h"]-after["h"]) - min(36, before["h"]-content_floor)) <= 3)` — the residual clamp is the content floor (accepted, not a bug); `content_floor` was probed BEFORE the gesture.

### G-R10-UNDO — Undo restores ALL three flex longhands incl. absent-inline (AD1, Risk-2)
- **Setup:** open `flow-grow.html`; `select_by_native_id("node-accent")`. Record `pre = {inlBasis, inlGrow, inlShrink}` BEFORE any gesture (all `""` on the pristine fixture).
- **Action:** E-handle drag +60 (writes basis + grow:0 + shrink:0). Then `bridge.command("undo")`; `wait 150ms`. Record `post = {inlBasis, inlGrow, inlShrink}`.
- **Assertions:**
  - `assertEqual(post["inlBasis"], pre["inlBasis"])` (both `""`).
  - `assertEqual(post["inlGrow"], pre["inlGrow"])` (both `""`).
  - `assertEqual(post["inlShrink"], pre["inlShrink"])` (both `""`).
  - `assertAlmostEqual(rendered_after_undo["w"], before_gesture["w"], delta=2)` — rendered width back to start.
- **Falsifies:** the highest-value hazard — a build that writes `flex-grow:0` but does NOT capture it leaves `inlGrow="0"` after undo → fails. Also covers the absent-inline case explicitly (pre was `""`).

### G-R10-REDO — Undo→redo idempotence
- **Action:** after G-R10-UNDO, `bridge.command("redo")`. Assert `rendered["w"]` returns to the post-gesture width within ±2px and `inlGrow=="0"`.

---

## R12 — Alt-held symmetric resize (`test_r12_alt_symmetric.py`, fixture `flow-grow.html`)

> Sequencing (AD7): R12 lands AFTER R10 is green. These tests assume R10's 1:1 write path.

### E-R12-1 — Alt-held: dragged edge tracks cursor 1:1, opposite edge mirrors, width grows 2Δ
- **Setup:** open `flow-grow.html`; `select_by_native_id("twin")` (plain block, start-pinned, NOT auto-centered).
- **Action:** record `before = rendered("twin")`. `page.keyboard.down("Alt")`. E-handle drag +60 (10 steps of `mouse.move(hx + i*6, hy)`, net cursor ΔX ≈ +60). `mouse.up()`. `page.keyboard.up("Alt")`. Record `after`.
- **Assertions (the dragged-edge-tracks-cursor property is the HEADLINE — F1):**
  - `assertAlmostEqual(after["right"] - before["right"], 60, delta=3)` — **HEADLINE: the dragged (right) edge tracks the cursor net travel 1:1** (NOT Δ/2). Under `fixedDirection:[0,0]` Moveable doubles `e.dist` (`Ra` `b=2`), so `beforeRect+dist` lands the dragged edge under the cursor.
  - `assertAlmostEqual(before["left"] - after["left"], 60, delta=3)` — left edge MIRRORS: moved LEFT by the same Δ (≈60), not Δ/2.
  - `assertAlmostEqual(after["w"] - before["w"], 120, delta=4)` — total width grew by **≈2Δ** (Δ per side). (delta=4: each edge carries its own rounding, so the width sum doubles the per-edge tolerance.)
- **Falsifies:** (a) Alt ignored → left edge unchanged → fails the mirror assertion; (b) a build that forces width=Δ (cursor-lagging the dragged edge to Δ/2) → fails the headline `right ≈ 60` and the `w ≈ 120` assertions. This locks the native 1:1-dragged-edge behavior D1 mandates and rejects the Δ-total / Δ/2-drift model.

### E-R12-2 — No-Alt one-sided unchanged
- **Setup:** open `flow-grow.html`; `select_by_native_id("twin")`.
- **Action:** SAME +60 E-handle drag WITHOUT Alt. Record before/after.
- **Assertions:** `assertLessEqual(abs(after["left"] - before["left"]), 2)` (left edge fixed) AND `assertAlmostEqual(after["right"] - before["right"], 60, delta=3)` (only right edge moved).

### E-R12-3 — Default restored after an Alt gesture (resizeEnd reset)
- **Setup:** open `flow-grow.html`; `select_by_native_id("twin")`.
- **Action:** do an Alt-held +40 gesture (release Alt + mouse.up). Then do a NON-Alt +40 gesture on the same element. Record before/after of the SECOND gesture.
- **Assertion:** `assertLessEqual(abs(after2["left"] - before2["left"]), 2)` — the second (non-Alt) gesture is one-sided, proving `onResizeEnd` reset `fixedDirection` to `false`.
- **Falsifies:** a build that sets `fixedDirection:[0,0]` but never resets → the second gesture is still symmetric → left edge moves → fails.

### E-R12-4 — Alt composes with R10: dragged edge 1:1, width grows 2Δ on the flex-grow accent
- **Setup:** open `flow-grow.html`; `select_by_native_id("node-accent")`.
- **Action:** Alt-held E-handle drag +60 (net cursor ΔX ≈ +60). Record before/after.
- **Assertions (F1 — doubled semantics under center anchor compose with the R10 dist-write):**
  - `assertAlmostEqual(after["right"] - before["right"], 60, delta=3)` — **HEADLINE: dragged (right) edge tracks the cursor 1:1** (the `beforeRect+dist` write with pre-doubled `dist` lands the edge under the cursor; NOT 30).
  - `assertAlmostEqual(before["left"] - after["left"], 60, delta=3)` — left edge mirrors by Δ.
  - `assertAlmostEqual(after["w"] - before["w"], 120, delta=4)` — width grew by **≈2Δ** (NOT 60); R10 dist-write needs no special math under Alt (S3-6).
  - `assertEqual(float(after["inlGrow"]), 0.0)` — grow still neutralized (R10 write intact under R12).
  - `assertAlmostEqual(parse_px(after["inlBasis"]), before["w"] + 120, delta=4)` — inline basis = startRendered + doubled dist (the basis grows 2Δ, the honest center-resize result).

---

## R11 — Resize guides + equal-size matching (`test_r11_resize_guides_equal_size.py`, fixture `flow-grow.html`)

> Sequencing (AD7): R11 lands AFTER R10 (its position-guide verification depends on R10 making edges move).

### E-R11-1 — Position guides FIRE on the flex-grow element post-R10 (a)
- **Setup:** open `flow-grow.html`; `select_by_native_id("node-accent")`.
- **Action:** E-handle drag in two phases (mirror `test_resize_shows_guidelines`): 5 steps `mouse.move(hx+i*6, hy)`, then probe, then 5 more steps; `mouse.up()`. Mid-drag probe: `found = H.doc_eval(page, "return doc.querySelectorAll('.moveable-line').length >= 1;")`.
- **Assertions:** `assertTrue(found, "position guides must appear during resize on the flex-grow element post-R10")` AND `assertNotAlmostEqual(after_w, before_w, delta=2)` (edge actually moved).
- **Falsifies:** R10 not actually moving the edge (the original "zero guides" symptom) → `found` False.

### E-R11-2 — Equal-size SNAP lands ON the matched dimension (b)
- **Setup:** open `flow-grow.html`. (The `twin` is `width:300px`.) `select_by_native_id("node-accent")`. Read `twinW = rendered("twin")["w"]` (≈300) and `accW0 = rendered("node-accent")["w"]`.
- **Action:** compute the cursor travel needed to bring the accent width to within 4px of 300 (drag toward `twinW`); E-handle drag that amount in 10 steps; `mouse.up()`. Record `accW1 = rendered("node-accent")["w"]`.
- **Assertion:** `assertAlmostEqual(accW1, twinW, delta=0.5)` — the accent width LANDED EXACTLY on the twin's width (snapped, not merely within 4px). Contrast control: `assertNotAlmostEqual(accW1, raw_cursor_target, delta=0.5)` where `raw_cursor_target` is the un-snapped value (must differ → snap fired).
- **Falsifies:** equal-size matching absent (accent lands at the raw cursor value, not exactly 300) → fails delta=0.5.

### E-R11-3 — Equal-size HINT renders during the snap, removed at end, positioned over the match (b, G5)
- **Setup/Action:** as E-R11-2, but probe mid-drag (while snapped): `hint = H.doc_eval(page, "return doc.querySelectorAll('[class*=\"hyp-size-hint\"]').length;")`, `pe = H.doc_eval(page, "const h=doc.querySelector('[class*=\"hyp-size-hint\"]'); return h?getComputedStyle(h).pointerEvents:null;")`, and the position-overlap probe `pos = H.doc_eval(page, "const h=doc.querySelector('[class*=\"hyp-size-hint\"]'); const t=doc.querySelector('#twin'); if(!h||!t) return null; const hr=h.getBoundingClientRect(), tr=t.getBoundingClientRect(); return {dx:Math.abs(hr.left-tr.left), dy:Math.abs(hr.top-tr.top)};")`. After `mouse.up()` + `wait 200ms`, probe again: `hint_after`.
- **Assertions:**
  - `assertGreaterEqual(hint, 1)` — hint overlay present during the snap.
  - `assertEqual(pe, "none")` — `pointer-events:none` (does not block handles).
  - `assertIsNotNone(pos)` AND `assertLessEqual(pos["dx"], 8)` AND `assertLessEqual(pos["dy"], 8)` — **the hint overlay sits OVER the matched `twin` element (G5: position uses the matched rect + scrollX/Y, not a stale document-origin offset)**. This catches the scroll-offset mispositioning the bare existence count would miss.
  - `assertEqual(hint_after, 0)` — teardown at `resizeEnd`.

### E-R11-4 — Equal-size hint is serializer-EXEMPT (b)
- **Setup:** open `flow-grow.html`; perform E-R11-2's equal-size gesture; then `H.set_fake_dialog(base, out)`; click `#save-as-btn`; `wait 600ms`.
- **Assertions:** read `out`; `assertNotIn("hyp-size-hint", text)` AND `assertEqual(re.findall(r'class="[^"]*hyp-size-hint', text), [])` — the `hyp-` namespace strip removed it (and teardown removed it from the live DOM pre-serialize).

### E-R11-5 — NO phantom snap to a solver-derived flex-grow sibling width (F5 guard)
- **Purpose:** `node-a`/`node-b` are same-parent flex-grow siblings of `node-accent`; their rendered widths are grow-share output, not author-set sizes. S3-7 excludes them from the equal-size candidate cache, so dragging the accent THROUGH a sibling's frozen start-width must NOT snap there (only the out-of-flow `twin` snaps).
- **Setup:** open `flow-grow.html`; record `siblW = rendered("node-a")["w"]` (the frozen grow-share width) and `accW0 = rendered("node-accent")["w"]`. `select_by_native_id("node-accent")`.
- **Action:** compute the cursor travel that brings the accent's width to within ≈1px of `siblW` (drag toward `siblW`, NOT toward the 300px `twin` — choose a target so the accent's width passes through `siblW` but stays >4px away from `twin`'s 300px). E-handle drag that amount in 12 slow steps (`wait 40ms` each); at the step whose cumulative travel lands the accent nearest `siblW`, probe `mid = rendered("node-accent")["w"]` and `hint = H.doc_eval(page, "return doc.querySelectorAll('[class*=\"hyp-size-hint\"]').length;")`. `mouse.up()`; record `accW1 = rendered("node-accent")["w"]`.
- **Assertions:**
  - `assertGreater(abs(accW1 - siblW), 1.0)` — the accent did NOT pin to the sibling's grow-share width (it landed at the raw cursor value, not snapped to `siblW`).
  - `assertEqual(hint, 0)` — no equal-size hint rendered while passing through the sibling width (the sibling is not a candidate).
- **Falsifies:** a build that includes same-parent flex-grow siblings in the candidate cache (the accent snaps to the stale `siblW` mid-gesture → `abs(accW1 - siblW) ≤ 1` or `hint ≥ 1` → fails).
- **Note:** E-R11-2 (snap to `twin`) and this E-R11-5 (no snap to sibling) together prove the exclusion is precise — `twin` (out-of-flow, explicitly width-set) snaps; same-parent grow siblings do not.

---

## R13 — Comment edit + delete (`test_r13_comment_edit_delete.py`, fixture `agent-comments.html`)

> Helpers: `_add_comment(text, agent=False)` and `_add_reply(text)` mirror `test_g2_save_with_comments.py` / `test_f5_comments.py`. `_read_island()` parses `#hyp-comments`. Panel rows read from `#comment-threads .comment-thread`.

### E-R13-1 — Edit root comment body
- **Setup:** open `agent-comments.html`; select `#p-lead`; `_add_comment("original")`. Read `id0` from the island.
- **Action:** in the panel row for `id0`, click **Edit** → composer opens prefilled; assert `page.input_value(".hyp-composer-textarea") == "original"`; fill `"edited body"`; `keyboard.press("Control+Enter")`; `wait 300ms`.
- **Assertions:**
  - island thread `id0`.`body == "edited body"`.
  - thread `id0` has a truthy `editedAt` (ISO parseable).
  - panel `.comment-body` for `id0` textContent == `"edited body"`.

### E-R13-2 — Edit undo restores exact prior body + editedAt absence
- **Setup/Action:** continue E-R13-1; `bridge.command("undo")`; `wait 150ms`.
- **Assertions:** island `id0`.`body == "original"` AND `id0` has NO `editedAt` key (it was absent pre-edit; undo removed it).

### E-R13-3 — Delete root comment
- **Setup:** open fixture; add two comments on `#p-lead` and `#p-arch` (ids `id0`,`id1`).
- **Action:** click **Delete** on `id0`'s panel row; `wait 300ms`.
- **Assertions:** island length == 1 and contains only `id1`; panel has exactly 1 `.comment-thread`; `H.doc_eval(page, "return doc.querySelectorAll('.hyp-comment-marker').length;")` decreased by 1.

### E-R13-4 — Delete-root undo restores thread + marker
- **Setup/Action:** continue E-R13-3; `undo`; `wait 150ms`.
- **Assertions:** island length == 2 (both ids present); marker count restored; panel shows 2 threads.

### E-R13-5 — Delete-reply undo restores at the ORIGINAL index (Risk-5)
- **Setup:** add a comment `id0`; add two replies `"r1"` then `"r2"` (so `replies = [r1, r2]`).
- **Action:** Delete the FIRST reply (`replyIndex 0`); `wait 300ms`; assert `replies == ["r2"]`. Then `undo`; `wait 150ms`.
- **Assertions:** `replies[0].body == "r1"` AND `replies[1].body == "r2"` — restored AT index 0, order preserved (NOT appended to the end).

### E-R13-6 — Edit reply body
- **Setup:** add comment `id0` + reply `"r1"`.
- **Action:** click reply's **Edit**; assert prefill `"r1"`; fill `"r1-edited"`; Ctrl+Enter.
- **Assertions:** `replies[0].body == "r1-edited"` AND `replies[0].editedAt` truthy; panel reply body updated.

### E-R13-7 — Edit composer stays in-viewport on a low anchor; no For-agents checkbox (Risk-12)
- **Setup:** open fixture; select `#li-2` (low in the document); `_add_comment("x")`; scroll the panel so the row is reachable.
- **Action:** click **Edit** on that row.
- **Assertions:**
  - composer `getBoundingClientRect().bottom <= window.innerHeight` (flip/clamp held — D12 unbroken).
  - `page.locator(".hyp-composer-agent").count() == 0` — For-agents checkbox HIDDEN in edit mode.

### E-R13-8 — Agent-block reflects an edited agent-tagged comment
- **Setup:** open fixture; select `#p-lead`; `_add_comment("do X", agent=True)` (id0). Save to `out1`; confirm `"instruction: do X"` present.
- **Action:** Edit `id0` body → `"do Y"`; save to `out2`.
- **Assertions:** `out2` contains `"instruction: do Y"` AND NOT `"instruction: do X"`. (Block regenerated from the store — S3-12.)

---

## R14 — Agent stamping + rewritten head block (`test_r14_agent_stamping.py`, fixture `agent-comments.html`)

### E-R14-1 — Single agent thread: stamp + selector resolves the right element
- **Setup:** open fixture; select `#p-lead`; `_add_comment("fix lead", agent=True)` (id0). Save to `out1`.
- **Assertions (read `out1` text + reopen):**
  - exactly one `data-hyp-agent=` occurrence; its value contains `id0`.
  - the stamped element is the one whose text is the lead paragraph (parse the saved HTML; the element carrying `data-hyp-agent` is the `<p>` with `id="p-lead"` text).
  - head block contains `target: [data-hyp-agent~="<id0>"]` (or `[data-hyp-agent="<id0>"]`).
  - **Reopen-resolve:** `H.open_via_dialog_ui(page, base, out1)`; `H.doc_eval(page, "const sel='[data-hyp-agent~=\"<id0>\"]'; const m=doc.querySelectorAll(sel); return {n:m.length, text:m[0]?m[0].textContent.slice(0,30):null};")` → `n == 1` and `text` matches the lead excerpt.

### E-R14-2 — Two agent threads on the SAME element → space-separated ids, both selectors resolve (S3-14)
- **Setup:** open fixture; select `#p-lead`; `_add_comment("a", agent=True)` (id0); select `#p-lead` again; `_add_comment("b", agent=True)` (id1). Save to `out`.
- **Assertions:** the lead element's `data-hyp-agent` value == `"<id0> <id1>"` (order = thread order); two block entries; reopening, `querySelectorAll('[data-hyp-agent~="<id0>"]')` and `querySelectorAll('[data-hyp-agent~="<id1>"]')` EACH return exactly the single shared element.

### E-R14-3 — Resolved/deleted threads don't stamp (S3-16)
- **Setup:** open fixture; add agent comment on `#p-lead` (id0) and on `#p-arch` (id1).
- **Action A (resolve):** `bridge.command("resolve-comment",{commentId:id0, resolved:true})`; save to `outR`.
- **Action B (delete):** reopen base fixture path? No — continue on the live doc: delete id1 (`delete-comment`); save to `outD`.
- **Assertions:** `outR` contains NO `data-hyp-agent` for id0 and no block entry for id0 (id1 still stamped). `outD` contains NO stamp/entry for id1.

### E-R14-4 — Live DOM stays clean after save (transient live-stamp reverted in `finally`, S3-13)
- **Setup:** open fixture; add agent comment on `#p-lead`; save to `out`.
- **Assertion:** immediately after save, `H.doc_eval(page, "return doc.querySelectorAll('[data-hyp-agent]').length;") == 0` — the LIVE document was never stamped.

### E-R14-5 — Block format completeness (S3-15)
- **Setup:** open fixture; select `#p-lead` (an `<p class="lead">`); `_add_comment("rename heading", agent=True)`; add a reply `"also bold it"`; save to `out`.
- **Assertions (read the head comment block `block_text`; each is an `assertIn(<substring>, block_text)`):**
  - `assertIn("target: [data-hyp-agent", block_text)` — the `target:` line opens with the attribute selector.
  - `assertIn('context: p .lead | "', block_text)` — the `context:` line carries tag (`p`) + non-`hyp` class (`.lead`) + the quoted excerpt that follows.
  - `assertIn("instruction: rename heading", block_text)`.
  - `assertIn("reply: also bold it", block_text)`.
  - `assertIn("author:", block_text)` AND `assertIn("date:", block_text)`.
  - `assertIn("remove the data-hyp-agent", block_text)` — the preamble's self-cleanup directive (the test pins the stable substring the spec mandates in S3-15; the implementer may add surrounding wording but MUST include this phrase).

### E-R14-6 — Stamping idempotence across multiple saves (S3-16)
- **Setup:** open fixture; add agent comment on `#p-lead` (id0); save to `out2`.
- **Action:** `H.open_via_dialog_ui(page, base, out2)` (reopen the saved file); `wait 500ms`; save to `out3`.
- **Assertions:** `out3` has exactly ONE `data-hyp-agent` occurrence (no accumulation), its value is exactly `id0` (the reopened file's prior stamp was stripped then re-derived — same id because the island id is stable), and exactly ONE block entry. `assertEqual(text3.count("data-hyp-agent"), 1)`.

### E-R14-7 — Node-count guard safe with stamps (Risk-3)
- **Setup:** open fixture; add 3 agent comments on 3 distinct elements; save to `out`.
- **Assertions:** save SUCCEEDS — `#shell-status` contains `"Saved"` (no serializer guard abort), `os.path.exists(out)` and size > 0, and the saved file has 3 `data-hyp-agent`-bearing elements. (Attributes are not nodes → guard unaffected.)

### E-R14-8 — Stamp a NON-FIRST element with selection + markers live (F3 desync guard)
- **Purpose:** the index-based `resolveCloneNode` would desync when `stripClone` removes body-appended `hyp-comment-marker`/`hyp-interaction-wrapper` nodes that precede a later body-child element; the transient-live-stamp path (S3-13) stamps by `matchAnchor` identity and is immune. E-R14-1/-2/-5 all tag `#p-lead` (near-first) and could pass by accident; this case tags a LATER element with the live chrome present.
- **Setup:** open `agent-comments.html`; agent-tag `#p-arch` (in the 2nd section, a later body-descendant) via `_add_comment("fix arch", agent=True)` (id0). Then agent-tag `#li-2` (`_add_comment`, id1) so a marker for id0 is already appended to `document.body`. **Leave an element SELECTED** at save time so the `hyp-interaction-wrapper` is live in the body: `select_by_native_id("li-2")` (re-select after adding, so the wrapper + the id0/id1 markers are all present as live body children). Confirm pre-save the live chrome exists: `H.doc_eval(page, "return doc.querySelectorAll('.hyp-comment-marker, #hyp-interaction-wrapper').length;") >= 2`.
- **Action:** `H.set_fake_dialog(base, out)`; click `#save-as-btn`; `wait 600ms`. Reopen: `H.open_via_dialog_ui(page, base, out)`; `wait 500ms`.
- **Assertions:**
  - In `out` text, the element carrying `data-hyp-agent="<id0>"` is the `#p-arch` paragraph (parse the saved HTML; assert the `data-hyp-agent` whose value contains id0 sits on the `<p id="p-arch">` whose text starts "Componentes desacoplados"), AND id1's stamp sits on `<li id="li-2">` (text "concilia") — neither stamp landed on a wrong sibling or was dropped.
  - **Reopen-resolve (the desync-killer assertion):** `H.doc_eval(page, "const m0=doc.querySelectorAll('[data-hyp-agent~=\"<id0>\"]'); const m1=doc.querySelectorAll('[data-hyp-agent~=\"<id1>\"]'); return {n0:m0.length, t0:m0[0]?m0[0].id:null, n1:m1.length, t1:m1[0]?m1[0].id:null};")` → `n0 == 1 and t0 == "p-arch"` AND `n1 == 1 and t1 == "li-2"`.
  - Live DOM clean after save: `H.doc_eval(page, "return doc.querySelectorAll('[data-hyp-agent]').length;") == 0`.
- **Falsifies:** an index-based clone-mapping build (stamp lands on the wrong element or is dropped because the live child-index includes the appended markers/wrapper that the clone lacks → `t0 != "p-arch"` or `n0 == 0`).

---

## R14 fresh-agent legibility verification (`test_r14_legibility.py` — DESIGN)

**Purpose:** prove the D4/S4 payoff — a saved file's head block alone lets an agent with ZERO project context locate every agent-tagged target. This is a STRUCTURAL test of the saved artifact, NOT an LLM call (deterministic, CI-safe).

**Premise:** "an agent with no project context" is modeled as a fresh browser context that loads the saved file as a PLAIN document (no editor, no runtime, no island knowledge) and is given ONLY the head block text. The "agent" must resolve every target using the block's `target:` selectors alone.

### G-R14-LEGIBILITY-1 — Every target resolvable via the head block alone
- **Setup:** open `agent-comments.html`; add **2+** agent-tagged comments on DISTINCT elements (`#p-lead` "fix lead", `#li-2` "renumber item"); save to `out`.
- **Extract phase (the only input the "fresh agent" gets):** parse `out` with a regex/stdlib HTML scan to pull the head comment block text; from it, extract every `[agent:<id>]` entry's `target:` selector and `instruction:` line. The test MUST NOT read the island, `data-hyp-*` mapping, or any structural path — ONLY the block's `target:` strings.
- **Resolve phase (fresh, context-free):** launch a NEW Playwright page; `page.goto` the saved file served as a plain document (via the `/doc/` route or `file://`); for EACH extracted `target:` selector, run `page.evaluate("(sel)=>{const m=document.querySelectorAll(sel); return m.length===1 ? m[0].outerHTML.slice(0,120) : {n:m.length};}", selector)`.
- **Pass criteria (ALL must hold):**
  1. **Count match:** the number of `[agent:` entries (count occurrences of the literal `[agent:` marker) == the number of agent-tagged comments added (2).
  2. **Unique resolution:** EVERY `target:` selector resolves to EXACTLY ONE element (`m.length === 1`) — no zero, no ambiguity.
  3. **Correct target:** each resolved element's text/native-id matches the comment's intended anchor (the `#p-lead` selector resolves the lead paragraph; the `#li-2` selector resolves the "concilia" list item). Verified by asserting the resolved `outerHTML` contains the expected native id or text excerpt.
  4. **Position-independence proof:** BEFORE resolving, mutate the fresh document's DOM to simulate "the agent's own first edit shifted the DOM" — e.g. `document.querySelector('#sec-ops').insertAdjacentHTML('afterbegin','<p>injected</p>')` (shifts nth-child indices). Re-run all `target:` selectors; assert they STILL each resolve to exactly one correct element. This is the core D4 win: an attribute selector survives DOM shifts that would break the old `buildPath` nth-of-type path.
- **Falsifies:** a build that kept the structural-path anchor (criterion 4 fails — the path goes stale after the injected node) OR a build whose stamping missed an element (criterion 2 fails with `m.length === 0`).

### G-R14-LEGIBILITY-2 — Self-cleanup directive is present and actionable
- **Assertion:** the extracted block preamble contains the self-cleanup directive (the S3-15 substring); a follow-up evaluate confirms that removing a given id's `data-hyp-agent` token (`element.setAttribute('data-hyp-agent', value.replace(id,'').trim())` or attribute removal when it was the only id) leaves the OTHER targets still resolvable — proving the cleanup instruction is per-id and non-destructive to siblings.

---

## Regression set (binding — `tests/e2e/` + `tests/unit/` stay green)

| ID | Guard | Assertion |
|----|-------|-----------|
| **REG-1 — existing suite green gate** | The full 116-test suite (`python -m pytest tests/` or the project's runner) re-runs after EACH of R10/R12/R11/R13/R14 (per-fix commit, AD7). | Zero new failures. Specifically named watches below. |
| **REG-2 — healthy width path 1:1** | `test_r2_resize_real.py` (resizes `.research-card`, the grid/width healthy path) | Stays green; R10 must not perturb the `else`/`absolute` branch. (Tecter fixture — runs only where `H.FIXTURE` is restored locally; the SYNTHETIC `grid-healthy.html` E-R10-3/4/5 are the AD8-compliant equivalents and run in CI.) |
| **REG-3 — position-snap resize guides** | `test_f2_select_guides.py::test_resize_shows_guidelines` | Stays green; R11 must not regress position guides on the width path. |
| **REG-4 — comment store/island** | `test_f5_comments.py` | Stays green; R13's added `editedAt` field is additive (existing assertions check key presence, not absence). |
| **REG-5 — save with comments + agent block** | `test_g2_save_with_comments.py` | Stays green; R14 keeps the sentinel `===== HYPRESENT AGENT INSTRUCTIONS =====` unchanged and only rewrites the per-entry anchor line; the no-comments chrome-free assertion (E-G2-5) still holds (no `data-hyp-` in a no-comment save). |
| **REG-6 — undo restores all flex longhands** | NEW **G-R10-UNDO** (above) | The dedicated guard for Risk-2; part of the regression set because it locks the capture contract. |
| **REG-7 — serializer node-count guard with stamped attributes** | NEW **E-R14-7** + a unit-style assertion: after a save with K agent stamps, the serializer did NOT emit an `error` event with scope `serializer` (node-count guard passed). | `assertEqual(serializer_error_count, 0)` (listen on console/bridge `error`). Attributes ≠ nodes → guard unaffected. |
| **REG-8 — no editor console errors** | Re-use the `test_r2_resize_real.py::test_no_console_errors` pattern on `flow-grow.html` and `agent-comments.html` after R10–R14 gestures. | Zero editor-origin console errors (asset 404s excluded). Matches the exit condition (D6: clean error-free run). |

**Red-first proof gate (binding pre-implementation step, F6 process gap):** BEFORE writing the R10 fix, run the NEW red tests against CURRENT master and RECORD the observed failure numbers in a run log (`docs/improvements-2026-06-r3/red-first-log.md`). Required red-first demonstrations (not assumptions): **E-R10-1** (slack amplification: master writes basis 1141→1324, right-edge moves ≈+33 ≠ +60 → fails `delta=2`), **E-R10-2** (dead zone on `flow-grow-deadzone.html`: master leaves rendered width PINNED, Δ ≈ 0 for a −120 cursor sweep → fails `delta=2` by ≈120px), **E-R10-2b** (first-gesture dead zone on `flow-grow-deadzone.html`: Δ ≈ 0 for −100 → fails `delta=3` by ≈100px). If any of these does NOT fail on master, STOP — the fixture does not reproduce the bug and the test is not a valid red-first proof; fix the fixture before proceeding. The R12 (E-R12-1/-4) doubled-width assertions are red against the pre-R12 build (no Alt anchor → one-sided, left edge unchanged → mirror assertion fails); record those too.

**Exit gate (owner-defined, user-feedback.md §Exit condition):** all of R10–R14 implemented + tested + committed individually on `master`; the full suite green (REG-1); and a clean, error-free local server run on the synthetic fixtures (REG-8). No push (D6).

---

## Coverage matrix (every spec contract → its test)

| Spec contract | Test(s) |
|---------------|---------|
| R10-1 slack 1:1 (amplification killed) | E-R10-1 |
| R10-2 no-slack 1:1 (dead zone killed, red-first on `flow-grow-deadzone.html`) | E-R10-2, E-R10-2b |
| R10-3 corner height floor | E-R10-6 |
| R10-4 healthy paths unchanged (incl. committed `grid-healthy.html`) | E-R10-3, E-R10-4, E-R10-5, REG-2 |
| R10-5 undo all 3 longhands | G-R10-UNDO, G-R10-REDO, REG-6 |
| R10 overfull-row bounded deviation | covered by E-R10-2 mechanism + documented edge case (no separate red-bar test; bound is layout-forced) |
| R12-1 Alt: dragged edge 1:1 + mirror, width 2Δ (F1) | E-R12-1 |
| R12-2 no-Alt one-sided | E-R12-2 |
| R12-3 start-only + reset (incl. error-path, G10) | E-R12-3 |
| R12-4 composes with R10 (doubled dist, F1) | E-R12-4 |
| R11-1 position guides post-R10 | E-R11-1 |
| R11-2 equal-size snap (to out-of-flow `twin`) | E-R11-2 |
| R11-3 equal-size hint lifecycle + position (G5) | E-R11-3 |
| R11-4 serializer-exempt hint | E-R11-4 |
| R11 exclude solver-derived flex-grow siblings (F5) | E-R11-5 |
| R13-1..7 edit/delete + undo + composer | E-R13-1..E-R13-7 |
| R13-6 agent-block sync on edit | E-R13-8 |
| R14-1 stamp + resolve | E-R14-1 |
| R14 multi-thread same element | E-R14-2 |
| R14 resolved/deleted don't stamp | E-R14-3 |
| R14 live DOM clean | E-R14-4 |
| R14 block format | E-R14-5 |
| R14 idempotence | E-R14-6 |
| R14 node-count guard | E-R14-7, REG-7 |
| R14 stamp non-first element, markers/wrapper live (F3 desync guard) | E-R14-8 |
| R14 fresh-agent legibility | G-R14-LEGIBILITY-1, -2 |
