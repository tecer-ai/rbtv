'use strict';

// engine/lane-watch.js — THE DAEMON LANE'S GOAL-PICKUP TRIGGER (owner ruling
// decisions.md#d-daemon-lane-button, which settles the follow-on `engine/seeding.js` named and
// deliberately did not invent).
//
// THE OWNER'S DESIGN, in his words: "build the button. it should be accessed by a CLI, which the
// channel master has access to. this CLI must change the file in goals that says if it is CURRENTLY
// being run by the daemon or by the console, so the daemon knows when to pick it up."
//
// So the trigger is a per-goal MARKER FILE the daemon watches, on the precedent of `execution-mode`
// (one word in a small file at the goal root, `bridges/chat/bus-ferry.js` § gate 2): the goal's
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
// ⚠ THE FILE CARRIES A SECOND TOKEN — THE LAUNCH PROFILE — and it has to. Seeding needs a NAMED
// profile from the one shared config (`DEC-1` § Shared profile source: this lane never composes or
// derives one, exactly as `rbtv run --profile` never does), and there is no other honest place to
// read it from: `taskforce.csv`'s harness/model columns are task 7.54's catalog, not a profile name.
// Handing a goal to the daemon without saying what its seats run on is not a thing that can work, so
// the CLI REFUSES `--set daemon` without `--profile`. A hand-written `daemon` with no profile is
// therefore rare, and it warns rather than guessing.
//
// WHAT THIS PASS IS NOT: a second seeding implementation. It decides WHICH goals, and calls
// `engine.seedGoal` for each — the one seam (PRIN-11).

const fs = require('node:fs');
const path = require('node:path');
const { RUN_LOCK, runnerAlive, heldSeatPredicate } = require('./attached-execution');

const LANE_FILE = 'execution-lane';
const DAEMON = 'daemon';
const CONSOLE = 'console';

// The lane assignment, read with the same tolerance `execution-mode` is read with: trimmed,
// case-insensitive, and everything that is not the positive word is the conservative default.
// The optional second token is the launch profile the daemon seeds with.
function readLane(goalFolder) {
  let raw;
  try {
    raw = fs.readFileSync(path.join(goalFolder, LANE_FILE), 'utf8');
  } catch {
    return { lane: CONSOLE, profile: null, present: false, raw: '' };
  }
  const text = raw.trim();
  const [word, profile] = text.split(/\s+/);
  if (String(word || '').toLowerCase() !== DAEMON) {
    return { lane: CONSOLE, profile: null, present: true, raw: text };
  }
  return { lane: DAEMON, profile: profile || null, present: true, raw: text };
}

// ── THE REPEATED-FAILURE MEMO ─────────────────────────────────────────────────────────────────
//
// A goal that cannot be seeded — a profile the shared config does not carry, a broken taskforce —
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

