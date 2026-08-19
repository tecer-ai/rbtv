'use strict';

// W6 — the `cli-write-roots:` seat-cage grant class (owner ruling W6/R2, 2026-08-14).
//
// The chain the MATERIALIZER walks: a seat exposes a SKILL; the skill's entry-point file declares
// `exposes-cli:`; each of those CLIs' `exposure.csv` rows declares `write-roots`; the resolved
// absolute roots are baked into the seat's `seat.md` as `cli-write-roots:`. spawn.js only READS
// that key — this probe measures the reading and the wall it produces, never the chain (that half
// is `materialize-seats.py --selftest` row EXP-1).
//
// THE CLAIM UNDER TEST, in the ruling's own words: a seat exposing a skill whose CLI declares a
// write-root can write INSIDE the root in-cage, and is DENIED one level up. The second half is the
// whole point — a grant that quietly widened to the parent would hand every such seat the tool's
// entire install tree.
//
// Driven through `composeCageFor` — the ONE composer both spawn doors use — against a real goal
// tree on disk and against the SHIPPED template (`config/spawn-profiles.yaml`'s `cage.SeatBinds`,
// read from the file, never retyped: retyping would test a copy, and the claim is that the SHIPPED
// line order produces these openings).
//
// Evidence rule is probe-seat-cage's (design §6, D51): a write claim is proven ON DISK from
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

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cli-write-roots-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'alpha');
  const mineDir = path.join(goalDir, 'seats', 'mine');
  const plainDir = path.join(goalDir, 'seats', 'plain');

  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.mkdirSync(mineDir, { recursive: true });
  fs.mkdirSync(plainDir, { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\nmine,s1,1,1\n');

  // The CLI's install tree. `state/` is the declared write root; `tool/` is its SIBLING and the
  // parent is the level up — both must stay read-only, or the grant is not a root, it is a tree.
  const cli = path.join(ws, '3-resources', 'tools', 'demo-cli');
  const stateDir = path.join(cli, 'state');
  fs.mkdirSync(stateDir, { recursive: true });
  fs.mkdirSync(path.join(cli, 'tool'), { recursive: true });
  fs.writeFileSync(path.join(stateDir, 'cache.json'), '{"stale":true}\n');
  fs.writeFileSync(path.join(cli, 'tool', 'demo.py'), "print('demo')\n");

  fs.writeFileSync(path.join(mineDir, 'seat.md'), [
    '---',
    'seat: mine',
    'cli-write-roots:',
    `  - ${stateDir}`,                              // valid: the CLI's declared state dir
    `  - ${path.join(goalDir, 'coordination')}`,    // overlaps .rbtv/goals — must be REFUSED
    '  - 3-resources/tools/demo-cli/state',         // relative: the materializer resolves, so refuse
    `  - ${path.join(cli, 'nowhere')}`,             // does not exist — never created from here
    'gateway-env: true',                            // a key AFTER the block: must survive the reader
    '---',
    'briefing',
  ].join('\n') + '\n');
  fs.writeFileSync(path.join(plainDir, 'seat.md'), '---\nseat: plain\n---\nbriefing\n');

  return { root, ws, cli, stateDir, mineDir, plainDir, goalDir,
           sessionsCsv: path.join(goalDir, 'sessions.csv') };
}

function cageFor(seatDir, logs) {
  const log = (level, message) => logs.push(`${level}: ${message}`);
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

capture('probe-cli-write-roots', async (lines) => {
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

    // ── C1 — the valid root composes ONE rw opening, ordered after the read-root ro floor.
    leg('C1a', 'the declared CLI write root is bound READ-WRITE',
      hasFlag(granted, '--bind', f.stateDir), `--bind ${f.stateDir}: ${hasFlag(granted, '--bind', f.stateDir)}`);
    leg('C1b', 'it is ordered AFTER the read-root ro floor (which would otherwise re-cover it)',
      granted.lastIndexOf(f.ws) < granted.lastIndexOf(f.stateDir),
      `read-root flag index ${granted.lastIndexOf(f.ws)} < cli-write-root index ${granted.lastIndexOf(f.stateDir)}`);

    // ── C2 — every refusal composes NOTHING, and says why. Same four rules as `rw-paths`,
    // enforced by the SAME predicate (`rwPathRefusal`), so a divergence here is a code defect.
    leg('C2a', 'an entry overlapping .rbtv/goals composes no rw opening',
      !hasFlag(granted, '--bind', path.join(f.goalDir, 'coordination')) ||
        granted.lastIndexOf(path.join(f.goalDir, 'coordination')) < granted.lastIndexOf(f.stateDir),
      `the ONLY coordination opening is the template's own literal line, not this grant`);
    leg('C2b', 'a RELATIVE entry composes nothing — the materializer resolves, this reader never guesses',
      logs.some((l) => l.includes('cli-write-roots entry REFUSED') && l.includes('not absolute')),
      `refusal log: ${JSON.stringify(logs.filter((l) => l.includes('cli-write-roots')))}`);
    leg('C2c', 'a nonexistent entry is skipped and NEVER created',
      !fs.existsSync(path.join(f.cli, 'nowhere')),
      `created on disk: ${fs.existsSync(path.join(f.cli, 'nowhere'))}`);
    leg('C2d', 'every refusal is logged loudly (3 refusals, none silent)',
      logs.filter((l) => l.includes('cli-write-roots entry REFUSED')).length === 3,
      `refusal log lines: ${JSON.stringify(logs.filter((l) => l.includes('cli-write-roots')))}`);

    // ── C3 — the block reader does not swallow the keys after the list.
    leg('C3', 'a frontmatter key AFTER the cli-write-roots block still reads (gateway-env survives)',
      granted.includes('--setenv'), `setenv present: ${granted.includes('--setenv')}`);

    // ── C4 — THE FAIL-CLOSED CONTROL. A seat without the key gets no opening and no refusal.
    leg('C4', 'a seat with NO cli-write-roots key gets nothing (and no refusal log)',
      !hasFlag(plain, '--bind', f.stateDir) &&
        plainLogs.filter((l) => l.includes('cli-write-roots entry REFUSED')).length === 0,
      `--bind ${f.stateDir}: ${hasFlag(plain, '--bind', f.stateDir)}; refusals ${plainLogs.filter((l) => l.includes('cli-write-roots entry REFUSED')).length}`);

    // ── C5 — THE RULING'S OWN CLAIM, measured ON DISK from outside the cage.
    const inside = path.join(f.stateDir, 'cache.json');
    const w1 = inCage(f.mineDir, granted, `printf '{"fresh":true}\\n' > ${inside}`);
    leg('C5a', 'a write INSIDE the declared root SUCCEEDS from inside the cage',
      bytes(inside).includes('fresh'),
      `on-disk bytes ${JSON.stringify(bytes(inside).trim())} (in-cage exit ${w1.exit}, not the evidence)`);

    const oneUp = path.join(f.cli, 'escaped.txt');
    const w2 = inCage(f.mineDir, granted, `echo reached > ${oneUp}`);
    leg('C5b', 'a write ONE LEVEL UP is DENIED — the grant is a root, not the tool tree',
      !fs.existsSync(oneUp),
      `file created one level up: ${fs.existsSync(oneUp)} (in-cage exit ${w2.exit}, not the evidence)`);

    const sibling = path.join(f.cli, 'tool', 'demo.py');
    const beforeSibling = bytes(sibling);
    const w3 = inCage(f.mineDir, granted, `echo tampered > ${sibling}`);
    leg('C5c', "the root's SIBLING (the CLI's own code) stays read-only",
      bytes(sibling) === beforeSibling,
      `${bytes(sibling) === beforeSibling ? 'UNCHANGED' : 'CHANGED — WALL BREACHED'} (in-cage exit ${w3.exit}, not the evidence)`);

    const beforeSessions = bytes(f.sessionsCsv);
    const w4 = inCage(f.mineDir, granted, `echo "imposter,999,999,999" >> ${f.sessionsCsv}`);
    leg('C5d', 'the goal sessions.csv IS writable (D3: ledgers writable; cli-write-roots does not carve it back)',
      bytes(f.sessionsCsv) !== beforeSessions && bytes(f.sessionsCsv).includes('imposter,999,999,999'),
      `${bytes(f.sessionsCsv) === beforeSessions ? 'UNCHANGED — FENCE TOO TIGHT' : 'GREW'} (in-cage exit ${w4.exit}, not the evidence)`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`cli-write-roots probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
