'use strict';

// The pty HOST — the keystroke-rung host on the server core (session-surface-spec.md Design 1 & 2,
// realizes CMP-9's keystroke rung). It is a small EXTENSION at the existing spawn/kill/log owner,
// NOT a new subsystem: a headed session gets the SAME store row/id/status/logs/kill surface and
// the SAME transient unit + profile-pinned caps/sandbox as any spawn (D44) — the pty path is the
// only thing added; policy does not move. It composes WITH the spawn manager (reuses its config,
// kill, status, and the spawn module's carrier/bwrap/config helpers) and OWNS only the headed
// spawn path. index.js wires it in by routing session_mode:headed spawns here (pty wiring only).
//
// ARCHITECTURE (all six properties PROBE-VERIFIED this task by observed system state, D79):
//   holder    : systemd-run --user --collect --unit=rbtv-worker-<id> <caps/sandbox> \
//                 dtach -N <sock> bwrap <...> node <shim> <status-file> <tui-argv>
//               (no `--` after the socket: dtach 0.9 REJECTS it — measured this task). The pty
//               MASTER lives in the in-unit dtach holder, so the session survives daemon restarts.
//   transport : a python pty-bridge (pty-bridge.py) running dtach's OWN `-a` client on a pty
//               (dtach -a refuses piped stdio — measured). Disposable + re-attachable.
//   capture   : the in-house vt model (vt-model.js) over the bridge byte stream (Amendment #4).
//   keys      : written to the bridge's stdin → pty → TUI (POST /keys/:id, the keystroke rung).
//   watch-tee : the bridge byte stream is tee'd to {data_root}/logs/<id>.log so `logs <id>` is a
//               live watch surface for headed sessions too (raw ANSI, not stream-json — D7 prop 1).
//   exit_code : the no-shell status shim (Amendment #5 option i) writes the TRUE child status to a
//               file the daemon reads — NEVER the unit's ExecMainStatus (M3 masks it).

const fs = require('node:fs');
const path = require('node:path');
const { spawn: childSpawn } = require('node:child_process');

const { loadConfig, resolveTemplateSlots, resolveWorkdir, resolveWorkspaceRoot, sessionsRootFor } = require('../spawn/config');
const { materializeHarnessConfig, harnessOf } = require('../spawn/harness-config');
const { buildBwrapArgv } = require('../spawn/bwrap');
const { generateSessionId, buildSystemdRunArgs, systemdStatus, setsidStatus } = require('../spawn/carrier');
const { composeHeadedArgv } = require('./carriage');
const { VtModel, DEFAULT_ROWS, DEFAULT_COLS } = require('./vt-model');
const {
  SpawnError,
  E_HEADED_NOT_CAPABLE,
  E_UNKNOWN_PROFILE,
  E_FLAG_INJECTION,
  E_FS_SANDBOX_UNAVAILABLE,
  E_SESSION_NOT_LIVE,
  E_PTY_BRIDGE,
  E_PROMPT_INJECTION_TIMEOUT,
  E_HOLDER_FAILED,
} = require('./errors');

const SHIM_PATH = path.join(__dirname, 'pty-status-shim.js');
const BRIDGE_PATH = path.join(__dirname, 'pty-bridge.py');

// Resolve a bare binary on PATH the way execvp would; absolute stays as-is. Fail-closed: an
// unresolvable holder/bridge binary is a typed error, never a hang or a silent skip.
function resolveOnPath(name) {
  if (path.isAbsolute(name)) return name;
  const dirs = (process.env.PATH || '').split(path.delimiter);
  for (const dir of dirs) {
    if (!dir) continue;
    const cand = path.join(dir, name);
    try { fs.accessSync(cand, fs.constants.X_OK); return cand; } catch { /* keep scanning */ }
  }
  return null;
}

