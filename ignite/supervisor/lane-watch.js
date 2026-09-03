'use strict';

// engine/lane-watch.js — THE DAEMON LANE'S GOAL-PICKUP TRIGGER (owner ruling
// decisions.md#d-daemon-lane-button, which settles the follow-on `supervisor/seeding.js` named and
// deliberately did not invent).
//
// THE OWNER'S DESIGN, in his words: "build the button. it should be accessed by a CLI, which the
// channel master has access to. this CLI must change the file in goals that says if it is CURRENTLY
// being run by the daemon or by the console, so the daemon knows when to pick it up."
//
// So the trigger is a per-goal MARKER FILE the daemon watches, on the precedent of `execution-mode`
// (one word in a small file at the goal root, `chat/bus-ferry.js` § gate 2): the goal's
// LANE ASSIGNMENT. `rbtv-goal lane` writes it — works daemon-down, because a file is what a CLI can
// write when nothing is listening — and this pass reads it once a cadence.
//
// ⚠ ABSENT MEANS `console`, AND THAT CHOICE IS FAIL-CLOSED ON PURPOSE. Every goal folder already on
// disk predates this build and carries no assignment; if absence meant `daemon`, the first tick
// after deploy would adopt every one of them at once. So the daemon picks up ONLY goals EXPLICITLY
// assigned to it — an unreadable file, a junk word and a missing file are ONE answer (`console`),
// exactly as `execution-mode` treats everything that is not `interactive`. "Assigned to the console"
// and "assigned to nobody" are deliberately not distinguished: neither is the daemon's business, and
// a third state would be a state nothing reads.
//
// ⚠ THE FILE IS ONE WORD. `daemon` or `console`, and nothing else — owner ruling
// `#d-abolish-profile-names` sub-ruling 3, 2026-08-12. It used to carry an optional SECOND token
// naming a fallback launch profile, which existed for exactly one reason: `launch-agent`
// structurally required a `profile` argument. That requirement is gone (`supervisor/seeding.js`
// § seedTaskforce), so the token has nothing left to fill, and a marker that can name what a seat
// runs on is a marker that can contradict the seat's own cast.
//
// ⚠ A TWO-TOKEN MARKER IS A LEGACY MARKER AND READS `console`, LOUDLY. Fail-closed is the rule
// here (see the ⚠ above), so a marker this grammar cannot parse must not be adopted — but a goal
// silently demoted to the console is precisely the "quietly stopped" failure this pass exists to
// avoid, so `readLane` reports `legacy: true` and the loop shouts the one-line fix once.
//
// A `daemon` marker on a goal that carries an UNCAST seat is not seeded, and that refusal is now
// the ruling rather than a shortage: "any workflow reaching a taskforce MUST be cast first; an
// uncast seat is a NAMED refusal at materialize/lane time — never a fallback." The warning names
// the seats and the command that casts them.
//
// WHAT THIS PASS IS NOT: a second seeding implementation. It decides WHICH goals, and calls
// `engine.seedGoal` for each — the one seam (PRIN-11).

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { RUN_LOCK, runnerAlive, heldSeatPredicate } = require('../operator/attached-execution');
// The seat's declared autonomous arm, read through the chat bridge's OWN reader — the same module
// `heldSeatPredicate` reads both gates from. A second parser of that frontmatter is a lane that
// disagrees with the ferry about what a seat declared (7.626 criterion 2).
const { seatFallback } = require('../chat/bus-ferry');
// WHICH SEATS ARE NOT CAST — the ONE predicate every door refuses on. `rbtv run` and
// `rbtv-goal lane` ask the same function, so this pass and the CLI that writes the marker can
// never disagree about which goals may be assigned to the daemon.
const { uncastSeats } = require('./seeding');
const { maybeReconcile, loadSessions } = require('./reconcile');
const { finishEvent, abandonedSeats } = require('./owed-from-endings');
const { bindEnding, goalNameOf } = require('./ending-reads');
// THE ROOM: the one detached-session opener (shared with the boot cockpit) and the one room
// predicate. Neither is re-implemented here — see `openGoalRoom` below.
const { composeDetachedSession } = require('./spawn/tmux');
const { deriveLease } = require('../runtime/lease/lease');

const LANE_FILE = 'execution-lane';
const DAEMON = 'daemon';
const CONSOLE = 'console';

// The lane assignment, read with the same tolerance `execution-mode` is read with: trimmed,
// case-insensitive, and everything that is not the positive word is the conservative default.
//
// ⚠ ONE WORD, WHOLE. The whole trimmed text must BE the lane word — `daemon claude-fable` is not
// `daemon`, it is a marker written under the retired grammar, and it resolves `console` under the
// fail-closed rule above. It is reported as `legacy` so the caller can say so instead of leaving
// the goal to look like one somebody parked deliberately. Its `python` twin is
// `operator/goals-tree/tool/goal_cli.py#read_lane`; the two change together, always (DEC-1).
//
// ⚑ A leftover `paused ` prefix (retired writer) still resolves `console` here with no special
// case: the whole text is not `daemon`. Pause itself is the goal-state row, not this file.
function readLane(goalFolder) {
  let raw;
  try {
    raw = fs.readFileSync(path.join(goalFolder, LANE_FILE), 'utf8');
  } catch {
    return { lane: CONSOLE, present: false, legacy: false, raw: '' };
  }
  const text = raw.trim();
  const word = text.toLowerCase();
  if (word === DAEMON) return { lane: DAEMON, present: true, legacy: false, raw: text };
  const legacy = text.split(/\s+/)[0].toLowerCase() === DAEMON;
  return { lane: CONSOLE, present: true, legacy, raw: text };
}

