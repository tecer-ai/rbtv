---
name: 'step-05-synthesis'
description: 'Synthesize findings and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/conversion-optimization.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Synthesize Conversion-Centered Design findings into a concise summary and UPDATE project-memo.md to capture learnings for the broader project context.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate clarity achieved. Be honest about what was learned. Connect conversion insights to the broader founder journey — how do these optimizations impact M5 market validation?

### Step-Specific Rules
- project-memo.md MUST be updated with Conversion Optimization synthesis
- Synthesis must be concise (300 words max)
- Link to full conversion-optimization.md for details
- Mark framework as completed in project-memo frontmatter
- Connect to Heuristic Evaluation [H] as natural next step

---

## CONTEXT BOUNDARIES

**Available context:**
- Complete conversion-optimization.md from Steps 1-4
- project-memo.md

**Out of scope:**
- Implementation of optimizations (that's a separate task)
- Heuristic Evaluation (separate framework)
- M5 Market Validation details

---

## MANDATORY SEQUENCE

### 1. Review Completed Work

Summarize what was accomplished:

> "Let's review what we built:
> 
> **Funnel Analysis:**
> - Analyzed [N] AIDA stages for [artifact type]
> - Conversion goal: [goal]
> 
> **Friction Points:**
> - Identified [N] friction points
> - [N] Critical, [N] Major, [N] Moderate
> 
> **Hypotheses:**
> - Generated [N] optimization hypotheses
> - Top hypothesis: [name] — expected [impact]
> 
> **Prioritization:**
> - [N] quick wins ready to implement
> - [N] scheduled for later batches
> 
> **Testing Roadmap:**
> - Phase 1 timeline: [estimate]
> - Success criteria defined for Batch 1"

### 2. Draft Framework Synthesis

Create a concise synthesis (300 words max) covering:

**Key Findings:**
- Primary conversion barrier: [one sentence]
- Biggest opportunity: [one sentence]
- CTA status: [optimized/needs work/critical issues]

**Top Optimizations:**
1. [Quick win #1 with expected impact]
2. [Quick win #2 with expected impact]
3. [Planned optimization with timeline]

**Conversion Posture:**
- Current: [Red/Yellow/Green] — [rationale]
- After Batch 1: [expected posture]

**Connections to Other Frameworks:**
- Heuristic Evaluation [H]: Apply optimizations before evaluation
- Testing Prep [F]: Success criteria feed into F&F test protocol
- M5 Market Validation: Optimized prototype ready for real customer testing

### 3. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/agents/paul/workflows/business-innovation/data/founder-process.md` for M4.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 4. Update conversion-optimization.md

Add Synthesis section to the output document:

```markdown
## Synthesis

### Key Findings

**Primary Conversion Barrier:** [one sentence]

**Biggest Opportunity:** [one sentence]

**CTA Status:** [assessment]

### Top Optimizations

1. **[Quick Win #1]** — [expected impact]
2. **[Quick Win #2]** — [expected impact]
3. **[Planned]** — [timeline and impact]

### Conversion Posture

**Current:** [Red/Yellow/Green] — [rationale]
**After Batch 1:** [expected posture]

### Framework Connections

- **Heuristic Evaluation [H]:** Implement Batch 1, then evaluate usability
- **Testing Prep [F]:** Success criteria inform F&F test protocol
- **M5 Market Validation:** Optimized prototype enables valid market testing
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-funnel-mapping', 'step-03-hypothesis-generation', 'step-04-optimization-plan', 'step-05-synthesis']
status: completed
```

### 5. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m4-conversion-centered-design` to `stepsCompleted` array

**In Progress > M4 Prototypation section:**

```markdown
### Conversion Optimization

**Status:** Completed

**Key Findings:**
- Primary Barrier: [one sentence]
- Biggest Opportunity: [one sentence]
- CTA Status: [assessment]

**Top Optimizations:**
1. [Quick win #1]
2. [Quick win #2]
3. [Planned optimization]

**Conversion Posture:** [Current] → [After Batch 1]

**Output:** [Link to conversion-optimization.md]
```

### 6. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 7. Completion Summary

Present to founder:

> "Conversion-Centered Design framework complete!
> 
> **What we achieved:**
> - Analyzed conversion funnel through 7 CCD principles
> - Identified [N] friction points ([N] Critical/Major)
> - Generated [N] optimization hypotheses
> - Prioritized into actionable batches
> - Created testing roadmap with success criteria
> 
> **Conversion Posture:** [Current] → [Expected after Batch 1]
> 
> **Recommended Next Steps:**
> 1. Implement Batch 1 quick wins
> 2. Run Heuristic Evaluation [H] to catch usability issues
> 3. Prepare for F&F testing with Testing Prep [F]
> 
> **Return path:** To continue M4 frameworks, return to bi-m4 milestone workflow."

### 8. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M4.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M4 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 9. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M4** — return to M4 Prototypation milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M4** is selected:
1. Verify conversion-optimization.md has status: completed
2. Verify project-memo.md has Conversion Optimization entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** conversion-optimization.md complete with synthesis, project-memo.md updated with framework entry, stepsCompleted accurate in both files, clear next steps communicated

❌ **FAILURE:** project-memo.md not updated, synthesis missing, framework not marked complete, no connection to next frameworks
