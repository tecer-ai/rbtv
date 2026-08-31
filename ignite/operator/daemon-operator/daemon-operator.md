# daemon-operator — the ignite OPERATOR surface (v1 stand-in)

A thin local wrapper over this machine's systemd **USER** unit ops for the ignite daemon:
`tool/rbtv-ignite-daemon start|restart|stop|kill|unit|selftest|deploy [--service NAME]`.

It never crosses the gateway, presents no `IGNITE_SENDER_TOKEN`, and works precisely when the
daemon is **down** — which is why it is not an `ignite` subcommand. The full contract, reasoning
and rejected alternatives live in `4-archives/executed/rbtv-sb-merge/rbtv-sb-merge-refactor-structure/ignite-operator-surface-design.md`
(merge-refactor campaign archive) and on the registry's `rbtv CLI` record § daemon verb family.
Not restated here (`PRIN-11`).

## The verbs

| Verb | Does | Wraps |
|------|------|-------|
| `start` | Starts the unit; a no-op **success** if already active, never an error. | `systemctl --user start` |
| `restart` | Stops and starts. The verb that puts a config edit into effect (config is materialized at boot; there is no live reload) — **but only a config edit already shipped to the deploy tree**: `ExecStart`/`RBTV_IGNITE_CONFIG_PATH` resolve into `$DEPLOY`, never the live repo, so restart can never pick up a live-repo-only change (task 167). On the `ignite`/`chat-bridge` units, restart now prints a loud staleness warning naming how many commits the deploy tree is behind `ignite/core-daemon` when the two disagree — it does not refuse the restart, since restart is also the crash-recovery verb. | `systemctl --user restart` |
| `stop` | Graceful: SIGTERM → grace → SIGKILL. | `systemctl --user stop` |
| `kill` | Ungraceful, SIGKILL immediately. A **distinct verb, never a flag on `stop`**, so it cannot be reached by accident. | `systemctl --user kill --signal=SIGKILL` |
| `unit` | The unit-level read: an explicit `health` verdict, load/active/sub state, main pid, active-since **and how many seconds the current active period has lasted**, last result and exec status, restart count, and the last journal lines. Answerable when the daemon is DOWN — which is when it is needed. `--json` for machine callers (the journal is text-only, deliberately: it is not escaped into the JSON). | `systemctl --user show` / `is-active` + `journalctl --user -u` |
| `selftest` | Exercises every lifecycle verb against a **throwaway unit it creates and removes**. It never touches the configured unit. | — |
| `deploy` | Refuses a missing or dirty deploy worktree; checks it out detached to the tip of `ignite/core-daemon`; ensures `ignite/node_modules`; prints old sha → new sha; restarts the unit and runs the survival check, **then also restarts `rbtv-chat-bridge.service`** (unless it's already the unit being deployed, or not installed on this box) — the bridge boots from the same deploy-tree bytes and was measured running 3-day-stale code across five deploys before this fix (task 42). Deploying = committing (D6). | `git checkout --detach` + `systemctl --user restart` (daemon + bridge) |

**`unit` is not `ignite status`.** `ignite status` is the *daemon's own* report of itself (tick
number, live sessions, queue depth) and needs it alive; `unit` is the *machine's* report about the
daemon and works when it is dead. No field appears in both — the read is called `unit` rather than
`status` for exactly this reason.

**Exit codes** (the `sd-graph` / `rbtv-goal` convention): `0` the act succeeded, or the read
succeeded · `1` the act was refused or its post-act check did not hold, or the read FAILED · `2`
usage error.

**⚠ AN EXIT CODE REPORTS WHETHER THE READ SUCCEEDED — NEVER WHETHER THE SUBJECT IS HEALTHY**
(leader ruling on defect `G-121`). `unit` exits **0** for any unit it could read, *including a
failed or crash-looping one*, and reports what it found in `health`. It exits **1** only when it
could not read the unit at all (`read_ok: false`, `error: "not-loaded"`). **A caller must branch on
`health`, never on the exit status.**

| `health` | Means |
|----------|-------|
| `healthy` | Active, and either never restarted or up longer than the unstable window. |
| `unstable` | **Active, but restarted within `RBTV_IGNITE_UNSTABLE_WINDOW_SECONDS` (default 300).** This is the verdict that exists because `active` alone is not health — see below. |
| `starting` | `activating` / `reloading` / `deactivating`. |
| `inactive` | Stopped, cleanly. |
| `failed` | The unit is in `failed` state. |

## `--service` — the same verbs, aimed at the other fixed units

Every verb above is already unit-name agnostic, and `RBTV_IGNITE_UNIT` has always steered them at
any unit. `--service` is a **selector on top of that**, not new control logic: it spares a caller
from knowing the unit names.

| `--service` | Acts on |
|-------------|---------|
| `ignite` (default) | `rbtv-ignite.service` |
| `chat-bridge` | `rbtv-chat-bridge.service` |
| `probe-suite` | `rbtv-probe-suite.timer` |

**⚠ `probe-suite` means the TIMER, never the `.service`.** The service is `static` — no `[Install]`,
it cannot be enabled or disabled — so the timer is the on/off switch. Firing ONE suite run right now
is a materially different act and keeps its own spelling:
`RBTV_IGNITE_UNIT=rbtv-probe-suite.service rbtv-ignite-daemon start`.

**An explicit `RBTV_IGNITE_UNIT` still WINS over `--service`** — every probe and every selftest
steers this script that way, and a selector must not silently overrule an operator's own override.
When the two disagree it is **said out loud on stderr**; a `--service` that quietly did nothing is
exactly the silent-no-op class this surface exists to close.

