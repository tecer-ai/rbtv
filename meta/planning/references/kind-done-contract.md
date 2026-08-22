---
description: decision procedure for authoring the done-contract section of a task file
tags: [planning]
---

# `<done-contract>` — what done means

Record first: `sd-graph show "done contract"`. It rules meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

Machine-checkability: done-criteria an edge job or verifier can judge with no interpretation, plus a route for every scenario — so acceptance is computed, never argued.

## why it exists

The contract is the gate between seats: work flows on only when its criteria pass, and its outcome map is what makes retry loops possible — a failure scenario that routes back to a validation task IS the loop's static existence. A contract nothing can check is not a contract; it is a hope.

## when one exists at all

Every task carries exactly one (`sd-graph show "cognitive unit"`, Requirement matrix). The same concept binds at other radii — goal and milestone contracts run-side, the outcome at the prompt radius (`sd-graph show outcome`) — this section authors the TASK radius only; each radius has its own home, never copies.

## what belongs — and what never does

Belongs:

- Observable done-criteria: file exists at the declared home, command exits 0, count matches, every named section present.
- The contract's constraints on the result — bounds the output itself must satisfy.
- The **outcome map**: for completion AND each failure scenario, the next step the workflow takes.
- A **feedback schema** per failure scenario: the structure the fail verdict's feedback follows, seeding the retry.

Never:

- Vague nouns — a clause two readers could score differently is a defect to fix at authoring cost, not at execution cost.
- The aim (task goal) · surfaces (scope) · method (procedure, prompt-side).
- Criteria requiring the author's unstated context to judge — the verifier holds only the contract's text.
- A count as sole proof of a content criterion: a count is necessary, never sufficient.

## how to write an optimal one

1. Write each criterion as a check something can RUN: name the observable, the probe, and the threshold. "The brief is thorough" fails this; "the brief answers each seeded question, with ≥1 cited source per answer" passes.
2. Enumerate failure scenarios honestly — partial output, failed validation, blocked dependency — and route EACH: retry, route back, escalate. An unrouted scenario stalls the workflow at runtime.
3. Give each failure route its feedback schema, so the retry starts from structure, not prose.
4. Test by adversarial read: could work satisfy every clause and still be wrong? Add the missing clause — that gap is where bad work gets accepted.
5. Keep criteria use-case-neutral and seed-relative ("the seeded subject", "the declared destination") so the contract binds every run — ad-hoc goal, optimize, port, or scaffold — unmodified.
