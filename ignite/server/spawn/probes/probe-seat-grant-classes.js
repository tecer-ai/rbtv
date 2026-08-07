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
    '---\nseat: mine\nread-root: true\nbus-write: true\ngoals-write: true\nlocal-bin: true\ngateway-env: true\n---\nbriefing\n');
  // The seat that declares NOTHING — the fail-closed control.
  fs.writeFileSync(path.join(runDir, 'seats', 'plain', 'seat.md'), '---\nseat: plain\n---\nbriefing\n');

  fs.writeFileSync(path.join(beta, 'runs', 'run-1', 'coordination', 'messages.md'), 'peer goal bus\n');
  // The goals-write target: a peer goal's open run with the two surfaces the materializer writes
  // (a seats/ dir, a taskforce.csv) AND the ground truth the grant must carve back read-only.
  fs.mkdirSync(path.join(beta, 'runs', 'run-1', 'seats'), { recursive: true });
  fs.writeFileSync(path.join(beta, 'runs', 'run-1', 'taskforce.csv'), 'taskforce-id,seat\n');
  fs.writeFileSync(path.join(beta, 'runs', 'run-1', 'sessions.csv'), 'seat,session-id,pid,pid-starttime\nthem,s9,9,9\n');

  return {
    root, ws, runDir,
    betaRun: path.join(beta, 'runs', 'run-1'),
    betaSessions: path.join(beta, 'runs', 'run-1', 'sessions.csv'),
    betaTaskforce: path.join(beta, 'runs', 'run-1', 'taskforce.csv'),
    betaSeats: path.join(beta, 'runs', 'run-1', 'seats'),
    deltaRun: path.join(delta, 'runs', 'run-1'),
    alphaClosedRun: path.join(alpha, 'runs', 'run-0'),
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

// bwrap does NOT clear the environment, so a caged child inherits the SPAWNER's PATH. In
// production that spawner is the daemon under the systemd --user manager, whose PATH has no
// ~/.local/bin — that absence is the whole reason the PATH setenv exists. This probe runs from an
// interactive shell whose PATH usually DOES have it, which would let the local-bin resolution leg
// pass with the grant removed (measured: it did). So the child env is pinned to the manager-shaped
// PATH here, and only the composed `--setenv PATH` can put ~/.local/bin back.
const MANAGER_PATH = '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin';

function inCage(seatDir, flags, script) {
  const argv = buildBwrapArgv({ argv: ['bash', '-c', script], workdir: seatDir, harness: null, seatBinds: flags });
  const env = { ...process.env, PATH: MANAGER_PATH };
  try {
    const stdout = execFileSync(argv[0], argv.slice(1), { stdio: ['ignore', 'pipe', 'pipe'], timeout: 30000, encoding: 'utf8', env });
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
    // Class-specific by construction: the claim is that BUS-WRITE contributes nothing for a run
    // with no coordination dir, so it is asserted on that dir — not on "no flag mentions this
    // run", which another grant class over the same run folder (goals-write) legitimately does.
    leg('G1d', 'a goal whose open run has NO coordination dir contributes no bus opening (never created)',
      !granted.includes(path.join(f.gammaRun, 'coordination')) && !fs.existsSync(path.join(f.gammaRun, 'coordination')),
      `gamma coordination in flags: ${granted.includes(path.join(f.gammaRun, 'coordination'))}; dir created on disk: ${fs.existsSync(path.join(f.gammaRun, 'coordination'))}`);
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

    // ── G2b/G2c — the bind is only half the grant: the CLIs must resolve BY NAME. A caged
    // session inherits the systemd user manager's PATH, which has no ~/.local/bin, so before the
    // PATH setenv every promised CLI was "command not found" with its directory mounted.
    if (fs.existsSync(LOCAL_BIN)) {
      const pathIdx = granted.indexOf('PATH');
      leg('G2b', 'local-bin also puts ~/.local/bin FIRST on the caged PATH',
        pathIdx > 0 && granted[pathIdx - 1] === '--setenv' && granted[pathIdx + 1].startsWith(`${LOCAL_BIN}:`),
        `setenv PATH = ${JSON.stringify(pathIdx > 0 ? granted[pathIdx + 1] : null)}`);

      // A REGULAR-FILE executable, never a symlink: most ~/.local/bin entries point at targets
      // outside the mounted set (the real workspace, or `claude` under the HOME tmpfs), and a
      // dangling target fails `command -v` for a reason that has nothing to do with PATH. This
      // leg's claim is name RESOLUTION, so it is asserted on an entry whose bytes are right there.
      const exe = fs.readdirSync(LOCAL_BIN).find((n) => {
        try {
          const st = fs.lstatSync(path.join(LOCAL_BIN, n));
          return st.isFile() && (st.mode & 0o111);
        } catch { return false; }
      });
      if (exe) {
        const resolved = inCage(f.mineDir, granted, `command -v ${exe} || echo NOT-FOUND`);
        leg('G2c', 'a user-local CLI resolves by NAME inside the cage (the grant is reachable, not just mounted)',
          resolved.stdout === path.join(LOCAL_BIN, exe), `command -v ${exe} -> ${JSON.stringify(resolved.stdout)}`);
      } else {
        leg('G2c', '~/.local/bin holds no executable to resolve — nothing to assert', true, `${LOCAL_BIN} has no executable file`);
      }
    }

    // ── G3 — gateway-env is an env var, not a mount, and carries NO token.
    const setenvIdx = granted.indexOf('--setenv');
    // The claim is that NO TOKEN rides this list — so it is asserted as a whitelist of variable
    // NAMES, not as a count. A count breaks the moment another grant class legitimately sets one
    // (PATH did), and "the count changed" is not the failure anyone cares about here.
    const setenvNames = granted.filter((a, i) => granted[i - 1] === '--setenv');
    leg('G3', 'gateway-env passes IGNITE_GATEWAY_ADDR, and the only other var set is PATH — no token ever rides',
      setenvIdx >= 0 && granted[setenvIdx + 1] === 'IGNITE_GATEWAY_ADDR' && granted[setenvIdx + 2] === GATEWAY_ADDR
      && setenvNames.every((n) => n === 'IGNITE_GATEWAY_ADDR' || n === 'PATH'),
      `setenv triple: ${JSON.stringify(granted.slice(setenvIdx, setenvIdx + 3))}; all setenv names ${JSON.stringify(setenvNames)}`);

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

    // ── G6 — goals-write: the seat materializer's write set, and the two narrowings that bound it.
    leg('G6a', "a declaring seat gets RW on another goal's OPEN RUN FOLDER (not just its coordination dir)",
      hasFlag(granted, '--bind', f.betaRun), `--bind ${f.betaRun}: ${hasFlag(granted, '--bind', f.betaRun)}`);
    leg('G6b', "the seat's OWN run folder is NEVER granted — the peer-seat tmpfs and seat.md carve stay unshadowed",
      !hasFlag(granted, '--bind', f.runDir), `--bind own runDir: ${hasFlag(granted, '--bind', f.runDir)}`);
    leg('G6c', "each granted run's sessions.csv is carved back READ-ONLY, after the rw opening",
      hasFlag(granted, '--ro-bind', f.betaSessions)
      && granted.lastIndexOf(f.betaSessions) > granted.lastIndexOf(f.betaRun),
      `--ro-bind ${f.betaSessions}: ${hasFlag(granted, '--ro-bind', f.betaSessions)}; carve after bind: ${granted.lastIndexOf(f.betaSessions) > granted.lastIndexOf(f.betaRun)}`);
    // THE SET, not a spot check. Asserting "beta is present" cannot tell an open-run resolver
    // from an every-run one — beta has a single run. The exact set can: it fails if a CLOSED run
    // is granted (alpha/run-0, delta/run-1), if the OWN run leaks in (alpha/run-1), or if an open
    // run is missed (gamma, whose run folder has no coordination dir — a goals-write grant does
    // not depend on one). Derived from the composed flags, compared against the fixture's own
    // declared open runs.
    const grantedRunDirs = [];
    for (let i = 0; i < granted.length; i++) {
      if (granted[i] === '--bind' && /[\\/]runs[\\/]run-\d+$/.test(granted[i + 1] || '')) grantedRunDirs.push(granted[i + 1]);
    }
    const expected = [f.betaRun, f.gammaRun].sort();
    leg('G6d', 'the granted RUN-FOLDER set is exactly the OPEN runs of other goals — no closed run, no own run',
      JSON.stringify([...new Set(grantedRunDirs)].sort()) === JSON.stringify(expected),
      `granted ${JSON.stringify([...new Set(grantedRunDirs)].sort())} vs expected ${JSON.stringify(expected)} `
      + `(alpha/run-0 closed, alpha/run-1 own, delta/run-1 closed all absent)`);
    leg('G6h', 'a seat declaring nothing gets no run folder at all',
      !plain.includes(f.betaRun) && !plain.includes(f.gammaRun) && !plain.includes(f.deltaRun) && !plain.includes(f.alphaClosedRun),
      `plain seat run-folder openings: ${JSON.stringify(plain.filter((a) => /[\\/]runs[\\/]run-\d+$/.test(a)))}`);

    // The materializer's two writes, proven ON DISK from outside the cage — and the carve proven
    // the same way, by the bytes of the file the grant must NOT have opened.
    inCage(f.mineDir, granted, `mkdir -p ${f.betaSeats}/seated && echo "seat: seated" > ${f.betaSeats}/seated/seat.md`);
    leg('G6e', "a seat descriptor can be materialized into another goal's open run",
      bytes(path.join(f.betaSeats, 'seated', 'seat.md')).includes('seat: seated'),
      `seated seat.md: ${JSON.stringify(bytes(path.join(f.betaSeats, 'seated', 'seat.md')).trim())}`);
    // The atomic append shape materialize-seats.py actually uses: tmp file in the SAME dir + rename.
    inCage(f.mineDir, granted,
      `cp ${f.betaTaskforce} ${f.betaRun}/.tf.tmp && echo "tf-1,seated" >> ${f.betaRun}/.tf.tmp && mv ${f.betaRun}/.tf.tmp ${f.betaTaskforce}`);
    leg('G6f', 'taskforce.csv appends via tmp-file-plus-rename IN the run dir (why the grant is the run dir)',
      bytes(f.betaTaskforce).includes('tf-1,seated'), `taskforce.csv now: ${JSON.stringify(bytes(f.betaTaskforce).trim())}`);
    const betaBefore = bytes(f.betaSessions);
    const spoof = inCage(f.mineDir, granted, `echo "imposter,999,999,999" >> ${f.betaSessions}`);
    leg('G6g', "the GRANTED run's sessions.csv is still unwritable — no cross-goal identity spoofing",
      bytes(f.betaSessions) === betaBefore,
      `on-disk bytes ${bytes(f.betaSessions) === betaBefore ? 'UNCHANGED' : 'CHANGED — WALL BREACHED'} (in-cage exit ${spoof.exit}, not the evidence)`);

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
