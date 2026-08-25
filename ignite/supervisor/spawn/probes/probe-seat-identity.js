'use strict';

// Task 7.11 — IDENTITY GATE PROBES. Pre-registered bars P1-P7 and P10.
//
// The bar this file exists to satisfy is G-IDGATE-FAILS: an identity gate that cannot produce
// P1's and P5's refusals is not a gate. So the probes here are mostly NEGATIVE — each one asserts
// that a specific wrong caller is REFUSED with a specific typed code, and P9's positive leg exists
// to stop the trivial cheat of refusing everything.
//
// P10 is the one that would have caught tonight's G-101: every command-time verdict is taken BARE
// and again under exec-away wrappers (`timeout`, `env -i`). A gate whose answer changes with the
// caller's shell line has handed its verdict to the caller, and two honest verifiers re-deriving
// it independently will reinforce each other's wrong answer — only varying the invocation shows it.

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync, spawn: childSpawn } = require('node:child_process');
const { capture } = require('./lib');
const { checkIdentity, readProcStat } = require('../../../runtime/seat-identity/identity');
const { parseSeatPath, checkGoalExecuting, checkMaterializedSeat } = require('../../../runtime/seat-identity/seat-folder');
const { deriveLease } = require('../../../runtime/lease/lease');

const CLI = path.join(__dirname, '..', '..', '..', 'runtime', 'seat-identity', 'rbtv-seat-identity');

// ── 7.607 E2a — THE GOAL MUST BE EXECUTING, AND THE EVIDENCE IS A REAL tmux ROOM ───────────────
//
// L2 is no longer a `runs.csv` read; it is `runtime/lease/lease.js` — the goal's tmux room existing
// right now. The in-process legs below inject `deriveLease` over a fixture tmux OUTPUT (real lease
// code, fake binary), but the P10 legs run the SHIPPED CLI as a child process, and that child
// resolves its own lease off the real binary. So this probe stands up a REAL room named for the
// fixture goal on an ISOLATED `TMUX_TMPDIR` socket and reaps it in `finally`.
//
// ⚠ ISOLATED SOCKET, NEVER THE DEFAULT SERVER. The box's default tmux server carries the owner's
// attached session; a probe may neither read it as evidence nor add a session to it. The socket
// dir is kept SHORT deliberately — a long `TMUX_TMPDIR` overruns `sun_path` and tmux prints
// `error connecting … (File name too long)`, which lease.js classifies as UNREADABLE (correctly),
// and this probe would then measure the fixture's path length instead of the gate.
const ROOM_TMPDIR = path.join(os.tmpdir(), `e2a-id-${process.pid}`);
function tmuxFixture(args) {
  return execFileSync('tmux', args, {
    // TMUX/TMUX_PANE unset (undefined keys are dropped from a child env): $TMUX overrides
    // TMUX_TMPDIR, so run from inside a pane the fixture — and its kill-server — would hit
    // the DEFAULT server instead of this scratch socket.
    encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, TMUX_TMPDIR: ROOM_TMPDIR, TMUX: undefined, TMUX_PANE: undefined },
  });
}
// The lease as the daemon computes it, off a fixture tmux — real predicate, fake binary.
const roomLive = (args) => deriveLease({ ...args, tmuxProbe: () => ({ sessions: 'testgoal\n', panes: '' }) });

// A fixture with the identity columns the LIVE schema does not yet carry (measured 2026-07-27;
// task 7.37 owns the settled schema). The fixture carries them so the MATCH logic is exercised —
// and probe P-schema below separately proves the gate fails closed when they are absent, which is
// the state of every real run today.
function fixture({ header = 'seat,session-id,pid,pid-starttime,tty,started,ended', rows = [] } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'g4-ident-'));
  const ws = path.join(root, 'ws');
  const goalsDir = path.join(ws, '.rbtv', 'goals');
  const goalDir = path.join(goalsDir, 'testgoal');
  const runDir = goalDir;   // 7.607 E2a — goal-direct: the goal folder IS the package
  const seatDir = path.join(runDir, 'seats', 'mine');
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(goalsDir, 'goals.csv'), 'name,created,due,type,status\ntestgoal,2026-07-27,,one-shot,active\n');
  fs.writeFileSync(path.join(runDir, 'taskforce.csv'), 'taskforce-id,seat\ntf-1,mine\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: mine\n---\n');
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), [header, ...rows].join('\n') + '\n');
  return { root, ws, goalDir, runDir, seatDir, sessionsCsv: path.join(runDir, 'sessions.csv') };
}

function selfPair() {
  const st = readProcStat(process.pid);
  return { pid: process.pid, starttime: st.starttime };
}

