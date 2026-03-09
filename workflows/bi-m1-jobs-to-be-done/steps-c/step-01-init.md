---
name: 'step-01-init'
description: 'Load context, explain JTBD framework, detect continuation'
nextStepFile: './step-02-job-hypotheses.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/jobs-to-be-done.md'
---

# Step 1: Initialize Jobs-to-be-Done

**Progress: Step 1 of 5** — Next: Job Hypotheses

---

## STEP GOAL

Load context from project-memo and Working Backwards output, explain the JTBD framework, and prepare for job discovery.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Customers hire products to make progress. Push for specificity on situations and outcomes. Reject vague job statements.

### Step-Specific Rules
- If jobs-to-be-done.md exists with stepsCompleted, offer to continue from last step
- Do NOT create job hypotheses in this step — that's for step 2
- Keep framework explanation concise (under 5 minutes reading)

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `{outputFolder}/working-backwards.md` for customer/problem insights (REQUIRED dependency)
3. Read `./data/jtbd-framework.md` for framework knowledge
4. Check if `{outputFolder}/jobs-to-be-done.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Dependency Check

**CRITICAL:** Working Backwards MUST be completed before JTBD.

Check for `{outputFolder}/working-backwards.md`:
- If missing or status ≠ completed:
  - HALT with: "JTBD requires Working Backwards to be completed first. The PR/FAQ provides the customer narrative that becomes job hypotheses. Please complete bi-m1-working-backwards workflow before proceeding."
  - Exit workflow
- If complete:
  - Extract key insights: primary customer, core problem, value proposition

### 2. Context Detection

Check for existing outputs:
- If `jobs-to-be-done.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain JTBD briefly:

> "Jobs-to-be-Done shifts perspective from 'what features do we build?' to 'what progress does our customer want to make?'
>
> The core insight: customers don't buy products — they **hire** them to get a job done. That job has:
>
> 1. A **situation trigger** — when does this matter?
> 2. **Desired progress** — what's the outcome they want?
> 3. **Competing forces** — what pulls them toward/away from change?
>
> We'll turn your Working Backwards insights into testable job hypotheses, then validate them through interviews."

### 4. Working Backwards Summary

From working-backwards.md, summarize:
- Primary customer (from Customer & Problem Brief)
- Core problem being solved
- Key value proposition (from Press Release)
- Top assumptions (for consideration in job framing)

Present: "Here's what Working Backwards revealed about your customer..."

### 5. Create Output Document

If not continuing, create jobs-to-be-done.md:

```yaml
---
name: jobs-to-be-done
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
dependsOn: working-backwards
---

# Jobs-to-be-Done: {Project Name}

## Job Hypotheses

*(To be completed in Step 2)*

## Interview Guide

*(To be completed in Step 3)*

## Job Stories & Forces

*(To be completed in Step 4)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Job Hypotheses

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure jobs-to-be-done.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-job-hypotheses.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Working Backwards dependency verified, user understands JTBD framework, output document created

❌ **FAILURE:** Proceeding without Working Backwards, generating job hypotheses in this step, not creating output document
