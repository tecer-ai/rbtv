---
name: commit
description: Use when committing changes to git. Triggers: user says "commit", "salva no git", "commita", or a task finishes and changes must be persisted. Handles file-op hygiene (git mv/git rm), remote sync, conflict detection, and commit message generation from diff analysis.
---

# Git Commit

Commit local changes with correct file-op hygiene, remote sync, and conflict handling.

## When to Use

| Signal | Example |
|--------|---------|
| User requests a commit | "commit", "commita", "salva no git" |
| Task completed and user asks to persist | "done, commit this" |

## File Operations

Use git commands for moves, renames, and deletes on tracked files. `git mv` preserves `git log --follow` history; filesystem operations break it.

| Operation | Use | Never Use |
|-----------|-----|-----------|
| Move/Rename | `git mv <source> <target>` | `mv`, filesystem rename, Delete+Write |
| Delete | `git rm <path>` | `rm`, `del`, Delete tool alone |

**Scope:** Tracked files only. `.gitignore`d, temp, and build artifacts use normal tools. New files use normal tools — `git add` at commit time.

## Procedure

Execute in order. Never skip steps.

### 1. Analyze Changes

1. `git -C "{repo}" status` — identify staged, unstaged, untracked
2. `git -C "{repo}" diff` — review unstaged
3. `git -C "{repo}" diff --cached` — review staged
4. `git -C "{repo}" log --oneline -5` — read recent commit style

Summarize changes and draft a commit message. Wait for user confirmation before proceeding.

### 2. Fetch and Check Remote

1. `git -C "{repo}" fetch`
2. `git -C "{repo}" rev-parse --abbrev-ref @{u}` — check upstream
   - No upstream → after commit, push with `-u`
3. If upstream exists: `git -C "{repo}" rev-list HEAD..@{u} --count`
   - Count 0 → Step 3
   - Count >0 → Step 4

### 3. Commit (No Remote Changes)

1. Stage specific files: `git -C "{repo}" add {files}` — never `git add -A`
2. Commit with confirmed message
3. Push only if user requested it

Go to Step 5.

### 4. Commit (Remote Changes Exist)

1. `git -C "{repo}" status --porcelain`
   - Clean → skip stash, go to pull
   - Dirty → `git -C "{repo}" stash`
2. `git -C "{repo}" pull`
3. If stashed: `git -C "{repo}" stash pop`

**Stash pop succeeds:**

1. If project has a test command (check `CLAUDE.md` or `package.json`), run tests. Fail → stop, notify user.
2. Stage and commit
3. Push only if user requested it

**Stash pop fails (conflict):**

1. STOP — do NOT commit
2. `git -C "{repo}" diff --name-only --diff-filter=U` — list conflicts
3. Present every conflicting file to user. Ask how to resolve each.
4. Execute user's resolution
5. `git -C "{repo}" stash drop`
6. If project has a test command, run tests. Fail → stop, notify user.
7. Stage and commit
8. Push only if user requested it

Go to Step 5.

### 5. Changelog Entry

If the commit touched any file in `_system/` or `.claude/`, append an entry to `_system/user/changelog.md` following `.claude/rules/changelog.md` format. Skip if those paths do not exist in this workspace.

## Commit Message Style

- Follow the repo's existing style (observed in Step 1.4)
- Summarize the "why", not the "what" — the diff shows the what
- Keep first line under 72 characters
- Add `Co-Authored-By: Claude <noreply@anthropic.com>` when the agent authored or co-authored the changes
