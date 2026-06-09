# Spec — Builder↔Editor Bridge (Save-and-Switch)

## Goal

The owner can cross from the builder to the editor (and back) without losing work: every crossing runs a Save-As (writes a NEW file, never overwrites), then opens that file in the target view.

## Context Snapshot

**Existing handoff, builder→editor** (`app/js/builder/builder-main.js`, assemble success path): `window.location.href = '/app/?file=' + encodeURIComponent(result.output);`. The editor consumes it (`app/js/main.js`): `const fileParam = new URLSearchParams(location.search).get("file");` — the comment there warns the value is ALREADY percent-decoded; never decode again. The editor then `openFile(fileParam, iframe)` and sets the doc chip.

**Editor→builder (new):** the editor gains an "Open in builder" control (topbar, near the existing Open/Save controls in `app/js/shell/file-controls.js`). Gesture: serialize the current document (the existing `serializeDoc()` → strip-only serializer), Save-As via the native dialog (`/api/dialog-save-as` writes the html and returns `{ok, path}`), then `window.location.href = '/app/builder.html?file=' + encodeURIComponent(path)`. The builder's `?file=` arrival is deck-ingest-spec gesture 6.

**Builder→editor (new):** a "Switch to editor" control in deck mode. Gesture: pick a NEW path via the path-only save dialog (`/api/dialog-save-path`, deck-save-spec), `/api/deck-save` the tray to it, then navigate to `/app/?file=<that path>` (the existing handoff). The Save-As dialog's native overwrite prompt exists, but the crossing flow always proposes a fresh filename (e.g. `{name}-restructured.html`) — the owner may override; the write itself goes wherever they confirmed.

**Cancel semantics:** the native dialogs return `{cancelled: true}`; a cancelled crossing leaves the current view untouched.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Owner clicks "Switch to editor" in the builder (deck mode, tray non-empty) | Native Save dialog appears; on confirm, the restructured deck is written to the chosen NEW file and the editor opens it (doc chip shows its name) |
| 2 | Owner clicks "Open in builder" in the editor with a deck open | Native Save dialog appears; on confirm, the serialized document is written to the chosen file and the builder opens it with a full tray |
| 3 | Owner cancels either dialog | No file written; the current view stays exactly as it was |
| 4 | Round trip builder → editor → builder | Each crossing writes a distinct new file; the final tray shows the deck as last saved; no work lost |
| 5 | Crossing with content the editor added (filled text, comments) | The builder tray thumbnails show the edited content (sections are re-split from the saved file) |

## Edge Cases & Error Behavior

| Case | Required behavior |
|------|-------------------|
| Builder tray empty | "Switch to editor" disabled |
| Editor has no document open | "Open in builder" disabled (mirror the existing Save control's disabled state) |
| Save fails (e.g. parent dir vanished) | Status-bar error in the current view; NO navigation |
| Deck-save returns an error mid-crossing | Same: error surfaced, navigation aborted |

## Out of Scope

- Live shared state, unsaved-state transfer, or merging the two pages (D20 stands).
- Overwrite crossings (explicit in-builder save owns overwrite; crossings always Save-As).

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Builder→editor crossing | Playwright headed e2e (`tests/e2e/test_pb12_bridge.py`): open deck copy, reorder, click "Switch to editor" (injected dialog returns a temp path) | New file exists; editor URL carries `?file=`; doc chip shows the new name | screenshot + pytest log |
| 2 | Editor→builder crossing | e2e: open a deck in the editor, click "Open in builder" (injected dialog) | New file exists; builder tray filled from it | screenshot + pytest log |
| 3 | Cancel leaves view intact | e2e: dialog launcher returns None | No navigation, no new file | pytest log |
| 4 | Round-trip preserves work | e2e: builder reorder → editor → builder; compare final tray order to the reorder | Order survives the round trip | pytest log + saved files |

> Every criterion obeys the **Fidelity floor** + **Evidence plausibility** rules: real app headed, real gestures, evidence files written during the exercise; implausibly fast OS-dialog timings are auto-reject + rerun.

**Fidelity floor for every criterion:** the real application running whole, on the owner's real data when one exists; UI criteria use a visible browser + real input, never synthetic `dispatchEvent`. Evidence is a file on disk written DURING the exercise. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker.

## Return Expectations

Files changed, validation commands run + exit codes + skips with reasons, local commit hash if committed, concerns, blockers. The report is a hint; the repo state is the truth.
