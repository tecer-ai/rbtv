---
task_id: p7-compound
status: pending
phase: understand
complexity_score: 9
human_review: optional
---

# Task p7-compound: Compound Learnings

## Goal

Review learnings.md and compound entries into actionable BMAD/RBTV system improvements.

---

## Context Files

| File | Purpose |
|------|---------|
| learnings.md | Source: accumulated learnings |
| shape.md | Context: execution history |

---

## Tools

| Tool | Mode | Purpose |
|------|------|---------|
| Read | direct | Load learnings |
| Write | direct | Update learnings with compound output |
| compound-learning | skill | Process learnings into system improvements |

---

## Execution Flow

### Phase: Understand

1. Read learnings.md for all accumulated entries
2. Identify entries marked "compound-ready" (all 4 checkboxes checked)
3. If no learnings accumulated, this task completes quickly

### Phase: Execute

1. For each compound-ready learning:
   - Identify target BMAD/RBTV component
   - Determine change type (Add rule | Clarify instruction | New template | Tool enhancement)
   - Draft specific proposed change

2. Group related learnings by target component

3. Generate compound documents in learnings.md:
   ```
   ## Compound: {Component Name} Improvements
   
   **Source Learnings:** L1, L5, L8
   **Target:** {File path}
   
   ### Changes
   1. {Change 1}
   2. {Change 2}
   
   ### Implementation Notes
   {How to apply}
   ```

4. Mark processed learnings: append "Compounded: YYYY-MM-DD"

### Phase: Validate

1. Verify all compound-ready learnings are processed
2. Verify compound documents have clear implementation paths
3. Present compound summary to user

### Phase: Close

1. Append execution entry to shape.md
2. Mark task status as completed in plan YAML
3. Report: "X learnings processed into Y compound documents"

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Compound documents | learnings.md | Compound sections |
| Processing markers | learnings.md | "Compounded: date" lines |

---

## Revolving Plan Rules

**When discoveries occur:**
- If compound reveals need for additional plan work, add new task
- **MANDATORY**: In output message, clearly state any tasks added or removed

---

## Special Note

If learnings.md is empty or has no compound-ready entries, this task completes with:
"No learnings accumulated during execution. Task complete."
