# Installer design decisions

These are the installer decisions in force. The installer code is the authority for behavior. The [building decisions](../decisions.md) own decisions about rbtv as a whole; the [overview](../skills/framework.md), glossary, and schemas own the source and record formats.

## D1 — Installer placement

The installer is the `core/rbtv` component. Its tool has a small `install.py` entry point, responsibility-specific modules in `lib/`, `discovery.py` beside the entry point, and checks in `selftest/`. `REPO_ROOT` is defined once in `lib/constants.py` as `Path(__file__).resolve().parents[6]`; the layout selftest checks it. This keeps imports and repository scans anchored to one location while the code stays readable by responsibility. The reason `core` owns the installer is in the [building decisions](../decisions.md#module-and-component-placement).

## D2 — Component source shape

The installer discovers modules and components through their named JSON records and reads units from their folders. The definition and layout belong to the [overview](../skills/framework.md), [component glossary](glossary/component.md), and [component schema](templates/component-json.schema.json).

## D3 — Source trees and precedence

The installer scans its fixed repository root and the target's `.rbtv/mirror/` together. A mirror component with the same id replaces the shipped component as a whole, and the installer reports what it shadows. This lets an installation supply its own component without mixing two sources under one id. The selftest also checks that shipped programs with shebangs have executable git modes, so a tool accepted on Windows remains runnable on POSIX.

## D4 — Receiving harnesses

The installer accepts `claude`, `codex`, and `opencode` as receiving harnesses. CLI changes require a nonempty supported set; a saved component record with no supported harness refuses on load. One supported set keeps the installed files and guidance copies consistent. The product's harness choice belongs to the [overview](../skills/framework.md).

## D5 — Install record

The shape of `.rbtv/config/install.json` belongs to the [install record schema](templates/install-json.schema.json) and [glossary](glossary/install-json.md).

When a selected unit, pack, or component is absent from the local source after an update, `rbtv update scaffolding` and `rbtv update all` remove its generated files, record entry, and command shortcut. Other add and remove operations continue, warn about the stale selection, and direct the user to `rbtv update all` for reconciliation.

The record's schema number is 9. A record of schema 8 is read with the components `core/build` and `core/install` as the one component `core/rbtv`, in an installation's record and in an agent's `agent.json`: their two entries become one that carries what both held, the unit `core/build#build` is `core/rbtv#framework`, `core/install#rbtv` is `core/rbtv#rbtv`, and `core/install#manage-components`, which has no successor, leaves the selection. The file is rewritten by the next command that writes the record; `rbtv update all` and `rbtv agent update AGENT all` then delete the generated files of the units that left, name them as removed, and point the `rbtv` shortcut at the program's present file.

## D6 — Collision gate

Before writing, the installer refuses a planned whole-file path or shared-file key held by someone else. A booked path or claim can be updated; a marked generated file can be adopted. This protects authored content while allowing installer output to be refreshed.

## D7 — Shared files

The installer recomputes claims in harness settings and instruction files from the selected installed units. It edits only its JSON keys or fenced sections and removes a shared file only when nothing else remains. This lets multiple components and authored content use the same file without either owning the whole file.

## D8 — Rules and folder instructions

Claude Code receives a marked full rule file in `.claude/rules/`; Codex and OpenCode receive each rule's full body in a labeled section of root `AGENTS.md`. A component's `folder-instructions/` file becomes a labeled section in the target folder's guidance file for each selected harness. The installer also raises Codex's project document limit in `.codex/config.toml` when an installed component targets Codex. These forms keep rules present and let several components contribute to one guidance file while preserving authored text. The source kinds and folders belong to the [overview](../skills/framework.md).

## D13 — Guidance copies

The recorded basis is `CLAUDE.md`, `AGENTS.md`, or `none`. For each basis file found in the target tree, the installer generates the other filenames read by selected harnesses, deduplicated by name. It skips symlinks, nested git repositories, built-in skip folders, and configured exclusions. The basis is protected from deletion. Generated copies carry a banner; the installer can adopt a banner-bearing copy, strips a generated banner before copying from it, and keeps a copy unbooked if a partial removal cannot safely replan it. This gives each folder one authored source and avoids deleting guidance during recovery. The role of folder instructions belongs to the [glossary](glossary/folder-instructions.md).

## D14 — Clone-local ignore block

In a target with a `.git/` folder, the installer maintains its artifact list as a fenced claim in `.git/info/exclude`. It lists planned component files, the install record, and unbooked marked artifacts found in harness destinations; guidance copies stay committable. It reports files git already tracks. This keeps machine-specific paths out of commits without making one machine's ignore list overwrite another's.

## D15 — Whole-folder skills

A skill in the standard shareable format — a `_skills/<name>/` folder with `SKILL.md` and its own files — is read only from an installation's `.rbtv/mirror/`, never from the rbtv repository, and is identified as `_hub/skills/<name>`. It installs as a thin loader in each selected harness's skills folder: the skill's own frontmatter, verbatim so harness-specific keys survive, and a body that points at the source `SKILL.md` and its folder, from which its relative files resolve. The loader is booked in the install record and updated and removed like every other unit. The source folder is never copied or changed, so a skill kept current with `git pull` takes effect at once; a folder copied by an earlier installer is deleted on the next run.

## D16 — Installation settings

The first `add` requires an explicit harness set and guidance basis, unless `configure` has recorded both. Each component uses the installation harness set. A change through `configure`, `add|remove harness`, or `add|remove guidance exclude` replans every selected installed component. This makes a narrower setting remove the files it no longer calls for, and keeps settings separate from unit selection.

## D16b — Settings grammar

Set-valued settings use `add harness`, `remove harness`, `add guidance exclude`, and `remove guidance exclude`; `configure --guidance` replaces the single basis value. Named unit selection uses `add` and `remove`. The action leads each command so adding to a set and replacing one value have distinct, readable forms.

## D16c — Saved settings in inspection

`status` and `list --installed` show the saved harnesses, guidance basis, and guidance exclusions; their JSON output carries those values under `installation` and `settings`, respectively. These values describe the installation and belong beside its recorded selections.

## D9 — Tools on PATH

A selected tool creates a shortcut in `~/.rbtv/bin` under its tool name and creates no tool copy under the target. Planning checks the program before writing: every system requires a shebang (`#!`) first line, so a program that would not run on Linux is refused on Windows too; POSIX also requires execute permission, and Windows takes its interpreter from the shebang or the script extension. This gives each installation a checked, runnable entry point while keeping the program in its source location. The tool record and source folder belong to the [tool glossary](glossary/tool.md).

## D9b — Windows shortcuts

On Windows, each PATH tool gets a marked `<name>.cmd` shim and an extensionless shell launcher beside it; POSIX uses a symlink. The Windows shim chooses an interpreter from the program, maps Python shebangs to `python`, and prefers Git Bash for shell scripts. The pair serves native terminals and Git Bash without requiring Windows symlink privilege.

## D9c — User PATH

A real install that selects a PATH tool adds `~/.rbtv/bin` to the user's shell startup profiles on POSIX or user PATH on Windows. It leaves that PATH setup in place when an installation removes its tools. This lets new shells find installed commands and lets the same bin folder serve other installations.

## D10 — Absolute loader paths

The installer writes resolved absolute source paths into thin loaders. The [building decisions](../decisions.md#system-and-installation-decisions) own this choice and its machine-local rationale.

## D12 — Proof of ownership

Per-unit harness files use an `rbtv-managed` marker in the file, after YAML frontmatter when present. A marked generated file can be adopted into the book; a stale booked file whose marker is removed is released without deletion when no other ownership proof applies. Shared files use booked keys or fenced sections instead, and a copied skill folder uses its marked `SKILL.md`. These signals allow repair and handover without treating every file at a familiar path as installer-owned.

## D25 — Shared shortcut ownership and locks

`~/.rbtv/path-owners.json` records each shortcut's resolved target and the installations that need it. The installer removes a shortcut only after its last owner leaves, except that a shortcut whose recorded target has vanished is removed with all of its stale owners when its unit is removed. A vanished recorded target cannot reserve a shortcut: an installation may replace it while retaining the other owners for their next run. An existing different target remains a refusal. The installer preserves unrecorded shortcuts. Bounded locks serialize installation mutation and the shared shortcut record; installation lock names derive from resolved target paths in the system temporary folder. This prevents concurrent runs and different installations from silently taking over one command. An operating-system error while persisting PATH is reported as a warning after the installation succeeds. A shortcut whose target is not at its recorded path does not run, and that includes `rbtv` itself; the next update relinks it, so the program is started once by its full path: `python3 <repository>/core/rbtv/capabilities/tools/rbtv/install.py update all --target <installation>`, then, from the installation, for each placed agent, `python3 <repository>/core/rbtv/capabilities/tools/rbtv/install.py agent update <agent> all`.

## D26 — Public commands and local updates

`configure` records or changes harness and guidance settings; `add` and `remove` change selected units. Public unit filters and JSON use `type`; `list` follows exact named scope, `search` matches names and descriptions broadly, and short names resolve only when unique. `show` keeps a stable id and selection, with `scope` for module, component, or unit and `type` for a unit. These forms make selection inspectable and unambiguous.

`update guidance` copies maintained human guidance while preserving generated destination sections. `update scaffolding` regenerates selected installer-owned files and generated instruction sections while preserving human text. `update all` validates both phases before writing. Updates use local source and do not expand the saved selection; a selected unit, pack, or component whose source no longer exists is removed from the generated files and record by `update scaffolding` or `update all`, as D5 specifies. Named removal needs no blanket confirmation; broad nonempty removal requires `--yes`, and dry runs write nothing. `status` shows saved selection without claiming to check health; `doctor` checks files and selected shared shortcuts. These boundaries keep refreshing, inspecting, and checking separate and make broad deletion deliberate.

## D27 — The `rbtv` command: verbs, words, help

The command is `rbtv`, the program itself: there is no `install` level. Its verbs are `status`, `list` (alias `ls`, and `li` for `list --installed`), `search`, `show`, `configure`, `add`, `remove` (alias `rm`), `update`, `agent`, `doctor`, `interactive` and `selftest`. `rbtv --version` prints the version. An unknown verb, `install` included, is wrong usage: standard error, exit 2, the list of valid verbs and no sentence saying that a word moved. The old forms `set`, `dupe-artifacts`, `harness` and `artifact` are not recognised at all, and neither are the retired options `--kind`, `--exclude-kind` and `--artifact`.

The public words are **file** (what the catalog offers and what an installation selects; the JSON keys are `files`) and **installation** (the root folder; it replaces "workspace", and Ignite's flag becomes `--installation`). The state words `installed` and `not installed` stay, and `target` stays the name of the folder a command acts on. The unit named `google-workspace` is a name and is unchanged.

Every `-h` page is authored text: the help of each command path is kept verbatim in one module, and the parser says only what the grammar accepts. The selftest checks that each option a command takes is named on its page. Root help groups the verbs by intent; the agent verbs are one line there that points to `rbtv agent -h`.

`--target` has one meaning: the folder a root verb acts on, an installation or an agent folder. The `rbtv agent` verbs take no `--target`: AGENT is a name looked up in the installation found from the current folder, or a path used in place. `RBTV_AGENT_HOME` is the target of a root verb when `--target` is absent, and it never fills AGENT.

An agent that a component ships is installed by two verbs, one per installed form (D28): `rbtv agent add NAME` places it as an rbtv agent, and `rbtv add NAME --on HARNESS:MODEL:EFFORT` adds it to a target as a unit. The settings forms `add harness`, `remove harness`, `add guidance exclude` and `remove guidance exclude` (D16b) remain accepted and are listed under "Also accepted" in `configure -h`.

When it is missing, `rbtv agent add` writes the agent folder's `.gitignore`. It only adds ignores: every generated harness folder, root instruction filename and shared-file destination, derived from the harness path, guidance and shared-destination tables, plus itself and machine-local state. It contains no catch-all or negated rule, so the containing repository's ignore rules continue to decide every other file. An existing `.gitignore` belongs to its author and is left unchanged.

## D28 — One agent source format, two installed forms

A component ships an agent in one format: the folder `agents/<name>/`, holding `agent.md` (frontmatter `name`; the body is the prompt) and `agent.json` (`name`, `description`, and optionally `files` and `packs`). The catalog lists it once, as one unit of type `agent`. A shipped `agent.json` names no harness, no model and no effort: those values exist only in an installation, and rbtv refuses a component whose shipped agent names one (`agent-source-launch`), naming the fields to remove. A component that holds a file in a `sub-agents/` folder is refused (`agent-source-retired`) with a message that names `agents/<name>/`. One format means one prompt to maintain; the verb, not the source, decides how the agent is exposed.

`rbtv agent add NAME --harness H --model M --effort E` places the agent as an rbtv agent in `<installation>/.rbtv/agents/<name>/`. The three flags are required when the agent's `agent.json` has none of the values, checked as `rbtv agent configure` checks them, and written into the placed `agent.json`. When the file already has the values, a flag is refused and the refusal names `rbtv agent configure`.

`rbtv add NAME --on HARNESS:MODEL:EFFORT` adds the agent to a target as a unit, written as a harness-native sub-agent: `.claude/agents/<name>.md`, `.opencode/agents/<name>.md`, `.codex/agents/<name>.toml`. `--on` repeats, one per harness; each harness must be one the target receives (an rbtv agent receives its own harness); it is required when an agent is among the names and refused when none is. The flag is not `--harness`, `--model` and `--effort` because `--harness` on `rbtv add` already names the installation's receiving harnesses on a first setup. The file is written only for the harnesses given. It carries the agent's name, its description, the instruction to read its prompt, and that harness's model and effort in the harness's own settings (the table `SUB_AGENT_SETTINGS`): `model` and `effort` for Claude Code, `model` and `variant` for OpenCode, `model` and `model_reasoning_effort` for Codex. The model is written as the harness's own id for it, which rbtv reads from the command `cast --dry-run` would start, so the model table stays in `cast`. A value a file has no setting for, and the effort of a model with no effort dial, is recorded and reported as not applied. The agent's own `units` and `packs` are not applied: a harness-native sub-agent sees what its target has, and the result names them.

The model and effort live in the target's record, on the unit's entry: `components.<component>.units.<name>.sub_agent` maps each harness to `model` (cast's name), `model_id` (the harness's name) and `effort`. Nothing there is tied to one machine. `rbtv update` regenerates the files from that record alone, without `cast`. Running `rbtv add NAME --on` again for a harness replaces its values and the result shows the old ones. Removing the unit removes the files of every harness and the values. A harness that leaves the target loses its files and its values. A harness that joins it gets no sub-agent file: rbtv cannot choose a model and an effort, so the result of `rbtv configure` names each such agent and the command that adds it. An agent that is chosen with no model and effort for any receiving harness (through a pack, a whole component, the guided menu, or a record written by an earlier schema) writes no file, and the result warns with the command to run. A record of schema 7 is read unchanged, its former `sub-agent` unit read as the `agent` unit with no values.

Both forms may exist together for one agent in one installation. Only an agent a component ships is a unit: an agent written by hand in an installation is not offered as a sub-agent. `rbtv status`, `rbtv list` and `rbtv show` name, for each agent installed as a sub-agent, the harnesses it is written for with the model and effort of each.
