# V3-T2 Debug — R2 resize/move/reorder still dead: live root-cause settlement + fix spec

## Date
2026-06-04

## Agent / environment
Debug agent (Session 2, boundary C1). Branch `hypresent-v2` (verified; no git writes). Repro: `python server/server.py 127.0.0.1 8791` with `HYP_TEST_DIALOG=1`; Python Playwright 1.60.0, headless Chromium, default viewport 1280×720 (identical to the e2e harness); sample deck `tecer-gsmm-introduction.html` opened through the `/api/_test/set-dialog` seam + `#open-btn` (`conftest_helpers.open_via_dialog_ui`, the exact path the failing suites use). All real input via `page.mouse.*`. Scratch scripts ran from `%TEMP%`; server + browsers killed before finishing. ZERO product/test file edits — this report is the sole write.

---

## VERDICT: **BOTH** — primary PRODUCT-BUG (un-fixed by V3-T1) + secondary TEST-BUG (empty-point discovery is structurally unsatisfiable on this fixture)

**One-sentence root cause:** The Moveable control box is positioned ~`scrollY` pixels below the element it decorates because `#hyp-interaction-wrapper` is `position: fixed` while Moveable writes the target's **document-absolute** coordinates into the control-box transform — so at any non-trivial scroll the handles render far off-screen, `elementFromPoint` returns `null`, and every resize/move/reorder drag hits empty space; V3-T1 fixed pointer-events (a real but **secondary** defect) and never touched this coordinate-frame defect, so interaction stayed 100% dead.

**Kimi's hypothesis (v3-t2-BUG.md §Root-cause): REFUTED.** The wrapper, control box, and all 12 direction handles live **inside the iframe document**, not the parent. Measured `ownerDocument` identity and full ancestry confirm it; the parent document contains zero Moveable nodes.

**V3-T1 style: applied and effective at its stated job, but insufficient.** `#hyp-interaction-style` exists in the iframe `<head>`, its rule matches the controls, and computed `pointer-events` is now `auto` on the control box, the directions, and the SE handle. Pointer-events is no longer the blocker. It was a necessary precondition that fixed the wrong (secondary) layer.

---

## Evidence chain (verbatim measurements)

### A — Which document holds `#hyp-interaction-wrapper` + `.moveable-control-box`? → IFRAME (Kimi refuted)

```json
A_wrapper_controlbox_document = {
  "iframe_has_wrapper": true, "iframe_has_control_box": true,
  "iframe_direction_count": 12, "iframe_has_ring": true,
  "parent_has_wrapper": false, "parent_has_control_box": false, "parent_direction_count": 0
}
A_controlbox_ancestry_in_iframe = [
  "div.moveable-control-box.rCS1w3zcxh",
  "div#hyp-interaction-wrapper.hyp-interaction-wrapper",
  "body", "html", "#document"
]
A_ownerDocument_identity = { "controlbox_ownerDoc_is_iframeDoc": true, "wrapper_ownerDoc_is_iframeDoc": true }
```

The control-box ancestry `.moveable-control-box < #hyp-interaction-wrapper < body < html < #document` is measured **inside the iframe**, exactly matching diagnosis.md §R2 and flatly contradicting v3-t2-BUG.md's claim that the wrapper "sits outside the iframe (in the parent document)." Parent document = 0 Moveable nodes.

### B — `#hyp-interaction-style` present in that head? rule in styleSheets? matches the controls? → YES to all

```json
B_style_element = {
  "iframe_has_style_el": true, "parent_has_style_el": false, "style_in_head": true,
  "style_textContent": "#hyp-interaction-wrapper .moveable-control-box,#hyp-interaction-wrapper .moveable-control,#hyp-interaction-wrapper .moveable-line,#hyp-interaction-wrapper .moveable-area,#hyp-interaction-wrapper .moveable-direction { pointer-events: auto; }"
}
B_stylesheet_rule_and_matches = {
  "matched_selector": "#hyp-interaction-wrapper .moveable-control-box, … .moveable-direction { pointer-events: auto; }",
  "matches_controlbox": true, "matches_direction": true,
  "sheets": [ …, {"owner":"hyp-interaction-style","ruleCount":1,"href":null}, … ]
}
```

