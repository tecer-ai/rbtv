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

On create or conversion, start in the user's named module and component and use [Choosing where to build](../capabilities/methods/choosing-where-to-build.md) to check its boundary. Object only for a boundary violation. Editing an existing file does not reopen placement.

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
| [Choosing what to build](../capabilities/methods/choosing-what-to-build.md) | Choice of kind | Match the mechanism to the work | creating, reviewing or converting; editing when the current kind cannot support the required behavior | editing with the kind unchanged |
| [Choosing where to build](../capabilities/methods/choosing-where-to-build.md) | Repository, mirror, module and component choice | Place work inside the right boundary | creating or converting | editing |
| [Nested exposure](../capabilities/methods/nested-exposure.md) | Several capabilities under one exposure method | Group related methods without premature reading | one exposure method may route to multiple capabilities | only one capability is exposed |
| [Building from a conversation](../capabilities/methods/building-from-a-conversation.md) | Extraction of settled reusable instructions | Preserve the corrected method | asked to build from a completed conversation | capture during an ongoing conversation |
| [Tips development](../capabilities/methods/tips-development.md) | Capture of decisions and evidence during work | Preserve distinctions without starting another build | setting up or continuing capture during a conversation | extracting instructions after the conversation |
| [Writing a glossary entry](../capabilities/methods/writing-a-glossary-entry.md) | Entry structure, ownership and verification | Define a term and teach its authoring | creating, editing or converting an entry, or introducing a term without one | no term entry is added or changed |
| [Writing a capability](../capabilities/methods/writing-a-capability.md) | Writing routed methods and knowledge | Continue from the caller’s supplied context | creating, editing or converting a capability or procedure | writing a term definition |
| [Capability](../capabilities/glossary/capability.md) | Capability boundary and caller contract | Write the work that follows a route | the selected kind or named work is a capability | only writing an exposure method |
| [Cognitive unit](../capabilities/glossary/cognitive-unit.md) | Actionable instructions and their parts | Make instructions usable on another task | writing or changing instructions in a skill, rule, command, prompt or capability |  |
| [Routing table](../capabilities/glossary/routing-table.md) | Descriptions and file-selection rows | Select the right reading | writing or changing a description or routing table |  |
| [Entry point](../capabilities/glossary/entry-point.md) | Common body and conditional routes | Keep each reading focused | writing or changing the body or routes of a skill, command, rule or folder-instructions file |  |
| [Exposure method](../capabilities/glossary/exposure-method.md) | Who selects each installed form | Choose how content reaches the agent | choosing among skill, command, rule and folder instructions |  |
| [Prompt](../capabilities/glossary/prompt.md) | Standing instructions in prompt.md | Define behavior across the agent’s tasks | writing or changing a prompt body | only agent configuration or one launch task changes |
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
| [Workflow](../capabilities/glossary/workflow.md) | Task dependencies, shared writes and scheduling | Coordinate tasks from their declared inputs | writing, editing or reviewing a workflow | one task needs no coordination |
| [Provider](../capabilities/glossary/provider.md) | Providers, logins and saved logins | Name whose login or plan a launch uses | stating which provider, login or key a harness or model uses, or changing a supported provider | only choosing a harness or a model |
| [Provider accounts](../capabilities/providers.md) | `rbtv providers` verbs, saved-login location and the providers file | Save, switch and read provider accounts | listing or switching provider logins, reading plan usage, or editing `providers.json` | only defining the term |
| [Model catalog](../../cast/capabilities/glossary/model-catalog.md) | Files, rows, columns and `use` values of cast's table of models | State what a row or a column means | reading or editing a `models.csv`, or naming the model catalog in another file | only launching an already selected model |
| [Supported model](../../cast/capabilities/glossary/supported-model.md) | What a copy of cast can launch and where that is recorded | Tell a supported model from a selected one | stating which models cast can launch, or which copy of rbtv supports a model | only choosing among an installation's selected models |
| [Selected model](../../cast/capabilities/glossary/selected-model.md) | The models one installation launches and what is refused without one | Explain a launch refusal or name what an installation launches | stating which models an installation launches or why a model is refused | only changing a row's routing columns; use Model catalog |
| [Personalizing the model catalog](../../cast/capabilities/personalizing-the-model-catalog.md) | Selecting models, editing routing columns, supporting a new model, the order with the daemon and a second machine | Change an installation's models or cast's supported models | adding, removing or replacing a model for an installation or in cast | only changing one agent's model; use rbtv CLI |
| [Harness](../capabilities/glossary/harness.md) | Delivery differences between supported applications | Avoid assuming identical loading behavior | stating what an agent receives or supporting multiple harnesses |  |
| [Module record](../capabilities/glossary/module-json.md) | Module description record | Write the module’s listing record | creating, editing or converting `<module>.json` | only files inside an existing module change |
| [Component record](../capabilities/glossary/component-json.md) | Description and external dependencies | Write the component’s record | creating, editing or converting `<component>.json` | only files inside an existing component change |
| [Tool record](../capabilities/glossary/tool-json.md) | Executable reference and listing description | Make the intended program available by name | creating, editing or converting `<tool>.json` | only the program body changes |
| [Agent record](../capabilities/glossary/agent-json.md) | Author selections and installed setup | Maintain an agent’s record | writing or changing `agent.json` | only the prompt body changes |
| [Installation record](../capabilities/glossary/install-json.md) | Root selection and generated-file ownership | Maintain an installation’s selections | working with `install.json` | only component source changes |
| [Command ownership record](../capabilities/glossary/path-owners-json.md) | Commands shared by installations | Check ownership and release obsolete claims | working with shared command ownership | only writing a tool’s program |
| [Installation folder](../capabilities/glossary/rbtv-folder.md) | Installation-local folders and their owners | Place installation material | choosing where installation files belong | only changing component source |
| [rbtv home folder](../capabilities/glossary/rbtv-home-folder.md) | User-wide command shortcuts | Distinguish shared machine files from installation files | working with `~/.rbtv/` or command availability | only an installation’s local source changes |
| [Configuration folder](../capabilities/glossary/config.md) | Where a component keeps user settings, credentials and keys | Place and change configuration | a component, tool or agent saves user settings, choices, credentials or keys | only an agent’s job settings change |
| [Agent settings](../capabilities/glossary/settings-json.md) | Job-specific configuration | Supply an agent’s variable inputs | writing or changing `settings.json` | only launch settings change |
| [Environment file](../capabilities/glossary/environment-file.md) | Installation-local variable values | Supply values by the consumer’s loading rules | writing or changing `.rbtv/config/env/.env` guidance or contents | only naming an existing variable in component configuration |
| [Runtime folder](../capabilities/glossary/runtime.md) | Where a component or tool writes state, caches, locks and logs | Keep operational data out of source and settings | a component or tool writes operational data | only user-selected settings change |
| [Memory folder](../capabilities/glossary/memory-folder.md) | `.rbtv/memory/` and who maintains it | Keep other material out of general memory | deciding whether something belongs in `.rbtv/memory/` | working with one memory record; use Memory |
| [Mirror](../capabilities/glossary/mirror.md) | Installation-local component source | Add or replace local components | creating or changing mirror source | only repository source changes |
| [Self-contained skill](../capabilities/glossary/self-contained-skill.md) | SKILL.md and supporting files kept together | Import or author a shareable skill package | working with a whole-folder skill in mirror `_skills/` | writing a component’s `skills/<name>.md` |
| [Schema](../capabilities/glossary/schema.md) | Validator constraints and actual callers | Enforce the record’s contract | writing or changing a schema or adding a record field | only filling an existing record |
| [Template](../capabilities/glossary/template.md) | Layout and placeholders | Fill the required structure | writing or filling a page’s template |  |
| [Principle](../capabilities/glossary/principle.md) | Cross-kind design tests | Settle recurring design choices | writing or changing a principle | only applying an existing principle |
| [Memory](../../ignite/capabilities/glossary/memory.md) | General and agent memory, writer boundaries and record checks | Preserve memory across Ignite turns | creating, editing, reviewing or converting any Ignite memory record | only ordinary agent settings change |
| [Ignite configuration](../../ignite/capabilities/glossary/ignite-config.md) | Machine-local connections and consolidation settings | Configure Ignite through its actual validator | working with Ignite config.json | only agent.json changes |
| [Board](../../ignite/capabilities/glossary/board.md) | Subjects, watch-outs and software-maintained fields | Maintain short-term agent memory | working with an Ignite board or its convention | only long-term records change |
| [Dreamer](../../ignite/capabilities/glossary/dreamer.md) | Consolidation evidence and publication boundaries | Operate or verify long-term memory writing | working with consolidation or its produced records | only reading a stored fact |
| [Profile](../../ignite/capabilities/glossary/profile.md) | Facts supplied on nearly every turn | Keep standing owner context | working with profile.md |  |
| [Learned rules](../../ignite/capabilities/glossary/learned-rules.md) | Corrections and repeated lessons for one agent | Preserve learned behavior | working with learned.md |  |
| [Memory index](../../ignite/capabilities/glossary/memory-index.md) | Always-supplied root and generated folder lists | Route memory reads in the validated format | working with memory indexes |  |
| [Workspace memory](../../ignite/capabilities/glossary/workspace-memory.md) | Private notes and declared path matching | Supply notes only in the relevant workspace | working with workspace memory |  |
| [Inbox](../../ignite/capabilities/glossary/inbox.md) | Append-only owner facts and filing results | Remember a fact without rewriting memory | working with inbox.md or remember |  |
| [Agent topic](../../ignite/capabilities/glossary/agent-topic.md) | Subject, procedure and reference detail for one agent | Keep detail available on demand | working with agent memory topics |  |
| [Entity](../../ignite/capabilities/glossary/entity.md) | Stable identity, aliases and source-note links | Keep one record per owner-related entity | working with memory entities |  |
| [Knowledge](../../ignite/capabilities/glossary/knowledge.md) | Five durable owner-information kinds | Preserve topical facts without always supplying them | working with knowledge records |  |
| [Workstreams](../../ignite/capabilities/glossary/workstreams.md) | Pointers to active projects, areas and subjects | Find active work without copying its state | working with workstreams.md |  |
| [Daily timeline](../../ignite/capabilities/glossary/timeline-daily.md) | Daily episodes and source threads | Retain a day’s activity as on-demand history | working with daily memory timelines |  |
| [Weekly timeline](../../ignite/capabilities/glossary/timeline-weekly.md) | Consequential events linked to their source days | Retain a week’s history without repeating daily detail | working with weekly memory timelines |  |
