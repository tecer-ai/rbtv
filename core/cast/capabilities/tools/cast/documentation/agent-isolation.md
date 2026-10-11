# Agent isolation

When cast, Spark or Ignite launches an rbtv agent, the harness loads only what the agent folder holds. This page states what each harness loads from parent folders when nothing stops it, what the launch passes to stop it, and what the launch does not cover. Read it before changing `lib/isolation.js`, and when an agent loads something its folder does not hold or fails to load something it does.

## Goal

What an agent has is what rbtv installed in its folder: instruction files, rules, skills, commands, sub-agents, settings, hooks and MCP servers. Nothing reaches the agent from a folder above it, and the harness's native memory is off. An agent therefore behaves the same wherever its folder sits, and it loses the instructions, skills and memory of the installation around it. That loss is intended.

Whoever launches the agent names the agent folder and nothing else. `lib/isolation.js` is the only file that knows what each harness is passed.

## When it applies

Isolation applies when the launcher holds the agent folder:

- `cast --agent`, headless or `--headed`, and each fallback run of that launch;
- `cast resume` in a launch folder that holds `prompt.md` and `agent.json`;
- `spark`, which launches through `cast --agent --headed`;
- an Ignite turn whose request names `agentHome`, new or resumed.

It never applies to a launch that names no agent: `cast <harness> <model> <effort>`, `--rogue`, `cast resume` in any other folder, and an Ignite turn request without `agentHome`. Such a launch loads its parent folders' files as the harness does by itself, including when its launch folder is an agent folder. The launcher's own knowledge of the agent decides this; the working folder and the `RBTV_AGENT_HOME` variable are never read for it.

Every launch, of either kind, first removes from the environment it inherited the five OpenCode variables of the table below, then sets its own. A launch that names no agent therefore keeps none of them when an isolated agent runs it. A user who sets one of those five variables in a shell loses it in every cast launch.

## What each harness loads, and what the launch passes

Each table lists what the harness loaded from parent folders in the measured run with nothing passed, then each thing the launch passes and what it stops. `<agent folder>` is the agent folder's absolute path.

### Claude Code

With nothing passed, Claude Code loaded from the folders above the working folder: instruction files and rules of every parent folder; skills, commands, sub-agents and workflows of the parent folders inside the git repository; the MCP servers of every parent folder's `.mcp.json`, started with no approval in a headless run; and the hooks and `env` of `.claude/settings.local.json` at the root of the git repository.

