'use strict';

// Task 7.10 — RESOLVING A CALLER THE GATEWAY CANNOT SEE FROM THE INSIDE (issue G-124).
//
// §4b answers "who is sitting in this seat" for a process asking ABOUT ITSELF: it reads its own
// cwd and its own /proc ancestry. The gateway cannot do that. It is a different process, on the
// other side of a socket. The PID namespace is gone (D3, 2026-08-19 redesign): in-cage /proc is
// now the host's, so a caged seat sees real host pids. That does not make this module optional.
// A caller must never be able to assert who it is — receiver-measured identity is still the
// right design, still not an assertion channel, and every refusal stays. The old pid=2 /
// ancestry 2<-1 measurement was true under `--unshare-all`; it is no longer the world.
//
// THE MOVE THIS MODULE MAKES: stop asking the caller. A TCP peer does not get to choose which
// process owns its socket — the kernel does — so the RECEIVER can measure the caller instead:
//
//     (peer addr, peer port)  --/proc/net/tcp-->  socket inode
//     socket inode            --/proc/<pid>/fd-->  the OWNING pid   (a HOST pid: this process
//                                                  reads the HOST /proc, where the daemon's
//                                                  recorded pid actually lives)
//     that pid                --/proc/<pid>/{cwd,stat}--> the two measurables §4b needs
//
// and then hands those measurables to the SAME `checkIdentity` a local caller goes through. The
// gate is not reimplemented here and must never be: this module's whole job is to obtain §4b's
// inputs for a remote-in-process-terms caller. Every refusal L1-L4 — including the G-126 run-live
// and rostering checks — applies unchanged, because it is literally the same function.
//
// ⚠ IT IS NOT AN ASSERTION CHANNEL, AND THAT IS THE PROPERTY TO PROTECT. Nothing the caller
// SENDS is read here. No header, no body field, no token, no claimed seat name. If a later
// change adds a parameter that the caller controls, this stops being an identity gate and becomes
// a formality — that is G-111 exactly (`COORD_AGENT`, asserted, outranking pane resolution,
// verified). The function signature takes only what the KERNEL reported about the connection.
//
// ⚠ LOCAL CALLERS ONLY, by construction and stated rather than discovered later. A caller on
// another machine (the owner's desktop over the tailnet) has no socket on this box and no pid to
// find. It resolves to a typed refusal here so the per-sender TOKEN resolver — which remains the
// plug for non-seat callers — can answer it. A remote caller is not a seat, so "no seat" is the
// correct answer, not a gap.

const fs = require('node:fs');

const { checkIdentity } = require('./identity');

// ── /proc/net/tcp parsing ────────────────────────────────────────────────────
//
// Rows: "sl local_address rem_address st tx_queue:rx_queue tr tm->when retrnsmt uid timeout inode".
// v4 addresses are hex, little-endian within the 4-byte word; v6 rows appear in a separate table
// and are matched textually, since a v6 peer is compared against a v6 local end.

function hexToIpv4(hex) {
  const n = Number.parseInt(hex, 16);
  if (!Number.isFinite(n)) return null;
  return [n & 0xff, (n >>> 8) & 0xff, (n >>> 16) & 0xff, (n >>> 24) & 0xff].join('.');
}

// IPv6 in /proc is 32 hex chars in four little-endian 32-bit words. Only the loopback and
// v4-mapped forms need to round-trip for this module's purposes, so the parse normalises to a
// comparable string rather than pretty-printing a full v6 address.
function hexToIpv6(hex) {
  if (typeof hex !== 'string' || hex.length !== 32) return null;
  const words = [];
  for (let i = 0; i < 32; i += 8) {
    const w = hex.slice(i, i + 8);
    words.push(w.slice(6, 8) + w.slice(4, 6) + w.slice(2, 4) + w.slice(0, 2));
  }
  const joined = words.join('');
  // ::1
  if (/^0{31}1$/.test(joined)) return '::1';
  // ::ffff:a.b.c.d  (v4-mapped)
  if (/^0{20}ffff/i.test(joined)) {
    const v4 = joined.slice(24);
    return [0, 2, 4, 6].map((i) => Number.parseInt(v4.slice(i, i + 2), 16)).join('.');
  }
  return joined;
}

