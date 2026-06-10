# Spec — Copy / paste components

## Goal

The owner copies a selected component (`Ctrl+C`), then pastes it: `Ctrl+V` drops a floating copy under the cursor without disturbing the slide's layout; `Ctrl+Shift+V` inserts a copy into the row/grid so the layout rebalances (a fixed grid falls back to a floating copy). Copying a whole slide duplicates it. One Undo removes any paste, and saving still produces a clean, re-openable file.

## Context Snapshot

All runtime modules in `runtime/js/`. Exact anchors live in the backing tasks (`../phase-3/p3-1.task.md` … `p3-4.task.md`).

- **`element-registry.js`**: `tag()` assigns fresh `data-hyp-id` to untagged elements (a tree walk); `stripIds(clone)` removes ids from a clone; `roleOf(el)` → `'flex-child'|'grid-child'|'absolute'|'block'`; `idOf(el)`, `byId(id)`.
- **`commands.js`**: `deleteElement(hypId)` captures parent (by hyp-id, or the live body node), the next-sibling hyp-id, and the live node ref; `do()` removes the node, `undo()` re-inserts via a `place()` that resolves parent by hyp-id and inserts before the next sibling (or appends). This is the inverse pattern the paste command mirrors.
- **`interaction.js`**: `commitDrop(dragEl, cls)` snapshots displaced siblings' rects (FLIP FIRST, dragged element excluded), pushes a reorder command, then plays the FLIP in `requestAnimationFrame`, and calls `reanchorAfterMove()` + `remount(...)`. Reuse this snapshot→insert→play block for insert-paste. `mount(hypId)` mounts the Moveable; `lastPointer` is tracked in `onDrag`.
- **`reorder.js`**: `classifyDrop(el,x,y)`, `isContainer(el)`, `dominantAxis(el)` — pure drop classification (reuse for "where would an inserted node land").
- **`comments.js`**: `reanchorAfterMove()` re-resolves all anchors after a DOM move. Fresh-id clones carry NO comments (anchors keyed separately) — design D5.
- **`serializer.js`**: strips every `hyp-` id/class and `data-hyp-*` (except `data-hyp-agent`); **preserves inline `style` on real content** (`position/left/top`, `translate`) → floated copies persist. A node-count guard aborts a damaged save (returns `null`).
- **`runtime-main.js`** `boot()` registers bridge commands via `register(...)` and imports modules — where `copy`/`paste`/`paste-into-layout` register and `clipboard.js`/`paste.js` import.

## Interface Contracts (binding)

- **Clipboard slot** (`runtime/js/clipboard.js`, single in-memory slot, last copy wins):
  `{ node: <deep clone, all data-hyp-* stripped via stripIds + attribute sweep>, wasRegion: boolean, cascade: number }`. `wasRegion = (original.parentElement === document.body)`. Exports e.g. `copy(el)`, `get()`, `bumpCascade()`, `hasContent()`.
- **Paste command** (`runtime/js/commands.js`): `paste(node, parentHypId, nextHypId)` → `{ do(){ insert node into parentHypId before nextHypId (or append) }, undo(){ remove node }, label:"paste" }` — mirrors `deleteElement`'s captured-ref inverse. Slide-position side-effects (e.g. setting a static slide to `position:relative`) and `tag()`/`select()`/`mount()` are composed by `paste.js` around the pushed command (the way the `delete-element` handler wraps `reanchorComments()`), so undo reverts them too.

## Behavior Specification

