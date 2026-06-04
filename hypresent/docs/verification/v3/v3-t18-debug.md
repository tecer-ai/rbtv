# V3-T18 — Debug Report + FIX SPEC v6 (Boundary C9 EXIT gate)

**Method**: `superpowers:systematic-debugging` (root-cause-first) + `rbtv-playwright-cli` live instrumentation. Runtime-only instrumentation; **zero product/test file modifications** (this report is the only write). Scratch in `$env:TEMP`; servers/browsers killed.

**Branch**: `hypresent-v2`. **App**: `hypresent/`. Paths below relative to `hypresent/`.

---

## Reproduction baseline (this machine, headless Chromium 1280×720, Playwright 1.60.0)

| Run | Runner | Result |
|-----|--------|--------|
| Isolated `test_exit_smoke` | pytest | A FAILS (line 166) |
| Isolated `test_f2 …empty_click_deselect` | pytest | B FAILS (line 364) — does **not** skip here (empty point IS found) |
| Isolated `test_f5_comments` (13 tests) | pytest | **all pass** — C does NOT reproduce in isolation |
| Full `unittest discover` (116 tests), run ×3 | unittest | A+B fail every run; **C fails 1–2 composer-agent tests, varying which** (run1: F5 `test_save_as_includes_agent_block_first_in_head`; run2: G2 `test_e_g2_4_roundtrip_no_agent_block_duplication`; run3: F5 `test_reply_appears_in_agent_block`) |

**Key**: C is a cross-suite, load/timing-dependent flake whose *mechanism* is constant; the specific failing test varies because the first composer-agent `.check()` that lands on a low anchor is the one that times out.

**Incidental (NOT a blocker, surface only)**: run1 also showed a one-off `test_r2_resize_real::test_control_box_aligns_with_target` failure (Moveable handle hit-test under load). It did NOT recur in runs 2–3 and passes 8/8 in isolation. Pre-existing flake, unrelated to the three blockers or to any fix below.

---

## BLOCKER A — smoke delete no-op  ·  VERDICT: **TEST-SIDE** (target mismatch; NOT the edit-gate, NOT product)

### Evidence chain (live, verbatim)

The edit-gate is **innocent**. Full activeElement timeline across the exact smoke sequence (`$TEMP/hyp_blockerA.py`):

```
after_type        : activeTag=DIV  CE=true  anyCE=true  id=hyp-13   (editing)
after_a_escape    : activeTag=BODY CE=null  anyCE=false             (commit fired → edit-state{editing:false})
after_r8_dblclick : activeTag=DIV  CE=true  anyCE=true  id=hyp-13   (editing)
after_first_fontinc: activeTag=DIV CE=true  anyCE=true  id=hyp-13   (focus() did NOT blur the CE element)
after_3_fontinc   : activeTag=DIV  CE=true  anyCE=true  id=hyp-13
after_r8_escape   : activeTag=BODY CE=null  anyCE=false             (commit fired → edit-state{editing:false})
after_resize/move/color/comment/agent_tag : all BODY, anyCE=false
BEFORE_DELETE     : activeTag=BODY CE=null  anyCE=false
runtime_delete_guard_would_block : "not-blocked"
AFTER_DELETE_status              : "Element deleted."   ← success path ran (main.js:491)
AFTER_DELETE_element_present     : true                 ← captured del_id STILL in DOM
```

So the gate did NOT block (`editingAtPress=false`, runtime activeElement guard `not-blocked`), delete reported success, yet the asserted element survives.

Pass-2 (`$TEMP/hyp_blockerA2.py`) — MutationObserver + selection introspection at the delete moment:

```
captured_del_id (.research-card)   : hyp-132
elementFromPoint_at_click          : hitCls=research-card-body  nearestRegId=hyp-136  (a NESTED registered child)
ring_wraps                         : [{hypId: hyp-136, cls: research-card-body}]   ← get-selection returns hyp-136
removed_nodes                      : [hyp-selection-ring, {DIV research-card-body, hyp-136}, hyp-comment-marker, …moveable artifacts]
captured_del_id_still_present      : true
status                             : "Element deleted."
```

