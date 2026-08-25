'use strict';

// ── THE DERIVED LEASE — "is this goal executing?", answered from LIVE EVIDENCE ONLY ─────────────
//
// Epic 7.607 stage E1, executing `decisions.md#d-extinguishment-design-lock` items 1–4 (which in
// turn execute `#d-runs-extinguished`). This module REPLACES the run register as the answer to
// goal liveness. Its whole contract is one sentence:
//
//   A goal is EXECUTING iff its tmux room exists right now; the seats holding that lease are the
//   registered occupants whose (pid, pid-starttime) pair is alive AND whose /proc ancestry reaches
//   a pane of that room.
//
// ⚠ NO STORED STATUS IS READ, ANYWHERE IN THIS FILE, BY CONSTRUCTION. No `runs.csv`, no lease
// file, no heartbeat, no state.json, no mtime. That is not a style preference — it is the ruling
// (item 1: "NO stored status of any kind"), and the reason is the defect class the register kept
// producing: a stored `state=open` outlives the thing it describes, so every reader of it was
// answering a question about the past while believing it was reading the present (G-103's stale
// fire, the run-1 sensor writing into a run closed 6h earlier, the 7.608 deadlock where a stale
// open row refused a start for a run nobody was running). `sessions.csv` IS read here — but ONLY
// for the pid/starttime PAIR, which is a POINTER AT A PROCESS, never a status: the row asserts
// nothing about liveness, and every row it names is re-measured against /proc before it counts.
// A row for a dead process contributes exactly nothing and is not an error.
//
// ⚠ THE ROOM NAME IS THE GOAL NAME — the E1 transitional predicate is COLLAPSED (7.607 E2b).
// Design lock item 2: ONE room per goal, named for the goal. E1 accepted a second spelling,
// `<goal>-run-N`, because the layout had not yet moved and `workflow_launcher.session_name` still
// composed it. E2b re-keyed that launcher to the bare goal in the SAME stage as this collapse —
// never separately — so the legacy arm has no producer left. It is DELETED rather than kept as a
// tolerant reader, and under the goal-direct layout keeping it would have been worse than dead:
// `packageDirForRoom` mapped a legacy room to `<goal>/runs/run-N`, a path that no longer exists,
// so a legacy-named room derived a packageDir failing `existsSync` — contributing no authz grant
// and no verified seat while still counting as a matched room (E2a findings §5.3).
//
// ⚠ UNREADABLE IS NOT EMPTY, AND NEVER FAIL-OPEN. `tmux` missing, refusing, or erroring returns
// `{ ok: false, reason }`. Every caller must treat that as "I do not know", never as "no lease".
// The distinction is the one the register got wrong in both directions at once: the ticker gate
// fails CLOSED on ignorance (it may not start on a fact it could not read) while the watchers
// failed OPEN on it (a broken meter may not stop a healthy loop). Both postures are legitimate;
// what is not legitimate is a resolver that decides for them. So this reports and never decides.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { readCsv } = require('../seat-identity/csv');

// The ONE room spelling: the bare goal name. Exact equality, never a prefix or a pattern — a goal
// named `foo` must not match the room of a goal named `foo-bar`.
function roomNamesForGoal(goal, rooms) {
  return rooms.filter((r) => r === goal);
}

// Which folder a room's working content lives in. The package IS the goal folder (design-lock
// item 8), so this is now an identity — kept as a named function because it is exported and
// because the mapping is a real concept a reader looks for, not because it computes anything.
function packageDirForRoom({ goalDir }) {
  return goalDir;
}

// /proc/<pid>/stat, parsed from the LAST ')' — the comm field is parenthesised and may itself
// contain spaces and parentheses, which is the classic way this parse goes quietly wrong.
// (Deliberate near-duplicate of `seat-identity/identity.js`'s private reader: that file is not in
// this stage's write surface, so exporting from it is E2's fold. Noted as a compat seam.)
function readProcStat(pid) {
  let raw;
  try { raw = fs.readFileSync(`/proc/${pid}/stat`, 'utf8'); } catch { return null; }
  const close = raw.lastIndexOf(')');
  if (close < 0) return null;
  const rest = raw.slice(close + 2).trim().split(/\s+/);
  const ppid = Number.parseInt(rest[4 - 3], 10);
  const starttime = rest[22 - 3];
  if (!Number.isFinite(ppid) || starttime === undefined) return null;
  return { pid: Number(pid), ppid, starttime };
}

