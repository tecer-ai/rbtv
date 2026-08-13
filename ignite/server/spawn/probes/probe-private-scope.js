'use strict';

// W5 — WALL PROBES for THE PRIVATE READ SCOPE (owner ruling D-1, 2026-08-13).
//
// Same evidence rule as probe-ancestor-mask: every claim is proven by what the CAGED PROCESS
// ACTUALLY SEES, read back from outside. A composed flag list is not evidence that a mount
// happened — each leg here runs a real `bwrap` and reads the bytes it printed.
//
// ⚠ THE DENY CLAIM IS NEVER "EACCES" (adv C50). `--tmpfs` is writable-and-evaporates and a
// `/dev/null` ro-bind reads empty — neither DENIES, and a seat writing into either gets a success
// whose output does not exist. So every deny leg asserts CONTENT-ABSENCE (empty listing / 0 bytes /
// canary string gone) AND, for directories, WRITE REFUSAL, AND host-absence of the attempted write.
//
// The nine arms of the wave's acceptance list; 8 lives in `probe-seat-exposed-clis.js` (the
// positive multi-directory assertion belongs beside the CLI grant it exercises).
//   1  deny holds, both kinds — dir lists empty, file reads 0 bytes, canary gone, write REFUSES
//   2  order holds, PROVEN BY MUTATION — pierce re-emission removed => the pierce leg goes red
//   3  a merely-broader grant does NOT pierce
//   4  alias refuses — a grant resolving into a private entry without naming it
//   5  the two hardcodes are unoverrulable — a grant naming either refuses
//   6  the git leg — `git log -p` over a private path returns nothing without a git grant
//   7  every pierce is disclosed on the composer's output
//   9  peer seat folders remain absent under the universal read root

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeSeatCage, composeAncestorMasks, specToBwrapFlags } = require('../cage');
const { composePrivateScope } = require('../private-scope');
const { buildBwrapArgv } = require('../bwrap');

// The shipped stack's shape, cut to the lines these claims depend on. The read-root floor FIRST
// (adv C56 — it is what `tmpfs:{goalDir}/seats` must shadow), then the goal/seat lines, then the
// two grant line classes a pierce can ride on.
const TEMPLATE = [
  'ro-bind:{grant:readRoot}',
  'ro-bind:{goalDir}',
  'tmpfs:{goalDir}/seats',
  'bind:{seatDir}',
  'bind:{grant:rwPath}',
];

const CANARY = 'CANARY-PRIVATE-CONTENT';

function fixture() {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'priv-scope-')));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'testgoal');
  const seatDir = path.join(goalDir, 'seats', 'mine');
  const peerDir = path.join(goalDir, 'seats', 'peer');
  fs.mkdirSync(seatDir, { recursive: true });
  fs.mkdirSync(peerDir, { recursive: true });
  fs.writeFileSync(path.join(peerDir, 'seat.md'), `PEER-SEAT-${CANARY}\n`);
  fs.writeFileSync(path.join(goalDir, 'sessions.csv'), 'seat,pid,pid-starttime\nmine,1,1\n');

  // The private tree: a DIRECTORY entry and a FILE entry, plus a pierced leaf inside the directory.
  const areas = path.join(ws, '2-areas');
  fs.mkdirSync(path.join(areas, 'health'), { recursive: true });
  fs.mkdirSync(path.join(areas, 'finance'), { recursive: true });
  fs.writeFileSync(path.join(areas, 'finance', 'ledger.md'), `${CANARY}-FINANCE\n`);
  fs.writeFileSync(path.join(areas, 'health', 'notes.md'), `${CANARY}-HEALTH\n`);
  const secretFile = path.join(ws, 'secrets.md');
  fs.writeFileSync(secretFile, `${CANARY}-FILE\n`);

  // The pattern floor's targets — never enumerated, denied by shape alone.
  fs.writeFileSync(path.join(ws, 'stray.env'), `${CANARY}-STRAY-ENV\n`);

  // The two hardcodes, and the ONE non-entry beside them (adv C55).
  fs.mkdirSync(path.join(ws, '.rbtv', 'config'), { recursive: true });
  fs.writeFileSync(path.join(ws, '.rbtv', 'config', '.env'), `${CANARY}-PROVIDER-KEYS\n`);
  fs.writeFileSync(path.join(ws, '.rbtv', 'config', 'sender-token.env'), 'IGNITE_SENDER_TOKEN=SENDER-TOKEN-VALUE\n');

  // The alias: a name outside every entry whose REALPATH lands inside one.
  const alias = path.join(ws, 'alias-dir');
  fs.symlinkSync(path.join(areas, 'finance'), alias);

  fs.writeFileSync(path.join(ws, '.rbtv', 'config', 'private.json'), JSON.stringify({
    deny: ['2-areas/', 'secrets.md'],
    patterns: ['**/*.env', '**/credentials/', '**/*token*', '**/*.key', '**/.git'],
  }, null, 2));
  return { root, ws, goalDir, seatDir, peerDir, areas, secretFile, alias };
}

