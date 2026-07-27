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
| `jobcontain.py` | both | — | (library: self-cap, wall clock, single-instance lock) |

## THE FALLBACKS — one command each, and they stay armed (`r-cutover-gated`)

Neither job replaces the manual path; it only notices sooner. If a job misbehaves, disable
its queue rows and run these by hand:

```bash
# room dead — relaunch it through the kit path that created it
python3 <rbtv>/ignite/team-kit/coord.py --package <PKG> launch --only <SEAT> --force

# sensor dead — relaunch the watch loop
nohup python3 <rbtv>/ignite/team-kit/watch.py --package <PKG> --notify --loop 10 >/dev/null 2>&1 &
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
