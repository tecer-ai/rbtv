---
description: Read at the moment of creating, changing, or auditing a component's or capability's artifact set — which files exist, when each exists at all, and what belongs in each.
tags: [planning]
---

# Component anatomy — which files, when each exists, what goes in each

You are about to create or change component artifacts — as an assembler, a binder, a collapsed planner, or a toolsmith task registering a capability; the same procedure serves an ad-hoc goal, an optimize pass, a port, and a scaffold build. Legality (what each artifact IS) lives in the knowledge graph — `sd-graph show <term>` every artifact before writing it; this page's own cargo is the judgment no record carries: whether a file should exist at all.

## 1 — The artifact set (legality by record)

Placement first: a component folder is a direct child of a MODULE folder — check the membership tests (`component folder`, `module folder`) before landing a new component anywhere else, and never write a `module.md` for a folder the module membership test denies. A component folder's children are its KG `lives-in` inverses — verify the live set with `sd-graph inbound "component folder"` (9 at this writing) rather than trusting any list, this table included:

| Artifact | Exists when | Record (`sd-graph show`) |
|---|---|---|
| `component.md` | ALWAYS — no `component.md`, no component | `component entry point` |
| `exposure.csv` | the component exposes at least one part | `exposure manifest` — everything about it: `exposure.md` |
| `package.json` (the owning ecosystem's own manifest) | ONLY when the environment must provide something | `dependency manifest` |
| `prompts/<id>.md` — flat pool | the component defines prompts for agentic seats | `prompt pool` · `prompt file` |
| `tasks/<id>.md` — flat pool | the component defines tasks | `task pool` · `task file` |
| `seats.csv` | the component mints seats (executor-definition × task) | `seat catalog` |
| `capabilities/<name>/` | it passes step 3 below — never by default | `capability folder` |
| `references/` | standalone applied-not-executed content passes step 1 below | `references folder` |
| `workflows/<name>/` | the component ships a cataloged workflow | `workflow folder` — mechanics: `workflow-anatomy.md` |

Layout ruling: NO `prompts.csv`/`tasks.csv`, NO per-unit cognitive-unit files — one file per prompt and per task, kind-named XML sections inside, frontmatter as the card; `seats.csv` stays. Read `sd-graph decision d-prompt-task-files` before authoring any prompt, task, or seat; authoring those files is the prompt-file/task-file guides' job (siblings in this folder).

## 2 — The existence test (this page's own cargo — run before creating ANY file)

1. **Does it need to exist at all?** A file restating what an existing surface already documents — a CLI's own `--help`, a KG record body, a sibling file — is a restatement liability: it drifts the moment either side moves, and it is a worse copy on the day it is born. Precedent: three per-CLI capability files were built and deleted the SAME DAY because each restated its CLI's `--help`.
2. **Does a sibling already serve it?** Before authoring ANY cognitive unit, check the other workflows of this component, then the other components of this module, for a unit that already serves the need — and SHARE it rather than author a second one: a same-component read, an exposure promotion, or a marker-delimited carried block. A copied unit is two homes for one fact and drifts from the day it is born. A need a sibling ALMOST serves is an AMENDMENT to the sibling, never a new file beside it.
3. **Capability folder or routing line?** A capability folder exists ONLY when the capability needs standing instructions its own tool cannot carry. A tool documented by its own `--help` gets a routing line in the component's router surface (the exposed entry point — `exposure.md` §3, never `component.md`), not a folder — and a later-added tool is a routing line too, never a new file by default.
4. **Never author a measured-state companion.** Per-machine install/state tables are runtime observations: probe, don't store — a stored table is a second copy that goes stale in silence (`dependency manifest` § membership test).
5. **One fact, one home.** Before writing a fact, name its single home; every other surface points to it. Install and dependency facts home in the dependency manifest — package names, version ranges, and the per-element install commands (`rbtv.install`) — never in `component.md`, never in a reference.
6. **Where does it get written?** (owner-ruled) A produced component part is written where its component LIVES: a `.rbtv/mirror/` component's parts go in that mirror folder, an rbtv-repo component's parts go in that repo's module folder — NEVER into a `.claude/` installed copy, which the next install overwrites. A part whose destination this rule cannot resolve is REFUSED back to its requester with the ambiguity named, never guessed.

## 3 — What belongs in each (and what never does)

- `component.md` — orientation ONLY: what the component is, its exposed entry points, an optional entry-workflow pointer. Its reader is DECIDING WHETHER TO ENTER (the CLI delivers it at drill level 2) — a different reader from the working surface, so never merge the two files. History, build rationale, install facts, and tool documentation never live here.
- Prompt and task files — the kind guides and the prompt-file/task-file guides (siblings) own their authoring; this page only places them.
- A capability's instruction file — body = procedure, frontmatter = i/o spec, IN PLACE in its capability folder; never pooled, never split into unit files.
- `references/` — flat standalone reference files; each passes existence-test step 1 first.

## 4 — Exposure is the sibling's

How any part is exposed — method choice, manifest rows, and how the component's surface is organized for progressive disclosure — is owned by `exposure.md`. Decide nothing exposure-side from this page.

## Stop rule

An artifact kind this page and the KG both lack a home for: STOP and surface the gap. A missing guide is a build gap, never a judgment call.
