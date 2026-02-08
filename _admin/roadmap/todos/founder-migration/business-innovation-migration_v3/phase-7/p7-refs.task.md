---
task_id: p7-refs
status: pending
phase: understand
complexity_score: 7
human_review: none
---

# Task p7-refs: File Reference Review

## Goal

Verify all internal markdown links in created BI workflow files resolve correctly.

---

## Context Files

| File | Purpose |
|------|---------|
| All created bi-* workflow files | Target files for reference validation |
| shape.md | Execution log for file list |

---

## Tools

| Tool | Mode | Purpose |
|------|------|---------|
| Grep | direct | Search for markdown links |
| Read | direct | Verify link targets exist |
| Write | direct | Fix broken links |

---

## Execution Flow

### Phase: Understand

1. Read shape.md execution log for list of all created files
2. Identify all files that need reference checking

### Phase: Execute

1. For each workflow.md and step file:
   - Extract all markdown links `[text](path)`
   - Extract all relative path references
   - Verify each referenced file exists

2. Compile list of broken references:
   | File | Broken Link | Expected Target |
   |------|-------------|-----------------|
   
3. Fix each broken reference:
   - Update path to correct location
   - Document fix in shape.md

### Phase: Validate

1. Re-run reference check
2. Verify all links now resolve
3. Zero broken references = success

### Phase: Close

1. Append execution entry to shape.md with reference audit results
2. Mark task status as completed in plan YAML
3. Report: "X references checked, Y fixed, 0 remaining broken"

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Reference audit log | shape.md | Execution Log entry |
| Fixed files | Various | Updated markdown links |

---

## Revolving Plan Rules

**When discoveries occur:**
- If systematic naming issue found, document pattern in learnings.md
- **MANDATORY**: In output message, clearly state any tasks added or removed
