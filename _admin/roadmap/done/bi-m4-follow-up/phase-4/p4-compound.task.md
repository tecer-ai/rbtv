---
task_id: p4-compound
status: pending
phase: close
complexity_score: 5
human_review: optional
---

# Task p4-compound: Review learnings.md and Compound into System Improvements

## Goal

Review .cursor/plans/bi-m4-follow-up/learnings.md Learning Entries. Produce a short compound note summarizing BMAD/RBTV system improvement opportunities. Append the compound output to learnings.md under "Compound Generation" section. Do not remove or modify existing learning entries.

---

## Context Files

| File | Purpose |
|------|---------|
| .cursor/plans/bi-m4-follow-up/learnings.md | Learning Entries, Compound Generation section |

---

## Execution Flow

### Phase: Understand

1. Read learnings.md Learning Entries (if any)
2. Read "What Belongs Here" and Compound Generation instructions in template

### Phase: Execute

1. If no learning entries: append a single line under Compound Generation: "No learning entries recorded during this run."
2. If learning entries exist: summarize by category (missing rule, workflow gap, tool limitation, etc.); suggest 1–3 concrete improvements for BMAD/RBTV; append compound note under Compound Generation in learnings.md
3. Do not delete or edit existing learning entries

### Phase: Validate

1. learnings.md is append-only; no previous content removed
2. Compound is concise and actionable for system maintainers

### Phase: Close

1. Append execution entry to shape.md Execution Log
2. Mark task completed in plan YAML if updating plan state

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Compound note | .cursor/plans/bi-m4-follow-up/learnings.md | Appended under Compound Generation |

---

## Revolving Plan Rules

- **MANDATORY:** In output message, state any tasks added or removed
