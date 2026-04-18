---
name: 'step-01-init'
description: 'Load M1 context, verify prerequisites, explain framework'
nextStepFile: './step-02-harvest.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/leap-of-faith.md'
---

# Step 1: Initialize Leap of Faith

**Progress: Step 1 of 5** — Next: Harvest Assumptions

---

## STEP GOAL

Verify all M1 frameworks are complete, load project context, explain the Leap of Faith framework, and prepare for assumption harvesting.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge assumptions ruthlessly. The founder's biggest blind spots are the assumptions they don't know they're making.

### Step-Specific Rules
- MUST verify all 6 M1 frameworks are complete before proceeding
- If any M1 framework is missing, HALT and offer to help complete it
- If leap-of-faith.md exists with stepsCompleted, offer to continue from last step
- Do NOT harvest or classify assumptions in this step — that's for later steps

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and M1 completion status
2. Read `./data/leap-of-faith-framework.md` for framework knowledge
3. Check if `{outputFolder}/leap-of-faith.md` exists (continuation mode)
4. Read `{outputFolder}/bmad-analysis/` contents (if exists) for market research and brainstorming findings that inform assumption harvesting
5. Verify M1 framework outputs exist:
   - `{project-name}/business-innovation/m1-conception/working-backwards.md`
   - `{project-name}/business-innovation/m1-conception/jobs-to-be-done.md`
   - `{project-name}/business-innovation/m1-conception/competitive-landscape.md`
   - `{project-name}/business-innovation/m1-conception/problem-solution-fit.md`
   - `{project-name}/business-innovation/m1-conception/lean-canvas.md`
   - `{project-name}/business-innovation/m1-conception/five-whys.md`

---

## MANDATORY SEQUENCE

### 1. Prerequisites Check

Verify M1 Conception is complete:
- Check project-memo.md stepsCompleted for all 6 M1 frameworks
- Check that all M1 output files exist

If ANY M1 framework is missing:
> "**HALT:** Leap of Faith requires all M1 Conception frameworks to be complete.
>
> Missing: [list missing frameworks]
>
> These frameworks contain the assumptions we need to harvest. Would you like to:
> - [M1] Return to M1 to complete missing frameworks
> - [P] Proceed anyway (not recommended — analysis will be incomplete)"

### 2. Context Detection

Check for existing outputs:
- If `leap-of-faith.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Leap of Faith:

> "Leap of Faith is about confronting the assumptions you don't know you're making.
>
> In M1, you built a business concept through 6 frameworks. Hidden in those documents are dozens of beliefs about customers, markets, technology, and economics — some stated explicitly, most embedded implicitly.
>
> We'll now:
> 1. **Harvest** every assumption from your M1 work (explicit AND implicit)
> 2. **Classify** each as Value Hypothesis (customer/problem/solution) or Growth Hypothesis (business model/economics)
> 3. **Prioritize** by Impact × Uncertainty — what matters most and we know least about
> 4. **Define** observable signals that validate or invalidate each assumption
> 5. **Pre-commit** to kill/pivot/persevere criteria before sunk-cost bias kicks in
>
> The goal: know exactly what you're betting on and what evidence would change your mind."

### 4. Project Context Summary

From project-memo, summarize:
- Project name
- M1 completion status (which frameworks done)
- Key findings from M1 (customer, problem, solution)

Present: "Here's what we're validating..."

### 5. Create Output Document

If not continuing, create leap-of-faith.md:

```yaml
---
name: leap-of-faith
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Leap of Faith Analysis: {Project Name}

## Consolidated Assumption Inventory

*(To be completed in Step 2)*

## Classified Assumption Register

*(To be completed in Step 3)*

## Impact × Uncertainty Matrix

*(To be completed in Step 4)*

## Top Leap-of-Faith Assumptions

*(To be completed in Step 4)*

## Validation Signals & Kill Criteria

*(To be completed in Step 5)*

## Validation Backlog

*(To be completed in Step 5)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Harvest Assumptions

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure leap-of-faith.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-harvest.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All M1 frameworks verified complete, user understands framework purpose, output document created

❌ **FAILURE:** Proceeding without M1 check, harvesting assumptions in this step, skipping to later steps
