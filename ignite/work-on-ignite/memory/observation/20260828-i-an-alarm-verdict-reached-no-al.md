# 20260828-i-an-alarm-verdict-reached-no-al — an alarm verdict reached no alarm registry

kind: issue
component: observation
date: 2026-08-28
commit: a5b57bc0,96e20291
deployed: at
pin: ignite/observation/daemon-watchdog/probes/probe-watchdog-alarm-registry.py
components: runtime,meta-master

## Observed
On 2026-08-26 the channel master, asked over a live owner DM whether anything was standing,
answered "No standing warnings". It was reading `ignite status`'s `standing_warnings` field
faithfully, and that field was `[]`. At the same moment the out-of-process watchdog had been
printing `probe-suite   alarm  suite is LIVE but the correctness verdict is RED: 16 genuine
probe failure(s)` every ~60 seconds for hours, and
`.rbtv/runtime/watchdog/state.json` carried `{"alert": "probe-suite: … RED …", "since":
1787880251}`. Recorded as wave test 2, FAILED BY OMISSION (owner ruling,
`build/live-acceptance-tests/decisions.md`, CP-A 2). Re-verified at HEAD 2c1e5e50 on
2026-08-28 02:18–02:52Z: `ls <workspace>/.rbtv/runtime/ignite/alarm-registry.json` — NO SUCH
FILE on this instance, twelve days after the one alarm emitter landed. Deployed and HEAD were
identical on the watchdog side (it runs from the source tree); the daemon side runs from the
`rbtv-deploy` worktree and was identical too.

## Mechanism
Two independent halves, and the answer was wrong because BOTH held.

