'use strict';

// -- SELFTESTS FOR `owed-from-endings.js`'s CLASS B FIX -------------------------------------------
//
// Defect B (the `stools-canvas-audio-elevenlabs-close` incident, 2026-08-28): class B's "unread"
// test compared a message's MINUTE-precision timestamp against the chair's last CHECK-IN, not
// against the chair's own READ CURSOR (`workers.md`'s `lastread` cell, coord `persist_cursor`).
// Check-in and `coordinate read` land in the same daemon-lane sitting seconds apart, so a message
// stamped in that same minute read as "after check-in" and was filed READ FOREVER even when the
// sitting died before ever calling `read` - merely checking in discharged the wake.
//
// Three arms, matching the seat's definition of done:
//   (1) a message stamped in the CHECK-IN MINUTE but AFTER the read cursor -> the chair is class B
//       (woken). This is the exact incident shape: check-in and the driving message share a minute.
//   (2) a message BEFORE the cursor -> NOT woken (the cursor fix must not over-wake either).
//   (3) after N dead passes on the SAME unread mail, the existing attempt-counter brake (wired
//       generically in `reconcile.js`, untouched here) holds and stops the wake - named by its
//       counter row.
//
// `owedFromLedgers` (reconcile.js) is reused rather than re-derived: it is the real wiring
// (`loadSessions`, `loadMessages`, `checkinOf`, `tsAfter`, `STAFF_CHAIRS`, ...) every production
// caller of `classifyOwed` goes through, so a fixture built against it exercises this file exactly
// the way `reconcile.js` does.

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { owedFromLedgers } = require('./reconcile');
const { readCursor } = require('./owed-from-endings');
const counters = require('./attempt-counters');
const { seedRecoveryConfig, loadRecoveryConfig } = require('./recovery-config');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'owed-from-endings-selftest-'));
let failed = 0;
function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.stack ? err.stack : err}\n`);
}

function writeSessions(goalFolder, rows) {
  const cols = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
    'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
    'disposition-writer', 'execution', 'checkin', 'model', 'hold-anchor'];
  const linesOut = [cols.join(',')];
  for (const r of rows) {
    linesOut.push(cols.map((c) => (r[c] == null ? '' : String(r[c]).replace(/,/g, ' '))).join(','));
  }
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'), `${linesOut.join('\n')}\n`);
}

function writeMessages(goalFolder, blocks) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const parts = ['# messages\n'];
  for (const b of blocks) {
    parts.push(`## ${b.num} | from: ${b.sender} | to: ${b.to} | type: ${b.type} | ${b.ts}`);
    parts.push('');
    parts.push(b.body || 'body');
    parts.push('');
  }
  fs.writeFileSync(path.join(dir, 'messages.md'), parts.join('\n'));
}

// workers.md, coord/messages.py's own row shape:
// | agent | active | pane | summary | checkin | checkout | lastread |
function writeWorkers(goalFolder, rows) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const header = '| agent | active | pane | summary | checkin | checkout | lastread |\n'
    + '|---|---|---|---|---|---|---|\n';
  const body = rows.map((r) => `| ${r.agent} | ${r.active || 'yes'} | | | ${r.checkin || ''} | ${r.checkout || ''} | ${r.lastread == null ? '' : r.lastread} |`).join('\n');
  fs.writeFileSync(path.join(dir, 'workers.md'), header + body + '\n');
}

const readyEmpty = { ready: new Map(), granted: new Map(), rows: [], reason: null };

// -- (1) SAME-MINUTE AS CHECK-IN, AFTER THE CURSOR -> WOKEN ---------------------------------------
function caseUnreadAfterCursorSameMinuteAsCheckin() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'g1-'));
  // Sitting 10's own shape: checked in at 22:17, cursor kept at #43 (it never called `read`), and
  // message #45 is stamped in that SAME minute.
  writeSessions(goalFolder, [
    { 'session-id': 's10', seat: 'leader', started: '2026-08-28T22:17:39Z', checkin: '2026-08-28 22:17' },
  ]);
  writeWorkers(goalFolder, [{ agent: 'leader', checkin: '2026-08-28 22:17', lastread: 43 }]);
  writeMessages(goalFolder, [
    { num: 43, sender: 'boundary-auditor', to: 'leader', type: 'note', ts: '2026-08-28 21:00' },
    { num: 45, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-28 22:17' },
  ]);
  try {
    const d = owedFromLedgers(goalFolder, { readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map() });
    const leaderRow = d.classB.find((x) => x.seat === 'leader');
    assert.ok(leaderRow, `leader must be class B (woken) — got classB=${JSON.stringify(d.classB)}`);
    assert.strictEqual(leaderRow.lastNum, 45, `lastNum must be the unread message's own number, got ${leaderRow.lastNum}`);
    pass('(1) a message stamped in the check-in MINUTE but after the read cursor wakes the chair (class B)');
  } catch (err) { fail('(1) unread-after-cursor-same-minute', err); }
}

