# BMAD Architecture Decision Guide

A reference for understanding BMAD components and deciding which one to build.

---

## Core Concept: Text Files Are the Runtime

There is no code to compile, no server to run. The markdown files ARE the application. When the AI reads a file, it becomes that file's instructions. This means:

- Every word matters
- Instructions must be explicit and unambiguous
- The AI will follow what you write literally
- Structure your files as if writing a script the AI will execute

---

## The Five Layers

An agentic system has five layers, each a directory of text files:

| Layer | Purpose | Contains |
|-------|---------|----------|
| **Entry Points** | Bridge between IDE and system | Command files (thin loaders) |
| **Agents** | Personas with menus | Agent definition files |
| **Workflows** | Multi-step document builders | workflow.md + step files |
| **Knowledge** | Reference data | CSV, Markdown, YAML data files |
| **Infrastructure** | Configuration and discovery | config.yaml, manifests |

---

## Component Decision Tree

### What are you building?

**Start here:**

1. **Does it need a PERSONA that users interact with through a menu?**
   - YES → **AGENT**
   - NO → Continue to #2

2. **Does it produce an OUTPUT DOCUMENT through multiple sequential steps?**
   - YES → **WORKFLOW** (with step files)
   - NO → Continue to #3

3. **Is it a SINGLE-PURPOSE procedure that can be invoked by agents or workflows?**
   - YES → **TASK**
   - NO → Continue to #4

4. **Is it REFERENCE DATA that agents or workflows consult?**
   - YES → **KNOWLEDGE** (CSV, Markdown, or YAML)
   - NO → Continue to #5

5. **Is it SETTINGS that multiple components need?**
   - YES → **CONFIG** (config.yaml)
   - NO → Continue to #6

6. **Is it an ENTRY POINT that loads an agent or workflow?**
   - YES → **IDE COMMAND** (thin loader)
   - NO → Clarify requirements

---

## Blurry Lines Clarified

### Agent vs. Workflow

| Aspect | Agent | Workflow |
|--------|-------|----------|
| **Primary function** | Persona with menu of capabilities | Multi-step document builder |
| **User interaction** | Menu-driven, conversational | Sequential steps with Continue |
| **Output** | Routes to workflows or tasks | Produces a specific document |
| **State** | Optional memory (Expert agents) | State in output document frontmatter |
| **When to use** | Need personality + routing | Need structured document creation |

**Rule of thumb:** If you're building a character that does many things, it's an agent. If you're building a process that produces one document, it's a workflow.

### Workflow vs. Task

| Aspect | Workflow | Task |
|--------|----------|------|
| **Structure** | Multiple step files | Single XML file |
| **Output** | Document with frontmatter state | Action completion |
| **Invocation** | From agent menu or IDE command | From agent, workflow step, or direct |
| **Resumability** | Built-in via stepsCompleted | Not resumable |
| **When to use** | Building documents incrementally | Single-purpose procedures |

**Rule of thumb:** If you need to track progress across sessions and build a document section by section, it's a workflow. If you need a reusable procedure that completes in one go, it's a task.

### Step vs. Task

| Aspect | Step | Task |
|--------|------|------|
| **Bound to** | A specific workflow | Standalone, reusable |
| **Sequential** | Always follows previous step | Independent execution |
| **Output** | Appends to workflow's output document | Own action/output |
| **When to use** | Part of a workflow sequence | Reusable across contexts |

**Rule of thumb:** Steps are chapters in a book (workflow). Tasks are standalone utilities.

---

## Component Size Guidelines

| Component | Recommended Lines | Max |
|-----------|------------------|-----|
| Agent file | 55-76 | 100 |
| Workflow entry (workflow.md) | 60-80 | 120 |
| Step file | 80-200 | 250 |
| Task file (XML) | 40-100 | 150 |
| IDE command file | 10-15 | 20 |
| Module config.yaml | 8-15 | 20 |
| Knowledge fragment | 50-200 | 300 |

**Key insight:** Keep files short. If a file exceeds the max, split it.

---

## Design Principles

| # | Principle | Why It Matters |
|---|-----------|----------------|
| 1 | Text files are the runtime | The AI reads and executes your files literally |
| 2 | Micro-file architecture | Shorter files = less drift, easier maintenance |
| 3 | Sequential enforcement | AI tries to skip/optimize; prevent explicitly |
| 4 | User control at every step | Every step ends with menu, AI halts and waits |
| 5 | Persona-driven interaction | Specific personas produce specific output |
| 6 | Configuration over hardcoding | Use {project-root} variables, never absolute paths |
| 7 | Thin loaders | Entry points contain zero logic |
| 8 | State in frontmatter | Output documents track stepsCompleted |

