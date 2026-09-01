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
// Four arms, matching the seat's definition of done:
//   (1) a message stamped in the CHECK-IN MINUTE but AFTER the read cursor -> the chair is class B
//       (woken). This is the exact incident shape: check-in and the driving message share a minute.
//   (2) a message BEFORE the cursor -> NOT woken (the cursor fix must not over-wake either).
//   (3) after N dead passes on the SAME unread mail, `classifyOwed` ITSELF stops reporting the
//       chair as owed - the (N+1)th pass shows an empty class B, named by the counter row that
//       exhausted it. `reconcile.js`'s OWN `counterDisarmed` gate (unedited) only compares
//       `attempts >= n` with no frontier check, so it cannot tell stale mail from new mail landing
//       on an exhausted lane, and a caller of `deriveOwed` other than reconcile's own launch loop
//       saw `owed: true` regardless. `unreadFrontierExhausted` reads the SAME ledger `reconcile.js`
//       already writes (`RECONCILE_RESPAWN` driver, `<goal>/<chair>` subject, `unread` reason
//       class) and adds the missing frontier check at the wake itself.
//   (4) a FRONTIER ADVANCE (new, higher-numbered mail arrives) is not held by the brake - the
//       exhausted attempts were spent on the OLD frontier, and new work is owed a first attempt,
//       exactly as `attempt-counters.js#isRetryOf` already treats it for the write side.
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
const { readCursor, FINISH_MARKER } = require('./owed-from-endings');
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

function withWorkspaceRoot(root, fn) {
  const prev = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = root;
  try { return fn(); } finally {
    if (prev === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prev;
  }
}

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

// -- (5) `workers.md` CARRIES ONE ROW PER SITTING — THE CURSOR IS THE NEWEST ROW'S, NEVER THE FIRST
//
// `meet-transcript-summarizer-planning`, 2026-08-30: 8 leader rows, append-only (`coord/checkout.py
// #cmd_checkin` never rewrites an old row; `coord/messages.py#current_row` — "Latest row for an
// agent (last check-in wins)" — is `mine[-1]`, the LAST match). The first cut of `readCursor`
// returned on the FIRST matching line instead and answered sitting 1's cursor (0) forever, so
// every message #1-#25 read as unread on every pass after sitting 8 had already read them all
// (cursor 25) — two paid relaunches with no new mail before an orchestrator `supervise hold`
// stopped the loop.
function caseCursorIsNewestRowNotFirst() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'g5-'));
  writeSessions(goalFolder, [
    { 'session-id': 's1', seat: 'leader', started: '2026-08-30T10:00:00Z', checkin: '2026-08-30 10:00' },
    { 'session-id': 's2', seat: 'leader', started: '2026-08-30T11:00:00Z', checkin: '2026-08-30 11:00' },
    { 'session-id': 's3', seat: 'leader', started: '2026-08-30T12:00:00Z', checkin: '2026-08-30 12:00' },
  ]);
  // Three rows, append order = check-in order: cursor only ever grows (0 -> 9 -> 25), exactly the
  // shape `cmd_checkin`'s own "inherit the highest prior cursor" invariant guarantees.
  writeWorkers(goalFolder, [
    { agent: 'leader', checkin: '2026-08-30 10:00', lastread: 0 },
    { agent: 'leader', checkin: '2026-08-30 11:00', lastread: 9 },
    { agent: 'leader', checkin: '2026-08-30 12:00', lastread: 25 },
  ]);
  try {
    assert.strictEqual(readCursor(goalFolder, 'leader'), 25,
      `readCursor must answer the NEWEST row's cursor (25), not the first row's (0)`);

    const messagesUpTo25 = Array.from({ length: 25 }, (_, i) => ({
      num: i + 1, sender: 'boundary-auditor', to: 'leader', type: 'note', ts: '2026-08-30 09:00',
    }));
    writeMessages(goalFolder, messagesUpTo25);
    const notOwed = owedFromLedgers(goalFolder, { readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map() });
    assert.strictEqual(notOwed.classB.find((x) => x.seat === 'leader'), undefined,
      `mail up to #25 is already read by the newest sitting — must NOT be class B, got ${JSON.stringify(notOwed.classB)}`);

    writeMessages(goalFolder, [
      ...messagesUpTo25,
      { num: 26, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-30 13:00' },
    ]);
    const owed = owedFromLedgers(goalFolder, { readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map() });
    const leaderRow = owed.classB.find((x) => x.seat === 'leader');
    assert.ok(leaderRow, `mail #26, past every row's cursor, must wake the chair — got classB=${JSON.stringify(owed.classB)}`);
    assert.strictEqual(leaderRow.lastNum, 26, `must name the true unread frontier, got ${leaderRow.lastNum}`);
    pass('(5) an 8-sitting-shaped workers.md reads the NEWEST row\'s cursor: mail up to #25 not owed, #26 owed');
  } catch (err) { fail('(5) cursor is the newest row, not the first', err); }
}

