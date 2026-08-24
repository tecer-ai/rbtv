---
description: Use when asked to panel, or when one subject benefits from multiple independent points of view — parallel sub-agents examining the same thing through different perspectives, different models, or both.
tags: [sub-agents]
---

# Panel

A panel dispatches N sub-agents at the SAME subject, each contributing an independent point
of view. Where swarm layers waves to cover breadth, a panel is FLAT: one round of peers whose
value is diversity — different perspectives (agent roles), different models, or both. The
point: surface what any single viewpoint misses, and make disagreement visible instead of
averaged away.

## Trigger — a judgment call is in front of you

- A diagnosis, a verdict, a review, or a recommendation over more than a trivial evidence base
  is a PANEL. Never one agent, and never the manager itself.
- The test: does answering require weighing evidence that no single file read settles? Yes →
  panel. A judgment over N reports handed to one agent both breaks small scope (sub-agents
  skill § Staffing) and throws away the independence that makes the answer trustworthy.
- Trivial and settled by one read → one agent, no panel. Do not convene four lenses to confirm
  a value.

Staffing and launch mechanics are the sub-agents skill's (`references/sub-agents.md` — seats,
`cast` launches, output schemas, output location). This reference adds only what is
panel-specific.

## Interview — tiered

- **Always**: propose ONE composition to the user and get a confirm/adjust —
  the diversity axis (perspectives | models | both), the panelists (each one's angle and
  model), and whether a rebuttal round is on the table. One short round, then go.
- **Generative panels** (the panel produces solutions, designs, or drafts — not reviews):
  FIRST interview the user until the problem and their desired functioning are pinned.
  Every panelist inherits the problem statement; a vague one wastes the whole panel.

## Composition

- Panelists are ALWAYS sub-agents — the manager never takes an angle itself. A viewpoint
  produced inside the coordinator's context is not independent.
- Each panelist gets the same subject, a bounded scope, and ONE viewpoint stated in its
  prompt. Output schema is REQUIRED — panel outputs are always piped into synthesis.
- Diversity axes:
  - **Perspective** — same model, different roles/angles.
  - **Model** — same brief, different models (ideally different providers).
  - **Both** — the strongest form when the subject warrants the spend.

## Routing — the model-diversity exception

One `cast route` call for the task sets the CLASS and EFFORT for the whole panel. When model
diversity is a chosen axis, the top-verdict-only rule is deliberately relaxed — diversity is
the point here: run `cast route --catalog --json` and spread the seats across LAUNCHABLE
models within the tiers that class allows, preferring distinct providers over same-provider
variants. Eligible rows are the ones whose `use` column reads `route` or `panel` — a `panel`
row is in the roster FOR this, a model the owner wants heard in a panel but never named as a
single verdict. A `use: off` row is out: routing and panels both ignore it. The class boundary still holds (no reaching above the class's tiers), and the route
verdict's effort applies to every panelist.

## Synthesis

One run folder per panel (location per the sub-agents skill's output-location rule); every
panelist's raw output file is KEPT there — synthesis condenses, the raw files preserve.
A SYNTHESIS SEAT synthesizes — the manager reading N panelist outputs to combine them is the
violation the sub-agents skill's tripwire names. The manager synthesizes only a 2-panelist
panel it can hold in one page. Either way the synthesis is:

- **Convergence** — what multiple viewpoints independently agree on (the strongest findings).
- **Divergence** — where viewpoints conflict, with EACH side's argument. Never silently
  merged: a disagreement between independent viewpoints is signal, not noise.
- **Recommendation** — the manager's call, with its reason.

## Modes

The mode is whatever the subject needs; compose viewpoints freely. Two worked shapes:

- **Review panel** — panelists review one artifact, each through a different lens. Example
  lenses: adversarial (try to break it), consistency, bug hunt, design quality, root cause,
  first principles, customer/user, investor, completeness (edge cases, states), references
  (do the cited things exist and say what's claimed). The planning module's check seats
  (clarity, consistency, edges, permissions, resources, scope) are ready-made lenses to
  reuse when the subject is a plan.
- **Design panel** — after the deep interview, 2+ panelists each produce an independent
  solution to the same pinned problem (route class planner/broad — strong models), each with
  a small bounded scope and a shared output schema. Synthesis compares the designs and
  recommends one, grafting the best ideas from the others.
