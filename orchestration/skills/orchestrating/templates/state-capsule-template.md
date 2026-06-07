# State-Capsule Template

Instantiate this as `state-capsule.md` in the run's spine location at spine init (intake §3). It is the run's **mutable, atomic-overwrite resume state** — the small file the NEXT conductor reads to pick up cleanly after interruption or refresh. The State card (`{rbtv_path}/orchestration/skills/orchestrating/cards/state.md`) owns its semantics; this template is the render-ready body. Copy the block below, fill `{run-name}` + the init timestamp, leave the resume point at "intake complete" and the maps/sets empty.

---

## Template

```markdown
# State Capsule — {run-name}

> **Mutable file — overwriting is the contract.** The orchestrator atomically overwrites this file at each batch close and each reviewer close. Holds in-flight resume state ONLY — never an audit log (that is `run-log.md`, append-only) and never a worker-facing decision (that is `decisions.md`, append-only). A WORKER never reads this file.

> **Audience:** the next conductor session, resuming after interruption or context-refresh. Everything here exists to make resumption clean.

---

## Resume Point

- **Last completed:** {phase / batch / task ids — or "intake complete"}
- **Next dispatch:** {phase / batch / task ids — or "FINAL — run complete"}
- **Last update:** {ISO-8601 timestamp}

## Run Configuration

- **Run mode:** {halt | end-to-end | autonomous}
- **Context-refresh:** {suggest | off}
- **Plan path:** {absolute plan path — or NONE (plan-less run)}
- **Decisions file:** {path to decisions.md}

## Approved Delegation Map

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|

## Completed Batches

| Batch | Phase | Tasks | Worker | Status | Reviewer |
|-------|-------|-------|--------|--------|----------|

## Active Red Sets

> Test files whose failures are PLANNED (a RED task landed; its GREEN pair has not). Halt-recovery §5 registers and retires these; a failure IN this list does not halt, a failure NOT in it still halts. Self-expiring — a retired green removes its row.

| Red set (test files) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------|--------------------------|---------------------------|

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
| **Write via temp, then replace** | Write new content to a sibling `state-capsule.md.tmp`, verify it is well-formed (parses, required sections present), then atomically replace the live file. A stray `.tmp` at session start = a prior interrupted write — surface it to the user before proceeding. |
| **Never append** | Overwriting is the contract. NEVER append to this file and NEVER treat it as a history — history is `run-log.md`. |
| **Never a planning decision** | A decision that changes future work is append-only and belongs in `decisions.md`, never here. This file carries only in-flight resume state. |
| **Keep it small** | Collapse rows from phases older than the previous one into a single summary row. NEVER drop Run Configuration, Active Red Sets, Active Doubts/Blockers, or the Resume Point regardless of size — they are the resume contract. Full audit detail belongs in `run-log.md`. |
| **Re-read first on resume** | A resuming conductor reads THIS file first (resume point + delegation map + active red sets + active doubts), then the `run-log.md` tail to confirm what is in flight, then `decisions.md` for the rulings in force. Skip completed batches per the resume point; never redo a batch marked done. |

## Render note

This template is instantiated mechanically at spine init — copy the fenced block, substitute `{run-name}` and the timestamp, write it to the spine location, and set the resume point to "intake complete." The leading callouts (mutable-overwrite + audience) are part of the file and MUST survive instantiation — they keep the mutability boundary and the not-a-worker-surface rule visible at the point of use.
