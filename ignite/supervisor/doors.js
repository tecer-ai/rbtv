'use strict';

// -- THE EXPLICIT DOOR LIST - every way a process can be born, named once [T4-R7, C-15] ---------
//
// WHAT WAS BROKEN. Launches were ad hoc. Seeding enqueued, reconcile enqueued, `launch --rerun`
// composed its own pane or its own enqueue, and a bare console `claude` was born with nobody
// watching at all - four births, no common door, and therefore no answer to "what did this daemon
// spawn?" that survived the next restart. The registry one file over is the ANSWER; this file is
// the set of QUESTIONS it is allowed to be asked, because a persisted registry that only some
// launch paths write to is a registry that lies by omission.
//
// THE RULE, and it has exactly two arms [T4-R7]: a launch either flows through the supervisor -
// `superviseSpawn`, which is the registry's write moment (i) and the only supervised birth - or it
// is MARKED `unsupervised`. There is no third arm, and in particular there is no silent arm: a
// launch this file does not recognise is still recorded, flagged `unsupervised`, so an ad hoc
// caller shows up as an unsupervised sitting rather than as nothing at all. "Never silently live"
// is the whole property.
//
// WHAT A DOOR IS NOT. Not a permission check (`spawn.js`'s walls own that), not a queue (the heart
// store owns that), and not an ending (`death-stamp.js` owns that). A door is a NAME travelling
// with a launch so the registry row can say where the process came from.

const { recordSpawn, recordCheckIn, SUPERVISED, UNSUPERVISED } = require('./registry');

// -- The six rows of spec-supervisor section 3, verbatim ----------------------------------------
//
// `launcher` is the identity the launch ALREADY carries end to end, and reusing it is deliberate:
// seeding's and reconcile's enqueues have always stamped `enqueued_by` on the queue row, and
// `ticker.js#launchAgent` already threads `queueRow.enqueued_by` into `spawn()`. So the door name
// needs no new parameter on four call frames - it is derived from a value that was there all
// along. `--rerun`'s carrier is its own `reason` token (`daemon_lane_reason`, `leader-<door>-…`),
// which is why `doorForLauncher` also accepts a prefix match.
const WRAPPED = 'wrapped';
const MARKED_UNSUPERVISED = 'marked-unsupervised';

const DOORS = Object.freeze({
  seeding: {
    door: 'seeding',
    disposition: WRAPPED,
    launcher: 'attached-execution',
    chokepoint: 'supervisor/seeding.js seedGoal / launchOwed',
    note: 'daemon first-launches go through supervisor spawn',
  },
  reconcile: {
    door: 'reconcile',
    disposition: WRAPPED,
    launcher: 'goal-watcher',
    chokepoint: 'supervisor/reconcile.js deriveOwed / launchSitting',
    note: 'its launches go through supervisor spawn, never a second enqueue',
  },
  rerun: {
    door: 'rerun',
    disposition: WRAPPED,
    launcher: 'leader-rerun',
    // spec-supervisor §3 puts `--rerun` and `--declare-only` on ONE row, and `--reopen` is the
    // same leader-direct composer with a third flag: they are one door with three from-states,
    // not three doors. `daemon_lane_reason` spells each as its own `leader-<flag>-…` token, so the
    // aliases are listed rather than the token grammar being loosened — a loose prefix would
    // silently adopt any future `leader-*` composer into this door's disposition.
    aliases: ['leader-declare-only', 'leader-reopen', 'leader-launch'],
    chokepoint: 'coord/launch.py cmd_launch --rerun / --declare-only',
    note: 'the leader-direct relaunch door, on both the daemon and the console lane',
  },
  'attest-exit': {
    door: 'attest-exit',
    disposition: WRAPPED,
    launcher: null,          // a REAP door, not a birth: it ends sittings, it never starts one
    chokepoint: 'supervisor/spawn/spawn.js closeSeatSessionRow -> attest-exit --force-dead',
    note: 'wrapped by impl-supervisor-death-stamp: this door BECAME the supervisor death stamp',
  },
  'console-uncaged': {
    door: 'console-uncaged',
    disposition: MARKED_UNSUPERVISED,
    launcher: null,          // nobody witnesses this birth - that IS the disposition
    chokepoint: 'bare console / uncaged `claude` (IE-3)',
    note: 'marked unsupervised until check-in registers it [T4-R8]',
  },
  'goal-not-live': {
    door: 'goal-not-live',
    disposition: WRAPPED,
    launcher: null,
    refusal: 'E_GOAL_NOT_LIVE',
    chokepoint: 'supervisor/seeding.js readLease / goalNotLive (tmux room down; IE-1)',
    note: 'a supervisor-owned REFUSAL: no process born, no death stamp, nothing enqueued',
  },
});

