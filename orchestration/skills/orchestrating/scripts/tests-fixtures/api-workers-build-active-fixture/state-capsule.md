# State Capsule — api-workers-build

> **Mutable file — overwriting is the contract.** This is the TERMINAL capsule.

> **RUN CLOSED 2026-06-09T20:33Z — PLAN COMPLETE PENDING USER ACTION (owner approved at p6-checkpoint, option A; recorded as D-exec-16).** Nothing is in flight; nothing resumes. A future session touching this build starts from the durable record, not from this capsule.

---

## Resume Point

- **NEXT: dispatch p3-1 to kimi** — Claude Agent-tool package (opus/sonnet tiers) build pending, then update routing card §2a.
- **Where everything lives:**
  - Audit: `run-log.md` (events + Exit Scorecard) · Decisions: `decisions.md` (D1–D3, D-exec-1..16, ADX-1..4) · Artifact index: `deliverables.md` · Learnings: `learnings.md` (processed at p6-compound)
  - Evidence: `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/` — 6 build sheets (deepseek-pilot, chat-duo, deterministic-routing, conductor-integration, manus-pilot, orchestrated-pilot + captures)
  - Compound PRDs: `.user/compounds/rbtv-orchestrating/` (4 new, 2026-06-09) — tracked in `2-areas/compounds/compounds-tasks.md`
  - Follow-on tasks: `1-projects/rbtv-evolution/rbtv-evolution-tasks.md` — [Must] owner install run (crit 7) · [Should 📅 2026-07-15] cleanup batch (D-exec-10/11/15; deepseek-chat deprecates 2026-07-24) · [Could] D-exec-14 Manus artifact fetch, D-exec-4 qwen-code
  - rbtv deliverable commits: `d4d6e498 … 11dcb38` (ancestry verified under the parallel-session-advanced HEAD `e9ce107`)
- **Last update:** 2026-06-09T12:00Z

## Run Configuration

- Run mode was end-to-end; plan + decisions paths as in the record above. (Closed — configuration retained for audit only.)

## Approved Delegation Map

(Closed — the map served the run; see `run-log.md` for the per-dispatch record.)

## Completed Batches

| Batch | Phase | Status |
|-------|-------|--------|
| Phases 1–5 | 1–5 | ✅ all checkpoints APPROVED (detail: run-log + deliverables) |
| Phase 6 (p6-1 pilot · p6-refs · p6-compound · p6-checkpoint) | 6 | ✅ ALL CLOSED; owner approved 2026-06-09 (D-exec-16). **PLAN COMPLETE PENDING USER ACTION.** |

## Active Red Sets

(none)

## Active Doubts / Blockers

(none — run closed)

## Notes for Resuming Conductor

- **Do not resume this run — it is closed.** Future work on this build's follow-ons starts from `1-projects/rbtv-evolution/rbtv-evolution-tasks.md` (each task is cold-start sufficient).
- **Standing repo caution (for the cleanup-batch task):** the rbtv repo carries the mirror-install's PAUSED uncommitted footprint AND parallel sessions actively commit to it — re-diff every target against the LIVE tree before staging; commits via `rbtv-commit`, explicit pathspecs, never `git add -A`.
- **Standing dispatch rules born here:** future DeepSeek dispatches use `deepseek-v4-flash`/`v4-pro` ids (D-exec-15); every Manus dispatch demands the deliverable in message text (Learning 4 / PRD); the keystone §2 Claude naming must survive any future routing edit (D-exec-9c).
