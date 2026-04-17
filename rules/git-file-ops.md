---
description: Git file operations (move/rename/delete with history preservation) and mandatory pre-commit workflow with remote sync and conflict detection
---
# Git Operations Rule

## File Operations

When working inside a git repository, use git commands instead of filesystem-only operations for moves, renames, and deletes.

| Operation | Use | Never Use |
|-----------|-----|-----------|
| Move/Rename | `git mv <source> <target>` | `mv`, filesystem rename, or Delete+Write |
| Delete | `git rm <path>` | `rm`, `del`, or Delete tool alone |

`git mv` preserves file history across renames. Filesystem-only operations break `git log --follow` tracking.

**Scope:** Applies to all git-tracked files. Does NOT apply to `.gitignore`d files, temp files, or build artifacts. New files use normal tools — `git add` happens at commit time.

## Pre-Commit Workflow

Execute these steps in exact order before every commit. NEVER skip steps.

### Step 1: Fetch

```bash
git fetch
```

### Step 2: Check Remote State

Determine if the branch has an upstream and if new remote commits exist.

```bash
# Check if upstream exists
git rev-parse --abbrev-ref @{u} 2>/dev/null

# If upstream exists, count new remote commits
git rev-list HEAD..@{u} --count
```

- **No upstream set** → proceed directly to commit and push with `-u`.
- **Count is 0** → no new remote commits. Proceed to Step 3A.
- **Count is >0** → new remote commits exist. Proceed to Step 3B.

### Step 3A: No New Remote Commits

1. Stage and commit local changes.
2. Push (only if the user requested it).

### Step 3B: New Remote Commits Exist

1. **Guard:** Only stash if there are uncommitted changes (`git status --porcelain` is non-empty). If working tree is clean, skip to pull.
2. Stash local changes: `git stash`.
3. Pull remote changes: `git pull`.
4. Restore local changes: `git stash pop`.

#### Stash pop succeeds (no conflict)

1. Run project tests (if test commands are configured for the project).
2. Stage and commit local changes.
3. Push (only if the user requested it).

#### Stash pop fails (conflict detected)

1. **STOP** — do NOT commit.
2. Identify conflicting files: `git diff --name-only --diff-filter=U`.
3. Notify the user:
   - List every conflicting file.
   - Ask how to resolve each conflict.
4. Execute the user's resolution instructions.
5. Run `git stash drop` after all conflicts are resolved (failed `stash pop` leaves the stash intact).
6. Run project tests (if configured).
7. Stage and commit.
8. Push (only if the user requested it).