// -- (2) BEFORE THE CURSOR -> NOT WOKEN ------------------------------------------------------------
function caseReadMessageBeforeCursorNotWoken() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'g2-'));
  writeSessions(goalFolder, [
    { 'session-id': 's11', seat: 'leader', started: '2026-08-28T22:17:39Z', checkin: '2026-08-28 22:17' },
  ]);
  // The cursor has already advanced PAST message #45 — it was shown and read.
  writeWorkers(goalFolder, [{ agent: 'leader', checkin: '2026-08-28 22:17', lastread: 45 }]);
  writeMessages(goalFolder, [
    { num: 45, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-28 22:17' },
  ]);
  try {
    const d = owedFromLedgers(goalFolder, { readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map() });
    const leaderRow = d.classB.find((x) => x.seat === 'leader');
    assert.strictEqual(leaderRow, undefined, `an already-read message must NOT wake the chair — got ${JSON.stringify(leaderRow)}`);
    pass('(2) a message the cursor has already passed does NOT wake the chair');
  } catch (err) { fail('(2) read-message-not-woken', err); }
}

// -- (3) AFTER N DEAD PASSES ON THE SAME MAIL, THE ATTEMPT-COUNTER BRAKE HOLDS --------------------
//
// This composes the FIXED class B output with the EXISTING, untouched attempt-counter API exactly
// the way `reconcile.js` wires it (`driverFor('unread') === RECONCILE_RESPAWN`, `items: ['#lastNum']`
// — reconcile.js:983-991/1187-1206). Three identical dead passes (same messages, same never-moving
// cursor — the chair keeps dying before it can call `read`) must reach `attempts >= n` and read
// `exhausted: true`; a caller (reconcile.js, unedited here) will not launch on an exhausted row.
function caseBrakeHoldsAfterNDeaths() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'g3-'));
  writeSessions(goalFolder, [
    { 'session-id': 's12', seat: 'leader', started: '2026-08-28T22:17:39Z', checkin: '2026-08-28 22:17' },
  ]);
  writeWorkers(goalFolder, [{ agent: 'leader', checkin: '2026-08-28 22:17', lastread: 43 }]);
  writeMessages(goalFolder, [
    { num: 45, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-28 22:17' },
  ]);
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'g3-ws-'));
  seedRecoveryConfig(workspaceRoot);
  const recovery = loadRecoveryConfig({ workspace: workspaceRoot });
  const countersFile = path.join(workspaceRoot, 'attempt-counters.json');
  try {
    let last = null;
    for (let i = 0; i < recovery.attempt_counter_n; i += 1) {
      const d = owedFromLedgers(goalFolder, { readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map() });
      const leaderRow = d.classB.find((x) => x.seat === 'leader');
      assert.ok(leaderRow, `pass ${i + 1}: the chair must still be reported as owed unread mail — the counter cannot count a wake that never happened`);
      last = counters.countAttempt({
        driver: counters.DRIVERS.RECONCILE_RESPAWN,
        goal: 'g3-goal',
        seat: 'leader',
        reasonClass: 'unread',
        n: recovery.attempt_counter_n,
        items: [`#${leaderRow.lastNum}`],
      }, { countersFile });
    }
    assert.strictEqual(last.exhausted, true,
      `after ${recovery.attempt_counter_n} identical dead passes the brake must hold, got attempts=${last.attempts}/${last.n}`);
    const row = counters.peekCounter(
      { driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'g3-goal', seat: 'leader', reasonClass: 'unread' },
      { countersFile },
    );
    assert.ok(row, 'the counter row must be readable by name after exhaustion');
    assert.strictEqual(row.attempts, recovery.attempt_counter_n);
    pass(`(3) after ${recovery.attempt_counter_n} dead passes on the SAME mail the brake holds — counter row reconcile-respawn/g3-goal/leader/unread, attempts=${row.attempts}`);
  } catch (err) { fail('(3) brake holds after N deaths', err); }
}

