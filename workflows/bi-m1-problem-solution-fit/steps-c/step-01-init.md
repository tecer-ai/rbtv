---
name: 'step-01-init'
description: 'Load context, verify prerequisites, detect continuation'
nextStepFile: './step-02-problem-space.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/problem-solution-fit.md'
---

# Step 1: Initialize Problem-Solution Fit

**Progress: Step 1 of 5** — Next: Problem Space Mapping

---

## STEP GOAL

Load context from project-memo, verify Working Backwards and JTBD prerequisites are complete, and prepare for problem-solution fit analysis.

---

## Prior Context

**Builds on:** Working Backwards, Jobs-to-be-Done, Competitive Landscape
**Inherits (do not restate):** Customer definition, problem statement, value proposition — reference `{outputFolder}/working-backwards.md`; customer jobs — reference `{outputFolder}/jobs-to-be-done.md`; competitive positioning — reference `{outputFolder}/competitive-landscape.md`
**This framework adds:** Solution description, fit validation, triggers/emotions mapping, critical assumptions for solution viability

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. This framework consolidates prior work into a testable hypothesis. Be rigorous about prerequisites — without Working Backwards and JTBD, this canvas will be hollow.

### Step-Specific Rules
- If problem-solution-fit.md exists with stepsCompleted, offer to continue from last step
- Verify Working Backwards AND JTBD are completed before proceeding
- If prerequisites missing, guide user to complete them first
- Do NOT start canvas blocks in this step — that's for later steps

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and framework status
2. Read `./data/psf-framework.md` for framework knowledge
3. Check if `{outputFolder}/problem-solution-fit.md` exists (continuation mode)
4. Check if `{outputFolder}/working-backwards.md` exists and is completed
5. Check if `{outputFolder}/jobs-to-be-done.md` exists and is completed

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check for required prior frameworks:
- Working Backwards: Look for `bi-m1-working-backwards` in project-memo stepsCompleted
- JTBD: Look for `bi-m1-jobs-to-be-done` in project-memo stepsCompleted

If both present:
> "Prerequisites verified: Working Backwards and JTBD both completed. Ready to build the Problem-Solution Fit Canvas."

If either missing:
> "Problem-Solution Fit builds on prior frameworks:
> - Working Backwards: [✅ Completed / ❌ Not found]
> - Jobs-To-Be-Done: [✅ Completed / ❌ Not found]
>
> Complete the missing framework(s) first. Return to bi-m1 milestone workflow."

HALT if prerequisites missing.

### 2. Continuation Detection

If `problem-solution-fit.md` exists with `stepsCompleted`:
- Display last completed step
- Offer: "Continue from step N?" or "Start fresh?"

If no existing output:
- Proceed to framework introduction

### 3. Framework Introduction

Explain Problem-Solution Fit briefly:

> "Problem-Solution Fit Canvas tests whether your solution truly fits the specific customer problem. We'll:
>
> 1. Define one segment and one situation — narrow scope
> 2. Map the problem as experienced — triggers, emotions, behaviours
> 3. Articulate your solution in terms of behaviours it changes
> 4. Extract assumptions that must hold for fit to exist
>
> This consolidates Working Backwards and JTBD into a testable hypothesis."

### 4. Prior Framework Summary

From project-memo and prior outputs, summarize:
- Primary customer (from Working Backwards)
- Core problem statement (from Working Backwards)
- Key job statements (from JTBD)
- Current alternatives (from JTBD)

Present: "Here's what we know from prior frameworks..."

### 5. Create Output Document

If not continuing, create problem-solution-fit.md:

```yaml
---
name: problem-solution-fit
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Problem-Solution Fit Canvas: {Project Name}

## Problem-Space Brief

*(To be completed in Step 2)*

## Problem, Triggers, and Emotions

*(To be completed in Step 2)*

## Alternatives, Behaviours, and Constraints

*(To be completed in Step 2)*

## Our Solution

*(To be completed in Step 3)*

## Critical Assumptions

*(To be completed in Step 4)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Problem Space Mapping

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure problem-solution-fit.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-problem-space.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, project context loaded, output document created

❌ **FAILURE:** Proceeding without Working Backwards or JTBD, generating canvas content in this step, skipping prerequisites