| # | When (gesture) | Then (observable result) |
|---|----------------|--------------------------|
| 1 | Component selected, not editing, `Ctrl+C` | clipboard slot stores a deep clone with `data-hyp-*` stripped, `wasRegion` set, `cascade=0` |
| 2 | `Ctrl+C` while editing / real text selection | NOT intercepted — native text copy (D4) |
| 3 | `Ctrl+V`, pointer over a slide | a copy is placed **out of flow** (`position:absolute`, appended to the target slide) centred under the cursor; OTHER components on the slide do NOT move; the copy is tagged, selected, and Moveable-mounted |
| 4 | `Ctrl+V`, pointer not over a slide | fallback: target = the top-level region whose rect contains the viewport centre (design D3) |
| 5 | Repeated `Ctrl+V` at the same cursor | each copy is cascaded by `cascade*step` (~16px) and `cascade` increments (D7) |
| 6 | `Ctrl+Shift+V`, a component selected whose parent is NOT a grid | the clone is inserted as a real sibling immediately after the target; the flex row/block reflows; displaced siblings FLIP-animate; the clone becomes the selection |
| 7 | `Ctrl+Shift+V`, target's parent IS a CSS grid (`getComputedStyle(parent).display` grid/inline-grid, or `roleOf(target)==='grid-child'`) | fall back to float-paste (D11) |
| 8 | `Ctrl+Shift+V`, nothing selected | behave as float-paste |
| 9 | Clipboard holds a whole slide (`wasRegion` true) | BOTH paste keys insert it as a new top-level region after the current slide (a slide cannot float) — design D6 |
| 10 | Undo after any paste | the pasted copy is removed (and any slide-position side-effect reverted); Redo re-adds it |
| 11 | Save (`serialize`) after a paste | succeeds (node-count guard passes); the floated copy's inline `position/left/top`/`translate` persist; the file re-opens correctly |

**Float-paste placement (design §7.3):** target slide = `document.elementFromPoint(x,y)?.closest("section,.slide,[data-hyp-region]")`; set `clone.style.position='absolute'`, append to the slide, set `left/top` so the clone's centre sits at the cursor (cursor − slide-rect origin − half the clone's size); if the slide is `position:static`, set it `position:relative` (record for undo); then `tag()`, `select(cloneId)`, `interaction.mount(cloneId)`.

## Edge Cases & Error Behavior

| Case | Required behavior |
|------|-------------------|
| `Ctrl+V` with empty clipboard | no-op (optional status hint) |
| Float-paste target slide is `position:static` | set it `position:relative` and record the side-effect so undo reverts it |
| Float-paste pointer over shell chrome / gutter | fall back to current-slide centre (D3) |
| Insert-paste into a CSS grid | float-paste instead (D11) |
| Pasted copy | carries NO comment threads (fresh ids; D5) — nothing extra to do |
| After insert-paste | call `comments.reanchorAfterMove()` (siblings moved) |

## Out of Scope

- OS/system clipboard, cross-window/cross-file copy, multi-select copy.
- Changing existing drag/resize/reorder behaviour (only REUSING `commitDrop`'s FLIP block and `classifyDrop`).

## Test Plan

Headed, real mouse/keyboard. Flex/grid cases use `tests/e2e/fixtures/flow-grow.html` (flex row) and `grid-healthy.html` (CSS grid); the integrated run uses the real deck.

| # | Criterion (owner-observable) | Gesture | Expected result | Evidence captured |
|---|------------------------------|---------|-----------------|-------------------|
| C6 | Float paste, no reflow | select a component (not editing), `Ctrl+C`, move the mouse over a slide, `Ctrl+V` | a copy appears under the cursor; the OTHER components' measured `getBoundingClientRect` are unchanged before vs after | screenshot + a JSON dump of sibling rects before/after |
| C7 | Insert paste, reflow + grid fallback | in a flex row: select a component, `Ctrl+Shift+V`; on a fixed-grid slide: `Ctrl+Shift+V` | flex row rebalances (siblings' measured positions changed); on the grid a floating copy appears instead of breaking the grid | screenshots + measured positions for both |
| C8 | Whole-slide duplicate | copy a whole slide, paste | a new slide is inserted (duplicate), not a floating overlay | before/after screenshots + region count |
| C9 | Undo + clean | paste, single Undo (then Redo); then Save | Undo removes the copy, Redo re-adds it; pasted copies carry no comment threads; `serialize` after a paste succeeds (guard passes) and the saved file re-opens | screenshots + the saved HTML file + a re-open screenshot |

> Fidelity floor: real app whole, owner's real deck for the integrated run + the named fixtures for flex/grid, visible browser + real input, `getBoundingClientRect` measured, files written during the exercise.

## Return Expectations

`status` · `landed` (files + local commit hash on `master`) · `validation` (`node --check` on touched JS + the copy/paste pytest, each EXIT + WALL_MS; skips with reasons) · `concerns` · `open_questions`.
