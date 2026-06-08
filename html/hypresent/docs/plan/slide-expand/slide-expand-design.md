# Slide Expand — Design

**Date:** 2026-06-08
**Component:** hypresent builder (`html/hypresent/app`)
**Scope:** Front-end only. No server endpoints, no manifest/data changes.

## Problem

In the builder's center browse grid, slide cards show a small scaled-down thumbnail. To read a slide's actual content the user must add it to the deck and open the Editor, or squint at the thumbnail. There is no way to inspect a single slide full-size in place.

## Goal

Let the user open any slide full-size over the browse grid, read it, step through neighbours, optionally add it, and return — without leaving the builder or touching the deck unless they choose to.

## Outcome Criteria (owner-observable)

1. **Expand affordance** — Hovering a slide card shows a small round magnifier button in the thumbnail's top-right corner (alongside the existing bottom-right `+ Add` pill). Clicking it opens that slide full-size over the center grid and does **not** add the slide to the presentation tray.
2. **Full-size view** — The expanded slide renders at full fidelity (the same rendering used by the Editor), sized to fit the center column. The left library rail and right presentation tray stay visible and usable.
3. **Close returns intact** — A Close button (✕) and the `Esc` key return to the grid at the same scroll position the user left.
4. **Prev/Next** — `‹ Prev` / `Next ›` buttons and the `←` / `→` keys step through the currently **visible** slides in grid order. Hidden-by-language-filter slides are skipped. At the first/last visible slide the corresponding arrow is disabled (stop at ends, no wrap).
5. **Add from expanded view** — An `Add to presentation` button adds the slide currently on screen to the tray (tray count increases, the slide's grid badge appears). If the slide is already in the tray, the button shows an `Added` state instead of adding a duplicate.

## Architecture

One new module owns the expanded view; the browse pane only gains the button and a call into it.

| Unit | Responsibility |
|------|----------------|
| `js/builder/slide-stage.js` (new) | The expanded "stage": builds the overlay DOM inside the browse pane, renders the slide via `getSlideSrcdoc`, owns open/close, prev/next over visible cards, keyboard handling, and the Add button. Exposes `createSlideStage(opts) → { open(slideId), close() }`. |
| `js/builder/browse-pane.js` (edit) | Adds the magnifier button (`.s-expand`) to each card; its click calls `stage.open(slide.id)` and stops propagation so the card's add-on-click does not fire. |
| `js/builder/builder-main.js` (edit) | Creates the stage once a library is loaded; wires its `onAdd` to `tray.add` + `markTrayState`, and `isAdded` to `tray.has`. Passes the stage into `renderBrowse`. |
| `css/builder.css` (edit) | `.s-expand` button (mirrors `.s-add` hover behavior, top-right) and `.slide-stage` overlay + toolbar styles. |

### Data flow

- **Open:** card magnifier click → `stage.open(id)` → stage shows overlay over `#builder-browse`, fetches `getSlideSrcdoc(libraryPath, id)`, mounts it in a full-size iframe, sets toolbar state (Add vs Added, arrow enabled/disabled).
- **Navigate:** stage reads `#builder-browse .slide-card:not(.hidden)` in DOM order to get the visible id list, finds the current index, moves ±1, re-renders. This keeps the stage self-contained and always in sync with the active language filter.
- **Add:** Add button → `onAdd(id)` (builder-main: `tray.add(record)` + `markTrayState`) → stage flips the button to `Added`.
- **Close:** overlay hidden, focus returns to the originating card; browse scroll position is untouched because the grid was never unmounted (the overlay sits on top, it does not replace the grid DOM).

### Why an overlay on top, not a grid swap

The overlay is positioned over the browse pane and the grid stays mounted underneath. This preserves scroll position for free (criterion 3) and avoids re-rendering the grid + re-mounting preview iframes on every close.

## Interface contracts

```
createSlideStage({
  container,        // #builder-browse element
  getLibraryPath,   // () => current libraryPath (may change on "Change library")
  getSlideRecord,   // (id) => slide record (for tray.add)
  onAdd,            // (id) => void  — adds to tray
  isAdded,          // (id) => boolean
}) => { open(slideId), close() }
```

`browse-pane.renderBrowse(data, { onTag, libraryPath, onExpand })` — `onExpand(slideId)` is the new optional callback invoked by the magnifier button.

## Error / edge handling

- Slide srcdoc fetch fails → stage shows an inline "Couldn't load this slide" message in place of the iframe; toolbar (Close/nav) stays usable.
- `open` called with the stage already open → swap content to the new slide (no stacked overlays).
- Library changed while stage open → builder-main closes the stage on `handlePickLibrary` before re-rendering.
- Empty visible set / single visible slide → both arrows disabled.

## Testing

- Playwright e2e (matches existing builder e2e suite under `tests/`): load fixture library → hover card asserts `.s-expand` visible → click → assert overlay visible and tray count unchanged → assert iframe has srcdoc content → Next/Prev change the shown slide id and respect a language filter → Add increments tray count and flips button to Added → Esc closes and grid scroll position preserved.
- Done-gate: exercise all 5 outcome criteria in a visible browser against a real library; evidence sheet under the done-gate evidence root.

## Out of scope (YAGNI)

- Editing slide content in the expanded view (it is read-only inspection).
- Wrap-around navigation, fullscreen/zoom controls, thumbnail filmstrip.
- Any change to assembly, presets, or server behavior.
