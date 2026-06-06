# V3-T15 — R7 Alignment: Live-Instrumented Debug + FIX SPEC v5

**Date:** 2026-06-04
**Agent:** DEBUG AGENT #5 (Hypresent Session 2, boundary C7)
**Method:** systematic-debugging (root cause before fix); live runtime instrumentation only, ZERO product-file modifications. Server :8791, headless Chromium (Playwright sync API), real mouse input, fake-dialog seam, fixture `tecer-gsmm-introduction.html`.

---

## TL;DR — verdict overturns the briefing premise

**The R7 product code is CORRECT as shipped. The reported failures are a TEST-SIDE defect: the test's target selectors (`.research-card`, `.kicker`) are NON-UNIQUE, so the element the test *restyles+asserts-on* (`querySelector` → FIRST match) is NOT the element the test *selects* (a real mouse click that lands on a DIFFERENT matching element). Align operates correctly on the SELECTED element; the assertions read the un-restyled FIRST element → false negatives across E-R7-1..9.**

- There is **no universal no-op**. There is **no signature mismatch** (`runtime-main` passes a correct closure into `align(hypId, applyFn)`).
- `computeAlignCaps` does **NOT** misclassify `table-cell` or fixed-height blocks — caps return `vertical:true` for both when computed on the actual element.
- E-R7-10 `win` collision **is** real and test-side.

All 9 normative behaviors were live-validated GREEN against the unmodified runtime once the selected element == the restyled element. Evidence below.

---

## Phase 1 — Full-chain static map (read before instrumenting)

Production align chain, end to end:

| Stage | File:line | What it does | Verdict |
|-------|-----------|--------------|---------|
| Button click | `app/js/main.js:462-467` | `btn.addEventListener("click", () => bridge.command("align", { axis, value }))` | correct |
| Bridge → iframe | `runtime/js/bridge-iframe.js:66-72` | postMessage `{kind:'command', type:'align', payload}` → `handleCommand` → dispatchTable | correct |
| `align` registration | `runtime/js/runtime-main.js:127-138` | resolves selection via `current()`, `byId`, builds command, `historyPush` | correct |
| Command factory | `runtime/js/commands.js:341-372` | captures capture-all inline `before`; `do(){ applyFn() }` | correct |
| History | `runtime/js/history.js:39-53` | `push(cmd)` runs `cmd.do()` | correct |
| Apply | `runtime/js/text-format.js:299-318` | `applyAlign(el,axis,value)` writes `el.style[m.prop]=m[value]` | correct |
| Caps bridge | `runtime/js/selection.js:95-104` | `buildInfo` includes `alignCaps: computeAlignCaps(el)` | correct |
| Shell disable | `app/js/main.js:274-279, 470-490` | `selection-changed` → `__hypUpdateAlignButtons(caps)` | correct |

### Quoted: the callback-injection signature (the briefing's suspect #1 — DISPROVEN)

`commands.js:341` — `align(hypId, applyFn)` takes a **callback**, and `do()` invokes it:
```js
export function align(hypId, applyFn) {
  const el = getElement(hypId);
  const PROPS = ["text-align","justify-content","align-items","justify-items",
    "align-content","justify-self","align-self","vertical-align","display","flex-direction"];
  const before = {};
  for (const p of PROPS) before[p] = el.style.getPropertyValue(p);
  return {
    do() { applyFn(); },                                  // <-- invokes the closure
    undo() { /* restore every captured inline prop */ },
    label: "align",
  };
}
```

`runtime-main.js:135` passes a **proper arrow-function closure** (NOT `(hypId, axis, value)`):
```js
const cmd = makeAlignCommand(info.hypId, () => applyAlign(el, payload.axis, payload.value));
historyPush(cmd);
```
→ `applyFn` is a function, `do()` calls it, `applyAlign` runs. **No signature mismatch. The briefing's candidate (1) is false on the actual code.**

### Quoted: the vertical-capability predicate (`text-format.js:254-296`)

```js
export function computeAlignCaps(el) {
  if (!el) return { horizontal:false, vertical:false, hMap:null, vMap:null };
  const cs = getComputedStyle(el);
  const d = cs.display;
  const fd = cs.flexDirection || "row";
  const isFlex = d === "flex" || d === "inline-flex";
  const isGrid = d === "grid" || d === "inline-grid";
  const isCell = d === "table-cell";
  ...
  let vertical = false; let vMap = null;
  if (isFlex)      { vertical = true; vMap = fd.startsWith("row") ? {prop:"alignItems",...} : {prop:"justifyContent",...}; }
  else if (isGrid) { vertical = true; vMap = {prop:"alignItems", top:"start", middle:"center", bottom:"end"}; }
  else if (isCell) { vertical = true; vMap = {prop:"verticalAlign", top:"top", middle:"middle", bottom:"bottom"}; }
  else if (hasFixedHeight(el)) { vertical = true; vMap = {prop:"__flexColumn", top:"flex-start", middle:"center", bottom:"flex-end"}; }
  return { horizontal:true, vertical, hMap, vMap };
}
```
`isCell` (`d === "table-cell"`) and `hasFixedHeight(el)` both set `vertical = true`. The predicate is **correct**. (`hasFixedHeight` at `text-format.js:246-251` reads inline `el.style.height` first, then computed `cs.minHeight`; for `height:200px` inline it returns `true`.) The briefing's claim that the predicate misclassifies these is false — proven live in §C.

