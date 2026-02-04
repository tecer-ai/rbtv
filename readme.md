# RBTV (Robotville)

RBTV is a BMAD module providing documentation, git workflow, and build components. It is the professionalized, BMAD-compliant version of [Robotville](../../robotville/readme.md).

**Migration status:** Ongoing. Founder mode and Onboarder are pending migration. Onboarder may be discontinued.

---

## Table of Contents

1. [Purpose](#purpose)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Entry Points](#entry-points)
5. [Migration Notes](#migration-notes)

---

## Purpose

RBTV brings Robotville's capabilities into BMAD's micro-file architecture:

- **Problem structuring** — Convert vague needs into structured solutions
- **Documentation workflows** — Compound learnings, context handoffs, product docs
- **Plan lifecycle** — Create and execute plans with quality gates
- **Git workflow** — Conventional commits with context-aware messages
- **Design tooling** — Token extraction, validation, Mermaid rendering
- **Prompting assistance** — Craft effective prompts using AI model knowledge

---

## Architecture

RBTV follows BMAD micro-file architecture principles:

| Principle | Description |
|-----------|-------------|
| Micro-file design | Each step is self-contained, under 200 lines |
| Just-in-time loading | Only current step in memory |
| Sequential enforcement | Steps execute in numbered order, no skipping |
| State tracking | Progress saved in output document frontmatter |

### Folder Structure

```
rbtv/
├── config.yaml              # Module configuration
├── rbtv-manifest.csv        # Component registry (commands, workflows, skills, tasks)
├── subagents-manifest.csv   # Subagent registry for Task tool
├── agents/                  # Agent personas
│   ├── ana.md               # Documentation Orchestrator
│   ├── component-creator.md           # BMAD Component Builder
│   └── domcobb.md           # Problem Architect & Prompting Expert
├── tasks/                   # Standalone procedures
│   ├── context-search.xml
│   ├── quality-evaluator.xml
│   ├── tone-extraction.xml
│   ├── web-research.xml
│   └── data/                # Task knowledge files
├── workflows/               # Multi-step processes
│   ├── doc-compound-learning/
│   ├── doc-context-handoff/
│   ├── plan-lifecycle/
│   ├── git-commit/
│   ├── browser-web-automation/
│   ├── design-qa-validation/
│   ├── design-token-extraction/
│   ├── diagram-mermaid-render/
│   ├── problem-structuring/
│   ├── prompting-assistance/
│   └── build-rbtv-component/
└── .rbtv-docs/              # Internal documentation and compounds
```

---

## Components

### Agents

| Agent | Command | Purpose |
|-------|---------|---------|
| **Ana** | `/bmad-rbtv-doc` | Documentation orchestrator — compound, handoff, product docs |
| **Builder** | `/bmad-rbtv-create` | Create BMAD components (agents, workflows, tasks) |
| **domcobb** | `/bmad-rbtv-domcobb` | Problem structuring and prompting assistance |

### Workflows

| Workflow | Domain | Output |
|----------|--------|--------|
| doc-compound-learning | Documentation | Backlog PRD for system improvements |
| doc-context-handoff | Documentation | Context summary for agent continuity |
| plan-lifecycle | Planning | Plan files (*.plan.md) + execution decisions |
| git-commit | Git | Conventional commit with context-aware message |
| browser-web-automation | Browser | Screenshots, page interactions |
| design-qa-validation | Design | Validation report (4-layer framework) |
| design-token-extraction | Design | Design tokens JSON + brief |
| diagram-mermaid-render | Diagrams | PNG images from Mermaid code |
| problem-structuring | Analysis | MECE-structured problem definition |
| prompting-assistance | Prompting | Crafted prompts for AI models |

### Tasks

| Task | Purpose |
|------|---------|
| context-search | Search files for knowledge relevant to conversation |
| quality-evaluator | Evaluate work against quality criteria |
| tone-extraction | Extract voice signature from text |
| web-research | Rigorous research with source evaluation |

### Subagents

| ID | Purpose |
|----|---------|
| judge | Quality gate evaluation after complex tasks |
| web-research | Factual research with source evaluation |
| context-search | Deep file analysis and knowledge extraction |

---

## Entry Points

### Commands

| Command | Agent | Usage |
|---------|-------|-------|
| `/bmad-rbtv-doc` | Ana | Documentation workflows |
| `/bmad-rbtv-doc compound` | Ana | Direct to compound mode |
| `/bmad-rbtv-doc handoff` | Ana | Direct to handoff mode |
| `/bmad-rbtv-doc product` | Ana | Product documentation submenu |
| `/bmad-rbtv-create` | Builder | Create BMAD components |
| `/bmad-rbtv-git` | — | Git commit workflow |
| `/bmad-rbtv-plan` | — | Create or execute plans |
| `/bmad-rbtv-domcobb` | domcobb | Problem structuring or prompting |

### Skills (Auto-Apply)

Skills are thin loaders that auto-apply when context matches:

| Skill | Triggers On |
|-------|-------------|
| web-research | Research tasks, factual queries |
| design-validation | HTML design review, visual QA |
| visual-design-extraction | Design system analysis |
| tone-extraction | Voice analysis, style matching |
| mermaid-conversion | Mermaid diagram conversion |
| playwright-browser-automation | Browser automation tasks |

---

## Migration Notes

RBTV migrates Robotville capabilities to BMAD standards. Key differences:

| Aspect | Robotville | RBTV |
|--------|------------|------|
| File architecture | Monolithic files | Micro-files (<200 lines) |
| Step handling | In-memory processing | Just-in-time loading |
| State tracking | Session-based | Frontmatter in output docs |
| Component registry | Map files | CSV manifests |
| Workflow structure | Process files | steps-c/, steps-x/, templates/ |

### Pending Migration

- **Founder mode** — 6-milestone framework for idea-to-MVP journey
- **Onboarder** — User profile creation (may be discontinued)

### Completed Migration

- domcobb (problem structuring + prompting)
- Plan workflow (creation + execution with quality gates)
- Documentation workflows (compound, handoff)
- Design tooling (validation, extraction, Mermaid)
- Git workflow
- Browser automation

---

## Configuration

Module configuration:

All settings inherited from `_bmad/core/config.yaml`:
- `user_name`
- `communication_language`
- `document_output_language`
- `output_folder`

> **Note:** 
> - Workflow-specific output paths defined in each workflow.md frontmatter
> - Build paths defined in component-creator.md agent frontmatter
