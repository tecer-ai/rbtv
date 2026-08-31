'use strict';

// ── THE MECHANICAL `pause {goal}` / `resume {goal}`, RUN DAEMON-SIDE (owner direction 2026-08-28,
// ~02:00Z + 02:12Z item (2), recorded in `role-action-program/decisions.md`) ─────────────────────
//
// THE GAP THIS CLOSES. `chat/index.js#main()` builds the bridge with NO ports —
// `buildBridge(config)` passes no `endingStore`, no `listSeats`, no `rearmCounters` — so the
// mechanical door parsed the verb, resolved the target, and then applied NOTHING and answered
// nothing (wave tests 8/9/10). The capability was real on both sides and unreachable in the
// middle: the bridge is a SEPARATE PROCESS walled off from `heart.db`, the attempt-counter ledger
// and every sibling require (`chat/probes/probe-chat-boundary.js`), and the build memory records a
// migration that reached through that wall being reverted whole
// (`20260824-i-open-asks-has-no-boundary-lega`). The 2026-08-24 ruling that minted the fourteenth
// intent (`start-execution`) deliberately declined the pause word — "pause stays store-side until
// the execution-lane reconcile gate converges onto the goal-state row". The owner reversed that
// deferral on 2026-08-28: mint the intent so the bridge's mechanical verbs act through the daemon.
//
// ── THE CONTRACT, VERBATIM (both seats of the fix implement it; it was fixed, not negotiated) ───
//
//   Intent name `pause-resume`. Payload, closed: `{ verb: 'pause' | 'resume', goal: <bare name,
//   BUS_NAME_RE at parse.js:109> }`; any other key → `VALIDATION_FAILED` (`rejectUnknownKeys`,
//   parse.js:171). Sender: `kind: 'bridge'` only (authz.js — mirror `:482-507` `start-execution`'s
//   predicate; the daemon's own status/CLI callers are NOT admitted: the console has
//   `rbtv goal pause`).
//   Result (`ok:true`): `{ verb, goal, applied: boolean, actions: [...], refusals: [{row, text,
//   seat?}] }` — EXACTLY the return shape of today's `chat/pause-resume.js#applyPause` (`:113-124`)
//   / `#applyResume` (`:130-206`), so the bridge's `summarize()` renders it unchanged.
//   Errors: slug not in the live-goal roster → `NOT_FOUND` (message names the slug; the bridge
//   turns it into the verbatim §4.5 NACK); unauthorized → `UNAUTHORIZED_SENDER`; shape →
//   `VALIDATION_FAILED`. Default timeout (store + ledger writes; no override).
//
// ── WHAT MOVED, AND WHY IT MOVED RATHER THAN BEING RE-IMPLEMENTED ───────────────────────────────
//
// The resume-semantics table [C-14, `spec-recovery` §4] and its refusal prose MOVED here from
// `chat/pause-resume.js:44-206` and are now the daemon's. The bridge half of this fix (8b44d806)
// deleted its copy in the same landing and the door there is a SENDER: `forwarder.forward(
// 'pause-resume', {verb, goal})` plus `summarize()`, which reads `actions`/`refusals` and nothing
// else. THERE IS EXACTLY ONE COPY OF THIS TABLE and it is this one — a diagnostic name or a lane
// refusal string re-appearing in `chat/` would put two processes in charge of one fact, which is
// precisely how the two pause records below diverged.
//
// Every port the bridge could only ever have INJECTED is a real handle here:
//   · the ending store — `bind(openEndingStoreFor(workspaceRoot))` (`state-store/open.js:59-61`);
//     see THE ENDING HOME below for why it is emphatically NOT the caller's `heartStore.db`;
//   · the goal's lane roster — `supervisor/seeding.js#readTaskforce`, the reader the lane itself
//     spends (`lane-watch.js:568`). Never a second `taskforce.csv` parser;
//   · the counter half — `supervisor/exhaustion.js#rearmScope({store, goal, event: 'resume'})`,
//     built by `fix-rearm-wiring` (5aa80168) and UNWIRED in production for exactly want of this
//     intent (that entry's ATTENTION-4: "THE RESUME HALF IS BUILT AND UNREACHABLE").
// Both supervisor modules are LAZY-required for `lane-watch.js`'s own stated reason: a module-level
// import here is a dependency every probe and every importer of the state store inherits, and
// `supervisor/lane-watch.js` <-> `supervisor/reconcile.js` is a require cycle at load time.
//
// ⚑ THE ROSTER IS `goals.csv`, NOT A GLOB OF THE GOALS TREE. `<workspaceRoot>/.rbtv/goals/goals.csv`
//   is the register every creation route writes; `coord/owed-answers.py:55-70 packages()` is the
//   precedent. A directory listing would admit `_archive`, a half-deleted folder and any scratch
//   directory somebody left behind — and the answer this list produces is a REFUSAL the owner
//   reads, so a roster that is merely plausible is worse than none. A row whose folder is gone is
//   dropped (the register outlives a deletion), and a `_`-prefixed name is excluded exactly as
//   `lane-watch.js:464` excludes it from the lane pass: those are system packages, not goals the
//   owner pauses.
//
// ⚑ PAUSE/RESUME NEVER RELEASES AN ASK [§4.2]. Neither verb writes `open_asks`. An owner who pauses
//   a goal that is waiting on a question is still owed that question's answer, and the ask must
//   still read `open` to every digest, status line and kill clock afterwards.
//
// ⚑ `chatUser` NAMES THE SLACK PRINCIPAL IN THE EVIDENCE TEXT ONLY (owner re-ruling D-4(a),
//   2026-08-30 ~18:1xZ). It is OPTIONAL, reported by the bridge (`chat/pause-resume.js`) via the
//   `chat_user` payload field, shape-checked at both gateway copies (parse.js, dispatch.js) before
//   it ever reaches here — this module trusts that check and does no authorization with the value;
//   `authz.canPauseResume` never sees it. `state-store/cli.js`'s console route (`rbtv goal pause`)
//   passes no `chatUser`, so its evidence text is unchanged.
//
// ⚑ ONE PAUSE RECORD. This executor is the ONLY writer of the goal word. The console's
//   `rbtv goal pause` / `resume` reach it through `state-store/cli.js --op pauseResume` (no `--db`);
//   Slack reaches it through the fifteenth intent. The `execution-lane` file is the lane word
//   (`daemon`/`console`) and is not a pause surface. A leftover `paused ` prefix from before this
//   retirement is consumed by `lane-watch.js#laneIsPaused` (port the row, strip the prefix) — this
//   module does not refuse a resume that meets one.
//
// ⚑ THE ENDING HOME IS THE FILE THE LANE GATE READS, NEVER THE CALLER'S LANE STORE. This executor
//   binds `openEndingStoreFor(workspaceRoot)` — spec-state-store §1.1's ONE ending store at
//   `<workspace>/.rbtv/runtime/ignite/heart.db`, the same resolution the READER performs
//   (`supervisor/ending-reads.js:41` `bind(openEndingStoreFor(root))`, reached from
//   `lane-watch.js#laneIsPaused`) and the same file family 8 of the envelope (297765d8) binds rw
//   into every caged seat. It was `bind(heartStore.db)` and that bound whichever store the CALLER
//   happened to hold: under the daemon `{data_root}/heart.db` (`StateDirectory=rbtv-ignite`), which
//   the lane gate never opens. MEASURED 2026-08-28 03:37Z: a Slack `pause channel-master-diag-test`
//   wrote `paused` into the daemon's private store while the workspace store read `null` before and
//   after, and five lane cadences journaled zero paused-skips — the owner's pause was INERT.
//   `bindEnding` is the reader's function and is not reused here for two reasons: it lives in
//   `supervisor/`, which this component may not require (supervisor requires state-store, not the
//   reverse), and it FALLS THROUGH to the lane store when the home cannot be opened — the fail-safe
//   direction for a READER ("nothing declared") and precisely the wrong file for a WRITER. There is
//   still ONE resolver: `paths.js#endingStorePath`, which both sides reach through.
//   A HOME THAT CANNOT BE OPENED THEREFORE THROWS, and it throws BEFORE any write: the caller
//   answers `INTERNAL` and nothing was applied. Writing somewhere else and reporting success is the
//   one outcome this verb may not produce.

