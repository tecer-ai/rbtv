---
title: 'Handoff: {Context Title}'
docType: 'handoff'
mode: 'create'
handoffType: 'execution'
targetAgent: 'Agent executing tasks from approved plan'
stepsCompleted: []
inputDocuments: []
outputPath: '{outputFolder}'
date: '{date}'
---

# Handoff: {Context Title}

**Type:** Execution  
**Created:** {date}  
**For:** Agent executing tasks from approved plan

---

## Context Summary

{Brief overview — what plan is being executed, what has been completed so far}

---

## Problem Being Solved

{The problem that the execution addresses}

### Current State

{Execution progress — which tasks are done, which are in progress, which remain}

---

## User Goals

{What the user wants achieved through this execution}

1. {Goal 1}
2. {Goal 2}
3. {Goal 3}

---

## Constraints Gathered

{Technical, process, and scope constraints for execution}

| Constraint | Type | Description |
|------------|------|-------------|
| {Constraint 1} | {Technical/Process/Scope} | {Details} |
| {Constraint 2} | {Technical/Process/Scope} | {Details} |

---

## Decisions Already Made

{Implementation decisions that should not be revisited}

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| {Decision 1} | {Why this choice} | {What we didn't do and why} |
| {Decision 2} | {Why this choice} | {What we didn't do and why} |

---

## Information Gaps

{What remains unclear for execution — "None" if all context provided}

- {Gap 1 — if any}
- {Gap 2 — if any}

---

## Task Instructions

{Specific tasks the receiving agent should execute}

### Execution Order

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | {Task 1} | {Pending/In Progress/Done} | {Any notes} |
| 2 | {Task 2} | {Pending/In Progress/Done} | {Any notes} |
| 3 | {Task 3} | {Pending/In Progress/Done} | {Any notes} |

### Current Task Details

**Task:** {The specific task to resume or start}

**Expected Outcome:** {What successful completion looks like}

**Approach:** {How to execute this task}

---

## Files to Load

{Critical files the receiving agent MUST read before executing}

| File | Purpose | Priority |
|------|---------|----------|
| {plan file path} | The approved plan | MUST READ FIRST |
| {execution decisions path} | Decisions made during execution | MUST READ FIRST |
| {path/to/another.md} | {Why this file matters} | Reference |

---

## For the Agent Reading This Handoff

{Instructions for continuing execution}

### Immediate Next Steps

1. Read the approved plan file
2. Review execution decisions made so far
3. Resume task #{N} from the execution order
4. {Next specific action}

### Guidelines

- Follow the plan exactly — do not deviate without user approval
- Update execution decisions file after completing each task
- Test changes before marking tasks complete

### What NOT to Do

- Do not modify the approved plan without user approval
- Do not skip tasks in the execution order
- Do not re-decide matters already settled (see decisions table)

---

## Self-Cleanup Instruction

After successfully completing the execution:

- If all tasks are complete → Delete this handoff file
- If work continues → Update or create a new handoff for the next agent

---

## References

{Links to relevant execution documentation}

| Reference | Purpose |
|-----------|---------|
| {path or URL} | {How it relates} |
