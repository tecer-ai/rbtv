# Guide: Building an Agentic System

A practical guide for building text-file-based agentic systems that run inside AI code editors (Claude Code, Cursor).

**Based on**: Patterns extracted from BMAD 6.0.0-Beta.4
**Date**: 2026-02-01

---

## What You Are Building

An agentic system is a set of text files that turn an AI code editor into a structured, repeatable tool for a specific domain. When the user invokes a command, the AI reads your files, adopts a persona, follows a workflow, consults knowledge bases, and produces output documents.

There is no code to compile, no server to run. Your files ARE the application.

---

## Prerequisites

- An AI code editor: Claude Code or Cursor (or both)
- A domain you want to systematize (product development, testing, content creation, etc.)
- Understanding that the AI will read your files literally — every word matters

---

## Phase 1: Foundation

### Step 1.1: Set Up the Directory Structure

```
your-project/
├── .claude/commands/       # Claude Code entry points
├── .cursor/commands/       # Cursor entry points
├── _system/                # Core system (name this whatever fits)
│   ├── config.yaml         # Global configuration
│   ├── agents/             # Agent definitions
│   ├── workflows/          # Workflow directories
│   ├── tasks/              # Standalone task files
│   ├── data/               # Shared knowledge bases
│   └── _memory/            # Persistent state (optional)
└── _output/                # Generated artifacts
```

Pick a name for your system directory (`_system/`, `_agents/`, `_bmad/`, whatever fits your project). Use a leading underscore to signal "system files, not project files."

### Step 1.2: Create the Global Configuration

**File: `_system/config.yaml`**

```yaml
# Project settings
project_name: "Your Project"
user_name: "Your Name"
communication_language: English
document_output_language: English

# Output paths
output_folder: "{project-root}/_output"
```

This is the single source of truth for project-wide settings. Every agent and workflow loads this file first.

**Rules for config.yaml:**
- Use `{project-root}` for all paths — never hardcode absolute paths
- Keep it flat (key-value pairs). Avoid deep nesting.
- Only include settings that multiple components need

### Step 1.3: Create Your First Agent

Start with ONE agent. Don't design the whole system upfront.

**File: `_system/agents/my-agent.md`**

