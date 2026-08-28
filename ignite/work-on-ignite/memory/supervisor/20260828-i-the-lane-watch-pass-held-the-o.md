# 20260828-i-the-lane-watch-pass-held-the-o — The lane watch pass held the only event loop

kind: issue
component: supervisor
date: 2026-08-28
commit: 47b86f47
deployed: no
pin: ignite/supervisor/probes/probe-lane-watch-yield.js
components: runtime,gateway,observation

## Observed
The daemon's gateway answered nothing for most of every 10 s cadence, and the watchdog paged the
owner about it 29 times between 2026-08-27 15:26Z and 2026-08-28 05:25Z without the daemon ever
being dead. Measured on the live daemon (`diag-gateway-stall`, 2026-08-28, HEAD `2659b948`):
`inspect daemon` over 862 successful watchdog passes had median 1.35 s, p90 5.44 s, max 10.21 s —
one continuous heavy-tailed distribution whose upper tail straddles the watchdog's 10 s socket
timeout (`observation/daemon-watchdog/tool/rbtv-ignite-watchdog:129`), not a bimodal alive/wedged
state. Twenty `curl`s at 5 s intervals split cleanly: 16 at ~36 ms, 4 between 1.69 s and 3.44 s,
nothing in between. During the four-consecutive-failure window of 2026-08-27 17:22-17:27 the pass
held the loop a median 7.89 s and up to 12.56 s of every 10 s cadence with three seeded goals, and
the daemon logged 331 lines with no gap over 2.93 s — which reads as a healthy daemon and is the
trap: a log write does not yield the event loop. Zero seat launches occurred in that window
(`actionCount:4` every tick), so the acceptance report's "under seat-launch load" reading was wrong.

## Mechanism
`supervisor/lane-watch.js#runLaneWatch` (:445) was a plain function — no `async`, not one `await` in
its whole body — looping every goal directory at :470 and spending `execFileSync(python …)` per goal:
`seeding.js:239` `ready-seats` at 0.84-1.04 s measured, plus `:286` `renewal-state` per ready seat,
`:371` `boot-prompt`, `:455` `check-acyclic`, `:208` `summoned`, and `reconcile.js`'s tmux calls —
~2.4 s per seeded daemon-assigned goal. `runtime/index.js`'s `laneWatchPass` called it synchronously
inside the `setInterval` callback, and `runtime/gateway/gateway.js`'s HTTP listener lives on that
same single Node event loop. So for the whole sweep the loop could not accept, read or answer
anything. The cost is linear in seeded goals (7.89 s / 3 goals; 2.31 s with one), so a pass that
overran the 10 s interval was immediately joined by the next `setInterval` firing — two blocking
sweeps back to back with no gap, which is how four consecutive minutes of watchdog failure happen.
Caching the status snapshot was refuted at diagnosis: the handler costs 37 ms; there is no thread on
which to deliver a cached answer either.

