'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('./heart/heart-store');
const {
  bind,
  EndingStoreError,
  E_WRITE_ONCE,
  E_KILLED_VOCABULARY,
  copyHeartHome,
} = require('./index');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ending-store-'));
let failed = 0;

function pass(name) {
  process.stdout.write(`PASS ${name}\n`);
}

function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.stack ? err.stack : err}\n`);
}

function openApi() {
  const dbPath = path.join(fs.mkdtempSync(path.join(tmpRoot, 'db-')), 'heart.db');
  const heart = openHeartStore({ dbPath });
  return { heart, api: bind(heart.db), dbPath };
}

function closeApi(heart) {
  heart.close();
  closeHeartStore();
}

function caseArmedLaunchable() {
  const { heart, api } = openApi();
  try {
    const row = api.stampSeatDeclare({
      goal: 'g', seat: 's', ending: 'incomplete', diagnostic: 'context full',
      evidence_pointer: '/tmp/tail',
    });
    if (row.ending !== 'incomplete' || Number(row.armed) !== 1) throw new Error('not armed');
    const ok = api.isLaunchable({
      predecessorsDone: true, ending: row.ending, armed: row.armed, failedTerminal: false,
    });
    if (!ok) throw new Error('armed incomplete should be launchable');
    pass('armed incomplete launchable');
  } finally { closeApi(heart); }
}

function caseDisarmedUntilEvent() {
  const { heart, api } = openApi();
  try {
    const row = api.stampSystem({
      goal: 'g', seat: 's', ending: 'incomplete', diagnostic: 'blocked-on-human',
      evidence_pointer: 'thread-1',
    });
    if (Number(row.armed) !== 0 || row.named_event !== 'ask-answered') {
      throw new Error(`bad disarmed row ${JSON.stringify(row)}`);
    }
    const blocked = api.isLaunchable({
      predecessorsDone: true, ending: row.ending, armed: row.armed, failedTerminal: false,
    });
    if (blocked) throw new Error('disarmed should not be launchable');
    const armed = api.fireNamedEvent({ goal: 'g', seat: 's', named_event: 'ask-answered' });
    const ok = api.isLaunchable({
      predecessorsDone: true, ending: armed.ending, armed: armed.armed, failedTerminal: false,
    });
    if (!ok) throw new Error('should be launchable after named event');
    pass('disarmed not until named event');
  } finally { closeApi(heart); }
}

function caseWaitFromAsk() {
  const { heart, api } = openApi();
  try {
    api.insertAsk({
      ask_id: 'T.1', goal: 'g', seat: 's', label: 'work-content', evidence_pointer: 'permalink',
    });
    if (api.seatWaitingOnOwner({ goal: 'g', seat: 's' })) {
      throw new Error('unposted ask must not create wait');
    }
    api.postAsk({ ask_id: 'T.1' });
    if (!api.seatWaitingOnOwner({ goal: 'g', seat: 's' })) {
      throw new Error('posted open ask should derive wait');
    }
    pass('wait derived from open-ask fixture');
  } finally { closeApi(heart); }
}

function caseWaitAbsentReaped() {
  const { heart, api } = openApi();
  try {
    api.insertAsk({
      ask_id: 'T.2', goal: 'g', seat: 's', label: 'work-content', evidence_pointer: 'permalink',
    });
    api.postAsk({ ask_id: 'T.2' });
    const first = api.reapAndRelaunch({ ask_id: 'T.2' });
    if (first.ask.state !== 'closed') throw new Error('reap did not close');
    if (api.seatWaitingOnOwner({ goal: 'g', seat: 's' })) {
      throw new Error('wait must vanish after reap');
    }
    const again = api.reapAndRelaunch({ ask_id: 'T.2' });
    if (!again.idempotent) throw new Error('second reap must be idempotent');
    pass('wait absent when reaped');
  } finally { closeApi(heart); }
}

function caseWaitAbsentNeverPosted() {
  const { heart, api } = openApi();
  try {
    api.insertAsk({
      ask_id: 'T.3', goal: 'g', seat: 's', label: 'recovery', evidence_pointer: 'permalink',
    });
    if (api.seatWaitingOnOwner({ goal: 'g', seat: 's' })) {
      throw new Error('never-posted ask must not wait');
    }
    pass('wait absent when never posted');
  } finally { closeApi(heart); }
}

function caseGoalRunningWithAsk() {
  const { heart, api } = openApi();
  try {
    api.writeGoalWord({
      goal: 'g', stored: 'running', who_stamped: 'system', evidence_pointer: 'created',
    });
    api.insertAsk({
      ask_id: 'T.4', goal: 'g', seat: 's', label: 'work-content', evidence_pointer: 'permalink',
    });
    api.postAsk({ ask_id: 'T.4' });
    if (!api.isGoalRunning('g')) throw new Error('stored should stay running');
    if (api.goalWaitingOnOwner({ goal: 'g', canAdvance: true })) {
      throw new Error('goal wait must stay off while a lane advances');
    }
    pass('goal running with ask while another lane advances');
  } finally { closeApi(heart); }
}

function caseGoalWaitNothingAdvances() {
  const { heart, api } = openApi();
  try {
    api.writeGoalWord({
      goal: 'g', stored: 'running', who_stamped: 'system', evidence_pointer: 'created',
    });
    api.insertAsk({
      ask_id: 'T.5', goal: 'g', seat: 's', label: 'work-content', evidence_pointer: 'permalink',
    });
    api.postAsk({ ask_id: 'T.5' });
    if (!api.goalWaitingOnOwner({ goal: 'g', canAdvance: false })) {
      throw new Error('goal wait should appear when nothing advances and ask is open');
    }
    pass('goal wait only when nothing advances AND ask open');
  } finally { closeApi(heart); }
}

function caseFailedCrash() {
  const { heart, api } = openApi();
  try {
    if (api.getCurrentEnding({ goal: 'g', seat: 's' })) throw new Error('expected no ending');
    const row = api.stampSystem({
      goal: 'g', seat: 's', ending: 'failed', reason_class: 'crash',
      evidence_pointer: 'exit=1 /tmp/tail',
    });
    if (row.ending !== 'failed' || row.reason_class !== 'crash' || row.who_stamped !== 'system') {
      throw new Error(`bad crash stamp ${JSON.stringify(row)}`);
    }
    pass('dead-process + no ending → failed:crash');
  } finally { closeApi(heart); }
}

function caseDoneMissingOutput() {
  const { heart, api } = openApi();
  try {
    const missing = path.join(tmpRoot, 'no-such-output.md');
    const row = api.stampSeatDeclare({
      goal: 'g', seat: 's', ending: 'done',
      evidence_pointer: missing,
      declared_outputs: [missing],
    });
    if (row.ending !== 'failed' || row.reason_class !== 'outputs-missing') {
      throw new Error(`expected outputs-missing, got ${JSON.stringify(row)}`);
    }
    if (row.who_stamped !== 'system') throw new Error('outputs-missing must be system');
    pass('done with missing output → failed: outputs-missing');
  } finally { closeApi(heart); }
}

function caseWriteOnce() {
  const { heart, api } = openApi();
  try {
    api.stampSeatDeclare({
      goal: 'g', seat: 's', ending: 'incomplete', diagnostic: 'context full',
      evidence_pointer: '/tmp/tail',
    });
    let refused = false;
    try {
      api.stampSeatDeclare({
        goal: 'g', seat: 's', ending: 'incomplete', diagnostic: 'context full',
        evidence_pointer: '/tmp/tail2',
      });
    } catch (err) {
      if (err instanceof EndingStoreError && err.code === E_WRITE_ONCE) refused = true;
      else throw err;
    }
    if (!refused) throw new Error('second stamp was not refused');
    const replaced = api.replaceSeatEnding({
      goal: 'g', seat: 's', ending: 'done', who_stamped: 'seat',
      evidence_pointer: '/tmp/out',
      declared_outputs: [],
    });
    if (replaced.ending !== 'done') throw new Error('replace sitting failed');
    pass('write-once (second stamp refused)');
  } finally { closeApi(heart); }
}

function caseKilledVocab() {
  const { heart, api } = openApi();
  try {
    let refused = false;
    try {
      api.stampSeatDeclare({
        goal: 'g', seat: 's', ending: 'renew', evidence_pointer: '/tmp/x',
      });
    } catch (err) {
      if (err instanceof EndingStoreError && err.code === E_KILLED_VOCABULARY) refused = true;
      else throw err;
    }
    if (!refused) throw new Error('killed ending was accepted');
    pass('killed vocabulary refused');
  } finally { closeApi(heart); }
}

function caseCopyHome() {
  const { DatabaseSync } = require('node:sqlite');
  const srcDir = fs.mkdtempSync(path.join(tmpRoot, 'src-'));
  const srcDb = path.join(srcDir, 'old.db');
  const src = new DatabaseSync(srcDb);
  src.exec(`
    CREATE TABLE jobs_log (
      exec_id INTEGER PRIMARY KEY,
      job_id TEXT NOT NULL,
      action_type TEXT NOT NULL,
      args TEXT NOT NULL,
      enqueued_by TEXT NOT NULL,
      session_mode TEXT NOT NULL DEFAULT 'headless',
      fired_tick INTEGER NOT NULL,
      fired_at TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'launching'
    );
    INSERT INTO jobs_log (job_id, action_type, args, enqueued_by, fired_tick, fired_at, status)
    VALUES ('j1','fire-tool','{}','tester',1,'2026-08-24T00:00:00Z','done');
  `);
  src.close();
  const destDb = path.join(fs.mkdtempSync(path.join(tmpRoot, 'dest-')), 'heart.db');
  const result = copyHeartHome({ daemonDb: srcDb, destDb });
  if (!fs.existsSync(destDb)) throw new Error('dest missing');
  const dest = new DatabaseSync(destDb, { readOnly: true });
  const n = dest.prepare('SELECT count(*) AS n FROM jobs_log').get().n;
  dest.close();
  if (Number(n) !== 1) throw new Error(`expected 1 copied jobs_log row, got ${n}`);
  if (!result.copied.daemon_src || result.copied.daemon_src.jobs_log !== 1) {
    throw new Error(`copy report ${JSON.stringify(result)}`);
  }
  pass('one-shot copy-home copies jobs_log');
}

function caseAbandonSeat() {
  const { heart, api } = openApi();
  try {
    if (api.getSeatAbandonment({ goal: 'g', seat: 's' })) throw new Error('expected no abandonment');
    const first = api.abandonSeat({
      goal: 'g', seat: 's', anchor: 'owner: drop-lane, this lane is stuck for good', abandoned_by: 'owner',
    });
    if (first.idempotent) throw new Error('first abandonment must not report idempotent');
    if (!first.abandonment || first.abandonment.seat !== 's') {
      throw new Error(`bad abandonment row ${JSON.stringify(first)}`);
    }
    const read = api.getSeatAbandonment({ goal: 'g', seat: 's' });
    if (!read || read.anchor !== first.abandonment.anchor) throw new Error('read-back mismatch');
    // Permanent, no undo: a second call on the same lane returns the FIRST row unchanged, never a
    // second ruling — even when the caller supplies a different reason.
    const again = api.abandonSeat({
      goal: 'g', seat: 's', anchor: 'a different reason', abandoned_by: 'owner',
    });
    if (!again.idempotent) throw new Error('second abandonment of the same lane must be idempotent');
    if (again.abandonment.anchor !== first.abandonment.anchor) {
      throw new Error('idempotent abandonment must not overwrite the first ruling');
    }
    if (api.getSeatAbandonment({ goal: 'g', seat: 'other' })) throw new Error('other seat must stay clean');
    pass('abandonSeat: write, read-back, idempotent on retry, never overwrites');
  } finally { closeApi(heart); }
}

function caseTablesHosted() {
  const { heart } = openApi();
  try {
    const names = heart.db.prepare(
      "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('seat_endings','goal_states','open_asks','seat_endings_log')",
    ).all().map((r) => r.name).sort();
    const want = ['goal_states', 'open_asks', 'seat_endings', 'seat_endings_log'];
    if (names.join(',') !== want.join(',')) throw new Error(`tables ${names.join(',')}`);
    pass('tables hosted in heart.db');
  } finally { closeApi(heart); }
}

const cases = [
  caseTablesHosted,
  caseArmedLaunchable,
  caseDisarmedUntilEvent,
  caseWaitFromAsk,
  caseWaitAbsentReaped,
  caseWaitAbsentNeverPosted,
  caseGoalRunningWithAsk,
  caseGoalWaitNothingAdvances,
  caseFailedCrash,
  caseDoneMissingOutput,
  caseWriteOnce,
  caseKilledVocab,
  caseCopyHome,
  caseAbandonSeat,
];

for (const fn of cases) {
  try { fn(); } catch (err) { fail(fn.name, err); }
}

try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* tmp */ }

if (failed) {
  process.stdout.write(`${failed} FAIL\n`);
  process.exit(1);
}
process.stdout.write('ALL PASS\n');
