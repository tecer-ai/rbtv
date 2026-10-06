# rbtv command

The rbtv command is the program that recognizes a source by the folder it sits in and by its file name, checks the fields a schema names, and writes the file a harness reads. Outside rbtv each harness reads its own folders, and a file is not checked against a schema before the harness reads it. In rbtv the author writes the source, and this program writes what each harness reads.

It is for an author who has to know whether a finished file will still be recognized, the file that the program reads, the file that the program writes, and what a pass shows. An author wants it when the work could change that recognition, and when another page sends them here for the command to run and for what a pass shows. Work with it so the next run still recognizes the source, and a pass is not taken for a reading of the body.

## How it fails

A run can exit 0, and the source can still fail at what it is for. The scan keeps the frontmatter or the JSON and discards the body.

- The author stops at a pass. The description does not decide a load, the instructions do not do the work, and a row does not open. The program did not read the body.
- The source sits under `capabilities/`, or the file is named `skills.md`, `rules.md`, `commands.md`, `hooks.json`, `mcp-servers.json`, or `folder-instructions.md`. The program never scans that capability file, or it passes the index name over. The component can still pass. The file is not installed.
- After a description or a name changes, the author runs `rbtv update guidance`. That run can exit 0 and leave the generated file unchanged. The agent, or the human, still matches the old description.
- The author adds a broken file by its short name, reads `REFUSED [name-unknown]`, and moves the file. The schema problem is printed when the component id is added. It is not printed for the short name.
- The author runs `rbtv add NAME --on HARNESS:MODEL:EFFORT` and expects the list in `agent.json` to be installed. The result says that list was not applied. The run can still exit 0. A component source that names `harness`, `model`, or `effort` is refused before either placement.

## What it is composed of

The program is `install.py`, at `core/rbtv/capabilities/tools/rbtv/install.py`. It scans the repository and the installation's `.rbtv/mirror`, each as `<module>/<component>` and no deeper. On a shared id it reads the mirror, not the repository copy. A module, a component or a whole-folder skill whose name starts with `.` is not scanned. In the repository, `_hub` and `_skills` are not modules. A module with no component folder is skipped, and that skip is not a refusal. A component folder that has `skills/`, `rules/`, `commands/`, `hooks/`, `mcp-servers/`, `capabilities/` or `folder-instructions/` and no `<component>.json` is refused; a folder with only `agents/` or `packs/` and no record is skipped. A module that has a component and no `<module>.json` is refused. Those two records are checked against [component-json.schema.json](../templates/component-json.schema.json) and [module-json.schema.json](../templates/module-json.schema.json). This page does not list their fields.

The scan does not read a body, except to copy or paste that body into a file that it writes. It does not read a file under `capabilities/` except `capabilities/tools/<tool>/<tool>.json` and the first line of the program that record names. A file named `capabilities.md` or `glossary.md` is not a file that it installs. A whole-folder skill, `_skills/<name>/SKILL.md`, is recognized only in the mirror. That file is not checked against the skill schema. The scan requires a `---` block, and an extra key in that block is kept.

