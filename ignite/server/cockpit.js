'use strict';

// Task 7.36 (settle ledger R6, R15) — the BOOT COCKPIT: the owner's view BETWEEN runs.
//
// A goal's tmux room is RUN-scoped (R15): created at run start, torn down at run close. Between
// runs the owner has no room to attach to at all. R6 gives them one: at boot the ignite daemon
// spawns a tmux session holding teamview plus a LAZY master pane — cd'd to place with the harness
// NOT launched, so the owner attaches and types to start it.
//
// ── Why this is additive composition and NOT `composeSeatSpawn` (spawn/tmux.js:106) ────────────
//
// That function always does three things a cockpit must not do: it bwrap-wraps a harness argv
// (throwing E_FS_SANDBOX_UNAVAILABLE on a bwrap-less box before any tmux argv exists), it
// systemd-run --scope-wraps that, and it emits `tmux new-window -t ${room}:` — a WINDOW in an
// EXISTING room. The cockpit needs a new SESSION, and its master pane's entire point is that
// NOTHING is launched in it, so there is no harnessArgv to wrap. Forcing the seat composer here
// would mean inventing an argv for a pane defined by the absence of one.
//
// ⚠ WHAT DROPPING THE COMPOSER DROPPED WITH IT (fixed 2026-08-14, daemon-fix §1). The rationale
// above never mentioned CGROUP DETACHMENT, but `composeSeatSpawn`'s other job is the
// `systemd-run --scope` wrapper. Without it, at boot — when no tmux server is running yet — the
// `new-session` call FORKS THE TMUX SERVER as a child of the node process, inside
// `rbtv-ignite.service`'s cgroup (measured: server pid 241103 double-forked away, reparented to
// `systemd --user`, and STILL sat in the unit's cgroup). The unit is KillMode=control-group, so
// every stop/restart reaped the tmux server and with it EVERY pane on the box, including the
// owner's own sessions. The server-creating call is therefore wrapped in its own transient scope;
// the later split-window/new-window calls talk to an already-detached server and are untouched.
//
// The bound that SURVIVES the addition is DEC-1's R3 (R28): the ignite daemon stays the SOLE
// spawn path. This module is reached only from the daemon's own boot (server/index.js); it takes
// no caller argument, is exposed through no gateway intent, and no agent can ask for a cockpit or
// name one. The request surface gains nothing — the same stance the tmux ROOM takes at
// index.js:585 ("the room is not a caller argument").
//
// ── THIS MODULE IS A COMPOSER PLUS ONE THIN EXECUTOR ───────────────────────────────────────────
//
// `composeCockpitSpawn` returns argv vectors and touches nothing; `ensureCockpit` runs them
// through an INJECTABLE executor. Both halves are therefore exercisable without a live tmux
// server, which is why probe-cockpit can prove the composition on a box with no tmux at all and
// prove the live behaviour separately under a throwaway session name.
//
// ── The load-bearing rule inherited from spawn/tmux.js ─────────────────────────────────────────
// Every pane command is an ARGV VECTOR passed after tmux's `--` separator, never a composed
// string handed to a shell. tmux execs the vector directly. See that file's header for the run
// issue (G-11) this prevents.
//
// ── Two failure modes this design closes MECHANICALLY, both measured ───────────────────────────
//
// 1. THE TEAMVIEW PANE CANNOT DIE AT BOOT. teamview refuses (stderr, exit 2) when it cannot
//    resolve a run package, and a pane whose command exits is closed by tmux — so a bare
//    `teamview` in the cockpit would leave a dead pane, or no pane, exactly in the between-runs
//    case the cockpit exists for. Leader ruling (2026-07-27 ~23:25): the cockpit passes
//    `--package <abs run folder>` EXPLICITLY. Measured consequence, and it is stronger than the
//    ruling claimed: WITH an explicit --package teamview NEVER exits 2 even when the folder holds
//    no state.json — it renders a loud `TEAMVIEW: NO SNAPSHOT` frame and KEEPS LOOPING (verified
//    2026-07-27: 8s run, 4 redraws, killed by timeout at exit 124). The pane survives in every
//    state, so "teamview running" holds between runs, during runs, and on a fresh workspace.
//
// 2. THE SESSION CANNOT DIE WITH TEAMVIEW. The session is created BY THE MASTER PANE — a plain
//    login shell that never exits — and the teamview pane is SPLIT IN AFTERWARDS. So the
//    cockpit's life is anchored to the pane that cannot terminate, not to the one that could.
//    Creating it the other way round would make an attachable cockpit contingent on teamview.
//
// ── Naming (a criterion, not a preference) ─────────────────────────────────────────────────────
//
// The cockpit must be named distinctly from a goal room so neither is mistaken for the other.
// Three mechanisms, because a convention alone is not a guarantee:
//   * the name is a fixed constant carrying an `rbtv-` prefix, and it is validated through
//     spawn/tmux.js's OWN `assertTmuxName` (imported, never re-implemented — a second copy of
//     that guard would drift, and it would drift silently in the direction that matters);
//   * `ensureCockpit` REFUSES to spawn when the cockpit name collides with the goal room name
//     (RBTV_IGNITE_TMUX_ROOM) — the collision is caught at boot, not discovered by a human;
//   * the session carries the tmux user option `@rbtv-cockpit`, so anything needing to know
//     "is this the cockpit?" reads a MARKER rather than pattern-matching a name.
//
// Session existence is tested against EXACT names from `list-sessions -F '#{session_name}'`,
// never `has-session -t`: tmux target resolution prefix-matches, so `has-session` would report a
// goal room named `rbtv-cockpit-anything` as the cockpit and silently skip the spawn.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { pythonCmd } = require('../lib/python-cmd');

