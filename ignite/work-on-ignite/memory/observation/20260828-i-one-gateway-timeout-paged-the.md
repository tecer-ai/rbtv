# 20260828-i-one-gateway-timeout-paged-the — one gateway timeout paged the owner as a wedged daemon

kind: issue
component: observation
date: 2026-08-28
commit: 645c80dd
deployed: yes
pin: ignite/observation/daemon-watchdog/probes/probe-watchdog-timeout-strikes.py

## Observed
Between 2026-08-27T15:40:37Z and 2026-08-28T05:25:28Z the out-of-process watchdog
(`ignite/observation/daemon-watchdog/tool/rbtv-ignite-watchdog`, a ~70 s systemd user timer) sent
the owner 29 messages reading "daemon: THE GATEWAY IS UNANSWERABLE BUT THE DAEMON IS ALIVE —
systemd reports pid 341060 active since …, so this is a busy or wedged daemon, not a dead one …
NOT restarting; a human is needed." Every one came from the `unit-alive` arm of
`daemon_restart_gate()`. Every one was false in the only sense that matters to a reader: systemd
reported the daemon ACTIVE on all 29, no restart was ever taken, nothing was actionable, and the
owner took no action on any of them. Recorded as acceptance-wave test 15 finding A-1 and ruled by
the owner on 2026-08-28 ~16:45Z (`build/role-action-program/decisions.md`) to be fixed by option
(c) — this entry — paired with option (a), the daemon-side lane-watch yield built by the sibling
seat `fix-gateway-stall`.

The diagnosis seat `build/role-action-program/seats/diag-gateway-stall` measured the window before
anything was built (`report.md` §1.1): 892 complete passes, 862 `up` and 30 `down`. Per-pass
latency of the `inspect daemon` call — systemd's `Starting rbtv-watchdog.service` stamp to the row
the pass printed — has median 1.35 s, p90 5.44 s, and a maximum SUCCESSFUL value of 10.21 s
against a 10 s socket timeout; 112 of the 862 successes took over 5 s and 12 took over 8.8 s. All
30 failures sat at 10.28–10.98 s, i.e. exactly the timeout. Only one of the 30 (08-27T15:26:52Z,
1.59 s) was a non-timeout failure with a different cause. Deployed and HEAD are the same bytes on
this surface: the unit's `ExecStart` names the file in the SOURCE tree
(`systemctl --user cat rbtv-watchdog.service`), so this tool has no deploy gap at all.

## Mechanism
`gateway_call()` applies `TIMEOUT = RBTV_WATCHDOG_TIMEOUT_SECONDS` (10 s) as the socket timeout on
the `inspect daemon` request and returns `("down", "TimeoutError: timed out")` when it expires.
`probe_daemon()` passes that through as a `down` verdict, and `main()` hands it to
`daemon_restart_gate()`, whose first arm asks systemd for the unit's identity. When systemd answers
`running`, the arm correctly WITHHOLDS the restart (that half is the 2026-08-14 ruling, and it is
right) and then returns the note above, which `main()` appended to `alerts` — the owner-DM leg.

The defect is in the second half: the arm draws a conclusion about the daemon's STATE from ONE
sample of a latency distribution. The measurement above shows there is no bimodality to sample —
no "answering" mode and no "wedged" mode to tell apart. `inspect daemon` latency is one continuous
heavy-tailed distribution whose upper tail straddles the 10 s cutoff, produced by the daemon
parking its only thread in the `execFileSync` calls of its lane-watch pass (report §1.5, §2.2). A
sample above the cutoff and a sample at 9.5 s come from the same state of the same system, so the
timeout carries no information about whether the next call will answer. The arm's own words —
"busy or wedged" — name two conditions its evidence cannot separate, and it chose the alarming one
every time. The DM leg's 6 h re-alert ceiling did not help: each new episode was a fresh
fingerprint, so 30 timeouts scattered over 14 hours produced 29 first-time pages.

