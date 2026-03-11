---
task_id: p3-refs
status: pending
phase: understand
complexity_score: 3
human_review: none
---

# Task p3-refs: File Reference Review

## Goal

Verify all internal markdown links in plan deliverables resolve correctly.

---

## Context Files

**MUST read every file in the table below before any execution phase.** Do not proceed to Phase: Understand until all are loaded and read.

| File | Purpose |
|------|---------|
| `.cursor/plans/align-skills-anthropic-spec/shape.md` | Plan context |

---

## Execution Flow

### Phase: Understand

1. **MUST** read every file in the Context Files table above. Do not continue until all are read.
2. In the plan file, set this task's todo to `status: in_progress`.

### Phase: Execute

1. Verify all file paths referenced in plan deliverables exist:
   - `_config/.cursor/rules/bmad-rbtv-skill-standards.mdc`
   - `workflows/prompting-assistance/data/platform_knowledge/claude_skills.md`
   - `workflows/prompting-assistance/data/knowledge-index.csv` (contains claude_skills entry)
   - `workflows/build-rbtv-component/templates/ide-command-template.md` (updated)
   - All 7 `_config/.cursor/skills/bmad-rbtv-*/SKILL.md` files (name field updated)
   - `agents/fernando.md` (updated with rule reference)
2. Verify internal links in the new rule file and platform knowledge document resolve

### Phase: Validate

1. All referenced paths exist
2. No broken links

### Phase: Close

1. Append execution entry to shape.md.
2. Present summary to user. Mark complete after approval.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Verification report | Chat output | Summary of checked paths |

---

## Revolving Plan Rules

**When discoveries occur:**
- Append discovery to shape.md Execution Discoveries section
- If work is complex (>5 min), add new task to plan with next available ID
- If work is simple, perform immediately and document
- **MANDATORY**: In output message, clearly state any tasks added or removed
