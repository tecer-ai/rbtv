# Agent

An agent is a model at an effort, a harness and scaffolding, launched with a task. For an rbtv agent, `agent.json` holds the model, effort and harness, and the scaffolding is its prompt (`agent.md`) plus the files and packs `agent.json` selects. [Scaffolding](scaffolding.md) includes the prompt and other material the agent receives; the harness itself is not scaffolding.

Use an agent when work needs a separate context and a standing prompt must support different tasks. The description must let a caller select the agent and supply its task without first reading the prompt.

## Files and placement

An agent folder contains:

- `agent.md`: the prompt, with name-only frontmatter matching the folder name.
- `agent.json`: the record, with the same name, its description and any installation selections. Follow [Agent record](agent-json.md) when writing or changing the record.

A component ships an agent folder as `agents/<name>/`. Any other agent folder may sit anywhere, such as a plan's `agents/` folder.

Write the prompt using [Prompt](prompt.md). A shipped record contains no harness, model or effort choice; those belong to the installation. Keep machine-specific paths, accounts, channels and credentials out of both source files.

| Placement | Prompt read by the model | Installation selections |
|---|---|---|
| rbtv agent | `agent.md` in the agent folder, which is the working folder. A shipped agent added by name is first copied to `.rbtv/agents/<name>/` | The record's files and packs are installed in that folder |
| Harness sub-agent | The generated harness file points to source `agent.md` and copies the description | The record's selections are not installed; the sub-agent uses what the target already has |

An agent folder may be anywhere and is addressed by its path. A name without a path resolves under `.rbtv/agents/`. For an rbtv-agent placement, the installer supplies missing launch settings and a generated pointer to the prompt in folder instructions.

When sharing an agent folder through git, track its prompt, record and any memory or board it maintains. Keep machine-local [settings](settings-json.md) and harness session data out of that shared content; regenerate harness files in each installation.

An agent written for one task or one plan is an rbtv agent too. Write its folder where the work is, install it in place with `rbtv agent add FOLDER --harness H --model M --effort E`, and launch it with `cast --agent FOLDER`. [rbtv CLI](rbtv-cli.md) owns those options; the model is one of the installation's [selected models](../../../cast/capabilities/glossary/selected-model.md), which `cast models list` prints.

## Build the agent

Identify the work that needs separate context and two tasks the same prompt must support. Use the user's stated purpose rather than inventing a reason for delegation. If the work can stay in the caller and needs no standing function, revisit [Choosing what to build](../choosing-what-to-build.md).

Write the prompt first. Then use [Routing table](routing-table.md) for the record's description:

- CONTAINS distinguishes the standing function and method.
- PURPOSE names the result and inputs the launcher must put in the task, not launch settings.
- ALWAYS LOAD WHEN identifies a reason to launch this agent.
- DO NOT LOAD WHEN identifies a similar task for another agent or no launch.

These conditions select launches, not messages arriving after a channel is connected. Keep the description usable in a shortened listing and consistent with the prompt's function.

List installation selections only for the rbtv-agent placement. The prompt must not assume that merely listing a skill makes it available in harness-sub-agent placement. State the action for a missing dependency as Prompt requires.

## Edit, convert and test

Keep the folder name, prompt frontmatter and record name equal on renaming. Edit the authoritative source. Regenerate a harness-sub-agent placement after changing the description; its pointer reads source-body edits directly. An rbtv-agent launch reads `agent.md` in its folder. A shipped agent added by name runs from its copy in `.rbtv/agents/<name>/`: after changing the component's source, edit that copy or remove the agent and add it again. See [rbtv CLI](rbtv-cli.md) for the operation.

For an outside agent, put its standing instructions in the prompt and its description in the record. Keep model settings, permissions and tool configuration out of prompt prose; classify other content through Choosing what to build.

Test discovery from the description alone against a neighboring agent. The selected launch must carry all required inputs. Test the prompt separately through its intended placement, including missing dependencies. Installer acceptance checks the folder and records, not task selection or behavior.