// IS THE GOAL PAUSED — the JS twin of `goal_cli.py#_goal_is_paused` (DEC-1). ONE record: the
// goal-state row (`stored === 'paused'`). The `execution-lane` file is the lane word only.
//
// ── ONE PAUSE RECORD (owner ruling D-1 (a), 2026-08-30) ───────────────────────────────────────
//
// The console used to stash a `paused ` prefix in the lane file; Slack wrote the row. Either
// surface could hold the gate, so a goal paused one way and resumed the other stayed paused.
// The store row is now the only truth. Console pause/resume write the row through the same
// executor (`heart/pause-resume.js`) the intent uses.
//
// A leftover `paused ` prefix is NOT a second writer. It is consumed once: if the store has no
// word yet, port `paused` into the row then strip the prefix; if the store already has a word,
// the leftover is stale — strip it and believe the row. Never strip a prefix that is the only
// pause evidence: a write that did not land keeps the prefix and this function still returns
// true. ABSENT OR UNREADABLE IS NOT PAUSED.
//
// ⚠ `isGoalPaused` STILL CANNOT CARRY THIS, because it flattens "running" and "no row" into one
// `false`. A leftover prefix with no row is paused; that predicate would miss it. The row is
// read directly.
function laneIsPaused(goalFolder, heartStore) {
  let row = null;
  try {
    const { bindEnding, goalNameOf } = require('./ending-reads');
    const api = bindEnding(heartStore, goalFolder);
    if (api && typeof api.getGoalState === 'function') {
      row = api.getGoalState(goalNameOf(goalFolder));
    }
  } catch { /* store unreadable — leftover prefix still answers */ }

  const legacy = legacyPausePrefix(goalFolder);
  if (row && row.stored === 'paused') {
    if (legacy) {
      try { stripLegacyPausePrefix(goalFolder, legacy.rest); } catch { /* prefix is noise */ }
    }
    return true;
  }
  if (!legacy) return false;
  if (!row || !row.stored) {
    let wrote = false;
    try {
      const { bindEnding, workspaceRootOf, goalNameOf } = require('./ending-reads');
      const { bind, openEndingStoreFor } = require('../state-store');
      const root = workspaceRootOf(goalFolder);
      const api = root ? bind(openEndingStoreFor(root)) : bindEnding(heartStore, goalFolder);
      if (api && typeof api.writeGoalWord === 'function') {
        api.writeGoalWord({
          goal: goalNameOf(goalFolder), stored: 'paused', who_stamped: 'owner',
          evidence_pointer: 'legacy execution-lane paused prefix',
        });
        wrote = true;
      }
    } catch { wrote = false; }
    if (wrote) {
      try { stripLegacyPausePrefix(goalFolder, legacy.rest); } catch { /* row holds */ }
    }
    return true;
  }
  try { stripLegacyPausePrefix(goalFolder, legacy.rest); } catch { /* stale prefix */ }
  return false;
}

// IS THE GOAL CLOSED (`d-goal-closed-word`, `redesign-continue-1`) — the owner's `close` reply to
// the close-or-keep ask (`d-recovery-last-lane-asks`). Same shape as `laneIsPaused`'s row read,
// minus the legacy-prefix migration: `closed` has no legacy surface, so ONE record answers it, the
// goal-state row (`stored === 'closed'`). TERMINAL, unlike paused — there is no resume path.
function laneIsClosed(goalFolder, heartStore) {
  try {
    const { bindEnding, goalNameOf } = require('./ending-reads');
    const api = bindEnding(heartStore, goalFolder);
    if (!api || typeof api.getGoalState !== 'function') return false;
    const row = api.getGoalState(goalNameOf(goalFolder));
    return Boolean(row && row.stored === 'closed');
  } catch {
    return false;
  }
}

function legacyPausePrefix(goalFolder) {
  let raw;
  try { raw = fs.readFileSync(path.join(goalFolder, LANE_FILE), 'utf8'); } catch { return null; }
  const trimmed = raw.trim();
  if (!trimmed || trimmed.split(/\s+/)[0] !== 'paused') return null;
  return { rest: trimmed.split(/\s+/).slice(1).join(' ') };
}

function stripLegacyPausePrefix(goalFolder, rest) {
  const text = `${rest || 'console'}\n`;
  const tmp = path.join(goalFolder, `${LANE_FILE}.tmp`);
  fs.writeFileSync(tmp, text);
  fs.renameSync(tmp, path.join(goalFolder, LANE_FILE));
}

// ── THE REPEATED-FAILURE MEMO ─────────────────────────────────────────────────────────────────
//
// A goal that cannot be seeded — an uncast seat, a broken taskforce, a legacy lane marker —
// is re-read every cadence, and the first version of this pass logged it every cadence too: at a
// 10 s tick that is ~8,600 lines a day, per goal, for a condition that will not change until a
// human edits the marker. So the loud line fires ONCE PER (goal, marker content): the memo is
// keyed on the marker's exact text, so the moment somebody FIXES the marker the goal is loud
// again — which is the property that matters, because "quiet" must never mean "forgotten".
// Repeats drop to `debug`, and a goal that seeds successfully forgets its failure.
//
// ponytail: an in-memory Map that grows by one small entry per failing goal and clears on success
// or on a daemon restart. If the goals tree ever reaches a size where that is not free, key it on
// a bounded LRU — but the entries are two short strings and the tree is tens of goals.
const failedOn = new Map();

function shouldShout(goalFolder, marker) {
  if (failedOn.get(goalFolder) === marker) return false;
  failedOn.set(goalFolder, marker);
  return true;
}

// ── THE GOAL'S SLACK CHANNEL, ON THE DAEMON LANE (task 7.789) ─────────────────────────────────
//
// C3 (`runtime/ticker/goal-channel-start.js`) causes an interactive goal's channel to exist at its
// run start, and until now it had ONE caller: the queued `start-workflow` dispatch branch in
// `ticker.js`. The daemon lane starts a goal WITHOUT such a row — this pass adopts it off its
// `execution-lane` marker and calls `seedGoal` directly — so a daemon-lane goal was born with NO
// channel. Measured on `forge-reference-seat-id-naming`: journalctl over its entire 2026-08-11
// seeding carries zero `goal-channel-cli` lines. That matters because `chat/bus-ferry.js`
// gates owner messaging behind an existing channel, so every to-owner message from that goal's
// seats had nowhere to land.
//
// ⚠ THE DECISION IS NOT RE-MADE HERE. This calls `engine.ticker.ensureGoalChannel`, which calls
// `channelEnsureDecision` — the same function the queue lane's caller reaches, with the same body
// deciding which kind gets a channel and what the invocation is. Two callers, one decision.
//
// ⚠ ONCE PER GOAL, NOT ONCE PER TICK, AND THE DEDUPE IS OURS TO OWN. `goal-channel-start.js` says
// re-entry is free — and it is, at the BRIDGE: `ensureChannel` is idempotent and adopts an
// existing channel. What is NOT free is the act between here and there: every call forks a
// systemd unit running the bridge CLI, and this pass re-adopts an assigned goal EVERY cadence. At
// 10 s that is ~8,600 transient units a day, per goal, to re-learn a channel id that did not
// change. So it fires on the FIRST pass that adopts each goal, keyed on the goal folder.
//
// ponytail: the memo is daemon-lifetime, and a FAILED ensure is memoized too — a restart re-arms
// it. That is deliberate and it is the conservative direction: `channel-ensure-failed` here means
// a carrier or credential fault, which does not clear on its own, and retrying it every cadence
// would spawn the doomed unit ~8,600 times a day instead of once. If a transient failure mode is
// ever observed, clear the key on `channel-ensure-failed` and bound the retries — do not simply
// stop memoizing.
const channelEnsured = new Set();

