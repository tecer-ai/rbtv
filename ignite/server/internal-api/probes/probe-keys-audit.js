'use strict';

// probe-keys-audit — appendKillRecord (cli-expansion owner ruling, 2026-07-20) carries the
// fail-closed guarantee D93 ruled for the session audit. Until this probe, the function was
// referenced by no probe in the tree; dispatch.js's kill-session handler gates its success report
// on this write, and un-audited kills are exactly what the ruling exists to prevent.
//
// ⚑ SCOPE SHRANK AT TASK 7.29, and the shrink is the point rather than a trim. This probe also
// covered appendKeystrokeRecord (D92/D93) and, with `probe-keys-coalesce.js`, the screen-read
// path (D94). Both functions were deleted with the two pty intents they served, so their checks
// and that probe went with them — a check whose subject no longer exists cannot go red and is
// worse than no check. What REMAINS is the kill path, which did not retire.
//
// What it proves:
//   1. appendKillRecord happy path: one `session-killed` record, attributed, carrying NO
//      data/bytes (a kill has no typed secret to protect).
//   2. appendKillRecord refuses a missing log_path and an unattributed sender.
//   3. appendKillRecord is fail-closed: a loosened (0644) audit file REFUSES the write, and the
//      refusal writes NOTHING to the loosened file.
//   4. Repeated records land in ONE ordered append-only stream in the same session's audit file —
//      not independent writers that happen to target the same path.
//
// Mutant-checked at authoring time (bars.md 11): a scratch copy of keys-audit.js with the
// `if (mode & 0o077) throw` guard neutered was required in place of the real module and check 3
// flipped to FAIL against it (no exception, the record landed in the loosened file). The mutant
// is not shipped; this file always requires the real module.
//
// Isolation: throwaway files under os.tmpdir(). Capture truncated at module load (task 7.50).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-keys-audit.out');
fs.writeFileSync(outPath, '');

const { appendKillRecord, auditPathFor, KeysAuditError } = require('../keys-audit');

const checks = [];
function out(...args) {
  const line = args.join(' ');
  fs.appendFileSync(outPath, line + '\n');
  console.log(line);
}
function check(name, pass, detail = '') {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'} | ${name}${detail ? ' | ' + detail : ''}`);
}

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-probe-keys-audit-'));
const SENDER = { id: 'probe-owner', kind: 'owner', via: 'probe' };

function records(logPath) {
  const p = auditPathFor(logPath);
  if (!fs.existsSync(p)) return [];
  return fs.readFileSync(p, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
}

function main() {
  // === appendKillRecord (cli-expansion owner ruling, 2026-07-20) ===

  // --- happy path
  const killLog = path.join(dir, 'kill-session.log');
  const killRes = appendKillRecord({ logPath: killLog, execId: 21, sessionId: 'kill-session', sender: SENDER });
  const killRecords = records(killLog);
  check('appendKillRecord writes exactly one session-killed record',
    killRecords.length === 1 && killRecords[0].event === 'session-killed', `records=${killRecords.length}`);
  check('the kill record is attributed to the sender', killRecords[0].sender_id === SENDER.id);
  check('the kill record carries NO data/bytes (no typed secret in a kill)',
    !('data' in killRecords[0]) && !('bytes' in killRecords[0]));
  check('appendKillRecord returns the audit path it wrote', killRes.auditPath === auditPathFor(killLog));

  // --- refuses on a missing log_path
  let threw = null;
  try { appendKillRecord({ logPath: undefined, execId: 22, sessionId: 'x', sender: SENDER }); } catch (e) { threw = e; }
  check('appendKillRecord refuses a missing log_path',
    threw instanceof KeysAuditError, threw ? threw.message.slice(0, 60) : 'no throw');

  // --- refuses on an unattributed sender
  threw = null;
  try { appendKillRecord({ logPath: killLog, execId: 23, sessionId: 'kill-session', sender: { id: '' } }); } catch (e) { threw = e; }
  check('appendKillRecord refuses an unattributed (empty id) sender',
    threw instanceof KeysAuditError, threw ? threw.message.slice(0, 60) : 'no throw');

  // --- fail-closed: a loosened audit file refuses the write
  const killLooseLog = path.join(dir, 'kill-loose-session.log');
  fs.writeFileSync(auditPathFor(killLooseLog), '', { mode: 0o600 });
  fs.chmodSync(auditPathFor(killLooseLog), 0o644);
  threw = null;
  try { appendKillRecord({ logPath: killLooseLog, execId: 24, sessionId: 'kill-loose-session', sender: SENDER }); } catch (e) { threw = e; }
  check('appendKillRecord REFUSES a loosened (0644) audit file (fail-closed)',
    threw instanceof KeysAuditError, threw ? threw.message.slice(0, 60) : 'no throw');
  check('the refused kill write left the loosened file untouched',
    records(killLooseLog).length === 0, `records=${records(killLooseLog).length}`);

  // === shared file, ordering ===
  // A session's audit file is ONE append-only stream, not a writer that rewrites or replaces
  // earlier bytes — prove the stream property itself, which is what D93's append-only shape
  // promises. It was proved across keystrokes AND the kill until task 7.29 retired the keystroke
  // path; the property under test is unchanged, only the vocabulary available to write it.
  const sharedLog = path.join(dir, 'shared-session.log');
  appendKillRecord({ logPath: sharedLog, execId: 31, sessionId: 'shared', sender: SENDER });
  appendKillRecord({ logPath: sharedLog, execId: 31, sessionId: 'shared', sender: { ...SENDER, id: 'second-sender' } });
  const sharedRecords = records(sharedLog);
  check('successive records land in ONE ordered stream in the same file, earlier bytes intact',
    sharedRecords.length === 2
      && sharedRecords.map((r) => r.event).join(',') === 'session-killed,session-killed'
      && sharedRecords[0].sender_id === SENDER.id
      && sharedRecords[1].sender_id === 'second-sender',
    sharedRecords.map((r) => `${r.event}/${r.sender_id}`).join(','));
}

try {
  main();
} catch (err) {
  out('ERROR:', err.message, err.stack);
  checks.push({ name: 'unhandled error', pass: false });
} finally {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* tmp */ }
}

const failed = checks.filter((c) => !c.pass);
out('');
out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
out(`KEYS_AUDIT_OK: ${failed.length === 0}`);
out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
out(`WALL_MS: ${Date.now() - start}`);
process.exitCode = failed.length === 0 ? 0 : 1;
