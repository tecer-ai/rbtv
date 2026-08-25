---
description: "The trail component — the innovation trail itself: the M1 Conception → M2 Validation → M3 Brand sequence, its minimal per-project state and resume protocol, and the startup-mentor persona that walks a founder through it."
---

# trail

This component owns the JOURNEY, not the frameworks. It carries the milestone sequence and the
recommended framework order, the concept-ownership maps that say which framework owns which idea and
which later framework may reference it, the per-project state protocol (one memo file, five
frontmatter fields), and the mentor persona that runs the whole thing conversationally.

The boundary against its three sibling components is exact: `conception/`, `validation/` and
`brand/` hold the frameworks — what a Lean Canvas box means, what a good positioning statement
contains. Nothing here restates a framework, and nothing there states sequence, state, or persona.

## Parts

| Part | What it is |
|---|---|
| `references/innovation-trail.md` (reference) | The trail: milestones, recommended framework order, concept-ownership maps, the memo state protocol, and the run protocol. Exposed as the `innovate` command — the human front door. |
| `prompts/innovation-mentor.md` (prompt) | The startup-mentor persona (Paul, Startup Lifecycle Guide) and its routing procedure: whole trail, or one framework standalone. Exposed as the `innovation-mentor` skill — the agent front door. |
| `exposure.csv` (exposure manifest) | Two rows, one per front door above. Nothing else in this module is exposed on its own; every framework reference is reached through the persona's routing table. |

## Mapped but not yet migrated (preserved from the old module, 2026-08-21)

**None of what follows is part of this module.** It is the old module's own map of work that was
started or named but never finished, reproduced here so it is not lost. To pick any of it up, migrate
from the old paths named at the end of this section.

**M4 Prototypation** — a real milestone workflow in the old module (`bi-m4-prototypation`), but never
wired into the old master routing table, which stops at M3. Its goal was turning validated M1–M3
concepts into HTML prototypes. Its framework table, verbatim:

```text
| Code | Framework | Workflow | Output | Status |
|------|-----------|----------|--------|--------|
| [U] | User Flow & IA | ./bi-m4-user-flow-ia/workflow.md | user-flow-ia.md | ✅ Available |
| [D] | Design Direction | ./bi-m4-design-context/workflow.md | design_brief.md + design.json (via bridge) | ✅ Available |
| [B] | Build Prototype | *(to be created)* | HTML/CSS prototype | 🚧 Planned |
| [C] | Conversion Optimization | ./bi-m4-conversion-centered-design/workflow.md | conversion-optimization.md | ✅ Available |
| [H] | Heuristic Evaluation | ./bi-m4-heuristic-evaluation/workflow.md | heuristic-evaluation.md | ✅ Available |
| [F] | Testing Prep | *(to be created)* | testing-protocol.md | 🚧 Planned |
```

The M4 sequence: User Flow & IA → Design Direction → Build Prototype (planned) → Conversion
Optimization → Heuristic Evaluation → Testing Prep (planned). Conversion Optimization and Heuristic
Evaluation may run independently after the build.

Design Direction `[D]` is a BRIDGE, not a self-contained framework: it assembles M1–M3 and User Flow
& IA context and then invokes the external `bmad-method-lifecycle:bmad-create-ux-design`. Anyone
migrating M4 inherits that external dependency and must decide what replaces it.

**M5 Market Validation** and **M6 MVP** are downstream NAMES only — no workflow folders, no framework
routing tables, no framework data anywhere in the old module. The only M5 methods ever named in the
trail are **SPIN Selling** and **Smoke Test**; M6 is named as MVP and nothing more.

**The old module was DELETED from the rbtv repo on 2026-08-21** (owner-directed; rbtv commit
`fef8f455`, branch `ignite/core-daemon`). The paths below no longer exist on disk — recover any of
them from that repo's git history at `fef8f455^` (the deletion commit's parent), e.g.
`git -C 3-resources/tools/rbtv show 'fef8f455^:<path>'`.

Old source paths to migrate from (as they existed at `fef8f455^`):

- `3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m4-wip/` — the four built M4
  framework folders, their `workflow.md` files, their `data/*.md` framework documents, and
  `data/milestone-overview.md`.
- `3-resources/tools/rbtv/innovation/workflows/business-innovation/data/founder-process.md` — the old
  trail-level knowledge file. Its M1–M3 content is already migrated into
  `references/innovation-trail.md`; it maps no M4, M5 or M6 milestone, which is why the M4 map above
  had to come from `bi-m4-wip/workflow.md` instead.
- `3-resources/tools/rbtv/admin/roadmap/business-innovation-migration_v3/` — the old migration
  roadmap (planning history, including M4 and evaluation tasks, referencing since-superseded target
  paths). Not a dependency of anything; kept in the old repo as the record of how M4+ was planned.

## Origin (owner-ruled 2026-08-21)

Migrated from the old rbtv-repo module
`3-resources/tools/rbtv/innovation/workflows/business-innovation/` — this component from the
trail-level files (`workflow.md`, `data/founder-process.md`, `templates/project-memo.md`) and from
`3-resources/tools/rbtv/innovation/personas/paul.md`. The three milestone components
(`conception/`, `validation/`, `brand/`) took `bi-m1/`, `bi-m2/` and `bi-m3/` respectively.

Deliberately NOT carried: the micro-file step machinery (`steps-c/` numbered step files, one-step-at-
a-time loading rules), the `[N]`/`[C]`/`[H]`/`[DA]` menu and its fuzzy-match dispatch, Party Mode
(declared in the old help task but never implemented), the Vivian design-agent handoff inside
Brandbook, the `innovator-help.xml` help task, and the old two-layer state (a project memo plus
per-framework step frontmatter). The owner ruled state down to one memo file with five frontmatter
fields — see `references/innovation-trail.md` § State protocol.
