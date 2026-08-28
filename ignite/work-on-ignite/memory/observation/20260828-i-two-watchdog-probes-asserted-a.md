# 20260828-i-two-watchdog-probes-asserted-a — two watchdog probes asserted a leg that was ruled away

kind: issue
component: observation
date: 2026-08-28
commit: 9e05f472
deployed: no
pin: ignite/observation/daemon-watchdog/probes/probe-watchdog-alarm-exit-zero.py

## Observed
Between a5b57bc0 (2026-08-28 ~03:00Z) and 5771be33 the hourly probe suite carried five failing
assertions nobody was chasing, all in `ignite/observation/daemon-watchdog/probes/`. Reproduced at
HEAD from the repo root on 2026-08-28T21:20:26Z: `probe-watchdog-dry-run-no-dm` exit 1 with two
fails — `stage 3: the alert is still SHOWN, not swallowed` and `stage 5: CONTROL — without
--dry-run the notify leg fires — 0 notification(s)` — and `probe-watchdog-alarm-exit-zero` exit 1
with three — `stage 3: the state file records the standing alarm — {}`, `stage 4: the owner DM leg
still fires on an alarm — 0 notification(s)` and `stage 5: CONTROL — the watchdog itself breaking
exits NONZERO — exit=0`. The second half of the symptom was on paper: the a5b57bc0 seat's own
memory entry `observation/20260828-i-an-alarm-verdict-reached-no-al` claimed in its Verification
section that "all 7 pre-existing `daemon-watchdog` probes exit 0" and named both of these among
them, so every later reader was told the opposite of the measurement. Deployed-vs-HEAD does not
apply: probes are not deployed and the watchdog tool was not touched by this fix.

