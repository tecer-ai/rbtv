# Decisions — slide-expand

Worker-facing decisions for the slide-expand build. Resolved during brainstorming; see `slide-expand-design.md` for full design.

| # | Decision | Resolution |
|---|----------|------------|
| D1 | Expand button placement | Top-right magnifier icon on the thumbnail, appears on hover (mirrors `.s-add`). |
| D2 | Expanded-view actions | Close + Add to presentation + Prev/Next. |
| D3 | Prev/Next scope | Walk currently-visible cards (`.slide-card:not(.hidden)`) in DOM order; respect language filter; stop at ends, no wrap. |
| D4 | Overlay vs grid-swap | Overlay positioned over `#builder-browse`; grid stays mounted underneath (preserves scroll, avoids iframe remount). |
| D5 | Click isolation | Expand-button click stops propagation so the card's add-on-click does not fire. |
| D6 | Branch | Build directly on `master`, no feature branch (user decision). |
| D7 | Renderer reuse | Reuse `getSlideSrcdoc(libraryPath, id)` from `previews.js` for full-size render. |
| D8 | Module boundary | New `js/builder/slide-stage.js` owns the overlay; browse-pane only adds the button + calls `onExpand`. |
