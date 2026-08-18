#!/usr/bin/env node
'use strict';

// probe-goal-stall-alarm — THE OWNER ALARM, driven through the REAL seeding pass
// (owner ruling Q3a, 2026-08-18: "a frozen goal reaches the owner in its own Slack channel").
//
// THE QUESTION: on 2026-08-18 two goals sat frozen for 4+ hours, refusing to seed 3,028 times
// across a daemon restart, and NOTHING told the owner. Does a frozen goal now say so? Does a
// HEALTHY goal stay silent? And — the property that decides whether this is an alarm or a spam
// cannon — does a goal that is still stuck for the SAME reason get exactly ONE message, while a
// goal stuck for a DIFFERENT reason gets a new one?
//
// WHAT IS SUBSTITUTED, disclosed up front:
//   · `engine.seedGoal` is STAGED. It returns a `seedGoal`-shaped pickup per fixture goal, which
//     is how the condition is staged: the condition IS coord's answer, and staging coord's answer
//     without a python interpreter, a live sessions.csv and a real SKEW is what a fixture is for.
//     Everything ABOVE and BELOW it is real — the lane marker read, the taskforce read, the cast
//     check, the real `runLaneWatch`, the real `goal-stall-alarm.js`, the real dedup state.
//   · `engine.ticker.ensureGoalChannel` is a SPY. The performing half forks a systemd unit holding
//     a Slack credential; this probe asserts the composed argv byte-exactly and spawns nothing.
//     ⚑ NO PROCESS IS SPAWNED AND NO SLACK CALL IS MADE.
//   · The CLOCK is advanced by rewriting `since` on the alarm's own state entries — the real state
//     machine, driven forward in time, rather than a sleep. Nothing else is touched.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const IGNITE_SRC = path.resolve(__dirname, '..', '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-goal-stall-alarm.out');

const lines = [];
const failures = [];
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}
function say(s) { lines.push(s); }

const laneWatch = require('../../../engine/lane-watch');
const alarm = require('../goal-stall-alarm');

// ── the fixture tree ─────────────────────────────────────────────────────────────────────────
const goalsRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-goal-stall-alarm-'));
function makeGoal(name, lane = 'daemon') {
  const dir = path.join(goalsRoot, name);
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(dir, 'seats', s), { recursive: true });
  fs.writeFileSync(path.join(dir, 'taskforce.csv'), `taskforce-id,seat,after\ntf-${name},alpha,\ntf-${name},bravo,alpha\n`);
  for (const s of ['alpha', 'bravo']) {
    fs.writeFileSync(path.join(dir, 'seats', s, 'seat.md'),
      `---\nseat: ${s}\nharness: bash\nmodel: probe-alarm\n---\n\nbody\n`);
  }
  fs.writeFileSync(path.join(dir, 'execution-lane'), `${lane}\n`);
  return dir;
}

const G_SKEW = 'frozen-skew';
const G_REFUSED = 'frozen-refused';
const G_DEAD = 'frozen-ready-no-live';
const G_OK = 'healthy-moving';
const G_DONE = 'healthy-finished';
for (const g of [G_SKEW, G_REFUSED, G_DEAD, G_OK, G_DONE]) makeGoal(g);

// ── the staged pickups — `seedGoal`'s own return shape, one per fixture ───────────────────────
const base = (goal) => ({
  goalFolder: path.join(goalsRoot, goal), goal, seats: ['alpha', 'bravo'],
  readinessRefused: null, skewed: [], seeds: {}, skippedAsFinished: [],
  heldByOtherLane: {}, blockedOnOwner: {}, heldByStore: {}, enqueued: [], states: {},
});
const PICKUPS = {
  // (a) — the measured incident's shape AFTER `skew-per-seat`: a per-seat SKEW verdict, the rest
  // of the goal seeding around it.
  [G_SKEW]: { ...base(G_SKEW), skewed: [{ seat: 'alpha', verdict: 'SKEW', reason: 'live=done durable=exited' }], states: { alpha: 'waiting', bravo: 'waiting' } },
  // (a) second arm — `ready-seats` exited non-zero, so NOTHING was seeded for the whole goal.
  [G_REFUSED]: { ...base(G_REFUSED), readinessRefused: '`coordinate ready-seats` exited 1: no such file' },
  // (b) — ready work, zero live seats: the 18-hour `heldByStore` freeze's shape.
  [G_DEAD]: { ...base(G_DEAD), heldByStore: { alpha: 'the record has already fired it' }, states: { alpha: 'ready', bravo: 'waiting' } },
  // THE CONTROLS. One goal moving, one goal finished. Neither may alarm, ever.
  [G_OK]: { ...base(G_OK), enqueued: ['alpha'], states: { alpha: 'queued', bravo: 'waiting' } },
  [G_DONE]: { ...base(G_DONE), skippedAsFinished: ['alpha', 'bravo'], states: { alpha: 'done', bravo: 'done' } },
};

