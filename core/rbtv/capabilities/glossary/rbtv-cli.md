# rbtv CLI

The rbtv command-line interface scans source files, validates their records and writes the files each harness receives. Its `providers` verbs manage [provider](provider.md) accounts instead: they read no source and write no harness file, and [Provider accounts](../tools/rbtv/documentation/providers.md) owns them. Authors maintain the source. A successful install proves recognition and field validation, not that an agent will select or follow the instructions correctly.

The program is `core/rbtv/capabilities/tools/rbtv/install.py`. Its tool page, [rbtv](../tools/rbtv/rbtv.md), routes to the pages kept with the program. Use `rbtv -h` and its Discover commands to list, search and show existing material before creating another file for the same work: `list` gives a table of the entries under an exact name, `search` finds the modules, components, files and packs whose name or description holds every word, and `show` gives everything about one named entry.

## Source recognition

The scan reads the repository and the installation's `.rbtv/mirror/` as `<module>/<component>`, no deeper. A mirror component replaces a repository component with the same identity as a whole. Names starting with `.` are skipped; `_hub` and `_skills` are not repository modules.

A module with no component folder is skipped. A module containing a component needs `<module>.json`. A component with `skills/`, `rules/`, `commands/`, `hooks/`, `mcp-servers/`, `capabilities/` or `folder-instructions/` needs `<component>.json`; one containing only `agents/` or `packs/` without that record is skipped. Missing required records are refused. Two components with the same name in different modules are refused as `component-duplicate`, because that name alone names the component's [configuration](config.md) and [runtime](runtime.md) folders; a mirror component replacing the repository component of the same module is not a duplicate. Their fields are governed by [module-json.schema.json](../templates/module-json.schema.json) and [component-json.schema.json](../templates/component-json.schema.json).

The scan validates frontmatter or JSON. It does not evaluate prose bodies. Under `capabilities/`, it reads only a tool record and the executable's first line for validation; other pages are read directly by agents through routes.

| Source in a component | Authoring page | Schema |
|---|---|---|
| `skills/<name>.md` | [Skill](skill.md) | [skill](../templates/skill.schema.json) |
| `commands/<name>.md` | [Command](command.md) | [command](../templates/command.schema.json) |
| `rules/<name>.md` | [Rule](rule.md) | [rule](../templates/rule.schema.json) |
| `agents/<name>/prompt.md` and `agent.json` | [Agent](agent.md); [Prompt](prompt.md) for the body | [agent-json](../templates/agent-json.schema.json) |
| `folder-instructions/<name>.md` | [Folder instructions](folder-instructions.md) | [folder-instructions](../templates/folder-instructions.schema.json) |
| `hooks/<name>.json` | [Hook](hook.md) | [hook](../templates/hook.schema.json) |
| `mcp-servers/<name>.json` | [MCP server](mcp-server.md) | [mcp-server](../templates/mcp-server.schema.json) |
| `packs/<name>.json` | [Pack](pack.md) | [pack](../templates/pack.schema.json) |
| `capabilities/tools/<tool>/<tool>.json` | [Tool](tool.md) | [tool-json](../templates/tool-json.schema.json) |

Open the authoring page for the source being changed and its schema when changing validated fields. Use [Module](module.md) or [Component](component.md) when their boundaries change. For their records, read [Module record](module-json.md) or [Component record](component-json.md); for a tool’s record, read [Tool record](tool-json.md). A [capability](capability.md) is not installed; putting its text in an installable folder with valid frontmatter instead exposes it as that folder's kind.

The scanner silently skips the index names `skills.md`, `rules.md`, `commands.md`, `hooks.json`, `mcp-servers.json` and `folder-instructions.md`, and files with the wrong extension. There are no source-folder index files to install.

For named records, `name` equals the file stem; folder instructions have no `name`. Skills, commands, rules, hooks, MCP servers and both agent files use `^[a-z0-9][a-z0-9-]*$`. The `rbtv-` prefix is separately reserved and yields `REFUSED [name-reserved]`. Tool names equal their folder name and are not checked against that pattern or reserved prefix. The installer does not detect a command name that conflicts with a harness's built-in name; check that through [Command](command.md).