// -- RED (5) — returning on the FIRST matching row reproduces the live incident exactly ------------
function caseRedFirstRowReturn() {
  try {
    const src = fs.readFileSync(path.join(__dirname, 'owed-from-endings.js'), 'utf8');
    const CURRENT_BODY = [
      "function readCursor(goalFolder, chair) {",
      "  let text;",
      "  try { text = fs.readFileSync(workersPath(goalFolder), 'utf8'); } catch { return null; }",
      "  let newestValue = null; // the LAST matching row's own cell, numeric or not (null if not numeric)",
      "  let bestNumeric = null; // the highest numeric cursor this chair's history has ever reached",
      "  for (const line of text.split('\\n')) {",
      "    const m = line.match(WORKER_ROW);",
      "    if (!m || m[1] !== chair) continue;",
      "    const numeric = /^\\d+$/.test(m[2]) ? Number(m[2]) : null;",
      "    newestValue = numeric;",
      "    if (numeric !== null && (bestNumeric === null || numeric > bestNumeric)) bestNumeric = numeric;",
      "  }",
      "  // The newest row's own value wins whenever it is numeric — it is what `cmd_checkin`/`persist_",
      "  // cursor` last wrote for THIS sitting. Only a non-numeric newest row falls back to history.",
      "  return newestValue !== null ? newestValue : bestNumeric;",
      "}",
    ].join('\n');
    assert.ok(src.includes(CURRENT_BODY), 'readCursor body anchor missing');
    // The pre-fix shape: return on the FIRST matching line, exactly the live 2026-08-30 defect.
    const BUGGY_BODY = [
      "function readCursor(goalFolder, chair) {",
      "  let text;",
      "  try { text = fs.readFileSync(workersPath(goalFolder), 'utf8'); } catch { return null; }",
      "  for (const line of text.split('\\n')) {",
      "    const m = line.match(WORKER_ROW);",
      "    if (!m || m[1] !== chair) continue;",
      "    return /^\\d+$/.test(m[2]) ? Number(m[2]) : null;",
      "  }",
      "  return null;",
      "}",
    ].join('\n');
    const mutatedSrc = src.replace(CURRENT_BODY, BUGGY_BODY);
    assert.ok(mutatedSrc !== src, 'mutation did not change the source — anchor replace failed');
    const Module = require('node:module');
    const mut = new Module(path.join(__dirname, 'owed-from-endings.js'), null);
    mut.filename = path.join(__dirname, 'owed-from-endings.js');
    mut.paths = Module._nodeModulePaths(__dirname);
    mut._compile(mutatedSrc, mut.filename);

    const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'gred5-'));
    writeWorkers(goalFolder, [
      { agent: 'leader', checkin: '2026-08-30 10:00', lastread: 0 },
      { agent: 'leader', checkin: '2026-08-30 11:00', lastread: 9 },
      { agent: 'leader', checkin: '2026-08-30 12:00', lastread: 25 },
    ]);
    const cursor = mut.exports.readCursor(goalFolder, 'leader');
    assert.strictEqual(cursor, 0,
      `RED: returning on the first matching row must reproduce the incident (cursor stuck at 0), got ${cursor}`);
    pass('(RED 5) returning on the FIRST matching workers.md row reproduces the incident (cursor stuck at the oldest sitting\'s)');
  } catch (err) { fail('(RED 5) first-row return', err); }
}

