---
name: 'step-05-synthesis'
description: 'Prioritize jobs and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/jobs-to-be-done.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Prioritize jobs based on importance and satisfaction, synthesize key findings, and UPDATE project-memo.md to capture learnings across frameworks.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate clarity achieved. Note gaps that remain. Be honest about what was learned and what needs more validation.

### Step-Specific Rules
- project-memo.md MUST be updated with JTBD synthesis
- Synthesis must be concise (250 words max)
- Link to full jobs-to-be-done.md for details
- Mark framework as completed in project-memo frontmatter

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete jobs-to-be-done.md from Steps 1-4
- project-memo.md
- working-backwards.md (for consistency check)

**Out of scope:**
- Other M1 frameworks (separate workflows)
- M2 validation experiment design

---

## MANDATORY SEQUENCE

### 1. Prioritize Jobs

For each job identified, assess:

| Job | Importance (H/M/L) | Current Satisfaction (H/M/L) | Strategic Fit (H/M/L) |
|-----|-------------------|------------------------------|----------------------|
| [Job 1] | [H/M/L] | [H/M/L] | [H/M/L] |
| [Job 2] | [H/M/L] | [H/M/L] | [H/M/L] |
| [Job 3] | [H/M/L] | [H/M/L] | [H/M/L] |

**Priority rule:** Jobs that are High importance + Low satisfaction = most attractive.

Ask founder:
- "Which job, if we nailed it, would create the most value?"
- "Which job are customers most underserved on today?"
- "Which job fits best with our capabilities and vision?"

Select:
- **One primary job** for M1 focus
- Optionally 1-2 **secondary jobs** (explicitly not optimizing yet)

### 2. Synthesize Key Findings

Create a concise synthesis (250 words max) covering:

**Primary Job:** One sentence stating the job
**Why This Job:** Why it's more attractive than alternatives
**Key Forces:** What drives adoption and resistance
**Implications:** What this means for Problem-Solution Fit and Lean Canvas

### 3. Check Working Backwards Consistency

Compare JTBD findings to Working Backwards:
- Does the primary job align with the PR/FAQ customer narrative?
- Which PR/FAQ claims are supported by JTBD evidence?
- Which claims need revision based on JTBD insights?

### 4. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M1.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 5. Update jobs-to-be-done.md

Add Synthesis section to the output document:

```markdown
## Synthesis

### Job Prioritization

| Job | Importance | Satisfaction | Strategic Fit | Priority |
|-----|------------|--------------|---------------|----------|
| [Job 1] | [H/M/L] | [H/M/L] | [H/M/L] | Primary |
| [Job 2] | [H/M/L] | [H/M/L] | [H/M/L] | Secondary |
| [Job 3] | [H/M/L] | [H/M/L] | [H/M/L] | Deferred |

### Primary Job

**Statement:** When [situation], I want to [progress], so I can [outcome].

**Why This Job:** [One paragraph on why this is most attractive]

### Key Assumptions

1. [Assumption about job validity]
2. [Assumption about forces]
3. [Assumption about customer willingness to change]

### Framework Connections

- Feeds into: Problem-Solution Fit (grounds problem in job context)
- Feeds into: Lean Canvas (Customer Segments, Problem, UVP)
- Working Backwards alignment: [Supported / Needs revision / Mixed]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-job-hypotheses', 'step-03-interview', 'step-04-job-stories', 'step-05-synthesis']
status: completed
```

### 6. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m1-jobs-to-be-done` to `stepsCompleted` array

**In Progress > M1 Conception section:**

```markdown
### Jobs-to-be-Done

**Status:** Completed

**Primary Job:** When [situation], I want to [progress], so I can [outcome].

**Key Forces:**
- Push: [Main pain driving change]
- Anxiety: [Main fear resisting change]

**Top Assumptions:** [List 2-3]

**Output:** [Link to jobs-to-be-done.md]
```

### 7. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 8. Completion Summary

Present to founder:
> "Jobs-to-be-Done framework complete!
>
> **Primary job:** Our product is hired when [job statement].
>
> **Key insight:** [One sentence on most important finding]
>
> **What we achieved:**
> - Identified [N] job hypotheses from Working Backwards
> - Created interview guide for validation
> - Documented forces explaining adoption and resistance
> - Selected primary job for M1 focus
>
> **Next recommended framework:** [Competitive Landscape / Problem-Solution Fit / etc.]
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
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M1** — return to M1 Conception milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M1** is selected:
1. Verify jobs-to-be-done.md has status: completed
2. Verify project-memo.md has Jobs-to-be-Done entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** jobs-to-be-done.md complete with synthesis, project-memo.md updated with framework entry, primary job clearly stated, stepsCompleted accurate in both files

❌ **FAILURE:** project-memo.md not updated, synthesis missing, framework not marked complete, no primary job selected
