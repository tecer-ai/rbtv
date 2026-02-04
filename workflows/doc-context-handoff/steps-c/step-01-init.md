---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-location-selection.md
templateFiles:
  plan-development: ../templates/handoff-plan-development.md
  execution: ../templates/handoff-execution.md
  project: ../templates/handoff-project.md
outputFile: '{handoff_output_folder}/{filename}.md'
advancedElicitationTask: '{project-root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
---

# Step 01: Init

**Progress: Step 1 of 4** — Next: Location Selection

---

## STEP GOAL

Detect workflow context, determine handoff type, and prepare output document from template.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Context Curator. Continue your existing persona as Ana and communication style.

### Step-Specific Rules

- Detect handoff type from invocation context or ask user
- Load template before proceeding
- Create output document with proper frontmatter

---

## MANDATORY SEQUENCE

### 1. Check for Type Flag

Inspect the command invocation context:

- If invoked with `:plan` suffix (e.g., `/bmad-rbtv-doc handoff:plan`) → Set `handoffType = plan-development`
- If invoked with `:exec` suffix (e.g., `/bmad-rbtv-doc handoff:exec`) → Set `handoffType = execution`
- If no type flag → Continue to type detection

### 2. Detect Handoff Type from Context

If no type flag was provided, analyze the conversation context:

| Context Pattern | Detected Type |
|-----------------|---------------|
| User mentions plan creation, planning, or `/plan` context | `plan-development` |
| User mentions executing a plan or task completion | `execution` |
| General project discussion, no plan context | `project` |
| Unable to determine | Ask user to select |

If unable to determine, present type selection:

```
I'll help you create a handoff summary. What type of handoff is this?

[1] Plan Development — For continuing plan creation/modification
[2] Execution — For executing tasks from an approved plan
[3] Project — General project context transfer
```

HALT and wait for user selection.

### 3. Load Template

Select the template based on detected handoff type:

| Handoff Type | Template File |
|--------------|---------------|
| `plan-development` | `../templates/handoff-plan-development.md` |
| `execution` | `../templates/handoff-execution.md` |
| `project` | `../templates/handoff-project.md` |

- Read the appropriate template from `{templateFiles}` based on `{handoffType}`
- If template not found → Display error, present Retry/Exit menu
- Store template content in memory

### 4. Create Output Document

- Generate filename suggestion based on conversation context and handoff type
  - Format: `handoff-{context-slug}.md` (lowercase, hyphens, descriptive)
  - Examples: `handoff-auth-implementation.md`, `handoff-prd-review.md`
- Store filename in session (user will confirm in step-02)
- Create new document using template structure
- Populate frontmatter:

```yaml
---
title: 'Handoff: {Context Title}'
docType: 'handoff'
mode: 'create'
handoffType: '{plan-development|execution|project}'
targetAgent: '{description of receiving agent role}'
stepsCompleted: []
inputDocuments: []
date: '{current-date}'
---
```

### 5. Update State

- Add `step-01-init.md` to `stepsCompleted` array
- Save output document to memory (not yet to disk)

### 6. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to location selection (step-02)
- **[AE] Advanced Elicitation** — Load and execute `{advancedElicitationTask}`, then return and redisplay this step's menu
- **[X] Exit Workflow** — Save current state, exit agent

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-01-init.md` in `stepsCompleted`
2. Load `./step-02-location-selection.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**

- Handoff type correctly detected or selected
- Output document created with valid frontmatter (all required fields present)
- `stepsCompleted` array contains exactly one entry: `step-01-init.md`
- Menu presented with explicit HALT and execution stopped

❌ **FAILURE:**

- Template file not found and no error handling
- Output document created without frontmatter
- Proceeding to next step without user selecting Continue
- Missing `handoffType` field in frontmatter
