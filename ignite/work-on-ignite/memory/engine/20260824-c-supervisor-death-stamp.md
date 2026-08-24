# 20260824-c-supervisor-death-stamp — supervisor death stamp

kind: creation
component: engine
date: 2026-08-24
commit: 9b34c874
deployed: no
pin: NONE
components: team-kit,server

## Motivation
Death was stamped by two independent writers and neither read any evidence. `attest_exit_seat` (tmux lane) and `close_session_seat` (daemon lane, reached from `spawn.js#closeSeatSessionRow` as `attest-exit --session … --force-dead`) each originated the word `exited` onto a pid-less OPEN `sessions.csv` row: a fifth ending vocabulary carrying no reason at all. A reason-less terminal is unclassifiable, so the recovery ladder had nothing to act on and every consumer downstream read a stored ledger status as if it were liveness. The `done` side carried the mirror hole recorded in CODE-GROUND-TRUTH §4: the kill-and-reap after a finished seat fired only for `ephemeral: yes` descriptors, so every non-ephemeral seat completed its work and left its harness process holding memory with nobody owed the reap. Rulings [T4-R7] [C-15] [T1-R1] [T1-R3] [T1-R18] put death truth on the supervisor and killed the `exited` vocabulary.

## Design
ONE function from observed exit to ending, `supervisor/death-stamp.js`, replacing two evidence-blind stampers.

It carries spec-supervisor §4's table verbatim: a `done` checkout is confirm-and-reaped for EVERY seat and never stamped `failed`; an `incomplete` checkout has the seat's own declaration stand and is reaped; a death with no checkout is `failed` with a mandatory reason class — `crash` when the evidence is ordinary, and `crash` plus the exit code and the transcript-tail pointer when the seat had reached check-in [T1-R18]; and evidence naming the model provider classifies `provider-error`, whose strike or reroute policy stays spec-recovery's.

The ending store is INJECTED rather than imported, the same posture `registry.js#awaitingReap` takes with `hasEnding`: liveness and endings stay two files that one caller wires together, and the wiring point is `supervisor/cli.js`, which opens the store only for the ops that need an ending (`stampDeath`, `awaitingReap`) behind a new `--db`. Rejected: importing the state-store from `death-stamp.js` directly. It would make the liveness half of the supervisor unusable on a machine where the ending store cannot be opened, and the registry seat had already paid for the injection posture one file over.

`providerShaped` uses a SHORT literal marker list rather than a loose pattern. A loose match would file ordinary crashes as infrastructure and hide real defects behind a reroute, which is the more expensive error, so anything unrecognised falls through to `crash`.

## How it works
A door hands `stampDeath(evidence, { store, registryFile })` the facts it alone witnessed — the `(goal, seat)` pair, that the process is gone, the exit code, the transcript path, whether the seat checked in — and reads `store.getCurrentEnding` to learn what the seat already said. A declared `done` or `incomplete` is never overwritten; an already-`failed` ending is not re-stamped but is still offered its reap.

`confirmAndReap` CONFIRMS before it acts, and the only question it asks is the registry probe (`kill(pid,0)` plus the `/proc/<pid>/stat` field-22 start-time), never a pane and never a stored status. The start-time match is what makes signalling safe: a recycled pid reads dead and is never signalled. A live process is sent SIGTERM and then WAITED on inside `REAP_CONFIRM_BUDGET_MS` (3 s, 25 ms polls, `Atomics.wait`) — the first draft re-probed on the next line, read the still-running process as "refused the signal" and left the row standing forever, a permanent reap debt manufactured by the reaper itself. Only once the process is confirmed gone is the registry row dropped (write moment iii). A process that survives keeps its row, because a row dropped for something still running is a leak nobody can see afterwards, while an undropped row is exactly what `awaitingReap` reports.

Non-node callers reach the same path through `supervisor/cli.js --op stampDeath|confirmAndReap|awaitingReap` and, on the python side, `team-kit/supervisor_door.py`. `SUPERVISOR_REGISTRY` overrides the registry file so a probe, a selftest or a second instance never writes the live daemon's liveness surface.

## Consequences
`attest.py` stops calling `ending_store.stamp_system` entirely — the grep for `ending_store.` in that file is now zero — and `close_session_seat` returns the supervisor's ending instead of a constant it chose, so a `done` seat that merely needed reaping is no longer reported as a crash and no longer mints staff mail saying its work is not done. `live-sessions.js` renamed its `exited:<code>` finish reason to `process-exit:<code>` because that string travels into the evidence pointer. `attached-execution.js` comments claimed a `disposition=exited` write the code had already stopped doing; they now describe the code.

## Verification
`node ignite/supervisor/death-stamp.selftest.js` — 7 cases, `ALL PASS`, all on REAL child processes: (a) death before check-in stamps `failed`/`crash`, carries `exit=137`, and the store REFUSES a literal `exited` write; (a2) a checked-in crash carries the exit code and the transcript-tail pointer; (d) a `done` checkout leaves the process gone AND the registry row gone with the seat's `done` still standing; (b) `incomplete` stands and is reaped; (c) provider-shaped evidence classifies `provider-error`; (e) a process that survives the reap signal keeps its row; (f) the kit door answers identically over the real subprocess. `node deploy/probe-suite.js --dir server/spawn/probes --dir supervisor` — 33/33 GREEN. Landed on the `ignite/core-redesign` worktree branch; NOT deployed to the live tree (the redesign cutover seat owns that).

## ATTENTION
- The reap SIGNALS a live process. The only thing standing between that and killing an unrelated process is the `/proc` start-time match inside `isAliveProcess` — a caller that persists a pid with no start-time reopens pid recycling on a code path that sends SIGTERM.
- `store` is injected and unvalidated beyond a shape check. A caller that passes a stub which silently answers `null` from `getCurrentEnding` turns every `done` checkout into a `failed: crash` stamp — the store handle is what tells this path a seat already spoke.
- `REAP_CONFIRM_BUDGET_MS` is 3 s of SYNCHRONOUS blocking inside the caller. The ticker's close arm runs this inside a tick and already caps closes per tick for `execFileSync`'s sake; raising the budget without re-reading that cap is how a tick starts overrunning.
- A `done` checkout now reaps EVERY seat, not only `ephemeral: yes`. Any seat whose process was expected to outlive its own `done` (a parked owner door, a long-lived relay) will be terminated by this path — the pane-relay exemption `reap_blockers` carries has no counterpart here.
- a done checkout reaps EVERY seat now