The injected stylesheet is live in `document.styleSheets` (owner node `hyp-interaction-style`, 1 rule) and `el.matches()` against the live control-box and direction handles both return `true`.

### C — computed `pointer-events` at wrapper / control-box / direction / SE handle → wrapper `none` (intentional), everything else `auto`

```json
C_computed_pointer_events = {
  "wrapper":      {"computed_pointerEvents":"none","inline_style_pe":"none", "attr_style":"position: fixed; top: 0px; left: 0px; width: 100%; height: 100%; pointer-events: none; z-index: 999998;"},
  "control_box":  {"computed_pointerEvents":"auto","inline_style_pe":"", "attr_style":"position: absolute; display: block; visibility: visible; transform: translate3d(102px, 3104px, 0px); --zoom: 1; --zoompx: 1px;"},
  "one_direction":{"computed_pointerEvents":"auto","inline_style_pe":""},
  "se_handle":    {"computed_pointerEvents":"auto","inline_style_pe":"", "attr_style":"transform: translateZ(0px) translate(154px, 169px) rotate(0rad) scale(1);"}
}
```

Stylesheet walk for `pointer-events` rules matching the SE handle:

```json
C_pointerEvents_rules_matching_walk = [
  {"selector":".dark-bg-overlay","pointerEvents":"none","matchesSEhandle":false,"owner":"STYLE"},
  {"selector":"#hyp-interaction-wrapper .moveable-control-box, … .moveable-direction","pointerEvents":"auto","matchesSEhandle":true,"owner":"hyp-interaction-style"},
  {"selector":".rCS1w3zcxh .moveable-control.moveable-origin","pointerEvents":"none","matchesSEhandle":false},
  {"selector":".rCS1w3zcxh .moveable-area.moveable-avoid, … .moveable-pass","pointerEvents":"none","matchesSEhandle":false},
  {"selector":".rCS1w3zcxh .moveable-guideline","pointerEvents":"none","matchesSEhandle":false},
  {"selector":".rCS1w3zcxh[data-able-origindraggable] .moveable-control.moveable-origin","pointerEvents":"auto","matchesSEhandle":false}
]
```

**The ONLY `pointer-events` rule that matches the SE handle is V3-T1's `auto` rule.** No inline `pointer-events`, no competing stylesheet rule sets the handle to `none`. The handle's computed value is `auto`. **Pointer-events is fully fixed and is NOT why interaction is dead.** Note the diagnosis.md:99 claim that the handle has its own base `pointer-events: none` rule is not borne out — the vendored Moveable's `none` rules are scoped to `.moveable-origin`, `.moveable-area.moveable-avoid/pass`, and `.moveable-guideline`, none of which match a direction handle.

But note `control_box.attr_style` already shows the smoking gun: `transform: translate3d(102px, 3104px, 0px)` — a 3104px Y offset, while the card it decorates is at viewport-y ≈ 194 (see D).

### D — handle in-viewport assertion + `elementFromPoint` (iframe AND parent) → handle is 2900px OFF-SCREEN; both return `null`

```json
research_card_iframe_rect_after_scroll = { "x":80, "y":193.9, "w":198, "h":250 }   // card IS in viewport after scrollIntoView
D_handle_local_center_and_viewport = { "x":249, "y":3266, "w":14, "h":14, "cx":256, "cy":3273, "vw":1006, "vh":638, "in_viewport": false }
D_elementFromPoint_IFRAME_at_handle  = null      // iframe doc, at (256, 3273)
D_elementFromPoint_PARENT_at_mapped_handle = { "parent_coords":{"x":272,"y":3337.5}, "hit": null }
```

