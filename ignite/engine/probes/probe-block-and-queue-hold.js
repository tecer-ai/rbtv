#!/usr/bin/env node
'use strict';

// probe-block-and-queue-hold — THE MECHANICAL HOLD (owner ruling
// `1-projects/rbtv-sb-merge-refactor-core-build/decisions.md#d-block-and-queue-mechanical-hold`,
// settling the 7.626 `#decision` row).
//
// THE RULING, and therefore the two arms this probe exists to be: a `block-and-queue` seat that
// asks the owner and exits 0 is NOT `done` to the DAG — its dependents do NOT start (HOLD arm) —
// until the answer arrives, and then they DO (PAIRED arm). Before this build the two fallback arms
// were distinguishable at the owner's Slack surface and identical at the DAG.
//
// WHAT IS MEASURED WHERE:
//   · the HOLD, the RELEASE and every neighbouring case that must stay untouched — `hold-scenario.js`
//     beside this file, run as a child against THIS repo (arms H*/P*/C*).
//   · that the arms are not vacuous — the SAME scenario run against two MUTANT copies of `engine/`,
//     each with one line of the guard defanged. A mutant must make bravo START (arms M*).
//   · the ATTACHED lane's own two seams — `evaluateExit` and the foreground carriage — in process
//     (arms A*), because that lane has a terminal carriage the daemon lane does not.
//
// SUBSTITUTED, disclosed up front (`bars.md` 10): no seat PROCESS runs. Executions are synthesized
// through the store's own writers and published through the engine façade's own `publishRecord()`
// (the call the tick and the attached lane's adoption pass both make); the ask is appended to
// `coordination/messages.md` exactly as `coord.py send` appends it. What that leaves unmeasured is
// the ticker's dispatch, which no part of this ruling touches.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-block-and-queue-hold.out');
const SCENARIO = path.join(__dirname, 'hold-scenario.js');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => lines.push(s);
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-bq-hold-'));

// Run the scenario against an ignite root, in a child, with its own fixture dir.
function runScenario(igniteRoot, tag) {
  const dir = path.join(tmp, tag);
  fs.mkdirSync(dir, { recursive: true });
  const raw = execFileSync(process.execPath, [SCENARIO, igniteRoot, dir], { encoding: 'utf8', timeout: 120000 });
  return JSON.parse(raw);
}

// A MUTANT TREE: every entry of `ignite/` symlinked (so `../server`, `../bridges` and
// `node_modules` resolve to the real, unmutated code) except `engine/`, which is copied and then
// edited. One line changes per mutant, and the edit is ASSERTED to have landed — a mutation that
// silently did not apply is a probe that proves nothing (`ponytail:` a sed on source text; if the
// guard is ever reworded, the assertion below goes red rather than the arm going quietly vacuous).
function mutantRoot(tag, from, to) {
  const root = path.join(tmp, `mutant-${tag}`);
  fs.mkdirSync(root, { recursive: true });
  for (const e of fs.readdirSync(IGNITE_SRC)) {
    if (e === 'engine') continue;
    fs.symlinkSync(path.join(IGNITE_SRC, e), path.join(root, e));
  }
  fs.cpSync(path.join(IGNITE_SRC, 'engine'), path.join(root, 'engine'), { recursive: true });
  const targets = ['execution-record.js', 'seeding.js']
    .map((f) => path.join(root, 'engine', f))
    .filter((p) => fs.readFileSync(p, 'utf8').includes(from));
  if (targets.length !== 1) return { root, applied: false, where: `${targets.length} file(s) carry the mutation site` };
  const src = fs.readFileSync(targets[0], 'utf8');
  fs.writeFileSync(targets[0], src.replace(from, to));
  return { root, applied: true, where: path.basename(targets[0]) };
}

