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
| Agent | `agents/<name>/prompt.md` and `agent.json` |
| Hook, MCP server, pack | `hooks/<name>.json`, `mcp-servers/<name>.json`, `packs/<name>.json` |
| Tool | `capabilities/tools/<name>/<name>.json` and its executable |
| Folder instructions | `folder-instructions/<name>.md` |
| Capability | Markdown under `capabilities/`: a method page in `capabilities/methods/`, a tool page at `capabilities/tools/<tool>/<tool>.md`; read from source, not installed |
| Glossary entry | `capabilities/glossary/<term>.md` in the owning component |
| rbtv principle | `core/rbtv/capabilities/principles/<name>.md` |

A self-contained skill folder with `SKILL.md` and supporting files is allowed only under `.rbtv/mirror/_skills/<name>/`. There is no repository `_skills/` folder and no source-folder index such as `capabilities.md`, `principles.md` or `glossary.md`.

A skill, command, rule or folder-instructions file routes to capabilities, not to another exposure method. Do not nest those installed forms inside one another.

## Read for this work

Apply the same routes in create, edit, review and convert modes; there is no separate page per mode. Read mandatory pages first. For conditional rows, match the work and honor the exclusion. If [Choosing what to build](../capabilities/methods/choosing-what-to-build.md) settles a different kind from the request's wording, follow the settled kind's row too.

On create or conversion, start in the user's named module and component and use [Choosing where to build](../capabilities/methods/choosing-where-to-build.md) to check its boundary. Object only for a boundary violation. An agent folder outside a component, such as a plan's or a project's agent, is placed by [Agent](../capabilities/glossary/agent.md), not by Choosing where to build. Editing an existing file does not reopen placement.

If a required page is absent, report the missing path and stop that work. Do not substitute an older entry or build from this folder map alone. If no row covers the intended kind, ask for the missing definition rather than guessing.

Read these pages on every use, before the conditional readings:

- [Scaffolding language](../capabilities/glossary/scaffolding-language.md): Instructions understood on first reading.
- [Keep it stupidly simple](../capabilities/principles/keep-it-stupidly-simple.md): Remove unnecessary work and cognitive load.
- [Terminology is king](../capabilities/principles/terminology-is-king.md): Use one meaning consistently.
- [Single source of truth](../capabilities/principles/single-source-of-truth.md): Maintain each in one home.
- [Deterministic first](../capabilities/principles/deterministic-first.md): Use computed results for exact work.
- [Progressive disclosure](../capabilities/principles/progressive-disclosure.md): Supply each method when needed.
- [Agent parity](../capabilities/principles/agent-parity.md): Provide equivalent executable paths.

Then read every matching method:

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN | DO NOT LOAD WHEN |
|---|---|---|---|---|
| [rbtv CLI](../capabilities/glossary/rbtv-cli.md) | Recognition, generation and refresh commands | Validate and deliver source changes | creating or converting a file; changing the installer; reviewing or editing scanned source | only changing an unscanned capability body without renaming or moving it |
| [Documenting a change](../capabilities/methods/documenting-a-change.md) | Pages, records and routes to update with a change, and the checks before it is done | Keep instructions and routes accurate with the source | any change lands in the repository, before it is called done | nothing is written yet |
| [Building for Linux and Windows](../capabilities/methods/building-for-linux-and-windows.md) | Rules for encoding, line endings, executables, file attributes and names, and the run on both systems | Make a change run on Linux and Windows | writing or changing code, a tool, a test or an installer-scanned file | only prose changes |
| [Choosing what to build](../capabilities/methods/choosing-what-to-build.md) | Choice of kind, and routes to exposure method and nested exposure | Match the mechanism to the work | creating, reviewing or converting; editing when the current kind cannot support the required behavior | editing with the kind unchanged |
| [Choosing where to build](../capabilities/methods/choosing-where-to-build.md) | Repository, mirror, module and component choice | Place work inside the right boundary | creating or converting | editing |
| [Building from a conversation](../capabilities/methods/building-from-a-conversation.md) | Extraction of settled reusable instructions | Preserve the corrected method | asked to build from a completed conversation | capture during an ongoing conversation |
| [Tips development](../capabilities/methods/tips-development.md) | Capture of decisions and evidence during work | Preserve distinctions without starting another build | setting up or continuing capture during a conversation | extracting instructions after the conversation |
| [Schema](../capabilities/glossary/schema.md) | Validator constraints and actual callers | Enforce the record’s contract | writing or changing a schema or adding a record field | only filling an existing record |
| [Installation folder](../capabilities/glossary/rbtv-folder.md) | `.rbtv/` subfolders and their owners, with routes to mirror, configuration, runtime and memory folder and to the rbtv home folder | Place installation material | choosing where installation files belong, or a component, tool or agent saves settings, keys or operational data | only changing component source |
| [Installation record](../capabilities/glossary/install-json.md) | Root selection and generated-file ownership, with a route to command ownership | Maintain an installation’s selections | working with `install.json` or shared command ownership | only component source changes |
| [Provider](../capabilities/glossary/provider.md) | Providers, logins and saved logins, with a route to the `rbtv providers` verbs | Name whose login or plan a launch uses | stating which provider, login or key a harness or model uses, or changing a supported provider or saved login | only choosing a harness or a model |
| [Personalizing the model catalog](../../cast/capabilities/tools/cast/documentation/personalizing-the-model-catalog.md) | Selecting models, editing routing columns, supporting a new model, the order with the daemon and a second machine, with routes to the model catalog, supported and selected model | Change an installation's models or cast's supported models | adding, removing or replacing a model for an installation or in cast, or reading or editing a `models.csv` | only changing one agent's model; use Agent |
| [Workflow](../capabilities/glossary/workflow.md) | Task dependencies, shared writes and scheduling | Coordinate tasks from their declared inputs | writing, editing or reviewing a workflow | one task needs no coordination |
| [Testing Ignite](../../ignite/capabilities/methods/testing-ignite.md) | Ignite's testing method | Verify a change to Ignite before it is called done | changing any file under `core/ignite/` | only its glossary prose changes |
| [Memory](../../ignite/capabilities/glossary/memory.md) | General and agent memory, writer boundaries and record checks, with a route to each memory record kind | Preserve memory across Ignite turns | creating, editing, reviewing or converting any Ignite memory record | only ordinary agent settings change |

