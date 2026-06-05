# Continuable Init Step Template

Use this template to create a step-01-init.md that supports workflow continuation across sessions. Pair with `step-continue-template.md` for the step-01b-continue.md file.

---

## Template

```markdown
---
name: 'step-01-init'
description: '{What this initialization step accomplishes}'

# File References
nextStepFile: './step-02-{next-name}.md'
continueStepFile: './step-01b-continue.md'
workflowFile: './workflow.md'
outputFile: '{output_folder}/{output-name}.md'

# Template References
templateFile: './templates/{output-template-name}.md'
---

# Step 1: Workflow Initialization

**Progress: Step 1 of {Total}** — Next: {Next Step Title}

---

## STEP GOAL

Initialize the workflow by detecting continuation state and creating the output document.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a {role}. Continue your existing persona and communication style.

### Step-Specific Rules
- 🎯 Focus ONLY on initialization and setup
- 🚫 FORBIDDEN to look ahead to future steps
- 🚪 DETECT existing workflow state and route to continuation if needed

---

## MANDATORY SEQUENCE

### 1. Check for Existing Output Document

Look for file at `{outputFile}`:
- If exists, read the complete file including frontmatter
- If not exists, this is a fresh workflow — skip to section 3

### 2. Handle Existing Document

If the document exists and has frontmatter with `stepsCompleted`:
- **STOP** — Load and execute `{continueStepFile}` immediately
- Do NOT proceed with initialization

If the document exists AND all steps are complete:
- Ask user: "I found an existing {output type} from {date}. Would you like to:
  1. Create a new {output type}
  2. Continue modifying the existing one"
- Option 1: Create new document with timestamp suffix
- Option 2: Load `{continueStepFile}`

### 3. Fresh Workflow Setup

#### A. Input Document Discovery
{Describe what input documents to look for, if any.}

#### B. Create Output Document
Copy the template from `{templateFile}` to `{outputFile}`.
Initialize frontmatter:
```yaml
stepsCompleted: ["step-01-init.md"]
lastStep: 'init'
inputDocuments: []
date: '{current date}'
```

#### C. Welcome Message
Present a brief welcome and describe what happens next.

### 4. Auto-Proceed

**Proceeding to {Next Step Title}...**

ONLY when initialization is complete:
1. Confirm frontmatter has `stepsCompleted: ["step-01-init.md"]`
2. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Output document created from template, frontmatter initialized, continuation correctly detected and routed

❌ **FAILURE:** Proceeding without document initialization, not checking for existing documents, not routing to continuation when needed
```

---

## Field Instructions

### Frontmatter
- **name**: Always `step-01-init` for init steps
- **description**: What this initialization accomplishes
- **nextStepFile**: Path to step-02 (first content step)
- **continueStepFile**: Path to step-01b-continue.md (continuation handler)
- **workflowFile**: Path to parent workflow.md
- **outputFile**: Path to output document (use config variables)
- **templateFile**: Path to the output document template

### When to Use This Template

Use instead of `step-template.md` when:
- The workflow produces an output document
- Users may need multiple sessions to complete the workflow
- The workflow must detect and resume from previous progress

### Paired Template

This template MUST be paired with `step-continue-template.md` to create the step-01b-continue.md file.

---

## Key Differences from Standard Init

| Aspect | Standard Init (step-template.md) | Continuable Init (this template) |
|--------|----------------------------------|----------------------------------|
| Continuation detection | Not included | Checks `{outputFile}` for `stepsCompleted` |
| Routing | Always proceeds to step-02 | Routes to step-01b-continue if state exists |
| continueStepFile | Not present | Required frontmatter field |
| Output document | Optional | Required (state is tracked in it) |

---

## Size Guidelines

| Metric | Target | Max |
|--------|--------|-----|
| Total lines | 80-120 | 150 |
| Sequence actions | 3-4 | 5 |

---

## Common Mistakes

1. **Not checking for existing output first** — Continuation detection MUST happen before any setup

2. **Creating duplicate documents** — Always check before creating

3. **Proceeding to step-02 when continuation exists** — Route to step-01b-continue.md immediately

4. **Missing templateFile reference** — Fresh workflows need a template to copy from
