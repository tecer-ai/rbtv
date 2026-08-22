---
description: decision procedure for authoring the task-goal section of a task file
tags: [planning]
---

# `<task-goal>` — the task's reusable aim

Record first: `sd-graph show "task goal"`. It rules meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

One simple job, stated once: an aim that holds for every seed this task will ever receive, and that a literal-minded executor cannot misread.

## why it exists

The task is the WHAT half of a seat. Its goal is the anchor everything else hangs on — scope selects surfaces FOR it, the done contract judges completion OF it. A task with a fuzzy aim makes both of those guesses.

## when one exists at all

Every task carries exactly one (`sd-graph show "cognitive unit"`, Requirement matrix). The judgment call is the task's own existence, upstream of authoring: if you cannot state the aim in one line, the decomposition is wrong — split or merge the task, do not stretch the goal.

## what belongs — and what never does

Belongs:

- One reusable statement of the aim — what this task pursues, phrased to hold across every run that seeds it ("produce a cited research brief on the seeded topic").

Never:

- The run's concrete question, inputs, or output destination — instance data, arriving with the seed at runtime.
- Done criteria or scenario routing — the `<done-contract>` kind.
- Surfaces — the `<scope>` kind.
- Method — procedure, on the prompt side of the seat.
- The prompt's standing objective — that is the outcome, under the prompt's i/o spec; the task goal is THIS task's aim, not the umbrella aim.
- A second job. A goal needing "and" twice is two tasks — split it.

## how to write an optimal one

1. State the aim in one sentence. If the sentence needs a second, the task is too big — go back to the decomposition.
2. Generalize over seeds: replace every run-specific noun with its seeded role ("the seeded topic", "the subject workflow") so the same task file serves every run — and every use case: an ad-hoc goal, an optimize, a port, a scaffold.
3. Check the pairing: the aim must be reachable by an occupant running the paired prompt's procedure under its grants. An aim the prompt cannot pursue is a mis-paired seat, not a bold goal.
4. Re-read as a stranger executor: could two readers pursue different things? Sharpen the nouns until they could not.