// The ancestry as a SET of pids, caller-independent by construction (identity.js's own argument:
// a check asking "is my PARENT X" answers differently under a `timeout` wrapper, which is G-101).
function ancestryPids(startPid, maxDepth = 64) {
  const out = [];
  let pid = Number(startPid);
  const seen = new Set();
  for (let i = 0; i < maxDepth; i++) {
    if (!pid || pid < 1 || seen.has(pid)) break;
    seen.add(pid);
    out.push(pid);
    const st = readProcStat(pid);
    if (!st || pid === 1) break;
    pid = st.ppid;
  }
  return out;
}

// ⚠ THE SOCKET PATH IS CHECKED BEFORE tmux IS ASKED ANYTHING (7.607 E3b, closing the §2-review r17
// fail-open). The errno classifier below cannot close this hole, and that is the point of doing it
// here instead: `no such file or directory` is the SAME phrase for the legitimate no-server case
// (the socket file was never created) and for a MISCONFIGURED socket location (the directory the
// socket would live in does not exist, or `$TMUX` names a socket path that is gone). Measured
// 2026-08-09: a live goal read `ok:true, live:false, rooms:0` against a server-less socket dir —
// indistinguishable from "this goal is not executing", which is fail-OPEN on the lease's PRIMARY
// evidence in the one module whose header promises the opposite posture.
//
// The two cases ARE separable, just not from tmux's stderr: a socket DIRECTORY that does not exist
// or cannot be entered is a configuration fault, whereas an existing readable directory holding no
// socket is a real, readable EMPTY. So the directory is stat'd first and an absent/unreadable one
// THROWS — `deriveLease` turns that into `{ ok:false }`, which is ignorance, and every caller's own
// posture (the ticker gate's fail-closed, the watchers' fail-open) then applies to it correctly.
//
// ⚠ `$TMUX` IS CONSULTED FIRST BECAUSE IT WINS. Measured on this box 2026-08-09: with `$TMUX`
// naming a nonexistent socket and `TMUX_TMPDIR` naming a live isolated server, tmux tried the
// `$TMUX` path and failed — the environment variable inside a pane selects the socket outright and
// `TMUX_TMPDIR` is not consulted. A guard that only checked `TMUX_TMPDIR` would therefore be blind
// in exactly the context every team-kit seat runs in (a pane), and would ALSO invent a false
// unreadable there whenever a seat's stale `TMUX_TMPDIR` pointed nowhere while its real socket was
// fine. This is also the OTHER half of the E3 footgun the run's binding 12 names from the caller
// side: a `TMUX_TMPDIR` naming a nonexistent directory makes tmux fall back to the DEFAULT socket,
// so an "isolated" fixture silently reads the owner's live server. Refusing here means a
// misconfigured caller is told, rather than quietly answered about the wrong server.
function assertSocketReadable() {
  const inPane = (process.env.TMUX || '').trim();
  if (inPane) {
    const sock = inPane.split(',')[0];
    try {
      fs.accessSync(sock, fs.constants.R_OK | fs.constants.W_OK);
    } catch (err) {
      throw new Error(`$TMUX names the socket ${sock}, which is not usable (${err.code}) — this is a `
        + 'MISCONFIGURED socket location, not an absent server, and the two must not read alike');
    }
    return;
  }
  const dir = (process.env.TMUX_TMPDIR || '').trim() || '/tmp';
  let st;
  try {
    st = fs.statSync(dir);
    fs.accessSync(dir, fs.constants.R_OK | fs.constants.X_OK);
  } catch (err) {
    throw new Error(`the tmux socket directory ${dir} cannot be read (${err.code}) — a socket `
      + 'location that does not exist or cannot be entered is a CONFIGURATION fault, and tmux '
      + 'reports it with the same errno phrase as an absent server; classifying it EMPTY would be '
      + 'fail-open on the lease\'s primary evidence');
  }
  if (!st.isDirectory()) {
    throw new Error(`the tmux socket directory ${dir} is not a directory — the socket location is `
      + 'misconfigured, which is ignorance about the lease, never an absent lease');
  }
}