const fs = require('node:fs');
const path = require('node:path');
const { bind, openEndingStoreFor } = require('..');

// A THIRD copy of the name shape, checked against the module that owns it — `start-execution.js`'s
// reason verbatim: these names arrive from an internet-facing component and become PATH SEGMENTS
// under `.rbtv/goals/`.
const { isSafeName } = require('../../chat/bus-ferry');

const VERBS = new Set(['pause', 'resume']);

// The diagnostics the resume-semantics table has a row for (spec-state-store's
// `LISTED_INCOMPLETE` keys — quoted, not imported, exactly as `chat/pause-resume.js:40-43` quotes
// them: a closed vocabulary read from the spec, not a handle into another tree).
const D_BLOCKED_ON_HUMAN = 'blocked-on-human';
const D_GATE_CAP = 'gate-re-plan cap';
const D_COUNTER_EXHAUSTION = 'attempt-counter exhaustion';
const NAMED_EXTERNAL_INPUT = 'named-external-input';

// The named re-arm event this verb IS (`spec-recovery` §5's closed list names "mechanical
// `resume {goal}` on a disarmed-counter lane"). Lane-scoped, so `rearmScope` is handed the goal.
const REARM_EVENT = 'resume';

// Authored refusal prose, carried over from `chat/pause-resume.js:47-54` unchanged (NOT
// spec-verbatim — §4.5's two NACKs answer an UNPARSED verb; these answer a verb that parsed and
// named a live goal whose halt `resume` deliberately does not lift).
function blockedOnHumanRefusal(seat, askIds) {
  const where = askIds.length ? ` Answer it in its thread: ${askIds.join(', ')}.` : '';
  return `resume does not lift ${seat}: it is halted waiting on an open ask, and only an authorized reply in that thread releases it.${where}`;
}

