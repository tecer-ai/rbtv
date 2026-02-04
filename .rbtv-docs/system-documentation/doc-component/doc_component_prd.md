# Doc Component PRD

**Version:** 1.0  
**Date:** 2026-02-04  
**Status:** Implemented

---

## Overview

The `/bmad-rbtv-doc` command provides unified documentation generation through a single orchestrator agent (Ana) with mode-based routing. Part of the RBTV BMAD module at `_bmad/rbtv/`.

### Problem Solved

Three documentation needs consolidated into one command:
- **Compound** — Capture corrections/improvements as backlog PRDs
- **Handoff** — Create context transfer summaries for agent continuity
- **Product** — Create product documentation (Brief, PRD, UX Design)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Entry Point                                        │
│   .cursor/commands/bmad-rbtv-doc.md (thin loader)           │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Orchestrator Agent                                 │
│   _bmad/rbtv/agents/ana.md                                  │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Mode Workflows                                     │
│   _bmad/rbtv/workflows/doc/{mode}/workflow.md               │
│   + steps-c/ (create mode steps)                            │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Templates                                          │
│   _bmad/rbtv/workflows/doc/{mode}/templates/*.md            │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
_bmad/rbtv/
├── agents/
│   └── ana.md                          # Documentation Orchestrator
├── config.yaml                         # Module configuration
├── rbtv-manifest.csv                   # Command registry
└── workflows/
    └── doc/
        ├── compound/
        │   ├── workflow.md
        │   ├── steps-c/
        │   │   ├── step-01-init.md
        │   │   ├── step-02-self-assessment.md
        │   │   ├── step-03-discussion.md
        │   │   └── step-04-document.md
        │   └── templates/
        │       └── compound-prd.md
        └── handoff/
            ├── workflow.md
            ├── steps-c/
            │   ├── step-01-init.md
            │   ├── step-02-location-selection.md
            │   ├── step-03-extraction.md
            │   └── step-04-document.md
            └── templates/
                ├── handoff-plan-development.md
                ├── handoff-execution.md
                └── handoff-project.md
```

---

## Configuration

All configuration inherited from `_bmad/core/config.yaml`:
- `user_name`
- `communication_language`
- `document_output_language`
- `output_folder`

> **Note:** Workflow-specific output paths are defined in each workflow.md frontmatter. Product mode paths are managed by BMM workflows.

---

## Modes

### Mode Summary

| Mode | Purpose | Invocation | Status |
|------|---------|------------|--------|
| Compound | Capture improvements as backlog PRDs | `/bmad-rbtv-doc compound` | Implemented |
| Handoff | Context transfer for agent continuity | `/bmad-rbtv-doc handoff` | Implemented |
| Product | Product documentation (Brief, PRD, UX) | `/bmad-rbtv-doc product` | Links to BMAD core |

### Compound Mode

**Purpose:** Document corrections, improvements, or patterns as backlog PRDs for later implementation.

**Invocation:**
- `/bmad-rbtv-doc compound` — Standard (with discussion)
- `/bmad-rbtv-doc compound:yolo` — Skip discussion step

**Workflow (4 steps):**

| Step | File | Purpose |
|------|------|---------|
| 01 | step-01-init.md | Detect context, create output document |
| 02 | step-02-self-assessment.md | Error analysis, context evaluation, 5 improvement options |
| 03 | step-03-discussion.md | Discuss with user (skipped in yolo mode) |
| 04 | step-04-document.md | Generate backlog PRD, save to output location |

**Output:** Backlog PRD at `{outputFolder}/{filename}.md` (outputFolder defined in workflow.md)

**Key Rules:**
- Agent must perform self-assessment before documenting
- Generate exactly 5 distinct improvement approaches
- Document only — never implement changes

### Handoff Mode

**Purpose:** Create context transfer summaries enabling seamless continuation by a new agent.

**Invocation:**
- `/bmad-rbtv-doc handoff` — Project handoff (default)
- `/bmad-rbtv-doc handoff:plan` — Plan development handoff
- `/bmad-rbtv-doc handoff:exec` — Execution handoff

**Handoff Types:**

| Type | Template | Key Sections |
|------|----------|--------------|
| Plan Development | handoff-plan-development.md | Problem, Goals, Constraints, Judge Feedback |
| Execution | handoff-execution.md | Problem, Goals, Task Instructions, Files to Load |
| Project | handoff-project.md | Context Summary, Current State, Decisions |

**Workflow (4 steps):**

| Step | File | Purpose |
|------|------|---------|
| 01 | step-01-init.md | Detect context, determine handoff type |
| 02 | step-02-location-selection.md | Select output location |
| 03 | step-03-extraction.md | Extract goals, decisions, constraints |
| 04 | step-04-document.md | Generate handoff, include cleanup instruction |

**Output:** Handoff summary at user-selected location

**Key Rules:**
- Extract all decisions, constraints, and goals from conversation
- Include self-delete prompt for receiving agent
- Type-appropriate sections based on handoff type

### Product Mode

**Purpose:** Create product documentation through BMAD core workflows.

**Invocation:**
- `/bmad-rbtv-doc product` — Shows sub-menu
- `/bmad-rbtv-doc product:brief` — Product Brief
- `/bmad-rbtv-doc product:prd` — PRD (Create/Validate/Edit)
- `/bmad-rbtv-doc product:ux` — UX Design

**Integration:** Product sub-modes link to BMAD Method workflows at `_bmad/bmm/workflows/`:

| Sub-Mode | BMAD Workflow Path |
|----------|-------------------|
| Brief | `1-analysis/create-product-brief/workflow.md` |
| PRD | `2-plan-workflows/create-prd/workflow.md` |
| UX | `2-plan-workflows/create-ux-design/workflow.md` |

**Output:** Documents at `{planning_artifacts}/`

---

## Orchestrator Agent

**File:** `_bmad/rbtv/agents/ana.md`

**Persona:** Documentation Orchestrator + Knowledge Curator

**Activation Sequence:**
1. Load persona
2. Load `config.yaml` — store session variables
3. Check for mode argument — route if provided
4. Analyze conversation context — suggest mode if pattern detected
5. Present menu and wait for selection
6. Execute selected workflow

**Menu:**

| Command | Action |
|---------|--------|
| [P] Product | Show product sub-menu |
| [H] Handoff | Execute handoff workflow |
| [C] Compound | Execute compound workflow |
| [MH] Menu Help | Redisplay menu |
| [DA] Dismiss Agent | Exit |

**Shared Rules:**
- Communicate in configured language
- Track progress in output document frontmatter
- Halt at menus and wait for user input
- Never implement changes — document only
- All outputs use mode's template
- Respect configured output paths

---

## Workflow Architecture

All doc workflows follow BMAD micro-file architecture:

| Principle | Description |
|-----------|-------------|
| Micro-file Design | Each step is self-contained |
| Just-In-Time Loading | Only current step in memory |
| Sequential Enforcement | Steps execute in order, no skipping |
| State Tracking | Progress tracked in output frontmatter via `stepsCompleted` |

**Step Processing Rules:**
1. Read complete step file before any action
2. Follow MANDATORY SEQUENCE exactly
3. Present menu and HALT — wait for user input
4. On Continue: update frontmatter, load next step
5. On Exit: save state, exit workflow

**Critical Rules:**
- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read entire step file before execution
- 🚫 NEVER skip steps or optimize sequence
- ⏸️ ALWAYS halt at menus and wait for user input
- 🚫 NEVER implement changes — document only

---

## Component Inventory

| Layer | Files | Purpose |
|-------|-------|---------|
| Entry Point | 1 | `.cursor/commands/bmad-rbtv-doc.md` |
| Agent | 1 | `_bmad/rbtv/agents/ana.md` |
| Config | Inherited | Uses `_bmad/core/config.yaml` |
| Compound Workflow | 6 | workflow.md + 4 steps + 1 template |
| Handoff Workflow | 8 | workflow.md + 4 steps + 3 templates |
| **Total** | **17** | Doc component files |

---

## References

| Reference | Path |
|-----------|------|
| Module config | `_bmad/core/config.yaml` |
| Command registry | `_bmad/rbtv/rbtv-manifest.csv` |
| BMAD Product Brief | `_bmad/bmm/workflows/1-analysis/create-product-brief/` |
| BMAD PRD | `_bmad/bmm/workflows/2-plan-workflows/create-prd/` |
| BMAD UX Design | `_bmad/bmm/workflows/2-plan-workflows/create-ux-design/` |