Then, when the work is one of the kinds below, read that kind's page. (Ignite memory records are routed by the Memory row above, not here.) The kind's page carries its own routes — its record, template, schema and supporting pages — at the step that needs them; do not look for those routes here:

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN | DO NOT LOAD WHEN |
|---|---|---|---|---|
| [Skill](../capabilities/glossary/skill.md) | Agent-selected task instructions, with routes to cognitive unit, entry point, routing table, nested exposure and self-contained skill | Open on the intended task | the selected kind or named work is a skill | only another kind is being changed |
| [Rule](../capabilities/glossary/rule.md) | Always-supplied instructions with action conditions | Act when the condition arises | the selected kind or named work is a rule | only another kind is being changed |
| [Command](../capabilities/glossary/command.md) | Human invocation and supplied inputs | Perform the requested action | the selected kind or named work is a command | only another kind is being changed |
| [Folder instructions](../capabilities/glossary/folder-instructions.md) | Instructions supplied by folder location, with a route to folder artifact | Give each visit its required context | writing or changing folder instructions or a folder artifact | instructions apply across all folders; use Rule |
| [Agent](../capabilities/glossary/agent.md) | Agent folder and placement, with routes to prompt, agent record, agent settings, task and selected model | Launch the intended worker | the selected kind or named work is an agent or sub-agent, or any file in an agent folder changes | only another kind is being changed |
| [Hook](../capabilities/glossary/hook.md) | Event, matching and command outcome | Run and enforce at the intended event | writing or changing a hook | only a server or tool changes |
| [MCP server](../capabilities/glossary/mcp-server.md) | Server connection and credential references | Expose the intended server actions | writing or changing an MCP server record | only a tool or hook changes |
| [Tool](../capabilities/glossary/tool.md) | Program interface and executable record, with routes to tool record, configuration and runtime folder and the command-line method | Return usable results during a task | writing or changing a tool | only prose instructions change |
| [Pack](../capabilities/glossary/pack.md) | Shared installation selection | Install one group for several targets | writing or changing a pack, or sharing a selection across targets | only one target needs the selection |
| [Capability](../capabilities/glossary/capability.md) | Capability boundary and caller contract, with routes to writing a capability, template and schema | Write the work that follows a route | the selected kind or named work is a capability | only writing an exposure method |
| [Writing a glossary entry](../capabilities/methods/writing-a-glossary-entry.md) | Entry structure, ownership and verification | Define a term and teach its authoring | creating, editing or converting an entry, or introducing a term without one | no term entry is added or changed |
| [Principle](../capabilities/glossary/principle.md) | Cross-kind design tests | Settle recurring design choices | writing or changing a principle | only applying an existing principle |
| [Module](../capabilities/glossary/module.md) | Component grouping and module boundary, with a route to the module record | Place components by subject | writing or changing a module or `<module>.json` | only a component changes |
| [Component](../capabilities/glossary/component.md) | Source grouping and component boundary, with a route to the component record | Keep related files together | writing or changing a component or `<component>.json` | only a file inside an unchanged component changes |
