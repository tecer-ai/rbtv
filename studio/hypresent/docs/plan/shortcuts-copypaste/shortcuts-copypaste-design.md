# Hypresent — Shortcuts, whole-box formatting, and copy/paste — design spec

**Status:** design approved by the owner (2026-06-08). Ready to turn into an implementation plan.
**Audience:** an engineer/agent with **no prior context** on this discussion. Everything needed to
plan and build is in this document; read it top to bottom.

This spec doubles as the `rbtv-done-gate` **Contract**: §11 (Acceptance criteria) is the
owner-observable outcome list to exercise in a real browser before any done-claim.

---

## 0. Orientation — what & where

**App:** hypresent — a browser tool that visually edits an existing HTML "deck" (a presentation
authored as one HTML file with multiple slides). It is **not** a slide generator; it makes an
existing HTML editable: select elements, edit text, format, resize/move, recolor, comment, save.

**Repo root:** `3-resources/tools/rbtv/html/hypresent/` (inside the `rbtv` git repo; this is the
source, not an installed copy — edit here directly).

**Run it:**
```
cd <repo root>
python server/server.py 127.0.0.1 8799     # serves http://127.0.0.1:8799/app/
```
Open `http://127.0.0.1:8799/app/`, click **Open…**, choose a deck HTML. The deck renders inside an
`<iframe class="doc-frame">`; the editor chrome (toolbar, panels) is the page around it.

**Two real decks for testing:**
- `tecer-gsmm-introduction.html` (repo root) — the owner's real deck (gitignored; present locally).
- Synthetic fixtures: `tests/e2e/fixtures/flow-grow.html` (a flex row), `grid-healthy.html` (a CSS
  grid) — minimal, self-contained; ideal for flex-vs-grid paste cases.

---

## 1. Architecture primer (read before planning)

Two JavaScript worlds talk over a tiny postMessage bridge:

```
┌─ Shell (parent window) ─ app/ ───────────────┐        ┌─ Runtime (inside the deck iframe) ─ runtime/ ─┐
│ index.html  toolbar + panels + iframe mount   │  cmd→  │ runtime-main.js  registers command handlers   │
│ js/main.js  bootstraps, wires buttons, bridge │ ←event │ selection / history / commands / interaction  │
│ js/bridge/bridge-parent.js  createBridge()    │        │ text-edit / text-format / comments / serializer│
└───────────────────────────────────────────────┘        └────────────────────────────────────────────────┘
```

- **Shell** (`app/`, runs in the top window): the toolbar, comment panel, open/save, undo/redo
  buttons. It owns NO document logic — it sends **commands** into the iframe and listens for
  **events** back.
- **Runtime** (`runtime/`, injected INTO the opened deck as
  `<script type="module" src="/runtime/js/runtime-main.js">`): all document logic — detecting
  editable elements, selection, text editing, formatting, drag/resize, delete, comments,
  serialization, undo/redo.
- **Bridge** (`app/js/bridge/bridge-parent.js` ⇄ `runtime/js/bridge-iframe.js`):
  - Shell → runtime: `bridge.command(type, payload) → Promise<result>`.
  - Runtime → shell: `emit(type, payload)`; shell subscribes via `bridge.on(type, handler)`.
  - Runtime registers handlers via `register(type, handler)` in `runtime-main.js`'s `boot()`.