// -- RED (1)/(3) — reverting the cursor comparison to the pre-fix checkin/tsAfter shape reproduces
// the incident: the same-minute message is filed "read" forever, so arm (1) never wakes the chair
// and arm (3)'s counter never even gets a first attempt to count — the goal stays silently frozen,
// exactly `stools-canvas-audio-elevenlabs-close` on 2026-08-28.
function caseRedRevertToCheckinLogic() {
  try {
    const src = fs.readFileSync(path.join(__dirname, 'owed-from-endings.js'), 'utf8');
    const ANCHOR = "const cursor = readCursor(goalFolder, chair);\n    const unread = messages.filter((m) => m.to === chair && m.sender !== chair\n      && m.sender !== SYSTEM_MAIL_SENDER\n      && (cursor === null || m.num > cursor));";
    assert.ok(src.includes(ANCHOR), 'class B cursor-comparison anchor missing');
    const REVERTED = "const since = checkinOf(last.get(chair));\n    const unread = messages.filter((m) => m.to === chair && m.sender !== chair\n      && m.sender !== SYSTEM_MAIL_SENDER\n      && (!since || tsAfter(m.ts, since)));";
    const Module = require('node:module');
    const mut = new Module(path.join(__dirname, 'owed-from-endings.js'), null);
    mut.filename = path.join(__dirname, 'owed-from-endings.js');
    mut.paths = Module._nodeModulePaths(__dirname);
    mut._compile(src.replace(ANCHOR, REVERTED), mut.filename);

    const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'gred1-'));
    writeSessions(goalFolder, [
      { 'session-id': 's13', seat: 'leader', started: '2026-08-28T22:17:39Z', checkin: '2026-08-28 22:17' },
    ]);
    writeWorkers(goalFolder, [{ agent: 'leader', checkin: '2026-08-28 22:17', lastread: 43 }]);
    writeMessages(goalFolder, [
      { num: 45, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-28 22:17' },
    ]);
    const { loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter } = require('./reconcile');
    const d = mut.exports.classifyOwed(goalFolder, {
      readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map(),
      loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter,
      STAFF_CHAIRS: ['leader', 'goal-master'], SYSTEM_MAIL_SENDER: 'ignite-daemon',
    });
    const leaderRow = d.classB.find((x) => x.seat === 'leader');
    assert.strictEqual(leaderRow, undefined,
      `RED: reverting to checkin/tsAfter must reproduce the incident — the same-minute message must wrongly read as already-read, got ${JSON.stringify(leaderRow)}`);
    pass('(RED 1/3) reverting to the pre-fix checkin/tsAfter comparison reproduces the freeze (no wake, ever)');
  } catch (err) { fail('(RED 1/3) revert to checkin logic', err); }
}

// -- RED (2) — a cursor read that ignores the file (always answers 0) over-wakes on already-read mail
function caseRedCursorAlwaysZero() {
  try {
    const src = fs.readFileSync(path.join(__dirname, 'owed-from-endings.js'), 'utf8');
    const ANCHOR = 'function readCursor(goalFolder, chair) {';
    assert.ok(src.includes(ANCHOR), 'readCursor anchor missing');
    const mutatedSrc = src.replace(ANCHOR, `${ANCHOR}\n  return 0; // eslint-disable-line no-unreachable`);
    const Module = require('node:module');
    const mut = new Module(path.join(__dirname, 'owed-from-endings.js'), null);
    mut.filename = path.join(__dirname, 'owed-from-endings.js');
    mut.paths = Module._nodeModulePaths(__dirname);
    mut._compile(mutatedSrc, mut.filename);

    const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'gred2-'));
    writeSessions(goalFolder, [
      { 'session-id': 's14', seat: 'leader', started: '2026-08-28T22:17:39Z', checkin: '2026-08-28 22:17' },
    ]);
    writeWorkers(goalFolder, [{ agent: 'leader', checkin: '2026-08-28 22:17', lastread: 45 }]);
    writeMessages(goalFolder, [
      { num: 45, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-28 22:17' },
    ]);
    const { loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter } = require('./reconcile');
    const d = mut.exports.classifyOwed(goalFolder, {
      readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map(),
      loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter,
      STAFF_CHAIRS: ['leader', 'goal-master'], SYSTEM_MAIL_SENDER: 'ignite-daemon',
    });
    const leaderRow = d.classB.find((x) => x.seat === 'leader');
    assert.ok(leaderRow, `RED: a cursor stuck at 0 must wrongly re-wake on an already-read message, got ${JSON.stringify(leaderRow)}`);
    pass('(RED 2) a cursor read that ignores workers.md (always 0) over-wakes on already-read mail');
  } catch (err) { fail('(RED 2) cursor always zero', err); }
}

caseUnreadAfterCursorSameMinuteAsCheckin();
caseReadMessageBeforeCursorNotWoken();
caseBrakeHoldsAfterNDeaths();
caseRedRevertToCheckinLogic();
caseRedCursorAlwaysZero();

try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* tmp */ }

if (failed) {
  process.stdout.write(`${failed} FAIL\n`);
  process.exit(1);
}
process.stdout.write('ALL PASS\n');