const { assertTmuxName } = require('./spawn/tmux');
// 7.607 E3: the ONE home of 'is this goal executing' (design-lock item 1). Required here, never
// re-implemented — a second room predicate is the drift PRIN-11 forbids.
const { deriveLease } = require('./lease/lease');

// The reserved cockpit session name. A constant, never an operator string: it is half of the
// distinctness guarantee above, and a configurable name would make that guarantee configurable.
const COCKPIT_SESSION = 'rbtv-cockpit';
const COCKPIT_WINDOW = 'cockpit';
// The machine-readable identity marker (a tmux user option, session-scoped).
const COCKPIT_MARKER = '@rbtv-cockpit';

// The transient scope that holds the tmux SERVER, minted fresh per boot attempt. Not a fixed name:
// with this fix the server normally SURVIVES a daemon restart, so `ensureCockpit` finds the session
// and skips creation entirely — a constant unit name would collide on the rare re-create path
// (--collect only reaps a scope once its processes are gone).
const COCKPIT_SCOPE_PREFIX = 'rbtv-tmux-cockpit-';
const mintCockpitScopeUnit = () => `${COCKPIT_SCOPE_PREFIX}${randomUUID()}`;

// Percentage of the window width given to the teamview pane. The master pane keeps the rest and
// stays ACTIVE, so attaching lands the owner on the pane they type into (criterion: "attaching
// and typing starts a master normally") while the dashboard stays visible beside it.
const TEAMVIEW_PANE_PERCENT = 60;

class CockpitError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.code = code;
    this.detail = detail;
  }
}

const E_COCKPIT_NAME_COLLISION = 'E_COCKPIT_NAME_COLLISION';
const E_COCKPIT_TEAMVIEW_UNRESOLVED = 'E_COCKPIT_TEAMVIEW_UNRESOLVED';