// -- (3) AFTER N DEAD PASSES ON THE SAME MAIL, THE ATTEMPT-COUNTER BRAKE HOLDS --------------------
//
// `n` identical dead passes drive the SAME ledger `reconcile.js` writes to
// (`driverFor('unread') === RECONCILE_RESPAWN`, subject `<goal>/leader`, `items: ['#lastNum']` —
// reconcile.js:983-991/1187-1206, simulated here since reconcile.js itself is untouched and not
// under test). The (n+1)th pass must show `classifyOwed` ITSELF excluding the chair from class B —
// the wake stops at its source, named by the counter row that exhausted it — not merely "a
// downstream launcher declines to act on an owed row it still sees".
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
  const goal = 'g3-goal';
  try {
    withWorkspaceRoot(workspaceRoot, () => {
      for (let i = 0; i < recovery.attempt_counter_n; i += 1) {
        const d = owedFromLedgers(goalFolder, {
          readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map(), goal, countersFile,
        });
        const leaderRow = d.classB.find((x) => x.seat === 'leader');
        assert.ok(leaderRow, `pass ${i + 1}: the chair must still be reported as owed unread mail — the counter cannot count a wake that never happened`);
        counters.countAttempt({
          driver: counters.DRIVERS.RECONCILE_RESPAWN,
          goal,
          seat: 'leader',
          reasonClass: 'unread',
          n: recovery.attempt_counter_n,
          items: [`#${leaderRow.lastNum}`],
        }, { countersFile });
      }
      // pass n+1 — same frontier (#45), same everything: the brake must now hold at the SOURCE.
      const dNext = owedFromLedgers(goalFolder, {
        readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map(), goal, countersFile,
      });
      assert.strictEqual(dNext.classB.find((x) => x.seat === 'leader'), undefined,
        `RED-if-failing: pass ${recovery.attempt_counter_n + 1} must NOT wake the chair on the same exhausted frontier, got classB=${JSON.stringify(dNext.classB)}`);
      const row = counters.peekCounter(
        { driver: counters.DRIVERS.RECONCILE_RESPAWN, goal, seat: 'leader', reasonClass: 'unread' },
        { countersFile },
      );
      assert.ok(row, 'the counter row must be readable by name after exhaustion');
      assert.strictEqual(row.attempts, recovery.attempt_counter_n);
      pass(`(3) after ${recovery.attempt_counter_n} dead passes on the SAME mail, pass ${recovery.attempt_counter_n + 1} does NOT wake — counter row reconcile-respawn/${goal}/leader/unread, attempts=${row.attempts}`);
    });
  } catch (err) { fail('(3) brake holds after N deaths', err); }
}

