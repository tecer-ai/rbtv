---
name: 'step-06-synthesis'
description: 'Synthesize findings and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/lean-canvas.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 6: Synthesis

**Progress: Step 6 of 6** — Final Step

---

## STEP GOAL

Synthesize Lean Canvas findings into a concise summary and UPDATE project-memo.md to capture learnings across frameworks.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate clarity achieved. Note gaps that remain. Be honest about which assumptions are riskiest and need validation first.

### Step-Specific Rules
- project-memo.md MUST be updated with Lean Canvas synthesis
- Synthesis must be concise (300 words max)
- Link to full lean-canvas.md for details
- Tag assumptions for M2 validation priority
- Mark framework as completed in project-memo frontmatter

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete lean-canvas.md from Steps 1-5
- project-memo.md

**Out of scope:**
- Other M1 frameworks (separate workflows)
- M2 validation experiment design

---

## MANDATORY SEQUENCE

### 1. Review Completed Canvas

Summarize all 9 blocks:

> "Let's review your complete Lean Canvas:
>
> | Block | Summary |
> |-------|---------|
> | Problem | [Top 3 problems] |
> | Customer Segments | [Primary + Early Adopters] |
> | UVP | [One-sentence] |
> | Solution | [Top 3 features] |
> | Channels | [Key channels] |
> | Revenue Streams | [Pricing model] |
> | Cost Structure | [Key costs] |
> | Key Metrics | [North Star + leading indicators] |
> | Unfair Advantage | [Defensibility thesis] |"

### 2. Prioritize Assumptions

From all tagged assumptions, identify the riskiest:

> "You've tagged [N] assumptions. Let's prioritize for M2 validation:
>
> **Highest Risk (validate first):**
> 1. [Assumption]: If wrong, [consequence]
> 2. [Assumption]: If wrong, [consequence]
> 3. [Assumption]: If wrong, [consequence]
>
> These should be the focus of your M2 Leap of Faith and validation experiments."

### 3. Draft Framework Synthesis

Create a concise synthesis (300 words max):

```markdown
## Synthesis

### Canvas Summary

**Version:** Lean Canvas v0.1 — [Stage: Idea/Pre-product/MVP]

**Business Model Hypothesis:**
[One paragraph summarizing the core model: who, what problem, what solution, how we make money, what makes us defensible]

### Key Insights

1. **Customer clarity**: [What we learned about who we serve]
2. **Value proposition**: [What differentiates us]
3. **Economic model**: [Path to sustainability]
4. **Defensibility**: [What gives us an edge]

### Riskiest Assumptions

| Priority | Assumption | Validation Approach |
|----------|------------|---------------------|
| 1 | [Assumption] | [How to test in M2] |
| 2 | [Assumption] | [How to test in M2] |
| 3 | [Assumption] | [How to test in M2] |

### Framework Connections

- **Builds on**: Working Backwards (customer/problem), JTBD (jobs/forces), PSF (solution fit)
- **Feeds into**: M2 Leap of Faith (assumptions), TAM/SAM/SOM (segments), Unit Economics (revenue/costs)
- **Informs Unfair Advantage**: Competitive Landscape analysis
```

### 4. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M1.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 5. Update lean-canvas.md

Add Synthesis section and update frontmatter:

```yaml
stepsCompleted: ['step-01-init', 'step-02-customer-problem', 'step-03-value-solution', 'step-04-channels-revenue', 'step-05-metrics-advantage', 'step-06-synthesis']
status: completed
```

### 6. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m1-lean-canvas` to `stepsCompleted` array

**In Progress > M1 Conception section:**

```markdown
### Lean Canvas

**Status:** Completed

**Version:** v0.1 — [Stage]

**Business Model Hypothesis:**
[One paragraph summary]

**Key Blocks:**
- **UVP**: [One sentence]
- **Revenue Model**: [Pricing summary]
- **Unfair Advantage**: [One sentence]

**Riskiest Assumptions:**
1. [Top assumption]
2. [Second assumption]
3. [Third assumption]

**Output:** [Link to lean-canvas.md]
```

### 7. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 8. Completion Summary

Present to founder:

> "Lean Canvas framework complete!
>
> **What we achieved:**
> - Encoded your business model across 9 testable blocks
> - Connected each block to prior framework outputs
> - Identified [N] assumptions requiring M2 validation
> - Prioritized top 3 riskiest assumptions
>
> **Canvas Version:** v0.1 — [Stage]
>
> **Next steps:**
> - If M1 incomplete: Continue with remaining M1 frameworks
> - If M1 complete: Begin M2 Validation with Leap of Faith mapping
>
> **Return path:** To continue other M1 frameworks, return to bi-m1 milestone workflow."

### 9. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M1.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M1 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 10. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or assumption prioritization
- **[B] Back to M1** — return to M1 Conception milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M1** is selected:
1. Verify lean-canvas.md has status: completed
2. Verify project-memo.md has Lean Canvas entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** lean-canvas.md complete with synthesis, project-memo.md updated with framework entry, assumptions prioritized for M2, stepsCompleted accurate in both files

❌ **FAILURE:** project-memo.md not updated, synthesis missing, assumptions not prioritized, framework not marked complete
