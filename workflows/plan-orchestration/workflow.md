---
name: plan-orchestration
description: Orchestrate execution of a multi-step non-code plan by delegating phases to tiered sub-agents (haiku / sonnet / opus per the decision tree in step-02) and dispatching a reviewer per phase.
nextStep: ./step-01-pre-flight.md
---

# Plan Orchestration

**Goal:** Execute a multi-step non-code plan by orchestrating sub-agents — never executing tasks directly.

**Your Role:** Orchestrator. You read the plan, batch its tasks, assign each batch a model tier (haiku / sonnet / opus per the decision tree in step-02), dispatch executor sub-agents to do the work, dispatch reviewer sub-agents (one tier above the executor, floor sonnet) to validate each phase, and surface doubts to the user. You do NOT execute plan tasks yourself.

---

## Scope

**This workflow is for non-code work only.** Examples: vault refactors, content migrations, doc workflows, structural changes, knowledge organization.

**For code work, STOP and redirect:** invoke `superpowers:subagent-driven-development` instead. That skill provides per-task spec/quality review, TDD discipline, and git worktree integration that this workflow does not.

**For single-step tasks, STOP.** This workflow only applies to plans with multiple distinct steps or phases.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles
1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when ready to advance.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping.
4. **Orchestrator Never Executes** — The orchestrator delegates ALL plan work to sub-agents. The only direct work the orchestrator does is reading the plan, batching tasks, dispatching agents, and surfacing doubts.

### Critical Rules
- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read entire step file before execution
- 🚫 NEVER execute a plan task yourself — always delegate
- 🧠 NEVER skip the per-phase reviewer dispatch
- ⏸️ ALWAYS halt for the user when a sub-agent escalates a doubt
- 🛡️ NEVER override the user's checkpoint preference except for doubt escalations (which always halt)

---

## Initialization

1. Confirm the plan path. If not provided, ask the user for it.
2. Load the first step file (`step-01-pre-flight.md`) and follow its instructions exactly.
