# Agent isolation

When cast, Spark or Ignite launches an rbtv agent, the harness loads only what the agent folder holds. This page states what each harness loads from parent folders and from its account folder when nothing stops it, what the launch passes to stop it, and what the launch does not cover. Read it before changing `lib/isolation.js`, and when an agent loads something its folder does not hold or fails to load something it does.

## Goal

What an agent has is what rbtv installed in its folder: instruction files, rules, skills, commands, sub-agents, settings, hooks and MCP servers. Nothing reaches the agent from a folder above it, the harness's native memory is off, and the harness's account folder gives the agent the login and nothing else that a launch can stop. An agent therefore behaves the same wherever its folder sits, and it loses the instructions, skills and memory of the installation around it. That loss is intended.

On this page, a harness's account folder is the folder in the user's home where the harness keeps the login and the user's own configuration: `~/.claude` (with `~/.claude.json`) for Claude Code, `~/.codex` for Codex, and `~/.config/opencode` for OpenCode, whose login is in `~/.local/share/opencode`.

Whoever launches the agent names the agent folder and nothing else. `lib/isolation.js` is the only file that knows what each harness is passed.

## When it applies

Isolation applies when the launcher holds the agent folder:

- `cast --agent`, headless or `--headed`, and each fallback run of that launch;
- `cast resume` in a launch folder that holds `prompt.md` and `agent.json`, which also passes the model and effort of that `agent.json` when it names the resumed harness;
- `spark`, which launches through `cast --agent --headed`;
- an Ignite turn whose request names `agentHome`, new or resumed.

It never applies to a launch that names no agent: `cast <harness> <model> <effort>`, `--rogue`, `cast resume` in any other folder, and an Ignite turn request without `agentHome`. Such a launch loads its parent folders' files and the account folder as the harness does by itself, including when its launch folder is an agent folder.

A launch and an Ignite turn are isolated because the launcher was told which agent it starts; the working folder is not read for it. `cast resume` is the one exception: it has no agent to be told about, so it reads its launch folder and isolates when that folder is an agent folder. The `RBTV_AGENT_HOME` variable is never read for it.

Every launch, of either kind, first removes from the environment it inherited the seven variables an isolated launch sets (`CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` and the six OpenCode variables of the table below), then sets its own. A launch that names no agent therefore keeps none of them when an isolated agent runs it. A user who sets one of those seven variables in a shell loses it in every cast launch.

## What each harness loads, and what the launch passes

Each table lists what the harness loaded in the measured run with nothing passed, then each thing the launch passes and what it stops. `<agent folder>` is the agent folder's absolute path. A relative agent folder is made absolute against the current folder first; cast always passes an absolute one and Ignite refuses a relative one.

### Claude Code

With nothing passed, Claude Code loaded from the folders above the working folder: instruction files and rules of every parent folder; skills, commands, sub-agents and workflows of the parent folders inside the git repository; the MCP servers of every parent folder's `.mcp.json`, started with no approval in a headless run; and the hooks and `env` of `.claude/settings.local.json` at the root of the git repository. From the account folder it loaded the instruction file and rules, skills, commands, sub-agents, the hooks, `env` and permission rules of `settings.json`, the enabled plugins and the user-level MCP servers; and from the Claude account itself, the skills synced to it (13 `anthropic-skills:…` skills in the measured run) and its MCP servers.

