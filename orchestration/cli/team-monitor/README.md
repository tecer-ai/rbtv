# team-monitor — the run's one raw-source sensor

Settle ledger R24. team-monitor is the **only** component that touches raw sources — tmux
panes, harness session files, `/proc` RAM and pressure, pending prompts. Its sole output is
one canonical timestamped snapshot at `{goal}/runs/run-{n}/state.json`. `goal-watcher-job`
thresholds that file; `teamview` renders it; agents query it. Nobody else reads the panes.
PRIN-2 parity: one source of truth for the facts *and* for their treatment.

## Inheritance, not reimplementation

The per-pane harness / model / context engine already exists at
`../ctx-monitor/ctx_monitor.py`. team-monitor **imports it by path** and calls its
module-level API (`pane_records`, `list_panes`, `capture_pane`, `HARNESSES`). It contains
no copy of that source and never edits it. Two sensors, one of them fixed, is the failure
this design exists to prevent.

`selftest` proves this structurally: every top-level function in both files is compared by
name, and any name the engine already defines counts as a re-implementation. Two CLI
boilerplate names (`main`, `cmd_selftest`) are allowed through and are then required to
differ in body from the engine's.

What team-monitor adds is what the engine does not expose: **seat names** from the run
roster, **per-seat RAM and liveness**, **prompt-pending**, and **box-level pressure**.

## Commands

    team-monitor start   --package <run-folder>   # idempotent; the room-creation hook form
    team-monitor ensure  --package <run-folder>   # alias of start
    team-monitor stop    --package <run-folder>
    team-monitor status  --package <run-folder> [--json]   # reads state.json, never panes
    team-monitor once    --package <run-folder>   # one capture + write
    team-monitor snapshot --package <run-folder>  # capture to stdout; writes nothing
    team-monitor selftest

`--session` overrides the room (default: the goal folder name, from the package path).
`--sensor` overrides the inherited engine path.

## Lifecycle — run-scoped, both halves deterministic

- **Close** is deterministic by construction: the loop polls `tmux has-session` and exits
  when the room is gone. Nothing has to remember to stop it.
- **Start** is one idempotent line at room creation. `ensure` is safe to call repeatedly,
  including on a room that already has a live monitor.
- **Restart after a mid-run death is NOT this component's job** and is deliberately absent:
  a supervisor inside the supervised process supervises nothing. A monitor that dies is
  detected by the consumer — `goal-watcher-job`'s stale-snapshot row — because a snapshot
  that stops advancing is exactly what a dead sensor looks like from outside.

## Timestamp discipline — the whole point of the snapshot

`captured_at` is stamped as the **first act of the capture**, before any raw read.
Serialization writes `written_at` separately and never re-stamps `captured_at`. A frozen
sensor therefore produces a snapshot that visibly **ages**, which is what the staleness
tripwire and the age display both ride on. A timestamp stamped at write time would satisfy
"carries a timestamp" while defeating staleness detection entirely.

## Exactly one writer

Enforced by an exclusive `flock` on `{run}/coordination/team-monitor.lock`, not by
convention: a second writer refuses to start and exits 3. Readers (`snapshot`, `status`)
take no lock. Every write is `tmp` + `os.replace`, so a reader never sees a partial file.

## Snapshot shape

    schema, captured_at, captured_at_iso, capture_ms, written_at, writer_pid,
    session, session_alive, package, sensor,
    box{available_mb, total_mb, swap_used_mb, swap_total_mb, load1/5/15, cores,
        pressure_memory{some_avg10..300, some_total, full_avg10..300, full_total}},
    seats[{seat, pane, window, title, cwd, harness, harness_pid, pane_pid, model,
           model_source, ctx_pct, ctx_tokens, window_tokens, ctx_ambiguous, ctx_source,
           ctx_refresh, last_activity, last_activity_age_s, prompt_pending, ram_mb,
           liveness, roster_active}],
    roster_absent[{seat, pane, liveness, reason}]

`box{}` carries the **same** `captured_at` as the rest of the snapshot — box pressure is
thresholded continuously by `goal-watcher-job` without a second raw-source reader.

`roster_absent` is the GHOSTROW input, and it separates two failures that look alike from a
distance: a roster row whose **pane left the room**, and a roster row whose **pane is still
there but holds no harness process**. The second is the one that looks healthy.

`seat` is empty for a pane whose occupant has not checked in yet — a launched-but-silent
harness is a real state and is reported as one, never guessed.

## Known bounds, stated rather than discovered

- **Context percentages are directional** (issue G-31): sub-agent turns inflate the parent
  pane's reading, so records carry `ctx_ambiguous` and a `ctx_source` of `transcript~`. The
  unambiguous fields are pane, harness, model, `window_tokens` and liveness.
- **`ram_mb` is the pane's whole process tree**, so a seat running sub-processes reports
  their memory too. That is the right number for a box-pressure decision and the wrong one
  for "how big is this agent".
- **Roster resolution reads this run's shape** — `coordination/workers.md` plus
  `taskforce.csv`. The last row for a seat name wins, so a renewed seat resolves to its
  current pane.