Open the page that owns the source. The schema file is the authority for the fields. This page does not list them.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN | DO NOT LOAD WHEN |
|---|---|---|---|---|
| [the page "Skill"](skill.md)¹ | how a skill is written, and what the agent receives from the file that the program writes | the source the program recognizes as a skill | the source is `skills/<name>.md` | the source is a command, a rule, or a file under `capabilities/` |
| [the page "Command"](command.md)² | how a command is written, and what the human and the agent receive from the listed file | the source the program recognizes as a command | the source is `commands/<name>.md` | the source is a skill, or the question is only whether a harness already uses the name |
| [the page "Rule"](rule.md)³ | how a rule is written, and what each harness receives from the install | the source the program recognizes as a rule | the source is `rules/<name>.md` | the text is folder instructions, or a skill |
| [the page "Agent"](agent.md)⁴ | the folder, the two placements, and what the record may name | the folder the program recognizes as an agent | the source is `agents/<name>/` with `agent.md` and `agent.json` | the question is only the prompt body |
| [the page "Prompt"](prompt.md)⁵ | the body of `agent.md` | the text the program does not read when it checks that file | the question is the body of `agent.md` | the question is the placement, or a field of `agent.json` |
| [the page "Folder instructions"](folder-instructions.md)⁶ | the file the author maintains, and a component section | the text the program copies under the other harness name, or into a marked section | the file is `CLAUDE.md` or `AGENTS.md`, or `folder-instructions/<name>.md` | the text is a rule |
| [the page "Capability"](capability.md)⁷ | a file the program does not install | a page the agent reads in the source | the file is a page under `capabilities/`, and is neither a record nor a program under `capabilities/tools/` | the file is a skill, a rule, or a command |
| [the page "Module"](module.md)⁸ | the folder of components and its record | the folder the program recognizes as a module | the source is `<module>/<module>.json`, or the folder has no component | the question is one component |
| [the page "Component"](component.md)⁹ | the folder of files and its record, and the folders it may have | the folder the program recognizes as a component | the source is `<module>/<component>/<component>.json`, or a file sits in a folder the program does not scan | the question is one file inside the component |
| [the page "Hook"](hook.md)¹⁰ | how the record of a hook is written | the source the program recognizes as a hook | the source is `hooks/<name>.json` | the source is an MCP server or a tool |
| [the page "MCP server"](mcp-server.md)¹¹ | how the record of a server is written | the source the program recognizes as an MCP server | the source is `mcp-servers/<name>.json` | the source is a hook or a tool |
| [the page "Tool"](tool.md)¹² | how the program and the record of a tool are written | the folder the program recognizes as a tool | the source is `capabilities/tools/<tool>/<tool>.json` | the source is a page under `capabilities/` that is not that record |
| [the page "Pack"](pack.md)¹³ | what a pack lists and what turning it off removes | the source the program recognizes as a pack | the source is `packs/<name>.json`, or a run names `--pack` | the source is one file that a pack names |

The program also recognizes these. The schema file is what it checks the fields against.

- A hook is `hooks/<name>.json`, except `hooks.json`, checked against [hook.schema.json](../templates/hook.schema.json). Claude Code receives it in `.claude/settings.json`. Codex receives it in `.codex/hooks.json`. OpenCode receives no hook file. A pass can still exit 0, with a warning that no file was written for that harness.
- An MCP server is `mcp-servers/<name>.json`, except `mcp-servers.json`, checked against [mcp-server.schema.json](../templates/mcp-server.schema.json). Claude Code receives `.mcp.json`. Codex receives a block in `.codex/config.toml`. OpenCode receives `opencode.json`.
- A tool is `capabilities/tools/<tool>/<tool>.json`, checked against [tool-json.schema.json](../templates/tool-json.schema.json). The `name` equals the folder name. A JSON file in that folder whose stem is not the folder name is passed over. The program writes no file under the installation for a tool. It places a shortcut in `~/.rbtv/bin`, named with the tool name, pointing at the `entry`. The entry resolves to a file inside the component. With the prefix `ws:`, it is resolved from the installation root, is not absolute, and has no `..` segment. The program refuses `path-not-runnable` when the entry has no `#!` first line. On POSIX it also refuses that code when the entry is not executable.
- A pack is `packs/<name>.json`, checked against [pack.schema.json](../templates/pack.schema.json). The program writes no file for the pack. `rbtv add --pack NAME` installs the files the pack names. A bare name is never a pack.

A generated skill or command file carries this marker: `rbtv-managed — generated by the rbtv installer; edits are overwritten on the next run`. A rule that Codex or OpenCode receives, and a component's folder-instructions section, sit between `<!-- rbtv:start <label> -->` and `<!-- rbtv:end <label> -->`. Text outside those markers stays. The next scaffolding run overwrites the text between them. A guidance copy begins `GENERATED by install.py — DO NOT EDIT.` Edit the source, not that copy.

