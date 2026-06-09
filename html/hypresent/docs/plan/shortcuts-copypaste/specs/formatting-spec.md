# Spec — Whole-box formatting + repeat-fix

## Goal

The owner selects a text box (single click, NOT editing) and presses Bold / Italic / A+ / A− (button or shortcut): the **whole box** toggles bold/italic, or scales every text size proportionally — repeatably, without re-selecting. While **editing** text, selecting a word and pressing Bold toggles just that word, and pressing again toggles it back without re-selecting (the repeat bug, fixed).

## Context Snapshot

All current code is in `runtime/js/text-format.js` unless noted. Exact anchors live in the backing task (`../phase-1/p1-1.task.md`).

- **`apply(op)`** (op ∈ `bold|italic|fontInc|fontDec`) currently returns `false` unless `getActiveEditElement()` finds an element with `contenteditable="true"` as `document.activeElement`. Bold/italic call `document.execCommand`; `fontInc/fontDec` call `adjustFontSize(el, ±2)`. On any innerHTML change it builds `format(hypId, beforeHtml, afterHtml)` (a `commands.js` innerHTML-swap command) and `push`es it.
- **The repeat bug (design §5.1):** `history.push(cmd)` runs `cmd.do()` → `el.innerHTML = afterHtml`, which re-parses the subtree and **collapses the live selection**. Font-size survives because `adjustFontSize` re-finds its target span by the `data-hyp-fontspan` marker each press; **bold/italic have no such fallback and never restore the selection**, so the second press acts on a collapsed caret.
- **`selection.current()`** → `{hypId, role, rect, isText, alignCaps}`; `isText` is `true` when the element is text-editable. `selection.js` keeps the `hyp-` ring; it has no exported "give me the selected element node" helper yet.
- **`commands.format(hypId, beforeHtml, afterHtml)`** = `{do(){el.innerHTML=afterHtml}, undo(){el.innerHTML=beforeHtml}, label:"format"}`.
- **`text-edit.js`** owns the user-driven edit lifecycle: `enterEdit` sets `contenteditable=true`, `focus()`, `suspendInteraction()`, emits `edit-state {editing:true}`, and commits on blur/Esc. Whole-box formatting MUST NOT route through it.

## Behavior Specification

| # | When (gesture) | Then (observable result) |
|---|----------------|--------------------------|
| 1 | Editing text, a word selected, press Bold | the word bolds; the selection is **restored** from character offsets so a second Bold un-bolds the SAME word — no re-selection |
| 2 | Element selected (NOT editing, `current().isText` true), press Bold | ALL the element's text bolds via the existing `execCommand` path; one `format` command pushed; the ring stays; press again → all un-bolds |
| 3 | Element selected (not editing), press Italic | same as #2 for italic |
| 4 | Element selected (not editing), press A+ / A− | every text size in the box is multiplied by ONE factor (the factor that moves the element's base `font-size` by the existing ±2px step), including individually-sized descendant spans; one `format` command; ratios preserved |
| 5 | Whole-box op finishes | the element's `contenteditable` is restored to its prior value; the `hyp-` selection ring is intact; the box is NOT left in an editing session |

**Mechanism (binding):**
- **Repeat-fix (editing path):** before the op, capture the selection as character offsets (start,end) by walking the editable's text nodes; after `push`, restore a `Range` from those offsets (offsets are stable because bold/italic do not change characters).
- **Whole-box (selected path):** when `apply()` finds no active edit but `selection.current().isText` is true, operate on that element. For bold/italic, manage a transient `contenteditable` **locally** (set → select all → `execCommand` → capture `format` command → restore prior `contenteditable`), never via `text-edit.enterEdit`. For A+/A−, a new helper `scaleWholeBox(el, dir)` multiplies the base and every descendant explicit `font-size` by one factor; do NOT route whole-box sizing through `adjustFontSize`.

## Edge Cases & Error Behavior

| Case | Required behavior |
|------|-------------------|
| Whole-box Bold on an already-all-bold box | toggles OFF (one `format` command) |
| Whole-box A+ on mixed sizes | proportional scale keeps every ratio (design §5.3/D10) |
| Selected element is not text-editable (`isText` false) | whole-box op is a no-op (`apply` returns false) |
| No active edit AND no selection | `apply` returns false (unchanged) |
| Editing-path font-size repeat | unchanged — `test_r8_font_size_repeat` must still pass |
| Transient `contenteditable` | always restored to the prior value; the ring selection remains; `interaction` is never suspended by the whole-box path |

## Out of Scope

- New dedicated font-size keyboard shortcuts (A+/A− stay button/Ctrl-routed via the format command; only their whole-box behaviour changes here).
- Any change to alignment (`computeAlignCaps`/`applyAlign`) or the editing-path font-size logic beyond the §5.2 selection restore.

## Test Plan

Exercise headed, real mouse/keyboard, on the real deck `tecer-gsmm-introduction.html`. Build-phase e2e may be headless (`tests/e2e/`, playwright, `conftest_helpers`).

| # | Criterion (owner-observable) | Gesture | Expected result | Evidence captured |
|---|------------------------------|---------|-----------------|-------------------|
| C1 | Whole-box formatting | select a text box (not editing); press `Ctrl+B` (then the Bold button); press again; repeat for `Ctrl+I` and A+/A− | every press toggles/scales the WHOLE box; bold/italic repeat without re-selecting; A+/A− scale proportionally (measure two differently-sized words' computed `font-size` ratio before/after — unchanged ratio) | screenshot per state + a JSON dump of measured font-sizes |
| C2 | Repeat bug fixed (editing path) | double-click to edit; select a word; `Ctrl+B` bolds it; with it still selected, `Ctrl+B` again | the second press un-bolds the same word — no re-selection | before/after screenshots + the word's outerHTML |

> Fidelity floor: real app running whole, owner's real deck, visible browser + real input, evidence files written during the exercise. Evidence plausibility: a headed browser exercise under ~1s is auto-reject + rerun.

## Return Expectations

`status` (DONE/BLOCKED) · `landed` (files changed + local commit hash on `master`) · `validation` (`node --check` + the format-repeat pytest, each EXIT + WALL_MS; skips with reasons) · `concerns` · `open_questions` (precise blocker if halting).
