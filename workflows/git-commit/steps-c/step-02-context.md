---
stepNumber: 2
stepName: 'context'
nextStepFile: ./step-03-message.md
---

# Step 02: Gather Context

**Progress: Step 2 of 4** — Next: Generate Message

---

## STEP GOAL

Gather git context based on selected mode. Execute preparatory git commands.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Step-Specific Rules

- Execute git commands appropriate to the selected mode
- Store output for message generation in next step
- For SQ mode, handle merge conflicts gracefully
- ALL git commands MUST run with `required_permissions: ["all"]` to ensure SSH agent access for signing

---

## MANDATORY SEQUENCE

### 1. Execute Mode-Specific Commands

**ST Mode (Stage + Commit):**

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `git add -A` | Stage all changes |
| 2 | `git diff --cached --stat` | Get staged summary |
| 3 | `git diff --cached` | Get detailed diff |

**CO Mode (Commit Staged):**

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `git diff --cached --stat` | Get staged summary |
| 2 | `git diff --cached` | Get detailed diff |

**OR Mode (Organize):**

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `git status --porcelain` | Get all changes with statuses |
| 2 | Analyze changes | Group by scope/type/relationship |

**Efficiency Note:** Use the status output to write commit messages. Only run `git diff` on specific files if content details are needed for the message (rare - most messages can be written from file paths and change types alone).

**SQ Mode (Squash Merge):**

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `git branch --show-current` | Get source branch |
| 2 | `git fetch origin {target}` | Fetch target branch |
| 3 | `git checkout {target}` | Switch to target |
| 4 | `git pull` | Pull latest target |
| 5 | `git merge --squash {source}` | Squash merge |
| 6 | `git log {target}..{source} --format="%B"` | Get commit messages |
| 7 | `git diff --cached --stat` | Get merged summary |

If merge conflicts in SQ mode → Display conflict resolution instructions and HALT.

### 2. Store Context

Store gathered context for message generation:

- Diff output (detailed changes)
- Stat output (summary)
- File list with statuses
- For SQ: original commit messages

### 3. Present Context Summary (OR Mode Only)

**OR Mode (Normal or YOLO):** Present proposed groupings:

```
**Proposed commit organization:**

📦 **Group 1: {Category}** ({N} files)
- {file path} ({status})
- {file path} ({status})

Type: {type} — {brief description}

📦 **Group 2: {Category}** ({N} files)
- {file path} ({status})

Type: {type} — {brief description}

**Commands:**
- `approve` — proceed with these groups
- `merge <N> <M>` — combine groups
- `split <N> <files>` — extract files
- `move <file> to <N>` — reorganize
- `reorder <N> before <M>` — change order
```

**CRITICAL:** Group approval is REQUIRED even in YOLO mode. YOLO only skips prompts AFTER groups are approved.

HALT and wait for user to refine or approve groupings.

### 4. Present Menu Options

**Context gathered successfully.**

Files changed: {count}
Lines added: {+count}
Lines removed: {-count}

**YOLO Mode:** Skip menu, automatically proceed to step 3.

**Normal Mode:**

**Select an Option:**

- **[C] Continue** — Proceed to generate commit message
- **[V] View Details** — Show full diff
- **[X] Exit** — Cancel workflow

ALWAYS halt and wait for user selection.

---

## CONFLICT RESOLUTION (SQ Mode)

If merge conflicts occur, display:

```
Merge conflicts detected. To resolve:

1. Run: `git status` to see conflicting files
2. Open each file and resolve conflicts (look for <<<<<<< markers)
3. After resolving, run: `git add <file>` for each resolved file
4. Invoke this workflow again to continue

Conflicting files:
- {list of files}
```

Then HALT and exit workflow.

---

## CRITICAL STEP COMPLETION NOTE

**Normal Mode:** ONLY when **[C] Continue** is selected:

**YOLO Mode (Non-OR):** Automatically proceed after context gathered.

**YOLO Mode (OR):** Automatically proceed ONLY after user approves groupings.

1. Ensure context is stored in session
2. Load `./step-03-message.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**

- Git commands executed without errors
- Context gathered and stored
- OR mode groupings approved by user
- User explicitly selected Continue

❌ **FAILURE:**

- Git command failures not handled
- Proceeding with merge conflicts
- OR mode groupings not approved before continuing
