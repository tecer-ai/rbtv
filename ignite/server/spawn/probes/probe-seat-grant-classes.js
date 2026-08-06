'use strict';

// Owner ruling "1a" (2026-08-06) — the three CROSS-GOAL INSTRUMENT grant classes:
//
//   bus-write: true    RW the coordination dir of EVERY goal's OPEN run
//   local-bin: true    ro-bind the invoking user's ~/.local/bin
//   gateway-env: true  IGNITE_GATEWAY_ADDR in the session's environment (a --setenv, not a mount)
//
// This probe drives `composeCageFor` — the ONE composer both spawn doors use — against a real goal
// tree on disk and against the SHIPPED template (`config/spawn-profiles.yaml`'s `cage.SeatBinds`,
// read from the file, never retyped here). Retyping the template would test a copy: the whole
// claim is that the shipped line order composes these openings, so the shipped file is the input.
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

const GATEWAY_ADDR = '127.0.0.1:7431';
const LOCAL_BIN = path.join(os.homedir(), '.local', 'bin');

// The SHIPPED cage template.
function shippedSeatBinds() {
  const cfg = yaml.load(fs.readFileSync(path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml'), 'utf8'));
  return cfg.cage.SeatBinds;
}

// A workspace with FOUR goals, so every branch of the open-run scan is exercised by data rather
// than by argument: one goal whose open run has a coordination dir (granted) and whose CLOSED run
// also has one (must NOT be granted), a second goal with an open run (granted — this is the
// cross-goal opening the ruling is about), a goal whose open run has no coordination dir at all
// (skipped, never created), and a goal with no open run.
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'grant-classes-'));
  const ws = path.join(root, 'ws');
  const goals = path.join(ws, '.rbtv', 'goals');

  const mk = (goal, runsCsv, dirs) => {
    const goalDir = path.join(goals, goal);
    fs.mkdirSync(goalDir, { recursive: true });
    fs.writeFileSync(path.join(goalDir, 'runs.csv'), runsCsv);
    for (const d of dirs) fs.mkdirSync(path.join(goalDir, d), { recursive: true });
    return goalDir;
  };

  const HEADER = 'run-id,type,state,taskforce-ids,opened,closed\n';
  const alpha = mk('alpha',
    `${HEADER}run-0,fresh,closed,tf-0,2026-08-01 01:00,2026-08-02 01:00\nrun-1,fresh,open,tf-1,2026-08-02 01:00,\n`,
    ['runs/run-0/coordination', 'runs/run-1/coordination', 'runs/run-1/seats/mine', 'runs/run-1/seats/plain']);
  const beta = mk('beta', `${HEADER}run-1,fresh,open,tf-1,2026-08-02 01:00,\n`, ['runs/run-1/coordination']);
  const gamma = mk('gamma', `${HEADER}run-1,fresh,open,tf-1,2026-08-02 01:00,\n`, ['runs/run-1']);
  const delta = mk('delta', `${HEADER}run-1,fresh,closed,tf-1,2026-08-02 01:00,2026-08-03 01:00\n`, ['runs/run-1/coordination']);

  const runDir = path.join(alpha, 'runs', 'run-1');
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\nmine,s1,1,1\n');

  // The DECLARING seat — the channel-master's shape (read-root plus the three new keys).
  fs.writeFileSync(path.join(runDir, 'seats', 'mine', 'seat.md'),
    '---\nseat: mine\nread-root: true\nbus-write: true\nlocal-bin: true\ngateway-env: true\n---\nbriefing\n');
  // The seat that declares NOTHING — the fail-closed control.
  fs.writeFileSync(path.join(runDir, 'seats', 'plain', 'seat.md'), '---\nseat: plain\n---\nbriefing\n');

  fs.writeFileSync(path.join(beta, 'runs', 'run-1', 'coordination', 'messages.md'), 'peer goal bus\n');

  return {
    root, ws, runDir,
    mineDir: path.join(runDir, 'seats', 'mine'),
    plainDir: path.join(runDir, 'seats', 'plain'),
    sessionsCsv: path.join(runDir, 'sessions.csv'),
    ownCoord: path.join(runDir, 'coordination'),
    betaCoord: path.join(beta, 'runs', 'run-1', 'coordination'),
    closedCoord: path.join(alpha, 'runs', 'run-0', 'coordination'),
    gammaRun: path.join(gamma, 'runs', 'run-1'),
    deltaCoord: path.join(delta, 'runs', 'run-1', 'coordination'),
  };
}

const { parseSeatPath } = require('../../seat-identity/seat-folder');

function cageFor(seatDir) {
  return composeCageFor({ SeatBinds: shippedSeatBinds() }, parseSeatPath(seatDir), seatDir, GATEWAY_ADDR);
}

// `--bind SRC DEST` pairs only — a ro-bind of the same path is NOT a write opening.
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