What the program writes, for the kinds the table names:

- A skill is written to `.claude/skills/<name>/SKILL.md` for Claude Code and OpenCode, and to `.agents/skills/<name>/SKILL.md` for Codex. The written file names the source by its absolute path. The page "Skill"¹ says what the agent receives from that file.
- A command is written to `.claude/commands/<name>.md` for Claude Code, to `.opencode/commands/<name>.md` for OpenCode, and to `.codex/prompts/<name>.md` for Codex. The page "Command"² says what the human receives from that file.
- A rule, for Claude Code, is written to `.claude/rules/<name>.md`. Codex and OpenCode receive the body after the frontmatter, pasted into `AGENTS.md`. The description is not in that paste, so a description-only edit does not change it. Codex stops reading its `AGENTS.md` files at a size limit, 32 KiB by default. The program writes `project_doc_max_bytes = 131072` at the top of the installation's `.codex/config.toml`, which Codex reads only in a trusted folder. A body past the limit in force is cut. The page "Rule"³ says what each harness receives.
- Folder instructions from a component lose their frontmatter. The body is written into a marked section of the target folder's `CLAUDE.md` or `AGENTS.md`, for each installed harness. `.` as `target` is the installation root. The page "Folder instructions"⁶ says which file the author writes.
- The other harness name is a copy of the file the installation maintains. Claude Code reads `CLAUDE.md`. Codex and OpenCode read `AGENTS.md`. When every installed harness reads the maintained file, the program writes no second file.
- An agent named with `rbtv add` and `--on` is written as that harness's sub-agent file: `.claude/agents/<name>.md`, `.opencode/agents/<name>.md`, or `.codex/agents/<name>.toml`. The list in `agent.json` is not installed. An agent placed with `rbtv agent add` by name gets a copy of `agent.md` and `agent.json` in `.rbtv/agents/<name>/`, and no other file of its folder; an agent given as a path is used in place. The program writes `harness`, `model`, and `effort` into `agent.json` when that file has none. The page "Agent"⁴ says which placement installs the list. The program does not read the prompt body.

The installation's own record is `.rbtv/config/install.json`. The program writes it. A hand edit of an agent's `agent.json`, or of that record, is applied by `rbtv update scaffolding` or `rbtv update all`.

## How to work with it

The help of the program, `rbtv -h`, names every command. Its part "Discover" has the commands that list, search and show what the program recognizes and what this installation has. Run them before you write a second file for work that a file already does.

1. **Name the source, then what this run must not be taken to prove.** Name the source file and the folder it sits in before any run. The failure a pass hides is a file the scan accepts whose body the program never read. The cause is the split in the scan: frontmatter or JSON is checked, and the body is discarded. The situation is a run that exited 0, which you are about to take as proof that the work is done. Write what the run has to show: the source was recognized as its kind, and nothing about the body. An author who starts from the verb gets an exit code and no test of the work.

2. **Put the source where the program recognizes it.** Use the folder in the table. Do not put a capability in `skills/`, `rules/`, or `commands/`. A `*.md` file there, once its frontmatter matches that kind, is installed as that kind. It is not left unread under `capabilities/`. Do not name the file after its folder. The program passes `skills.md`, `rules.md`, `commands.md`, `hooks.json`, `mcp-servers.json`, and `folder-instructions.md` over, and it does not report them. A file in those folders that is not `*.md` or `*.json`, as that folder requires, is passed over the same way.

   The `name` in the frontmatter or the JSON equals the file stem, except in `folder-instructions/`, which has no `name` field. For a skill, a command, a rule, a hook, an MCP server, and `agent.md` and `agent.json`, that name matches `^[a-z0-9][a-z0-9-]*$`: it starts with a lower-case letter or a digit, and the rest is lower-case letters, digits, or hyphens. A tool name is not checked against that pattern. It equals the tool folder name. A name that starts with `rbtv-` matches the pattern and is still refused, with `REFUSED [name-reserved]`, before any write; a tool name is not checked for that prefix. The program does not compare a command name with a harness command. A pass does not show that the name is free. The page "Command"² says what the harness does with a name it already lists.

   A component's `agent.json` names no `harness`, no `model`, and no `effort`. The folder name, the `name` in `agent.md`, and the `name` in `agent.json` agree. A file in `sub-agents/` is refused: `an agent is no longer shipped as one file in sub-agents/. Ship it as the folder agents/<name>/ with agent.md and agent.json`.

