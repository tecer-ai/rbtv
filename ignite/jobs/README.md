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
| `jobcontain.py` | both | — | (library: self-cap, wall clock, single-instance lock) |

(`goal-watcher-job.py`, `run-state-job.py`, `restart-daemon.py` and `recover-room.py` are also in
this folder and are NOT in the table above — noticed while adding the `edge-runner` row, left alone
rather than back-filled from guesswork.)

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

⚠ **AND `workdir` IS THE OTHER HALF OF THAT DOOR, for the same reason one field over.** The door
resolves its gateway endpoint and its sender token from FILES, never from the environment — the CLI
reads `{workspace}/.rbtv/modules/ignite/server.json` and `{workspace}/.rbtv/config/.env`, and it
finds `{workspace}` from `RBTV_IGNITE_WORKSPACE_ROOT` **or, absent that, from its own CWD**
(`cli/lib/config.js` `resolveWorkspaceRoot`). A fired exec has neither: `runToolLikeExec` passes
`envFile: null` and `systemd-run --user` does not carry the daemon's own `Environment=` lines to the
child, so the variable the daemon unit sets **does not reach this job**. Its CWD is therefore the
whole resolution, and its CWD is `args.workdir` falling back to `default_workdir_root`
(`ticker.js` `launchFireTool`). Passing `workdir` explicitly is what stops the door's credentials
from depending on an unrelated config key that happens to hold the right value today.

⚠⚠ **A RE-FIRE RE-ENQUEUES EVERY SEAT THAT HAS NOT BOOTED YET, AND THE INTERVAL IS THE ONLY BOUND.**
This job holds no memory between fires and reads no queue: `launch_candidates` suppresses a seat on
a terminal mark or an `active: yes` roster row, **and a roster row is written by the SEAT ITSELF
after it boots and registers** — so between `add-job` and that registration a candidate is invisible
to the guard and a second fire enqueues it again. Two consequences, and the second is the one to
plan around:

- **Pick an interval longer than a seat's worst-case boot-to-register latency.** `--every 60` is
  shorter than a cold harness takes to come up; `300` is the conservative default above. This is a
  bound chosen by the operator, not a guarantee the job makes.
- **A seat whose spawn never registers re-enqueues on EVERY fire, without limit.** An unhomed or
  refused launch job never produces a roster row, so nothing ever suppresses it. Watch `inspect
  queue` after arming a run; a growing count of the same seat is this, not a stuck ticker.

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