// ── teamview resolution ────────────────────────────────────────────────────────────────────────
//
// Order: an explicit env override (the operator surface, D26(3) — instance paths never in code),
// then `teamview` on PATH, then the repo-relative sibling in the orchestration module. The PATH
// entry is a PER-MACHINE symlink that git never syncs, so it can be absent on a fresh box; the
// repo-relative fallback is what makes the cockpit work there without an operator step. Returns
// null when nothing resolves — the caller decides, so this function stays pure.
function resolveTeamviewArgv({ igniteSrc, env = process.env, exists = fs.existsSync } = {}) {
  const override = env.RBTV_IGNITE_COCKPIT_TEAMVIEW;
  if (override) return [override];

  for (const dir of String(env.PATH || '').split(path.delimiter)) {
    if (!dir) continue;
    const cand = path.join(dir, 'teamview');
    if (exists(cand)) return [cand];
  }

  if (igniteSrc) {
    const sibling = path.resolve(igniteSrc, '..', 'orchestration', 'teamview', 'tool', 'teamview.py');
    if (exists(sibling)) { const py = pythonCmd(); return py ? [py, sibling] : null; }
  }
  return null;
}

// ── package resolution ─────────────────────────────────────────────────────────────────────────
//
// WHICH goal the cockpit renders. The leader ruled the FORM (an explicit --package); this is the
// only part left.
//
// ⚠ THE LIVE QUESTION IS ASKED OF THE LEASE, NOT OF AN mtime (7.607 E3, design-lock item 1;
// inventory #12). This used to glob `{workspace}/.rbtv/goals/*/runs/run-*` and rank by
// `state.json`'s mtime — a THREE-WAY wrong reading of "which workspace is live": the run folders
// are gone, an mtime is a stored artefact of the last writer rather than evidence of a live
// execution, and a stale sensor left one goal outranking the goal that was actually executing.
// A goal is EXECUTING iff its room exists NOW; that is the lease's whole contract and this asks
// it directly.
//
// THE ORDER, and why each rung exists:
//   1. the env override — an operator pinning a fixed view outranks every derivation;
//   2. a LIVE LEASE — the goal whose room exists now. Exactly one is the design (item 2); on
//      more than one the FIRST by name is taken deterministically rather than refusing, because
//      this composes a VIEW and a cockpit that refuses to render is worse than one rendering a
//      named, checkable choice;
//   3. BETWEEN EXECUTIONS, the most recent snapshot — the goal that just finished, which
//      teamview renders with its visible STALE warning (task 7.34 / R24). This rung reads an
//      mtime, and that is legitimate here BECAUSE it is not answering liveness: rung 2 already
//      answered it `no`. The question here is "what did the owner last look at".
//
// An UNREADABLE lease falls through to rung 3 rather than resolving nothing: this is a view, and
// the posture on ignorance for a view is to show the last thing known, never to blank the screen.
function resolveCockpitPackage(workspaceRoot, { env = process.env, readLease = null } = {}) {
  const override = env.RBTV_IGNITE_COCKPIT_PACKAGE;
  if (override) return path.resolve(override);
  if (!workspaceRoot) return null;

  const goalsRoot = path.join(workspaceRoot, '.rbtv', 'goals');
  let goals;
  try {
    goals = fs.readdirSync(goalsRoot, { withFileTypes: true }).filter((g) => g.isDirectory());
  } catch {
    return null;
  }

  // RUNG 2 — the live lease. `readLease` is the injection point a probe supplies a fixture tmux
  // server through; the default is the one home (`server/lease/lease.js`), never a second room
  // predicate written here.
  const lease = readLease || deriveLease;
  const live = [];
  for (const goal of goals) {
    let l;
    try { l = lease({ workspaceRoot, goal: goal.name }); } catch { continue; }
    if (l && l.ok && l.live && l.rooms && l.rooms.length) live.push(l.rooms[0].packageDir);
  }
  if (live.length) return live.sort()[0];

  // RUNG 3 — nothing is executing: the most recent snapshot. Ranked by `state.json` mtime, and a
  // goal WITH a snapshot always outranks one without, whatever the mtimes say: a folder touched
  // by an unrelated write is not evidence that anything ever ran there.
  let best = null;
  for (const goal of goals) {
    const goalPath = path.join(goalsRoot, goal.name);
    let stamp = 0;
    let hasSnapshot = false;
    try {
      stamp = fs.statSync(path.join(goalPath, 'state.json')).mtimeMs;
      hasSnapshot = true;
    } catch {
      try { stamp = fs.statSync(goalPath).mtimeMs; } catch { continue; }
    }
    const better = !best
      || (hasSnapshot && !best.hasSnapshot)
      || (hasSnapshot === best.hasSnapshot && stamp > best.stamp);
    if (better) best = { goalPath, stamp, hasSnapshot };
  }
  return best ? best.goalPath : null;
}

