# Folder structure

rbtv's own structure, and the work convention it offers. A module or component defines any further structure it needs. A plan folder is defined by `meta/plan`. PARA roots are defined by `meta/para`. This page does not copy those definitions.

`rbtv structure` prints one section of this page. It does not keep a second copy of a tree.

## Mandatory for rbtv

rbtv requires only `.rbtv/` at the installation root. Everything else at that root is the user's. rbtv works without it. The work lifecycle below and PARA are offered conventions, not requirements.

Inside an agent folder, rbtv requires `prompt.md`, `agent.json`, `settings.json`, `rbtv/` and `runtime/`. `memory/` and `_artifacts/board.md` are the existing baseline. Create any other folder only when the work needs it.

The installation-level tree sits beside the agent tree. These names are rbtv-owned. A folder is created when rbtv first needs it. It is mandatory where rbtv reads it, not a folder the user must create by hand before rbtv runs.

```text
.rbtv/
  config/install.json     required once the installation has a saved selection
  config/<component>/     settings, choices and keys that component stores
  runtime/<component>/    operational data for that component
  memory/                 the installation's shared memory
  mirror/                 installation-specific components, including _skills/
  agents/                 agents found by name
```

| Path | Kind | Who writes | Who reads | Tracked |
|---|---|---|---|---|
| `config/install.json` | operational record of the selection | the installer | the installer | no |
| `config/<component>/` | what the user chose or supplied | that component | that component | no |
| `runtime/<component>/` | operational data | that component | that component | no; not disposable |
| `memory/` | durable shared memory | the memory writer | agents allowed to read it | as memory's own rule states |
| `mirror/` | authored installation-specific source | the user or an agent | the installer | the user's choice |
| `agents/` | agent folders found by name | `rbtv agent add` | launch and list | authored source yes; see the agent section |

## agent

The standing agent folder. The `foundations` pack (`core/rbtv/packs/foundations.json`) applies the rule `agent-folder` to every agent, so every agent receives this rule. The rule routes here and does not copy this tree. `rbtv agent add` applies the pack. `rbtv agent update` adds it when the record lacks it, unless `agent.json` has `exclude_foundations: true`. `rbtv agent remove AGENT --pack foundations` writes that field.

Required paths are the ones in Mandatory for rbtv. The rest are created when needed.

```text
<agent>/
  prompt.md                 required; owner-authorized standing instructions
  agent.json                required; selections and launch record
  settings.json             required; machine-local choices, grouped by tool or concern
  rbtv/                     required; source authored for this agent
    skills/                 optional; installed skills
    rules/                  optional; installed procedure rules
    commands/               optional
    hooks/                  optional
    mcp-servers/            optional
    capabilities/
      methods/              optional; supporting procedures read from source
      tools/<tool>/         optional; tool program and documentation, off PATH
  runtime/                  required; operational data, outside source
    ignite/                 optional; database, conversations and turn records
    <tool-or-concern>/      optional; durable runs, receipts, cursors, logs and caches
  memory/                   baseline; learned rules, topics and topic index
  _artifacts/board.md       baseline; retained board path
  tmp/                      optional; disposable working material only
  work/                     optional; substantial agent-owned work
    backlog/<work>/         optional; work not started
    <active-work>/          optional; named folder at the work root while active
    done/<work>/            optional; completed work; an optional domain grouping may sit beneath done/
```

`work/` uses the work convention: `backlog/` for work not started, a named folder at the root of `work/` for active work, and `done/` for completed work. `done/` is not an archive. A decision in `done/` stays authoritative until superseded. Generated harness files stay at the paths each harness requires. The installer owns them. The tree omits them. `task.md` stays at the agent root for a one-task agent. Private credential values stay in their designated secret store. `settings.json` names environment variables.

| Path | Kind | Who writes | Who reads | Tracked |
|---|---|---|---|---|
| `prompt.md` | authored standing instructions | the owner, or an agent only at the owner's active request | the launched agent | yes |
| `agent.json` | authored launch record | `rbtv agent` and the agent for its own selections | launch | yes |
| `settings.json` | machine-local choices | the agent for its own tools, hooks and MCP servers; owner choices are kept | the agent | no |
| `rbtv/` | authored source | the agent | the installer | yes |
| `runtime/` | operational data | the tool that owns the bucket | that tool | no; not disposable |
| `memory/`, `_artifacts/board.md` | durable baseline records | the memory and board writers | the agent | yes |
| `tmp/` | disposable material | the agent | the agent, for the current task | no |
| `work/` | durable work | the agent | the agent and later readers | yes |
| generated harness files | generated output | the installer | the harness | no |

