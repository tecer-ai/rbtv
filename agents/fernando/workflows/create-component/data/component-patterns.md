# Component Patterns

Reference data for the create-component workflow. Defines size limits, required sections, and structural requirements for each component type (agent, skill, workflow, step, task, rule).

## RBTV Component Pattern Compliance

## Agent Files (`agents/*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 55-76 lines recommended, 100 max |
| Structure | XML-in-markdown with `<agent>` root tag |
| Required sections | `<activation>`, `<menu-handlers>`, `<rules>`, `<persona>`, `<menu>` |
| Config loading | Activation must load `{project-root}/_bmad/rbtv/_config/config.yaml` |
| WAIT instruction | Menu must include explicit "WAIT for input" |
| Paths | All paths use `{project-root}` variables, never relative (`../`) |
| Persona structure | `<role>`, `<identity>`, `<communication_style>`, `<principles>` |

## Workflow Files (`workflows/*/workflow.md`)

| Rule | Requirement |
|------|-------------|
| Size | 60-80 lines recommended, 120 max |
| Required frontmatter | `name`, `description`, `nextStep` |
| Config frontmatter | **MUST** declare `main_config: '{project-root}/_bmad/rbtv/_config/config.yaml'` if the workflow uses config — frontmatter ONLY, never body text |
| Optional frontmatter | `parentWorkflow`, `outputFolder`, `validateWorkflow`, `editWorkflow` |
| Forbidden frontmatter | `workflow_path`, `thisStepFile` |
| Cross-module paths | Use `{bmad_core}`, `{bmad_bmm}`, `{bmad_rbtv}`, `{bmad_output}` variables — never `{project-root}/_bmad/core/` etc. directly |

## Step Files (`workflows/*/steps-*/step-*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 80-200 lines recommended, 250 max |
| Required frontmatter | `name`, `description`, `nextStepFile` |
| Optional frontmatter | `outputFile`, `partyModeWorkflow`, `knowledgeFile` |
| Forbidden frontmatter | `workflow_path`, `thisStepFile` |
| Terminal steps | `nextStepFile: null` for final steps |
| HALT | Every step must end with menu + "HALT and WAIT" |

## IDE Command Files (`_config/claude/commands/*.md`)

| Rule | Requirement |
|------|-------------|
| Size | 10-15 lines ideal, 20 max |
| Pattern | Thin loader — zero logic |
| Required frontmatter | `name`, `description` |
| Content | Single LOAD instruction pointing to agent/workflow/task file |
| Paths | Use `{project-root}` (not `@{project-root}`) |

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
| Relative paths in agents (`../workflows/`) | Use `{project-root}/_bmad/rbtv/workflows/` |
| `@{project-root}` prefix in commands | Remove `@` prefix |
| Logic in command files | Extract to task/agent file, make command a thin loader |
| Agent exceeds 100 lines | Externalize protocols/actions to data files |
| Hardcoded catalog lists | Reference manifests (`tools-manifest.csv`) |
