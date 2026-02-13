---
title: 'Compound: Add PR Mode to Git Workflow'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments: []
outputPath: '_admin-output/planning-artifacts'
date: '2026-02-13'
yoloMode: false
---

# Add PR Mode to Git Workflow

**Type:** Workflow
**Priority:** High
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

The git workflow offers four modes (ST, CO, OR, SQ) but none creates a Pull Request on GitHub. The SQ mode performs a local squash merge directly to the target branch, bypassing collaborative safeguards (review trails, CI checks, branch protection). Users have no PR-based path within the workflow and must exit the workflow to use `gh` CLI manually.

### Goals

Add a fifth PR mode to the git workflow that pushes the current branch and creates a Pull Request via `gh pr create`. PR mode is a peer to SQ -- SQ is the fast path for solo/admin work, PR is the collaborative path for team/code changes.

### Constraints

- Minimal scope for v1: `gh pr create` with title and body only
- No reviewers, labels, CI wait, or merge strategy selection in v1
- SQ mode must remain unchanged
- `gh` CLI must be available on the system (prerequisite check needed)
- Must follow existing workflow micro-file architecture and step patterns

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap

**Expectation:** When squash-merging a feature branch to master, the workflow should offer the option to create a Pull Request on GitHub -- providing a review trail, CI checks, and team collaboration before merging.

**Actual behavior:** The git workflow's SQ mode performs a local `git merge --squash`, commits directly to the target branch, pushes, and deletes the source branch. There is no PR-based path. The user had no opportunity to choose between a direct merge and a PR-based merge.

**Impact:** For solo/admin work on documentation, this was acceptable. However, for team workflows, production code, or any context requiring review trails, the SQ mode bypasses standard collaborative safeguards. The user correctly identified this gap after the merge was already completed.

### Context Source Evaluation

| File | Role | Assessment |
|------|------|------------|
| `workflows/git-commit/workflow.md` | Workflow entry point, mode definitions | Defines 4 modes (ST, CO, OR, SQ). No PR mode exists. SQ is described only as local squash merge. No guidance on when PR vs direct merge is appropriate. |
| `workflows/git-commit/steps-c/step-01-init.md` | Mode selection and validation | SQ prerequisite only checks "not on main/master". No prompt asking direct merge vs PR. |
| `workflows/git-commit/steps-c/step-02-context.md` | Context gathering for SQ | SQ steps are hardcoded: checkout target → pull → squash merge. No branching logic for PR path. |
| `workflows/git-commit/steps-c/step-04-execute.md` | Execution | SQ with +push: commits, pushes, deletes branches. No alternative to create PR instead. |

**Gaps identified:**
- No PR-based merge mode in the git workflow
- No prompt asking user to choose between direct merge and PR
- No guidance on when SQ (direct) vs PR is appropriate
- `gh` CLI (GitHub CLI) is not leveraged anywhere in the workflow

### Improvement Options

1. **New Rule**: Add PR merge guidance rule
   - **Rationale:** A rule could define when direct merge vs PR is appropriate (e.g., solo admin work = direct OK; team code = PR required). This would inform agent behavior across workflows, not just git.
   - **Location:** `_config/.cursor/rules/bmad-rbtv-git-merge-policy.mdc` (new file)

2. **Modify Existing Rule**: Add PR sub-option to SQ mode in workflow.md
   - **Rationale:** The simplest change -- when user selects SQ, prompt: "Direct merge or PR?" Direct merge follows current path; PR pushes branch and runs `gh pr create`.
   - **Location:** `workflows/git-commit/workflow.md` (mode overview) + `workflows/git-commit/steps-c/step-01-init.md` (add sub-mode prompt)

3. **Update System File**: Add a fifth mode (PR) to the git workflow
   - **Rationale:** A dedicated PR mode would handle: push branch, create PR via `gh pr create`, optionally set reviewers/labels. Keeps SQ as-is for direct merges. Cleaner separation of concerns.
   - **Location:** `workflows/git-commit/workflow.md` (add PR mode) + new step files for PR flow in `steps-c/`

4. **Add Constraint**: Warn before direct merge to main/master
   - **Rationale:** Even if SQ mode stays as-is, a guardrail in step-01 could warn: "You're about to merge directly to master without a PR. Continue?" This preserves choice but adds awareness.
   - **Location:** `workflows/git-commit/steps-c/step-01-init.md` (SQ prerequisite validation section)