function main() {
  say('probe-block-and-queue-hold — the ruling d-block-and-queue-mechanical-hold, measured');
  say(`fixture: ${tmp}`);
  say('');

  // ── V · THE VOCABULARY IS THE FERRY'S, NOT A SECOND SPELLING ────────────────────────────────
  const ferry = require('../../bridges/chat/bus-ferry');
  const rec = require('../execution-record');
  check('V1 the arm this hold keys on IS one of the ferry\'s declared arms — one vocabulary, not two',
    ferry.FALLBACK_ARMS.includes(rec.FALLBACK_BLOCK_AND_QUEUE),
    `${rec.FALLBACK_BLOCK_AND_QUEUE} ∈ ${JSON.stringify(ferry.FALLBACK_ARMS)}`);
  check('V2 the held outcome is the STORE\'s own turn word — no term is minted for this',
    rec.BLOCKED === 'blocked'
      && require('../../server/heart/heart-store').TERMINAL_TURN_STATUSES.has(rec.BLOCKED),
    `outcome word: '${rec.BLOCKED}'`);

  // ── H · THE HOLD ARM ────────────────────────────────────────────────────────────────────────
  say('');
  say('H — a block-and-queue seat asks the owner, exits 0, and its dependent does NOT start');
  const r = runScenario(IGNITE_SRC, 'real');
  check('H0 the wave really started — alpha was due and bravo was not',
    r.seeded.join() === 'alpha', JSON.stringify(r.seeded));
  check('H1 the seat\'s record row says `blocked`, NOT `done` — the outcome no scheduler reads as finished',
    r.recordAfterAsk.join() === 'alpha=blocked', JSON.stringify(r.recordAfterAsk));
  check('H2 THE RULING: its dependent does NOT start — nothing is enqueued while the ask is open',
    r.enqueuedWhileHeld.length === 0 && r.statesWhileHeld.bravo === 'waiting',
    `enqueued ${JSON.stringify(r.enqueuedWhileHeld)} · bravo=${r.statesWhileHeld.bravo}`);
  check('H3 …and the held seat itself is NOT `done` and NOT re-dispatchable',
    r.statesWhileHeld.alpha === 'live', `alpha=${r.statesWhileHeld.alpha}`);
  check('H4 the hold is REPORTED, not silent — an operator can see what the wave is waiting on',
    r.blockedOnOwner.join() === 'alpha', JSON.stringify(r.blockedOnOwner));

  // ── P · THE PAIRED ARM ──────────────────────────────────────────────────────────────────────
  say('');
  say('P — the answer lands (a session at the asking seat\'s own home) and the dependent starts');
  // The answer's own leg, structurally: the bridge homes an `agent`-thread reply at THAT seat.
  const { resolveGoalSeat } = require('../../bridges/chat/forward-path');
  const wsRoot = path.join(tmp, 'real', 'workspace');
  check('P0 the answer leg homes at the ASKING seat — the revival this release depends on exists',
    resolveGoalSeat(wsRoot, 'hold-goal', 'alpha').ok === true,
    JSON.stringify(resolveGoalSeat(wsRoot, 'hold-goal', 'alpha')));
  check('P1 while the REVIVED session runs, the dependent STILL waits — the F6 concurrency is closed',
    r.enqueuedDuringRevival.length === 0 && r.statesDuringRevival.bravo === 'waiting'
      && r.statesDuringRevival.alpha === 'live',
    `enqueued ${JSON.stringify(r.enqueuedDuringRevival)} · ${JSON.stringify(r.statesDuringRevival)}`);
  check('P2 the revived session\'s work lands COHERENTLY in the record — the ask, then the outcome',
    r.recordFinal.join() === 'alpha=blocked,alpha=done', JSON.stringify(r.recordFinal));
  check('P3 THE RULING\'s other half: the dependent DOES start once the seat is answered and finished',
    r.enqueuedAfterAnswer.join() === 'bravo' && r.statesAfterAnswer.alpha === 'done',
    `enqueued ${JSON.stringify(r.enqueuedAfterAnswer)} · alpha=${r.statesAfterAnswer.alpha}`);
  check('P4 the operator escape works too — the SAME held goal is `live` without a `--relaunch` grant and not with it',
    r.relaunchWithout.alpha === 'live' && r.relaunchWith.alpha !== 'live',
    `without=${r.relaunchWithout.alpha} · with=${r.relaunchWith.alpha}`);

  // ── R · THE REVIEW'S THREE FINDINGS, each an arm ────────────────────────────────────────────
  say('');
  say('R — review 51cd2eb: the second hold and its escape (F1), the unreported last word (F2), a');
  say('    genuinely blocked turn that is not a spent hold (F3)');
  check('R-F1 a seat held on its SECOND ask carries a `done` row AND is still held',
    r.secondHoldRecord.join() === 'alpha=blocked,alpha=done,alpha=blocked'
      && r.secondHoldEnqueued.length === 0 && r.secondHoldStates.bravo === 'waiting',
    `${JSON.stringify(r.secondHoldRecord)} · enqueued ${JSON.stringify(r.secondHoldEnqueued)} · bravo=${r.secondHoldStates.bravo}`);
  check('R-F1 …and it is REPORTED as blocked-on-the-owner, never as finished',
    r.secondHoldBlockedOnOwner.join() === 'alpha' && !r.secondHoldSkippedAsFinished.includes('alpha'),
    `blockedOnOwner ${JSON.stringify(r.secondHoldBlockedOnOwner)} · skippedAsFinished ${JSON.stringify(r.secondHoldSkippedAsFinished)}`);
  check('R-F1 …and `--relaunch` RELEASES it — the documented escape, which was a NO-OP for this shape',
    r.secondHoldRelaunch.alpha !== 'live',
    `after the grant alpha=${r.secondHoldRelaunch.alpha}`);
  check('R-F2 a seat whose LAST row is another lane\'s OPEN one is not finished, and IS reported',
    r.foreignOpenRecord.join() === 'alpha=done,alpha=open'
      && r.foreignOpenStates.alpha === 'live'
      && !r.foreignOpenSkippedAsFinished.includes('alpha')
      && r.foreignOpenHeldByOtherLane.join() === 'alpha'
      && r.foreignOpenEnqueued.length === 0,
    `${JSON.stringify(r.foreignOpenRecord)} · alpha=${r.foreignOpenStates.alpha} · heldByOtherLane ${JSON.stringify(r.foreignOpenHeldByOtherLane)} · skippedAsFinished ${JSON.stringify(r.foreignOpenSkippedAsFinished)}`);
  check('R-F3 a turn that genuinely ended `blocked` writes a `blocked` row — the control for the pairing',
    r.turnBlockedFirstRow.join() === 'alpha=blocked', JSON.stringify(r.turnBlockedFirstRow));
  check('R-F3 …and it is NOT a spent hold: the NEXT turn\'s real ask is still held',
    r.turnBlockedRecord.join() === 'alpha=blocked,alpha=blocked'
      && r.turnBlockedEnqueued.length === 0 && r.turnBlockedStates.bravo === 'waiting',
    `${JSON.stringify(r.turnBlockedRecord)} · enqueued ${JSON.stringify(r.turnBlockedEnqueued)} · bravo=${r.turnBlockedStates.bravo}`);

  // ── C · WHAT MUST NOT CHANGE ────────────────────────────────────────────────────────────────
  say('');
  say('C — the neighbouring cases, each of which must behave exactly as it did before');
  const c = r.controls;
  const untouched = (name) => {
    const x = c[name];
    return x.record.join() === 'alpha=done' && x.enqueued.join() === 'bravo';
  };
  check('C1 a block-and-queue seat that NEVER ASKED completed normally — nothing is held',
    untouched('never-asked'), JSON.stringify(c['never-asked']));
  check('C2 `default-and-disclose` is untouched — it proceeds on its default and does not wait',
    untouched('default-and-disclose'), JSON.stringify(c['default-and-disclose']));
  check('C3 `park` is untouched — the ask is parked, the seat proceeds',
    untouched('park'), JSON.stringify(c.park));
  check('C4 a flagged seat with NO declared arm keeps its pre-ruling behaviour — a lint violation gains nothing',
    untouched('no-arm-declared'), JSON.stringify(c['no-arm-declared']));
  check('C5 a seat ANSWERED ON THE BUS before it exited is NOT held — the hold is the UNANSWERED ask',
    untouched('answered-before-exit'), JSON.stringify(c['answered-before-exit']));

  // ── M · THE MUTATIONS ───────────────────────────────────────────────────────────────────────
  say('');
  say('M — the same scenario against a defanged guard: each mutant must let the dependent START');
  //
  // ⚠ EACH MUTANT REVERTS EXACTLY ONE GUARD TO WHAT STOOD BEFORE IT, so these four ARE the
  // red-first proofs for the four fixes — the arm below each is the one the review measured red.
  const mutants = [
    ['outcome', 'the close publishes `done` instead of `blocked`',
      'return held ? { outcome: BLOCKED, held } : { outcome: status, held: null };',
      'return { outcome: status, held: null };',
      (o) => o.enqueuedWhileHeld.join() === 'bravo',
      (o) => `enqueued ${JSON.stringify(o.enqueuedWhileHeld)} · record ${JSON.stringify(o.recordAfterAsk)}`],
    ['predicate', 'seatState stops honouring the record\'s last word',
      'const isDone = (seat) => !(notFinished && notFinished.has(seat))\n    && ((done && done.has(seat)) || seatIsFinished(byJob.get(jobIdFor(seat, goal))));',
      'const isDone = (seat) => ((done && done.has(seat)) || seatIsFinished(byJob.get(jobIdFor(seat, goal))));',
      (o) => o.enqueuedWhileHeld.join() === 'bravo',
      (o) => `enqueued ${JSON.stringify(o.enqueuedWhileHeld)} · record ${JSON.stringify(o.recordAfterAsk)}`],
    // review F1 — the grant bailing on "has a done row" instead of "finished by the last word"
    ['grant', 'the relaunch grant bails on ANY `done` row (review F1)',
      '      if (finished.has(seat)) continue;',
      '      if (done.has(seat)) continue;',
      (o) => o.secondHoldRelaunch.alpha === 'live',
      (o) => `after the grant alpha=${o.secondHoldRelaunch.alpha} (the escape is a NO-OP)`],
    // review F2 — the foreign deletion doing the same, hiding a crashed foreign revival
    ['foreign', 'the foreign deletion outranks a LATER open row (review F2)',
      '  for (const seat of finished) foreign.delete(seat);',
      '  for (const seat of done) foreign.delete(seat);',
      (o) => o.foreignOpenHeldByOtherLane.length === 0,
      (o) => `heldByOtherLane ${JSON.stringify(o.foreignOpenHeldByOtherLane)} · skippedAsFinished ${JSON.stringify(o.foreignOpenSkippedAsFinished)}`],
    // review F2's other half — the report itself claiming the seat is finished
    ['skipped', 'skippedAsFinished reads ANY `done` row (review F2)',
      'seats.filter((s) => view.finished.has(s))',
      'seats.filter((s) => view.done.has(s))',
      (o) => o.foreignOpenSkippedAsFinished.includes('alpha'),
      (o) => `skippedAsFinished ${JSON.stringify(o.foreignOpenSkippedAsFinished)} while states says alpha=${o.foreignOpenStates.alpha}`],
    // review F3 — counting a genuinely blocked turn as a spent hold
    ['spent', 'every `blocked` row counts as a spent hold (review F3)',
      " && doneTurns.has(r['session-id'])",
      '',
      (o) => o.turnBlockedEnqueued.join() === 'bravo',
      (o) => `enqueued ${JSON.stringify(o.turnBlockedEnqueued)} · record ${JSON.stringify(o.turnBlockedRecord)}`],
  ];
  for (const [tag, what, from, to, isRed, detail] of mutants) {
    const m = mutantRoot(tag, from, to);
    if (!check(`M-${tag} the mutation APPLIED (a mutation that did not land proves nothing)`, m.applied, m.where)) continue;
    let out = null;
    let err = null;
    try { out = runScenario(m.root, `run-${tag}`); } catch (e) { err = e.message; }
    check(`M-${tag} RED under the mutant — ${what}`,
      Boolean(out) && isRed(out), err || (out ? detail(out) : 'scenario threw'));
  }

  // ── A · BOTH LANES: the attached lane's own seams ───────────────────────────────────────────
  say('');
  say('A — the ATTACHED lane honours the same hold: one implementation, two attachments');
  const attached = require('../attached-execution');
  const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
  const aTmp = path.join(tmp, 'attached');
  const dataRoot = path.join(aTmp, 'data');
  fs.mkdirSync(dataRoot, { recursive: true });
  const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'), 'utf8'));
  cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
  cfg.default_workdir_root = path.join(aTmp, 'work');
  fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
  cfg.profiles['probe-hold'] = {
    exec: { argv: ['true'], prompt: 'stdin' },
    headed: { tui: { argv: ['true'] } },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: '.rbtv/goals',
    caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
    sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
  };
  const aConfig = path.join(aTmp, 'spawn-profiles.yaml');
  fs.writeFileSync(aConfig, yaml.dump(cfg));

  const goalFolder = path.join(aTmp, 'workspace', '.rbtv', 'goals', 'attached-hold');
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(goalFolder, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), 'taskforce-id,seat,after\ntf-a,alpha,\ntf-a,bravo,alpha\n');
  fs.writeFileSync(path.join(goalFolder, 'seats', 'alpha', 'seat.md'),
    '---\nseat: alpha\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nalpha\n');
  fs.writeFileSync(path.join(goalFolder, 'seats', 'bravo', 'seat.md'), '---\nseat: bravo\n---\n\nbravo\n');
  fs.writeFileSync(path.join(goalFolder, 'execution-mode'), 'interactive\n');

  // alpha is human-interactive in an interactive goal, so the attached lane CARRIES it in the
  // terminal. The injected carriage IS the session: it writes the ask onto the bus and exits 0.
  return attached.executeAttached({
    goalFolder,
    profile: 'probe-hold',
    spawnConfigPath: aConfig,
    tickIntervalMs: 200,
    maxTicks: 2,
    spawnForeground: () => {
      fs.appendFileSync(path.join(goalFolder, 'coordination', 'messages.md'),
        '## 1 | from: alpha | to: owner | type: ask | 2026-08-10 12:00\nwhich way?\n\n');
      return { status: 0 };
    },
  }).then((res) => {
    const rows = require('../execution-record').readExecutionRecord(goalFolder).rows;
    check('A1 the FOREGROUND carriage publishes `blocked` too — the arm is the seat\'s, not the lane\'s',
      rows.map((x) => `${x.seat}=${x.outcome || 'open'}`).join() === 'alpha=blocked',
      JSON.stringify(rows.map((x) => `${x.seat}=${x.outcome || 'open'}/${x.lane}`)));
    const st = attached.statusAttached({ goalFolder });
    check('A2 `--status` reports the hold — alpha not done, bravo waiting, and WHY it is waiting',
      !st.done.includes('alpha') && st.waiting.includes('bravo') && st.blockedOnOwner.join() === 'alpha',
      JSON.stringify({ done: st.done, waiting: st.waiting, blockedOnOwner: st.blockedOnOwner }));
    check('A3 the attached loop RETURNS `blocked` rather than calling the run complete or the seat failed',
      res && res.outcome === 'blocked' && (res.unfinished || []).includes('bravo'),
      JSON.stringify({ outcome: res && res.outcome, unfinished: res && res.unfinished }));
  });
}

Promise.resolve()
  .then(main)
  .catch((err) => { check('probe completed without throwing', false, err && err.stack ? err.stack.split('\n')[0] : String(err)); })
  .then(() => {
    say('');
    say(`checks: ${lines.filter((l) => /^(ok|FAIL)/.test(l)).length} · failures: ${failures.length}`);
    say(`verdict: ${failures.length ? `FAIL — ${failures.join(' | ')}` : 'PASS'}`);
    say(`wall_ms: ${Date.now() - start}`);
    fs.writeFileSync(OUT_PATH, `${lines.join('\n')}\n`);
    process.stdout.write(`${lines.join('\n')}\n`);
    process.exit(failures.length ? 1 : 0);
  });
