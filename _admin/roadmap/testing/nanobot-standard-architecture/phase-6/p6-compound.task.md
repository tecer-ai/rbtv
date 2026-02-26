---
task_id: p6-compound
status: pending
phase: understand
complexity_score: 7
human_review: optional
---

# Task p6-compound: Compound Learnings into System Improvements

## Goal

Process all entries in `learnings.md` that are marked compound-ready and generate actionable system improvement documents.

---

## Context Files

**MUST read every file in the table below before any execution phase.** Do not proceed to Phase: Understand until all are loaded and read.

| File | Purpose |
|------|---------|
| `_admin/roadmap/todos/_claude-code-workspace/nanobot-standard-architecture/learnings.md` | Source of meta-learnings to compound |
| `_admin/roadmap/todos/_claude-code-workspace/nanobot-standard-architecture/shape.md` | Execution context |

---

## Tools

**Available tools:** Read `_config/tools-manifest.csv` for full list.

| Tool | Mode | Purpose |
|------|------|---------|
| doc | skill | Generate compound learning documents |

---

## Execution Flow

### Phase: Understand

1. **MUST** read every file in the Context Files table above.
2. Set this task's todo to `status: in_progress` in the plan file.
3. Review all learning entries in learnings.md.
4. Identify entries with all four Compound Readiness checkboxes checked.
5. If no compound-ready entries exist, skip to Phase: Close with "No learnings to compound" summary.

### Phase: Execute

1. Group compound-ready learnings by target component.
2. For each group, generate a compound improvement document:
   - Source learnings referenced
   - Target file/component
   - Specific changes proposed
   - Implementation notes
3. Save compound documents to `_admin-output/` (admin output folder).
4. Mark processed learnings in learnings.md (append "Compounded: YYYY-MM-DD" line).

**Discovery Handling:**
- If learnings reveal systemic issues: document as new compound recommendation.

### Phase: Validate

1. Verify all compound-ready learnings were processed.
2. Verify compound documents are actionable and specific.

### Phase: Close

1. Append execution entry to shape.md.
2. Present summary to user with compound documents created. Do not mark complete until user approves.
3. After approval, set todo to `status: completed`.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Compound documents | `_admin-output/` | Markdown |
| Updated learnings | `learnings.md` | Appended "Compounded" markers |

---

## Revolving Plan Rules

**When discoveries occur:**
- Append discovery to shape.md Execution Discoveries section
- If work is complex (>5 min), add new task to plan with next available ID
- If work is simple, perform immediately and document
- **MANDATORY**: In output message, clearly state any tasks added or removed