- **Server** (`server/server.py`, stdlib only): static routes `/app/*`, `/runtime/*`, and `/doc/*`
  (the open deck's folder); POST `/api/*` for open/save/builder. Test seam:
  `POST /api/_test/set-dialog` and `/api/_test/set-folder-dialog` are active only when
  `HYP_TEST_DIALOG=1` (used to feed native file/folder dialogs in tests).

**Conventions (decisions A2/A3/A12, see `docs/spec/03-module-map.md`):**
- Every module is small, single-purpose, independently testable. **No monolith.**
- All editor-injected DOM uses the `hyp-` prefix: classes/ids `hyp-…`, attributes `data-hyp-*`.
  The **serializer strips all of it** on save, so the saved HTML is clean.
- All document mutations go through the **command + history** pattern (undo/redo for everything).

---

## 2. Existing building blocks to REUSE (do not reinvent)

Exact files, public functions, and what they already do. New work composes these.

| File | Public surface | What it does (relevant to this work) |
|------|----------------|--------------------------------------|
| `runtime/js/element-registry.js` | `tag()`, `byId(id)`, `idOf(el)`, `roleOf(el)`, `stripIds(clone)` | `tag()` assigns fresh `data-hyp-id` to untagged elements. `roleOf` → `'flex-child'\|'grid-child'\|'absolute'\|'block'`. `stripIds` removes ids from a clone. |
| `runtime/js/selection.js` | `select(id)`, `clear()`, `current()→{hypId,role,rect,isText,alignCaps}`, `onSelectionChange(cb)` | Single-element selection + `hyp-` ring. Click selects nearest registered ancestor. `current().isText` = element is text-editable. |
| `runtime/js/history.js` | `push(cmd)`, `undo()`, `redo()`, `state()` | One linear undo/redo stack. `push(cmd)` runs `cmd.do()`. Already owns the `Ctrl+Z`/`Ctrl+Shift+Z`/`Ctrl+Y` keydown listener (inside the iframe). A `cmd` = `{do(), undo(), label}`. |
| `runtime/js/commands.js` | `text`, `format`, `resize`, `move`, `reorder`, `deleteElement`, `colorToken`, `colorElement`, `colorBorder`, `align`, `comment` | Command factories. `format(id,beforeHtml,afterHtml)` = innerHTML swap (used by bold/italic/font). `deleteElement(id)` captures parent + next-sibling + node ref; `undo()` re-inserts. `reorder(...)` moves a node to a new parent before an anchor. |
| `runtime/js/text-format.js` | `apply(op)` (`bold\|italic\|fontInc\|fontDec`), `snapshotSelection()`, `clearFontState()`, `computeAlignCaps`, `applyAlign` | Formatting. **Today `apply()` no-ops unless a `contenteditable` text edit is active.** Bold/italic call `execCommand`; font-size calls internal `adjustFontSize` (span-based, with selection snapshot/restore). All push a `format` command. |
| `runtime/js/text-edit.js` | self-activating | Double-click → `contenteditable=true` + focus + `suspendInteraction()`; blur/Esc → commit a `text` command + restore `contenteditable`. |
| `runtime/js/interaction.js` | `mount(id)`, `unmount()`, `remount(id)`, `suspend/resume`, `isActive()` | One Moveable per selection (drag + resize + snapping). On drag-end, `classifyDrop` → keep-translate (move) OR `reorder`/`reparent` with **FLIP animation of displaced siblings** (`commitDrop`). Tracks `lastPointer`. Reuse the FLIP block for insert-paste. |
| `runtime/js/reorder.js` | `classifyDrop(el,x,y)`, `isContainer(el)`, `dominantAxis(el)` | Pure drop classification: same-parent → reorder, other container → reparent. Reuse for "where would an inserted node land". |
| `runtime/js/comments.js` | `add`, `threads`, `reanchorAfterMove`, `toJson`, … | Threads anchored by a collision-resistant key (survives id strip), stored in a `<script id="hyp-comments">` island. `reanchorAfterMove()` re-resolves anchors after DOM moves — call it after insert-paste. |
| `runtime/js/serializer.js` | `serialize()→html\|null` | On save: deep-clone, strip every `hyp-` id/class and `data-hyp-*` attr (except `data-hyp-agent`), remove injected runtime script + editor `contenteditable`, re-embed comment island, node-count guard. **Inline `style` on real content (e.g. `position:absolute; left/top`, `translate`) is preserved** → pasted/floated elements persist correctly. |
| `runtime/js/runtime-main.js` | `boot()` registers bridge commands; wires `onSelectionChange`→interaction | Where new bridge commands (`copy`, `paste`, `paste-into-layout`) get registered, and where a new shortcuts module is imported. Already registers `delete-element`, `format`, `get-selection`, `select`, `undo`, `redo`, etc. |
| `runtime/js/bridge-iframe.js` | `register(type,h)`, `emit(type,payload)` | Iframe side of the bridge. |
| `app/js/bridge/bridge-parent.js` | `createBridge(iframe)→{command,on,off,destroy}` | Shell side of the bridge. |
| `app/js/main.js` | shell bootstrap | Wires `#fmt-bold/#fmt-italic/#fmt-font-inc/#fmt-font-dec` (mousedown→`format-snapshot`+iframe focus, click→`format`), `#delete-btn`, `#comment-btn` (→`openComposer`), `#undo-btn/#redo-btn`, panel composer. Holds `bridge`, `lastSelection`, `isEditingNow`. |
| `app/index.html` | shell DOM | Toolbar ids: `#fmt-bold`, `#fmt-italic`, `#fmt-font-dec`, `#fmt-font-inc`, `#align-left/center/right`, `#align-top/middle/bottom`, `#comment-btn`, `#delete-btn`; topbar: `#undo-btn`, `#redo-btn`, `#doc-chip`; `iframe.doc-frame`; `#shell-panel`. |

---

## 3. Problem statement & scope

**Three asks + one bug found during design:**
1. New keyboard shortcuts (comment, delete-component, bold, italic) and a clickable place to see
   all shortcuts.
2. Copy/paste a component. Pasting is the hard part: components live inside flexible rows / CSS
   grids, so inserting a copy into the flow makes the container rebalance and resize every sibling.
3. **Bug:** bold/italic only work on the first click; pressing again does nothing until the element
   is re-selected.

**In scope:** formatting repeat-fix + whole-box formatting; the four shortcuts + a cheat-sheet
overlay; internal copy/paste of a component.

**Out of scope (future):** OS/system-clipboard or cross-window/cross-file copy; multi-select copy;
new dedicated font-size keyboard shortcuts (A+/A− stay button-driven — only their *whole-box*
behaviour changes).

---

## 4. Locked decisions (with rationale)

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| D1 | Paste model | **Two shortcuts:** `Ctrl+V` floats a copy (no reflow); `Ctrl+Shift+V` inserts into the row/grid (reflows) | Safe default + full control |
| D2 | Clipboard scope | **Internal, in-memory, this deck only** | Avoids OS-clipboard edge cases & `Ctrl+C`-vs-text conflicts; also fully testable headed (no native dialog) |
| D3 | Float-paste position | **Under the mouse cursor**, on whatever slide it's over; fallback: pointer not over a slide → centre of the slide currently in view | Precise "drop it here"; never silently fails |
| D4 | `Ctrl+C` while typing | Stays **native text copy**; copies the *component* only when a component is selected and **not** editing | Least surprising |
| D5 | Comments on a copy | **Paste clean** | Falls out naturally: the clone gets fresh ids, so no anchor matches |
| D6 | Copying a whole slide | Allowed → paste **duplicates the slide** (always inserts; a slide can't float) | Useful, low risk |
| D7 | Repeated paste | **Cascades** each copy further so they don't stack exactly | PowerPoint convention |
| D8 | Comment shortcut key | **`Ctrl+Alt+C`** (NOT `Ctrl+Shift+C`) | `Ctrl+Shift+C` = Chrome "Inspect Element"; `Ctrl+Alt+C` is conflict-free |
| D9 | Bold/italic/A+/A− scope | Act on the **whole text box when selected** (not editing); on the **highlighted words when editing** | Matches the owner's mental model |
| D10 | Whole-box font size | **Scale all text proportionally** (multiply every size, incl. individually-sized words, by one factor) | A mixed-size box grows/shrinks as one and keeps its proportions |
| D11 | Insert-paste into a grid | **Fall back to float-paste** when the target's parent is a CSS grid | A fixed grid overflows/breaks instead of rebalancing like a flex row |

---

## 5. Part 1 — Formatting: repeat-fix + whole-box

### 5.1 Root cause of the bug (verified)
`commands.format.do()` runs `el.innerHTML = afterHtml`. `history.push(cmd)` calls `do()`, which
**re-parses the subtree and collapses the live text selection**. Font-size survives because
`adjustFontSize` re-finds its target span by a `data-hyp-fontspan` marker and bumps it without a
live selection; **bold/italic have no such fallback and never restore the selection** — so the
second press acts on a collapsed caret and does nothing until the element is re-selected.

### 5.2 Fix — keep the selection alive across the round-trip (editing path)
In `text-format.apply()` (bold/italic path):
1. Before the op, capture the selection as **character offsets** within the editable element
   (start, end), by walking its text nodes.
2. Run `execCommand` and `push` the `format` command as today.
3. After `push`, **restore** the selection from those offsets (walk the new text nodes back to a
   `Range`). Character offsets are stable because bold/italic don't change text characters.

Result: bold/italic (and combinations) repeat on the same text without re-selecting.

### 5.3 Whole-box behaviour (selected, NOT editing) — D9/D10
When a format op is requested and there is **no active edit** but `selection.current()` resolves a
**text-editable** element (`isText`), operate on the whole element:

| Op | Whole-box behaviour |
|----|---------------------|
| Bold / Italic | Select ALL the element's text, toggle via the existing `execCommand` path (if any part isn't bold → all bold; press again → clear), capture as one `format` command. Keep the element selected (ring) afterward. |
| A+ / A− | **Proportional scale (D10):** capture innerHTML before; multiply the element's base `font-size` **and every descendant's explicit `font-size`** by one factor matching the existing ±2px step at the base; capture innerHTML after; push one `format` command. (New helper, e.g. `scaleWholeBox(el, dir)`; do NOT route whole-box sizing through the span-based `adjustFontSize`, which is for the editing path.) |

**Implementation notes:**
- Manage the transient `contenteditable` **locally** inside `text-format` for the whole-box bold/italic
  toggle — do NOT go through `text-edit.enterEdit` (its blur listener + interaction-suspend are for
  user-driven edits). Always restore the prior `contenteditable` and leave the ring selection intact.
- The editing path (real text selection inside an active edit) is unchanged except for 5.2.
- The shell already snapshots selection on toolbar mousedown (`format-snapshot`) for the focus
  bounce; the new keyboard path (`Ctrl+B`/`Ctrl+I`) needs no bounce (focus is already in the doc).

### 5.4 Files
`runtime/js/text-format.js` (primary), `runtime/js/runtime-main.js` (`format` handler may pass an
"editing vs selected" hint or `text-format` reads `selection.current()` itself), possibly a tiny
helper in `selection.js` to expose the selected element node.

### 5.5 Compatibility (must NOT break)
- `tests/e2e/test_r8_font_size_repeat.py` — font-size repeat **in edit mode** must still work.
- Existing bold/italic-in-edit behaviour must still work (now also repeatable).

---

## 6. Part 2 — Keyboard shortcuts + cheat-sheet

### 6.1 Bindings

| Action | Key | Owned by | Notes |
|--------|-----|----------|-------|
| Bold | `Ctrl+B` | runtime | whole box if selected; highlighted text if editing (Part 1) |
| Italic | `Ctrl+I` | runtime | same |
| Comment | `Ctrl+Alt+C` | shell | opens the composer for the selected component (same as `#comment-btn`) |
| Delete component | `Ctrl+Del` | runtime | same guards as `#delete-btn` (blocked while editing, blocked on last region) |
| Copy component | `Ctrl+C` | runtime | only when a component is selected and not editing (else native copy) |
| Paste — float under cursor | `Ctrl+V` | runtime | D3 |
| Paste — into layout | `Ctrl+Shift+V` | runtime | D1, D11 |
| Show shortcuts | click **"?"**, or `Ctrl+/` | shell | cheat-sheet overlay |

### 6.2 Capture architecture (the iframe/shell focus split)
Keyboard events go to whichever document has focus. Use TWO cooperating listeners:

- **New `runtime/js/shortcuts.js`** (inside the iframe): a `keydown` listener handling the
  in-document actions (bold, italic, delete, copy, paste-float, paste-into-layout) by calling the
  runtime functions directly. For shell-owned actions it `emit("shortcut", {action})` to the shell.
  `preventDefault()` on every combo it owns — crucially `Ctrl+B`/`Ctrl+I` (suppress native), and
  `Ctrl+V`/`Ctrl+Shift+V`/`Ctrl+Del` when a component is selected.
- **Shell listener in `app/js/main.js`**: handles the same combos when focus is in the shell chrome
  (call the existing button handlers, or forward via `bridge.command`). Also `bridge.on("shortcut", …)`
  to fire comment / show-shortcuts when the runtime forwarded them.

**Guards:** never hijack `Ctrl+C`/`Ctrl+V` while a text edit is active or a real text selection
exists (D4) — let the browser do native copy/paste of text there.

### 6.3 Cheat-sheet overlay
- Add a **"?"** icon button to the topbar in `app/index.html` (e.g. a `tb-ico` next to `#redo-btn`,
  id `#shortcuts-btn`).
- New `app/js/shell/shortcuts-help.js` (+ styles in `app/css/shell.css`): a modal overlay listing
  all shortcuts grouped — **Text** (bold, italic, A+/A−), **Components** (copy, paste, paste-into-layout,
  delete), **Editing** (comment, undo, redo, show-shortcuts). Opens on the "?" click or `Ctrl+/`;
  closes on outside-click or `Esc`. Pure shell UI; no runtime involvement.

### 6.4 Compatibility (must NOT break)
- `tests/e2e/test_r3_delete.py::test_no_keyboard_delete` asserts **plain `Delete`/`Backspace` must
  NOT delete a component.** Our keyboard delete is **`Ctrl+Del` ONLY**; plain `Delete`/`Backspace`
  stay inert. Do not regress this.
- The existing toolbar buttons keep working unchanged; shortcuts are additive.

---

## 7. Part 3 — Copy / paste components

### 7.1 Clipboard model
New `runtime/js/clipboard.js`: a single in-memory slot holding
`{ node: <deep clone, all data-hyp-* stripped>, wasRegion: <bool>, cascade: <int> }`. Last copy wins.
Strip `data-hyp-id` (`stripIds`) **and** any other `data-hyp-*` markers from the clone so paste
re-tags cleanly and carries no editor state. `wasRegion = (original.parentElement === document.body)`.

### 7.2 Copy (`Ctrl+C`)
When a component is selected and NOT editing text → store `clone = selected.cloneNode(true)`, strip
its `data-hyp-*`, set `wasRegion`, reset `cascade=0`. While editing / with a real text selection →
do not intercept (native copy).

### 7.3 Paste — float under cursor (`Ctrl+V`) — D3, D7
1. Track the last pointer position with a lightweight `mousemove` listener in the iframe
   (`{x,y}` in client coords; can live in `shortcuts.js` or `interaction.js`).
2. Clone the clipboard node; `tag()` after insertion assigns fresh ids.
3. **Target slide** = `document.elementFromPoint(x,y)?.closest("section,.slide,[data-hyp-region]")`.
   Fallback (pointer not over a slide): the top-level region whose rect contains the viewport centre.
4. Place the clone **out of flow** so nothing reflows: `clone.style.position='absolute'`, append to
   the target slide, set `left/top` so the clone's centre sits at the cursor (cursor minus slide
   rect origin minus half the clone's size). Ensure a positioning context: if the slide is
   `position:static`, set it `position:relative` (record this side-effect for undo).
5. `tag()`, `select(cloneId)`, `interaction.mount(cloneId)` (it's now an `absolute`-role element the
   drag/resize already handles).
6. **Cascade (D7):** if the same cursor is reused for repeated `Ctrl+V`, offset each by
   `cascade * step` (e.g. 16px) and increment.
7. Push ONE paste command (do: insert + tag + slide-position side-effect; undo: remove clone +
   revert side-effect).

### 7.4 Paste — into layout (`Ctrl+Shift+V`) — D1, D11
- Target = `selection.current()` element. If none → behave as float-paste.
- If the target's **parent is a CSS grid** (`getComputedStyle(parent).display` is `grid`/`inline-grid`,
  or `roleOf(target)==='grid-child'`) → **fall back to float-paste** (D11).