function ensureGoalChannelOnce({ goal, goalFolder, engine, say }) {
  if (channelEnsured.has(goalFolder)) return false;
  const perform = engine && engine.ticker && engine.ticker.ensureGoalChannel;
  // The ATTACHED lane and the probes build an engine with no ticker surface. A goal channel is a
  // daemon-lane act, so absence here is the ordinary case and not a fault: nothing is said.
  if (typeof perform !== 'function') return false;
  channelEnsured.add(goalFolder);
  // Fire and forget, exactly as the queue lane does: the carriers resolve when the child is
  // launched, never when Slack answers, and this pass runs immediately before a tick.
  //
  // ⚠ THE CALL IS SYNCHRONOUS; ONLY ITS RESULT IS AWAITED. Deferring the call itself into a
  // microtask would hand the performer a `goalFolder` this pass has already moved past, and would
  // make "was it called?" unobservable to any synchronous caller — including the probe arm that
  // proves the once-per-goal memo. A synchronous throw is caught by the same handler.
  let pending;
  try {
    pending = perform({ goal });
  } catch (err) {
    say('warn', 'lane watch: goal-channel ensure threw — the goal is seeded, its channel is not ensured',
      { goal, error: err && err.message });
    return true;
  }
  Promise.resolve(pending)
    .then((actions) => {
      for (const a of actions || []) {
        say(a.action === 'channel-ensure-failed' ? 'warn' : 'info',
          `lane watch: goal channel — ${a.action}`, { goal, ...a });
      }
    })
    .catch((err) => say('warn',
      'lane watch: goal-channel ensure threw — the goal is seeded, its channel is not ensured',
      { goal, error: err && err.message }));
  return true;
}

// A LIVE console run owns this goal — do not even seed against it.
//
// The open-row holds in the execution record already stop the daemon from dispatching a seat the
// console lane is running (`seeding.js` § `foreign`), so this is belt AND braces, deliberately: the
// holds work per SEAT and one cadence behind, while the lock answers "somebody is attached to this
// goal RIGHT NOW" with no lag at all. The read is the lock's own liveness test (`runnerAlive`: pid
// plus start time, so a recycled pid cannot brick a goal) rather than mere file existence — a
// crashed runner's leftover lock must not park the goal forever.
//
// ⚠ THE LOCK IS READ, NEVER TAKEN AND NEVER CLEARED. It is the ATTACHED lane's interlock (one
// attached runner per goal); the daemon is not an attached runner, and a stale one is the next
// `rbtv run`'s to clear, not this pass's.
function consoleRunIsLive(goalFolder) {
  let held;
  try {
    held = fs.readFileSync(path.join(goalFolder, RUN_LOCK), 'utf8');
  } catch {
    return false;
  }
  const [pidRaw, startRaw] = held.trim().split(/\s+/);
  return runnerAlive(Number(pidRaw), startRaw);
}

// ── THE FROZEN INVARIANT'S FACTS, COLLECTED WHERE THEY ARE ALREADY KNOWN [T1-R15, C-5] ────────
//
// `observation/frozen.js` is a READER of scheduler facts and refuses to derive any of them itself —
// every one is HANDED IN by the caller that already computes it. This pass IS that caller: it runs
// once a cadence over exactly the goals the daemon drives, and by the time a goal is seeded it
// already knows the goal-state row, the pause, what was enqueued and what the provider lanes say.
// Collecting the facts here costs one store read per goal; collecting them anywhere else would mean
// deriving them a second time, which is how two surfaces come to disagree about one goal.
//
// ⚠ ONLY GOALS THIS PASS ACTUALLY SEEDED ARE OBSERVED. A goal it stepped over — console lane, no
// taskforce, unreadable casts, a live console run — is NOT reported as un-frozen and NOT reported
// as frozen: it is not observed at all. Frozen counts nothing in by exception, so an unobserved
// goal can only make the invariant quieter, and the pass already says out loud why it skipped.
//
// ⚠ `eligible_launch` IS THIS PASS'S OWN ANSWER. `pickup.enqueued` is what the seed just queued;
// a goal that queued work is a goal the scheduler has something to do for, which is the exact arm
// [T1-R15] names. Nothing here re-asks `deriveOwed` — the seed already did.
//
// ⚠ NOTHING IN HERE THROWS. A fact read that fails yields NO observation for that goal rather than
// a half-composed one: `frozen.js` refuses an observation missing a field (the observing code is
// the bug), and a pass that could die collecting evidence would take the daemon's goal pickup with
// it.
function frozenFactsFor({ goal, goalFolder, engine, pickup, seats = [], lanesFile = undefined, now = undefined }) {
  const heartStore = engine && engine.heartStore;
  let goalState = null;
  let openAsk = false;
  try {
    const { bindEnding } = require('./ending-reads');
    const api = bindEnding(heartStore, goalFolder);
    if (!api || typeof api.getGoalState !== 'function') return null;
    const row = api.getGoalState(goal);
    // NO ROW IS NOT `running`. A goal the store has never recorded is one nothing can claim to know
    // is stuck; it is reported as its own word so the predicate's first arm answers it honestly.
    goalState = (row && row.stored) || 'unrecorded';
    openAsk = typeof api.countOpenAsks === 'function' ? api.countOpenAsks(goal) > 0 : false;
  } catch {
    return null;
  }

  // The two [C-5] exclusions, asked of every seat on the goal: ONE lane waiting out a provider
  // backoff (or skipped pending a reroute) is enough to make this goal's quiet deliberate.
  let backoffWaiting = false;
  let reroutePending = false;
  try {
    const providerLanes = require('./provider-lanes');
    for (const seat of seats) {
      if (!seat) continue;
      const lane = providerLanes.laneFacts({ goal, seat }, { lanesFile, now });
      if (lane.provider_backoff_waiting) backoffWaiting = true;
      if (lane.reroute_pending) reroutePending = true;
      if (backoffWaiting && reroutePending) break;
    }
  } catch { /* no lane history is "no exclusion", never a death */ }

  return {
    goal_id: goal,
    goal_state: goalState,
    paused: laneIsPaused(goalFolder, heartStore),
    eligible_launch: (pickup && Array.isArray(pickup.enqueued) ? pickup.enqueued.length : 0) > 0,
    open_ask: openAsk,
    provider_backoff_waiting: backoffWaiting,
    reroute_pending: reroutePending,
    // A path a human can open: the goal folder carries the taskforce, the seats and the
    // coordination bus that answer "what was this goal doing when it stopped".
    evidence_pointer: goalFolder,
  };
}

