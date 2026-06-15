# Component Patterns

Reference data for the create-component workflow. Defines naming standards, size limits, required sections, and structural requirements for each component type.

## Naming Standard

| Component | Convention | Pattern | Examples |
|-----------|-----------|---------|----------|
| **Workflow folder** | Domain noun — what the area is about | `{domain-noun}/` | `documentation/`, `ai-consulting/`, `summarization/`, `business-innovation/` |
| **Skill** | Capability noun — what auto-discovery matches on | `{capability}/` | `planning/`, `commit/`, `design-extraction/`, `tone-extraction/` |
| **Command** | Role or domain noun — what the user invokes | `{role-or-domain}.md` | `mentor.md`, `designer.md`, `writing.md` |
| **Persona** | Character name | `{name}.md` | `vivian.md`, `paul.md`, `domcobb.md` |
| **Rule** | Behavior it enforces | `{behavior}.md` | `atomic-files.md`, `chat-discipline.md`, `reasoning.md` |

**Key rules:**
- Skills and commands that invoke the same workflow share the same base name.
- Never name a command or skill after a persona — the persona is loaded *by* the workflow.
- Workflow folders are named by what they produce or do, not who runs them.
- Related workflows group under a domain-named parent folder (e.g., `session-close/compound-learning/`, `session-close/context-handoff/`).
- Exception: `domcobb` command name is legacy, kept by design.

## Structural Layout

The repo is module-first: every component lives under its owning module folder (`core/`, `office/`, `studio/`, `orchestration/`, `models/`, `builder/`, `innovation/`, `writing/`, `caveman/`, `coding/`). Module membership is declared in `admin/install/module-manifest.json` and documented in `modules/{module}.md`. Inside each module, components are organized by type:

| Directory | Contains | Naming |
|-----------|----------|--------|
| `{module}/personas/` | Flat persona files — character sheets only | `{name}.md` |
| `{module}/workflows/` | All workflow logic — standalone or domain-grouped | `{domain}/` or `{domain}/{sub-workflow}/` |
| `{module}/skills/` | Thin loaders ONLY — zero logic, always delegates to a workflow or task | `{capability}/SKILL.md` |
| `{module}/commands/` | Thin loaders — one per skill (except skill-only components) | `{name}.md` |
| `{module}/tasks/` | Shared XML task specifications | `{name}.xml` |
| `{module}/rules/` | Behavior rules (copied to target on install) | `{behavior}.md` |
| `{module}/subagents/` | Claude Code dispatchable subagents | `{name}.md` |

**Content-named folders (beyond the type-folders).** A module MAY carry top-level
folders named by their CONTENT (not a component type), as siblings of the
type-folders above, in two cases:

1. Shared reference data consulted by multiple components (e.g. `standards/`).
   Single-owner data instead co-locates inside its owning component (a `data/`
   subfolder, per Co-located data).
2. A cohesive capability/procedure + its co-located data with no type-folder home —
   a runnable script + its usage doc, or a module-internal procedure + the
   reference data it consults.

No generic `knowledge/`/`data/` module bucket is introduced — each folder is named
for what it holds. The Thin Loader Invariant is unchanged: logic never lives in
`skills/`; these folders hold the logic/data that has no `skills/`, `workflows/`,
or XML-`tasks/` home.

## Rule Design Compliance

Rule files have additional design requirements beyond naming and sizing. Read `{rbtv_path}/builder/workflows/component-creation/data/rule-design-guide.md` for enforcement types, required design elements, anti-gaming design, and the rule template.

## Thin Loader Invariant

Skills and commands are ALWAYS thin loaders. No exceptions.

| Rule | Detail |
|------|--------|
| Skills | SKILL.md loads and delegates to a workflow, task, or agent. All logic lives in the target file. |
| Commands | Single LOAD instruction pointing to a workflow or agent. Zero logic. |
| Standalone capability | If a capability has no existing workflow/task to point to, create one first. The skill still delegates. |
| Co-located data | Data files may live alongside SKILL.md, but SKILL.md itself remains a thin loader. |
| MCP tools | Tool config files may live in the skill folder, but SKILL.md itself remains a thin loader. |

## RBTV Component Pattern Compliance

## Agent Files (`{module}/personas/*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 55-76 lines recommended, 100 max |
| Structure | XML-in-markdown with `<agent>` root tag |
| Required sections | `<activation>`, `<menu-handlers>`, `<rules>`, `<persona>`, `<menu>` |
| Config loading | No runtime config load; paths use `{rbtv_path}` resolved at install time |
| WAIT instruction | Menu must include explicit "WAIT for input" |
| Paths | All paths use `{rbtv_path}` variables, never relative (`../`) |
| Persona structure | `<role>`, `<identity>`, `<communication_style>`, `<principles>` |

**Exception — mandated multi-mode/multi-section personas:** The ~100-line soft-max does NOT apply to persona files mandated by an architecture spec to carry multiple self-contained audience or mode sections. For these, the budget scales with the number of mandated sections: the soft-max applies PER mode-section, not to the whole file. A reviewer finding such a persona over the whole-file soft-max MUST check whether the length is mandated-structural (architecture + decision record) before flagging it as a defect.

