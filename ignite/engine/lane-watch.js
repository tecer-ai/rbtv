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
const { RUN_LOCK, runnerAlive } = require('./attached-execution');

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
    return { lane: CONSOLE, profile: null, present: false };
  }
  const [word, profile] = raw.trim().split(/\s+/);
  if (String(word || '').toLowerCase() !== DAEMON) {
    return { lane: CONSOLE, profile: null, present: true };
  }
  return { lane: DAEMON, profile: profile || null, present: true };
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
    const { lane, profile } = readLane(goalFolder);

    if (lane !== DAEMON) { skipped.push({ goal, reason: 'not-assigned-to-the-daemon' }); continue; }

    if (!fs.existsSync(path.join(goalFolder, 'taskforce.csv'))) {
      // Assigned but not yet materialized — a normal state between `rbtv-goal scaffold` and
      // `rbtv-goal materialize`, not a fault. Quiet.
      skipped.push({ goal, reason: 'no-taskforce-yet' });
      continue;
    }

    if (!profile) {
      skipped.push({ goal, reason: 'no-profile-in-the-assignment' });
      say('warn', 'lane watch: goal is assigned to the daemon but names NO launch profile — not seeded', {
        goal,
        fix: `rbtv-goal lane ${goal} --set daemon --profile <name>`,
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
      say('error', 'lane watch: seeding a daemon-assigned goal FAILED — the tick continues', { goal, error: err.message });
      continue;
    }

    adopted.push(pickup);
    const held = Object.keys(pickup.heldByOtherLane || {});
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
    });
  }

  return { adopted, skipped };
}

module.exports = { LANE_FILE, DAEMON, CONSOLE, readLane, consoleRunIsLive, runLaneWatch };
