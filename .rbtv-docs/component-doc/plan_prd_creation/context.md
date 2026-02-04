# Doc Component — Shaping Context

**Created:** 2026-02-02  
**Source:** Shaping conversation with domcobb agent  
**Purpose:** Provide all context for agents executing the doc component PRD plan

---

## Overview

This document captures all decisions, directions, and context from the shaping conversation. Every agent executing a task in the doc component PRD plan MUST read this document first.

---

## What We're Building

A unified `/rbtv_doc` command that consolidates three existing documentation commands into a single component with mode-based routing, following BMAD's agentic architecture patterns.

### Commands Being Merged

| Current Command | Purpose | Fate in New System |
|-----------------|---------|-------------------|
| `/doc` | Creates product/architecture documentation from conversations | Becomes `product` mode |
| `/compound` | Standardizes learnings into system files (currently implements changes) | Becomes `learning` mode (document-only) |
| `/handoff` | Creates context transfer summaries for agent continuity | Becomes `handoff` mode |

### Additional Modes Identified

| Mode | Purpose |
|------|---------|
| `usecase` | Documents product use cases |
| `decision` | Captures plan decisions (shape.md pattern) — auto-triggered by `/plan`, out of scope for now |

---

## Architecture Decisions

### BMAD Pattern Adoption

| Pattern | Adopt? | Notes |
|---------|--------|-------|
| Workflow.md with mode routing | Yes | Master orchestrator for `/rbtv_doc` |
| Step-file architecture | Yes | Each mode has sequential step files |
| Tri-modal workflows (Create/Validate/Edit) | Yes | Each mode supports all three lifecycle states |
| Agent persona structure | TBD | Architecture phase determines if needed |
| Config.yaml pattern | TBD | Architecture phase determines if needed |
| Registry/manifest CSVs | TBD | Architecture phase determines if needed |

### Directory Structure

**Core principle:** `.cursor/` contains only thin loaders for native Cursor features. All logic lives in `_rbtv/`.

**Terminology:**
- **Components:** doc, plan, etc. — organizational units in `_rbtv/work/`

**Proposed structure:**

```
.cursor/
├── commands/
│   └── rbtv_doc.md              # Thin loader → _rbtv/work/doc/
├── plans/
│   └── plan_prd_creation/   # This plan's artifacts
└── ...

_rbtv/
└── work/
    └── doc/                     # Doc component
        ├── agent.md             # Master orchestrator (persona + mode routing)
        ├── config.yaml          # Component-level config
        ├── product/             # Product documentation workflow (on hold)
        ├── handoff/             # Handoff workflow (on hold)
        └── compound/            # Compound workflow (focus)
            ├── workflow.md
            ├── steps-c/
            ├── steps-v/
            ├── steps-e/
            └── templates/
```

**Note:** Structure determined in PRD based on BMAD component pattern analysis.

### Thin Loader Pattern

`.cursor/commands/rbtv_doc.md` will be a thin loader that:
1. Accepts optional mode argument
2. Loads the master orchestrator agent from `_rbtv/work/doc/agent.md`
3. Passes mode argument (or triggers menu if none)

---

## Mode Behavior Decisions

### Mode Invocation

| Scenario | Behavior |
|----------|----------|
| `/rbtv_doc product` | Routes directly to product mode workflow |
| `/rbtv_doc handoff` | Routes directly to handoff mode workflow |
| `/rbtv_doc` (no argument) | Presents menu for user to select mode |

### Learnings Mode Specifics

**Critical decision:** Learnings mode documents only — it does NOT implement changes.

| Current Compound Behavior | New Learnings Mode Behavior |
|---------------------------|----------------------------|
| Captures learning | Captures learning |
| Proposes location | Documents proposed location |
| Asks implementation questions | Documents implementation considerations |
| Implements change | **Does NOT implement** — creates backlog PRD |
| Flags related files | Documents related files in PRD |

