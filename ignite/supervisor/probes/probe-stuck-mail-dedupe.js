#!/usr/bin/env node
'use strict';

// -- task 69 — the daemon's stuck-mail alarm must not self-feed on its OWN prior `type: stuck` mail
//
// Seed evidence (redesign-continue-1.md #69): with a goal's leader chair down, the daemon filed a
// new `type: stuck` message from `ignite-daemon` to `leader` every ~10 min, each one itself unread
// mail addressed to the leader — 114 rows observed by 2026-08-22 15:26Z on meet-transcript-summarizer.
// The mechanism that wrote those rows (`reconcile.js`'s `sendStuck`) is DELETED as of the
// 2026-08-25 attempt-counter redesign (see `ignite/work-on-ignite/memory/engine/
// 20260825-c-attempt-counter-replaces-both.md`) — the daemon no longer emits a `type: stuck`
// message on every cadence. D70 (commit affceae2, 2026-08-22) separately excludes the ONE
// surviving system-mail sender (`ignite-daemon`, `SYSTEM_MAIL_SENDER`) from class B's unread count
// in `owed-from-endings.js`, so even a system-authored row that DOES land is never counted as
// progress or re-armed against.
//
// This probe proves BOTH arms hold on the CURRENT tree:
//   (a) many prior `type: stuck` rows authored by `ignite-daemon` do NOT inflate class B's
//       `unreadCount` — only genuine (non-system) unread mail is counted.
//   (b) a genuine new unread row from a real sender (not `ignite-daemon`) still wakes the chair —
//       the exclusion is sender-scoped, never a blanket "ignore type: stuck".
// A red arm reverts the exclusion (drops `m.sender !== SYSTEM_MAIL_SENDER`) to confirm the fixture
// actually discriminates: reverted, the daemon's own rows count and reproduce the observed growth.

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { owedFromLedgers } = require('../reconcile');

const HERE = __dirname;
const OUT_PATH = path.join(HERE, 'probe-stuck-mail-dedupe.out');
const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'stuck-mail-dedupe-'));

let failed = 0;
const lines = [];
function log(s) { lines.push(s); }
function pass(name) { log(`PASS ${name}`); }
function fail(name, err) { failed += 1; log(`FAIL ${name}: ${err && err.stack ? err.stack : err}`); }

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

function writeWorkers(goalFolder, rows) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const header = '| agent | active | pane | summary | checkin | checkout | lastread |\n'
    + '|---|---|---|---|---|---|---|\n';
  const body = rows.map((r) => `| ${r.agent} | ${r.active || 'yes'} | | | ${r.checkin || ''} | ${r.checkout || ''} | ${r.lastread == null ? '' : r.lastread} |`).join('\n');
  fs.writeFileSync(path.join(dir, 'workers.md'), header + body + '\n');
}

const readyEmpty = { ready: new Map(), granted: new Map(), rows: [], reason: null };

// Leader is DOWN (no sessions.csv row at all — never checked in, never left a cursor); one real
// unread message (#846, the owner's D87 proof target) followed by four ignite-daemon `type: stuck`
// self-escalations (#847-#850), reproducing the seed's exact numbering.
function caseSelfFeedExcluded() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'g-selffeed-'));
  writeSessions(goalFolder, []);
  writeWorkers(goalFolder, []);
  writeMessages(goalFolder, [
    { num: 846, sender: 'boundary-auditor', to: 'leader', type: 'note', ts: '2026-08-22 14:05' },
    { num: 847, sender: 'ignite-daemon', to: 'leader', type: 'stuck', ts: '2026-08-22 14:15', body: 'unread:leader:846' },
    { num: 848, sender: 'ignite-daemon', to: 'leader', type: 'stuck', ts: '2026-08-22 14:25', body: 'unread:leader:847' },
    { num: 849, sender: 'ignite-daemon', to: 'leader', type: 'stuck', ts: '2026-08-22 14:35', body: 'unread:leader:848' },
    { num: 850, sender: 'ignite-daemon', to: 'leader', type: 'stuck', ts: '2026-08-22 14:45', body: 'unread:leader:849' },
  ]);
  try {
    const d = owedFromLedgers(goalFolder, { readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map() });
    const leaderRow = d.classB.find((x) => x.seat === 'leader');
    assert.ok(leaderRow, `leader must still be class B for the one real message — got classB=${JSON.stringify(d.classB)}`);
    assert.strictEqual(leaderRow.unreadCount, 1,
      `unreadCount must count ONLY the real message (#846), never the daemon's own 4 stuck rows — got ${leaderRow.unreadCount}`);
    assert.strictEqual(leaderRow.lastNum, 846,
      `lastNum must name the real frontier (#846), not the daemon's own last stuck row (#850) — got ${leaderRow.lastNum}`);
    pass('(a) 4 prior ignite-daemon `type: stuck` rows do NOT inflate unreadCount — counts only the real message');
    return true;
  } catch (err) { fail('(a) self-feed excluded', err); return false; }
}

