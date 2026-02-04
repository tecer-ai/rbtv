---
stepNumber: 4
stepName: 'document'
nextStepFile: null
outputFile: '{outputFolder}/{filename}.md'
---

# Step 04: Document Generation

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Generate the complete handoff summary document, save to the configured location, and present completion summary.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Context Curator. Continue your existing persona as Ana and communication style.

### Step-Specific Rules

- Use all extracted content from step-03
- Include all type-specific sections
- Never overwrite existing handoff files
- Include self-cleanup instruction for receiving agent

---

## MANDATORY SEQUENCE

### 1. Compile Document Sections

Using the extracted content from step-03, populate the template sections:

**Section: Context Summary**

```markdown
## Context Summary

{Brief overview of the conversation/project state — 2-3 sentences maximum}
```

**Section: Problem Being Solved**

```markdown
## Problem Being Solved

{Clear statement of what the receiving agent should address}

### Current State

{Where we are now — what's been completed, what's in progress}

### Root Cause (if applicable)

{Why the problem exists — helpful for debugging/planning contexts}
```

**Section: User Goals**

```markdown
## User Goals

{What the user wants to achieve — explicit goals from the conversation}

1. {Goal 1}
2. {Goal 2}
3. {Goal 3}
```

**Section: Constraints Gathered**

```markdown
## Constraints Gathered

{Technical, process, and project constraints that must be respected}

| Constraint | Type | Description |
|------------|------|-------------|
| {Constraint 1} | {Technical/Process/Scope} | {Details} |
| {Constraint 2} | {Technical/Process/Scope} | {Details} |
```

**Section: Decisions Already Made**

```markdown
## Decisions Already Made

{Prevent receiving agent from re-deciding settled matters}

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| {Decision 1} | {Why this choice} | {What we didn't do and why} |
| {Decision 2} | {Why this choice} | {What we didn't do and why} |
```

**Section: Information Gaps**

```markdown
## Information Gaps

{What remains unclear or needs resolution — "None" if all context provided}

- {Gap 1 — if any}
- {Gap 2 — if any}
```

**Section: Files to Load**

```markdown
## Files to Load

{Critical files the receiving agent MUST read before proceeding}

| File | Purpose | Priority |
|------|---------|----------|
| {path/to/file.md} | {Why this file matters} | MUST READ FIRST |
| {path/to/another.md} | {Why this file matters} | Reference |
```

### 2. Add Type-Specific Sections

**For plan-development handoffs:**

```markdown
## Judge Feedback Summary

**Status:** {Approved | Needs Revision | Pending Review}

**Issues Identified:**
- {Issue 1}
- {Issue 2}

**Requirement Coverage:**
- {Requirement 1}: ✅ Covered / ❌ Missing
- {Requirement 2}: ✅ Covered / ❌ Missing
```

**For execution handoffs:**

```markdown
## Task Instructions

### Execution Order

1. {First task}
2. {Second task}
3. {Third task}

### Guidelines

- {Approach or methodology to follow}
- {Constraints on execution}
```

### 3. Add Agent Instructions Section

```markdown
## For the Agent Reading This Handoff

{Step-by-step instructions for the receiving agent}

### Immediate Next Steps

1. {Step 1 — most important action}
2. {Step 2}
3. {Step 3}

### Guidelines

- {Guideline 1 — approach or methodology to follow}
- {Guideline 2}

### What NOT to Do

- {Anti-pattern 1 — common mistakes to avoid}
- {Anti-pattern 2}
```

### 4. Add Self-Cleanup Section

```markdown
---

## Self-Cleanup Instruction

After successfully completing the handoff instructions, consider whether this handoff document is still needed:

- If the work is complete → Delete this handoff file
- If work continues → Update or create a new handoff for the next agent
```

### 5. Add References Section

```markdown
## References

{Links to relevant documentation, prior handoffs, or external resources}

| Reference | Purpose |
|-----------|---------|
| {path or URL} | {How it relates} |
```

### 6. Check for Existing File

- Check if a file with the target name exists at the selected location
- If it exists, append `_2`, `_3`, `_4`, etc. to the filename (before the extension)
- Never overwrite existing handoff files

### 7. Save Document

- Write complete handoff to `{outputPath}/{filename}.md`
- Preserve all frontmatter including `stepsCompleted` history
- Ensure all sections are populated (no empty sections)

### 8. Update State

- Add `step-04-document.md` to `stepsCompleted` array
- Mark workflow as complete (all 4 steps in `stepsCompleted`)
- Update frontmatter with final state

### 9. Present Completion Summary

Display success message:

```
✅ Handoff summary created successfully!

📄 Location: {outputPath}/{filename}.md

📋 Summary:
- Type: {Handoff Type}
- Problem: {Brief problem statement}
- Goals: {count} captured
- Decisions: {count} documented
- Files to Load: {count} referenced

This handoff is ready for the receiving agent.

What would you like to do next?
[N] New Handoff — Create another handoff summary
[DA] Dismiss Agent — Exit bmad-rbtv-doc
```

HALT and wait for user selection.

---

## MENU OPTIONS

- `[N] New Handoff` → Reset workflow, start new handoff (load `step-01-init.md` with fresh context)
- `[DA] Dismiss Agent` → Exit bmad-rbtv-doc agent, return to normal chat

---

## CRITICAL STEP COMPLETION NOTE

This is the final step. No next step file to load.

On `[N] New Handoff`:

1. Clear session context
2. Load `step-01-init.md` to start fresh

On `[DA] Dismiss Agent`:

1. Thank the user
2. Exit gracefully

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**

- All handoff sections populated with content (no empty sections)
- Type-specific sections included for plan-development/execution handoffs
- Self-cleanup instruction included
- File saved to configured output location
- Filename follows naming convention: `handoff-{context-slug}.md`
- `stepsCompleted` contains all 4 steps
- Completion summary displayed with full file path
- Menu presented with `[N] New Handoff` and `[DA] Dismiss Agent` options

❌ **FAILURE:**

- Handoff saved with empty sections
- Overwriting existing handoff file
- Missing self-cleanup instruction
- Filename doesn't follow naming convention
- Document saved to wrong location
- `stepsCompleted` array incomplete
- Completion summary missing file path
