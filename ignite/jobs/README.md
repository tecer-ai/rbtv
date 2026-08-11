# `ignite/jobs/` — detector scripts fired by the daemon as `fire-tool` jobs

Built for tasks 7.71 (`r-selfheal-job`) and 7.72 (run issue G-2). A `fire-tool` job runs a
catalogue entry's `argv` verbatim (`server/ticker/ticker.js` `runToolLikeExec`), so these
scripts are the deterministic half of a self-healing job: the daemon decides *when* to look,
the script decides *whether* to act. A periodic `launch-agent` job would instead spawn a
recovery agent every period regardless of health — an unbounded paid path.

| Script | Job | Judges | Acts when |
|--------|-----|--------|-----------|
| `selfheal-room.py` | 7.71 | a tmux session named as the room | the session does not exist |
| `edge-runner-job.py` | C1 | the executing goal's finished seats + every downstream `after` row | the package is ARMED (`{package}/coordination/edge-fastpath.json`); otherwise it stands down |
| `goal-watcher-job.py` | 7.32 / B2 | the goal's `state.json` snapshot (CMP-20) and nothing raw | a threshold in CMP-21's Layout is crossed — see below; **DARK today, no live catalogue entry** |
| `jobcontain.py` | both | — | (library: self-cap, wall clock, single-instance lock) |

(`goal-state-job.py`, `restart-daemon.py` and `recover-room.py` are also in this folder and are NOT
in the table above — noticed while adding the `edge-runner` row, left alone rather than back-filled
from guesswork.)

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

⚠ **It is DARK. `config/spawn-profiles.yaml` carries only `goal-watcher-throwaway`; the live
`goal-watcher` entry is deliberately absent** and arming it is a separate gated act. A live entry
MUST set `--to` to the goal's actual leader seat — the throwaway's non-leader value exists only to
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
- **The catalogue entry names a GOAL, and `job-id`/`profile` are not in it at all.** The package is
  DERIVED from the goal's LIVE LEASE at fire time (`coord.derive_lease` — the goal's tmux room plus
  its ancestry-verified seats; no stored status is read, and it refuses on an unreadable lease or on
  anything but exactly one room), and STEP 4's `job-id`/`profile` are read from the resolved
  package's own `coordination/edge-fastpath.json` — the same file the check-out fast path reads, so
  the two triggers of CMP-25 are armed by ONE act. An unarmed package is marked, reported, and
  advanced not at all. That is what keeps `r-cutover-gated` intact through the registration.

Registering it on a machine (per-machine runtime state — never in git, and needing a daemon restart
first so the boot-read catalogue carries the entry):

```bash
ignite register-job edge-runner --action-type fire-tool \
  --args-schema '{"required":{"tool":"string","goal":"string"},"optional":{"workdir":"string"}}'
# `workdir` is PASSED, not merely permitted — see the door-resolution warning below.
ignite add-job --fn edge-runner \
  --args-json '{"tool":"edge-runner","goal":"/home/henri/ht-wkdir/second-brain/.rbtv/goals/build-core-daemon-mvp","workdir":"<the workspace root — the dir holding .rbtv/>"}' \
  --trigger periodic --every 300
```

⚠⚠ **`goal` MUST be in the `--args-schema` AND in every `--args-json`, and getting the schema wrong
BURNS THE ID PERMANENTLY.** Since task 7.559 the catalogue entry's `--goal` is a `{{goal}}`
placeholder backed by the entry's `args_allowlist` (`config/spawn-profiles.yaml`), so every queue
row must carry `goal`. A job registered WITHOUT `goal` in its schema has no route to that operand:
an enqueue that carries `goal` is refused at the door (`unknown argument: goal`, `E_BAD_ARGS`), and
an enqueue without it passes the door and then REFUSES AT EVERY FIRE
(`placeholder {{goal}} has no value in the row args`, recorded `failed`). Registration is
CREATE-ONLY with a typed duplicate refusal (`E_JOB_EXISTS`), and there is no UPDATE surface and no
DELETE surface (`heart-store.js` above `registerJob`) — a schema registered without `goal` cannot be
repaired in-band; the id is burnt forever. What you CAN do is stop the bleeding:
`ignite deregister-job edge-runner` (task 7.364) sets `enabled = 0`, after which the ticker DEFERS
every due row of that job and `add-job` refuses it; `ignite remove-job <queue-id>` then clears the
pending rows a disable leaves behind (it defers them, it does not delete them). Neither frees the
id — re-registering it is still `E_JOB_EXISTS`.
Read the printed schema back before moving on.

The example `goal` above is a REAL member of the entry's `args_allowlist` — today its only one.
The value is admitted by `===` identity against that list, so an invented path, a trailing slash,
or a near miss of any kind is itself refused; use a path that is literally on the list.

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
- **One catalogue entry per target.** Each detector's target is in its argv, not its cwd, so
  re-pointing a job at a live target requires a config edit plus a daemon restart rather than a
  different enqueue.
- **`detach_argv` FORWARDS the caller's PATH across its inner hop** (7.551). That hop is a second
  `systemd-run --user`, so the detached process was handed the systemd MANAGER's environment, not
  the fired tool's — dropping the PATH `carrier.js` `toolExecEnv()` composed for it
  (`d-owner-f1-carrier-env-0808`). Nothing about argv[0] was broken (systemd-run resolves that
  CLIENT-side against the caller's PATH); what was broken is what the detached process and its
  descendants resolve BY NAME afterwards — `selfheal-room` → `recover-room.py` → `coord.py` boots
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