**Rationale:** Creates a backlog of improvement PRDs that can be evaluated and prioritized before implementation. Separates identification from execution.

### Plan Decisions Mode

**Status:** Out of scope for initial PRD

This mode will be auto-triggered when `/plan` completes, capturing shaping decisions in a `shape.md` file. Integration with plan component will be designed separately.

---

## Workflow Architecture Decisions

### Tri-Modal Pattern

Each mode workflow supports three sub-modes:

| Sub-Mode | Purpose | Step Directory |
|----------|---------|----------------|
| Create | Build new documentation from scratch | `steps-c/` |
| Validate | Audit existing documentation for quality | `steps-v/` |
| Edit | Modify sections of existing documentation | `steps-e/` |

### State Persistence

Following BMAD pattern, workflow state lives in output document frontmatter:

```yaml
---
stepsCompleted: [step-01-init.md, step-02-discovery.md]
inputDocuments: [referenced-file.md]
workflowType: 'product'
mode: 'create'
date: '2026-02-02'
---
```

This enables resumable workflows across sessions.

### Subagent Usage

**Decision:** Subagents will be used for internal research before documentation.

**Details deferred:** Specific subagent integration will be designed when mode workflows are specified. Initial focus is on core documentation flow without subagent complexity.

---

## Constraints

| Constraint | Description |
|------------|-------------|
| Additive only | New component in `_rbtv/work/doc/`; existing robotville structure unchanged |
| Command name | Use `/rbtv_doc` during development to avoid conflicts |
| No auto-triggers | All modes are manual triggers (except future plan decisions mode) |
| PRD first | This plan creates a PRD specification, not implementation |

---

## Scope Boundaries

### In Scope

- PRD for unified `/rbtv_doc` command
- Mode taxonomy and behavior specifications
- Workflow architecture (master + per-mode)
- Step-file specifications
- Output document templates
- Entry point command specification

### Out of Scope

- Plan decisions mode (auto-trigger from `/plan`)
- Subagent implementation details
- Migration of existing ai_pro/founder to component structure
- Implementation of the component (separate plan after PRD)

---

## Reference Documents

| Document | Path | Purpose |
|----------|------|---------|
| BMAD Architecture | `docs/to_dos/bmad_benchmark/02-agentic-system-architecture.md` | Architecture patterns reference |
| BMAD Component Patterns | `docs/to_dos/bmad_benchmark/03-component-patterns-and-templates.md` | Templates for workflows, steps, etc. |
| Current doc command | `.cursor/commands/doc.md` | Absorb into product mode |
| Current compound command | `.cursor/commands/compound.md` | Absorb into learning mode |
| Current handoff command | `.cursor/commands/handoff.md` | Absorb into handoff mode |
| Compound improvements research | `docs/to_dos/compound-engineering-v2/todo-benchmark-everys-compound-engineering.md` | Planned improvements for compound/learning |
| Product documentation rule | `.cursor/rules/documentation/product-documentation.mdc` | Output folder standards |

---

## Open Questions (Resolved in PRD)

1. **Directory structure:** Resolved — `_rbtv/work/doc/` with agent.md orchestrator and mode subdirectories
2. **Config.yaml:** Resolved — Yes, component-level config.yaml for output paths and language settings
3. **Registries:** Resolved — No manifest CSVs needed; 3 modes don't require registry overhead
4. **Agent persona:** Resolved — Yes, agent.md with "Archivist" persona provides consistent character
5. **Mode taxonomy:** Resolved — product/handoff/compound (usecase absorbed into product mode)

---

## Glossary

| Term | Definition |
|------|------------|
| Component | Organizational unit in `_rbtv/work/` (doc, plan, etc.) |
| Mode | A documentation type within the `/rbtv_doc` command |
| Thin loader | A `.cursor/` file that only loads and delegates to `_rbtv/` files |
| Tri-modal | BMAD pattern where one workflow handles Create, Validate, and Edit |

---

*Last updated: 2026-02-03*