// ONE PASS over the goals tree. Called from the daemon's loop, immediately before each tick, so a
// seat seeded by this pass is dispatched by the tick that follows it rather than a cadence later.
//
// NOTHING HERE IS FATAL. A goal with a broken taskforce, an unreadable folder or a failing seed is
// logged and skipped; the daemon serves every other goal from the same loop, and taking the tick
// down over one goal folder is the one behaviour a watch pass must not have. The next pass retries.
//
// `isHeld` IS DELIBERATELY NOT PASSED, and that is the existing behaviour standing rather than a
// gap being introduced: a human-interactive seat has no terminal to reach on the daemon side, and
// what should happen to it there is migrate task 7.626 (the fallback gap), which this build was
// explicitly told not to solve. Passing a predicate here would silently park such seats forever —
// a NEW behaviour — so the daemon dispatches them exactly as it does today.
//
// ponytail: O(goals) `readdir` + one small read per goal per cadence, and `engine.seedGoal`
// publishes the record once per adopted goal. At tens of goals and a 10 s cadence that is noise;
// if the tree ever reaches thousands, watch mtimes instead of re-reading every pass.
function runLaneWatch({ goalsRoot, engine, logger = null }) {
  const say = (level, message, extra = {}) => { if (logger) logger({ level, message, ...extra }); };
  const adopted = [];
  const skipped = [];

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
    const { lane, profile, raw } = readLane(goalFolder);

    if (lane !== DAEMON) {
      skipped.push({ goal, reason: 'not-assigned-to-the-daemon' });
      failedOn.delete(goalFolder);      // a goal handed back to the console starts clean if it returns
      continue;
    }

    if (!fs.existsSync(path.join(goalFolder, 'taskforce.csv'))) {
      // Assigned but not yet materialized — a normal state between `rbtv-goal scaffold` and
      // `rbtv-goal materialize`, not a fault. Quiet.
      skipped.push({ goal, reason: 'no-taskforce-yet' });
      continue;
    }

    if (!profile) {
      skipped.push({ goal, reason: 'no-profile-in-the-assignment' });
      say(shouldShout(goalFolder, raw) ? 'warn' : 'debug',
        'lane watch: goal is assigned to the daemon but names NO launch profile — not seeded', {
          goal,
          fix: `rbtv goal lane ${goal} --set daemon --profile <name>`,
        });
      continue;
    }

    // ⚠ THE PROFILE IS CHECKED BEFORE ANYTHING IS WRITTEN, and that ordering is the fix rather
    // than the check. `enqueue` refuses an unknown profile (`E_UNKNOWN_PROFILE`) — but only AFTER
    // `seedTaskforce` has already registered a job row per seat, and `registerJob` is create-only,
    // so a marker carrying a typo left permanent orphan rows in the daemon's store on its very
    // first pass and then threw every cadence forever. Refusing here writes nothing at all.
    // `Object.hasOwn`, not a truthiness test, for the store's own reason: `constructor` is a legal
    // kebab-case name that walks the prototype chain and reads present.
    const known = (engine.heartStore && engine.heartStore.config && engine.heartStore.config.profiles) || {};
    if (!Object.hasOwn(known, profile)) {
      skipped.push({ goal, reason: 'unknown-profile', profile });
      say(shouldShout(goalFolder, raw) ? 'warn' : 'debug',
        'lane watch: the assignment names a launch profile the shared config does not carry — not seeded, and NOTHING was registered', {
          goal,
          profile,
          known: Object.keys(known),
          fix: `rbtv goal lane ${goal} --set daemon --profile <a name from profiles: in the shared config>`,
        });
      continue;
    }

    if (consoleRunIsLive(goalFolder)) {
      skipped.push({ goal, reason: 'console-run-live' });
      say('info', 'lane watch: a console run is LIVE on this goal — not seeding against it', { goal });
      continue;
    }

    let pickup;
    try {
      pickup = engine.seedGoal({ goalFolder, goal, profile });
    } catch (err) {
      skipped.push({ goal, reason: 'seed-failed', error: err.message });
      say(shouldShout(goalFolder, raw) ? 'error' : 'debug',
        'lane watch: seeding a daemon-assigned goal FAILED — the tick continues', { goal, error: err.message });
      continue;
    }

    failedOn.delete(goalFolder);
    adopted.push(pickup);
    const held = Object.keys(pickup.heldByOtherLane || {});

    // ── F1 · THE DIVERGENCE THIS PASS KNOWINGLY STEPS OVER (task 7.626) ───────────────────────
    //
    // A seat that declares `human-interactive:` in an `interactive` goal is carried in the
    // TERMINAL by the attached lane, and refused rather than dispatched when no terminal exists.
    // Over here there is no terminal at all, and the daemon dispatches it as an ordinary detached
    // child — its `fallback:` firing nowhere. That is the EXISTING behaviour and the owner's ruled
    // default (7.626 owns the fix; d-daemon-lane-button deliberately did not solve it here).
    //
    // What was NOT acceptable is doing it SILENTLY, which is what shipped: a channel-master goal
    // defaults to the daemon lane, so this is the AFK default path, and the lane that refuses the
    // same seat loudly made the quiet one look equivalent. So the condition is REPORTED — on the
    // log line and on the pass's own return — and named to the task that owns it. Nothing here
    // changes what is dispatched.
    //
    // Wrapped: the predicate reads the goal's `execution-mode` and each seat's descriptor off
    // disk, and a malformed one must not be able to stop a pass that has already seeded.
    let humanInteractive = [];
    try {
      const isHeld = heldSeatPredicate(goalFolder);
      humanInteractive = pickup.enqueued.filter((seat) => isHeld(seat));
    } catch { /* unreadable descriptor: the report loses a line, the goal keeps running */ }
    if (humanInteractive.length) {
      pickup.humanInteractiveDispatched = humanInteractive;
      say('warn', 'lane watch: dispatching HUMAN-INTERACTIVE seat(s) headless — there is no terminal in this lane, '
        + 'so their `fallback:` fires nowhere. This is the existing ruled behaviour, NOT a decision taken here; '
        + 'the fix is migrate task 7.626.', { goal, seats: humanInteractive });
    }
    // Loud when something moved, quiet otherwise: an adopted goal is re-read every cadence and an
    // info line per goal per 10 s is a journal nobody can read. `heldByOtherLane` is carried on the
    // line whenever it is non-empty — an operator has to be able to tell "somebody else is running
    // this seat right now" from "this seat is done" (the migrate trigger task's own requirement).
    say(pickup.enqueued.length || held.length ? 'info' : 'debug', 'lane watch: daemon-assigned goal seeded', {
      goal,
      profile,
      enqueued: pickup.enqueued,
      skippedAsFinished: pickup.skippedAsFinished,
      heldByOtherLane: pickup.heldByOtherLane,
      humanInteractiveDispatched: humanInteractive,
    });
  }

  return { adopted, skipped };
}

module.exports = { LANE_FILE, DAEMON, CONSOLE, readLane, consoleRunIsLive, runLaneWatch, failedOn };