// ── THE DAEMON LANE OPENS THE GOAL'S FIRST ROOM ───────────────────────────────────────────────
//
// WHAT WAS MISSING, and it is a MISSING HALF rather than a wrong line. `seeding.js#seedGoal`
// refuses every launch on a goal whose room is down (`deriveLease().live`, the D9 seed gate), and
// until now NO daemon-side path ever opened a FIRST one: `reconcile.js` REBUILDS a room only when
// `deriveOwed` says work is owed, which for a goal that never launched a seat is false by
// construction (its `sessions.csv` does not exist, so the ledger half has no seats and the graph
// half is not handed in); the boot cockpit opens only `rbtv-cockpit`; and 7.778 deleted
// `workflow_launcher.py` — the code that opened the room and launched the entry seat — writing
// "WHAT OPENS THE ENTRY SEAT NOW: the LANE" (`operator/goal-creation-request/tool/
// goal_creation_request.py`) without giving the lane a room-opener. Measured 2026-08-27 on
// `scratch-cli-reach-report`: born with a 7-row taskforce and 7 seat folders, then journalled
// "goal NOT seeded this pass … has NO live room … Start the room (`rbtv run`)" every 10 s,
// forever. The lane's own contract is the opposite (`meta/master/references/master-scaffold-flow.md`:
// "the daemon picks the goal up by itself and runs its seats unattended"; owner ruling OQ-22:
// "No queue — the lane advances the goal"), so the lane owes the room.
//
// WHY HERE AND NOT IN `seeding.js`. `seedGoal` is deliberately lane-agnostic — its own header:
// "It is deliberately a FUNCTION AND NOT A TRIGGER" — and the ATTACHED lane and the probes call
// it too. A room-opener there would open rooms for lanes that own their own. This pass IS the
// daemon lane, and by its call site every lane-shaped guard has already been established: the
// goal is `daemon`-assigned (a paused marker flattens to `console` and never reaches here), it
// carries a `taskforce.csv`, and no console run is live on it.
//
// WHAT THIS FUNCTION STILL OWES, and each guard is a state a room must NOT be opened in:
//   1. NO LAUNCHABLE ROW — every seat is unbuilt or uncast. A room for a goal that cannot launch
//      anything is a room nothing will ever use.
//   2. AN UNREADABLE LEASE — refused on ignorance, exactly as `seedGoal` refuses: "tmux is
//      unreadable" is not "there is no room".
//   3. A LIVE ROOM — the idempotence. This never opens a second room; a goal whose room exists is
//      left exactly as it is, whoever opened it.
//   4. NOT A FIRST SEEDING — the goal has session rows, so seats HAVE run in a room here and the
//      room's absence means it was closed after the fact (an owner closing it is the ordinary
//      case). That is the OWED path's subject: `reconcile.js` rebuilds it under the leader chair
//      when work is owed, and re-opening it from here would race that path and would re-open a
//      room the owner deliberately closed. `sessions.csv` is the record `classifyOwed` itself
//      reads to decide a goal has seats with a history.
//
// FAIL-SOFT, like every other act in this pass: a refusing tmux is one `warn` and a goal left for
// the next cadence, never a dead tick.
const ROOM_SCOPE_PREFIX = 'rbtv-tmux-room-';

function defaultRunTmux(argv) {
  return execFileSync(argv[0], argv.slice(1), { encoding: 'utf8', timeout: 15000 }).trim();
}

function openGoalRoom({
  goal, goalFolder, workspaceRoot, rows, laneSkips,
  readLease = deriveLease, runTmux = defaultRunTmux, say = () => {},
}) {
  const launchable = (rows || [])
    .map((r) => (r.seat || '').trim())
    .filter((seat) => seat && !(laneSkips && laneSkips.has(seat)));
  if (!launchable.length) return { opened: false, reason: 'no-launchable-row' };

  let lease;
  try {
    lease = readLease({ workspaceRoot, goal });
  } catch (err) {
    return { opened: false, reason: 'lease-unreadable', error: err.message };
  }
  if (!lease || !lease.ok) {
    return { opened: false, reason: 'lease-unreadable', error: lease && lease.reason };
  }
  if (lease.live) return { opened: false, reason: 'room-already-live' };

  if (loadSessions(goalFolder).length) {
    return { opened: false, reason: 'not-a-first-seeding' };
  }

  const scopeUnit = `${ROOM_SCOPE_PREFIX}${randomUUID()}`;
  let argv;
  try {
    // NO window name: a room the daemon opened must be indistinguishable from one a human opened
    // with `tmux new-session -s <goal>`, and the cwd is the goal folder — the package
    // (`lease.js#packageDirForRoom` is the identity), which is what `recover-room.py` uses too.
    argv = composeDetachedSession({ sessionName: goal, cwd: goalFolder, scopeUnit });
  } catch (err) {
    say('warn', 'lane watch: this daemon-lane goal\'s name cannot be a tmux session name, so no '
      + 'room can be opened for it and it can never be seeded', { goal, error: err.message });
    return { opened: false, reason: 'name-refused', error: err.message };
  }

  let pane;
  try {
    pane = runTmux(argv);
  } catch (err) {
    say('warn', 'lane watch: FAILED to open this daemon-lane goal\'s room — nothing is seeded this '
      + 'pass and the next cadence retries', { goal, scopeUnit, error: err.message });
    return { opened: false, reason: 'open-failed', error: err.message };
  }

  say('info', 'room opened by the daemon lane (first seeding)', {
    goal, goalFolder, room: goal, pane, scopeUnit, launchable,
  });
  return { opened: true, reason: 'opened', room: goal, pane, scopeUnit };
}

