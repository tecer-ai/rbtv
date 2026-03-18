---
name: 'step-05-synthesis'
description: 'Estimate de-risking effort, determine overall posture, update project-memo'
nextStepFile: null
outputFile: '{outputFolder}/technology-readiness-level.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Assess overall technical readiness posture, consolidate findings, wire outputs into downstream milestones, and update project-memo.md with TRL synthesis.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. State the overall posture clearly and honestly. If Red, say Red. Don't soften bad news.

### Step-Specific Rules
- MUST determine overall posture (Green/Yellow/Red) with justification
- MUST wire outputs to Pre-mortem, M4, and M6
- MUST update project-memo.md with synthesis
- If posture is Red, MUST discuss implications for proceeding

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/technology-readiness-level.md` for all sections
2. Read `{outputFolder}/project-memo.md` for update location
3. Count components, TRL scores, spikes, and effort

---

## MANDATORY SEQUENCE

### 1. Calculate Summary Statistics

Compile from all steps:

| Metric | Count |
|--------|-------|
| Total components | [X] |
| Components at TRL 1-3 (High Risk) | [X] |
| Components at TRL 4-5 (Moderate Risk) | [X] |
| Components at TRL 6-9 (Low Risk) | [X] |
| Technical risks identified | [X] |
| High-uncertainty risks | [X] |
| Spikes required | [X] |
| Total de-risking effort | [X] person-days |
| De-risking timeline | [X] weeks |

### 2. Determine Overall Posture

Apply posture criteria:

| Posture | Criteria |
|---------|----------|
| 🟢 **Green** | All components TRL 4+, no spikes needed, moderate residual risks |
| 🟡 **Yellow** | 1-2 components below TRL 4, spikes < 2 weeks total |
| 🔴 **Red** | 3+ components below TRL 4, OR any below TRL 2 with no clear path |

Determine posture:

> "**Overall Technical Posture: [🟢 Green / 🟡 Yellow / 🔴 Red]**
>
> Justification: [Reasoning based on metrics]"

### 3. State Implications

**If Green:**
> "Technical foundation is solid. You can proceed to M4 Prototypation with standard engineering practices. Monitor [X] residual risks during development."

**If Yellow:**
> "Technical foundation is mostly solid, but [X] components need de-risking. Plan [Y] weeks of spike work before M4 Prototypation, or run spikes in parallel with early M4 planning.
>
> Key spikes to complete:
> 1. [Spike 1]
> 2. [Spike 2]"

**If Red:**
> "⚠️ Technical feasibility is in question. [X] components are at low TRL with significant unknowns.
>
> **Options:**
> 1. Invest [Y] weeks in technical de-risking before proceeding
> 2. Pivot the technical approach to reduce novelty
> 3. Invoke kill criteria if core tech is unproven
>
> **Recommendation:** [What you should do next]"

### 4. Wire Into Downstream Milestones

Document outputs for other frameworks:

**Pre-mortem (M2):**
> "Provide these as technical failure modes:
> - [TR-XX]: [Risk description]
> - [TR-YY]: [Risk description]
> - Low-TRL components: [TC-XX], [TC-YY]"

**M4 Prototypation:**
> "Provide TRL table and spike results for:
> - Architecture decisions (components at TRL 4-5 need extra attention)
> - Build sequencing (start with highest-TRL components)
> - Resource allocation (spike work before feature building)"

**M6 MVP:**
> "Provide residual risks for feature scope decisions:
> - Low-TRL components may need simpler alternatives
> - [List specific constraints for MVP]"

### 5. Consolidate Risk Summary

Create summary table:

| Risk ID | Component | Description | Severity | Action |
|---------|-----------|-------------|----------|--------|
| TR-01 | TC-XX | [Description] | High | Spike / Monitor / Accept |
| TR-02 | TC-YY | [Description] | Medium | Spike / Monitor / Accept |
| ... | ... | ... | ... | ... |

### 6. Create Final Spike Roadmap

If spikes exist, create visual roadmap:

```
Week 1          Week 2          Week 3          Week 4
|--------------|--------------|--------------|--------------|
[Spike 1: TC-01       ]
                [Spike 2: TC-02       ]
[Spike 3: TC-03]
                               [Spike 4: TC-04]
                                              → M4 Ready
```

State:
- Start date assumption
- Dependencies between spikes
- Go/No-Go decision point

### 7. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M2.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 8. Update Output Document

Finalize technology-readiness-level.md with:
- Summary statistics
- Overall posture with justification
- Implications and recommendations
- Downstream milestone inputs
- Risk summary
- Spike roadmap (if applicable)

Update frontmatter:
- Add `step-05-synthesis` to `stepsCompleted`
- Set `status: completed`
- Set `overallPosture: [green/yellow/red]`

### 9. Update project-memo.md

Add TRL synthesis to project-memo.md:

**In Validation Progress section:**
```markdown
### Technology Readiness Level
**Status:** Complete
**Overall Posture:** [🟢 Green / 🟡 Yellow / 🔴 Red]

**Component Summary:**
- Total: [X] components
- High Risk (TRL 1-3): [X]
- Moderate Risk (TRL 4-5): [X]
- Low Risk (TRL 6-9): [X]

**De-Risking Required:**
- Spikes needed: [X]
- Total effort: [X] person-days
- Timeline: [X] weeks

**Key Technical Risks:**
1. [TR-XX]: [Description] — [Action]
2. [TR-YY]: [Description] — [Action]

**Integration:** Risks wired to Pre-mortem; TRL table provided to M4
```

Update project-memo.md frontmatter: add `bi-m2-technology-readiness-level` to `stepsCompleted`

### 10. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 11. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M2.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M2 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 12. Present Completion Summary

> "## TRL Assessment Complete
>
> **Overall Posture:** [🟢 Green / 🟡 Yellow / 🔴 Red]
>
> **Key Findings:**
> - [X] components assessed, [Y] at low TRL
> - [X] technical risks identified
> - [X] spikes needed, [Y] person-days effort
>
> **Implications for M4:**
> - [What this means for prototypation]
>
> **Next Steps:**
> - [If Green]: Proceed to M4 Prototypation
> - [If Yellow]: Complete spikes, then proceed
> - [If Red]: Address feasibility concerns before proceeding
>
> [Return to M2 Milestone workflow]"

---

## VALIDATION CHECKLIST

Before completing, verify:
- [ ] Overall posture is stated (Green/Yellow/Red) with justification
- [ ] De-risking effort and timeline are estimated
- [ ] Technical risks are flagged for Pre-mortem
- [ ] M4 and M6 inputs are documented
- [ ] project-memo.md is updated with TRL synthesis
- [ ] If Red, implications are stated clearly

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Clear posture, honest implications, downstream frameworks connected

❌ **FAILURE:** Vague posture, softening Red to Yellow, not updating project-memo
