---
stepNumber: 1
stepId: pre-flight
nextStepFile: ./step-02-ingest-batch.md
---

# Step 1: Pre-flight Gate

**Goal:** Confirm the plan qualifies for orchestration and capture user preferences before any sub-agent dispatch.

---

## MANDATORY SEQUENCE

### 1. Verify Plan is Multi-Step

Read the plan file's index, table of contents, or top-level structure. Confirm it has:
- 2+ distinct phases OR
- 5+ tasks that can be grouped into phases

If the plan is single-step or trivial: STOP and tell the user this skill does not apply — they should execute the plan directly or use a simpler tool.

### 2. Verify Plan is Non-Code

Scan the plan for code-work signals: TDD, git commits, branch management, test suites, code refactoring across files, package changes.

If the plan is code work: STOP and redirect the user to `superpowers:subagent-driven-development`. Do not proceed.

### 3. Ask User: Orchestrate?

Present:

> This plan has [N] phases / [M] tasks. I can either:
> - **Orchestrate** — I delegate each phase to sub-agents (model tier per task: haiku for mechanical work, sonnet for enumerated cases, opus by default), dispatch a reviewer after each phase (one tier above the executor, floor sonnet), and only surface doubts to you. I never execute plan work myself.
> - **Skip orchestration** — you handle execution another way.
>
> Want me to orchestrate?

If the user declines: STOP the workflow.

### 4. Ask User: Run Mode?

Present:

> Three run modes:
> - **Halt** — I stop after each phase's reviewer and wait for your go-ahead. Doubts halt. USER-EXECUTED-ONLY tasks halt for you to do them.
> - **End-to-end** — I run phases continuously without stopping at checkpoints. Doubts still halt. USER-EXECUTED-ONLY tasks still halt.
> - **Autonomous** — I run continuously and decide unilaterally on doubts and USER-EXECUTED-ONLY tasks too. Every unilateral decision is appended to `autonomous-run-log.md` in the plan folder for your post-hoc review. Plan-marked HARD halts (irreversibility gates, e.g., pre-cutover) are NEVER overridden. I will not destroy user content.
>
> Which?

Record the user's choice as `run_mode: halt | end-to-end | autonomous`.

If `run_mode: autonomous`, copy the template at `{rbtv_path}/workflows/plan-orchestration/templates/autonomous-run-log-template.md` to `{plan_dir}/autonomous-run-log.md` (filling `{plan-name}` in the frontmatter and H1). If the file already exists, leave it intact and append new entries at the bottom — never overwrite.

Halt-type behavior summary:

| Halt type | halt | end-to-end | autonomous |
|-----------|------|------------|------------|
| Checkpoint between phases | HALT | skip | skip |
| Doubt escalation from sub-agent | HALT | HALT | skip + log decision |
| USER-EXECUTED-ONLY task | HALT | HALT | skip + log defaults accepted |
| Plan-marked HARD halt (irreversibility gate) | HALT | HALT | HALT (never overridden) |
| Audit log discipline | none | none | mandatory (`autonomous-run-log.md`) |

### 5. Confirm and Proceed

Echo back:

> Confirmed: orchestrating [plan path] in [halt | end-to-end | autonomous] mode. {If autonomous: autonomous-run-log.md initialized at [path].} Proceeding to ingest the plan.

Load `./step-02-ingest-batch.md`.
