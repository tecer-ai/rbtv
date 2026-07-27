'use strict';

// Task 7.30 (settle ledger R7/R8/R15/R28) — the tmux SEAT spawn target.
//
// The substrate change is a change of TARGET, never of GATE: the ignite daemon remains the sole
// spawn path (DEC-1 R3, R28). What moves is where a headed session lands — a tmux pane in the
// goal's run-scoped room (R15: one pane per seat), instead of a server-owned pty unit.
//
// The composed pane command is, in this order (R7/R28):
//
//     systemd-run --user --scope -p <caps>  --  bwrap <mount-namespace flags> -- <harness argv>
//     |__ cgroup caps, so a spiking seat dies      |__ the FS wall (bwrap.js); absence IS the
//         alone inside its own cgroup                  mechanism, there is no deny list
//
// Both layers survive INSIDE tmux because they are part of the pane's own argv: tmux execs the
// vector, the scope wraps it, bwrap wraps the harness. Nothing depends on tmux enforcing anything.
//
// Why `--scope` and not the transient `--unit` SERVICE the headless carrier uses (carrier.js
// spawnSystemd): a service is started BY systemd and reparented away, so its output never belongs
// to the pane. `--scope` puts the CALLER's own process into a fresh cgroup and keeps it where it
// was started — which is what a pane needs, since the pane IS the terminal the human attaches to.
//
// THIS MODULE IS A PURE COMPOSER. It never spawns, never calls tmux, never touches the daemon.
// The argv it returns is handed to the caller to execute — the same stance bwrap.js takes, and the
// reason both are testable without a live room.
//
// ── The load-bearing rule of this file ──────────────────────────────────────────────────────
// The pane command is an ARGV VECTOR passed after tmux's `--` separator. It is NEVER a composed
// string typed into a shell. tmux execs the vector directly, so no shell ever parses it: quotes,
// backticks, `$(...)`, semicolons and newlines in any argument reach the process byte-identical.
// Verified on this box 2026-07-27 — an argument containing  a`b`$(c) "d" 'e' ;f  arrived intact.
// This is not a style preference. The run's own team kit types a composed, quoted briefing into an
// interactive shell, and under ble.sh that shell EXECUTED the briefing as bash: the agent never
// started while its roster row read ACTIVE (run issue G-11). Any future edit that turns this back
// into a string handed to `sh -c` re-opens that class.

const { SpawnError, E_FS_SANDBOX_UNAVAILABLE, E_TMUX_NAME_INVALID, E_BAD_REQUEST } = require('./errors');
const { buildBwrapArgv } = require('./bwrap');
const { capToProperty } = require('./carrier');

// A tmux session/window name is a tmux TARGET, not free text: `:` and `.` separate
// session:window.pane, and a name carrying one silently re-targets the command at another pane.
// Names are server-composed (goal slug, seat name from the descriptor), never caller free text —
// this guard exists so that stays true even if a caller path is added later.
const NAME_FORBIDDEN = /[:.\s]/;

function assertTmuxName(kind, name) {
  if (typeof name !== 'string' || name.length === 0) {
    throw new SpawnError(E_TMUX_NAME_INVALID, `${kind} name must be a non-empty string`, { kind, name });
  }
  if (NAME_FORBIDDEN.test(name)) {
    throw new SpawnError(
      E_TMUX_NAME_INVALID,
      `${kind} name ${JSON.stringify(name)} contains a tmux target separator (':', '.') or whitespace — refusing to compose a command that could re-target another pane`,
      { kind, name },
    );
  }
}

// systemd unit names have their own alphabet. The session id is a server-minted uuid, so this is
// a belt on a value that is already safe.
function scopeUnitName(sessionId) {
  return `rbtv-seat-${String(sessionId).replace(/[^A-Za-z0-9_.-]/g, '-')}`;
}

// caps -> scope properties, through the CARRIER'S OWN translator. Reused rather than
// re-implemented on purpose: `capToProperty` THROWS on a directive it cannot translate, so a
// profile that declares a cap this carrier cannot apply fails the spawn loudly instead of quietly
// running a less-confined seat (D46). A second copy here would eventually drift out of that
// promise, and the drift would be silent in exactly the direction that matters.
function scopeCapArgs(caps) {
  const args = [];
  for (const [key, value] of Object.entries(caps || {})) {
    if (value === undefined || value === null) continue;
    const prop = capToProperty(key, value);
    if (prop) args.push('-p', prop);
  }
  return args;
}

// [systemd-run ... --] ++ argv
function buildScopeArgv({ unitName, caps, argv, userManager = true }) {
  if (!Array.isArray(argv) || argv.length === 0) {
    throw new SpawnError(E_BAD_REQUEST, 'buildScopeArgv: empty argv', {});
  }
  const out = ['systemd-run'];
  if (userManager) out.push('--user');
  out.push('--scope', '--quiet', `--unit=${unitName}`);
  out.push(...scopeCapArgs(caps));
  out.push('--');
  out.push(...argv);
  return out;
}

// The whole composition, in one call.
//
//   { room, windowName, sessionId, workdir, harnessArgv, caps, editablePaths, promptFile,
//     harness, maskPaths, userManager }
//     -> { tmuxArgv, scopeArgv, wrappedArgv, unitName }
//
// ORDER IS THE FAIL-CLOSED GUARANTEE. buildBwrapArgv runs FIRST and throws
// E_FS_SANDBOX_UNAVAILABLE on a box without bwrap (or with an unresolvable harness binary). It
// throws before any tmux argv exists, so on that box the caller has nothing to execute and NO
// PANE IS CREATED — the seat is not spawned unconfined, it is not spawned at all (D59, and task
// 7.30's criterion that the absence of bwrap still fails closed spawning nothing).
function composeSeatSpawn({
  room,
  windowName,
  sessionId,
  workdir,
  harnessArgv,
  caps = {},
  editablePaths = [],
  promptFile = null,
  harness = null,
  maskPaths = [],
  seatBinds = null,
  userManager = true,
}) {
  assertTmuxName('tmux session', room);
  assertTmuxName('tmux window', windowName);

  // 1. The FS wall. Throws on a bwrap-less box — before anything tmux-shaped exists.
  //    `seatBinds` (task 7.11) is the composed seat cage; when present it replaces the flat
  //    workdir+editablePaths openings inside buildBwrapArgv. Passed straight through: this module
  //    composes tmux, it does not get a vote on the walls.
  const wrappedArgv = buildBwrapArgv({
    argv: harnessArgv,
    workdir,
    editablePaths,
    promptFile,
    harness,
    maskPaths,
    seatBinds,
  });

  // 2. The cgroup caps, wrapping the wall.
  const unitName = scopeUnitName(sessionId);
  const scopeArgv = buildScopeArgv({ unitName, caps, argv: wrappedArgv, userManager });

  // 3. The pane. `--` then the vector: tmux execs it, no shell parses it (see the header rule).
  //    `-d` so the spawn does not steal the attached client's focus; `-P -F` so the caller gets
  //    the pane id back and can identify THIS pane later without matching on a name.
  const tmuxArgv = [
    'tmux', 'new-window',
    '-d',
    '-t', `${room}:`,
    '-n', windowName,
    '-c', workdir,
    '-P', '-F', '#{pane_id} #{pane_pid}',
    '--',
    ...scopeArgv,
  ];

  return { tmuxArgv, scopeArgv, wrappedArgv, unitName };
}

module.exports = { composeSeatSpawn, buildScopeArgv, scopeUnitName, E_TMUX_NAME_INVALID };
