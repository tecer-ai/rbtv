---
task_id: p5-compound
status: pending
phase: understand
complexity_score: 4
human_review: optional
executor: claude
reviewer: claude-opus
---

# Task p5-compound: Compound learnings into system improvements

## Goal

Process every entry in `../learnings.md` into actionable system changes (or explicitly mark none compound-ready), per the Compound Generation section of that file.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../learnings.md` | The entries to process and the compound criteria/process |
| `../deliverables.md` | Artifact index — the read-order for synthesis inputs |
| `../decisions.md` | Execution discoveries that may contextualize learnings |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).

### Phase: Execute
1. Review each learning entry; assess Compound Readiness checkboxes.
2. Group compound-ready learnings by target component; draft the compound blocks per the template in `../learnings.md` § Compound Generation.
3. Follow `rbtv-compounding`: state each structural fix and where it would go; ask the user before implementing. Compound PRDs the user approves land per the vault routing table (`.user/compounds/{component}/`).
4. Mark processed learnings with a `Compounded: YYYY-MM-DD` line.

### Phase: Validate
1. Every learning entry is either compounded or carries an explicit not-ready reason.

### Phase: Close
Standalone close: append nothing routine to decisions.md; present the compound summary to the user; on approval flip plan checkbox, frontmatter status, `../deliverables.md` row.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Compound blocks / PRD proposals | appended to `../learnings.md` (+ user-approved PRDs per vault routing) | markdown |
