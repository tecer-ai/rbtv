# 20260828-i-the-console-resume-never-fired — the console resume never fired the re-arm event

kind: issue
component: operator
date: 2026-08-28
commit: 8c226055
deployed: no
pin: ignite/operator/goals-tree/probes/probe-console-resume-rearm.py
components: state-store,supervisor

## Observed
`rbtv goal resume goal-memory-management` printed `RESUMED — lane assignment restored to DAEMON`
at 2026-08-28 17:35Z and the goal's kept attempt counter
`reconcile-respawn / goal-memory-management/leader / nonterm` stayed at `attempts: 3`, DISARMED, in
`supervisor/attempt-counters.json` under the deploy worktree. Nothing on the console said so: the
verb's whole output is the lane line. The next failed seat on that goal would have been skipped on
every 5-minute reconcile pass with no leader wake — the silent stall the counter's re-arm exists to
end. The owner's Slack `resume` at 17:39Z cleared the row, which is what isolated the door rather
than the mechanism: the same verb, typed at the other door, worked. Deployed HEAD and repo HEAD
were the same commit (5771be33) throughout, so this is not a deploy skew.

The row that must move is named by `spec-recovery` §4 row 1 — a disarmed `incomplete:` from
attempt-counter exhaustion is what `resume {goal}` "re-arms … resets that counter; named re-arm
event" — and §5's closed list of named re-arm events names "mechanical `resume {goal}` on a
disarmed-counter lane". Since `a7603764` (`20260828-i-a-code-deploy-wiped-the-counte`, whose
ATTENTION-2 states it outright) a code deploy no longer un-sticks a `nonterm` lane, so this console
verb is the only console-reachable producer of that event.

## Mechanism
`operator/goals-tree/tool/goal_cli.py#cmd_resume` performed exactly two acts: `write_lane_raw` with
the `paused ` prefix stripped, and `_append_decisions_ruling`. It never fired the resume event at
all. The whole implementation of §4's table lives daemon-side in
`state-store/heart/pause-resume.js#applyResume`, reached only from
`runtime/internal-api/dispatch.js#handlePauseResume` — the fifteenth intent (`4a032354`), which the
Slack bridge is the only authorized sender of. One contract, two doors, one implementation, and the
console door was wired to none of it: `rearmCounterRows` → `supervisor/exhaustion.js#rearmScope
({event: 'resume'})` had exactly one caller and it was not this one.

The wrong value is therefore born at `cmd_resume` — the point at which the verb reports the goal
resumed while the state that decides whether its lanes run is untouched.

