# 20260831-c-reference-a-headless-seat-cann — reference: a headless seat cannot wait

kind: creation
component: meta-planning
date: 2026-08-31
commit: 91c2a160
deployed: no
pin: NONE
components: planning

## Motivation

Five sittings in the `redesign-continue-1` plan were lost to seats that backgrounded a check or armed a watcher and ended the turn expecting a wake that can never arrive.

Four were already recorded in that plan's `status.md` §8 traps (`1-projects/build-ignite/build/redesign-continue-1/`). The fifth, seat `note-approval-gate` at 2026-08-31 19:44Z, produced a report whose entire body was one sentence — "I'll pause here and wait for the Monitor notification about `coord.py selftest`'s outcome before proceeding to commit." — exited 0, and left +61 lines in `ignite/coord/messages.py` and +40 in `ignite/coord/coord_selftest.py` uncommitted in a shared tree.

The trap lived only in one plan folder's `status.md`, which nothing outside that plan reads, and in `ignite/coord/protocol.md` §parked-wait, which speaks about checkout dispositions rather than about a seat's own checks. No planning-side surface warned anyone: `ignite/planning/component.md` did not mention sittings, turns, or waiting at all, and neither did `meta/planning`'s guide set.

The root cause is NOT agent carelessness, and that is why a prohibition alone would have fixed nothing. Every one of those seats wanted a GATE, and the gate they reached for — `coord.py selftest` — was red-and-aborting at pristine HEAD for most of that plan's life (20-25 failures, count varying run to run, with at least three distinct early aborts). Running it out of band was a reasonable response to a broken gate. What was missing was a sanctioned alternative.

## Design

One reference, `meta/planning/references/headless-seat-cannot-wait.md`, on one subject: a headless seat's sitting is turn-bounded, so it MUST never end a turn expecting a wake.

A reference rather than a rule or a prompt section because it is applied at a nameable moment — a seat about to background a check, an orchestrator meeting a suspicious return — rather than always-on, which is `kind-reference.md`'s own test.

The load-bearing half is deliberately the ALTERNATIVE, not the prohibition: a scope-down ladder — the single arm covering the change, then the one module or suite section touched, then a cheaper check of the same property (lint, parse, targeted grep, a direct call of the changed function) — with an explicit instruction to report which check ran and what it did not cover. A gate that genuinely cannot be obtained is reported as an unmet gate with the reason named, and the seat finishes anyway. Rejected: writing it as a bare prohibition, which is what the plan's `status.md` bullet already was, and which had not stopped the fifth loss.

One exception is carved out and bounded: a seat MAY hand work over to another live agent (an orchestrator, a successor on an `after` edge, the owner), because a different live agent does the collecting. It may never wait for that work to come back, and the handoff must be complete at the moment the turn ends.

