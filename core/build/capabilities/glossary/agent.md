# Agent

An agent is a prompt, a model (with its effort), a [harness](harness.md) and [scaffolding](scaffolding.md). A user or another agent supplies its work, a [task](task.md), at runtime.

## Agent file

The agent's prompt, in `agent.md`. Its frontmatter (structured metadata at the top of the file) holds one field, `name`, which must equal the folder name and the name in the agent's [`agent.json`](agent-json.md). Its body is the prompt: its [template](template.md) defines its sections, and its [schema](schema.md) defines its frontmatter. It holds no harness, model, or effort: those are in `agent.json`. The author may add a "Navigation" section that lists the folders the agent works in, with paths relative to the installation root, so the same agent works on any machine where that root is the same repository. rbtv does not read that section. rbtv gives the model the body of `agent.md`, without its frontmatter, on every launch path.

## rbtv agent

An rbtv agent is an agent that has a folder holding `agent.md` (its prompt) and `agent.json` (its description, harness, model, effort, chosen units and packs, and the record of generated files). An rbtv agent lives anywhere and is managed in place; `.rbtv/agents/<name>/` is where one is found by name. The [`rbtv` command](rbtv-command.md) manages it with the agent verbs, `rbtv agent add | remove | configure | update | list`, each taking the agent as a name or a folder path. Adding it writes the [generated files](scaffolding.md) inside the agent's own folder:

```text
<agent folder>/
|-- agent.md          (the agent file: the prompt; shared through git)
|-- agent.json        (the agent record; shared through git)
|-- settings.json     (values the agent reads for its job; per machine)
|-- .gitignore        (written by rbtv: keeps per-machine data out of git)
|-- memory/
|   `-- learned.md    (learned rules; the dreamer writes this)
|-- _artifacts/
|   `-- board.md      (short-term memory)
|-- <harness files>   (generated files: folder instructions, loaders for selected units)
`-- <live data>       (conversations and their history, written while the agent runs)
```

Terms: [`agent.json`](agent-json.md), [`settings.json`](settings-json.md), and [folder instructions](folder-instructions.md), where rbtv writes the agent section: a pointer to `agent.md`. The agent reads a conversation's history when the recent messages are not enough, so that history is a [cognitive unit](cognitive-unit.md) too.

**Shared through git:** `agent.md` and `agent.json`, the agent's definition. The agent's `memory/` folder and `_artifacts/board.md` are also tracked in git. Nothing in these shared files holds a path or a time, so the same agent works on every machine.

**Per machine:** the generated files, which `rbtv agent update` rebuilds on each machine from `agent.json`; `settings.json`; and the live data. The `.gitignore` keeps them out of git. The user can override it, which is safe only when one machine runs the agent at a time.

The agent folder is self-contained: everything the agent is and has done lives in it, so it can be its own git repository and be shared between installations.

## Memory on a turn

Every turn, including a scheduled wake, receives the shared general-memory [profile](profile.md), this agent's [learned rules](learned-rules.md), this agent's [board](board.md), the general-memory [index](memory-index.md), and the [inbox](inbox.md). [Workspace memory](workspace-memory.md) is added only when the working directory is under that file's declared paths. The agent maintains the board. It never writes learned rules. The [dreamer](dreamer.md) writes those, and the agent's topic files. A scheduled wake starts a fresh conversation bound to no thread. The board holds the check's details. `ignite post --thread` continues an existing thread and joins that thread's history.

## Ignite agent

An rbtv agent connected to Ignite: the Ignite [pack](pack.md) is on and a Slack channel or a direct message wakes it. The pack holds the standard units of an Ignite agent, for Slack communication and Ignite's behaviour. `ignite connect` turns the pack on through `rbtv` and connects the agent to one Slack channel or to direct messages (`--dm`). It records that connection in the machine's [`config/ignite/config.json`](ignite-config.md), never in the agent folder, so sharing an agent never connects it twice. It also creates the agent's board, its database and its `conversations/` folder. Ignite connects only agents that live under `.rbtv/agents/`. `ignite disconnect` removes the Slack route and turns the pack off. An Ignite agent changes itself with `ignite manage add|remove|configure|update`, which runs `rbtv agent` for it; it reads the catalog with `ignite manage models|list|search|show`. Outside a turn the change verbs are refused.

Ignite's waking program then runs one agent turn for each message in the agent's channel: a reply in a thread continues that thread's conversation, and a new message in the channel starts a new one. The agent can also set timers that wake it. The waking program runs on Linux only, a deliberate restriction that keeps Ignite simple, so an Ignite agent's Slack side runs on a Linux machine.

## Running an agent

Whoever launches an agent hands it its `agent.md` prompt as its instructions, through the harness's strongest channel: a system prompt in Claude Code, developer instructions in Codex, and the first message in OpenCode. The agent section of the agent folder's folder instructions points to `agent.md` as well, so the agent finds its instructions again after the harness shortens a long conversation.

- **Through Slack**, when it is an Ignite agent: each message, or a timer, supplies the task.
- **`spark AGENT`**: interactively, a person opens the agent. `spark` is a tool of the `cast` component.
- **`cast -rbtv AGENT`**: launched by another agent, which passes the task.
- **`cast -rogue FILE`**: a rogue agent: a prompt file with no folder that is not an rbtv agent, launched with `cast`'s inline arguments for harness, model, and effort.

Ignite, `cast -rbtv` and `spark` all use the agent's own harness, model, and effort, as recorded in its `agent.json`. `rbtv agent configure` is the only command that changes them. `spark`, `cast -rbtv` and Ignite set `RBTV_AGENT_HOME` to the agent's folder; the Ignite commands that act for an agent, such as `ignite board`, `ignite remember` and `ignite manage`, use it.

## Sub-agent

An agent launched by another agent. Any agent that an agent launches through `cast` is a sub-agent, whatever its kind. Some harnesses, such as Claude Code and Codex, launch sub-agents of their own, but only on their own harness and models; `cast` lets an agent launch a sub-agent on any harness and model. Some harnesses also let a person start a sub-agent directly; `spark` is the route rbtv offers for that interactive use.

A sub-agent is not a cognitive unit of the agent that launches it. Like a [tool](tool.md), it shapes that agent's [context window](context-window.md) indirectly: it gives the work a fresh context window, access to other models and their different views, and specialized agents to distribute tasks to.

## Harness-native sub-agent

A file in a harness's own sub-agent format, shipped by a component in its `sub-agents/` folder: `.claude/agents/<name>.md` for Claude Code, `.opencode/agents/<name>.md` for OpenCode, or `.codex/agents/<name>.toml` for Codex. It is called through that harness's own tool, by an agent, and where the harness allows it, by a person. It is not an rbtv agent and not an [exposure method](exposure-method.md) of rbtv's agent kind. An rbtv agent, by contrast, can be called by a person or by an agent.
