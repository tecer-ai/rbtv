# PB-T8 Evidence — builder-load-browse

## Probe 1: `node --check`
- `library-load.js` — PASS
- `browse-pane.js` — PASS
- `builder-main.js` — PASS

## Probe 2: Export signatures (grep)
- `browse-pane.js: export function renderBrowse` — FOUND
- `browse-pane.js: export function applyLangFilter` — FOUND
- `library-load.js: export async function pickAndLoadLibrary` — FOUND
- `library-load.js: export async function loadLibraryByPath` — FOUND

## Probe 3: No `require()`
- `library-load.js` — none
- `browse-pane.js` — none
- `builder-main.js` — none

## git status --porcelain html/hypresent/app/js/builder/
```
?? html/hypresent/app/js/builder/browse-pane.js
?? html/hypresent/app/js/builder/builder-main.js
?? html/hypresent/app/js/builder/library-load.js
```

## Result
PASS — all acceptance criteria satisfied.