function gateCapRefusal(seat) {
  return `resume does not lift ${seat}: it stopped at the re-plan cap. Answer the gate decision-ask — resume does not open a third re-plan.`;
}

function goalsRootOf(workspaceRoot) {
  return path.join(workspaceRoot, '.rbtv', 'goals');
}

function goalDirOf(workspaceRoot, goal) {
  return path.join(goalsRootOf(workspaceRoot), String(goal));
}

// ── THE LIVE-GOAL ROSTER ────────────────────────────────────────────────────────────────────────
//
// The names the mechanical verb may target. A slug outside this list is the `NOT_FOUND` the bridge
// renders as the verbatim §4.5 NACK, so this function decides what an owner is told does not exist.
//
// The first field of a `goals.csv` row is the name and a name cannot contain a comma
// (`BUS_NAME_RE`), so splitting at the first comma is exact rather than a naive CSV read — and the
// result is validated against the name shape rather than trusted, because a malformed register
// must not put an arbitrary string into a path.
function liveGoals(workspaceRoot) {
  const goalsRoot = goalsRootOf(workspaceRoot);
  let text;
  try {
    text = fs.readFileSync(path.join(goalsRoot, 'goals.csv'), 'utf8');
  } catch {
    return [];
  }
  const names = [];
  for (const line of text.split(/\r?\n/).slice(1)) {
    const name = line.split(',')[0].trim();
    if (!name || name.startsWith('_')) continue;
    if (!isSafeName(name)) continue;
    if (names.includes(name)) continue;
    let stat;
    try { stat = fs.statSync(path.join(goalsRoot, name)); } catch { continue; }
    if (!stat.isDirectory()) continue;
    names.push(name);
  }
  return names;
}

