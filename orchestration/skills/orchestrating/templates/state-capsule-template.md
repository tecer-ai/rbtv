# State-Capsule Template

Instantiate this as `state-capsule.md` in the run's spine location at spine init (intake §3). It is the run's **mutable, atomic-overwrite resume state** — the small file the NEXT conductor reads to pick up cleanly after interruption or refresh. The State card (`{rbtv_path}/orchestration/skills/orchestrating/cards/state.md`) owns its semantics; this template is the render-ready body. Copy the block below, fill `{run-name}` + the init timestamp, leave the resume point at "intake complete" and the maps/sets empty.

---

## Template

```markdown
# State Capsule — {run-name}

> Mutable file, but entries are append-only per `_shared/authoring/decisions-discipline.md`. Follow it. Planning decisions belong in `decisions.md`, not here.

> **Audience:** the next conductor session, resuming after interruption or context-refresh. Everything here exists to make resumption clean.

> **Regenerate, don't edit:** at each boundary write (batch close, reviewer close, pre-refresh) re-instantiate this file from the template skeleton carrying ONLY live values — never edit the prior capsule in place. Per-row test: "does the NEXT dispatch need this row?" (history → `run-log.md`, rulings → `decisions.md`; carry pointers, not narratives). State each volatile fact — next dispatch, next hard halt, each worker's quota — EXACTLY ONCE.

> **Every claim here is computed, not recalled:** each factual claim written below — the resume point, a status, a count, a "complete" — is COMPUTED from a command AT THE MOMENT OF WRITING, never recalled from having done the thing. `rbtv-deterministic-first`'s Compute gate binds this write; follow it, do not restate it. The agent reading this cannot see what you did — an unverified claim here instructs it to act on a state that does not exist.

---

## Resume Point

- **Last completed:** {phase / batch / task ids — or "intake complete"}
- **Next dispatch:** {phase / batch / task ids — or "FINAL — run complete"}
- **Last update:** {ISO-8601 timestamp}

## Run Configuration

- **Run mode:** {halt | end-to-end | autonomous}
- **Context-refresh:** {suggest | off}
- **Plan path:** {absolute plan path — or NONE (plan-less run)}
- **Decisions file:** {the ONE resolved path — for a plan-backed run, the plan's worker-facing file INSIDE the plan folder (`decisions.md`, or `shape.md` for a pre-D13-rename plan); for a plan-less run, the `decisions.md` INSIDE the spine folder. Never both, never ambiguous.}

## Approved Delegation Map

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|

## Completed Batches

| Batch | Phase | Tasks | Worker | Status | Reviewer |
|-------|-------|-------|--------|--------|----------|

## Active Red Sets

> Test files whose failures are PLANNED (a RED task landed; its GREEN pair has not). Halt-recovery §5 registers and retires these; a failure IN this list does not halt, a failure NOT in it still halts. Self-expiring — a retired green removes its row. Format: ONE test-file path per row, relative to the work-dir root — EXACT paths only, never globs (the gate-exclusion match is exact-path, so a glob would over- or under-exclude).

| Red set (test file — exact path) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------------------|--------------------------|---------------------------|

## Active Doubts / Blockers

- **Doubt escalated:** {none — or: the question + what was tried + why unresolved}
- **Blocker:** {none — or: what blocked + what would unblock}
- **Checkpoint awaiting user approval:** {none — or: phase id}

## Notes for Resuming Conductor

{Free-form, short. Critical context the next session needs: user overrides, irreversibility warnings, model-tier exceptions, a no-commit condition (plan-less no-repo workspace). Overwritten, not appended — replace stale notes when they no longer apply.}
```

---

## Atomic-overwrite discipline (hard text)

| Rule | Statement |
|------|-----------|
| **Regenerate from skeleton** | A boundary write (batch close, reviewer close, pre-refresh) RE-INSTANTIATES this file from the template skeleton carrying only live values — NEVER an in-place edit of the prior capsule. In-place editing accretes superseded rows and contradictions a resuming conductor would act on; regeneration makes leanness independent of session age. |
| **Per-row liveness** | For each row ask "does the NEXT dispatch need this?" — if not, it does not belong here. History → `run-log.md`, rulings → `decisions.md`. Carry POINTERS (commit hashes, findings paths, D-/ADX-numbers), never narratives. |
| **Volatile facts once** | Each volatile fact — next dispatch, next hard halt, each worker's quota state — stated EXACTLY ONCE. A fact restated in two sections is a contradiction. The next dispatch belongs ONLY in Resume Point. `stamp.py --scope conductor` refuses a capsule with a duplicate section header, a next-dispatch claim outside Resume Point, the next dispatch stated more than once, or a Resume Point missing any of the three labeled bullets (`Last completed` / `Next dispatch` / `Last update`) — its lockstep writes those labeled fields in place (state card §7). |
| **Write via temp, then replace** | Write new content to a sibling `state-capsule.md.tmp`, verify it is well-formed (parses, required sections present), then atomically replace the live file. A stray `.tmp` at session start = a prior interrupted write — surface it to the user before proceeding. |
| **Never append** | Overwriting is the contract. NEVER append to this file and NEVER treat it as a history — history is `run-log.md`. |
| **Never a planning decision** | A decision that changes future work is append-only and belongs in `decisions.md`, never here. This file carries only in-flight resume state. |
| **Keep it small** | Collapse rows from phases older than the previous one into a single summary row. NEVER drop Run Configuration, Active Red Sets, Active Doubts/Blockers, or the Resume Point regardless of size — they are the resume contract. Full audit detail belongs in `run-log.md`. |
| **Re-read first on resume** | A resuming conductor reads THIS file first (resume point + delegation map + active red sets + active doubts), then the `run-log.md` tail to confirm what is in flight, then `decisions.md` for the rulings in force. Skip completed batches per the resume point; never redo a batch marked done. |

## Render note

This template is instantiated mechanically at spine init — copy the fenced block, substitute `{run-name}` and the timestamp, write it to the spine location, and initialize the Resume Point: **Last completed** = "intake complete", **Next dispatch** = the first task/batch routing will assign, **Last update** = the init timestamp. The leading callouts (mutable-overwrite + audience + computed-claims) are part of the file and MUST survive instantiation — they keep the mutability boundary, the not-a-worker-surface rule, and the compute-every-claim obligation visible at the point of use.
