---
name: framework
description: "CONTAINS: rbtv source layout and routes to authoring guidance PURPOSE: create, edit, review and convert files using the guidance for their kind ALWAYS LOAD WHEN: authoring a skill, command, rule, agent, folder instructions, hook, MCP server, tool, module, component or another rbtv or .rbtv source; converting outside material to rbtv; discussing how to develop it DO NOT LOAD WHEN: using or installing existing material without changing its source"
---

Use this skill to create, edit, review or convert rbtv files. Read the mandatory pages below, then every conditional page that matches the work. Follow those pages for the method; this skill supplies the map and reading route.

## What rbtv provides

rbtv defines conventions for agent instructions and installs them for supported harnesses. The installer recognizes each kind by its source folder and filename. Authors edit the source; generated harness files are replaced from it.

Write shared components in the repository. Write installation-specific components in `.rbtv/mirror/`, with the same layout. A mirror component replaces the entire repository component with the same module and component names. Components do not belong in `.rbtv/config/`, `.rbtv/agents/`, `.rbtv/runtime/` or `.rbtv/memory/`.

A module is `<module>/` with `<module>.json`; a component is `<module>/<component>/` with `<component>.json`. Inside a component:

| Kind | Source |
|---|---|
| Skill, rule, command | `skills/<name>.md`, `rules/<name>.md`, `commands/<name>.md` |
| Agent | `agents/<name>/agent.md` and `agent.json` |
| Hook, MCP server, pack | `hooks/<name>.json`, `mcp-servers/<name>.json`, `packs/<name>.json` |
| Tool | `capabilities/tools/<name>/<name>.json` and its executable |
| Folder instructions | `folder-instructions/<name>.md` |
| Capability | Markdown under `capabilities/`; read from source, not installed |
| Glossary entry | `capabilities/glossary/<term>.md` in the owning component |
| rbtv principle | `core/rbtv/capabilities/principles/<name>.md` |

A self-contained skill folder with `SKILL.md` and supporting files is allowed only under `.rbtv/mirror/_skills/<name>/`. There is no repository `_skills/` folder and no source-folder index such as `capabilities.md`, `principles.md` or `glossary.md`.

A skill, command, rule or folder-instructions file routes to capabilities, not to another exposure method. Do not nest those installed forms inside one another.

## Read for this work

Apply the same routes in create, edit, review and convert modes; there is no separate page per mode. Read mandatory pages first. For conditional rows, match the work and honor the exclusion. If [Choosing what to build](../capabilities/choosing-what-to-build.md) settles a different kind from the request's wording, follow the settled kind's row too.

On create or conversion, start in the user's named module and component and use [Choosing where to build](../capabilities/choosing-where-to-build.md) to check its boundary. Object only for a boundary violation. Editing an existing file does not reopen placement.

If a required page is absent, report the missing path and stop that work. Do not substitute an older entry or build from this folder map alone. If no row covers the intended kind, ask for the missing definition rather than guessing.

Read these pages on every use, before the conditional readings:

- [Scaffolding language](../capabilities/glossary/scaffolding-language.md): Instructions understood on first reading.
- [Keep it stupidly simple](../capabilities/principles/keep-it-stupidly-simple.md): Remove unnecessary work and cognitive load.
- [Terminology is king](../capabilities/principles/terminology-is-king.md): Use one meaning consistently.
- [Single source of truth](../capabilities/principles/single-source-of-truth.md): Maintain each in one home.
- [Deterministic first](../capabilities/principles/deterministic-first.md): Use computed results for exact work.
- [Progressive disclosure](../capabilities/principles/progressive-disclosure.md): Supply each method when needed.
- [Agent parity](../capabilities/principles/agent-parity.md): Provide equivalent executable paths.

