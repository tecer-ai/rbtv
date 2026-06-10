# Deliverables Map - builder-open-deck

> **Single index of every artifact this plan produces.**
>
> **Every agent working on this plan MUST:**
> 1. Read this file BEFORE starting any task — it tells you the exact path your output must land at.
> 2. UPDATE this file AFTER delivering — flip the Status to ✅ and confirm the Path matches what you produced.
>
> The synthesis tasks (p5-compound, p5-checkpoint) read this map to find every input they need. If an artifact lands somewhere this map doesn't list, the synthesis agent will miss it. The index being accurate is a hard dependency, not a courtesy.

---

## Phase 1 deliverables — Save Core

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p1-1 | Recompose engine + unit tests | `server/recompose.py`, `tests/test_recompose.py` | ✅ |
| p1-2 | Deck API handlers + routes + tests | `server/deck_api.py`, `server/server.py`, `tests/test_deck_api.py` | ✅ |
| p1-checkpoint | Phase 1 evaluation findings + headed real-deck evidence + user approval | `./phase-1/evidence/` + `./decisions.md` (Decision entry on rejection only) | ✅ |

## Phase 2 deliverables — Ingest

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p2-1 | Deck-open module, UI entry, `?file=` arrival, e2e | `app/js/builder/deck-load.js`, `app/js/builder/builder-main.js`, `app/builder.html`, `tests/e2e/test_pb8_deck_open.py` | ✅ |
| p2-2 | Deck-themed tray thumbnails + e2e extension | `app/js/builder/previews.js`, `app/js/builder/tray.js`, `app/js/builder/deck-load.js`, `tests/e2e/test_pb8_deck_open.py` (+ `app/js/builder/builder-main.js` stopgap removal per ADX-3) | ✅ |
| p2-checkpoint | Phase 2 evaluation findings + headed evidence + user approval | `./phase-2/evidence/` | ✅ |

## Phase 3 deliverables — Compose

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p3-1 | Heterogeneous tray (uid identity, 3 kinds, duplicate, `getItems()`) + e2e | `app/js/builder/tray.js`, `app/js/builder/tray-sorter.js`, `app/js/builder/builder-main.js`, `tests/e2e/test_pb9_deck_tray.py` | ✅ |
| p3-2 | Deck-mode library add + blank add + e2e | `app/js/builder/builder-main.js`, `app/js/builder/browse-pane.js`, `app/builder.html`, `tests/e2e/test_pb10_deck_add.py` | ✅ |
| p3-3 | Save deck UI (new-file vs overwrite) + e2e | `app/js/builder/deck-save.js`, `app/js/builder/builder-main.js`, `app/builder.html`, `tests/e2e/test_pb11_deck_save.py` | ✅ |
| p3-checkpoint | Phase 3 evaluation findings + headed full-loop evidence + user approval | `./phase-3/evidence/` | ✅ |

## Phase 4 deliverables — Bridge

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p4-1 | Save-and-switch controls both directions + e2e | `app/js/builder/builder-main.js`, `app/builder.html`, `app/js/main.js`, `app/index.html`, `app/js/shell/file-controls.js`, `tests/e2e/test_pb12_bridge.py` | ✅ |
| p4-checkpoint | Phase 4 evaluation findings + headed round-trip evidence + user approval | `./phase-4/evidence/` | ✅ |

## Phase 5 deliverables — Close

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p5-refs | Link-resolution report (all plan links valid per Plan Linking Standard) | `./decisions.md` (Decision entry only if violations found) | pending |
| p5-compound | Compound blocks / PRD proposals from learnings | appended to `./learnings.md` | pending |
| p5-checkpoint | Final evaluation, done-gate evidence sheet, user approval | `./phase-5/evidence/` + `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/` | pending |

**Status values:** `pending` | `in-progress` | `✅` | `⏸ deferred` — deferrals carry a parenthetical reason in the cell.

---

## How the synthesis tasks consume this index

A fresh agent at p5-compound / p5-checkpoint reads, in order:

1. **This file (`deliverables.md`)** — the artifact index.
2. `./decisions.md` end-to-end — every Decision and Discovery; the running rationale.
3. Each artifact referenced above, in document order — they build on each other.
4. `./learnings.md` — meta-observations that may inform the synthesis.

p5-compound folds learnings into compound proposals; p5-checkpoint folds everything into the final v1 acceptance against the structured problem's Success Criteria.

---

## Sub-folder creation

`phase-1/evidence/` … `phase-5/evidence/` (checkpoint capture files), `specs/` (already created). Sub-folders are created on demand by the first task that needs them — never pre-created empty.
