---
description: Read at the moment a user asks to create or change any scaffolding — a rule, prompt, skill, task, seat, capability, workflow, agent, or any part of rbtv or the mirror. The one router from that request to the right workflow or guide.
tags: [planning]
---

# build — the scaffolding router

**You are reading this because a user wants scaffolding created or changed.** This page is the ONE
router surface for the meta/planning component (owner-ruled 2026-08-21): it replaced the standalone
`planning` and `forge` skills, and it holds the kind router that used to
live in forge's console entry. The `plan` skill (named `plan-in-session-run` until 2026-08-24)
stands alone again — owner-directed 2026-08-24. Stop at the first section that answers you; everything deeper is
reached through the links here.

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

## 1 — Workflow or guide? The route rule

A request to CREATE or BUILD something always routes to a WORKFLOW — you never author the part
yourself in the console session. The GUIDES (§3) are reached when an agent must understand or
author correctly mid-task — a kind's anatomy, a naming law, a style rule — without launching
anything.

| The request is… | Route |
|---|---|
| ONE small part of a component that already EXISTS — a reference, prompt, task, seat, capability, exposure entry, or sub-agent definition | **forge** — `workflows/forge/console-entry.md` (setup + run handover; the per-kind authoring table is §2 below) |
| a NEW component, a NEW workflow, a DAG change larger than one seat row, or pieces spanning components | **plan-console** — `workflows/plan-console/console-entry.md` |
| already-decided work to structure as a console-orchestrated seat plan (no goal/daemon run) | **plan** — `references/plan.md` |

Three further conditions escalate a forge-shaped request to plan-console whatever the kind: the pieces
span more than one component in a way one build pass cannot carry; a new workflow or DAG is needed;
the request is a symptom of an unstated bigger goal. `forg-intake` runs that test itself — you
route, it rules.

---

## 2 — The KIND ROUTER (authoring table per piece kind)

Read the request and stop at the FIRST row that holds. The row names the guide the part is authored
against, the shape of its target path, the registration act that makes it real, and the condition
that sends the request to plan-console instead of forge.

| Piece kind | Authoring guide | Target-path shape | Registration act | Escalates when |
|---|---|---|---|---|
| **a NEW COMPONENT** | — | — | — | **ALWAYS — forge never mints a component. Route the request to the plan-console workflow.** |
| reference | `references/kind-reference.md` | `<component-root>/references/<name>.md` | none by default — a reference is reached by an explicit prose read; an `exposure.csv` row appears only on a real exposure decision | its subject belongs to a component that does not exist |
| prompt | `references/file-prompt.md` plus the kind guide of each section it carries | `<component-root>/prompts/<id>.md` | a `seats.csv` row pairing it with a task; an `exposure.csv` row only where an agent must reach it on its own | it needs a manifest node in a workflow that does not exist |
| task | `references/file-task.md` | `<component-root>/tasks/<id>.md` | a `seats.csv` row pairing it with a prompt | the same |
| seat | `references/workflow-anatomy.md` + `references/workflow-authoring-checklist.md` | a row in `<component-root>/seats.csv`, plus one row in the workflow manifest when the seat holds a node | the `seats.csv` row, and the manifest row with its `after` edges | the seat needs a NEW workflow, or a DAG change larger than one row |
| capability | `references/kind-capability.md` | `<component-root>/<name>.md` for a single capability carrying no tool, otherwise `<component-root>/capabilities/<name>/<name>.md` | registered AND exposed in the same act — the `exposure.csv` row per `references/exposure.md` | its owning component does not exist |
| capability whose core is a CLI | the `create-cli` capability, followed exactly | `<component-root>/capabilities/<name>/tool/` — a CLI is a capability's tool, landed inside its owning component | the first-party `path` row in the owning component's `exposure.csv`, written in the same act — create-cli's *Expose the Finished Tool* close-out | the owning component cannot be resolved |
| exposure entry | `references/exposure.md` + `references/exposure-choice.md` | a row in `<component-root>/exposure.csv` | the row IS the act | no method in the closed canon fits the part |
| sub-agent definition | `references/file-prompt.md` + `references/file-task.md` | `<component-root>/prompts/<id>.md` and `<component-root>/tasks/<id>.md` | a `seats.csv` row holding no manifest node, sanctioned by a `method=sub-agent` row on its executor prompt | it must run as a workflow node instead |

`<component-root>` is resolved by the write-destination rule, never guessed: a `.rbtv/mirror/`
component's parts go in that mirror folder, an rbtv-repo component's parts go in that repo's module
folder, and NEVER into a `.claude/` installed copy. A destination that rule cannot resolve is
REFUSED back to the user with the ambiguity named.

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
| `references/workflow-anatomy.md` | structuring a workflow DAG, authoring its manifest, binding its taskforce |
| `references/workflow-authoring-checklist.md` | authoring or amending seat declarations — the six walls (also a standalone skill: seat prompts materialize it) |
| `references/seat-id-naming.md` | naming a workflow's seat rows — the workflow-code prefix law |
| `references/plan.md` | structuring already-decided work as a console-run seat plan |
| `references/headless-seat-cannot-wait.md` | a seat is about to background a check or end its turn expecting to be woken — and an orchestrator meeting a seat that exited 0 with a stub report and uncommitted work |

**Exposure:**

| Guide | Moment |
|---|---|
| `references/exposure.md` | exposing anything — method canon, manifest rows, progressive disclosure (mandatory read, §0) |
| `references/exposure-choice.md` | picking WHICH harness primitive exposes a part — audience × trigger, skill-vs-sub-agent |

**Capabilities (each self-documents; tools via `-h`):**

| Capability | What it does |
|---|---|
| `capabilities/create-cli/create-cli.md` | build or UX-review a composable agent-facing CLI — the D9 toolsmith means (also a standalone skill: seat prompts materialize it) |
| `capabilities/component-lint/component-lint.md` | deterministic lint over a component folder |
| `capabilities/capability-cards/capability-cards.md` | render one uniform card per exposed mirror resource |
| `capabilities/delta-anchors/delta-anchors.md` | verify/apply an authoring seat's delta file — anchors verbatim, all-or-nothing |
