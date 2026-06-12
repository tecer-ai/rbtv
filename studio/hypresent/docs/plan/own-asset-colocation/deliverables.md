# Deliverables Map - Own-Asset Colocation

> **Single index of every artifact this plan produces.**
>
> **Every agent working on this plan MUST:**
> 1. Read this file BEFORE starting any task — it tells you the exact path your output must land at.
> 2. UPDATE this file AFTER delivering — flip the Status to ✅ and confirm the Path matches what you produced.
> 3. EDIT Status/Path cells in place — this file is mutable (unlike append-only decisions.md); NEVER append duplicate rows to record a status change. A task added during execution gets a `pending` row in its phase table; a removed task's row is ~~struck~~, never deleted.
>
> The final checkpoint (`p2-checkpoint`) reads this map to confirm every artifact landed. The index being accurate is a hard dependency, not a courtesy.
>
> **Path anchor:** `server/…` and `tests/…` paths are relative to the hypresent app dir `3-resources/tools/rbtv/studio/hypresent/`.

---

## Phase 1 deliverables

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p1-1 | Own-asset copy + collision-safe rename/rewrite in the save handler (and the recompose override, if used) | `server/deck_api.py`, `server/recompose.py` | ✅ |
| p1-2 | Unit tests for own-asset behavior (spec test plan rows 1-5) + any recompose-override tests | `tests/test_deck_api.py`, `tests/test_recompose.py` | ✅ |
| p1-checkpoint | Phase 1 evaluation findings + user approval | `./decisions.md` (Checkpoint entry) | ✅ |

## Phase 2 deliverables

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p2-1 | Headed done-gate evidence — real deck copy renders own images in builder + editor (incl. collision case) | `./phase-2/done-gate-evidence/` | ⏸ deferred (done-gate PROVEN editor-render + disk colocation; surfaced the p2-3 live-path bug + builder srcdoc gap) |
| p2-2 | Save-to-new-dir own-asset regression assertion | `tests/e2e/test_pb11_deck_save.py` | pending |
| p2-3 | BUG fix — real builder save-to-new-dir copies no own-assets (live-path divergence) | `server/deck_api.py` / live save path (TBD at root-cause) | pending (next session) |
| p2-refs | Plan-folder link validation result | `./decisions.md` (Discovery entry only if a violation is found) | pending |
| p2-checkpoint | Final evaluation findings + user approval to complete | `./decisions.md` (Checkpoint entry) | pending |

**Status values:** `pending` | `in-progress` | `✅` | `⏸ deferred` — deferrals carry a parenthetical reason in the cell.

---

## How the final checkpoint consumes this index

A fresh agent at `p2-checkpoint` reads, in order:

1. **This file (`deliverables.md`)** — the artifact index.
2. `./decisions.md` end-to-end — every Decision and Discovery; the running rationale.
3. `./specs/own-asset-colocation-spec.md` — the behavior + test plan to evaluate against.
4. The Phase 2 done-gate evidence under `./phase-2/done-gate-evidence/`, and the test logs.

---

## Sub-folder creation

`./phase-1/`, `./phase-2/`, `./phase-2/done-gate-evidence/`, `./specs/` — created on demand by the first task that needs them; never pre-created empty.