// -- (4) A FRONTIER ADVANCE IS NOT HELD BY THE BRAKE ----------------------------------------------
//
// Continuing from an EXHAUSTED lane (arm 3's exact ledger state): new, higher-numbered mail is a
// first attempt at different work, never a retry of what exhausted the counter — the row's
// `owed_items` still names the OLD frontier (`#45`), so the new frontier (`#46`) does not match it.
function caseFrontierAdvanceResets() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'g4-'));
  writeSessions(goalFolder, [
    { 'session-id': 's13', seat: 'leader', started: '2026-08-28T22:17:39Z', checkin: '2026-08-28 22:17' },
  ]);
  writeWorkers(goalFolder, [{ agent: 'leader', checkin: '2026-08-28 22:17', lastread: 43 }]);
  writeMessages(goalFolder, [
    { num: 45, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-28 22:17' },
  ]);
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'g4-ws-'));
  seedRecoveryConfig(workspaceRoot);
  const recovery = loadRecoveryConfig({ workspace: workspaceRoot });
  const countersFile = path.join(workspaceRoot, 'attempt-counters.json');
  const goal = 'g4-goal';
  try {
    withWorkspaceRoot(workspaceRoot, () => {
      // Exhaust the lane on frontier #45, exactly as arm 3.
      for (let i = 0; i < recovery.attempt_counter_n; i += 1) {
        counters.countAttempt({
          driver: counters.DRIVERS.RECONCILE_RESPAWN, goal, seat: 'leader', reasonClass: 'unread',
          n: recovery.attempt_counter_n, items: ['#45'],
        }, { countersFile });
      }
      const exhausted = owedFromLedgers(goalFolder, {
        readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map(), goal, countersFile,
      });
      assert.strictEqual(exhausted.classB.find((x) => x.seat === 'leader'), undefined,
        'setup check: the lane must be exhausted on #45 before the frontier advances');

      // NEW mail arrives — a higher message number never counted before.
      writeMessages(goalFolder, [
        { num: 45, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-28 22:17' },
        { num: 46, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-29 09:00' },
      ]);
      const advanced = owedFromLedgers(goalFolder, {
        readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map(), goal, countersFile,
      });
      const leaderRow = advanced.classB.find((x) => x.seat === 'leader');
      assert.ok(leaderRow, `a frontier advance past the exhausted mail must wake the chair for the NEW work, got classB=${JSON.stringify(advanced.classB)}`);
      assert.strictEqual(leaderRow.lastNum, 46, `the wake must name the NEW frontier, got ${leaderRow.lastNum}`);
      pass('(4) a frontier advance (new mail past the exhausted item) is owed a first attempt — the brake does not hold new work');
    });
  } catch (err) { fail('(4) frontier advance resets the brake', err); }
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

// -- RED (3)/(4) — dropping the frontier check (exhausted -> ALWAYS suppress) blocks NEW mail too --
//
// This is the exact gap `reconcile.js`'s own `counterDisarmed` has (`attempts >= n`, no item
// check) and the reason this fix reads the ledger here instead of trusting that gate alone: without
// the frontier comparison, an exhausted lane would refuse legitimate new work forever, indistinct
// from refusing a genuine retry of stale work.
function caseRedFrontierCheckIgnored() {
  try {
    const src = fs.readFileSync(path.join(__dirname, 'owed-from-endings.js'), 'utf8');
    const ANCHOR = "if (!row || !(Number(row.attempts) >= n)) return false;\n  const recorded = Array.isArray(row.owed_items) ? row.owed_items : [];\n  return recorded.includes(`#${lastNum}`);";
    assert.ok(src.includes(ANCHOR), 'unreadFrontierExhausted anchor missing');
    const mutatedSrc = src.replace(ANCHOR, 'return Boolean(row && Number(row.attempts) >= n);');
    const Module = require('node:module');
    const mut = new Module(path.join(__dirname, 'owed-from-endings.js'), null);
    mut.filename = path.join(__dirname, 'owed-from-endings.js');
    mut.paths = Module._nodeModulePaths(__dirname);
    mut._compile(mutatedSrc, mut.filename);

    const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'gred3-'));
    writeSessions(goalFolder, [
      { 'session-id': 's15', seat: 'leader', started: '2026-08-28T22:17:39Z', checkin: '2026-08-28 22:17' },
    ]);
    writeWorkers(goalFolder, [{ agent: 'leader', checkin: '2026-08-28 22:17', lastread: 43 }]);
    const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'gred3-ws-'));
    seedRecoveryConfig(workspaceRoot);
    const recovery = loadRecoveryConfig({ workspace: workspaceRoot });
    const countersFile = path.join(workspaceRoot, 'attempt-counters.json');
    const goal = 'gred3-goal';
    // Exhaust the lane on frontier #45 — same as arm 3/4's setup.
    for (let i = 0; i < recovery.attempt_counter_n; i += 1) {
      counters.countAttempt({
        driver: counters.DRIVERS.RECONCILE_RESPAWN, goal, seat: 'leader', reasonClass: 'unread',
        n: recovery.attempt_counter_n, items: ['#45'],
      }, { countersFile });
    }
    // NEW mail, past the exhausted frontier — #46 was never counted.
    writeMessages(goalFolder, [
      { num: 46, sender: 'boundary-auditor', to: 'leader', type: 'completion', ts: '2026-08-29 09:00' },
    ]);
    const { loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter } = require('./reconcile');
    const d = withWorkspaceRoot(workspaceRoot, () => mut.exports.classifyOwed(goalFolder, {
      readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map(),
      loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter,
      STAFF_CHAIRS: ['leader', 'goal-master'], SYSTEM_MAIL_SENDER: 'ignite-daemon', goal, countersFile,
    }));
    const leaderRow = d.classB.find((x) => x.seat === 'leader');
    assert.strictEqual(leaderRow, undefined,
      `RED: dropping the frontier check must wrongly block NEW mail on an exhausted lane, got ${JSON.stringify(leaderRow)}`);
    pass('(RED 3/4) dropping the frontier check reproduces reconcile.js\'s own gap — an exhausted lane blocks NEW mail too');
  } catch (err) { fail('(RED 3/4) frontier check ignored', err); }
}

