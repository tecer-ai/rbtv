---
stepNumber: 3
stepName: 'discussion-and-document'
nextStepFile: null
outputFile: '{outputFolder}/{filename}.md'
---

# Step 03: Discussion & Document

**Purpose:** Present self-assessment findings to user, discuss proposed improvements, capture user preferences, generate complete backlog PRD, and save to configured output location.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Check Yolo Flag

- Read the output document frontmatter
- If `yoloMode: true` → SKIP this entire step, immediately load `step-04-document.md`
- If `yoloMode: false` → Continue with discussion

### 2. Present Self-Assessment Summary

- Summarize the error analysis in 2-3 sentences
- Highlight the top 2-3 improvement options (based on impact and feasibility)
- Ask user: "Which improvement direction would you like to pursue?"

### 3. Discuss Implementation Details

For the user's selected improvement option(s), discuss:
- **Proposed file location:** Where should this change be implemented?
- **Scope of change:** How extensive is the modification?
- **Related files:** What other files may need updates?
- **Priority/urgency:** How critical is this improvement?

Ask clarifying questions:
- "Should this apply globally or only in specific contexts?"
- "Are there edge cases we should consider?"
- "Do you prefer a minimal fix or a comprehensive solution?"

### 4. Capture User Preferences

- Document which improvement option(s) the user wants to pursue
- Record preferred file location
- Note any additional context or constraints mentioned by the user
- Capture priority level (High/Medium/Low)

### 5. Append Discussion to Output Document

Write to `## Discussion Notes` section:

```markdown
## Discussion Notes

### Selected Improvement Option
[Which option(s) the user chose]

### Implementation Preferences
- **File Location:** [User's preferred location]
- **Scope:** [Minimal/Moderate/Comprehensive]
- **Priority:** [High/Medium/Low]

### Additional Context
[Any constraints, edge cases, or considerations mentioned by user]
```

### 6. Present Discussion Menu

Present the following menu and HALT. Wait for user selection.

**Options:**
- `[C] Continue` → Proceed to generate the final PRD (Phase 2 below)
- `[RA] Revise Assessment` → Return to `step-02-self-assessment.md` for refinement (does NOT update `stepsCompleted` — allows re-execution of step-02)
- `[X] Exit Workflow` → Save current state, exit agent

---

## PHASE 2: DOCUMENT GENERATION

Execute this phase when the user selects `[C] Continue` from the discussion menu, or immediately after yolo mode skips the discussion phase.

### 7. Generate Complete PRD

Fill in all remaining template sections:

**Overview Section:**
- **Problem:** What went wrong? What behavior needs to change?
- **Goals:** What should happen instead?
- **Constraints:** Any limitations or requirements to consider

**Proposed Solution Section:**
- Select the improvement option from discussion (or best option if yoloMode)
- Provide detailed specification of the proposed change
- Include code examples or rule wording if applicable

**Implementation Details Table:**

```markdown
| Aspect | Details |
|--------|---------|
| File(s) to modify/create | [Specific file paths] |
| Scope of change | [Minimal/Moderate/Comprehensive] |
| Related files | [Dependencies and files that may need updates] |
```

**Rationale Section:**
- Explain why this solution addresses the problem
- Reference the error analysis from step-02
- Justify the approach over alternatives

**Acceptance Criteria:**
- List at least 3 specific, testable criteria
- Format as checkboxes:

```markdown
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
```

**Related Files Table:**

```markdown
| File | Relationship |
|------|--------------|
| [path] | [How it relates — influences, depends on, conflicts with] |
```

**References Section:**
- Link to relevant documentation
- Include conversation context if applicable
- Reference related PRDs or issues

### 8. Save Document

- Write complete PRD to `{outputFolder}/{filename}.md`
- Preserve all frontmatter including `stepsCompleted` history
- Ensure all sections are populated (no empty sections)

### 9. Update State

- Add `step-03-discussion-and-document.md` to `stepsCompleted` array
- Mark workflow as complete (all 3 steps in `stepsCompleted`)
- Update frontmatter with final state

### 10. Present Completion Summary

Display success message:

```
✅ Compound PRD created successfully!

📄 Location: {outputFolder}/{filename}.md

📋 Summary:
- Problem: [Brief problem statement]
- Solution: [Selected improvement option]
- Priority: [High/Medium/Low]

This PRD documents the proposed improvement and is ready for review and prioritization.

What would you like to do next?
[N] New Compound — Document another improvement
[DA] Dismiss Agent — Exit doc
```

HALT and wait for user selection.

---

## COMPLETION MENU

- `[N] New Compound` → Reset workflow, start new compound PRD (load `step-01-init.md` with fresh context)
- `[DA] Dismiss Agent` → Exit doc agent, return to normal chat

---

## YOLO MODE BEHAVIOR

If `yoloMode = true`:
1. Skip discussion phase (substeps 1-6)
2. Agent makes best judgment on improvement option without user input
3. Proceed directly to Phase 2: Document Generation (substep 7)

---

## SUCCESS CRITERIA

- ✅ Yolo flag checked at start of step; if `yoloMode = true`, skip discussion and proceed to document generation
- ✅ Self-assessment summary presented to user (2-3 sentence summary) — unless yoloMode
- ✅ User preferences captured: selected improvement option, file location, scope, priority — unless yoloMode
- ✅ Discussion notes appended to output document's `## Discussion Notes` section — unless yoloMode
- ✅ All PRD sections populated with content (no empty sections except optional ones)
- ✅ Output filename follows naming convention: `cp-{component}-{description}.md`
- ✅ Document saved to configured output location
- ✅ `stepsCompleted` array contains exactly three entries: `step-01-init.md`, `step-02-self-assessment.md`, `step-03-discussion-and-document.md`
- ✅ Completion summary displayed with full file path
- ✅ Menu presented with `[N] New Compound` and `[DA] Dismiss Agent` options