3. **Run the command that writes, and read a refusal from the component id.** A file that is not yet installed is recognized by `rbtv add NAME`. The first add in an installation also needs `--harness` and `--guidance`. The harness is `claude`, `codex`, or `opencode`. The guidance is `CLAUDE.md`, `AGENTS.md`, or `none`. A later add can omit both. `--target D` is the installation. Without `--target`, `RBTV_AGENT_HOME` is used when it is set; set to an empty value or to a directory that does not exist, it is refused, `agent-home-invalid`. When it is not set, the program walks up from the current directory. It takes the first ancestor with `.rbtv/config/install.json`, or with `agent.md` and `agent.json`. If none has that file, it takes the first ancestor with a `.rbtv/` directory that is not the home directory. If none has that directory, it takes the current directory. A run from the repository, with no `--target` and no installation above it, writes into that repository.

   A pass exits 0, and an add names the identifier `module/component#name` of each file it selected. A refusal exits 1 and prints `REFUSED [code]`; with `--json` the refusal is a JSON object. A usage error exits 2. When the short name is unknown, add the component id, `rbtv add module/component`. That run prints the schema problem. The short name does not.

   Weak: `rbtv add broken-skill`

   Strong: `rbtv add trial/bad`

   The weak line prints `REFUSED [name-unknown]` and does not print the schema problem, so the author moves a file whose name does not equal its stem.

4. **Choose the agent placement before the run.** To write a harness sub-agent, run `rbtv add NAME --on HARNESS:MODEL:EFFORT`, once per harness the installation receives. Model and effort are checked with `cast list`. The result names the list in `agent.json` and says it was not applied. A harness-native sub-agent sees what its target has. To place the folder as an rbtv agent, run `rbtv agent add AGENT --harness HARNESS --model MODEL --effort EFFORT` when `agent.json` has none of those three. They are written into the record. Giving them again is refused: change them with `rbtv agent configure`. Agent verbs take no `--target`. A name is found under `.rbtv/agents/<name>/`. A path is that folder, used in place, and nothing is copied. `rbtv add module/component` skips an agent the component ships and says so. It does not place that agent.

   Weak: `rbtv add review --on claude:MODEL:EFFORT`

   Strong: `rbtv agent add review --harness claude --model MODEL --effort EFFORT`

   The weak line writes a sub-agent file and leaves the list uninstalled. The run can exit 0.

5. **Read the pass as a schema match for that kind.** A pass shows the checked fields matched and the file was recognized as that kind. It does not show that the body was read.

   - A skill, a command, a rule, or folder instructions: the frontmatter matched its schema. A pass does not show that a reader reaches every row. It does not show that the party who decides is the one that this kind gives the decision to. It does not show that the instructions do the work.
   - A skill: a pass does not show that the agent opens the skill on the task that the description names, or stays closed on the similar task.
   - A command: a pass does not show that the human can choose from the name. It does not show that the typing carries the inputs. It does not show that the instructions do the action.
   - A rule: a pass does not show that the body stops the fault. It does not show that the description decides an install. It does not show that the agent acts only when the point comes.
   - An agent folder: both files were recognized, the names agree, and a component source names no harness, model, or effort. It does not show that the description decides a launch, or that the prompt does the work. The page "Prompt"⁵ is the body that was not read.
   - Folder instructions: a pass of the component source shows the frontmatter matched and, when the file was selected and the run was not a dry run, that the marked section was written. It does not show that an agent in the folder reads the right file. A pass of `rbtv update guidance` shows that the other harness name, where one is needed, was written from the file the installation maintains. It does not show that the body or the rows are right.
   - A capability: no run accepts the file. A run that exits 0 for the component shows the component record was found and each recognized file matched. It says nothing about a file under `capabilities/`.

