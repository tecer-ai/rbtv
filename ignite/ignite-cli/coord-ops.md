---
id: coord-ops
description: "Work as a seat inside a running team — check in, read the bus, send a typed message, declare outputs, check out, file a system issue, and lint what you authored. Reach for it whenever you are SEATED and the subject is the team rather than the daemon."
inputs: where you are in a sitting — arriving, mid-work with something to say or hand over, hitting a defect that is not yours to fix, or about to hand authored floor content to the next reader
outcome: the seat's obligation is discharged through the kit that owns the run record, instead of a hand-edited log the coordinator will not read
outputs: a bus reading, a sent message, a checkin/checkout record, a filed system issue, or a lint verdict — returned to the caller, never routed or saved by this capability
---

<capability>

# coord-ops — which coordination tool, and when

Law: `spec-component-map.md` §7.2. This file answers only **"which tool"**. Every tool below
documents its own flags — ask it (`<tool> -h`), never guess, and never expect this file to
restate a flag surface. `coordinate -h` in particular IS the protocol's command surface; no
second copy of it exists in prose.

This is the bundle a caged worker gets — and only when its seat's `exposes: path:` block
already names the underlying tool (§7.4).

## Do you need this at all?

- **You need a goal, a worktree, or a run** → `goal-ops`.
- **You need to see fleet state** → `observe`.
- **You hit a defect in your own work** → fix it. `file-issue` is for a defect on the ignite
  or meta surface that is NOT yours to fix.

## The cheapest rung that works — stop at the first row that holds

| You need | Reach for |
|---|---|
| To arrive, read the bus, send a typed message, declare outputs, or check out | `coordinate <verb>` — then `coordinate -h` for the verb surface |
| To record a defect, gap or change notice on the ignite/meta surface — file it, do not fix it | `file-issue` |
| To check authored floor content before the next reader inherits it | `floor-lint` |

**The skipped rung is `coordinate -h`.** Guessing a verb, then hand-writing into the run log
when the guess fails, is the recurring damage — the log is the coordinator's record, and a
hand edit is invisible to it.

**The wrong rung is silence.** A seat that hits a blocker and simply stops leaves the run
holding nothing; check out with the ending that is true.

## Deliberately not in this bundle

| Tool | Why not |
|---|---|
| `save-coord` | owner-console (§7.1) — an owner gate over the run record, not an agent act |

A skill is discovery, not a grant: a caged seat still runs only what its `exposed-clis:`
block names, and this bundle is granted to a caged worker only under that condition.
