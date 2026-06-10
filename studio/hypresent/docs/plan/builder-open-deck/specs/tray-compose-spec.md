# Spec — Heterogeneous Tray Compose

## Goal

With a deck open in the builder, the owner can reorder, remove, and duplicate its slides, add blank placeholders, and add slides from any library — all in ONE tray — and then save the result (save gesture itself: deck-save-spec).

## Context Snapshot

**Current tray** (`app/js/builder/tray.js`): `createTray({listEl, onChange})` keeps `const model = []` of `{id, title, kind, lang}`; `add(rec)` dedups by id (`if (model.some(m => m.id === rec.id)) return;`); rows render with grip, position number, srcdoc thumb iframe, title, and a remove button; `attachSorter(listEl, {onReorder})` (pointer-events sorter in `tray-sorter.js`) syncs DOM order back to the model by `dataset.slideId`; `getOrder()` returns ids.

**Row identity must change:** deck mode allows DUPLICATE rows (same existing slide twice) and three row kinds, so id-keyed identity breaks. Every row gains a unique `uid` (monotonic counter); `dataset.slideId` keying and the sorter's id round-trip move to `uid`. Row kinds:

| kind | payload | thumbnail source | dedup |
|------|---------|------------------|-------|
| `existing` | `{index}` into the open deck's sections | deck `head` + section html (srcdoc, from deck-load) | duplicates ALLOWED |
| `library` | `{libraryPath, slideId, title, lang}` | `getSlideSrcdoc(libraryPath, slideId)` (`previews.js`) | dedup per (libraryPath, slideId), matching current behavior |
| `blank` | none | a static placeholder srcdoc | duplicates ALLOWED |

**Library add** (`app/js/builder/builder-main.js`): browse cards toggle via `onTag` (`if (tray.has(rec.id)) tray.remove(rec.id); else tray.add(rec)`), the slide-stage `onAdd` adds, `markTrayState(order)` badges browse cards with in-tray state. In deck mode the same browse pane and gestures feed the deck tray with `library` rows. `markTrayState` receives only library rows' slide ids.

**Duplicate gesture (new):** each row gets a duplicate control (mirroring the remove button idiom); duplicating an `existing` or `blank` row inserts a copy with a fresh `uid` directly after it. Duplicating a `library` row is NOT offered in v1 (dedup rule above).

**Add blank (new):** an "Add blank slide" button near the tray appends a `blank` row. This is the approved sibling feature landing here.

**Tray → save items mapping:** `getItems()` (new) returns the ordered list `[{kind:"existing", index} | {kind:"library", library_path, slide_id} | {kind:"blank"}]` — exactly the `/api/deck-save` items contract (deck-save-spec).

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Owner drags a row by its grip to a new position | Order updates, numbers renumber 1..N, all three kinds drag identically |
| 2 | Owner clicks a row's remove button | Row disappears; numbers renumber |
| 3 | Owner clicks duplicate on an existing/blank row | An identical row appears right after it with its own thumbnail |
| 4 | Owner clicks "Add blank slide" | A visibly-blank placeholder row appends to the tray |
| 5 | Owner loads a library (existing pick flow) with a deck open | Browse pane fills; deck tray is untouched |
| 6 | Owner clicks a browse card / stage Add with a deck open | A `library` row appends to the deck tray; the card badges as in-tray |
| 7 | Owner clicks the same browse card again | The library row is removed (toggle), matching current behavior |
| 8 | Mixed tray exists | Existing, library, and blank rows are visually distinguishable (e.g. a kind badge) yet uniformly draggable |

## Edge Cases & Error Behavior

| Case | Required behavior |
|------|-------------------|
| Removing ALL rows | Tray empty state; save disabled (nothing to write) |
| Duplicate then remove the original | The copy survives (uid identity, not id identity) |
| Library changed (Change library…) after adding rows from the previous library | Already-added rows keep their stored `libraryPath` and stay valid |
| Reorder during thumbnail load | Row stays functional; thumb fills in when ready (existing decorative-thumb rule) |
| No deck open (assemble mode) | Tray behaves exactly as today — library-only, id-keyed dedup, assemble button; zero regression |

## Out of Scope

- Theme reconciliation for library rows (they render unstyled in the final deck — accepted).
- Slide-stage expand for existing/blank rows.
- Persisting tray state across page reloads.

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Mixed tray reorder | Playwright headed e2e (`tests/e2e/test_pb9_deck_tray.py` / `test_pb10_deck_add.py`): open deck copy, add library slide + blank, drag rows with real mouse | Final order matches the drag sequence across kinds | screenshot + pytest log |
| 2 | Duplicate | e2e: click duplicate on an existing row | Two rows with same content, independent removal | screenshot + pytest log |
| 3 | Library toggle in deck mode | e2e: load fixture library (`tests/e2e/fixtures/builder-lib/`), click a card twice | Row appears then disappears; badge follows | pytest log |
| 4 | Assemble-mode regression | Run the existing tray e2e (`tests/e2e/test_pb4_tray_reorder.py`) unchanged | Still passes | pytest log |

> Every criterion obeys the **Fidelity floor** + **Evidence plausibility** rules: real app headed, real mouse drags (never synthetic `dispatchEvent`), evidence files written during the exercise; implausibly fast timings are auto-reject + rerun.

**Fidelity floor for every criterion:** the real application running whole, on the owner's real data when one exists; UI criteria use a visible browser + real input. Evidence is a file on disk written DURING the exercise. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker.

## Return Expectations

Files changed, validation commands run + exit codes + skips with reasons, local commit hash if committed, concerns, blockers. The report is a hint; the repo state is the truth.
