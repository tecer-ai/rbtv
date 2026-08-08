# `ignite/jobs/` — detector scripts fired by the daemon as `fire-tool` jobs

Built for tasks 7.71 (`r-selfheal-job`) and 7.72 (run issue G-2). A `fire-tool` job runs a
catalogue entry's `argv` verbatim (`server/ticker/ticker.js` `runToolLikeExec`), so these
scripts are the deterministic half of a self-healing job: the daemon decides *when* to look,
the script decides *whether* to act. A periodic `launch-agent` job would instead spawn a
recovery agent every period regardless of health — an unbounded paid path.

| Script | Job | Judges | Acts when |
|--------|-----|--------|-----------|
| `selfheal-room.py` | 7.71 | a tmux session named as the room | the session does not exist |
| `selfheal-watch.py` | 7.72 | `{package}/coordination/watch-heartbeat.json` | the stamp is old **or** its pid is not a live `watch.py` |
| `edge-runner-job.py` | C1 | the live run's finished seats + every downstream `after` row | the run is ARMED (`{package}/coordination/edge-fastpath.json`); otherwise it stands down |
| `goal-watcher-job.py` | 7.32 / B2 | the run's `state.json` snapshot (CMP-20) and nothing raw | a threshold in CMP-21's Layout is crossed — see below; **DARK today, no live catalogue entry** |
| `jobcontain.py` | both | — | (library: self-cap, wall clock, single-instance lock) |

(`run-state-job.py`, `restart-daemon.py` and `recover-room.py` are also in this folder and are NOT
in the table above — noticed while adding the `edge-runner` row, left alone rather than back-filled
from guesswork.)

## `goal-watcher-job.py` is the one that ACTS on a threshold, not only reports it (CMP-21)

Owner ruling `decisions.md#d-watcher-deterministic-chain` (2026-08-08) settles CMP-21 and RETIRES
the operational-recovery role and the closer this job used to escalate to. Its chain is now
**detect → fix INLINE where the fix is mechanical → nudge the SEAT → nudge the LEADER**, and the
alignment landed as work-list item B2. What a reader of the older docstrings must not carry over:

- **It is no longer notify-only.** Two rows perform an inline mechanical fix under `--notify`:
  the staleness row runs team-monitor's own idempotent `ensure`, and the reap row runs the kit's
  observe-only `reap` pass over the awaiting-close debt. `run_inline` is the file's ONE exec door
  and it refuses any program outside `INLINE_FIX_SCRIPTS` — which is what keeps the shadow
  backstop's "no queue door is reachable from here" claim checkable now that the file spawns.
- **The recipient is per DECISION, not per pass.** `--to` now names the **LEADER** seat and takes
  every judgment row; `QUIET` and `CONTEXT` go to the SUBJECT SEAT itself and escalate to the
  leader after `--escalate-after` consecutive unresolved passes.
- **The run-stall row reads FOUR terms, not three.** `run.live_executors` counts live *paned*
  seats only, so the predicate also reads `headless[]` (a row whose `outcome` is `null` is an
  executor still occupying work) — without it a healthy headless window reads as a stalled run.
  Any term the sensor could not read makes the row **UNDECIDABLE**; a null is never read as `0`.
- **The dirty-finish enqueue is still SHADOW** (owner-class bar, rider 1 of
  `p-756-edge-consumption-true`), and **launch gating is still the launch door's** —
  `coord.launch_gates` already refuses against the same `budget.json` floor, so this row supplies
  the rising trend and the leader's nudge, never a second gate.

`python3 goal-watcher-job.py --selftest` asserts the stall predicate's null discipline, the
headless half, the recipient chain, the escalation, the exec allowlist, and the absence of a
retired role in every `decision(...)` this file can emit. A pass WITHOUT `--notify` is a full dry
run: every row is decided and printed, nothing is delivered and no child process is spawned.

⚠ **It is DARK. `config/spawn-profiles.yaml` carries only `goal-watcher-throwaway`; the live
`goal-watcher` entry is deliberately absent** and arming it is a separate gated act. A live entry
MUST set `--to` to the run's actual leader seat — the throwaway's non-leader value exists only to
exercise delivery.

## `edge-runner-job.py` is the one whose registration is the whole point (task C1)

Owner ruling `d-owner-batch1` (1): CMP-25's edge-runner registers as a REAL daemon job — the shape
its registry record already described ("runs out of the heart store like any job") — superseding
the interim in-process arm-file-gated call from `team-kit/coord.py`, which STAYS wired.

