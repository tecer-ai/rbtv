# watch-operator — the WATCH-LOOP operator surface

`tool/rbtv-ignite-watch <verb> (--package <abs-path> | --goal <name-or-path>)`, reached from the
`rbtv` CLI as `rbtv ignite watch <verb>`.

The fourth ignite service's power verbs, plus the watch loop's own pass cadence. It is a separate
capability from `daemon-operator` for one reason: **its target is a RUN PACKAGE, not a fixed unit.**

## Why it is not a `--service` row on `daemon-operator`

The other three services are one fixed, always-installed unit each. The watch loop's unit is
**transient and derived**: `rbtv-watch-<sha1(str(package))[:12]>`, created by `systemd-run` when
the self-heal job relaunches it (`jobs/jobcontain.py` `unit_name` / `detach_argv`). There can be
zero of them, one, or — across two simultaneous runs — several under different names. So every verb
here first has to answer *which run*, and only then *which unit*.

## The verbs

| Verb | Does |
|------|------|
| `unit` | The unit-level read for this run's watch unit. `--json` for machine callers. Delegated to `daemon-operator`, so the exit code, the `health` field and the G-121 rule are that surface's, unchanged. |
| `start` | Launches a fresh `watch.py --package <pkg> --loop-forever` inside its own transient unit, then verifies a LIVE `watch.py` for the package — the launcher's exit code is not the verdict. |
| `restart` | Restarts the existing unit (delegated). Refuses when none is loaded, naming `start`. |
| `stop` / `kill` | Delegated to `daemon-operator` against the computed unit. |
| `heartbeat-show` | The run's declared watch cadence, read through `budget.py`'s `read_cadence()`. |
| `heartbeat-set <seconds> [--restart]` | Writes `cadence.watch_loop_max_seconds` into `{package}/budget.json`. |
| `selftest` | Proves the cadence path (ceiling gate, key preservation, read-back, unit-name agreement) against a throwaway package. Touches no systemd and no live run. |

**⚠ `start` and `restart` are NOT symmetric here.** For a fixed-unit service they differ only in
whether the unit was already up. Here there is no unit at all until the first launch: `start`
CREATES it, `restart` acts on one that exists. `--help` says so, because a caller who assumes the
fixed-unit symmetry reaches for `restart` and gets a refusal.

## Target resolution — refused, never guessed

`--package` is the explicit override and always wins. Otherwise `--goal` names a goal (a name under
the walked-up `.rbtv/goals`, or a goal folder's path) and the ONE live run is resolved from its
`runs.csv` by `coord.resolve_live_run()` — via `jobs/selfheal-watch.py`'s `resolve_package()`, the
register's single reader. Zero or two runs reading `open` is a **refusal** (exit 1), never a guess:
acting on a guessed package is how a self-heal once reported healthy while doing nothing for the
live run. Every verb prints the resolved package, its provenance and the computed unit.

## `heartbeat-set` is NOT the ticker's cadence

`heartbeat` is a RETIRED word for the ticker engine (`ignite/CLAUDE.md` § Terminology). The
acceptance list's "heartbeat (set time)" is the **watch loop's** liveness-pass cadence, whose one
home is `{package}/budget.json` → `cadence.watch_loop_max_seconds`. The ticker engine's cadence is
a different, already-built surface: `rbtv ignite ticker set-interval`. Setting one while meaning
the other fails silently and completely.

**The 30-second ceiling is enforced here and nowhere else.** Owner ruling `r-watch-loop-30s` caps
the cadence at 30 s; `budget.py`'s `read_cadence()` checks only "positive integer" and bounds
nothing, so until this verb existed the ruling had no code that could refuse a breach. This is a
**gate, not a home** — the value still lives in the run's `budget.json` and is read from there. A
value hand-edited into that file past this gate is still accepted by every reader.

**Write-then-restart, not live reload** — the ratified posture the ticker already carries.
`watch.py` resolves its cadence once, in `main()`, before the loop starts; an edit while a loop runs
has no effect until that loop is relaunched. `heartbeat-set` says so, and `--restart` performs it
(restarting a running loop, or starting one if none is). A restart that fails is **loud and does not
revert the write**: the edit is durable and correct, only unapplied.

The write preserves every other key and the file's own indentation (a `budget.json` is prose-heavy
and hand-authored; re-indenting would bury a one-number change in a whole-file diff), and lands via
a temp file + rename so a crash can never leave a run holding a truncated budget.

## No second implementation (`PRIN-11`)

| Behaviour | Comes from |
|-----------|-----------|
| which run is live | `jobs/selfheal-watch.py` `resolve_package()` |
| which unit that is | `jobs/jobcontain.py` `unit_name()` — the same digest, or the two surfaces would name different units for one run and each be blind to the other's watcher |
| `unit` / `restart` / `stop` / `kill` | `capabilities/daemon-operator`, as a subprocess steered by `RBTV_IGNITE_UNIT` |
| the launch argv | the argv `selfheal-watch.py` builds — `--loop-forever` and **no cadence number**, so a relaunch can never courier a stale one |
| reading the cadence | `team-kit/budget.py` `read_cadence()` |

## Exit codes

The `sd-graph` / `rbtv-goal` convention, extended by exactly the two `rbtv-ignite-ticker` extends it
by: `0` the act/read succeeded · `1` refused, or the read FAILED · `2` usage error · `3` the cadence
is out of range, **nothing written** · `4` the write landed but the restart failed.
