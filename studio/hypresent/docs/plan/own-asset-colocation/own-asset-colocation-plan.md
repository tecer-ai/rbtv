---
name: own-asset-colocation
overview: "On save-to-a-new-directory, /api/deck-save copies the source deck's own referenced assets into the destination, with collision-safe rename + scoped ref-rewrite, so own-slide images render in the builder and editor."
---

# Own-Asset Colocation

> Read `decisions.md` for full context, decisions, and constraints.
> Read `./deliverables.md` for the artifact index — where every task lands its output.
> Behavior + test plan: `./specs/own-asset-colocation-spec.md`.
> Task files (`→ path`) contain per-task execution instructions.

## Architectural Constraints

| Principle | Enforcement |
|-----------|-------------|
| Own-asset rewrite is scoped to preserved SOURCE sections only — library/blank sections never rewritten | Unit tests (collision + multi-section) + code review at `p1-checkpoint` |
| With no own-asset collision, every preserved section AND inter-slide separator stays byte-for-byte identical to source | Existing `test_deck_api` / `test_recompose` / `test_pb11` stay green |
| Reuse the existing asset machinery (`_find_referenced_assets`, skip-if-exists, `shutil.copy2`) — no parallel copy path | Code review at `p1-checkpoint` |
| Library-asset behavior (`D-asset-colocation`) is unchanged; only own-assets are added | Spec Behavior row 7 + existing tests green |
| Collision never lets a slide render the wrong image (rename own-asset + rewrite its ref; library keeps the original name) | Spec test rows 4-5; headed proof row 7 |
| Headed proof on a real deck copy (builder reopen + editor) before final approval | `p2-checkpoint` gate, `rbtv-done-gate` floor |

**Execution Rules:**
1. Read `./deliverables.md` before starting any task — it tells you the exact path your output must land at.
2. Update `./deliverables.md` after delivering — flip your task's Status, confirm the Path.
3. Read `decisions.md` before starting any task.
4. One task in progress at a time.
5. Dependencies are sacred — never skip prerequisite tasks.
6. Checkpoints: evaluate work against the review criteria in the checkpoint task file, present findings, HALT for human approval.
7. `decisions.md` is append-only and reserved for Decision/Discovery entries. Never modify previous entries.
8. Internal links use file-relative paths (`./`, `../`); `server/…` and `tests/…` paths are relative to the hypresent app dir `3-resources/tools/rbtv/studio/hypresent/` — run `pytest` from there.

## Revolving Plan Rules

- Simple discovery (<5 min): resolve immediately, document in `decisions.md`.
- Complex discovery: add a new task to the plan, document in `decisions.md`, notify the user.

> `decisions.md` entries: decision + rationale + scope ONLY (+ optional one-word `compoundable` marker for harvest-worthy findings) — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Tasks

### Phase 1: Build — own-asset copy + collision-safe rename/rewrite

- [x] `p1-1` UPDATE `server/deck_api.py` (and `server/recompose.py` if using the override mechanism) to copy the source deck's own referenced assets to the destination with collision-safe rename + section-scoped ref-rewrite, per `./specs/own-asset-colocation-spec.md` → `phase-1/p1-1.task.md`
- [x] `p1-2` UPDATE `tests/test_deck_api.py` (and `tests/test_recompose.py` if recompose changed) with unit tests covering the spec's Test Plan rows 1-5 → `phase-1/p1-2.task.md`
- [x] `p1-checkpoint` **CHECKPOINT** — unit suite green · implementation matches spec + invariants · `decisions.md` audit → `phase-1/p1-checkpoint.task.md`

### Phase 2: Prove — headed done-gate + regression guard

- [~] `p2-1` Run a headed done-gate exercise on a real deck copy (own images + a name-collision case): restructure → save to a NEW directory → verify images render on builder reopen AND in the editor; capture evidence → `phase-2/p2-1.task.md`
- [x] `p2-2` UPDATE `tests/e2e/test_pb11_deck_save.py` with a save-to-new-dir own-asset regression assertion → `phase-2/p2-2.task.md`
- [x] `p2-3` **BUG (blocks the feature)** — the OWNER's real builder save-to-new-dir copies NO own-assets, even though the committed handler (`3ce0400`) passes 52/52 tests AND a direct `handle_deck_save` call copies them. Root-cause the live-path divergence (capture the real `/api/deck-save` payload). Surfaced at `p2-1` (2026-06-12). → `phase-2/p2-3.task.md`
- [x] `p2-refs` Verify all internal plan links resolve and comply with the Plan Linking Standard (internal file-relative; `server/…`,`tests/…` app-relative)
- [x] `p2-4` **Owner ruling (option B)** — `assets_missing` in the `/api/deck-save` response + non-blocking builder warning when preserved sections reference own assets absent beside the source deck. Added at the rejected p2-checkpoint (2026-06-12). → `phase-2/p2-4.task.md`
- [x] `p2-5` **DEFECT (real-deck breakage)** — head-CSS `url("assets/…")` own assets are never colocated (section-span-only scan); the real gsmm deck saves with all backgrounds broken. Extend the copy + `assets_missing` warning to deck chrome. Surfaced by the p2-4 headed probe (2026-06-12). → `phase-2/p2-5.task.md`

- [x] `p2-6` **BLOCKER (owner re-test failed)** — owner's real save STILL copies no assets after p2-4+p2-5 (all probes green; divergence un-replicated). Fresh-context investigation carrying the full session corpus: three open unknowns (server running old uncommitted code? different save entry point — editor/bridge? root-copy file?), Step-0 = ask the owner to narrate one save. → `phase-2/p2-6.task.md`

- [x] `p2-7` **CONFIRMED GAP (owner ruling: fix now)** — the EDITOR/bridge Save-As (`/api/save-as`) writes HTML and copies nothing; give it the same own-asset colocation + `assets_missing` semantics via a factored shared helper. → `phase-2/p2-7.task.md`

### Final gate

- [x] `p2-checkpoint` **FINAL CHECKPOINT** — done-gate evidence sufficient · full `pytest` (unit + e2e) green · refs validated · `decisions.md` audit · user approval to complete → `phase-2/p2-checkpoint.task.md`
