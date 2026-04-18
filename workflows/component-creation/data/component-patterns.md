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

| Directory | Contains | Naming |
|-----------|----------|--------|
| `personas/` | Flat persona files — character sheets only | `{name}.md` |
| `workflows/` | All workflow logic — standalone or domain-grouped | `{domain}/` or `{domain}/{sub-workflow}/` |
| `skills/` | Thin loaders ONLY — zero logic, always delegates to a workflow or task | `{capability}/SKILL.md` |
| `commands/` | Thin loaders — one per skill (except skill-only components) | `{name}.md` |
| `tasks/` | Shared XML task specifications | `{name}.xml` |
| `rules/` | Behavior rules (copied to target on install) | `{behavior}.md` |
| `subagents/` | Claude Code dispatchable subagents | `{name}.md` |

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

## Agent Files (`personas/*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 55-76 lines recommended, 100 max |
| Structure | XML-in-markdown with `<agent>` root tag |
| Required sections | `<activation>`, `<menu-handlers>`, `<rules>`, `<persona>`, `<menu>` |
| Config loading | No runtime config load; paths use `{rbtv_path}` resolved at install time |
| WAIT instruction | Menu must include explicit "WAIT for input" |
| Paths | All paths use `{rbtv_path}` variables, never relative (`../`) |
| Persona structure | `<role>`, `<identity>`, `<communication_style>`, `<principles>` |

## Workflow Files (`workflows/*/workflow.md`)

| Rule | Requirement |
|------|-------------|
| Size | 60-80 lines recommended, 120 max |
| Required frontmatter | `name`, `description`, `nextStep` |
| Optional frontmatter | `outputFolder`, `editWorkflow` |
| Forbidden frontmatter | `workflow_path`, `thisStepFile`, `main_config`, `parentWorkflow`, `validateWorkflow` |
| Paths | Use `{rbtv_path}` and `runtime output resolution` placeholders — never absolute paths or hardcoded folders |

## Step Files (`workflows/*/steps-*/step-*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 80-200 lines recommended, 250 max |
| Required frontmatter | `name`, `description`, `nextStepFile` |
| Optional frontmatter | `outputFile`, `partyModeWorkflow`, `knowledgeFile` |
| Forbidden frontmatter | `workflow_path`, `thisStepFile` |
| Terminal steps | `nextStepFile: null` for final steps |
| HALT | Every step must end with menu + "HALT and WAIT" |

## Command Files (`commands/*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 10-15 lines ideal, 20 max |
| Pattern | Thin loader — zero logic |
| Required frontmatter | `name`, `description` |
| Content | Single LOAD instruction pointing to persona/workflow/task file |
| Paths | Use `{rbtv_path}` (not `@{rbtv_path}`) |

## Task Files (`tasks/*.xml`)

| Rule | Requirement |
|------|-------------|
| Size | 40-100 lines recommended, 150 max |
| Structure | XML with `<task>` root tag |
| Required sections | `<objective>`, `<llm>`, `<flow>` |
| Flow | Sequential `<step>` elements with `<substep>` children |

## Common Violations

| Violation | Fix |
|-----------|-----|
| Relative paths in agents (`../workflows/`) | Use `{rbtv_path}/workflows/` |
| `@{rbtv_path}` prefix in commands | Remove `@` prefix |
| Logic in command files | Extract to task/agent file, make command a thin loader |
| Fat skill with inline logic | Create a backing task or workflow file, make skill a thin loader |
| Agent exceeds 100 lines | Externalize protocols/actions to data files |
| Hardcoded catalog lists | Reference manifests (`tools-manifest.csv`) |
