---
stepNumber: 3
stepName: 'message'
nextStepFile: ./step-04-execute.md
---

# Step 03: Generate Message

**Progress: Step 3 of 4** — Next: Execute Operations

---

## STEP GOAL

Generate Conventional Commits message(s) based on gathered context. Obtain user approval.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Step-Specific Rules

- Follow Conventional Commits format exactly
- Respect user-selected size limit
- Auto-detect scope from file paths
- Flag breaking changes when patterns detected

---

## MANDATORY SEQUENCE

### 1. Analyze Changes

Review gathered context to determine:

- **Type**: feat, fix, docs, style, refactor, test, other
- **Scope**: Auto-detect from primary file paths
- **Breaking changes**: Look for removed/renamed public APIs, changed signatures

### 2. Generate Commit Message

Follow this structure:

```
<type>[scope][!]: <title>

<summary paragraph>

<categorized sections if applicable>

<impact statement if applicable>
```

**Title Rules:**

| Rule | Requirement |
|------|-------------|
| Length | Target ~50 chars, max 80 |
| Casing | Lowercase only |
| Punctuation | No period at end |
| Mood | Imperative ("add" not "added") |

**Types:**

| Type | Purpose |
|------|---------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation changes |
| style | Formatting, no code change |
| refactor | Code restructuring |
| test | Adding or updating tests |
| other | Maintenance, anything else |

**Size Content:**

| Size | Content |
|------|---------|
| 280 | Summary paragraph only |
| 1000 | Summary + 2-3 categorized sections |
| 2000 | Full structure with impact statement |

### 3. Present Message for Approval

**Generated commit message:**

```
{type}[{scope}]: {title}

{body}
```

**Analysis:**

- Type: `{type}` — {reason}
- Scope: `{scope}` — detected from {source}
- Breaking changes: {yes/no, explanation}
- Character count: {X}/{limit}
- Push: {yes/no}

**Proceed? (yes/edit/abort)**

HALT and wait for user response.

### 4. Handle User Response

| Response | Action |
|----------|--------|
| `yes` or `y` | Store message, proceed to execute |
| `edit` or `e` | Ask user for modified message |
| `abort` or `a` | Cancel workflow |
| Modified text | Use as commit message |

If user edits, store the modified message exactly as provided.

### 5. OR Mode: Repeat for Each Group

For OR mode, process each approved group:

1. Stage only files in current group
2. Get diff for this group
3. Generate message for this group
4. Present for approval: "Proceed? (yes/edit/skip/abort)"
5. On `yes`: store message, continue to next group
6. On `skip`: leave files unstaged, continue to next group
7. On `abort`: cancel remaining groups

After all groups processed, proceed to execute step.

### 6. Present Menu Options (Non-OR Modes)

**Message approved.**

**Select an Option:**

- **[C] Continue** — Proceed to execute commit
- **[E] Edit Message** — Modify the commit message
- **[X] Exit** — Cancel workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected or message approved:

1. Store approved message(s) in session
2. Load `./step-04-execute.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**

- Message follows Conventional Commits format
- Character count within size limit
- User explicitly approved message
- OR mode: all groups processed

❌ **FAILURE:**

- Message exceeds size limit without notice
- Proceeding without user approval
- Breaking changes not flagged
