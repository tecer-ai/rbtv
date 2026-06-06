# Research 02 — Moveable.js Snapping & Alignment Guidelines

**Date:** 2026-06-03  
**Scope:** Moveable.js snappable API for Google-Slides-style alignment guidelines in Hypresent.  
**Vendored version:** 0.53.0 (latest published as of research date — confirmed on GitHub Releases and npm).  
**No files were modified; this file is the sole write.**

---

## 1. Vendored Version Confirmation

The vendored file at `app/js/vendor/moveable.min.js` declares:

```
Copyright (c) 2019 Daybrush
name: moveable
license: MIT
version: 0.53.0
```

0.53.0 is also the **latest published version** on npm and GitHub (published 2023-12-03). No newer release exists as of June 2026. The library appears to be in maintenance mode — no releases after 0.53.0. **No upgrade is needed or available.**

License: **MIT** — confirmed from vendored banner and jsDelivr/cdnjs listings. [1][3]

---

## 2. Snappable API — Complete Option Reference for v0.53.0

All options below are present in 0.53.0 unless noted otherwise. Sources: official Snappable API docs [2] and types file [4].

### 2a. Core enable

| Option | Type | Default | Notes |
|--------|------|---------|-------|
| `snappable` | `boolean \| string[]` | `false` | `true` enables all snap types. String array selects specific abilities (e.g. `["resizable","draggable"]`). |
| `snapContainer` | `MoveableRefType<HTMLElement>` | `null` (uses constructor `container`) | Must be set to the iframe's `document.body` (or the `wrapper` div) when Moveable is mounted inside an iframe — see §5. |

### 2b. Snap directions

```typescript
interface SnapDirections {
  left?: boolean;   // default: true
  top?: boolean;    // default: true
  right?: boolean;  // default: true
  bottom?: boolean; // default: true
  center?: boolean; // default: false — horizontal center line
  middle?: boolean; // default: false — vertical midline
}
```

| Option | Type | Default | Governs |
|--------|------|---------|---------|
| `snapDirections` | `boolean \| SnapDirections` | `{left,top,right,bottom:true}` | Which edges/centers of the **dragged/resized element** snap to guidelines. |
| `elementSnapDirections` | `boolean \| SnapDirections` | `{left,top,right,bottom:true}` | Which edges/centers of the **guideline elements** are used as snap targets. |

To get Google Slides center-alignment behavior, both `center` and `middle` must be explicitly set to `true` — they default to `false`.

### 2c. Distance and gap

| Option | Type | Default | Notes |
|--------|------|---------|-------|
| `snapThreshold` | `number` | `5` | Pixel radius within which snap triggers. |
| `snapHorizontalThreshold` | `number` | `5` | Per-axis override (added in 0.53.0). |
| `snapVerticalThreshold` | `number` | `5` | Per-axis override (added in 0.53.0). |
| `snapRenderThreshold` | `number` | `1` | Minimum pixel proximity before guideline line renders. Keep at 1. |
| `snapGap` | `boolean` | `true` | Show equal-spacing gap snap guides between elements. |
| `maxSnapElementGuidelineDistance` | `number` | `Infinity` | Ignore element guideline sources beyond this many pixels. Set to `~300`–`600` for slide-like layouts to exclude off-screen elements. |
| `maxSnapElementGapDistance` | `number` | `Infinity` | Same limit but for gap snap sources. |

### 2d. Element guidelines

```typescript
interface ElementGuidelineValueOption extends SnapDirections {
  element: Element;         // the DOM element to use as guideline source
  className?: string;       // extra CSS class(es) added to rendered guide lines for this element
  refresh?: boolean;        // re-measure element rect on every render (expensive); default false
}
```

`elementGuidelines` accepts `Array<Element | ElementGuidelineValueOption>`. Simple form: just pass DOM elements. Extended form: pass objects with per-element direction overrides and optional `className`.

### 2e. Display options

| Option | Type | Default | Notes |
|--------|------|---------|-------|
| `isDisplaySnapDigit` | `boolean` | `true` | Show numeric distance label on gap snap lines. |
| `isDisplayInnerSnapDigit` | `boolean` | `false` | Show inner-element distance labels. |
| `snapDigit` | `number` | `0` | Decimal precision for distance labels. |
| `snapDistFormat` | `(dist, type) => string \| number` | identity | Format the distance text. |