An agent's folder name and record name must agree. Shipped component records cannot name `harness`, `model` or `effort`. The obsolete source folder `sub-agents/` is refused; use the agent folder format.

A self-contained mirror skill is the exception: `.rbtv/mirror/_skills/<name>/SKILL.md`. It is recognized only there, requires a frontmatter block and is not checked against the skill schema; extra keys are retained in its copy. Listings show its `description`, written on one line or as a `>` or `|` block. Its folder name cannot start with the reserved `rbtv-` prefix.

## What is generated

| Kind | Claude Code | Codex | OpenCode |
|---|---|---|---|
| Skill copy | `.claude/skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md` | `.claude/skills/<name>/SKILL.md` |
| Self-contained skill copy | `.claude/skills/<name>/`, the whole folder | `.agents/skills/<name>/`, the whole folder | `.claude/skills/<name>/`, the whole folder |
| Command copy | `.claude/commands/<name>.md` | `.codex/prompts/<name>.md` | `.opencode/commands/<name>.md` |
| Rule | `.claude/rules/<name>.md` | `.agents/skills/<name>/SKILL.md`, the rule as a skill | `.claude/rules/<name>.md`, listed in `opencode.json` under `instructions` |
| Native sub-agent | `.claude/agents/<name>.md` | `.codex/agents/<name>.toml` | `.opencode/agents/<name>.md` |
| Hook | `.claude/settings.json` | `.codex/hooks.json` | No hook file; a warning can accompany exit 0. |
| MCP server | `.mcp.json` | Block in `.codex/config.toml` | `opencode.json` |

A skill or command copy carries generated frontmatter and the source body. A skill's frontmatter holds the name and description; a command's holds the description for Claude Code and OpenCode, and Codex receives none. A link written from the source's folder, the repository root or `.rbtv/` becomes the absolute path of its target on this machine; a path inside a code span is left as written. The copy of a self-contained skill keeps its own frontmatter and every file of its folder except symlinks, `.git`, `node_modules` and `__pycache__`, so its relative links open inside the copy. A native sub-agent file is a pointer naming the absolute path of the agent's prompt. The generated marker follows the frontmatter and says edits will be overwritten; in a self-contained skill only `SKILL.md` carries it. Component folder instructions sit between `<!-- rbtv:start <label> -->` and `<!-- rbtv:end <label> -->`; text outside those markers is retained.

A rule reaches each harness through that harness's own channel, and never through `AGENTS.md`. The copy in `.claude/rules/` is the whole source file with its links made absolute. Claude Code reads that folder. OpenCode reads no rules folder: rbtv lists every rule copy in `opencode.json` under `instructions`, sorted, by paths relative to the installation, so the file reads the same on every machine. rbtv owns that key: it removes the key with the last rule, and refuses to write it when the file already holds an `instructions` key rbtv did not write. For Codex the rule is a skill: generated frontmatter with the rule's name and one fixed description, which carries that name and tells the model to open the skill when a session starts, then the rule's body. A rule and a skill with the same name cannot both be installed for Codex; rbtv refuses the run.

Component folder instructions lose frontmatter and are written as marked sections in the target folder's instruction files. Target `.` means the installation root. The installation maintains one instructions filename and generates the other when a selected harness needs it. If every selected harness reads the maintained name, no second file is needed. Guidance copies start with `GENERATED by install.py — DO NOT EDIT.`

Codex joins every `AGENTS.md` from the project root down to the working folder, and its default combined limit is 32 KiB; a guidance copy with component sections, plus the copies in nested folders, can pass it. rbtv writes `project_doc_max_bytes = 131072` at the top of the installation's `.codex/config.toml`, which Codex uses in a trusted folder. Text beyond the effective limit is still cut. [Harness](harness.md) distinguishes generated files from verified runtime discovery.

A tool gets a shortcut in `~/.rbtv/bin` pointing to its executable, not an installed executable copy. The `entry` resolves inside the component. A `ws:` entry instead resolves from the installation root, must be relative and cannot contain `..`. Missing shebang or, on POSIX, missing executable permission yields `path-not-runnable`. JSON files in the tool folder whose stem differs from the folder name are skipped.

A pack generates no file of its own. `rbtv add --pack NAME` installs its members; a bare name never selects a pack.

## Select the target and placement

