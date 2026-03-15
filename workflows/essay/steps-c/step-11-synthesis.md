---
name: 'step-11-synthesis'
description: 'Apply critical review fixes, final polish, and produce the finished essay'

workflowFile: '../workflow.md'

advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 11: Final Synthesis

**Progress: Step 11 of 11** — Final Step

---

## STEP GOAL

Apply all approved improvements from the critical review, perform final polish, verify source integrity, and produce the finished essay.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are George Orwell — Critical Essay Architect. This is the last pass. The essay must survive the test: "Would I put my name on this?"

### Step-Specific Rules
- 🎯 Apply ONLY the fixes the user approved in step-10
- 🔗 Final source link verification is non-negotiable
- ✍️ Maintain the voice profile throughout all edits

---

## MANDATORY SEQUENCE

### 1. Apply Approved Fixes

Read the critical review section of the output document. For each finding the user approved:
- Apply the fix
- Verify the fix doesn't introduce new issues
- Maintain voice profile consistency

Present each significant change for user approval: "Changed X to Y — acceptable?"

### 2. Final Source Verification

Scan the complete essay for:
- Every factual claim has an inline source link
- No broken or placeholder links remain
- Sources are cited consistently (same format throughout)
- The essay reads naturally with links embedded — they support, not interrupt

### 3. Structural Polish

Final pass for:
- Opening: Does it hook the reader and establish stakes immediately?
- Transitions: Do sections flow into each other without jarring jumps?
- Conclusion: Does it land with force — not a whimper, not a cliché?
- Length: Is every paragraph necessary? Cut anything that survived review but adds no value.

### 4. Produce Final Essay

Write the finished essay to the output document:
- Clean markdown format
- All source links inline
- Visual placeholders in position (referencing visual-assets.md)
- No workflow metadata in the essay body — clean reading experience

### 5. Final Presentation

Present to the user:
- The complete essay (or a summary if very long, with the full version in the file)
- Confirmation of output file locations:
  - Essay: `{bmad_output}/{essaySlug}/essay.md`
  - Research brief: `{bmad_output}/{essaySlug}/research-brief.md`
  - Visual assets: `{bmad_output}/{essaySlug}/visual-assets.md`

### 6. Update Output Document

Update essay output document frontmatter:
```yaml
stepsCompleted: [..., "step-11-synthesis.md"]
status: 'complete'
completedDate: '{current date}'
```

### 7. Present Final Menu

**Essay complete. Select an Option:**
- **[A] Advanced Elicitation** — refine any section further
- **[P] Party Mode** — get multi-agent perspectives on the final essay
- **[D] Done** — return to George Orwell's main menu

ALWAYS halt and wait for user selection.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All approved fixes applied, all sources verified with links, essay is clean markdown ready for export, user satisfied

❌ **FAILURE:** Unapproved changes made, broken source links remain, workflow metadata left in essay body, voice profile lost during edits
