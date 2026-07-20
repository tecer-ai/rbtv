'use strict';

// probe-keys-coalesce — task 7.13 piece 1: screen-read polls are COALESCED at source.
//
// What it proves:
//   1. The first poll of a run appends ONE fail-closed `screen-read` record (D94 unchanged).
//   2. Subsequent polls within the coalesce gap write NOTHING to disk (`coalesced: true`).
//   3. Closing the run appends ONE `screen-read-summary` carrying count + first_ts/last_ts.
//   4. A run of exactly one poll writes NO summary (the open record says everything).
//   5. Fail-closed is preserved: a loosened (0644) audit file REFUSES a new run's open record.
//   6. BEFORE/AFTER volume: an equivalent simulated attach (N polls) measured under the old
//      per-poll appender vs the coalescer — the live-box ratio this exists to kill was
//      2,139 poll records for one attach.
//
// Isolation: throwaway files under os.tmpdir(). Capture truncated at module load (D51).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-keys-coalesce.out');
fs.writeFileSync(outPath, '');

const {
  appendScreenReadRecord, recordScreenRead, flushScreenReadRuns, KeysAuditError, auditPathFor,
} = require('../keys-audit');

const checks = [];
let skipped = 0;
function out(...args) {
  const line = args.join(' ');
  fs.appendFileSync(outPath, line + '\n');
  console.log(line);
}
function check(name, pass, detail = '') {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'} | ${name}${detail ? ' | ' + detail : ''}`);
}

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-probe-coalesce-'));
const SENDER = { id: 'probe-owner', kind: 'owner', via: 'probe' };
const N_POLLS = 40; // one 10-second human glance at the attach client's ~250 ms poll

function records(logPath) {
  const p = auditPathFor(logPath);
  if (!fs.existsSync(p)) return [];
  return fs.readFileSync(p, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
}

function main() {
  // --- BEFORE: the old per-poll appender, N polls of one simulated attach.
  const beforeLog = path.join(dir, 'before-session.log');
  for (let i = 0; i < N_POLLS; i++) {
    appendScreenReadRecord({ logPath: beforeLog, execId: 1, sessionId: 'before-session', sender: SENDER });
  }
  const beforeCount = records(beforeLog).length;
  check(`BEFORE (per-poll appender): ${N_POLLS} polls -> ${N_POLLS} records`, beforeCount === N_POLLS,
    `records=${beforeCount}`);

  // --- AFTER: the coalescer, the SAME N polls.
  const afterLog = path.join(dir, 'after-session.log');
  const first = recordScreenRead({ logPath: afterLog, execId: 2, sessionId: 'after-session', sender: SENDER });
  check('first poll opens the run on disk (coalesced: false)', first.coalesced === false);
  let coalescedAll = true;
  for (let i = 1; i < N_POLLS; i++) {
    const r = recordScreenRead({ logPath: afterLog, execId: 2, sessionId: 'after-session', sender: SENDER });
    if (!r.coalesced) coalescedAll = false;
  }
  check('polls 2..N are coalesced in memory (no disk write)', coalescedAll);
  const midRecords = records(afterLog);
  check('mid-run the audit holds exactly ONE record (the fail-closed open)', midRecords.length === 1,
    `records=${midRecords.length}`);
  check('the open record is D94\'s `screen-read`, attributed', midRecords[0].event === 'screen-read' && midRecords[0].sender_id === SENDER.id);

  flushScreenReadRuns({ execId: 2 });
  const closedRecords = records(afterLog);
  check('run close appends exactly ONE `screen-read-summary`', closedRecords.length === 2 && closedRecords[1].event === 'screen-read-summary',
    `records=${closedRecords.length} last=${closedRecords[closedRecords.length - 1].event}`);
  const summary = closedRecords[1];
  check(`summary carries the count (${N_POLLS})`, summary.count === N_POLLS, `count=${summary.count}`);
  check('summary carries the time range (first_ts <= last_ts)',
    typeof summary.first_ts === 'string' && typeof summary.last_ts === 'string' && summary.first_ts <= summary.last_ts);
  const afterCount = closedRecords.length;
  out(`VOLUME | attach of ${N_POLLS} polls | before=${beforeCount} records | after=${afterCount} records | reduction=${(100 * (1 - afterCount / beforeCount)).toFixed(1)}%`);
  check('audit volume dropped at source for an equivalent attach', afterCount < beforeCount,
    `${beforeCount} -> ${afterCount}`);

  // --- A single-poll run writes NO summary.
  const oneLog = path.join(dir, 'one-session.log');
  recordScreenRead({ logPath: oneLog, execId: 3, sessionId: 'one-session', sender: SENDER });
  flushScreenReadRuns({ execId: 3 });
  const oneRecords = records(oneLog);
  check('a one-poll run closes with NO summary (the open record says everything)',
    oneRecords.length === 1 && oneRecords[0].event === 'screen-read');

  // --- A NEW run after close re-opens on disk (per-run granularity, not per-boot).
  const again = recordScreenRead({ logPath: afterLog, execId: 2, sessionId: 'after-session', sender: SENDER });
  check('a new run after close re-opens fail-closed on disk', again.coalesced === false && records(afterLog).length === 3);
  flushScreenReadRuns();

  // --- Fail-closed preserved: a loosened audit refuses a new run's open record.
  const looseLog = path.join(dir, 'loose-session.log');
  fs.writeFileSync(auditPathFor(looseLog), '', { mode: 0o600 });
  fs.chmodSync(auditPathFor(looseLog), 0o644);
  let threw = null;
  try { recordScreenRead({ logPath: looseLog, execId: 4, sessionId: 'loose-session', sender: SENDER }); } catch (e) { threw = e; }
  check('a loosened (0644) audit file REFUSES the run open (fail-closed, D94 unchanged)',
    threw instanceof KeysAuditError, threw ? threw.message.slice(0, 60) : 'no throw');
}

try {
  main();
} catch (err) {
  out('ERROR:', err.message, err.stack);
  checks.push({ name: 'unhandled error', pass: false });
} finally {
  try { flushScreenReadRuns(); } catch { /* drain */ }
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* tmp */ }
}

const failed = checks.filter((c) => !c.pass);
out('');
out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
out(`SKIPPED_COUNT: ${skipped}`);
out(`COALESCE_OK: ${failed.length === 0}`);
out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
out(`WALL_MS: ${Date.now() - start}`);
process.exitCode = failed.length === 0 ? 0 : 1;
