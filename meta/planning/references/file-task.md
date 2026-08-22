---
description: decision procedure for authoring a task file — frontmatter card, section set, section order
tags: [planning]
---

# the task file — `tasks/<task-id>.md`

Records first: `sd-graph show "task file"` (its file-schema field is the layout authority) · `sd-graph show task`. The records rule meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

One readable home for one reusable WHAT: the task's aim, surfaces, and done contract in a single document a stranger executor — and the seat row pairing it — can consume whole.

## why it exists

The task file is the specific-WHAT half a seat row joins to a prompt file's reusable HOW. Whole-file layout, versioned by git history alone — no version-ids, no references, no index, no lockfile, and no `tasks.csv` (the frontmatter IS the card; a catalog would duplicate it). `seats.csv` stays — pairing this task with a prompt into a seat.

## when one exists at all

One file per reusable task, in the component's `tasks/` pool. Before creating one: is this genuinely ONE bounded unit of work? A description needing "and" twice is two tasks — two files. Fully deterministic work is a job for a tool, not a task file for an occupant. And the file is a reusable TEMPLATE — a one-run specific belongs in the seed, not in a new task file.

## naming the id

The id is both the file name and the `id:` field, and it MUST name the ACT the task commissions, verb first: `interview-goal`, `split-goal`, `assemble-plan`, `bind-taskforce`, `judge-milestone`.

NEVER name a task after the workflow that runs it. A task lives in the COMPONENT's pool and any workflow in that component may pair it into a seat, so a workflow name in the id claims an ownership the model does not grant, and it goes false the moment a second workflow reuses it. The workflow code belongs to the SEAT id and nowhere else: seat `plan-interviewer` pairs prompt `interviewer` with task `interview-goal`. The verb's OBJECT may still name a subject one workflow owns — `judge-forge-build` judges a forge build — because that says WHAT is acted on, not who runs it. A collision inside the pool means the act name is too vague — sharpen it, NEVER prefix it.

## what belongs — and what never does

**Frontmatter — the card, exactly these fields:**

- `id` — the task's stable id; seat rows reference it.
- `description` — one line, for blurb-first staffing discovery.

**`context:` is DELETED, not optional** (owner-ruled 2026-08-14, W6/R3 — the `capabilities:` retirement's precedent). Standing pointers are named in the task's own `<scope>` read surface, where a task already says what it reads; the seat's INSTRUMENTS are named in the paired prompt's `<resources>`. `component-lint`'s `task-no-context` check refuses the field on any task file, and nothing carries it through assembly any more. Neither field may return: a card carrying either is a defect, never a variant.

**Body — one kind-named XML section per task-serving unit, in this order:**

`<task-goal>` → `<scope>` → `<done-contract>`

All three are demanded — confirm against the requirement matrix (`sd-graph show "cognitive unit"`, its Requirement matrix's task column), which wins on any mismatch. Author each by its guide: `references/kind-task-goal.md` · `references/kind-scope.md` · `references/kind-done-contract.md`.

**NO i/o fields, anywhere in the file.** The run's concrete question, inputs, and output destination are instance data arriving with the seed at runtime. An i/o section on a task file is a defect, not a variant — the i/o spec is a prompt/capability kind. The ban is on declaring the TASK FILE's own runtime inputs and outputs: a done-contract clause describing the required SHAPE of an artifact the task orders produced is pass/fail criteria and belongs there, never an i/o section in disguise.

Never in a task file: prompt-serving units (role, procedure, resources, permissions, restrictions, constraints) · a harness or model binding · seed data baked in as if reusable · a `capabilities:` field — RETIRED (owner-ruled 2026-08-10, core-build ledger `d-task-capabilities-retired`): a task states its WORK; the means it needs are identified by whoever authors the paired prompt (written into that prompt's `exposes:` and `<resources>`) and by the resource-definer/mechanizer flow, whose toolsmith tasks carry the capability requirements. `component-lint` check `task-no-capabilities` enforces the absence.

## how to write an optimal one

1. Answer the meta-question first — one line on what this task pursues and why it must exist. No answer → no file.
2. Author the three sections in order, each by its guide; keep every statement seed-relative ("the seeded topic", "the subject workflow") so one file serves every run and every use case — ad-hoc goal, optimize, port, scaffold.
3. Re-read as a stranger executor holding only this file plus a seed: aim, surfaces, and done-criteria unambiguous, nothing referring to this session. Then check the frontmatter parses as YAML.