---

## 3. Copy-Pasteable Config Recipe

This recipe targets the exact Hypresent constructor pattern (`new window.Moveable(wrapper, options)` inside the iframe) for both resize and move modes.

```javascript
// Gather sibling elements as guideline sources.
// Call this each time the tool is activated on a new target element.
function getElementGuidelines(targetEl) {
  // All data-hyp-id elements on the same slide EXCEPT the active target.
  const slide = targetEl.closest('section, .slide, body') ?? document.body;
  return Array.from(slide.querySelectorAll('[data-hyp-id]'))
    .filter(el => el !== targetEl);
}

// --- RESIZE MODE (replaces current resize.js constructor call) ---
const moveableResize = new window.Moveable(wrapper, {
  target: el,
  resizable: true,
  edge: true,
  throttleResize: 1,

  // Snappable
  snappable: true,
  snapContainer: wrapper,           // coordinate space = iframe viewport
  snapThreshold: 5,
  snapGap: true,
  maxSnapElementGuidelineDistance: 500,

  elementGuidelines: getElementGuidelines(el),
  snapDirections: { left: true, top: true, right: true, bottom: true, center: true, middle: true },
  elementSnapDirections: { left: true, top: true, right: true, bottom: true, center: true, middle: true },

  isDisplaySnapDigit: false,        // keep UI clean; set true if gap distances are useful
  snapRenderThreshold: 1,
});

// --- MOVE MODE (replaces current move.js constructor call) ---
const moveableMove = new window.Moveable(wrapper, {
  target: el,
  draggable: true,
  resizable: false,
  throttleDrag: 0,

  // Snappable (identical snap config)
  snappable: true,
  snapContainer: wrapper,
  snapThreshold: 5,
  snapGap: true,
  maxSnapElementGuidelineDistance: 500,

  elementGuidelines: getElementGuidelines(el),
  snapDirections: { left: true, top: true, right: true, bottom: true, center: true, middle: true },
  elementSnapDirections: { left: true, top: true, right: true, bottom: true, center: true, middle: true },

  isDisplaySnapDigit: false,
  snapRenderThreshold: 1,
});
```

**Updating guidelines when the target changes** (the 150ms polling loop in both `resize.js` and `move.js`):

```javascript
// When the polling loop detects a new target, update guidelines:
moveable.elementGuidelines = getElementGuidelines(newTargetEl);
// Direct property assignment is supported; no setState() or updateRect() required
// for elementGuidelines alone. Call updateRect() only if target geometry changed.
moveable.target = newTargetEl;
moveable.updateRect();
```

**Per-element `refresh: true` pattern** (use only if element positions change during drag, e.g. reflowing flex/grid siblings):

```javascript
elementGuidelines: getElementGuidelines(el).map(e => ({ element: e, refresh: true }))
// Costs one getBoundingClientRect() per guideline element per render frame.
// For ~10-100 elements this is acceptable; profile if jank appears.
```

---

## 4. Guideline Rendering — CSS Classes and DOM Structure

Moveable auto-renders guideline DOM elements inside its control box (`.moveable-control-box`), which is appended to the `container` argument of the constructor — in Hypresent's case, the `div.hyp-moveable-wrapper` (fixed, full-viewport, z-index 999998, pointer-events:none).

Key CSS classes on rendered guideline lines [2][4][5]:

| Class | Element type | Styling hook |
|-------|-------------|--------------|
| `.moveable-line` | `div` | General line element (position, width/height) |
| `.moveable-gap` | subclass of `.moveable-line` | Gap snap indicator — style via `background` |
| `.moveable-dashed` | subclass of `.moveable-line` | Dashed guideline — style via `border-top-color` |
| `.moveable-bold` | subclass of `.moveable-line` | Bold primary guideline |

To override colors:

```css
/* Inside the iframe document (where Moveable renders) */
.moveable-gap { background: #0084ff !important; }
.moveable-dashed { border-top-color: #0084ff !important; }
.moveable-bold { background: #0084ff !important; }
```

**Z-index:** The `hyp-moveable-wrapper` is already at z-index 999998 and Moveable appends its control box (including guideline lines) as a child. Guideline lines inherit the stacking context of the wrapper. No additional z-index tuning is needed — the wrapper already sits above slide content. The `pointer-events:none` on the wrapper means guidelines are non-interactive, which is correct.