- Otherwise insert the clone as a real sibling **immediately after the target**
  (`target.parentNode.insertBefore(clone, target.nextSibling)`); the flex row/block reflows.
  **FLIP-animate** displaced siblings (reuse the snapshot→insert→play block in
  `interaction.commitDrop`). `tag()`, `select(cloneId)`, `comments.reanchorAfterMove()`.
- The pasted copy becomes the new selection. Push ONE paste command (do: insert + tag; undo: remove).

### 7.5 Whole-slide paste (D6)
If `clipboard.wasRegion` is true (the copied thing was a top-level region / whole slide), **both**
paste keys insert it as a **new top-level region after the current slide** (a slide can't float).
"Current slide" = the selected region, else the region in view.

### 7.6 Cross-cutting
- **Fresh ids:** strip on copy + `tag()` after insert → no id collisions. Comments are keyed
  separately, so the fresh-id clone carries **no comments** (D5) — nothing extra to do.
- **Undo:** one history command per paste, mirroring `commands.deleteElement`'s inverse (capture the
  inserted node ref; `do()` inserts + tags + any side-effect, `undo()` removes + reverts).
- **Serialization:** the floated copy's inline `position/left/top` (and any `translate`) are real
  content styles → preserved by `serializer.js` (it only strips `hyp-`/`data-hyp-*`). A pasted deck
  re-opens correctly. Confirm a `serialize()` after paste still passes the node-count guard.
