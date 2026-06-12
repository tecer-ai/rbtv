# State Capsule — own-asset-colocation

> Mutable file, but entries are append-only per `_shared/authoring/decisions-discipline.md`. Follow it. Planning decisions belong in `decisions.md`, not here.

> **Audience:** the next conductor session, resuming after interruption or context-refresh. Everything here exists to make resumption clean.

> **Regenerate, don't edit:** at each boundary write re-instantiate from the skeleton carrying ONLY live values. Carry pointers, not narratives. State each volatile fact EXACTLY ONCE.

---

## Resume Point

- **Last completed:** Phase 1 committed `3ce0400` (52/52 green); p2-1 done-gate proved editor-render + disk-colocation but SURFACED a blocker
- **Next dispatch:** p2-3 — root-cause the live builder save-to-new-dir asset-copy BUG (see `./phase-2/p2-3-builder-save-asset-copy-bug.task.md`). Then p2-2, p2-refs, p2-checkpoint.
- **Last update:** 2026-06-12T03:40Z

## Run Configuration

- **Run mode:** halt
- **Context-refresh:** suggest
- **Plan path:** `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent\docs\plan\own-asset-colocation\own-asset-colocation-plan.md`
- **Decisions file:** `…/own-asset-colocation/decisions.md`
- **Code backend:** CLI fleet — codex executes, Claude opus reviews (Kimi out of credits, D1)

## Approved Delegation Map

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|
| B-bug | 2 | p2-3 (live-bug root-cause) | top-tier opus debug role (live-debug-with-owner — needs the real builder + a captured payload) | HALT (human) | — |
| B5 | 2 | p2-2 | codex-cli:default (conductor runs e2e) | opus | — |
| B6 | 2 | p2-refs + p2-checkpoint | claude-code-native:opus | HALT (human) | — |

## Completed Batches

| Batch | Phase | Tasks | Worker | Status | Reviewer |
|-------|-------|-------|--------|--------|----------|
| B1-B3 | 1 | p1-1, p1-2, p1-checkpoint | codex (build) + opus (review) | DONE — committed `3ce0400`, 52/52 green | opus §2 PASS + owner approved |
| B4 | 2 | p2-1 | sonnet (done-gate) | DONE_WITH_NOTES — editor-render + disk-colocation PROVEN; surfaced p2-3 blocker + builder srcdoc gap | conductor cold-verify |

## Active Red Sets

| Red set (test file — exact path) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------------------|--------------------------|---------------------------|

## Active Doubts / Blockers

- **Doubt escalated:** none
- **Blocker:** **p2-3 — real builder save-to-new-dir copies NO own-assets, even on a fresh server, despite committed code passing 52/52 tests AND a direct `handle_deck_save` call copying 5 assets. Live-path divergence UNRESOLVED. Decisive next step: instrument `/api/deck-save`, capture the real payload (`source_path`/`out_path`/`items`/`source_root`/assets existence). Full plan in the p2-3 task file.**
- **Checkpoint awaiting user approval:** run HALTED at owner instruction (capture-not-solve); p2-checkpoint not reached.

## Notes for Resuming Conductor

- **RUN HALTED 2026-06-12 — phase 1 committed `3ce0400`; phase 2 BLOCKED on p2-3 (live builder save bug).** Owner asked to capture + stop, not solve. Resume by executing `./phase-2/p2-3-builder-save-asset-copy-bug.task.md`.
- **Repro that WORKS (code is correct in isolation):** direct `handle_deck_save` on `5-workbench/tecer-biz/investors/_decks/pitch-deck/small-deck-v3/tecer-pitch-deck.html` copies 5 assets (command in the p2-3 task file). The bug is in the LIVE builder→server path only.
- **Source task updated:** `2-areas/rbtv/rbtv-tasks.md` → "Implement own-asset handling…" carries a `_Status (2026-06-12)_` bullet + plan link.
- **Two separate lower-priority follow-ups (decisions.md):** builder thumbnail `srcdoc` `<base>` gap (renders no relative asset, pre-existing, orthogonal); `assets_renamed` not shown in the builder status bar.
- hypresent server: `python server/server.py` on 127.0.0.1:8765, stdlib http.server, **NO auto-reload** (restart to load code). `pytest`/e2e: `python -m pytest` from hypresent (global Python312 has pytest 9.0.3 + playwright chromium 1223). codex sandbox can't run repo python → conductor runs all validation (decisions.md). `rbtv-coding-discipline` skill not installed (rbtv-reasoning-equivalent). stamp.py CLI was reworked mid-run by a parallel session (`--event-type`/`--worker`/`--outcome`/`--next-dispatch`).