// -- ABANDONMENT — a lane's second terminal outcome excludes it from the owed set -----------------
//
// `d-recovery-abandoned-is-an-ending` (owner ruling, 2026-08-31): `drop-lane` retires ONE lane
// `(goal, seat)` forever, recorded in `state-store/tables.sql`'s `seat_abandonments` table — the
// ending store's own home, reached exactly as `seat_holds` already is. These arms prove the
// counters honour it: an abandoned seat must never appear in `classA`, `classB`, or the `pending`
// frontier `classE` reports — and a NON-abandoned seat in the SAME pass must still appear in each,
// so the exclusion is proven discriminating rather than a check that stopped counting everything.
const {
  openEndingStoreFor, closeEndingStores, bind: bindStore,
} = require('../state-store');

function caseAbandonedSeatExcludedFromClassAAndClassB() {
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'abandon-ws-ab-'));
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    const goal = 'abandon-ab-goal';
    const goalFolder = path.join(workspaceRoot, '.rbtv', 'goals', goal);
    fs.mkdirSync(goalFolder, { recursive: true });
    // classA fixture: two seats, both stamped `failed` (a nonterm class-A row) — one abandoned.
    writeSessions(goalFolder, [
      {
        'session-id': 'sa1', seat: 'worker-dropped', started: '2026-08-31T20:00:00Z',
        ended: '2026-08-31T20:05:00Z', checkin: '2026-08-31 20:00',
      },
      {
        'session-id': 'sa2', seat: 'worker-control', started: '2026-08-31T20:00:00Z',
        ended: '2026-08-31T20:05:00Z', checkin: '2026-08-31 20:00',
      },
      // `abandonedSeats`/`heldSeats` are both built off `seats` (session-derived, `lastBySeat`) —
      // a chair the classB loop checks must ALSO have a session row, matching how a held chair
      // already needs one (`caseBrakeHoldsAfterNDeaths` gives 'leader' a session row for the same
      // reason). Without one, the abandonment lookup never runs for that chair at all.
      {
        'session-id': 'sa3', seat: 'chair-dropped', started: '2026-08-31T20:00:00Z', checkin: '2026-08-31 20:00',
      },
      {
        'session-id': 'sa4', seat: 'chair-control', started: '2026-08-31T20:00:00Z', checkin: '2026-08-31 20:00',
      },
    ]);
    // classB fixture: two chairs, both with unread mail — one abandoned.
    writeWorkers(goalFolder, [
      { agent: 'chair-dropped', checkin: '2026-08-31 20:00', lastread: 0 },
      { agent: 'chair-control', checkin: '2026-08-31 20:00', lastread: 0 },
    ]);
    writeMessages(goalFolder, [
      { num: 1, sender: 'owner', to: 'chair-dropped', type: 'note', ts: '2026-08-31 20:01' },
      { num: 2, sender: 'owner', to: 'chair-control', type: 'note', ts: '2026-08-31 20:01' },
    ]);
    api.stampSystem({
      goal, seat: 'worker-dropped', ending: 'failed', reason_class: 'crash', evidence_pointer: '/tmp/dropped',
    });
    api.stampSystem({
      goal, seat: 'worker-control', ending: 'failed', reason_class: 'crash', evidence_pointer: '/tmp/control',
    });
    api.abandonSeat({
      goal, seat: 'worker-dropped', anchor: 'owner: drop-lane, this lane is stuck for good', abandoned_by: 'owner',
    });
    api.abandonSeat({
      goal, seat: 'chair-dropped', anchor: 'owner: drop-lane, unread mail from a dead chair', abandoned_by: 'owner',
    });

    const {
      loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter,
    } = require('./reconcile');
    const d = withWorkspaceRoot(workspaceRoot, () => require('./owed-from-endings').classifyOwed(goalFolder, {
      readyAnswer: readyEmpty,
      live: new Set(),
      queued: new Set(),
      goal,
      loadSessions,
      loadMessages,
      lastBySeat,
      liveSeatsFromLedgers,
      checkinOf,
      tsAfter,
      STAFF_CHAIRS: ['chair-dropped', 'chair-control'],
      SYSTEM_MAIL_SENDER: 'ignite-daemon',
    }));

    assert.strictEqual(d.classA.find((x) => x.seat === 'worker-dropped'), undefined,
      `an abandoned lane must never appear in classA, got ${JSON.stringify(d.classA)}`);
    assert.ok(d.classA.find((x) => x.seat === 'worker-control'),
      `CONTROL: a non-abandoned lane with the same failed ending must still appear in classA, got ${JSON.stringify(d.classA)}`);
    assert.strictEqual(d.classB.find((x) => x.seat === 'chair-dropped'), undefined,
      `an abandoned chair must never appear in classB, got ${JSON.stringify(d.classB)}`);
    assert.ok(d.classB.find((x) => x.seat === 'chair-control'),
      `CONTROL: a non-abandoned chair with the same unread mail must still appear in classB, got ${JSON.stringify(d.classB)}`);
    pass('abandoned lane excluded from classA and classB, control lane still owed in the same pass');
  } catch (err) { fail('abandoned lane excluded from classA and classB', err); } finally { closeEndingStores(); }
}

