# 20260828-c-15th-intent-pause-resume-the-m — 15th intent: pause-resume, the mechanical verb daemon-side

kind: creation
component: gateway
date: 2026-08-28
commit: 4a032354
deployed: no
pin: ignite/runtime/internal-api/probes/probe-pause-resume.js
components: runtime,state-store,supervisor,chat

## Motivation
The owner's mechanical `pause {goal}` / `resume {goal}` — one grammar, no judgment, the whole
reason the door bypasses the goal master [T5-R14] — parsed correctly, resolved its target
correctly, and then changed nothing and said nothing. Wave tests 8/9/10 failed on that silence.
The cause was not the door: `chat/index.js:119` builds the bridge with `buildBridge(config)` and
injects NO ports, and no port could legally have been injected — every applier the verb needs is
daemon state the bridge process may not hold (`chat/probes/probe-chat-boundary.js` forbids it a
store handle, a child process and a sibling require; entry `20260824-i-open-asks-has-no-boundary-lega`
records a migration that reached through that wall being reverted whole). The 2026-08-24 ruling
that minted `start-execution` had DECLINED the pause word — "pause stays store-side until the
execution-lane reconcile gate converges onto the goal-state row". That convergence never arrived;
what arrived was the evidence that waiting had cost the owner the verb entirely.

## Design
The owner reversed the deferral on 2026-08-28 (~02:00Z, item (2) at 02:12Z,
`role-action-program/decisions.md`): mint the intent so the bridge's mechanical verbs act through
the daemon. Same shape as the fourteenth — bridge is an authenticated CALLER, the daemon holds the
capability.

ONE intent with a `verb` field, not two. `pause` and `resume` are one door in the spec
(`spec-owner-io` §4.2/§4.4/§4.5: one grammar, one target resolution, one NACK), one authorization
question and one result shape; a per-verb pair would put a fork at the door that exists nowhere
else and would have to be kept in lockstep across all three copies of the closed intent set twice
over. The verb is a CLOSED two-member enum and therefore SHAPE, refused at the gateway the way
`SESSION_MODES` and `TRIGGER_KINDS` are.

The result shape is `applyPause`/`applyResume`'s own return value plus `verb` and `goal` —
deliberately not a new wire format. The renderer the owner reads (`summarize()`) was already
right, so fixing the contract at the shape it already produced left the bridge's rendering
byte-unchanged and made the two seats' halves independently buildable.

Rejected: keeping an injectable applier port on the bridge and defaulting it to a real sender —
that seam is exactly where an embedder writes a stub to make a test pass, after which the door
tells the owner a goal is paused while it runs. `start-execution.js`'s precedent verbatim.

## How it works
`gateway/parse.js` registers `pause-resume` and checks SHAPE only: the closed verb enum and the
goal against `BUS_NAME_RE`; an unknown key is a refusal (`rejectUnknownKeys`), there is no
`comments` field because [C-14]'s resume-with-instructions is the BRIDGE's to carry.
`internal-api/dispatch.js#handlePauseResume` runs the ladder every sibling uses — strict schema,
shape re-check (DEC-3), authorization, act — and `authz.canPauseResume` is BRIDGE-ONLY, the fourth
member of the joint-narrowest group. `kind: owner` is refused with a CONCRETE reason rather than
"no caller today": the owner's console route is `rbtv goal pause`, and admitting an owner token
would put a second owner-facing writer of one fact on the authorization surface.

`state-store/heart/pause-resume.js` performs the act. The resume-semantics table [C-14] and its
refusal prose MOVED here from the bridge, which deleted its copy in the same landing (8b44d806) —
there is exactly one copy and it is this one. The three ports that could only ever have been
injected are real handles: `bind(heartStore.db)` for the ending store, `seeding.js#readTaskforce`
for the goal's lanes (the reader the lane pass itself spends, never a second `taskforce.csv`
parser), and `exhaustion.js#rearmScope({event:'resume'})` for the counter half. Both supervisor
modules are LAZY-required — a module-level import would be a dependency every importer of the
state store inherits, and `lane-watch` <-> `reconcile` is a load-time cycle.