Then read every matching conditional page:

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN | DO NOT LOAD WHEN |
|---|---|---|---|---|
| [rbtv CLI](../capabilities/glossary/rbtv-cli.md) | Recognition, generation and refresh commands | Validate and deliver source changes | creating or converting a file; changing the installer; reviewing or editing scanned source | only changing an unscanned capability body without renaming or moving it |
| [Choosing what to build](../capabilities/choosing-what-to-build.md) | Choice of kind | Match the mechanism to the work | creating, reviewing or converting; editing when the current kind cannot support the required behavior | editing with the kind unchanged |
| [Choosing where to build](../capabilities/choosing-where-to-build.md) | Repository, mirror, module and component choice | Place work inside the right boundary | creating or converting | editing |
| [Nested exposure](../capabilities/nested-exposure.md) | Several capabilities under one exposure method | Group related methods without premature reading | one exposure method may route to multiple capabilities | only one capability is exposed |
| [Building from a conversation](../capabilities/building-from-a-conversation.md) | Extraction of settled reusable instructions | Preserve the corrected method | asked to build from a completed conversation | capture during an ongoing conversation |
| [Tips development](../capabilities/tips-development.md) | Capture of decisions and evidence during work | Preserve distinctions without starting another build | setting up or continuing capture during a conversation | extracting instructions after the conversation |
| [Writing a glossary entry](../capabilities/writing-a-glossary-entry.md) | Entry structure, ownership and verification | Define a term and teach its authoring | creating, editing or converting an entry, or introducing a term without one | no term entry is added or changed |
| [Writing a capability](../capabilities/writing-a-capability.md) | Writing routed methods and knowledge | Continue from the caller’s supplied context | creating, editing or converting a capability or procedure | writing a term definition |
| [Capability](../capabilities/glossary/capability.md) | Capability boundary and caller contract | Write the work that follows a route | the selected kind or named work is a capability | only writing an exposure method |
| [Cognitive unit](../capabilities/glossary/cognitive-unit.md) | Actionable instructions and their parts | Make instructions usable on another task | writing or changing instructions in a skill, rule, command, prompt or capability |  |
| [Routing table](../capabilities/glossary/routing-table.md) | Descriptions and file-selection rows | Select the right reading | writing or changing a description or routing table |  |
| [Entry point](../capabilities/glossary/entry-point.md) | Common body and conditional routes | Keep each reading focused | writing or changing the body or routes of a skill, command, rule or folder-instructions file |  |
| [Exposure method](../capabilities/glossary/exposure-method.md) | Who selects each installed form | Choose how content reaches the agent | choosing among skill, command, rule and folder instructions |  |
| [Prompt](../capabilities/glossary/prompt.md) | Standing instructions in agent.md | Define behavior across the agent’s tasks | writing or changing a prompt body | only agent configuration or one launch task changes |
| [Skill](../capabilities/glossary/skill.md) | Agent-selected task instructions | Open on the intended task | the selected kind or named work is a skill | only another kind is being changed |
| [Rule](../capabilities/glossary/rule.md) | Always-supplied instructions with action conditions | Act when the condition arises | the selected kind or named work is a rule | only another kind is being changed |
| [Command](../capabilities/glossary/command.md) | Human invocation and supplied inputs | Perform the requested action | the selected kind or named work is a command | only another kind is being changed |
| [Agent](../capabilities/glossary/agent.md) | Agent folder, record and placement | Launch the intended worker | the selected kind or named work is an agent or sub-agent | only another kind is being changed |
| [Folder instructions](../capabilities/glossary/folder-instructions.md) | Instructions supplied by folder location | Give each visit its required context | writing or changing folder instructions | instructions apply across all folders; use Rule |
| [Folder artifact](../capabilities/glossary/folder-artifact.md) | Records reached from folder instructions | Keep case-specific workspace information | writing or changing a folder artifact | writing the folder instructions themselves |
| [Module](../capabilities/glossary/module.md) | Component grouping and module boundary | Place components by subject | writing or changing a module | only a component changes |
| [Component](../capabilities/glossary/component.md) | Source grouping and component boundary | Keep related files together | writing or changing a component | only a file inside an unchanged component changes |
| [MCP server](../capabilities/glossary/mcp-server.md) | Server connection and credential references | Expose the intended server actions | writing or changing an MCP server record | only a tool or hook changes |
| [Hook](../capabilities/glossary/hook.md) | Event, matching and command outcome | Run and enforce at the intended event | writing or changing a hook | only a server or tool changes |
| [Tool](../capabilities/glossary/tool.md) | Program interface and executable record | Return usable results during a task | writing or changing a tool | only prose instructions change |
| [Pack](../capabilities/glossary/pack.md) | Shared installation selection | Install one group for several targets | writing or changing a pack, or sharing a selection across targets | only one target needs the selection |
| [Task](../capabilities/glossary/task.md) | One launch’s inputs, scope and completion | Give a worker bounded work | writing or changing launch text or a task file | changing the standing prompt |
| [Harness](../capabilities/glossary/harness.md) | Delivery differences between supported applications | Avoid assuming identical loading behavior | stating what an agent receives or supporting multiple harnesses |  |
| [Schema](../capabilities/glossary/schema.md) | Validator constraints and actual callers | Enforce the record’s contract | writing or changing a schema or adding a record field | only filling an existing record |
| [Template](../capabilities/glossary/template.md) | Layout and placeholders | Fill the required structure | writing or filling a page’s template |  |
| [Principle](../capabilities/glossary/principle.md) | Cross-kind design tests | Settle recurring design choices | writing or changing a principle | only applying an existing principle |
