'use strict';

// probe-keys-audit — appendKeystrokeRecord (D92/D93) and appendKillRecord (cli-expansion owner
// ruling, 2026-07-20) carry the SAME fail-closed guarantee `probe-keys-coalesce.js` already proves
// for appendScreenReadRecord (D94). Until this probe, NEITHER function was referenced by any probe
// in the tree (grep across ignite/ for the two names: dispatch.js only). dispatch.js's own
// send-to-session / kill-session handlers throw un-audited keystrokes and un-audited kills are
// exactly what D92/D93 exist to prevent — the two write paths that actually gate keystroke
// delivery and the kill success report had zero coverage of their own.
//
// What it proves:
//   1. appendKeystrokeRecord happy path: one `keys-accepted` record, attributed, `data` carried
//      verbatim (control bytes intact), `bytes` measured in UTF-8 bytes (not `.length`).
//   2. appendKeystrokeRecord refuses a missing log_path and an unattributed sender (D93's own two
//      preconditions).
//   3. appendKeystrokeRecord is fail-closed: a loosened (0644) audit file REFUSES the write, and
//      the refusal writes NOTHING to the loosened file.
//   4. appendKillRecord happy path: one `session-killed` record, attributed, carrying NO
//      data/bytes (a kill has no typed secret to protect).
//   5. appendKillRecord refuses a missing log_path and an unattributed sender.
//   6. appendKillRecord is fail-closed: a loosened (0644) audit file REFUSES the write.
//   7. The three intents share ONE ordered append-only stream in the same session's audit file —
//      not three independent writers that happen to target the same path.
//
// Mutant-checked at authoring time (bars.md 11): a scratch copy of keys-audit.js with both
// `if (mode & 0o077) throw` guards neutered was required in place of the real module and checks 3
// and 6 flipped to FAIL against it (no exception, the record landed in the loosened file) — see
// COMPLETION note for this probe. The mutant is not shipped; this file always requires the real
// module.
//
// Isolation: throwaway files under os.tmpdir(). Capture truncated at module load (task 7.50).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-keys-audit.out');
fs.writeFileSync(outPath, '');

const { appendKeystrokeRecord, appendKillRecord, auditPathFor, KeysAuditError } = require('../keys-audit');

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
  // === appendKeystrokeRecord (D92/D93) ===

  // --- happy path
  const ksLog = path.join(dir, 'ks-session.log');
  // Control bytes (verbatim-carry) AND a multi-byte UTF-8 char ('é', 2 bytes / 1 UTF-16 code
  // unit) — without the latter, `.length` and `Buffer.byteLength(data, 'utf8')` agree on any
  // pure-ASCII string and the "bytes is UTF-8, not .length" check below could not discriminate.
  const data = 'echo café\x07\x1b[K';
  const ksRes = appendKeystrokeRecord({ logPath: ksLog, execId: 11, sessionId: 'ks-session', sender: SENDER, data });
  const ksRecords = records(ksLog);
  check('appendKeystrokeRecord writes exactly one keys-accepted record',
    ksRecords.length === 1 && ksRecords[0].event === 'keys-accepted', `records=${ksRecords.length}`);
  check('the record is attributed to the sender',
    ksRecords[0].sender_id === SENDER.id && ksRecords[0].sender_kind === SENDER.kind);
  check('data is carried verbatim (control bytes intact)', ksRecords[0].data === data);
  check('bytes is the UTF-8 byte length, not .length', ksRecords[0].bytes === Buffer.byteLength(data, 'utf8'));
  check('appendKeystrokeRecord returns the audit path it wrote', ksRes.auditPath === auditPathFor(ksLog));

  // --- refuses on a missing log_path
  let threw = null;
  try { appendKeystrokeRecord({ logPath: '', execId: 12, sessionId: 'x', sender: SENDER, data: 'x' }); } catch (e) { threw = e; }
  check('appendKeystrokeRecord refuses a missing log_path',
    threw instanceof KeysAuditError, threw ? threw.message.slice(0, 60) : 'no throw');

  // --- refuses on an unattributed sender
  threw = null;
  try { appendKeystrokeRecord({ logPath: ksLog, execId: 13, sessionId: 'ks-session', sender: null, data: 'x' }); } catch (e) { threw = e; }
  check('appendKeystrokeRecord refuses an unattributed (null) sender',
    threw instanceof KeysAuditError, threw ? threw.message.slice(0, 60) : 'no throw');

  // --- fail-closed: a loosened audit file refuses the write
  const ksLooseLog = path.join(dir, 'ks-loose-session.log');
  fs.writeFileSync(auditPathFor(ksLooseLog), '', { mode: 0o600 });
  fs.chmodSync(auditPathFor(ksLooseLog), 0o644);
  threw = null;
  try { appendKeystrokeRecord({ logPath: ksLooseLog, execId: 14, sessionId: 'ks-loose-session', sender: SENDER, data: 'x' }); } catch (e) { threw = e; }
  check('appendKeystrokeRecord REFUSES a loosened (0644) audit file (fail-closed, D93)',
    threw instanceof KeysAuditError, threw ? threw.message.slice(0, 60) : 'no throw');
  check('the refused write left the loosened file untouched (no record laundered through)',
    records(ksLooseLog).length === 0, `records=${records(ksLooseLog).length}`);

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
  threw = null;
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
  // A session's audit file is ONE append-only stream across all three intents (D93/D94/the kill
  // ruling all EXTEND the same vocabulary into the SAME file, never parallel it) — prove that,
  // not just each writer in isolation.
  const sharedLog = path.join(dir, 'shared-session.log');
  appendKeystrokeRecord({ logPath: sharedLog, execId: 31, sessionId: 'shared', sender: SENDER, data: 'a' });
  appendKeystrokeRecord({ logPath: sharedLog, execId: 31, sessionId: 'shared', sender: SENDER, data: 'b' });
  appendKillRecord({ logPath: sharedLog, execId: 31, sessionId: 'shared', sender: SENDER });
  const sharedRecords = records(sharedLog);
  check('keystrokes and the kill land in ONE ordered stream in the same file',
    sharedRecords.length === 3
      && sharedRecords.map((r) => r.event).join(',') === 'keys-accepted,keys-accepted,session-killed',
    sharedRecords.map((r) => r.event).join(','));
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