To configure an installation before selecting files, use `rbtv configure --harness HARNESS --guidance BASIS`. Choose `none` when no maintained folder-instructions file exists; `CLAUDE.md` or `AGENTS.md` must already exist at the target root when selected as the basis.

For a file not yet installed, use `rbtv add NAME`. The first add also needs `--harness` (`claude`, `codex` or `opencode`) and `--guidance` (`CLAUDE.md`, `AGENTS.md` or `none`). Later adds may omit those settings.

Use `--target D` to select the installation explicitly, especially for a test. Without it, selection is:

1. `RBTV_AGENT_HOME` when set. An empty value or nonexistent directory is refused as `agent-home-invalid`.
2. Otherwise, the first ancestor of the current directory containing `.rbtv/config/install.json` or `agent.json`. An agent folder found this way without its `prompt.md` is refused as `prompt-missing`.
3. Otherwise, the first ancestor containing a `.rbtv/` directory, excluding the home directory.
4. Otherwise, the current directory.

A run from a source repository with no explicit target or enclosing installation can therefore write into that repository.

Choose agent placement deliberately:

- `rbtv add NAME --on HARNESS:MODEL:EFFORT` writes a harness-native sub-agent. Repeat per selected harness. Model and effort are checked with `cast models list`, run from the target: the model must be one the installation selected. The agent's requested file list is reported as unapplied; the sub-agent receives what its target already has.
- `rbtv agent add AGENT --harness HARNESS --model MODEL --effort EFFORT` installs an rbtv agent and its requested files. Supply those launch fields only when absent from its record; change existing values with `rbtv agent configure`. Agent verbs take no `--target`, except `rbtv agent list --target FOLDER`, which lists the agents of that folder as `cast list --agents --target FOLDER` reads it. By name, the prompt and record are copied to `.rbtv/agents/<name>/`, with no other source-folder files. A path uses the folder in place.

A component explicitly named to `rbtv add module/component` includes its shipped agents and therefore needs `--on` when agents are present. Selections through `--all`, `--module`, `--component` or `--type` skip agents and report that skip. Use agent add for rbtv-agent placement.

## Interpret results and refresh changes

An accepted add exits 0 and names selected `module/component#name` identifiers. A refusal exits 1 with `REFUSED [code]`, or a JSON refusal under `--json`; a usage error exits 2. If a short name produces `name-unknown`, try `rbtv add module/component` to expose the underlying schema error before moving or renaming the file.

A pass proves the checked fields and recognized kind, and outside a dry run the applicable generation. It does not prove instruction quality, selection boundaries, complete routes, runtime loading or correct behavior. A successful component scan says nothing about an ordinary capability page. Hook and server runtime checks belong to their entries.

Edit the source, then choose the refresh that reaches the reader:

| Change | Required refresh |
|---|---|
| Skill or command body, name or description, or a file of a self-contained skill | `rbtv update scaffolding`, and `rbtv agent update AGENT scaffolding` for each agent that has it. Each machine runs them after it receives the source change; the copies are machine-local. `rbtv add NAME` and `rbtv update all` also rewrite the copy. |
| Rule body, name or description | `rbtv update scaffolding`, and `rbtv agent update AGENT scaffolding` for each agent that has it, on each machine. It rewrites the rule file Claude Code and OpenCode read, the Codex skill and the `opencode.json` list; a hand edit to any of them is lost. |
| Component folder-instruction section | Add or scaffolding regeneration; a hand edit inside generated markers is lost. |
| Maintained folder instruction file's copy under the other harness name | `rbtv update guidance`. It rebuilds no copy or managed section; with guidance `none` it can succeed without writing anything. |
| Both scaffolding and guidance | `rbtv update all`, in that order. |
| Mirror replacement added or removed while the repository still supplies that component | `rbtv update all`; inspect the selected source and resulting files. |
| Agent's generated scaffolding | `rbtv agent update AGENT scaffolding` or `rbtv agent update AGENT all`. |

The installer owns `.rbtv/config/install.json`. If that record or an agent's `agent.json` is edited, scaffolding or all applies its settings. Test refreshes in an isolated installation: change a description, confirm guidance alone leaves the listing unchanged, then confirm scaffolding updates it. This distinguishes a successful invocation from the intended reader actually receiving the change.
