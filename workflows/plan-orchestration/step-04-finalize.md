---
stepNumber: 4
stepId: finalize
nextStepFile: null
---

# Step 4: Finalize

**Goal:** Produce the orchestrator's final message and surface anything incomplete or low-confidence.

---

## MANDATORY SEQUENCE

### 1. Load the Finalization Template

Read `{rbtv_path}/workflows/plan-orchestration/templates/finalization-message-template.md`. This template defines the required sections and ordering.

### 2. Gather Inputs

Collect from this orchestration session:

- Plan name, path, and overall status (COMPLETE vs COMPLETE PENDING USER ACTION)
- All commits added this session, with one-line descriptions
- Per-batch records from `{plan_dir}/orchestration-state.md` Completed Batches table
- Any USER-EXECUTED-ONLY tasks left unflipped or pending
- Any reviewer findings that required user input
- Any deviations from the original delegation plan
- If `run_mode: autonomous`: every entry in `{plan_dir}/autonomous-run-log.md`, sorted by confidence ascending

### 3. Produce the Message

Write the message inline (chat output) following the template structure exactly. Section discipline:

| Section | Required? | Notes |
|---------|-----------|-------|
| Status line | Always | Plan name, status, commit list, optional phase summary |
| Batch summary | Always | One row per batch, including reviewer dispatches |
| Next actions — in order | Always | Self-explanatory items; name paths/decisions/commits inline; state consequences of skipping; list prerequisites |
| Decisions worth your review | Required if `run_mode: autonomous` AND ≥1 entry has confidence medium or low | Sort lowest-confidence first; otherwise replace with "No low-confidence decisions logged." |
| Artifacts | Always | Plan, shape, learnings, orchestration state; autonomous run log if mode was autonomous |
| Working tree note | Optional | Include if uncommitted/unstaged work was deliberately left untouched |
| Post-merge / next-step commands | Optional | Include if the user must run commands to land or follow up |

Each Next-action item MUST be self-explanatory — the user reads this with zero session context. Do NOT use phrases that assume timing (e.g., "when you wake up"). Use neutral framing like "Next actions" so the message works for any time-of-day finalization.

### 4. Surface Incompleteness Honestly

If the plan is COMPLETE PENDING USER ACTION (e.g., user-driven merge), say so in the status line. Do not claim COMPLETE when irreversible final steps remain.

If a USER-EXECUTED-ONLY task was bundled-accepted under autonomous mode, the relevant log entry MUST appear in "Decisions worth your review" — not just in the artifacts log. Surface it explicitly so the user does not have to read the full log to find it.

### 5. End

Inform the user the orchestration workflow is complete. Do not auto-invoke any follow-up skill — let the user decide.