// ── the spy engine ───────────────────────────────────────────────────────────────────────────
let performed = [];
let logged = [];
const engine = {
  seedGoal: ({ goal }) => JSON.parse(JSON.stringify(PICKUPS[goal])),
  ticker: { ensureGoalChannel: (subject) => { performed.push(subject); return []; } },
};
const logger = (row) => logged.push(row);

function pass() {
  performed = []; logged = [];
  laneWatch.runLaneWatch({ goalsRoot, engine, logger });
  return {
    alarms: performed.filter((s) => s.decision && s.decision.act === 'goal-alarm').map((s) => s.decision),
    ensures: performed.filter((s) => !s.decision),
  };
}
// The clock, advanced on the alarm's OWN state. Only `since` moves.
function advance(ms) { for (const e of alarm.alarmState.values()) e.since -= ms; }
const OVER = alarm.STALL_MS + 1000;

say(`FIXTURE goals root: ${goalsRoot}`);
say(`THRESHOLD: STALL_MS = ${alarm.STALL_MS} ms (${alarm.STALL_MS / 60000} min)`);
say('');

// ── ARM 1 · THE ALARM FIRES ON A STAGED CONDITION ────────────────────────────────────────────
say('── ARM 1 · the alarm fires on a staged condition ────────────────────────────────────────');
const p1 = pass();
check('pass 1: the condition is seen but has NOT persisted — no alarm yet',
  p1.alarms.length === 0 && alarm.alarmState.size === 3,
  `alarms=${p1.alarms.length} tracked=${[...alarm.alarmState.keys()].sort().join(',')}`);

advance(OVER);
const p2 = pass();
check('pass 2, past the threshold: EVERY frozen goal alarms, and only they',
  p2.alarms.length === 3 && p2.alarms.map((d) => d.goal).sort().join(',') === [G_DEAD, G_REFUSED, G_SKEW].sort().join(','),
  `alarms=${p2.alarms.map((d) => d.goal).sort().join(',')}`);

for (const d of p2.alarms.sort((a, b) => a.goal.localeCompare(b.goal))) {
  const argvOk = d.argv.length === 5
    && d.argv[0] === process.execPath
    && d.argv[1] === path.join(IGNITE_SRC, 'bridges', 'chat', 'goal-channel-cli.js')
    && d.argv[2] === 'post'
    && d.argv[3] === d.goal
    && d.argv[4] === d.text;
  check(`the composed invocation for \`${d.goal}\` is the bridge CLI's own \`post <goal-id> <text…>\``, argvOk);
  say(`  ARGV  ${JSON.stringify(d.argv)}`);
  say(`  TEXT  ${JSON.stringify(d.text)}`);
  say(`  SIG   ${d.signature}   stuckMs=${d.stuckMs}`);
}
check('the message is ONE argv element — newlines survive the CLI\'s `positional.slice(2).join(\' \')`',
  p2.alarms.every((d) => d.argv.length === 5 && d.argv[4].includes('\n')));
check('the journal carries the alarm as a WARN naming the goal, before any launch outcome',
  logged.filter((r) => r.level === 'warn' && /OWNER ALARM/.test(r.message)).length === 3);
say('');

// ── ARM 2 · A HEALTHY GOAL PRODUCES ZERO ALARM ACTIONS ───────────────────────────────────────
say('── ARM 2 · the negative arm — a healthy goal never alarms ────────────────────────────────');
check('neither healthy goal is even TRACKED — the condition never held for them',
  !alarm.alarmState.has(G_OK) && !alarm.alarmState.has(G_DONE),
  `tracked=${[...alarm.alarmState.keys()].sort().join(',')}`);
