# State Capsule — own-asset-colocation

> Mutable file, but entries are append-only per `_shared/authoring/decisions-discipline.md`. Follow it. Planning decisions belong in `decisions.md`, not here.

> **Audience:** the next conductor session, resuming after interruption or context-refresh. Everything here exists to make resumption clean.

> **Regenerate, don't edit:** at each boundary write re-instantiate from the skeleton carrying ONLY live values. Carry pointers, not narratives. State each volatile fact EXACTLY ONCE.

---

## Resume Point

- **Last completed:** p2-6 resolved (second save endpoint); owner re-test PASSED
- **Next dispatch:** focused opus review of p2-7 diff -> commit wave (rbtv-commit) -> p2-checkpoint complete -> close
- **Last update:** 2026-06-12T16:34Z

## Run Configuration

- **Run mode:** halt
- **Context-refresh:** suggest
- **Plan path:** `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent\docs\plan\own-asset-colocation\own-asset-colocation-plan.md`
- **Decisions file:** `…/own-asset-colocation/decisions.md`
- **Code backend:** CLI fleet — codex executes, Claude opus reviews (Kimi out of credits, D1)

## Approved Delegation Map

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|
| B-live | 2 | p2-6 (owner-flow divergence) | live-debug-with-owner (Step-0 owner narration; then conductor probes or top-tier debug worker) | HALT (human) | — |

## Completed Batches

| Batch | Phase | Tasks | Worker | Status | Reviewer |
|-------|-------|-------|--------|--------|----------|
| B1-B3 | 1 | p1-1, p1-2, p1-checkpoint | codex (build) + opus (review) | DONE — committed `3ce0400`, 52/52 green | opus §2 PASS + owner approved |
| B4, B-bug, B5, B6 | 2 | p2-1, p2-3, p2-2, p2-refs + checkpoint-eval | sonnet / opus / codex | DONE (see run-log) — editor render, root-cause evidence, e2e regression test, all-PASS review | conductor gates PASS |
| B7 | 2 | p2-4 (warning) | codex 0.137.0 / gpt-5.5 (default) | DONE — warning headed-proven (`p2-4-warning-probe.json`); 64/64 | conductor gate PASS + re-checkpoint opus PASS |
| B8 | 2 | p2-5 (chrome colocation) | codex 0.137.0 / gpt-5.5 (default) | DONE — real gsmm deck: all 8 assets + editor cover-bg render (`p2-5-real-gsmm-proof.json`); 67/67 | conductor gate PASS + re-checkpoint opus PASS |

## Active Red Sets

| Red set (test file — exact path) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------------------|--------------------------|---------------------------|

## Active Doubts / Blockers

- **Doubt escalated:** none
- **Blocker:** **p2-6 — the OWNER's real save still copies no assets after p2-4+p2-5, while every probe (direct handler ×2 real gsmm decks; headed builder UI ×3 decks incl. the real gsmm intro = all 8 assets) is green. The divergence lives in something his flow does that no probe replicated. Full corpus + investigation order in `./phase-2/p2-6.task.md`.**
- **Checkpoint awaiting user approval:** p2-checkpoint REJECTED twice (option-B ruling, then failed re-test); re-runs only after p2-6 closes.

## Notes for Resuming Conductor

- **UNCOMMITTED VALIDATED WAVE — parallel-session exposure.** p2-4+p2-5 code sits uncommitted in the rbtv working tree: `studio/hypresent/server/deck_api.py`, `app/js/builder/{builder-main,deck-save}.js`, `tests/test_deck_api.py`, `tests/e2e/test_pb11_deck_save.py`, `tests/e2e/p2_3_live_repro.py` (+ plan-state under `docs/plan/own-asset-colocation/**`). HEAD moved to `08206c9` via a parallel session mid-run. Before ANY staging: `git status` + per-file `git diff` to confirm the deltas survive; commit via `rbtv-commit`, explicit pathspecs, never `git add -A`. A parallel `git restore` would wipe validated work — p2-6 names the re-derivation sources if that happens.
- **Owner's deck candidates:** real (WITH assets): `5-workbench/tecer-biz/prospects/gsmm/presentations/2026-06-02-introduction/tecer-gsmm-introduction.html`, `…/2026-06-11-board/tecer-gsmm-board-v8.html`. Trap copies (NO assets, KEEP as repro material until p2-6 closes): hypresent root `tecer-gsmm-introduction.html`, `tecer-gsmm-introduction-test-v3.html`.
- **Vault follow-ups captured in `2-areas/rbtv/rbtv-tasks.md` (2026-06-12):** builder srcdoc `<base>` gap; flaky `test_r2_resize_real.py::test_control_box_aligns_with_target`; `assets_renamed` not surfaced in builder status bar. The main vault task carries the p2-6 pointer.
- hypresent server: `python server/server.py` on 127.0.0.1:8765, stdlib http.server, **NO auto-reload** (restart to load the uncommitted code). `python -m pytest` from the hypresent app dir. codex sandbox can't run repo python → conductor runs all validation. Known pre-existing flakes (outside the named 3-file suite): `test_f5_comments.py::test_tagging_does_not_move_marker`, `test_r2_resize_real.py::test_control_box_aligns_with_target`.