---

## Phase 1 — Live instrumentation (Section A): full-chain trace for ONE click

Setup mirrored the test exactly: open via fake dialog, `e.style.cssText += 'display:block;'` on `querySelector('.research-card')`, real mouse click at the element's rect center to select.

**A1 — `get-selection` after the real click reports a DIFFERENT element than the one restyled:**
```json
{ "hypId": "hyp-136", "role": "block", "isText": true,
  "alignCaps": { "horizontal": true, "vertical": false, "hMap": {"prop":"textAlign",...}, "vMap": null } }
```
**A3 — the element the test restyled+asserts-on:** `hypId: "hyp-132"`, inline `display: block;`.
→ **MISMATCH: restyled `hyp-132`, selected `hyp-136`.**

**A5 — bridge trace for the real `#align-center` click (the command DID fire and succeed):**
```json
[ {"dir":"out","kind":"command","type":"align","payload":{"axis":"h","value":"center"}},
  {"dir":"in","kind":"event","type":"history-changed","payload":{"cursor":0,"canUndo":true,"canRedo":false}},
  {"dir":"in","kind":"response","id":"...","ok":true,"result":{"ok":true}} ]
```
The handler fired, the command ran, history advanced (`cursor:0`), response `{ok:true}`. **No exception, no swallowed rejection** (A8 page-errors `[]`).

**A6 — `hyp-132` (the asserted element) is unchanged** (`text-align: start`) because `text-align:center` was written to `hyp-136` (the selected element) — which is exactly correct per the selection-scoped spec (V3-S19: "resolves the current selection's hypId itself"). The test simply asserts on the wrong node.

**A7/A8** — no console errors except `404 (assets/)` (already filtered by the suite); no page errors.

---

## Phase 1 — Live instrumentation (Section C): caps probed directly per display

`get-selection.alignCaps` read on the SELECTED element (selection driven by exact hypId — no rect ambiguity):

| Restyle (on the selected element) | `caps.vertical` | `vMap.prop` | computed `display` | Verdict |
|-----------------------------------|-----------------|-------------|--------------------|---------|
| `display:table-cell;` | **true** | `verticalAlign` | `table-cell` | correct (enabled) |
| `display:block;height:200px;` | **true** | `__flexColumn` | `block` (h=200px inline) | correct (enabled) |
| `display:block;height:auto;min-height:0;` | **false** | `null` | `block` | correct (disabled) |
| `display:flex;flex-direction:row;` | **true** | `alignItems` | `flex` | correct (enabled) |

**`table-cell` → `vertical:true`. fixed-height block → `vertical:true`. Neither is misclassified.** (In an earlier probe the SAME caps read `vertical:false` for "table-cell" — but only because the class selector had selected a *different, un-restyled* block; once the read is on the restyled element, caps are correct. This is the same root cause, re-confirmed.)

---

## Phase 1 — Confirmation (Section B): query-id ≠ select-id in the REAL test flow

Replicating the test's exact `_restyle` + `_select` (real mouse click), capturing `querySelector` id vs `get-selection` id:

| Test restyle | queried id (`querySelector` FIRST, gets the style) | selected id (real click) | MISMATCH |
|--------------|-----------------------------------------------------|--------------------------|----------|
| `display:block;` | `hyp-132` | `hyp-136` | **yes** |
| `display:flex;flex-direction:row;` | `hyp-132` | `hyp-133` | **yes** |
| `display:table-cell;` | `hyp-132` | `hyp-136` | **yes** |
| `display:block;height:200px;` | `hyp-132` | `hyp-136` | **yes** |