function parseTcpTable(file) {
  let raw;
  try { raw = fs.readFileSync(file, 'utf8'); } catch { return []; }
  const rows = [];
  const lines = raw.split('\n');
  for (let i = 1; i < lines.length; i++) {
    const f = lines[i].trim().split(/\s+/);
    if (f.length < 10) continue;
    const l = f[1].split(':');
    const r = f[2].split(':');
    if (l.length !== 2 || r.length !== 2) continue;
    const conv = l[0].length === 8 ? hexToIpv4 : hexToIpv6;
    rows.push({
      localAddr: conv(l[0]),
      localPort: Number.parseInt(l[1], 16),
      remoteAddr: conv(r[0]),
      remotePort: Number.parseInt(r[1], 16),
      inode: f[9],
    });
  }
  return rows;
}

// Node reports v4-mapped v6 addresses as "::ffff:127.0.0.1"; /proc reports the same socket in the
// tcp6 table. Comparison is on the normalised form so the two spellings of one address match.
function normAddr(a) {
  if (typeof a !== 'string') return null;
  const s = a.replace(/^::ffff:/i, '');
  if (s === '0:0:0:0:0:0:0:1') return '::1';
  return s;
}

function isLoopback(addr) {
  const a = normAddr(addr);
  if (!a) return false;
  return a === '::1' || /^127\./.test(a);
}

// The PEER's socket is the row whose LOCAL end is this connection's REMOTE end (and vice versa).
// Matching on the full four-tuple, never on the port alone: ports are reused across interfaces
// and a three-field match could name a different connection's inode.
function findPeerInode({ peerAddr, peerPort, localAddr, localPort }) {
  const rows = [...parseTcpTable('/proc/net/tcp'), ...parseTcpTable('/proc/net/tcp6')];
  const hits = rows.filter((r) => r.localPort === peerPort
    && r.remotePort === localPort
    && normAddr(r.localAddr) === normAddr(peerAddr)
    && normAddr(r.remoteAddr) === normAddr(localAddr));
  // Two rows for one four-tuple would mean the table is being read mid-change or the tuple is not
  // unique; either way the answer is not trustworthy, so it is refused rather than picked from.
  if (hits.length !== 1) return { inode: null, count: hits.length };
  return { inode: hits[0].inode, count: 1 };
}

// Which process holds that socket?
//
// ⚠ FAIL CLOSED ON MORE THAN ONE HOLDER, and this is the case that is easy to miss: a socket fd
// can be INHERITED across fork or passed over a unix socket with SCM_RIGHTS, so two unrelated
// processes can legitimately hold the same inode. "First match wins" would let whichever process
// happens to sort first in /proc supply the identity — a lottery, not a measurement. Ambiguity
// here is refused, exactly as a missing row is.
function findSocketHolders(inode, { procRoot = '/proc' } = {}) {
  const want = `socket:[${inode}]`;
  const holders = [];
  let entries;
  try { entries = fs.readdirSync(procRoot); } catch { return holders; }
  for (const ent of entries) {
    if (!/^\d+$/.test(ent)) continue;
    let fds;
    try { fds = fs.readdirSync(`${procRoot}/${ent}/fd`); } catch { continue; }
    for (const fd of fds) {
      let link;
      try { link = fs.readlinkSync(`${procRoot}/${ent}/fd/${fd}`); } catch { continue; }
      if (link === want) { holders.push(Number(ent)); break; }
    }
  }
  return holders;
}

// The caged process's cwd, read from the HOST /proc. This resolves because the cage binds every
// opening SRC == DEST (bwrap.js / cage.js): the path string a caged process holds names the same
// file outside the namespace. If that ever stops being true this read returns a path the host
// cannot resolve, and `checkIdentity` refuses on the folder — fail-closed, not fail-open.
function cwdOfPid(pid) {
  try { return fs.readlinkSync(`/proc/${pid}/cwd`); } catch { return null; }
}

