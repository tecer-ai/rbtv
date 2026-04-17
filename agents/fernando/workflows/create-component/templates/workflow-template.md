# Workflow Template

Use this template to create a new BMAD workflow.

---

## Template

```markdown
---
name: {workflow-name}
description: {one-line description}
web_bundle: true
nextStep: ./steps-c/step-01-init.md
validateWorkflow: ./steps-v/step-01-init.md
editWorkflow: ./steps-e/step-01-init.md
---

# {Workflow Name}

**Goal:** {What this workflow produces in one sentence.}

**Your Role:** {Role description} collaborating with the user as a peer. This is a partnership — you bring expertise, they bring domain knowledge.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles
1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in the output document's frontmatter.
5. **Append-Only Building** — Build documents by appending content as directed to the output file.

### Step Processing Rules
1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: update frontmatter, then load the next step file.

### Critical Rules
- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter of output files when writing the final output for a specific step
- 🎯 ALWAYS follow the exact instructions in the step file
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER create mental todo lists from future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Build new {artifact} from scratch | steps-c/step-01-init.md | {output file} |
| Validate | Audit existing {artifact} for quality | steps-v/step-01-init.md | Validation report |
| Edit | Modify sections of existing {artifact} | steps-e/step-01-init.md | Updated {artifact} |

---

## INITIALIZATION SEQUENCE

1. Load module config: `{project-root}/_bmad/{module}/config.yaml`
2. Determine mode from user intent or frontmatter
3. Load the first step file for the selected mode
4. Follow step instructions exactly
```

---

## Design Decisions (answer before building)

| # | Decision | Your Answer |
|---|----------|-------------|
| 1 | **Continuable or single-session?** If continuable, add `step-01b-continue.md` | {answer} |
| 2 | **Tri-modal?** If Create only, remove `validateWorkflow`/`editWorkflow` and `steps-v/`/`steps-e/` | {answer} |
| 3 | **Module affiliation?** If part of a module, add `parentWorkflow:` field | {answer} |
| 4 | **Output type?** If document: define template. If action-only: skip output frontmatter | {answer} |

---

## Field Instructions

### Frontmatter
- **name**: Machine-readable identifier for cross-references
- **description**: Human-readable purpose
- **nextStep**: Path to first Create mode step
- **parentWorkflow**: Path to parent workflow (if part of a module/milestone hierarchy)
- **outputFolder**: Runtime output path (if produces documents)
- **validateWorkflow**: Path to first Validate mode step (optional — only if tri-modal)
- **editWorkflow**: Path to first Edit mode step (optional — only if tri-modal)

### Sections
- **Goal**: Single sentence describing what the workflow produces
- **Your Role**: Who the AI is during this workflow
- **Core Principles**: Standard 5 principles (copy as-is)
- **Critical Rules**: Standard 7 rules with emojis (copy as-is)
- **Mode Overview**: Table mapping modes to entry points
- **Initialization Sequence**: Steps to load config and first step

---

## Directory Structure

```
workflow-name/
├── workflow.md           # This file (entry point)
├── workflow.yaml         # Optional: metadata, variables
├── steps-c/              # Create mode steps
│   ├── step-01-init.md
│   ├── step-01b-continue.md  # Continuation handler
│   ├── step-02-discover.md
│   └── step-N-complete.md
├── steps-v/              # Validate mode steps (optional)
├── steps-e/              # Edit mode steps (optional)
├── templates/            # Output document templates
│   └── output-template.md
└── data/                 # Workflow-specific knowledge
```

---

## Size Guidelines

| Metric | Target | Max |
|--------|--------|-----|
| workflow.md lines | 60-80 | 120 |
| Steps per mode | 4-8 | 14 |
| Total step files | 10-15 | 30 |

---

## Common Mistakes

1. **Missing critical rules** — Always include the 7 emoji rules. They prevent AI drift.

2. **No mode routing** — If you support Validate/Edit, add frontmatter fields.

3. **Skipping init sequence** — Always load config before first step.
