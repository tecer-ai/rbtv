---
task_id: T1-slide-expand
workspace: 3-resources/tools/rbtv
work_dir: html/hypresent
branch: master
allowlist:
  create:
    - app/js/builder/slide-stage.js
    - tests/e2e/test_pb7_slide_expand.py
  modify:
    - app/js/builder/browse-pane.js
    - app/js/builder/builder-main.js
    - app/css/builder.css
  delete: []
---

# T1 — Slide expand (full-size in-place inspector)

## Goal

Add an "expand" affordance to each slide card in the hypresent **builder** browse grid. Hovering a card shows a small round magnifier button in the thumbnail's top-right corner; clicking it opens that slide **full-size** over the center browse area, with Close / Prev / Next / Add controls. The left library rail and right presentation tray stay visible. This is read-only inspection — it never edits slide content.

All work is in `html/hypresent` (the work dir). Run commands from there. Do NOT touch any file outside the allowlist. Do NOT create files at the repo root (write evidence/scratch under `docs/plan/slide-expand/` if needed).

## Acceptance criteria (owner-observable — these are the done contract)

1. **Expand affordance** — Hovering a `.slide-card` reveals a round magnifier button (`.s-expand`) in the thumbnail's top-right corner. Clicking it opens the expanded view for that slide and does **NOT** add the slide to the tray (tray count unchanged).
2. **Full-size view** — The expanded slide renders at full fidelity (same srcdoc the thumbnails use) sized to fit the center column. The `.lib-rail` (left) and `.builder-tray` (right) remain visible.
3. **Close returns intact** — A Close button (✕) and the `Esc` key close the view and return to the grid at the **same scroll position** it was opened from.
4. **Prev/Next** — `‹ Prev` / `Next ›` buttons and the `←` / `→` keys step through the currently **visible** slides (`.slide-card:not(.hidden)`) in DOM order. Filtered-out (hidden) slides are skipped. At the first visible slide Prev is disabled; at the last, Next is disabled (stop at ends — NO wrap).
5. **Add from expanded view** — An `Add to presentation` button adds the on-screen slide to the tray (tray count rises, the slide's grid badge appears). If the slide is already in the tray, the button shows an `Added` state and does NOT add a duplicate.

## Self-verifiable checks (run these yourself before returning)

- `node --check app/js/builder/slide-stage.js && node --check app/js/builder/browse-pane.js && node --check app/js/builder/builder-main.js` → all EXIT 0.
- `python -m pytest tests/e2e/test_pb7_slide_expand.py -q` → passes (the e2e test you add; see §E2E).

---

## Current code — exact excerpts to anchor edits

### A. `app/js/builder/browse-pane.js`

Current function signature:
```js
export function renderBrowse(data, { onTag, libraryPath }) {
```
Change it to also accept an `onExpand` callback:
```js
export function renderBrowse(data, { onTag, libraryPath, onExpand }) {
```

Current per-card block that builds the thumbnail and the existing add pill (locate by this exact text):
```js
      const thumbWrapper = document.createElement('div');
      thumbWrapper.className = 'slide-thumb-wrapper';

      const iframe = document.createElement('iframe');
      iframe.dataset.slideId = slide.id;
      iframe.setAttribute('tabindex', '-1');
      // srcdoc intentionally empty — previews mounted lazily below
      thumbWrapper.appendChild(iframe);

      const addPill = document.createElement('span');
      addPill.className = 's-add';
      addPill.textContent = '+ Add';
      thumbWrapper.appendChild(addPill);

      card.appendChild(thumbWrapper);
```
Add a magnifier button to `thumbWrapper` (after the iframe, before or after `addPill`). It MUST be a real `<button>` so it is focusable/clickable, and its click MUST `stopPropagation()` so the card's add-on-click (below) does not fire:
```js
      const expandBtn = document.createElement('button');
      expandBtn.type = 'button';
      expandBtn.className = 's-expand';
      expandBtn.setAttribute('aria-label', 'Expand slide');
      expandBtn.title = 'Expand';
      // magnifier glyph (inline SVG)
      expandBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>';
      expandBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (typeof onExpand === 'function') onExpand(slide.id);
      });
      thumbWrapper.appendChild(expandBtn);
```

Current card click handler (do NOT change — shown so you keep its behavior; the expand button must not trigger it):
```js
      card.addEventListener('click', () => onTag(slide));
```

### B. `app/css/builder.css`

Current existing add-pill rules (mirror these for `.s-expand`; locate by this exact text):
```css
.s-add {
  position: absolute; right: 10px; bottom: 10px; z-index: 3;
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px 6px; border-radius: 999px;
  background: var(--ink); color: var(--paper); font-size: 12.5px; font-weight: 700;
  opacity: 0; transform: translateY(4px);
  transition: opacity .15s ease, transform .15s ease;
  pointer-events: none;
}
.slide-card:hover .s-add { opacity: 1; transform: none; }
.slide-card.is-added .s-add { display: none; }
```
Add `.s-expand` rules immediately after the `.s-add` block. The expand button sits top-right, appears on hover, but UNLIKE `.s-add` it must be clickable (`pointer-events: auto`):
```css
.s-expand {
  position: absolute; top: 8px; right: 8px; z-index: 3;
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; padding: 0; border: 0;
  border-radius: 999px; cursor: pointer;
  background: var(--ink); color: var(--paper);
  opacity: 0; transform: translateY(-4px);
  transition: opacity .15s ease, transform .15s ease, background .15s ease;
  pointer-events: none;
}
.s-expand svg { width: 16px; height: 16px; }
.slide-card:hover .s-expand { opacity: 1; transform: none; pointer-events: auto; }
.s-expand:hover { background: var(--accent); }
.s-expand:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```
Then add the expanded-view (stage) styles. The stage is an absolutely-positioned overlay that fills the `#builder-browse` scroll container and sits ON TOP of the grid (grid stays mounted). Use the design tokens already in this file (`--paper`, `--ink`, `--line`, `--accent`, `--white`, `--shadow-lift`, `--r-card`, `--ink-mut`). Append at the end of the file:
```css
/* ════════════ SLIDE STAGE (expanded view) ════════════ */
.slide-stage {
  position: absolute; inset: 0; z-index: 20;
  display: none; flex-direction: column;
  background: var(--paper);
}
.slide-stage.is-open { display: flex; }
.slide-stage-bar {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; border-bottom: 1px solid var(--line);
  background: var(--paper);
}
.slide-stage-bar .ss-title {
  font-size: 14px; font-weight: 600; color: var(--ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1;
}
.slide-stage-bar button {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: 999px; cursor: pointer;
  font-size: 13px; font-weight: 600; border: 1px solid var(--line);
  background: var(--white); color: var(--ink);
}
.slide-stage-bar button:hover:not(:disabled) { border-color: var(--ink-mut); }
.slide-stage-bar button:disabled { opacity: .4; cursor: default; }
.slide-stage-bar .ss-add { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.slide-stage-bar .ss-add.is-added { background: var(--accent); border-color: var(--accent); }
.slide-stage-bar .ss-close { margin-left: 4px; }
.slide-stage-body {
  flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center;
  padding: 24px; overflow: auto;
}
.slide-stage-frame {
  width: 1280px; height: 720px; max-width: 100%;
  aspect-ratio: 16 / 9; border: 1px solid var(--line); border-radius: var(--r-card);
  box-shadow: var(--shadow-lift); background: var(--white); overflow: hidden;
  container-type: inline-size;
}
.slide-stage-frame iframe {
  width: 1280px; height: 720px; border: 0; background: var(--white);
  transform: scale(calc(100cqw / 1280px)); transform-origin: top left;
}
.slide-stage-error {
  color: var(--ink-mut); font-size: 14px; padding: 40px; text-align: center;
}
```
NOTE: `.builder-browse` / `#builder-browse` must be a positioned ancestor for `inset:0` to anchor to it. Check the existing `.builder-browse` rule near the top of the TRAY/center section; if it lacks `position`, add `position: relative;` to it (surgical — only that one property).

### C. `app/js/builder/previews.js` (no edit — reuse this export)

Already exported, use as-is:
```js
export function getSlideSrcdoc(libraryPath, slideId) // returns Promise<srcdocString>
```

### D. `app/js/builder/builder-main.js`

Current import line (locate by exact text):
```js
import { renderBrowse, applyLangFilter, markTrayState } from './browse-pane.js';
```

Current tray creation (gives you `tray.add`, `tray.has`, `tray.getOrder`; `markTrayState` updates badges):
```js
  const tray = createTray({
    listEl: trayList,
    onChange: () => {
      const order = tray.getOrder();
      if (assembleBtn) assembleBtn.disabled = order.length === 0;
      if (trayCount) trayCount.textContent = order.length + (order.length === 1 ? ' slide' : ' slides');
      markTrayState(order);
    }
  });
  state.tray = tray;
```

Current browse render call inside `handlePickLibrary` (locate by exact text):
```js
    // browse + sections nav (cards toggle add/remove on click)
    const onTag = (rec) => {
      if (tray.has(rec.id)) tray.remove(rec.id);
      else tray.add(rec);
    };
    renderBrowse(result.data, { onTag, libraryPath: result.path });
```

Required edits in `builder-main.js`:
1. Import the stage factory at top:
   ```js
   import { createSlideStage } from './slide-stage.js';
   ```
2. Create ONE stage instance (after `state.slideLookup` is set, since it needs slide records). The simplest place: inside `handlePickLibrary`, just before the `renderBrowse(...)` call, create/refresh the stage and pass `onExpand`. Because library can change, store the stage on `state` and close it on each new pick. Wire it like:
   ```js
   // close any open stage from a previous library, then (re)create
   if (state.stage) state.stage.close();
   state.stage = createSlideStage({
     container: browsePane,                 // #builder-browse element (already grabbed above as browsePane)
     getLibraryPath: () => state.libraryPath,
     getSlideRecord: (id) => state.slideLookup ? state.slideLookup.get(id) : null,
     onAdd: (id) => {
       const rec = state.slideLookup ? state.slideLookup.get(id) : null;
       if (rec && !tray.has(id)) tray.add(rec);   // tray.onChange already calls markTrayState
     },
     isAdded: (id) => tray.has(id),
   });
   const onExpand = (id) => state.stage.open(id);
   ```
   Then update the render call to pass it:
   ```js
   renderBrowse(result.data, { onTag, libraryPath: result.path, onExpand });
   ```
   (`browsePane` is already defined near the top of the DOMContentLoaded handler as `const browsePane = document.getElementById('builder-browse');`.)

### E. `app/js/builder/slide-stage.js` (CREATE — new module)

Create the module exporting `createSlideStage(opts) => { open(slideId), close() }`. Requirements:

- **DOM:** On first use, build the stage element once and append it INTO `container` (`#builder-browse`), so the CSS `inset:0` overlay covers the grid. Structure:
  - `.slide-stage` (root, hidden until open)
    - `.slide-stage-bar` containing: Prev button (`.ss-prev`, label `‹ Prev`), Next button (`.ss-next`, label `Next ›`), a flexible `.ss-title` (set to the slide's title or id), an `Add to presentation` button (`.ss-add`), and a Close button (`.ss-close`, label `✕` / aria-label "Close").
    - `.slide-stage-body` containing `.slide-stage-frame` with a single `<iframe>` (the full-size render target).
- **open(slideId):**
  - Compute the visible-id list FRESH each open: `Array.from(container.querySelectorAll('.slide-card:not(.hidden)')).map(c => c.dataset.slideId)`. Track the current index within it.
  - Render the slide: `getSlideSrcdoc(getLibraryPath(), slideId)` → set `iframe.srcdoc`. On rejection, show `.slide-stage-error` text "Couldn't load this slide." in the body (keep the bar usable).
  - Set `.ss-title` to the slide record's `title` (fallback to id) via `getSlideRecord(id)`.
  - Update button states: Prev disabled when current index ≤ 0; Next disabled when current index ≥ last; Add button shows `Added` + `.is-added` class + disabled when `isAdded(id)` is true, else label `Add to presentation` enabled.
  - Add `is-open` class. Remember the originating card's scroll position is preserved automatically because the grid is never unmounted — do NOT scroll the container.
  - If already open, just swap to the new slide (re-render, recompute index from the visible list) — never stack.
- **Navigation:** Prev/Next move the current index by ∓1 within the visible-id list and re-render (same logic as open, minus rebuilding the list). Re-disable arrows at the ends.
- **Add button:** calls `onAdd(currentId)`, then refreshes the Add button state to `Added`.
- **Keyboard:** while open, `Esc` → close; `ArrowLeft` → Prev (if enabled); `ArrowRight` → Next (if enabled). Attach the keydown listener to `document` on open and remove it on close (do NOT leak listeners across opens). Guard arrows so they don't fire when a text input is focused.
- **close():** remove `is-open`, clear `iframe.srcdoc` (free the render), remove the keydown listener. Return focus to the card that was expanded if it still exists (`container.querySelector('.slide-card[data-slide-id="..."]')`), else no-op.
- **Add-state freshness:** the Add button reflects `isAdded(id)` at open/navigate time. (If the user adds via the grid while the stage is closed, the next open recomputes it — sufficient.)

Keep the module self-contained: import `getSlideSrcdoc` from `./previews.js`. No other deps.

---

## E2E test — `tests/e2e/test_pb7_slide_expand.py` (CREATE)

Mirror the existing builder e2e pattern (see `test_pb6_states.py` and `builder_helpers.py`). Use a UNIQUE port `8807`. Skeleton to follow:

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H
import builder_helpers as B

PORT = 8807


class PB7SlideExpandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop(); H.stop_server(cls.proc)

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 720})

    def tearDown(self):
        self.page.close()

    def _open_first(self):
        self.page.goto(self.base + "/app/builder.html")
        B.pick_library_ui(self.page, self.base, B.e2e_lib_path())
        ids = self.page.eval_on_selector_all(".slide-card", "els=>els.map(e=>e.dataset.slideId)")
        self.assertTrue(len(ids) > 0)
        # hover then click the expand button on the first card
        card = self.page.locator(f".slide-card[data-slide-id='{ids[0]}']")
        card.hover()
        card.locator(".s-expand").click()
        self.page.wait_for_selector(".slide-stage.is-open", timeout=5000)
        return ids
