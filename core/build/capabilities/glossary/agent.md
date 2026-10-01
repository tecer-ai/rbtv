# Agent

An agent is a [prompt](prompt.md) given to an AI model, which processes the prompt, through a [harness](harness.md). A user or another agent supplies its work, a [task](task.md), at runtime.

## Agent file

An agent is defined by its agent file, `agent.md`: its prompt, with frontmatter (structured metadata at the top of the file) that names and describes the agent, selects the skills, rules, commands, [hooks](hook.md), and [MCP servers](mcp-server.md) it uses, and lists its key folders. Its fields are defined by its [schema](schema.md), and its prompt's sections by its [template](template.md). Key folders are the folders the agent is expected to work in and navigate, written relative to the installation root so that one root can be shared across machines. The agent file holds no harness, model, or effort: they are chosen when the agent is installed or launched. A component can ship agent files in its `agents/` folder.

## Installed agent

`rbtv install` installs an agent from its agent file into its own agent folder, `.rbtv/agents/<agent>/` under the installation root. Whoever installs it chooses its harness, model, and effort. The [installer](rbtv-installer.md) [scaffolds](scaffolding.md) the agent folder as it does any target folder:

```text
.rbtv/agents/<agent>/
|-- agent.md          (the agent file: the agent's single source)
|-- launch.json       (harness, model, and effort)
|-- settings.json     (agent-specific values the agent reads)
|-- .rbtv/config/install.json   (what the installer installed here)
|-- memory/
|   `-- learned.md    (learned rules; the dreamer writes this)
|-- _artifacts/
|   `-- board.md      (short-term memory)
|-- <harness files>   (generated: folder instructions, loaders for selected units)
`-- <live data>       (conversations and their history, written while the agent runs)
```

Terms: [`launch.json`](launch-json.md), [`settings.json`](settings-json.md), [`install.json`](install-json.md), and [folder instructions](folder-instructions.md), where the installer writes the agent section: a pointer to `agent.md` and the agent's key folders. A shipped agent file is copied into the folder on install; from then on, the copy in the folder is the source. Running the installer again regenerates everything else from it. The agent reads a conversation's history when the recent messages are not enough, so that history is a [cognitive unit](cognitive-unit.md) too.

The agent folder is self-contained: everything the agent is and has done lives in it, so it can be its own git repository and be shared between installations. The installation root is always three folders above it, so nothing inside stores that path. Files the installer generates are rebuilt by running the installer in each installation, never shared as they are. The agent's `memory/` folder and `_artifacts/board.md` are tracked in git. The installer writes an ignore file, `.gitignore`, that keeps data tied to one machine, such as the harness sessions an agent resumes, out of git; the user can override it, which is safe only when one machine runs the agent at a time.

## Memory on a turn

Every turn, including a scheduled wake, receives the shared general-memory [profile](profile.md), this agent's [learned rules](learned-rules.md), this agent's [board](board.md), the general-memory [index](memory-index.md), and the [inbox](inbox.md). [Workspace memory](workspace-memory.md) is added only when the working directory is under that file's declared paths. The agent maintains the board. It never writes learned rules. The [dreamer](dreamer.md) writes those, and the agent's topic files. A scheduled wake starts a fresh conversation bound to no thread. The board holds the check's details. `ignite-agent post --thread` continues an existing thread and joins that thread's history.

## Ignite agent

An installed agent that also receives the standard Ignite cognitive units, for Slack communication and Ignite's behaviour, and a Slack connection. Ignite's install step runs `rbtv install` for the agent and adds those units. Its units come only from its agent file and Ignite's standard list: `ignite-agent update` removes any unit in the agent folder selected by neither, including one installed there by hand. To give the agent a unit, list it in its agent file. Ignite's connect step, run on the machine where the agent will run, connects the agent to one Slack channel and records that connection in the machine's [`config/ignite/config.json`](ignite-config.md), never in the agent folder, so sharing an agent never connects it twice.

Ignite's waking program then runs one agent turn for each message in the agent's channel: a reply in a thread continues that thread's conversation, and a new message in the channel starts a new one. The agent can also set timers that wake it. The waking program runs on Linux only, a deliberate restriction that keeps Ignite simple, so an Ignite agent's Slack side runs on a Linux machine.

## Running an agent

Whoever launches an agent hands it its `agent.md` prompt as its instructions, through the harness's strongest channel: a system prompt in Claude Code, developer instructions in Codex, and the first message in OpenCode. The agent section of the agent folder's folder instructions points to `agent.md` as well, so the agent finds its instructions again after the harness shortens a long conversation.


- **Through Slack**, when it is an Ignite agent: each message, or a timer, supplies the task.
- **`rbtv spark <agent>`**: interactively, from its agent folder, with the harness, model, and effort in its `launch.json` at that moment.
- **`cast -ig`**: launched by another agent, which passes the harness, model, and effort, chosen with `cast route`, and the task.
- **`cast -rg`**: a one-off agent that is not installed, launched with `cast`'s inline arguments: its harness, model, and effort, the agent file's body as its system prompt, and the task. Its frontmatter selections take effect only when the agent is installed.

## Sub-agent

An agent launched by another agent. Any agent that an agent launches through `cast` is a sub-agent. Some harnesses, such as Claude Code and Codex, launch sub-agents of their own, but only on their own harness and models; `cast` lets an agent launch a sub-agent on any harness and model. Where a harness has its own sub-agent definitions, the installer also translates agent files into them.

A sub-agent is not a cognitive unit of the agent that launches it. Like a [tool](tool.md), it shapes that agent's [context window](context-window.md) indirectly: it gives the work a fresh context window, access to other models and their different views, and specialized agents to distribute tasks to.
