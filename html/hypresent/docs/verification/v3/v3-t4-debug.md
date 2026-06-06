# V3-T4 — R8 Font-Size Repeat: Live Root-Cause + Fix Spec v3

**Date:** 2026-06-04
**Boundary:** C2 (R8 font-size repeat)
**Fixture:** tecer-gsmm-introduction.html · **Server:** 127.0.0.1:8791 (live) · baseline reproduced on test runner port 8798
**Method:** runtime-only instrumentation (re-`register` bridge handlers + faithful re-implementation of `text-format.js` apply path, driven by REAL dblclick + REAL `#fmt-font-inc` clicks through the REAL parent→iframe bridge and REAL `history.push`). ZERO product/test files modified on disk.

---

## 0. Verdict (read first)

- **Working hypothesis (stale-snapshot race) is REJECTED.** The snapshot is *fresh* every press; nothing consumes press N−1's range. The two real defects are **collapsed-snapshot-passes-as-valid** (primary, blocks the fallback) and **node-identity tracking is unstable** (deeper, severs `currentFontSpan` on every press via the history `innerHTML` round-trip).
- **Live-validated fix:** marker-based, identity-free, race-free. After 3 presses → **ONE span, 38px (base 32 +6), zero empties.** Unlimited repeats, new-word targeting, cross-session isolation, and B/I all pass.
- **Fix touches ONE file: `runtime/js/text-format.js`.** No change to `runtime-main.js`, `app/js/main.js`, `bridge-iframe.js`, or the test. **No test assertion is wrong — do NOT weaken the test.**

---

## 1. Reproduction (baseline RED)

Real test runner, real input:
```
FAILED tests/e2e/test_r8_font_size_repeat.py::...::test_three_increases_one_span_plus6_zero_empty
AssertionError: 3 != 1 : expected exactly ONE font-size span after 3 presses, got 3 (sizes=[34, 34, 34])
```
Live instrumented reproduction on 8791 (real dblclick selects word `"Tecer "`, base computed = 32px): **count=3, sizes=[34,34,34], emptyCount=2.** Final DOM:
```html
<div class="slide-title" ...><span style="font-size: 34px;"></span><span style="font-size: 34px;"></span>
  A <span style="font-size: 34px;">Tecer </span>entrega operações financeiras autônomas </div>
```
Two **empty** 34px spans prepended at `div@0`; the real "Tecer" span never grows past +2.

---

## 2. Interleaving evidence (VERBATIM)

Bridge handlers wrapped with hi-res `performance.now()` + sequence number. Each `format` arrival logs live-selection state and a Selection-method spy that reveals which branch executed. (Full capture: `$TEMP/hypdbg/capture_out.json`.)

### Press 1 — snapshot then format (CORRECT)
```
SNAPSHOT-pre  seq1 t1204.6  rangeCount1 collapsed=false selText="Tecer "
              cAC=#text("A Tecer entrega operaçõe") in <div.slide-title>  startC=...@23 endC=...@29
FORMAT-pre    seq3 t1209.3  rangeCount1 collapsed=false selText="Tecer "  cAC=#text(...) in <div.slide-title>
  selEvents:  ["removeAllRanges","addRange(range \"Tecer \")","getRangeAt(0)","getRangeAt(0)",
               "getRangeAt(0)","removeAllRanges","addRange(range \"Tecer \")"]
  spanInfo:   count1 sizes[34] nesting[0] empty[false]
  afterHTML:  ... A <span style="font-size: 34px;">Tecer </span>entrega ...
FORMAT-post   seq4 t1211.1  rangeCount1 collapsed=TRUE  selText=""  cAC=<div.slide-title> startC=<div.slide-title>@0
```
Press 1 restores the live word, wraps it, and re-selects it — but the selection **collapses to `div.slide-title@0` immediately after** (FORMAT-post).

