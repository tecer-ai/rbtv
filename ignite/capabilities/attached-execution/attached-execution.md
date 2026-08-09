# attached-execution — the `rbtv run` verb

**Built for core-build task 7.44.** Owner ruling `decisions.md#d-attached-run-embedded-engine`:
**ONE implementation of workflow advancement, TWO attachments.**

The daemon attaches ignite's engine to a systemd unit behind a gateway. This capability attaches
**the same engine** — same heart store shape, same queue, same tick algorithm, same fire path — to
the calling terminal, and it dies with that terminal.

| | daemon lane | attached lane |
|---|---|---|
| entry | `rbtv ignite daemon start` | `rbtv run <goal-folder> --profile <name>` |
| store | `{state_root}/heart.db` | `<goal-folder>/heart.db` |
| lifetime | outlives the terminal | dies with it |
| recovery | `goal-watcher-job` | **the owner re-runs the verb** — no watcher, ruled |
| engine | `ignite/engine/` | `ignite/engine/` — the same one |

## Entry point

`tool/rbtv-execution` — reached as `rbtv run`. It owns argv, output and exit codes and NO advancement
logic. Exit codes: `0` complete (or the tick bound was reached) · `1` refused, or the run cannot
advance · `3` **a worker asked a question and the run handed it back**. The third is distinct on
purpose: a run that stopped to ask is neither a success nor a failure, and a caller must be able to
tell without parsing prose.

## What it runs

The goal folder's `taskforce.csv` is the workflow. Each row is a seat; the row's **`after` column is
the wave structure**. Seats with no `after` are wave 1 and are enqueued together; a seat whose
`after` names another is released only once that one is **done** — started is not enough. How many
run at once is the ticker's `max_live_agent_sessions`, not this capability's: the wave decides
ELIGIBILITY, the ticker decides DISPATCH.

**The profile is passed by NAME and never derived.** Mapping an elected (harness, model) onto one
profile name is core-build task **7.54**'s catalog; a second mapping here is exactly the drift
`DEC-1` § Shared profile source exists to prevent. All four properties of the widened sole-spawn
gate hold: a pinned NAMED profile from the one shared config · picked by name · caller free text
never reaching argv · the pure-mechanism boundary intact.

## Resume, and the absence of a watcher

State lives in `<goal-folder>/heart.db`. Re-running the verb reopens it and continues: job
registration is create-only and a seat that already has an execution row is never re-enqueued, so a
re-run is a **resume, not a replay**. Proven by SIGKILLing a live run and re-running it
(`ignite/engine/probes/probe-engine-library.js`, section C3c).

⚠ **No watcher runs for an attached lane, and that is RULED rather than missing**
(`decisions.md#d-attached-lane-no-watcher`). The accepted cost, in the ruling's own words: *an
attached run that dies unattended stays dead until the owner notices.* Recovery is re-running this
command. Do not build a watchdog for this lane and do not file its absence as a gap.

## Windows

The verb runs on Windows as a **supported, DEGRADED substrate**
(`decisions.md#d-windows-degraded-attached-lane`) — but **the degraded branch bodies are not built
yet, and it says so rather than pretending.** `ignite/engine/substrate.js` refuses a non-POSIX host
with a typed `E_SUBSTRATE_UNSUPPORTED` naming all four sites (carrier · tree-kill ·
filesystem-wall · seat-room) and **core-build task 7.84**, which carries them.

The refusal is deliberate. Falling through would run POSIX constructs on a host that cannot honour
them — most sharply, the tree-kill signals a process GROUP inside a swallowing `try/catch` whose
liveness re-check reads a throw as *"the process is gone"*, so it would report a successful kill
having killed nothing. **A silent false green is worse than a refusal.**

## Probe

`ignite/engine/probes/probe-engine-library.js` — 56 checks over criteria 1–4 and the seam. Every
refusal carries a positive control in the same run, and the wave and resume claims are measured at
the DECISION rather than at what happened to fire (both were rewritten after a mutation sweep
showed the first versions could not fail). What it deliberately does not prove is stated in its own
header: nothing about Windows, and the seats it launches are `sleep`, not harnesses.
