---
description: Read before adding or changing an operator-facing surface - the goals tree, bindings, the daemon and ticker operator verbs, the master profile, the goal-creation request door and the attached rbtv run.
---

# operator

The operator surfaces the CLI delegates to. Law is
`1-projects/build-ignite/redesign/specs/spec-component-map.md` §1 under [D22],
[T4-R11], [C-15].

Every part here is a thing an agent or the owner ASKS FOR by name. The front door
that routes to them is `ignite-cli/`; the machinery they act on lives in
`runtime/`, `supervisor/`, `state-store/` and `planning/`. This component owns
neither the router skills (§7, `ignite-cli/`) nor the daemon loop.

## What lives here

| Part | Folder / file | What it is |
|---|---|---|
| goals tree | `goals-tree/` | `rbtv goal` - the goal folder tree, its scaffold and its refusals (no capability card today; `tool/README.md` is its doc) |
| bindings | `bindings/` | `rbtv-bindings` - the per-seat harness/model/effort casting sheet author |
| daemon operator | `daemon-operator/` | `rbtv ignite daemon` - the owner-console daemon verb |
| ticker settings | `ticker-settings/` | `rbtv ignite ticker` - cadence and ticker settings |
| master profile | `master-profile/` | `rbtv-master-profile` - which harness+model+effort the channel master's next sitting runs on |
| goal-creation request | `goal-creation-request/` | `rbtv-goal-request` - the request door a seat uses to ask for a goal |
| attached execution | `attached-execution/`, `attached-execution.js` | `rbtv run` - the engine attached to the calling terminal instead of the daemon |

`daemon-watchdog/` is NOT here: it moved to `observation/` per §2, because it
observes and alarms rather than serving an operator verb.

## Where its parts came from

`capabilities/` (all of it except `daemon-watchdog/`) and `engine/attached-execution.js`,
plus the three engine probes that travel with the attached lane
(`probes/probe-attached-status.js`, `probe-cross-lane-resume.js`,
`probe-foreground-carrier.js`) - moved with history by impl-structure-moves-js per
`spec-component-map` §2.