### Press 2 — the failure (VERBATIM)
```
SNAPSHOT-pre  seq5 t1420.1  rangeCount1 collapsed=TRUE  selText=""  cAC=<div.slide-title>  startC=<div.slide-title>@0
FORMAT-pre    seq7 t1420.3  rangeCount1 collapsed=TRUE  selText=""  cAC=<div.slide-title>  startC=<div.slide-title>@0
  selEvents:  ["removeAllRanges","addRange(collapsed \"\")","getRangeAt(0)","getRangeAt(0)",
               "removeAllRanges","addRange(collapsed \"\")","getRangeAt(0)","removeAllRanges","addRange(collapsed \"\")"]
  spanInfo:   count2 sizes[34,34] nesting[0,0] empty[true,false]
  afterHTML:  <span style="font-size: 34px;"></span> A <span style="font-size: 34px;">Tecer </span>entrega ...
```
The mousedown snapshot captured a **collapsed range at `div@0`** (because press 1 left the selection collapsed there). `format` then: (1st `removeAllRanges;addRange(collapsed "")`) = snapshot restore fired on the collapsed range; (2nd) = the collapsed-reselect block; (3rd) = post-create reselect. Result: a NEW **empty** 34px span at `div@0`. Press 3 (seq9–12) repeats identically → second empty span.

**Key observation: the snapshot is NOT stale.** SNAPSHOT-pre on press 2 (seq5) is captured fresh at t1420 and reflects the *current* collapsed selection — it is exactly the post-press-1 collapse, not a leftover of press 1's word range.

---

## 3. Named root cause + the exact executing branch

### 3a. Primary defect — collapsed snapshot passes BOTH gates, blocking the fallback

Live predicate evaluation reproducing the press-2 entry state (`$TEMP/hypdbg/verify_branches.py`):
```json
{ "snapshotIsValid": true, "sv_startConnected": true, "sv_endConnected": true, "sv_elContainsCAC": true,
  "haveUsableRange": true, "fallbackReached": false,
  "ew_collapsed": true, "ew_startNodeType": 1, "ew_isTextNode": false, "expandToWord_wouldExpand": false,
  "cAC_equals_el": true, "foundPriorSpan": false, "mintedEmptySpan": true, "spanCountAfter": 2 }
```

Branch-by-branch, against `runtime/js/text-format.js`:

1. **`snapshotIsValid(el)` returns `true`** on the collapsed `div@0` range — its endpoints (`div`) are `isConnected` and `el.contains(div)` is true (`contains` includes self). The executing line (`:100`):
   ```js
   if (snapshotIsValid(el)) {            // TRUE for a collapsed div@0 range
     sel.removeAllRanges();
     sel.addRange(savedRange.cloneRange());
   }
   ```
   The R8 "snapshot-always-wins" comment claims the live selection is "focus-shift garbage" — but here the *snapshot itself* is garbage (collapsed), and it is restored unconditionally.

2. **`haveUsableRange` is `true`** because a collapsed range still has `rangeCount > 0`. **This is the branch that executed on press 2** and is the load-bearing failure — the `currentFontSpan` fallback (the ONLY path that grows the existing span) is **never reached** (`fallbackReached:false`). The executing line (`:109`):
   ```js
   const haveUsableRange = sel && sel.rangeCount > 0;   // TRUE — collapsed range counts
   if (!haveUsableRange) { /* currentFontSpan fallback — SKIPPED on press 2+ */ }
   ```

3. `expandToWord` is a no-op: the collapsed range's `startContainer` is the **`div` element** (nodeType 1), so `expandToWord` returns it unchanged (`:76-77`). The walk-up loop body never runs because `container === el` (`:136` `while (container && container !== el)` is immediately false → `foundPriorSpan:false`).

4. `range.surroundContents(span)` on the empty collapsed range mints an **empty** span (`mintedEmptySpan:true`, `:161`).

### 3b. Deeper defect — `currentFontSpan` is severed every press by the history round-trip

Even a *reached* `currentFontSpan` fallback cannot work, because `apply()` finishes each press with `history.push(format(hypId, beforeHtml, afterHtml))`, and that command's `do()` runs **`el.innerHTML = afterHtml`** (`commands.js:71`, executed by `history.push` at `history.js:49`). Live proof (`$TEMP/hypdbg/prove_detach.py`):
```json
{ "sameBefore": true, "connBefore": true,     // before push: tracked node IS the live node
  "sameAfter": false, "connAfter": false }    // after  push: tracked node DETACHED; a NEW span is live
```
So `currentFontSpan` from press 1 is `isConnected === false` by press 2 — confirmed live in the fix-v1 trace: `[cfs=SPAN:34px, cfsConnected=false, titleHasCfs=false]`. **Any design that holds a live DOM node reference across presses is fundamentally broken in this architecture.**

