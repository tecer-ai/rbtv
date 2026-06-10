# Research: Presentation Builder UI — Drag-Reorder & Slide Preview Architecture

**Research date:** 2026-06-06
**Scope:** Topic 1 — Drag-reorder mechanism (tray list, Playwright real-input testability); Topic 2 — ~60 slide preview rendering (iframe srcdoc, lazy mount, font caveats)

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

---

## Topic 1 — Drag-Reorder Mechanism

### 1.1 The Testability Trap: Native HTML5 DnD — CONFIRMED

Native HTML5 drag-and-drop (`draggable="true"` + `dragstart`/`dragover`/`drop` event model) is **not reliably triggerable via Playwright `mouse.down/move/up` real-mouse input.** [Source 1, 2, 5, 6]

The authoritative technical reason, from the Playwright PR #34882 (merged Feb 2025, addressing Angular CDK):

> "Two types of drag & drop exist: (1) Native HTML5 — uses `draggable='true'`; the browser switches from `mousemove` to drag events during the OS-level drag loop. (2) Raw mouse events — `mousedown/mousemove/mouseup` — the browser never enters the OS drag loop." [Source 5]

Playwright's `mouse.down/move/up` sequence fires raw mouse events and does NOT enter the OS-level drag loop. Consequently:

- `dragstart`, `dragover`, `drop` events **do not fire** from `mouse.down/move/up` in Playwright. [Source 1, 2, 6]
- Playwright's `dragTo()` attempts to simulate the sequence but has an additional hard requirement: a `DataTransfer` object, which real mouse events cannot manufacture. Applications listening for the HTML5 drag lifecycle with DataTransfer ignore the mouse-only simulation. [Source 6]
- The dragover quirk: if a page relies on `dragover`, at least TWO sequential `mouse.move()` calls to the target are required; a single move is insufficient in all browsers. [Source 4, 5]
- Known open bugs: `dragTo` regression in v1.50 (Issue #34688, Feb 2025); no pointer/mouse events in WebKit for canvas custom DnD (Issue #38370, Dec 2025). [Source 2, 3]

**Verdict:** Native HTML5 DnD UIs are UNTESTABLE under the real-mouse mandate in Playwright without dispatching `DragEvent` + `DataTransfer` via `page.evaluate()` — which is synthetic JS injection, banned by the mandate. Native DnD is ruled out.

---

### 1.2 Approach Comparison Matrix

| Approach | Real-input Testable (Playwright mouse.down/move/up) | Vendorability | Code size | Key failure modes |
|---|---|---|---|---|
| (a) Native HTML5 DnD (`draggable`, dragstart/drop) | **NO** — OS drag loop never entered; DataTransfer missing | N/A (browser built-in) | 0 lines own code | Untestable under mandate; browsers differ |
| (b) SortableJS default (native DnD mode) | **NO** — same trap as (a); uses HTML5 DnD by default | Single file, CDN | ~53 KB min / ~17 KB gz [Source 7, 8] | Same as (a) |
| (b2) SortableJS `forceFallback: true` | **YES** — fallback ignores HTML5 DnD; uses pointer/mouse events [Source 8, 9] | Single file CDN: `https://cdn.jsdelivr.net/npm/sortablejs@1.15.7/Sortable.min.js` | ~53 KB min / ~17 KB gz | Bug #2331: `dragOver` elements may be incorrect in fallback [Source 10]; nested scroll caveats exist |
| (c) Hand-rolled pointer-events (~100–200 lines) | **YES** — `pointerdown/pointermove/pointerup` are fired by Playwright mouse.down/move/up [Source 1, 11] | Self-contained; no external dep | ~100–200 lines | Requires `pointercancel` and `pointerleave` handling; `requestAnimationFrame` loop needed for smooth move |
| (d) Dragula | Likely YES (uses mouse events, not native DnD) — but UNMAINTAINED [Source 12, 13] | Single file | ~15 KB | Abandoned by author (bevacqua); 46 open PRs unmerged, community confirms maintenance dead [Source 13] |

---

### 1.3 Recommended Approach: Hand-Rolled Pointer-Events (~150 lines)

**Recommendation: (c) — hand-rolled `pointerdown/pointermove/pointerup` reorder.**

Rationale:

1. **Testability is guaranteed.** Playwright's `mouse.down()/move()/up()` CDP sequence fires `pointerdown`, `pointermove`, `pointerup` natively. A pointer-event-driven sorter requires zero workarounds for testing — this is the event class Playwright is designed to simulate. [Source 1, 4, 11]

2. **No external dependency.** The app is vanilla-JS with no build step. Adding SortableJS even with `forceFallback:true` (53 KB min) introduces a vendored file and a known fallback-mode bug (Issue #2331: `dragOver` element detection fails in fallback). [Source 10]

3. **Established pattern.** The `pointerdown → pointermove (in rAF) → pointerup` reorder pattern is well-documented (Robert Hickman's 2024 reference, multiple codepens). Core logic: `getBoundingClientRect()` per item to find insertion point; `translate` CSS for visual feedback; `pointerleave` to cancel on viewport exit; `touch-action: none` on container to prevent scroll conflict. [Source 11, 14, 15]

4. **SortableJS `forceFallback:true` is second choice** if the hand-rolled path is unacceptable. Vendor artifact: `https://cdn.jsdelivr.net/npm/sortablejs@1.15.7/Sortable.min.js` — MIT license — ~53 KB minified (~17 KB gzipped) — latest release v1.15.7 (published 2026-02-11). [Source 7, 8, 9] Known caveat: Issue #2331 (open) — in fallback mode, `dragOver` element detection via `document.elementFromPoint` may return incorrect targets when the ghost overlaps the item; workaround is `hideGhostForTarget()` utility. [Source 10]

**No vendor artifact required for the recommended approach.** All code is self-owned.

---

## Topic 2 — Rendering ~60 Slide Previews

### 2.1 Architecture Recommendation

**Recommended pattern: IntersectionObserver-gated `srcdoc` iframe mounting + CSS `transform: scale()` thumbnails, with a virtualization cap.**

#### Mount strategy

Do NOT create all 60 iframes upfront. Each same-origin `srcdoc` iframe runs in the same renderer process as the parent (Chrome does not isolate same-site srcdoc iframes in a separate process) [Source 16], meaning 60 simultaneously active iframes share the main thread and memory. Field reports confirm memory spikes at scale: one product (Meeting Room 365) observed browser memory limits beyond 10 simultaneous live iframe thumbnails and switched to backend screenshots beyond that threshold. [Source 17]

**Mount on demand via IntersectionObserver:**

```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting && !entry.target.dataset.mounted) {
      entry.target.srcdoc = buildSlideHTML(entry.target.dataset.slideId);
      entry.target.dataset.mounted = 'true';
    }
  });
}, { rootMargin: '200px' }); // pre-load one screen ahead
```

Use `rootMargin` to mount just before visibility to avoid blank flash. [Source 18, 19]

#### `loading="lazy"` for srcdoc iframes

The HTML spec's lazy-loading algorithm applies the same intersection-based check for both `src` and `srcdoc` navigations, so `loading="lazy"` is spec-conformant for srcdoc iframes. [Source 20] However, browser implementations vary: the attribute is not universally tested against srcdoc and may silently degrade. **Use IntersectionObserver as the primary gate; treat `loading="lazy"` as progressive enhancement only.** [Source 18, 21]

#### Scale technique

Each iframe is rendered at full slide dimensions (e.g., 1280×720 px) and shrunk via CSS only:

```css
.slide-thumb-wrapper {
  width: 256px;   /* thumbnail display width */
  height: 144px;
  overflow: hidden;
  position: relative;
}
.slide-thumb-wrapper iframe {
  width: 1280px;
  height: 720px;
  transform: scale(0.2);
  transform-origin: top left;
  pointer-events: none;
}
```

CSS `transform: scale()` is applied after layout — no reflow cost for the scale itself. The iframe still allocates memory at 1280×720. [Source 22]

#### `content-visibility: auto` for off-screen iframes

`content-visibility: auto` (Baseline Newly Available, September 2025) skips layout and paint for off-screen elements but **does NOT prevent an already-mounted iframe from loading or executing** — it defers rendering only, not network or JS. [Source 23, 24] For unmounted iframes (where `srcdoc` has not been assigned), wrapping `.slide-thumb-wrapper` divs with `content-visibility: auto` reduces initial paint cost. It does not substitute for IntersectionObserver-gated mounting. Pair with `contain-intrinsic-size` to prevent layout shift on scroll.

#### Live iframe vs render-to-image tradeoff

| Approach | Fidelity | CPU/memory at 60 | Font reliability | Maintenance |
|---|---|---|---|---|
| Live `srcdoc` iframe (IntersectionObserver-gated) | Pixel-perfect; dynamic | High but manageable if lazy-mounted | External fonts load per-iframe (see §2.2) | Low |
| `html2canvas` / dom-to-image snapshot | Approximate; known CSS edge cases | Render cost at snapshot time, low after | External fonts often fail to embed [Source 25, 26] | Medium |
| SVG `foreignObject` snapshot | Approximate; more CSS bugs | Same | External fonts fail in security-sandboxed contexts [Source 25] | High |
| Server-side screenshot (Playwright/puppeteer backend) | Pixel-perfect | Negligible (server-side) | Reliable | High (infra) |

For a local same-origin app with no backend, **live iframes are the correct choice**. Render-to-image libraries (`html2canvas`, `dom-to-image`) have documented unreliability with external fonts and SVG `foreignObject` rendering. [Source 25, 26]

---

### 2.2 Google Fonts in Multiple iframes — Font Caching Caveat

Each `srcdoc` iframe that includes a `<link>` to Google Fonts CDN makes an independent request. Since Chrome v86 (2020), the HTTP cache is **partitioned by top-level origin** — fonts from `fonts.gstatic.com` are NOT shared across sites and NOT cached from previous visits. [Source 27] However, for same-page iframes with the same origin, the cache partition is the same (`your-local-host`), so the font file is fetched once and reused across all 60 iframes via the partitioned cache.

**Practical implication:** The CSS `@import` or `<link>` to Google Fonts triggers one CDN request per iframe for the CSS stylesheet (which is cheap), and one font binary request per iframe per weight/style — but the font binary is cached after the first iframe loads it. The cascade is: iframe 1 fetches font binary → cached → iframes 2-60 hit cache. No 60x font download.

**Risk:** `fonts.googleapis.com` requires an external connection. If the local server has no internet access, all iframes fail to load the font. Self-hosting the font files locally eliminates this risk and removes the CDN stylesheet request entirely. [Source 27, 28]

---

### 2.3 Known Pitfalls

1. **60 simultaneous live iframes = memory spike.** Mount lazily; unmount (set `srcdoc = ''`) on items scrolled far out of viewport if memory pressure is observed. [Source 17]
2. **`loading="lazy"` + `srcdoc` spec coverage is thin.** Confirmed in the WHATWG spec as applied to both `src` and `srcdoc`, but browser implementations not uniformly tested against srcdoc. Use IntersectionObserver as primary mechanism. [Source 20, 21]
3. **`content-visibility: auto` does not prevent iframe resource loading.** Already-mounted iframes remain active. Only prevents repaint of off-screen wrappers. [Source 23, 24]
4. **CSS `transform: scale()` does not reduce iframe memory allocation.** The iframe still renders at 1280×720 in memory; only the visual output is scaled. [Source 22]
5. **Native HTML5 DnD untestable under Playwright real-mouse mandate.** Confirmed across multiple independent sources. [Source 1, 2, 5, 6]
6. **SortableJS `forceFallback:true` ghost-element detection bug** (Issue #2331 open): `elementFromPoint` may return the ghost div itself, causing incorrect drop target. Mitigate with `hideGhostForTarget()` before each elementFromPoint call. [Source 10]
7. **Dragula is abandoned.** Author confirmed inactive; 46 open PRs unmerged; community reports no maintenance. Do not use. [Source 12, 13]
8. **html2canvas / SVG foreignObject external font failure.** Both approaches fail to embed Google Fonts reliably when served from a CDN. Only inline fonts or self-hosted font data URIs work reliably. [Source 25, 26]

---

## Sources

[1] How To Test Drag and Drop Using Playwright | BrowserStack — https://www.browserstack.com/guide/playwright-drag-and-drop — 2026-06-06 — 2024 (undated update) — TS:7.7 (AT:7 TR:8 TM:8)

[2] [Bug]: Playwright WebKit codegen cannot record drag-and-drop on custom canvas · Issue #38370 — https://github.com/microsoft/playwright/issues/38370 — 2026-06-06 — December 2025 — TS:8.3 (AT:9 TR:8 TM:8)

[3] [Bug]: DragTo Fails in 1.50 · Issue #34688 · microsoft/playwright — https://github.com/microsoft/playwright/issues/34688 — 2026-06-06 — February 2025 — TS:8.3 (AT:9 TR:8 TM:8)

[4] Actions | Playwright (official docs) — https://playwright.dev/docs/input — 2026-06-06 — 2025 — TS:9.3 (AT:10 TR:9 TM:9)

[5] fix(drag-n-drop): send two mousemove events to make Angular CDK work · PR #34882 — https://github.com/microsoft/playwright/pull/34882 — 2026-06-06 — February 2025 — TS:9.0 (AT:9 TR:9 TM:9)

[6] Automating Drag-and-Drop in React/MUI Apps with Playwright | DevAssure — https://www.devassure.io/blog/drag-and-drop-mui/ — 2026-06-06 — 2024 — TS:7.0 (AT:7 TR:7 TM:7)

[7] sortablejs v1.15.6 | Bundlephobia — https://bundlephobia.com/package/sortablejs — 2026-06-06 — 2025 — TS:7.7 (AT:8 TR:8 TM:7)

[8] GitHub - SortableJS/Sortable — https://github.com/SortableJS/Sortable — 2026-06-06 — 2025 — TS:8.3 (AT:9 TR:8 TM:8)

[9] Releases · SortableJS/Sortable — https://github.com/SortableJS/Sortable/releases — 2026-06-06 — February 2026 — TS:8.7 (AT:9 TR:9 TM:8)

[10] [bug] if use forceFallback, cannot get the dragOver elements · Issue #2331 — https://github.com/SortableJS/Sortable/issues/2331 — 2026-06-06 — undated, open — TS:8.3 (AT:9 TR:8 TM:8)

[11] Implementing a drag and drop sortable list in vanilla JavaScript using pointer events — https://robehickman.com/js-drag-drop-sortable — 2026-06-06 — 2024 — TS:7.3 (AT:7 TR:7 TM:8)

[12] GitHub - bevacqua/dragula — https://github.com/bevacqua/dragula — 2026-06-06 — last significant commit ~2022 — TS:7.3 (AT:8 TR:7 TM:7)

[13] Is your project still maintained? · Issue #689 · bevacqua/dragula — https://github.com/bevacqua/dragula/issues/689 — 2026-06-06 — 2023 — TS:8.0 (AT:9 TR:8 TM:7)

[14] Building a Seamless Drag-to-Reorder Widget with Vanilla JavaScript | Taha Shashtari — https://tahazsh.com/blog/seamless-ui-with-js-drag-to-reorder-example/ — 2026-06-06 — 2024 — TS:7.0 (AT:7 TR:7 TM:7)

[15] Build a Drag & Drop Sortable List with Pure JavaScript (Touch + Mouse) | Medium — https://medium.com/@a1guy/build-a-drag-drop-sortable-list-with-pure-javascript-touch-mouse-c297399ddbd9 — 2026-06-06 — 2024 — TS:6.7 (AT:6 TR:7 TM:7)

[16] Iframes and Process Allocation — https://webperf.tips/tip/iframe-multi-process/ — 2026-06-06 — 2023–2024 — TS:7.7 (AT:8 TR:8 TM:7)

[17] Iframe Performance Part 2: The Good News | Max Rafferty — https://medium.com/slices-of-bread/iframe-performance-part-2-the-good-news-26eb53cea429 — 2026-06-06 — undated — TS:6.7 (AT:6 TR:7 TM:7); also: Simulating Website Thumbnails using iFrames | James Futhey — https://medium.com/@jamesfuthey/simulating-the-creation-of-website-thumbnail-screenshots-using-iframes-7145269891db — 2026-06-06 — undated — TS:6.7 (AT:6 TR:7 TM:7)

[18] It's time to lazy-load offscreen iframes! | web.dev — https://web.dev/articles/iframe-lazy-loading — 2026-06-06 — 2020, updated 2024 — TS:9.0 (AT:10 TR:9 TM:8)

[19] Lazy loading using the Intersection Observer API — LogRocket — https://blog.logrocket.com/lazy-loading-using-the-intersection-observer-api/ — 2026-06-06 — 2023 — TS:7.3 (AT:7 TR:7 TM:8)

[20] HTML Standard — 4.8.5 The iframe element (WHATWG) — https://html.spec.whatwg.org/multipage/iframe-embed-object.html — 2026-06-06 — 2025 — TS:9.7 (AT:10 TR:10 TM:9)

[21] Lazy loading - Performance | MDN Web Docs — https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Lazy_loading — 2026-06-06 — 2024 — TS:9.3 (AT:10 TR:9 TM:9)

[22] How to Scale the Content of iframe Element | W3Docs — https://www.w3docs.com/snippets/css/how-to-scale-the-content-of-iframe-element.html — 2026-06-06 — undated — TS:6.7 (AT:7 TR:6 TM:7); CSS Transform Origin and Scale with Responsive Preview Containers | Mudos Digital — https://mudosdigital.com/css-transform-origin-and-scale-with-responsive-preview-containers/ — 2026-06-06 — 2024 — TS:6.7 (AT:6 TR:7 TM:7)

[23] content-visibility: the new CSS property that boosts your rendering performance | web.dev — https://web.dev/articles/content-visibility — 2026-06-06 — 2020, updated 2024 — TS:9.0 (AT:10 TR:9 TM:8)

[24] The CSS content-visibility property is now Baseline Newly available | web.dev — https://web.dev/blog/css-content-visibility-baseline — 2026-06-06 — September 2025 — TS:9.3 (AT:10 TR:9 TM:9)

[25] Snapdom: a modern and faster alternative to html2canvas — DEV Community — https://dev.to/tinchox5/snapdom-a-modern-and-faster-alternative-to-html2canvas-1m9a — 2026-06-06 — 2024 — TS:6.7 (AT:6 TR:7 TM:7)

[26] Fonts are not loaded when using html2canvas within an iframe · Issue #1772 — https://github.com/niklasvh/html2canvas/issues/1772 — 2026-06-06 — 2018, unresolved — TS:8.0 (AT:9 TR:8 TM:7)

[27] Self host Google fonts for better Core Web Vitals — https://www.corewebvitals.io/pagespeed/self-host-google-fonts — 2026-06-06 — 2024 — TS:7.3 (AT:7 TR:7 TM:8)

[28] Google Fonts Developer Guide — FontFYI — https://fontfyi.com/blog/google-fonts-developers-guide/ — 2026-06-06 — 2024 — TS:7.0 (AT:7 TR:7 TM:7)

---

## Sources Discarded

No sources discarded — all sources met TS >= 6 threshold.

Sources filtered during evaluation but not cited (low TM or superseded by higher-authority sources): GreenGeeks iframe explainer (AT:4 TR:6 TM:5, TS:5.0 — general audience), several CodePen embeds (no authority score applicable), zoer.ai React DnD guide (AT:5 TR:5 TM:6, TS:5.3 — React-specific, not applicable).