The last section is written for the ORCHESTRATOR rather than the seat, because the seat that hit the trap is gone by the time anyone can act: it names the three-part mechanical signature (exit 0 AND a report with no findings AND uncommitted changes on that seat's custody files) and prescribes resuming the seat's OWN session over launching a fresh one.

## How it works

The reference is reached by an explicit prose read from four surfaces, one per reader:

`meta/planning/references/build.md` §3 carries a row in its "Workflows and seats" guide table, naming the moment of reading — that is how every sibling guide in this component is reached, and how `forge` inherits it, since `workflows/forge/console-entry.md` §1 routes every forge run through `build.md` §1-§2 rather than carrying its own guide list.

`meta/planning/workflows/plan-console/workflow.md` and `workflows/d13-replan/workflow.md` each gained a paragraph binding their DRAFTER: `plan-drafter` authors the plan's execution seats under `planning/current/` and `repl-drafter` amends a failed milestone's seats, so those two are the surfaces where the rule must land in produced seat bodies. `plan-console`'s paragraph also binds `plan-verifier` to fail a seat body that instructs its occupant to wait. `forge` was deliberately NOT given its own link: it is a scaffolding-part builder, not a plan workflow, and it already reads `build.md`.

`ignite/planning/component.md` gained a paragraph stating the daemon-side mechanism in its own words plus the pointer, so an agent working the planning door learns what the seats it mints are subject to.

No `exposure.csv` row was written. `build.md` §2's kind router gives a reference none by default — a reference is reached by an explicit prose read, and a row appears only on a real exposure decision. `meta/planning/exposure.csv` therefore stays as it was; the two reference rows it does carry (`build`, `plan`, `workflow-authoring-checklist`) are skill-exposed entry surfaces, which this one is not.

## Consequences

Nothing was replaced or deleted; the additions are five files, +88 lines, in one commit (`91c2a160`) taken by explicit pathspec against a shared, dirty tree holding a PAUSED sibling goal's in-flight envelope work (`ignite/planning/path_b.py`, `plan_envelope.py`, `probes/probe-planning-path-b-materialize.py` were left untouched and uncommitted, as were `ignite/supervisor/spawn/spawn.js` and everything under `ignite/envelope/`).

The rule does not yet reach a CAGED seat at run time. `materialize-seats.py` generates each seat's `CLAUDE.md`/`AGENTS.md` guidance pair, including an "Always-on rules — binding for this whole sitting" block, and that generated text is what a caged seat can actually read — `meta/planning/references/headless-seat-cannot-wait.md` is not bound into a cage, so a caged occupant cannot open it. Landing the rule there would require editing `_SEAT_GUIDANCE_MD`/`_SEAT_RULES_BLOCK` in `ignite/planning/materialize-seats.py`, which regenerates every seat's guidance pair; that was surfaced and NOT done in this pass. Until it is, the rule reaches produced seats only through the drafter that authors their bodies.

`ignite/coord/protocol.md` §196-201 keeps its parked-wait rule, which is the checkout-disposition sibling of this subject (`--incomplete` versus `--renew` versus staying up to poll) and is not duplicated by the new reference.

## Verification

The daemon-lane applicability was established by direct source reading before the `ignite/planning` link was written, not assumed: `ignite/supervisor/launch.py` enqueues the daemon-lane job with `session_mode=headless` and states "no tmux pane"; `ignite/envelope/spawn-profiles.yaml` builds `["claude","-p",...]` with `prompt: stdin` for the claude family and `["opencode","run","--auto",...]` / codex `exec -` for the others; `ignite/supervisor/spawn/spawn.js#composeArgv` appends only `--append-system-prompt-file` and an effort rung, never an interactive or session-keeping flag; `ignite/supervisor/spawn/carrier.js` delivers the prompt as `StandardInput=file:` (bytes then EOF) and records that the former pty host was deleted; the nudge transport `ignite/coord/nudge.py` is `tmux send-keys` into a pane a headless sitting does not hold; and `launch.py`'s own daemon-lane boot prompt tells every seat "hold no pane, no wake can reach you". The one warm-session mechanism, `ignite/supervisor/spawn/live-sessions.js`, is gated to claude-only seats declaring `human-interactive: yes` and reached only through the chat bridge, so no reconcile/ticker work seat routes through it. Pending work is picked up by `reconcile.js` re-spawning a FRESH sitting on its 5-minute cadence, which is why an in-flight backgrounded check dies with the turn.

The recovery prescription is a measured outcome, not a proposal: the `note-approval-gate` seat was resumed in its own session, carried its surviving diff forward, re-measured its premise, and landed `861f7633` and `db907d76` with a clean tree on both its custody files (recorded in that plan's `seats.md` row 76).

Not deployed — this is repo content under `meta/` and `ignite/planning/component.md`, not runnable daemon code, and no deploy was run.

## ATTENTION

- A headless sitting that ends its turn waiting reports SUCCESS: exit 0, no error, no timeout. An orchestrator grading on exit codes marks it done and loses the work silently — grade on the three-part signature (exit 0 AND a findings-free report AND uncommitted changes on that seat's custody files) instead.
- The rule does NOT yet reach a caged seat at run time: `meta/planning/references/headless-seat-cannot-wait.md` is not bound into any cage. A seat learns it only if its author put it in the seat body. Do not assume a produced seat has read it.
- Do not "fix" this by re-fielding it as a prohibition. The five losses happened while a prohibition was already written in the plan's `status.md`; what was missing was the scope-down ladder and permission to report an unmet gate and finish.
- Recover a trapped seat by RESUMING its own session, never by launching a fresh one — a fresh seat re-derives from scratch and collides with the diff still sitting in the tree. Identify the session by its own `[cast:<id>]` title tag; a shared project store makes "the last session" the wrong session.
- exit 0 + stub report + uncommitted custody files is the signature; the exit code lies
