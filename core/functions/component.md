---
description: "The functions component — small standalone cognitive functions: single-prompt behaviors (interview, investignosis, digest, …) exposed as skills and invoked conversationally from any session."
---

# functions

A pool of conversational behaviors. Each function is ONE prompt file under
`prompts/`, structured as a seat prompt (kind-named cognitive-unit sections),
plus ONE `exposure.csv` row exposing it as a skill. A multi-mode function MAY
additionally keep per-mode method cards under `references/` (see below). No
seats, no workflow, no tools — a capability-only component in the `web/browse`
shape.

Adding a function = add `prompts/<id>.md` + one exposure row, then re-run the
installer.

## Functions

| Function | What it does |
|----------|--------------|
| `brainstorm` | Define something still unclear, or generate new ideas — routes to one of six methods (problem structuring, ideation, idea sparring, pre-mortem, first principles, six hats) |
| `handoff` | Transfer all session knowledge about a piece of work into one cold-startable document for a zero-context agent |
| `interview` | Interview the user with hard, critical questions to excavate and pressure-test their thinking |
| `investignosis` | Investigate and/or diagnose something in the code/file base — two consecutive passes (evidence first, defended root cause second), self or via a `swarm` |
| `triage` | Owner-ruled triage of a backlog file — task file, `issues.md`, or `loose-ends.md` |

## The `references/` pattern (owner-ruled 2026-08-21)

A function whose job splits into several distinct METHODS — one behavior, many
ways of running it — MAY keep each method as its own reference file under
`references/`. The prompt file stays a lean ROUTER: it picks the mode, states
the read as an explicit procedure step at the moment the mode runs, and carries
no method prose of its own. The occupant reads exactly ONE method card per
invocation, so a six-mode function costs the context of a one-mode one.

Rules:

- Reference paths in the prompt are component-relative (`references/<mode>.md`).
- Reference files get NO `exposure.csv` row — they are read by the router
  prompt, never exposed or invoked on their own.
- The single-prompt functions above are unaffected: a function with one method
  keeps that method in its prompt file and grows no `references/` folder.

`brainstorm` is the live instance of this shape.