// A launch that names no door is not refused - it is MARKED. Refusing would turn an unmapped
// caller into a dead goal; marking turns it into a visible unsupervised sitting, which is the arm
// [T4-R7] actually asks for.
function doorForLauncher(launcher) {
  const name = String(launcher || '').trim();
  if (!name) return null;
  for (const row of Object.values(DOORS)) {
    if (!row.launcher) continue;
    if (name === row.launcher) return row.door;
    for (const alias of row.aliases || []) {
      if (name === alias || name.startsWith(`${alias}-`)) return row.door;
    }
    // `--rerun`'s token is `leader-rerun-<anchor-slug>`: the door is the stem, the anchor is the
    // brake's per-investigation budget key (D66) and is none of this file's business.
    if (name.startsWith(`${row.launcher}-`)) return row.door;
  }
  return null;
}

function doorRow(door) {
  return DOORS[String(door || '')] || null;
}

function supervisionFor(door) {
  const row = doorRow(door);
  return row && row.disposition === WRAPPED ? SUPERVISED : UNSUPERVISED;
}

// -- SUPERVISOR SPAWN - the registry's write moment (i), and the only supervised birth -----------
//
// Called by the door that HOLDS the pid, immediately after spawn returns one. It classifies rather
// than throws: a launcher this list does not know still gets a row, flagged `unsupervised`, and
// the caller is handed `{ door: null, supervision: 'unsupervised' }` so it can say so out loud.
//
// `launch_token` is the daemon-minted identity at launch and it is NOT the pane, NOT the cgroup and
// NOT the pid [T2-R8]: on the daemon lane it is the session id `spawn()` mints before argv is
// composed. Minting is untouched by this file - it is carried, not invented here.
function superviseSpawn({ door = null, launcher = null, goal, seat, pid, start_time: startTime = null,
  launch_token: launchToken = null }, registryFile) {
  const resolved = door || doorForLauncher(launcher);
  const supervision = resolved ? supervisionFor(resolved) : UNSUPERVISED;
  const row = recordSpawn({
    goal, seat, pid, start_time: startTime, launch_token: launchToken, supervision,
  }, registryFile);
  return { ...row, door: resolved, supervision, unsupervised: supervision === UNSUPERVISED };
}

// -- THE MARKED ARM - console-uncaged, and any other birth the daemon did not perform ------------
//
// A bare console `claude` has no witness at birth, so there is nothing to write at the moment it
// starts. The mark is therefore what the SEAT's own check-in writes: `registerCheckIn` is write
// moment (ii), and the flip to `supervised` IS the moment the sitting becomes supervisable. Until
// then the sitting simply has no row - and an absent row answers "not supervised", never "alive",
// because `readopt` may not invent a death from a missing row and no probe may invent a life from
// one either.
function markUnsupervised({ goal, seat, pid, start_time: startTime = null,
  launch_token: launchToken = null }, registryFile) {
  return recordSpawn({
    goal, seat, pid, start_time: startTime, launch_token: launchToken, supervision: UNSUPERVISED,
  }, registryFile);
}

function registerCheckIn({ goal, seat, pid, start_time: startTime = null,
  launch_token: launchToken = null }, registryFile) {
  return recordCheckIn({
    goal, seat, pid, start_time: startTime, launch_token: launchToken,
  }, registryFile);
}

// -- THE REFUSAL ARM - E_GOAL_NOT_LIVE, and it is a refusal rather than an ending ----------------
//
// The room is down, so no process can be born. THREE things must therefore not happen, and the
// returned document asserts all three by name because each one was a measured incident: nothing is
// spawned (no registry row - this function touches no file at all), nothing is stamped (a refused
// launch is not a dead seat, and stamping one would put a `failed` on a seat that never ran), and
// nothing is enqueued (G-leader-0818-1830 burned two relaunch grants on launches the spawn door
// was always going to refuse). It is NOT a seat `failed`: that class is envelope's
// `launch-refused`, and inventing a second word for it here is how the fifth ending vocabulary
// came to exist in the first place.
function refuseLaunch({ door = 'goal-not-live', goal = null, seat = null, evidence = '' }) {
  const row = doorRow(door);
  return {
    refused: true,
    door,
    code: (row && row.refusal) || 'E_LAUNCH_REFUSED',
    goal,
    seat,
    evidence: String(evidence || ''),
    spawned: false,
    stamped: false,
    enqueued: false,
  };
}

module.exports = {
  DOORS,
  WRAPPED,
  MARKED_UNSUPERVISED,
  doorForLauncher,
  doorRow,
  supervisionFor,
  superviseSpawn,
  markUnsupervised,
  registerCheckIn,
  refuseLaunch,
};
