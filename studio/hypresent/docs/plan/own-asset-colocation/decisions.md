# Decisions - Own-Asset Colocation

> **Purpose:** This document captures shaping decisions, discoveries, constraints, and references that future agents need. The Original Shaping section is immutable. Other sections are append-only during routine execution.

---

## Original Shaping

### Scope Definition

**What this accomplishes:**
- On save-to-a-new-directory, `/api/deck-save` copies the source deck's OWN referenced `assets/*` into the destination's `assets/` folder, so own-slide images render on builder reopen AND in the editor.
- Name collisions are resolved by renaming the own-asset and rewriting that ref inside the owning source section(s), so no slide ever renders the wrong image.

**What this does NOT include:**
- Rewriting LIBRARY fragment refs or changing library-asset behavior (ruling `D-asset-colocation` stays).
- Approaches (b) rewrite-all-refs and (c) warn-at-save (owner-rejected).
- Copying the source deck's FULL asset tree — only assets the SAVED deck still references.
- Content-hash dedup of identical assets; same-directory library collisions (pre-existing library behavior, untouched).

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Own-asset handling approach | (a) replicate referenced own-assets into the destination `assets/` folder | Owner choice over (b)/(c); reuses the existing assembler/library-copy machinery |
| Collision handling | (B) rename the colliding own-asset + rewrite its ref inside the owning source section; the original name stays with the library/pre-existing file | Owner choice over skip-on-collision; guarantees no slide renders the wrong image |
| Copy precision | Only assets referenced by PRESERVED source slides (dropped slides' assets skipped) | Matches the library loop's referenced-only precision; no dead-asset bloat |
| Plan type | Plain interactive, code-bearing | Not orchestration-shaped; a behavior spec is authored |
| Done-gate evidence location | In-plan `./phase-2/done-gate-evidence/` | Keeps the plan self-contained; matches the sibling `builder-open-deck` in-plan evidence precedent |
| Recommended rewrite mechanism | Rewrite colliding refs on each preserved section's isolated HTML before splicing (e.g. an optional `html` override on recompose's `existing` item) | Avoids fragile post-recompose result surgery; preserves index→separator semantics. Implementer's call — invariants bind regardless |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Byte-for-byte span preservation (ADX-2) is relaxed ONLY for colliding own-asset refs inside source sections | `recompose` invariant + `deck-save-spec` | Non-colliding sections AND inter-slide separators MUST stay byte-identical; existing faithfulness tests (`test_deck_api`, `test_recompose`, `test_pb11`) must stay green |
| Edit the rbtv SOURCE repo (nested git repo), never `.claude/` | `rbtv-source-of-truth` | This is hypresent APP code, not an rbtv component → no module-manifest/README docs-sync needed |
| Don't overengineer | Owner instruction | Minimal diff, reuse existing helpers, no speculative options; 2 phases / 2 checkpoints |
| Headed proof on a real deck copy (builder + editor) | `rbtv-done-gate` floor | A prose claim does not close the feature; evidence file on disk required |
| Before any staging, re-check the rbtv repo's foreign uncommitted state; explicit pathspecs, never `git add -A` | `rbtv-commit` + parallel-session discipline | The rbtv repo carries uncommitted state from parallel tasks |

### User Inputs

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Approach | "i want the go with the option that it replicates the asset files in an assets folder in the destination folder" | Locked approach (a) |
| 2 | Plan scope | "lets not overengineer the plan" | Lean structure: 2 phases, 2 checkpoints, minimal diff, reuse over new abstractions |
| 3 | Collision handling | "why not make the hypresent system rename the asset, just appending smth to its name?" | Decision B (rename + scoped ref-rewrite) |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Collision strategy | Rename the colliding asset | Flagged that file-rename alone 404s (preserved HTML still refs the old name) → requires rewriting the ref, which relaxes byte-for-byte preservation and is approach (b) for the collision case; offered A (skip+report) / B (rename+rewrite) / C (flip precedence) | Owner chose **B** with the tradeoff explicit; AI added the safety invariants: rewrite scoped to source sections only, one-name consistency map, boundary-safe replacement, 1:1 item→section guard, `assets_renamed` response surface |

---

## Standards Applied

### RBTV Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| `rbtv-planning` | This plan's structure and artifacts |
| `rbtv-coding-discipline` | Phase 1 implementation discipline |
| `rbtv-done-gate` | Phase 2 headed proof on a real deck copy |
| `rbtv-source-of-truth` | Edit the rbtv source repo, never installed `.claude/` copies |
| `rbtv-commit` | Commits with explicit pathspecs after foreign-state re-check |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Own-asset rewrite scoped to preserved SOURCE sections only | Unit tests (collision + multi-section) + code review at `p1-checkpoint` |
| Non-colliding sections + separators stay byte-for-byte | Existing `test_deck_api` / `test_recompose` / `test_pb11` stay green |
| Library-asset behavior unchanged | Unit test (Behavior row 7) + existing tests green |
| Paths anchor to the hypresent app dir `3-resources/tools/rbtv/studio/hypresent/` | `pytest` run from there; task Context Files use app-relative paths |

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")

> `decisions.md` entries: decision + rationale + scope ONLY (+ optional one-word `compoundable` marker for harvest-worthy findings) — never file-lists or N→M narratives; supersede by appending, never rewrite.

<!-- Decisions and discovery entries will be appended below this line -->

