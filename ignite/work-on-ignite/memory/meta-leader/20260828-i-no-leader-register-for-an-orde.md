# 20260828-i-no-leader-register-for-an-orde — no leader register for an ordering in a row's verdict

kind: issue
component: meta-leader
date: 2026-08-28
commit: 7652dc10
deployed: yes
pin: NONE
components: supervisor,state-store,coord

## Observed
The pass relaunched `plan-verifier` 2 min into the prerequisite run its own verdict had named
(`stools-canvas-audio-elevenlabs-planning`, 2026-08-28). `plan-verifier` checked out `incomplete`
with `armed=1` at 18:55:48Z, its verdict (that goal's `coordination/messages.md` #15) stating "ORDER
MATTERS: plan-drafter applies R1/R2 FIRST, then re-bind, then relaunch me". The leader read it and
launched `plan-drafter` at 18:57:15Z. The reconcile pass at 18:59:09Z listed
`classA:["plan-verifier"]` and relaunched the verifier at 18:59:14Z — 2 min into the drafter's run
and before any re-bind. The verifier opened the OLD `planning/bound-commit`, stopped BLOCKED and
re-armed itself: one paid opus-5 sitting, ~5 minutes, and one recovery attempt burned, on a goal the
leader had already sequenced correctly in its own head.

## Mechanism
An armed `incomplete` is a class-A relaunch of that seat (`reconcile.js:930`) and the pass reads
ROWS, never mail, while §4 taught `supervise hold` for an owner answer only.
`supervisor/owed-from-endings.js#classifyEnding` maps `incomplete` + `armed=1` to reason
`incomplete`, and `supervisor/reconcile.js:930` answers that class-A row by relaunching THAT seat by
name (D33(a)) on every ~5-minute pass. The ordering the seat wrote lived only in a message, and the
pass reads ROWS and never mail — so nothing between the verdict and the relaunch could see it. The
leader had no act that expresses "not yet, in this order": `accept` and `instruct` both END the row,
and `supervise hold` (c29b2f43) was taught in `meta/leader/prompts/leader.md` §4 for one case only —
"you are waiting on a named change, typically an owner answer". A peer's self-re-arm with a stated
prerequisite is the same case and was not named, so the leader launched the prerequisite and left
the armed row standing, which is exactly the state the pass re-drives.

## Attempts
First attempt held — checked: c29b2f43 (`supervise hold`, whose ATTENTION 1 already states a hold
suppresses the WHOLE seat's class A "as true of an `armed incomplete` relaunch of the seat itself"),
a7603764 (the code-deploy re-arm cause filter, the other half of the same owner ruling), and
f3aa3f16 (the B11 relaunch-budget wake, the previous edit to this same enumerated §4 block). The
instrument was already built and deployed; only the prompt lagged. Owner ruled L2 = (a) prompt only,
and explicitly did NOT build option (b), a `checkout --incomplete --after <seat>` ordering field.

## Fix
One paragraph added to `meta/leader/prompts/leader.md` §4, immediately after the
three-sanctioned-acts block, in the leader's own register and with no new terminology: an armed
`incomplete` row whose verdict names work that must land FIRST is held in the SAME sitting the
verdict is read and BEFORE the prerequisite is launched (the next pass is minutes away — the
observed run had a 3 min 21 s window). It states the verb's real reach rather than an aspiration:
`--until` names ONLY a change on the HELD seat itself (`state-store/vocabulary.js#HOLD_UNTIL`,
honoured by `state-store/predicates.js#seatHeld`) — `new-ending` watches that seat's own ending
stamp, `ask-answered:<ask-id>` an ask open on that goal — so no `--until` word can name ANOTHER
seat's ending, and on a row being stopped from running `--until new-ending` would wait on a re-stamp
only the leader's own later ruling produces. The taught sequence is therefore `--until
ask-answered:<id>` where the prerequisite IS an open owner ask (self-clearing), else `--until
release` → prerequisite lands and is checked on disk → `supervise release <seat> --go` → the next
pass returns the row to class A and relaunches that seat. Rejected: teaching `--until new-ending` as
"wait for the prerequisite" (it names the wrong seat's ending and would read as a hold that clears
itself when nothing will clear it), and asking for a new ordering flag (owner ruling, and a second
ordering surface beside `after` edges).

## Consequences
Prose only — no code, no behaviour change, and the installed descriptors need no re-materialize:
`supervisor/spawn/spawn.js:1556` and `:1924` run `refreshSeatDescriptor` BEFORE the first read of
`seat.md` at both launch doors (D37), and it renders from the catalog root read off the descriptor's
own `component:` line, which on all three live goals is `…/3-resources/tools/rbtv/meta/leader/` —
the repo working tree this edit lands in. The next leader spawn on any goal picks the paragraph up;
a refresh that fails never blocks a launch, so the worst case is one more sitting on the old sheet.
No daemon restart is owed for this commit.

## Verification
`supervise hold --help` / `supervise release --help` read for the contract, and the contract re-read
in code: `state-store/predicates.js#seatHeld` (the three release conditions),
`state-store/writers.js#holdSeat` (the `new-ending` witness captured at write time),
`coord/ruling.py#cmd_hold` (the closed-list refusal text), `supervisor/owed-from-endings.js` (held
seats skipped in the class-A loop) and `supervisor/reconcile.js:930` (an `incomplete` class-A row
relaunches THAT seat, which is what a release returns to). `component-lint --component meta/leader`:
9 checks run, 3 skipped, 2 findings — byte-identical to the same lint over a `git archive HEAD` copy
of `meta/leader`, so both are pre-existing (`resources-coverage` over-cap bullets `coordinate` 535
and `work-on-ignite` 324 chars). `materialize-seats.py --package <live stools planning goal> --seat
leader --catalog-root <repo>/meta --refresh --root --json --dry-run` exits 0, plans 13 writes, and
its rendered descriptor differs from the installed `seats/leader/seat.md` by EXACTLY the two added
lines (unified diff, n=0) — the renderer accepts the edited prompt and would change nothing else.
Nothing applied: the goal folder's `seats/leader/seat.md` mtime is unmoved (21:11:42Z, before the
run). No nested `.rbtv/` under the repo; tmux session list untouched (no probe, selftest or spawn
was run).

## ATTENTION
1. `--until` CAN NEVER NAME ANOTHER SEAT. Every release condition is answered from a row about the HELD seat (its own ending stamp) or the goal's open asks — a hold that "waits for the drafter" does not exist, and reading `new-ending` as that is the trap this entry was written for.
2. `--until new-ending` ON A HELD, STOPPED ROW IS ALMOST `--until release`. The hold prevents the run that would re-stamp the ending, so the only remaining re-stamp is the leader's own `accept`/`instruct` — it silently ends the hold at the moment the leader rules, which is not the moment the prerequisite lands.
3. THE HOLD MUST BE POSTED BEFORE THE PREREQUISITE IS LAUNCHED, not after. The pass runs every ~5 minutes and answers an armed `incomplete` row with a relaunch; the observed run left a 3 min 21 s window between the seat's checkout and the pass that undid its ordering.
4. A RELEASE BUYS ONE SITTING ON THE COUNT THE LANE ALREADY HAD (c29b2f43 ATTENTION 5) — a hold re-arms nothing, so a lane already at N stays disarmed through hold and release.

- `--until` can never name ANOTHER seat's ending — an ordering hold is `--until release` plus the leader's own `supervise release` once the prerequisite lands