// ONE PASS over the goals tree. Called from the daemon's loop, immediately before each tick, so a
// seat seeded by this pass is dispatched by the tick that follows it rather than a cadence later.
//
// NOTHING HERE IS FATAL. A goal with a broken taskforce, an unreadable folder or a failing seed is
// logged and skipped; the daemon serves every other goal from the same loop, and taking the tick
// down over one goal folder is the one behaviour a watch pass must not have. The next pass retries.
//
// `isHeld` IS DELIBERATELY NOT PASSED, and 7.626 CONFIRMED that rather than changing it. `isHeld`
// is the ATTACHED lane's "carry this seat in the terminal instead" seam; there is no terminal here
// and the ruling (`d-s19-fallback-rides-goal-channels`) is that there need not be one — the goal's
// channel is the owner surface, so a human-interactive seat is DISPATCHED and its declared
// `fallback:` executes at the ferry. Holding it here would park it forever with nobody to release
// it, and would also stop it ASKING — which is the one thing every arm needs it to do.
//
// ponytail: O(goals) `readdir` + one small read per goal per cadence, and `engine.seedGoal`
// publishes the record once per adopted goal. At tens of goals and a 10 s cadence that is noise;
// if the tree ever reaches thousands, watch mtimes instead of re-reading every pass.
// `readLease` is the D9 goal-live check's injection point, forwarded verbatim to
// `engine.seedGoal` — production passes nothing and seeding reads the real lease.
async function runLaneWatch({
  goalsRoot, engine, logger = null, readLease = undefined, lanesFile = undefined,
  // The room opener's executor seam, `ensureCockpit`'s own pattern. Production passes nothing.
  runTmux = undefined,
}) {
  const say = (level, message, extra = {}) => { if (logger) logger({ level, message, ...extra }); };
  // `<workspace>/.rbtv/goals` — the one resolution the lease needs, computed once per pass.
  const workspaceRoot = path.resolve(goalsRoot, '..', '..');
  const adopted = [];
  const skipped = [];
  // The rooms this pass OPENED. A goal here is not skipped — it is a goal whose first room the
  // lane had to create before it could be seeded at all.
  const roomsOpened = [];
  // One observation per goal this pass seeded, for `runtime/frozen-pass.js`. Collected, never acted
  // on here: this pass seeds goals, and an alarm is somebody else's act.
  const frozenFacts = [];

  let entries;
  try {
    entries = fs.readdirSync(goalsRoot, { withFileTypes: true });
  } catch {
    // No goals tree on this workspace. Not an error and not worth a line every cadence.
    return { adopted, skipped, roomsOpened };
  }

  for (const entry of entries) {
    // ⚠ ONE EVENT-LOOP TURN, AT THE HEAD OF EVERY GOAL, AND IT IS THE WHOLE REASON THIS FUNCTION IS
    // `async`. Everything this loop then does is BLOCKING — `maybeReconcile` and `engine.seedGoal`
    // spend `execFileSync(python …)` at a measured ~2.4 s per seeded goal (diag 2026-08-28, §2.3) —
    // and the gateway's HTTP listener (`runtime/gateway/gateway.js`) lives on this same single
    // loop. Without this yield the pass held the loop for a median 7.9 s and up to 12.6 s of every
    // 10 s cadence with three seeded goals, so `inspect daemon` could not be answered at all and
    // the watchdog's 10 s cutoff landed inside that spread: 30 timeouts, 29 owner DMs, never a
    // dead daemon (diag §1.1, §1.5, §2.2). A log line does NOT yield — that is why the journal
    // looked alive throughout.
    //
    // `setImmediate` and not `setTimeout(0)`: it resolves in the check phase, i.e. AFTER the poll
    // phase has drained pending socket reads, which is exactly the work a waiting gateway request
    // is sitting in. The worst contiguous block therefore drops from the whole sweep to ONE goal.
    //
    // ⚠ THE PRICE, ACCEPTED: a gateway request can now land between two goals, on a half-done
    // pass. The daemon's cadence carries a pass-already-running guard (`runtime/index.js`) so a
    // pass never overlaps a pass; nothing serialises a pass against a REQUEST, and no lock is
    // wanted here — every write this loop makes is per-goal and idempotent on the next cadence.
    // Proof: `probes/probe-lane-watch-yield.js`.
    await new Promise(setImmediate);
    if (!entry.isDirectory()) continue;
    const goal = entry.name;
    const goalFolder = path.join(goalsRoot, goal);
    const { lane, legacy, raw } = readLane(goalFolder);

    // D1 watcher: honour pause via the ONE reader (the goal-state row). CONTINUE —
    // seeding used to skip only because a `paused ` prefix made readLane return
    // console; the file is no longer a pause surface, so without this continue a
    // store-paused daemon-lane goal would still be adopted.
    if (!goal.startsWith('_') && laneIsPaused(goalFolder, engine && engine.heartStore)) {
      maybeReconcile({ goal, goalFolder, engine, say });
      skipped.push({ goal, reason: 'paused' });
      continue;
    }

    if (!goal.startsWith('_') && finishEvent(goalFolder)) {
      maybeReconcile({ goal, goalFolder, engine, say });
      skipped.push({ goal, reason: 'finished' });
      continue;
    }

    // D1 watcher, `closed` sibling: honour the owner's close-or-keep `close` reply via the ONE
    // reader (the goal-state row) — same shape as the `paused` continue above, TERMINAL rather
    // than resumable.
    if (!goal.startsWith('_') && laneIsClosed(goalFolder, engine && engine.heartStore)) {
      maybeReconcile({ goal, goalFolder, engine, say });
      skipped.push({ goal, reason: 'closed' });
      continue;
    }

    if (lane !== DAEMON) {
      // A LEGACY two-token marker is reported, not silently treated as a console assignment: it
      // was written to say `daemon` and this grammar cannot honour it, which is a state only a
      // human can clear. Once per marker text, like every other loud line in this pass.
      if (legacy) {
        skipped.push({ goal, reason: 'legacy-two-token-marker', raw });
        say(shouldShout(goalFolder, raw) ? 'warn' : 'debug',
          'lane watch: this goal\'s `execution-lane` carries the RETIRED two-token grammar '
          + '(`daemon <profile-name>`) — the second token was the fallback launch profile, abolished by '
          + '`#d-abolish-profile-names`. The marker does not parse as `daemon`, so the goal reads CONSOLE '
          + 'and is NOT being picked up.', {
            goal,
            raw,
            fix: `rbtv goal lane ${goal} --set daemon`,
          });
        // ⚠ THE MEMO IS **NOT** CLEARED FOR A LEGACY MARKER, and that asymmetry is the whole
        // point of the memo. A goal genuinely handed back to the console is a resolved state and
        // starts clean if it returns; a legacy marker is an UNRESOLVED one that will be re-read
        // every cadence until a human rewrites it — clearing here would re-arm the loud line on
        // every pass, which at a 10 s tick is ~8,600 identical warnings a day.
        continue;
      }
      skipped.push({ goal, reason: 'not-assigned-to-the-daemon' });
      failedOn.delete(goalFolder);      // a goal handed back to the console starts clean if it returns
      continue;
    }

    if (!fs.existsSync(path.join(goalFolder, 'taskforce.csv'))) {
      // ── B12(ii) · A DAEMON GOAL WITH NO TASKFORCE IS STUCK, AND IT IS SAID OUT LOUD ─────────
      //
      // WHAT WAS HERE: `// Assigned but not yet materialized — a normal state between
      // `rbtv-goal scaffold` and `rbtv-goal materialize`, not a fault. Quiet.` and a bare
      // `continue`. It was wrong on both halves.
      //
      // NOT A TRANSIENT. Nothing in this pass, and nothing the daemon runs, ever materializes a
      // goal — `taskforce.csv` has exactly one writer, `scaffold-seats`
      // (`planning/materialize-seats.py`), which is invoked by the CREATION route and by nobody
      // else. So this is not a state the goal moves out of on its own: once here, it is here
      // until a human or a master runs that second act. Measured on
      // `cli-tools-reachability-report`, created straight off `rbtv goal scaffold --lane daemon`
      // on 2026-08-26 — 0 daemon journal mentions, ever, because of this `continue`.
      //
      // NOT QUIET. The memo above says it in this file's own words: "'quiet' must never mean
      // 'forgotten'". `shouldShout` is keyed on the lane marker text, so this shouts ONCE per
      // (goal, marker) and drops to `debug` after — the same bound every other loud line here
      // has, and it re-arms the moment the marker changes or the goal seeds successfully.
      //
      // THE CAUSE IS FIXED AT THE CREATION VERB, not here [B12(i)]: `rbtv goal scaffold` now
      // refuses to mint a daemon-lane goal it is not going to materialize. This line is the
      // second half — the goals that reached this state before that gate existed are named
      // instead of vanishing.
      skipped.push({ goal, reason: 'no-taskforce-yet' });
      say(shouldShout(goalFolder, raw) ? 'warn' : 'debug',
        'lane watch: this goal is assigned to the DAEMON but has NO `taskforce.csv` — it has no '
        + 'seats, so nothing is seeded and the goal is skipped on EVERY cadence. This does not '
        + 'clear itself: the taskforce has one writer (`scaffold-seats`), reached only by the '
        + 'creation route, so the goal stands here until that act is run against it.', {
          goal,
          missing: path.join(goalFolder, 'taskforce.csv'),
          // NOT `rbtv goal materialize` — that verb REFUSES when `taskforce.csv` is absent or
          // empty, which is precisely this state. The writer is `scaffold-seats`.
          fix: `scaffold-seats --package ${goalFolder} --workflow <workflow> --root `
            + '(plus --catalog-root/--bindings/--claude-md/--budget-json), or re-create the goal '
            + 'through the goal-creation request route, which scaffolds AND materializes in one act',
        });
      continue;
    }

    // D1 watcher: after the folder is a real goal with a taskforce, so ready-seats has a
    // package to read. Placed HERE so an unreadable/absent taskforce still reaches the
    // continues below — a reconcile that called ready-seats first would spend
    // COORD_TIMEOUT_MS on probe fixtures.
    if (!goal.startsWith('_')) {
      maybeReconcile({
        goal, goalFolder, engine, say,
        dryRun: consoleRunIsLive(goalFolder),
      });
    }

    // ── REGISTERED BUT UNBUILT: A ROW WITH NO `seats/<seat>/` FOLDER (adv, C71 / D5 defect 1) ─
    //
    // THE DEFECT, measured on the flagship: a milestone's planner and binder REGISTER the next
    // milestone's build team as `taskforce.csv` rows and NOTHING ever materializes them. The rows
    // exist, the folders do not, and the goal's next hop never happens.
    //
    // ⚠ ORDER IS LOAD-BEARING — THIS RUNS **BEFORE** THE UNCAST CHECK BELOW, AND MUST. A row with
    // no folder has no `seat.md`, so it has no declared harness/model, so `uncastSeats` reports it
    // UNCAST — and the genuine state ("registered, never built") would be permanently reported as
    // a DIFFERENT state ("somebody forgot to cast it") whose fix (`rbtv-bindings set`) does not
    // repair it. Placed here, an unbuilt seat is BUILT and the uncast check below then rules on a
    // complete tree; placed after, it is swallowed forever. The ORDER survives the C-9 inversion
    // below — what changed is the BLAST RADIUS of the answer, never which answer is given.
    //
    // It runs after `taskforce.csv` exists (a goal with no registry has no rows to be unbuilt).
    // The folders it writes are read by the very next pass, 10 s later, through the ordinary
    // path — so the seats it just built are skipped THIS cadence and only this cadence. Lazy-
    // required for the reason `seeding.js` lazy-requires the spawn reader — a module-level import
    // here is a dependency every probe of this file inherits.
    let unbuiltRows;
    try {
      unbuiltRows = require('./seeding').readTaskforce(goalFolder);
    } catch (err) {
      skipped.push({ goal, reason: 'taskforce-unreadable', error: err.message });
      say(shouldShout(goalFolder, raw) ? 'warn' : 'debug',
        'lane watch: could not read this goal\'s taskforce — not seeded', { goal, error: err.message });
      continue;
    }
    // ── THE PER-LANE SKIP SET [D16, C-9] ────────────────────────────────────────────────────
    //
    // THE DEFECT THIS INVERTS, and it is the shape of inventory ST-19 / ST-20 / ST-10: BOTH
    // checks below used to `continue` the WHOLE GOAL. One registered-but-unbuilt row, or one
    // seat somebody forgot to cast, and every healthy sibling on that goal stopped being
    // launchable — for as long as the one bad row stood. A one-seat defect presented as a dead
    // goal, and the remedy an operator reached for (`rbtv-bindings set` on the named seat) did
    // not visibly change anything until the LAST such row was fixed.
    //
    // WHAT REPLACES IT: a `seat -> reason` map threaded into `seedGoal`, which skips exactly
    // those lanes and seeds the rest. The refusals are UNCHANGED — an unbuilt seat is still not
    // launched, an uncast seat is still not launched, and both are still NAMED at the same log
    // level. Only the blast radius changed.
    const laneSkips = new Map();
    const unbuilt = unbuiltRows
      .map((r) => (r.seat || '').trim())
      .filter((s) => s && !fs.existsSync(path.join(goalFolder, 'seats', s)));
    if (unbuilt.length) {
      const { buildUnbuiltSeats } = require('../planning/queue-request');
      const outcome = buildUnbuiltSeats({
        goalFolder,
        goalsRoot,
        rows: unbuiltRows,
        unbuilt,
        say: (level, message, extra = {}) => say(level, message, { goal, ...extra }),
      });
      skipped.push({ goal, reason: 'unbuilt-seats', seats: unbuilt, built: outcome.built, failed: outcome.failed });
      // THOSE LANES are not seeded this cadence — the goal is. A build that succeeded changed the
      // tree the checks below read, and a build that refused leaves the row in exactly the state
      // that made the uncast branch lie about it; either way the answer for THAT SEAT is "not
      // this pass" and the next cadence rules on the tree as it now is.
      for (const seat of unbuilt) laneSkips.set(seat, 'unbuilt-seat');
    }

    // ── EVERY SEAT MUST BE CAST (`#d-abolish-profile-names` sub-ruling 3) ────────────────────
    //
    // The refusal that stood here was `no-profile-in-the-assignment`: the marker named no profile
    // and the goal's own casts could not supply one. Both halves are gone — there is no profile to
    // name and nothing to supply — and what replaces them is the ruling itself: a goal carrying an
    // uncast seat is NOT seeded, and the seats are NAMED. Seeding it anyway would queue rows whose
    // only possible outcome is `E_UNCAST_SEAT` at spawn, one wasted execution row per seat.
    //
    // `uncastSeats` is the one predicate `rbtv-goal lane --set daemon` and `rbtv run` also ask, so
    // what this pass seeds and what those doors accept can never disagree. Nothing here is fatal,
    // exactly as nothing else in this loop is: an unreadable taskforce leaves the goal for the next
    // cadence rather than taking the tick down.
    //
    // ⚠ THE LIST IS A PER-LANE SKIP, NOT A GOAL VERDICT [C-9]. `uncastSeats` is a whole-goal
    // COMPUTER and stays one — every caller still asks it the same question. What it no longer
    // does is decide the fate of the seats it did NOT name.
    let uncast;
    try {
      uncast = uncastSeats(goalFolder);
    } catch (err) {
      skipped.push({ goal, reason: 'cast-unreadable', error: err.message });
      say(shouldShout(goalFolder, raw) ? 'warn' : 'debug',
        'lane watch: could not read this goal\'s casts — not seeded', { goal, error: err.message });
      continue;
    }
    // An unbuilt row has no `seat.md`, so it is ALSO uncast — reported under the reason that
    // names the real state and carries the fix that repairs it (the load-bearing order above).
    const uncastOnly = uncast.filter((s) => !laneSkips.has(s));
    if (uncastOnly.length) {
      skipped.push({ goal, reason: 'uncast-seats', seats: uncastOnly });
      say(shouldShout(goalFolder, raw) ? 'warn' : 'debug',
        'lane watch: this goal carries seat(s) with NO cast — THOSE SEATS are not seeded and nothing '
        + 'was registered for them. Their siblings on this goal seed normally [C-9]. Bindings are the '
        + 'one source of truth for what a seat runs (`#d-abolish-profile-names`); there is no fallback '
        + 'to launch these on.', {
          goal,
          seats: uncastOnly,
          fix: `rbtv-bindings set <workflow.csv> <seat> <harness> <model> [effort], then rbtv goal materialize ${goal}`,
        });
      for (const seat of uncastOnly) laneSkips.set(seat, 'uncast-seat');
    }

    // ── AN ABANDONED LANE IS A PER-LANE SKIP, NEVER A RELAUNCH TARGET (`d-recovery-abandoned-is`
    // `-an-ending`) ───────────────────────────────────────────────────────────────────────────
    //
    // `drop-lane` retires ONE `(goal, seat)` pair forever, recorded in the ONE ending store's
    // `seat_abandonments` table. `classifyOwed`'s ledger half already excludes it from classA/
    // classB/pending (`owed-from-endings.js`), so a watcher-cadence pass never re-counts it owed —
    // but the graph half `seeding.js#launchOwed` asks for class R off `recordView`, which does not
    // populate `view.abandoned`, so a seat coord still marks READY (stale — coord does not know
    // about the drop) can still reach `classR` on that path. This list is the same C-9 per-lane
    // backstop `unbuilt`/`uncast` already use above: naming the seat here means `launchOwed`'s own
    // `laneSkips` check (seeding.js) refuses to enqueue it regardless of which half of the owed
    // computer let it through, and `openGoalRoom` below never opens a goal's first room under it.
    const abandonedMap = abandonedSeats(
      bindEnding(engine && engine.heartStore, goalFolder), goalNameOf(goalFolder, goal),
      unbuiltRows.map((r) => (r.seat || '').trim()).filter(Boolean),
    );
    const abandonedOnly = [...abandonedMap.keys()].filter((s) => !laneSkips.has(s));
    if (abandonedOnly.length) {
      skipped.push({ goal, reason: 'abandoned-seats', seats: abandonedOnly });
      say('debug', 'lane watch: this goal carries seat(s) dropped via `drop-lane` — THOSE SEATS are '
        + 'not seeded, permanently, and nothing was registered for them. Their siblings on this goal '
        + 'seed normally [C-9].', { goal, seats: abandonedOnly });
      for (const seat of abandonedOnly) laneSkips.set(seat, 'abandoned');
    }

    // ── PERSIST THE SKIP SET FOR A READ-ONLY CONSUMER (task-121 criterion 3) ─────────────────
    //
    // `laneSkips` above is IN-PROCESS ONLY — nothing durable ever recorded it, so a chair running
    // `supervise ready-seats` (a separate, on-demand, Python CLI) had no way to see that THIS
    // pass declined to launch a seat, without host journal access: `ready_seat_rows` reported such
    // a seat plain READY, matching every OTHER root seat, with nothing distinguishing it.
    //
    // ⚠ THIS DOES NOT CHANGE WHAT LAUNCHES. `laneSkips` is untouched and stays the one
    // decision-maker; this block only PERSISTS the same decision so `ready.py#daemon_lane_skips`
    // can surface it as an ADDITIVE note beside the verdict, never as the verdict itself — dag-10
    // RS-4 (coord_selftest.py) rules, deliberately and on purpose, that a registered-but-unbuilt
    // seat reads READY there, is a valid `launch --only` stub, and stays census-addressable; that
    // invariant is NOT reopened by this report existing alongside it.
    //
    // Written EVERY PASS, including EMPTY — a seat built or cast since the last cadence must stop
    // reporting blocked here too, not just stop being skipped. Fail-soft: a write failure is named
    // at `debug` (not `warn` — the launch decision above already ran and is correct either way)
    // and never takes the tick down, matching every other write in this pass.
    try {
      const skipsOut = {};
      for (const [seat, reason] of laneSkips) skipsOut[seat] = reason;
      const skipDir = path.join(goalFolder, 'coordination');
      fs.mkdirSync(skipDir, { recursive: true });
      const skipPath = path.join(skipDir, 'lane-skips.json');
      const tmp = `${skipPath}.tmp`;
      fs.writeFileSync(tmp, JSON.stringify({ written_at: new Date().toISOString(), skips: skipsOut }, null, 2));
      fs.renameSync(tmp, skipPath);
    } catch (err) {
      say('debug', 'lane watch: could not persist the lane-skip report for ready-seats — the '
        + 'launch decision above is unaffected', { goal, error: err.message });
    }

    if (consoleRunIsLive(goalFolder)) {
      skipped.push({ goal, reason: 'console-run-live' });
      say('info', 'lane watch: a console run is LIVE on this goal — not seeding against it', { goal });
      continue;
    }

    // ── THE ROOM, BEFORE THE SEED ────────────────────────────────────────────────────────────
    // Every lane-shaped guard is established by here (daemon-assigned, not paused, taskforce
    // present, no console run), so this call decides only the four room-shaped ones and opens the
    // FIRST room when they all hold — see `openGoalRoom`. `seedGoal` reads the lease itself on
    // the very next line, so a room opened here is seeded THIS pass, and a refusal falls through
    // to seeding's own `goalNotLive` branch unchanged.
    const room = openGoalRoom({
      goal, goalFolder, workspaceRoot, rows: unbuiltRows, laneSkips,
      ...(readLease ? { readLease } : {}), ...(runTmux ? { runTmux } : {}),
      say: (level, message, extra = {}) => say(level, message, extra),
    });
    if (room.opened) roomsOpened.push({ goal, room: room.room, pane: room.pane });

    let pickup;
    try {
      pickup = engine.seedGoal({
        goalFolder, goal, ...(readLease ? { readLease } : {}),
        // C-9: the skipped lanes travel WITH the seed call instead of cancelling it.
        ...(laneSkips.size ? { laneSkips } : {}),
      });
    } catch (err) {
      skipped.push({ goal, reason: 'seed-failed', error: err.message });
      say(shouldShout(goalFolder, raw) ? 'error' : 'debug',
        'lane watch: seeding a daemon-assigned goal FAILED — the tick continues', { goal, error: err.message });
      continue;
    }

    // READINESS REFUSED (§ D1): `coordinate ready-seats` exited non-zero — no python, a package it
    // could not read, a timeout, output that is not the documented array. `seedGoal` already logged
    // it at `warn` with the evidence and wrote NOTHING; this pass must not go on to report the goal
    // as "seeded". Recorded as a skip so the pass's own return says which goals were left alone and
    // why, and retried next cadence like every other transient here.
    //
    // ⚠ THE FAIL-CLOSE LIVES IN `seeding.js#seedGoal`, NOT HERE — this only logs and skips what it
    // was handed. A prior report placed it in this file and sent an investigation to the wrong one.
    //
    // ⚠ AND A DISPOSITION SKEW NO LONGER ARRIVES HERE AT ALL (Q2a, owner-ruled 2026-08-18). It used
    // to: `ready-seats` exited 1 on any SKEW row, so ONE disputed seat refused the WHOLE goal and
    // froze 65 healthy siblings for 4.5 hours. coord now exits 0 and carries the dispute on the
    // rows, `seedGoal` seeds every unaffected seat and `warn`s the skew by name, and this branch is
    // left to the refusals it was always about.
    if (pickup.readinessRefused) {
      skipped.push({ goal, reason: 'readiness-refused', evidence: pickup.readinessRefused });
      continue;
    }

    // D9 (seed-gates): the goal is not LIVE — `seedGoal` refused before anything was enqueued or
    // any relaunch grant spent, and already logged + surfaced it. A skip, not an adoption: a goal
    // with no room must not be reported "seeded" nor have a channel ensured for it.
    if (pickup.goalNotLive) {
      skipped.push({ goal, reason: 'goal-not-live', evidence: pickup.goalNotLive });
      continue;
    }

    failedOn.delete(goalFolder);
    adopted.push(pickup);
    {
      const facts = frozenFactsFor({
        goal,
        goalFolder,
        engine,
        pickup,
        seats: unbuiltRows.map((r) => (r.seat || '').trim()).filter(Boolean),
        lanesFile,
      });
      if (facts) frozenFacts.push(facts);
    }
    // The goal is ADOPTED — this is its daemon-lane run start, and the one moment its channel has
    // to exist before its seats' first to-owner message. After the seed, not before: a goal whose
    // seeding refused above gets no channel, exactly as the queue lane ensures nothing for a row
    // that does not start.
    ensureGoalChannelOnce({ goal, goalFolder, engine, say });
    const held = Object.keys(pickup.heldByOtherLane || {});

    // ── THE HUMAN-INTERACTIVE SEATS AND THEIR ARMS (task 7.626, ruling
    // `d-s19-fallback-rides-goal-channels`) ──────────────────────────────────────────────────
    //
    // A seat that declares `human-interactive:` in an `interactive` goal is carried in the TERMINAL
    // by the attached lane. Over here there is no terminal, and the ruling is that there does not
    // need to be one: the goal's Slack channel with a thread per agent IS the owner surface, so the
    // seat is dispatched exactly as it was and its declared `fallback:` executes AT THE FERRY —
    // `park` parks the ask, the other two deliver it MARKED (`bus-ferry.js` § THE SEAT'S FALLBACK
    // ARM). This pass therefore no longer steps over the condition; it REPORTS which arm each
    // dispatched seat is running under, which is the only thing an operator cannot derive.
    //
    // ⚠ THE RESIDUAL WARN IS THE UNDECLARED CASE, and only it: a flagged seat with NO `fallback:`
    // is a `component-lint` violation that reached dispatch, and it keeps its pre-7.626 behaviour
    // (delivered, unmarked) rather than acquiring an arm nobody wrote. That is worth a line; a
    // declared arm is not.
    //
    // Wrapped: both readers open descriptors off disk, and a malformed one must not be able to stop
    // a pass that has already seeded.
    let humanInteractive = {};
    let undeclared = [];
    try {
      const isHeld = heldSeatPredicate(goalFolder);
      for (const seat of pickup.enqueued) {
        if (!isHeld(seat)) continue;
        const arm = seatFallback(goalFolder, seat);
        humanInteractive[seat] = arm;
        if (!arm) undeclared.push(seat);
      }
    } catch { humanInteractive = {}; undeclared = []; }
    if (Object.keys(humanInteractive).length) {
      pickup.humanInteractiveDispatched = humanInteractive;
      if (undeclared.length) {
        say('warn', 'lane watch: HUMAN-INTERACTIVE seat(s) dispatched with NO declared `fallback:` — their asks '
          + 'reach the goal channel UNMARKED, so the owner cannot tell a question from a disclosure. This is a '
          + '`component-lint --check interactive-fallback` violation that reached dispatch.', { goal, seats: undeclared });
      }
    }
    // Loud when something moved, quiet otherwise: an adopted goal is re-read every cadence and an
    // info line per goal per 10 s is a journal nobody can read. `heldByOtherLane` is carried on the
    // line whenever it is non-empty — an operator has to be able to tell "somebody else is running
    // this seat right now" from "this seat is done" (the migrate trigger task's own requirement).
    // `blockedOnOwner` rides the same line for the same reason `heldByOtherLane` does — and it is
    // the one an operator most needs, because a goal whose wave is held on a HUMAN looks exactly
    // like a goal that has quietly stopped (ruling #d-block-and-queue-mechanical-hold).
    const waiting = Object.keys(pickup.blockedOnOwner || {});
    say(pickup.enqueued.length || held.length || waiting.length ? 'info' : 'debug', 'lane watch: daemon-assigned goal seeded', {
      goal,
      enqueued: pickup.enqueued,
      skippedAsFinished: pickup.skippedAsFinished,
      heldByOtherLane: pickup.heldByOtherLane,
      blockedOnOwner: pickup.blockedOnOwner,
      humanInteractiveDispatched: humanInteractive,
    });
  }

  return { adopted, skipped, roomsOpened, frozenFacts };
}

module.exports = {
  LANE_FILE, DAEMON, CONSOLE, readLane, laneIsPaused, laneIsClosed, consoleRunIsLive, runLaneWatch, failedOn,
  openGoalRoom,
  frozenFactsFor,
  ensureGoalChannelOnce, channelEnsured,
  maybeReconcile,
};