The card sits at iframe-local y≈194 (correctly scrolled into the 638px-tall viewport), but its **SE handle is at y=3266** — 2628px **below the bottom of the viewport**. `elementFromPoint` (iframe) returns `null` because nothing is painted at that off-screen point. The parent-document `elementFromPoint` at the iframe-origin-mapped coordinate also returns `null`. This is NOT a pointer-events miss and NOT a cross-document issue — **the handle is rendered ~scrollY pixels below where the card actually is.**

### D′ — proof the off-screen offset == scroll distance (control box mis-placed by the full scroll)

```json
scroll_and_card_abs = { "scrollY":2851, "card_rect_top":193.9, "card_offsetTop_abs":3045 }
controlbox_vs_card_alignment = {
  "control_box_getClientRect": {"x":102,"y":3104,"w":1,"h":1},
  "control_box_transform": "translate3d(102px, 3104px, 0px)",
  "card_getClientRect": {"x":80,"y":193.9,"w":198,"h":250},
  "se_handle_getClientRect": {"x":249,"y":3266,"w":14,"h":14},
  "wrapper_position": "fixed",
  "wrapper_rect": {"x":0,"y":0,"w":1006,"h":638}
}
controlbox_minus_card_viewport_top_DELTA = { "delta_px": 2910.09 }
```

The control box's `getBoundingClientRect().top = 3104`; the card's = 193.9. **Delta = 2910px ≈ scrollY (2851) + the residual offset.** The control-box transform `translate3d(102px, 3104px)` equals the card's **document-absolute** position (offsetTop ≈ 3045 + box origin), but it is applied inside a `position: fixed` wrapper whose coordinate origin is the **viewport** (wrapper rect at y=0, height 638 = viewport). So the document-absolute transform projects the control box `scrollY` pixels too low. This is the mechanism.

### E — real handle drag + real body drag (current/broken state) → both dead, zero console output

```json
E_before_resize_geometry = { "w":198, "h":250, "inline_w":"", "inline_h":"", "translate":"" }
E_resize_drag = {
  "handle_screen": {"x":272,"y":3337.5},               // off-screen target
  "mid_drag_classes_at_step6": {"resizing":0,"dragging":0,"lines":8},
  "after_geometry": {"w":198,"h":250,"inline_w":"","inline_h":"","flexBasis":""},
  "width_changed": false, "height_changed": false
}
E_resize_console = []
E_body_drag_move = {
  "slide_title_screen_center": {"x":519,"y":383.7},
  "before_translate": "", "after_translate": "",
  "mid_drag_classes_step4": {"dragging":1,"lines":8},
  "translate_changed": false
}
E_body_drag_console = []
```

Resize at the (off-screen) handle: geometry unchanged 198×250 → 198×250, no `.moveable-resizing`, silent. Body drag at the card's **correct on-screen center**: Moveable's `.moveable-area` does receive the pointer-down (`dragging:1` appears mid-drag, confirming pointer-events:auto works), but `style.translate` stays empty — because the control box / `.moveable-area` geometry is offset by the same 2910px, so Moveable's internal drag delta math is corrupted and onDrag never commits a usable translate. Both dead, both silent (no exception) — exactly matching diagnosis.md §R2 ("throws nothing") and v3-t2-BUG.md.

### E′ / FIX VERIFICATION — live patch wrapper `fixed`→`absolute` (DOM-only, no file edit): control box re-aligns, real resize WORKS

```json
// candidate-fix applied live: wrapper.style.position='absolute'; top/left=0; width/height = scroll document size
TEST2_before_patch_alignment = { "cb_top":3104, "card_top":193.9 }
TEST2_after_patch_alignment  = { "cb_top":253, "card_top":193.9, "cb_transform":"translate3d(102px, 3104px, 0px)", "se_top":415, "se_in_vp":true }

FIX_handle_after_patch = { "top":415, "left":249, "w":14, "h":14, "in_vp": true }
FIX_elementFromPoint_at_handle = { "coords":{"x":256,"y":422}, "hit":{"tag":"DIV","cls":"moveable-control moveable-direction moveable-se moveable-resizable"} }
FIX_REAL_resize_result = {
  "handle_screen": {"x":272,"y":486.5},
  "before": {"w":198,"h":250}, "after": {"w":258,"h":289},
  "mid": {"resizing":0,"dragging":1},
  "width_changed": true, "height_changed": true, "console": []
}
```

