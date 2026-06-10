# PB-T10 — Builder JS: compose tray + hand-rolled drag-reorder

## Evidence

### 1. `node --check` passes
```
$ node --check tray-sorter.js
$ node --check tray.js
$ node --check builder-main.js
```
All three exit 0 with no syntax errors.

### 2. `tray-sorter.js` required tokens (present)
- `pointerdown` — present
- `pointermove` — present
- `pointerup` — present
- `requestAnimationFrame` — present
- `getBoundingClientRect` — present
- `touchAction` — present
- `keydown` — present
- `Escape` — present
- `releasePointerCapture` — present

### 3. `tray-sorter.js` forbidden tokens (absent)
Grep for `draggable`, `dragstart`, `dragover`, `DataTransfer`:
```
NONE FOUND — PASS
```

### 4. Export checks
- `tray.js` exports `createTray` — PASS
- `tray-sorter.js` exports `attachSorter` — PASS

### 5. `git status --porcelain html/hypresent/app/js/builder/`
```
?? html/hypresent/app/js/builder/builder-main.js
?? html/hypresent/app/js/builder/tray-sorter.js
?? html/hypresent/app/js/builder/tray.js
```

## Summary
- `tray.js` created with `createTray` factory (model, add, remove, setFromPreset, render, getOrder).
- `tray-sorter.js` created with hand-rolled `attachSorter` using pointer events, rAF, getBoundingClientRect, and Escape-cancel with pre-drag order restore.
- `builder-main.js` wired: tray construction, `onTag` → `tray.add`, preset select → `tray.setFromPreset`, assemble-btn enable/disable via `onChange`, `state.tray` stored for PB-T11.
