You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate code by exact strings, NEVER line numbers.

# PB-T10 — Builder JS: compose tray (tag/remove/preset) + hand-rolled drag-reorder

## Objective
Implement the compose tray (click-to-tag append, remove, preset preload) and a HAND-ROLLED pointer-events drag-reorder sorter (D4-S4 — NO vendored DnD lib; testable under the real-mouse mandate by construction).

## FILE ALLOWLIST
- ✚ create `html/hypresent/app/js/builder/tray.js`
- ✚ create `html/hypresent/app/js/builder/tray-sorter.js`
- ✎ modify `html/hypresent/app/js/builder/builder-main.js` (wire tag handler + preset select; strictly AFTER PB-T8's edit — plan serialization)
- ✗ nothing else.

## DOM contract (from PB-T6)
- `#tray-list` (an `<ol>`), `#preset-select` (a `<select>`), `#assemble-btn` (button).
- Each tray row should be an `<li class="tray-row" data-slide-id="{id}">` with a position number, the title, a `kind` badge, and a remove button `.tray-remove`.

## Contract (D4-S4 + research-01-ui §1.3, quotes you implement)
> D4-S4: tray drag-reorder = HAND-ROLLED pointer-events sorter (~150 lines, pointerdown/move/up + rAF + getBoundingClientRect insertion) — no vendored lib.
> research-01-ui §1.1: native HTML5 DnD (`draggable=true` + dragstart/drop) is UNTESTABLE under Playwright real-mouse input (the OS drag loop is never entered, no DataTransfer). Pointer events (`pointerdown/pointermove/pointerup`) ARE fired by Playwright `mouse.down/move/up`.
> research-01-ui §1.3: `getBoundingClientRect()` per item to find insertion point; `translate`/transform for visual feedback; `pointerleave`/`pointercancel` to cancel; `touch-action:none` on the container; the move loop in `requestAnimationFrame`.

## tray.js — the tray model + render
Export a `createTray({ listEl, onChange })` factory returning an object with:
- `model` — an array of `{id, title, kind, lang}` (the assembly order ground truth — convention-spec §4.2 "slides is ground truth").
- `add(rec)` — append once (if `rec.id` already in model, no-op; build-spec S-B6.1 append-once); re-render; call `onChange`.
- `remove(id)` — drop the row; re-render + renumber; `onChange`.
- `setFromPreset(slideIds, slideLookup)` — replace the model with the preset's ids in order (build-spec S-B7.1), resolving each id to `{id,title,kind,lang}` via `slideLookup` (a map from `catalog_data.slides`); re-render; `onChange`.
- `render()` — rebuild `#tray-list` as ordered `<li class="tray-row" data-slide-id>` rows with position number + title + kind badge + a `.tray-remove` button (wired to `remove(id)`); then call `attachSorter` from tray-sorter.js so rows are draggable; renumber positions 1..N.
- `getOrder()` — return the model's id array (for assembly).
`onChange` lets builder-main.js enable/disable `#assemble-btn` (enabled iff model non-empty — build-spec S-B11.3) and update the destination default.

## tray-sorter.js — the hand-rolled pointer sorter (~150 lines)
Export `function attachSorter(listEl, { onReorder })` that makes the `<li>` children reorderable via pointer events:
- Set `listEl.style.touchAction = 'none'` (research-01-ui §1.3).
- On `pointerdown` on a row (not on the `.tray-remove` button): capture the pointer (`row.setPointerCapture(e.pointerId)`), record the dragged row + its start index AND a snapshot of the pre-drag DOM order (the ordered `data-slide-id` list — needed for Escape restore), add a `.tray-drag-ghost` class for visual feedback, and ADD a transient `keydown` listener (on `document` or `window`) for Escape-cancel (build-spec S-B8.1a). Wire the `keydown` ONLY here (while a drag is active), so it never intercepts Escape outside a drag.
- On `pointermove` (inside a `requestAnimationFrame` throttle): compute the insertion index by comparing the pointer Y against each sibling row's `getBoundingClientRect()` midpoint; if the target index differs from the current DOM position, move the dragged `<li>` (insertBefore) to that slot. Use a `translate` transform on the dragged row for feedback (research-01-ui §1.3).
- On `pointerup` / `pointercancel` / `pointerleave`: release capture, remove the ghost class + transform, REMOVE the transient `keydown` listener, and call `onReorder(newOrderIds)` where `newOrderIds` is the current DOM order of `data-slide-id`s. The tray model is then re-synced to the DOM order (build-spec S-B8.3).
- ESCAPE cancels an active drag (build-spec S-B8.1a / RV2-6): the transient `keydown` handler, on `event.key === "Escape"`, RESTORES the pre-drag DOM order (reinsert the rows in the snapshot order so the dragged row returns to its start index), releases pointer capture (`releasePointerCapture(pointerId)`), removes the ghost class + transform, removes BOTH the transient `keydown` and any in-flight move handling, and does NOT call `onReorder` (the model is left at its pre-drag order — no model mutation on cancel). Escape MUST win even if a `pointerup` would otherwise fire: once cancelled, the drag is over and the order stays the pre-drag order.
- NO `draggable="true"`, NO `dragstart`/`dragover`/`drop`, NO `DataTransfer` ANYWHERE (build-spec S-B8.2). Only `pointer*` + `keydown` (Escape) + `requestAnimationFrame` + `getBoundingClientRect`.

`onReorder` updates `tray.model` to match the new DOM order (the factory wires this when it calls `attachSorter`).

## builder-main.js — wire tag + preset (additive, after PB-T8's edit)
- Construct the tray: `const tray = createTray({ listEl: document.getElementById('tray-list'), onChange: () => { document.getElementById('assemble-btn').disabled = tray.getOrder().length === 0; } });`
- Replace PB-T8's placeholder `onTag` with `const onTag = (rec) => tray.add(rec);` and pass it to `renderBrowse`.
- Build a `slideLookup` map from `state.data.slides` (id → record). Wire `#preset-select` change: find the chosen preset in `state.data.presets`, call `tray.setFromPreset(preset.slides, slideLookup)`, and set `#deck-filename` default + the document lang default from `preset.lang`/`preset.title` (build-spec S-B7.1). Do NOT mutate the preset (the builder never edits presets — convention-spec §3.3).
- Store `tray` on the module state so PB-T11 (assemble) can read `tray.getOrder()`.

## Acceptance criteria (self-verifiable)
1. `node --check` passes on `tray.js`, `tray-sorter.js`, `builder-main.js`.
2. `tray-sorter.js` contains `pointerdown`, `pointermove`, `pointerup`, `requestAnimationFrame`, `getBoundingClientRect`, `touchAction`, AND a `keydown`/`Escape` cancel handler with `releasePointerCapture` (RV2-6 — grep `keydown`, `Escape`, `releasePointerCapture`); it does NOT contain `draggable`, `dragstart`, `dragover`, `DataTransfer` (grep — these MUST be absent, the whole point of D4-S4).
3. `tray.js` exports `createTray`; `tray-sorter.js` exports `attachSorter`.

Full drag behavior (real mouse reorder, model changes) is verified by PB-T14's e2e suite with `page.mouse.down/move/up`.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/builder-tray-result.md`: the probe results (INCLUDING the grep confirming no `draggable`/`dragstart`/`DataTransfer`) + `git status --porcelain html/hypresent/app/js/builder/`.

DONE means: two files created, builder-main.js wired, probes pass (esp. the no-native-DnD grep), evidence written. Failure → BLOCKED + stop.