---

## 4. Nesting structure per press (Phase C)

Spans are **siblings, not nested** (every `nesting` value = 0); each new span is created at `div@0` from the element's base computed size (32 → +2 = 34) because the walk-up never finds a parent font-span.

| After press | outerHTML (whitespace-collapsed) | span count / sizes / empties |
|---|---|---|
| 1 | `A <span fs=34>Tecer </span>entrega …` | 1 / [34] / 0 |
| 2 | `<span fs=34></span> A <span fs=34>Tecer </span>entrega …` | 2 / [34,34] / 1 |
| 3 | `<span fs=34></span><span fs=34></span> A <span fs=34>Tecer </span>entrega …` | 3 / [34,34,34] / 2 |

Each press's computed base for the new span = 32px (the `.slide-title` element), +2 = 34px — never compounding, because the empty spans hold no text and the real span is never the walk-up target.

---

## 5. Winning design — marker-based, identity-free, race-free

**Idea:** stop trusting (a) the snapshot's collapse state and (b) a live node reference. Track the editor's font-size span by a **stable DOM marker `data-hyp-fontspan`** that is re-found by `querySelector` every press, so it survives the `innerHTML = afterHtml` round-trip. Marker name is deliberately `data-hyp-*` so the serializer's existing strip pass (`serializer.js:178-184`) removes it from saved output automatically — saved HTML stays clean with zero extra code.

**Precedence in `adjustFontSize(el, delta)`:**
1. snapshot-always-wins restore (unchanged).
2. **Word-expand the live range FIRST.** If a **non-collapsed** range results → it is a real selection: walk up to an existing font-span and grow it, else create a new span. Creating/growing **moves the single marker** to the targeted span (clears any other marked span). → handles press 1 and genuine new-word selections.
3. **Else (range missing or still collapsed after expand)** → re-find `el.querySelector('span[data-hyp-fontspan]')` and grow it. No node reference held. → handles every repeat press; correctness does NOT depend on snapshot timing (snapshot may be collapsed/late/never — the marked span deterministically wins).

`clearFontState()` additionally strips the marker (document-wide; the marker is set only by this module) so the live DOM matches pre-R8 after commit. Cross-session isolation also holds structurally because step 3's `querySelector` is scoped to the active `el`.

### 5a. Live validation outputs (REAL input, REAL bridge + history)

`$TEMP/hypdbg/validate2_out.json` — all scenarios:

| Scenario | Result | Expectation | Verdict |
|---|---|---|---|
| **s1 — 3× inc** (load-bearing) | count=1, sizes=[**38**], empty=0, marked=1 | base 32 +6 = 38 | **PASS** |
| s2 — 3× dec | count=1, sizes=[**26**], empty=0 | max(8, 32−6)=26 | **PASS** |
| s3 — inc,inc,dec | count=1, sizes=[**34**], empty=0 | 32+2=34 | **PASS** |
| s4 — 6× inc (unlimited) | count=1, sizes=[**44**], empty=0 | 32+12=44 | **PASS** |
| s5 — new word "autônomas" mid-stream | count=2, marked=1; "Tecer"=34 untouched, new span=34 | new word gets its OWN span | **PASS** |
| s5b — new word then collapsed repeat | count=2, sizes=[34,**36**] | repeat bumps NEW span only | **PASS** |
| s6 — Escape commit → edit .kicker | y_count=1, sizes=[14] | fresh single span, no carry-over | **PASS** |
| s7 — bold then italic | `font-weight` spans produced; font-size path untouched | no B/I regression | **PASS** |

Per-press branch trace for s1 (proves the intended path):
```
fontInc -> restored;createdSpan;                  sizes[34] marked[true]
fontInc -> restored;fallback;bumpedMarked(36px);  sizes[36] marked[true]
fontInc -> restored;fallback;bumpedMarked(38px);  sizes[38] marked[true]
```
s5 (new-word correctly takes the create path, not fallback; marker moves):
```
fontInc -> restored;createdSpan;   sizes[34]      marked[true]
fontInc -> restored;createdSpan;   sizes[34,34]   marked[false,true]   // "Tecer" demarked, new span marked
```

