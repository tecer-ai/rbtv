---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain TRL framework'
nextStepFile: './step-02-current-trl-assessment.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/technology-readiness-level.md'
---

# Step 1: Initialize TRL Assessment

**Progress: Step 1 of 5** — Next: Current TRL Assessment

---

## STEP GOAL

Load context from project-memo and M1 frameworks, explain the TRL framework, and prepare for technical component assessment.

---

## Prior Context

**Builds on:** Leap of Faith, Assumption Mapping
**Inherits (do not restate):** Technical assumptions from assumption inventory — reference `{outputFolder}/leap-of-faith.md`; test priorities — reference `{outputFolder}/assumption-mapping.md`
**This framework adds:** Technical feasibility assessment, component TRL scores, technical risk register, spike cards

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor enforcing brutal technical honesty. "We could build that" is TRL 1-2, not TRL 5. Evidence must exist, not be imagined.

### Step-Specific Rules
- If technology-readiness-level.md exists with stepsCompleted, offer to continue from last step
- Do NOT score components in this step — that's for Step 2
- TRL can run in parallel with TAM/SAM/SOM and Unit Economics — no strict prerequisite

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `{outputFolder}/../m1-conception/problem-solution-fit.md` for solution concept
3. Read `{outputFolder}/../m1-conception/lean-canvas.md` for Solution block
4. Read `{outputFolder}/../m1-conception/working-backwards.md` for Internal FAQ technical questions
5. Read `{outputFolder}/bmad-analysis/` contents (if exists) for technical research findings
6. Read `./data/trl-framework.md` for framework knowledge
7. Check if `{outputFolder}/technology-readiness-level.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Verify M1 frameworks are available:
- Check for Problem-Solution Fit solution concept
- Check for Lean Canvas Solution block
- Check for Working Backwards Internal FAQ

**If M1 frameworks NOT complete:**
> "⚠️ Prerequisites Missing: TRL assessment requires solution definition from M1.
>
> Needed:
> - Problem-Solution Fit (Our Solution block)
> - Lean Canvas (Solution block with top 3-5 capabilities)
> - Working Backwards (Internal FAQ technical questions)
>
> **Action needed:** Return to M1 workflow and complete these frameworks first."

HALT and present option to return to M1 workflow.

### 2. Context Detection

Check for existing outputs:
- If `technology-readiness-level.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain TRL briefly:

> "Technology Readiness Level (TRL) is NASA's 9-level scale for assessing how close a technology is to operational deployment.
>
> **Why this matters for startups:**
> - Most founders overestimate ('we can build that in a weekend') or underestimate ('we need years of R&D')
> - TRL forces honest, evidence-based assessment of EACH component separately
> - The weakest component determines your risk profile
>
> **The scale:**
> - TRL 1-3: Concept to proof-of-concept (high risk)
> - TRL 4-6: Lab to staging validation (moderate risk)
> - TRL 7-9: Production proven (low risk)
>
> Components below TRL 4 need **technical spikes** before you commit to M4 Prototypation."

### 4. Extract Solution Definition

From M1 frameworks, extract:

**From Problem-Solution Fit:**
- Core mechanism of value creation
- Key capabilities required

**From Lean Canvas Solution block:**
- Top 3-5 features/capabilities listed

**From Working Backwards Internal FAQ:**
- Technical feasibility questions raised
- Architecture assumptions mentioned
- Integration dependencies noted

Present: "Here's what your solution needs to deliver..."

### 5. Identify Technical Questions

List all technical questions from Internal FAQ:

| Question | Source Section | Status |
|----------|----------------|--------|
| [Technical question 1] | Internal FAQ | Unanswered |
| [Technical question 2] | Internal FAQ | Unanswered |
| ... | ... | ... |

> "These are the technical feasibility questions we need to address. Every one should map to a component or risk by the end of this assessment."

### 6. Create Output Document

If not continuing, create technology-readiness-level.md:

```yaml
---
name: technology-readiness-level
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
overallPosture: pending
---

# Technology Readiness Level Assessment: {Project Name}

## Component Inventory

*(To be completed in Step 2)*

## TRL Scores

*(To be completed in Step 2)*

## Technical Risks

*(To be completed in Step 3)*

## Spike Cards

*(To be completed in Step 4)*

## Synthesis

*(To be completed in Step 5)*
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Current TRL Assessment

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure technology-readiness-level.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-current-trl-assessment.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** M1 context loaded, technical questions identified, output document created

❌ **FAILURE:** Proceeding without M1 context, scoring components in this step
