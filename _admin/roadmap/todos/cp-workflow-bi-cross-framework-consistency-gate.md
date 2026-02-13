---
title: 'Compound: Cross-Framework Consistency Gate via Party Mode'
docType: 'compound'
mode: 'create'
priority: 'Medium'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments:
  - '_bmad-output/robotville-v4.0/founder/m1-conception/working-backwards.md'
  - '_bmad-output/robotville-v4.0/founder/m1-conception/jobs-to-be-done.md'
  - '_bmad-output/robotville-v4.0/founder/m1-conception/problem-solution-fit.md'
  - '_bmad-output/robotville-v4.0/founder/project-memo.md'
outputPath: '_bmad-output/planning-artifacts'
date: '2026-02-13'
yoloMode: false
---

# Cross-Framework Consistency Gate via Party Mode

**Type:** Workflow
**Priority:** Medium
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

The Business Innovation (BI) workflow executes frameworks sequentially within each milestone. Later frameworks often produce insights (via Party Mode discussions, deeper analysis, or corrected assumptions) that contradict or refine claims made in earlier frameworks. The workflow has no backward reconciliation mechanism. Completed frameworks are never re-checked for consistency with newer outputs.

**Observed impact (robotville-v4.0 M1):** Problem-Solution Fit (framework #3) produced four material corrections to the customer model, emotional framing, segment definition, and competitor hierarchy. Two corrections were partially backported to JTBD during the PSF session. Zero were backported to Working Backwards. The project-memo still carries WB-era summaries. If M2 started without manual intervention, it would inherit conflicting narratives across its input documents.

### Goals

After 3 or more frameworks are completed within a single milestone, each subsequent framework completion should invite the user to run a cross-framework consistency review using Party Mode in a fresh context. The review should surface contradictions, alignment gaps, and assumption inventory overlaps — and produce actionable decisions (backport, override, or note as intentional evolution).

### Constraints

- Must not add significant workflow complexity — the BI workflow is already multi-step
- Must leverage existing infrastructure (Party Mode) rather than creating new review machinery
- Must run in fresh context to avoid anchoring bias from the just-completed framework
- Must be optional (recommended, not blocking) to respect the founder's pace and delivery targets
- Must work for any milestone, not just M1

---

## Self-Assessment

### Error Analysis

**Error Type:** Knowledge gap — cross-framework consistency gap.

No single framework was executed incorrectly. The issue is structural: later frameworks produced insights that invalidated or refined assumptions in earlier frameworks, and the system has no mechanism to enforce or even suggest backward reconciliation. The PSF Party Mode session corrected the emotional model (curiosity/uncertainty, not frustration/pain), narrowed the segment definition (people who've crossed to intent, not all idea-havers), elevated "do nothing" from one-of-six to the #1 competitor, and flagged end-to-end (M1-M6) as an unvalidated differentiator. JTBD was partially updated; WB and project-memo were not.

### Context Source Evaluation

| File | Issue |
|------|-------|
| `_bmad/rbtv/workflows/bi-business-innovation/` | **Gap:** No backward reconciliation step. Workflow moves forward only. No mechanism to flag when a later framework contradicts an earlier one. |
| `_bmad-output/.../working-backwards.md` | Contains pre-PSF emotional model, broad segment definition, "do nothing" as one-of-six. Not updated after PSF corrections. |
| `_bmad-output/.../jobs-to-be-done.md` | Partially updated — Forces Analysis includes PSF corrections. Hypothesis validation table and assumption numbering not reconciled. |
| `_bmad-output/.../problem-solution-fit.md` | Most current. Cross-references WB assumptions fully. Does NOT cross-reference JTBD assumptions. Treats end-to-end as validated despite JTBD flagging it as unvalidated (H3). |
| `_bmad-output/.../project-memo.md` | Carries WB-era summaries. Doesn't reflect PSF corrections to emotional model or segment narrowing. |

### Improvement Options

1. **New Rule**: Post-completion cross-framework consistency gate step in the BI workflow
   - **Rationale:** After each framework, agent checks key claims against all prior frameworks. Heaviest option — adds a mandatory step to every framework completion.
   - **Location:** New step file in `_bmad/rbtv/workflows/bi-business-innovation/steps-c/`

2. **Modify Existing Rule**: Add backward-looking "Alignment Check" sub-section to each framework's synthesis step
   - **Rationale:** Catches inconsistencies at the point of creation. Moderate weight — modifies every framework template.
   - **Location:** Each framework's final step file (e.g., `step-05-synthesis.md`)

3. **Update System File**: Add a canonical assumption registry to the project-memo template
   - **Rationale:** Single source of truth for assumptions, de-duplicated across frameworks. Solves the numbering overlap problem.
   - **Location:** `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md`

4. **Add Constraint**: Require all Party Mode contradictions to be resolved before marking a framework complete
   - **Rationale:** Prevents the exact scenario that occurred — framework marked complete while prior documents carry contradictory claims.
   - **Location:** Framework completion gate in each workflow's final step

5. **Alternative Approach (SELECTED)**: Party Mode consistency review invitation after 3+ frameworks complete in a milestone
   - **Rationale:** Lightest, most effective. Reuses existing Party Mode infrastructure. Fresh context eliminates anchoring bias. Multi-agent format naturally surfaces tensions a single-agent checklist would miss. Optional but recommended — respects founder pace.
   - **Location:** Framework completion logic in BI workflow

---

## Proposed Solution

**Selected: Option 5 — Party Mode Consistency Review Invitation**

After a framework is marked `status: completed` and the project-memo is updated, the framework completion step checks how many frameworks are now completed in the current milestone. If the count is 3 or more, a recommendation is displayed inviting the user to run a cross-framework consistency review via Party Mode in a fresh conversation.

### Behaviour

**Trigger condition:** `completed_frameworks_in_current_milestone >= 3`

**Display (after framework completion message):**

```
---

📋 **Cross-Framework Consistency Check (Recommended)**

You now have {count} completed frameworks in {milestone_name}. Later frameworks
often refine or contradict earlier ones. A Party Mode review catches drift before
it compounds.

**How:** Start a fresh conversation and run:

  /bmad-rbtv-mentor → PM → "Review all completed {milestone_name} frameworks
  for coherence" with @project-memo.md

💡 Fresh context is recommended — the review benefits from loading the documents
cold, without anchoring to the session that just completed.

---
```

**Key design decisions:**
- **Threshold = 3** (fixed, not relative). First two frameworks rarely contradict each other meaningfully. The third is where drift starts.
- **Every completion after 3** shows the invitation, not just once. The user may skip it after framework #3 but want it after #5. No tracking of whether they already did it.
- **Optional, not blocking.** The user can ignore it and proceed. No gate, no enforcement.
- **Fresh context is recommended, not enforced.** The prompt suggests a new conversation but doesn't prevent running it in the current session.
- **Copy-paste prompt included.** The user gets an exact command sequence so they don't need to remember what to ask or how to invoke Party Mode for this purpose.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | Each BI framework's completion/synthesis step file (the step that sets `status: completed` and updates project-memo). These are the `step-05-synthesis.md` (or equivalent final step) files within each framework's workflow directory under `_bmad/rbtv/workflows/bi-business-innovation/`. |
| Scope of change | Minimal — append a conditional display block to existing completion steps. No new files, no new templates, no new workflow logic. |
| Related files | `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` (may need a note in the workflow architecture section documenting this behaviour). `project-memo.md` template (already tracks `stepsCompleted` per milestone — the count is derivable from this). |

---

## Rationale

The BI workflow's sequential framework execution is correct — each framework builds on the previous ones. But "builds on" also means "may invalidate." The PSF Party Mode session proved that three expert agents reviewing all completed frameworks cold surfaced four material inconsistencies that the in-session agent missed entirely. This is not an agent failure — it's an architectural gap. The fix should match the problem's nature: lightweight, leveraging existing tools, and respecting the founder's pace.

Party Mode is the right mechanism because:
1. Multi-agent format naturally produces diverse perspectives (product, strategy, design, technical)
2. Fresh context eliminates the anchoring bias that makes the completing agent the worst reviewer of its own work
3. The infrastructure already exists and was proven effective in this exact scenario
4. No new step files, templates, or gate logic required — just a conditional display block

The five heavier alternatives (new gate steps, modified synthesis templates, canonical registries, mandatory resolution constraints, milestone-boundary reviews) solve the same problem with more machinery and more friction. They are documented in the Self-Assessment section for future reference if the lightweight approach proves insufficient.

---

## Acceptance Criteria

- [ ] Each BI framework's completion step checks the count of completed frameworks in the current milestone
- [ ] When count >= 3, a recommendation block is displayed with the Party Mode review invitation
- [ ] The recommendation includes a copy-paste prompt with the correct command sequence (`/bmad-rbtv-mentor → PM → review prompt + @project-memo.md`)
- [ ] The recommendation is non-blocking — user can proceed without running the review
- [ ] The recommendation appears after every framework completion when count >= 3 (not just the first time)
- [ ] The recommendation explicitly suggests fresh context (new conversation)

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` | Parent workflow — documents milestone/framework structure |
| `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-05-synthesis.md` (per framework) | Target modification — completion steps where the invitation is added |
| `_bmad/core/workflows/party-mode/workflow.md` | Leveraged infrastructure — Party Mode is the review mechanism |
| `_bmad-output/{project}/founder/project-memo.md` | Data source — `stepsCompleted` per milestone provides the framework count |

---

## References

- **Triggering session:** Party Mode cross-framework review of robotville-v4.0 M1 (Working Backwards, Jobs-to-be-Done, Problem-Solution Fit) — 2026-02-13
- **Participants:** Victor (Innovation Strategist), John (Product Manager), Maya (Design Thinking Coach)
- **Tensions identified:** (1) Emotional model drift WB→PSF, (2) Segment narrowing not backported, (3) Competitor hierarchy mismatch, (4) End-to-end confidence gap

---

## Discussion Notes

### Selected Improvement Option
Option 5 (Alternative Approach) — proposed by the founder as a simplification of the original five options. Party Mode consistency review invitation after 3+ frameworks complete in a milestone.

### Implementation Preferences
- **File Location:** Each BI framework's completion/synthesis step
- **Scope:** Minimal — conditional display block appended to existing steps
- **Priority:** Medium — implement before M2, not blocking M1 completion

### Additional Context
- Founder emphasized fresh context as critical — "very interesting insights and discussions may arise that may require context bandwidth"
- The review that surfaced this need was itself a Party Mode session, proving the mechanism works
- The 2-day delivery target means this should not block current M1 framework completion; document now, implement when touching the BI workflow next
