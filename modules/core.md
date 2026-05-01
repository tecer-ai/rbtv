# Core

## Purpose

The core module is always installed — it's the foundation every other RBTV module depends on. It provides the generic productivity layer: structured planning, web research, document processing, browser automation, and the component authoring workflow. It also installs the behavioral rules that passively shape every Claude interaction in any workspace where RBTV is present. If you install RBTV at all, you have core.

---

## Components

### Planning & meta

Tools for creating structured plans and extending the RBTV system itself.

#### `rbtv-planning`

- **What**: Interactive workflow that produces a complete, self-executing plan — a main plan file, a scope document (`shape.md`), a learnings log, and individual micro-step task files for each action. Each micro-step file contains complete execution instructions so the plan runs without the original conversation context.
- **When to use**: Any multi-step task where you want a structured output you can hand off to another agent session, delegate to a teammate, or return to later. Good for projects, feature builds, operational rollouts, or anything with more than 3–4 sequential decisions.
- **How to invoke**: Say "create a plan for X" or "let's plan this out" — Claude picks up the trigger automatically. You can also say `rbtv-planning` directly.
- **Inputs / outputs**:
  - Input: task description, gathered conversationally across 4 guided steps
  - Output: `{plan-name}-plan.md`, `shape.md`, `learnings.md`, and `phase-N/pN-X.task.md` micro-step files in a folder at the confirmed output path
- **Example**: "Create a plan for migrating our CRM to HubSpot" → Claude walks through scope, phases, and task granularity, then writes all files.

---

#### `rbtv-create-component`