// Control: a genuine new unread row from a REAL sender (not ignite-daemon) still wakes the chair —
// the fix must be sender-scoped, never a blanket exclusion of anything shaped like `type: stuck`.
function caseGenuineStuckFromRealSenderStillWakes() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'g-genuine-'));
  writeSessions(goalFolder, []);
  writeWorkers(goalFolder, []);
  writeMessages(goalFolder, [
    // A real seat (not the daemon) genuinely reporting itself blocked — routed to leader per D2 —
    // must count as real unread backlog, exactly like any other seat-authored mail.
    { num: 900, sender: 'boundary-auditor', to: 'leader', type: 'stuck', ts: '2026-08-22 14:05', body: 'blocked on the data root' },
  ]);
  try {
    const d = owedFromLedgers(goalFolder, { readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map() });
    const leaderRow = d.classB.find((x) => x.seat === 'leader');
    assert.ok(leaderRow, `a real seat's own type:stuck report must still wake the chair — got classB=${JSON.stringify(d.classB)}`);
    assert.strictEqual(leaderRow.unreadCount, 1, `got ${leaderRow.unreadCount}`);
    pass('(b) a genuine type:stuck report from a real (non-daemon) sender still wakes the chair — control');
  } catch (err) { fail('(b) genuine stuck still wakes', err); }
}

// RED — revert the sender exclusion (as it read before D70) and confirm the fixture actually
// discriminates: with the exclusion gone, the daemon's own 4 rows count and lastNum drifts to the
// daemon's own last row, reproducing the self-feed exactly as observed 2026-08-22.
function caseRedWithoutExclusion() {
  const src = fs.readFileSync(path.join(HERE, '..', 'owed-from-endings.js'), 'utf8');
  const CURRENT = "const unread = messages.filter((m) => m.to === chair && m.sender !== chair\n      && m.sender !== SYSTEM_MAIL_SENDER\n      && (cursor === null || m.num > cursor));";
  const REVERTED = "const unread = messages.filter((m) => m.to === chair && m.sender !== chair\n      && (cursor === null || m.num > cursor));";
  if (!src.includes(CURRENT)) {
    fail('(RED) without exclusion', new Error('anchor text not found in owed-from-endings.js — re-locate before trusting this arm'));
    return;
  }
  const mutated = src.replace(CURRENT, REVERTED);
  // Written BESIDE the real `owed-from-endings.js` (never under `probes/`) so its own relative
  // `require('./ending-reads')` etc. resolve exactly as the original's do.
  const modPath = path.join(HERE, '..', `._red_owed_from_endings_${process.pid}.js`);
  fs.writeFileSync(modPath, mutated);
  try {
    delete require.cache[require.resolve('../reconcile')];
    delete require.cache[require.resolve('../owed')];
    delete require.cache[require.resolve('../owed-from-endings')];
    delete require.cache[require.resolve(modPath)];
    const Module = require('node:module');
    const origResolve = Module._resolveFilename;
    Module._resolveFilename = function patched(request, ...rest) {
      if (request === './owed-from-endings') return modPath;
      return origResolve.call(this, request, ...rest);
    };
    let reconcileRed;
    try {
      reconcileRed = require('../reconcile');
    } finally {
      Module._resolveFilename = origResolve;
    }
    const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'g-red-'));
    writeSessions(goalFolder, []);
    writeWorkers(goalFolder, []);
    writeMessages(goalFolder, [
      { num: 846, sender: 'boundary-auditor', to: 'leader', type: 'note', ts: '2026-08-22 14:05' },
      { num: 847, sender: 'ignite-daemon', to: 'leader', type: 'stuck', ts: '2026-08-22 14:15', body: 'unread:leader:846' },
      { num: 848, sender: 'ignite-daemon', to: 'leader', type: 'stuck', ts: '2026-08-22 14:25', body: 'unread:leader:847' },
    ]);
    const d = reconcileRed.owedFromLedgers(goalFolder, { readyAnswer: readyEmpty, live: new Set(), queued: new Set(), endings: new Map() });
    const leaderRow = d.classB.find((x) => x.seat === 'leader');
    assert.ok(leaderRow, 'reverted fixture setup broken — leader must still be class B');
    assert.strictEqual(leaderRow.unreadCount, 3,
      `RED arm must reproduce the self-feed (unreadCount counts the daemon's own rows too) — got ${leaderRow.unreadCount}`);
    assert.strictEqual(leaderRow.lastNum, 848,
      `RED arm's lastNum must drift to the daemon's OWN last stuck row (the self-feed signature), got ${leaderRow.lastNum}`);
    pass('(RED) reverting the SYSTEM_MAIL_SENDER exclusion reproduces the self-feed — the fixture discriminates');
  } catch (err) {
    fail('(RED) without exclusion', err);
  } finally {
    fs.rmSync(modPath, { force: true });
    delete require.cache[require.resolve('../reconcile')];
    delete require.cache[require.resolve('../owed-from-endings')];
  }
}

caseSelfFeedExcluded();
caseGenuineStuckFromRealSenderStillWakes();
caseRedWithoutExclusion();

const summary = failed ? `${failed} FAILED` : 'ALL PASS';
log(summary);
const body = lines.join('\n');
fs.writeFileSync(OUT_PATH, body);
console.log(body);
process.exit(failed ? 1 : 0);