---

## 6. FIX SPEC v3 — executor-ready

**File:** `runtime/js/text-format.js` — **ONLY file changed.** Apply the four edits below verbatim. No other product file, no test file.

### Edit 1 — module state (replace the `currentFontSpan` var + its comment)

**Anchor (current, lines 20–26):**
```js
// --- R8 state: selection survival across the toolbar-click focus cycle ---
// The toolbar button's mousedown does preventDefault + iframe focus(), which
// collapses the iframe Selection to the editable root. We snapshot the live
// range on that mousedown (via the format-snapshot bridge command) and restore
// it here; we also track the current font-size span as a fallback.
let savedRange = null;
let currentFontSpan = null;
```
**Replace with:**
```js
// --- R8 state: selection survival across the toolbar-click focus cycle ---
// The toolbar button's mousedown does preventDefault + iframe focus(), which
// collapses the iframe Selection to the editable root. We snapshot the live
// range on that mousedown (via the format-snapshot bridge command) and restore
// it on the next apply().
//
// We do NOT hold a live reference to the tracked font-size span: history.push
// runs the format command's `el.innerHTML = afterHtml`, which re-serialises the
// subtree and DETACHES any held node every press (RV?? — proven live in v3-t4).
// Instead the tracked span is marked with FONT_SPAN_MARKER and re-found by
// querySelector each press, so it survives the innerHTML round-trip. The marker
// is a data-hyp-* attribute, so serializer.js strips it from saved output.
let savedRange = null;
const FONT_SPAN_MARKER = "data-hyp-fontspan";
```

### Edit 2 — `clearFontState` (strip the marker instead of nulling the node ref)

**Anchor (current, lines 60–64):**
```js
/** Clear R8 font state (called on edit commit so a new edit starts clean). */
export function clearFontState() {
  savedRange = null;
  currentFontSpan = null;
}
```
**Replace with:**
```js
/** Clear R8 font state (called on edit commit so a new edit starts clean). */
export function clearFontState() {
  savedRange = null;
  // Strip the tracked-span marker so a fresh edit starts with no tracked span.
  // The marker is set only by this module, so a document-wide strip is safe.
  document
    .querySelectorAll(`span[${FONT_SPAN_MARKER}]`)
    .forEach((s) => s.removeAttribute(FONT_SPAN_MARKER));
}
```

### Edit 3 — `adjustFontSize` (the core rewrite)

