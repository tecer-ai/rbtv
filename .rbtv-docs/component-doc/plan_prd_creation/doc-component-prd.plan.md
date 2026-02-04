---
name: Doc Component PRD
overview: Create a PRD for the unified doc component that merges doc, compound, and handoff commands into a single `/rbtv_doc` command with BMAD-style workflow architecture.
todos:
  - id: p1-1
    content: |
      Create context document. This task creates `.cursor/plans/doc-component-v2/context.md` containing: all decisions from the shaping conversation with domcobb; mode definitions and their purposes; BMAD patterns to adopt; directory structure decisions; constraints and boundaries. This file will be referenced by every subsequent task.
    status: completed
  - id: p1-2
    content: |
      CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` to understand all decisions from the shaping conversation. Read `docs/to_dos/bmad_benchmark/agentic-system-study/02-agentic-system-architecture.md` for BMAD architecture patterns.
      
      GOAL: Write the Architecture section of the PRD defining the doc component's structure: directory layout for `system/doc/`, component hierarchy (command → workflow → steps → templates), thin loader pattern for `.cursor/` files, and mode routing mechanism.
      
      AGENT: Read `_bmad/rbtv/agents/builder.md` and embody the Builder agent. Understand the task, discuss doubts and alternatives with the user before executing, then write the Architecture section.
    status: completed
  - id: p1-condensation
    content: |
      CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project context. Read execution decision files for p1-1 and p1-2.
      
      GOAL: Condense p1-1 and p1-2 execution decisions into a single Phase 1 execution decisions file.
      
      AGENT: Read `_bmad/rbtv/agents/builder.md` and embody the Builder agent. Review both task decisions, merge into cohesive phase summary.
    status: completed
  - id: p1-checkpoint
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` and the PRD at `docs/to_dos/doc-component-v2/doc_component_prd.md` (Architecture section).
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Verify Phase 1 completion - context document exists and captures all shaping decisions; architecture section defines clear directory structure for the doc component; BMAD pattern adoption is explicit and justified. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
      
      Stop and wait for human approval before Phase 2.
    status: pending
  - id: p2-1
    content: |
      CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project decisions and `.cursor/plans/doc-component-v2/use_cases_context.md` for handoff patterns. Analyze existing commands: `.cursor/commands/doc.md`, `compound.md`, `handoff.md` to extract mode requirements.
      
      GOAL: Write the Modes section of the PRD defining mode taxonomy (product, handoff, learning, usecase), each mode's purpose/trigger/output, mode selection UX, and workflow mapping.
      
      AGENT: Read `_bmad/rbtv/agents/builder.md` and embody the Builder agent. Understand the task, discuss doubts and alternatives with the user before executing, then write the Modes section.
    status: completed
  - id: p2-2
    content: |
      CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project decisions and `.cursor/plans/doc-component-v2/use_cases_context.md` for handoff workflow patterns. Read `docs/to_dos/bmad_benchmark/agentic-system-study/03-component-patterns-and-templates.md` Section 2 for workflow templates.
      
      GOAL: Write the Workflows section of the PRD covering master orchestrator workflow (mode routing), per-mode tri-modal structure (Create, Validate, Edit), workflow.md template pattern, and state persistence.
      
      AGENT: Read `_bmad/rbtv/agents/builder.md` and embody the Builder agent. Understand the task, discuss doubts and alternatives with the user before executing, then write the Workflows section.
    status: completed
  - id: p2-3
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project decisions and directory structure.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Write the Components section of the PRD listing all files to be created: entry point `.cursor/commands/rbtv_doc.md`, system files in `system/doc/` structure, workflows, steps, templates, data files, and their dependencies. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p2-condensation
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project context. Read execution decision files for p2-1, p2-2, and p2-3.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Condense p2-1, p2-2, and p2-3 execution decisions into a single Phase 2 execution decisions file. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p2-checkpoint
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` and the PRD at `docs/to_dos/doc-component-v2/doc_component_prd.md` (Modes, Workflows, and Components sections).
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Verify Phase 2 completion - all modes defined with clear purposes; workflow structure follows BMAD patterns; component list is complete and organized. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
      
      Stop and wait for human approval before Phase 3.
    status: pending
  - id: p3-1
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project decisions. Read `docs/to_dos/bmad_benchmark/agentic-system-study/03-component-patterns-and-templates.md` Section 3 for step-file templates.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Write step-file specifications section in the PRD for each mode's workflow: step sequence (step-01 through step-N), each step's goal/mandatory sequence/menu options, and step frontmatter fields (nextStepFile, outputFile, etc.). PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p3-2
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project decisions and `.cursor/plans/doc-component-v2/use_cases_context.md` for handoff template structure (8 sections), handoff type distinctions, and use case documentation patterns.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Write the Templates section of the PRD defining output document templates for each mode: product documentation, handoff summary, learning/backlog PRD, and use case documentation. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p3-3
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project decisions and thin loader pattern.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Write the Entry Point section of the PRD specifying the `/rbtv_doc` command: command file structure (thin loader pattern), how it invokes the master orchestrator, argument parsing for mode selection, and menu fallback. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p3-condensation
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project context. Read execution decision files for p3-1, p3-2, and p3-3.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Condense p3-1, p3-2, and p3-3 execution decisions into a single Phase 3 execution decisions file. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p4-1
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project decisions. Read the complete PRD at `docs/to_dos/doc-component-v2/doc_component_prd.md`.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Review and validate the complete PRD for consistency with context decisions, BMAD pattern compliance, completeness (all modes/workflows/steps/templates), and zero-context principle (self-contained). PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p4-file-review
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` and the complete PRD at `docs/to_dos/doc-component-v2/doc_component_prd.md`.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Review and update all file references in the PRD and context document to ensure accuracy and consistency. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p4-final-condensation
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` for project context. Read all phase execution decision files (Phase 1, 2, 3, and individual task decisions).
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Condense all phase execution decisions into a single plan-level execution decisions file that captures the complete journey. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
    status: pending
  - id: p4-checkpoint
    content: |
      Follow the instructions:
      
      1) GAIN CONTEXT: Read `.cursor/plans/doc-component-v2/context.md` and the complete PRD at `docs/to_dos/doc-component-v2/doc_component_prd.md`.
      
      2) UNDERSTAND YOUR RULES: Read and follow `robotville/.cursor/rules/documentation/atomic-files.mdc`.
      
      3) UNDERSTAND YOUR GOAL: Final checkpoint - verify PRD is complete, all sections written, all decisions captured, and document is ready for human approval. PRD path: `docs/to_dos/doc-component-v2/doc_component_prd.md`
      
      4) EXECUTE: Read `_bmad/rbtv/agents/builder.md` and follow its instructions.
      
      5) VERIFY: Use the Task tool to invoke judge and have him verify your work.
      
      Stop and wait for human approval.
    status: pending
isProject: false
---

# Doc Component PRD Plan

Create a Product Requirements Document for the unified doc component that consolidates three existing commands (doc, compound, handoff) into a single `/rbtv_doc` command following BMAD's agentic architecture patterns.

---

## Context

### Problem

Three separate documentation commands exist with overlapping purposes:

- `/doc` — Creates product/architecture documentation from conversations
- `/compound` — Standardizes learnings into system files (implements changes)
- `/handoff` — Creates context transfer summaries for agent continuity

These should be unified into a coherent doc component following BMAD's proven patterns.

### Goals

1. Design a unified `/rbtv_doc` command with mode-based routing
2. Adopt BMAD's workflow architecture (agent, workflows, step-files, tri-modal pattern)
3. Structure `_rbtv/work/document/` as a component
4. Keep `.cursor/` minimal — thin loaders referencing `_rbtv/` files
5. Compound mode produces PRD-style backlog items (no implementation)

### Constraints

- Additive only — no deletion of existing `system/` structure (ai_pro, founder remain as modules)
- Command name: `/rbtv_doc` (to avoid conflicts during development)
- Modes are manual triggers; menu presented if user specifies none
- Plan decisions mode (automatic on `/plan` completion) is out of scope for now

### Key Decisions Made

| Decision | Rationale |

|----------|-----------|

| Master orchestrator as AGENT | Provides consistent character, menu-driven UX, BMAD-compliant structure |

| BMAD-style workflows for modes | Proven pattern for multi-mode document generation |

| Tri-modal workflows (Create, Validate, Edit) | Handles full lifecycle of documentation artifacts |

| Component structure in `_rbtv/work/document/` | Matches robotville's work component pattern |

| `.cursor/` as thin loaders only | Native Cursor features work; logic lives in `_rbtv/` |

| Single context file for plan execution | All decisions captured for agents executing tasks |

| Compound mode = document only | Creates backlog PRDs instead of implementing changes |

### Rejected Alternatives

| Alternative | Why Rejected |

|-------------|--------------|

| Separate skills per doc type | Loses unified experience, harder to maintain |

| Immediate migration of existing `system/` structure | Out of scope; this work is additive |

| Workflow-only orchestration (no agent) | Initially considered, but agent provides better UX with persona and consistent character |

---

## Files to Load

| Path | Purpose | When |

|------|---------|------|

| `.cursor/plans/doc-component-v2/context.md` | All decisions and context from shaping conversation | **Every task — FIRST action** |

| `docs/to_dos/bmad_benchmark/agentic-system-study/02-agentic-system-architecture.md` | BMAD architecture reference | Architecture definition phase |

| `docs/to_dos/bmad_benchmark/agentic-system-study/03-component-patterns-and-templates.md` | BMAD component templates | When creating workflows, steps, templates |

| `.cursor/commands/doc.md` | Current doc command to absorb | Mode design phase |

| `.cursor/commands/compound.md` | Current compound command to absorb | Mode design phase |

| `.cursor/commands/handoff.md` | Current handoff command to absorb | Mode design phase |

| `.cursor/rules/documentation/product-documentation.mdc` | Output folder standards | PRD writing phase |

| `.cursor/plans/doc-component-v2/use_cases_context.md` | Real-world handoff patterns, mode design inputs, template structures | Mode and template design (p2-1, p2-2, p3-2) |

---

## Workflow

```mermaid
flowchart TD
    subgraph p1 [Phase 1: Foundation]
        p1_1[Create context doc]
        p1_2[Define architecture]
        p1_1 --> p1_2
    end

    subgraph p2 [Phase 2: PRD Core]
        p2_1[Write modes section]
        p2_2[Write workflows section]
        p2_3[Write components section]
        p2_1 --> p2_2 --> p2_3
    end

    subgraph p3 [Phase 3: PRD Details]
        p3_1[Write step-file specs]
        p3_2[Write templates section]
        p3_3[Write entry point section]
        p3_1 --> p3_2 --> p3_3
    end

    subgraph p4 [Phase 4: Finalize]
        p4_1[Review and validate PRD]
        p4_2[Final checkpoint]
    end

    p1 --> CP1[P1 Checkpoint]
    CP1 --> p2
    p2 --> CP2[P2 Checkpoint]
    CP2 --> p3
    p3 --> p4
    p4 --> Done[PRD Complete]
```

---

## Phase 1: Foundation

**Goal:** Establish context document and architecture definition that guides all subsequent PRD sections.

Task details are in the YAML frontmatter above.

---

## Phase 2: PRD Core Sections

**Goal:** Define the modes, workflows, and component specifications in the PRD.

Task details are in the YAML frontmatter above.

---

## Phase 3: PRD Details

**Goal:** Specify step-files, templates, and entry point in detail.

Task details are in the YAML frontmatter above.

---

## Phase 4: Finalize

**Goal:** Review, validate, and complete the PRD.

Task details are in the YAML frontmatter above.

---

## Deliverables

| Deliverable | Location |

|-------------|----------|

| Context document | `.cursor/plans/doc-component-v2/context.md` |

| PRD | `docs/to_dos/doc-component-v2/doc_component_prd.md` |

| Execution decisions | `.cursor/plans/doc-component-v2/` |

---

## Notes

- PRD does not implement the component — it specifies what to build
- After PRD approval, a separate implementation plan will be created
- Learnings template may need research if BMAD's isn't directly applicable
- Terminology: plan, doc, etc. are "components"; ai_pro, founder are "modules" (until migration)