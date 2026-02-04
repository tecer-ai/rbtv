---
title: 'Handoff: {Context Title}'
docType: 'handoff'
mode: 'create'
handoffType: 'plan-development'
targetAgent: 'Agent continuing plan creation or modification'
stepsCompleted: []
inputDocuments: []
outputPath: '{outputFolder}'
date: '{date}'
---

# Handoff: {Context Title}

**Type:** Plan Development  
**Created:** {date}  
**For:** Agent continuing plan creation or modification

---

## Context Summary

{Brief overview of the planning conversation — what plan is being developed, current stage}

---

## Problem Being Solved

{The problem that the plan will address}

### Current State

{Where we are in plan development — discovery complete? draft exists? under review?}

### Root Cause

{Why the plan is needed — the underlying issue or opportunity}

---

## User Goals

{What the user wants the plan to achieve}

1. {Goal 1}
2. {Goal 2}
3. {Goal 3}

---

## Constraints Gathered

{Technical, process, and project constraints that must be respected in the plan}

| Constraint | Type | Description |
|------------|------|-------------|
| {Constraint 1} | {Technical/Process/Scope} | {Details} |
| {Constraint 2} | {Technical/Process/Scope} | {Details} |

---

## Decisions Already Made

{Planning decisions that should not be revisited}

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| {Decision 1} | {Why this choice} | {What we didn't do and why} |
| {Decision 2} | {Why this choice} | {What we didn't do and why} |

---

## Information Gaps

{What remains unclear for plan completion — "None" if all context provided}

- {Gap 1 — if any}
- {Gap 2 — if any}

---

## Judge Feedback Summary

{Summarizes any judge evaluation received during planning}

**Status:** {Approved | Needs Revision | Pending Review | Not Yet Reviewed}

**Issues Identified:**

- {Issue 1}
- {Issue 2}

**Requirement Coverage:**

- {Requirement 1}: ✅ Covered / ❌ Missing
- {Requirement 2}: ✅ Covered / ❌ Missing

---

## Files to Load

{Critical files the receiving agent MUST read before continuing plan work}

| File | Purpose | Priority |
|------|---------|----------|
| {plan file path} | The plan being developed | MUST READ FIRST |
| {context file path} | Planning context | MUST READ FIRST |
| {path/to/another.md} | {Why this file matters} | Reference |

---

## For the Agent Reading This Handoff

{Instructions for continuing plan development}

### Immediate Next Steps

1. Read the plan-creation guardrail: `.cursor/rules/jobs/guardrails/plan-creation.mdc`
2. Read the plan command: `.cursor/commands/plan.md`
3. Review the existing plan and judge feedback (if any)
4. {Next specific action for plan development}

### Guidelines

- Follow the plan creation protocol from plan.md
- Address any judge feedback issues before proceeding
- Confirm with user before making major planning decisions

### What NOT to Do

- Do not revisit decisions already made (see table above)
- Do not skip judge review if plan is ready for evaluation
- Do not implement changes — this is plan development, not execution

---

## Self-Cleanup Instruction

After successfully completing the plan development:

- If the plan is approved and ready for execution → Delete this handoff file
- If work continues → Update or create a new handoff for the next agent

---

## References

{Links to relevant planning documentation}

| Reference | Purpose |
|-----------|---------|
| {path or URL} | {How it relates} |
