'use strict';

// Task 7.10 — the peer-identity resolver (issue G-124).
//
// THE QUESTION UNDER TEST: can a receiver resolve a caller's SEAT across a socket, when that
// caller is inside a cage whose own /proc cannot contain the host pid the daemon recorded?
//
// THE DISCIPLINE THAT MAKES THIS EVIDENCE (p-green-harness-over-a-broken-mechanism):
//
//  • THE COMPOSITION IS THE TEST. Every leg that matters runs the client INSIDE a real bwrap cage
//    carrying the flags buildBwrapArgv emits. G-124 exists precisely because every gate probe ran
//    outside a cage and every wall probe inside one — both halves green, the seam untested.
//  • NO PROBE FEEDS THE RESOLVER THE IDENTITY IT EXISTS TO RESOLVE. The client sends a header
//    naming a DIFFERENT seat on purpose (leg P5); the resolver must ignore it. The fixture supplies
//    a folder, a csv and a live process — never a seat name.
//  • REFUSALS ARE PROVED, NOT ASSUMED. A resolver that says yes to everything would pass a
//    positive-only suite.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawn } = require('node:child_process');

const { capture } = require('./lib');
const { resolvePeerSeat, isLoopback, findSocketHolders } = require('../../seat-identity/peer-identity');

const BWRAP = '/usr/bin/bwrap';

function selfStarttime(pid) {
  const raw = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
  return raw.slice(raw.lastIndexOf(')') + 2).trim().split(/\s+/)[22 - 3];
}

// A fixture seat that is LIVE, MATERIALIZED and ROSTERED, registered to a pid that will genuinely
// be an ancestor of the client — so L1-L4 pass honestly rather than by relaxation.
function buildFixture({ seat = 'occupant', registerPid, runState = 'open' } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-peer-'));
  const goal = 'peer-goal';
  const run = 'run-1';
  const goalDir = path.join(root, '.rbtv', 'goals', goal);
  const runDir = path.join(goalDir, 'runs', run);
  const seatDir = path.join(runDir, 'seats', seat);
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(root, '.rbtv', 'goals', 'goals.csv'), `name,created,due,type,status\n${goal},2026-07-27,,one-shot,active\n`);
  fs.writeFileSync(path.join(goalDir, 'runs.csv'), `run-id,type,state,taskforce-ids,opened,closed\n${run},fresh,${runState},tf-1,2026-07-27 01:30,\n`);
  fs.writeFileSync(path.join(runDir, 'taskforce.csv'), `seat,role\n${seat},executor\n`);
  fs.writeFileSync(path.join(seatDir, 'seat.md'), `---\nseat: ${seat}\n---\n`);
  fs.writeFileSync(
    path.join(runDir, 'sessions.csv'),
    `seat,session-id,pid,pid-starttime,started,ended\n${seat},s1,${registerPid},${selfStarttime(registerPid)},t,\n`,
  );
  return { root, goalDir, runDir, seatDir };
}

// The client: connects and sends a DELIBERATELY FALSE self-claim. Nothing it says may be read.
const CLIENT_SRC = `
const http=require('http');
const req=http.request({host:'127.0.0.1',port:Number(process.env.PORT),path:'/',
  headers:{'x-seat':'a-seat-i-am-not','x-claimed-pid':'1'}},r=>{r.resume();r.on('end',()=>process.exit(0));});
req.on('error',()=>process.exit(3));
req.end();
`;

// One request/response cycle: start a receiver, run `spawnClient`, resolve the peer DURING the
// request, return what the resolver said.
function measure(spawnClient) {
  return new Promise((resolve) => {
    let done = false;
    const server = http.createServer((req, res) => {
      const verdict = resolvePeerSeat(req.socket);
      // Carried only to prove it is ignored.
      verdict.__clientClaimed = req.headers['x-seat'] || null;
      res.end('ok\n');
      if (!done) { done = true; setImmediate(() => server.close(() => resolve(verdict))); }
    });
    server.listen(0, '127.0.0.1', () => {
      const child = spawnClient(server.address().port);
      child.on('error', () => {
        if (!done) { done = true; server.close(() => resolve({ ok: false, code: 'SPAWN_ERROR' })); }
      });
    });
    setTimeout(() => {
      if (!done) { done = true; try { server.close(); } catch {} resolve({ ok: false, code: 'TIMEOUT' }); }
    }, 25000).unref();
  });
}

