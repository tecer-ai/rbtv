---
title: 'Compound: Confirm target repo in rbtv-git before commit'
docType: 'compound'
mode: 'create'
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments: []
outputPath: '{project-root}/_bmad/rbtv/.rbtv-docs/to_dos/'
date: '2025-02-04'
yoloMode: false
---

# Confirm target repo in rbtv-git before commit

**Type:** Workflow  
**Priority:** Medium  
**Status:** Backlog

---

## Overview

### Problem

The rbtv-git workflow never asked which repository to commit. It prompted for mode (ST/CO/OR/SQ), size (280/1000/2000), and push (+push/no push) but omitted target-repo confirmation. In multi-repo workspaces (e.g. systems with BMAD, robotville), committing without confirming the repo risks committing the wrong tree.

### Goals

The command must confirm (or explicitly accept) the target repository before gathering git context or performing any commit. Repo confirmation should occur first, before mode/size/push.

### Constraints

- Must not break single-repo usage (e.g. default to cwd repo when only one).
- Must work when invoked from different working directories or project roots.

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap. The git-commit workflow design did not include target-repo confirmation. The agent followed step-01-init exactly (mode → size → push); the step never asks for or confirms repo. User expectation: the command should first confirm which repo is being committed. Actual behavior: workflow proceeded to mode/size/push only. Impact: in multi-repo workspaces, users cannot be sure which repo will receive the commit without an explicit confirmation step.

### Context Source Evaluation

**Files that influenced behavior:**
- `_bmad/rbtv/workflows/git-commit/workflow.md` — Defines init sequence (parse mode/size/push, load step-01). No mention of repo detection or confirmation.
- `_bmad/rbtv/workflows/git-commit/steps-c/step-01-init.md` — Mandatory sequence: parse mode, prompt missing mode, prompt missing size, prompt missing push, validate mode prerequisites, present menu. No step for "confirm target repo."

**Evaluation:** Step-01 was followed as written. The guidance was not ambiguous; the step simply omits repo. Gap: no step or rule exists that requires "confirm target repository before any git operations." No file was missing or misinterpreted; the workflow specification is incomplete for multi-repo use.

### Improvement Options

1. **New Rule**: Add a rule that any git workflow must confirm (or explicitly accept) the target repository before gathering git context or committing.
   - **Rationale:** Ensures all git workflows, including future ones, require repo confirmation.
   - **Location:** `.cursor/rules/` (e.g. job or guardrail rule) or a rule referenced by the git-commit workflow.

2. **Modify Existing Rule**: In the git-commit workflow document, add an explicit principle: "Repo must be confirmed before mode/size/push." Update step-01-init to include repo confirmation in its mandatory sequence.
   - **Rationale:** Makes the requirement part of the workflow contract and step file so agents and maintainers see it.
   - **Location:** `_bmad/rbtv/workflows/git-commit/workflow.md` and `steps-c/step-01-init.md`.

3. **Update System File**: Add repo confirmation to step-01-init (or a new step-00): before "Parse Command Arguments," add "Detect or prompt for target repo → confirm with user → store repo path/name in session." Then ensure step-02-context uses that repo.
   - **Rationale:** Fixes the omission at the source; repo becomes a first-class parameter.
   - **Location:** `_bmad/rbtv/workflows/git-commit/steps-c/step-01-init.md` (or new `step-00-repo.md`).

4. **Add Constraint**: Add a workflow-level constraint: "Repo MUST be confirmed before any step that reads git state or runs git commands." Enforce in workflow.md and in step-01.
   - **Rationale:** Prevents any future step reordering from skipping repo confirmation.
   - **Location:** `_bmad/rbtv/workflows/git-commit/workflow.md` (Critical Rules / INITIALIZATION SEQUENCE).

