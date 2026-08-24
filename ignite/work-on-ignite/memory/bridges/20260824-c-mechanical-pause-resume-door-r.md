# 20260824-c-mechanical-pause-resume-door-r — mechanical pause/resume door + resume-semantics table

kind: creation
component: bridges
date: 2026-08-24
commit: 5b6762f9
deployed: no
pin: bridges/chat/probes/probe-chat-pause-resume.js
components: engine,state-store

## Motivation
[C-14] pins a MECHANICAL `pause {goal}` / `resume {goal}`, and there was none. Pausing a goal meant
opening a conversation with that goal's master — an agent turn, a model call and a judgment, to
perform two words that admit no judgment at all — and there was no `resume` verb with defined
semantics anywhere: what resume DOES to a halted lane existed only as prose in `spec-recovery` §4.

## Design
One module, `bridges/chat/pause-resume.js`, holding the verb end to end: target resolution, the
verbatim §4.5 mechanical NACK, and the application of the resume-semantics table. It CALLS the
redesign's ending-store API rather than re-implementing recovery — `writeGoalWord`, `fireNamedEvent`,
`getCurrentEnding`, `listOpenAsks` and `getGoalState` are the whole surface it touches.

The store arrives INJECTED (the object `state-store/index.js#bind(db)` returns), plus a
`listSeats(goal)` enumerator, because `probes/probe-chat-boundary.js` forbids this process a store
handle and because the ending store has no "every lane of this goal" reader today — inventing one
here would be a second source of that fact. Rejected: reaching `require('../../state-store')`
directly (a sibling reach the boundary rule exists to stop, and the bridge process has no database
to open anyway), and re-deriving pause from the legacy `execution-lane` first token.

Parsing is `reply-grammar.js`'s, unchanged and uncopied: THERE IS NO THIRD PAUSE GRAMMAR. The
owner-reply `pause` token applies to the ending store's goal word (`goal_states.stored`); it is NOT
`lane-watch.laneIsPaused`, which reads the legacy `execution-lane` file's first token. Two readers
exist during the migration and a third would be one more place for them to disagree.

## How it works
`handle({text, channelId, threadTs, channelGoal, liveGoals})` parses; a first token that is not
`pause`/`resume` returns `{mechanical: false}` and the caller continues to the master doors
[T5-R14], unchanged. In a goal channel a bare verb targets that channel's goal; in the system
channel or a DM `channelGoal` is null so the slug is required, and a slug matching zero or several
live goals gets the verbatim §4.5 mechanical NACK with nothing changed.

`pause` is the inverse of the paused-goal row ONLY: `running` → `paused`. It does not disarm a lane
and does not open an ask. `resume` applies EVERY matching row of the table, independently: the goal
flips `paused` → `running`; a lane whose diagnostic is `attempt-counter exhaustion` is re-armed
through `fireNamedEvent(named-external-input)` — the closed list of named re-arm events in
`spec-recovery` §5 names this verb explicitly — while `recovery_relaunch_count` is deliberately left
where it stands; a `blocked-on-human` lane is REFUSED and pointed at its open ask thread; a
`gate-re-plan cap` lane is REFUSED and pointed at the gate decision-ask. A disarmed lane whose
diagnostic has no row is left untouched and said so, rather than lifted by a rule nobody wrote.

`chat-bridge.js` reaches it twice: ahead of the master doors for a top-level goal-channel or DM
message, and from `releaseAskFor` when the release door reports a mechanical verb inside an ask
thread — that second path carries the comments, which is what makes an approval-thread
`resume {goal}` resume-with-instructions [C-14].

## Consequences
Nothing replaced. `lane-watch.laneIsPaused` and `goal_cli.lane_is_paused` are untouched and still
read `execution-lane`; this verb writes the ending store's `goal_states` row. Until the two pause
records converge, a goal paused through this door is paused to every ending-store reader and NOT to
`reconcile.js`'s lane gate. That convergence is state-store/recovery work, not this door's.

NOT REACHABLE IN PRODUCTION. `index.js#main()` wires no `endingStore`: the bridge is a separate
process and the gateway intent set (`gateway/parse.js#INTENTS`) carries no goal-word intent. With no
port the door parses and targets correctly and applies NOTHING, logging a warn — chosen over a
stub that would answer as if it worked.

## Verification
`probes/probe-chat-pause-resume.js`, new, 12 checks, EXIT=0, driving the door against the REAL
ending store (`state-store/open.js` on a throwaway workspace) rather than a fake — the failure being
replaced is a resume that CLAIMS to lift a lane and leaves it disarmed, which only real writer state
can catch. Covered: no slug in the system channel, a slug matching zero goals and a slug matching
two, each producing the byte-exact §4.5 mechanical NACK with the goal word unchanged; a bare verb in
a goal channel targeting that goal and no sibling; a non-mechanical first token falling through with
no NACK; ONE FIXTURE PER RESUME-SEMANTICS ROW asserting post-resume state (paused goal → running;
counter-exhausted lane armed 0→1 with `named_event` consumed and `recovery_relaunch_count`
unchanged; blocked-on-human still disarmed with its ask still `open` and named in the refusal;
gate-cap still disarmed with `named_event` still `ask-answered`); a goal carrying three halted kinds
at once applying every matching row; and `pause` leaving an armed lane armed and an open ask open,
then `resume` leaving that ask `open` with `authorized_reply_at` still null. Red-armed by mutation:
disabling the blocked-on-human branch reddens that row. `node --check` exit 0.
`node deploy/probe-suite.js --dir bridges/chat/probes` 25/25 GREEN. Not deployed — worktree branch
`ignite/core-redesign`.

## ATTENTION
1. THERE ARE TWO PAUSE RECORDS ON THIS TREE RIGHT NOW. This verb writes `goal_states.stored`; `reconcile.js` gates on `lane-watch.laneIsPaused`, which reads the `execution-lane` file's first token. A goal paused through this door is NOT paused to the reconcile loop until those converge — do not read a green probe here as "the daemon will stop the goal".
2. `insertAsk` LANDS `posted = 0`. The §2.1 wait predicate reads `posted = 1`, so a fixture that inserts an ask and expects it to be found must call `postAsk` too. This cost one red arm: the blocked-on-human row refused correctly but could name no thread, which reads exactly like a broken refusal.
3. `fireNamedEvent` IS THE RE-ARM AND IT DOES NOT TOUCH `recovery_relaunch_count` — that is correct, not an omission. The table's "resets that counter" is the DRIVER's same-reason counter (spec-recovery §5), which lives on the driver; the relaunch budget must survive a resume, and the probe asserts it does.
4. THE MODULE HOLDS NO STORE HANDLE AND MUST NEVER ACQUIRE ONE. It lives in `bridges/chat/`, which `probe-chat-boundary.js` scans; a `require('../../state-store')` added for convenience would both redden that probe's intent and give the bridge process a database it cannot legitimately open.
5. A BARE `pause`/`resume` NACKS UNLESS THE CALLER PASSES `channelGoal`. In a goal channel that looks exactly like a parser bug and is a missing option at the call site — the same trap `reply-grammar.js`'s own entry already carries, now with a second caller that can forget it.
- Two pause records coexist: this writes goal_states.stored, reconcile.js reads execution-lane's first token