// The goal's lanes, from the reader the lane pass itself spends. A goal with no taskforce (a
// half-born or console-lane goal) has no lanes to lift and resume applies the GOAL row only — the
// failure is reported, never thrown, exactly as the bridge's `seatsOf` reported it.
function seatsOf(goalDir, log) {
  try {
    const { readTaskforce } = require('../../supervisor/seeding');
    return (readTaskforce(goalDir) || []).map((r) => String(r.seat)).filter(Boolean);
  } catch (err) {
    log('warn', 'could not enumerate the goal\'s lanes — resume applies the goal row only', { error: err.message });
    return [];
  }
}

// The counter half's one call site (`supervisor/exhaustion.js#rearmScope`). A ledger that refuses
// must not cost the owner the rest of the table — the failure becomes a refusal the door posts,
// never an exception that eats the verb.
// `seat` narrows the sweep to one lane (`d-recovery-retry-scope`) — omitted, `rearmScope` sweeps
// every counter the goal owns, exactly as before this fix.
function rearmCounterRows(store, goal, countersFile, log, seat) {
  try {
    const { rearmScope } = require('../../supervisor/exhaustion');
    const out = rearmScope({
      store, goal, seat, event: REARM_EVENT,
    }, { countersFile });
    return { cleared: (out && Array.isArray(out.cleared)) ? out.cleared : [], error: null };
  } catch (err) {
    log('warn', 'the attempt-counter re-arm refused — resume\'s counter half did not happen', { error: err.message });
    return { cleared: [], error: err.message };
  }
}

// `pause {goal}` is the inverse of the paused-goal row ONLY (spec-recovery §4): flip
// `running` → `paused`. It does not disarm a lane and it does not open an ask.
function applyPause(store, goal, evidencePointer) {
  const before = store.getGoalState(goal);
  if (before && before.stored === 'paused') {
    return { applied: true, actions: [{ row: 'goal', change: 'already-paused', goal }], refusals: [] };
  }
  if (before && before.stored === 'finished') {
    return { applied: false, reason: 'finished', actions: [], refusals: [{ row: 'goal', text: `${goal} is finished — there is nothing to pause.` }] };
  }
  store.writeGoalWord({ goal, stored: 'paused', who_stamped: 'owner', evidence_pointer: evidencePointer('pause', goal) });
  return { applied: true, actions: [{ row: 'goal', change: 'running→paused', goal }], refusals: [] };
}