5. **Alternative Approach**: Make repo explicit via command argument (e.g. `/bmad-rbtv-git repo:robotville` or `repo:.) so the command never infers repo from cwd. Default to current repo only when a single repo is detectable.
   - **Rationale:** Removes ambiguity; scriptable and clear for automation.
   - **Location:** Command file that invokes the workflow, plus workflow/step-01 parsing for `repo:` and passing repo into context step.

---

## Proposed Solution

**Option 4 — Add Constraint.** Add a workflow-level constraint so repo confirmation cannot be skipped by step reordering or future edits.

**Specification:**

1. **Workflow (`workflow.md`)**  
   - In **Critical Rules**, add: "Repo MUST be confirmed before any step that reads git state or runs git commands."  
   - In **INITIALIZATION SEQUENCE**, add a step before "Load step-01": "Confirm target repo (detect or prompt, then confirm with user); store repo path/name in session."  
   - Keep the constraint visible so agents and maintainers treat repo as a prerequisite.

2. **Step-01 (`steps-c/step-01-init.md`)**  
   - In **MANDATORY SEQUENCE**, add a step **before** "Parse Command Arguments": "Confirm target repo — detect repo (e.g. from cwd or workspace), present to user, accept confirmation or override; store in session."  
   - Ensure step-02-context (and any step that runs git) receives or uses the confirmed repo.

3. **No new files required.** Constraint and behavior live in existing workflow and step-01.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `_bmad/rbtv/workflows/git-commit/workflow.md`, `_bmad/rbtv/workflows/git-commit/steps-c/step-01-init.md` |
| Scope of change | Add one constraint + one init step in workflow; add one mandatory step (repo confirm) at start of step-01 sequence. |
| Related files | `steps-c/step-02-context.md` (must use confirmed repo for git context); command file that invokes workflow (optional: pass repo arg later). |

---

## Rationale

The error was a **knowledge gap**: the workflow design omitted repo confirmation. Adding a **constraint** (Option 4) fixes this by:

- Making the requirement explicit and durable — future edits or reordering cannot drop repo confirmation without violating the stated rule.
- Keeping the change in the workflow and step files that agents already load, so no new rule file or command contract is required.
- Leaving room for implementation detail (e.g. detect single repo vs prompt in multi-repo) inside step-01, while the workflow guarantees "confirm before git."

Alternatives: A new rule (Option 1) would apply broadly but might not be loaded by the git workflow. Updating only step-01 (Option 3) fixes behavior but does not guard against future reordering. Option 4 adds both the guardrail and the expectation that step-01 implements it.

---

## Acceptance Criteria

- [ ] `workflow.md` contains the constraint: "Repo MUST be confirmed before any step that reads git state or runs git commands."
- [ ] `workflow.md` INITIALIZATION SEQUENCE includes a step to confirm target repo before loading step-01.
- [ ] `step-01-init.md` MANDATORY SEQUENCE includes a repo-confirmation step (detect or prompt, confirm with user, store in session) before "Parse Command Arguments."
- [ ] Step that gathers git context (e.g. step-02) uses the confirmed repo when running git commands or reading git state.

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/workflows/git-commit/workflow.md` | Add constraint and init step; defines contract for repo confirmation. |
| `_bmad/rbtv/workflows/git-commit/steps-c/step-01-init.md` | Implement repo confirm step; must run before mode/size/push. |
| `_bmad/rbtv/workflows/git-commit/steps-c/step-02-context.md` | Consumes confirmed repo for git context; may need minor update to use session repo. |
| `_bmad/rbtv/.cursor/commands/bmad-rbtv-git.md` | Invokes workflow; may later support `repo:` argument. |

---

## References

- Git workflow: `_bmad/rbtv/workflows/git-commit/workflow.md`
- Init step: `_bmad/rbtv/workflows/git-commit/steps-c/step-01-init.md`
- Compound source: this PRD (Discussion Notes, Self-Assessment)

---

## Discussion Notes

### Selected Improvement Option

**Option 4 — Add Constraint:** Add a workflow-level constraint that "Repo MUST be confirmed before any step that reads git state or runs git commands." Enforce in workflow.md and in step-01.

### Implementation Preferences

- **File Location:** `_bmad/rbtv/workflows/git-commit/workflow.md` (Critical Rules / INITIALIZATION SEQUENCE); optionally reference in `steps-c/step-01-init.md`.
- **Scope:** Add one explicit constraint to the workflow; ensure step-01 includes repo confirmation in its mandatory sequence so the constraint is actionable.
- **Priority:** Medium (backlog).

### Additional Context

User chose to advance with Option 4. Constraint prevents future step reordering from skipping repo confirmation; implementation still requires step-01 (or equivalent) to perform the actual repo confirm step.
