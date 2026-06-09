# Spec — Deck Ingest (Open Deck in Builder)

## Goal

The owner can click "Open deck…" in the builder (or arrive via `/app/builder.html?file=<path>`), pick an existing presentation, and see its slides as an ordered tray of correct thumbnails rendered with the deck's own theme.

## Context Snapshot

**Builder boot** (`app/js/builder/builder-main.js`): on `DOMContentLoaded` it wires the library pick (`handlePickLibrary` via `pickAndLoadLibrary()`), the tray (`createTray({ listEl: trayList, onChange })`), browse pane, and the assemble button. There is currently NO deck-open concept — `state` is `{ libraryPath, data, tray, slideLookup }`.

**Builder mode model (new):** opening a deck puts the builder in **deck mode** — `state.deck = { path, name, dir, sections }` (sections from `/api/deck-load`). Deck mode and library state coexist: the library browse remains usable for adding slides (tray-compose-spec). The assemble flow remains the no-deck mode; in deck mode the assemble button is replaced by the deck save controls (deck-save-spec owns save UI).

**`/api/deck-load` contract** (`server/deck_api.py`, backed by `recompose.split_sections`): payload `{"path": str}` → `{"ok": true, "name": str, "dir": str, "head": str, "sections": [{"index": int, "html": str}]}`. `head` is the deck's `<head>` inner HTML with `<script>` elements removed (style/meta survive — enough to render thumbnails). Non-conforming deck (zero sections) → `{"error": ...}` surfaced in the builder status bar (`setStatus(msg, 'error')` idiom).

**Native open dialog:** `handle_dialog_open` (`server/api.py`) shows the file picker and currently delegates to `handle_open` (which re-points `/doc/`). Deck ingest needs the PATH only — `server/deck_api.py` exposes `handle_dialog_open_path` reusing `_launch_dialog("open")` (injectable via `set_dialog_launcher`), returning `{"path": ...}` or `{"cancelled": true}`.

**Thumbnail idiom** (`app/js/builder/previews.js`): library thumbs build `srcdoc` via `buildSrcdoc(theme, fragment)` → `<!DOCTYPE html><html><head><style>${theme}</style></head><body>${fragment}</body></html>`, fetched lazily. Deck thumbs follow the same srcdoc pattern but compose from the deck's `head` + the section's `html` (scripts already stripped server-side); no fetch needed — content arrived with deck-load.

**Tray rows** (`app/js/builder/tray.js`): `model` records are `{id, title, kind, lang}` keyed by library slide id, thumbnails via `getSlideSrcdoc(libraryPath, rec.id)`. Deck rows need a different srcdoc source — the row model gains a per-row srcdoc provider (exact mechanism is executor judgment; tray-compose-spec defines the row-kind model).

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Owner clicks "Open deck…" in the builder topbar | Native open dialog appears (Windows file picker, `.html` filter) |
| 2 | Owner picks a conforming deck | Tray fills with one row per top-level `<section>`, in document order, numbered 1..N; the deck's filename shows in the topbar |
| 3 | Tray rows render | Each thumbnail shows that slide rendered with the deck's own theme (recognizable content, not blank/unstyled) |
| 4 | Owner cancels the dialog | Builder state unchanged; no error shown |
| 5 | Owner picks a non-conforming file (no `<section>`s) | Status bar shows the error; tray unchanged |
| 6 | Builder is opened as `/app/builder.html?file=<path>` | Same result as gestures 1-2 without the dialog (the bridge arrival path) |
| 7 | A deck is already open and owner opens another | The new deck replaces the tray contents (confirm prompt if the tray has unsaved changes) |

## Edge Cases & Error Behavior

| Case | Required behavior |
|------|-------------------|
| Deck with one single slide | One-row tray; everything still works |
| Large deck (30+ slides) | Tray scrolls; thumbnails lazy-render (reuse the IntersectionObserver idiom if needed) |
| Deck whose sections contain heavy media | Thumbnails stay decorative — a failed thumb render never breaks the row (mirror `catch(() => {})` in `tray.js`) |
| File deleted between dialog and load | Status-bar error; builder state unchanged |

## Out of Scope

- Editing slide content; slide-stage expand for deck rows (library browse keeps its own).
- Watching the file for external changes.
- The save path (deck-save-spec) and row manipulation semantics (tray-compose-spec).

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Open deck → full tray | Playwright headed e2e (`tests/e2e/test_pb8_deck_open.py`): inject dialog launcher to return a copy of a real root deck; click "Open deck…" | Row count equals the deck's section count; order matches document order | screenshot + pytest log |
| 2 | Thumbnails themed | Same e2e: assert each row iframe srcdoc contains the section markup and head styles; visual check headed | Thumbnails visibly render slide content | screenshot |
| 3 | Non-conforming file rejected | e2e: dialog returns a sectionless HTML file | Status bar error; tray empty | screenshot + pytest log |
| 4 | `?file=` arrival | e2e: navigate to `/app/builder.html?file=<deck>` | Tray filled, no dialog | pytest log |

> Every criterion obeys the **Fidelity floor** + **Evidence plausibility** rules: real app headed, owner's real deck copies, evidence files written during the exercise; implausibly fast timings are auto-reject + rerun.

**Fidelity floor for every criterion:** the real application running whole, on the owner's real data when one exists; UI criteria use a visible browser + real input, never synthetic `dispatchEvent`. Evidence is a file on disk written DURING the exercise. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker.

## Return Expectations

Files changed, validation commands run + exit codes + skips with reasons, local commit hash if committed, concerns, blockers. The report is a hint; the repo state is the truth.