```

Add at least these test methods (use `wait_for_*`, never bare sleeps where avoidable):
- `test_expand_opens_without_adding`: open first card's expand → `.slide-stage.is-open` visible AND `.tray-row` count is still 0.
- `test_close_returns`: open → press `Escape` → `.slide-stage` no longer has `is-open`.
- `test_next_prev`: open first → click `.ss-next` → assert the stage iframe/title changed to the 2nd visible slide; click `.ss-prev` → back to first. Assert `.ss-prev` is disabled on the first slide.
- `test_add_from_stage`: open → click `.ss-add` → assert `.tray-row` count becomes 1 AND the `.ss-add` button shows the added state (`is-added` class or text `Added`).

(If a selector for the originating slide's identity in the bar is needed, set a `data-slide-id` attribute on `.slide-stage` or `.ss-title` in `slide-stage.js` so the test can assert the current slide — your choice, just make it assertable.)

---

## Return contract

Return these five fields exactly:
- `status`: DONE / BLOCKED
- `landed`: files changed + commit hash (commit on `master` with a clear message after self-checks pass)
- `validation`: the `node --check` and `pytest` commands you ran, each with EXIT code and WALL_MS; list any skipped check with the reason
- `concerns`: anything you are unsure about
- `open_questions`: the precise blocker if you halt

If anything in this task is ambiguous or an anchor excerpt does not match the file, HALT and report it in `open_questions` — do NOT guess.