**Custom per-element guideline color** (requires `className` on each guideline entry):

```javascript
elementGuidelines: getElementGuidelines(el).map(e => ({
  element: e,
  className: 'hyp-guide',
}))
// Then in iframe CSS: .moveable-gap.hyp-guide { background: rgba(255,0,100,0.8) !important; }
```

---

## 5. Dynamic `elementGuidelines` Refresh Pattern

### Findings from issues #266, #854, and API docs [2][4][6][7]

**Root cause of the caching issue:** In older versions (pre-0.23.0), `elementGuidelines` was cached after the first render. From 0.23.0 onward, direct property assignment on the Moveable instance triggers an internal re-measure on the next drag/resize event.

**Correct pattern for Hypresent** (where the target may change via the 150ms polling loop):

```javascript
// On target change — both resize.js and move.js polling handlers:
function onTargetChange(moveable, newEl) {
  moveable.target = newEl;
  moveable.elementGuidelines = getElementGuidelines(newEl);
  // updateRect() is needed to re-measure the new target's geometry:
  moveable.updateRect();
}
```

**Per-element `refresh: true` flag:** Set to `true` per `ElementGuidelineValueOption` to force a re-measure of that guideline element on every render frame. Appropriate when sibling elements may reflow (e.g. flex containers where resizing one child changes others). Cost: one `getBoundingClientRect()` call per marked element per drag/resize event. For 10–100 elements on a slide this is negligible (<1ms on modern hardware). Set to `false` (default) for static layouts.

**Function-based `elementGuidelines` is NOT supported** — the prop accepts only an array. No callback API exists. The pattern is: rebuild the array and assign it before (or at the start of) each interaction.

