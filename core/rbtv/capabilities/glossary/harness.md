# Harness

A harness is the application that runs a model and supplies its instructions, tools and other context. It is one part of an [agent](agent.md), alongside the model and scaffolding. rbtv supports Claude Code, Codex and OpenCode, identified in configuration as `claude`, `codex` and `opencode`.

Name the harness when stating how instructions reach an agent. The same source can require different installed files, and installation does not prove that a running session loaded them.

## What differs

| Kind | Claude Code | Codex | OpenCode |
|---|---|---|---|
| Rule | Loads the body from its rules folder; frontmatter is stripped. The path-list field controls conditional loading, but rbtv rules carry no path list. | Has no always-loaded rules folder. rbtv installs each rule as a skill in `.agents/skills/`; Codex lists its name and description and loads the body only when the model selects it. Codex's command-permission rules are a different mechanism. | Reads no rules folder. rbtv lists each rule file in `opencode.json` under `instructions`; OpenCode loads every listed file in every session. |
| Folder instructions | Uses `CLAUDE.md`. With default project-instruction settings, `AGENTS.md` is a fallback only when the working directory and its parents have none of `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md`. Settings can change this. | Reads instruction files from project root down to the starting directory, subject to a combined size limit. | Uses `AGENTS.md`, falling back to `CLAUDE.md` when no `AGENTS.md` is present. |
| Skill | Lists name and description; loads instructions when selected. Also supports human invocation. | Lists name and description; can shorten descriptions or omit entries when many skills are installed. | Lists name and description and loads the selected instructions. It reads `.claude/skills/` and `.agents/skills/`, so it would list a rule installed as a Codex skill; rbtv denies that skill in `opencode.json` when OpenCode already loads the rule. |
| Command | The installed command carries a description. | The rbtv-generated command file carries no description. Discovery of these generated project-local prompts still requires verification. | The installed command carries a description. |
| Hook | Runs shell hooks from settings. | Runs shell hooks from configuration when it holds a stored approval of each one. A session that `cast` launches or resumes, and every Codex turn the Ignite waking service runs, skips that approval step, so any hook file in the launch folder runs unreviewed; [Hook](hook.md) states the cost. | No equivalent settings hook is emitted by rbtv; plugins are a separate mechanism. |

Claude Code's skill listing has a 1,536-character cap per entry and an overall budget that can drop descriptions. Keep the selection boundary visible as [Routing table](routing-table.md) describes; do not rely on the full description reaching every model. The [Exposure method](exposure-method.md) entry defines rbtv's choice between agent-selected skills and human-invoked commands, even when a harness offers both ways to invoke a skill.

For exact authoring and installation behavior, open the entry for the kind being changed: [Rule](rule.md), [Folder instructions](folder-instructions.md), [Skill](skill.md), [Command](command.md), [Hook](hook.md) or [Agent](agent.md). [rbtv CLI](rbtv-cli.md) owns the generated paths and configured instruction-size limit. Raising that limit does not eliminate it.

## Configuration and verification

An installation selects its harnesses in `.rbtv/config/install.json`, under `harnesses`. An installed rbtv agent chooses the one that launches it with `harness` in `agent.json`; its folder receives the files of all three, so a launch that falls back to a model of another harness finds the same skills, rules, hooks and folder instructions. Component-shipped agent records do not fix that choice; follow [Agent](agent.md) when writing them.

When a design depends on loading order, discovery, a size limit or an event, verify that behavior on the target harness and settings. Keep unverified behavior explicit. A file generated for a harness is evidence of installation, not evidence that a session read it. Do not prescribe one harness's tool as the only way to perform a shared instruction; [Cognitive unit](cognitive-unit.md) governs that wording.