---

## Workflow Design Decisions

Before building a workflow, answer these 4 questions:

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| 1 | **Continuable or single-session?** | Continuable: user may return across sessions | If continuable: add `step-01b-continue.md` that reads existing output frontmatter and resumes |
| 2 | **Tri-modal?** | Create only, or Create + Validate + Edit | If tri-modal: create `steps-v/` and `steps-e/` directories; add `validateWorkflow` and `editWorkflow` frontmatter |
| 3 | **Module affiliation?** | Standalone vs part of a module | Affects config.yaml path and `parentWorkflow` field |
| 4 | **Output type?** | Document (frontmatter + sections) vs action-only | If document: define output template; if action-only: no output frontmatter needed |

### Step Type Patterns

| Type | When to Use | Example |
|------|-------------|---------|
| **init** | First step — load context, check prerequisites, create output doc | `step-01-init.md` |
| **continuation** | Resume existing output — offer "continue" or "start fresh" | `step-01b-continue.md` |
| **middle** | Core work step — elicit, analyze, generate content | `step-02-discover.md` |
| **branch** | Decision point — route to different step paths | `step-03-select-mode.md` |
| **final/synthesis** | Last step — compile, validate, update project-memo | `step-N-synthesis.md` |

### Frontmatter Standards

**Required for all step files:** `name`, `description`, `nextStepFile`
**Optional:** `outputFile`, `partyModeWorkflow`, `knowledgeFile`
**FORBIDDEN in frontmatter:** `workflow_path`, `thisStepFile` (these create circular references)

---

## Common Mistakes to Avoid

| Mistake | Why It Fails | Better Approach |
|---------|--------------|-----------------|
| Generic personas | AI defaults to generic helpful assistant | Use metaphors, specific beliefs, communication quirks |
| Long files | AI loses context, drifts from instructions | Split files, keep each under 200 lines |
| Logic in entry points | Creates IDE-specific behavior | Entry points only load files |
| Missing STOP instructions | AI rushes through steps | Explicit halt: "WAIT for user input" |
| Hardcoded paths | Breaks when moved | Use {project-root} variables |
| Hardcoded catalog lists | Drift and maintenance burden | Reference manifests (tools-manifest.csv, etc.) |
| No state tracking | Can't resume sessions | Frontmatter in output documents |
| Skipping adversarial review | Rubber-stamped output | Build in mandatory challenge mechanisms |

---

## Manifest-First Checklist

Before generating a file that references a catalog of commands, skills, rules, cursor sub-agents, or similar:

1. **Check:** Does the file you're generating contain a catalog-style list? (e.g. "all commands", "every skill", "all rules")
   - If NO catalog list → no manifest needed, proceed normally
   - If YES → continue to step 2
2. **Check:** Does a manifest already exist for this catalog?
   - AI-available tools (skills + cursor sub-agents) → `_bmad/rbtv/_config/tools-manifest.csv`
3. **If manifest exists:** Reference it in the generated file (path + column names), NOT an inline list
4. **If no manifest exists:** CREATE one as a `.csv` in `_bmad/rbtv/_config/` and reference it

**NEVER** hardcode catalog-style lists inline. Always point to a manifest as the single source of truth.

> **Terminology:** All skills and cursor sub-agents are also commands, but not all commands are skills/cursor sub-agents. Files in `.cursor/agents/` are **cursor sub-agents** (thin loaders for the Cursor sub-agent feature), NOT RBTV agent personas.

---

## Cross-Reference Patterns

How components connect to each other:

| Source | Points To | Mechanism |
|--------|-----------|-----------|
| IDE Command | Agent file | `{project-root}` path in LOAD instruction |
| Agent menu | Workflow/Task | `exec`, `workflow`, or `template` attribute |
| Agent activation | config.yaml | Hardcoded {project-root} path (step 2) |
| Workflow.md | First step file | Frontmatter `nextStep` |
| Step file | Next step file | Frontmatter `nextStepFile` |
| Step file | Output document | Frontmatter `outputFile` |
| Output document | Steps completed | `stepsCompleted` array in frontmatter |

---

## Quick Reference: When to Build What

| You want to... | Build a... |
|----------------|------------|
| Create a character users interact with | Agent |
| Build a document through guided steps | Workflow |
| Add a step to an existing workflow | Step file |
| Create a reusable procedure | Task |
| Store reference data | Knowledge file |
| Store project settings | config.yaml |
| Create an entry point for IDE | IDE Command |
| Catalog all agents/workflows | Registry (CSV) |
| Define a document structure | Output template |
