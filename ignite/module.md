---
description: Use when operating the ignite runtime — the daemon and its job queue, the goals tree, or a coordinated multi-agent team run. The module's CLIs self-explain; enter here to find which one you need.
---

# ignite

The runtime layer of rbtv: agents doing coordinated work over time. Two faces of one
substrate — the **ignite daemon** (a Node.js service that makes a workspace's job queue
launch due jobs on a runtime host) and the **team-kit** (mechanics for running a parallel
multi-agent team in tmux).

This file is the module entry point (`module entry point` — the skill-format front door the
installer realizes as this module's discovery skill). It lists what is here in one line each
and routes into the CLI; **it carries no bodies.** Each CLI self-explains through `-h`, which
is where the detail lives — progressive disclosure (`PRIN-3`), one rung at a time.

## Command-line capabilities

| Capability | One line | Reach it |
|---|---|---|
| `daemon-operator` | Local systemd USER unit ops that work precisely when the daemon is DOWN — `start`/`restart`/`stop`/`kill`/`unit`, on any of the three FIXED services via `--service ignite\|chat-bridge\|probe-suite`. Health is a FIELD, never the exit status. | `rbtv ignite daemon <verb>` · `-h` |
| `goals-tree` | The goals-tree machinery — `scaffold`/`reindex`/`lint`/`materialize` over a goal folder. | `rbtv goal <verb>` · `-h` |
| `daemon-watchdog` | One bounded liveness pass over the whole deployment — probe, restart through the units, DM the owner only on action or failure to restore. Normally nobody runs it: a systemd timer does, every 60s. | `observation/daemon-watchdog/tool/rbtv-ignite-watchdog --dry-run` · `-h` |
| `master-profile` | The channel master choosing its OWN harness and model — the `master_profile` field of the chat-bridge config, validated against the LIVE `profiles:` set. Same three verbs; the apply restarts `rbtv-chat-bridge`, which ends the requesting sitting — so `request --chat-thread <channel>:<ts>` makes it SELF-REPORT the outcome first: one `to: owner` bus row carrying the bracketed `[chat-thread:]` token, appended before the restart and carried into the thread by the chat bridge's bus ferry, which POSTS it verbatim on the `[deliver: post]` disposition rather than minting a sitting to paraphrase it. No `--effort`: effort is measurably not on the master spawn wire. | `operator/master-profile/tool/rbtv-master-profile <verb>` · `-h` |
| `bindings` | The CASTING SHEET a workflow is run through — which harness, model and effort each seat gets. `catalog` (what this box can spawn, effort NUMBERED, and the validator `set` uses), `inspect` (seats, definitions, hints, what is still uncast), `scaffold` (create-only), `set`. One file per workflow at `.rbtv/config/modules/{module}/{component}/bindings/{code}.json`; direct writes, no daemon, no restart. | `operator/bindings/tool/rbtv-bindings <verb>` · `-h` |
| gateway client | Enqueue and remove scheduled/periodic jobs, inspect runtime state. | `rbtv ignite <command>` · `-h` |
| team-kit | Run a coordinated parallel multi-agent team in tmux: checkin, typed append-only messaging, bounded reads, staged launches, close/renew ceremonies. | `coordinate -h` |
| ending store | One seat-ending / goal-word / open-ask store plus derived wait and launchability predicates. Hosted in `heart.db`; APIs in `state-store/`. Engine readers (`seeding.js`, `reconcile.js`, `lane-watch.js`) consume those predicates — no verdict enum. | `ignite/state-store/` · `cli.js --help` via `--db` `--op` |
| supervisor | The ONE liveness surface: a persisted registry of supervised sittings (seat, pid, `/proc` start-time, launch token, supervised/unsupervised), the `kill(pid,0)`+start-time probe every "is it alive" question is answered by, and the boot re-adopt pass that runs BEFORE any ending stamp — so an empty registry after a restart can never mass-stamp live seats `failed`. Pane, carrier and tick silence are not liveness. Not a CLI (kit door: `cli.js --op`). Also the recovery half [spec-recovery]: the ONE `last_progress_at` work-product fact and the per-kind signal collectors that are its only writers, the no-progress kill clock with its closed list of three pause conditions (verified open ask, provider backoff, disarmed lane until its named event), the strict loader for `{workspace}/.rbtv/config/ignite/recovery.json` that refuses to arm any clock on an invalid or missing file and never falls back to in-code numbers, and the operational checkpoint contract (progress note, side-effect journal, relaunch prompt). | `ignite/supervisor/` |
| observation | The ONE schema-enforced alarm emitter [T4-R10]: four required fields (condition in plain words, concrete subject, evidence pointer, what-would-clear-it with `unknown` allowed) refused by THROW at the emitting call site, and a PERSISTED signature registry that dedupes one emission per open condition across a daemon restart and publishes the open conditions the system digest re-surfaces. Carries the frozen-goal SCHEDULER INVARIANT [T1-R15] — running + no live seat + no eligible launch + no open ask + not paused, held the configured window — which reads liveness from the supervisor registry only and never fires on a provider-backoff or reroute-pending lane [C-5]. Alarms are one-way and never wake anything. Not a CLI. | `ignite/observation/` |
| planning | Planning-door Path A mint + lock + supervised wrapper (goal-wide trigger, `.materialize.lock`, five failure classes). Not a CLI. | `planning/` |

## Drilling

```
rbtv ignite                  this module's components, rules, and action verbs
rbtv ignite <component>      that component's entry point body + its invocable entry points
```

The daemon's conventions, install model, and state layout live in `ignite/CLAUDE.md`; the
coordination kit's protocol in `ignite/coord/protocol.md`. Neither is restated here (`PRIN-11`).

## Components

| Folder | One line |
|---|---|
| `envelope/` | Plan-time per-goal bind-list compiler + versioned template / deny-list / daemon-owned records |
| `planning/` | Planning-door Path A mint + lock + supervised wrapper (goal-wide trigger, `.materialize.lock`) |
| `observation/` | The one schema-enforced alarm emitter + persisted signature registry + the frozen-goal scheduler invariant |
| `runtime/` | The daemon process host: HTTP service, engine composition root, tick driver, gateway seam, lease, internal API and the fire-tool job scripts |
| `chat/` | The Slack bridge: reply leg, ask and approval threads, durable outbox, bus ferry, system digest and the chat session config |
| `operator/` | The operator surfaces the CLI delegates to: goals tree, bindings, daemon and ticker verbs, master profile, goal-creation request, attached `rbtv run` |
| `ignite-cli/` | The `rbtv ignite` front door — verb dispatch and the gateway client seam, no daemon behavior of its own |
| `coord/` | The coordination kit: the `coordinate` CLI and its split modules, addressing, declared outputs, tmux viewports, messages, the checkout write API, the injection ladder and the kit's shipped skills |
| `teambuild/` | The staffing-discovery browse (`rbtv teambuild`) over the component databases — binds nothing |
| `deploy/` | The systemd units, the probe-suite runner and its scheduled twin, and the PATH-link tool |
