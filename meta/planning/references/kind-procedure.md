---
description: decision procedure for authoring the procedure section of a prompt file or a capability's instruction body
tags: [planning]
---

# `<procedure>` — the reusable HOW

Record first: `sd-graph show procedure`. It rules meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

A method the occupant can follow without improvising — every step it will need, in order, with nothing left to be discovered mid-work.

## why it exists

Without a stated method the occupant re-derives one per session, differently each time. The procedure is the one home of the seat's method; the task supplies only the specific WHAT at runtime.

## when one exists at all

Every prompt and every capability carries one (`sd-graph show "cognitive unit"`, Requirement matrix). The judgment call is per STEP: a step exists only if the work fails without it. Before writing any step, ask whether code can do it — a deterministic step belongs in a tool the procedure calls, never in prose the occupant simulates.

## what belongs — and what never does

Belongs:

- Ordered steps and their control flow — loops, branches, stop conditions — independent of any one run's inputs.
- Decision procedures: the test to run and what each result means.
- Forced reads, as explicit STEPS at the acting moment ("before authoring X, read Y") — a reference merely listed as available does not exist.

Never:

- Identity or posture (role) · standing bounds that hold across every step (constraints) · grants or bans (permissions, restrictions) · the deliverable contract (i/o spec).
- Run specifics — the concrete question, inputs, and destinations arrive with the seed.
- Restated record or reference content: point to it, at the step that needs it. A copied fragment drifts.
- KG citations as instructions. The occupant must act without a lookup: write "an edge exists only where data actually moves", never "per PRIN-4".

## how to write an optimal one

1. Walk the work start to finish; write the steps in execution order, one act per step.
2. Strip every step code could do into a tool call; keep reasoning only where only reasoning works.
3. Name each step's inputs and where they come from — a step that assumes undeclared material is a defect.
4. Wire guide/reference reads in as numbered steps at the moment they are needed, never as a reading list.
5. Re-read as the occupant with zero memory of this session: can you execute every step from its text alone? Fix what fails.
6. Keep it use-case-neutral — the same method must serve an ad-hoc goal, an optimize, a port, or a scaffold run unmodified.
