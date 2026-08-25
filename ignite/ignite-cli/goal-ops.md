---
id: goal-ops
description: "Work a goal end to end — ask for one, walk the goals tree, materialize its seats, get an isolated worktree, and run it attached. Reach for it whenever a GOAL or its seat lane is the subject. The planning pipeline's own internals are deliberately absent."
inputs: where you are in a goal's life — no goal yet, a goal that needs seats, a seat that needs an isolated tree, or a goal ready to run
outcome: the next act in the goal's life happens through the one tool that owns it, instead of hand-building a folder the daemon will not recognize
outputs: a goal-creation request, a goals-tree reading or edit, a materialized seat lane, a worktree, or an attached run's output — returned to the caller, never routed or saved by this capability
---

<capability>

# goal-ops — which goal tool, and when

Law: `spec-component-map.md` §7.2. This file answers only **"which tool"**. Every tool below
documents its own flags — ask it (`<tool> -h`), never guess, and never expect this file to
restate a flag surface.

A goal has a life: requested → registered in the tree → seats materialized → run. Each stage
has exactly one door, and the doors are not interchangeable.

## Do you need this at all?

- **You are seated INSIDE a goal already** and need to talk to the team or check out →
  `coord-ops`, not this file.
- **You want to read what a running goal is doing** → `observe`.
- **You want to change WHO staffs a seat** — its harness, model, effort → `staffing`.

## The cheapest rung that works — stop at the first row that holds

| You need | Reach for |
|---|---|
| To ask for a goal that does not exist yet — the request, not the goal | `rbtv-goal-request` |
| To read, list, or act on goals that DO exist — the goals tree | `rbtv goal <verb>` |
| To build (or rebuild) a goal's seat lane from its planning source | `materialize-seats` — `scaffold-seats` is the same tool under its other name |
| An isolated git worktree for a seat, and the flow that lands it back | `worktree-flow` |
| To run a goal ATTACHED to your own terminal, on the same engine the daemon uses | `rbtv run <goal-folder>` |

**The skipped rung is the first one.** Hand-creating a goal folder because
`rbtv-goal-request` felt like ceremony is the recurring waste — an unregistered folder is
invisible to the daemon and to every tool above.

**The re-run that is safe.** `materialize-seats` is the regenerator of the derived
`planning/current/seat-lane/` tree. Edit the SOURCE and re-materialize; an edit inside the
derived tree is silently overwritten on the next pass.

## Deliberately not in this bundle

| Tool | Why not |
|---|---|
| The planning pipeline's internals — the planning door, its lock, the path-A/path-B minters, the queue-request and failure recorders | Not a caller surface: the pipeline invokes them for itself. Reach for `materialize-seats` and `rbtv goal`, which are the doors that own them |

A skill is discovery, not a grant: a caged seat still runs only what its `exposed-clis:`
block names.
