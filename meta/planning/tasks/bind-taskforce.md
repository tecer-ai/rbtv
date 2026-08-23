---
id: bind-taskforce
description: "Bind executors late per seat, append the team's rows to the run's single taskforce.csv, register, then verify materialized seats on disk"
---

<task-goal>
Bind an executor to every seat of the seeded checked plan, append the team's rows to the run's single `taskforce.csv`, register, and verify on disk what materialization produced.
</task-goal>

<scope>
- Read: the checked plan under `planning/current/` — the manifest at `manifest.csv`, the seat pairs under `seats/<seat-id>/`, and its disposition record at `dispositions.md`; the staffing hints (prompt frontmatter and seat catalog); the run's `taskforce.csv`; the materialized seat folders; the guides named in this task's Guides bullet.
- Write: the pass's casting sheet at `planning/current/bindings.json` — the GOAL-LOCAL sheet, which is where a pass that AUTHORED its seats inside the goal casts them; written through `rbtv-bindings` (`catalog` → `scaffold` → `set`, each verb handed the GOAL FOLDER) and never by hand. A pass whose seats belong to a CATALOGED workflow casts them in that workflow's own central sheet instead, under the module config root — one file per workflow, addressed by workflow code, reached by handing the same verbs the manifest rather than the goal folder. That path is NOT restated here and must never be backticked into this bullet — every backticked path token in this clause is projected into the seat's declared outputs and gated against its cage, and the central sheet lies outside it. The bindings capability's own `bindings.md` is its one home; read it there. Also: the run's `taskforce.csv` (append only); the produced seats' `seat.md` inscriptions (ephemeral product); the verification report at `planning/current/verification.md`.
- **Guides — read whole before writing:** `references/workflow-anatomy.md`; `references/component-anatomy.md`; `references/exposure.md`; `ws:1-projects/build-ignite/system-definition/primer.md`.
</scope>

<done-contract>
Done when, checkable at the edge:
- One row appended to the run's `taskforce.csv` per plan seat — row count equals seat count; every pre-existing row byte-identical.
- Every row's `after` set (guards included) matches the manifest's; every agentic row binds harness + model + effort; every deterministic row binds a tool.
- The pass's casting sheet reports `uncast: none` under `rbtv-bindings inspect` (handed the goal folder for goal-authored seats, the manifest for cataloged ones), and every value in it came from a `set` — a harness+model outside `rbtv-bindings catalog` is a defect, not a choice.
- For an ephemeral product: every produced seat's `seat.md` carries its FULL content, frontmatter naming source prompt/task ids only where a cataloged definition was reused.
- The registration passes the goal lint at exit 0.
- `planning/current/verification.md` lists, per row, the materialized artifact found on disk — written from a read-back performed after materialization. (The file may exist EMPTY from spawn — existence is not the artifact; the per-row listing is.)

Outcome map:
- All rows verified on disk → completion: the pass's terminal act.
- The goal lint rejects the registration → fix registration data and re-lint; a defect in plan content → FAIL back; feedback schema {lint-output, offending-artifact}.
- Materialization missing or partial after registration → FAIL-BLOCKED naming each missing artifact; feedback schema {row, expected-artifact, observed}.
</done-contract>