## project

A project is bounded work with a defined end. It keeps a named overview and a task file when it has a task. The work convention sits at the project root, beside those files: `backlog/` for work not started, a named folder at the project root for active work, and `done/` for completed work. `done/` is not an archive. Its decisions stay authoritative. A domain may group under `done/`. No universal extra level is required.

One index, one routing table, one instruction file. `{name}.md` is the index: a description of purpose, scope and current state, then the folder's only routing table (`File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN`). `CLAUDE.md` or `AGENTS.md`, whichever the installation maintains, is mandatory. It says to read the index first and carries the folder-wide rules. It holds no second routing table and no generated section. `meta/para` ships the templates a creation step copies. Afterwards the files are the user's.

The task file is `{name}-tasks.md`. Create it when the first task lands. Moving a folder into `done/` does not hide an unfinished task: reconcile the task before calling the work complete.

| Path | Kind | Who writes | Who reads | Tracked |
|---|---|---|---|---|
| `{name}.md` | authored index; the only routing table | the user or the agent doing the work | anyone opening the project | yes |
| instruction file | authored folder rules; required | the user or the agent | the harness, for work in the folder | yes |
| `{name}-tasks.md` | authored tasks; optional until the first task | the user or the agent | task discovery | yes |
| `backlog/`, named active folder, `done/` | durable work; optional until that state exists | the agent doing the work | later readers | yes |
| generated harness files | generated output | the installer, when a component targets this folder | the harness | no |

## area

An area is a continuing responsibility. Its current reference stays at the area root. Bounded work inside the area follows the same work convention as a project: `backlog/`, a named active folder at the area root, and `done/`. `done/` is not an archive.

The index and instruction file follow the same rule as a project. `{name}.md` is the only routing table. The instruction file is mandatory, points at the index, holds the folder-wide rules, and holds no second routing table and no generated section.

| Path | Kind | Who writes | Who reads | Tracked |
|---|---|---|---|---|
| `{name}.md` | authored index; the only routing table | the user or the agent | anyone opening the area | yes |
| instruction file | authored folder rules; required | the user or the agent | the harness, for work in the folder | yes |
| `{name}-tasks.md` | authored tasks; optional until the first task | the user or the agent | task discovery | yes |
| current reference at the root | durable reference | the user or the agent | anyone continuing the responsibility | yes |
| `backlog/`, named active folder, `done/` | durable bounded work; optional | the agent doing that work | later readers | yes |

## plan

A plan folder is the generic plan folder of `meta/plan`. It may sit in a project, an area, an agent's `work/`, or any repository. The coordinating agent lives in `agents/` and is opened with spark. The workflow owns execution status. The overview points to it and does not keep a second task-state narrative. No extra status folders are imposed inside the plan.

```text
<plan-folder>/
  workflow.md                  required; the file the coordinating agent schedules from
  read-first.md                required; what every agent reads before its own task
  agents/<plan>-<agent>/       required; one agent folder per agent: prompt.md, agent.json, task.md
  reports/                     required; reports/<agent>.md written when that agent finishes
  checkpoints/                 optional; one file per owner checkpoint, when the plan has any
  judgements/                  optional; one verdict file per judge, and plan-review.md
  CLAUDE.md                    required; with AGENTS.md, the two-line pointer to workflow.md
  AGENTS.md                    required; the same two lines
  decisions.md                 optional; created when the first ruling is written
  doubts.md                    optional; created when the first doubt is written
  status.md                    optional; created when the first status record is written
  loose-ends.md                optional; captured loose ends, when the plan records them in a file
  ideas.md                     optional; framed ideas, when the plan records them
```

| Path | Kind | Who writes | Who reads | Tracked |
|---|---|---|---|---|
| `workflow.md`, `read-first.md`, `agents/` | authored plan source | the planning method, then the coordinator for status | the coordinating agent; each agent reads its own task and `read-first.md` | yes |
| `reports/`, `checkpoints/`, `judgements/` | durable work products | the agent named by the file | the coordinator and judges | yes |
| `CLAUDE.md`, `AGENTS.md` | authored pointers | the planning method | a harness that opens the folder | yes |
| `decisions.md`, `doubts.md`, `status.md`, loose-ends and ideas files | optional authored records | the agent that first needs the record | later readers | yes |