## Workflow Files (`{module}/workflows/*/workflow.md`)

| Rule | Requirement |
|------|-------------|
| Size | 60-80 lines recommended, 120 max |
| Required frontmatter | `name`, `description`, `nextStep` |
| Optional frontmatter | `outputFolder`, `editWorkflow` |
| Forbidden frontmatter | `workflow_path`, `thisStepFile`, `main_config`, `parentWorkflow`, `validateWorkflow` |
| Paths | Use `{rbtv_path}` and `runtime output resolution` placeholders — never absolute paths or hardcoded folders |

## Step Files (`{module}/workflows/*/steps-*/step-*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 80-200 lines recommended, 250 max |
| Required frontmatter | `name`, `description`, `nextStepFile` |
| Optional frontmatter | `outputFile`, `partyModeWorkflow`, `knowledgeFile` |
| Forbidden frontmatter | `workflow_path`, `thisStepFile` |
| Terminal steps | `nextStepFile: null` for final steps |
| HALT | Every step must end with menu + "HALT and WAIT" |

## Command Files (`{module}/commands/*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 10-15 lines ideal, 20 max |
| Pattern | Thin loader — zero logic |
| Required frontmatter | `name`, `description` |
| Content | Single LOAD instruction pointing to persona/workflow/task file |
| Paths | Use `{rbtv_path}` (not `@{rbtv_path}`) |

## Task Files (`{module}/tasks/*.xml`)

| Rule | Requirement |
|------|-------------|
| Size | 40-100 lines recommended, 150 max |
| Structure | XML with `<task>` root tag |
| Required sections | `<objective>`, `<llm>`, `<flow>` |
| Flow | Sequential `<step>` elements with `<substep>` children |

## Agent Handoff Block

Multi-agent workflows embed handoff instructions in step files at each agent boundary. The handoff block is the ONLY control-transfer mechanism between agents — the current agent NEVER loads a step owned by another agent.

**Format** — a blockquote inside the step's CRITICAL STEP COMPLETION NOTE, executed ONLY when the continuing menu option is selected:

```markdown
> **AGENT HANDOFF — {target agent or module}**
>
> {Next step or capability} is owned by **{agent name (persona)}** — not by the current agent. You cannot execute it yourself.
>
> Instruct the user:
>
> *"{What was just locked}. To continue, invoke the `{exact-invocation-as-installed}` {skill|command} ({persona name}) and select **[{menu key}] {menu item label}**. {What the next agent will do}."*
>
> Do NOT load {next step file} yourself. The {target agent} loads it.
```

**Required elements:**

| # | Element | Rule |
|---|---------|------|
| 1 | Header | Blockquote opening with `**AGENT HANDOFF — {target}**` |
| 2 | Exact invocation | The skill or command name AS INSTALLED in the target workspace (e.g., `rbtv-designing` skill, `rbtv-innovator` command) — NEVER a persona shorthand (`@designer`, `@mentor`) or a source-repo filename |
| 3 | Menu item | The exact menu key + label from the target agent's menu — verify it exists in `{module}/personas/{name}.md` before writing the block |
| 4 | Prohibition | Explicit "Do NOT load {next step} yourself" line — the receiving agent loads its own steps |

**Variants:**

| Variant | Shape | Live example |
|---------|-------|--------------|
| One-way | Agent A's final step ends in handoff; control never returns | `office/workflows/pitch/steps-c/step-06-structure.md` |
| Round-trip | Agent A → Agent B (one step) → back to Agent A; BOTH boundary steps carry a handoff block | `innovation/workflows/business-innovation/bi-m3/bi-m3-brandbook/` (steps 02 → 03 → 04) |
| Conditional re-handoff | Handoff text branches on detected state (e.g., deck exists vs not) | `office/workflows/pitch/steps-e/step-e01-narrative.md` |

Multi-agent workflow.md files MUST carry a routing table (step range → agent → exact invocation → responsibility) obeying the same invocation rule as element 2.

**Rename discipline:** renaming any skill or command MUST include a repo-wide sweep of handoff blocks and routing tables for the old invocation name. Stale invocations are the defect class this pattern exists to prevent.

## Common Violations

| Violation | Fix |
|-----------|-----|
| Relative paths in agents (`../workflows/`) | Use `{rbtv_path}/{module}/workflows/` |
| `@{rbtv_path}` prefix in commands | Remove `@` prefix |
| Logic in command files | Extract to task/agent file, make command a thin loader |
| Fat skill with inline logic | Create a backing task or workflow file, make skill a thin loader |
| Agent exceeds 100 lines | Externalize protocols/actions to data files |
| Hardcoded catalog lists | Reference manifests (`tools-manifest.csv`) |
| Stale handoff invocation (`@designer`, `@mentor`) | Use the exact installed skill/command name; sweep handoff blocks and routing tables on every rename (see Agent Handoff Block) |
