---
name: 'step-01-init'
description: 'Load M2 context, verify prerequisites, explain framework'
nextStepFile: './step-02-failure-scenarios.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/pre-mortem.md'
---

# Step 1: Initialize Pre-mortem

**Progress: Step 1 of 5** — Next: Brainstorm Failure Scenarios

---

## STEP GOAL

Verify all prior M2 frameworks are complete, load project context, explain the pre-mortem method, and prepare for prospective hindsight brainstorming.

---

## Prior Context

**Builds on:** Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, Technology Readiness Level
**Inherits (do not restate):** Assumption inventory and priorities — reference `{outputFolder}/leap-of-faith.md` and `{outputFolder}/assumption-mapping.md`; market sizing — reference `{outputFolder}/tam-sam-som.md`; unit economics — reference `{outputFolder}/unit-economics.md`; technical risks — reference `{outputFolder}/technology-readiness-level.md`
**This framework adds:** Failure modes (prospective hindsight), ranked failure table, mitigation cards, kill criteria alignment

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Create psychological safety for honest risk surfacing. The most dangerous failures are the ones nobody wants to say out loud.

### Step-Specific Rules
- MUST verify all 5 prior M2 frameworks are complete before proceeding
- If any M2 framework is missing, HALT and recommend completing it first
- If pre-mortem.md exists with stepsCompleted, offer to continue from last step
- Do NOT brainstorm failure modes in this step — that's for Step 2

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and M2 completion status
2. Read `./data/pre-mortem-framework.md` for framework knowledge
3. Read `{outputFolder}/bmad-analysis/` contents (if exists) for risk signals from market/competitive research
4. Check if `{outputFolder}/pre-mortem.md` exists (continuation mode)
5. Verify M2 framework outputs exist:
   - `{outputFolder}/leap-of-faith.md`
   - `{outputFolder}/assumption-mapping.md`
   - `{outputFolder}/tam-sam-som.md`
   - `{outputFolder}/unit-economics.md`
   - `{outputFolder}/technology-readiness-level.md`

---

## MANDATORY SEQUENCE

### 1. Prerequisites Check

Verify prior M2 frameworks are complete:
- Check project-memo.md stepsCompleted for M2 frameworks
- Check that M2 output files exist

If ANY prior M2 framework is missing:
> "**HALT:** Pre-mortem MUST be the final M2 framework.
>
> Missing: [list missing frameworks]
>
> Pre-mortem synthesizes risks from all prior M2 frameworks. Running it now would produce generic failure modes instead of project-specific risks.
>
> Would you like to:
> - [M2] Return to M2 milestone to complete missing frameworks
> - [P] Proceed anyway (not recommended — analysis will be shallow)"

### 2. Context Detection

Check for existing outputs:
- If `pre-mortem.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Pre-mortem:

> "Pre-mortem uses prospective hindsight to surface risks that optimism bias normally suppresses.
>
> Instead of asking 'what could go wrong?' (which triggers defensive optimism), we state as fact:
>
> **'It is 12 months from now. The project has failed. The product never reached product-market fit. The team has disbanded. Funding ran out. Why did this happen?'**
>
> This reframe gives psychological permission to voice doubts. Research shows it increases risk identification by 30%.
>
> We'll now:
> 1. **Brainstorm** failure modes across 7 categories (market, product, team, financial, technical, competitive, operational)
> 2. **Rank** by Likelihood × Severity to identify top threats
> 3. **Define** concrete mitigations with early warning signals
> 4. **Wire** findings into kill criteria and project memo
>
> Rule: No filtering during brainstorming. Every plausible failure reason gets listed. We filter in the ranking step."

### 4. Project Context Summary

From project-memo, summarize:
- Project name
- M2 frameworks completed
- Key risks already identified (from Leap of Faith, Unit Economics, TRL)

Present: "Here's the risk landscape we're synthesizing..."

### 5. Create Output Document

If not continuing, create pre-mortem.md:

```yaml
---
name: pre-mortem
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Pre-mortem Analysis: {Project Name}

## Failure Prompt

*(To be completed in Step 2)*

## Raw Failure Mode Inventory

*(To be completed in Step 2)*

## Ranked Failure Table

*(To be completed in Step 3)*

## Mitigation Cards

*(To be completed in Step 4)*

## Kill Criteria Alignment

*(To be completed in Step 5)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Failure Scenarios brainstorming

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure pre-mortem.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-failure-scenarios.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All prior M2 frameworks verified complete, user understands prospective hindsight method, output document created

❌ **FAILURE:** Proceeding without M2 check, brainstorming failures in this step, skipping to later steps
