# `ignite/jobs/` — detector scripts fired by the daemon as `fire-tool` jobs

Built for tasks 7.71 (`r-selfheal-job`) and 7.72 (run issue G-2). A `fire-tool` job runs a
catalogue entry's `argv` verbatim (`server/ticker/ticker.js` `runToolLikeExec`), so these
scripts are the deterministic half of a self-healing job: the daemon decides *when* to look,
the script decides *whether* to act. A periodic `launch-agent` job would instead spawn a
recovery agent every period regardless of health — an unbounded paid path.

| Script | Job | Judges | Acts when |
|--------|-----|--------|-----------|
| `goal-watcher-job.py` | 7.32 / B2 | the goal's `state.json` snapshot (CMP-20) and nothing raw | a threshold in CMP-21's Layout is crossed — see below; **DARK: no catalogue entry and no profile block** |
| `jobcontain.py` | both | — | (library: self-cap, wall clock, single-instance lock) |

**Runs on: Linux only.** `goal-watcher-job.py` and `restart-daemon.py` import
`jobcontain.py`, whose containment ACTIONS need POSIX `fcntl`/`resource`. (This list read FOUR until
2026-08-11, naming `selfheal-watch.py` — that script was deleted with its whole blast radius at task
7.35, commit `c23c770c`, and its queue row deregistered 2026-08-11. Do not re-add it: the surviving
mentions of the id elsewhere in this tree are HISTORY in prose, not a file that exists.)
Since task 7.715 the module LOADS anywhere (lazy imports) but only ACTS on the VPS — author any
brief that exercises their real behaviour against it (`ignite/CLAUDE.md § jobs/`).

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
- **The staleness row's `ensure` carries `--session`, and without it the row could not repair the
  case it exists for** (task 7.561). team-monitor resolves the room's session from a ROSTER PANE
  and REFUSES when none resolves (`SessionUnresolved`, `G-296`) — which is exactly a room whose
  sensor died with its panes. The name is BANKED every pass from the snapshot's own `session`
  field (`remember_session`) and NEVER derived from the package path, so the arm with no readable
  snapshot — the dead-room arm — still has one. Both call sites build the argv through
  `sensor_ensure`, so the remedy text the leader is told to run and the argv the job execs cannot
  drift apart. A room whose session was never banked degrades to the sessionless call and the
  failing exit reaches the leader, which is CMP-21 invariant 2's own "a sensor that will not come
  back is the leader's". Proven end-to-end on a deliberately-built dead room by
  `probes/probe-dead-room-sensor-session.py`.
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

⚠ **It is DARK, and now unreachable: `config/spawn-profiles.yaml` carries NO `goal-watcher` entry
and the catalogue carries no `goal-watcher*` row** — both were retired 2026-08-20 when the per-goal
reconciliation loop (`engine/reconcile.js`, D1/D15) took over goal-level health. The program and its
probes survive; whole-program retirement was not this change's scope.

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

Neither job replaces the manual path; it only notices sooner. If a job misbehaves, disable
its queue rows and run these by hand:

```bash
# room dead — relaunch it through the kit path that created it
python3 <rbtv>/ignite/team-kit/coord.py --package <PKG> launch --only <SEAT> --force

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
address space at startup and aborts with SIGTRAP. Measured: `goal-watcher-job.py` →
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