function caseAbandonedSeatExcludedFromPending() {
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'abandon-ws-pending-'));
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    const goal = 'abandon-pending-goal';
    const goalFolder = path.join(workspaceRoot, '.rbtv', 'goals', goal);
    fs.mkdirSync(goalFolder, { recursive: true });
    writeSessions(goalFolder, [
      { 'session-id': 'sp1', seat: 'worker-dropped', started: '2026-08-31T20:00:00Z', checkin: '2026-08-31 20:00' },
      { 'session-id': 'sp2', seat: 'worker-control', started: '2026-08-31T20:00:00Z', checkin: '2026-08-31 20:00' },
    ]);
    api.abandonSeat({
      goal, seat: 'worker-dropped', anchor: 'owner: drop-lane, this lane will never launch', abandoned_by: 'owner',
    });
    const {
      loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter,
    } = require('./reconcile');
    const d = withWorkspaceRoot(workspaceRoot, () => require('./owed-from-endings').classifyOwed(goalFolder, {
      readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
      live: new Set(),
      queued: new Set(),
      goal,
      loadSessions,
      loadMessages,
      lastBySeat,
      liveSeatsFromLedgers,
      checkinOf,
      tsAfter,
      STAFF_CHAIRS: [],
      SYSTEM_MAIL_SENDER: 'ignite-daemon',
    }));
    const pending = (d.classE && d.classE.pending) || [];
    assert.ok(!pending.includes('worker-dropped'),
      `an abandoned lane must never appear in the pending frontier, got ${JSON.stringify(pending)}`);
    assert.ok(pending.includes('worker-control'),
      `CONTROL: a non-abandoned lane with no ending must still appear in the pending frontier, got ${JSON.stringify(pending)}`);
    pass('abandoned lane excluded from the pending frontier (classE), control lane still pending in the same pass');
  } catch (err) { fail('abandoned lane excluded from pending', err); } finally { closeEndingStores(); }
}

