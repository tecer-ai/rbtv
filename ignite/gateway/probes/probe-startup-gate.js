'use strict';

// probe-startup-gate — spawn-profiles-spec.md Design 4 § Startup gate + § Edge cases:
// "a missing, empty, or group/world-readable senders_file makes the daemon REFUSE TO
// START, loudly."
//
// ⚑ THIS PROBE EXERCISES THE LANDMINE ON PURPOSE, IN ISOLATION. Every file below is a
// THROWAWAY under os.tmpdir(). It never reads, writes, or touches the live
// senders_file, and it NEVER starts, stops, or signals the live daemon.
//
// MUTATION — the guard is proven in BOTH directions, because "it refused" is not by
// itself evidence that a check exists: a loader that refused EVERYTHING would pass
// every refusal case here. So each bad file is shown to be refused, the good file is
// shown to be ACCEPTED (the gate discriminates), and — for the mode check, the one
// guard whose subject is otherwise perfectly valid content — the same bytes are shown
// to parse cleanly once the permission bits are the only thing wrong. That last check
// is what proves the mode gate is load-bearing rather than incidental: without it,
// nothing else would have stopped the file.
//
// Capture truncated at module load, BEFORE any work (D51 evidence-husk hazard). The
// process exit code is the truth; the footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const yaml = require('js-yaml');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-startup-gate.out');
fs.writeFileSync(outPath, '');

const { loadSendersFile, hashToken } = require('../sender-auth');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
const skipped = 0;
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), `ignite-probe-gate-${process.pid}-`));
const TOKEN = crypto.randomBytes(16).toString('hex');

const VALID_YAML = [
  'senders:',
  '  - sender-id: probe-owner',
  '    kind: owner',
  `    token-hash: ${hashToken(TOKEN)}`,
  '    enabled: true',
  '',
].join('\n');

function write(name, content, mode = 0o600) {
  const p = path.join(tmpDir, name);
  fs.writeFileSync(p, content, { mode });
  fs.chmodSync(p, mode);
  return p;
}