- **Files:** `runtime/js/clipboard.js` (new), `runtime/js/paste.js` (new), `runtime/js/commands.js`
  (add a `paste`/insert command factory), `runtime/js/runtime-main.js` (register `copy`/`paste`/
  `paste-into-layout`; import the modules), `runtime/js/shortcuts.js` (keys + pointer tracking).

---

## 8. New & modified files (summary)

**New**
- `runtime/js/shortcuts.js` — in-iframe keydown router + pointer tracker; forwards shell actions.
- `runtime/js/clipboard.js` — in-memory clipboard slot.
- `runtime/js/paste.js` — float-paste + insert-paste logic.
- `app/js/shell/shortcuts-help.js` — cheat-sheet overlay.

**Modified**
- `runtime/js/text-format.js` — selection-restore fix (5.2) + whole-box behaviour (5.3) + `scaleWholeBox`.
- `runtime/js/commands.js` — `paste`/insert command factory.
- `runtime/js/runtime-main.js` — register `copy`/`paste`/`paste-into-layout`; import `shortcuts.js`,
  `clipboard.js`, `paste.js`; possibly pass an editing-vs-selected hint to `format`.
- `app/js/main.js` — shell-side shortcut listener + `bridge.on("shortcut", …)`; wire `#shortcuts-btn`.
- `app/index.html` — add `#shortcuts-btn` ("?") to the topbar.
- `app/css/shell.css` — overlay styles.
- `docs/spec/03-module-map.md` — add the new modules (keep the module map truthful, per repo rule).