Its catalogue entry is `tools: edge-runner` in `config/spawn-profiles.yaml`. Two things follow from
that, and both are properties of THIS job rather than of the two above:

- **Its exit is CMP-25's step 5.** Called in-process the pass returns into a caller that keeps
  running and nobody observes an exit. Fired as a job it is a process, and `recordToolCompletion`
  records the exit — 0 → `done`, non-zero → `failed`, with the pass's own output tail as the
  completion corpus. Registering it is what made step 5 exist; no exit arm was added to the file.
- **The catalogue entry names a GOAL, and `job-id`/`profile` are not in it at all.** The run is
  resolved from `{goal}/runs.csv` at fire time (`coord.resolve_live_run`, which refuses on zero or
  two open rows), and STEP 4's `job-id`/`profile` are read from the resolved run's own
  `coordination/edge-fastpath.json` — the same file the check-out fast path reads, so the two
  triggers of CMP-25 are armed by ONE act. An unarmed run is marked, reported, and advanced not at
  all. That is what keeps `r-cutover-gated` intact through the registration.

Registering it on a machine (per-machine runtime state — never in git, and needing a daemon restart
first so the boot-read catalogue carries the entry):

```bash
ignite register-job edge-runner --action-type fire-tool \
  --args-schema '{"required":{"tool":"string"},"optional":{"workdir":"string"}}'
# `workdir` is PASSED, not merely permitted — see the door-resolution warning below.
ignite add-job --fn edge-runner \
  --args-json '{"tool":"edge-runner","workdir":"<the workspace root — the dir holding .rbtv/>"}' \
  --trigger periodic --every 300
```

⚠ **`--ignite-bin` in that entry is load-bearing.** STEP 4's door is the `ignite` CLI, and a
`fire-tool` exec inherits the systemd `--user` MANAGER's PATH, which does not carry `~/.local/bin`.
The bare name resolves for every interactive caller and for nobody under the daemon.

✔ **PATH — and PATH only — is fixed at the carrier since F1** (`d-owner-f1-carrier-env-0808`). Every
`fire-tool` exec is now composed with `--setenv PATH=<~/.local/bin>:…` (`server/spawn/carrier.js`
`toolExecEnv`), so a bare tool name DOES resolve under the daemon and no future entry has to
rediscover the lesson above. The flag stays regardless: it names the REPO file rather than the
`~/.local/bin` symlink, and that reason is untouched by the environment fix. **Nothing else about
the environment changed** — see the `workdir` note below, which still holds in full.

⚠ **AND `workdir` IS THE OTHER HALF OF THAT DOOR, for the same reason one field over.** The door
resolves its gateway endpoint and its sender token from FILES, never from the environment — the CLI
reads `{workspace}/.rbtv/modules/ignite/server.json` and `{workspace}/.rbtv/config/.env`, and it
finds `{workspace}` from `RBTV_IGNITE_WORKSPACE_ROOT` **or, absent that, from its own CWD**
(`cli/lib/config.js` `resolveWorkspaceRoot`). A fired exec has neither: `runToolLikeExec` passes
`envFile: null` and `systemd-run --user` does not carry the daemon's own `Environment=` lines to the
child, so the variable the daemon unit sets **does not reach this job** — and the F1 carrier fix
above does NOT change that, because it composes exactly one variable (`PATH`) and deliberately
inherits nothing else. Its CWD is therefore the
whole resolution, and its CWD is `args.workdir` falling back to `default_workdir_root`
(`ticker.js` `launchFireTool`). Passing `workdir` explicitly is what stops the door's credentials
from depending on an unrelated config key that happens to hold the right value today.

⚠ **A RE-FIRE STILL ASKS FOR EVERY SEAT THAT HAS NOT BOOTED YET — THE DOOR IS WHAT MAKES THAT
HARMLESS** (task Q9, ruling `d-q9-door`). This job holds no memory between fires and reads no
queue: `launch_candidates` suppresses a seat on a terminal mark or an `active: yes` roster row,
**and a roster row is written by the SEAT ITSELF after it boots and registers** — so between
`add-job` and that registration a candidate is still invisible to THIS file's guard and a second
fire still submits it. What changed is the other side: `heartStore.enqueue` is now IDEMPOTENT per
(run, seat), so the second submission mints no row.