// `resume {goal}` — the resume-semantics table [C-14], EVERY MATCHING ROW. A goal may carry more
// than one halted kind at once, and each row is independent: the goal flipping to `running` does
// not re-arm a counter-exhausted lane, and a lane refusing to be lifted does not stop the goal word
// from flipping.
//
// `targetSeat` is the LANE-SCOPING parameter (owner ruling 2026-08-31, `d-recovery-retry-scope`):
// present, the sweep below touches ONLY that one `(goal, seat)` lane — the goal word (ROW 4) is
// left exactly as it stands, since that row is the GOAL's, not any lane's, and "re-arms ONLY that
// lane" is the ruling's own wording. Absent, every line below runs exactly as it did before this
// parameter existed — that goal-wide path is unchanged, byte for byte.
function applyResume(store, {
  goal, goalDir, evidencePointer, countersFile, log, seat: targetSeat = undefined,
}) {
  const actions = [];
  const refusals = [];

  // THE LANES ARE ENUMERATED BEFORE THE FIRST WRITE, and that ordering is the fix, not a tidy-up.
  // This was the loop head — `for (const seat of seatsOf(goalDir, (level, message, fields) =>
  // log(level, message, { seat, ...fields })))` — and the logger closure captured the loop variable
  // it was declared alongside. On a goal whose `taskforce.csv` cannot be read, `seatsOf` calls that
  // logger from its own catch, BEFORE `const seat` is initialised: `ReferenceError: Cannot access
  // 'seat' before initialization`, thrown out of a function whose whole contract is that a
  // missing taskforce is REPORTED, never thrown. It fired after row 4 below had already flipped the
  // goal to `running`, so the owner was told the resume was NOT applied while the store said it
  // was (daemon journal 2026-08-28 03:39:07Z). Any goal with no readable taskforce hit it on every
  // resume. Enumerating first removes the capture AND puts the only failure the lane roster can
  // produce ahead of every write, so that failure can no longer half-apply the verb. `log` is
  // passed plainly: an enumeration that failed has no seat to name, which is exactly what the
  // closure was pretending otherwise.
  // A named target skips the roster read entirely — the caller already named the one lane it
  // means, and a stale or unreadable `taskforce.csv` must not stand between the owner and the one
  // seat they explicitly targeted.
  const seats = targetSeat !== undefined ? [targetSeat] : seatsOf(goalDir, log);

  // ROW 1, THE COUNTER HALF. It runs FIRST because it is the half the reconcile loop reads: a lane
  // whose counter still stands at N is skipped on every pass no matter what the ending row says.
  const counter = rearmCounterRows(store, goal, countersFile, log, targetSeat);
  for (const row of counter.cleared) {
    actions.push({
      row: 'counter',
      seat: row.seat || row.subject,
      driver: row.driver,
      reason_class: row.reason_class,
      attempts: row.attempts,
      change: 'counter reset',
    });
  }
  if (counter.error) refusals.push({ row: 'counter', text: `${goal}: the attempt counters were NOT re-armed — ${counter.error}` });

  // ROW 4 — paused goal: flip `paused` → `running`. Armed eligible lanes may then launch; a
  // disarmed one stays disarmed until its own row (or another named re-arm) consumes the flag.
  // Skipped for a lane-scoped resume: the goal word is the GOAL's row, not the targeted lane's, and
  // touching it would resume every OTHER lane's launch eligibility too — exactly what "ONLY that
  // lane" forbids.
  if (targetSeat === undefined) {
    const goalState = store.getGoalState(goal);
    if (goalState && goalState.stored === 'paused') {
      store.writeGoalWord({ goal, stored: 'running', who_stamped: 'owner', evidence_pointer: evidencePointer('resume', goal) });
      actions.push({ row: 'goal', change: 'paused→running', goal });
    } else if (goalState && goalState.stored === 'finished') {
      refusals.push({ row: 'goal', text: `${goal} is finished — resume does not reopen a finished goal.` });
    }
  }

  for (const seat of seats) {
    let current = null;
    try { current = store.getCurrentEnding({ goal, seat }); } catch { current = null; }
    if (!current || current.ending !== 'incomplete' || Number(current.armed) !== 0) continue;
    const diagnostic = String(current.diagnostic || '');

    // ROW 2 — `incomplete: blocked-on-human`: NACK pointing at the open ask thread. Resume is NOT
    // a substitute for an authorized reply and does not reap the ask.
    if (diagnostic === D_BLOCKED_ON_HUMAN) {
      let askIds = [];
      try { askIds = (store.listOpenAsks({ goal, seat }) || []).map((a) => String(a.ask_id)); } catch { askIds = []; }
      refusals.push({ row: 'blocked-on-human', seat, text: blockedOnHumanRefusal(seat, askIds), asks: askIds });
      continue;
    }

    // ROW 3 — gate-cap stop (two failed D13s): NACK pointing at the gate decision-ask. Resume does
    // not open a third re-plan and does not flip the cap.
    if (diagnostic === D_GATE_CAP) {
      refusals.push({ row: 'gate-cap', seat, text: gateCapRefusal(seat) });
      continue;
    }

    // ROW 1 — disarmed `incomplete:` from attempt-counter exhaustion: re-arm that driver via the
    // NAMED RE-ARM EVENT the store already models. `fireNamedEvent` is the one writer of that flag
    // — the counter is CONSUMED here, and the relaunch budget (`recovery_relaunch_count`) is
    // deliberately left where it stands.
    if (diagnostic === D_COUNTER_EXHAUSTION || current.named_event === NAMED_EXTERNAL_INPUT) {
      try {
        store.fireNamedEvent({ goal, seat, named_event: NAMED_EXTERNAL_INPUT });
        actions.push({ row: 'counter-exhaustion', seat, change: 'disarmed→armed', named_event: NAMED_EXTERNAL_INPUT });
      } catch (err) {
        refusals.push({ row: 'counter-exhaustion', seat, text: `could not re-arm ${seat}: ${err.message}` });
      }
      continue;
    }
    // Any other disarmed diagnostic has NO row in the table — it is left exactly as it is, and said
    // so, rather than lifted by a rule nobody wrote.
    refusals.push({ row: 'no-row', seat, text: `resume has no rule for ${seat} (${diagnostic || 'disarmed'}) — left untouched.` });
  }

  return { applied: true, actions, refusals };
}

