---
id: draft-plan
description: "Produce the complete draft plan — seats/workflow, envelope and credential-name sections, interact flags, outputs, relaunch budget"
---

<task-goal>
Produce the complete draft plan for the seeded goal: every design milestone detailed, the execution seats or workflow, envelope and credential-name sections, interact flags, declared outputs, and relaunch budget.
</task-goal>

<scope>
- **Read:** `planning/design.md`, `planning/facts-brief.md`, and every artifact those name.
- **Write:** `planning/draft-plan.md` — and, as parts of that same plan, `planning/execution-contract.md` and the plan's own execution seat set under `planning/current/` (see the done contract). All three ride the goal's shared `planning/` workspace, which the cage opens read-write to every seat; they are ONE product with parts, not a second `goal-writes`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/draft-plan.md` exists and its first line is exactly `DRAFT-PLAN`.
- Every milestone id from `planning/design.md` appears, detailed; no id added or dropped.
- The body has an execution seats/workflow, a permission-envelope *section*, a credential-name *section* (names only), per-seat interact flags, declared outputs, a relaunch budget, and named handoff contents.
- An **EXECUTION DECLARATION** section is present and complete. Approval BIRTHS the execution goal: the owner's `approve` runs a Path-B birth that scaffolds a new goal folder and MINTS its roster, so a plan with no declaration has no truthful value for the fields that birth requires, and no plan executes "in place" inside the planning goal. The section carries exactly these fields and no others — they are what the `approve-package` writer takes:
  - `execution-goal` — the bare safe name the goal will be born under. It becomes a path segment under `.rbtv/goals/` AND the goal name `rbtv-goal scaffold` takes, so it must be lowercase kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`) and must not be `owner`. Not a path, not a title, not a sentence, and never an underscore, a dot or a capital.
  - `lane` — the born goal's lane, as `scaffold --lane` takes it.
  - `roster` — the execution seat ids, comma-separated. Duplicate ids are refused at birth.
  - `workflow` and `sheet` — where the plan lands as a durable workflow, when the owner declared durable at goal creation. Omitted for a one-off taskforce, and said to be omitted.
  - `contract-file` — REQUIRED, and it is `planning/execution-contract.md`, the file this task writes. The birth reads it out of the bound commit's tree and it becomes the born goal's `goal.md` body; a package naming a file that is not under the plan artifacts, or not there at all, is refused at the writer.
- The declaration says, in the plan's own words, that the daemon mints those roster seats AT BIRTH from this declaration. NO seat in this planning goal casts, materializes, or launches an execution seat, and no milestone may assign that act to one — a milestone whose mechanism names a planning-goal seat as the caster is not draftable and the mechanism must be rewritten to the birth.
- `planning/execution-contract.md` exists and is the CONTRACT THE BORN GOAL IS BORN UNDER — the owner's request restated as this execution goal's contract, plus a pointer to the plan artifacts at the bound commit (which artifacts, and that `planning/bound-plan.json` in the born goal records the commit). BODY ONLY: no YAML frontmatter, because `scaffold` writes the goal's own frontmatter and puts this text under it — a second `---` block lands inside the body. It is not the draft, not a summary of the draft, and not a copy of it: it is what a stranger seat opening the born goal reads first.
- Where the declaration omits `workflow` (a ONE-OFF plan — the ordinary case), the plan's execution seats are AUTHORED HERE, in the layout the birth mints from, because no catalog carries them:
  - `planning/current/manifest.csv` — header `Seat/workflow,after,i/o,Modality`; one row per execution seat; `after` names only seats of this same manifest (a member naming nothing that exists is refused at birth).
  - `planning/current/seats/<seat>/` — exactly two files per seat, a PROMPT and a TASK. Each carries YAML frontmatter with a unique `id:` and a `description:`, over kind-named sections: the prompt's `<role>` (plus `<permissions>`, which is a HARD GATE — a seat with no permissions block is refused) and the task's `<task-goal>`. The prompt's frontmatter also carries the seat's `goal-writes`, `cage-grants`, `rw-paths` and `on-fail-relaunch` cells; `on-fail-relaunch` names a SEAT, never a boolean.
  - Every `id:` must be unique inside the plan AND must not be one the component catalog already carries — a goal-authored definition may never shadow a cataloged one, and the birth refuses when it does.
  - `planning/current/bindings.json` — the casting sheet, one entry per manifest seat under `seats`, each with `harness` and `model` (plus `agent_type`, `mode`, `effort`, `ctx-refresh`). An uncast seat is a named refusal at the birth: harness and model are not the daemon's to invent.
  - The roster in the EXECUTION DECLARATION names seats of this manifest and nothing else. A roster id the manifest does not carry, and an empty roster with no manifest, are both refused at the approve-package writer.
- No per-seat wall-clock deadline field. No durable scaffolding minted. Envelope is a section, not a compiled artifact.
- Every produced execution seat carries the six authoring declarations (one `goal-writes` or documented empty+chat schema; instruments named; interact+fallback when the role reaches a human; seat-folder names; no hardcoded owner values; a complete done-contract).
- An `input-gaps` list is present (may be empty).
- Completeness: every actor has a seat or an explicit out-of-scope; every input has a source seat or an input-gap; each seat names its failure arm; two seats with the same id is a fail; a declared output present in neither a seat `goal-writes` nor a named handoff is a fail; a roster seat id absent from the plan's own seat list, or a plan seat absent from the roster, is a fail.

Outcome map:

- **Complete** → the draft, the execution contract and the plan's own seat set seed review+finalize.
- **Markerless upstream** → repair forward, log the gap, complete. Never reject. Never re-enter design.
- **Owner reject-retry comments** (when this task is relaunched with comments as a closed findings list) → treat those comments as the only fix targets; do not reopen the approach.
</done-contract>
