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
const { RUN_LOCK, runnerAlive, heldSeatPredicate } = require('../operator/attached-execution');
// The seat's declared autonomous arm, read through the chat bridge's OWN reader — the same module
// `heldSeatPredicate` reads both gates from. A second parser of that frontmatter is a lane that
// disagrees with the ferry about what a seat declared (7.626 criterion 2).
const { seatFallback } = require('../chat/bus-ferry');
// WHICH SEATS ARE NOT CAST — the ONE predicate every door refuses on. `rbtv run` and
// `rbtv-goal lane` ask the same function, so this pass and the CLI that writes the marker can
// never disagree about which goals may be assigned to the daemon.
const { uncastSeats } = require('./seeding');
const { maybeReconcile } = require('./reconcile');

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
// ⚑ `paused ` STILL PREFIXES, and still resolves `console` here with no special case: a paused
// marker's whole text is not `daemon`, which is the entire mechanism (`goal_cli.py#pause`).
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

// IS THE GOAL PAUSED — the JS twin of `goal_cli.py#lane_is_paused` (the two change together,
// like `readLane`/`read_lane`, DEC-1). `readLane` above deliberately flattens a paused marker
// into `console` (that is the whole pause mechanism for SEEDING); this reader answers the
// DIFFERENT question the ticker's dispatch pause gate asks — "did an operator pause this goal?"
// — which `console` cannot carry. ABSENT OR UNREADABLE IS NOT PAUSED: the marker is the
// operator's explicit act, and `rbtv-goal pause` CREATES the file on a goal that never had one
// (`read_lane_raw` supplies `console\n`), so every goal is pausable and an unpaused goal keeps
// its exact current behaviour.
//
// ── ONE PAUSE RECORD, AND THE STORE ROW IS IT ─────────────────────────────────────────────────
//
// There were TWO records of "is this goal paused": the goal-state row in the ending store, and
// the first word of the `execution-lane` file. This function read both and the FILE could win —
// the store answer was consulted only for a TRUE, so a store row reading `running` fell through
// to a stale `paused` marker on disk and the goal stayed frozen against the record that had
// actually been updated. That is the two-records shape, one function down from the two owed-work
// computers, and it converges the same way: THE ROW IS THE RECORD.
//
// ⚠ AND `isGoalPaused` CANNOT CARRY THE CONVERGENCE BY ITSELF, because it flattens two different
// answers into `false`: "the row says running" and "there is no row at all". Only the first is an
// answer. So the row is read directly and its EXISTENCE is the test — a goal the store knows about
// is answered by the store, full stop, and the file shim is reached only by a goal the store has
// never recorded (every goal predating the goal-state table, and every fixture that pauses by
// writing the marker). ABSENT OR UNREADABLE IS STILL NOT PAUSED, on both surfaces.
function laneIsPaused(goalFolder, heartStore) {
  try {
    const { bindEnding, goalNameOf } = require('./ending-reads');
    const api = bindEnding(heartStore, goalFolder);
    if (api && typeof api.getGoalState === 'function') {
      const row = api.getGoalState(goalNameOf(goalFolder));
      if (row && row.stored) return row.stored === 'paused';
    }
  } catch { /* the store could not be asked at all — fall through to the file shim */ }
  let raw;
  try {
    raw = fs.readFileSync(path.join(goalFolder, LANE_FILE), 'utf8');
  } catch {
    return false;
  }
  return raw.trim().split(/\s+/)[0] === 'paused';
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
function runLaneWatch({ goalsRoot, engine, logger = null, readLease = undefined, lanesFile = undefined }) {
  const say = (level, message, extra = {}) => { if (logger) logger({ level, message, ...extra }); };
  const adopted = [];
  const skipped = [];
  // One observation per goal this pass seeded, for `runtime/frozen-pass.js`. Collected, never acted
  // on here: this pass seeds goals, and an alarm is somebody else's act.
  const frozenFacts = [];

  let entries;
  try {
    entries = fs.readdirSync(goalsRoot, { withFileTypes: true });
  } catch {
    // No goals tree on this workspace. Not an error and not worth a line every cadence.
    return { adopted, skipped };
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const goal = entry.name;
    const goalFolder = path.join(goalsRoot, goal);
    const { lane, legacy, raw } = readLane(goalFolder);

    // D1 watcher: honour pause via the ONE reader. A paused marker flattens to
    // console below, so without this call maybeReconcile never sees the goal and
    // the skip would be an accident of the console-flatten (two readings of one
    // state). Call it here; reconcileGoal returns skipped:'paused' before
    // ready-seats. Seeding still uses the existing lane !== DAEMON path.
    if (!goal.startsWith('_') && laneIsPaused(goalFolder, engine && engine.heartStore)) {
      maybeReconcile({ goal, goalFolder, engine, say });
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

    if (consoleRunIsLive(goalFolder)) {
      skipped.push({ goal, reason: 'console-run-live' });
      say('info', 'lane watch: a console run is LIVE on this goal — not seeding against it', { goal });
      continue;
    }

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

  return { adopted, skipped, frozenFacts };
}

module.exports = {
  LANE_FILE, DAEMON, CONSOLE, readLane, laneIsPaused, consoleRunIsLive, runLaneWatch, failedOn,
  frozenFactsFor,
  ensureGoalChannelOnce, channelEnsured,
  maybeReconcile,
};