let healthyAlarms = 0;
for (let i = 0; i < 5; i += 1) { advance(OVER); healthyAlarms += pass().alarms.filter((d) => d.goal === G_OK || d.goal === G_DONE).length; }
check('5 more passes, each past the threshold: ZERO alarms for a goal that is moving or finished',
  healthyAlarms === 0, `healthyAlarms=${healthyAlarms}`);
check('CONTROL — `conditionOf` returns null for both healthy pickups, and non-null for all three frozen ones',
  alarm.conditionOf(PICKUPS[G_OK]) === null && alarm.conditionOf(PICKUPS[G_DONE]) === null
  && [G_SKEW, G_REFUSED, G_DEAD].every((g) => alarm.conditionOf(PICKUPS[g]) !== null));
say('');

// ── ARM 3 · DEDUP ────────────────────────────────────────────────────────────────────────────
say('── ARM 3 · dedup — one message per state, a new message on a state CHANGE ────────────────');
let repeats = 0;
const runs = [];
for (let i = 0; i < 3; i += 1) { advance(OVER); const r = pass(); runs.push(r.alarms.length); repeats += r.alarms.length; }
check('3 consecutive passes over the SAME unchanged stuck state, each past the threshold: ZERO further alarms',
  repeats === 0, `per-pass alarm counts = [${runs.join(', ')}]  (the single alarm was ARM 1 pass 2)`);

// THE STATE CHANGES: a second seat skews. Different signature ⇒ the clock restarts and a new
// message is owed once it too persists.
PICKUPS[G_SKEW].skewed.push({ seat: 'bravo', verdict: 'SKEW', reason: 'live=blocked durable=done' });
const p3 = pass();
check('the state CHANGES (a second seat skews): the clock restarts — not yet a second alarm',
  p3.alarms.length === 0 && alarm.alarmState.get(G_SKEW).signature === 'skew:alpha,bravo',
  `alarms=${p3.alarms.length} signature=${alarm.alarmState.get(G_SKEW).signature}`);
advance(OVER);
const p4 = pass();
check('once the NEW state persists past the threshold, a SECOND alarm fires — and only for it',
  p4.alarms.length === 1 && p4.alarms[0].goal === G_SKEW && p4.alarms[0].signature === 'skew:alpha,bravo',
  `alarms=${p4.alarms.map((d) => `${d.goal}/${d.signature}`).join(',')}`);
say(`  ARGV  ${JSON.stringify(p4.alarms[0].argv)}`);

// UNFREEZE ⇒ REFREEZE is a NEW alarm, not a remembered silence.
const frozenSkew = PICKUPS[G_SKEW];
PICKUPS[G_SKEW] = { ...base(G_SKEW), enqueued: ['alpha'], states: { alpha: 'queued', bravo: 'waiting' } };
pass();
check('the goal UNFREEZES: its dedup entry is dropped entirely, so nothing is remembered',
  !alarm.alarmState.has(G_SKEW));
PICKUPS[G_SKEW] = frozenSkew;
pass(); advance(OVER);
const p5 = pass();
check('it RE-FREEZES for the same old reason: a new alarm fires — a re-freeze is never silent',
  p5.alarms.length === 1 && p5.alarms[0].goal === G_SKEW,
  `alarms=${p5.alarms.map((d) => d.goal).join(',')}`);
say('');

// ── ARM 4 · THE CHANNEL IS ARMED FOR THE GOAL THAT NEVER ADOPTS ──────────────────────────────
say('── ARM 4 · the post has somewhere to land ────────────────────────────────────────────────');
// `frozen-refused` `continue`s before `adopted.push`, so the ordinary run-start ensure never fires
// for it. Without the alarm's own arming call it would have no channel and `post` would exit 1.
check('the alarm armed the goal channel for `frozen-refused`, which NEVER reaches the adoption ensure',
  laneWatch.channelEnsured.has(path.join(goalsRoot, G_REFUSED)));
check('CONTROL — no channel was ever ensured for a healthy CONSOLE-assigned goal (none exists here) '
  + 'and the two healthy daemon goals got theirs from the ordinary adoption path, not from an alarm',
  laneWatch.channelEnsured.has(path.join(goalsRoot, G_OK)) && !alarm.alarmState.has(G_OK));
say('');