// The one tmux read. Injectable so a probe supplies a real fixture server's output rather than
// this module growing an assertion channel.
function defaultTmuxProbe() {
  assertSocketReadable();
  const run = (args) => execFileSync('tmux', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  // `list-sessions` exits 1 with "no server running", or with `error connecting to <socket> (No
  // such file or directory)`, when nothing is up — that is a legitimate EMPTY, not an unreadable.
  // ⚠ THE CLASSIFICATION IS BY THE ERRNO PHRASE, NEVER BY THE BARE WORDS "error connecting".
  // A bare `error connecting` arm swallows every OTHER connect failure — permission denied, a
  // socket path over the sun_path limit, a half-dead server — and reports it as "no sessions",
  // which is fail-OPEN on ignorance in this module's PRIMARY evidence and the exact inversion of
  // the posture the header promises. Measured on this box 2026-08-09 (§2 review): a scratch
  // `TMUX_TMPDIR` whose socket path exceeded the limit printed `error connecting to … (File name
  // too long)` and was read as an empty tmux, so the ticker gate would have ADMITTED a start on a
  // reading it never actually made. The no-server case is still empty — it carries the errno
  // phrase and matches the second alternative below.
  let sessions = '';
  try {
    sessions = run(['list-sessions', '-F', '#{session_name}']);
  } catch (err) {
    const text = `${(err && err.stderr) || ''}${(err && err.message) || ''}`;
    if (/no server running|no such file or directory/i.test(text)) sessions = '';
    else throw err;
  }
  let panes = '';
  try {
    panes = run(['list-panes', '-a', '-F', '#{session_name} #{pane_pid}']);
  } catch { panes = ''; }
  return { sessions, panes };
}

// THE LEASE. `deriveLease({ workspaceRoot, goal })` →
//   { ok: true, live, goal, goalDir, rooms: [{room, packageDir, panePids, seats:[…]}], seats, evidence }
//   { ok: false, reason, evidence }   ← UNREADABLE; never a lease verdict
//
// `live` is the ROOM's existence (design lock item 2: "the room's existence is the lease's primary
// evidence"). `seats` is the ancestry-verified occupant set — the AUTHZ half (item 4). A live room
// with zero verified seats is still a live lease: the room is the goal's execution, and a room
// mid-relaunch between seat boots would otherwise read as finished, which is the crash case the
// watcher must NOT mistake for a finish.
function deriveLease({ workspaceRoot, goal, tmuxProbe = defaultTmuxProbe }) {
  if (!workspaceRoot || !goal) {
    return { ok: false, reason: 'deriveLease requires workspaceRoot and goal', evidence: {} };
  }
  let raw;
  try {
    raw = tmuxProbe();
  } catch (err) {
    return {
      ok: false,
      reason: `tmux is unreadable (${err && err.message}) — the lease's primary evidence could not `
        + 'be measured. This is IGNORANCE, not an absent lease; callers must not read it as "no lease".',
      evidence: { tmux: 'unreadable' },
    };
  }

  const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', goal);
  const allRooms = String(raw.sessions || '').split('\n').map((s) => s.trim()).filter(Boolean);
  const matched = roomNamesForGoal(goal, allRooms);

  const panesByRoom = new Map();
  for (const line of String(raw.panes || '').split('\n')) {
    const [room, pid] = line.trim().split(/\s+/);
    if (!room || !pid) continue;
    if (!panesByRoom.has(room)) panesByRoom.set(room, []);
    panesByRoom.get(room).push(Number(pid));
  }

  const rooms = matched.map((room) => {
    const packageDir = packageDirForRoom({ goalDir, goal, room });
    const panePids = panesByRoom.get(room) || [];
    return { room, packageDir, panePids, seats: verifiedSeats({ packageDir, panePids }) };
  });

  const seats = rooms.flatMap((r) => r.seats.map((s) => ({ ...s, room: r.room, packageDir: r.packageDir })));
  return {
    ok: true,
    live: rooms.length > 0,
    goal,
    goalDir,
    rooms,
    seats,
    evidence: {
      'rooms-matched': matched,
      'room-predicate': `session name === "${goal}" (design-lock item 2: one room per goal)`,
      'sessions-seen': allRooms.length,
      'seats-verified': seats.length,
    },
  };
}

// The occupant set of ONE room: `sessions.csv` rows whose recorded process is alive with the
// recorded starttime AND whose ancestry reaches one of the room's panes.
//
// ⚠ ALL THREE CONJUNCTS ARE LOAD-BEARING and each kills a distinct forgery:
//   pid alive          — a departed seat's row grants nothing (historical seat folders are inert)
//   starttime matches  — pid reuse cannot inherit a dead seat's standing
//   ancestry in a pane — a process alive outside the goal's room is not IN this execution
// A room whose panes could not be listed verifies NOTHING rather than everything: an unmeasurable
// ancestry is not a satisfied one.
function verifiedSeats({ packageDir, panePids }) {
  const log = readCsv(path.join(packageDir, 'sessions.csv'));
  if (!log.exists) return [];
  const need = ['seat', 'pid', 'pid-starttime'];
  if (!need.every((c) => log.header.includes(c))) return [];
  const hasEnded = log.header.includes('ended');
  const paneSet = new Set(panePids);

  // Latest non-ended row per seat wins (protocol P1: a re-check-in supersedes its predecessor).
  const current = new Map();
  for (const row of log.rows) {
    if (!row.seat) continue;
    if (hasEnded && row.ended && row.ended.trim()) { current.delete(row.seat); continue; }
    current.set(row.seat, row);
  }

  const out = [];
  for (const [seat, row] of current) {
    const pid = Number.parseInt(row.pid, 10);
    if (!Number.isFinite(pid)) continue;
    const st = readProcStat(pid);
    if (!st) continue;                                     // dead — the row is history
    if (String(st.starttime) !== String(row['pid-starttime']).trim()) continue;  // pid reuse
    const chain = ancestryPids(pid);
    if (!chain.some((p) => paneSet.has(p))) continue;       // alive, but not in this room
    out.push({ seat, pid, 'pid-starttime': st.starttime, seatDir: path.join(packageDir, 'seats', seat) });
  }
  return out;
}

function describeLease() {
  return [
    'lease evidence: tmux room existence (primary) + ancestry-verified live seat processes',
    'room predicate: session name === <goal> (exact; the E1 <goal>-run-N arm is deleted, E2b)',
    'seat predicate: sessions.csv (pid, pid-starttime) alive AND ancestry reaches a pane of that room',
    'stored status read: NONE — no runs.csv, no lease file, no heartbeat, no mtime',
    'tmux unreadable: { ok:false, reason } — ignorance, never "no lease"; the caller decides its posture',
  ].join('\n');
}

module.exports = {
  deriveLease, describeLease, roomNamesForGoal, packageDirForRoom, verifiedSeats,
  // exported for the probe's unreadable-classification arms ONLY — nothing else calls them.
  defaultTmuxProbe, assertSocketReadable,
};

// ── THE PY ACCESSOR'S ENTRY POINT (7.607 E1) ───────────────────────────────────────────────────
//
// `node lease.js <workspaceRoot> <goal>` prints the lease as ONE JSON object and exits 0 whether
// the lease is live or not (an absent lease is an ANSWER); exit 1 only when it is UNREADABLE, so a
// shell caller can tell ignorance from absence without parsing prose.
//
// It exists so `team-kit/coord.py derive_lease` can be a THIN ACCESSOR over this one home
// (7.607 E3b: it named `resolve_live_run` until that wrapper was deleted — the package IS the goal
// folder, so the wrapper's whole answer had collapsed to the goal's own name)
// rather than a second implementation of the room predicate in Python. That second implementation
// is precisely the drift PRIN-11 forbids and precisely what the register era produced: three
// independent `runs.csv` parsers (inventory #33/#36/#37) that could disagree. One home, two
// language bindings, one shell hop.
if (require.main === module) {
  const [, , workspaceRoot, goal] = process.argv;
  const out = deriveLease({ workspaceRoot, goal });
  process.stdout.write(`${JSON.stringify(out)}\n`);
  process.exit(out.ok ? 0 : 1);
}