// ── the composition ────────────────────────────────────────────────────────────────────────────
//
// Returns the three argv vectors, in the order they must run. Pure: it validates and composes,
// it never executes.
//
//   1. newSessionArgv — creates the session AND the LAZY master pane in one act, wrapped in a
//      per-attempt `systemd-run --user --scope --collect` so the tmux server it forks lands in
//      its OWN cgroup instead of the daemon's (see the header note). Everything after the
//      wrapper's `--` is the intact tmux vector: there is NO command after `-c <masterDir>`, and
//      that absence IS the feature — tmux starts the configured default-shell, so the pane holds
//      a shell and no harness. `-d` so the spawn never steals an attached client's focus.
//      `-P -F` still captures on stdout: systemd-run --scope forks/execs and waits, and its own
//      chatter goes to stderr.
//   2. markArgv       — stamps the identity marker.
//   3. splitArgv      — adds the teamview pane. `-d` keeps the MASTER pane active, so an
//      attaching owner lands where they type. `--` then the vector: tmux execs it, no shell
//      parses it.
function composeCockpitSpawn({
  sessionName = COCKPIT_SESSION,
  windowName = COCKPIT_WINDOW,
  masterDir,
  teamviewArgv,
  packageDir,
  teamviewPercent = TEAMVIEW_PANE_PERCENT,
  scopeUnit = mintCockpitScopeUnit(),
}) {
  assertTmuxName('tmux session', sessionName);
  assertTmuxName('tmux window', windowName);
  if (!masterDir) {
    throw new CockpitError('E_BAD_REQUEST', 'composeCockpitSpawn: masterDir is required', {});
  }
  if (!Array.isArray(teamviewArgv) || teamviewArgv.length === 0) {
    throw new CockpitError(E_COCKPIT_TEAMVIEW_UNRESOLVED,
      'composeCockpitSpawn: teamviewArgv is required and must be a non-empty vector', {});
  }

  // Composed inline rather than through spawn/tmux.js's `buildScopeArgv`: that one emits
  // `--quiet` and no `--collect`, takes seat caps this call has none of, and names its unit
  // `rbtv-seat-*`. Widening it for one non-seat caller would change every seat's argv; the
  // divergence here is four literal flags.
  const newSessionArgv = [
    'systemd-run', '--user', '--scope', '--collect', `--unit=${scopeUnit}`,
    '--',
    'tmux', 'new-session',
    '-d',
    '-s', sessionName,
    '-n', windowName,
    '-c', masterDir,
    '-P', '-F', '#{pane_id} #{pane_pid}',
  ];

  const markArgv = ['tmux', 'set-option', '-t', `${sessionName}:`, COCKPIT_MARKER, '1'];

  // packageDir may be null on a workspace that has never held a run. teamview is still launched
  // — it renders its own loud NO SNAPSHOT frame and keeps looping (see header note 1) — but with
  // no --package it would exit 2 and the pane would die, so the flag is only passed when the
  // value exists, and the pane's cwd carries the fallback.
  const teamviewCmd = packageDir ? [...teamviewArgv, '--package', packageDir] : [...teamviewArgv];

  const splitArgv = [
    'tmux', 'split-window',
    '-d',
    '-h', '-l', `${teamviewPercent}%`,
    '-t', `${sessionName}:${windowName}`,
    '-c', packageDir || masterDir,
    '-P', '-F', '#{pane_id} #{pane_pid}',
    '--',
    ...teamviewCmd,
  ];

  return { newSessionArgv, markArgv, splitArgv, teamviewCmd, scopeUnit };
}