// ── THE ACT ─────────────────────────────────────────────────────────────────────────────────────
//
// `found:false` is the ONLY non-shape refusal and it is deliberately the roster's, not the
// filesystem's: the handler turns it into `NOT_FOUND` and the bridge turns THAT into the verbatim
// §4.5 mechanical NACK. `countersFile` is injectable ONLY for the probe, for the reason every
// injected port in this tree carries — a probe must be able to prove the table without writing the
// live attempt-counter ledger — never so production can point the ledger somewhere else.
// The caller hands NO store handle. It used to hand its own `heartStore` and that handle was the
// defect (see THE ENDING HOME above): the only store this verb may touch is derived from
// `workspaceRoot`, so there is no parameter through which the wrong one can arrive.
// `seat` (owner ruling 2026-08-31, `d-recovery-retry-scope`) is OPTIONAL and narrows `resume` to
// ONE `(goal, seat)` lane — absent, every path below is byte-for-byte what it was before this
// parameter existed. It is checked a THIRD time here against the module that owns the name shape
// (same reason the goal is: both become PATH SEGMENTS and directory-scan keys downstream), and is
// simply never read by `applyPause` — a pause has no per-lane effect, so a caller who slips it
// past the two gateway copies' verb=resume check gets a no-op, never a wrong write.
function pauseResume({
  workspaceRoot, verb, goal, seat = undefined, countersFile = undefined, chatUser = undefined, logger = null,
}) {
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, verb, goal, ...fields }); };
  if (!VERBS.has(String(verb))) return { found: false, reason: 'bad-verb', detail: `unknown mechanical verb ${verb}` };
  if (!isSafeName(goal)) return { found: false, reason: 'bad-name', detail: 'goal is not a bare safe name' };
  if (seat !== undefined && !isSafeName(seat)) return { found: false, reason: 'bad-name', detail: 'seat is not a bare safe name' };
  if (!liveGoals(workspaceRoot).includes(String(goal))) {
    return { found: false, reason: 'no-such-goal', detail: `${goal} is not a live goal` };
  }
  const goalDir = goalDirOf(workspaceRoot, goal);
  const store = bind(openEndingStoreFor(workspaceRoot));
  // `chatUser` absent (console route, or an older bridge during the deploy gap) keeps the
  // pre-existing text byte-for-byte — `state-store/cli.js`'s known "owner resume in chat" cost is
  // unchanged by this fix, deliberately (see its own comment on `runRootedOp`).
  const evidencePointer = (v, g) => (chatUser
    ? `owner ${v} in chat · by ${chatUser} (reported by bridge) · goal ${g}`
    : `owner ${v} in chat · goal ${g}`);
  const out = verb === 'pause'
    ? applyPause(store, goal, evidencePointer)
    : applyResume(store, {
      goal, goalDir, evidencePointer, countersFile, log, seat,
    });
  return {
    found: true, verb, goal, ...(seat !== undefined ? { seat } : {}), ...out,
  };
}

module.exports = {
  pauseResume,
  liveGoals,
  VERBS,
  REARM_EVENT,
  D_BLOCKED_ON_HUMAN,
  D_GATE_CAP,
  D_COUNTER_EXHAUSTION,
  NAMED_EXTERNAL_INPUT,
  blockedOnHumanRefusal,
  gateCapRefusal,
};