// Request-level injection hygiene (mirrors spawn.js rejectFlagInjection BYTE-FOR-BYTE — the same
// policy the headless sole-spawn-path applies; kept local because spawn.js does not export it).
// Applied to WORKDIR ONLY — the headed PROMPT is deliberately exempt (task 7.22): post-7.14 the
// headed carriage vocabulary is file|keystroke (KNOWN_HEADED_CARRIAGES, spawn/config.js; argv
// carriage RETIRED, batch-08 item 4), so the prompt is 0600-file DATA or typed keystrokes and can
// NEVER reach argv — a leading dash / newline / $() is harmless there, and rejecting it blocked
// composed multi-turn transcripts (the same over-refusal p7-multiturn removed headless-side).
// Composition-level guards stay: composeHeadedArgv refuses retired/unknown carriages typed, and
// the queue-time carriage double gate (heart-store.js, 6.2b) is untouched.
function rejectFlagInjection(value, field) {
  if (typeof value !== 'string') return;
  // Reject strings that look like flag injection attempts: leading dash, or embedded shell metacharacters.
  if (value.startsWith('-')) {
    throw new SpawnError(E_FLAG_INJECTION, `${field} starts with a flag marker`, { field, value });
  }
  if (/[;&|`$()\n\r]/.test(value)) {
    throw new SpawnError(E_FLAG_INJECTION, `${field} contains shell metacharacters`, { field, value });
  }
}

// RO-bind flags for the TUI binary (mirrors bwrap.js binaryBindFlags — kept local because bwrap.js
// is outside this task's allowlist). The headless path gets this bind from buildBwrapArgv (its
// argv[0] IS the worker binary); the headed argv[0] is node (the shim interpreter), so without an
// explicit bind the ACTUAL TUI binary is unreachable whenever it lives under the tmpfs'd HOME —
// the REAL seed case (`opencode` at ~/.opencode/bin/opencode). Proven by mutation at the p6-2
// review (shim status file: spawn ENOENT) and fixed here. A symlinked binary additionally binds
// its realpath's directory. Binaries under /usr are already ro-bound wholesale.
function tuiBinaryBindFlags(binPath) {
  const underUsr = (p) => p === '/usr' || p.startsWith('/usr/');
  const flags = [];
  if (underUsr(binPath)) return flags;
  flags.push('--ro-bind', binPath, binPath);
  let real;
  try { real = fs.realpathSync(binPath); } catch { return flags; }
  if (real !== binPath) {
    const dir = path.dirname(real);
    if (!underUsr(dir)) flags.push('--ro-bind', dir, dir);
  }
  return flags;
}

// Resolve template slots across a sandbox block by SHAPE (mirrors spawn.js resolveSandbox — the
// same {workdir} substitution the headless path applies; kept local because spawn.js does not
// export it and this task's allowlist forbids editing spawn.js).
function resolveSandbox(sandbox, workdir) {
  if (!sandbox) return sandbox;
  const values = { workdir };
  const resolved = { ...sandbox };
  for (const [key, value] of Object.entries(sandbox)) {
    if (typeof value === 'string') {
      resolved[key] = resolveTemplateSlots([value], values)[0];
    } else if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
      resolved[key] = resolveTemplateSlots(value, values);
    }
  }
  return resolved;
}

function createPtyHost({ heartStore, spawnManager, dataRoot, userManager = true, logger = null, pythonBin = 'python3' }) {
  if (!spawnManager || !spawnManager.config) throw new Error('createPtyHost requires the spawn manager (for config + kill/status)');
  const config = spawnManager.config;
  if (!dataRoot) throw new Error('createPtyHost requires dataRoot');

  const workspaceRoot = resolveWorkspaceRoot(heartStore && heartStore.dbPath);
  const sessionsRoot = sessionsRootFor(workspaceRoot);
  const ptyDir = path.join(dataRoot, 'ptys');
  const logDir = path.join(dataRoot, 'logs');

  // execId -> live session state (bridge + vt + tee). Absent = not attached in THIS daemon process.
  const sessions = new Map();

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  function ensureDirs() {
    fs.mkdirSync(ptyDir, { recursive: true, mode: 0o700 });
    fs.mkdirSync(logDir, { recursive: true, mode: 0o700 });
  }

  function sockPathFor(sessionId) { return path.join(ptyDir, `${sessionId}.sock`); }
  function transcriptLogFor(sessionId) { return path.join(logDir, `${sessionId}.log`); }
  function holderDiagLogFor(sessionId) { return path.join(logDir, `${sessionId}.holder.log`); }

  // Attach the daemon-side reader: a python pty-bridge running `dtach -a` on the holder socket.
  // Its stdout is the pty byte stream → the vt model + the transcript tee. Its stdin is the
  // keystroke channel. Disposable + re-attachable (the session lives in the in-unit holder).
  function attachBridge(entry, { rows = DEFAULT_ROWS, cols = DEFAULT_COLS } = {}) {
    const py = resolveOnPath(pythonBin);
    if (!py) throw new SpawnError(E_PTY_BRIDGE, `pty bridge interpreter '${pythonBin}' not found on PATH`, {});
    const proc = childSpawn(py, [BRIDGE_PATH, entry.sock, String(rows), String(cols)], {
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    entry.bridge = proc;
    entry.bridgeAlive = true;
    proc.stdout.on('data', (buf) => {
      // D96: the vt has now taken at least one byte, so a render is a real screen rather than the
      // blank of a not-yet-repainted re-attach. Set BEFORE the vt write so a throwing vt cannot
      // leave a painted screen reported as `repainting`.
      entry.painted = true;
      try { entry.vt.write(buf); } catch (e) { log('warn', 'vt write failed', { error: e.message }); }
      try { if (entry.logStream) entry.logStream.write(buf); } catch { /* tee best-effort */ }
    });
    proc.stderr.on('data', (buf) => log('warn', 'pty bridge stderr', { execId: entry.execId, data: buf.toString().slice(0, 200) }));
    proc.on('exit', (code, signal) => { entry.bridgeAlive = false; log('info', 'pty bridge exited', { execId: entry.execId, code, signal }); });
    proc.on('error', (err) => { entry.bridgeAlive = false; log('warn', 'pty bridge error', { execId: entry.execId, error: err.message }); });
    return proc;
  }

  // Spawn a headed session: allocate a pty via the in-unit dtach holder in the SAME transient unit
  // shape as any spawn, run the profile's headed.tui.argv (prompt-carried per Design 3) on the pty
  // slave through bwrap + the status shim, write the store row through the store module (D44), and
  // attach the daemon-side bridge/vt/tee. Signature mirrors spawnManager.spawn's headed call.
  async function spawnHeaded(execId, profileName, prompt = null, requestedWorkdir = null, enqueuedBy = 'unknown') {
    ensureDirs();

    // The same request-level hygiene the headless sole-spawn-path applies (spawn.js order:
    // injection checks BEFORE profile resolution). Workdir only — the prompt is carriage-borne
    // DATA (file|keystroke), never argv; see rejectFlagInjection's header (task 7.22).
    rejectFlagInjection(requestedWorkdir, 'workdir');

    const profile = config.profiles[profileName];
    if (!profile) throw new SpawnError(E_UNKNOWN_PROFILE, `unknown launch profile: ${profileName}`, { profile: profileName });
    if (!profile.headed) {
      throw new SpawnError(E_HEADED_NOT_CAPABLE, `profile ${profileName} is not headed-capable`, { profile: profileName, sessionMode: 'headed' });
    }

    const sessionId = generateSessionId();
    const workdir = resolveWorkdir(profile, requestedWorkdir, config.default_workdir_root, null, { execId, sessionsRoot, workspaceRoot });

    // Advisory harness-local write-restraint config (mirrors spawn.js — the kernel bwrap sandbox
    // below is load-bearing; this is the second belt).
    const resolvedSandbox = resolveSandbox(profile.sandbox, workdir);
    const editablePaths = (() => {
      const rwp = resolvedSandbox && resolvedSandbox.ReadWritePaths;
      if (!rwp) return [];
      return (Array.isArray(rwp) ? rwp : [rwp]).filter((p) => p && p !== workdir);
    })();
    try {
      const hc = materializeHarnessConfig({ sessionDir: workdir, profile, editablePaths });
      if (hc && hc.written) log('info', 'harness config materialized (headed)', { harness: hc.harness, path: hc.written });
    } catch (err) {
      log('warn', 'harness config materialization failed (advisory)', { error: err.message });
    }

    // Prompt carriage (Design 3): argv-slot | file | keystroke; reject-by-default when a prompt is
    // supplied against a profile declaring no carriage; stdin is structurally absent.
    const statusFile = path.join(workdir, '.ignite-headed-exit.json');
    const carriageResult = composeHeadedArgv(profile.headed, prompt, profileName, {
      ensurePromptFile: (p) => {
        const promptDir = path.join(dataRoot, 'prompts');
        fs.mkdirSync(promptDir, { recursive: true, mode: 0o700 });
        const pf = path.join(promptDir, `${sessionId}.txt`);
        fs.writeFileSync(pf, p ?? '', { mode: 0o600 });
        return pf;
      },
    });
    const tuiArgv = carriageResult.argv;
    const promptFile = carriageResult.promptFile;

    // Resolve the TUI binary the way execvp would, fail-closed (the same D59 posture bwrap.js
    // applies to its argv[0]), and rewrite argv[0] absolute so the exec inside the unit does not
    // depend on the unit's PATH.
    const tuiBin = resolveOnPath(tuiArgv[0]);
    if (!tuiBin) {
      throw new SpawnError(
        E_FS_SANDBOX_UNAVAILABLE,
        `headed TUI binary ${tuiArgv[0]} not resolvable on PATH — cannot bind it into the sandbox; refusing to spawn (D59 fail-closed)`,
        { binary: tuiArgv[0] },
      );
    }
    tuiArgv[0] = tuiBin;

    // Copy the status shim into the session dir (RW-bound in bwrap) so `node <shim>` is reachable
    // inside the sandbox WITHOUT binding the ignite source tree into the worker namespace (D59
    // keeps the source tree unreachable). One source of truth: the repo shim file.
    const shimInDir = path.join(workdir, '.ignite-pty-shim.js');
    fs.copyFileSync(SHIM_PATH, shimInDir);
    // Pre-create the status file so the shim (inside bwrap, workdir is RW-bound) can write it and
    // the daemon can read it after the TUI exits.
    fs.writeFileSync(statusFile, '', { mode: 0o600 });

    // node <shim> <status-file> <tui-argv...>  — no shell; the shim forks the TUI and waitpid()s.
    const shimArgv = [process.execPath, shimInDir, statusFile, ...tuiArgv];

    // bwrap-wrap exactly as the headless path does (same FS walls, same harness state binds).
    const wrapped = buildBwrapArgv({ argv: shimArgv, workdir, editablePaths, promptFile, harness: harnessOf(profile), maskPaths: config.auth?.senders_file ? [path.dirname(config.auth.senders_file)] : [] });

    // Splice the TUI-binary ro-binds in before bwrap's `--` separator (i.e. after the HOME tmpfs
    // is declared — bind order is load-bearing, see bwrap.js). The first literal `--` element in
    // a bwrap argv is always the flags/command separator (no bwrap flag or path equals `--`).
    const tuiBinds = tuiBinaryBindFlags(tuiBin);
    if (tuiBinds.length) wrapped.splice(wrapped.indexOf('--'), 0, ...tuiBinds);

    // dtach holder as the unit main process (NO `--` after the socket — dtach 0.9 rejects it).
    const dtachPath = resolveOnPath('dtach');
    if (!dtachPath) throw new SpawnError(E_HOLDER_FAILED, 'dtach not found on PATH — the in-unit pty holder is unavailable (install dtach; screen is the documented fallback)', {});
    const sock = sockPathFor(sessionId);
    try { fs.rmSync(sock, { force: true }); } catch { /* stale socket */ }
    const holderArgv = [dtachPath, '-N', sock, ...wrapped];

    // Same carrier composition as any spawn: caps + bwrap-compatible sandbox props on the unit.
    const holderDiagLog = holderDiagLogFor(sessionId);
    const transcriptLog = transcriptLogFor(sessionId);
    // Task 7.13 piece 4 (settles D97): pre-create BOTH log files 0600 before the unit starts —
    // systemd's `StandardOutput=append:` creates missing files at the manager's default mode
    // (664 observed live). An existing file keeps its mode, so the pre-create wins the race.
    // appendFileSync: never truncate. The tee's own createWriteStream below already passes
    // mode 0600, but mode applies at CREATION only — the unit could create the file first.
    fs.appendFileSync(holderDiagLog, '', { mode: 0o600 });
    fs.appendFileSync(transcriptLog, '', { mode: 0o600 });
    const { args, unitName } = buildSystemdRunArgs({
      sessionId, argv: holderArgv, workdir, logPath: holderDiagLog,
      caps: profile.caps, sandbox: resolvedSandbox, envFile: profile.env?.file, userManager,
    });

    heartStore.updateExecutionStatus(execId, { status: 'launching', sessionId, logPath: transcriptLog });

    // Launch systemd-run and wait for the unit to be running (mirrors spawnSystemd's success read).
    await new Promise((resolve, reject) => {
      const p = childSpawn('systemd-run', args, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      p.stderr.on('data', (d) => { stderr += d.toString(); });
      p.on('error', (err) => reject(new SpawnError(E_HOLDER_FAILED, `systemd-run spawn error: ${err.message}`, { unitName })));
      p.on('close', (code) => code === 0 ? resolve() : reject(new SpawnError(E_HOLDER_FAILED, `systemd-run failed (exit ${code}): ${stderr}`, { unitName, exitCode: code })));
    }).catch((err) => {
      heartStore.updateExecutionStatus(execId, { status: 'failed', endedAt: new Date() });
      throw err;
    });

    // Wait briefly for dtach to create the socket (the holder is up when the socket exists).
    const socketReady = await waitForSocket(sock, 3000);
    const info = systemdStatus(unitName, userManager);
    const pid = info.pid || null;
    // PID-reuse guard datum + session_ref capture — the same row fields the headless
    // sole-spawn-path records (spawn.js resolvePidStarttime / captureSessionRef; cwd-implicit
    // is the only capture rule resolvable at spawn time — stdout-json refs arrive later).
    const pidStarttime = pid ? (setsidStatus(pid).pidStarttime || null) : null;
    const sessionRef = profile.session_ref && profile.session_ref.source === 'cwd-implicit' ? workdir : null;

    heartStore.updateExecutionStatus(execId, {
      status: 'running', carrier: 'systemd', unitName, pid, pidStarttime, sessionRef,
      logPath: transcriptLog, sessionId, profile: profileName, workdir, startedAt: new Date(),
    });

    // Register + attach the daemon-side reader.
    const entry = {
      execId, sessionId, unitName, sock, statusFile, workdir,
      logPath: transcriptLog, carriage: carriageResult.carriage,
      vt: new VtModel({ rows: DEFAULT_ROWS, cols: DEFAULT_COLS }),
      logStream: fs.createWriteStream(transcriptLog, { flags: 'a', mode: 0o600 }),
      bridge: null, bridgeAlive: false,
      painted: false,   // D96: no byte has reached the vt yet — a render now is blank, not stale.
    };
    sessions.set(execId, entry);
    if (socketReady) {
      attachBridge(entry);
    } else {
      log('warn', 'holder socket not ready within budget; session row written, bridge deferred', { execId, sock });
    }

    // keystroke carriage: inject after a rendered-screen readiness marker (Design 3 last resort).
    if (carriageResult.keystrokePlan) {
      await injectKeystrokePrompt(entry, carriageResult.keystrokePlan).catch((err) => {
        heartStore.updateExecutionStatus(execId, { status: 'failed', endedAt: new Date() });
        throw err;
      });
    }

    const fresh = heartStore.getExecution(execId);
    if (fresh) fresh.workdir = workdir;
    return fresh;
  }

  function waitForSocket(sock, timeoutMs) {
    return new Promise((resolve) => {
      const deadline = Date.now() + timeoutMs;
      const iv = setInterval(() => {
        if (fs.existsSync(sock)) { clearInterval(iv); resolve(true); return; }
        if (Date.now() >= deadline) { clearInterval(iv); resolve(false); }
      }, 50);
    });
  }

  // ── D96: ATTACHMENT IS NOT LIVENESS ────────────────────────────────────────────────────────
  //
  // THE BUG THIS CLOSES: `sessions` is an in-daemon ATTACHMENT map — it is populated at exactly
  // two sites (spawnHeaded, reconnect) and `shutdown()` clears it while deliberately leaving every
  // holder RUNNING. So a daemon restart empties this map WHILE THE SESSIONS KEEP RUNNING, and both
  // rungs below used absence-from-the-map as their liveness test. The result: a session that is
  // genuinely ALIVE in its unit was reported `E_SESSION_NOT_LIVE` — "dead". The old message even
  // said all three things at once ("dead, unknown, or not attached in this daemon"); the CODE
  // could not tell them apart, so the caller could not either.
  //
  // ⚑ WHY THIS IS WORTH REOPENING CERTIFIED CODE: the restart window is EXACTLY the window D83's
  // in-unit holder was ruled to make survivable. The daemon was reporting "not live" about
  // precisely the sessions that ruling exists to preserve — the holder kept its promise and the
  // liveness check broke it.
  //
  // THE DISTINCTION: liveness is a property of the UNIT (the D83 holder + its socket), never of a
  // daemon-local map. So absence from `sessions` asks a question rather than answering one, and
  // `reconnect()` is the thing that ALREADY consults the real oracle: it reads the row, checks
  // `systemctl is-active` on the unit, and checks the holder socket — throwing E_SESSION_NOT_LIVE
  // ONLY when the session is genuinely dead or unknown. Routing the unattached case through it
  // therefore needs NO NEW TYPED CODE (a term mint is owner-gated): the dead case keeps the
  // existing code, and the ALIVE case stops being an error at all.
  //
  // ⚑ RE-ATTACHING RATHER THAN RE-LABELLING IS DELIBERATE. Reporting the live-but-unattached case
  // under some new code would still refuse the caller, leaving D83's surviving session undrivable
  // and the holder's value unrealized. Re-attaching is the RATIFIED behavior — Behavior #7: "the
  // daemon reconnects to the holder's pty socket; the session survives" — applied at the point the
  // code decides instead of only at boot. index.js already runs that pass at boot; this makes a
  // session the boot pass MISSED self-heal on first use (see the surfaced index.js gaps).
  function attachedAndHealthy(entry) {
    return Boolean(entry && entry.bridge && entry.bridgeAlive && entry.bridge.stdin.writable);
  }

  // Resolve the ATTACHED entry for a session, re-attaching if the session is alive but unattached
  // OR mapped to a bridge that has gone dead. Throws the typed E_SESSION_NOT_LIVE (via reconnect)
  // only when the UNIT says genuinely dead.
  function ensureAttached(execId) {
    const existing = sessions.get(execId);
    if (existing && attachedAndHealthy(existing)) return existing;
    // NOT ATTACHED, or mapped to a DEAD bridge over a still-live unit — NEITHER is dead. Ask the
    // unit, not the map: a present-but-unhealthy map entry must not short-circuit the re-attach
    // (that was the bug — a stale entry blocked this path forever, needing a daemon restart to
    // clear). reconnect() itself disposes of any stale bridge before installing the fresh one.
    // reconnect() throws the typed E_SESSION_NOT_LIVE if the row/unit/socket say the session is
    // genuinely gone: never a hang (Behavior #11), and never a lie about a live one.
    reconnect(execId);
    const entry = sessions.get(execId);
    if (!entry) {
      // reconnect() resolved without registering an entry — a wiring fault, not a sender error.
      throw new SpawnError(E_PTY_BRIDGE, `re-attached session ${execId} but no bridge entry was registered`, { execId });
    }
    return entry;
  }

  // POST /keys/:id — write keystroke bytes into the live session's pty (the keystroke rung, CMP-9).
  // A dead/nonexistent session yields a TYPED error, never a hang (Behavior #11).
  function sendKeys(execId, data) {
    // D96: absence from the map means UNATTACHED, so ask the unit before calling anything dead.
    // A session alive in its holder is re-attached here and the keystrokes land. Always route
    // through ensureAttached (never take the map entry directly) so a mapped-but-DEAD bridge is
    // also health-checked and re-attached, not just a map-absent one (task 7.17).
    const entry = ensureAttached(execId);
    if (!attachedAndHealthy(entry)) {
      throw new SpawnError(E_SESSION_NOT_LIVE, `no live headed pty for session ${execId} (dead, unknown, or not attached in this daemon)`, { execId });
    }
    entry.bridge.stdin.write(Buffer.isBuffer(data) ? data : Buffer.from(String(data), 'utf8'));
    return { execId, wrote: Buffer.byteLength(data) };
  }

  // Screen capture — the current rendered screen from the server-side vt model (Behavior #3).
  function captureScreen(execId) {
    // D96: same distinction. `repainting` reports that this vt has not yet taken a byte — after a
    // lazy re-attach the `-r winch` repaint is still in flight, so the render is blank/partial.
    // Behavior #7 allows a momentarily stale first capture but forbids a SILENTLY blank one, so
    // the state is reported rather than passed off as an empty screen. Always route through
    // ensureAttached (task 7.17 — same reasoning as sendKeys above).
    const entry = ensureAttached(execId);
    return {
      execId, sessionId: entry.sessionId, rows: entry.vt.rows, cols: entry.vt.cols,
      screen: entry.vt.render(), repainting: !entry.painted,
    };
  }

  // Reconnect to a session that survived a daemon restart (Behavior #7): the holder + pty live in
  // the unit; re-attach the bridge and the vt model repaints on attach (dtach -r winch). Sources
  // the row from the store; refuses if the unit is not alive.
  function reconnect(execId, { rows = DEFAULT_ROWS, cols = DEFAULT_COLS } = {}) {
    const row = heartStore.getExecution(execId);
    if (!row || !row.session_id) throw new SpawnError(E_SESSION_NOT_LIVE, `no session row to reconnect: ${execId}`, { execId });
    if (row.unit_name) {
      const info = systemdStatus(row.unit_name, userManager);
      if (!info.active) throw new SpawnError(E_SESSION_NOT_LIVE, `unit ${row.unit_name} is not active; nothing to reconnect`, { execId });
    }
    const sock = sockPathFor(row.session_id);
    if (!fs.existsSync(sock)) throw new SpawnError(E_SESSION_NOT_LIVE, `holder socket ${sock} absent; session did not survive`, { execId });
    const transcriptLog = transcriptLogFor(row.session_id);
    const existing = sessions.get(execId);
    if (existing && existing.bridge) { try { existing.bridge.kill('SIGKILL'); } catch { /* replacing */ } }
    const entry = {
      execId, sessionId: row.session_id, unitName: row.unit_name, sock,
      statusFile: path.join(row.workdir || '', '.ignite-headed-exit.json'), workdir: row.workdir,
      logPath: transcriptLog, carriage: null,
      vt: new VtModel({ rows, cols }),
      logStream: fs.createWriteStream(transcriptLog, { flags: 'a', mode: 0o600 }),
      bridge: null, bridgeAlive: false,
      painted: false,   // D96: a fresh vt on re-attach — blank until dtach's `-r winch` repaint lands.
    };
    sessions.set(execId, entry);
    attachBridge(entry, { rows, cols });
    return { execId, reconnected: true, sock };
  }

  // Source the headed row's exit_code (Amendment #5): the TRUE child status from the shim's status
  // file, NEVER the unit's ExecMainStatus (M3 masks it). Returns { exit_code, source } — a typed
  // `unknown` (honest absence) when the status file is missing/unreadable, never a masked 0.
  function sourceExitCode(execId) {
    const entry = sessions.get(execId);
    const row = heartStore.getExecution(execId);
    const statusFile = (entry && entry.statusFile) || (row && row.workdir ? path.join(row.workdir, '.ignite-headed-exit.json') : null);
    if (!statusFile || !fs.existsSync(statusFile)) return { exit_code: 'unknown', source: 'status-file-absent' };
    let raw;
    try { raw = fs.readFileSync(statusFile, 'utf8').trim(); } catch { return { exit_code: 'unknown', source: 'status-file-unreadable' }; }
    if (!raw) return { exit_code: 'unknown', source: 'status-file-empty' };
    try {
      const parsed = JSON.parse(raw);
      if (Number.isInteger(parsed.code)) return { exit_code: parsed.code, source: 'status-shim' };
      if (parsed.signal) return { exit_code: `signal:${parsed.signal}`, source: 'status-shim' };
      return { exit_code: 'unknown', source: 'status-shim-no-code' };
    } catch { return { exit_code: 'unknown', source: 'status-file-malformed' }; }
  }

  // keystroke carriage injection: poll the RENDERED screen for the readiness marker up to the
  // timeout, then inject the prompt text and Enter as SEPARATE writes (the POC's recorded defect).
  // Timeout → typed prompt-injection-timeout failure (Behavior #10), never a silent no-prompt.
  function injectKeystrokePrompt(entry, plan) {
    return new Promise((resolve, reject) => {
      const deadline = Date.now() + plan.timeoutMs;
      const iv = setInterval(() => {
        let screen = '';
        try { screen = entry.vt.render(); } catch { /* not ready */ }
        if (screen.includes(plan.readiness)) {
          clearInterval(iv);
          try {
            sendKeys(entry.execId, plan.prompt);
            setTimeout(() => { try { sendKeys(entry.execId, '\r'); resolve(); } catch (e) { reject(e); } }, 60);
          } catch (e) { reject(e); }
          return;
        }
        if (Date.now() >= deadline) {
          clearInterval(iv);
          reject(new SpawnError(E_PROMPT_INJECTION_TIMEOUT, `keystroke prompt readiness marker '${plan.readiness}' not seen within ${plan.timeoutMs}ms`, { execId: entry.execId }));
        }
      }, 100);
    });
  }

  function listHeaded() {
    return Array.from(sessions.values()).map((e) => ({ execId: e.execId, sessionId: e.sessionId, unitName: e.unitName, bridgeAlive: e.bridgeAlive }));
  }

  // Detach all daemon-side readers WITHOUT ending sessions (holders live in their units). Used on
  // daemon shutdown: closing the bridge's stdin makes pty-bridge.py detach cleanly and the session
  // survives for the next daemon boot to reconnect (Behavior #7).
  function shutdown() {
    for (const entry of sessions.values()) {
      try { if (entry.bridge && entry.bridge.stdin.writable) entry.bridge.stdin.end(); } catch { /* best-effort */ }
      try { if (entry.bridge) entry.bridge.kill('SIGTERM'); } catch { /* best-effort */ }
      try { if (entry.logStream) entry.logStream.end(); } catch { /* best-effort */ }
    }
    sessions.clear();
  }

  return { spawnHeaded, sendKeys, captureScreen, reconnect, sourceExitCode, listHeaded, shutdown, config };
}

module.exports = { createPtyHost };
