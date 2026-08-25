---
id: staffing
description: "Decide and record WHO works — build a team, write a seat's casting sheet, re-cast the channel master, and find out which seat you yourself are. Reach for it whenever the subject is a seat's identity, harness, model or effort rather than the work itself."
inputs: the staffing question in front of you — a team that needs building, a seat whose harness/model/effort must change, or an identity you must establish before acting
outcome: the staffing act lands on the casting sheet the launch doors actually read, instead of a per-dispatch override that no door honors
outputs: a built team, a written or read binding, a re-cast master, or this session's own seat identity — returned to the caller, never routed or saved by this capability
---

<capability>

# staffing — which staffing tool, and when

Law: `spec-component-map.md` §7.2. This file answers only **"which tool"**. Every tool below
documents its own flags — ask it (`<tool> -h`), never guess, and never expect this file to
restate a flag surface.

Staffing is written to a **casting sheet** — a per-seat record of `harness`, `model` and
`effort`. Every launch door resolves the cast from that sheet at launch time. Profile NAMES
are abolished: the unit is a harness plus a model, never a name.

## Do you need this at all?

- **The seats already exist and you want the goal to RUN** → `goal-ops`.
- **You want to know what a seat is doing right now** → `observe`.
- **You are a seat and need to talk to your team** → `coord-ops`.

## The cheapest rung that works — stop at the first row that holds

| You need | Reach for |
|---|---|
| To know which seat THIS session is — before you write anything as that seat | `rbtv-seat-identity` |
| To read or write one seat's casting sheet — its harness, model, effort | `rbtv-bindings` |
| To re-cast the CHANNEL MASTER itself (its own sheet, its own validator) | `rbtv-master-profile` |
| To build a whole team — the seats, their roles, their staffing, together | `rbtv teambuild` |

**The skipped rung is the first one.** Acting as a seat you never confirmed you are is how a
message lands under the wrong name; the identity check costs one command.

**The over-reached rung is the last.** `rbtv teambuild` builds a TEAM. Changing one seat's
model is `rbtv-bindings`, and re-materializing the seat afterwards — not a rebuild of the
whole team.

## Deliberately not in this bundle

| Tool | Why not |
|---|---|
| `cast` | a core-module tool (the model/harness routing verdict), outside this plan's scope (§7.2). It is reachable on its own; this bundle just does not route to it |

A skill is discovery, not a grant: a caged seat still runs only what its `exposed-clis:`
block names.
