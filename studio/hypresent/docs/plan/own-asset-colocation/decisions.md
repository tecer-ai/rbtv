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
