# Installer design decisions

These are the installer decisions in force. The installer code is the authority for behavior. The [building decisions](../../build/decisions.md) own decisions about rbtv as a whole; the [overview](../../build/capabilities/rbtv.md), glossary, and schemas own the source and record formats.

## D1 — Installer placement

The installer is the `core/installer` component. Its tool has a small `install.py` entry point, responsibility-specific modules in `lib/`, `discovery.py` beside the entry point, and checks in `selftest/`. `REPO_ROOT` is defined once in `lib/constants.py` as `Path(__file__).resolve().parents[6]`; the layout selftest checks it. This keeps imports and repository scans anchored to one location while the code stays readable by responsibility. The reason `core` owns the installer is in the [building decisions](../../build/decisions.md#module-and-component-placement).

## D2 — Component source shape

The installer discovers modules and components through their named JSON records and reads units from their folders. The definition and layout belong to the [overview](../../build/capabilities/rbtv.md#folder-structure), [component glossary](../../build/capabilities/glossary/component.md), and [component schema](../../build/capabilities/templates/component-json.schema.json).

## D3 — Source trees and precedence

The installer scans its fixed repository root and the target's `.rbtv/mirror/` together. A mirror component with the same id replaces the shipped component as a whole, and the installer reports what it shadows. This lets a workspace supply its own component without mixing two sources under one id. The selftest also checks that shipped programs with shebangs have executable git modes, so a tool accepted on Windows remains runnable on POSIX.

## D4 — Receiving harnesses

The installer accepts `claude`, `codex`, and `opencode` as receiving harnesses. CLI changes require a nonempty supported set; a saved component record with no supported harness refuses on load. One supported set keeps the installed files and guidance copies consistent. The product's harness choice belongs to the [overview](../../build/capabilities/rbtv.md).

## D5 — Install record

The shape of `.rbtv/config/install.json` belongs to the [install record schema](../../build/capabilities/templates/install-json.schema.json) and [glossary](../../build/capabilities/glossary/install-json.md).

## D6 — Collision gate

Before writing, the installer refuses a planned whole-file path or shared-file key held by someone else. A booked path or claim can be updated; a marked generated file can be adopted. This protects authored content while allowing installer output to be refreshed.

## D7 — Shared files

The installer recomputes claims in harness settings and instruction files from the selected installed units. It edits only its JSON keys or fenced sections and removes a shared file only when nothing else remains. This lets multiple components and authored content use the same file without either owning the whole file.

## D8 — Rules and folder instructions

Claude Code receives a marked full rule file in `.claude/rules/`; Codex and OpenCode receive each rule's full body in a labeled section of root `AGENTS.md`. A component's `folder-instructions/` file becomes a labeled section in the target folder's guidance file for each selected harness. The installer also raises Codex's project document limit in `.codex/config.toml` when an installed component targets Codex. These forms keep rules present and let several components contribute to one guidance file while preserving authored text. The source kinds and folders belong to the [overview](../../build/capabilities/rbtv.md#folder-structure).

## D13 — Guidance copies

The recorded basis is `CLAUDE.md`, `AGENTS.md`, or `none`. For each basis file found in the target tree, the installer generates the other filenames read by selected harnesses, deduplicated by name. It skips symlinks, nested git repositories, built-in skip folders, and configured exclusions. The basis is protected from deletion. Generated copies carry a banner; the installer can adopt a banner-bearing copy, strips a generated banner before copying from it, and keeps a copy unbooked if a partial removal cannot safely replan it. This gives each folder one authored source and avoids deleting guidance during recovery. The role of folder instructions belongs to the [glossary](../../build/capabilities/glossary/folder-instructions.md).

## D14 — Clone-local ignore block

In a target with a `.git/` folder, the installer maintains its artifact list as a fenced claim in `.git/info/exclude`. It lists planned component files, the install record, and unbooked marked artifacts found in harness destinations; guidance copies stay committable. It reports files git already tracks. This keeps machine-specific paths out of commits without making one machine's ignore list overwrite another's.

## D15 — Whole-folder skills

A skill in the standard shareable format — a `_skills/<name>/` folder with `SKILL.md` and its own files — is read only from an installation's `.rbtv/mirror/`, never from the rbtv repository, and is identified as `_hub/skills/<name>`. It installs as a thin loader in each selected harness's skills folder: the skill's own frontmatter, verbatim so harness-specific keys survive, and a body that points at the source `SKILL.md` and its folder, from which its relative files resolve. The loader is booked in the install record and updated and removed like every other unit. The source folder is never copied or changed, so a skill kept current with `git pull` takes effect at once; a folder copied by an earlier installer is deleted on the next run.

## D16 — Workspace settings

The first `add` requires an explicit harness set and guidance basis, unless `configure` has recorded both. Each component uses the workspace harness set. A change through `configure`, `add|remove harness`, or `add|remove guidance exclude` replans every selected installed component. This makes a narrower setting remove the files it no longer calls for, and keeps settings separate from item selection.

## D16b — Settings grammar

Set-valued settings use `add harness`, `remove harness`, `add guidance exclude`, and `remove guidance exclude`; `configure --guidance` replaces the single basis value. Named item selection uses `add` and `remove`. The action leads each command so adding to a set and replacing one value have distinct, readable forms.

## D16c — Saved settings in inspection

`status` and `list --installed` show the saved harnesses, guidance basis, and guidance exclusions; their JSON output carries those values under `installation` and `settings`, respectively. These values describe the installation and belong beside its recorded selections.

## D9 — Tools on PATH

A selected tool creates a shortcut in `~/.rbtv/bin` under its tool name and creates no tool copy under the target. Planning checks the program before writing: every system requires a shebang (`#!`) first line, so a program that would not run on Linux is refused on Windows too; POSIX also requires execute permission, and Windows takes its interpreter from the shebang or the script extension. This gives each installation a checked, runnable entry point while keeping the program in its source location. The tool record and source folder belong to the [tool glossary](../../build/capabilities/glossary/tool.md).

## D9b — Windows shortcuts

On Windows, each PATH tool gets a marked `<name>.cmd` shim and an extensionless shell launcher beside it; POSIX uses a symlink. The Windows shim chooses an interpreter from the program, maps Python shebangs to `python`, and prefers Git Bash for shell scripts. The pair serves native terminals and Git Bash without requiring Windows symlink privilege.

## D9c — User PATH

A real install that selects a PATH tool adds `~/.rbtv/bin` to the user's shell startup profiles on POSIX or user PATH on Windows. It leaves that PATH setup in place when a workspace removes its tools. This lets new shells find installed commands and lets the same bin folder serve other workspaces.

## D10 — Absolute loader paths

The installer writes resolved absolute source paths into thin loaders. The [building decisions](../../build/decisions.md#system-and-installation-decisions) own this choice and its machine-local rationale.

## D12 — Proof of ownership

Per-unit harness files use an `rbtv-managed` marker in the file, after YAML frontmatter when present. A marked generated file can be adopted into the book; a stale booked file whose marker is removed is released without deletion when no other ownership proof applies. Shared files use booked keys or fenced sections instead, and a copied skill folder uses its marked `SKILL.md`. These signals allow repair and handover without treating every file at a familiar path as installer-owned.

## D25 — Shared shortcut ownership and locks

`~/.rbtv/path-owners.json` records each shortcut's resolved target and the workspaces that need it. The installer removes a shortcut only after its last owner leaves, preserves unrecorded shortcuts, and refuses conflicting targets before target writes. Bounded locks serialize workspace mutation and the shared shortcut record; workspace lock names derive from resolved target paths in the system temporary folder. This prevents concurrent runs and different workspaces from silently taking over one command. An OS error while persisting PATH is reported as a warning after the workspace install succeeds.

## D26 — Public commands and local updates

`configure` records or changes harness and guidance settings; `add` and `remove` change selected items. Public item filters and JSON use `type`; `list` follows exact named scope, `search` matches names and descriptions broadly, and short names resolve only when unique. `show` keeps a stable id and selection, with `scope` for module, component, or item and `type` for an item. These forms make selection inspectable and unambiguous.

`update guidance` copies maintained human guidance while preserving generated destination sections. `update scaffolding` regenerates selected installer-owned files and generated instruction sections while preserving human text. `update all` validates both phases before writing. Updates use local source and do not expand the saved selection; a selected unit whose source no longer exists leaves the record, and the report lists it as "removed (source no longer exists)", so the record always matches the installed files. Named removal needs no blanket confirmation; broad nonempty removal requires `--yes`, and dry runs write nothing. `status` shows saved selection without claiming to check health; `doctor` checks files and selected shared shortcuts. These boundaries keep refreshing, inspecting, and checking separate and make broad deletion deliberate.