**Discovery (2026-06-12) — codex `workspace-write` sandbox cannot execute repo Python.** `compoundable`
Decision: the CONDUCTOR runs all `pytest`/e2e validation for codex-executed code tasks; codex dispatches do NOT require the worker to self-validate. Rationale: codex's sandbox denies PATH python (`python`/`py`/`python3` → EXIT 127) and its `uv`-managed python lacks `pytest` with PyPI network blocked — so codex writes code/tests correctly but cannot run them (p1-1 hit it as pytest-EXIT-2, p1-2 as the python-127 `BLOCKED`; both validated green by the conductor's `python -m pytest`). Scope: affects p2-2 (codex e2e test — conductor runs the e2e suite, not codex) and any future codex code task in this plan.

**Discovery (2026-06-12) — `rbtv-coding-discipline` skill referenced by the task files does not exist.**
Decision: treat the `rbtv-coding-discipline` references in `p1-1.task.md` / `p1-2.task.md` (Tools tables) as the equivalent discipline already binding via `rbtv-reasoning` (minimal diff, reuse helpers, surgical changes, read-before-write); do NOT block on the missing skill. Rationale: the skill is absent from `.claude/skills/` and from every rbtv source module (the `coding/` module ships only a `done-gate` skill + `done-gate`/`non-technical-user` rules) — confirmed at the p1-checkpoint opus review. Scope: phase-1 tasks (done under the equivalent standard); a plan/task-file fix to drop or repoint the reference is a follow-up, not a blocker.

**Discovery (2026-06-12) — the spec's "render in the BUILDER" criterion is structurally unachievable for ANY relative-path deck asset (pre-existing, orthogonal to colocation).** `compoundable`
Decision: the own-asset-colocation feature is judged DELIVERED on disk-colocation + EDITOR render (both proven at the headed done-gate, p2-1); the builder-reopen render sub-claim (spec Goal + Test Plan row 7) is `unexercisable` against the current builder, NOT a colocation failure. Rationale: the builder renders slide thumbnails/stage via `srcdoc` iframes (`app/js/builder/previews.js`, `tray.js`, `slide-stage.js`) with NO `<base>` tag, so every relative `assets/...` ref resolves to the builder page origin (`/app/assets/...`) and 404s — for own, library, AND pre-existing assets alike; file placement cannot fix it. The editor (`/doc/` route, `server.py` `set_doc_root`) serves the deck from its real directory, so colocated assets resolve and render there (done-gate: own + collision images `naturalWidth=1`). The colocation feature copies the files to the correct location and rewrites collision refs correctly (proven on disk + editor). Scope: closes the "render in builder" expectation as a SEPARATE pre-existing builder-rendering gap (a `<base>`-tag fix in the srcdoc machinery) — a follow-up, not part of this feature. Owner decides acceptance at p2-checkpoint.

**Discovery (2026-06-12) — BLOCKER: the real builder save-to-new-dir copies NO own-assets, despite the committed handler passing all tests AND a direct call copying them.** `compoundable`
Decision: the feature is NOT done; a new task `p2-3` is added to root-cause the live-path divergence next session, and the run halts here at the owner's instruction. Rationale: the owner saved a real gsmm/tecer deck from the builder to the Desktop and no `assets/` folder / images were copied — re-tested on a FRESH server, same failure. Yet (a) the committed code `3ce0400` passes 52/52 unit+e2e tests, and (b) a direct `handle_deck_save` call on the real `small-deck-v3/tecer-pitch-deck.html` copies 5 assets (STATUS 200). DISPROVEN: stale/pre-patch server (fresh server reproduces), assets-outside-`<section>` (refs verified inside section bodies), open-flow path re-point (`api.py` resolves the real path). The bug is in the REAL builder→server save path, in something the direct repro does not replicate — prime suspect: the actual `source_path` the builder POSTs may point to a dir without `assets/` beside it (silent skip via Behavior row 5), or the live server runs stale bytecode / a different instance, or the restructured `items` shape diverges. Scope: blocks plan completion; full investigation plan + repro + suspects in `./phase-2/p2-3-builder-save-asset-copy-bug.task.md`. Next session captures the real `/api/deck-save` payload (instrument the handler) as the decisive evidence.

---

## References

> **Path format:** External files (outside this plan folder) use paths relative to the hypresent app dir (`3-resources/tools/rbtv/studio/hypresent/`). Internal files (within this plan folder) use file-relative paths (`./`, `../`).

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `server/deck_api.py` | `handle_deck_save` + existing library asset-copy loop, `_find_referenced_assets`, `_ASSET_RE`, skip-if-exists, response shape |
| `server/recompose.py` | `split_sections` / `recompose` — sections preserved verbatim; one output section per item; separator logic keyed on `existing` index |
| `tests/test_deck_api.py` | Unit conventions; `test_deck_save_fragment_and_blank_with_assets`, `test_deck_save_asset_collision_skip`, `test_deck_save_overwrite_in_place` are the templates to extend |
| `tests/e2e/test_pb11_deck_save.py` | Headed harness: playwright, `_copy_deck`, `_open_deck`, fake dialog |
| `docs/plan/builder-open-deck/decisions.md` (`D-asset-colocation`) | The accepted v1 limitation this feature removes |
| `docs/plan/builder-open-deck/specs/deck-save-spec.md` | The deck-save behavior + ADX-2 byte-for-byte contract this spec extends |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `./specs/own-asset-colocation-spec.md` | Behavior + test plan source of truth | p1-1, p1-2, p2-1, p2-2 |
| `server/deck_api.py`, `server/recompose.py` | Implementation surfaces | p1-1 |
| `tests/test_deck_api.py`, `tests/test_recompose.py` | Unit test homes | p1-2 |
| `tests/e2e/test_pb11_deck_save.py` | e2e regression home | p2-2 |