/**
 * Resolve the SEAT behind a live connection.
 *
 * @param {object} conn - what the KERNEL reported about the socket. Nothing here is caller-supplied
 *   content: these are properties of the connection, read from the server's own socket object.
 * @param {object} [opts] - `{ readLease }`, the SAME injection point `checkIdentity` and
 *   `checkGoalExecuting` already carry, threaded through so the seam can be driven end-to-end
 *   without a live tmux room (7.607 E3b). It is NOT an assertion channel and cannot become one:
 *   the gateway calls `checkPeerSeat(conn)` with ONE argument, so nothing on the wire can reach
 *   this parameter — only the composition root (`server/index.js`) or a probe can, exactly as with
 *   `checkIdentity({ readLease })`. And a lease reader supplies MEASURABLES (a tmux listing), never
 *   a seat name or a verdict, so the property the header protects is untouched.
 * @returns the `checkIdentity` result (`{ ok: true, seat, ... }`) or a typed refusal.
 */
function resolvePeerSeat(conn = {}, { readLease = undefined } = {}) {
  const {
    E_PEER_NOT_LOCAL, E_PEER_UNRESOLVED, E_PEER_AMBIGUOUS,
  } = require('../spawn/errors');

  const peerAddr = conn.remoteAddress;
  const peerPort = conn.remotePort;
  const localAddr = conn.localAddress;
  const localPort = conn.localPort;

  if (!peerAddr || !Number.isFinite(peerPort) || !localAddr || !Number.isFinite(localPort)) {
    return {
      ok: false,
      code: E_PEER_UNRESOLVED,
      message: 'the connection carries no complete address pair — a caller that cannot be located cannot be identified',
    };
  }

  // A non-loopback peer is not a process on this box. Refused HERE, with a code that says why, so
  // the token resolver downstream can answer it — this is a handoff, not a denial.
  if (!isLoopback(peerAddr)) {
    return {
      ok: false,
      code: E_PEER_NOT_LOCAL,
      message: `peer ${peerAddr} is not on this host, so it holds no seat here — seat identity is resolvable only for local callers; ` +
        'a remote sender authenticates by token, which is the unchanged v1 path',
      peer: peerAddr,
    };
  }

  const { inode, count } = findPeerInode({ peerAddr, peerPort, localAddr, localPort });
  if (!inode) {
    return {
      ok: false,
      code: count > 1 ? E_PEER_AMBIGUOUS : E_PEER_UNRESOLVED,
      message: count > 1
        ? `${count} sockets match ${peerAddr}:${peerPort} -> ${localAddr}:${localPort}; an ambiguous connection is refused, never guessed`
        : `no socket in /proc/net/tcp matches ${peerAddr}:${peerPort} -> ${localAddr}:${localPort} — the caller could not be located`,
    };
  }

  const holders = findSocketHolders(inode);
  if (holders.length === 0) {
    return {
      ok: false,
      code: E_PEER_UNRESOLVED,
      message: `socket inode ${inode} is held by no readable process — the caller could not be attributed to a pid`,
      inode,
    };
  }
  if (holders.length > 1) {
    return {
      ok: false,
      code: E_PEER_AMBIGUOUS,
      message: `socket inode ${inode} is held by ${holders.length} processes (${holders.join(', ')}) — an fd shared across processes ` +
        'names no single caller, and picking one would be a lottery rather than a measurement',
      inode,
      holders,
    };
  }

  const pid = holders[0];
  const cwd = cwdOfPid(pid);
  if (!cwd) {
    return {
      ok: false,
      code: E_PEER_UNRESOLVED,
      message: `the working directory of caller pid ${pid} is unreadable — one of the two measurables is missing, so identity is refused`,
      pid,
    };
  }

  // THE HANDOFF. Same gate, same refusals, same code — the only difference is whose measurables
  // it is given. A second implementation of the gate here would be a second definition of what a
  // seat is, and the two would drift.
  const result = checkIdentity({ cwd, pid, readLease });
  return result.ok
    ? { ...result, resolvedFrom: 'connection', callerPid: pid, socketInode: inode }
    : { ...result, resolvedFrom: 'connection', callerPid: pid, socketInode: inode };
}

module.exports = {
  resolvePeerSeat,
  findPeerInode,
  findSocketHolders,
  parseTcpTable,
  isLoopback,
  normAddr,
};