## Attempts
First attempt held on the page volume — checked: the whole history of this arm before touching it.
`daemon_restart_gate()` was itself the 2026-08-14 fix (owner ruling, `hand-notes/daemon-issues.md`
§2) for a WORSE failure in the same place: 57 `restart rc=0` passes against a live daemon, each
reaping the shared tmux server. That fix added the three gates — liveness, `RBTV_WATCHDOG_STRIKES`
(3 consecutive failed passes), and `RBTV_WATCHDOG_RESTART_BACKOFF_SECONDS` — and it worked: the
restart lever fired zero times across all 30 failures here. What it did not do is apply the same
"one missed call is not an outage" reasoning to the NOTIFICATION; the strikes gate sits on the
ACTION path only, by explicit design (the 6 h suppression window must never be able to throttle an
act), and the unit-alive arm short-circuits before the strikes are ever consulted. `0cbbb555` (the
BIT-7 cure) later added `daemon_health_streak()`, which DOES require N consecutive passes — but its
subject is the systemd identity reading, not the gateway call, and it read `healthy` on all 30 of
these passes. `a5b57bc0`/`96e20291` (wave test 2) moved the `alarm` VERDICT off the DM leg and into
the alarm registry, but the unit-alive note is a `down` verdict held at the gate, not an `alarm`
verdict, so it was untouched by that change and still reached the DM alone. Option (d) from the
diagnosis — raising `RBTV_WATCHDOG_TIMEOUT_SECONDS` to 30 — was considered and rejected by the
owner in the same ruling: it suppresses the symptom by moving the only written latency contract to
a number worse than the real requirement.

## Fix
Commit `645c80dd`. Only a gateway TIMEOUT, and only while systemd reports the unit ALIVE, is a
strike. `RBTV_WATCHDOG_TIMEOUT_STRIKES` (default 3) consecutive such passes are now required before
the condition reaches the owner at all. Below the threshold the pass prints one row —
`daemon: gateway timeout — strike k/3, no page` — writes a `page-withheld` ledger row naming the
arm, the count and the threshold, and posts nothing. At the threshold the condition goes through
`raise_row_alarm("daemon", …)`: one emitter delivery plus the ONE row in the alarm registry,
deduped by the registry's own open-row record and cleared unchanged by the existing `up` branch.

WHICH FAILURES ARE NOT STRIKES, and why the distinction is the whole design. Connection refused, a
`gateway HTTP 5xx`, a malformed body and an unreadable unit all keep their single-sample behaviour
and reach the owner on the FIRST pass. Those are determinate readings of a subject that is not
answering AT ALL; a timeout is a determinate reading of a subject that answered too slowly ONCE. A
rule that counted them together would delay the report of a genuinely dead daemon by three cadences
to fix a problem only the timeout has. `is_gateway_timeout()` sorts them off the text
`gateway_call()` produced, matching `TimeoutError:` / `timeout:` at the head (the name differs
across Python versions) and `timed out` anywhere, because urllib wraps a connect-phase timeout as
`URLError: <urlopen error timed out>` and the exception name alone would miss it.

WHERE THE COUNTER LIVES. `timeout_strikes` in the existing
`<workspace>/.rbtv/runtime/watchdog/failcount.json`, beside the restart `strikes` — the same file,
the same flat shape, the same `write_json_atomic` path, persisted by every arm's existing write, so
the change adds no write and no store. Rejected: a new file. The counter has exactly the semantics
`failcount.json` was built for (consecutive daemon-row passes, reset by an answered one) and it is
already cleared on the `up` verdict by `clear_failcount()`, which now zeroes both counters —
meaning the reset rule needed no new wiring at all. The reset is deliberately wider than "an `up`
pass": any pass that does not time out sets it to 0, including a failure of a different kind,
because the rule is CONSECUTIVE timing-out passes and a refused connection in the middle of a
timeout run is evidence of a different condition entirely (and pages on its own account anyway).

WHY THE THRESHOLD PAGE MOVED TO THE REGISTRY. The pre-fix note went to the DM leg and left NO row
on the standing-condition surface, so `ignite status`'s `open_conditions` and the 2-hourly system
digest were blind to it — the exact wave-test-2 defect `a5b57bc0` fixed for the `alarm` verdict.
Routing it through `raise_row_alarm` gives one delivery and one row, and the registry's durable
open-row dedupe replaces `state.json`'s 6 h re-alert timer for this condition. Rejected: emitting
AND keeping the `alerts.append` — two deliveries of one condition is the volume violation
spec-owner-io §9.2 forbids.

