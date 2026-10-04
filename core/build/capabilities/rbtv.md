# What is rbtv?

rbtv provides the conventions and software for creating and operating [agents](glossary/agent.md), their [cognitive units](glossary/cognitive-unit.md), and their [scaffolding](glossary/scaffolding.md). It shapes each agent's [context window](glossary/context-window.md) through cognitive units: with no change to the model itself, the context window is what makes a standard model act the way an agent needs. It supports Claude Code, Codex, and OpenCode as [harnesses](glossary/harness.md). Its concepts have direct counterparts in each harness. The [rbtv command](glossary/rbtv-command.md) translates them into each harness's format.

## How it works

[Modules](glossary/module.md) group [components](glossary/component.md). Components contain [cognitive units](glossary/cognitive-unit.md) and [capabilities](glossary/capability.md), the reusable content those units share, including [tools](glossary/tool.md). Some cognitive units form a [prompt](glossary/prompt.md); others are exposed as [skills](glossary/skill.md) chosen by agents, [commands](glossary/command.md) invoked by humans, or [rules](glossary/rule.md) always presented to agents. An [agent](glossary/agent.md) is a prompt, a model (with its effort), a harness and scaffolding. [Scaffolding](glossary/scaffolding.md) is everything an agent is exposed to besides its prompt: the cognitive units it has (skills, rules, commands, folder instructions) and the hooks, MCP servers and tools set up for it. Skill, rule, command, agent, hook, and MCP server are the [exposure methods](glossary/exposure-method.md). Instructions that apply only inside a folder are [folder instructions](glossary/folder-instructions.md), not an exposure method. A [pack](glossary/pack.md) is a named list of units that a component declares; a root or an agent turns it on or off as one step.

### The rbtv command

The [`rbtv` command](glossary/rbtv-command.md) manages what an agent is exposed to, by managing which units it has, for the root and for agents, and creates agents. The installation root is an rbtv agent with no `agent.md` and no stored harness, model or effort: the person chooses them when opening it. Its file is [`install.json`](glossary/install-json.md) in `.rbtv/config/`. An agent's file is [`agent.json`](glossary/agent-json.md), beside its `agent.md`. Both list the units chosen on their own (`units`) and the packs turned on (`packs`), and both hold the record of the files rbtv generated for them. `rbtv update SCOPE` makes the folder match that file: it generates the chosen units whose files are missing, and removes the generated files of units the file no longer lists. A hand edit to an agent's `agent.json` or to the root's `install.json`, or a change that arrives by `git pull`, is applied by one `update`; the root's `install.json` is changed by `rbtv configure`, `rbtv add`, `rbtv remove`, and `rbtv update`, which records the files it generated. The `rbtv agent` verbs (`add`, `remove`, `configure`, `update`, `list`) act on one agent by name or folder path; `configure` changes its harness, model and effort, and `add` puts in place the units its `agent.json` declares.

