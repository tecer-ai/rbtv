'use strict';

// Owner ruling "a" (2026-08-06) — the `rw-paths` seat-cage grant class:
//
//   rw-paths:
//     - 3-resources/tools/google/credentials
//
// A block list of WORKSPACE-RELATIVE paths bound READ-WRITE, punched back through the read-only
// floor `read-root: true` lays down. Motivating case: gtools cannot rewrite its OAuth token under
// a whole-workspace ro-bind, so the channel-master's mail reads die when the token expires.
//
// Driven through `composeCageFor` — the ONE composer both spawn doors use — against a real goal
// tree on disk and against the SHIPPED template (`config/spawn-profiles.yaml`'s `cage.SeatBinds`,
// read from the file, never retyped here). Retyping it would test a copy; the claim under test is
// that the SHIPPED line order produces these openings.
//
// The evidence rule is probe-seat-cage's (design §6, D51): a write claim is proven ON DISK from
// OUTSIDE the cage, by the target file's bytes. The in-cage exit status is information only.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeCageFor } = require('../spawn');
const { buildBwrapArgv } = require('../bwrap');
const { parseSeatPath } = require('../../seat-identity/seat-folder');

function shippedSeatBinds() {
  const cfg = yaml.load(fs.readFileSync(path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml'), 'utf8'));
  return cfg.cage.SeatBinds;
}

// One seat declaring EVERY class of entry at once — the good one plus each refusal — so the
// composed flag list and the refusal log are read off a single composition rather than five.
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'rw-paths-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'alpha');
  const runDir = goalDir;   // 7.607 E2a — goal-direct: the goal folder IS the package
  const mineDir = path.join(runDir, 'seats', 'mine');
  const plainDir = path.join(runDir, 'seats', 'plain');

  fs.mkdirSync(path.join(runDir, 'coordination'), { recursive: true });
  fs.mkdirSync(mineDir, { recursive: true });
  fs.mkdirSync(plainDir, { recursive: true });
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\nmine,s1,1,1\n');

  // The declared, VALID target: an in-workspace credentials dir (the gtools shape).
  const creds = path.join(ws, '3-resources', 'tools', 'google', 'credentials');
  fs.mkdirSync(creds, { recursive: true });
  fs.writeFileSync(path.join(creds, 'token.json'), '{"stale":true}\n');

  // Something OUTSIDE the workspace for the `..` escape to aim at — it must stay unbound even
  // though it exists, so the refusal cannot be mistaken for the nonexistent-path skip.
  const outside = path.join(root, 'outside');
  fs.mkdirSync(outside, { recursive: true });

  fs.writeFileSync(path.join(mineDir, 'seat.md'), [
    '---',
    'seat: mine',
    'read-root: true',
    'rw-paths:',
    '  - 3-resources/tools/google/credentials',   // valid
    '  - ../outside',                              // escapes the root
    `  - ${outside}`,                              // absolute
    '  - .rbtv/goals/alpha',                       // covers sessions.csv + seat.md
    '  - .rbtv',                                   // CONTAINS the whole goals subtree
    '  - 3-resources/tools/nope',                  // does not exist
    'gateway-env: true',                           // a key AFTER the block: must survive the reader
    '---',
    'briefing',
  ].join('\n') + '\n');
  fs.writeFileSync(path.join(plainDir, 'seat.md'), '---\nseat: plain\nread-root: true\n---\nbriefing\n');

  return { root, ws, mineDir, plainDir, creds, outside, runDir, sessionsCsv: path.join(runDir, 'sessions.csv') };
}

function cageFor(seatDir, logs) {
  const log = (level, message, extra) => logs.push(`${level}: ${message}`);
  return composeCageFor({ SeatBinds: shippedSeatBinds() }, parseSeatPath(seatDir), seatDir, '127.0.0.1:7431', log);
}

function hasFlag(flags, verb, p) {
  for (let i = 0; i < flags.length; i++) {
    if (flags[i] === verb && flags[i + 1] === p) return true;
  }
  return false;
}

function inCage(seatDir, flags, script) {
  const argv = buildBwrapArgv({ argv: ['bash', '-c', script], workdir: seatDir, harness: null, seatBinds: flags });
  try {
    const stdout = execFileSync(argv[0], argv.slice(1), { stdio: ['ignore', 'pipe', 'pipe'], timeout: 30000, encoding: 'utf8' });
    return { exit: 0, stdout: stdout.trim() };
  } catch (err) {
    return { exit: err.status === undefined ? -1 : err.status, stdout: (err.stdout || '').toString().trim() };
  }
}

function bytes(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch (err) { return `<<ABSENT:${err.code}>>`; }
}

capture('probe-seat-rw-paths', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    const logs = [];
    const granted = cageFor(f.mineDir, logs);
    const plainLogs = [];
    const plain = cageFor(f.plainDir, plainLogs);

    const token = path.join(f.creds, 'token.json');
    const nope = path.join(f.ws, '3-resources', 'tools', 'nope');

    // ── R1 — the valid entry composes ONE rw opening, and it lands AFTER the read-root ro floor.
    leg('R1a', 'a declared in-workspace dir is bound READ-WRITE',
      hasFlag(granted, '--bind', f.creds), `--bind ${f.creds}: ${hasFlag(granted, '--bind', f.creds)}`);
    leg('R1b', 'it is ordered AFTER the read-root ro floor (which would otherwise re-cover it)',
      granted.lastIndexOf(f.ws) < granted.lastIndexOf(f.creds),
      `read-root flag index ${granted.lastIndexOf(f.ws)} < rw-path index ${granted.lastIndexOf(f.creds)}`);

    // ── R2 — every refusal composes NOTHING, and says why.
    leg('R2a', 'an escaping entry (../outside) composes nothing',
      !granted.includes(f.outside), `outside path present in flags: ${granted.includes(f.outside)}`);
    leg('R2b', 'an absolute entry composes nothing',
      !hasFlag(granted, '--bind', f.outside), `--bind ${f.outside}: ${hasFlag(granted, '--bind', f.outside)}`);
    leg('R2c', 'an rw-paths entry covering the run folder is still REFUSED (logged); D3 bind:{goalDir} is a different opening',
      logs.some((l) => l.includes('rw-paths entry REFUSED') && l.includes('.rbtv/goals')),
      `runDir bound via template (D3): ${hasFlag(granted, '--bind', f.runDir)}; goals refusal logged: ${logs.some((l) => l.includes('.rbtv/goals'))}`);
    leg('R2d', 'an entry CONTAINING the whole .rbtv/goals subtree composes nothing',
      !granted.includes(path.join(f.ws, '.rbtv')), `.rbtv present in flags: ${granted.includes(path.join(f.ws, '.rbtv'))}`);
    leg('R2e', 'a nonexistent entry is skipped and NEVER created',
      !granted.includes(nope) && !fs.existsSync(nope),
      `flags mention it: ${granted.includes(nope)}; created on disk: ${fs.existsSync(nope)}`);
    leg('R2f', 'every refusal is logged loudly (4 refusals + 1 skip, none silent)',
      logs.filter((l) => l.includes('rw-paths entry REFUSED')).length === 5,
      `refusal log lines: ${JSON.stringify(logs)}`);

    // ── R3 — the block reader does not swallow the keys after the list.
    leg('R3', 'a frontmatter key AFTER the rw-paths block still reads (gateway-env survives)',
      granted.includes('--setenv'), `setenv present: ${granted.includes('--setenv')}`);

    // ── R4 — THE FAIL-CLOSED CONTROL. A seat without the key gets no rw opening at all.
    leg('R4', 'a seat with NO rw-paths key gets nothing (and no refusal log)',
      // Counts REFUSALS, not log lines: composeCageFor logs one unconditional info line per spawn
      // (the ancestor-mask policy), so a bare line count would make this leg fail on any future
      // logging the cage adds — and pass for the wrong reason if rw-paths ever went silent.
      !hasFlag(plain, '--bind', f.creds) && plainLogs.filter((l) => l.includes('rw-paths entry REFUSED')).length === 0,
      `--bind ${f.creds}: ${hasFlag(plain, '--bind', f.creds)}; rw-paths refusals ${plainLogs.filter((l) => l.includes('rw-paths entry REFUSED')).length} (all logs: ${JSON.stringify(plainLogs)})`);

    // ── R5 — measured ON DISK from outside the cage: the opening is real, the wall still holds.
    const w1 = inCage(f.mineDir, granted, `printf '{"fresh":true}\\n' > ${token}`);
    leg('R5a', 'a write into the declared rw path SUCCEEDS from inside the cage',
      bytes(token).includes('fresh'), `on-disk bytes ${JSON.stringify(bytes(token).trim())} (in-cage exit ${w1.exit}, not the evidence)`);

    const before = bytes(f.sessionsCsv);
    const w2 = inCage(f.mineDir, granted, `echo "imposter,999,999,999" >> ${f.sessionsCsv}`);
    leg('R5b', 'the run-level sessions.csv IS writable (D3: ledgers writable; rw-paths does not carve it back)',
      bytes(f.sessionsCsv) !== before && bytes(f.sessionsCsv).includes('imposter,999,999,999'),
      `on-disk bytes ${bytes(f.sessionsCsv) === before ? 'UNCHANGED — FENCE TOO TIGHT' : 'GREW'} (in-cage exit ${w2.exit}, not the evidence)`);

    const outsideFile = path.join(f.outside, 'reached.txt');
    inCage(f.mineDir, granted, `echo reached > ${outsideFile}`);
    leg('R5c', 'the refused out-of-workspace path is not reachable for write',
      !fs.existsSync(outsideFile), `file created outside the workspace: ${fs.existsSync(outsideFile)}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`rw-paths probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
