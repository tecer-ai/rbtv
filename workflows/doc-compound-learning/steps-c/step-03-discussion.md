---
stepNumber: 3
stepName: 'discussion'
nextStepFile: ./step-04-document.md
outputFile: '{compound_output_folder}/{filename}.md'
---

# Step 03: Discussion

**Purpose:** Present self-assessment findings to user, discuss proposed improvements, capture user preferences.

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

### 6. Update State

- Add `step-03-discussion.md` to `stepsCompleted` array
- Save updated output document to memory

### 7. Present Menu

- Present the following menu and HALT
- Wait for user selection

---

## MENU

Present the following menu and HALT. Wait for user selection.

**Options:**
- `[C] Continue` → Proceed to `step-04-document.md` to generate final PRD
- `[RA] Revise Assessment` → Return to `step-02-self-assessment.md` for refinement (does NOT update `stepsCompleted` — allows re-execution of step-02)
- `[X] Exit Workflow` → Save current state, exit agent

---

## NEXT STEP

On Continue selection:
1. Update output document frontmatter: add `step-03-discussion.md` to `stepsCompleted` array
2. Load and execute: `./step-04-document.md`

---

## YOLO MODE BEHAVIOR

If `yoloMode = true`:
1. Skip all discussion steps (1-7)
2. Immediately load `step-04-document.md`
3. Agent makes best judgment on improvement option without user input

---

## SUCCESS CRITERIA

- ✅ Yolo flag checked at start of step; if `yoloMode = true`, step immediately loads step-04 without executing discussion
- ✅ Self-assessment summary presented to user (2-3 sentence summary)
- ✅ User preferences captured: selected improvement option, file location, scope, priority
- ✅ Discussion notes appended to output document's `## Discussion Notes` section
- ✅ `stepsCompleted` array contains exactly three entries: `step-01-init.md`, `step-02-self-assessment.md`, `step-03-discussion.md`
- ✅ Menu presented with explicit HALT and execution stopped
