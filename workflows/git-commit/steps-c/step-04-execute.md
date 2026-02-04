---
stepNumber: 4
stepName: 'execute'
nextStepFile: null
---

# Step 04: Execute Operations

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Execute git commit (and push if requested). Report results.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Step-Specific Rules

- Execute commit with approved message
- Handle push errors gracefully
- Report success or failure clearly

### Forbidden Operations

- NEVER use `--force` or `--force-with-lease`
- NEVER use `--no-verify`
- NEVER amend without explicit request
- NEVER rebase without explicit request
- NEVER add AI co-author trailers unless instructed

---

## MANDATORY SEQUENCE

### 1. Execute Commit(s)

**ST/CO Modes:**

```bash
git commit -m "$(cat <<'EOF'
{approved message}
EOF
)"
```

**OR Mode:**

For each approved group:

1. `git add {files in group}`
2. `git commit -m "{group message}"`
3. Continue to next group

**SQ Mode:**

```bash
git commit -m "$(cat <<'EOF'
{approved message}
EOF
)"
```

### 2. Handle Commit Errors

| Error | Response |
|-------|----------|
| Pre-commit hook failure | Display error, offer to fix and retry |
| Nothing to commit | "No changes to commit." |
| Other failure | Display error message, halt |

### 3. Execute Push (If Requested)

Only if user specified `+push`:

```bash
git push
```

**SQ Mode with +push:**

After successful push, clean up branches:

```bash
git branch -d {source-branch}
git push origin --delete {source-branch}
```

### 4. Handle Push Errors

| Error | Response |
|-------|----------|
| Push rejected | "Push rejected. Run `git pull` to integrate remote changes, then retry." |
| Network failure | "Network error. Check connection and retry." |
| Permission denied | "Permission denied. Check your credentials." |

### 5. Report Results

**Success (commit only):**

```
✓ Committed: {type}({scope}): {title}
```

**Success (with push):**

```
✓ Committed: {type}({scope}): {title}
✓ Pushed to origin/{branch}
```

**Success (SQ with push):**

```
✓ Committed: {type}({scope}): {title}
✓ Pushed to origin/{target-branch}
✓ Deleted branch: {source-branch} (local and remote)
```

**Success (OR mode):**

```
**Summary:**
✓ {N} commits created
✓ {M} files organized and committed
- {commit 1 title}
- {commit 2 title}
- ...

Note: Commits not pushed. Use `git push` when ready.
```

### 6. Workflow Complete

Display final status and exit workflow.

---

## ERROR RECOVERY

### Pre-commit Hook Failure

```
Pre-commit hook failed. Error:
{error output}

Options:
- Fix the issues and run the workflow again
- Use a different mode or adjust files
```

### Push Failure

```
Commit succeeded but push failed:
{error message}

Your commit is saved locally. To push later:
1. Resolve the issue (pull, auth, network)
2. Run: git push
```

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**

- Commit(s) created successfully
- Push executed if requested (no errors)
- Clear success message displayed
- SQ mode: branches cleaned up if +push

❌ **FAILURE:**

- Commit failed without error handling
- Push failed without recovery guidance
- No status report displayed