5. **Alternative Approach**: Replace SQ mode with PR-first workflow
   - **Rationale:** Instead of local squash merge, SQ mode could always create a PR with squash merge setting, then merge via GitHub API (`gh pr merge --squash`). This ensures review trail, CI checks, and branch protection compliance. Direct merge becomes an explicit override.
   - **Location:** Complete rework of `workflows/git-commit/steps-c/step-02-context.md` and `step-04-execute.md` for SQ mode

---

## Proposed Solution

Add a fifth mode **PR** (Pull Request) to the git workflow. The PR mode:

1. **Pushes** the current branch to remote (if not already pushed)
2. **Generates** a PR title and body using the same commit message generation logic (step-03-message.md)
3. **Creates** a PR via `gh pr create --title "{title}" --body "{body}"`
4. **Reports** the PR URL to the user

The flow reuses existing steps where possible:
- step-01-init.md: Add PR to mode menu, validate `gh` CLI is available
- step-02-context.md: PR mode gathers `git log` and `git diff --stat` for the branch (similar to SQ context)
- step-03-message.md: Generate PR title/body (same format as commit message, repurposed)
- step-04-execute.md: Execute `git push -u origin HEAD` + `gh pr create`

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `workflows/git-commit/workflow.md`, `steps-c/step-01-init.md`, `steps-c/step-02-context.md`, `steps-c/step-03-message.md`, `steps-c/step-04-execute.md` |
| Scope of change | Minimal -- add PR sections to each existing step file, no new step files needed |
| Related files | `_config/.cursor/commands/bmad-rbtv-git.md` (no change needed, mode is parsed at runtime) |

---

## Rationale

Option 3 (new PR mode) was selected over embedding PR within SQ (option 2) because:

- **Separation of concerns:** SQ and PR serve fundamentally different purposes. SQ is a local operation that merges and commits. PR is a remote operation that creates a review request. Mixing them adds complexity to SQ's already-defined behavior.
- **No disruption:** Existing SQ users are unaffected. PR is additive.
- **Minimal implementation:** PR mode reuses all 4 existing steps -- each step gets a PR section added alongside the existing ST/CO/OR/SQ sections. No new step files required.
- **`gh` CLI dependency:** PR mode requires `gh` CLI, which SQ does not. Keeping them separate allows clean prerequisite validation.

---

## Acceptance Criteria

- [ ] PR mode appears in the mode selection menu (step-01) alongside ST, CO, OR, SQ
- [ ] PR mode validates `gh` CLI is available and user is authenticated (`gh auth status`)
- [ ] PR mode validates current branch is not main/master
- [ ] PR mode pushes branch to remote if not already pushed
- [ ] PR mode generates title and body using existing message generation logic
- [ ] PR mode creates PR via `gh pr create` and displays the resulting PR URL
- [ ] SQ mode behavior is completely unchanged
- [ ] YOLO mode works with PR (auto-approves title/body, still confirms push)

---

## Related Files

| File | Relationship |
|------|--------------|
| `workflows/git-commit/workflow.md` | Primary file -- mode table and overview to update |
| `workflows/git-commit/steps-c/step-01-init.md` | Add PR to mode menu and prerequisites |
| `workflows/git-commit/steps-c/step-02-context.md` | Add PR context gathering (log + stat) |
| `workflows/git-commit/steps-c/step-03-message.md` | Repurpose message generation for PR title/body |
| `workflows/git-commit/steps-c/step-04-execute.md` | Add PR execution (push + gh pr create) |

---

## References

- GitHub CLI documentation: `gh pr create`
- Conversation context: squash merge of `feature/domcobb-ps-lite` on 2026-02-13 triggered this compound

---

## Discussion Notes

### Selected Improvement Option

Option 3: Add a fifth PR mode to the git workflow as a dedicated PR creation workflow using `gh` CLI. PR mode is a peer to SQ, not a replacement.

### Implementation Preferences

- **File Location:** `workflows/git-commit/` -- new step files for PR flow in `steps-c/`, updated mode table in `workflow.md`
- **Scope:** Minimal -- `gh pr create` with title/body generated from commit message workflow. No reviewers, labels, CI wait, or merge strategy selection in v1.
- **Priority:** High

### Additional Context

- SQ mode stays as-is for direct merges (solo/admin/docs work)
- PR mode handles `gh pr create` for team/code/protected-branch scenarios
- Workflow could suggest which mode is appropriate based on file types and change size, but this is out of scope for v1
- Agent assessment: PR vs SQ are peer modes, not one replacing the other. SQ is the fast path, PR is the collaborative path.
