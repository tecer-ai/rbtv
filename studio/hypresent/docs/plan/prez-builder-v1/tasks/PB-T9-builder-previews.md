You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate code by exact strings, NEVER line numbers.

# PB-T9 — Builder JS: IntersectionObserver-gated srcdoc previews

## Objective
Implement lazy slide previews (D5-S4): IntersectionObserver mounts a card's `srcdoc` iframe near view, with a fixed virtual viewport + CSS scale + a mounted-count cap. Previews NEVER inject the editor runtime.

## FILE ALLOWLIST
- ✚ create `html/hypresent/app/js/builder/previews.js`
- ✎ modify `html/hypresent/app/js/builder/browse-pane.js` (call `mountPreviews` after rendering cards; this edit is strictly after PB-T8's creation of browse-pane.js — plan serialization)
- ✗ nothing else.

## Contract (D5-S4 + research-01-ui §2.1, quotes you implement)
> D5-S4: browse-pane previews = IO-gated srcdoc iframes (rootMargin ~200px) + transform:scale at a fixed virtual viewport; mounted-count cap; theme.css injected into each srcdoc per the convention's renderable unit; previews NEVER inject the editor runtime.
> research-01-ui §2.1: "Do NOT create all iframes upfront ... Mount on demand via IntersectionObserver ... rootMargin: '200px' to pre-load one screen ahead." Memory ceiling ~10 live; cap mounted iframes.

The renderable unit (build-spec S-B5.2):
```
<!DOCTYPE html><html><head><style>{theme.css}</style></head><body>{fragment HTML}</body></html>
```
`theme.css` and each `slides/{id}.html` are fetched from the library via `POST /api/library-asset {path, name}` (PB-T7): `name="theme.css"` and `name="slides/{id}.html"`. The response is `{content}`.

## previews.js
Export `function initPreviews(libraryPath)` that:
- Fetches `theme.css` ONCE via `/api/library-asset {path:libraryPath, name:"theme.css"}` and caches the content (one theme per library).
- Returns/sets up an IntersectionObserver with `{ rootMargin: '200px' }` whose callback, for each intersecting `.slide-thumb-wrapper iframe[data-slide-id]` not yet mounted (`!iframe.dataset.mounted`), fetches the fragment via `/api/library-asset {path, name:"slides/"+id+".html"}` and sets `iframe.srcdoc = buildSrcdoc(theme, fragmentHTML)`, then `iframe.dataset.mounted='true'`.
Export `function mountPreviews(libraryPath, container)` that fetches the theme (via initPreviews) and observes every `.slide-thumb-wrapper iframe` under `container`.
Implement `buildSrcdoc(theme, fragment)` = the renderable-unit string above. The srcdoc MUST NOT contain `/runtime/js/runtime-main.js` (previews never inject the runtime — build-spec S-B5.2).

### Mounted-count cap (build-spec S-B5.4 / research-01-ui §2.1 / RV2-5)
Track mounted iframes in a Map/Set carrying a last-used marker (update the marker each time an iframe (re)intersects or mounts). Constant `const MOUNT_CAP = 24;`. When mounting would exceed `MOUNT_CAP`, evict by THIS policy — NEVER blank an in-view iframe:
- Eviction candidates = ONLY mounted iframes NOT currently intersecting the viewport. Determine "currently intersecting" from the latest IntersectionObserver entries (track `isIntersecting` per iframe in the observer callback) OR a `getBoundingClientRect()` in-viewport test at eviction time. An intersecting (in-view) iframe is NEVER an eviction candidate.
- Among the non-intersecting candidates, evict the LEAST-RECENTLY-USED (oldest last-used marker): set its `srcdoc=''`, delete `dataset.mounted`, remove it from the tracking structure. THEN mount the new iframe.
- If EVERY mounted iframe is currently intersecting at the cap (no non-intersecting candidate), do NOT blank any — mount the new iframe anyway (the cap raises TRANSIENTLY). It re-tightens on the next eviction pass once an iframe scrolls out of view.
- There is NO FIFO/oldest-in-insertion-order fallback — it could evict an in-view iframe (a visible-preview regression) and is forbidden (RV2-5). Eviction is ALWAYS "LRU among non-intersecting, never in-view".

### Scale (build-spec S-B5.3)
The CSS already sets the iframe to 1280×720 with `transform: scale(0.2)` + `overflow:hidden` wrapper + `pointer-events:none` (from PB-T6's builder.css `.slide-thumb-wrapper` rules). Do NOT re-set scale in JS — rely on the CSS. Just mount the srcdoc.

## browse-pane.js — call previews after rendering
In `renderBrowse` (created by PB-T8), AFTER appending all cards, import and call `mountPreviews(libraryPath, document.getElementById('browse-groups'))`. `renderBrowse` must accept the `libraryPath` — if PB-T8's signature is `renderBrowse(data, {onTag})`, extend it to `renderBrowse(data, {onTag, libraryPath})` and have `builder-main.js` pass it (note this contract extension in evidence so the orchestrator can confirm PB-T8's caller matches; do NOT edit builder-main.js here — that is PB-T8's/PB-T11's file. If the caller does not yet pass libraryPath, guard: only call mountPreviews when libraryPath is provided).

## Acceptance criteria (self-verifiable)
1. `node --check html/hypresent/app/js/builder/previews.js` and `node --check html/hypresent/app/js/builder/browse-pane.js` exit 0.
2. `previews.js` exports `initPreviews` and `mountPreviews` (grep `export function initPreviews`, `export function mountPreviews`).
3. `previews.js` contains `rootMargin` set to `'200px'` and a `MOUNT_CAP` constant and the renderable-unit `<style>` injection; it does NOT contain the string `runtime-main.js`.
4. Eviction never targets an in-view iframe (RV2-5): the eviction code path filters to NON-intersecting iframes before choosing a victim (the code tracks `isIntersecting`/in-viewport per iframe and selects the least-recently-used among non-intersecting only). There is NO unconditional oldest-in-insertion-order (FIFO) eviction. (Confirm by reading the eviction branch; the behavioral proof is PB-T13's no-in-view-blanking test.)

Full preview behavior (IO mount, cap, no-runtime) is verified by PB-T13's e2e suite.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/builder-previews-result.md`: the probe results + `git status --porcelain html/hypresent/app/js/builder/`.

DONE means: previews.js created, browse-pane.js extended, probes pass, evidence written. Failure → BLOCKED + stop.