Use the agent template from the [Component Patterns document](./03-component-patterns-and-templates.md#1-agent-patterns-and-template). Fill in:

1. **Persona** — this is where you spend the most time
   - `role`: What the agent does + their specialization
   - `identity`: Who they are (background, personality)
   - `communication_style`: How they talk (use a metaphor or archetype)
   - `principles`: 2-4 beliefs that shape their judgment (NOT tasks)

2. **Menu** — start with 2-3 items plus the standard PM/DA entries
   - Each item needs a 2-letter command shortcut
   - Each item needs a routing attribute (exec, workflow, or action)

3. **Activation** — follow the standard 5-step activation protocol

**Common mistake:** Writing generic personas. "A helpful assistant that manages projects" is useless. "A detective who asks WHY relentlessly, cuts through fluff, and believes that PRDs should emerge from user interviews not template filling" — that shapes behavior.

### Step 1.4: Create the IDE Command

**File: `.claude/commands/my-agent.md`** (and identical copy in `.cursor/commands/`)

```markdown
---
name: 'my-agent'
description: 'what this agent does'
---

You must fully embody this agent's persona and follow all activation instructions exactly as specified. NEVER break character until given an exit command.

<agent-activation CRITICAL="TRUE">
1. LOAD the FULL agent file from {project-root}/_system/agents/my-agent.md
2. READ its entire contents
3. FOLLOW every step in the <activation> section precisely
4. DISPLAY the welcome/greeting as instructed
5. PRESENT the numbered menu
6. WAIT for user input before proceeding
</agent-activation>
```

**Test it now.** Open your editor, run the command, verify the agent activates with the right persona and shows the menu.

---

## Phase 2: First Workflow

### Step 2.1: Design the Workflow

Before writing files, answer:
- What does this workflow produce? (output document)
- How many steps does it need? (aim for 4-8)
- Does it need Create/Validate/Edit modes? (start with Create only)
- What inputs does it need from the user?

### Step 2.2: Create the Workflow Directory

```
_system/workflows/my-workflow/
├── workflow.md              # Entry point
├── steps-c/                 # Create mode steps
│   ├── step-01-init.md
│   ├── step-02-discover.md
│   ├── step-03-draft.md
│   └── step-04-complete.md
└── templates/
    └── output-template.md
```

### Step 2.3: Write workflow.md

Use the workflow template from the [Component Patterns document](./03-component-patterns-and-templates.md#2-workflow-patterns-and-template). The key content:

- Goal statement (1 sentence)
- Role definition (who the AI is during this workflow)
- Core principles (copy the standard 4 principles)
- Critical rules (copy the standard 6 rules with emojis)
- Initialization sequence (load config, load first step)

### Step 2.4: Write the Output Template

**File: `templates/output-template.md`**

```markdown
---
title: '{Document Title}'
stepsCompleted: []
inputDocuments: []
workflowType: 'my-workflow'
date: '{{date}}'
user_name: '{{user_name}}'
project_name: '{{project_name}}'
---

# {Document Title}

_This document builds through step-by-step discovery._
```

The frontmatter is critical — it enables state tracking and session resumption.

### Step 2.5: Write Step Files

Follow the step file template from the [Component Patterns document](./03-component-patterns-and-templates.md#3-step-file-patterns-and-template).

**Step-01-init.md** is special. It must:
1. Check if the output document already exists (for continuation)
2. Discover input documents (scan configured directories)
3. Create the output document from template
4. Present a welcome message and menu

**Middle steps** (02, 03, etc.) follow the standard pattern:
1. STEP GOAL (what this step accomplishes)
2. MANDATORY EXECUTION RULES
3. MANDATORY SEQUENCE (numbered actions)
4. Menu (A/P/C options)
5. Step completion note (update frontmatter, load next)

**Final step** marks the workflow complete:
1. Review the entire output document
2. Final polish pass
3. Save to the configured output location
4. Report completion

### Step 2.6: Wire the Workflow to the Agent

Add a menu item to your agent that routes to this workflow:

```xml
<item cmd="MW or fuzzy match on my workflow" workflow="{project-root}/_system/workflows/my-workflow/workflow.yaml">[MW] My Workflow: Description of what it does</item>
```

### Step 2.7: Create the Workflow Command

**File: `.claude/commands/my-workflow.md`** (and `.cursor/commands/`)

```markdown
---
name: 'my-workflow'
description: 'what this workflow does'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND: LOAD the FULL {project-root}/_system/workflows/my-workflow/workflow.md, READ its entire contents and follow its directions exactly!
```

**Test it end to end.** Run the workflow command, go through each step, verify the output document is produced correctly.

---

## Phase 3: Knowledge and Data

### Step 3.1: Decide What Knowledge Your System Needs

Knowledge files are reference material that agents and workflows consult. Categories:

| Type | Format | Use When |
|------|--------|----------|
| Domain expertise | Markdown | Detailed explanations, patterns, best practices |
| Structured catalogs | CSV | Lists of methods, frameworks, presets, options |
| Reference indexes | CSV/YAML | Mapping topics to knowledge fragments (for large KBs) |
| Examples | Markdown | Sample outputs, reference implementations |

### Step 3.2: Write Knowledge Files

**Keep knowledge files focused.** One topic per file, 50-200 lines. If a file is getting long, split it.

**For CSV data files:**
```csv
name,category,description,when_to_use
"Method A","analysis","What it does","When it's appropriate"
"Method B","design","What it does","When it's appropriate"
```

Always include a description column and a category column for filtering.

**For markdown knowledge:**
- Use clear headers
- Include practical examples
- Write imperatively ("Do X" not "One might consider X")
- Reference specific techniques, not vague concepts

### Step 3.3: Connect Knowledge to Agents/Workflows

**Small knowledge bases (< 10 files):** Load eagerly during agent activation.

**Large knowledge bases (10+ files):** Use the index pattern:
1. Create an index file (CSV) mapping topics to fragment paths
2. Agent consults the index based on user's question
3. Agent loads only relevant fragments

---

## Phase 4: Scaling Up

### Step 4.1: Add Workflow Modes (Validate, Edit)

Once your Create mode works, add:

**Validate mode (steps-v/):**
- Step-01: Load existing document, set up validation report
- Steps 2-N: Check specific quality criteria
- Final step: Produce validation report with findings

**Edit mode (steps-e/):**
- Step-01: Load existing document, ask what to change
- Steps 2-N: Execute targeted edits
- Final step: Save updated document

Update workflow.md to add mode routing:
```yaml
nextStep: ./steps-c/step-01-init.md
validateWorkflow: ./steps-v/step-01-init.md
editWorkflow: ./steps-e/step-01-init.md
```

### Step 4.2: Add More Agents

Each agent should have:
- A distinct persona (not just a different name)
- A different expertise domain
- A different communication style
- At least one unique workflow or capability

**Avoid:** Creating agents that overlap heavily. If two agents do similar things, merge them or sharpen their differentiation.

### Step 4.3: Create Workflow Chains

Workflows produce documents. Later workflows consume those documents as inputs.

![Diagram 01](04-guide-building-agentic-systems_mmdc/diagram_01.png)

**Input discovery pattern:** Each workflow's init step scans configured directories for input documents using filename patterns. The user confirms which documents to load.

### Step 4.4: Add Registries

When you have 5+ agents or 10+ workflows, add CSV registries:

**agent-manifest.csv:**
```csv
name,displayName,title,icon,role,module,path
analyst,"Mary","Business Analyst",📊,"Analysis + requirements",main,agents/analyst.md
```

**workflow-manifest.csv:**
```csv
name,description,module,path
create-brief,"Create product brief",main,workflows/create-brief/workflow.md
```

The master agent (or help system) queries these registries to list available capabilities.

### Step 4.5: Modularize (When Needed)

When your system grows beyond one domain, split into modules:

```
_system/
├── _config/            # Global registries
│   ├── manifest.yaml
│   ├── agent-manifest.csv
│   └── workflow-manifest.csv
├── core/               # Shared infrastructure
│   ├── config.yaml
│   ├── agents/
│   └── tasks/
├── module-a/           # Domain A
│   ├── config.yaml
│   ├── agents/
│   ├── workflows/
│   └── data/
└── module-b/           # Domain B
    ├── config.yaml
    ├── agents/
    ├── workflows/
    └── data/
```

Each module has its own config.yaml, agents, workflows, and data. Global registries catalog everything.

---

## Phase 5: Quality Patterns

### Step 5.1: Add Adversarial Review

AI agents tend to agree with everything. Build in adversarial patterns:

**Code review workflow:** Must find 3-10 issues minimum. "Looks good" is a failure state.

**Validation workflows:** Check against specific, measurable criteria. Report findings, not opinions.

**Gate workflows:** Block progression to the next phase until quality criteria are met.

### Step 5.2: Add Session Continuity

For workflows that take multiple sessions:

1. **step-01b-continue.md** — detect existing output document
2. Read `stepsCompleted` from frontmatter
3. Find the last completed step's `nextStepFile`
4. Greet user with context summary
5. Route to the next unfinished step

### Step 5.3: Add Memory (Expert Agents)

For agents that should learn across sessions:

```
_memory/
└── agent-name/
    ├── memories.md       # Accumulated knowledge
    ├── preferences.md    # User preferences
    └── entries/          # Session records
```

Agent activation loads memory files. Agent records new observations during interaction.

---

## Rules of Thumb

### DO

1. **Keep files short.** Agent files: 55-76 lines. Step files: 80-200 lines. If a file is over 250 lines, split it.

2. **Write for literal execution.** The AI reads your words literally. "Consider possible approaches" produces vague output. "List 3 approaches with trade-offs for each" produces specific output.

3. **Use emojis for critical rules.** 🛑 NEVER, 📖 ALWAYS, 🚫 FORBIDDEN. These catch the AI's attention in long documents.

4. **Test each component in isolation.** Activate an agent. Run a workflow. Walk through each step. Don't build the whole system before testing.

5. **Use the standard menu pattern.** [A] Advanced Elicitation, [P] Party Mode, [C] Continue. Users learn one pattern and it works everywhere.

6. **Make personas specific.** Use metaphors, name specific frameworks, give agents opinions. Generic personas produce generic output.

7. **Track state in frontmatter.** YAML frontmatter in output documents is your workflow's database.

8. **Use variable placeholders.** `{project-root}`, `{user_name}`, `{output_folder}`. Never hardcode paths.

### DON'T

1. **Don't put logic in command files.** Command files are thin loaders. All logic lives in agent/workflow files.

2. **Don't let the AI skip steps.** Explicit sequential enforcement. "Do not deviate, skip, or optimize." Without this, the AI will compress or skip steps.

3. **Don't write principles as tasks.** "Manage sprints" is a task. "Small batches reduce risk" is a principle. Principles shape judgment.

4. **Don't load multiple step files.** One step at a time. Load next only on user Continue. This prevents the AI from pre-reading and rushing.

5. **Don't design the whole system upfront.** Start with one agent and one workflow. Test. Iterate. Add complexity only when needed.

6. **Don't over-abstract.** Three similar step files are better than a premature template system. Duplication is cheaper than the wrong abstraction.

7. **Don't forget adversarial review.** The AI agrees with everything unless you build in explicit challenge mechanisms.

8. **Don't nest too deeply.** If you find yourself 5 directories deep, flatten. `_system/module/workflows/workflow-name/steps-c/` is about as deep as you should go.

---

## Checklist: Minimum Viable Agentic System

- [ ] Directory structure created (`_system/`, `.claude/commands/`, `.cursor/commands/`)
- [ ] config.yaml with project name, user name, output paths
- [ ] One agent with distinct persona, menu, activation protocol
- [ ] IDE command file for the agent (both IDEs)
- [ ] Agent activates correctly and shows menu
- [ ] One workflow with 4+ steps (Create mode)
- [ ] Output template with frontmatter state tracking
- [ ] Step files follow the standard structure (goal, rules, sequence, menu)
- [ ] Workflow produces correct output document
- [ ] IDE command file for the workflow (both IDEs)

---

## Checklist: Production-Ready Agentic System

- [ ] All items from minimum viable checklist
- [ ] 3+ agents with distinct personas and expertise domains
- [ ] Workflow chains (output of one workflow feeds into the next)
- [ ] Tri-modal workflows (Create/Validate/Edit) for key artifacts
- [ ] Session continuity (step-01b-continue.md in long workflows)
- [ ] Knowledge bases (CSV data + markdown references)
- [ ] Adversarial review workflows (gate checks, code review)
- [ ] CSV registries (agent-manifest, workflow-manifest)
- [ ] Help system (maps user intents to workflows)
- [ ] Modular organization (if multi-domain)
- [ ] Memory system for expert agents (if needed)
- [ ] All components tested end to end

---

## Reference

- [BMAD Architecture](./01-bmad-architecture.md) — detailed architecture of the reference system
- [Agentic System Architecture](./02-agentic-system-architecture.md) — abstract architecture reference
- [Component Patterns and Templates](./03-component-patterns-and-templates.md) — templates for every component type