// class R (the graph half, `owed.js#seatState`/`deriveLaunchable`) is a pure-function unit test —
// it takes its `abandoned` set as an option rather than reading a store, so no DB fixture is needed.
function caseAbandonedSeatExcludedFromClassR() {
  try {
    const { deriveLaunchable } = require('./owed');
    const rows = [
      { seat: 'worker-dropped', after: '' },
      { seat: 'worker-control', after: '' },
    ];
    const abandoned = new Set(['worker-dropped']);
    const { classR, states } = deriveLaunchable({
      rows,
      byJob: new Map(),
      queued: new Set(),
      ready: new Set(['worker-dropped', 'worker-control']),
      jobIdFor: (seat) => seat,
      seatIsFinished: () => false,
      seatHasRun: () => false,
      view: {
        done: new Set(), foreign: new Set(), notFinished: new Set(), abandoned,
      },
    });
    assert.strictEqual(states['worker-dropped'], 'abandoned',
      `an abandoned seat must report a distinct terminal state, got ${states['worker-dropped']}`);
    assert.ok(!classR.find((r) => r.seat === 'worker-dropped'),
      `an abandoned seat coord still marks READY must never enter classR (graph-owed), got ${JSON.stringify(classR)}`);
    assert.ok(classR.find((r) => r.seat === 'worker-control'),
      `CONTROL: a non-abandoned seat coord marks READY must still enter classR, got ${JSON.stringify(classR)}`);
    pass('seatState/deriveLaunchable (class R) honour the abandoned exclusion, control seat still launchable');
  } catch (err) { fail('abandoned seat excluded from class R (seatState)', err); }
}

