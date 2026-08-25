---
description: Read BEFORE editing any ignite source — the entry point for agents and humans changing this module's code. Links only; every body lives in the component it belongs to.
---

# working-on-ignite

You are about to change ignite **source**. This file is a routing table, not a manual: it
carries **no bodies** (`PRIN-11`). Each row names the one place that answers its question, and
that place is where an edit to the answer goes.

Working *inside a goal* rather than on this code? → [`working-in-a-goal.md`](working-in-a-goal.md).

## Before the first edit

| Do this | Where |
|---|---|
| Read the build memory for every component you will touch, then file to it when you close | [`work-on-ignite/`](work-on-ignite/component.md) · procedure: [`work-on-ignite/references/work-on-ignite.md`](work-on-ignite/references/work-on-ignite.md) |
| Find which component owns what you are about to change | [`module.md`](module.md) — the module entry point and its component table |
| Check whether the tree you are editing is **derived** (regenerated, so an edit there is lost) | `spec-component-map.md` §4 "Derived-tree convention" · the live refusal is `refuse_if_derived` in [`coord/`](coord/component.md) |

Law for this module's layout: `1-projects/build-ignite/redesign/specs/spec-component-map.md`
(§1 the component map, §2 what moved where, §3 the 2000-line size budget, §4 source vs derived,
§5 these two docs, §7 the CLI consolidation).

## The components

One row per conforming component. The `component.md` is the body; `exposure.csv` beside it is
what the installer reads.

| Component | Read |
|---|---|
| `chat/` — the Slack bridge, bus ferry, ask and approval threads | [`chat/component.md`](chat/component.md) |
| `coord/` — the coordination kit and the `coordinate` CLI | [`coord/component.md`](coord/component.md) |
| `deploy/` — systemd units, the probe-suite runner, the PATH-link tool | [`deploy/component.md`](deploy/component.md) |
| `envelope/` — the plan-time envelope compiler, the cage/fence, admission | [`envelope/component.md`](envelope/component.md) |
| `ignite-cli/` — the `rbtv ignite` front door and its router skills | [`ignite-cli/component.md`](ignite-cli/component.md) |
| `observation/` — the one alarm emitter, the frozen invariant, the watchdog | [`observation/component.md`](observation/component.md) |
| `operator/` — the operator surfaces the CLI delegates to | [`operator/component.md`](operator/component.md) |
| `planning/` — the planning door, the lock, `materialize-seats.py` | [`planning/component.md`](planning/component.md) |
| `runtime/` — the daemon process host: service, ticker driver, gateway, jobs | [`runtime/component.md`](runtime/component.md) |
| `state-store/` — the one ending store, its predicates, the state layout and this module's vocabulary | [`state-store/component.md`](state-store/component.md) |
| `supervisor/` — the one liveness surface, spawn, recovery, launch specs | [`supervisor/component.md`](supervisor/component.md) |
| `teambuild/` — the staffing-discovery browse | [`teambuild/component.md`](teambuild/component.md) |
| `work-on-ignite/` — the build memory | [`work-on-ignite/component.md`](work-on-ignite/component.md) |

## Reaching the code from a command

The `rbtv ignite` front door owns routing, not behaviour. Which command belongs to which
bundle, and which role loads which bundle, is `spec-component-map.md` §7; the router files
live with the front door.

→ [`ignite-cli/component.md`](ignite-cli/component.md) · [`ignite-cli/README.md`](ignite-cli/README.md)

## Deploying and verifying a change

| Question | Read |
|---|---|
| What does a restart actually pick up — the commit or my working tree? | [`deploy/component.md`](deploy/component.md) § Deploy model (pinned vs live tree) |
| How is ignite installed, and what travels in git? | [`deploy/component.md`](deploy/component.md) § Installation model |
| How do I run the probes, and why never by hand? | [`deploy/component.md`](deploy/component.md) § Probes · runner `deploy/probe-suite.js` |
| Where does state live on disk? | [`state-store/component.md`](state-store/component.md) § State layout |
| Which word means what in a spec, a column or a commit? | [`state-store/component.md`](state-store/component.md) § Terminology |
| What external tools does this module need? | [`dependencies.txt`](dependencies.txt) — updated in the SAME change that adds or drops a dependency |

## The docs-in-sync rule

A component change is incomplete without its `component.md` / `exposure.csv` / README update
**in the same commit set**, and without every path the change moved still resolving from this
doc and its sibling [T4-R14]. A stale home here fails the change that made it stale.
