---
id: write-task
description: "Author the complete body of the seeded task piece inside the assigned probe folder — the three-field card and exactly the three kind-named sections, with no i/o field and no capabilities field anywhere"
---

<task-goal>
Deliver one complete task file body for the seeded piece, its card and its three sections authored to the guides this task names.
</task-goal>

<scope>
- **Read:** the seeded piece row; the task-file law, the three section guides, and the prose law in the files named in this task's Guides bullet; the target component's existing task files, as precedent for its live conventions.
- **Write:** the assigned filename inside the assigned probe folder — nothing else. The target path the piece row names belongs to the dispatching seat.
- **Guides — read whole before writing:** `references/file-task.md`; `references/kind-task-goal.md`; `references/kind-scope.md`; `references/kind-done-contract.md`; `references/authoring-style.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- A file exists at the assigned filename inside the assigned probe folder, carrying frontmatter and all three sections whole — no placeholder, no section deferred.
- The frontmatter parses as YAML and carries only these fields: `id`, `description`. `id` equals the assigned filename's stem; a `capabilities:` field is absent — it is retired, and the paired prompt carries the means — and a `context:` field is absent, which is DELETED, not optional: standing pointers are named in the task's `<scope>` and instruments in the paired prompt's `<resources>`.
- The body carries exactly three kind-named XML sections in this order — task-goal → scope → done-contract — one of each and nothing else.
- NO i/o field appears anywhere in the file: the run's concrete question, inputs and output destination arrive with the seed.
- The task goal states ONE aim in one sentence; an aim needing "and" twice is two tasks.
- The scope names read surfaces and write surfaces separately, and every surface it names is one the done contract fails without.
- Every done criterion is a check something can RUN — it names the observable, the probe, and the threshold — and the contract carries an outcome map routing completion and EVERY failure scenario, each failure route carrying its feedback schema.
- Every statement is seed-relative, so the file serves every run unmodified; no owner-specific value appears.
- The return `{piece-id, kind, probe-path, self-check: pass|fail, evidence}` reached the dispatcher, its evidence naming, per rule of the named guides, the draft line that satisfies it.

Outcome map:

- **self-check pass** → the dispatching seat re-reads the body and lands it at the piece row's target path.
- **self-check fail** → the return still reaches the dispatcher, naming every failing rule. Feedback schema: {piece-id, the rule, the draft line that fails it}.
- **The aim needs a second sentence** → return `self-check: fail` with the split named; the decomposition is wrong and no stretched goal is drafted. Feedback schema: {piece-id, the two aims, the sentence carrying the second}.
- **A done criterion no probe can run** → return `self-check: fail` naming that criterion; a contract nothing can check is not drafted as if it were one. Feedback schema: {piece-id, the criterion, what would make it observable}.
</done-contract>
