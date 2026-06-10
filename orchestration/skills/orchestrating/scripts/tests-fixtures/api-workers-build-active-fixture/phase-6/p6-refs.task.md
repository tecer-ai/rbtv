---
task_id: p6-refs
status: pending
phase: validate
complexity_score: 4
human_review: optional
executor: { model: claude, variant: sonnet }
reviewer: { model: claude, variant: opus }
allowlist:
  modify:
    - ../**   # plan folder only, file-relative (fix links if broken)
orchestrator_executed: false
---

# Task p6-refs: Verify plan links + Plan Linking Standard

## Goal

Verify every markdown link inside the plan folder resolves and complies with the Plan Linking Standard (internal = `./`/`../` file-relative; external = project-root-relative). Fix any violation.

## Context Files

| File | Purpose |
|------|---------|
| `../api-workers-build-plan.md` + `../deliverables.md` + `../decisions.md` | The link sources to check |
| all `phase-*/*.task.md` + `specs/*.md` | Their internal/external references |

## Allowlist

- ✎ modify: files inside the plan folder only (to fix broken/non-compliant links)

## Execution Flow

### Phase: Understand
1. Mark in-progress in the three locations.

### Phase: Execute
1. For every `→ path` in the plan task list, verify the `.task.md` exists.
2. For every `.task.md` on disk, verify a matching `→ path` reference exists.
3. Check no file inside the plan folder self-references via an absolute/root-relative path to the plan folder; internal links use `./`/`../`; external links are project-root-relative.

### Phase: Validate
1. Zero broken links; zero Plan Linking Standard violations.

### Phase: Close
Follow the microstep template Phase: Close (orchestration mode).

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Link-check result + fixes | plan folder | (in-place fixes) |

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
