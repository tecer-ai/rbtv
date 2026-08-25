# `ignite/jobs/` — detector scripts fired by the daemon as `fire-tool` jobs

Built for tasks 7.71 (`r-selfheal-job`) and 7.72 (run issue G-2). A `fire-tool` job runs a
catalogue entry's `argv` verbatim (`server/ticker/ticker.js` `runToolLikeExec`), so these
scripts are the deterministic half of a self-healing job: the daemon decides *when* to look,
the script decides *whether* to act. A periodic `launch-agent` job would instead spawn a
recovery agent every period regardless of health — an unbounded paid path.

| Script | Job | Judges | Acts when |
|--------|-----|--------|-----------|
| `jobcontain.py` | — | — | (library: self-cap, wall clock, single-instance lock) |

**Runs on: Linux only.** `restart-daemon.py` imports
`jobcontain.py`, whose containment ACTIONS need POSIX `fcntl`/`resource`. (This list read FOUR until
2026-08-11, naming `selfheal-watch.py` — that script was deleted with its whole blast radius at task
7.35, commit `c23c770c`, and its queue row deregistered 2026-08-11. Do not re-add it: the surviving
mentions of the id elsewhere in this tree are HISTORY in prose, not a file that exists.)
Since task 7.715 the module LOADS anywhere (lazy imports) but only ACTS on the VPS — author any
brief that exercises its real behaviour against it (`ignite/CLAUDE.md § jobs/`).

(`restart-daemon.py` and `recover-room.py` are also in this folder and are NOT in the table above —
noticed while adding the (since deleted) `edge-runner` row, left alone rather than back-filled from
guesswork. `goal-state-job.py` was a third one; it is DELETED — `build/one-readiness-predicate.md`,
owner-ruled 2026-08-11, as a third reader of the readiness question that `coordinate ready-seats`
now answers alone.)

`agent-tmp-clean.py` (task 7.404) is also in this folder and is **not** a `fire-tool` job — it has
no catalogue entry and nothing fires it. It ages out `~/.cache/agent-tmp`, the disk-backed location
`coord.py` hands kit-launched seats as their `TMPDIR` (its `AGENT_TMPDIR`, task 7.400), which had
nothing aging it out. It is a DRY RUN unless `--go`, refuses an age floor below 7 days, and refuses
a root that is `/tmp` or on tmpfs — the two locations the owner ruled off-limits. The owner ruled its schedule on
2026-08-10: a **systemd user timer, daily** — `agent-tmp-clean.{service,timer}` under
`~/.config/systemd/user/` on the ignite VPS (`OnCalendar=daily`, `Persistent=true`, running with
`--go`). Those unit files are per-machine runtime state and are deliberately NOT in this repo.

## `goal-watcher-job.py` — DELETED 2026-08-21, and the reconcile loop is what replaced it

3,053 lines plus 12 dedicated probes, removed under the owner ruling *"if the program is dead,
delete it — there must be no dead code."* It was the ENFORCEMENT half of R24's observation
architecture (task 7.32, CMP-21): it read the goal's `state.json` snapshot (CMP-20), thresholded
it, performed the mechanical fixes inline (stale-sensor restart via team-monitor's idempotent
`ensure`, the observe-only `reap` pass, ruled seat revival through `systemd-run`) and nudged the
seat then the leader.

**It had been dark since 2026-08-20**, when the per-goal reconciliation loop (`engine/reconcile.js`,
D1/D15) took over goal-level health and every `goal-watcher*` catalogue row and profile block was
retired. Measured before deletion on 2026-08-21: no systemd unit or timer, no cron entry, zero rows
matching `%watcher%` in `heart.db`'s `jobs` and `queue` tables, last fire ever
`2026-08-17T11:19:50Z` in `jobs_log`, and every remaining mention of the name across `ignite/` a
comment rather than a call.

