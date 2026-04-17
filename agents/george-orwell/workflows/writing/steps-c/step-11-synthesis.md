---
name: 'step-11-synthesis'
description: 'Apply critical review fixes, final polish, produce finished essay, and run style guide ritual'
styleGuideTemplate: '../data/style-guide-template.md'

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

### 7. "What Do You Notice?" — Style Guide Ritual

**This step feeds the completed essay back into the persistent style guide.** It is the mechanism that makes the system compound — each essay teaches the next.

**7a. Check for Style Guide**

Check if `styleGuide` is set in frontmatter OR if `{bmad_output}/style-guide.md` exists.

- If style guide exists: proceed to 7b.
- If no style guide AND user skipped creation in step 03: ask "Now that the essay is complete — want to create a persistent style guide from this work? It will grow with each essay." If yes, copy `{styleGuideTemplate}` to `{bmad_output}/style-guide.md` and proceed to 7b. If no, skip to step 8.

**7b. Analyze the Completed Essay**

Read the finished essay end-to-end. Compare against the current style guide. Identify:

1. **New structural patterns** — Did this essay follow the style guide's structural arc, or did a new pattern emerge? Name it if new.
2. **New signature moves** — Any recurring techniques worth naming and preserving?
3. **New anti-patterns discovered** — Any passages that were revised heavily? What went wrong? Worth adding to the blacklist?
4. **Voice confirmation or drift** — Did the essay reinforce the core directives, or reveal tensions worth documenting?
5. **Positive examples** — Identify 1-2 paragraphs that best exemplify the writer's voice. Explain why they work.
6. **Negative examples** — Identify passages that felt "off" or were heavily revised. Explain what went wrong.

**7c. Present Proposed Updates**

Present findings as proposed style guide updates. For each:
- What section of the guide it updates
- What specifically would be added or refined
- Why this matters for future essays

Ask: "Which updates should I apply to your style guide?"

**7d. Write Updates**

For each confirmed update:
- Append to the relevant section of `{bmad_output}/style-guide.md`
- NEVER overwrite existing entries — append only
- Add a changelog entry:
  ```
  ### {current date} — "{essay title}" (Essay #{essayCount + 1})
  - [list of changes made]
  ```
- Increment `essayCount` in style guide frontmatter
- Update `lastUpdated` to current date

### 8. Present Final Menu

**Essay complete. Select an Option:**
- **[A] Advanced Elicitation** — refine any section further
- **[P] Party Mode** — get multi-agent perspectives on the final essay
- **[D] Done** — return to George Orwell's main menu

ALWAYS halt and wait for user selection.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All approved fixes applied, all sources verified with links, essay is clean markdown ready for export, style guide ritual completed (if guide exists), user satisfied

❌ **FAILURE:** Unapproved changes made, broken source links remain, workflow metadata left in essay body, voice profile lost during edits, skipping the style guide ritual when a guide exists