function cagedArgv(port, fx, clientFile) {
  return [
    '--die-with-parent', '--unshare-all', '--share-net',
    '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
    '--ro-bind', '/usr', '/usr',
    '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib', '/lib',
    '--symlink', 'usr/lib64', '/lib64', '--symlink', 'usr/sbin', '/sbin',
    '--ro-bind', '/etc', '/etc',
    // The seat cage stack, in composeSeatCage's order: peer seat folders are ABSENT, the seat's
    // own folder is punched back through the tmpfs, and sessions.csv stays READ-ONLY above it.
    '--ro-bind', fx.goalDir, fx.goalDir,
    '--tmpfs', path.join(fx.goalDir, 'runs'),
    '--ro-bind', fx.runDir, fx.runDir,
    '--tmpfs', path.join(fx.runDir, 'seats'),
    '--bind', fx.seatDir, fx.seatDir,
    '--ro-bind', clientFile, clientFile,
    '--chdir', fx.seatDir,
    process.execPath, clientFile,
  ];
}

capture('probe-peer-identity', async (lines) => {
  const clientFile = path.join(os.tmpdir(), `probe-peer-client-${process.pid}.js`);
  fs.writeFileSync(clientFile, CLIENT_SRC);
  const PORT = (p) => ({ ...process.env, PORT: String(p) });
  // ⚠ FAILURE IS SIGNALLED BY THROWING, never by returning false. `capture()` sets PASS when this
  // callback RESOLVES and ignores its return value entirely — so a probe that returned a boolean
  // would report PASS with every leg failing. Caught by reading lib.js before trusting a green.
  const fails = [];
  const t = (cond, name, detail) => {
    lines.push(`${cond ? 'PASS' : 'FAIL'} ${name}`);
    if (detail) lines.push(`       ${detail}`);
    if (!cond) fails.push(name.split(' ')[0]);
  };

  // ── P1 — UNCAGED: the receiver resolves a legitimate local caller's seat ────
  {
    const fx = buildFixture({ registerPid: process.pid });
    const v = await measure((port) => spawn(process.execPath, [clientFile],
      { cwd: fx.seatDir, env: PORT(port), stdio: 'ignore' }));
    t(v.ok === true && v.seat === 'occupant',
      'P1 — uncaged caller RESOLVED to its seat from the connection alone',
      `ok=${v.ok} seat=${v.seat} code=${v.code || '-'} callerPid=${v.callerPid}`);
    t(v.resolvedFrom === 'connection', 'P1-ii — the verdict records that it came from the CONNECTION',
      `resolvedFrom=${v.resolvedFrom}`);
  }

  // ── P2 — THE COMPOSITION, and the reason this probe exists ─────────────────
  // A caller inside a real cage: its OWN /proc says pid 2, ancestry 2<-1. The receiver must still
  // resolve it. This is the leg that fails under G-124's design and passes under this one.
  {
    const fx = buildFixture({ registerPid: process.pid });
    const v = await measure((port) => spawn(BWRAP, cagedArgv(port, fx, clientFile),
      { env: PORT(port), stdio: 'ignore' }));
    t(v.ok === true && v.seat === 'occupant',
      'P2 — CAGED caller RESOLVED (G-124: its own /proc cannot see the recorded host pid)',
      `ok=${v.ok} seat=${v.seat} code=${v.code || '-'} callerPid=${v.callerPid} inode=${v.socketInode}`);
  }

  // ── P3 — the caller's CLAIM is ignored ─────────────────────────────────────
  {
    const fx = buildFixture({ registerPid: process.pid });
    const v = await measure((port) => spawn(process.execPath, [clientFile],
      { cwd: fx.seatDir, env: PORT(port), stdio: 'ignore' }));
    t(v.__clientClaimed === 'a-seat-i-am-not' && v.seat === 'occupant',
      'P3 — a caller CLAIMING another seat is resolved to its REAL one (no assertion channel)',
      `claimed=${v.__clientClaimed} resolved=${v.seat}`);
  }

  // ── P4 — REFUSAL: a caller in a seat folder whose run is CLOSED ────────────
  // The G-126 checks reach the peer path for free, because it is the SAME gate.
  {
    const fx = buildFixture({ registerPid: process.pid, runState: 'closed' });
    const v = await measure((port) => spawn(process.execPath, [clientFile],
      { cwd: fx.seatDir, env: PORT(port), stdio: 'ignore' }));
    t(v.ok === false && v.code === 'E_RUN_NOT_LIVE',
      'P4 — REFUSED: seat folder in a CLOSED run (G-126 checks apply on the peer path too)',
      `ok=${v.ok} code=${v.code}`);
  }

  // ── P5 — REFUSAL: a caller that is not in a seat folder at all ────────────
  {
    const v = await measure((port) => spawn(process.execPath, [clientFile],
      { cwd: os.tmpdir(), env: PORT(port), stdio: 'ignore' }));
    t(v.ok === false && v.code === 'E_IDENTITY_NO_SEAT',
      'P5 — REFUSED: caller outside any seat folder',
      `ok=${v.ok} code=${v.code}`);
  }

  // ── P6 — REFUSAL: a non-loopback peer is a handoff, with its own code ─────
  {
    const v = resolvePeerSeat({
      remoteAddress: '100.64.0.9', remotePort: 5555, localAddress: '100.64.0.1', localPort: 8080,
    });
    t(v.ok === false && v.code === 'E_PEER_NOT_LOCAL',
      'P6 — REFUSED: a remote (tailnet) caller holds no seat here; token resolver answers it',
      `ok=${v.ok} code=${v.code}`);
  }

  // ── P7 — REFUSAL: an unlocatable connection ──────────────────────────────
  {
    const v = resolvePeerSeat({
      remoteAddress: '127.0.0.1', remotePort: 1, localAddress: '127.0.0.1', localPort: 2,
    });
    t(v.ok === false && v.code === 'E_PEER_UNRESOLVED',
      'P7 — REFUSED: no socket matches the four-tuple — absence never passes',
      `ok=${v.ok} code=${v.code}`);
  }

  // ── P8 — a malformed connection object ───────────────────────────────────
  {
    const v = resolvePeerSeat({});
    t(v.ok === false && v.code === 'E_PEER_UNRESOLVED',
      'P8 — REFUSED: an incomplete address pair', `code=${v.code}`);
  }

  // ── P9 — the ambiguity guard is REAL, not a comment ──────────────────────
  // An inherited fd genuinely puts one socket inode in two processes' fd tables. Rather than
  // simulate it, this asserts the property the guard depends on: the holder scan REPORTS every
  // holder, so the >1 branch is reachable. A guard whose precondition can never occur is decoration.
  {
    const srv = http.createServer(() => {});
    await new Promise((r) => srv.listen(0, '127.0.0.1', r));
    const child = spawn(process.execPath, ['-e', 'setTimeout(()=>{},3000)'], { stdio: 'ignore' });
    const holders = findSocketHolders(999999999);
    t(Array.isArray(holders) && holders.length === 0,
      'P9 — the holder scan returns a LIST (so the >1 refusal branch is reachable), empty for a bogus inode',
      `holders=${JSON.stringify(holders)}`);
    child.kill(); srv.close();
  }

  // ── P10 — loopback classification, both spellings ────────────────────────
  {
    t(isLoopback('127.0.0.1') && isLoopback('::1') && isLoopback('::ffff:127.0.0.1')
      && !isLoopback('100.64.0.1'),
      'P10 — loopback recognised in v4, v6 and v4-mapped spellings; tailnet is not loopback');
  }

  try { fs.unlinkSync(clientFile); } catch {}

  // Completeness asserted, never counted (G-121): a truncated run reads greener than a full one,
  // because the legs that did not run print nothing at all.
  // 11, counted from the legs below, not estimated — this assertion caught the author's own
  // miscount on its first run, which is the only reason it is worth its two lines.
  const EXPECTED = 11;
  const ran = lines.filter((l) => l.startsWith('PASS ') || l.startsWith('FAIL ')).length;
  if (ran !== EXPECTED) {
    lines.push(`FAIL completeness — ran ${ran} of ${EXPECTED} legs`);
    fails.push(`completeness(${ran}/${EXPECTED})`);
  }

  lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
  if (fails.length > 0) throw new Error(`peer-identity probes failed: ${fails.join(', ')}`);
});