// ── THE INVISIBLE-ENDING GAP (owner-ordered fix, 2026-09-01, `rr-live-proof`) ────────────────────
//
// `classifyOwed`'s candidate universe used to be `sessions.csv`'s seats alone (`lastBySeat`'s
// keys) — a seat whose ending was stamped directly, with NO `sessions.csv` row ever written for
// it, was never even a candidate: not excluded, never asked about. Measured live on
// `.rbtv/goals/test-retry-proof/`: `worker-a` carries a real `incomplete/armed:1` ending row and
// zero session rows, and never once appeared across six real reconcile passes.
//
// THIS ARM PROVES BOTH HALVES OF THE FIX IN ONE PASS, so neither can silently regress the other:
//   · `worker-invisible` — an ending row, zero session rows — now IS a class-A candidate.
//   · `worker-launched` — the CONTROL, an ordinary launched-and-ended seat with the same ending —
//     is unaffected, proving the widening did not change how a normal candidate is read.
//   · The candidate set (`d.seats`) is asserted to hold EXACTLY these two names — a healthy goal's
//     seats that never launched and were never stamped (the population this fix must never touch,
//     because nothing here ever writes them an ending row) do not silently ride along.
function caseInvisibleEndingSeatBecomesClassA() {
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'invisible-ending-ws-'));
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    const goal = 'invisible-ending-goal';
    const goalFolder = path.join(workspaceRoot, '.rbtv', 'goals', goal);
    fs.mkdirSync(goalFolder, { recursive: true });
    writeSessions(goalFolder, [
      {
        'session-id': 's1', seat: 'worker-launched', started: '2026-09-01T00:00:00Z',
        ended: '2026-09-01T00:05:00Z', checkin: '2026-09-01 00:00',
      },
    ]);
    api.stampSystem({
      goal, seat: 'worker-launched', ending: 'failed', reason_class: 'crash', evidence_pointer: '/tmp/launched',
    });
    // `worker-invisible` gets an ending row and NOTHING in sessions.csv — the exact shape
    // `rr-live-proof` measured on `worker-a`. `worker-never-run` gets neither: the ordinary,
    // healthy not-yet-launched seat, proven absent by never writing it anything at all.
    api.stampSystem({
      goal, seat: 'worker-invisible', ending: 'failed', reason_class: 'crash', evidence_pointer: '/tmp/invisible',
    });

    const {
      loadSessions, loadMessages, lastBySeat, liveSeatsFromLedgers, checkinOf, tsAfter,
    } = require('./reconcile');
    const d = withWorkspaceRoot(workspaceRoot, () => require('./owed-from-endings').classifyOwed(goalFolder, {
      readyAnswer: readyEmpty,
      live: new Set(),
      queued: new Set(),
      goal,
      loadSessions,
      loadMessages,
      lastBySeat,
      liveSeatsFromLedgers,
      checkinOf,
      tsAfter,
      STAFF_CHAIRS: [],
      SYSTEM_MAIL_SENDER: 'ignite-daemon',
    }));

    assert.ok(d.classA.find((x) => x.seat === 'worker-invisible'),
      `a seat with an ending-store row but ZERO sessions.csv rows must appear in classA, got ${JSON.stringify(d.classA)}`);
    assert.ok(d.classA.find((x) => x.seat === 'worker-launched'),
      `CONTROL: an ordinary launched seat with the same failed ending must still appear in classA, got ${JSON.stringify(d.classA)}`);
    assert.strictEqual(d.classA.length, 2,
      `exactly the two stamped seats must be class A, got ${JSON.stringify(d.classA)}`);
    assert.deepStrictEqual([...d.seats].sort(), ['worker-invisible', 'worker-launched'],
      `the candidate universe must be exactly the two seats with real evidence (a session or an ending row) — no seat neither launched nor stamped may ride along, got ${JSON.stringify(d.seats)}`);
    pass('a seat whose ending was stamped directly, with zero sessions.csv rows, is no longer invisible to class A — an ordinary never-launched, never-stamped seat is still untouched');
  } catch (err) { fail('invisible-ending seat becomes a class A candidate', err); } finally { closeEndingStores(); }
}

function caseFinishMarkerPin() {
  try {
    const recordsPy = fs.readFileSync(path.join(__dirname, '..', 'coord', 'records.py'), 'utf8');
    assert.ok(recordsPy.includes(`FINISH_MARKER = "${FINISH_MARKER}"`),
      `FINISH_MARKER drifted from records.py: ${JSON.stringify(FINISH_MARKER)}`);
    pass('(PIN) FINISH_MARKER is byte-identical to coord/records.py');
  } catch (err) { fail('(PIN) FINISH_MARKER', err); }
}

caseUnreadAfterCursorSameMinuteAsCheckin();
caseReadMessageBeforeCursorNotWoken();
caseCursorIsNewestRowNotFirst();
caseFinishMarkerPin();
caseBrakeHoldsAfterNDeaths();
caseFrontierAdvanceResets();
caseRedRevertToCheckinLogic();
caseRedCursorAlwaysZero();
caseRedFrontierCheckIgnored();
caseRedFirstRowReturn();
caseAbandonedSeatExcludedFromClassAAndClassB();
caseAbandonedSeatExcludedFromPending();
caseAbandonedSeatExcludedFromClassR();
caseInvisibleEndingSeatBecomesClassA();

try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* tmp */ }

if (failed) {
  process.stdout.write(`${failed} FAIL\n`);
  process.exit(1);
}
process.stdout.write('ALL PASS\n');
