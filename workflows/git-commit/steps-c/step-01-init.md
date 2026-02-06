---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-context.md
---

# Step 01: Init

**Progress: Step 1 of 4** — Next: Gather Context

---

## STEP GOAL

Detect or prompt for mode, size, and push preference. Validate prerequisites.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Step-Specific Rules

- Parse command arguments for mode/size/push flags
- Prompt for any missing parameters before proceeding
- Validate mode prerequisites before continuing

---

## MANDATORY SEQUENCE

### 1. Parse Command Arguments

Extract from user command:

- **Mode**: ST, CO, OR, SQ (case-insensitive)
- **Size**: 280, 1000, 2000
- **Push**: +push flag presence
- **YOLO**: +yolo flag presence

Store detected values in session.

If YOLO mode detected:
- Set yoloMode = true
- If size not specified, use defaultSize (1000)
- Skip menu presentations in subsequent steps

### 2. Prompt for Missing Mode

If mode not detected, present:

```
Which mode?

- **ST** — Stage all changes + commit
- **CO** — Commit staged changes only
- **OR** — Organize changes into multiple commits
- **SQ** — Squash merge branch to main
```

HALT and wait for user selection.

**YOLO Mode Exception:** This prompt is REQUIRED even in YOLO mode.

### 3. Prompt for Missing Size

If size not detected:

**YOLO Mode:** Skip prompt, use defaultSize (1000)

**Normal Mode:** Present:

```
Commit message size?

- **280** — Small (concise summary)
- **1000** — Medium (detailed, default)
- **2000** — Large (comprehensive with full context)
```

HALT and wait for user selection.

### 4. Prompt for Missing Push Preference

If push not detected, present:

```
Push after commit?

- **+push** — Yes, push to remote
- **no push** — No, commit only (default)
```

HALT and wait for user selection.

**YOLO Mode Exception:** This prompt is REQUIRED even in YOLO mode.

### 5. Validate Mode Prerequisites

| Mode | Prerequisite | Error Message |
|------|--------------|---------------|
| CO | Staged changes exist | "No staged changes. Use ST mode or stage files first." |
| SQ | Not on main/master | "Cannot squash main into itself. Switch to feature branch." |
| ST | — | No validation needed |
| OR | Changes exist | "No changes found. Working directory is clean." |

If prerequisite fails → Display error and HALT.

### 6. Present Menu Options

**Configuration Complete:**

- Mode: `{mode}`
- Size: `{size}`
- Push: `{+push | no push}`
- YOLO: `{yes | no}`

**YOLO Mode:** Skip menu, automatically proceed to step 2.

**Normal Mode:**

**Select an Option:**

- **[C] Continue** — Proceed to gather git context
- **[R] Reconfigure** — Change mode/size/push settings
- **[X] Exit** — Cancel workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

**Normal Mode:** ONLY when **[C] Continue** is selected:

**YOLO Mode:** Automatically proceed after validation:

1. Store mode, size, push, yoloMode in session
2. Load `./step-02-context.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**

- Mode, size, and push preference captured
- Prerequisites validated for selected mode
- User explicitly selected Continue

❌ **FAILURE:**

- Proceeding without all parameters
- Skipping prerequisite validation
- Loading next step without user selection