**The survival check adapts to the unit TYPE, and the type comes from systemd.** A `.timer` has no
`MainPID` — a perfectly healthy one reports 0 — so for a non-service unit `ActiveState` after the
settle window is the whole check. The type is read from `systemctl show … -p Id`, never parsed off
the name: a unit named without a suffix **is** a service (systemd appends `.service`), which is
exactly how the transient watch units are named, and a string test would have silently skipped the
pid-survival check on every one of them. `kill` against a `.timer` refuses loudly (systemd: "Unit
type does not support process killing") rather than reporting a false success.

**Environment:** `RBTV_IGNITE_UNIT` (default `rbtv-ignite.service`; wins over `--service`) · `RBTV_IGNITE_SETTLE_SECONDS`
(default 3) · `RBTV_IGNITE_JOURNAL_LINES` (default 20) · `RBTV_IGNITE_UNSTABLE_WINDOW_SECONDS`
(default 300) · `RBTV_IGNITE_DEPLOY` (default `$XDG_STATE_HOME/rbtv-deploy`, else `~/.local/state/rbtv-deploy`). The unit name is an override so a probe can
always be pointed at a throwaway unit instead of the live daemon.

## Three behaviours that are not thin, and why they are here anyway

1. **`start`/`restart` verify SURVIVAL, not a single read.** A crash-looping unit reports `active`
   with an already-dead pid, and a *changed* `MainPID` does not prove a restart succeeded either.
   The verbs re-read the pid after a settle window and fail loud when it moved. This is a measured
   failure on this box, not a hypothetical: the daemon crash-looped to `NRestarts=46` on
   2026-07-27 and was reported healthy while it was down.
2. **`unit` returns a health VERDICT, not just fields.** A unit that crash-looped and was
   restarted by systemd reports `active` / `result=success` / `exec-status 0`, with `n_restarts`
   as the **only** dissenting field — measured on a throwaway unit, and it is how the shipped
   version of this script reported a crash-looped daemon as perfectly healthy (`G-121`). Restarts
   are therefore weighed against how long the current period has lasted, and a recently restarted
   unit reads `unstable`. The survival check in (1) covers the WRITE path; this covers the READ
   path, which was open.
3. **Every verb resolves `LoadState` first.** `systemctl --user show` reports an unknown unit as
   `inactive` / `MainPID=0` **without erroring**, so a missing unit otherwise reads exactly like a
   stopped one. A unit the user manager does not know is a typed refusal (exit 1), never a
   measurement.

## No seat gate — deliberate

Owner-ruled 2026-07-26: during development **all agents on the box may run all daemon commands**.
Do not add a gate here. The enforcement point that does exist is the OS — a daemon-spawned worker's
bwrap namespace mounts `--tmpfs /run`, masking `/run/user/<uid>/bus`, so the user manager is
unreachable from inside the cage (`CMP-17` Invariant 5). The ruled master gate needs `CMP-13`'s
resolver (core-build task 7.10) and is **PARKED** in
`4-archives/executed/rbtv-sb-merge/rbtv-sb-merge-refactor/parked-gaps.md` (archived 2026-08-18, park unchanged); it turns on only with explicit owner sign-off.
Discovery is not authorization: the surface is handed to every agent per `PRIN-8`.

## Retirement — the successor is the `rbtv` CLI

**This is a SECOND ARTIFACT that exists only because its home is unbuilt, and it retires — but
the `rbtv` CLI landing is NOT what retires it. ⚠ THIS SCRIPT IS LOAD-BEARING RIGHT NOW.**

- **Successor:** the `rbtv` CLI's daemon verb family, `rbtv ignite daemon start|restart|stop|kill|unit|deploy`
  (registry `concepts/rbtv-cli.md` § daemon verb family; owner-ruled `d-ignite-operator-surface`).
- **Fold-in — DONE, and it WRAPS rather than moves** (core-build task 7.65, landed 2026-07-27).
  `rbtv ignite daemon <verb>` **execs this script**: same verbs, same names, same exit codes, no
  contract change — because 7.65's criteria ruled "wraps the stand-in script behavior unchanged",
  and a wrapper is not a reimplementation. **So the CLI is a CALLER of this folder, not a
  replacement for it, and this folder is now a DEPENDENCY rather than a predecessor.**
- **Trigger — the CLI STOPS DELEGATING, not the CLI landing.** Retirement waits until the daemon
  verbs have a real home of their own (the `CMP-5` component layer, still unbuilt) and `rbtv` no
  longer execs this script. **Until then there is nothing to retire into.**
- **On retirement (NOT YET — check the trigger above first):** delete this capability folder, and
  drop the stand-in pointer from the box runbook's § Daemon lifecycle section, which then names the
  `rbtv` command directly.

⚠ **Why this section is worded so insistently.** It previously named the trigger as "the `rbtv` CLI
landing" and instructed deleting this folder on retirement — written when fold-in was expected to
mean ABSORPTION. The CLI then landed and *wrapped*, so **the trigger fired while the instruction
became wrong: a reader checking the trigger CORRECTLY would have been told to delete the folder
`rbtv ignite daemon` depends on, breaking all five verbs.** Filed as `G-131` by `C2-rbtv-cli` (which
built the wrapper), reworded on the leader's ruling. A retirement clause must key on the condition
that makes the artifact *unused*, never on the arrival of the thing that uses it.

Also out of scope here and staying so: the cadence edit `rbtv ignite ticker set-interval` (its
first `settings.json` consumer is core-build task 7.66), and `enable`/`disable` plus unit-file
edits, which are install-time acts owned by the deploy runbook.
