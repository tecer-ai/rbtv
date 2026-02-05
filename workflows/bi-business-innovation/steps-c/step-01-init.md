---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-project-setup.md
continueStepFile: ./step-03-milestone-select.md
knowledgeFile: ../data/founder-process.md
---

# Step 01: Initialize Business Innovation

**Progress: Step 1 of 3** — Next: Project Setup (new) or Milestone Selection (continue)

---

## STEP GOAL

Detect project state and determine whether to start a new project or continue an existing one.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a YC mentor. Be direct, critical, and constructive. Challenge assumptions while supporting the founder's vision.

### Step-Specific Rules

- Detect existing project from context before prompting user
- If project-memo is referenced in context, suggest Continue mode
- Present clear menu options and wait for selection

---

## MANDATORY SEQUENCE

### 1. Load Knowledge

Read `{knowledgeFile}` to understand milestone structure and routing.

### 2. Context Detection

Analyze conversation context to detect existing project:

**Check for project-memo reference:**
- Did user @-mention a project-memo.md file?
- Are there framework output files referenced?

**If project detected:**
- Note the project name from frontmatter
- Identify current milestone from frontmatter (currentMilestone)
- Prepare Continue mode suggestion

**If no project detected:**
- Prepare New Project mode

### 3. Present Mode Selection

Display the following menu based on detection:

**If project detected:**
```
I detected an existing project: {project-name}
Current milestone: {currentMilestone}
Current framework: {currentFramework}

Select an option:
[C] Continue Project — resume work on {project-name}
[N] New Project — start a fresh business innovation project
[X] Exit — cancel workflow
```

**If no project detected:**
```
Welcome to Business Innovation.

This workflow guides you through 6 milestones from idea to MVP:
M1: Conception — structure your idea
M2: Validation — test feasibility
M3: Brand — create brand identity
M4: Prototypation — build prototype
M5: Market Validation — validate demand
M6: MVP — build minimum viable product

Select an option:
[N] New Project — start a fresh business innovation project
[C] Continue Project — reference a project-memo file to resume work
[X] Exit — cancel workflow
```

### 4. HALT

ALWAYS halt and wait for user selection.

---

## MENU ROUTING

| Selection | Action |
|-----------|--------|
| [N] New Project | Load `{nextStepFile}` (step-02-project-setup.md) |
| [C] Continue Project | Load `{continueStepFile}` (step-03-milestone-select.md) |
| [X] Exit | Confirm exit, end workflow |

---

## CRITICAL STEP COMPLETION NOTE

ONLY when user makes a selection:

**For [N] New Project:**
1. Confirm new project mode
2. Load `{nextStepFile}` and follow its instructions

**For [C] Continue Project (with project detected):**
1. Read project-memo.md into context
2. Load `{continueStepFile}` and follow its instructions

**For [C] Continue Project (no project detected):**
1. Ask user to @-mention or provide path to their project-memo.md file
2. Once provided, read project-memo.md into context
3. Load `{continueStepFile}` and follow its instructions

**For [X] Exit:**
1. Confirm exit
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Mode correctly detected from context
- Clear menu presented with project info (if detected)
- User selection captured and routed correctly

❌ **FAILURE:**
- Proceeding without user selection
- Loading next step before HALT
- Missing project detection when project-memo is in context