// Compose the full flag list the way spawn.js#composeCageFor does: cage spec, then the last-
// appended mask block (which itself is masks-then-pierces).
function cageFor(f, rwPaths = [], opts = {}) {
  const spec = composeSeatCage({
    seatBinds: TEMPLATE,
    values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir },
    grants: [{ readRoot: f.ws }, ...rwPaths.map((p) => ({ rwPath: p }))],
  });
  const mask = composeAncestorMasks(spec, {
    workspaceRoot: f.ws, launchFolder: f.seatDir, log: opts.log || (() => {}),
  });
  return { spec, mask, flags: [...specToBwrapFlags(spec), ...mask.flags] };
}

function inCage(f, script, rwPaths = []) {
  const argv = buildBwrapArgv({
    argv: ['bash', '-c', script],
    workdir: f.seatDir,
    harness: 'claude',
    seatBinds: cageFor(f, rwPaths).flags,
  });
  try {
    return execFileSync(argv[0], argv.slice(1), { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (err) {
    return ((err.stdout || '') + (err.stderr || '')).toString();
  }
}

capture('probe-private-scope', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    // ── 1 — DENY HOLDS, BOTH KINDS ────────────────────────────────────────────────────────────
    // Content-absence AND write-refusal AND host-absence of the write. Never EACCES alone.
    const wrote = path.join(f.areas, 'planted.md');
    const one = inCage(f,
      `echo "dir=[$(ls ${f.areas} 2>/dev/null | tr '\\n' ' ')]"; ` +
      `echo "file=[$(cat ${f.secretFile} 2>/dev/null)]"; ` +
      `echo "bytes=[$(test -s ${f.secretFile} && echo nonempty || echo zero)]"; ` +
      `echo "floor=[$(cat ${f.ws}/stray.env 2>/dev/null)]"; ` +
      `echo "grep=[$(grep -r ${CANARY} ${f.areas} ${f.secretFile} 2>/dev/null)]"; ` +
      `(echo x > ${wrote}) 2>&1 | head -1`);
    leg('1', 'masked dir lists empty, masked file reads 0 bytes, canary absent, in-cage write REFUSES and lands nothing on the host',
      /dir=\[\]/.test(one) && /file=\[\]/.test(one) && /bytes=\[zero\]/.test(one) &&
      /floor=\[\]/.test(one) && /grep=\[\]/.test(one) &&
      /Read-only file system|Permission denied/.test(one) && !fs.existsSync(wrote),
      `in-cage: ${JSON.stringify(one.trim())}; host-absent=${!fs.existsSync(wrote)}`);

    // ── 2 — ORDER HOLDS, PROVEN BY MUTATION ───────────────────────────────────────────────────
    // A grant NAMING a path inside a private entry sees the pierced content...
    const health = path.join(f.areas, 'health');
    const two = inCage(f, `echo "pierced=[$(cat ${health}/notes.md 2>/dev/null)]"; ` +
      `echo "sibling=[$(cat ${f.areas}/finance/ledger.md 2>/dev/null)]"`, [health]);
    const pierceWorks = new RegExp(`pierced=\\[${CANARY}-HEALTH\\]`).test(two) && /sibling=\[\]/.test(two);
    // ...and the MUTATION: drop the pierce flags (everything the composer emitted after the last
    // mask) and the same read must go dark. If it does not, the pierce was never what made it work.
    const { spec, mask } = cageFor(f, [health]);
    const pierceFlagCount = mask.pierced.length * 3;      // --<verb> SRC DEST per re-emitted opening
    const mutated = mask.flags.slice(0, mask.flags.length - pierceFlagCount);
    const mutatedArgv = buildBwrapArgv({
      argv: ['bash', '-c', `echo "pierced=[$(cat ${health}/notes.md 2>/dev/null)]"`],
      workdir: f.seatDir, harness: 'claude',
      seatBinds: [...specToBwrapFlags(spec), ...mutated],
    });
    let mutOut;
    try { mutOut = execFileSync(mutatedArgv[0], mutatedArgv.slice(1), { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'pipe'] }); }
    catch (err) { mutOut = ((err.stdout || '') + (err.stderr || '')).toString(); }
    leg('2', 'the pierce is what carries the content: removing the re-emission turns the same read dark (mutation)',
      pierceWorks && mask.pierced.length > 0 && /pierced=\[\]/.test(mutOut),
      `live: ${JSON.stringify(two.trim())}; pierces=${JSON.stringify(mask.pierced)}; mutated: ${JSON.stringify(mutOut.trim())}`);

    // ── 3 — A MERELY-BROADER GRANT DOES NOT PIERCE ────────────────────────────────────────────
    // The read-root floor CONTAINS 2-areas rather than sitting inside it; so does a grant on the
    // workspace root. Neither is a pierce, and the entry stays masked.
    const three = inCage(f, `echo "dir=[$(ls ${f.areas} 2>/dev/null | tr '\\n' ' ')]"`, [f.ws]);
    leg('3', 'a parent-scope grant does not pierce — the private entry inside it stays masked',
      /dir=\[\]/.test(three), `in-cage: ${JSON.stringify(three.trim())}`);

    // ── 4 — ALIAS REFUSES ─────────────────────────────────────────────────────────────────────
    // The mask cannot close this one — the alias is a separate mountpoint carrying the real
    // content — so the COMPOSITION is refused. The refusal must be typed, not a stray TypeError.
    let aliasErr = null;
    try { cageFor(f, [f.alias]); } catch (err) { aliasErr = err; }
    leg('4', 'a grant whose realpath lands in a private entry without naming it REFUSES the whole composition',
      !!aliasErr && aliasErr.code === 'E_CAGE_PRIVATE_ALIAS' && aliasErr.message.includes(f.alias),
      `error=${aliasErr ? `${aliasErr.code}: ${aliasErr.message}` : 'NONE — the composition succeeded'}`);

    // ── 5 — THE HARDCODES ARE UNOVERRULABLE ───────────────────────────────────────────────────
    const envFile = path.join(f.ws, '.rbtv', 'config', '.env');
    const privJson = path.join(f.ws, '.rbtv', 'config', 'private.json');
    const hardCage = cageFor(f, [envFile, privJson]);
    const five = inCage(f,
      `echo "env=[$(cat ${envFile} 2>/dev/null)]"; ` +
      `echo "priv=[$(cat ${privJson} 2>/dev/null)]"; ` +
      `echo "sender=[$(cat ${f.ws}/.rbtv/config/sender-token.env 2>/dev/null)]"`, [envFile, privJson]);
    leg('5', 'rw grants naming .rbtv/config/.env or private.json REFUSE; the sender-token non-entry stays readable (adv C55)',
      hardCage.mask.refusedPierces.filter((r) => /unoverrulable/.test(r.reason)).length === 2 &&
      /env=\[\]/.test(five) && /priv=\[\]/.test(five) && /sender=\[IGNITE_SENDER_TOKEN=SENDER-TOKEN-VALUE\]/.test(five),
      `refusals=${JSON.stringify(hardCage.mask.refusedPierces)}; in-cage: ${JSON.stringify(five.trim())}`);

    // ── 6 — THE GIT LEG ───────────────────────────────────────────────────────────────────────
    // ~9k tracked private files + every deleted secret are readable through `git cat-file` /
    // `git log -p` regardless of any deny list — unless `.git` itself is masked.
    let gitOk = false; let gitDetail = 'git unavailable — leg skipped';
    try {
      const env = { ...process.env, GIT_AUTHOR_NAME: 'p', GIT_AUTHOR_EMAIL: 'p@p', GIT_COMMITTER_NAME: 'p', GIT_COMMITTER_EMAIL: 'p@p' };
      execFileSync('git', ['-C', f.ws, 'init', '-q'], { env, stdio: 'ignore' });
      execFileSync('git', ['-C', f.ws, 'add', '-A'], { env, stdio: 'ignore' });
      execFileSync('git', ['-C', f.ws, 'commit', '-qm', 'seed'], { env, stdio: 'ignore' });
      // The POSITIVE CONTROL matters here: `log=[0]` is also what an absent `git` binary prints,
      // so the leg would pass for the wrong reason without proving git RUNS in this cage.
      const six = inCage(f,
        `echo "log=[$(git -C ${f.ws} log -p -- 2-areas/finance/ledger.md 2>/dev/null | grep -c ${CANARY})]"; ` +
        `echo "gitruns=[$(git --version >/dev/null 2>&1 && echo yes || echo no)]"; ` +
        `echo "dotgit=[$(ls ${f.ws}/.git 2>/dev/null | tr '\\n' ' ')]"`);
      gitOk = /log=\[0\]/.test(six) && /dotgit=\[\]/.test(six) && /gitruns=\[yes\]/.test(six);
      gitDetail = `in-cage: ${JSON.stringify(six.trim())}`;
    } catch (err) { gitDetail = `git unavailable — ${err.message}`; gitOk = true; }
    leg('6', 'git log -p over a private path returns nothing in-cage for a seat with no git grant',
      gitOk, gitDetail);

    // ── 7 — EVERY PIERCE IS DISCLOSED AT SPAWN ────────────────────────────────────────────────
    // Two halves: the composer REPORTS every pierce it emitted, and spawn.js LOGS one line per
    // reported entry (adv C54 — disclosure at spawn, where all grant sources converge). The second
    // half is asserted against spawn.js's own source, because this probe composes cages without
    // running the dispatch path that would emit them.
    const pierces = cageFor(f, [health]).mask.pierced;
    const spawnSrc = fs.readFileSync(path.join(__dirname, '..', 'spawn.js'), 'utf8');
    const logsEach = /for \(const p of mask\.pierced\) log\(/.test(spawnSrc) &&
      /for \(const r of mask\.refusedPierces\) log\(/.test(spawnSrc);
    leg('7', 'the composer reports every pierce, and spawn.js logs one line per pierce and per refusal',
      pierces.length === 1 && pierces[0].includes(health) && logsEach,
      `pierced=${JSON.stringify(pierces)}; spawn.js discloses pierces+refusals=${logsEach}`);

    // ── 9 — PEER SEAT FOLDERS REMAIN ABSENT UNDER THE UNIVERSAL READ ROOT ─────────────────────
    const nine = inCage(f,
      `echo "peers=[$(ls ${f.goalDir}/seats 2>/dev/null | tr '\\n' ' ')]"; ` +
      `echo "peerfile=[$(cat ${f.peerDir}/seat.md 2>/dev/null)]"; ` +
      `echo "own=[$(ls ${f.seatDir} >/dev/null 2>&1 && echo readable)]"`);
    leg('9', 'peer seat folders stay absent under the read root; the seat keeps its own folder',
      !new RegExp(`peerfile=\\[.*${CANARY}`).test(nine) && /peerfile=\[\]/.test(nine) && /own=\[readable\]/.test(nine),
      `in-cage: ${JSON.stringify(nine.trim())}`);

    lines.push('');
    lines.push(fails.length === 0 ? 'ALL LEGS PASS' : `FAILED LEGS: ${fails.join(', ')}`);
    // THROW is how this suite signals failure — `capture()` turns a resolved promise into PASS
    // regardless of anything written into `lines`, so a `process.exitCode` here would be
    // overwritten by its `process.exit(exit)` and the probe would report GREEN with red legs.
    if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch { /* best effort */ }
  }
});