// ── ARM 5 · THE WIRE, AND THE BOUND ──────────────────────────────────────────────────────────
say('── ARM 5 · the wire, and the credential bound ────────────────────────────────────────────');
const laneSrc = fs.readFileSync(path.join(IGNITE_SRC, 'engine', 'lane-watch.js'), 'utf8');
const alarmAt = laneSrc.indexOf('alarmOnStall({ goal, goalFolder, pickup, engine, say });');
const refusedAt = laneSrc.indexOf('if (pickup.readinessRefused) {');
check('the alarm is evaluated ABOVE the readiness-refused `continue` — the measured freeze\'s own branch',
  alarmAt > 0 && refusedAt > alarmAt, `alarm@${alarmAt} refused-branch@${refusedAt}`);
check('lane-watch reaches the ONE performer with a decision it did not make — no second performer',
  /engine\.ticker\.ensureGoalChannel/.test(laneSrc) && /perform\(\{ decision \}\)/.test(laneSrc));
const alarmSrc = fs.readFileSync(path.join(IGNITE_SRC, 'server', 'ticker', 'goal-stall-alarm.js'), 'utf8');
check('the alarm module reads NO credential — no token, no SLACK_* env, no `process.env` at all',
  !/SLACK|_TOKEN|process\.env/.test(alarmSrc));
check('it composes the bridge CLI path from `goal-channel-start.js`\'s own constants, not a second answer',
  /require\('\.\/goal-channel-start'\)/.test(alarmSrc) && /IGNITE_SRC, ENSURE_CLI/.test(alarmSrc));
check('the condition is derived from the pickup ONLY — nothing here re-reads coord or the store',
  !/readySeats|execFile|spawn|heartStore/.test(alarmSrc));

say('');

// ── ARM 6 · THE RED ARM — WITHOUT THE WIRE, THE SAME STAGED FREEZE IS SILENT ─────────────────
//
// Every arm above is green. That proves nothing on its own: an arm that would pass with or without
// the change measures nothing. So the SAME staged conditions are driven through a `lane-watch.js`
// with the alarm call REMOVED — the file exactly as it stood before this change — compiled in
// memory under its own filename so its relative requires resolve identically. Nothing is written
// beside the source, and the anchor is asserted present first: a mutation that matched nothing is
// a red arm measuring nothing.
say('── ARM 6 · the red arm — the pre-change pass, same freeze, no alarm ───────────────────────');
const Module = require('node:module');
const LANE_PATH = path.join(IGNITE_SRC, 'engine', 'lane-watch.js');
const ANCHOR = 'alarmOnStall({ goal, goalFolder, pickup, engine, say });';
check('the mutation anchor is present — the red arm is measuring the real call site',
  laneSrc.includes(ANCHOR));
const mut = new Module(LANE_PATH, null);
mut.filename = LANE_PATH;
mut.paths = Module._nodeModulePaths(path.dirname(LANE_PATH));
mut._compile(laneSrc.replace(ANCHOR, '/* the pre-change pass: nothing evaluates the freeze */'), LANE_PATH);
alarm.alarmState.clear();
performed = []; logged = [];
for (let i = 0; i < 4; i += 1) { advance(OVER); mut.exports.runLaneWatch({ goalsRoot, engine, logger }); }
const mutAlarms = performed.filter((sub) => sub.decision && sub.decision.act === 'goal-alarm');
check('WITHOUT the call, 4 passes over three frozen goals produce ZERO alarms — the measured silence',
  mutAlarms.length === 0 && alarm.alarmState.size === 0,
  `alarms=${mutAlarms.length} tracked=${alarm.alarmState.size}`);
check('CONTROL — the mutant pass still RAN and still saw the goals (it seeded and ensured as before)',
  performed.length > 0 && logged.length > 0,
  `performed=${performed.length} logged=${logged.length}`);

const verdict = failures.length ? 'FAIL' : 'PASS';
say('');
say(`SUMMARY: ${lines.filter((l) => l.startsWith('PASS')).length}/${lines.filter((l) => /^(PASS|FAIL)/.test(l)).length} passed`);
say('BOUNDARY: no process spawned, no Slack call made, no live goal touched — the invocation is composed and asserted, never run');
say(`VERDICT: ${verdict}`);
const out = lines.join('\n') + '\n';
fs.writeFileSync(OUT_PATH, out);
process.stdout.write(out);
fs.rmSync(goalsRoot, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