## Attempts
Two earlier fixes of a "gateway stall" exist and neither is this cause. `a6528bec` (2026-08-12) added
`{withThread}` to the heart-store list path; `fecd3b6a` + its pair (2026-08-21,
`server/20260821-i-heart-store-perf-fixes`) added `_execListCache` and `idx_jobslog_jobid_firedat`,
its own subject calling itself "the other half of the gateway stall". Both attacked query cost inside
the handler, which this diagnosis measured at 37 ms — they could not have held, because the handler
was never the cost. Separately `ticker/ticker.js:1960` already carried an in-code comment naming this
exact hazard ("Each close is a BLOCKING `execFileSync` of python, and this loop runs INSIDE the
tick") at one call site while every other call site on the cadence path stayed unaddressed. Owner
ruling 2026-08-28 ~16:45Z chose option (a) — yield between goals — paired with option (c), the
watchdog's consecutive-failure rule (`645c80dd`, sibling seat, `observation/`).

## Fix
`runLaneWatch` becomes `async` and awaits one `setImmediate` turn at the head of the per-goal loop;
`laneWatchPass` awaits it; the cadence callback awaits watch, then frozen, then tick, in the order
they always ran, behind a `passInFlight` flag that DROPS a tick arriving while a pass is still
running (named once at `debug`, never queued behind it). Every `execFileSync` is left exactly as it
is — `seeding.js` and `reconcile.js` are not touched, which is what keeps this ~25 lines in two
files. `setImmediate` and not `setTimeout(0)`: it resolves in the check phase, after the poll phase
has drained pending socket reads, which is where a waiting gateway request sits. What the yield buys
is availability, not speed: the sweep costs exactly what it cost. What changes is the WAIT a client
on the loop pays — it was the whole sweep and therefore grew with every goal added to the tree, and
it is now a fixed two-to-three loop turns' worth of goal-block at any tree size. Rejected: moving the
pass out of the daemon process (option B — eliminates the whole class including `recoverRoom`, but
the pass reaches the in-process engine store, so it needs an IPC seam and its own design decision);
raising `RBTV_WATCHDOG_TIMEOUT_SECONDS` (moves the only written latency contract to a number worse
than the real requirement, hiding the outage from the chat bridge and every seat); a status cache
(refuted by measurement above).

## Consequences
A gateway request can now land BETWEEN two goals, on a half-done pass — impossible by construction
before. The guard covers pass-vs-pass only and no lock was added: every write the loop makes is
per-goal and idempotent on the next cadence, so a mid-pass reader sees goals earlier in the readdir
order seeded this cadence and later ones not yet, which is the state it would have seen one cadence
earlier for those goals. `runLaneWatch`'s return type became a Promise, so both probes that drive it
were swept in the same commit, including their fixture helpers (`withOnlyGoals`, `withMutantSeeding`,
`pass`, `runMutant`) — an un-awaited callback there would tear the fixture down mid-pass. The daemon
call site's mutation anchor in `probe-daemon-lane-watch.js` M3 moved to `^\s*(await )?laneWatchPass\(\);`.
NOT covered and still open: `reconcile.js#recoverRoom` (:289-297) holds the loop for one `spawnSync`
with a 120 000 ms timeout, observed at 66.6 s on 2026-08-27 15:40:17 — inside one goal-block, so the
yield does not shorten it.

## Verification
`supervisor/probes/probe-lane-watch-yield.js` (new, 16/16 PASS, three consecutive runs, WALL_MS
~9900) drives the REAL `runLaneWatch` over 4- and 8-goal synthetic trees whose per-goal work is a
300 ms synchronous block, with a real HTTP client and server on the same event loop; a Y0 control
asserts each goal cost 301 ms and nothing more, which is the evidence no subprocess ran. Measured:
yield deleted -> max wait 1203 ms over a 1202 ms sweep with 0 answers delivered inside it, and
2431 ms over 8 goals (linear); yield present -> 604 ms at 4 goals and 603 ms at 8, answered
repeatedly during the sweep (bounded). G1-G3 compile the daemon's cadence callback verbatim from
`runtime/index.js` between two asserted anchors and invoke it: two overlapping ticks start ONE pass
with one `debug` line, the guard block deleted starts TWO, and the order stays watch -> frozen ->
tick. `probe-lane-room-open` 27/27 PASS (was PASS at the 2026-08-28T16:00Z scheduled suite run).
`probe-daemon-lane-watch` 82 ok / 1 FAIL — the same pre-existing L9 M9 red as that 16:00Z run, no new
red. `.rbtv/` absent under the repo and `tmux list-sessions` byte-identical after every run. NOT
DEPLOYED: the daemon (`rbtv-ignite`) still runs `2659b948` and this seat performed no restart.

## ATTENTION
1. A log line does NOT yield the Node event loop. The daemon journal showing no gap over 3 s during
   a stall is not evidence the loop was free — it is the trap that made this cause survive two
   earlier "gateway stall" fixes. Measure a CLIENT's latency, or the contiguous busy span, never the
   inter-line gap.
2. The yield buys availability, not speed, and the number that matters is the BOUND, not the ratio.
   A round trip costs a small fixed number of loop turns and the pass hands out one turn per goal,
   so the post-fix wait is 2-3 goal-blocks — at today's ~2.4 s per seeded goal that is still seconds.
   What is gone is the GROWTH with tree size, which is what would have made the gateway unusable.
3. The guard is pass-vs-pass ONLY. Nothing serialises a pass against a gateway request any more, and
   that was deliberate. Any future code in this loop that is NOT idempotent across cadences, or that
   leaves a store in a state only the end of the pass repairs, breaks an invariant that used to be
   free from the loop being uninterruptible.
4. `runtime/index.js`'s two `await laneWatchPass();` lines must each stay a bare statement on its own
   line: `probe-daemon-lane-watch.js` L7 counts them and M3 drops lines matching
   `^\s*(await )?laneWatchPass\(\);` to prove the call-site arm can go red. A call wrapped in an
   assignment or an argument survives that mutation and the arm would pass against a daemon that had
   stopped adopting goals by itself.
5. `readTaskforce` shells `execFileSync(python goal_cli.py check-acyclic)` through
   `validateTaskforce`, memoised per taskforce path in a `seeding.js` module-level map. Any probe
   that reaches it launches python (~750 ms per fresh goal folder) and its timings then depend on
   whether that memo is warm — which silently made a first pass over a fresh fixture root 3.5x
   slower than a second. `probe-lane-watch-yield` stubs the read out for exactly this reason.
- a log line does not yield the event loop — a journal with no gaps is not a free loop
