---
name: 'step-05-synthesis'
description: 'Wire findings to Lean Canvas and validation backlog, update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/five-whys.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Synthesize Five Whys findings into a concise summary, update Lean Canvas with structural causes, seed M2 validation backlog, and UPDATE project-memo.md to capture learnings. This is the final M1 framework — trigger M1 completion check.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate the structural clarity achieved. Be honest about remaining hypotheses. This is M1's capstone — ensure findings propagate to all relevant artefacts.

### Step-Specific Rules
- project-memo.md MUST be updated with Five Whys synthesis
- Lean Canvas MUST be updated with refined Problem block
- Targeted Root Cause Hypotheses MUST seed M2 validation entries
- Synthesis must be concise (250 words max)
- As final M1 framework, trigger M1 completion check

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete five-whys.md from Steps 1-4
- project-memo.md
- lean-canvas.md

**Out of scope:**
- Running new 5 Whys chains
- M2 validation experiment design (only seeding)

---

## MANDATORY SEQUENCE

### 1. Review Completed Work

Summarize what was accomplished:

> "Let's review what we built:
> - Anchor Problem Statement for [scenario]
> - [N] 5 Whys chains reaching structural causes
> - Root Cause Map with [N] causes ([M] targeted, [P] non-targeted)
> - [N] Targeted Root Cause Hypotheses with measurable outcomes
>
> Key insight: [Most significant non-obvious root cause discovered]"

### 2. Draft Framework Synthesis

Create a concise synthesis (250 words max) covering:

**Key Findings:**
- Anchor scenario: [one sentence]
- Primary root cause: [one sentence]
- What we're targeting: [one sentence]
- What we're explicitly NOT tackling: [one sentence]

**Top Hypotheses for M2 Validation:**
1. [Hypothesis 1 — from Targeted Root Cause Hypotheses]
2. [Hypothesis 2]
3. [Hypothesis 3]

**Connections to Other Frameworks:**
- Refines: Lean Canvas Problem block
- Seeds: M2 Leap of Faith / Assumption Mapping
- Informs: Problem-Solution Fit critical assumptions

### 3. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/agents/paul/workflows/business-innovation/data/founder-process.md` for M1.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 4. Update five-whys.md

Add Synthesis section:

```markdown
## Synthesis

### Key Findings

**Anchor Scenario:** [one sentence]

**Primary Root Cause:** [one sentence]

**What We're Targeting:** [brief list]

**What We're NOT Tackling (v1):** [brief list with rationale]

### Top Hypotheses for M2 Validation

1. [Hypothesis 1]
2. [Hypothesis 2]
3. [Hypothesis 3]

### Framework Connections

- Refines: Lean Canvas Problem block (structural causes, not symptoms)
- Seeds: M2 Leap of Faith and Assumption Mapping
- Informs: Problem-Solution Fit critical assumptions
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-problem-framing', 'step-03-why-chain', 'step-04-root-cause', 'step-05-synthesis']
status: completed
```

### 5. Update Lean Canvas

Read lean-canvas.md and update:

**Problem block:**
- Replace surface symptoms with structural root causes
- Add "(Root cause)" annotation to distinguish from symptoms

**Key Metrics:**
- Add metrics from Targeted Root Cause Hypotheses

Present changes to founder for approval before saving.

### 6. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m1-five-whys` to `stepsCompleted` array

**In Progress > M1 Conception section:**

```markdown
### Five Whys

**Status:** Completed

**Key Findings:**
- Anchor Scenario: [one sentence]
- Primary Root Cause: [one sentence]
- Targeting: [brief list]
- Not Tackling (v1): [brief list]

**Top M2 Validation Hypotheses:**
1. [Hypothesis 1]
2. [Hypothesis 2]
3. [Hypothesis 3]

**Output:** [Link to five-whys.md]
```

### 7. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 8. M1 Completion Check

Five Whys is the final M1 framework. Check M1 status:

Read project-memo stepsCompleted and check for all 6 M1 frameworks:
- bi-m1-working-backwards
- bi-m1-jobs-to-be-done
- bi-m1-competitive-landscape
- bi-m1-problem-solution-fit
- bi-m1-lean-canvas
- bi-m1-five-whys

**If ALL 6 completed:**
> "🎉 M1 Conception is COMPLETE!
>
> You've finished all 6 conception frameworks:
> ✅ Working Backwards (customer & problem clarity)
> ✅ Jobs-to-be-Done (job statements & forces)
> ✅ Competitive Landscape (market positioning)
> ✅ Problem-Solution Fit (solution boundaries)
> ✅ Lean Canvas (business model)
> ✅ Five Whys (root cause analysis)
>
> **Recommended next step:** M2 Validation to test your critical assumptions."

Update project-memo.md:
- Set `currentMilestone: m2-validation` in frontmatter
- Add M1 completion note in Progress section

**If NOT all completed:**
> "Five Whys is complete. M1 has [N] of 6 frameworks done.
>
> Remaining: [list incomplete frameworks]
>
> Return to M1 milestone workflow to continue."

### 9. Completion Summary

Present to founder:
> "Five Whys framework complete!
>
> **What we achieved:**
> - Traced [scenario] to structural root causes
> - Identified [N] causes, targeting [M] in v1
> - Seeded [N] hypotheses for M2 validation
> - Updated Lean Canvas with structural problem definition
>
> **Root cause insight:** [Most significant finding]
>
> **Return path:** To continue other M1 frameworks or proceed to M2, return to bi-m1 milestone workflow."

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
1. Verify five-whys.md has status: completed
2. Verify project-memo.md has Five Whys entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** five-whys.md complete with synthesis, project-memo.md updated with framework entry, Lean Canvas updated, M1 completion checked, stepsCompleted accurate in all files

❌ **FAILURE:** project-memo.md not updated, Lean Canvas not updated, synthesis missing, M1 completion not checked
