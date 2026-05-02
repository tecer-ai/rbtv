---
stepNumber: 3
stepId: orchestrate-loop
nextStepFile: ./step-04-finalize.md
---

# Step 3: Orchestrate Loop

**Goal:** Execute the delegation plan phase by phase: dispatch executors per batch, dispatch reviewer per phase, honor checkpoint mode, halt on doubts.

---

## MANDATORY SEQUENCE

For each phase in order:

### 1. Dispatch Executors (one per batch)

For each batch in the current phase:

1. Load the executor prompt template at `./templates/executor-prompt.md`.
2. Fill in the template variables:
   - `{batch_tasks}` — the full text of the tasks in this batch (paste from plan, do NOT just reference)
   - `{plan_path}` — full path to the plan file
   - `{shape_path}` — full path to shape.md, or `NONE` if no shape exists
   - `{referenced_docs}` — list of doc paths the plan references (for sonnet doc-reader fallback)
3. Dispatch via the Agent tool with `subagent_type: general-purpose` and `model: opus`.
4. Wait for the sub-agent's return.
5. Handle the return status:

| Status | Action |
|--------|--------|
| **DONE** | Mark batch complete. Proceed to next batch in phase. |
| **DONE_WITH_NOTES** | Note the observations. Proceed to next batch. |
| **DOUBT_ESCALATED** | STOP. Surface the doubt to the user (see Section 4). |
| **BLOCKED** | STOP. Surface the blocker to the user. |

Dispatch executors **sequentially** within a phase — never in parallel. Sequential dispatch prevents conflicts when batches touch overlapping files.

### 2. Dispatch Phase Reviewer

After ALL batches in the phase complete:

1. Load the reviewer prompt template at `./templates/reviewer-prompt.md`.
2. Fill in the template variables:
   - `{phase_name}` — name/number of the phase just completed
   - `{phase_scope}` — what this phase was supposed to accomplish (paste from plan)
   - `{plan_path}` — full path to the plan file
   - `{shape_path}` — full path to shape.md, or `NONE`
   - `{batches_completed}` — list of batch summaries returned by executors
3. Dispatch via the Agent tool with `subagent_type: general-purpose` and `model: opus`.
4. The reviewer is instructed to FIX issues in place, not just report them.
5. Wait for the reviewer's return.
6. If the reviewer escalates a doubt: STOP and surface to user.

### 3. Honor Checkpoint Mode

After the reviewer returns clean:

- **`checkpoint_mode: halt`** — Present a brief summary of the phase and the reviewer's findings. Ask: "Phase [N] complete. Continue to Phase [N+1]?" Wait for user.
- **`checkpoint_mode: end-to-end`** — Proceed immediately to the next phase. No prompt.

### 4. Doubt Escalation Handling

When a sub-agent returns `DOUBT_ESCALATED`:

1. Present the doubt to the user verbatim, with context:
   > Sub-agent halted with a doubt during [phase/batch].
   > **Question:** [the doubt]
   > **What it tried:** [shape consultation result, sonnet doc-read result]
   > **Awaiting your input.**
2. Wait for user response.
3. Pass the user's answer back into a fresh executor (or reviewer) dispatch with the doubt resolved.

### 5. Loop or Advance

When all phases are complete, load `./step-04-finalize.md`.