The live-goal roster is `.rbtv/goals/goals.csv` (`coord/owed-answers.py#packages`'s precedent),
filtered to rows whose folder exists and whose name is not `_`-prefixed. A slug outside it is
`NOT_FOUND`, which the bridge renders as §4.5's verbatim mechanical NACK. A directory listing was
rejected: it would admit `_archive`, a half-deleted folder and any scratch directory, and the
answer this list produces is a refusal the owner READS.

## Consequences
Nothing was deleted here; the bridge's half deleted its table and its unwired ports.
`exhaustion.js#rearmScope`'s `resume` producer is WIRED in production for the first time — it was
built by 5aa80168 and unreachable for exactly want of this intent (that entry's ATTENTION-4).

One second-order hazard had to be closed in the same change and is filed separately under
`supervisor`: no goal on this instance carries a `goal_states` row, so making the Slack verb write
one would have let it override the console's `execution-lane` pause marker. `laneIsPaused` is now
an OR over both surfaces and the resume executor refuses by name when the console marker still
parks the goal.

BOTH HALVES MUST DEPLOY TOGETHER. The bridge already forwards `pause-resume`; a daemon without this
commit answers `UNKNOWN_INTENT`, which the bridge renders as itself (not as the NACK) — loud, but
a broken verb.

## Verification
`runtime/internal-api/probes/probe-pause-resume.js`, new, 38/38 EXIT 0: pause flips the row and
reports `running→paused`; resume runs every matching row of the table on one goal (goal word,
counter-exhausted lane re-armed on BOTH halves, blocked-on-human refused with its ask id, the ask
still open afterwards [§4.2]); a bogus slug is `NOT_FOUND` naming the slug; `_channel-master` is
refused and the roster excludes it; bridge-only authz proven against agent / proven goal-master /
owner and across the wire; four shape refusals including the core's independent re-check. Three red
mutations run inside the probe on discarded copies: dropping the authz predicate authorizes an
agent, dropping the roster check applies a bogus slug, restoring the pre-change `laneIsPaused`
return un-parks the console-parked goal.

`probe-intent-drift` PASS with all three copies at 15 — the lockstep guard is what proves the
gateway allowlist, the core gate and the switch moved together. `probe-authz-seat` 17/17,
`probe-start-execution` 20/20, `probe-gateway-boundary` PASS, `probe-chat-pause-resume` 23/23.
Supervisor selftests 12/13 before and after. tmux session list byte-identical. NOT DEPLOYED at
filing (commit 4a032354 on `ignite/core-daemon`).

## ATTENTION
1. BOTH HALVES DEPLOY TOGETHER OR THE VERB IS BROKEN. The bridge forwards `pause-resume` as of 8b44d806; a daemon booted from a tree without 4a032354 answers `UNKNOWN_INTENT` and the owner is told the intent is unknown rather than that their goal was paused. Advancing one deploy without the other is the failure.
2. THE RESULT SHAPE IS THE CONTRACT AND `summarize()` IS ITS ONLY READER. Renaming `actions`/`refusals` or changing a `row` value daemon-side degrades the owner's line to the bridge's malformed-result refusal — loud, but a refusal for a verb that actually worked and wrote to the store.
3. A SLUG OUTSIDE THE ROSTER MUST STAY A TYPED `NOT_FOUND`, never an `ok:true` with empty actions. `summarize()` renders an empty result as "nothing to change", which an owner who mistyped a goal name reads as "it was already fine". The roster IS the refusal.
4. THE ROSTER IS THE REGISTER, NOT THE TREE. Globbing `.rbtv/goals/` would admit `_archive` and every scratch folder, and this list decides what an owner is told does not exist. `goals.csv` is what every creation route writes.
5. `_`-PREFIXED PACKAGES ARE REFUSED THREE TIMES AND THE ROSTER FILTER IS NOT THE ONE THAT FIRES. `BUS_NAME_RE` and `isSafeName` both require an alphanumeric first character, so a probe asserting `NOT_FOUND` for `_channel-master` would report a code path that never ran as covered — the roster filter keeps the LIST honest for its other readers, and that is what the probe asserts.
- Both halves deploy together: a daemon without 4a032354 answers UNKNOWN_INTENT to the bridge's pause-resume forward
