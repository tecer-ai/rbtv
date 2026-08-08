# daemon-watchdog — the ignite LIVENESS surface (CMP-28)

A tiny, agentless, independent watchdog: a systemd user timer firing one deterministic
pass — `tool/rbtv-ignite-watchdog` — that PROBES the deployment, RESTARTS through the
services' own units what is down, and NOTIFIES the owner's chat DM only when it acted or
when a restart did not restore the subject. Silence means healthy.

The component's contract, its three invariants and its differentiation from every
neighbour live on the registry record `CMP-28-daemon-watchdog` in the merge-refactor
campaign's `system-definition/architecture/`. Not restated here (`PRIN-11`).

## What it is NOT, in one line each

| Not | Because |
|-----|---------|
| the goal-watcher job (CMP-21) | that is an ignite JOB fired by the ignite daemon, so it can watch everything except ignite being down — the hole this fills |
| the scheduled probe suite | that grades CORRECTNESS on an hourly sweep; this grades LIVENESS every 60s and restores it |
| `Restart=on-failure` | unit-level restart policy catches a crashing process, not a hung one, a dead timer, or a service that exited cleanly into wrongness |
| the daemon-operator | that is the OPERATOR surface a human or a script drives by hand. This CALLS it — the restart-and-verify implementation is not written twice |

## The probe table

Four rows. Each is `probe → restart action → notify condition`, and the notify condition is
identical on every row: **acted, or acted and it did not come back.** Nothing notifies on green.

| Row | Probe | Restart action |
|-----|-------|----------------|
| `daemon` | `POST /` `{intent:"inspect", payload:{target:"daemon"}}` at the gateway with a Bearer token. Connect failure / timeout / non-200 = **down**. HTTP 401 = **alarm**, never down: the daemon is up and answering, the token is not accepted — restarting cannot fix that and would loop | `RBTV_IGNITE_UNIT=<daemon unit> rbtv-ignite-daemon restart` |
| `bridge` | `is-active`, AND the newest Socket-Mode lifecycle line in the last 200 journal lines. `active` only proves the Node process exists — Slack's socket can die under it. The bridge's own `reconnect()` is the first line of self-heal, so what this catches is that **backoff loop being stuck**: newest marker is a reconnect failure with no later hello. Neither marker present is NOT a fault; a healthy bridge is quiet | `RBTV_IGNITE_UNIT=<bridge unit> rbtv-ignite-daemon restart` |
| `probe-suite` | `<workspace>/.rbtv/runtime/probe-suite/latest.json`: `now - fired_at > stale_after_seconds`. **Liveness only** — `verdict`/`passed`/`failed` sit in that same artifact and are deliberately never read here | bare `systemctl --user restart <timer>` — see § The one row that does not use the operator |
| `goal-watcher` | the job's own periodic **queue row**, via `inspect queue`: overdue by more than the row's OWN `interval_seconds`. No row at all = **alarm** (it is not scheduled; no restart creates a queue row). Queue unreadable = **skip**, because that means the daemon is down and the `daemon` row already owns both the cause and the only lever | `RBTV_IGNITE_UNIT=<daemon unit> rbtv-ignite-daemon restart` — a FULL daemon restart, and the DM says so in those words |

**Two of these deserve their reasoning stated, because both were nearly built wrong.**

1. **The goal-watcher job has NO systemd unit of its own.** It is a recurring entry in the
   daemon's job catalogue, fired by the ticker into a *transient* `rbtv-worker-*` unit each
   time. So there is no `systemctl restart <the goal watcher>` and there never will be: the
   only lever is a full daemon restart. The notify text says "restarted the WHOLE daemon …
   this job has no unit of its own" so the owner is never misled about blast radius.
2. **Its staleness threshold is read, not written.** The overdue bar is the queue row's own
   `interval_seconds`, fetched in the same pass. A cadence literal here would be a home in
   waiting — it drifts silently the moment anyone retunes the job, and nothing consumes it
   to notice.

## The one row that does not use the operator, and why it is measured rather than assumed

`rbtv-ignite-daemon`'s act verbs verify SURVIVAL: they re-read `MainPID` after a settle
window and fail loud when it moved or is zero. **A `.timer` unit has no `MainPID` — it is
always 0 — so that check can never hold for the probe-suite row.** Measured on a throwaway
timer, 2026-08-08: the wrapper exits `1` with *"did not survive 2s — MainPID 0 -> 0"* while
a bare `systemctl --user restart` exits `0` and leaves the timer active. So that one row
calls `systemctl` directly. Everything Service-typed still goes through the operator; this
is a typed exception, not a second implementation.

## Silence, and how it survives a subject that cannot be restored

Invariant 3 says notify on action or failure-to-restore, never on a green pass. At a 60s
cadence a permanently-unrestorable subject would honour that rule and still DM the owner
~1440 times a day — the invariant violated by volume rather than by rule. So the pass keeps
a one-field state file (`<workspace>/.rbtv/runtime/watchdog/state.json`) holding the
previous pass's alert fingerprint, and re-notifies only when the fingerprint CHANGES. An
all-green pass clears it, so the next occurrence of the same fault does notify.

## Verbs and exit codes

`rbtv-ignite-watchdog [--dry-run]` — one pass, then exit. `--dry-run` probes and reports
what it WOULD restart without restarting anything.

