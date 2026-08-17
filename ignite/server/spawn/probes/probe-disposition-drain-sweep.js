'use strict';

// probe-disposition-drain-sweep — F3 follow-up: the drain reaches a goal with NO live exec.
//
// The fixture has no seats, no sessions, no spawn manager and no ticker: NOTHING of either goal
// is alive, which is the exact state the original F3 wiring could not reach (it drained only the
// goals of execs in the crash sweep's `liveBeforeCrash`). What triggers the drain here is the
// grant file itself.
//
// A1  a goal with an unspent grant and no live exec is drained: the durable cell becomes `done`,
//     the writer stays `leader`, and the grant is spent
// A2  a goal whose grants are all SPENT is left byte-identical — the unspent test is load-bearing,
//     not a blanket drain of every goal on every tick
// A3  a second pass drains nothing at all (no goal carries an unspent grant any more)

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { capture } = require('./lib');
const { applyDispositionGrants } = require('../spawn');

const SESSIONS_HEADER = 'session-id,seat,harness,native-session-id,workdir,recorded,started,ended,'
  + 'pid,pid-starttime,tty,disposition,disposition-writer,execution,checkin,model';
const GRANTS_HEADER = 'seat,session-id,from-state,ruled,writer,anchor,stamp,spent-at';
const STAMP = '2026-08-17T12:00:00Z';

function seedGoal(goalsRoot, goal, seat, sid, spentAt) {
  const goalDir = path.join(goalsRoot, goal);
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'sessions.csv'),
    `${SESSIONS_HEADER}\n${sid},${seat},bash,,,${STAMP},${STAMP},${STAMP},,,,exited,,,,\n`);
  fs.writeFileSync(path.join(goalDir, 'coordination', 'disposition-grants.csv'),
    `${GRANTS_HEADER}\n${seat},${sid},exited,done,leader,p-drain-sweep,${STAMP},${spentAt}\n`);
  return goalDir;
}

function cell(goalDir, seat, col) {
  const [header, ...rows] = fs.readFileSync(path.join(goalDir, 'sessions.csv'), 'utf8')
    .trim().split('\n');
  const cols = header.split(',');
  const row = rows.map((r) => r.split(',')).reverse().find((r) => r[cols.indexOf('seat')] === seat);
  return row ? (row[cols.indexOf(col)] || '') : null;
}

capture('probe-disposition-drain-sweep', async (lines) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p-drain-sweep-'));
  try {
    const goalsRoot = path.join(tmp, '.rbtv', 'goals');
    const dead = seedGoal(goalsRoot, 'dead-goal', 'deadseat', 'dead-sid', '');
    const spent = seedGoal(goalsRoot, 'spent-goal', 'spentseat', 'spent-sid', STAMP);
    fs.mkdirSync(path.join(goalsRoot, 'no-grant-goal', 'coordination'), { recursive: true });
    const spentBefore = fs.readFileSync(path.join(spent, 'sessions.csv'), 'utf8');

    const res = applyDispositionGrants({ workspaceRoot: tmp, log: null });
    lines.push(`drained: ${JSON.stringify(res.drained.map((d) => ({ goal: path.basename(d.goalDir), applied: d.applied })))}`);

    // A1
    const disposition = cell(dead, 'deadseat', 'disposition');
    const writer = cell(dead, 'deadseat', 'disposition-writer');
    const grantRow = fs.readFileSync(path.join(dead, 'coordination', 'disposition-grants.csv'), 'utf8')
      .trim().split('\n')[1];
    if (disposition !== 'done' || writer !== 'leader') {
      throw new Error(`A1: dead-goal row reads disposition=${disposition} writer=${writer} — the drain did not reach a goal with no live exec`);
    }
    if (grantRow.trimEnd().endsWith(',')) throw new Error(`A1: grant not spent: ${grantRow}`);
    lines.push(`A1 dead-goal (no live exec): disposition=${disposition} writer=${writer} grant=${grantRow}`);

    // A2
    const spentAfter = fs.readFileSync(path.join(spent, 'sessions.csv'), 'utf8');
    if (spentAfter !== spentBefore) throw new Error('A2: a goal with only SPENT grants was written to');
    if (res.drained.some((d) => d.goalDir === spent)) throw new Error('A2: spent-only goal was drained');
    lines.push('A2 spent-goal: sessions.csv byte-identical, not drained');

    // A3
    const again = applyDispositionGrants({ workspaceRoot: tmp, log: null });
    if (again.drained.length !== 0) throw new Error(`A3: second pass drained ${again.drained.length} goal(s)`);
    lines.push('A3 second pass: 0 goals drained (nothing unspent remains)');

    lines.push('result: the drain is keyed off the grant file — a grant minted on a fully dead goal is applied');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
