# Agent

An agent is a model, a harness and scaffolding launched with a task. Scaffolding includes the prompt and other material the agent receives; the harness itself is not scaffolding.

Use an agent when work needs a separate context and a standing prompt must support different tasks. The description must let a caller select the agent and supply its task without first reading the prompt.

## Files and placement

A component supplies `agents/<name>/` containing:

- `agent.md`: the prompt, with name-only frontmatter matching the folder name.
- `agent.json`: the record, with the same name, its description and any installation selections. Follow [Agent record](agent-json.md) when writing or changing the record.

Write the prompt using [Prompt](prompt.md). A shipped record contains no harness, model or effort choice; those belong to the installation. Keep machine-specific paths, accounts, channels and credentials out of both source files.

| Placement | Prompt read by the model | Installation selections |
|---|---|---|
| rbtv agent | Copy in `.rbtv/agents/<name>/`; that folder is the working folder | The record's skills, rules, commands and packs are installed there |
| Harness sub-agent | The generated harness file points to source `agent.md` and copies the description | The record's selections are not installed; the sub-agent uses what the target already has |
| Managed in place | `agent.md` in the managed folder | Follow the installation record; it may already contain launch settings |

A managed folder may be at an explicit path. A name without a path resolves under `.rbtv/agents/`. For an rbtv-agent placement, the installer supplies missing launch settings and a generated pointer to the prompt in folder instructions.

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

Keep the folder name, prompt frontmatter and record name equal on renaming. Edit the authoritative source. Regenerate a harness-sub-agent placement after changing the description; its pointer reads source-body edits directly. An rbtv-agent launch uses a copy, so update that placement after changing its source. See [rbtv CLI](rbtv-cli.md) for the operation.

For an outside agent, put its standing instructions in the prompt and its description in the record. Keep model settings, permissions and tool configuration out of prompt prose; classify other content through Choosing what to build.

Test discovery from the description alone against a neighboring agent. The selected launch must carry all required inputs. Test the prompt separately through its intended placement, including missing dependencies. Installer acceptance checks the folder and records, not task selection or behavior.
