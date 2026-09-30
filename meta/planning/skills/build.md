---
name: build
description: "Use whenever the user says plan, build, or create for any scaffolding — rules, prompts, skills, workflows, agents, parts of rbtv, or the mirror. The one router: mandatory reads, the workflow-vs-guide route rule, the per-kind authoring table, and every meta/planning guide. NOT plan-document writing."
---
# build — the scaffolding router

**You are reading this because a user wants scaffolding created or changed.** This page routes
the request to the right authoring guide or to the `plan` skill. Stop at the first section that
answers you; details live in the linked guides.

Written to be read cold. Nothing below assumes you saw an earlier turn.

---

## 0 — Mandatory reads, ALWAYS

Before ANY scaffolding act — routing included — read these three, every time:

| File | What it rules |
|---|---|
| `references/ethos.md` | the shared design ethos every built thing obeys |
| `references/component-anatomy.md` | which files a component or capability has at all, and what belongs in each |
| `references/exposure.md` | how a part reaches an agent — methods, the manifest, progressive disclosure |

---

## 1 — Plan or guide? The route rule

A multi-seat request routes to the `plan` skill, whose output is a console-orchestrated seat plan.
For a single, bounded component part, use the matching guide in §2 and edit it in the current
session. The guides also apply when a plan seat authors that part.

| The request is… | Route |
|---|---|
| ONE small part of an existing component — a reference, prompt, task, seat, capability, exposure entry, or sub-agent definition | Author it with the matching guide in §2; run `component-lint` on the touched component. |
| a new component, a new reusable workflow, a larger DAG change, or pieces spanning components | **plan** — `skills/plan.md`; settle the scope and decisions before writing its seat plan. |
| already-decided work to structure as a console-orchestrated seat plan | **plan** — `skills/plan.md`. |

If a small request exposes a larger unsettled goal, settle that goal before writing a seat plan.

---

## 2 — The KIND ROUTER (authoring table per piece kind)

Read the request and stop at the FIRST row that holds. The row names the guide, target path,
registration act, and condition that calls for a seat plan.

| Piece kind | Authoring guide | Target-path shape | Registration act | Escalates when |
|---|---|---|---|---|
| **a NEW COMPONENT** | `references/component-anatomy.md` | `<module>/<component>/` | component entry and any needed exposure rows | the work needs several seats or decisions are unsettled — use `plan` |
| reference | `references/kind-reference.md` | `<component-root>/references/<name>.md` | none by default — a reference is reached by an explicit prose read; an `exposure.csv` row appears only on a real exposure decision | its subject belongs to a component that does not exist |
| prompt | `references/file-prompt.md` plus the kind guide of each section it carries | `<component-root>/prompts/<id>.md` | a `seats.csv` row pairing it with a task; an `exposure.csv` row only where an agent must reach it on its own | it needs a manifest node in a workflow that does not exist |
| task | `references/file-task.md` | `<component-root>/tasks/<id>.md` | a `seats.csv` row pairing it with a prompt | the same |
| seat in a reusable component workflow | `references/workflow-anatomy.md` + `skills/workflow-authoring-checklist.md` | a row in `<component-root>/seats.csv`, plus one row in the workflow manifest when the seat holds a node | the `seats.csv` row and manifest row | several dependent rows change — use `plan` |
| capability | `references/kind-capability.md` | `<component-root>/<name>.md` for a single capability carrying no tool, otherwise `<component-root>/capabilities/<name>/<name>.md` | registered AND exposed in the same act — the `exposure.csv` row per `references/exposure.md` | its owning component does not exist |
| capability whose core is a CLI | the `create-cli` capability, followed exactly | `<component-root>/capabilities/<name>/tool/` — a CLI is a capability's tool, landed inside its owning component | the first-party `path` row in the owning component's `exposure.csv`, written in the same act — create-cli's *Expose the Finished Tool* close-out | the owning component cannot be resolved |
| exposure entry | `references/exposure.md` + `references/exposure-choice.md` | a row in `<component-root>/exposure.csv` | the row IS the act | no method in the closed canon fits the part |
| sub-agent definition | `references/file-prompt.md` + `references/file-task.md` | `<component-root>/prompts/<id>.md` and `<component-root>/tasks/<id>.md` | a `seats.csv` row with no manifest node and any needed exposure row | it needs a scheduled workflow node — use `plan` |

`<component-root>` is resolved by the write-destination rule, never guessed: a `.rbtv/mirror/`
component's parts go in that mirror folder, an rbtv-repo component's parts go in that repo's module
folder, and NEVER into a `.claude/` installed copy. A destination that rule cannot resolve is
REFUSED back to the user with the ambiguity named.

For capability versus agent setting, read `kind-capability.md`; for CLI discovery and parent
routers, read `exposure.md` § Skills are the discovery route.

---

## 3 — The guide table (every guide in meta/planning)

Reach a single guide when the moment its description names has arrived — no workflow launch needed
to READ. Descriptions are each file's own frontmatter, verbatim in spirit; the file self-documents.

**Authoring kinds — cognitive units:**

| Guide | Moment |
|---|---|
| `references/file-prompt.md` | authoring a prompt file — frontmatter card, section set, section order |
| `references/file-task.md` | authoring a task file — frontmatter card, section set, section order |
| `references/kind-role.md` | authoring a prompt's role section (persona, agent-type) |
| `references/kind-procedure.md` | authoring a procedure section of a prompt or capability body |
| `references/kind-io-spec.md` | authoring a prompt's io-spec (input, outcome, output) |
| `references/kind-constraints.md` | authoring a prompt's constraints, incl. the shared-ethos carry |
| `references/kind-restrictions.md` | authoring a prompt's restrictions section |
| `references/kind-permissions.md` | authoring a prompt's permissions section |
| `references/kind-task-goal.md` | authoring a task's task-goal section |
| `references/kind-scope.md` | authoring a task's scope section |
| `references/kind-done-contract.md` | authoring a task's done-contract section |
| `references/kind-reference.md` | authoring, splitting, merging, or refusing a reference file |
| `references/kind-capability.md` | ruling when a capability exists and what its instruction file carries |
| `references/authoring-style.md` | writing or amending ANY authored surface — the prose law |

**Workflows and seats:**

| Guide | Moment |
|---|---|
| `references/workflow-anatomy.md` | structuring a reusable component workflow DAG and its manifest |
| `skills/workflow-authoring-checklist.md` | authoring or amending reusable workflow seat declarations |
| `references/seat-id-naming.md` | naming a workflow's seat rows — the workflow-code prefix law |
| `skills/plan.md` | structuring already-decided work as a console-run seat plan |
| `references/headless-seat-cannot-wait.md` | a seat is about to background a check or end its turn expecting to be woken — and an orchestrator meeting a seat that exited 0 with a stub report and uncommitted work |

**Exposure:**

| Guide | Moment |
|---|---|
| `references/exposure.md` | exposing anything — method canon, manifest rows, progressive disclosure (mandatory read, §0) |
| `references/exposure-choice.md` | picking WHICH harness primitive exposes a part — audience × trigger, skill-vs-sub-agent |

**Capabilities (each self-documents; tools via `-h`):**

| Capability | What it does |
|---|---|
| `skills/create-cli.md` | build or UX-review a composable agent-facing CLI — the D9 toolsmith means (also an independently installed skill) |
| `capabilities/component-lint/component-lint.md` | deterministic lint over a component folder |
| `capabilities/capability-cards/tool/capability_cards.py -h` | inspect existing exposed tools while assigning seat instruments (§ `plan`) |