## Attempts
First attempt held — checked: `4a032354` (`20260828-c-15th-intent-pause-resume-the-m`, which minted
the intent and whose "How it works" records that `rearmScope`'s `resume` producer became wired "for
the first time" — daemon-side only); `919be192`
(`20260828-i-pause-wrote-a-store-the-lane-g`, the writer/reader store split, whose ATTENTION-1 and
-2 govern how this fix may and may not reach the store); `a7603764`
(`20260828-i-a-code-deploy-wiped-the-counte`, which removed the other producer);
`5aa80168` (`20260827-c-the-four-named-re-arm-events-g`, which built `rearmScope` and whose
ATTENTION-4 recorded the resume half as built and unreachable); `8b44d806`
(`20260828-c-the-mechanical-door-becomes-a`, the bridge's sender half). Nothing had ever attempted
the console leg.

## Fix
`cmd_resume` fires the SAME executor the intent fires, and no second copy of the table exists in
Python. It reaches it through a new ROOTED op on `state-store/cli.js` — `--op pauseResume`, taking
NO `--db`, because `pauseResume` resolves its own ending store from `workspaceRoot` and that absence
of a caller-supplied handle IS `919be192`'s fix; handing this op a `--db` would re-open that defect
through a new door. `runRootedOp` drains the executor's `logger` port into the result as `logs`, so
a ledger that refused becomes a line the operator reads rather than an empty `actions` list that
looks like "there was nothing to re-arm".

THE CALL IS PLACED AFTER THE UNSTASH, and the order is load-bearing: `applyResume` refuses with
`lane-file-paused` while the console marker still reads `paused ` (that refusal is what stops a
Slack resume silently un-parking an operator's park), so firing before the unstash would make this
door refuse itself.

IT DOES NOT ROUTE THROUGH THE GATEWAY INTENT, and that was checked rather than assumed:
`runtime/internal-api/authz.js:531 canPauseResume` is `sender.kind === 'bridge'` and nothing else,
and its own comment refuses the owner concretely — "the owner's own console route is `rbtv goal
pause` … admitting an owner token here would put a SECOND owner-facing writer of one fact on the
authorization surface". A direct call to the executor is therefore the only shape available, and it
is the right one: the executor, not the intent, is where the contract lives.

THE LEDGER PATH IS NAMED BY THE CONSOLE, and this is the part the seat's brief did not anticipate.
`supervisor/attempt-counters.js#DEFAULT_COUNTERS_PATH` is `__dirname/attempt-counters.json`, so the
counter ledger lives beside the CODE, not in the workspace. The console runs entirely from the live
SOURCE tree (`~/.local/bin/rbtv` → `meta/rbtv-cli/tool/rbtv`, `RBTV_ROOT` resolved positionally from
that file), and the source tree carries no ledger at all — it is gitignored and never created there.
Letting the executor default the path would have re-armed an absent file, printed "nothing to
re-arm", and left the daemon's row at N: the same writer/reader file split as `919be192`, arriving
through a different door. `_daemon_counters_file()` therefore resolves the ledger under the tree the
DAEMON booted, `${RBTV_IGNITE_DEPLOY:-${XDG_STATE_HOME:-$HOME/.local/state}/rbtv-deploy}` — the
identical expression `operator/daemon-operator/tool/rbtv-ignite-daemon:266` reads, so there is one
convention for "the tree the daemon runs" and not a second one invented here.

A failure is LOUD AND NON-FATAL. The unstash has already landed by the time the event fires, so a
store that will not open, a `node` that will not run, or a goal outside `goals.csv` produces a named
line saying the counters are UNCHANGED, and the verb still exits 0 on the write that did happen.
Aborting instead would leave the marker restored and the caller told the whole resume failed.

REJECTED: re-implementing the counter half in Python (two copies of one table is how the two pause
records diverged in the first place); routing through the gateway (refused by authz, by name);
passing `--db` to the rooted op (`919be192`'s ATTENTION-1); and widening `pauseResume`'s parameter
list to carry the door name — see Consequences.

## Consequences
The console verb now performs EVERY row of §4's table, not only the counter half: on a goal whose
ending store also carries a `paused` goal word it flips it to `running`, and it reports
blocked-on-human / gate-cap lanes as refusals it did not lift. That is the contract, and it closes a
second silent lie — a goal paused at BOTH surfaces used to read RESUMED at the console while
`lane-watch.js#laneIsPaused` still answered paused on the store leg.

`state-store/heart/pause-resume.js` IS UNCHANGED, deliberately, and the cost is recorded here rather
than paid silently: `evidencePointer` is a hardcoded `owner ${verb} in chat`, so a console resume
that flips the goal word files its provenance as chat. A parameter carrying the door was written and
REVERTED, because `runtime/internal-api/probes/probe-pause-resume.js` R0d/R4 anchor the exact
`function pauseResume({...})` parameter list as `919be192`'s red-proof, and any added parameter — on
any line, in any position — kills that mutation silently. Correcting the string requires moving that
anchor in the same change, which is another surface's wall.

`state-store/cli.js`'s `pause-resume` require is LAZY: the module pulls `chat/bus-ferry` in at load
time and this CLI is on the kit's hot path (`coord/ending_store.py` spawns it once per checkout
stamp), so a require nobody on the `--db` path uses is a cost every one of those would pay.

## Verification
`operator/goals-tree/probes/probe-console-resume-rearm.py`, new, 29/29 EXIT 0, entirely on scratch
workspaces with their own `.rbtv/goals` tree, ending store and `RBTV_IGNITE_DEPLOY` ledger. (a) the
verb restores the lane AND the seeded `reconcile-respawn/nonterm` row at N=3 is gone, with the
output naming the row and its count; (b)/(b2) a disarmed `incomplete:` ending row reads armed after,
by the counter sweep when a counter row exists and by §4's per-seat leg when none does; (b3) a
paused goal word flips and the `in chat` pointer is asserted as the known gap rather than
overlooked; (c) a second resume says `nothing to re-arm`; (e) a store that cannot open leaves the
lane restored, exit 0, a loud line, and the counter row honestly still at N; (f) a goal outside
`goals.csv` is a named skip. Two red proofs: (g) removes the call and the N=3 row SURVIVES while the
mutant still exits 0 and still restores the lane — which is exactly what the live defect looked
like; and (d) is the only arm that can see the LEDGER FILE SPLIT — it seeds the scratch deploy
ledger and a decoy ledger outside the daemon's tree, and asserts which file moved.

Unchanged before and after: `runtime/internal-api/probes/probe-pause-resume.js` 53/53 EXIT 0 (the
Slack path's control — it is what caught the reverted signature change),
`chat/probes/probe-chat-pause-resume.js` 23/23 EXIT 0, `probe-goal-root-escape` 27/0,
`probe-goal-scaffold-standard-files` 43/0, `probe-goal-splice` 48/0, `probe-goals-root-walkup` 8/0,
`probe-goal-teardown` EXIT 0. `goal_cli.py selftest` carries its 3 pre-existing coord-symbol
failures (`_DEFERRAL_BY_DISPOSITION`, `CLASS_TO_VERDICT`, `ADMISSION_LIMBS`) before and after, and
no others. `node --check` on `cli.js`; `compile()` on `goal_cli.py`.

Live state proven untouched across the whole sitting: `<ws>/.rbtv/runtime/ignite/heart.db`
163840 bytes @ 2026-08-24T19:04:17Z and `~/.local/state/rbtv-ignite/heart.db` 200331264 bytes @
2026-08-28T21:09:18Z, both byte-size and mtime identical before and after; the live ledger's seven
rows identical by driver/subject/reason_class/attempts with zero occurrences of the probe's goal
name; every live `execution-lane` mtime unchanged; no `.rbtv/` under the repo root.

NOT DEPLOYED at filing (commit 8c226055 on `ignite/core-daemon`) AND NO DEPLOY OR RESTART IS
REQUIRED for this fix to take effect: nothing here is daemon-loaded. `state-store/cli.js` has no JS
importer at all (it is a `require.main` entry) and appears in no entry of
`.rbtv/runtime/daemon-code.json`; `pause-resume.js` is unchanged. The console verb runs from the
source tree end to end, so it is live now.

## ATTENTION
1. THE ATTEMPT-COUNTER LEDGER LIVES BESIDE THE CODE, NOT IN THE WORKSPACE. `attempt-counters.js`
   resolves `__dirname/attempt-counters.json`, so the daemon's ledger is under the deploy worktree
   and the console's own tree has none. Any process that is not the daemon must NAME the daemon's
   ledger or it re-arms nothing while reporting success. Deleting `_daemon_counters_file()` "because
   the default already works" restores the exact defect this entry closes.
2. THE RE-ARM MUST STAY AFTER THE UNSTASH. `applyResume` refuses `lane-file-paused` while the
   console marker still parks the goal; moving the call above `write_lane_raw` makes the console
   door refuse itself and report a resume that re-armed nothing.
3. A ROOTED OP MUST NEVER TAKE `--db`. `pauseResume` derives its store from `workspaceRoot` and that
   absence is `919be192`'s fix. Adding a `--db` passthrough "for symmetry with the other ops" hands
   the executor a caller's lane store again, and a pause written there is invisible to
   `laneIsPaused` while still reporting applied.
4. DO NOT WIDEN `pauseResume`'s PARAMETER LIST WITHOUT MOVING `probe-pause-resume`'s R0d/R4. Those
   arms match the parameter list as a LITERAL STRING; any added parameter makes the mutation a no-op
   and the probe still reports green, silently retiring `919be192`'s red proof. This is why a
   console resume's `evidence_pointer` still reads `in chat`.
5. THE CONSOLE CANNOT ROUTE THROUGH THE `pause-resume` INTENT AND THIS IS RULED, NOT MISSING.
   `authz.js#canPauseResume` admits `sender.kind === 'bridge'` only and refuses an owner token by
   name. "Just send the intent from the CLI" is a change to the authorization surface, not a
   refactor.
- the attempt-counter ledger is __dirname-relative: a non-daemon process must NAME the daemon's ledger or it re-arms nothing while reporting success