// The default executor. Separated so `ensureCockpit` can be driven with a recording stub.
function defaultRunTmux(argv, { timeoutMs = 10000 } = {}) {
  return execFileSync(argv[0], argv.slice(1), { encoding: 'utf8', timeout: timeoutMs }).trim();
}

// Exact session names. `list-sessions` exits non-zero when no server is running at all, which is
// the ordinary state at boot — that is "no sessions", not an error.
function listSessionNames(runTmux) {
  try {
    const out = runTmux(['tmux', 'list-sessions', '-F', '#{session_name}']);
    return String(out).split('\n').map((s) => s.trim()).filter(Boolean);
  } catch {
    return [];
  }
}

// ── the boot entry point ───────────────────────────────────────────────────────────────────────
//
// IDEMPOTENT: a cockpit that already exists is left exactly as it is. The daemon has
// Restart=on-failure, so boot runs again on every restart; a spawn that recreated the session
// would destroy whatever the owner had open in it.
//
// FAIL-SOFT BY CONSTRUCTION: every failure is reported and swallowed. A box with no tmux, no
// teamview, or a refusing tmux server must not take the daemon down — the cockpit is a
// convenience surface, and the daemon carries the control plane. The one thing it will not do
// quietly is skip: every outcome is logged with its reason.
// ⚠ `installed` IS A REQUIRED GATE, AND IT WAS ADDED BECAUSE THE FEATURE LEAKED. A cockpit
// deliberately OUTLIVES the daemon that spawned it (that is the whole point — R15: it is the view
// that survives between runs). The unforeseen consequence: EVERY daemon boot leaves one behind,
// including the throwaway daemons that probes boot. Measured 2026-07-27 — running the ignite probe
// suite left a stray `rbtv-cockpit` session on the box, spawned by another task's throwaway unit.
//
// The gate is the module's OWN canonical install test (D81: a valid server.json = installed),
// already computed at boot entry in index.js — NOT a new heuristic, and deliberately not one: a
// rule like "skip workspaces under /tmp" would be this project inventing policy to paper over its
// own side effect. A daemon booting a workspace that is not installed is not serving an owner, so
// it has no owner's view to put up.
//
// DISCLOSED COST: on the very FIRST boot of a genuine new install, server.json is not yet valid
// (it is written later, on a successful tailnet bind), so no cockpit appears until the next boot.
// Accepted: a workspace on its first boot has no runs to view, and the reason is logged by name.
function ensureCockpit({
  workspaceRoot,
  igniteSrc,
  installed = false,
  goalRoom = null,
  masterDir = null,
  sessionName = COCKPIT_SESSION,
  env = process.env,
  runTmux = defaultRunTmux,
  logger = () => {},
} = {}) {
  const log = (level, message, extra = {}) => logger({ level, message, check: 'cockpit', ...extra });

  if (String(env.RBTV_IGNITE_COCKPIT || '').toLowerCase() === 'off') {
    log('info', 'boot cockpit disabled by RBTV_IGNITE_COCKPIT=off', { spawned: false });
    return { spawned: false, reason: 'disabled' };
  }

  if (!installed) {
    log('info', 'boot cockpit skipped: this workspace is not installed (no valid server.json), so ' +
      'this daemon is not serving an owner — see cockpit.js on why a throwaway daemon must not ' +
      'leave a persistent session behind', { spawned: false });
    return { spawned: false, reason: 'workspace-not-installed' };
  }

  try {
    // The distinctness criterion, enforced rather than conventional. A goal room sharing the
    // cockpit's name would make every later tmux target ambiguous, so this refuses the spawn
    // instead of creating the ambiguity.
    if (goalRoom && goalRoom === sessionName) {
      throw new CockpitError(E_COCKPIT_NAME_COLLISION,
        `the goal room and the cockpit are both named ${JSON.stringify(sessionName)} — refusing to ` +
        `spawn a cockpit that cannot be told apart from a run's room (task 7.36 naming criterion). ` +
        `Point RBTV_IGNITE_TMUX_ROOM at a different name.`,
        { sessionName, goalRoom });
    }

    // The master pane's cwd. Default: the WORKSPACE ROOT — a session opened cold at the workspace
    // root IS the console master (the workspace's own Console Master rule), so a pane parked
    // there is a master the moment the owner types a harness into it. That is what makes the pane
    // LAZY rather than merely empty: the identity comes from the place, not from a launch.
    // R6's "console-run goals are owner territory" is honoured — the daemon provides the pane and
    // neither spawns nor tracks a session in it.
    const resolvedMasterDir = masterDir || env.RBTV_IGNITE_COCKPIT_MASTER_DIR || workspaceRoot;
    if (!resolvedMasterDir) {
      throw new CockpitError('E_BAD_REQUEST', 'cockpit: no master pane directory could be resolved', {});
    }

    const existing = listSessionNames(runTmux);
    if (existing.includes(sessionName)) {
      log('info', 'boot cockpit already present, left untouched', { session: sessionName, spawned: false });
      return { spawned: false, reason: 'already-present', session: sessionName };
    }

    const teamviewArgv = resolveTeamviewArgv({ igniteSrc, env });
    if (!teamviewArgv) {
      throw new CockpitError(E_COCKPIT_TEAMVIEW_UNRESOLVED,
        'cockpit: teamview could not be resolved from RBTV_IGNITE_COCKPIT_TEAMVIEW, PATH, or the ' +
        'orchestration module beside this one — not spawning a cockpit with a dead dashboard pane.',
        {});
    }

    const packageDir = resolveCockpitPackage(workspaceRoot, { env });
    const composed = composeCockpitSpawn({
      sessionName,
      masterDir: resolvedMasterDir,
      teamviewArgv,
      packageDir,
    });

    const masterPane = runTmux(composed.newSessionArgv);
    runTmux(composed.markArgv);
    const teamviewPane = runTmux(composed.splitArgv);

    log('info', 'boot cockpit spawned', {
      session: sessionName,
      masterDir: resolvedMasterDir,
      package: packageDir,
      masterPane,
      teamviewPane,
      scopeUnit: composed.scopeUnit,
      spawned: true,
    });
    return { spawned: true, session: sessionName, masterDir: resolvedMasterDir, packageDir, masterPane, teamviewPane };
  } catch (err) {
    // Loud, and never fatal. `reason` names WHY there is no cockpit, so an absent one is never
    // mistaken for a healthy one.
    //
    // ⚠ One `reason` this arm CAN carry is a missing `systemd-run` — since the cockpit-scope fix
    // (2026-08-14, `0ce5f9e0`) the session-creating vector is systemd-run-wrapped, so on a box
    // without it this arm fires instead of spawning an unwrapped cockpit. That path is
    // DELIBERATELY unexercised: the owner ruled on 2026-08-15 (closeout R5.4) that NON-SYSTEMD
    // BOXES ARE OUT OF SUPPORT. Do not build a fixture for it — the question is closed.
    log('warn', 'boot cockpit not spawned', {
      spawned: false,
      reason: err.code || 'error',
      error: err.message,
    });
    return { spawned: false, reason: err.code || 'error', error: err.message };
  }
}

module.exports = {
  COCKPIT_SESSION,
  COCKPIT_WINDOW,
  COCKPIT_MARKER,
  TEAMVIEW_PANE_PERCENT,
  CockpitError,
  E_COCKPIT_NAME_COLLISION,
  E_COCKPIT_TEAMVIEW_UNRESOLVED,
  resolveTeamviewArgv,
  resolveCockpitPackage,
  composeCockpitSpawn,
  ensureCockpit,
};
