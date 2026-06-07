# PB-T9 — Builder JS: IntersectionObserver-gated srcdoc previews

## Probe Results

### 1. Syntax check (`node --check`)
- `html/hypresent/app/js/builder/previews.js` — **PASS** (exit 0)
- `html/hypresent/app/js/builder/browse-pane.js` — **PASS** (exit 0)

### 2. Export verification (grep)
- `export function initPreviews` — **FOUND** in previews.js
- `export function mountPreviews` — **FOUND** in previews.js

### 3. Configuration & renderable-unit verification (grep)
- `rootMargin` set to `'200px'` — **FOUND** in previews.js
- `MOUNT_CAP` constant — **FOUND** in previews.js (`const MOUNT_CAP = 24;`)
- `<style>` injection in renderable unit — **FOUND** in previews.js (`buildSrcdoc`)
- `runtime-main.js` — **NOT FOUND** (correct; previews never inject the runtime)

### 4. Eviction policy (RV2-5) — code review
Eviction logic in `evictIfNeeded()`:
- Filters candidates to mounted iframes **NOT** in `intersecting` set **AND** failing `isInViewport()` (`getBoundingClientRect` test).
- If no non-intersecting candidates exist, returns early → **transient cap raise** (no iframe blanked).
- Victim selection is **LRU among non-intersecting candidates only** (`lastUsed` timestamp comparison).
- **No FIFO/insertion-order fallback** exists in the code path.
- In-view iframes are **NEVER** eviction candidates.

**Conclusion: RV2-5 satisfied.**

## browse-pane.js contract extension
- `renderBrowse` signature extended from `(data, { onTag })` to `(data, { onTag, libraryPath })`.
- `mountPreviews(libraryPath, groupsContainer)` is called **after** all cards are appended, guarded by `if (libraryPath)`.
- This allows PB-T8/PB-T11's `builder-main.js` to opt-in by passing `libraryPath`; no crash if absent.

## git status --porcelain html/hypresent/app/js/builder/
```
?? html/hypresent/app/js/builder/browse-pane.js
?? html/hypresent/app/js/builder/previews.js
```

## Status: DONE
- `previews.js` created
- `browse-pane.js` extended
- All probes pass
- No product bugs blocking
