---
description: Read at the moment of picking WHICH harness primitive exposes a part — the audience × trigger table, and the skill-vs-sub-agent call in full.
tags: [planning]
---

# Exposure choice — which primitive

You have already ruled that an agent should reach this part ON ITS OWN (`exposure.md` §2, step 1). This page picks the ONE method. The closed method canon, the manifest row shape, seat-folder materialization, progressive disclosure, and the stop rule for an exposure no method fits all live in `exposure.md` — none of it is restated here.

## 1 — The decision table

Read the part's AUDIENCE (who reaches it) and its TRIGGER (what makes it arrive), then stop at the first row that holds.

| Audience | Trigger | Method |
|---|---|---|
| agent | on-demand | `skill` |
| human | on-demand | `command` |
| agent | always-on, every turn | `rule` |
| machine | event | `hook` |
| agent | dispatchable | `sub-agent` |
| any agent working in the folder | folder-ambient | `agents.md` |
| a shell | reached as a tool | `path` |
| the harness | registration payload | `config` |
| the assembler | shopped as a closing seat | `pool` |

Audience is what separates `skill` from `command`; trigger is what separates `skill` from `rule`.

## 2 — Skill or sub-agent

The two get confused because both put work in front of an agent. They differ in WHERE the work runs and WHAT the caller keeps.

A **skill is LOADED INTO THE CALLING AGENT'S OWN CONTEXT.** The caller keeps its context, its turn, and its authority; what the skill carries, the caller now holds and acts on directly. Reach for a skill when the caller MUST RETAIN what it learns.

A **sub-agent is DISPATCHED INTO A SEPARATE CONTEXT and returns a structured result.** The caller keeps that result and nothing else — every intermediate read the sub-agent made stays in the sub-agent's context and dies with the dispatching step. Reach for a sub-agent when ANY holds:

- The work is bounded and fully describable in a task artifact.
- Its intermediate reading would flood the caller's context.
- It must run in parallel with siblings.
- It needs a different model tier than the caller.

Tie-breakers, in order:

1. The caller reasons over the output turn by turn → `skill`.
2. The work is a bounded unit with a return schema → `sub-agent`.

Live precedent in this component's `exposure.csv`: `researcher` and `diagnoser` are `method=sub-agent` — each is a bounded probe whose reading would flood the interviewer and whose product returns as a foldable result. `workflow-authoring-checklist` and `create-cli` are `method=skill` — the seat that opens either must hold it while it authors.

## 3 — One canonical method per part

A part gets exactly ONE method and ONE row. Two rows for one part is the manifest saying one fact twice, and every check keyed on part→method then has two answers. When two methods both look defensible, the part's real trigger has not been read yet — read it again rather than adding a row.