| Exit | Means |
|------|-------|
| `0` | the pass completed — all green, or it acted and every subject came back |
| `1` | a subject is still down after its restart action (a human is needed), or the pass could not run at all (no token, unreadable config, notify failed) |
| `2` | usage error |

Unlike `rbtv-ignite-daemon`'s `unit` verb, this exit code is NOT "did the read succeed" —
a watchdog pass has no read to report, only an outcome. And unlike
`rbtv-probe-suite.service`, exit `1` is deliberately **not** whitelisted in the unit, so a
subject that will not come back shows as a failed unit to anyone reading
`systemctl --user status rbtv-watchdog`.

## Environment

Every per-instance value is resolved at runtime; nothing is baked into the code.

| Variable | Default |
|----------|---------|
| `RBTV_WATCHDOG_WORKSPACE` | CWD — the workspace root that carries `.rbtv/` |
| `RBTV_WATCHDOG_GATEWAY` | `http://127.0.0.1:7431/` |
| `IGNITE_WATCHDOG_TOKEN` | falls back to `IGNITE_SENDER_TOKEN` |
| `RBTV_WATCHDOG_DAEMON_UNIT` · `_BRIDGE_UNIT` · `_PROBE_TIMER` | `rbtv-ignite.service` · `rbtv-chat-bridge.service` · `rbtv-probe-suite.timer` |
| `RBTV_WATCHDOG_WATCH_JOB` | `selfheal-watch` |
| `RBTV_WATCHDOG_TARGETS` | all four rows. **The test-override hook** — mirrors `RBTV_IGNITE_UNIT`: a probe scopes the pass to one row and points that row's unit variable at a throwaway unit, instead of editing the real probe table |
| `RBTV_WATCHDOG_OPERATOR` | the sibling `daemon-operator/tool/rbtv-ignite-daemon`, else `rbtv-ignite-daemon` on PATH |
| `RBTV_WATCHDOG_STATE` | `<workspace>/.rbtv/runtime/watchdog/state.json` |
| `RBTV_WATCHDOG_NOTIFY_FILE` | unset. **Test double** — when set, notifications are appended there as JSON lines and Slack is never called |
| `RBTV_WATCHDOG_NOTIFY_PREFIX` | empty — prepended to every message; how a TEST DM is marked as one |
| `SLACK_BOT_TOKEN`, `IGNITE_CHAT_BRIDGE_CONFIG` | the notify credential, and the bridge's own config — read ONLY to resolve WHO the owner is (explicit `bus_ferry_dm_user`, else the first allowlist entry), so the two components can never disagree about it |

**The notify client is the watchdog's own two Slack calls** (`conversations.open`, then
`chat.postMessage`), not the bridge's. It has to be: this must reach the owner when the
chat bridge is the thing that is down, so it can depend on neither the bridge process nor
its bus-poll loop. The accepted consequence is stated plainly — if the bridge is down at
the instant of the alert, Slack itself may be unreachable and that pass's DM fails; the
NEXT pass 60s later re-attempts, so the message is delayed by one cadence, never lost.

## Enabling this thing — the gate, in order

The units ship **installed and DISABLED**. Enabling is a deliberate act, and it has a
prerequisite that fails silently if skipped.

1. **Mint the watchdog's gateway sender** — the sanctioned way, per the deployment
   runbook's § Sender registry: generate a token on this box, hash it with
   `printf %s "$T" | sha256sum` (no trailing newline), append a row to the sender registry
   with `kind: agent`, and put the plaintext in the machine's gitignored env surface as
   `IGNITE_WATCHDOG_TOKEN`. Never a CLI flag — argv leaks into process lists.
2. **Restart the daemon.** The sender registry is read ONCE at startup; there is no live
   reload. Until this happens the new token is not accepted and every pass reports
   `alarm: 401 AUTH_REFUSED`.
3. Substitute and install both units from `units/`, then
   `systemctl --user daemon-reload && systemctl --user enable --now rbtv-watchdog.timer`.
4. `systemctl --user list-timers rbtv-watchdog.timer` — confirm `NEXT` is populated.

⚠ **Steps 1–2 are the gate, not step 3.** Enabling the timer before the sender is loaded
produces a watchdog that alarms on its own credentials once and then goes quiet under
repeat-suppression — which reads exactly like a healthy system.

## Proving it

`probes/probe-watchdog-staged-failure.py`, run through the enumerator
(`node deploy/probe-suite.js --only probe-watchdog-staged-failure`), stages a real failure
end to end: down → detected → restarted → notified → recovered, then a clean pass proven
SILENT. It creates and removes its own throwaway unit and routes notify to a test double;
**it never starts, stops or restarts the three live units, and never messages the owner** —
the same non-interference guarantee `rbtv-ignite-daemon selftest` established for this
capability family. A real-DM confirmation is a one-time manual step
(`RBTV_WATCHDOG_NOTIFY_PREFIX` marks it), never part of the repeatable check.

## Retirement

Nothing retires this yet. It is not a stand-in: unlike `daemon-operator`, it has no
successor in the `rbtv` CLI and no home waiting for it in the `CMP-5` component layer — a
watchdog is a scheduled act, not a verb a human types. If the `rbtv` CLI ever grows a
`rbtv ignite watchdog run` verb it should **exec this script** the way
`rbtv ignite daemon` execs the operator, which would make this folder a dependency rather
than a predecessor. Retire it only when nothing execs it and no timer fires it.