Deleted with it: `probes/probe-goal-watcher-{census-inrun,delivery-retry,door-exemption,
ghostrow-debounce,homings,revival,selftest,worktree-watch-start}.py`,
`probes/probe-dead-room-sensor-session.py`, `probes/probe-headless-retention-unknown.py`,
`../capabilities/daemon-watchdog/probes/probe-watchdog-goal-watcher-arm.py` and
`../coord/probes/probe-lifecycle-exec.py` — every one of them drives the deleted program as its
subject. (`probe-headless-retention-unknown` also touched `team_monitor.headless()`'s retention
closure, which keeps its own coverage inside `team_monitor.py`'s selftest.)

**Nothing else lost a caller, and that was CHECKED, not assumed.** `coord.py`'s hidden
`lifecycle-exec` command is still forked live by the RENEW checkout path (`coord.py` s3-09 builds
`["setsid", sys.executable, coord.py, "lifecycle-exec", ...]`) and keeps its coverage in
`../coord/probes/probe-lifecycle-idents.py`, which drives `cmd_lifecycle_exec` directly.
`jobcontain.detach_argv` is still called by `restart-daemon.py` and covered by
`probes/probe-detach-env.py`. What went dark is only the deleted program's own `run_revival`
actuator, which fired `lifecycle-exec` through a second `systemd-run` hop.

## `edge-runner-job.py` — DELETED 2026-08-11, and nothing replaced it here

Owner ruling `build/one-readiness-predicate.md`. There were THREE implementations of "is this seat
ready to launch" — `coord.py`'s, this file's, and `engine/seeding.js`'s — they drifted, and the
drift is what stalled the live goal. The ruling keeps ONE: `coord.py`'s `ready_seat_rows`, consumed
by `engine/seeding.js` through `coordinate ready-seats --json`. The script, its `tools: edge-runner`
catalogue entry, its probe and its audit record are gone; the `edge-runner` catalogue row in each
machine's `heart.db` is per-machine runtime state and is removed by hand.

What the ~130 lines that stood here documented, and where each still lives — because none of it was
this job's alone:

- registering a `fire-tool` job, and the ⚠ **CREATE-ONLY registration whose wrong schema burns the
  id permanently** (`E_JOB_EXISTS`, no UPDATE surface and no DELETE surface) —
  `server/heart/heart-store.js` above `registerJob`. The stop-the-bleeding pair is
  `ignite deregister-job <fn>` (sets `enabled = 0`) then `ignite remove-job <queue-id>`; neither
  frees the id.
- ⚠ **why a fired job needs `--ignite-bin` and an explicit `workdir`** — a `fire-tool` exec inherits
  the systemd `--user` MANAGER's PATH and is passed `envFile: null`, so the gateway CLI resolves its
  endpoint and its token from its CWD. Stated on the surviving entries in
  `config/spawn-profiles.yaml`.
- the Q9 IDEMPOTENT DOOR (`d-q9-door`) that makes a periodic re-submission harmless — measured on
  this job, binding on every enqueuer, and documented at `heartStore.enqueue`.

## THE FALLBACKS — one command each, and they stay armed (`r-cutover-gated`)

No job replaces the manual path; it only notices sooner. If a job misbehaves, disable
its queue rows and run this by hand:

```bash
# room dead — relaunch it through the kit path that created it
python3 <rbtv>/ignite/coord/coord.py --package <PKG> launch --only <SEAT> --force

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

⚠ **`child_preexec()` only covers a child THIS SCRIPT EXECS.** A helper called IN-PROCESS spawns
its own, and that grandchild inherits the cap. **node dies under it** — V8 reserves GBs of VIRTUAL
address space at startup and aborts with SIGTRAP. Measured on the since-deleted
`goal-watcher-job.py` — the hazard is this library's, not that script's — where
`coord.derive_lease()` → `server/lease/lease.js` read the lease as `unreadable (exit -5)` and the
job REFUSED TO START on ~200 consecutive fires (2026-08-11 → 2026-08-15) while reporting IGNORANCE
about a lease that is perfectly readable from a shell. Wrap any such call in
`with jobcontain.uncapped():` — the AS cap is lifted for that block only, the wall-clock alarm and
CPU cap stay on. Guarded by `probes/probe-jobcontain-uncapped.py`, whose U1 control fails the whole
probe if node ever SURVIVES the cap (a green U2 could not otherwise be told from a no-op).

## Design calls, settled and stated (never defaulted into)

- **Recovery goes through the kit, not the daemon** (7.71). The sole-spawn-path invariant covers
  daemon-spawned *seats*; a room is a tmux session, and this one was kit-created. Routing its
  recovery through the daemon would widen that invariant, would be dead code tonight
  (`RBTV_IGNITE_TMUX_ROOM` is deliberately unset), and would be exactly the control-loop cutover
  `r-cutover-gated` forbids. (`selfheal-room.py`, which carried that reasoning, was deleted
  2026-08-20; `engine/reconcile.js` now detects the dead room and shells `recover-room.py`.)
- **One catalogue entry per target.** Each detector's target is in its argv, not its cwd, so
  re-pointing a job at a live target requires a config edit plus a daemon restart rather than a
  different enqueue.
- **`detach_argv` FORWARDS the caller's PATH across its inner hop** (7.551). That hop is a second
  `systemd-run --user`, so the detached process was handed the systemd MANAGER's environment, not
  the fired tool's — dropping the PATH `carrier.js` `toolExecEnv()` composed for it
  (`d-owner-f1-carrier-env-0808`). Nothing about argv[0] was broken (systemd-run resolves that
  CLIENT-side against the caller's PATH); what was broken is what the detached process and its
  descendants resolve BY NAME afterwards — `recover-room.py` → `coord.py` boots
  the harness by the bare name `claude`, which lives in `~/.local/bin` and is absent from the
  manager PATH. So the helper emits `--setenv=PATH=<os.environ["PATH"]>`: **forwarded, never
  re-derived** (PRIN-11 — under the daemon that string IS `toolExecEnv()`'s output byte-for-byte;
  from a human shell it is that shell's PATH, and both are correct). Guarded by
  `probes/probe-detach-env.py` — whose R2 arm is what fails a re-derivation that would look right.

## `probes/` — `probe-detach-env.py`

The folder's first probe (7.551). It drives the real `detach_argv` and reads the PATH the DETACHED
process received, never the launcher's exit code — `systemd-run --collect --quiet` returns 0 as
soon as the unit starts, and `--collect` reaps the unit before any `systemctl show` could read it.
Its C0 control fires the same child through a bare hop and REFUSES to grade (exit 2) if that
already carries the caller's PATH, so the arm can never pass for the wrong reason. Discovery is
structural (`deploy/probe-suite.js`), so the file enrolled with no registration step:
`node deploy/probe-suite.js --only detach-env`.