The `rbtv` command reads each module's [`<module>.json`](glossary/module-json.md) and each component's [`<component>.json`](glossary/component-json.md), including its description and external dependencies (software the component needs but does not include). The folder a skill, rule, command, sub-agent, hook, or MCP server sits in decides how it is exposed. A component may ship an [rbtv agent](glossary/agent.md#rbtv-agent) in `agents/`, which `rbtv agent add NAME` places in `.rbtv/agents/NAME/`. Where a harness has its own sub-agent format, rbtv translates each [harness-native sub-agent](glossary/agent.md#harness-native-sub-agent) file in `sub-agents/` into that format. It creates [thin loaders](glossary/thin-loader.md) for skills and commands, installs rules directly, translates [hooks](glossary/hook.md) and [MCP servers](glossary/mcp-server.md) into each harness's settings, and places tools on [`PATH`](glossary/path.md). Per-unit generated files carry `rbtv-managed`; shared files use booked keys or fenced sections, guidance copies carry a generated banner, PATH shortcuts are recorded in [`~/.rbtv/path-owners.json`](glossary/path-owners-json.md), and the root's and each agent's record lists the units and files rbtv has put in place. The mirror also holds [self-contained skills](glossary/self-contained-skill.md) under `_skills/`; rbtv lists them and installs thin loaders to their source `SKILL.md`. An [Ignite agent](glossary/agent.md#ignite-agent) is an rbtv agent whose `agent.json` turns the `ignite` pack on; `ignite connect` turns it on and connects Slack, and `ignite disconnect` turns it off. Harness exposure methods can also tell agents that a tool exists and how to use it. rbtv writes the other harness copies of each folder's folder instructions from the one file the author wrote. For each file a component ships from `folder-instructions/`, it writes that component's own marked section inside the target folder's folder instructions file, one section per component, never touching text outside it. In an rbtv agent's folder it also writes the agent section, which points the agent to its `agent.md`. Its non-interactive commands, `rbtv list`, `rbtv search`, and `rbtv show`, let agents and humans discover the cognitive units available, and carry everything needed to choose a unit and enter it in an agent's `agent.json`.

## Running agents

- An [Ignite agent](glossary/agent.md#ignite-agent) is an rbtv agent connected to Ignite: a Slack channel wakes it. Each message in its channel, or a timer, runs it. A scheduled wake starts a fresh conversation with no thread. The [board](glossary/board.md) holds the check's details. `ignite post --thread` continues an existing thread.
- Every turn, including a scheduled wake, injects the [profile](glossary/profile.md), that agent's [learned rules](glossary/learned-rules.md), its [board](glossary/board.md), the general-memory [index](glossary/memory-index.md), and the [inbox](glossary/inbox.md). [Workspace memory](glossary/workspace-memory.md) is added only when the working directory matches its declared paths. A missing or invalid injected file falls back to the last good git version and alerts, without blocking the turn ([memory](glossary/memory.md)). `ignite remember` appends to the inbox.
- `spark AGENT` runs an rbtv agent interactively, in a terminal a person uses. `spark list` shows the agents it can open.
- `cast -rbtv AGENT` lets another agent launch an rbtv agent. AGENT is a name under `.rbtv/agents/` or a path to the agent's folder. `cast list -rbtv` shows the agents it can launch, each with its description.
- `spark`, `cast -rbtv` and the Ignite launch all use the agent's own harness, model and effort, read from its `agent.json`, and set `RBTV_AGENT_HOME` to the agent's folder, so a command the agent runs can find the agent it belongs to. Only `rbtv agent configure` changes the harness, model or effort; no launch command overrides them ([running an agent](glossary/agent.md#running-an-agent)).
- `ignite turn` runs one turn with an exact session id; the waking program calls it. `--installation PATH` names the installation when the walk up from the current folder cannot find it.
- `cast <harness> <model> <effort 1-5> [launch-folder] (-p TEXT | -f FILE) -rogue FILE` launches a rogue agent: a prompt file with no folder, not an rbtv agent. The caller gives its harness, model and effort.
- An agent launched by another agent is a [sub-agent](glossary/agent.md#sub-agent). A [harness-native sub-agent](glossary/agent.md#harness-native-sub-agent) is a file in a harness's own sub-agent format, called through that harness's own tool, by an agent, and where the harness allows it by a person; `spark` is the route rbtv offers for interactive use.

## Folder structure

Each component uses this source layout:

```text
<module>/
|-- <module>.json
`-- <component>/
    |-- <component>.json
    |-- skills/          (<skill>.md)
    |-- rules/           (<rule>.md)
    |-- commands/        (<command>.md)
    |-- agents/          (<agent>/: agent.md and agent.json, an rbtv agent)
    |-- sub-agents/      (<sub-agent>.md: harness-native sub-agents)
    |-- packs/           (<pack>.json)
    |-- hooks/           (<hook>.json)
    |-- mcp-servers/     (<mcp-server>.json)
    |-- capabilities/
    |   `-- tools/
    |       `-- <tool>/  (<tool>.json and the program it names)
    `-- folder-instructions/
```

Terms: [`<module>.json`](glossary/module-json.md), [`<component>.json`](glossary/component-json.md), [`skills/`](glossary/skill.md), [`rules/`](glossary/rule.md), [`commands/`](glossary/command.md), [`agents/`](glossary/agent.md#rbtv-agent), [`sub-agents/`](glossary/agent.md#harness-native-sub-agent), [`packs/`](glossary/pack.md), [`hooks/`](glossary/hook.md), [`mcp-servers/`](glossary/mcp-server.md), [`capabilities/`](glossary/capability.md), [`capabilities/tools/<tool>/`](glossary/tool.md), and [`folder-instructions/`](glossary/folder-instructions.md), whose flat files each name their target folder in their frontmatter. Each skill, rule, command, and sub-agent is one file named after it. Each folder in `agents/` is named after its agent and holds two files: the [agent file](glossary/agent.md#agent-file) `agent.md`, the agent's prompt with frontmatter holding only its `name`, and [`agent.json`](glossary/agent-json.md), its description, harness, model, effort, chosen units and packs. Neither file holds anything tied to one machine. Each file in `packs/` is a [pack](glossary/pack.md) named after it.

rbtv creates [`.rbtv/`](glossary/rbtv-folder.md) inside the target folder, where rbtv is installed:

```text
<target-folder>/
`-- .rbtv/
    |-- mirror/
    |-- config/          (the root's install.json, and user-specific configuration such as ignite/)
    |-- agents/
    |   `-- <agent>/     (one agent folder: agent.md and agent.json, plus its generated files)
    |-- runtime/
    `-- memory/          (general memory: one fixed root)
        |-- profile.md
        |-- inbox.md
        |-- workstreams.md
        |-- _artifacts/index.md
        |-- entities/
        |-- knowledge/
        |-- workspaces/
        `-- timeline/
```

An agent may also live anywhere else, such as inside a plan's folder, and is then managed in place; `.rbtv/agents/` is where rbtv finds an agent by name.

rbtv writes a `.gitignore` in each agent folder that keeps generated files and machine data out of git. `agent.md` and `agent.json` are shared through git; machine data such as `settings.json` is not.

rbtv also keeps [`~/.rbtv/`](glossary/rbtv-home-folder.md) in the user's home, for the commands it places on `PATH` and [`path-owners.json`](glossary/path-owners-json.md), its record of them.

Terms: [`mirror/`](glossary/mirror.md), [`config/`](glossary/config.md), [`install.json`](glossary/install-json.md), [`ignite/config.json`](glossary/ignite-config.md), [`agents/<agent>/`](glossary/agent.md#rbtv-agent), [`agent.json`](glossary/agent-json.md), [`runtime/`](glossary/runtime.md), and [`memory/`](glossary/memory.md). An agent folder's own layout, with [`settings.json`](glossary/settings-json.md), [`memory/learned.md`](glossary/learned-rules.md) ([template](templates/learned-rules.md)), and [`_artifacts/board.md`](glossary/board.md) ([template](templates/board.md)), is in [agent](glossary/agent.md#rbtv-agent). General-memory files, one line each: [`profile.md`](glossary/profile.md) ([template](templates/profile.md)), [`inbox.md`](glossary/inbox.md) ([template](templates/inbox.md)), [`workstreams.md`](glossary/workstreams.md) ([template](templates/workstreams.md)), [`_artifacts/index.md`](glossary/memory-index.md) ([template](templates/memory-index.md)), [`entities/`](glossary/entity.md) ([template](templates/entity.md)), [`knowledge/`](glossary/knowledge.md) ([template](templates/knowledge.md)), [`workspaces/<slug>.md`](glossary/workspace-memory.md) ([template](templates/workspace-memory.md)), [`timeline/daily/`](templates/timeline-daily.md) ([template](templates/timeline-daily.md)), [`timeline/weekly/`](templates/timeline-weekly.md) ([template](templates/timeline-weekly.md)). Agent topics: [`<agent>/memory/<slug>.md`](glossary/agent-topic.md) ([template](templates/agent-topic.md)). The [dreamer](glossary/dreamer.md) writes long-term memory.

## Folder artifacts

A folder an agent maintains can hold [folder artifacts](<_under-evaluation/guides/folder artifacts/glossary/folder-artifact.md>) in `_artifacts/`, under plain names, each with one fixed purpose. `_artifacts/` does not replace rbtv's `capabilities/` folders. A wiki keeps its own index names.

```text
<folder>/
|-- <folder instructions>
`-- _artifacts/
    |-- index.md       (content index: when to open each item that is not an artifact)
    |-- board.md       (short-term memory, on an agent, project, or area folder)
    `-- <other artifacts>
```

Terms: [index file](<_under-evaluation/guides/folder artifacts/glossary/index-file.md>) ([template](templates/index-file.md)), [board](glossary/board.md) ([template](templates/board.md)), and [task file](glossary/task-file.md) at `_artifacts/<folder>-tasks.md`, the one plain-name exception. rbtv's JSON records stay beside their folder, not in `_artifacts/`: [`<module>.json`](glossary/module-json.md), [`<component>.json`](glossary/component-json.md), and [`<tool>.json`](glossary/tool-json.md). A module, component, or tool folder has its JSON record and no index file.

## Folder instructions

Any folder can hold [folder instructions](glossary/folder-instructions.md), meant to reach an agent when it reads or changes files in that folder, and to route it to the right file at that moment. A [rule](glossary/rule.md) applies to every task of every agent that receives it, whatever folder it works in.

## Authoring

- [Role](glossary/role.md), [persona](glossary/persona.md), [procedure](glossary/procedure.md), and [constraints](glossary/constraints.md) are sections of the agent file, not separate files. [Scope](glossary/scope.md) and a [done contract](glossary/done-contract.md) are written with the [task](glossary/task.md), not in the prompt.
- An agent's chosen units and packs are fields of its [`agent.json`](glossary/agent-json.md), not prompt prose; each unit name there resolves to exactly one unit, and a missing or ambiguous name is an error from rbtv. Its `agent.md` frontmatter holds only `name`, which must equal the folder name and the `name` in `agent.json`. Its harness, model, and effort are fields of `agent.json`, set when the agent is created and changed only by `rbtv agent configure` ([agent](glossary/agent.md)).
- Do not hand-write a [thin loader](glossary/thin-loader.md), the parts of [`.rbtv/`](glossary/rbtv-folder.md) that rbtv writes ([`config/`](glossary/config.md), [`runtime/`](glossary/runtime.md), and an agent's generated files), and do not edit a generated copy. Change the source and run `rbtv update`. The hand-written pieces of `.rbtv/` are [`mirror/`](glossary/mirror.md) and each agent's `agent.md`, [`agent.json`](glossary/agent-json.md), and [`settings.json`](glossary/settings-json.md). A mirror component uses the same layout as a shipped component; a [self-contained skill](glossary/self-contained-skill.md) uses the mirror's `_skills/` folder. Do not hand-edit files the [dreamer](glossary/dreamer.md) writes. Append a fact about the owner with `ignite remember`. Write board subjects and watch-outs with `ignite board`.
- A component folder without [`<component>.json`](glossary/component-json.md) is an error from rbtv. Outside software a tool needs is listed there, not in [`<tool>.json`](glossary/tool-json.md), which names the program rbtv places on `PATH`.
- Each exposed unit carries its own name and a short description, so rbtv can present it without a separate list: skills, commands, rules, and sub-agents in frontmatter, rbtv agents in `agent.json`, hooks, MCP servers, tools, and packs in their JSON record ([Progressive disclosure](principles/progressive-disclosure.md)). rbtv checks each against its [schema](glossary/schema.md) and refuses one that does not match.
- A file that agents and programs both read follows a [template](glossary/template.md) for what agents read and a [schema](glossary/schema.md) for what programs read, such as an agent file's body and its frontmatter. Both are listed in [templates/templates.md](templates/templates.md).
- Data created while a component runs goes under [`.rbtv/runtime/`](glossary/runtime.md), not in source and not in `mirror/`; an rbtv agent's live data stays in its own agent folder. An artifact keeps its plain name when its folder is renamed. The [task file](glossary/task-file.md) is the exception: its name follows the folder, because the task tool matches the `-tasks.md` ending.
- Choosing which kind to build is [choosing what to build](<_under-evaluation/guides/procedure documents/choosing-what-to-build.md>). Guides are listed in [guides/guides.md](guides/guides.md). Templates are listed in [templates/templates.md](templates/templates.md).
