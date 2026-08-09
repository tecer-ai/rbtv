'use strict';

// Owner ruling "1a" (2026-08-06) — the CROSS-GOAL INSTRUMENT grant classes:
//
// ⚠ 7.607 E1 RE-FOUNDING. `bus-write` / `goals-write` are no longer scoped by `runs.csv`'s
// `state` column but by the DERIVED LEASE (`server/lease/lease.js`, design lock item 4, SECURITY):
// a goal contributes a grant only while its ROOM EXISTS and at least one seat of that room has a
// live, ancestry-verified process. So the fixture below builds REAL tmux rooms with REAL verified
// seats — "open" is no longer something a fixture can assert into a CSV, and that is the point:
// with seat folders becoming goal-durable, a register-shaped predicate would have widened the bus
// to every historical seat a goal ever had. Legs G8a/G8b are that widening, refused.
//
//   bus-write: true    RW the coordination dir of every goal holding a LIVE LEASE
//   local-bin: true    ro-bind the invoking user's ~/.local/bin
//   gateway-env: true  IGNITE_GATEWAY_ADDR in the session's environment (a --setenv, not a mount)
//   tmux-socket: true  ro-bind tmux's socket dir back through bwrap's `--tmpfs /tmp`, so the
//                      coordination CLI's WAKE leg can reach a pane (owner-directed 2026-08-07)
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

// ⚠ ISOLATED TMUX SERVER, INSTALLED BEFORE ANY SOCKET PATH IS COMPUTED. The lease is derived
// from real rooms, so this probe must create some — and it may never create them on the box's
// DEFAULT server, where the owner's live acceptance room sits. `TMUX_TMPDIR` is redirected here,
// above `TMUX_SOCK_DIR` below and above every grant resolution, so the probe, the grant resolver
// and the lease module all agree on one throwaway server. Killed in the finally block.
const TMUX_SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'grantcls-tmux-'));
const SAVED_TMUX_ENV = { TMUX_TMPDIR: process.env.TMUX_TMPDIR, TMUX: process.env.TMUX, TMUX_PANE: process.env.TMUX_PANE };
process.env.TMUX_TMPDIR = TMUX_SCRATCH;
delete process.env.TMUX;
delete process.env.TMUX_PANE;

const GATEWAY_ADDR = '127.0.0.1:7431';
const LOCAL_BIN = path.join(os.homedir(), '.local', 'bin');
// tmux's OWN default socket dir, derived exactly as resolveTmuxSocketGrant derives it — the same
// second-spelling the LOCAL_BIN line above accepts, and for the same reason: a probe that imported
// the resolver's answer could not tell a right answer from a resolver agreeing with itself.
const TMUX_SOCK_DIR = path.join(process.env.TMUX_TMPDIR || '/tmp', `tmux-${process.getuid()}`);