| The launch passes | What it stops |
|---|---|
| The agent folder as working folder, holding [the empty `.git` folder](#the-empty-git-folder) | Parent skills, commands, sub-agents, workflows and output styles, and the hooks and `env` of the repository root's `settings.local.json`. It also makes Claude Code keep auto memory under the agent folder's name instead of the repository's |
| `--settings '<json>'` with `claudeMdExcludes`: for every folder above the agent folder, up to the top-level folder, the paths `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/CLAUDE.md`, `.claude/AGENTS.md` and `.claude/rules/**`; for the user's home folder only the first three | Parent instruction files and rules. The paths are listed one by one because every pattern not built from those folders also removed the agent's own files |
| `--strict-mcp-config` | Every MCP server not named on the command line: those of parent folders, the home-level ones and the account's |
| `--mcp-config <agent folder>/.mcp.json`, only when that file exists | Nothing: it gives back the MCP servers of the agent's own file. With no file, the agent has no MCP server. It is left out for a missing file because Claude Code then refuses to start (`Invalid MCP configuration: MCP config file not found`, exit 1) |
| `autoMemoryEnabled: false`, in the same `--settings` object | Auto memory |

### Codex

With nothing passed and the repository root trusted, Codex loaded from the folders above the working folder: `AGENTS.md`, the skills of `.agents/skills` and `.codex/skills`, and from every parent `.codex/` the configuration, MCP servers, hooks, command rules and sub-agent roles.

| The launch passes | What it stops |
|---|---|
| `-c 'project_root_markers=[]'` | Everything above. Codex looks for a project root above the working folder and loads every `.codex/` on the way; with no root marker it stops at the working folder |
| `-c 'projects={"<agent folder>"={trust_level="trusted"}}'` | Nothing: it makes Codex load the agent's own files whatever trust the folders above have. Without it the agent's `.codex/` loads only when a trust entry of a folder above covers the agent folder, and its `AGENTS.md` is dropped when the repository root is marked untrusted |
| `--disable memories` | The `memories` feature |

Not passed: `--disable plugins`, which also removes the home-level plugin marketplaces.

The agent's own hooks run, and no parent hook does, because every Codex start carries `--dangerously-bypass-hook-trust` whether or not it launches an agent; [cast](../cast.md#agent-launches---agent---rogue) states that option and its cost.

### OpenCode

With nothing passed, OpenCode loaded from the parent folders up to the root of the git repository, and from none above it: `AGENTS.md`, the files its `instructions` setting names, commands, sub-agents, skills, the MCP server definition and plugins.

OpenCode takes no argument for this, so the launch sets five environment variables. The first two also remove the agent's own files and the home-level skills and instructions; the other three give those back.

| The launch sets | What it does |
|---|---|
| `OPENCODE_DISABLE_PROJECT_CONFIG=1` | Stops every project file, the agent's own included |
| `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` | Stops the skills OpenCode takes from other harnesses' folders: the home-level `~/.claude/skills` were gone with it set |
| `OPENCODE_CONFIG_DIR=<agent folder>/.opencode` | Gives back the agent's `.opencode/`: sub-agents, commands, skills and plugins |
| `OPENCODE_CONFIG=<agent folder>/opencode.json` | Gives back the agent's settings, MCP servers, and the commands and sub-agents that file defines |
| `OPENCODE_CONFIG_CONTENT=<one JSON object>` | Gives back the instruction files and the skills folders, named below |

`OPENCODE_CONFIG_CONTENT` holds `instructions`: the agent folder's `AGENTS.md`, each entry of the `instructions` key of its `opencode.json` made absolute (a URL, a `~/` path and an absolute path stay as written), and the home-level `AGENTS.md` of OpenCode's configuration folder. The entries are made absolute because a relative one is not loaded under the first variable. It also holds `skills.paths`: `.claude/skills` and `.agents/skills` of the agent folder and of the user's home folder. A file or folder of these that does not exist is left out, and an `opencode.json` that is missing or cannot be parsed counts as naming no instruction file.

## The empty `.git` folder

Every agent folder holds an empty folder named `.git`. The [installer's decision D33](../../../../../rbtv/capabilities/tools/rbtv/documentation/design-decisions.md) states which `rbtv` commands create it, why it is empty and why git does not carry it.

Only Claude Code needs it. Claude Code has no argument that stops parent skills, commands, sub-agents and the repository root's local settings; it stops looking for them at a folder that holds `.git`. On Codex the folder alone stops only parent `AGENTS.md` and `.agents/skills`, and `project_root_markers=[]` isolates with the folder present or absent. On OpenCode the folder changes nothing.

An agent folder that lacks it, such as one received through git on another machine, is still launched: on Claude Code the agent then loads parent skills, commands, sub-agents and the repository root's local settings. cast does not create the folder.

## Native memory

| Harness | Memory | How it is turned off |
|---|---|---|
| Claude Code | Auto memory: a folder per project under `~/.claude/projects/`, whose index is put in the system prompt and which the agent may write | `autoMemoryEnabled: false` in the `--settings` object. The setting is used, not the environment variable `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, because a variable is inherited by every launch the agent makes |
| Codex | The feature `memories`: files under Codex's home folder put in the instructions, and a background task that writes new ones | `--disable memories`, which wins over an enabled feature |
| OpenCode | None | Nothing to turn off |

## What stays loaded

The user's home-level configuration stays loaded on every harness, with one exception: on Claude Code the home-level MCP servers and the account's are not loaded, because an agent has only the MCP servers of its own folder.

- Claude Code: the exclusion list leaves out the home folder's `.claude/CLAUDE.md`, `.claude/AGENTS.md` and `.claude/rules/**`.
- Codex: the configuration, rules, skills and plugins of `~/.codex`.
- OpenCode: the skills of `~/.claude/skills` and `~/.agents/skills` and the home-level `AGENTS.md`, which the launch gives back.

## Limits

- The agent can open any file with its own tools, parent folders included. Isolation covers what the harness loads by itself.
- A sub-agent that a harness starts by itself does not pass through cast; what it loads was not measured.
- `--headed` launches and resumed sessions receive the same arguments and variables. Each harness's help lists every argument for those forms; no interactive session was measured.
- Only the path the launcher was given is walked. An agent folder reached through a symbolic link has a second path whose parent folders are not listed for Claude Code.
- OpenCode keeps the repository around the agent folder as its project, so the agents under one repository share a project in OpenCode's session store. When `.opencode/` is loaded, OpenCode writes into it (`.gitignore`, `package.json`, `package-lock.json`, `node_modules/`).

## Not tested

- Windows: nothing was run there. The paths of the exclusion list and of the Codex trust entry are built with the system's separator.
- Claude Code: whether listing a parent `AGENTS.md` matters (a parent `AGENTS.md` never loaded, with or without the list); whether the home folder's `.claude/` files stay loaded as the list intends; plugins, managed policy files and `--add-dir`.
- Codex: the effect of `--disable memories` on the prompt (only the feature's state was observed); a managed or system configuration that sets `project_root_markers` back; `AGENTS.override.md`.
- OpenCode: the home-level `AGENTS.md` given back through `instructions`; an agent folder outside any git repository; custom tools, `mode/` files and `tui.json` in parent folders.

Measured on Claude Code 2.1.296, Codex 0.162.0 and OpenCode 1.17.18, on Linux, in headless runs.
