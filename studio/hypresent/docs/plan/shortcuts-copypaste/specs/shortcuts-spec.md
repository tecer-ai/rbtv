# Spec — Keyboard shortcuts + cheat-sheet

## Goal

The owner uses keyboard shortcuts for the common editor actions, and clicks a **"?"** (or presses `Ctrl+/`) to see every shortcut in a cheat-sheet overlay. Shortcuts work whether keyboard focus is inside the document iframe or in the shell chrome, and never hijack native text copy/paste while editing.

## Context Snapshot

Two JS worlds over a postMessage bridge (design §1). Exact anchors live in the backing tasks (`../phase-2/p2-1.task.md`, `../phase-2/p2-2.task.md`).

- **Runtime (iframe), `runtime/js/runtime-main.js`** `boot()` registers bridge commands via `register(type, handler)` and imports modules; it already registers `format`, `delete-element` (with edit-active + last-region guards), `get-selection`, `select`, `undo`, `redo`, and imports `./text-edit.js`. `emit(type, payload)` (from `bridge-iframe.js`) sends events to the shell.
- **`delete-element` guards** already live in the runtime handler: blocked while a `contenteditable` edit is active (`{blocked:"editing"}`) and on the only remaining top-level region (`{blocked:"last-region"}`). The keyboard delete reuses this exact handler.
- **Shell (parent), `app/js/main.js`** holds `bridge`, `isEditingNow` (cached from the runtime `edit-state` event), `lastSelection`; wires `#fmt-bold/#fmt-italic/#fmt-font-inc/#fmt-font-dec` (mousedown→`format-snapshot`+`iframe.contentWindow.focus()`, click→`format`), `#delete-btn`, `#comment-btn` (→`openComposer` for the selected element), `#undo-btn/#redo-btn`. The comment button's flow (`get-selection` → `openComposer`) is what the comment shortcut triggers.
- **`app/index.html`** topbar has `#undo-btn`/`#redo-btn` as `tb-ico` buttons; the format toolbar has `#fmt-bold` … `#delete-btn`. `app/css/shell.css` defines tokens (`--paper`, `--ink`, `--line`, `--accent`, `--white`, `--shadow-lift`, `--r-card`, `--ink-mut`, `--font-ui`) and the `.tb-ico` / button patterns to mirror.

## Behavior Specification

### Bindings (design §6.1)

| Action | Key | Owned by | Notes |
|--------|-----|----------|-------|
| Bold | `Ctrl+B` | runtime | calls the runtime format path (whole-box if selected, per formatting-spec) |
| Italic | `Ctrl+I` | runtime | same |
| Comment | `Ctrl+Alt+C` | shell | opens the composer for the selected component (same as `#comment-btn`); NOT `Ctrl+Shift+C` |
| Delete component | `Ctrl+Del` | runtime | same guards as `#delete-btn` (blocked while editing / on last region) |
| Copy component | `Ctrl+C` | runtime | ONLY when a component is selected and not editing (else native copy) — wired in P3 |
| Paste — float | `Ctrl+V` | runtime | wired in P3 |
| Paste — into layout | `Ctrl+Shift+V` | runtime | wired in P3 |
| Show shortcuts | click **"?"** or `Ctrl+/` | shell | cheat-sheet overlay |

### Capture architecture (the focus split)

- **New `runtime/js/shortcuts.js`** (in the iframe): one `keydown` listener handling in-document actions (bold, italic, delete; copy/paste added in P3) by calling the runtime functions directly. For shell-owned actions it `emit("shortcut", {action})`. **`preventDefault()` on every combo it owns** — crucially `Ctrl+B`/`Ctrl+I` (suppress native) and `Ctrl+Del` when a component is selected.
- **Shell listener in `app/js/main.js`**: handles the same combos when focus is in the shell chrome (calls the existing button handlers or forwards via `bridge.command`), and `bridge.on("shortcut", …)` to fire comment / show-shortcuts when the runtime forwarded them.

### Bridge event contract (binding — both sides build to it)

`emit("shortcut", { action })` where `action ∈ { "comment", "show-shortcuts" }`. The shell's `bridge.on("shortcut", ({action}) => …)` maps `"comment"` → the `#comment-btn` flow, `"show-shortcuts"` → open the overlay.

### Cheat-sheet overlay

A **"?"** `tb-ico` button (`#shortcuts-btn`) added to the topbar next to `#redo-btn`. New `app/js/shell/shortcuts-help.js` builds a modal overlay listing all shortcuts grouped **Text** (bold, italic, A+/A−) · **Components** (copy, paste, paste-into-layout, delete) · **Editing** (comment, undo, redo, show-shortcuts). Opens on the "?" click or `Ctrl+/`; closes on outside-click or `Esc`. Pure shell UI, styled in `app/css/shell.css` with the existing tokens; no runtime involvement.

## Edge Cases & Error Behavior

| Case | Required behavior |
|------|-------------------|
| `Ctrl+Alt+C` | opens the comment composer; MUST NOT trigger Chrome's inspector (that is `Ctrl+Shift+C`, deliberately avoided) |
| `Ctrl+Del` while editing / on last region | blocked, identical to `#delete-btn` (the runtime `delete-element` handler returns `{blocked:…}`) |
| Plain `Delete` / `Backspace` | inert — NO component delete (compat with `test_r3_delete::test_no_keyboard_delete`); shortcuts.js owns `Ctrl+Del` ONLY |
| `Ctrl+C`/`Ctrl+V` while a text edit is active or a real text selection exists | NOT intercepted — native browser copy/paste (D4); guard in shortcuts.js |
| Existing toolbar buttons | keep working unchanged; shortcuts are additive |
| Overlay open, press `Esc` | closes the overlay (and only that; does not also exit an edit) |

## Out of Scope

- Copy/paste **behaviour** (clipboard, float/insert paste) — specified in `copypaste-spec.md`; P2 only reserves the keys/guards conceptually, the actual copy/paste keys + pointer tracking are added to `shortcuts.js` in P3.
- Any change to what the comment composer or delete handler DO.

## Test Plan

Headed, real keyboard, real deck. Build-phase e2e headless in `tests/e2e/`.

| # | Criterion (owner-observable) | Gesture | Expected result | Evidence captured |
|---|------------------------------|---------|-----------------|-------------------|
| C3 | Comment shortcut | select a component; press `Ctrl+Alt+C` | the comment composer opens for that component; Chrome's inspector does NOT open | screenshot of the open composer |
| C4 | Delete shortcut | select a component; `Ctrl+Del` deletes it; try while editing and on the last region (blocked); press plain `Delete`/`Backspace` | `Ctrl+Del` deletes; blocked while editing and on last region; plain `Delete`/`Backspace` do nothing | before/after screenshots + tray/region count |
| C5 | Cheat-sheet | click **"?"** then press `Ctrl+/`; press `Esc`; click outside | the overlay opens listing all shortcuts grouped; `Esc`/outside-click closes it | screenshots open + closed |

> Fidelity floor: visible browser + real key events on the real app; evidence files written during the exercise.

## Return Expectations

`status` · `landed` (files + local commit hash on `master`) · `validation` (`node --check` on touched JS + the shortcuts pytest + `test_r3_delete`, each EXIT + WALL_MS; skips with reasons) · `concerns` · `open_questions`.
