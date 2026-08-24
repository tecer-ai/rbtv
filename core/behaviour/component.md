---
description: "The behaviour component — the always-on rules that govern HOW an agent thinks and answers, independent of what it is working on."
---

# behaviour

`behaviour/` holds the dispositions an agent carries into EVERY turn — how it receives a
request, how it responds to a proposal it disagrees with, how simply it decides to build, and
how it approaches a fix. Nothing here is task-specific
and nothing here is loaded on demand: every part is exposed with `method: rule`, which is what
separates this component from `core/functions`, whose parts are skills an agent reaches for at
a moment.

The boundary against `meta/planning`: planning references rule how an ARTIFACT is authored and
are read at the moment of authoring one. Behaviour rules govern the agent itself and are read
on every turn, authoring or not.

| Reference | Answers |
|---|---|
| `challenging` | **How does an agent respond to a proposal?** The pre-agreement `<counter>` gate, position stability under pressure, sycophancy tripwires, constructive adversarialism, first principles, second-order impact, and surface-never-act proactivity. |
| `problem-framing` | **How does an agent receive a request?** Reading a proposal as a question, the symptom check, deliverable-first, structured options, and named assumptions. |
| `kiss` | **How simply does an agent decide to build, BEFORE the work?** Does it need to exist at all, the simplest design that fully solves it, YAGNI, existing means first, complexity faced only when demanded. The code left AFTER the work is the `core/coding` skill's subject, not this rule's. |
| `root-cause` | **How does an agent approach a fix?** Cause never symptom, why down to the cause, the sibling sweep, the root cause written BEFORE the first edit, and the contract test that locates where a wrong value is born. The edit itself (where it lands, the band-aid deleted, the patch signs) is `core/coding`'s `no-patches`. |

## Entry points

- `references/` — the rule bodies.
- `exposure.csv` — one `reference`/`rule` row per file.

**ORIGIN 2026-08-21.** Both files carry forward the `Critical Partnership` and `Problem Framing`
sections of the retired `rbtv-reasoning` behavior rule, split into one subject each and extended
by owner ruling with first principles, second-order impact, constructive adversarialism, and
surface-never-act proactivity. That rule's other three sections — Self-Verification, Unnecessary
Pre-Work and Execution Discipline — were dropped with it by owner ruling, NOT rehomed here.

**2026-08-23.** `kiss` added (owner: "this is for all, not only coding"). `root-cause` split out of
`problem-framing` on the reference split test (a fix is a different moment than a request) with
its before-edit tripwire and the origin test — owner-ruled the ONE home of the written root-cause
statement; the `coding` skill's `no-patches` does not repeat it.