With **only** the wrapper's `position` changed from `fixed` to `absolute` (and sized to the scroll document), the **same** `translate3d(102px, 3104px)` transform now lands the control box at viewport-top **253** — essentially on the card (top 194; the ~59px residual is Moveable's normal control-origin offset). The SE handle moves on-screen (top 415, `in_vp:true`), `elementFromPoint` returns the **`moveable-se` handle** (was `null`), and a real handle drag resizes the card **198×250 → 258×289** (width AND height changed) with zero console errors. **This is the fix, proven end-to-end against real input.**

Corroborating control at `scrollY≈0` (where fixed ≈ document coords): a top element at `element_top:0` still showed `control_box_top:285` under the fixed wrapper (delta tracks the element's document-absolute offsetTop), consistent with the model.

### F — empty-point discovery for `test_escape_and_empty_click_deselect` → STRUCTURALLY UNSATISFIABLE on this fixture (TEST-BUG, fixture limitation confirmed)

```json
F_empty_point_discovery = { "found": null, "probed": 196, "vw":1006, "vh":638,
  "samples": [ {"x":975,"y":319,"hit":"SECTION.slide.slide--soft","empty":false}, … all 196 land on a slide … ] }
F_body_and_slide_geometry = { "body_rect":{"x":0,"y":-425,"w":1006,"h":7144.9}, "body_margin":"0px", "viewport":{"w":1006,"h":638}, "slideCount":10 }
F_corner_probes = { "tl":{hit:"SECTION.slide…",hasHypAncestor:true}, "tr":…true, "bl":…true, "br":…true, "r_mid":…true, "b_mid":…true }   // every corner+margin hits a slide
EMPTY_interslide_gaps_doc_coords = { "interSlideGapsDocCoords": [], "totalGaps": 0 }    // slides tile edge-to-edge, NO gaps
bottom_probe (scrolled to document bottom) = firstEmpty: null                          // last slide bottom == body bottom (7144.9); no trailing empty
right_margin_probe = { "slideRight":1006, "vw":1006, "hasRightMargin":false }           // slides are full viewport width
registration = { "slideCount":10, "slidesWithHypId":10, "bodyHypId":null, "totalRegistered":366 }
after_body_click = { "before":{wrapper:1,ring:true}, "after_body_click":{wrapper:1,ring:true} }   // clicking body hits a slide → re-selects, never clears
after_escape_key = { "wrapper":1, "ring":true }                                                    // Escape is NOT wired to deselect in the runtime
```

The deck's 10 `section.slide` elements are **all registered** (`data-hyp-id`), are **full-viewport-width**, **tile edge-to-edge with zero gaps**, and **fill the entire 7145px body** (last-slide bottom == body bottom; body has 0 margin/padding). Widening the Playwright window does not help — the iframe element stays 1006px wide and slides scale to 100%. Therefore **no point inside the iframe viewport resolves to an empty (no-`[data-hyp-id]`-ancestor) target** — the test's empty-point discovery (`test_f2_select_guides.py:266-287`) cannot succeed, exactly as v3-t2-BUG.md notes ("fixture fills viewport — test limitation, not the blocking bug"). Independently confirmed: clicking the iframe `body` re-selects (hits a slide) and never clears, and **Escape does not deselect** in the runtime (so the test's `if escape_works` guard correctly stays false). This is a real, separate test defect, but it is NOT the resize/move/reorder blocker.

---

## Falsified hypothesis (named)

**Kimi's "parent-document control box" hypothesis (v3-t2-BUG.md §Root-cause hypothesis): REFUTED by A + A′ + D.** The control box and all handles are in the **iframe** document (ownerDocument identity = iframe doc; ancestry under iframe `body`; parent document has 0 Moveable nodes). The handles being un-hittable is NOT because they are in a different document — it is because they are rendered ~`scrollY` px **off-screen within the iframe** due to the `position: fixed` wrapper. V3-T1's pointer-events approach "missed it" because the diagnosis it was built on (diagnosis.md §R2) correctly identified pointer-events:none but **stopped there** and never measured the control-box `getBoundingClientRect` vs the target's — so the dominant coordinate-frame defect was invisible to it.

---

## FIX SPEC (complete; executable by a non-reasoning executor)

### (a) PRODUCT FIX — required. One file, one logical change.

**File:** `runtime/js/interaction.js`

**Root cause to fix:** `#hyp-interaction-wrapper` is `position: fixed`, but Moveable writes the target's document-absolute coordinates into the control-box transform; inside a fixed (viewport-anchored) container those coordinates render the controls `scrollY` px off-screen. Fix = give the wrapper a **document-flow coordinate origin** (`position: absolute`, anchored at the document top-left, sized to the scroll document) so Moveable's absolute transform lands correctly. The wrapper stays `pointer-events: none` (empty-region click-through preserved) and `zIndex: 999998`.

**Current anchor — `createWrapper()`, interaction.js lines 174-182 (verbatim):**

```js
function createWrapper() {
  ensureInteractionStyle();
  const w = document.createElement("div");
  w.className = "hyp-interaction-wrapper";
  w.id = "hyp-interaction-wrapper";
  Object.assign(w.style, { position: "fixed", top: "0", left: "0", width: "100%", height: "100%", pointerEvents: "none", zIndex: "999998" });
  document.body.appendChild(w);
  return w;
}
```

**Replace the `Object.assign(...)` line (line 179) with:**

```js
  Object.assign(w.style, {
    position: "absolute",
    top: "0",
    left: "0",
    width: Math.max(document.documentElement.scrollWidth, document.documentElement.clientWidth) + "px",
    height: Math.max(document.documentElement.scrollHeight, document.documentElement.clientHeight) + "px",
    pointerEvents: "none",
    zIndex: "999998",
  });
```

Live-verified outcome of exactly this change (DOM-equivalent applied at runtime): control-box top 3104→253 (aligns to card at 194), SE handle on-screen (`in_vp:true`), `elementFromPoint(handle)` returns the `.moveable-se` handle, real handle drag resizes 198×250→258×289, zero console errors.

**Required companion — keep the wrapper sized to the document as it changes.** The document height is not static (resize commits, reflow, content edits change `scrollHeight`). Add a resize of the wrapper to the existing `remount()` so the overlay tracks document growth. **Current anchor — `remount()`, interaction.js lines 356-364 (verbatim):**

```js
export function remount(hypId) {
  // re-point the existing Moveable to the (possibly reflowed) element
  if (!moveable) { mount(hypId); return; }
  const el = byId(hypId); if (!el) { unmount(); return; }
  activeHypId = hypId;
  moveable.target = el;
  moveable.elementGuidelines = getElementGuidelines(el);
  moveable.updateRect();
}
```

**Insert immediately after `activeHypId = hypId;` (i.e. before `moveable.target = el;`):**

```js
  if (wrapper) {
    wrapper.style.width = Math.max(document.documentElement.scrollWidth, document.documentElement.clientWidth) + "px";
    wrapper.style.height = Math.max(document.documentElement.scrollHeight, document.documentElement.clientHeight) + "px";
  }
```

**Why this is the minimal correct fix (not the alternatives):**
- Moveable's own coordinate math keys off the container/offsetParent position (vendored source: control-box style is computed as `position: y?"fixed":"absolute"` and the offset walk tests `"fixed"===x` on ancestors). Making the wrapper `absolute` with a document-origin makes Moveable's absolute branch land on the document, which is where the target's absolute coordinates live.
- The vendored Moveable exposes a `rootContainer` prop, but passing it is a larger change to `buildMoveable()` and its interaction with `snapContainer: wrapper` is unverified this session — the `position` change is smaller, fully verified, and leaves the snap container identity untouched.
- V3-T1's `ensureInteractionStyle()` injection (lines 158-169) is **still required** — keep it. With the wrapper now on-screen, the handles need `pointer-events: auto` to be hittable; C proves that rule is the only thing granting it. Do not remove V3-T1; this fix is **additive** to it.

**Do NOT change:** the wrapper's `pointer-events: none` (preserves empty-region click-through), `zIndex`, the `ensureInteractionStyle()` call, or `buildMoveable`'s `snapContainer: wrapper`.

### (b) TEST FIXES

#### b1 — REQUIRED for every drag/resize/reorder test in BOTH suites: target the handle/element by its LIVE `getBoundingClientRect`, and SCROLL THE HANDLE (not just the element) into the viewport before driving the pointer.

After the product fix, the handle renders at the card's on-screen position. But the card is 250px tall and its SE handle is at the card's bottom-right; `scrollIntoView({block:'center'})` centers the card, which keeps the SE handle on-screen for a 250px card in a 638px viewport — verified (handle top 415 < 638). For taller targets the existing `_scroll_into_view` (which only asserts the *element* is partially visible) is insufficient. The tests already compute the handle from its live rect (`test_r2_resize_real.py:_handle_center` / `:_iframe_handle_local_center`, and `test_f2_select_guides.py:169-181`), so once the product fix lands these coordinate computations become correct automatically. **No coordinate-math change is needed in the tests for resize/move/reorder — they were computing handle coordinates correctly all along; the handle was simply off-screen due to the product bug.**

Add a hardening guard so a future off-screen handle FAILS LOUDLY instead of silently dragging empty space. In `test_r2_resize_real.py`, `_handle_center` (lines 84-93) and `_iframe_handle_local_center` (lines 95-103): after fetching `h`, assert the handle is within the iframe viewport.

**Current anchor — `_iframe_handle_local_center`, test_r2_resize_real.py lines 95-103 (verbatim):**

```python
    def _iframe_handle_local_center(self):
        """Handle center in IFRAME-local coordinates (for elementFromPoint inside the iframe doc)."""
        h = H.doc_eval(
            self.page,
            "const el=doc.querySelector('.moveable-control-box .moveable-se') || doc.querySelector('.moveable-control-box .moveable-e');"
            "if(!el) return null; const r=el.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};",
        )
        self.assertIsNotNone(h, "resize handle not rendered")
        return h["x"], h["y"]
```

**Replace its `doc_eval` body + assertion with (adds an in-viewport assertion that catches the exact R2 defect):**

```python
    def _iframe_handle_local_center(self):
        """Handle center in IFRAME-local coordinates (for elementFromPoint inside the iframe doc)."""
        h = H.doc_eval(
            self.page,
            "const el=doc.querySelector('.moveable-control-box .moveable-se') || doc.querySelector('.moveable-control-box .moveable-e');"
            "if(!el) return null; const r=el.getBoundingClientRect();"
            "return {x:r.left+r.width/2, y:r.top+r.height/2,"
            " in_vp:(r.left+r.width/2>=0 && r.left+r.width/2<=win.innerWidth && r.top+r.height/2>=0 && r.top+r.height/2<=win.innerHeight)};",
        )
        self.assertIsNotNone(h, "resize handle not rendered")
        self.assertTrue(h["in_vp"], f"resize handle center is outside the iframe viewport ({h['x']},{h['y']}) — control box mis-placed (R2 product bug)")
        return h["x"], h["y"]
```

(Apply the same `in_vp` assertion pattern to `_handle_center`, lines 84-93, before returning the screen coordinates.)

#### b2 — REQUIRED: `test_escape_and_empty_click_deselect` empty-point discovery — make the no-empty-point case an explicit, honest skip of the click sub-assertion (not a hard failure), since this fixture has no empty region.

**Live-verified fact:** the fixture's slides tile the entire document edge-to-edge (no gaps, no margins, full-width, body height == sum of slides), all 10 slides are registered, and neither a body click nor Escape deselects. There is NO real-input empty-click target on this deck. The current code (test_f2_select_guides.py:284-287) does `assertIsNotNone(empty_local, ...)` which **fails the whole test** when no empty point exists — this is the only failing assertion in this test that is a genuine fixture/test mismatch, not the R2 bug.

**Current anchor — test_f2_select_guides.py lines 284-302 (verbatim):**

```python
        self.assertIsNotNone(
            empty_local,
            "no empty (no [data-hyp-id] ancestor) point found in the iframe viewport — cannot test empty-click deselect (RV05)",
        )
        fb = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        self.page.mouse.click(fb["x"] + empty_local["x"], fb["y"] + empty_local["y"])
        self.page.wait_for_timeout(200)

        wrapper_count2 = H.doc_eval(
            self.page, "return doc.querySelectorAll('#hyp-interaction-wrapper').length;"
        )
        ring_present2 = H.doc_eval(
            self.page, "return !!doc.querySelector('.hyp-selection-ring');"
        )

        self.assertEqual(wrapper_count2, 0, "click-empty-space should remove wrapper")
        self.assertFalse(ring_present2, "click-empty-space should remove selection ring")
```

**Replace with (skip the click sub-assertion only when the fixture genuinely has no empty region — verified live that it does not):**

```python
        if empty_local is None:
            # This fixture's slides tile the document edge-to-edge with no gaps/margins
            # and every slide is registered, so no real-input empty-click target exists.
            # Verified live (v3-t2-debug.md §F). The empty-click deselect path is not
            # exercisable on this deck; skip ONLY this sub-assertion, not the whole suite.
            self.skipTest("fixture has no empty (no-[data-hyp-id]) point — empty-click deselect not exercisable on this deck (see v3-t2-debug.md §F)")
        fb = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        self.page.mouse.click(fb["x"] + empty_local["x"], fb["y"] + empty_local["y"])
        self.page.wait_for_timeout(200)

        wrapper_count2 = H.doc_eval(
            self.page, "return doc.querySelectorAll('#hyp-interaction-wrapper').length;"
        )
        ring_present2 = H.doc_eval(
            self.page, "return !!doc.querySelector('.hyp-selection-ring');"
        )

        self.assertEqual(wrapper_count2, 0, "click-empty-space should remove wrapper")
        self.assertFalse(ring_present2, "click-empty-space should remove selection ring")
```

**Rationale for skip (not a relaxed assertion):** the empty-click deselect behavior is real and worth testing, but it is **unobservable on this fixture** — the honest signal is "not exercisable here," not a green pass nor a false fail. This matches v3-t2-BUG.md's own classification ("test limitation, not the blocking bug"). The proper long-term fix is a deck fixture with a non-full-bleed slide or body margin; that is a fixture change, out of scope for these two suites. If a non-skip outcome is mandated, the only real-input alternative on this exact deck is to drive deselect through the supported runtime path via `page.evaluate` on the bridge (`clear-selection`) — but that is not an "empty click" and would mis-name the test.

#### b3 — NOT NEEDED: cross-realm `getComputedStyle` / `doc_eval` coordinate frames are correct.

`conftest_helpers.doc_eval` runs the body via the parent window's `Function`, resolving `doc=f.contentDocument`, `win=f.contentWindow`, and calling `win.getComputedStyle(...)` (the tests pass `getComputedStyle` unqualified inside the body, which resolves to the **parent** window's `getComputedStyle`, but it is invoked on an iframe element and returns that element's correct computed style cross-realm — verified: width/height/pointer-events all read correctly). `_iframe_origin` + `_screen_center` correctly add the iframe element's page rect to the iframe-local rect. These are sound; no change.

---

## Recurrence guard (post-fix)

The existing `test_handle_is_hittable` (test_r2_resize_real.py:106-115) already locks the regression: it asserts `elementFromPoint(handleCenter)` returns a `.moveable-` element. With the product fix it passes (D-fix evidence). The added `in_vp` assertion (b1) makes any future re-introduction of an off-screen control box fail loudly at the coordinate layer rather than silently dragging empty space.