Structure confirmed (live): `.research-card` (`hyp-132`) **has registered children** (`research-card-header` `hyp-133`, `research-card-body` `hyp-136`); `.kicker` (`hyp-12`) has **none**.

### Root cause
The smoke captures `del_id` from a **static `.research-card` query** (line 161) but then **clicks the card's center** (line 162). `selection.js` walks up from `event.target` to the *nearest* registered element — which is the nested `.research-card-body` (`hyp-136`), not the card. `get-selection` returns `hyp-136`; `delete-element` correctly removes `hyp-136`; the card's `data-hyp-id` (`hyp-132`) persists → `assertFalse(...hyp-132 present)` fails. The R3 isolated suite passes because it deletes a childless element (`.kicker`-class), so click-selection == captured id.

### Live validation of the fix (`del_id` from the actually-selected element)
```
selected id (ring-wrapped): hyp-136
AFTER DELETE, selected-id present: False   (expect False)  ✓
AFTER UNDO,  selected-id present: True    (expect True)   ✓
```
Round-trip assertion fully preserved; only the `del_id` *source* corrected. No outcome weakened.

---

## BLOCKER B — empty-click deselect fails on a "real" empty point  ·  VERDICT: **TEST-SIDE** (probe defect; product clear() is correct)

### Evidence chain (live, verbatim — `$TEMP/hyp_blockerB.py`)

The probe's "empty point" is `(100,370)`, but `elementFromPoint` there returns a Moveable resize line:

```
empty_point hit                 : "moveable-line moveable-direction moveable-edge moveable-s moveable-resizable"
elementFromPoint_with_wrapper   : pointerEvents="auto"  closestHypId=null  closestHypArtifact="hyp-interaction-wrapper"
click_log (capture-phase trace) : target=moveable-line  isHypDirect=false  nearestHypCls="hyp-interaction-wrapper"
                                  earlyReturnWouldFire=true  walkReachesRegistered=null  clearShouldRun=false
wrapper_after_empty_click       : 1   ← NOT cleared
ring_after_empty_click          : true
```

**Broken link (quoted current code, `runtime/js/selection.js:204-205`)**:
```js
const nearestHyp = node.closest('[class^="hyp-"], [class*=" hyp-"]');
if (nearestHyp) return;          // ← Moveable line's ancestor is #hyp-interaction-wrapper → early return; clear() never reached
```
The Moveable south-edge line is hittable because of the R2 fix (`interaction.js:162-164`, `pointer-events: auto` on `.moveable-line.moveable-direction`). The probe's emptiness test (`!el.closest('[data-hyp-id]')`, `test_f2_select_guides.py:337`) treats "no registered ancestor" as empty — but a Moveable control line has no registered ancestor while NOT being an empty region. The product **correctly** declines to deselect when a control surface is clicked.

### Candidate mechanisms — verified, not assumed
- ❌ drag-start guard — N/A (real click, no drag).
- ✅ **"empty point lands on a hyp- artifact"** — CONFIRMED (Moveable south-edge line, `pointer-events:auto`).
- ❌ stale-state observer — `clear()` was never called (early-return), so observer comparison is irrelevant.
- ❌ `removeWrapper` regressed — N/A; product clear() path proven working (below).
- ❌ document-sized wrapper intercepts despite `pointer-events:none` — the wrapper itself is `none`; it is its **child Moveable line** (`pointer-events:auto`) that intercepts.

### Flakiness (5 isolated runs of the exact probe)
```
run1: empty=(100,370) hit=moveable-line  wrapAfter=1 ring=True   → FAIL
run2: empty=(None,None)                  → SKIP
run3: empty=(100,370) hit=moveable-line  wrapAfter=1 ring=True   → FAIL
run4: empty=(None,None)                  → SKIP
run5: empty=(100,370) hit=moveable-line  wrapAfter=1 ring=True   → FAIL
```
The Moveable south-edge line's rendered extent at the selected `.slide-title` sometimes covers the gap point (100,370), sometimes not — pure render/timing nondeterminism.

