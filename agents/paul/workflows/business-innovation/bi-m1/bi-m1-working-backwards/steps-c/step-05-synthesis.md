---
name: 'step-05-synthesis'
description: 'Synthesize findings and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/working-backwards.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Synthesize Working Backwards findings into a concise summary and UPDATE project-memo.md to capture learnings across frameworks.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate clarity achieved. Note gaps that remain. Be honest about what was learned and what still needs validation.

### Step-Specific Rules
- project-memo.md MUST be updated with Working Backwards synthesis
- Synthesis must be concise (250 words max)
- Link to full working-backwards.md for details
- Mark framework as completed in project-memo frontmatter

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete working-backwards.md from Steps 1-4
- project-memo.md

**Out of scope:**
- Other M1 frameworks (separate workflows)
- M2 validation experiment design

---

## MANDATORY SEQUENCE

### 1. Review Completed Work

Summarize what was accomplished:

> "Let's review what we built:
> - Customer & Problem Brief defining [customer] and their [problem]
> - Press Release articulating [value proposition]
> - External FAQ addressing [N] customer questions
> - Internal FAQ answering 'Is it worth doing?' with [decision]
> - [N] assumptions tagged for validation"

### 2. Draft Framework Synthesis

Create a concise synthesis (250 words max) covering:

**Key Findings:**
- Primary customer: [one sentence]
- Core problem: [one sentence]
- Solution value: [one sentence]
- Decision: [Is it worth doing? answer]

**Assumptions to Validate:**
- Top 3 assumptions requiring M2 validation

**Connections to Other Frameworks:**
- Feeds into: JTBD, Lean Canvas, Problem-Solution Fit
- Customer & Problem Brief seeds job statements
- Internal FAQ assumptions seed Leap of Faith mapping

### 3. Deduplication Verification

As the first framework in M1, this framework defines foundational concepts. Later frameworks will reference these definitions. No deduplication check is required — this framework is the concept originator for this milestone.

### 4. Update working-backwards.md

Add Synthesis section to the output document:

```markdown
## Synthesis

### Key Findings

**Primary Customer:** [one sentence]

**Core Problem:** [one sentence]

**Solution Value:** [one sentence]

**Decision:** [Is it worth doing? answer with brief rationale]

### Top Assumptions for Validation

1. [Assumption 1]
2. [Assumption 2]
3. [Assumption 3]

### Framework Connections

- Feeds into: JTBD (job statements), Lean Canvas (Problem, Segments, UVP), Problem-Solution Fit
- Internal FAQ assumptions seed M2 Leap of Faith mapping
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-discover', 'step-03-press-release', 'step-04-faq', 'step-05-synthesis']
status: completed
```

### 5. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m1-working-backwards` to `stepsCompleted` array

**In Progress > M1 Conception section:**

```markdown
### Working Backwards

**Status:** Completed

**Key Findings:**
- Primary Customer: [one sentence]
- Core Problem: [one sentence]
- Decision: [Is it worth doing? answer]

**Top Assumptions:** [List 3]

**Output:** [Link to working-backwards.md]
```

### 6. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 7. Completion Summary

Present to founder:
> "Working Backwards framework complete!
>
> **What we achieved:**
> - Defined [customer] and their [problem]
> - Created press release and FAQ
> - Answered 'Is it worth doing?' with [decision]
> - Identified [N] assumptions for validation
>
> **Next recommended framework:** [JTBD / Competitive Landscape / etc.]
>
> **Return path:** To continue other M1 frameworks, return to bi-m1 milestone workflow."

### 8. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M1.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M1 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 9. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M1** — return to M1 Conception milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M1** is selected:
1. Verify working-backwards.md has status: completed
2. Verify project-memo.md has Working Backwards entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** working-backwards.md complete with synthesis, project-memo.md updated with framework entry, stepsCompleted accurate in both files

❌ **FAILURE:** project-memo.md not updated, synthesis missing, framework not marked complete