capture('probe-seat-grant-classes', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    const granted = cageFor(f.mineDir);
    const plain = cageFor(f.plainDir);

    // ── G1 — bus-write resolves the OPEN runs of EVERY goal, and only those.
    leg('G1a', "a declaring seat gets RW on another goal's open-run coordination dir",
      hasFlag(granted, '--bind', f.betaCoord), `--bind ${f.betaCoord}: ${hasFlag(granted, '--bind', f.betaCoord)}`);
    leg('G1b', "its OWN open run's coordination dir is RW (and the duplicate opening is harmless)",
      granted.filter((a, i) => a === '--bind' && granted[i + 1] === f.ownCoord).length >= 1,
      `own-coordination --bind count ${granted.filter((a, i) => a === '--bind' && granted[i + 1] === f.ownCoord).length}`);
    leg('G1c', 'a CLOSED run of the same goal is NOT bound at all',
      !granted.includes(f.closedCoord), `closed-run coordination present in flags: ${granted.includes(f.closedCoord)}`);
    leg('G1d', 'a goal whose open run has NO coordination dir contributes nothing (never created)',
      !granted.some((a) => a.startsWith(f.gammaRun)) && !fs.existsSync(path.join(f.gammaRun, 'coordination')),
      `flags mention gamma run: ${granted.some((a) => a.startsWith(f.gammaRun))}; dir created on disk: ${fs.existsSync(path.join(f.gammaRun, 'coordination'))}`);
    leg('G1e', 'a goal with no OPEN run contributes nothing',
      !granted.includes(f.deltaCoord), `delta (closed-only) coordination present: ${granted.includes(f.deltaCoord)}`);

    // ── G2 — local-bin, ro. Skipped-with-a-verdict when the box has no ~/.local/bin: the grant
    // resolver requires the path to EXIST, so asserting a bind on a box without one would be a
    // check that fails for the wrong reason.
    if (fs.existsSync(LOCAL_BIN)) {
      leg('G2', 'local-bin is bound READ-ONLY (never rw), at os.homedir()/.local/bin',
        hasFlag(granted, '--ro-bind', LOCAL_BIN) && !hasFlag(granted, '--bind', LOCAL_BIN),
        `--ro-bind ${LOCAL_BIN}: ${hasFlag(granted, '--ro-bind', LOCAL_BIN)}; --bind: ${hasFlag(granted, '--bind', LOCAL_BIN)}`);
    } else {
      leg('G2', 'local-bin: absent on this box, so the grant is correctly empty',
        !granted.includes(LOCAL_BIN), `${LOCAL_BIN} does not exist; flags mention it: ${granted.includes(LOCAL_BIN)}`);
    }

    // ── G3 — gateway-env is an env var, not a mount, and carries NO token.
    const setenvIdx = granted.indexOf('--setenv');
    leg('G3', 'gateway-env passes IGNITE_GATEWAY_ADDR and nothing else',
      setenvIdx >= 0 && granted[setenvIdx + 1] === 'IGNITE_GATEWAY_ADDR' && granted[setenvIdx + 2] === GATEWAY_ADDR
      && granted.filter((a) => a === '--setenv').length === 1,
      `setenv triple: ${JSON.stringify(granted.slice(setenvIdx, setenvIdx + 3))}; setenv count ${granted.filter((a) => a === '--setenv').length}`);

    // ── G4 — THE FAIL-CLOSED CONTROL. A seat declaring none of the keys gets none of it.
    leg('G4', 'a seat declaring NO keys gets no bus-write, no local-bin, no gateway env',
      !plain.includes(f.betaCoord) && !plain.includes(LOCAL_BIN) && !plain.includes('--setenv') && !plain.includes(f.ws),
      `beta coord: ${plain.includes(f.betaCoord)}; local-bin: ${plain.includes(LOCAL_BIN)}; setenv: ${plain.includes('--setenv')}; read-root: ${plain.includes(f.ws)}`);

    // ── G5 — THE INVARIANT SURVIVES. sessions.csv stays unwritable in a bus-write composition,
    // proven on disk from outside the cage; and the cross-goal bus really is writable, proven the
    // same way — the wall and the opening measured by the same instrument.
    const before = bytes(f.sessionsCsv);
    const w = inCage(f.mineDir, granted, `echo "imposter,999,999,999" >> ${f.sessionsCsv}`);
    leg('G5a', 'the run-level sessions.csv is STILL unwritable under bus-write',
      bytes(f.sessionsCsv) === before,
      `on-disk bytes ${bytes(f.sessionsCsv) === before ? 'UNCHANGED' : 'CHANGED — WALL BREACHED'} (in-cage exit ${w.exit}, not the evidence)`);

    const peerFile = path.join(f.betaCoord, 'messages.md');
    inCage(f.mineDir, granted, `echo "a cross-goal message" >> ${peerFile}`);
    leg('G5b', "another goal's open-run coordination dir is genuinely writable from inside the cage",
      bytes(peerFile).includes('a cross-goal message'), `peer bus file now: ${JSON.stringify(bytes(peerFile).trim())}`);

    const envRead = inCage(f.mineDir, granted, 'printf %s "$IGNITE_GATEWAY_ADDR"');
    leg('G5c', 'IGNITE_GATEWAY_ADDR arrives in the caged session',
      envRead.stdout === GATEWAY_ADDR, `in-cage value ${JSON.stringify(envRead.stdout)}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`grant-class probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