## Mechanism
a5b57bc0 moved the delivery of an `alarm` verdict. Before it, `main()` appended the condition to
the owner-DM `alerts` list; after it, the `alarm` branch calls `raise_row_alarm()` — one emitter
delivery plus one row in `<workspace>/.rbtv/runtime/ignite/alarm-registry.json`, and explicitly
NOT the DM leg beside it (`daemon-watchdog.md:76` and `:180`, spec-owner-io §9.2, "one delivery,
never two"). Both probes stage a `probe-suite` row graded RED — an `alarm` — and both asserted the
DM leg: one required a notification in `RBTV_WATCHDOG_NOTIFY_FILE` as its non-vacuity control, the
other required it as an assertion in its own right and read the standing-alarm record out of
`state.json`, which an `alarm` no longer writes (state.json holds the DM-dedupe fingerprint, and
the `alarming` branch actively clears it). The change was correct and its callers were not swept
with it. The exit-zero probe's control arm went stale by the same mechanism one step removed: it
provoked "the watchdog itself breaking" by pointing `RBTV_WATCHDOG_STATE` at an unwritable path,
which only breaks a pass that WRITES state.json — after a5b57bc0 an alarm pass does not, so the
tool ran to completion and exited 0, and an arm that exists to prove the nonzero path is still
reachable proved nothing.

## Attempts
First attempt held — checked: `git log` on `ignite/observation/daemon-watchdog/probes/` (645c80dd,
5815fbaa, a5b57bc0 are the only touches since the probes were written; none re-aimed these two
arms), the a5b57bc0 memory entry, and `daemon-watchdog.md` §R1 and §"ONE delivery, not two".

## Fix
Each failing stage was re-decided from the spec rather than deleted, and the tool was left
untouched. `probe-watchdog-dry-run-no-dm`: stage 2 now requires the dry pass to write no registry
row as well as send no DM; stage 3 reads the SHOWN alert off the `would raise … but --dry-run`
line instead of `notify()`'s "NOT sent" string, which an alarm never reaches; stage 4 checks the
dedupe record the alarm path actually keeps (`row-alarms.json`) beside `state.json`; the stage 5
CONTROL requires exactly one OPEN registry row AND still zero DMs, so it pins "one delivery, never
two" in the same assertion that keeps the dry arm non-vacuous. `probe-watchdog-alarm-exit-zero`:
stage 3 asserts owner ruling R1's other half — exit 0 with no record is the alarm going silent —
at the place a5b57bc0 moved that record to (one open registry row carrying signature class
`watchdog-probe-suite-alarm`, plus `probe-suite` named in `row-alarms.json`); stage 4 was INVERTED
rather than deleted, because the removed behaviour has a ruling behind it and the negative is what
guards against re-adding it; stage 5 keeps its contract (`daemon-watchdog.md:252-258` — exit 0
means the pass RAN, anything else means the watchdog itself broke) and changes only the
provocation, to an unwritable `RBTV_WATCHDOG_ROW_ALARMS`, which is where this path now writes.
Rejected: deleting the two DM arms (loses the guard the ruling deserves), and provoking the break
through a usage error (return 2 is a different contract row, already covered by
`probe-watchdog-workspace-refusal`). Both fixtures now arm `RBTV_SYSTEM_CHANNEL_ID` with a fake id
so the shim does not refuse the emit — the notify sink is checked by the shim before any token, so
nothing can reach Slack — and drop an ambient `RBTV_WATCHDOG_ROW_ALARMS` so no fixture write can
land on the live store.

## Consequences
No behaviour changed: probes only, and the watchdog tool is byte-identical. The five failing
assertions leave the probe-suite RED count, which should read 13 on the next hourly pass if
nothing else moved (18 at 07:40Z, minus these five). The false claim in
`observation/20260828-i-an-alarm-verdict-reached-no-al` was corrected in place rather than
rewritten: the sentence is annotated `[⚠ FALSE for two of those seven …]` and a dated
`## Correction — 2026-08-28T21:26Z` section at the foot quotes the claim, lists the five
reproduced failures and states the cause. The `--dry-run` and one-delivery properties are now
asserted by two probes each (`probe-watchdog-alarm-registry` arms A and B10 in-process, these two
end-to-end through a real subprocess); the overlap is deliberate — the fixtures differ.

## Verification
`probe-watchdog-dry-run-no-dm` and `probe-watchdog-alarm-exit-zero`, 5 checks each, exit 0 — run
from the repo root (2026-08-28T21:21:48Z / 21:22:23Z) and from the vault root (21:23:14Z), with
`ls 3-resources/tools/rbtv/.rbtv` absent after both. The other 8 probes in the folder exit 0
(`probe-g188-daemon-identity`, `probe-runner-grade-verdicts`, `probe-watchdog-alarm-registry` 31
checks, `probe-watchdog-bit7-silence`, `probe-watchdog-staged-failure`,
`probe-watchdog-timeout-strikes`, `probe-watchdog-workspace-refusal`,
`probe-watchdog-alarm-transport`). Red mutations, applied to a full-tree copy at `/tmp/wd-mut`
(never the live tool) which was first re-baselined green: dropping the `if dry:` guard in
`raise_row_alarm` reddens dry stages 2, 3 and 4; restoring the pre-a5b57bc0 `alerts.append` branch
reddens dry stage 5 and exit-zero stages 3, 4 and 5; making `save_row_alarms` swallow its write
error reddens exit-zero stage 5 alone. Live state untouched: `alarm-registry.json`,
`row-alarms.json`, `state.json`, `failcount.json` and `outage-ledger.jsonl` under
`.rbtv/runtime/` are byte-identical by sha256 before (21:20:06Z) and after (21:23:42Z) every run;
`daemon.json`'s mtime moved with the live 60s timer and its content did not. No Slack post and no
owner DM: every fixture arms `RBTV_WATCHDOG_NOTIFY_FILE` in a scratch directory. Not deployed and
no restart taken — probes are not deployed, and nothing under `tool/` changed.

## ATTENTION
1. A probe arm that "controls" for a leg the code no longer has is worse than a deleted one: it
   fails loudly and the whole probe reads as broken, which is how five reds sat in the suite for
   18 hours with a memory entry saying they were green.
2. A non-vacuity control names a MECHANISM, and the mechanism can rot while the property stays
   true. `RBTV_WATCHDOG_STATE` unwritable stopped breaking the tool the moment an `alarm` stopped
   writing `state.json`; the arm still ran, still exited 0, and asserted nothing.
3. Fixtures for this tool inherit the operator's environment (`env = dict(os.environ)`). Any
   `RBTV_WATCHDOG_*` override left in a shell aims the fixture's writes at whatever it names —
   pop the ones you rely on defaulting into the scratch workspace, `RBTV_WATCHDOG_ROW_ALARMS`
   above all, since it is the one the alarm path writes without being asked.
4. The alarm shim refuses with `no system channel` unless `RBTV_SYSTEM_CHANNEL_ID` is set, and a
   refused emit records NOTHING — so a probe that forgets it sees an empty registry and blames the
   tool. The fake id is safe only because the shim checks `RBTV_WATCHDOG_NOTIFY_FILE` before any
   token (`watchdog-alarm.js:81`).
5. The shim requires the whole `ignite/` tree (it loads `ignite/observation/emitter.js`), so a
   mutation scratch holding only `daemon-watchdog/` fails the emit and reddens arms the mutation
   never touched.
- a control arm's provocation can rot while the property stays true — re-check WHY it breaks, not that it does
- watchdog fixtures inherit RBTV_WATCHDOG_* from the shell: pop the ones you rely on defaulting into the scratch workspace
