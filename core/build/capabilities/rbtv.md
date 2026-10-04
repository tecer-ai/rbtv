# What is rbtv?

rbtv provides the conventions and software for creating and operating [agents](glossary/agent.md), their [cognitive units](glossary/cognitive-unit.md), and their [scaffolding](glossary/scaffolding.md). It shapes each agent's [context window](glossary/context-window.md) through cognitive units: with no change to the model itself, the context window is what makes a standard model act the way an agent needs. It supports Claude Code, Codex, and OpenCode as [harnesses](glossary/harness.md). Its concepts have direct counterparts in each harness. The [rbtv installer](glossary/rbtv-installer.md) translates them into each harness's format.

## How it works

[Modules](glossary/module.md) group [components](glossary/component.md). Components contain [cognitive units](glossary/cognitive-unit.md) and [capabilities](glossary/capability.md), the reusable content those units share, including [tools](glossary/tool.md). Some cognitive units form a [prompt](glossary/prompt.md); others are exposed as [skills](glossary/skill.md) chosen by agents, [commands](glossary/command.md) invoked by humans, or [rules](glossary/rule.md) always presented to agents. A prompt given to an AI model through a [harness](glossary/harness.md) is an [agent](glossary/agent.md). Skill, rule, command, agent, hook, and MCP server are the [exposure methods](glossary/exposure-method.md). Instructions that apply only inside a folder are [folder instructions](glossary/folder-instructions.md), not an exposure method.

### Installer

