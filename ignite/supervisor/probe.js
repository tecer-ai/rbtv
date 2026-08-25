'use strict';

// -- "IS THIS SITTING ALIVE?" - asked of the registry, and of nothing else [T4-R8, C-15] ---------
//
// WHAT WAS BROKEN. Three disjoint predicates answered this question and could disagree: a tmux
// pane (`coord.py#live_panes` / `cmd_status`), the cgroup carrier (`carrier_self_session`), and
// tick silence (`ticker.js`'s `lastActivityTick` knobs). A pane is a VIEWPORT - closing it kills
// nothing and opening one proves nothing. A carrier is IDENTITY, not a heartbeat. Tick silence is
// a statement about work product, not about a process, and its home is spec-recovery's
// `last_progress_at`. None of the three is an answer, so spec-supervisor section 6 retires all
// three onto the probe below.
//
// WHY THIS FILE AND NOT `registry.js`. The registry answers about a ROW (`isRowAlive`). Every
// legacy consumer asks about a SITTING - a `(goal, seat)` pair it holds a name for and no row for.
// Composing "find the row, then probe it" at each of the seven consumers is how three predicates
// became three answers; it is composed once, here.
//
// THE THREE-VALUED ANSWER IS THE POINT. `alive` is `true`, `false`, or `null` - and `null` means
// UNSUPERVISED (no row), never "probably running". A consumer that collapses `null` into `true`
// re-invents the pane; one that collapses it into `false` re-opens the mass-restamp hole (C-15),
// because a console-uncaged seat that has not checked in yet has no row and is not dead.

const { loadRegistry, isRowAlive, keyOf, SUPERVISED } = require('./registry');

function rowsFor(goal, pathOverride) {
  const rows = loadRegistry(pathOverride);
  return goal ? rows.filter((r) => (r.goal || '') === goal) : rows;
}

function probeSitting({ goal = '', seat }, pathOverride) {
  if (!seat) throw new Error('probeSitting requires a seat name');
  const key = keyOf({ goal: goal || '', seat });
  const row = loadRegistry(pathOverride).find((r) => keyOf(r) === key) || null;
  if (!row) return { goal: goal || '', seat, supervised: false, alive: null, row: null };
  return {
    goal: row.goal || '',
    seat: row.seat,
    supervised: row.supervision === SUPERVISED,
    alive: isRowAlive(row),
    row,
  };
}

// One call for a whole goal: `cmd_status` renders every seat at once, and N subprocess round trips
// per render is exactly the cost that made the pane predicate attractive in the first place.
function probeGoal(goal, pathOverride) {
  const out = {};
  for (const row of rowsFor(goal, pathOverride)) {
    out[row.seat] = {
      supervised: row.supervision === SUPERVISED,
      alive: isRowAlive(row),
      pid: row.pid || null,
      launch_token: row.launch_token || null,
    };
  }
  return out;
}

module.exports = { probeSitting, probeGoal };

// The JSON door for team-kit's python (`coord/liveness.py`). Deliberately this file's own main
// rather than a second op on `supervisor/cli.js`: that CLI opens the ENDING STORE for the ops that
// need one, and a liveness question that cannot be answered on a machine where the store will not
// open is a liveness question with a second failure mode it does not need.
if (require.main === module) {
  const argv = process.argv.slice(2);
  const flag = (name) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 && i + 1 < argv.length ? argv[i + 1] : null;
  };
  const file = flag('registry') || process.env.SUPERVISOR_REGISTRY || null;
  const goal = flag('goal') || '';
  const seat = flag('seat');
  try {
    const answer = seat ? probeSitting({ goal, seat }, file) : probeGoal(goal, file);
    process.stdout.write(`${JSON.stringify(answer)}\n`);
  } catch (err) {
    process.stderr.write(`${err.message}\n`);
    process.exit(1);
  }
}
