'use strict';

// `d-path-exposes-authorable` (owner, 2026-08-10) — the SANDBOX realization of a prompt card's
// `exposes: path:` declaration. materialize resolves each declared part against its component's
// exposure.csv and writes the enabled-CLI set into the seat descriptor:
//
//   exposed-clis:
//     - coordinate /…/rbtv/ignite/team-kit/coord.py
//
// The cage binds BOTH ENDS read-only — the code tree at its real path, and the installed NAME as a
// sandbox symlink on PATH. A seat declaring nothing gets nothing.
//
// RED FIRST, IN THE SAME LAYOUT: the undeclared seat's legs run before the declared seat's, off
// the same fixture and the same shipped template, so "the CLI runs" is measured against a control
// in which it demonstrably does not. The evidence rule is probe-seat-cage's (design §6, D51): a
// reachability claim is proven by RUNNING the thing inside the cage, never by reading the flags —
// the flag legs below are the mechanism, the exec legs are the claim.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeCageFor } = require('../spawn');
const { buildBwrapArgv } = require('../bwrap');
const { parseSeatPath } = require('../../seat-identity/seat-folder');

// The SHIPPED template, read from the file — never retyped. The claim under test is that the
// shipped line order plus the code-appended grant line produce these openings.
function shippedSeatBinds() {
  const cfg = yaml.load(fs.readFileSync(path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml'), 'utf8'));
  return cfg.cage.SeatBinds;
}

// The real subject: the team-kit coordination CLI, which is exactly what 7.607 E4 measured
// unreachable from inside a composed cage. Resolved from THIS file's position, so the probe moves
// with the tree rather than carrying an instance path.
const CODE_TREE = path.resolve(__dirname, '..', '..', '..', 'team-kit');
const ENTRY = path.join(CODE_TREE, 'coord.py');

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'exposed-clis-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'alpha');
  const mineDir = path.join(goalDir, 'seats', 'mine');
  const plainDir = path.join(goalDir, 'seats', 'plain');

  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.mkdirSync(mineDir, { recursive: true });
  fs.mkdirSync(plainDir, { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\nmine,s1,1,1\n');
  fs.writeFileSync(path.join(plainDir, 'secret.txt'), 'peer seat content\n');

  // One seat declaring the good entry plus EVERY refusal class, so the composition and the refusal
  // log are read off a single compose rather than four.
  fs.writeFileSync(path.join(mineDir, 'seat.md'), [
    '---',
    'seat: mine',
    'exposed-clis:',
    `  - coordinate ${ENTRY}`,        // valid
    '  - noseparator',                 // no `<name> <path>` split
    '  - ../evil /usr/bin/env',        // name is not a part-id
    '  - rel team-kit/coord.py',       // target is not absolute
    `  - ghost ${path.join(root, 'nonexistent', 'x')}`, // target does not exist
    'gateway-env: true',               // a key AFTER the block: must survive the list reader
    '---',
    'briefing',
  ].join('\n') + '\n');
  // THE CONTROL: same tree, same template, no declaration.
  fs.writeFileSync(path.join(plainDir, 'seat.md'), '---\nseat: plain\n---\nbriefing\n');

  return { root, ws, goalDir, mineDir, plainDir };
}

function cageFor(seatDir, logs) {
  const log = (level, message) => logs.push(`${level}: ${message}`);
  return composeCageFor({ SeatBinds: shippedSeatBinds() }, parseSeatPath(seatDir), seatDir, '127.0.0.1:7431', log);
}

function hasFlag(flags, verb, a, b) {
  for (let i = 0; i < flags.length; i++) {
    if (flags[i] === verb && flags[i + 1] === a && (b === undefined || flags[i + 2] === b)) return true;
  }
  return false;
}

function pathEnv(flags) {
  for (let i = 0; i < flags.length; i++) {
    if (flags[i] === '--setenv' && flags[i + 1] === 'PATH') return flags[i + 2];
  }
  return null;
}

function inCage(seatDir, flags, script) {
  const argv = buildBwrapArgv({ argv: ['bash', '-c', script], workdir: seatDir, harness: null, seatBinds: flags });
  try {
    const stdout = execFileSync(argv[0], argv.slice(1), { stdio: ['ignore', 'pipe', 'pipe'], timeout: 60000, encoding: 'utf8' });
    return { exit: 0, out: stdout.trim() };
  } catch (err) {
    return { exit: err.status === undefined ? -1 : err.status, out: ((err.stdout || '') + (err.stderr || '')).toString().trim() };
  }
}

capture('probe-seat-exposed-clis', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  const rbtvBin = path.join(os.homedir(), '.rbtv-bin');

  try {
    if (!fs.existsSync(ENTRY)) throw new Error(`fixture precondition: ${ENTRY} is absent — the probe's subject must exist`);

    const plainLogs = [];
    const plain = cageFor(f.plainDir, plainLogs);
    const logs = [];
    const granted = cageFor(f.mineDir, logs);

    // ── RED CONTROL FIRST — the undeclared seat, same layout, same template ──────────────────
    leg('X0a', 'a seat with NO exposed-clis key composes no symlink, no code-tree bind, no PATH',
      !plain.includes('--symlink') && !hasFlag(plain, '--ro-bind', CODE_TREE) && pathEnv(plain) === null,
      `symlink: ${plain.includes('--symlink')}; ro-bind ${CODE_TREE}: ${hasFlag(plain, '--ro-bind', CODE_TREE)}; PATH: ${pathEnv(plain)}`);
    const red = inCage(f.plainDir, plain, 'coordinate --help');
    leg('X0b', 'RED: `coordinate --help` is UNREACHABLE from inside the undeclared seat\'s cage',
      red.exit !== 0 && !/Coordination CLI/.test(red.out),
      `exit ${red.exit}; output ${JSON.stringify(red.out.slice(0, 160))}`);

    // ── X1 — the composition: both ends, plus the name on PATH ───────────────────────────────
    leg('X1a', 'the declared CLI\'s CODE TREE is bound READ-ONLY at its real path',
      hasFlag(granted, '--ro-bind', CODE_TREE, CODE_TREE),
      `--ro-bind ${CODE_TREE} ${CODE_TREE}: ${hasFlag(granted, '--ro-bind', CODE_TREE, CODE_TREE)}`);
    leg('X1b', 'the installed NAME is a sandbox symlink onto the real entry point',
      hasFlag(granted, '--symlink', ENTRY, path.join(rbtvBin, 'coordinate')),
      `--symlink ${ENTRY} ${path.join(rbtvBin, 'coordinate')}: ${hasFlag(granted, '--symlink', ENTRY, path.join(rbtvBin, 'coordinate'))}`);
    leg('X1c', 'that bin dir leads PATH — a mount the occupant cannot NAME is not a grant',
      (pathEnv(granted) || '').split(':')[0] === rbtvBin, `PATH=${pathEnv(granted)}`);

    // ── X2 — every refusal composes NOTHING, and says why ────────────────────────────────────
    const refusals = logs.filter((l) => l.includes('exposed-clis entry REFUSED'));
    leg('X2a', 'all four malformed entries are refused per entry and logged loudly',
      refusals.length === 4, `refusals: ${JSON.stringify(refusals)}`);
    leg('X2b', 'no refused entry composes a symlink (exactly one symlink pair: the valid one)',
      granted.filter((x) => x === '--symlink').length === 1,
      `symlink flag count: ${granted.filter((x) => x === '--symlink').length}`);
    leg('X2c', 'a frontmatter key AFTER the block still reads (gateway-env survives the list reader)',
      hasFlag(granted, '--setenv', 'IGNITE_GATEWAY_ADDR'), `IGNITE_GATEWAY_ADDR emitted: ${hasFlag(granted, '--setenv', 'IGNITE_GATEWAY_ADDR')}`);

    // ── X3 — GREEN, measured by RUNNING it inside the composed cage ──────────────────────────
    const green = inCage(f.mineDir, granted, 'coordinate --help');
    leg('X3a', 'GREEN: `coordinate --help` RUNS from inside the declared seat\'s cage',
      green.exit === 0 && /Coordination CLI/.test(green.out),
      `exit ${green.exit}; output ${JSON.stringify(green.out.slice(0, 160))}`);
    const which = inCage(f.mineDir, granted, 'command -v coordinate');
    leg('X3b', 'it resolves through the granted bin dir, by the name the seat was promised',
      which.exit === 0 && which.out === path.join(rbtvBin, 'coordinate'), `command -v -> ${JSON.stringify(which.out)}`);

    // ── X4 — the grant does not widen anything else ──────────────────────────────────────────
    // A UNIQUE marker, not a length compare: the baseline for a length compare would have to be
    // read after the attempt (a guard reading its own constant — it passes for any change), and
    // the subject is a live file another session may be editing concurrently, which would make a
    // length compare fail for the wrong reason. The marker answers exactly one question: did MY
    // write land? It also never reaches the file, so nothing needs cleaning up after a pass.
    const marker = `RBTV-CAGE-BREACH-${process.pid}-${Date.now()}`;
    const ro = inCage(f.mineDir, granted, `echo ${marker} >> ${ENTRY} 2>&1; echo rc=$?`);
    leg('X4a', 'the code tree is READ-ONLY from inside — the write is refused and no byte lands',
      !fs.readFileSync(ENTRY, 'utf8').includes(marker) && /rc=[1-9]/.test(ro.out),
      `in-cage: ${JSON.stringify(ro.out.slice(0, 120))}; marker present in ${ENTRY}: ${fs.readFileSync(ENTRY, 'utf8').includes(marker)}`);
    // …and the GREEN CONTROL for that detector, in the same cage and the same layout: the same
    // marker written to a path this cage DOES open (the seat's own folder) must land. Without it
    // X4a passes for any reason a write fails, including a broken script.
    const wmarker = `RBTV-CAGE-WRITABLE-${process.pid}-${Date.now()}`;
    const wpath = path.join(f.mineDir, 'control.txt');
    inCage(f.mineDir, granted, `echo ${wmarker} > ${wpath}`);
    leg('X4a-control', 'the same marker DOES land in a path the cage opens — X4a is red-capable',
      fs.existsSync(wpath) && fs.readFileSync(wpath, 'utf8').includes(wmarker),
      `marker present in the seat's own folder: ${fs.existsSync(wpath) && fs.readFileSync(wpath, 'utf8').includes(wmarker)}`);
    const peer = inCage(f.mineDir, granted, `cat ${path.join(f.plainDir, 'secret.txt')} 2>&1; echo rc=$?`);
    leg('X4b', 'a SIBLING seat folder stays unreachable (the peer-seat tmpfs still holds)',
      !/peer seat content/.test(peer.out), `in-cage: ${JSON.stringify(peer.out.slice(0, 160))}`);
    const ghost = inCage(f.mineDir, granted, 'command -v ghost; command -v rel; echo rc=$?');
    leg('X4c', 'a REFUSED entry grants nothing — its name resolves to no command',
      !/\/ghost/.test(ghost.out) && !/\/rel/.test(ghost.out), `in-cage: ${JSON.stringify(ghost.out.slice(0, 160))}`);

    // ── X5 — W5 / ruling D-1: a MULTI-DIRECTORY CLI runs green in-cage ───────────────────────
    // THE POSITIVE HALF of the private-scope wave, and the one D1 itself measured red: every leg
    // above exercises a CLI that reads nothing but its own directory. `rbtv teambuild` is the
    // opposite shape — its code `require`s a SIBLING capability's `lib/render`, and its corpus is
    // a `.rbtv/mirror` data root somewhere else entirely. Under the old per-seat `read-root`
    // declaration this seat (which declares none) saw neither and crashed; under the universal
    // read root it resolves both. A red here means the cage has gone back to binding only the
    // entry point's own folder.
    const CAPS = path.resolve(__dirname, '..', '..', '..', '..', 'core', 'capabilities');
    if (!fs.existsSync(path.join(CAPS, 'teambuild', 'tool', 'rbtv-teambuild'))) {
      throw new Error(`fixture precondition: ${CAPS}/teambuild/tool/rbtv-teambuild is absent — X5's subject must exist`);
    }
    // The two code trees are COPIED INTO the fixture workspace, because that is where they sit in
    // production (`<ws>/3-resources/tools/rbtv/…`) and the whole claim is that the seat reaches the
    // SIBLING one through the workspace read root rather than through its own grant. Copying keeps
    // the probe free of any instance path while preserving the production topology; exposing the
    // repo's own copy instead would test a layout no deployment has.
    const repo = path.join(f.ws, 'tools', 'rbtv', 'core', 'capabilities');
    fs.cpSync(path.join(CAPS, 'teambuild'), path.join(repo, 'teambuild'), { recursive: true });
    fs.cpSync(path.join(CAPS, 'rbtv-cli'), path.join(repo, 'rbtv-cli'), { recursive: true });
    const TEAMBUILD = path.join(repo, 'teambuild', 'tool', 'rbtv-teambuild');
    const multiDir = path.join(f.goalDir, 'seats', 'multi');
    fs.mkdirSync(multiDir, { recursive: true });
    fs.writeFileSync(path.join(multiDir, 'seat.md'),
      `---\nseat: multi\nexposed-clis:\n  - teambuild ${TEAMBUILD}\n---\nbriefing\n`);
    // The corpus root: a real mirror shape inside the fixture workspace, i.e. a data root the CLI
    // reaches only because the WORKSPACE is readable, not because its own directory is.
    const mirror = path.join(f.ws, '.rbtv', 'mirror', 'demo', 'demo');   // <mirror>/<module>/<component>
    fs.mkdirSync(mirror, { recursive: true });
    fs.writeFileSync(path.join(mirror, 'seats.csv'), 'seat-id,description\nds-1,A demo seat row\n');
    const multi = cageFor(multiDir, []);
    const census = inCage(multiDir, multi, `teambuild seats --root ${path.join(f.ws, '.rbtv', 'mirror')} --json 2>&1`);
    leg('X5', 'a MULTI-DIRECTORY CLI (sibling code tree + a data root elsewhere) runs GREEN in-cage',
      census.exit === 0 && /ds-1/.test(census.out),
      `exit ${census.exit}; output ${JSON.stringify(census.out.slice(0, 240))}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`exposed-clis probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
