# Session 2 — User Feedback (2026-06-04)

Product owner's verbatim feedback after hands-on use of the v2 build (branch `hypresent-v2`, post-67/67 EXIT gate). Source of truth for scorecard items R1–R9. Agents read THIS file — never conversation history.

## R1 — Open/Save dialog opens behind the browser window

> "currently opens behind the main window (must open on top of the open browser window, otherwise it looks buggy - me, until discovering it, clicked many times thinking it was not working, until i minimized the browser and saw the modal in the back)"

Required: native dialogs must appear on top of the focused Chrome window.

## R2 — Element resizing does not work

> "I see the 'box' around the item with 'circles' edges, which are part of this feature, but when I click there and drag, nothing happens"

Required: dragging a resize handle resizes the element. v2 e2e reported 8/8 green on F2 — real-input repro is mandatory before root-causing.

## R3 — Element deletion (missing)

> "does not exist, there should be an option to delete element"

Required: user-facing way to delete the selected element. UX details (button/key/undo/comment-thread fate) pending question round.

## R4 — Color button 🎨 (`#color-btn`) purpose unclear

> "has no apparent function (if there is, let me know in the question round), it seems that all it does can be done without it. if this is true, it can be deleted"

Required: identify its actual function → owner decides keep vs delete.

## R5 — Palette token tooltip

> "Palette Tokens work well, but there should be a tooltip to explain that, when editing there, it will edit all components with that color across the doc."

## R6 — Per-token copy-HEX affordance

> "For each color of the palette token, user should have a small, 'discreto' [discreet] button to copy the HEX code (for when user wants to apply that color in another component)"

## R7 — Text alignment controls

> "add option to centralize (horizontal or vertical), align left, right, top or bottom (only aligning the text inside its text box - if text box is not a html term, let me know and we decide together, you can have an extra question round for that)"

Required: alignment of text within its containing element, horizontal and vertical. Terminology + CSS mechanism to be settled in question round.

## R8 — Font-size buttons single-fire per selection

> "the buttons to increase and decrease font size only allow one increase/decrease 'per selection' (after increasing/decreasing once, i must select the component again, if i want to decrease another time, and so one). it should allow to increase/decrease as many times as user wants, without having to select again"

Note: README documents this as known limitation "font-size caret artifact" — owner now requires a real fix, not a workaround note.

## R9 — Outline panel shows "no regions detected"

> "dont understand what it is, wherever I click it shows 'no regions detected'. Its either broken or its useless"

Required: diagnose root cause; owner decides fix vs remove.

## Embedded owner questions (reserve for the single question round)

1. R4: what does `#color-btn` actually do → keep or delete?
2. R7: "text box" terminology + alignment semantics per display type.
3. R9: outline — fix detection or remove the panel.