capture('probe-seat-identity', async (lines) => {
  const fails = [];
  const cleanup = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  // The real room the child-process CLI legs need. Started BEFORE any leg so a failure to create
  // it takes the probe down loudly rather than turning every CLI leg into a silent E_GOAL_NOT_LIVE.
  fs.mkdirSync(ROOM_TMPDIR, { recursive: true, mode: 0o700 });
  tmuxFixture(['new-session', '-d', '-s', 'testgoal', 'sleep', '600']);

  try {
    // ── P4 — a system CLI from a non-seat cwd has NO identity and is refused.
    const r4 = checkIdentity({ cwd: os.tmpdir(), readLease: roomLive });
    leg('P4', 'CLI from a non-seat cwd is refused, never treated as anonymous-but-allowed',
      r4.ok === false && r4.code === 'E_IDENTITY_NO_SEAT', `code=${r4.code}`);

    // ── P6 — a real seat folder with NO session row. Absence must never fall through to allow.
    const f6 = fixture({ rows: [] }); cleanup.push(f6.root);
    const r6 = checkIdentity({ cwd: f6.seatDir, readLease: roomLive });
    leg('P6', 'seat folder with no session row is refused (absence fails CLOSED)',
      r6.ok === false && r6.code === 'E_IDENTITY_NO_SESSION', `code=${r6.code}`);

    // ── P5 — THE CORE PROBE. A real seat folder whose last row records a DIFFERENT live process.
    // The other process is genuinely alive, so this is not "the row was missing" passing by
    // accident — the bar names that cheat explicitly and this leg is built to exclude it.
    const other = childSpawn('sleep', ['30'], { stdio: 'ignore' });
    cleanup.push(() => { try { other.kill(); } catch {} });
    await new Promise((r) => setTimeout(r, 120));
    const otherSt = readProcStat(other.pid);
    const f5 = fixture({ rows: [`mine,sess-1,${other.pid},${otherSt.starttime},,2026-07-27 17:00,`] });
    cleanup.push(f5.root);
    const r5 = checkIdentity({ cwd: f5.seatDir, readLease: roomLive });
    const otherStillLive = Boolean(readProcStat(other.pid));
    leg('P5', 'CORE: right folder, wrong process -> E_IDENTITY_MISMATCH naming the occupant',
      r5.ok === false && r5.code === 'E_IDENTITY_MISMATCH' && r5.registeredPid === other.pid && otherStillLive,
      `code=${r5.code} registered=${r5.registeredPid} (a LIVE process, so the row was present — not the missing-row cheat)`);

    // ── P9-gate — the LEGITIMATE caller passes. Without this the gate could refuse everything.
    const self = selfPair();
    const f9 = fixture({ rows: [`mine,sess-1,${self.pid},${self.starttime},,2026-07-27 17:00,`] });
    cleanup.push(f9.root);
    const r9 = checkIdentity({ cwd: f9.seatDir, readLease: roomLive });
    leg('P9-gate', 'the registered occupant IS confirmed (the gate is not merely refusing everything)',
      r9.ok === true && r9.seat === 'mine', `ok=${r9.ok} seat=${r9.seat} matched-ancestor=${r9.matchedAncestor && r9.matchedAncestor.pid}`);

    // ── P7 — an asserted identity must change NOTHING. This is G-111 wired as a test.
    const saved = { COORD_AGENT: process.env.COORD_AGENT, RBTV_SEAT: process.env.RBTV_SEAT };
    process.env.COORD_AGENT = 'someone-else';
    process.env.RBTV_SEAT = 'someone-else';
    const r7pass = checkIdentity({ cwd: f9.seatDir, readLease: roomLive });
    const r7fail = checkIdentity({ cwd: f5.seatDir, readLease: roomLive });
    process.env.COORD_AGENT = saved.COORD_AGENT; process.env.RBTV_SEAT = saved.RBTV_SEAT;
    leg('P7', 'COORD_AGENT/RBTV_SEAT asserting another seat changes no verdict, in EITHER direction',
      r7pass.ok === true && r7pass.seat === 'mine' && r7fail.ok === false && r7fail.code === 'E_IDENTITY_MISMATCH',
      `with the assertion set: confirmed seat is still "${r7pass.seat}"; the mismatch is still ${r7fail.code}`);

    // ── P-schema — the state of EVERY live run today: a log without the identity columns.
    // It must be a typed refusal, never a degrade to "the folder alone".
    const fS = fixture({ header: 'seat,session-id,harness,workdir,started,ended', rows: ['mine,sess-1,claude,/x,2026-07-27 17:00,'] });
    cleanup.push(fS.root);
    const rS = checkIdentity({ cwd: fS.seatDir, readLease: roomLive });
    leg('P-schema', 'a session log lacking pid/pid-starttime is a typed refusal, not a degraded pass',
      rS.ok === false && rS.code === 'E_IDENTITY_SCHEMA', `code=${rS.code} missing=${(rS.missing || []).join('/')}`);

    // ── P-reuse — a recorded pid that has been REUSED by a different process. The starttime is
    // what defeats this; without it a stale row would confirm a stranger.
    const fR = fixture({ rows: [`mine,sess-1,${self.pid},999999999,,2026-07-27 17:00,`] });
    cleanup.push(fR.root);
    const rR = checkIdentity({ cwd: fR.seatDir, readLease: roomLive });
    leg('P-reuse', 'same pid + different starttime is a MISMATCH (pid reuse cannot confirm)',
      rR.ok === false && rR.code === 'E_IDENTITY_MISMATCH' && rR.pidReused === true,
      `code=${rR.code} pidReused=${rR.pidReused}`);

    // ── L2/L3 unit legs — P2 and P3's checks, exercised directly on fixtures.
    //
    // 7.607 E2a: P2 was "a seat of a CLOSED run is refused, run state read by NAME from runs.csv".
    // The register is gone, so the SUBJECT is now the lease: the same seat folder, the same
    // refusal, live evidence instead of a stored status. Both directions in one pair — the green
    // arm FIRST, so a `checkGoalExecuting` that refused unconditionally cannot pass this leg.
    const parsedSeat = parseSeatPath(f9.seatDir);
    const liveYes = checkGoalExecuting(parsedSeat, { readLease: roomLive });
    const noRoom = (a) => deriveLease({ ...a, tmuxProbe: () => ({ sessions: '', panes: '' }) });
    const liveNo = checkGoalExecuting(parsedSeat, { readLease: noRoom });
    leg('P2', 'a seat whose goal is NOT executing is refused; the SAME seat is admitted while it is',
      liveYes.ok === true && liveNo.ok === false && /not executing/.test(liveNo.reason || ''),
      `executing: ok=${liveYes.ok}; not executing: ${liveNo.reason}`);

    const imposter = path.join(f9.runDir, 'seats', 'imposter');
    fs.mkdirSync(imposter, { recursive: true });
    const m3 = checkMaterializedSeat(parseSeatPath(imposter));
    leg('P3', 'a hand-made seats/imposter/ (right shape, no seat.md, not rostered) is refused',
      m3.ok === false && /no seat\.md/.test(m3.reason), `reason: ${m3.reason}`);

    const liar = path.join(f9.runDir, 'seats', 'liar');
    fs.mkdirSync(liar, { recursive: true });
    fs.writeFileSync(path.join(liar, 'seat.md'), '---\nseat: mine\n---\n');
    const m3b = checkMaterializedSeat(parseSeatPath(liar));
    leg('P3-ii', 'a seat.md claiming ANOTHER seat\'s name is refused (descriptor never overrides the folder)',
      m3b.ok === false && /disagree/.test(m3b.reason), `reason: ${m3b.reason}`);

    // ── P10 — THE CALLER-INDEPENDENCE BAR. Same question, five invocation shapes.
    // `2>&1` on every shape: the CLI writes its refusal to STDERR, and a probe that captured only
    // stdout would score every shape as `<none>` and call them consistent — agreement produced by
    // measuring nothing. That is the first thing this leg got wrong when it was written.
    //
    // EVERY SHAPE ALSO CARRIES A RAN-MARKER. The second thing it got wrong was an `echo | xargs
    // -I{}` shape: the empty input line meant xargs never executed the CLI, and the leg scored
    // that silence as a passing verdict. A shape that does not run the tool must FAIL the probe,
    // not agree with it — so each shape must print its marker or the leg is void.
    // ⚠ `TMUX_TMPDIR` RIDES EVERY SHAPE, `env -i` INCLUDED, AND THAT DOES NOT WEAKEN THE BAR.
    // The bar is that no environment ASSERTION changes the verdict — `COORD_AGENT`, `RBTV_SEAT`,
    // a claimed name (P7 varies exactly those and this leg keeps every wrapper). `TMUX_TMPDIR` is
    // not an assertion: it is the ADDRESS of the evidence store, and the fixture room lives on an
    // isolated socket precisely because the probe may not touch the box's default tmux server.
    // Dropping it from `env -i` would not test caller-independence, it would point that one shape
    // at a different machine-wide server — a fixture defect wearing a bar's clothes.
    // ⚠ AND `$TMUX` IS CLEARED ON EVERY SHAPE FOR THE SAME REASON, NOT A DIFFERENT ONE.
    // `$TMUX` is an ADDRESS too, and `runtime/lease/lease.js` (§ `$TMUX` IS CONSULTED FIRST
    // BECAUSE IT WINS) reads it BEFORE `TMUX_TMPDIR` and lets it select the socket outright.
    // So a suite run launched from inside a pane leaked `$TMUX` into five of the six shapes --
    // `env -i` being the one that dropped it -- and those five addressed the OPERATOR's server
    // instead of the fixture room: bare/timeout/nested-sh/exec-away/nohup all answered
    // `E_GOAL_NOT_LIVE` while `env -i` answered `E_IDENTITY_MISMATCH`, i.e. P10 and P10-ii went
    // RED for a socket-ADDRESS reason with nothing to do with caller-independence (task 7.627,
    // measured on the ignite VPS). The runner has stripped `$TMUX` from every probe child since
    // a3f8f90f, which is what turned these legs green again -- but a probe that only holds
    // because its RUNNER isolates it is not isolated, it is lucky. Clearing it here keeps the
    // shapes pointed at the fixture room under a leaking caller too, and the bar is untouched:
    // an address is not an assertion, exactly as the paragraph above rules for `TMUX_TMPDIR`.
    const SOCK = `TMUX_TMPDIR=${ROOM_TMPDIR} TMUX= TMUX_PANE=`;
    const shapes = [
      ['bare',      `cd ${f5.seatDir} && ${SOCK} ${CLI} 2>&1; echo "RAN exit=$?"`],
      ['timeout',   `cd ${f5.seatDir} && ${SOCK} timeout 30 ${CLI} 2>&1; echo "RAN exit=$?"`],
      ['env -i',    `cd ${f5.seatDir} && env -i ${SOCK} ${CLI} 2>&1; echo "RAN exit=$?"`],
      ['nested sh', `cd ${f5.seatDir} && ${SOCK} sh -c '${CLI} 2>&1'; echo "RAN exit=$?"`],
      ['exec-away', `cd ${f5.seatDir} && ( export ${SOCK}; exec ${CLI} ) 2>&1; echo "RAN exit=$?"`],
      ['nohup',     `cd ${f5.seatDir} && ${SOCK} nohup ${CLI} 2>&1; echo "RAN exit=$?"`],
    ];
    const verdicts = [];
    for (const [label, script] of shapes) {
      let out;
      try { out = execFileSync('bash', ['-c', script], { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'pipe'] }); }
      catch (err) { out = ((err.stdout || '') + (err.stderr || '')).toString(); }
      const ran = /RAN exit=/.test(out);
      const code = (/E_[A-Z_]+/.exec(out) || ['<none>'])[0];
      const exit = (/RAN exit=(\d+)/.exec(out) || [null, '?'])[1];
      verdicts.push({ label, code, exit, ran });
    }
    const allRan = verdicts.every((v) => v.ran && v.code !== '<none>');
    const codes = new Set(verdicts.map((v) => v.code));
    const exits = new Set(verdicts.map((v) => v.exit));
    leg('P10', 'the command-time verdict is IDENTICAL bare and under every exec-away wrapper',
      allRan && codes.size === 1 && exits.size === 1 && codes.has('E_IDENTITY_MISMATCH'),
      verdicts.map((v) => `${v.label}:${v.code}/exit${v.exit}${v.ran ? '' : '/DID-NOT-RUN'}`).join('  '));

    // And the positive verdict must be caller-independent too — a gate that only agrees when it
    // is refusing has been tested in one direction.
    const posShapes = [
      ['bare',    `cd ${f6.seatDir} && ${SOCK} ${CLI} 2>&1`],
      ['timeout', `cd ${f6.seatDir} && ${SOCK} timeout 30 ${CLI} 2>&1`],
      ['env -i',  `cd ${f6.seatDir} && env -i ${SOCK} ${CLI} 2>&1`],
    ];
    const posV = posShapes.map(([label, script]) => {
      let out;
      try { out = execFileSync('bash', ['-c', script], { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'pipe'] }); }
      catch (err) { out = ((err.stdout || '') + (err.stderr || '')).toString(); }
      return `${label}:${(/E_[A-Z_]+/.exec(out) || ['<none>'])[0]}`;
    });
    const posCodes = new Set(posV.map((s) => s.split(':')[1]));
    leg('P10-ii', 'a DIFFERENT verdict (NO_SESSION) is caller-independent too — not just the mismatch',
      posCodes.size === 1 && posCodes.has('E_IDENTITY_NO_SESSION'), posV.join('  '));

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`identity probes failed: ${fails.join(', ')}`);
  } finally {
    try { tmuxFixture(['kill-server']); } catch { /* already gone */ }
    try { fs.rmSync(ROOM_TMPDIR, { recursive: true, force: true }); } catch {}
    for (const c of cleanup) {
      if (typeof c === 'function') c();
      else { try { fs.rmSync(c, { recursive: true, force: true }); } catch {} }
    }
  }
});