`daemon_restart_gate()` returns `(allow, line, route)` rather than `(allow, note)`. The route
(`dm` · `alarm` · `silent`) is the gate's decision because only the gate knows which arm it took;
`main()` reading the note text to guess would be a parser over a message. Rejected: a `None` note
to mean "silent", which would also have killed the printed row.

## Consequences
Nothing was deleted. The restart lever is untouched: the new gate is inside the unit-alive arm
only, so a timeout with systemd reporting the unit NOT active still falls through to the strikes
arm and still restarts once `RBTV_WATCHDOG_STRIKES` are spent — the one case the component exists
for. The `backoff` and `strikes` arms are byte-identical in text and still route `dm`, as does the
non-timeout unit-alive failure.

`main()`'s summary branch changed: `elif alarming:` became `elif alarming or withheld:` and now
prints the standing-alarm sentence (unchanged wording) plus one line per withheld condition. It had
to. A pass that read the daemon row `down`, withheld the page, and then printed "all green —
exiting silently" would be the absence-reads-as-health sentence this component exists to remove,
and it is the same trap `a5b57bc0` had to fix when the `alarm` verdict left the DM leg.

`probes/probe-watchdog-bit7-silence.py` called `daemon_restart_gate` directly and broke on the
signature (`ValueError: too many values to unpack`); it was updated in the same commit and gained
one check that both of its arms — a timeout against a unit systemd does NOT report alive, and a
non-timeout failure against a live one — still route `dm`. No other caller exists in the tree
(`grep -rn daemon_restart_gate`).

BEHAVIOUR THE OWNER WILL NOTICE, stated plainly: a 12-second gateway blip now produces NOTHING —
one journal line reading `strike 1/3, no page`. A daemon genuinely stalled for 3+ minutes produces
the same condition it always did, arriving at the third consecutive timing-out pass, so at most
~3.5 minutes later than before (three ~70 s cadences each spending a 10 s timeout). Against the
recorded window a 3-consecutive rule suppresses 25 of the 29 pages and a 2-consecutive rule 20 —
only 17:22–17:27 on 08-27 had four in a row. And when it does fire it arrives as an alarm-registry
row plus one system-channel post rather than an owner DM, which is spec §9.2's design and is a real
change in what reaches the owner's phone.

Still open and deliberately not touched here: `ignite/observation/component.md` and
`exposure.csv`'s `rbtv-ignite-watchdog` description still name only the `watchdog-daemon-unhealthy`
class and the N-fail alarm, and now also miss the `watchdog-daemon-alarm` family this fix makes
reachable. That gap predates this change (flagged by
`observation/20260828-i-an-alarm-verdict-reached-no-al`) and both files are outside this seat's
wall.

## Verification
`ignite/observation/daemon-watchdog/probes/probe-watchdog-timeout-strikes.py` — 49 checks, exit 0.
In-process over the real `main()`, one scratch workspace per arm, `daemon_identity` stubbed to a
unit systemd reports RUNNING (the condition of all 29 pages), `daemon_verdicts` stubbed away, any
restart attempt raising, and `RBTV_WATCHDOG_NOTIFY_FILE` armed so an ambient `SLACK_BOT_TOKEN`
cannot post. The two delivery surfaces are counted separately — the DM sink file for the owner-DM
leg, `kind: alarm` records in the outbox for the emitter — so "one message reached the owner" is
never asserted as the absence of both. It proves: two timing-out passes then a success deliver
nothing and leave `timeout_strikes` at 0, with no registry file created and no DM fingerprint in
`state.json`, and both withheld passes on the ledger; three timing-out passes open EXACTLY ONE row
(class `watchdog-daemon-alarm`, subject `{type: daemon, id: <unit>}`, condition naming the
consecutive count and the live pid) and send EXACTLY ONE emitter message with the DM leg unused,
and a fourth pass mints neither; three timeouts, a success and another timeout deliver nothing,
because the success both cleared the row and reset the counter to 0; a connection refused pages on
the FIRST pass with the unchanged unit-alive text, counts no strike, opens no row, and resets a
standing two-strike run; and `RBTV_WATCHDOG_TIMEOUT_STRIKES=2` really moves the threshold. RED
CONTROL in the same run: a copy of the tool with both new branches disabled — the pre-fix arm
exactly — pages the owner on ONE timeout and writes no registry row.

