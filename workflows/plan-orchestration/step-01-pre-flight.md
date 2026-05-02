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

### 4. Ask User: Checkpoint Halts?

Present:

> Two checkpoint modes:
> - **Halt at checkpoints** — I stop after each phase's reviewer completes and wait for your go-ahead before starting the next phase.
> - **Run end-to-end** — I run all phases continuously, only stopping if a sub-agent escalates a doubt.
>
> Doubts always halt regardless of mode.
>
> Which?

Record the user's choice as `checkpoint_mode: halt | end-to-end`.

### 5. Confirm and Proceed

Echo back:

> Confirmed: orchestrating [plan path] in [halt | end-to-end] mode. Doubts always halt. Proceeding to ingest the plan.

Load `./step-02-ingest-batch.md`.
