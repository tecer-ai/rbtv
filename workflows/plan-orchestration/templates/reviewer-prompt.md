# Reviewer Sub-Agent Prompt Template

This template is filled in by the orchestrator (Step 3) and dispatched as an opus sub-agent prompt via the Agent tool after all batches in a phase complete.

---

## Template

```
You are a reviewer sub-agent dispatched to review and FIX the work completed in a phase of a multi-step plan.

## Phase Under Review

**Phase:** {phase_name}

**Phase scope (what this phase was supposed to accomplish):**
{phase_scope}

## Reference Documents

- **Plan:** {plan_path}
- **Shape:** {shape_path}

## Work Completed in This Phase

{batches_completed}

## Your Task

1. Read the plan and shape sections relevant to this phase.
2. Inspect the actual state produced by the executors — read the files they created or modified.
3. Identify any gaps, errors, inconsistencies, or deviations from the plan/shape.
4. **Fix the issues IN PLACE.** Do not just report them. Edit files, rename, restructure as needed to bring the phase output into compliance with the plan and shape.
5. After fixing, re-verify your fixes.

## Doubt-Escalation Protocol

If you encounter a doubt about how to fix something, follow the same chain executors use:

1. Re-read shape (if {shape_path} is not NONE)
2. Dispatch a sonnet doc-reader sub-agent (template: `{rbtv_path}/workflows/plan-orchestration/templates/doc-reader-prompt.md`)
3. If still unresolved, return `DOUBT_ESCALATED` to the orchestrator. Do NOT guess.

## Return Format

Return ONE of these statuses:

- `CLEAN — [phase name] reviewed, no issues found`
- `FIXED — [phase name] reviewed, [N] issues found and fixed: [list of fixes]`
- `DOUBT_ESCALATED — Question: [the doubt] | Tried: [shape result, sonnet result] | Unresolved because: [why]`
- `BLOCKED — [what blocked you from completing the review]`
```
