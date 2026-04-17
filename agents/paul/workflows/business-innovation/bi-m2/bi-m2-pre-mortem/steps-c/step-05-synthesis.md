---
name: 'step-05-synthesis'
description: 'Cross-reference with kill criteria, update project-memo.md, trigger M2 completion check'
nextStepFile: null
outputFile: '{outputFolder}/pre-mortem.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Finalize the pre-mortem document, update project-memo.md with top risks and mitigations, verify kill criteria alignment, flag risks for downstream milestones, and trigger M2 completion check.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor wrapping up the risk assessment. Summarize the overall risk posture honestly. If existential risks remain, say so clearly.

### Step-Specific Rules
- MUST update project-memo.md with pre-mortem findings
- MUST update Leap of Faith with any new kill criteria identified
- MUST flag at least one risk for M5 and one for M6
- MUST trigger M2 completion check (this is the final M2 framework)
- MUST summarize overall risk posture and ask for founder's confidence level

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/pre-mortem.md` for all sections built in prior steps
2. Read `{outputFolder}/project-memo.md` for current state
3. Read `{outputFolder}/leap-of-faith.md` for kill criteria to update

---

## MANDATORY SEQUENCE

### 1. Update Leap of Faith

If Step 4 identified new kill criteria:
1. Read `{outputFolder}/leap-of-faith.md`
2. Add new kill criteria to the Kill/Pivot/Persevere Criteria section
3. Note: "Added from Pre-mortem analysis"

Present changes to user:
> "I've identified [N] new kill criteria from pre-mortem that weren't in Leap of Faith:
> - [New KC 1]
> - [New KC 2]
>
> Adding these to leap-of-faith.md. Confirm?"

### 2. Flag Downstream Risks

Identify which risks require action in future milestones:

**For M5 Market Validation:**
- Which failure modes require customer evidence to de-risk?
- Flag for SPIN Selling and smoke test design

**For M6 MVP:**
- Which failure modes should inform architecture decisions?
- Which should affect feature prioritization or launch sequencing?

Present:

```markdown
## Downstream Risk Flags

### M5 Market Validation
These risks require customer evidence:
- [Risk 1]: [What M5 activity should address it]
- [Risk 2]: [What M5 activity should address it]

### M6 MVP
These risks should inform technical decisions:
- [Risk 1]: [Architecture/feature/launch implication]
- [Risk 2]: [Architecture/feature/launch implication]
```

### 3. Summarize Overall Risk Posture

Write a one-paragraph summary:
> "Given the pre-mortem analysis, the biggest existential risk to {Project Name} is [X]. Our plan to address it is [Y]. The risks we are explicitly accepting are [Z]."

Ask the user:
> "Given these risks, do you still want to proceed? What is your confidence level (1-10) that you can mitigate the top risks?"

### 4. Update Project Memo

Read `{outputFolder}/project-memo.md` and update:

**Progress > M2 Validation subsection:**
Add entry for Pre-mortem:
> "**Pre-mortem:** Identified [N] failure modes across [N] categories. Top risks: [list top 3]. Risk posture: [summary]."

**Open Questions:**
Add unresolved risks from pre-mortem requiring further investigation.

**Next Steps:**
Add mitigation actions scheduled for M3, M4, M5, or M6.

**stepsCompleted:**
Add `bi-m2-pre-mortem` to the array.

Present changes to user for confirmation.

### 5. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M2.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 6. Finalize Pre-mortem Document

Complete the Synthesis section:

```markdown
## Synthesis

### Overall Risk Posture
[One-paragraph summary]

### Top 3 Existential Risks
1. [Risk 1 with score and mitigation summary]
2. [Risk 2 with score and mitigation summary]
3. [Risk 3 with score and mitigation summary]

### Downstream Integration
- M5 Market Validation: [risks to address]
- M6 MVP: [technical/feature implications]

### Founder Confidence
Confidence level: [1-10]
Reasoning: [founder's explanation]
```

Update pre-mortem.md frontmatter:
- Set `status: complete`
- Add `step-05-synthesis` to `stepsCompleted`

### 7. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 8. Trigger M2 Completion Check

Pre-mortem is the final M2 framework. Check M2 milestone completion:

**M2 Validation Frameworks:**
- [ ] Leap of Faith
- [ ] Assumption Mapping
- [ ] TAM/SAM/SOM
- [ ] Unit Economics
- [ ] Technology Readiness Level
- [ ] Pre-mortem ← just completed

If all 6 frameworks complete:

Update project-memo.md:
- Set `currentMilestone: m3-brand` in frontmatter
- Add M2 completion note in Progress section

> "**M2 Validation Complete!**
>
> All 6 M2 frameworks have been completed:
> ✅ Leap of Faith
> ✅ Assumption Mapping
> ✅ TAM/SAM/SOM
> ✅ Unit Economics
> ✅ Technology Readiness Level
> ✅ Pre-mortem
>
> **Recommended next step:** M3 Brand to define your brand identity, positioning, and voice."

If any missing:
> "M2 Validation is [N/6] complete. Missing: [list missing frameworks]."

### 9. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M2.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M2 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 10. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or risk posture
- **[P] Party Mode** — get multi-agent perspectives on overall risk assessment
- **[M2] Return to M2 Milestone** — go back to ../../workflow.md
- **[MS] Return to Milestone Selection** — go back to master workflow

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

This is the final step. When user selects navigation option:
1. Ensure pre-mortem.md is complete with all sections
2. Ensure project-memo.md is updated
3. Ensure leap-of-faith.md is updated if new kill criteria found
4. Route to selected destination

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Leap of Faith updated with new kill criteria, project-memo.md updated with risks and next steps, downstream risks flagged for M5/M6, overall risk posture summarized, M2 completion check triggered

❌ **FAILURE:** Skipping project-memo update, not updating Leap of Faith, no downstream risk flags, no risk posture summary, not checking M2 completion