**Anchor (current, lines 93–175) — the ENTIRE function body from `function adjustFontSize(el, delta) {` through its closing `}` immediately before `// --- Public API ---`:**
```js
function adjustFontSize(el, delta) {
  const sel = window.getSelection();

  // (R8 step 1) SNAPSHOT-ALWAYS-WINS: if a VALID mousedown snapshot exists, restore
  // it UNCONDITIONALLY. The post-toolbar-click live selection is focus-shift garbage
  // by construction (mousedown→focus() relocated it), so the validated snapshot always
  // supersedes it. There is NO live-collapse / commonAncestorContainer === el check.
  if (snapshotIsValid(el)) {
    sel.removeAllRanges();
    sel.addRange(savedRange.cloneRange());
  }

  // (R8 step 2) If there is STILL no usable range — no snapshot was restored AND the
  // live selection has no range at all — fall back to the tracked span from a prior
  // press: bump it directly and return. "No usable range" is a genuine no-range state
  // (sel missing or rangeCount === 0), NEVER a collapse-identity check.
  const haveUsableRange = sel && sel.rangeCount > 0;
  if (!haveUsableRange) {
    if (currentFontSpan && el.contains(currentFontSpan)) {
      const cur = parseFloat(currentFontSpan.style.fontSize);
      currentFontSpan.style.fontSize = `${Math.max(8, Math.round(cur + delta))}px`;
    }
    savedRange = null; // consume the snapshot
    return;
  }

  let range = sel.getRangeAt(0).cloneRange();
  range = expandToWord(range);

  const currentRange = sel.getRangeAt(0);
  if (currentRange.collapsed && range !== currentRange) {
    sel.removeAllRanges();
    sel.addRange(range);
  }

  range = sel.getRangeAt(0);

  // Walk up the ancestor chain to find an existing font-size span created
  // by this editor and update it instead of nesting a new one.
  let container = range.commonAncestorContainer;
  if (container.nodeType === Node.TEXT_NODE) {
    container = container.parentElement;
  }
  while (container && container !== el) {
    if (
      container.tagName.toLowerCase() === "span" &&
      container.style.fontSize
    ) {
      const currentSize = parseFloat(container.style.fontSize);
      const newSize = Math.max(8, Math.round(currentSize + delta));
      container.style.fontSize = `${newSize}px`;
      currentFontSpan = container; // (R8) track for the fallback path
      savedRange = null;            // consume the snapshot
      return;
    }
    container = container.parentElement;
  }

  // Compute reference size from the start of the selection
  let refNode = range.startContainer;
  if (refNode.nodeType === Node.TEXT_NODE) refNode = refNode.parentElement;
  const computedSize = parseFloat(window.getComputedStyle(refNode).fontSize);
  const newSize = Math.max(8, Math.round(computedSize + delta));

  const span = document.createElement("span");
  span.style.fontSize = `${newSize}px`;

  try {
    range.surroundContents(span);
  } catch (_e) {
    span.appendChild(range.extractContents());
    range.insertNode(span);
  }

  currentFontSpan = span;  // (R8) track the newly created span
  savedRange = null;       // consume the snapshot

  // Reselect the wrapped content so subsequent ops apply cleanly
  sel.removeAllRanges();
  const newRange = document.createRange();
  newRange.selectNodeContents(span);
  sel.addRange(newRange);
}
```
**Replace the ENTIRE function with:**
```js
/** Find this editor's currently-tracked font-size span inside `el` (re-found each
 *  call so it survives the history `innerHTML = afterHtml` round-trip). */
function trackedFontSpan(el) {
  return el.querySelector(`span[${FONT_SPAN_MARKER}]`);
}

/** Mark `span` as the single tracked font-size span; clear the marker from any
 *  other span in `el` (single-marker invariant). */
function setTrackedFontSpan(el, span) {
  el.querySelectorAll(`span[${FONT_SPAN_MARKER}]`).forEach((s) => {
    if (s !== span) s.removeAttribute(FONT_SPAN_MARKER);
  });
  if (span) span.setAttribute(FONT_SPAN_MARKER, "");
}

function adjustFontSize(el, delta) {
  const sel = window.getSelection();

  // (R8 step 1) SNAPSHOT-ALWAYS-WINS: if a VALID mousedown snapshot exists, restore
  // it. The post-toolbar-click live selection is focus-shift garbage by construction.
  if (snapshotIsValid(el)) {
    sel.removeAllRanges();
    sel.addRange(savedRange.cloneRange());
  }

  // (R8 step 2 — v3) Word-expand the candidate range FIRST, then decide usability by
  // COLLAPSE (not rangeCount). A collapsed range whose container is the editable root
  // (the post-press-1 focus-collapse, or a collapsed snapshot) is NOT usable for
  // formatting — both the live selection AND a restored collapsed snapshot land here.
  let range = sel && sel.rangeCount > 0 ? sel.getRangeAt(0).cloneRange() : null;
  if (range) range = expandToWord(range);

  // No range, or still collapsed after word-expansion → repeat path: re-find the
  // marked span and bump it. Race-free: independent of snapshot timing/identity.
  if (!range || range.collapsed) {
    const span = trackedFontSpan(el);
    if (span) {
      const cur = parseFloat(span.style.fontSize);
      span.style.fontSize = `${Math.max(8, Math.round(cur + delta))}px`;
    }
    savedRange = null; // consume the snapshot
    return;
  }

  // A real (non-collapsed) word range: commit it to the live selection.
  sel.removeAllRanges();
  sel.addRange(range);
  range = sel.getRangeAt(0);

  // Walk up to an existing font-size span and grow it instead of nesting a new one.
  let container = range.commonAncestorContainer;
  if (container.nodeType === Node.TEXT_NODE) {
    container = container.parentElement;
  }
  while (container && container !== el) {
    if (
      container.tagName.toLowerCase() === "span" &&
      container.style.fontSize
    ) {
      const currentSize = parseFloat(container.style.fontSize);
      container.style.fontSize = `${Math.max(8, Math.round(currentSize + delta))}px`;
      setTrackedFontSpan(el, container); // move the single marker here
      savedRange = null;                 // consume the snapshot
      return;
    }
    container = container.parentElement;
  }

  // Create a new span for this (new) word, sized from the selection start.
  let refNode = range.startContainer;
  if (refNode.nodeType === Node.TEXT_NODE) refNode = refNode.parentElement;
  const computedSize = parseFloat(window.getComputedStyle(refNode).fontSize);
  const newSize = Math.max(8, Math.round(computedSize + delta));

  const span = document.createElement("span");
  span.style.fontSize = `${newSize}px`;

  try {
    range.surroundContents(span);
  } catch (_e) {
    span.appendChild(range.extractContents());
    range.insertNode(span);
  }

  setTrackedFontSpan(el, span); // this new span is now the single tracked span
  savedRange = null;            // consume the snapshot

  // Reselect the wrapped content so subsequent ops apply cleanly.
  sel.removeAllRanges();
  const newRange = document.createRange();
  newRange.selectNodeContents(span);
  sel.addRange(newRange);
}
```