Regression, run from `/tmp` before and after the change: all 9 other `daemon-watchdog` probes
identical either side. Green: `probe-g188-daemon-identity` (112/112),
`probe-runner-grade-verdicts` (11/11), `probe-watchdog-alarm-registry` (31/31),
`probe-watchdog-staged-failure`, `probe-watchdog-workspace-refusal`,
`probe-watchdog-alarm-transport.js` (11), and `probe-watchdog-bit7-silence` (20 before, 21 after
with the added check). Red before and after with the IDENTICAL failure lists, and not moved by this
change: `probe-watchdog-dry-run-no-dm` (2) and `probe-watchdog-alarm-exit-zero` (3), both left red
by `a5b57bc0` because they still assert the `alarm` verdict reaches the DM leg. After every run,
`ls <repo>/.rbtv` — no such file or directory, so nothing planted a stray workspace.

DEPLOYED: immediately and by saving the file. `systemctl --user cat rbtv-watchdog.service` shows
`ExecStart=/usr/bin/python3 <repo>/ignite/observation/daemon-watchdog/tool/rbtv-ignite-watchdog` —
the source tree, no worktree. The tool's last write was 2026-08-28T16:56:32Z and the first pass to
run the new code was **16:57:27Z**; `git diff HEAD` on the tool is empty, so what has been running
since is the committed bytes. The passes at 16:57:27, 16:58:37, 16:59:41, 17:00:41 and 17:01:42
all read `daemon up` and none exercised the new branches. The one true standing alarm on this box —
the probe-suite RED, open since 2026-08-28T02:58:37Z — is untouched: still the single open row in
`.rbtv/runtime/ignite/alarm-registry.json` with `emission_count: 1`, still the only entry in
`row-alarms.json`, and every pass still prints the same standing-alarm line. No restart and no
deploy was performed.

## ATTENTION
1. Only a TIMEOUT against a unit systemd reports ALIVE is a strike. Widening this to every `down`
   verdict would delay the report of a genuinely dead daemon by three cadences — a connection
   refused is a determinate reading, not a slow one, and it is the case the whole component exists
   for. `is_gateway_timeout()` is the sorting function; changing what it matches changes which
   outages go quiet for three minutes.
2. The gate lives INSIDE the unit-alive arm. Moving it above the arms, or into `probe_daemon()`,
   silently removes the restart lever for a timeout with the unit not active — and that failure is
   invisible until the day the daemon is actually dead.
3. The threshold page goes through `raise_row_alarm`, NOT `alerts`. One condition, one delivery
   (spec-owner-io §9.2), and the registry's persisted open-row is the dedupe. Re-adding an
   `alerts.append` beside it because someone reports the DM stopped arriving reintroduces the
   double delivery and replaces a durable dedupe with a 6 h timer.
4. `timeout_strikes` resets on ANY pass that does not time out, not only on `up`. The rule is
   consecutive timing-out passes; a version that only reset on `up` would let a refused connection
   in the middle of a run carry the count forward and page for two timeouts an hour apart.
5. `daemon_restart_gate` returns three values. It is called directly by
   `probe-watchdog-bit7-silence.py`; a future arm that returns two will pass compilation and fail
   only inside that probe, at the point where a red arm is easiest to read as pre-existing.
- only a TIMEOUT against a LIVE unit is a strike — a refused connection is a determinate reading and still reports on pass 1
- the gate is INSIDE the unit-alive arm; moving it up removes the restart lever for a timeout with the unit not active
- daemon_restart_gate returns three values (allow, line, route) — probe-watchdog-bit7-silence.py unpacks it directly
