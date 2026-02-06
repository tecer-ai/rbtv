---
stepNumber: 1
stepName: 'project-setup'
nextStepFile: ./step-02-milestone-select.md
projectMemoTemplate: ../templates/project-memo.md
outputFolder: '{project-root}/_bmad-output/{project-name}/founder'
---

# Step 01: Project Setup

**Progress: Step 1 of 2** — Next: Milestone Selection

---

## STEP GOAL

Initialize a new business innovation project with proper folder structure and project-memo.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a YC mentor. Guide the founder through setup with clarity and efficiency. Get them ready to work, not stuck in process.

### Step-Specific Rules

- Gather project name before creating any files
- Use template exactly as provided
- Create all milestone folders upfront
- Initialize project-memo with frontmatter state tracking

---

## MANDATORY SEQUENCE

### 1. Gather Project Name

Ask the founder:
```
What's the name of your project?
(Use a short, memorable name — this will be used in file paths and documents)
```

Wait for response.

### 2. Confirm Project Setup

Present the setup summary:
```
I'll create the following structure for "{project-name}":

_bmad-output/{project-name}/founder/
├── project-memo.md        # Your cumulative project summary + state tracking
├── m1-conception/         # M1 framework outputs
├── m2-validation/         # M2 framework outputs
├── m3-brand/              # M3 framework outputs
├── m4-prototypation/      # M4 framework outputs
├── m5-market-validation/  # M5 framework outputs
└── m6-mvp/                # M6 framework outputs

Proceed with setup? [Y/N]
```

Wait for confirmation.

### 3. Create Folder Structure

Execute the following commands:
```
mkdir -p {outputFolder}
mkdir -p {outputFolder}/m1-conception
mkdir -p {outputFolder}/m2-validation
mkdir -p {outputFolder}/m3-brand
mkdir -p {outputFolder}/m4-prototypation
mkdir -p {outputFolder}/m5-market-validation
mkdir -p {outputFolder}/m6-mvp
```

### 4. Initialize Project Memo

Read `{projectMemoTemplate}` and create `{outputFolder}/project-memo.md`:
- Set projectName in frontmatter
- Set currentMilestone to "M1: Conception"
- Set currentFramework to "Not Started"
- Set stepsCompleted to empty array
- Initialize all sections with placeholder content

### 5. Confirm Initialization

Present completion summary:
```
✅ Project "{project-name}" initialized successfully.

Created:
- project-memo.md (your cumulative project summary + state tracking)
- 6 milestone folders (m1-conception through m6-mvp)

You're ready to begin with M1: Conception.
```

### 6. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to milestone selection
- **[X] Exit** — exit workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}` and follow its instructions

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Project name gathered from user
- All folders created
- project-memo.md initialized with project name and frontmatter state
- User proceeds to milestone selection

❌ **FAILURE:**
- Creating files without project name
- Missing any required folders
- Template not properly instantiated
- Proceeding without user confirmation