---

## 9. Edge cases

| Case | Handling |
|------|----------|
| `Ctrl+V` with empty clipboard | No-op (optional status hint) |
| `Ctrl+C` on a whole slide → `Ctrl+V` | Inserts a new slide (D6), not a floating overlay |
| Float-paste target slide is `position:static` | Set it `position:relative` (record for undo) so the absolute copy anchors to the slide |
| Float-paste pointer over shell chrome / gutter | Fallback to current-slide centre (D3) |
| Insert-paste with nothing selected | Float-paste instead |
| Insert-paste into a CSS grid | Float-paste instead (D11) |
| Whole-box bold on an already-all-bold box | Toggles OFF |
| Whole-box A+ on mixed sizes | Proportional scale keeps ratios (D10) |
| `Ctrl+Del` while editing / on last region | Blocked, same as `#delete-btn` (reuse `delete-element` guards) |
| Plain `Delete`/`Backspace` | Still inert (compat with `test_r3_delete`) |

---

## 10. Suggested implementation phases

1. **Formatting** — repeat fix (5.2) + whole-box (5.3). Self-contained; unblocks `Ctrl+B/I`.
2. **Shortcuts + cheat-sheet** — `shortcuts.js` + shell listener + "?" overlay (wire bold/italic/
   comment/delete; copy/paste keys arrive in phase 3).