FIRST HALF — the alarm never reached the registry. `daemon-watchdog/tool/rbtv-ignite-watchdog`
`main()` graded each row `up` / `down` / `alarm` / `skip`. The `alarm` branch read
`alerts.append("%s: %s (no restart can fix this — human needed)"); continue` — the owner-DM
leg and nothing else (fingerprint dedupe in `state.json`, a 6h re-alert ceiling, `notify()`).
`emit_alarm()` — this tool's route into `ignite/observation/emitter.js` through the sibling
`tool/watchdog-alarm.js` shim — had exactly ONE caller: `daemon_health_streak()`'s N-consecutive-
fail path. So an `alarm` verdict, the one verdict that MEANS "a human is needed and no restart
helps", was the one verdict that never became an alarm row. With no row ever written, the
registry file did not exist, and every reader of it read nothing: `chat/glance.js` (the §5
system digest's "Open conditions", which reads `emitter.readOpenConditions()`) rendered
"• none open", and nothing daemon-side read it at all.

SECOND HALF — the status read had one source where the spec has two.
`runtime/internal-api/dispatch.js#handleInspectDaemon` built `standing_warnings` from
`heartStore.listWarnings({standingOnly: true})` and published no other standing-condition
field. That is the daemon's OWN warning table. spec-owner-io §5 puts open conditions in the
alarm-signature REGISTRY, written from outside the daemon process by the watchdog and the
frozen invariant; §9 makes the emitter the one place they are composed. The master material
(`meta/master/references/master-instruments.md`, owner ruling OQ-7a) told every role that
`standing_warnings` IS the agent-facing alarm surface and that an empty list means "no
condition is standing" — true of the daemon's warnings, false of everything else. So even had
the first half been fixed alone, no role reading `ignite status` would have seen it.

## Attempts
First attempt held — checked: the whole history of the alarm route before touching it.
`0cbbb555` (the BIT-7 cure) built `emit_alarm()` and wired it to `daemon_health_streak` only;
`b3f71a70` wired the shim's Slack transport; `bd954a96`/`3d653ce9` landed the emitter and the
frozen invariant; `b3d3425c` wired `chat/glance.js` to `readOpenConditions`. Read the three
memory entries those left (`capabilities/20260825-c-watchdog-outage-ledger-n-fail`,
`capabilities/20260825-c-the-watchdog-alarm-shim-s-slac`,
`capabilities/20260825-i-bit-7-unknown-was-a-silent-sta`) plus
`engine/20260825-c-one-alarm-emitter-frozen-invar` and
`bridges/20260825-c-glance-wiring-slot-driver-read`. None of them claims the `alarm` verdict is
covered: the N-fail entry is explicit that its subject is the daemon-unhealthy streak. The
`alarm` row was never in scope of any of them — it predates the emitter by weeks and was simply
never revisited when the emitter landed. Two load-bearing earlier decisions were deliberately
NOT reversed: the 6h re-alert ceiling on the DM leg (it still governs `down` rows) and the R1
exit-code ruling (an alarm is not a systemd failure).

## Fix
ONE DELIVERY THROUGH THE EMITTER, on both halves, and the roles told the truth about both.

Watchdog: the `alarm` branch calls `raise_row_alarm()`, which routes through `emit_alarm()` and
does NOT append to `alerts`. That mirrors `daemon_health_streak` exactly — it returns a REPORT
LINE and raises through the emitter, and nothing it observes enters the DM leg. Rejected:
emitting AND keeping the DM. Two deliveries of one condition is the volume violation
spec-owner-io §9.2 forbids, and the emitter's persisted open-row signature is a durable dedupe
where `state.json`'s fingerprint is a 6h timer that a daemon restart cannot survive. Signature
class `watchdog-<row>-alarm` — one class per ROW, never per observed text, so a `probe-suite`
moving from `RED` to a runner-grade-broken verdict re-posts on the SAME row (the emitter's own
rule: the text is the change detector, not the key). Subject `{type: <row>, id: <unit>}` from a
new `ROW_UNITS` table; rejected widening `ROWS` to a fourth member, which `main()` and the
probes unpack positionally and would all have broken for a fact none of them reads.

The CLEAR is the other half of the same fix. An open registry row nobody closes turns the
standing-condition surface into a list of everything that has ever been wrong, which reads
exactly like a system that is still wrong. `clear_row_alarm()` closes the signature when the row
reads `up` again. The shim had no clear op, so `act: "clear"` was added to `watchdog-alarm.js`
itself; rejected a second shim, because two copies of the workspace resolution and the registry
path is how a caller comes to clear a row in a registry the emitter never wrote. `up` ONLY,
never `skip`: a skipped row was not graded, and closing a condition because nobody looked is the
absence-reads-as-health shape this component exists to remove. The clear branch is handed a
`post` that THROWS, so it is structurally incapable of posting — clearing is silent by the
emitter's own rule. `.rbtv/runtime/watchdog/row-alarms.json` (`RBTV_WATCHDOG_ROW_ALARMS`) records
which rows hold an open row; its own file for the reason `daemon.json` and `failcount.json` are
(`state.json` is cleared on every all-green pass, which is exactly the pass that must CLEAR),
and it is what makes the emitter reachable once per EPISODE instead of once per 60s pass — this
tool is pure Python stdlib precisely so it still runs when everything else is down.

Daemon: `handleInspectDaemon` gains `open_conditions` = `emitter.readOpenConditions()` over
`alarmRegistryPath(workspaceRoot)`, the root the api already holds. `standing_warnings` is
untouched — the two answer different questions. The emitter instance is handed a `post` that
THROWS (`chat/glance.js`'s device), so the daemon's status read can never compose an alarm, and
it `reload()`s before every read because the WRITERS are other processes. A null workspace root
answers `null`, never `[]`: "nothing is open" and "this daemon cannot read the registry at all"
are different facts, and collapsing them publishes health from the configuration that cannot
know. Finally `master-instruments.md` § instruments now names BOTH fields, states that an empty
list on either means none standing on that side, and states that a `null` is UNKNOWN.

## Consequences
Nothing was deleted or replaced. `ignite/observation/emitter.js` was NOT touched — it is
consumed, never extended. The DM leg is unchanged for `down` rows, held restarts and
failed-to-restore rows; only the `alarm` verdict left it. A pass whose ONLY finding is a standing
alarm no longer prints "all green — exiting silently": it names the standing rows and where to
read them, because with the alarm out of `alerts` the old summary line would have been a lie.
`state.json` reverts to being purely the DM-dedupe record, which is what it was built as.

BEHAVIOUR THE OWNER WILL NOTICE: a standing `alarm` no longer arrives as a repeating owner DM
every 6h. It arrives ONCE in the system channel and is then re-surfaced by the 2-hourly system
digest and by `ignite status`. That is spec §9.2's design, and the digest is now wired — but it
is a real change in what reaches the owner's phone.

`ignite/observation/component.md` § "Registered caller: the daemon watchdog" still documents only
the `watchdog-daemon-unhealthy` class and does not yet name the `watchdog-<row>-alarm` family or
record that the watchdog is the first caller to use `clear`; `ignite/observation/exposure.csv`'s
`rbtv-ignite-watchdog` description likewise names only the N-fail alarm. Both were outside this
seat's wall and are left open, surfaced in the seat report.

## Verification
`ignite/observation/daemon-watchdog/probes/probe-watchdog-alarm-registry.py` — 31 checks, exit 0.
In-process over the real `main()` with one stubbed row, a scratch workspace per run, and
`RBTV_WATCHDOG_NOTIFY_FILE` armed so an ambient `SLACK_BOT_TOKEN` cannot make it post. It proves
`--dry-run` writes no registry and no row-alarms record; an `alarm` verdict opens exactly ONE row
carrying the class, the `{type,id}` subject, the `latest.json` evidence pointer, the clears-when
sentence and `immediate: true`, with the durable `pending-delivery` outbox record beside it and
NO owner DM and NO `state.json` fingerprint; a second pass mints no second row and leaves
`emission_count: 1`; a row reading `up` clears (state `cleared`, `cleared_at` stamped, row-alarms
empty, ledgered) and posts nothing; a green pass with nothing open costs no shim call and no
ledger row. RED CONTROL in the same run: a mutated copy of the tool with the pre-fix
`alerts.append(...)` restored writes no registry file and delivers the condition to the DM sink
alone.

`ignite/runtime/internal-api/probes/probe-inspect-open-conditions.js` — 18 checks, exit 0.
In-process over the real dispatcher, a throwaway store and a scratch registry written by a
SEPARATE emitter instance: one open row surfaces on `open_conditions` key by key (the exact
five-key contract `chat/system-digest.js` documents), a cleared row leaves, a row written AFTER
the api was built is still seen (the reload), no registry file answers `[]` and the read creates
no file, a null workspace root answers `null`, and `standing_warnings` answers independently
throughout. RED CONTROL: a copy of `dispatch.js` with the field removed answers `undefined` while
`standing_warnings` still answers `[]` — the exact state the wrong 2026-08-26 answer was given
from.

Regression: all 7 pre-existing `daemon-watchdog` probes exit 0 (`probe-watchdog-staged-failure`,
`probe-watchdog-dry-run-no-dm`, `probe-watchdog-bit7-silence`, `probe-watchdog-alarm-exit-zero`,
`probe-watchdog-alarm-transport`, `probe-g188-daemon-identity`, `probe-runner-grade-verdicts`);
`node ignite/observation/emitter.selftest.js` ALL PASS; all 15 `internal-api/probes`, all 5
`runtime/gateway/probes` and all 12 `ignite-cli/probes` exit 0;
`chat/probes/probe-chat-glance-wiring.js` (the same read interface) exit 0. Two chat probes are
RED and untouched by this change (`ignite/chat/` has no modified file):
`probe-chat-boundary.js` (a named pre-existing red) and `probe-chat-ask-release.js` arm E7.

DEPLOYED: the watchdog half, YES and immediately — it runs from the source tree on a 60s systemd
user timer. The 2026-08-28 02:58:37Z pass emitted
`watchdog-probe-suite-alarm:probe-suite:rbtv-probe-suite.timer` with `delivered=True` (one
system-channel post for the standing probe-suite RED), and the 02:59 pass printed `already open
in the alarm registry since 2026-08-28T02:58:37Z`. `cat
.rbtv/runtime/ignite/alarm-registry.json` now shows that row OPEN with `emission_count: 1`. The
daemon half is NOT deployed: `dispatch.js` is boot-loaded from
`/home/henri/.local/state/rbtv-deploy`, so `ignite status` on the live daemon (pid 4086597, not
restarted) still answers without `open_conditions`. It needs a daemon restart, which was outside
this seat's authority.

## ATTENTION
1. An `alarm` verdict is now ONE delivery, through the emitter, and deliberately NOT a DM. Do
   not "restore" the `alerts.append` next to the emit because someone reports they stopped
   getting the DM — that is two deliveries of one condition, the volume violation §9.2 forbids,
   and the re-surfacing channel is the 2-hourly digest plus `ignite status`.
2. The clear fires on `up` ONLY, never on `skip`. A `skip` means the row was not graded; closing
   a standing condition because nobody looked is the exact absence-reads-as-health defect this
   component exists to remove, and it would read as a fixed system on every surface at once.
3. `row-alarms.json` is the episode guard, not a cache to tidy away. Deleting it or folding it
   into `state.json` puts a `node` spawn on every healthy 60s pass of a tool that is pure Python
   stdlib precisely so it still runs when everything else is down — and `state.json` is cleared
   on every all-green pass, which is exactly the pass that has to CLEAR.
4. `open_conditions: null` is NOT `[]`. `[]` says nothing is open; `null` says this daemon holds
   no workspace root and cannot read the registry at all. Any renderer or role that collapses
   them re-creates the 2026-08-26 answer from the one configuration that cannot know.
5. The signature class is per ROW, never per condition TEXT. `probe-suite` going from `RED` to
   `COVERAGE-MISMATCH` is the same standing condition reworded; a text-keyed class would mint a
   row per rewording and dedupe would die silently, which is indistinguishable from working.
- an alarm verdict is ONE delivery through the emitter — never re-add the DM append beside it
- the clear fires on `up` only, never on `skip` — a skipped row was not graded
- open_conditions null is NOT [] — null means this daemon cannot read the registry at all