`.research-card` matches **7** elements in the open deck (43 occurrences in the source file); `.kicker` matches **10**. `querySelector` returns the first; the real click at that first element's rect-center coordinate lands on/selects a neighbor. Selected elements' inline style is empty (`""`) — they were never restyled. This single fact explains **every** assertion failure (E-R7-1..6) and **every** timeout (E-R7-7/E-R7-9: the selected neighbor is a plain block → vertical correctly disabled → the test's vertical click times out).

---

## Phase 3/4 — Live-validated 9-scenario matrix (real shell, UNIQUE target)

Artifact-free run: a single top-level region tagged with a unique `id`, restyled and real-mouse-selected so **query-id == select-id**, driven through the **complete production chain** (real `selection-changed` event → `__hypUpdateAlignButtons` → real button click → bridge `align` → runtime handler → `makeAlignCommand` → `historyPush` → `applyAlign` → `el.style`). **No product files modified.**

| # | Scenario | Action | Observed (computed) | Expected | Pass |
|---|----------|--------|---------------------|----------|------|
| 1 | block H-center | `#align-center` | `text-align: center` | center | ✅ |
| 1u | block undo | Undo | `text-align: start` *(probe2)* | start | ✅ |
| 2 | flex-row V-middle | caps `vertical:true`, btn enabled, `#align-middle` | `align-items: center` | center | ✅ |
| 3 | flex-col H-right | `#align-right` | `align-items: flex-end` | flex-end | ✅ |
| 4 | grid H-center | `#align-center` | `justify-items: center` | center | ✅ |
| 5 | table-cell V-bottom | caps `vertical:true`, btn **enabled**, `#align-bottom` | `vertical-align: bottom` | bottom | ✅ |
| 6 | plain auto-height block | vertical | caps `vertical:false`; top/middle/bottom **disabled**, center enabled | V disabled, H enabled | ✅ |
| 7 | fixed-height block V-middle | caps `vertical:true` (`__flexColumn`), btn enabled, `#align-middle` | `display:flex` + `flex-direction:column` + `justify-content:center` | flex + center | ✅ |
| 7u | fixed-height undo | Undo | `display: block` (restored) | block | ✅ |

Raw evidence (probe D-final):
```json
"1_block":     {"sel_ok":true,"caps_v":true,"text_align":"center"},
"2_flexrow":   {"sel_ok":true,"caps_v":true,"vbtn_disabled":false,"align_items":"center"},
"3_flexcol":   {"sel_ok":true,"align_items":"flex-end"},
"4_grid":      {"sel_ok":true,"justify_items":"center"},
"5_tablecell": {"sel_ok":true,"caps_v":true,"vbtn_disabled":false,"display":"table-cell","vertical_align":"bottom"},
"6_plainblock":{"sel_ok":true,"caps_v":false,"top_dis":true,"mid_dis":true,"bot_dis":true,"center_dis":false},
"7_fixed":     {"sel_ok":true,"caps_v":true,"vMap_prop":"__flexColumn","vbtn_disabled":false,
                "display":"flex","justify_content":"center","flex_direction":"column",
                "undo_display":"block","undo_expect":"block"}
```
`CONSOLE ERRORS (non-404): []` — `PAGE ERRORS: []`. The capture-all undo restores `display` on the flex-converted block (scenario 7u), exactly per V3-S15.

> Note on scenario 1u: probe D-final's clear-selection mouse click at `(2,2)` perturbed the post-undo read; the **authoritative** block-undo result is from probe B/D (select-by-id, isolated): `S1 block — AFTER: text-align:center` → `S1 block — AFTER UNDO: text-align:start`. Block H-center undo is confirmed GREEN.

---

## Section E — E-R7-10 `win` collision (test-side, confirmed)

`conftest_helpers.py:91-99` `doc_eval` wraps the body as:
```python
fn = new Function('doc','win', body)   # 'win' is a FUNCTION PARAMETER
```
The colliding test body (`test_r7_alignment.py:148`) declares a `const win`:
```python
caps_flex = H.doc_eval(self.page, f"const e=doc.querySelector({self.TARGET!r}); const win=document.querySelector('iframe.doc-frame').contentWindow; return null;")
```
`const win = ...` redeclares the `win` parameter → **`SyntaxError: Identifier 'win' has already been declared`**. The line is also dead (immediately followed by `return null;`). Fix = delete the line (preferred) or rename the local. No assertion is touched.

---

# FIX SPEC v5 — executor-ready

**Scope correction vs. the briefing:** because the root cause is test-side, FIX SPEC v5 contains **ZERO product edits** to `text-format.js`, `commands.js`, `runtime-main.js`, `selection.js`, or `main.js`. Editing any of those would be a symptom-chase against working code (and would regress the passing E-R7-8). All edits are in the ONE test file. The product files listed in the briefing as "files actually needing change" need none — proven by the GREEN matrix above against the unmodified runtime.

## EDIT 1 — Make the alignment target UNIQUELY addressable (fixes E-R7-1..9)

**Root cause:** `self.TARGET` (`.research-card` / `.kicker`) is non-unique; `querySelector` (restyle+assert) and the real-click `_select` resolve to different elements.

**File:** `tests/e2e/test_r7_alignment.py`

**Fix:** in `_ensure_target`, after resolving a class that exists, pin a stable unique `id` on the FIRST match and switch `TARGET` to that id selector, so `querySelector(TARGET)` and the real mouse click address the SAME node.

**Current anchor (`test_r7_alignment.py:36-42`):**
```python
    # pick a registered element that exists in the fixture
    TARGET = ".research-card"

    def _ensure_target(self):
        if not H.doc_eval(self.page, f"return !!doc.querySelector('{self.TARGET}');"):
            self.TARGET = ".kicker"
        self.assertTrue(H.doc_eval(self.page, f"return !!doc.querySelector('{self.TARGET}');"), "no usable registered element")
```

**Replace with:**
```python
    # pick a registered element that exists in the fixture
    TARGET = ".research-card"

    def _ensure_target(self):
        # Resolve a class that exists, then PIN a unique id on its FIRST match so the
        # element we restyle/assert (querySelector) is the SAME element the real-mouse
        # _select() clicks. The fixture has MANY .research-card / .kicker nodes; without
        # a unique handle, querySelector returns the first while the click selects a
        # neighbour, and every assertion reads the wrong (un-restyled) element.
        cls = ".research-card"
        if not H.doc_eval(self.page, f"return !!doc.querySelector('{cls}');"):
            cls = ".kicker"
        ok = H.doc_eval(
            self.page,
            f"const e=doc.querySelector('{cls}'); if(!e) return false; "
            f"e.id='r7-target'; return true;",
        )
        self.assertTrue(ok, "no usable registered element")
        self.TARGET = "#r7-target"
```

**Why this is sufficient and minimal:** `_restyle`, `_select`, `_computed` already read `self.TARGET` via `querySelector`; once `TARGET` is `#r7-target` (a unique id), all three address one node, and the real mouse click at that node's rect-center selects that exact node (proven: §"Live-validated matrix" — `sel_ok:true` for every scenario). No change to any assertion, timing, or click target. `id='r7-target'` is additive (the runtime registry adopts existing ids; `byId`/selection are unaffected) and is reset per test because `setUp` reopens a fresh fixture copy.

> Optional hardening (not required for green; the rect-center click already lands correctly because a uniquely-id'd region with real content has a hittable interior): none needed. If a future fixture has a zero-area first match, also set a min-size in `_restyle`; current fixture does not require it.

## EDIT 2 — Remove the `win` redeclaration (fixes E-R7-10 SyntaxError)

**Root cause:** `doc_eval` injects `win` as a `new Function` parameter; the test body redeclares `const win`.

**File:** `tests/e2e/test_r7_alignment.py`

**Current anchor (`test_r7_alignment.py:146-149`):**
```python
        # flex → vertical true
        self._restyle("display:flex;flex-direction:row;")
        self._select()
        caps_flex = H.doc_eval(self.page, f"const e=doc.querySelector({self.TARGET!r}); const win=document.querySelector('iframe.doc-frame').contentWindow; return null;")
```

**Replace with** (drop the dead `caps_flex`/`win` line entirely — it computes nothing and `win` is already provided by `doc_eval`):
```python
        # flex → vertical true
        self._restyle("display:flex;flex-direction:row;")
        self._select()
```

**Why:** the line assigns `null` to an unused variable and only exists to (incorrectly) demonstrate caps access; the test's real assertions (lines 152, 156) drive caps through the button disabled-state, which is correct and untouched. Removing the line eliminates the `SyntaxError` with no behavioral change. (Equivalent alternative if the line must stay: rename `win` → `cw` and use the injected `win` instead of re-deriving it. Deletion is preferred — it is dead code.)

## No other changes

- No edit to `_select`, `_restyle`, `_computed`, `_undo`, or any `assertEqual` — the existing assertions are correct and pass once EDIT 1 aligns the queried/selected element.
- No product-file edit. The runtime, command factory, caps predicate, apply logic, selection payload, and shell button wiring are all correct as shipped (live-proven GREEN).

---

## Verification performed (evidence before assertion)

- Server :8791 started/stopped; all browsers closed in-script; port re-checked free; scratch removed from `$env:TEMP`. No git writes. No web.
- Full production chain instrumented at every boundary (button → bridge out → response/event → history → caps payload → computed style) for real clicks.
- 9/9 normative scenarios produced spec-mandated outcomes against the UNMODIFIED runtime; the only variable changed vs. the failing test was target uniqueness, which EDIT 1 reproduces.
- Confirmed the failing test selects a different element than it restyles (query-id ≠ select-id) across all four display modes.
- Reproduced the `win` collision mechanism from `doc_eval`'s `new Function('doc','win', body)` wrapper.