- **The duplicate is absorbed at the door, not here** — and deliberately so: this file speaks to
  the queue only through `submit` and must never read it back. A repeat submission for a (run,
  seat) already held — by a pending row OR by a live turn — returns the ORIGINATING queue id, so
  the pass sees an ordinary success and stays green. The daemon log names each one
  (`idempotent-suppress`, with the originating id); the queue does not grow.
- **A seat whose spawn never registers no longer re-enqueues without limit.** It re-submits on
  every fire and is absorbed every time, so `inspect queue` no longer grows. The seat is released
  the moment its turn reaches a TERMINAL outcome (`done`/`blocked`/`failed`/`killed`) — which is
  what keeps crash-retry working; a seat that crash-loops is the goal-watcher's stall row to
  escalate, not the door's.
- **The interval is now a cost choice, not a correctness bound.** A shorter interval means more
  absorbed submissions and more log lines, never duplicate launches. `300` remains the default
  above because a pass is not free, not because a shorter one would double-launch a seat.

⚠ **A PRODUCTIVE PASS IS RECORDED `failed` WHENEVER ANY CANDIDATE WAS REFUSED**, and that is the
file's own pre-existing fail-loud contract (`return 1 if res["failed"]`), deliberately not changed
by the registration. `recordToolCompletion` maps any non-zero exit to `failed`, so `jobs_log` shows
`failed` identically for "advanced nine edges, refused two" and for "crashed on line one" — the
exit code and the status do not distinguish them. **The distinction is only in the completion
corpus** (the pass's output tail): a productive pass names every `QUEUED` row above its refusals,
a crashed one does not. Read the corpus, never the status, to tell the two apart. Under a periodic
trigger a run carrying one permanently-refused candidate reports `failed` on every fire.

## THE FALLBACKS — one command each, and they stay armed (`r-cutover-gated`)

Neither job replaces the manual path; it only notices sooner. If a job misbehaves, disable
its queue rows and run these by hand:

```bash
# room dead — relaunch it through the kit path that created it
python3 <rbtv>/ignite/team-kit/coord.py --package <PKG> launch --only <SEAT> --force

# sensor dead — relaunch the watch loop (cadence comes from the run's budget.json; pass no number)
nohup python3 <rbtv>/ignite/team-kit/watch.py --package <PKG> --notify --loop-forever >/dev/null 2>&1 &
```

## What they write

Nothing but stdout/stderr, which `fire-tool` captures into `{data_root}/logs/<session>.log`
— an artifact class task 7.13's age sweep already bounds. The only file either script creates
is its own `flock` lockfile (empty, one per target, released at exit). No private log class
was invented outside 7.13's sweep.

## Containment is self-imposed, because nothing imposes it (issues.md G-30)

`runToolLikeExec` passes literal `caps: {}` / `sandbox: {}` and `ticker.js` never calls
`buildBwrapArgv` — a `fire-tool` exec gets **no** bwrap namespace and **no** cgroup caps, unlike
every seat. `jobcontain.py` therefore caps each detector's own address space and wall clock and
enforces one instance per target. Its central subtlety: `RLIMIT_AS` is inherited, so every child
is exec'd through `child_preexec()`, which restores the original limits — otherwise a detector
would hand its 256 MB cap to the very sensor or recovery agent it is resurrecting.

## Design calls, settled and stated (never defaulted into)

- **Recovery goes through the kit, not the daemon** (7.71). The sole-spawn-path invariant covers
  daemon-spawned *seats*; a room is a tmux session, and this one was kit-created. Routing its
  recovery through the daemon would widen that invariant, would be dead code tonight
  (`RBTV_IGNITE_TMUX_ROOM` is deliberately unset), and would be exactly the control-loop cutover
  `r-cutover-gated` forbids. Full reasoning in `selfheal-room.py`'s docstring.
- **A heartbeat is two facts** (7.72): the timestamp *and* that its stated pid is a live
  `watch.py`. A fresh stamp left by a dead writer is a gravestone, and freshness-only logic reads
  it as healthy for a whole tolerance window — observed on this run 2026-07-27 04:46–04:54.
- **Tolerance ×3**, matching `coord.watcher_heartbeat()`, so the job and the `coordinate workers`
  line humans read never disagree about the same file.
- **One catalogue entry per target.** Each detector's target is in its argv, not its cwd, so
  re-pointing a job at a live target requires a config edit plus a daemon restart rather than a
  different enqueue.
