---
stepNumber: 4
stepName: 'document'
nextStepFile: null
outputFile: '{compound_output_folder}/{filename}.md'
---

# Step 04: Document

**Purpose:** Generate complete backlog PRD, save to configured output location, present completion summary.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Generate Complete PRD

Fill in all remaining template sections:

**Overview Section:**
- **Problem:** What went wrong? What behavior needs to change?
- **Goals:** What should happen instead?
- **Constraints:** Any limitations or requirements to consider

**Proposed Solution Section:**
- Select the improvement option from step-03 discussion (or best option if yoloMode)
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

### 2. Determine Output Filename

- Suggest filename based on improvement title
- Format: `{improvement-slug}.md` (lowercase, hyphens, descriptive)
- Examples:
  - `fix-rule-ambiguity-file-operations.md`
  - `add-constraint-git-commit-hooks.md`
  - `update-agent-persona-clarity.md`
- Ask user for confirmation or override

### 3. Save Document

- Write complete PRD to `{compound_output_folder}/{filename}.md`
- Preserve all frontmatter including `stepsCompleted` history
- Ensure all sections are populated (no empty sections)

### 4. Update State

- Add `step-04-document.md` to `stepsCompleted` array
- Mark workflow as complete (all 4 steps in `stepsCompleted`)
- Update frontmatter with final state

### 5. Present Completion Summary

- Display success message with file location
- Summarize what was documented
- Present the following menu and HALT
- Wait for user selection

---

## COMPLETION MESSAGE FORMAT

```
✅ Compound PRD created successfully!

📄 Location: {compound_output_folder}/{filename}.md

📋 Summary:
- Problem: [Brief problem statement]
- Solution: [Selected improvement option]
- Priority: [High/Medium/Low]

This PRD documents the proposed improvement and is ready for review and prioritization.

What would you like to do next?
[N] New Compound — Document another improvement
[DA] Dismiss Agent — Exit bmad-rbtv-doc
```

---

## MENU

Present the following menu and HALT. Wait for user selection.

**Options:**
- `[N] New Compound` → Reset workflow, start new compound PRD (load `step-01-init.md` with fresh context)
- `[DA] Dismiss Agent` → Exit bmad-rbtv-doc agent, return to normal chat

---

## NEXT STEP

None — this is the final step (`nextStepFile: null`).

---

## SUCCESS CRITERIA

- ✅ All PRD sections populated with content (no empty sections except optional ones)
- ✅ Output filename follows naming convention: lowercase, hyphens, descriptive (e.g., `fix-rule-ambiguity.md`)
- ✅ Document saved to configured output location (`{compound_output_folder}/{filename}.md`)
- ✅ `stepsCompleted` array contains exactly four entries: `step-01-init.md`, `step-02-self-assessment.md`, `step-03-discussion.md`, `step-04-document.md`
- ✅ Completion summary displayed with full file path
- ✅ Menu presented with `[N] New Compound` and `[DA] Dismiss Agent` options
