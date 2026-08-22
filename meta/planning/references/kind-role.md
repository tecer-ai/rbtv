---
description: decision procedure for authoring the role section of a prompt file, including its persona and agent-type sub-kinds
tags: [planning]
---

# `<role>` — the prompt's identity section

Records first: `sd-graph show role` · `sd-graph show persona` · `sd-graph show "agent type"` · `sd-graph decision d-persona-judgment-residue`. The records rule meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

Aim. The role points the occupant's judgment at exactly the search space the seat's contracts cannot reach. The persona AIMS; the done contract JUDGES — a role never enforces anything.

## why it exists

An occupant with no identity defaults to a generic assistant: it stops at the first plausible answer, hedges, and accommodates. The role replaces that default with the seat's own optimization target.

## when one exists at all

Every prompt carries exactly one — the requirement matrix (`sd-graph show "cognitive unit"`, its Requirement matrix field) makes role required for a prompt, so existence is not the judgment call. The call is persona THICKNESS: strength scales with the seat's judgment content. A persona with almost nothing to say about WHO the agent is signals mechanical mass that belongs in code — at the limit, reseat the job on a deterministic tool and author no prompt at all.

## what belongs — and what never does

Three facets, all inside this one section. Persona and agent type are indented sub-kinds of role in the requirement matrix — they get no separate top-level sections and no separate guides:

- **agent type** — the team-function classification, picked from the settled taxonomy (`sd-graph show "agent type"`); never invent a type.
- **persona** — WHO the agent is: the character/standpoint covering ONLY the seat's judgment residue — stopping criterion, exploration breadth, risk posture, tie-breaking where the instructions are silent.
- **role-level scope** — the role's standing remit, in prose. Distinct from the task file's `<scope>`, which names one task's surfaces.

Never in a role: method steps (procedure) · grants or bans (permissions, restrictions) · the standing aim (that is the outcome, under the i/o spec — the role-level "agent goal" field is retired) · task specifics (seed-carried) · theatrical costume.

## how to write an optimal one

1. State in one line what this seat optimizes for — and what it never optimizes for. If you cannot, the seat must not exist.
2. Write the persona as the character that would search that way (a never-satisfied examiner keeps probing where a neutral agent stops early).
3. Size it to the judgment residue: open-ended seat → thick, load-bearing persona; mostly-constrained seat → thin, analytical one. Thinness is a diagnostic, not a defect — act on it.
4. Check convergence: two seats whose honest personas converge are one seat.
5. Phrase everything use-case-neutrally — the same role must serve an ad-hoc goal run, an optimize, a port, or a scaffold run unmodified.