// The SHIPPED cage template.
function shippedSeatBinds() {
  const cfg = yaml.load(fs.readFileSync(path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml'), 'utf8'));
  return cfg.cage.SeatBinds;
}

// The room + verified-seat pair that makes a goal EXECUTING. A room whose pane pid is written
// into the package's sessions.csv with that process's REAL starttime is the only shape the lease's
// three conjuncts accept — which is why a fixture can no longer assert liveness into a file.
function makeRoom(pkgDir, room) {
  execFileSync('tmux', ['new-session', '-d', '-s', room], { stdio: 'ignore', timeout: 15000 });
  const pid = execFileSync('tmux', ['list-panes', '-t', room, '-F', '#{pane_pid}'],
    { encoding: 'utf8', timeout: 15000 }).trim().split('\n')[0];
  const raw = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
  const starttime = raw.slice(raw.lastIndexOf(')') + 2).trim().split(/\s+/)[22 - 3];
  fs.mkdirSync(pkgDir, { recursive: true });
  fs.writeFileSync(path.join(pkgDir, 'sessions.csv'),
    `seat,session-id,pid,pid-starttime\noccupant,s1,${pid},${starttime}\n`);
  return { pid, starttime };
}

// A workspace with FIVE goals, so every branch of the LEASE scan is exercised by data rather than
// by argument: one goal EXECUTING with a coordination dir (granted, and it is the seat's OWN), a
// second executing goal (granted — the cross-goal opening the ruling is about), an executing goal
// with no coordination dir at all (skipped, never created), and the TWO SECURITY CASES the
// re-founding exists for: `historical`, whose seat folders are all still on disk but which has NO
// ROOM; and `ghost`, which HAS a room but whose only registered occupant is a dead pid.
//
// ── 7.607 E2a — GOAL-DIRECT, AND THE ROOM NAME IS NOW THE GOAL'S ───────────────────────────────
//
// Two fixture changes, both forced and neither cosmetic:
//   · No `runs.csv` is written ANYWHERE. It was already a decoy here — E1 proved the predicate
//     ignores it — and the file no longer exists in the layout, so writing one would test a shape
//     that cannot occur. The states it used to encode are encoded by ROOMS now, which is the
//     point of the ruling.
//   · Rooms are named for the GOAL (`alpha`), not `<goal>-run-N`. The lease's E1 transitional
//     predicate still ACCEPTS the legacy spelling, but `packageDirForRoom` resolves that spelling
//     to `<goal>/runs/run-N` — a path that no longer exists — so a legacy-named room would
//     contribute nothing and every grant leg would pass for the wrong reason. E2b deletes that
//     arm; this fixture is already on the far side of it.
//   · `alpha`'s CLOSED EARLIER RUN is gone with the compartment. Its assertion (a non-executing
//     compartment of a goal is not granted) has no subject at goal level and is not simulated —
//     what replaces it is `historical`, a whole goal with everything on disk and no room, which
//     is the same claim at the granularity the layout actually has.
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'grant-classes-'));
  const ws = path.join(root, 'ws');
  const goals = path.join(ws, '.rbtv', 'goals');

  const mk = (goal, dirs) => {
    const goalDir = path.join(goals, goal);
    fs.mkdirSync(goalDir, { recursive: true });
    for (const d of dirs) fs.mkdirSync(path.join(goalDir, d), { recursive: true });
    return goalDir;
  };

  const alpha = mk('alpha', ['coordination', 'seats/mine', 'seats/plain']);
  const beta = mk('beta', ['coordination']);
  const gamma = mk('gamma', []);
  // ⚠ THE SECURITY FIXTURES. `historical` is the state the ruling names: every seat folder the
  // goal ever had still on disk (they are goal-durable now) and NO ROOM. `ghost` has a room but
  // nobody in it — its only registered occupant is a pid past the kernel's maximum, so it cannot
  // be alive.
  const historical = mk('historical', ['coordination', 'seats/ghost-a', 'seats/ghost-b']);
  const ghost = mk('ghost', ['coordination']);
  const deadPid = Number(fs.readFileSync('/proc/sys/kernel/pid_max', 'utf8').trim()) + 1;
  fs.writeFileSync(path.join(historical, 'sessions.csv'),
    `seat,session-id,pid,pid-starttime\nghost-a,s1,${deadPid},1\n`);
  fs.writeFileSync(path.join(ghost, 'sessions.csv'),
    `seat,session-id,pid,pid-starttime\nnobody,s1,${deadPid},1\n`);

  const runDir = alpha;   // the goal folder IS the package
  // The three EXECUTING goals get real rooms and real verified occupants; `historical` gets none.
  // `ghost` gets a room and no live occupant.
  const rooms = ['alpha', 'beta', 'gamma'];
  makeRoom(runDir, 'alpha');
  makeRoom(beta, 'beta');
  makeRoom(gamma, 'gamma');
  execFileSync('tmux', ['new-session', '-d', '-s', 'ghost'], { stdio: 'ignore', timeout: 15000 });
  rooms.push('ghost');

  // The DECLARING seat — the channel-master's shape (read-root plus the three new keys).
  fs.writeFileSync(path.join(runDir, 'seats', 'mine', 'seat.md'),
    '---\nseat: mine\nread-root: true\nbus-write: true\ngoals-write: true\nlocal-bin: true\ngateway-env: true\ntmux-socket: true\n---\nbriefing\n');
  // The seat that declares NOTHING — the fail-closed control.
  fs.writeFileSync(path.join(runDir, 'seats', 'plain', 'seat.md'), '---\nseat: plain\n---\nbriefing\n');

  fs.writeFileSync(path.join(beta, 'coordination', 'messages.md'), 'peer goal bus\n');
  // The goals-write target: a peer goal that is EXECUTING, with the two surfaces the materializer
  // writes (a seats/ dir, a taskforce.csv) AND the ground truth the grant must carve back read-only.
  fs.mkdirSync(path.join(beta, 'seats'), { recursive: true });
  fs.writeFileSync(path.join(beta, 'taskforce.csv'), 'taskforce-id,seat\n');

  return {
    root, ws, runDir, rooms,
    historicalRun: historical,
    historicalCoord: path.join(historical, 'coordination'),
    ghostRun: ghost,
    ghostCoord: path.join(ghost, 'coordination'),
    betaRun: beta,
    betaSessions: path.join(beta, 'sessions.csv'),
    betaTaskforce: path.join(beta, 'taskforce.csv'),
    betaSeats: path.join(beta, 'seats'),
    mineDir: path.join(runDir, 'seats', 'mine'),
    plainDir: path.join(runDir, 'seats', 'plain'),
    sessionsCsv: path.join(runDir, 'sessions.csv'),
    ownCoord: path.join(runDir, 'coordination'),
    betaCoord: path.join(beta, 'coordination'),
    gammaRun: gamma,
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
    // 7.607 E2a — G1c's subject was `alpha`'s CLOSED EARLIER RUN, and a goal has no compartments
    // left to close. The claim it made — a non-executing part of the tree is not bound — survives
    // at goal granularity as G8a below (`historical`: every seat folder on disk, no room, nothing
    // bound), which is the same assertion against a state that can actually occur. Not silently
    // dropped; re-homed, and named here so the census stays honest.
    // Class-specific by construction: the claim is that BUS-WRITE contributes nothing for a run
    // with no coordination dir, so it is asserted on that dir — not on "no flag mentions this
    // run", which another grant class over the same run folder (goals-write) legitimately does.
    leg('G1d', 'an EXECUTING goal with NO coordination dir contributes no bus opening (never created)',
      !granted.includes(path.join(f.gammaRun, 'coordination')) && !fs.existsSync(path.join(f.gammaRun, 'coordination')),
      `gamma coordination in flags: ${granted.includes(path.join(f.gammaRun, 'coordination'))}; dir created on disk: ${fs.existsSync(path.join(f.gammaRun, 'coordination'))}`);
    leg('G1e', 'a goal with no room contributes nothing',
      !granted.includes(f.historicalCoord), `historical (no room) coordination present: ${granted.includes(f.historicalCoord)}`);

    // ── ⚠⚠ G8 — THE SECURITY ARMS OF THE 7.607 E1 RE-FOUNDING (design lock item 4).
    //
    // These are the two states a register-shaped predicate carried into the extinguished layout
    // would have GRANTED, and the ruling forbids both by name: "historical seat folders on disk
    // grant nothing", and access holds only "while [a seat] has a live, ancestry-verified process".
    // Each is asserted on BOTH grant classes, because a widening in either is the same breach.
    leg('G8a', '⚠⚠ a goal with EVERY seat folder it ever had still on disk (they are GOAL-DURABLE '
      + 'now) but with NO ROOM grants NOTHING — not the bus, not the goal folder. This is the exact '
      + 'widening a register-shaped predicate carried into the extinguished layout would produce',
      !granted.includes(f.historicalCoord) && !granted.includes(f.historicalRun),
      `historical coordination in flags: ${granted.includes(f.historicalCoord)}; run folder: ${granted.includes(f.historicalRun)}`);
    leg('G8b', '⚠⚠ a goal that HAS a live room but whose only registered occupant is a DEAD pid '
      + 'grants NOTHING either — the room alone is a lease for the ticker gate but never for authz; '
      + 'an unoccupied room is a room nobody is in',
      !granted.includes(f.ghostCoord) && !granted.includes(f.ghostRun),
      `ghost coordination in flags: ${granted.includes(f.ghostCoord)}; run folder: ${granted.includes(f.ghostRun)}`);
    leg('G8c', 'and the CONTROL that makes G8a/G8b mean something: the two executing goals with '
      + 'live ancestry-verified occupants ARE granted, from the same walk, in the same call',
      granted.includes(f.betaCoord) && granted.includes(f.ownCoord),
      `beta bus: ${granted.includes(f.betaCoord)}; own bus: ${granted.includes(f.ownCoord)}`);

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
    leg('G6b', "the seat's OWN goal folder is NEVER granted — the peer-seat tmpfs and seat.md carve stay unshadowed",
      !hasFlag(granted, '--bind', f.runDir), `--bind own runDir: ${hasFlag(granted, '--bind', f.runDir)}`);
    leg('G6c', "each granted goal's sessions.csv is carved back READ-ONLY, after the rw opening",
      hasFlag(granted, '--ro-bind', f.betaSessions)
      && granted.lastIndexOf(f.betaSessions) > granted.lastIndexOf(f.betaRun),
      `--ro-bind ${f.betaSessions}: ${hasFlag(granted, '--ro-bind', f.betaSessions)}; carve after bind: ${granted.lastIndexOf(f.betaSessions) > granted.lastIndexOf(f.betaRun)}`);
    // THE SET, not a spot check. Asserting "beta is present" cannot tell an open-run resolver
    // from an every-run one — beta has a single run. The exact set can: it fails if a CLOSED run
    // is granted (alpha/run-0, delta/run-1), if the OWN run leaks in (alpha/run-1), or if an open
    // goal is missed (gamma, which has no coordination dir — a goals-write grant does not depend
    // on one).
    //
    // ⚠ THE SET IS ENUMERATED FROM THE FIXTURE'S OWN GOAL DIRS, NOT FROM A PATH PATTERN. The old
    // body matched `--bind` targets against a /runs\/run-N$/ regex; with the compartment gone that
    // pattern matches NOTHING, so the leg would have compared [] against [] and passed while
    // measuring nothing at all. Membership of each goal dir the fixture built is checked instead.
    const allGoalDirs = [f.runDir, f.betaRun, f.gammaRun, f.historicalRun, f.ghostRun];
    const grantedRunDirs = allGoalDirs.filter((d) => hasFlag(granted, '--bind', d));
    const expected = [f.betaRun, f.gammaRun].sort();
    leg('G6d', 'the granted GOAL-FOLDER set is exactly the EXECUTING, OCCUPIED other goals — not the own goal, not a roomless one, not an unoccupied room',
      JSON.stringify([...new Set(grantedRunDirs)].sort()) === JSON.stringify(expected),
      `granted ${JSON.stringify([...new Set(grantedRunDirs)].sort())} vs expected ${JSON.stringify(expected)} `
      + `(alpha own, historical roomless, ghost unoccupied — all absent)`);
    leg('G6h', 'a seat declaring nothing gets no goal folder at all',
      allGoalDirs.every((d) => !hasFlag(plain, '--bind', d)),
      `plain seat goal-folder openings: ${JSON.stringify(allGoalDirs.filter((d) => hasFlag(plain, '--bind', d)))}`);

    // The materializer's two writes, proven ON DISK from outside the cage — and the carve proven
    // the same way, by the bytes of the file the grant must NOT have opened.
    inCage(f.mineDir, granted, `mkdir -p ${f.betaSeats}/seated && echo "seat: seated" > ${f.betaSeats}/seated/seat.md`);
    leg('G6e', "a seat descriptor can be materialized into another goal's executing folder",
      bytes(path.join(f.betaSeats, 'seated', 'seat.md')).includes('seat: seated'),
      `seated seat.md: ${JSON.stringify(bytes(path.join(f.betaSeats, 'seated', 'seat.md')).trim())}`);
    // The atomic append shape materialize-seats.py actually uses: tmp file in the SAME dir + rename.
    inCage(f.mineDir, granted,
      `cp ${f.betaTaskforce} ${f.betaRun}/.tf.tmp && echo "tf-1,seated" >> ${f.betaRun}/.tf.tmp && mv ${f.betaRun}/.tf.tmp ${f.betaTaskforce}`);
    leg('G6f', 'taskforce.csv appends via tmp-file-plus-rename IN the goal dir (why the grant is the goal dir)',
      bytes(f.betaTaskforce).includes('tf-1,seated'), `taskforce.csv now: ${JSON.stringify(bytes(f.betaTaskforce).trim())}`);
    const betaBefore = bytes(f.betaSessions);
    const spoof = inCage(f.mineDir, granted, `echo "imposter,999,999,999" >> ${f.betaSessions}`);
    leg('G6g', "the GRANTED goal's sessions.csv is still unwritable — no cross-goal identity spoofing",
      bytes(f.betaSessions) === betaBefore,
      `on-disk bytes ${bytes(f.betaSessions) === betaBefore ? 'UNCHANGED' : 'CHANGED — WALL BREACHED'} (in-cage exit ${spoof.exit}, not the evidence)`);

    const envRead = inCage(f.mineDir, granted, 'printf %s "$IGNITE_GATEWAY_ADDR"');
    leg('G5c', 'IGNITE_GATEWAY_ADDR arrives in the caged session',
      envRead.stdout === GATEWAY_ADDR, `in-cage value ${JSON.stringify(envRead.stdout)}`);

    // ── G7 — tmux-socket. The bind is only half the grant here too (G2c's lesson): bwrap lays a
    // `--tmpfs /tmp` over this path on EVERY spawn, so what has to be shown is that a tmux CLIENT
    // COMMAND reaches a live server through the opening — not that a path appears in the flags.
    //
    // The server is a PRIVATE one on its own `-L` socket, which lands in the very directory the
    // grant binds, so the leg exercises the real opening without ever addressing a live room
    // (G-163: a probe must not touch tracked state). It is killed in the finally block.
    const probeSocket = `grantprobe-${process.pid}`;
    let tmuxUp = false;
    try {
      execFileSync('tmux', ['-L', probeSocket, 'new-session', '-d', '-s', 'p', 'cat'], { stdio: 'ignore', timeout: 15000 });
      tmuxUp = true;
    } catch {}

    if (!tmuxUp) {
      leg('G7', 'tmux unavailable on this box — the grant cannot be exercised here', true,
        'no tmux server could be started; G7a-d skipped rather than passed for the wrong reason');
    } else {
      leg('G7a', "tmux's socket dir is bound READ-ONLY (never rw)",
        hasFlag(granted, '--ro-bind', TMUX_SOCK_DIR) && !hasFlag(granted, '--bind', TMUX_SOCK_DIR),
        `--ro-bind ${TMUX_SOCK_DIR}: ${hasFlag(granted, '--ro-bind', TMUX_SOCK_DIR)}; --bind: ${hasFlag(granted, '--bind', TMUX_SOCK_DIR)}`);

      // THE REACHABILITY LEG — the one that would have caught the live defect. A read-only mount
      // does not refuse connect(2) on a unix socket, which is the whole reason ro is sufficient;
      // if that ever stopped holding, this goes red while G7a stays green.
      const listed = inCage(f.mineDir, granted, `tmux -L ${probeSocket} list-sessions -F '#{session_name}' 2>&1 || echo UNREACHABLE`);
      leg('G7b', 'a caged seat REACHES a live tmux server through the ro opening (connect(2) is not refused by a ro mount)',
        listed.stdout === 'p', `in-cage list-sessions -> ${JSON.stringify(listed.stdout)}`);

      // The wake leg's own primitives, not a proxy for them: coord.py drives panes with exactly
      // send-keys/capture-pane, and it is those that died on the masked socket.
      const woke = inCage(f.mineDir, granted,
        `tmux -L ${probeSocket} send-keys -t p -l wake-probe && tmux -L ${probeSocket} capture-pane -p -t p | tr -d '\\n'`);
      leg('G7c', "the WAKE primitives work through it — send-keys types and capture-pane reads it back",
        woke.stdout.includes('wake-probe'), `in-cage capture after send-keys -> ${JSON.stringify(woke.stdout)}`);

      // …and the BOUND that read-only buys: the seat drives rooms that exist, it mints none.
      // Proven ON DISK from outside the cage (design §6, D51) — the socket file's absence, not
      // the in-cage exit status.
      const mintSocket = path.join(TMUX_SOCK_DIR, `grantprobe-mint-${process.pid}`);
      const mint = inCage(f.mineDir, granted, `tmux -L grantprobe-mint-${process.pid} new-session -d -s m true 2>&1 || echo REFUSED`);
      leg('G7d', 'read-only is a real bound: a caged seat cannot MINT a tmux server in that dir',
        !fs.existsSync(mintSocket),
        `socket on disk after the attempt: ${fs.existsSync(mintSocket) ? 'CREATED — WALL BREACHED' : 'ABSENT'} (in-cage output ${JSON.stringify(mint.stdout)}, not the evidence)`);
    }

    // ── G7e — the fail-closed control for this class, on the seat that declares nothing.
    leg('G7e', 'a seat declaring no tmux-socket key gets no tmux opening at all',
      !plain.includes(TMUX_SOCK_DIR), `plain seat mentions ${TMUX_SOCK_DIR}: ${plain.includes(TMUX_SOCK_DIR)}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`grant-class probes failed: ${fails.join(', ')}`);
  } finally {
    try { execFileSync('tmux', ['-L', `grantprobe-${process.pid}`, 'kill-server'], { stdio: 'ignore', timeout: 15000 }); } catch {}
    // The throwaway server holding this probe's fixture rooms, and the scratch socket dir it lived
    // in. Reaped here so the box carries nothing away from this run.
    try { execFileSync('tmux', ['kill-server'], { stdio: 'ignore', timeout: 15000 }); } catch {}
    for (const [k, v] of Object.entries(SAVED_TMUX_ENV)) {
      if (v === undefined) delete process.env[k]; else process.env[k] = v;
    }
    try { fs.rmSync(TMUX_SCRATCH, { recursive: true, force: true }); } catch {}
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
