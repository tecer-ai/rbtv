---
name: Scaffold
description: Load the right template, gather all content, and prepare the complete scaffold for user approval.
nextStepFile: step-04-build.md
---

# Step 3: Scaffold

**Goal:** Produce a complete, approved scaffold — file tree, entry point, step summaries — before writing a single file.

---

## Mandatory Sequence

### 1. Load Template

Load the appropriate template from `{rbtv_path}/workflows/component-creation/templates/`:

| Component | Template file |
|-----------|--------------|
| Workflow entry | `workflow-template.md` |
| Step file | `step-template.md` or `step-continue-template.md` |
| Agent/Persona | `agent-template.md` |
| Rule | `rule-template.md` |
| Task | `task-template.md` |
| Skill / Command (thin loader) | `ide-loader-template.md` |
| Knowledge/Data | `knowledge-template.md` |
| Output document | `output-template.md` |

### 2. Context-First Discovery

Before asking any questions, scan the conversation for already-provided information.

Present what was found:

```
Based on our conversation, I understand you want to build:
- Component type: [type]
- Name: [name]
- Purpose: [one sentence]
- [Any other gathered details]

Is this correct?
```

Wait for confirmation. Then identify gaps — ask ONLY for information that is missing.

Never ask for information the user already provided. Never ask questions whose answers can be inferred from Step 1.

### 3. Workflow Step Planning (workflows only)

For workflows, plan the complete step chain before writing any content:

| Step # | ID | Name | Goal | nextStepFile |
|--------|-----|------|------|-------------|
| 01 | step-01-{name} | {Name} | {one sentence} | step-02-{name}.md |
| ... | ... | ... | ... | ... |
| N | step-0N-{name} | {Name} | {one sentence} | null |

Also identify:
- Data files needed (names, purpose)
- Output document structure (if the workflow produces a document)

### 4. Rule Scaffold (rules only)

Present the rule's design for approval before building:

| Element | Content |
|---------|---------|
| Behavior enforced | {one sentence} |
| Trigger | {when the rule activates} |
| Scope boundary | {when the rule does NOT apply} |
| Enforcement mechanism | {type: structured output gate / sequencing gate / tripwire / pre-flight check} |
| Required output | {what visible artifact proves compliance} |
| Gaming resistance | {how token compliance is prevented} |

Also present the anti-pattern table draft (both skip and game entries).

Wait for explicit approval of the design before proceeding to build.

### 5. Skill/Command Scaffold (skills and commands only)

Prepare BOTH files:

1. **Thin loader** (`SKILL.md` or command file) — load instruction only, zero logic
2. **Backing file** (workflow, task, or agent) — all logic lives here

**Thin loader gate:** Before presenting the scaffold, verify the SKILL.md draft passes this check:

| Check | Pass | Fail |
|-------|------|------|
| SKILL.md body is a single LOAD/READ instruction pointing to a backing file | Proceed | Rewrite — move logic to backing file |
| No instructions, tables, guidelines, or reference material in SKILL.md | Proceed | Rewrite — that content belongs in the backing file or a data file |
| Backing file exists or is being created in this scaffold | Proceed | Design the backing file first |

Data files (reference docs, examples, config) MAY live alongside SKILL.md, but SKILL.md itself NEVER references or explains them — the backing file does.

Present both file contents for approval before proceeding.

### 6. Present Complete Scaffold

Present for user approval:

**File tree:**
```
{component-name}/
  workflow.md
  step-01-{name}.md
  step-02-{name}.md
  ...
  data/
    {knowledge-file}.md
```

**Entry point content:** full draft of `workflow.md` or equivalent entry file

**Step summaries** (for workflows): one-line goal per step

**Thin loader content** (for skills/commands): full draft of the loader file

Wait for explicit user approval. Do not proceed to Step 04 until the scaffold is approved.

---

## Step Menu

| Option | Action |
|--------|--------|
| [C] Continue | Proceed to Step 04 — Build |
| [X] Exit | Stop workflow |

HALT and WAIT for user input.
