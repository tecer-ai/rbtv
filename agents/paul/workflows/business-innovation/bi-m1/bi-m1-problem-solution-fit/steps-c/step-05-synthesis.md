---
name: 'step-05-synthesis'
description: 'Validate alignment and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/problem-solution-fit.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Synthesize Problem-Solution Fit findings into a concise summary, validate alignment, and UPDATE project-memo.md to capture learnings.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate clarity achieved. Note gaps that remain. Be honest about what was validated and what assumptions need testing.

### Step-Specific Rules
- project-memo.md MUST be updated with Problem-Solution Fit synthesis
- Synthesis must be concise (250 words max)
- Link to full problem-solution-fit.md for details
- Mark framework as completed in project-memo frontmatter

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete problem-solution-fit.md from Steps 1-4
- project-memo.md

**Out of scope:**
- Lean Canvas or 5 Whys execution (separate workflows)
- M2 experiment design (separate milestone)

---

## MANDATORY SEQUENCE

### 1. Alignment Validation

Review the complete canvas for internal consistency:

> "Let's validate alignment across the canvas:
>
> **Problem-Solution Alignment:**
> - Does the solution address the specific problem situations we mapped?
> - Can we trace each solution element to behaviours or constraints?
>
> **Completeness Check:**
> - Problem-Space Brief: [✅/❌]
> - Problem, Triggers, Emotions: [✅/❌]
> - Behaviours and Constraints: [✅/❌]
> - Our Solution: [✅/❌]
> - Critical Assumptions: [✅/❌]"

If gaps found:
> "We have gaps in [area]. Return to Step [N] to complete?"

### 2. Framework Connections

Identify how this canvas feeds other frameworks:

> "This canvas outputs:
>
> **For Lean Canvas:**
> - Problem: [from Problem-Space Brief]
> - Customer Segments: [from scoping]
> - Solution: [from Our Solution]
>
> **For 5 Whys:**
> - Starting problem statement: [from Problem block]
>
> **For M2 Leap of Faith:**
> - Critical assumptions: [from Step 4 priorities]"

### 3. Review Completed Work

Summarize accomplishments:

> "Let's review what we built:
> - Problem-Space Brief defining [segment] in [situation]
> - Problem mapping with [N] concrete situations
> - Solution articulated in terms of [key behaviours changed]
> - [N] critical assumptions tagged for validation
>
> **Key insight:** [one sentence capturing the core problem-solution fit hypothesis]"

### 4. Draft Framework Synthesis

Create concise synthesis (250 words max):

**Segment & Situation:**
- Focus: [one sentence on who and when]

**Problem-Solution Thesis:**
- Problem: [one sentence on what hurts]
- Solution: [one sentence on what changes]
- Core mechanism: [how value is created]

**Top Assumptions:**
1. [Highest priority assumption]
2. [Second priority]
3. [Third priority]

**Framework Connections:**
- Feeds Lean Canvas: Problem, Segments, Solution blocks
- Feeds 5 Whys: Problem statement
- Feeds M2 Leap of Faith: Critical assumptions

### 5. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/agents/paul/workflows/business-innovation/data/founder-process.md` for M1.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 6. Update problem-solution-fit.md

Add Synthesis section:

```markdown
## Synthesis

### Alignment Validation

**Problem-Solution Fit Status:** [Validated at concept level / Needs refinement]

### Key Findings

**Segment & Situation:** [one sentence]

**Problem-Solution Thesis:** [one sentence on problem] → [one sentence on solution]

**Core Mechanism:** [how value is created]

### Top Assumptions for Validation

1. [PSF-X]: [Assumption] — Test: [How to falsify]
2. [PSF-Y]: [Assumption] — Test: [How to falsify]
3. [PSF-Z]: [Assumption] — Test: [How to falsify]

### Framework Connections

- **Lean Canvas:** Problem, Customer Segments, Solution inputs ready
- **5 Whys:** Problem statement defined
- **M2 Leap of Faith:** [N] critical assumptions tagged
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-problem-space', 'step-03-solution-space', 'step-04-assumptions', 'step-05-synthesis']
status: completed
```

### 7. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m1-problem-solution-fit` to `stepsCompleted` array

**In Progress > M1 Conception section:**

```markdown
### Problem-Solution Fit

**Status:** Completed

**Key Findings:**
- Segment: [one sentence on who]
- Problem: [one sentence on what hurts]
- Solution: [one sentence on what changes]

**Top Assumptions:** [List 3 with IDs]

**Output:** [Link to problem-solution-fit.md]
```

### 8. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 9. Completion Summary

Present to founder:

> "Problem-Solution Fit Canvas complete!
>
> **What we achieved:**
> - Defined [segment] and their problem in [situation]
> - Articulated solution as response to [key behaviours]
> - Identified [N] critical assumptions for validation
>
> **Canvas Status:** [Validated at concept level / Needs refinement]
>
> **Next recommended frameworks:**
> - Lean Canvas: Uses Problem, Segments, Solution from this canvas
> - 5 Whys: Starts from problem statement we defined
>
> **Return path:** To continue other M1 frameworks, return to bi-m1 milestone workflow."

### 10. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M1.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M1 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 11. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M1** — return to M1 Conception milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M1** is selected:
1. Verify problem-solution-fit.md has status: completed
2. Verify project-memo.md has Problem-Solution Fit entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** problem-solution-fit.md complete with synthesis, project-memo.md updated with framework entry, stepsCompleted accurate in both files

❌ **FAILURE:** project-memo.md not updated, synthesis missing, framework not marked complete