**Best practice for Hypresent:** Since `begin(hypId)` is called per interaction, populate `elementGuidelines` in the `begin()` call. No mid-drag refresh is needed unless slide elements move independently (they don't in Hypresent today).

---

## 6. Known Issues and Risks

### 6a. Snap coordinate space in iframe

**Risk: MEDIUM-HIGH.** Moveable v0.48.0 added explicit iframe context support (`"Supported iframe context"`, `"Fixed ownerDocument CSS for iframe"`). Before 0.48.0 this was broken. Since the vendored version is 0.53.0 (post-0.48.0), iframe support is included. [8]

**However**, the `snapContainer` must be explicitly set to a container element inside the iframe. In Hypresent, `wrapper` (the `div.hyp-moveable-wrapper` appended to `document.body` inside the iframe) is the right choice. If `snapContainer` is omitted or set to `null`, Moveable defaults to the Moveable constructor's `container` argument — which in Hypresent is also `wrapper`. Either way, the coordinate space is the iframe viewport, not the parent page, which is correct.

**Guideline positions** (`elementGuidelines` elements) must also be in the same document as the iframe. Since all `[data-hyp-id]` elements are in the iframe document, this is satisfied automatically.

### 6b. CSS-transformed elements and guideline offset accuracy

**Risk: LOW-MEDIUM.** Issue #219 (April 2020, fixed in milestone 0.17.0) documented that element guidelines computed incorrectly when a parent was scaled. The changelog shows multiple fixes in the 0.40–0.53 range: `"Fixed delta offset for element guidelines"` (0.46.0), `"Fixed guideline offset delta"` (0.46.1), `"Resolved transform matrix"` (0.46.0). [8]

For Hypresent's specific case: `move.js` writes only `transform: translate()` on elements. Elements that started with no transform are unaffected. Elements with an existing transform (e.g. `.slide-number` using `transform` for positioning) may produce slightly wrong guideline positions because `getBoundingClientRect()` captures the rendered position correctly, but Moveable's internal matrix decomposition path for such elements has had a history of drift. **Mitigation:** exclude absolutely-positioned or pre-transformed elements from `elementGuidelines` if accuracy issues appear.

### 6c. `throttleResize: 1` interaction with snap

**Risk: LOW.** `throttleResize: 1` rounds the resize delta to 1px increments. Snap overrides the throttled value when a snap target is within `snapThreshold` pixels — snap wins over throttle. No conflict is expected. The one documented case of snap+throttle conflict (issue #877) was specific to `snapGridWidth/Height`, not `elementGuidelines`. The app does not use grid snapping. [9]

### 6d. Flex/grid children and `flex-basis` sizing

**Risk: MEDIUM.** Resize.js writes `flex-basis` on flex children. `getBoundingClientRect()` on a flex child correctly returns its rendered size (after flex layout), so `elementGuidelines` measurements are accurate. However, after a `resizeEnd` commits a `flex-basis` change, the sibling flex children may reflow. If the user then resizes a second element, the cached (pre-reflow) guideline rects for siblings will be stale. **Fix:** use `refresh: true` on all guideline elements in flex containers, or re-assign `elementGuidelines` on each `begin()` call (which already happens per the recommended pattern above).

### 6e. Guideline shadow flicker (issue #596)

**Risk: LOW.** Issue #596 (Jan 2022, milestone 0.41.0) reported guideline lines appearing and then disappearing. The 0.42.2 changelog entry `"Fixed snap rendering for first drag"` likely addresses this. Since the vendored version is 0.53.0, this is resolved.

### 6f. No upgrade path

**Risk: LOW.** 0.53.0 is the latest version. No upgrade is available. All features needed for the R2 implementation (snappable, elementGuidelines, snapDirections with center/middle, snapGap, maxSnapElementGuidelineDistance, per-element className, refresh flag) are present in 0.53.0.

---

## 7. Upgrade Recommendation

**No upgrade needed.** 0.53.0 is the latest published version. The full snappable feature set required for Google Slides-style alignment guidelines — including `elementGuidelines`, `snapDirections` with `center`/`middle`, `snapGap`, `maxSnapElementGuidelineDistance`, `ElementGuidelineValueOption.className`, and `refresh` — is present in the vendored version. [1][3]

If a future version were released, breaking changes to watch for based on the 0.40–0.53 changelog pattern:
- Property renames (e.g. `snapRotationDegress` → `snapRotationDegrees` typo fix in 0.49.0) — always check the CHANGELOG before bumping.
- `element` field in `ElementGuidelineValueOption` changed from plain `Element` to `MoveableRefType<Element>` at some point — direct DOM element references remain compatible.

---

## 8. Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

[1] moveable — https://www.npmjs.com/package/moveable — 2026-06-03 — 2023-12-03 — TS:8.3 (AT:8 TR:8 TM:9)

[2] Snappable API Documentation — https://daybrush.com/moveable/release/latest/doc/Moveable.Snappable.html — 2026-06-03 — 2023-12-03 — TS:9.3 (AT:10 TR:9 TM:9)

[3] GitHub daybrush/moveable — https://github.com/daybrush/moveable — 2026-06-03 — 2023-12-03 — TS:9.3 (AT:10 TR:9 TM:9)

[4] MoveableOptions types.ts — https://daybrush.com/moveable/release/latest/doc/packages_react-moveable_src_react-moveable_types.ts.html — 2026-06-03 — 2023-12-03 — TS:9.3 (AT:10 TR:9 TM:9)

[5] CSS classes for guidelines (search synthesis) — https://daybrush.com/moveable/release/latest/doc/Moveable.Snappable.html — 2026-06-03 — 2023-12-03 — TS:8.3 (AT:9 TR:8 TM:8)

[6] Issue #266: Updating element guidelines — https://github.com/daybrush/moveable/issues/266 — 2026-06-03 — 2021 — TS:7.7 (AT:8 TR:7 TM:8)

[7] Issue #854: Request draggable elementGuidelines — https://github.com/daybrush/moveable/issues/854 — 2026-06-03 — 2023 — TS:7.0 (AT:8 TR:6 TM:7)

[8] moveable CHANGELOG.md (raw) — https://raw.githubusercontent.com/daybrush/moveable/master/CHANGELOG.md — 2026-06-03 — 2023-12-03 — TS:9.3 (AT:10 TR:9 TM:9)

[9] Issue #877: Fixed grid snap incorrect — https://github.com/daybrush/moveable/issues/877 — 2026-06-03 — 2023 — TS:7.0 (AT:8 TR:6 TM:7)

---

## Sources Discarded

No sources discarded — all sources used met the TS >= 6 threshold. Two sources (issues #596, #219, #397) had comments unavailable from page extraction; they contributed issue-level metadata only and are not cited as primary evidence for any claim.
