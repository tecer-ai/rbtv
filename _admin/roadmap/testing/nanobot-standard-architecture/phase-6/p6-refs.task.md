---
task_id: p6-refs
status: pending
phase: understand
complexity_score: 8
human_review: none
---

# Task p6-refs: File Reference Review

## Goal

Verify all internal markdown links across the RBTV codebase resolve correctly after the restructuring. Fix any broken references.

---

## Context Files

**MUST read every file in the table below before any execution phase.** Do not proceed to Phase: Understand until all are loaded and read.

| File | Purpose |
|------|---------|
| `_admin/roadmap/todos/_claude-code-workspace/nanobot-standard-architecture/shape.md` | Execution context, all changes made during plan |

---

## Tools

**Available tools:** Read `_config/tools-manifest.csv` for full list.

| Tool | Mode | Purpose |
|------|------|---------|
| context-search | skill | Scan for broken references across codebase |

---

## Execution Flow

### Phase: Understand

1. **MUST** read every file in the Context Files table above.
2. Set this task's todo to `status: in_progress` in the plan file.
3. Review shape.md execution log to identify all files created, moved, renamed, or deleted during this plan.
4. Build a list of paths that changed.

### Phase: Execute

1. Search all markdown files for references to changed paths.
2. Search all YAML frontmatter for references to changed paths.
3. For each broken reference found:
   - Determine correct new path.
   - UPDATE the referencing file.
4. Verify `bmad-compat.yaml` touchpoints still resolve after all changes.

**Discovery Handling:**
- If widespread breakage is found: document scope in shape.md, fix systematically.

### Phase: Validate

1. Re-scan for broken references — expect zero results.
2. Spot-check 10 key files for correct internal links.

### Phase: Close

1. Append execution entry to shape.md with count of references fixed.
2. Present summary to user. Do not mark complete until user approves.
3. After approval, set todo to `status: completed`.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Fixed references | Various files | Updated markdown/YAML links |

---

## Revolving Plan Rules

**When discoveries occur:**
- Append discovery to shape.md Execution Discoveries section
- If work is complex (>5 min), add new task to plan with next available ID
- If work is simple, perform immediately and document
- **MANDATORY**: In output message, clearly state any tasks added or removed