| The launch passes | What it stops |
|---|---|
| The agent folder as working folder, holding [the empty `.git` folder](#the-empty-git-folder) | Parent skills, commands, sub-agents, workflows and output styles, and the hooks and `env` of the repository root's `settings.local.json`. It also makes Claude Code keep auto memory under the agent folder's name instead of the repository's |
| `--strict-mcp-config` | Every MCP server not named on the command line: those of parent folders, the user-level ones and the account's |
| `--mcp-config <agent folder>/.mcp.json`, only when that file exists | Nothing: it gives back the MCP servers of the agent's own file. With no file, the agent has no MCP server. It is left out for a missing file because Claude Code then refuses to start (`Invalid MCP configuration: MCP config file not found`, exit 1) |
| `--setting-sources project,local` | The `user` setting source, which is the account folder: its `settings.json` (hooks, `env`, permission rules, defaults), skills, commands, sub-agents and plugins, and the skills synced from the Claude account. The agent's own `.claude/settings.json` and `.claude/settings.local.json` are the two sources named and stay loaded. The login does not depend on the `user` source |
| `--settings '<json>'` with `claudeMdExcludes`: for every folder above the agent folder, up to the top-level folder, the paths `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/CLAUDE.md`, `.claude/AGENTS.md` and `.claude/rules/**` | Parent instruction files and rules. The user's home folder is one of those folders when the agent folder is inside it, so the list then holds the account folder's `CLAUDE.md`, `AGENTS.md` and `rules/`, which `--setting-sources` does not stop. The paths are listed one by one because every pattern not built from those folders also removed the agent's own files |
| `autoMemoryEnabled: false`, in the same `--settings` object | Auto memory |
| The environment variable `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1` | 16 of the 19 skills bundled in the program. No argument or setting stops them together. `claude --help` does not list the variable; it was found in the program and measured |

The order of the arguments matters in one place: `--mcp-config` takes every value up to the next option, so an option always follows it, never the task or another value. `--setting-sources` and `--settings` each take one value and may sit anywhere among the options.

### Codex

With nothing passed and the repository root trusted, Codex loaded from the folders above the working folder: `AGENTS.md`, the skills of `.agents/skills` and `.codex/skills`, and from every parent `.codex/` the configuration, MCP servers, hooks, command rules and sub-agent roles. From the account folder it loaded `config.toml` (default model and effort, trusted folders, enabled plugins and marketplaces, any MCP server and developer instructions), the skills of an enabled plugin, a list of recommended plugins, and the skills bundled in the program, which Codex writes into the account folder's `skills/.system`.

| The launch passes | What it stops |
|---|---|
| `-c 'project_root_markers=[]'` | Everything from the folders above. Codex looks for a project root above the working folder and loads every `.codex/` on the way; with no root marker it stops at the working folder |
| `-c 'projects={"<agent folder>"={trust_level="trusted"}}'` | Nothing: it makes Codex load the agent's own files whatever trust the folders above have, and whether or not `config.toml` is read. Without it the agent's `.codex/` loads only when a trust entry of a folder above covers the agent folder, and its `AGENTS.md` is dropped when the repository root is marked untrusted |
| `--disable memories` | The `memories` feature |
| `--disable plugins` | The account folder's plugins and their skills, and the list of recommended plugins |
| `-c skills.bundled.enabled=false` | The skills bundled in the program |
| `--ignore-user-config`, on `codex exec` and `codex exec resume` only | The account folder's `config.toml`: its MCP servers, plugin and marketplace entries, developer instructions and defaults |

Codex's interactive forms (`codex` and `codex resume`) refuse `--ignore-user-config` with `error: unexpected argument`, so a `--headed` launch goes without it and reads `config.toml`. Every other value above is accepted by every form.

What `config.toml` supplied that a launch needs, the launch passes itself: the model (`-m`), the effort (`-c model_reasoning_effort`), the approval policy (`-c approval_policy=never`) and the trust of the agent folder (the entry above). `cast resume` in an agent folder and an Ignite resumed turn pass the same four, and the resumed turn ran on the agent's model and effort. A Codex resume that is passed no model does not keep the session's model: it ran on the default model of `config.toml`, and on Codex's own default (`gpt-6.1-sol` in the measured run) with `config.toml` ignored.

The agent's own hooks run, and no parent hook does, because every Codex start carries `--dangerously-bypass-hook-trust` whether or not it launches an agent; [cast](../cast.md#agent-launches---agent---rogue) states that option and its cost.

### OpenCode

With nothing passed, OpenCode loaded from the parent folders up to the root of the git repository, and from none above it: `AGENTS.md`, the files its `instructions` setting names, commands, sub-agents, skills, the MCP server definition and plugins. From the user's home it loaded the skills of `~/.claude/skills` and `~/.agents/skills`, the instruction file `~/.claude/CLAUDE.md`, and the content of its account folder.

OpenCode takes no argument for this, so the launch sets six environment variables. The first two also remove the agent's own files; the last three give those back.

| The launch sets | What it does |
|---|---|
| `OPENCODE_DISABLE_PROJECT_CONFIG=1` | Stops every project file, the agent's own included |
| `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` | Stops the skills OpenCode takes from other harnesses' folders, in the user's home and in the agent folder |
| `OPENCODE_DISABLE_CLAUDE_CODE=1` | Stops `~/.claude/CLAUDE.md`, the instruction file of Claude Code's account folder |
| `OPENCODE_CONFIG_DIR=<agent folder>/.opencode` | Gives back the agent's `.opencode/`: sub-agents, commands, skills and plugins. It also replaces the folder the account `AGENTS.md` is read from, so `~/.config/opencode/AGENTS.md` is not loaded |
| `OPENCODE_CONFIG=<agent folder>/opencode.json` | Gives back the agent's settings, MCP servers, and the commands and sub-agents that file defines |
| `OPENCODE_CONFIG_CONTENT=<one JSON object>` | Gives back the agent's instruction files and skills folders, named below |

`OPENCODE_CONFIG_DIR` and `OPENCODE_CONFIG` are set whether or not `.opencode/` and `opencode.json` exist. With both missing, OpenCode started, answered and created `.opencode/` in the agent folder.

`OPENCODE_CONFIG_CONTENT` holds two lists, and nothing from the user's home:

- `instructions`: the agent folder's `AGENTS.md` when it exists, then each entry of the `instructions` key of the agent's `opencode.json`. A relative entry is made absolute against the agent folder, because a relative one is not loaded under the first variable; a URL, a `~/` path and an absolute path stay as written. An entry that is not text is dropped, and an entry listed twice is kept once. The entries taken from `opencode.json` are passed on without a check that the files exist. An `opencode.json` that is missing or cannot be parsed counts as naming no instruction file.
- `skills.paths`: `.claude/skills` and `.agents/skills` of the agent folder, each only when it exists.

## The empty `.git` folder

Every agent folder holds an empty folder named `.git`. The [installer's decision D33](../../../../../rbtv/capabilities/tools/rbtv/documentation/design-decisions.md) states which `rbtv` commands create it, why it is empty and why git does not carry it.

Only Claude Code needs it. Claude Code has no argument that stops parent skills, commands, sub-agents and the repository root's local settings; it stops looking for them at a folder that holds `.git`. On Codex the folder alone stops only parent `AGENTS.md` and `.agents/skills`, and `project_root_markers=[]` isolates with the folder present or absent. On OpenCode the folder changes nothing.

An agent folder that lacks it, such as one received through git on another machine, is still launched: on Claude Code the agent then loads parent skills, commands, sub-agents and the repository root's local settings. cast does not create the folder.

## Native memory

| Harness | Memory | How it is turned off |
|---|---|---|
| Claude Code | Auto memory: a folder per project under `~/.claude/projects/`, whose index is put in the system prompt and which the agent may write | `autoMemoryEnabled: false` in the `--settings` object. The setting is used, not the environment variable `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, because a variable is inherited by every program the agent runs |
| Codex | The feature `memories`: files under Codex's home folder put in the instructions, and a background task that writes new ones | `--disable memories`, which wins over an enabled feature |
| OpenCode | None | Nothing to turn off |

## What an agent still receives

### From the account folder

The login stays on every harness: it is read in place, and the launch neither copies nor moves it. Besides the login:

| Harness | What still reaches an agent |
|---|---|
| Claude Code | Nothing. Claude Code still reads and rewrites `~/.claude.json` (account identity, caches, start counter) on every launch |
| Codex | An account `AGENTS.md` (`~/.codex/AGENTS.md`), the skills of `~/.codex/skills` outside `.system`, and the hooks of `~/.codex/hooks.json`: no argument stops these three. On a `--headed` launch, `config.toml` as well. Codex also keeps its sessions, model list and state files in the account folder |
| OpenCode | The content of `~/.config/opencode/` except its `AGENTS.md`: the global `opencode.json` or `opencode.jsonc` (instructions, MCP servers, commands, sub-agents) and the `command/`, `agent/`, `plugin/`, `skill/` and `skills/` folders. OpenCode has no switch for it that leaves other programs untouched. The login store, the stored MCP sign-ins and the session database in `~/.local/share/opencode/` stay in use |

A file added to either folder reaches every agent on that harness, so the installation's owner keeps both folders free of such content:

- Keep the Codex account folder (`~/.codex`) free of an `AGENTS.md`, skills outside `.system`, hooks (`hooks.json`) and command rules.
- Keep OpenCode's account configuration folder (`~/.config/opencode/`) free of instruction files, commands, sub-agents, plugins, skills and settings content.

No argument, setting or variable excludes this content for an agent alone. A private account folder per agent (`CODEX_HOME` for Codex, `XDG_CONFIG_HOME` for OpenCode) was rejected: it puts the Codex login at risk when the login is refreshed, loses the Codex sessions, and every program the agent runs inherits the variable, which changes where those programs read their own settings.

On the machine measured, `~/.codex` holds no `AGENTS.md`, no skill outside `.system` and no `hooks.json`, and `~/.config/opencode/` holds one `opencode.jsonc` with no setting, so nothing of this table reaches an agent there today.

### From the program itself

Each program brings content of its own that no argument, setting or variable found removes. It is not content of the account folder.

| Harness | What the program brings |
|---|---|
| Claude Code | Three bundled skills (`design`, `doctor`, `plugin-authoring`); 36 slash commands that are not skills (among them `clear`, `compact`, `config`, `init`, `mcp`, `model`, `security-review`, `usage`); five sub-agents (`claude`, `Explore`, `general-purpose`, `Plan`, `statusline-setup`); three built-in plugins (`cc-plugin-agents-md`, `cc-plugin-telemetry`, `cc-plugin-plugin-authoring`); and its own tools. `--disable-slash-commands` removes the slash commands and takes the agent's own skills and commands with them, so it is not passed |
| Codex | Its base instructions and the blocks it adds to every prompt (`<collaboration_mode>`, `<multi_agent_role>`, `<multi_agent_mode>`, `<environment_context>`). The bundled skills leave the prompt with `-c skills.bundled.enabled=false`. With that setting and `--disable plugins`, Codex created no `skills/` folder in a new account folder, where without them it created `skills/.system` with five skills; this was measured on `codex debug prompt-input` only |
| OpenCode | One built-in skill, `customize-opencode` |

## Limits

- The agent can open any file with its own tools, parent folders and account folders included. Isolation covers what the harness loads by itself.
- A sub-agent that a harness starts by itself does not pass through cast; what it loads was not measured.
- An environment variable reaches every program the agent runs. A cast launch removes the seven; a harness the agent starts directly, without cast, keeps them.
- `cast resume` in an agent folder passes a model and an effort only when the folder's `agent.json` names the resumed harness. A session of another harness in that folder, such as one a fallback run left, is resumed isolated on the model that harness picks.
- `--headed` launches receive the same arguments and variables, except Codex's `--ignore-user-config`. Each harness's help lists every other argument for its interactive form; no interactive session was measured.
- Only the path the launcher was given is walked. An agent folder reached through a symbolic link has a second path whose parent folders are not listed for Claude Code.
- OpenCode keeps the repository around the agent folder as its project, so the agents under one repository share a project in OpenCode's session store. When `.opencode/` is loaded, OpenCode writes into it (`.gitignore`, `package.json`, `package-lock.json`, `node_modules/`).

## Not tested

- Windows: nothing was run there. The paths of the exclusion list and of the Codex trust entry are built with the system's separator.
- Claude Code: whether listing a parent `AGENTS.md` matters (a parent `AGENTS.md` never loaded, with or without the list); the real `~/.claude/CLAUDE.md` and `rules/` with content (the exclusion was measured on a stand-in home folder); an account folder moved with `CLAUDE_CONFIG_DIR` to a folder above the agent; an account output style or status line; managed policy files and `--add-dir`.
- Codex: the effect of `--disable memories` on the prompt (only the feature's state was observed); a managed or system configuration that sets `project_root_markers` back; `AGENTS.override.md`; the account folder's prompts and command rules; whether `skills.bundled.enabled=false` stops Codex writing `skills/.system` on `codex exec`, the form a launch uses; the first-run and full-access notices of a `--headed` launch.
- OpenCode: `cast resume opencode last` in an agent folder with the model passed (`opencode run -c -m`; the resume by session id was run); an `instructions` entry that names a missing file; an agent folder outside any git repository; custom tools, `mode/` files and `tui.json` in parent folders or in the account folder.

Measured on Claude Code 2.1.296, Codex 0.162.0 and OpenCode 1.17.18, on Linux, in headless runs.