### Product clear() path proven correct (`$TEMP/hyp_blockerB3.py`)
```
synthetic body-targeted click → wrapper_after: 1 → 0,  ring_after: false   → "WORKS (body click clears)"
```
With the corrected emptiness predicate (exclude hyp- artifacts), this fixture yields **no empty point** (all 191 candidates are over a registered element or a hyp- control) → the test reaches its existing `skipTest` (D25-permitted, matching the BUG report's accepted skip). Verified live: `fixed_probe_empty_point = {x:null}` (`$TEMP/hyp_blockerB2.py`).

---

## BLOCKER C — composer agent checkbox never stable (4 tests, was v2-green)  ·  VERDICT: **PRODUCT-SIDE** (no viewport bottom-clamp)

### Evidence chain (live, verbatim)

The checkbox is **NOT moving, NOT zero-size, NOT hidden, NOT covered-by-an-element — it is BELOW THE VIEWPORT FOLD** and therefore un-actionable. Coverage probe at the real cross-suite failure (`$TEMP/hypsc/sitecustomize.py`, full `unittest discover`):

```
selector : .hyp-composer-agent input
probe    : rect={x:105, y:784, w:13, h:13}   centerInViewport=FALSE   cy=791  innerH=720
           composerRect={x:96, y:703, w:240, h:135}   (bottom=838, overflows 720 by 118px)
           vis=visible  disp=block  op=1  disabled=false
           elementFromPoint_is_checkbox=false  stack=[]   (point is off-screen)
           htmlTransform=none  bodyTransform=none  docScrollY=0
Playwright call log (verbatim):
  - element is visible, enabled and stable
  - scrolling into view if needed
  - done scrolling
  - element is outside of the viewport      ← THE HANGING GATE
  - retrying click action … 58× … Timeout 30000ms exceeded.
```

Controlled experiment (forced `position:fixed; top:5000px` composer) reproduced the IDENTICAL Playwright signature for **both** `Locator.check` (F5) and `Page.check` (G2):
```
- element is visible, enabled and stable
- scrolling into view if needed / done scrolling
- element is outside of the viewport
- retrying click action …
```
→ A `position:fixed` element below the fold is "visible & stable" but its action point can't be scrolled into view → infinite retry → timeout.

### Root cause (quoted current code, `app/js/shell/comment-composer.js:34-38`)
```js
const left = (fb.left + (rect ? rect.left : 20));
const top  = (fb.top + (rect ? rect.top + (rect.height || 0) : 20));   // below-anchor; no bottom bound
pop.style.position = "fixed";
pop.style.left = Math.max(8, left) + "px";
pop.style.top  = Math.max(8, top) + "px";                              // only a TOP/min clamp; NO bottom/viewport clamp
```
The composer (≈135px tall) is positioned just below the anchor with **only a `Math.max(8, …)` minimum clamp**. When the anchor element sits low in the viewport (which happens nondeterministically across the full suite as `frame.locator('.slide-title').first.click()` settles the iframe scroll/layout differently), `top + height` exceeds the viewport bottom and the agent checkbox (last child) lands off-screen → un-clickable. Isolation hides it because the anchor lands high (197px fold margin measured: composer top=435, checkbox center=523, fold=720).

### Suspect bisection (per task) — culprit named with evidence
- R2 document-sized wrapper / Moveable `updateRect` loops → **iframe-side**; the parent composer is `position:fixed` z=1000000, unaffected. Probe shows no movement, no transform. **Not the cause.**
- R7 `alignCaps` in every `selection-changed` payload → toggles toolbar button `disabled` only; does not move a fixed parent popover. **Not the cause.**
- R3 `edit-state` events → no parent layout effect on the popover. **Not the cause.**
- **Culprit: the composer's own positioning math (no bottom clamp) + a low anchor.** Direct, deterministic, validated.

### Live validation of the fix (flip-above-anchor using the real anchor rect)
Repro with a deliberately low anchor, then the proposed clamp applied at runtime:
```
REPRO  : composer top=644  checkbox cy=732 (>720)  inVp=false → .check() TIMED OUT   (BUG reproduced)
FIXED  : composer top=465  checkbox cy=553         inVp=true  → .check() SUCCEEDED
```
The fix flips the composer above the anchor when below-anchor would overflow the bottom, then clamps to the viewport. Checkbox returns on-screen and clickable. No test assertion touched.

---

## FIX SPEC v6 — executor-ready (apply all three; each anchor is verbatim current code)

### (a) PRODUCT files

#### FIX C-1 — `app/js/shell/comment-composer.js` : clamp composer within viewport (flip above anchor on bottom overflow)

**Anchor — REPLACE these exact lines (34-38):**
```js
  const left = (fb.left + (rect ? rect.left : 20));
  const top = (fb.top + (rect ? rect.top + (rect.height || 0) : 20));
  pop.style.position = "fixed";
  pop.style.left = Math.max(8, left) + "px";
  pop.style.top = Math.max(8, top) + "px";
```
**WITH:**
```js
  const left = (fb.left + (rect ? rect.left : 20));
  // anchorTop = on-screen top of the anchored element; belowTop = composer's default
  // position just under the anchor. We may flip to ABOVE the anchor if the composer
  // would overflow the viewport bottom (it is position:fixed and cannot scroll into view).
  const anchorTop = (fb.top + (rect ? rect.top : 20));
  const belowTop = (fb.top + (rect ? rect.top + (rect.height || 0) : 20));
  pop.style.position = "fixed";
  pop.style.left = Math.max(8, left) + "px";
  pop.style.top = Math.max(8, belowTop) + "px";   // provisional; clamped after append (height known)
  // Stash for the post-append viewport clamp.
  pop.dataset.hypAnchorTop = String(anchorTop);
  pop.dataset.hypBelowTop = String(belowTop);
```

**Anchor — REPLACE this exact line (95):**
```js
  document.body.appendChild(pop);
```
**WITH:**
```js
  document.body.appendChild(pop);
  // Viewport clamp (V3-T18 BLOCKER C): a position:fixed composer below the fold is
  // "visible & stable" but un-actionable (cannot scroll into view) — its agent checkbox
  // then never receives the click. Measure the real height now and keep the whole
  // composer inside the viewport: flip above the anchor on bottom overflow, else clamp.
  {
    const M = 8, GAP = 6;
    const h = pop.offsetHeight || 0;
    const vh = window.innerHeight;
    const anchorTop = parseFloat(pop.dataset.hypAnchorTop) || 0;
    let top = parseFloat(pop.style.top) || 0;
    if (top + h > vh - M) {
      const flipped = anchorTop - h - GAP;            // place composer fully above the anchor
      top = (flipped >= M) ? flipped : Math.max(M, vh - h - M);
      pop.style.top = top + "px";
    }
  }
  delete pop.dataset.hypAnchorTop;
  delete pop.dataset.hypBelowTop;
```

> Notes for executor: surgical change, confined to `openComposer`. Default (high-anchor) behavior is unchanged — the clamp only fires on bottom overflow. Validated live: BUG repro → fix → `.check()` succeeds. Restores F5/G2 composer-agent tests without touching any test.

### (b) TEST files (sequencing/setup corrections only — NO outcome assertion weakened)

#### FIX A-1 — `tests/e2e/test_exit_smoke.py` : derive `del_id` from the actually-selected element

**Anchor — current lines (161-166):**
```python
        del_id = H.doc_eval(self.page, f"return doc.querySelector('{del_sel}').getAttribute('data-hyp-id');")
        self.page.mouse.click(origin_d["x"]+rect_d["x"]+min(rect_d["w"]/2,40), origin_d["y"]+rect_d["y"]+rect_d["h"]/2)
        self.page.wait_for_timeout(200)
        self.page.click("#delete-btn")
        self.page.wait_for_timeout(250)
        self.assertFalse(H.doc_eval(self.page, f"return !!doc.querySelector('[data-hyp-id=\"{del_id}\"]');"), "R3: element deleted")
```
**REPLACE WITH** (remove the pre-click static `del_id`; capture the id the runtime actually selected after the click — `.research-card` has registered children, so the click selects a nested child, and delete acts on that child):
```python
        self.page.mouse.click(origin_d["x"]+rect_d["x"]+min(rect_d["w"]/2,40), origin_d["y"]+rect_d["y"]+rect_d["h"]/2)
        self.page.wait_for_timeout(200)
        # Capture the element the runtime ACTUALLY selected (the click resolves to the nearest
        # registered element under the pointer, which may be a registered CHILD of del_sel).
        # Delete + undo must round-trip on THAT element, not the static container query.
        del_id = H.doc_eval(
            self.page,
            "const r=doc.querySelector('.hyp-selection-ring');"
            "if(!r) return null;"
            "const rr=r.getBoundingClientRect();"
            "const c=Array.from(doc.querySelectorAll('[data-hyp-id]')).filter(el=>{"
            " const x=el.getBoundingClientRect();"
            " return Math.abs(x.left-rr.left)<2 && Math.abs(x.top-rr.top)<2"
            "  && Math.abs(x.width-rr.width)<2 && Math.abs(x.height-rr.height)<2;});"
            "return c[0] ? c[0].getAttribute('data-hyp-id') : null;",
        )
        self.assertIsNotNone(del_id, "R3: an element must be selected before delete")
        self.page.click("#delete-btn")
        self.page.wait_for_timeout(250)
        self.assertFalse(H.doc_eval(self.page, f"return !!doc.querySelector('[data-hyp-id=\"{del_id}\"]');"), "R3: element deleted")
```
> The existing line-169 undo assertion (`assertTrue(...del_id present)`) is unchanged and now round-trips on the correct id. `del_sel`, `origin_d`, `rect_d` (lines 156-160) are unchanged; the `del_id` line moves from before the click to after it and reads the live selection. Validated live: delete→False, undo→True.

#### FIX B-1 — `tests/e2e/test_f2_select_guides.py` : empty-point probe must exclude hyp- artifacts

**Anchor — current line (337):**
```python
            "  if(el===null || el===doc.documentElement || el===doc.body || !el.closest('[data-hyp-id]')){"
```
**REPLACE WITH:**
```python
            "  if(el===null || el===doc.documentElement || el===doc.body || (!el.closest('[data-hyp-id]') && !el.closest('[class^=\"hyp-\"], [class*=\" hyp-\"]'))){"
```
> A point landing on a hyp- artifact (the document-sized `#hyp-interaction-wrapper` or a `pointer-events:auto` Moveable control line introduced by R2) is NOT an empty-region click — the product correctly keeps the selection. With this exclusion the fixture yields no empty point → the test reaches its existing `skipTest` at line 347 (D25-permitted, identical to the BUG report's accepted skip). The `assertEqual(wrapper_count2, 0, …)` and `assertFalse(ring_present2, …)` at lines 364-365 are **unchanged** — they still fire on any genuinely empty point. Validated live: fixed probe returns `{x:null}` on this fixture; product clear() proven correct via synthetic body click. Edit is confined to this one test method.

---

## Cross-suite threat assessment
- **FIX C-1** changes only the low-anchor branch of `openComposer`; high-anchor positioning (every passing F5/G2 path today) is byte-identical. No other consumer of the composer exists. Removes the C flake for F5 *and* G2.
- **FIX A-1** edits only `test_full_smoke_zero_console_errors`. No shared helper touched.
- **FIX B-1** edits only the empty-point probe inside `test_escape_and_empty_click_deselect`. Other F2 tests untouched.
- **Surface (not fixed)**: `test_r2_resize_real::test_control_box_aligns_with_target` showed a one-off failure under full-suite load (run1 only; passes 8/8 isolated, did not recur). Pre-existing Moveable hit-test flake; orthogonal to these fixes. Recommend a separate stability pass if it recurs.