3. **Copy/paste** — `clipboard.js` + copy; then float-paste; then insert-paste + grid fallback; then
   whole-slide.

Each phase ends by exercising its acceptance criteria at the fidelity floor and filling the evidence
sheet (§12).

---

## 11. Acceptance criteria (owner-observable — the done-gate Contract)

Exercise each in a **visible (headed) browser with real mouse/keyboard**, on a **real deck**
(`tecer-gsmm-introduction.html`; use `flow-grow.html`/`grid-healthy.html` for the flex/grid cases),
capturing evidence files (screenshots / measured values) during the run.

- **C1 — Whole-box formatting.** With a text box selected (not editing): `Ctrl+B` (or the Bold
  button) bolds ALL its text; press again → un-bolds; repeatable without re-selecting. Same for
  `Ctrl+I`, and for A+/A− (the whole box scales proportionally, keeping its internal proportions).
- **C2 — Repeat bug fixed (editing path).** While editing text, select a word, `Ctrl+B` bolds it;
  with it still selected, `Ctrl+B` again un-bolds it — no re-selection needed.
- **C3 — Comment shortcut.** With a component selected, `Ctrl+Alt+C` opens the comment composer for
  it, and does NOT trigger Chrome's inspector.
- **C4 — Delete shortcut.** With a component selected, `Ctrl+Del` deletes it; blocked while editing
  and on the last remaining region. Plain `Delete`/`Backspace` still do nothing.