// Returns the refusal message, or null when the gate ACCEPTED the file.
function gateRefusal(filePath) {
  try {
    loadSendersFile(filePath);
    return null;
  } catch (err) {
    return err.message;
  }
}

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out(`TMPDIR: <throwaway>/${path.basename(tmpDir)}`);

  // --- 1. MISSING file -> refuse, loudly and actionably.
  let msg = gateRefusal(path.join(tmpDir, 'does-not-exist.yaml'));
  check('a MISSING senders_file REFUSES the daemon start', msg !== null, msg ? 'refused' : 'ACCEPTED — the gate is absent');
  check('the missing-file refusal is LOUD (names the cause and the remedy)',
    msg !== null && /REFUSING TO START/.test(msg) && /missing/i.test(msg) && /0600|senders\.example/.test(msg),
    msg ? msg.split('.')[0] + '.' : 'n/a');

  // --- 2. EMPTY file -> refuse. An empty registry means no sender can EVER
  // authenticate: that is a misconfiguration, not a posture.
  msg = gateRefusal(write('empty.yaml', ''));
  check('an EMPTY senders_file REFUSES the daemon start', msg !== null && /REFUSING TO START/.test(msg) && /empty/i.test(msg), msg ? 'refused: empty' : 'ACCEPTED');

  // --- 3. GROUP/WORLD-READABLE -> refuse. The CONTENT here is perfectly valid; the
  // permission bits are the only defect.
  const loose = write('loose.yaml', VALID_YAML, 0o644);
  msg = gateRefusal(loose);
  check('a GROUP/WORLD-READABLE senders_file REFUSES the daemon start (mode 0644)',
    msg !== null && /REFUSING TO START/.test(msg) && /group\/world/i.test(msg),
    msg ? 'refused: mode 644' : 'ACCEPTED — a world-readable credential file would have booted');
  check('the mode refusal names the fix (chmod 600)', msg !== null && /chmod 600/.test(msg), 'remedy present in the message');

  // MUTATION — is the mode check load-bearing, or is something else refusing this file?
  // The same bytes are parsed directly: they are VALID. So the ONLY thing standing
  // between a world-readable credential file and a booted daemon is the mode check.
  const looseParses = (() => {
    try {
      const doc = yaml.load(fs.readFileSync(loose, 'utf8'));
      return Array.isArray(doc.senders) && doc.senders.length === 1;
    } catch { return false; }
  })();
  check('MUTATION: those exact bytes are VALID content — only the MODE check refuses them (the gate is load-bearing)',
    looseParses === true,
    'the file parses to 1 well-formed sender; without the mode gate it would have loaded');
  // ...and the identical content at 0600 is ACCEPTED, isolating mode as the sole variable.
  const tight = write('tight.yaml', VALID_YAML, 0o600);
  check('MUTATION: the IDENTICAL content at mode 0600 is ACCEPTED (mode is the only variable)',
    gateRefusal(tight) === null,
    'same bytes, 0600 -> accepted');

  // --- 4. MALFORMED YAML -> refuse.
  msg = gateRefusal(write('malformed.yaml', 'senders: [ this: is: not: yaml\n'));
  check('a MALFORMED senders_file REFUSES the daemon start', msg !== null && /REFUSING TO START/.test(msg), msg ? 'refused: malformed' : 'ACCEPTED');

  // --- 5. NO senders declared -> refuse.
  msg = gateRefusal(write('nosenders.yaml', 'senders: []\n'));
  check('a senders_file declaring NO senders REFUSES the daemon start', msg !== null && /no senders/i.test(msg), msg ? 'refused: empty roster' : 'ACCEPTED');

  // --- 6. A malformed ROW -> refuse, naming the row. Never a silently skipped sender:
  // that would present later as "my token stopped working" with nothing in any log.
  msg = gateRefusal(write('badrow.yaml', ['senders:', '  - sender-id: x', '    kind: wizard', '    token-hash: ' + hashToken(TOKEN), '    enabled: true', ''].join('\n')));
  check('an invalid sender KIND REFUSES the start and names the offending row',
    msg !== null && /senders\[0\]/.test(msg) && /owner\|agent\|bridge/.test(msg),
    msg ? 'refused: kind=wizard' : 'ACCEPTED');

  msg = gateRefusal(write('badhash.yaml', ['senders:', '  - sender-id: x', '    kind: owner', '    token-hash: plaintext-token-oops', '    enabled: true', ''].join('\n')));
  check('a non-SHA-256 token-hash REFUSES the start (plaintext tokens never rest on disk)',
    msg !== null && /token-hash/.test(msg), msg ? 'refused: bad hash' : 'ACCEPTED');

  // --- 7. THE SHIPPED SEED must REFUSE. This is what makes "credentials never in git"
  // (D27) mechanically true rather than a promise: a verbatim copy of the seed cannot
  // boot a daemon, so the seed can never quietly become a live registry.
  const seed = path.join(__dirname, '..', '..', 'config', 'senders.example.yaml');
  const seedCopy = write('seed-copy.yaml', fs.readFileSync(seed, 'utf8'), 0o600);
  msg = gateRefusal(seedCopy);
  check('the SHIPPED SEED (config/senders.example.yaml), copied verbatim at 0600, REFUSES to boot',
    msg !== null && /token-hash/.test(msg),
    msg ? 'refused: placeholder token-hash — the seed cannot become a live registry by copy alone' : 'ACCEPTED — THE SEED WOULD BOOT A DAEMON');
  check('the shipped seed contains NO 64-hex token-hash (no credential in git)',
    !/token-hash:\s*[0-9a-f]{64}/i.test(fs.readFileSync(seed, 'utf8')),
    'every token-hash in the seed is a visible placeholder');

  // --- 8. The gate ACCEPTS a well-formed 0600 registry — it discriminates.
  const good = write('good.yaml', VALID_YAML, 0o600);
  const senders = loadSendersFile(good);
  check('a well-formed 0600 senders_file is ACCEPTED (the gate discriminates, not just denies)',
    Array.isArray(senders) && senders.length === 1 && senders[0].id === 'probe-owner' && senders[0].kind === 'owner',
    `loaded ${senders.length} sender(s)`);
  check('the loaded sender carries NO plaintext token (only the hash ever rests on disk)',
    !JSON.stringify(senders).includes(TOKEN),
    'plaintext token absent from the loaded registry');

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SKIPPED_COUNT: ${skipped}`);
  out(`STARTUP_GATE_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out(`SKIPPED_COUNT: ${skipped}`);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
}