- **What**: Guided builder for any RBTV or vault AI component — skills, workflows, rules, commands, personas, tasks. Acts as a design partner: it challenges assumptions and forces key decisions before writing any file. Handles both RBTV-standard components (placed in the RBTV source repo) and workspace-native components (placed per that workspace's CLAUDE.md conventions).
- **When to use**: Creating a new skill, workflow, or rule from scratch. Modifying an existing component. Trying to understand how a component is structured before editing it. Use this instead of manually exploring component directories — the workflow handles discovery.
- **How to invoke**: "Create a new skill for X" or "build a workflow for Y" — or invoke by name: `rbtv-create-component`.
- **Inputs / outputs**:
  - Input: component type, description of what it should do, target system (RBTV or workspace-native)
  - Output: correctly placed and structured component file(s) with compliant naming and size
- **Example**: "I need a skill that runs our weekly competitor scan" → Claude identifies the right component type, drafts the structure, confirms placement, writes the files.

---

### Research

Tools for getting information from the web and processing long-form documents.

#### `rbtv-web-searching`

- **What**: Three-mode web interaction layer — Preview (title/description only), Extract (full page content via Defuddle CLI), and Research (multi-source, cited, scored). Research mode enforces data integrity: every claim requires a verified source, sources are scored on authority/trustability/topic-match, and anything below a 6/10 threshold is discarded. Output always includes a citation legend and a "Sources Discarded" section.
- **When to use**: Any time you give Claude a URL to read, ask it to research a topic, or need facts with citations. This skill is also mandatory for any sub-agent doing web work — parent agents must name it explicitly in sub-agent prompts.
- **How to invoke**: Triggered automatically when you paste a URL or ask Claude to research something. Invocable directly: `rbtv-web-searching`.
- **Inputs / outputs**:
  - Preview: URL → title + description
  - Extract: URL → clean markdown article body (Defuddle removes ads/nav)
  - Research: topic → structured report with scored citations, discarded sources, and fact/analysis/speculation labels
- **Example**: "Research the current state of AI agent frameworks" → Claude searches, scores sources, and returns a cited report with a legend and discarded-sources list.

---

#### `/rbtv-digest`

- **What**: Processes a long source (conversation export, transcript, book chapter, long document) that the orchestrator Claude cannot read directly due to context limits. It chunks the source, dispatches sub-agents to extract decisions or concepts from each chunk, groups the results, and synthesizes them into either a **reconciled document** (updates an existing doc with session decisions + user line-comments) or a **study note**. The orchestrator never reads the source — only sub-agents do.
- **When to use**: You have a long conversation or document you want to mine for decisions, incorporate into an existing spec, or turn into study notes. Especially useful after long planning sessions where you want to update a PRD or plan with what was decided.
- **How to invoke**: `/rbtv-digest` — Claude asks for source path, mode (reconcile or study), and target document.
- **Inputs / outputs**:
  - Input: source file path, mode selection, target document(s) for reconcile or destination for study
  - Output (reconcile): target document(s) updated in place + a delta document per target showing what changed
  - Output (study): new study note at confirmed destination
- **Example**: `/rbtv-digest` → "reconcile" → point to a long strategy conversation → point to your current strategy doc → Claude mines the conversation and updates the doc with decisions made, showing a diff.

---

### Personas

#### `/rbtv-session-close` (Ana)

- **What**: Invokes Ana, a session-close specialist persona. Ana presents a menu with three modes: **Compound** (captures an agent correction or improvement as a backlog PRD — turns a session fix into a durable system change), **Handoff** (writes a context-transfer document so the next agent session picks up seamlessly), and **Refresh** (updates an active plan or PRD with outcomes from this session, no new file).
- **When to use**: End of any significant working session — especially when the session produced corrections, decisions, or scope changes worth preserving. Run before closing a long planning or coding session to avoid losing context.
- **How to invoke**: `/rbtv-session-close` — or with a mode flag: `/rbtv-session-close compound`, `/rbtv-session-close handoff`, `/rbtv-session-close refresh`.
- **Inputs / outputs**:
  - Input: mode selection (or Ana suggests one based on session content)
  - Output: one of — a backlog PRD (compound), a handoff document (handoff), or an in-place update to an existing plan/PRD (refresh)
- **Example**: After a session where Claude made an error you corrected: `/rbtv-session-close compound` → Ana captures the correction as an improvement PRD, ready for the RBTV backlog.

---

### Dev utilities

#### `rbtv-playwright-cli`

- **What**: Browser automation via Playwright CLI — takes screenshots, runs interactions, and tests web pages. Restricts Bash permissions to `playwright-cli:*` commands only.
- **When to use**: Automating browser tasks, capturing page screenshots, or testing web UI.
- **How to invoke**: "Take a screenshot of X" or "test this page interaction" — or `rbtv-playwright-cli` directly.
- **Inputs / outputs**: URL or interaction description → screenshots, test results, or extracted page state
- **Example**: "Screenshot the current state of our staging dashboard" → Claude runs Playwright CLI and returns the image.

---

## Rules — always-loaded behavior

These rules are copied into every workspace's `.claude/rules/` on install and shape Claude's behavior across every interaction. They aren't invoked manually — they're passive context that fires automatically. Full text is in the linked files.

| Rule | What it enforces |
|------|------------------|
| [atomic-files](../rules/atomic-files.md) | Agent-facing files must be self-contained, non-repetitive, and use mandatory language — no context-only references or summarized file content |
| [audio-aware](../rules/audio-aware.md) | Handles transcription artifacts (self-corrections, ambiguous names/dates) and loads a name glossary at session start |
| [bash-patterns](../rules/bash-patterns.md) | Bans shell operators (`\|`, `&&`, `;`, redirects) in Bash calls — each command must be a single, auditable invocation with absolute paths |
| [chat-discipline](../rules/chat-discipline.md) | Every response leads with the decision or result, not the analysis; prose capped at 6 lines outside tables/code; full detail goes to output files |
| [compounding](../rules/compounding.md) | On any user correction, Claude checks whether a structural fix (rule, workflow, routing change) would prevent recurrence and offers to implement it |
| [context-preservation](../rules/context-preservation.md) | Detects valuable session context (reasoned choices, unwritten knowledge, structured data) and routes it to the right vault/plan destination before the session ends |
| [output-resolution](../rules/output-resolution.md) | Before writing any output file, Claude proposes a specific resolved path with reasoning and waits for confirmation — never writes to an assumed location |
| [reasoning](../rules/reasoning.md) | Mandates a `<counter>` block before any agreement or endorsement; enforces position stability under pressure; prevents sycophancy |
| [skill-first](../rules/skill-first.md) | The first tool call on any new task must be a skill scan — Claude cannot proceed to Read/Grep/Bash before checking whether a skill covers the task |
| [source-of-truth](../rules/source-of-truth.md) | Installed `.claude/` files are generated copies — all edits go to the RBTV source repo; re-run `install.py` to propagate |
