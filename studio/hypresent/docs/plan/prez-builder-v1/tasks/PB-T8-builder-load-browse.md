You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate code by exact strings, NEVER line numbers.

# PB-T8 — Builder JS: library pick + load + validate + section-grouped browse + language filter

## Objective
Implement the library-load flow and the section-grouped browse pane with a language filter. Two new modules + wire them from `builder-main.js`.

## FILE ALLOWLIST
- ✚ create `html/hypresent/app/js/builder/library-load.js`
- ✚ create `html/hypresent/app/js/builder/browse-pane.js`
- ✎ modify `html/hypresent/app/js/builder/builder-main.js` (wire the pick/load/browse — this is the SOLE writer of builder-main.js in this wave step; later tasks PB-T10/PB-T11 also edit it, strictly after you, per the plan serialization)
- ✗ nothing else.

## The builder.html DOM contract (created by PB-T6 — these ids exist)
- `#pick-library-btn` (button), `#library-name` (span), `#builder-status` (span).
- `#browse-groups` (container for section groups), `#browse-empty` (empty-state div), `#lang-filter` (select with an `all` option).
- `#preset-select` (select), `#tray-list` (ol), `#assemble-btn` (button, disabled).
Vanilla ES modules, `camelCase` functions, no framework.

## The endpoints you call (created by PB-T7)
- `POST /api/dialog-folder` → `{path}` or `{cancelled:true}`.
- `POST /api/library-load {path}` → the engine `--catalog-data --json` envelope: `{ ok, errors, warnings, catalog_data: { name, default_lang, sections:[...], slides:[ {id,file,section,title,audience,lang,kind,summary,assets:[...],provenance} ], presets:[ {preset,slides:[...],lang,title,audience} ], extra_asset_root } }`.

## library-load.js — pick + load
Export an `async function pickAndLoadLibrary()` that:
1. `fetch('/api/dialog-folder', {method:'POST'})` → if `cancelled`, return null.
2. `fetch('/api/library-load', {POST, body: JSON.stringify({path})})` → parse the envelope.
3. If `envelope.ok === false` → return `{ ok:false, path, errors: envelope.errors }`.
4. Else return `{ ok:true, path, data: envelope.catalog_data, warnings: envelope.warnings }`.
Also export `async function loadLibraryByPath(path)` (same as steps 2–4) so tests can drive load without the dialog. Throw on a non-OK HTTP status (read `data.error`).

## browse-pane.js — render section groups + filter
Export `function renderBrowse(data, { onTag })` that, given `catalog_data`:
1. Clears `#browse-groups`; hides `#browse-empty`.
2. For each section in `data.sections` ORDER (convention-spec §6.4 / §2.2 — sections drive GUI grouping order), create a `.browse-group` with a label and the slides whose `section` equals it, in manifest order (the order they appear in `data.slides`).
3. Each slide → a `.slide-card` element (dataset.slideId = id) showing `title`, a `kind` badge (`ready`/`template`), `lang`, and an empty preview wrapper `.slide-thumb-wrapper` containing a NOT-yet-mounted `<iframe data-slide-id="{id}">` (previews are mounted by PB-T9 — leave the iframe srcdoc EMPTY here; just create the wrapper + iframe element). Clicking a card calls `onTag(slideRecord)` (build-spec S-B4.3 click-to-tag).
4. Populate `#lang-filter` options from the distinct `lang` values in `data.slides` (plus the existing `all`).
Export `function applyLangFilter(selectedLang)` implementing convention-spec §2.2 / §8.1 #14 filter semantics:
> A slide matches when its `lang` equals the selection OR its `id` has NO `.{lang}` suffix (language-neutral ids always pass). "all" shows everything.
Hide/show `.slide-card`s accordingly (toggle a `hidden` class or `style.display`). The filter is GUI-only; it never changes assembly.

A slide id "has no `.{lang}` suffix" means: the id does not end in `.pt`/`.en`/any 2-letter lang token matching a known lang. SIMPLEST correct rule: a card is language-neutral iff its `lang` value applies to all — but the contract keys on the ID suffix. Implement: neutral iff the id does NOT contain a `.` followed by exactly the card's own `lang` at the end (i.e. `id.endsWith('.'+lang)` === false means neutral). When filtering to `selectedLang`, show a card iff `selectedLang==='all'` OR `card.lang===selectedLang` OR `!id.endsWith('.'+card.lang)`.

## builder-main.js — wire it (additive to the PB-T6 stub)
Keep the existing stub's `DOMContentLoaded` mount log. ADD:
- A module-scoped `state = { libraryPath: null, data: null, tray: [] }` (the tray is filled by PB-T10; declare it here).
- Wire `#pick-library-btn` click → `pickAndLoadLibrary()`; on `{ok:true}` set `state.libraryPath`/`state.data`, set `#library-name` text to `data.name`, render the browse pane via `renderBrowse(data, { onTag })` (the `onTag` handler is added by PB-T10 — for now pass a placeholder `onTag = (rec) => console.info('tag', rec.id)`), populate `#preset-select` options from `data.presets` (PB-T10 wires the selection), surface any `warnings` in `#builder-status`. On `{ok:false}` show the invalid-library state (build-spec S-B11.2): set `#browse-groups` to a `.builder-invalid` block listing ALL of `errors` (the engine returns the FULL accumulated §8 violation list — S-A6.1a / RV2-4; render every entry, e.g. one `<li>` per error, not just `errors[0]`). 
- Wire `#lang-filter` change → `applyLangFilter(value)`.
Import from `./library-load.js` and `./browse-pane.js`.

## Acceptance criteria (self-verifiable)
1. `node --check` passes on all three files (`library-load.js`, `browse-pane.js`, `builder-main.js`).
2. The three files use only ES `import`/`export` (no `require`).
3. `browse-pane.js` exports `renderBrowse` and `applyLangFilter`; `library-load.js` exports `pickAndLoadLibrary` and `loadLibraryByPath` (grep the files for `export function renderBrowse`, `export function applyLangFilter`, `export async function pickAndLoadLibrary`, `export async function loadLibraryByPath`).

The full behavior (real load + grouping + filter) is verified by PB-T13's e2e suite — you cannot fully exercise the DOM here; the `node --check` + export probes are your gate.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/builder-load-browse-result.md`: the probe results + `git status --porcelain html/hypresent/app/js/builder/`.

DONE means: three files created/edited, probes pass, evidence written. Failure → BLOCKED + stop.
