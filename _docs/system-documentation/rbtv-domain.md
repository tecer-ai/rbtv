# Domain Model Specification: Robotville

**Purpose:** Canonical reference for Robotville's domain logic, terminology, and constraints. Use as the Source of Truth for development decisions.

---

## Table of Contents

1. [Domain Synopsis](#1-domain-synopsis)
2. [Domain Glossary](#2-domain-glossary)
3. [Variables and Value Sets](#3-variables-and-value-sets)
4. [Constraints](#4-constraints)
5. [Assumptions](#5-assumptions)

---

## 1. Domain Synopsis

Robotville is a **business-side structure layer** for AI-assisted entrepreneurship. It provides the structured thinking framework that happens *before* development—transforming vague ideas into validated concepts through guided questioning, structured planning, and milestone-based project evolution.

### In-Bounds (What Robotville Does)

| Category | Scope |
|----------|-------|
| **Problem structuring** | Transforms vague problems into structured solutions through iterative Socratic questioning |
| **Innovation guidance** | Guides users through business strategy, problem definition, and concept validation |
| **Planning infrastructure** | Creates and manages structured execution plans with quality gates, checkpoints, and condensation |
| **Quality assurance** | Independent evaluation of work outputs before human review via Judge sub-agent |
| **Context management** | Optimizes AI model context through use-case-based maps, handoffs, and zero-context plan design |
| **Founder lifecycle** | Six-milestone journey from napkin sketch (M1) to validated MVP (M6) |
| **User personalization** | Creates and maintains user profiles that adapt agent behavior to individual preferences |
| **Document generation** | Templates, frameworks, and structured outputs for business documentation |
| **Browser automation** | Playwright-based web navigation, screenshot capture, and content extraction |
| **Design extraction** | Visual design token extraction from websites and images |
| **Institutional memory** | Compound learnings that standardize corrections and patterns into system files |

### Out-of-Bounds (What Robotville Does NOT Do)

| Category | Boundary |
|----------|----------|
| **Code generation** | Does not write application code; defers to execution tools (Cursor, Claude Code, Lovable) |
| **Development frameworks** | Does not replace BMAD or similar dev-phase frameworks; designed to precede them |
| **Decision-making** | Does not make decisions for users; asks questions so users make better decisions |
| **Runtime execution** | No runtime components; operates entirely as static files interpreted by AI agents |
| **Project management** | Does not track timelines, sprints, or resource allocation; focuses on conceptual structure |
| **Technical architecture** | Does not define system architecture, APIs, or infrastructure; that belongs to development phase |
| **Production deployment** | Does not handle CI/CD, hosting, or operational concerns |

### Boundary Principle

Robotville occupies the **pre-development layer**:

```
[Vague Idea] → [Robotville: Structure & Validate] → [BMAD: Plan Development] → [Cursor/Lovable: Execute]
```

The system amplifies human thinking rather than replacing it. Users remain in the driver's seat; Robotville ensures they don't miss the turns.

---

## 2. Domain Glossary

Ubiquitous language definitions. Use these terms consistently across all documentation, agents, and user communication.

### Core Entities

| Term | Definition | Aliases (Avoid) |
|------|------------|-----------------|
| **Agent** | AI personality with specific skills that guides users through complex tasks via iterative interaction | Bot, Assistant, Persona |
| **Command** | Workflow automation invoked with `/command_name` syntax; executes structured tasks with predictable outputs | Macro, Script, Action |
| **Skill** | Specialized knowledge package in `.cursor/skills/` that auto-applies when context matches; teaches agents reusable workflows | Capability, Module, Plugin |
| **Rule** | Behavioral standard stored in `.cursor/rules/`; automatically applied based on file context or triggers | Guideline, Policy, Setting |
| **Plan** | Structured execution document with phases, tasks, checkpoints, and condensation points; zero-context design | Roadmap, Checklist, Sprint |
| **Milestone** | Major project stage in the Founder Module (M1-M6); represents significant conceptual progress | Phase, Stage, Sprint |
| **Framework** | Process documentation and knowledge base for applying business strategy concepts | Methodology, Template, Pattern |
| **Template** | Document skeleton with placeholders for content generation; used to create consistent outputs | Boilerplate, Scaffold, Blueprint |
| **Map** | Navigation document that routes agents to relevant resources; use-case-based discovery | Index, Directory, Registry |
| **Handoff** | Context transfer document capturing decisions, rationale, and state for fresh agent execution | Summary, Notes, Briefing |

### Agents

| Agent | Domain Role |
|-------|-------------|
| **domcobb** | Problem structurer; transforms vague problems into structured solutions via 4-act Socratic process |
| **mentor** | Founder guide; leads users through 6 milestones from conception to MVP |
| **onboarder** | Profile creator; captures user preferences and generates personalized rules |
| **lavoisier** | Design extractor; creates design briefs and layout specifications (M4 phase) |

### Sub-Agents

| Agent | Domain Role |
|-------|-------------|
| **judge** | Quality evaluator; independent assessment of work outputs before human review |

### Skills

| Skill | Domain Role |
|-------|-------------|
| **plan-workflow** | Plan creation and execution protocols |
| **compound-learnings** | Standardizes corrections and patterns into system files |
| **multiple-responses** | Generates diverse response alternatives when explicitly requested |
| **web-research** | Enforces research data integrity and source evaluation standards |
| **playwright-browser-automation** | Web navigation and screenshot capture via Playwright MCP |
| **mermaid-conversion** | Converts Mermaid diagrams to PNG images |
| **tone-extraction** | Extracts writing voice signatures from text |
| **visual-design-extraction** | Extracts design tokens from website screenshots |

### Founder Module Milestones

| ID | Name | Domain Definition |
|----|------|-------------------|
| **M1** | Conception | Structure raw idea into comprehensive business concept |
| **M2** | Validation | Validate technical and financial feasibility |
| **M3** | Brand | Create preliminary brand identity and guidelines |
| **M4** | Prototypation | Build working HTML prototype for friends-and-family testing |
| **M5** | Market Validation | Validate market demand and pricing through real feedback |
| **M6** | MVP | Create minimum viable product usable by real clients |

### Plan Components

| Term | Definition |
|------|------------|
| **Phase** | Logical grouping of related tasks within a plan; labeled P1, P2, P3... |
| **Task** | Single actionable unit within a plan; identified by `p[phase]-[number]` format |
| **Checkpoint** | Mandatory review point at phase boundaries; requires human or Judge approval |
| **Condensation** | Process of extracting key decisions and patterns from execution into reusable artifacts |
| **Execution Decision** | Record of choices made during task execution; stored in `[task_id]_execution_decisions.md` |

### Workflow Concepts

| Term | Definition |
|------|------------|
| **Zero-Context Design** | Plans and handoffs are self-contained; any agent with no prior knowledge can execute |
| **Human-in-the-Loop** | Users set direction and approve checkpoints; AI executes and proposes |
| **Compound Engineering** | Planning-heavy, execution-light development; humans think, AI implements, humans validate |
| **Vibe Coding** | Approach where ideas translate to working software through structured AI collaboration |
| **Quality Gate** | Mandatory evaluation point where work must meet criteria before proceeding |

---

## 3. Variables and Value Sets

Data points the system tracks, with their domains (valid value types/ranges).

### User Profile Variables

| Variable | Domain | Description |
|----------|--------|-------------|
| `user.name` | String (1-100 chars) | User's display name |
| `user.role` | Enum: `founder`, `developer`, `designer`, `business`, `hybrid` | Primary professional role |
| `user.experience_level` | Enum: `beginner`, `intermediate`, `advanced`, `expert` | AI/Cursor proficiency |
| `user.communication_style` | Enum: `concise`, `detailed`, `technical`, `conversational` | Preferred interaction style |
| `user.language` | ISO 639-1 code (e.g., `en`, `pt-br`) | Primary language |
| `user.timezone` | IANA timezone (e.g., `America/Sao_Paulo`) | User's local timezone |
| `user.preferences.rule_mode` | Enum: `minimal`, `standard`, `comprehensive` | Level of personalization |

### Plan Variables

| Variable | Domain | Description |
|----------|--------|-------------|
| `plan.id` | String: `[name]-[hash].plan.md` | Unique plan identifier |
| `plan.status` | Enum: `draft`, `active`, `paused`, `completed`, `abandoned` | Current plan state |
| `plan.phase_count` | Integer: 1-10 | Number of phases in plan |
| `plan.task_count` | Integer: 1-50 | Total tasks across all phases |
| `task.id` | String: `p[1-9]-[1-99]` | Task identifier format |
| `task.status` | Enum: `pending`, `in_progress`, `blocked`, `completed`, `skipped` | Task execution state |
| `task.verdict` | Enum: `approved`, `revision_needed`, `rejected` | Judge evaluation result |
| `checkpoint.status` | Enum: `pending`, `passed`, `failed` | Checkpoint gate state |

### Milestone Variables

| Variable | Domain | Description |
|----------|--------|-------------|
| `milestone.id` | Enum: `M1`, `M2`, `M3`, `M4`, `M5`, `M6` | Milestone identifier |
| `milestone.status` | Enum: `not_started`, `in_progress`, `completed`, `blocked` | Milestone state |
| `milestone.duration_estimate` | String: `[1-4]+ weeks` | Expected duration range |
| `project.name` | String: lowercase, snake_case, 3-50 chars | Project identifier |
| `project.current_milestone` | Enum: `M1`-`M6` | Active milestone |

### Agent Variables

| Variable | Domain | Description |
|----------|--------|-------------|
| `agent.name` | String: lowercase, 3-20 chars | Agent identifier |
| `agent.verbosity` | Integer: 1-10 | Output detail level (trait) |
| `agent.act` | Integer: 1-4 (domcobb-specific) | Current act in Socratic process |
| `agent.identity_adopted` | Boolean | Whether agent persona is active |

### Document Variables

| Variable | Domain | Description |
|----------|--------|-------------|
| `document.type` | Enum: `template`, `framework`, `output`, `plan`, `handoff` | Document category |
| `document.last_updated` | Date: `YYYY-MM-DD` | Last modification date |
| `document.path` | String: valid filesystem path | Document location |

---

## 4. Constraints

Logical rules and invariants the system must enforce.

### Agent Constraints

| ID | Constraint | Enforcement |
|----|------------|-------------|
| **A1** | Agent identity must be adopted immediately upon @mention invocation | Agent reads identity section, speaks in first person |
| **A2** | Agent must follow defined process in full (Acts, Steps, Checkpoints) | Cannot skip steps even if request seems simple |
| **A3** | Only one agent identity active per conversation | Cannot blend multiple agent personas |
| **A4** | Agent must operate within defined scope boundaries | Out-of-scope requests deferred with explanation |
| **A5** | Agent cannot make decisions for users | Must ask questions; users decide |

### Plan Constraints

| ID | Constraint | Enforcement |
|----|------------|-------------|
| **P1** | Task ID format must be `p[phase]-[number]` | Validation on plan creation |
| **P2** | Tasks must be sequentially numbered within phase (no gaps) | Renumber if inserting |
| **P3** | Checkpoint required at every phase boundary | Plan validation fails without checkpoints |
| **P4** | Plans must be zero-context (self-contained) | No "as discussed" or external references |
| **P5** | Condensation task required for phases with 3+ tasks | Automatic insertion |
| **P6** | Judge must evaluate before marking task complete | Three-step execution protocol |
| **P7** | Execution decisions must be written after task completion | `[task_id]_execution_decisions.md` created |

### Milestone Constraints

| ID | Constraint | Enforcement |
|----|------------|-------------|
| **M1** | Milestones must be completed in order (M1 → M2 → ... → M6) | Cannot start M3 before M2 complete |
| **M2** | Each milestone must produce defined deliverables | Milestone checklist validation |
| **M3** | Milestone status cannot regress (completed → in_progress) | Status transitions are forward-only |

### Document Constraints

| ID | Constraint | Enforcement |
|----|------------|-------------|
| **D1** | All file names must be in English, snake_case | Naming validation |
| **D2** | All document content must be in English | Language rule |
| **D3** | File references must use markdown links with full relative paths | `[name.md](path/to/name.md)` format |
| **D4** | Documents must include `Last updated: YYYY-MM-DD` footer | Footer validation |
| **D5** | Headings must use Title Case | Formatting rule |

### Quality Constraints

| ID | Constraint | Enforcement |
|----|------------|-------------|
| **Q1** | Work output must pass Judge evaluation before human review | Quality gate |
| **Q2** | Pre-completion checklist must be satisfied | Coverage, Consistency, Safety, Quality, Next Steps |
| **Q3** | Root cause must be addressed, not symptoms | Reasoning rule |
| **Q4** | Critical feedback must be delivered directly | No sycophantic agreement |

### Git Constraints

| ID | Constraint | Enforcement |
|----|------------|-------------|
| **G1** | File renames must use `git mv` only | Forbidden: `Rename-Item`, `Move-Item`, `mv` |
| **G2** | No `&&` for command chaining (PowerShell 5.1) | Use `;` or separate lines |
| **G3** | Destructive commands require explicit user approval | `--force`, `--hard`, `--no-verify` blocked |

---

## 5. Assumptions

Technical and operational presets taken for granted.

### Platform Assumptions

| ID | Assumption | Implication |
|----|------------|-------------|
| **T1** | Primary platform is Cursor IDE | Commands, rules, and skills use Cursor conventions |
| **T2** | User operates on Windows (PowerShell 5.1) | No `&&` chaining; use `;` or separate commands |
| **T3** | AI models support 15+ minute context windows | Wave 3 (Workflows Era) capability |
| **T4** | MCP (Model Context Protocol) is available | Playwright MCP for browser automation |
| **T5** | Git is installed and repositories are version-controlled | All file operations assume git context |

### Architecture Assumptions

| ID | Assumption | Implication |
|----|------------|-------------|
| **A1** | Brownfield installation model | Parent container holds Robotville + project repos |
| **A2** | `.cursor/` is synced from Robotville to parent | Single configuration across all projects via sync scripts |
| **A3** | User preferences are preserved during updates | `user_profile.json` gitignored; `user_preferences/` folder created by onboarder |
| **A4** | Each project maintains independent git repository | No monorepo assumption |
| **A5** | System documents are AI agent instructions | Clarity and brevity prioritized over human readability |

### Workflow Assumptions

| ID | Assumption | Implication |
|----|------------|-------------|
| **W1** | Users follow human-in-the-loop pattern | AI proposes, human approves, AI executes |
| **W2** | Compound engineering approach preferred | Planning-heavy, execution-light development |
| **W3** | Zero-context design for all plans/handoffs | Fresh agents can execute without prior conversation |
| **W4** | Quality gates are mandatory, not optional | Judge evaluation before completion |
| **W5** | Agents adopt identity completely when invoked | No partial or blended personas |
| **W6** | Map files provide use-case-based routing | Agents load only relevant maps to minimize context |

### Business Context Assumptions

| ID | Assumption | Implication |
|----|------------|-------------|
| **B1** | Target user has business background (not technical) | Innovation structure over development efficiency |
| **B2** | Projects aim for 1-5 person viable businesses | Optimized for small team, high-margin operations |
| **B3** | Brazil is primary market for initial validation | Pix, WhatsApp, local e-commerce considered |
| **B4** | BMAD handles development phase | Robotville stops at validated concept/MVP spec |
| **B5** | Founder module spans weeks, not hours | Deep work, not quick tasks |

### Integration Assumptions

| ID | Assumption | Implication |
|----|------------|-------------|
| **I1** | Robotville precedes BMAD in project lifecycle | Handoff occurs at development phase boundary |
| **I2** | Execution tools (Cursor, Claude Code, Lovable) are downstream | Robotville outputs feed into these tools |
| **I3** | Platform-agnostic core files | Agents, templates, frameworks portable across AI platforms |
| **I4** | Skills auto-apply based on context matching | No explicit invocation required |
| **I5** | Rules apply based on file type and triggers | Automatic behavioral enforcement |

---

*Last updated: 2026-01-29*