6. **After an edit, run the command that rewrites the file the reader sees.** A change to the body of a skill or a command reaches the agent on the next open, because the pointer names the source. A change to the description or the name does not, until the program writes the pointer or the listed file again. Run `rbtv add NAME`, or `rbtv update scaffolding`, or `rbtv update all`. `rbtv update scaffolding` regenerates generated files for what the record lists. It does not copy the instruction file the installation maintains. `rbtv update guidance` copies that file into the other harness name and does not rebuild a pointer, a rule section, or a component section. `rbtv update all` runs scaffolding, then guidance. When guidance is `none`, `rbtv update guidance` writes nothing and can still exit 0. An edit of a rule's source reaches the agent only after scaffolding or add writes the copy or the section again. An edit between the markers is lost on that run. For an agent folder, run `rbtv agent update AGENT scaffolding` or `rbtv agent update AGENT all`.

   Weak: `rbtv update guidance`

   Strong: `rbtv update scaffolding`

   The weak line can exit 0 and leave the pointer's description unchanged.

Checks:

- The source sits in a folder the scan reads, under a name the program recognizes. The `name` equals the file stem, or the file is folder instructions and has no `name`. A generated file carries the managed marker, or the text sits between `rbtv:start` and `rbtv:end`. The author did not edit that generated file. A component's `agent.json` names no harness, model, or effort.
- A pass exits 0, and an add names `module/component#name`. That shows the checked fields matched and, outside a dry run, that the generated file was written. It does not show that the body was read. It does not show that a description decides a load. It does not show that a file under `capabilities/` does the work. A refusal exits 1. `REFUSED [name-unknown]` on a short name is not the schema result. Add the component id for that result.
- Change a description in a source that is already installed. Run `rbtv update guidance`. Read the pointer or the listed file and confirm the old description is still there. Run `rbtv update scaffolding` and confirm the new description is there.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Skill | [Skill](skill.md) | when | the source is a skill, or a pass is being read for a skill | take what the agent receives from the pointer, and how the skill is written |
| 2 | Command | [Command](command.md) | when | the source is a command, or a name may already be a harness command | take what the listed file carries, and what a harness does with a name it already lists |
| 3 | Rule | [Rule](rule.md) | when | the source is a rule | take what each harness receives |
| 4 | Agent | [Agent](agent.md) | when | the source is an agent folder, or a placement is being chosen | take which placement installs the list, and what the record may name |
| 5 | Prompt | [Prompt](prompt.md) | when | the question is the body of `agent.md` | take how that body is written, and that a pass does not read it |
| 6 | Folder instructions | [Folder instructions](folder-instructions.md) | when | the file is the one the installation maintains, or a component section | take which file the author writes, and what a marked section is |
| 7 | Capability | [Capability](capability.md) | when | the file is under `capabilities/` and is not a tool record | take that the program does not install the file, and the agent reads it in the source |
| 8 | Module | [Module](module.md) | when | the source is a module record, or a module folder is not listed | take what the folder and the record contain |
| 9 | Component | [Component](component.md) | when | the source is a component record, or a file is in a folder the program does not scan | take which folders a component has, and where each kind goes |
| 10 | Hook | [Hook](hook.md) | when | the source is a hook | take how the record is written, and what a pass does not show for it |
| 11 | MCP server | [MCP server](mcp-server.md) | when | the source is an MCP server | take how the record is written, and what a pass does not show for it |
| 12 | Tool | [Tool](tool.md) | when | the source is a tool | take how the program and the record are written, and that the program writes no copy of the program |
| 13 | Pack | [Pack](pack.md) | when | the source is a pack, or a run names `--pack` | take what the list contains, and what turning the pack off removes |