The installer reads each module's [`<module>.json`](glossary/module-json.md) and each component's [`<component>.json`](glossary/component-json.md), including its description and external dependencies (software the component needs but does not include). The folder a skill, rule, command, agent, hook, or MCP server sits in decides how it is exposed. Where a harness has its own sub-agent definitions, the installer translates agent files into them. It creates [thin loaders](glossary/thin-loader.md) for skills and commands, installs rules directly, translates [hooks](glossary/hook.md) and [MCP servers](glossary/mcp-server.md) into each harness's settings, and places tools on [`PATH`](glossary/path.md). Per-unit generated files carry `rbtv-managed`; shared files use booked keys or fenced sections, guidance copies carry a generated banner, PATH shortcuts are recorded in [`~/.rbtv/path-owners.json`](glossary/path-owners-json.md), and [`install.json`](glossary/install-json.md) tracks the installed units and files. The mirror also holds [self-contained skills](glossary/self-contained-skill.md) under `_skills/`; the installer lists them and installs thin loaders to their source `SKILL.md`. It installs an [agent](glossary/agent.md#installed-agent) from its agent file into the agent's own folder under `.rbtv/agents/`, with the cognitive units its frontmatter, the structured metadata at the top of the file, selects, and the harness, model, and effort chosen by whoever installs it, recorded in [`launch.json`](glossary/launch-json.md). `rbtv install agent update` refreshes an installed agent from its agent file. `rbtv install update` regenerates installed units from source; a unit whose source no longer exists is removed and reported, while a renamed unit is installed under its new name only by `rbtv install add`. An [Ignite agent](glossary/agent.md#ignite-agent) is installed and updated through Ignite's own install step, which adds its units and, on update, removes any unit in the agent folder that neither the agent file nor Ignite's list selects; the `rbtv` help says so, because a plain `rbtv install` would leave them out. Its non-interactive commands, `rbtv install list`, `search`, and `show`, let agents and humans discover the cognitive units available, and carry everything needed to choose a unit and enter it in an agent file. Harness exposure methods can also tell agents that a tool exists and how to use it. It writes the other harness copies of each folder's folder instructions from the one file the author wrote. For each file a component ships from `folder-instructions/`, it writes that component's own marked section inside the target folder's folder instructions file, one section per component, never touching text outside it. In an installed agent's folder it also writes the agent section, which points the agent to its `agent.md` and lists its key folders.

### Running agents
*Revisar essa parte*

- An [Ignite agent](glossary/agent.md#ignite-agent) is an installed agent with Ignite's standard cognitive units and a Slack connection; each message in its channel, or a timer, runs it. A scheduled wake starts a fresh conversation with no thread. The [board](glossary/board.md) holds the check's details. `ignite-agent post --thread` continues an existing thread.
- Every turn, including a scheduled wake, injects the [profile](glossary/profile.md), that agent's [learned rules](glossary/learned-rules.md), its [board](glossary/board.md), the general-memory [index](glossary/memory-index.md), and the [inbox](glossary/inbox.md). [Workspace memory](glossary/workspace-memory.md) is added only when the working directory matches its declared paths. A missing or invalid injected file falls back to the last good git version and alerts, without blocking the turn ([memory](glossary/memory.md)). `ignite-agent remember` appends to the inbox.
- `rbtv spark <agent>` runs an installed agent interactively.
- `cast -ig` lets another agent launch an installed agent, passing its harness, model, and effort; `cast -rg` launches a one-off agent that is not installed ([running an agent](glossary/agent.md#running-an-agent)). An agent launched by another agent is a [sub-agent](glossary/agent.md#sub-agent).

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
    |-- agents/          (<agent>.md: named agent definitions)
    |-- hooks/           (<hook>.json)
    |-- mcp-servers/     (<mcp-server>.json)
    |-- capabilities/
    |   `-- tools/
    |       `-- <tool>/  (<tool>.json and the program it names)
    `-- folder-instructions/
```

Terms: [`<module>.json`](glossary/module-json.md), [`<component>.json`](glossary/component-json.md), [`skills/`](glossary/skill.md), [`rules/`](glossary/rule.md), [`commands/`](glossary/command.md), [`agents/`](glossary/agent.md), [`hooks/`](glossary/hook.md), [`mcp-servers/`](glossary/mcp-server.md), [`capabilities/`](glossary/capability.md), [`capabilities/tools/<tool>/`](glossary/tool.md), and [`folder-instructions/`](glossary/folder-instructions.md), whose flat files each name their target folder in their frontmatter. Each skill, rule, command, and agent is one file named after it. Each file in `agents/` is an [agent file](glossary/agent.md#agent-file): the agent's prompt, with frontmatter declaring the skills, rules, commands, hooks, and MCP servers it uses, and its key folders. It holds no harness, model, or effort.

The installer creates [`.rbtv/`](glossary/rbtv-folder.md) inside the target folder, where rbtv is installed:

```text
<target-folder>/
`-- .rbtv/
    |-- mirror/
    |-- config/          (user-specific configuration, such as ignite/)
    |-- agents/
    |   `-- <agent>/     (one self-contained agent folder)
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

The installer also keeps [`~/.rbtv/`](glossary/rbtv-home-folder.md) in the user's home, for the commands it places on `PATH` and [`path-owners.json`](glossary/path-owners-json.md), its record of them.

Terms: [`mirror/`](glossary/mirror.md), [`config/`](glossary/config.md), [`install.json`](glossary/install-json.md), [`ignite/config.json`](glossary/ignite-config.md), [`agents/<agent>/`](glossary/agent.md#installed-agent), [`runtime/`](glossary/runtime.md), and [`memory/`](glossary/memory.md). An agent folder's own layout, with [`launch.json`](glossary/launch-json.md), [`settings.json`](glossary/settings-json.md), [`memory/learned.md`](glossary/learned-rules.md) ([template](templates/learned-rules.md)), and [`_artifacts/board.md`](glossary/board.md) ([template](templates/board.md)), is in [agent](glossary/agent.md#installed-agent). General-memory files, one line each: [`profile.md`](glossary/profile.md) ([template](templates/profile.md)), [`inbox.md`](glossary/inbox.md) ([template](templates/inbox.md)), [`workstreams.md`](glossary/workstreams.md) ([template](templates/workstreams.md)), [`_artifacts/index.md`](glossary/memory-index.md) ([template](templates/memory-index.md)), [`entities/`](glossary/entity.md) ([template](templates/entity.md)), [`knowledge/`](glossary/knowledge.md) ([template](templates/knowledge.md)), [`workspaces/<slug>.md`](glossary/workspace-memory.md) ([template](templates/workspace-memory.md)), [`timeline/daily/`](glossary/timeline-daily.md) ([template](templates/timeline-daily.md)), [`timeline/weekly/`](glossary/timeline-weekly.md) ([template](templates/timeline-weekly.md)). Agent topics: [`<agent>/memory/<slug>.md`](glossary/agent-topic.md) ([template](templates/agent-topic.md)). The [dreamer](glossary/dreamer.md) writes long-term memory.

## Folder artifacts

A folder an agent maintains can hold [folder artifacts](glossary/folder-artifact.md) in `_artifacts/`, under plain names, each with one fixed purpose. `_artifacts/` does not replace rbtv's `capabilities/` folders. A wiki keeps its own index names.

```text
<folder>/
|-- <folder instructions>
`-- _artifacts/
    |-- index.md       (content index: when to open each item that is not an artifact)
    |-- board.md       (short-term memory, on an agent, project, or area folder)
    `-- <other artifacts>
```

Terms: [index file](glossary/index-file.md) ([template](templates/index-file.md)), [board](glossary/board.md) ([template](templates/board.md)), and [task file](glossary/task-file.md) at `_artifacts/<folder>-tasks.md`, the one plain-name exception. rbtv's JSON records stay beside their folder, not in `_artifacts/`: [`<module>.json`](glossary/module-json.md), [`<component>.json`](glossary/component-json.md), and [`<tool>.json`](glossary/tool-json.md). A module, component, or tool folder has its JSON record and no index file.

## Folder instructions

Any folder can hold [folder instructions](glossary/folder-instructions.md), meant to reach an agent when it reads or changes files in that folder, and to route it to the right file at that moment. A [rule](glossary/rule.md) applies to every task of every agent that receives it, whatever folder it works in.

## Authoring

- [Role](glossary/role.md), [persona](glossary/persona.md), [procedure](glossary/procedure.md), and [constraints](glossary/constraints.md) are sections of the agent file, not separate files. [Scope](glossary/scope.md) and a [done contract](glossary/done-contract.md) are written with the [task](glossary/task.md), not in the prompt.
- An agent file's selected units and key folders are frontmatter fields, not prompt prose; each name there resolves to exactly one unit, and a missing or ambiguous name is an installer error. Its harness, model, and effort are not in the file: they are chosen at install, in [`launch.json`](glossary/launch-json.md), or at launch ([agent](glossary/agent.md)).
- Do not hand-write a [thin loader](glossary/thin-loader.md), [`.rbtv/`](glossary/rbtv-folder.md), [`config/`](glossary/config.md), or [`runtime/`](glossary/runtime.md), and do not edit a generated copy. Change the source and run the installer. The hand-written pieces of `.rbtv/` are [`mirror/`](glossary/mirror.md) and each installed agent's `agent.md` and [`settings.json`](glossary/settings-json.md). A mirror component uses the same layout as a shipped component; a [self-contained skill](glossary/self-contained-skill.md) uses the mirror’s `_skills/` folder. Do not hand-edit files the [dreamer](glossary/dreamer.md) writes. Append a fact about the owner with `ignite-agent remember`. Write board subjects and watch-outs with `ignite-agent board`.
- A component folder without [`<component>.json`](glossary/component-json.md) is an installer error. Outside software a tool needs is listed there, not in [`<tool>.json`](glossary/tool-json.md), which names the program the installer places on `PATH`.
- Each exposed unit carries its own name and a short description, so the installer can present it without a separate list: skills, commands, rules, and agents in frontmatter, hooks, MCP servers, and tools in their JSON record ([Progressive disclosure](principles/progressive-disclosure.md)). The installer checks each against its [schema](glossary/schema.md) and refuses one that does not match.
- A file that agents and programs both read follows a [template](glossary/template.md) for what agents read and a [schema](glossary/schema.md) for what programs read, such as an agent file's body and its frontmatter. Both are listed in [templates/templates.md](templates/templates.md).
- Data created while a component runs goes under [`.rbtv/runtime/`](glossary/runtime.md), not in source and not in `mirror/`; an installed agent's live data stays in its own agent folder. An artifact keeps its plain name when its folder is renamed. The [task file](glossary/task-file.md) is the exception: its name follows the folder, because the task tool matches the `-tasks.md` ending.
- Choosing which kind to build is [choosing what to build](guides/choosing-what-to-build.md). Guides are listed in [guides/guides.md](guides/guides.md). Templates are listed in [templates/templates.md](templates/templates.md).