- **C5 — Cheat-sheet.** Clicking "?" (or `Ctrl+/`) opens an overlay listing all shortcuts; `Esc` /
  outside-click closes it.
- **C6 — Float paste, no reflow.** With a component selected (not editing), `Ctrl+C`, move the mouse
  over a slide, `Ctrl+V` → a copy appears under the cursor; the OTHER components on that slide do NOT
  move (assert their measured `getBoundingClientRect` are unchanged before vs after).
- **C7 — Insert paste, reflow + grid fallback.** With a component in a flex row selected,
  `Ctrl+Shift+V` inserts a copy next to it and the row rebalances (siblings shift — assert measured
  positions changed). On a fixed-grid slide, `Ctrl+Shift+V` produces a floating copy instead of
  breaking the grid.
- **C8 — Whole-slide duplicate.** Copying a whole slide and pasting duplicates it as a new slide.
- **C9 — Undo + clean.** A single Undo removes a pasted copy (Redo re-adds it); pasted copies carry
  no comment threads; saving (`serialize`) after a paste succeeds (node-count guard passes) and the
  saved file re-opens.

**Drivability (rbtv-build-for-agent-testability):** all criteria are `drivable` as-is in a headed
browser — keyboard via real key events, cursor-paste via real `mouse.move` + key, no-reflow via
measured `getBoundingClientRect`, the cheat-sheet via click + visibility. The internal clipboard (D2)
means **no native OS dialog** is in any criterion → **no test seam needs to be built**.

---

## 12. Testing & evidence

**Build-phase tests (may be headless)** — follow the existing harness in `tests/e2e/`:
- Pattern: `unittest` + `playwright.sync_api`, helpers in `tests/e2e/conftest_helpers.py`
  (`start_server(port, test_dialog=True)`, `copy_fixture()`, `copy_synthetic(name)`,
  `open_via_dialog_ui(page, base, path)`, `wait_runtime_ready(page)`, `doc_eval(page, jsBody)`,
  `preset_author(page)`). See `tests/e2e/test_r3_delete.py` for the canonical shape (select via real
  mouse click at the element's screen rect, act, assert via `doc_eval`).
- Suggested new suites: `test_*_format_repeat_wholebox.py`, `test_*_shortcuts.py`,
  `test_*_copy_paste.py` (use `flow-grow.html` for the flex reflow/float cases and `grid-healthy.html`
  for the grid fallback).
- Unit tests for any new server behaviour go in `tests/unit/` (none expected — this work is
  client-side; the internal clipboard needs no server).

**Done-gate exercise (MUST be headed)** — a Playwright script with `chromium.launch(headless=False)`
driving the **real** server + a **real** deck with **real** mouse/keyboard, capturing screenshots and
measured geometry per criterion. Model it on the existing done-gate exercise at
`1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-07-ui-redesign/exercise.py`.

**Evidence location** (resolved from the vault CLAUDE.md routing table for `rbtv-done-gate`):
`1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/{YYYY-MM-DD}-{feature}.md` with capture
files in a sibling `{YYYY-MM-DD}-{feature}/` folder. Fill one evidence sheet (criteria C1–C9) before
any done-claim.

**Compatibility regression set (must stay green):** at minimum `test_r3_delete.py` (esp.
`test_no_keyboard_delete`), `test_r8_font_size_repeat.py`, `test_r7_alignment.py`, and the serializer
tests in `tests/unit/`.

---

## 13. References (read on demand)
- `docs/spec/01-architecture.md` — full architecture & decisions (A-numbers).
- `docs/spec/02-html-convention.md` — what counts as an editable element / region.
- `docs/spec/03-module-map.md` — per-module purpose + public interface (update it when adding modules).
- `docs/spec/05-verification-plan.md` — per-module pass/fail criteria style.
- `runtime/js/interaction.js` `commitDrop()` — the FLIP + reorder pattern to reuse for insert-paste.
- `runtime/js/commands.js` `deleteElement()` — the insert/remove + undo pattern to mirror for paste.

## 14. Open questions / future
- Optional later: dedicated keyboard shortcuts for font size and a one-key "duplicate in place".
- Optional later: system-clipboard support for cross-window/cross-file copy.