### Edit 4 — none. `snapshotSelection`, `snapshotIsValid`, `expandToWord`, `getActiveEditElement`, `apply`, and the imports are unchanged. `runtime-main.js`, `app/js/main.js`, `bridge-iframe.js` unchanged.

### Test changes — NONE.
The test assertions are correct and were verified to GREEN under the fix (live): `count == 1`, `emptyCount == 0`, `sizes[0] ≈ base+6`. Do **not** weaken any outcome assertion.

---

## 7. Why this satisfies every constraint

1. **Race-free** — the repeat path (step 3) reads the DOM marker via `querySelector`; it never depends on whether/when the snapshot arrived. A collapsed/late/absent snapshot still yields the marked span. Proven: s1/s4 grow monotonically via `fallback;bumpedMarked` while the snapshot each press is collapsed garbage.
2. **New-word targeting** — a fresh dblclick yields a non-collapsed range → step 2 create-path runs (`createdSpan`, not fallback) and `setTrackedFontSpan` moves the marker to the new word; the old span is left intact. Proven: s5 (count=2, marked moved) + s5b (collapsed repeat bumps only the new word).
3. **Cross-session isolation** — `clearFontState()` strips the marker on commit; additionally `trackedFontSpan(el)` is element-scoped. Proven: s6 (.kicker gets its own single span, no carry-over from .slide-title).
4. **Unlimited repeats** — one span grows/shrinks indefinitely (`Math.max(8, …)` floor preserved). Proven: s4 (6 presses → 44px, count 1).
5. **No B/I regression** — the marker and the new logic live entirely within the `fontInc/fontDec` path; bold/italic still route through `document.execCommand`. Proven: s7.
6. **Clean serialized output** — `data-hyp-fontspan` is a `data-hyp-*` attribute, stripped by `serializer.js:178-184`; `clearFontState` also strips it on commit.

---

## 8. Reproduction artifacts (scratch, `%TEMP%/hypdbg/`)

| File | Purpose |
|---|---|
| `instrument.js` / `run_capture.py` / `capture_out.json` | §2 verbatim interleaving (baseline RED, 3 presses) |
| `verify_branches.py` | §3a live predicate proof (collapsed snapshot valid + fallback skipped) |
| `prove_detach.py` | §3b live proof the history `innerHTML` round-trip detaches the tracked node |
| `fix2_emulation.js` / `validate_fix2.py` / `validate2_out.json` | §5 live validation of the winning design (all 8 scenarios) |

Executor next step: apply Edits 1–3 to `runtime/js/text-format.js`, then run
`python -m pytest tests/e2e/test_r8_font_size_repeat.py -q` (expects 5/5 GREEN).
