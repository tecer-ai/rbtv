'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawn: childSpawn } = require('node:child_process');
const { loadConfig, resolveTemplateSlots, resolveWorkdir, resolveWorkspaceRoot, sessionsRootFor } = require('./config');
const { materializeHarnessConfig, harnessOf } = require('./harness-config');
const { buildBwrapArgv } = require('./bwrap');
const { composeSeatSpawn } = require('./tmux');
const {
  generateSessionId,
  selectCarrier,
  spawnSystemd,
  spawnSetsid,
  systemdStatus,
  setsidStatus,
  killSystemd,
  killSetsid,
  listSystemdUnits,
} = require('./carrier');
const {
  SpawnError,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_MODE,
  E_HEADED_NOT_CAPABLE,
  E_FLAG_INJECTION,
  E_WORKDIR_ESCAPE,
  E_WORKDIR_MISSING,
  E_UNKNOWN_REQUEST_KEY,
  E_SESSION_NOT_FOUND,
  E_CARRIER_FAILED,
  E_ORPHAN_RESCAN_FAILED,
  E_MISSING_KEY,
  E_BAD_REQUEST,
} = require('./errors');

const SESSION_MODES = new Set(['headless', 'headed']);

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function captureSessionRef(profile, launchResult, workdir) {
  const rule = profile.session_ref;
  if (!rule) return null;
  if (rule.source === 'cwd-implicit') return workdir;
  // stdout-json / stdout-json-event require reading the worker's stdout, which is
  // redirected to the log file. For long-running agents the ref arrives later;
  // p2-2 stores null here and the ticker completion path (p3-1) can patch it.
  return null;
}

async function resolvePidStarttime(carrier, pid, unitName) {
  if (carrier === 'systemd' && unitName) {
    // systemctl show ExecMainStartTimestamp is absolute; pid_starttime uses /proc stat field 22.
    // We need a PID to read /proc; systemctl show gives us ExecMainPID.
    const { systemdStatus } = require('./carrier');
    const info = systemdStatus(unitName);
    if (info.pid) {
      const { setsidStatus } = require('./carrier');
      const st = setsidStatus(info.pid);
      return st.pidStarttime || null;
    }
    return null;
  }
  if (carrier === 'setsid' && pid) {
    const { setsidStatus } = require('./carrier');
    const st = setsidStatus(pid);
    return st.pidStarttime || null;
  }
  return null;
}

// Execute a composed tmux argv. The argv is passed as a VECTOR to childSpawn with no shell — the
// same property tmux.js composes for, carried through to the actual exec. `shell: true` here would
// undo the entire reason that module builds a vector (run issue G-11's class); do not add it.
// tmux's `-P -F '#{pane_id} #{pane_pid}'` prints the two handles on stdout.
function runTmux(tmuxArgv) {
  return new Promise((resolve, reject) => {
    const proc = childSpawn(tmuxArgv[0], tmuxArgv.slice(1), { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '';
    let err = '';
    proc.stdout.on('data', (d) => { out += d.toString(); });
    proc.stderr.on('data', (d) => { err += d.toString(); });
    proc.on('error', (e) => reject(new SpawnError(E_CARRIER_FAILED, `tmux spawn error: ${e.message}`, { carrier: 'tmux-scope' })));
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new SpawnError(E_CARRIER_FAILED, `tmux new-window failed (exit ${code}): ${err || out}`, { carrier: 'tmux-scope', exitCode: code }));
        return;
      }
      const [paneId, panePidRaw] = out.trim().split(/\s+/);
      const panePid = Number.parseInt(panePidRaw, 10);
      resolve({ paneId: paneId || null, panePid: Number.isFinite(panePid) ? panePid : null });
    });
  });
}

function validateRequestKeys(req) {
  const known = new Set(['profile', 'session_mode', 'prompt', 'workdir']);
  for (const key of Object.keys(req)) {
    if (!known.has(key)) {
      throw new SpawnError(E_UNKNOWN_REQUEST_KEY, `unknown request key: ${key}`, { key });
    }
  }
}

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

function ensurePromptFile(dataRoot, sessionId, prompt) {
  const promptDir = path.join(dataRoot, 'prompts');
  fs.mkdirSync(promptDir, { recursive: true, mode: 0o700 });
  const promptPath = path.join(promptDir, `${sessionId}.txt`);
  fs.writeFileSync(promptPath, prompt ?? '', { mode: 0o600 });
  return promptPath;
}

// Resolve template slots across the WHOLE sandbox block rather than one named directive.
// systemd's sandbox vocabulary is path-heavy (ReadWritePaths=, ReadOnlyPaths=, BindPaths=,
// InaccessiblePaths=, ...); resolving only the directive today's profiles happen to use would
// leave the next one added silently carrying a literal `{workdir}` into the unit — the same
// defect, one directive over. Values are resolved by SHAPE, not by name: strings and
// string-arrays go through slot resolution, everything else (booleans like PrivateTmp,
// numbers) passes through untouched. A slot with no value throws E_MISSING_KEY from
// resolveTemplateSlots — the spawn fails loudly rather than emitting a literal `{slot}`.
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

function composeArgv(profile, mode, sessionId, workdir, prompt, dataRoot) {
  const isHeaded = mode === 'headed';
  const block = isHeaded ? profile.headed.tui : profile.exec;
  const promptCarriage = block.prompt;

  let stdinFile = null;
  if (promptCarriage === 'stdin') {
    // stdin carriage: the prompt rides a file the CARRIER connects as the worker's stdin
    // (StandardInput=file: on systemd; the file's fd on setsid) — bytes then EOF at end-of-file,
    // the "server writes the prompt, then closes stdin" contract. The path never appears in argv
    // (no {prompt_file} slot), and bwrap needs no bind: fd 0 is opened before the wrap execs.
    // Headed blocks can never reach here — config.js rejects `headed.tui.prompt: stdin` at load.
    stdinFile = ensurePromptFile(dataRoot, sessionId, prompt);
  }
  // The former `file` and `argv-last` branches are DELETED (task 7.23): task 7.14 (batch-08
  // item 4 half A) narrowed the loadable headless vocabulary to `stdin` only
  // (KNOWN_PROMPT_VALUES, config.js), making both branches unreachable from any loadable
  // config. Headed `file` carriage is owned end-to-end by the pty host (composeHeadedArgv,
  // pty/carriage.js) — it never routes through here.

  const argv = resolveTemplateSlots(block.argv, { workdir });

  return { argv, stdinFile, promptCarriage };
}

function ensureLogPath(dataRoot, sessionId) {
  const logDir = path.join(dataRoot, 'logs');
  fs.mkdirSync(logDir, { recursive: true, mode: 0o700 });
  const logPath = path.join(logDir, `${sessionId}.log`);
  // Task 7.13 piece 4 (settles D97): pre-create the transcript 0600 BEFORE the carrier opens
  // it — systemd's `StandardOutput=append:` creates a missing file at the manager's default
  // mode (664 observed live), leaving a secret-bearing transcript world-readable while its
  // audit neighbour sits at 0600. An existing file keeps its mode, so this pre-create wins.
  // appendFileSync (not writeFileSync): never truncate an existing transcript.
  fs.appendFileSync(logPath, '', { mode: 0o600 });
  return logPath;
}

// THE one derivation of a session's exit-marker path (the file the carrier's post-exit hook
// writes the real exit status to, and the ticker's sweep reads back). The ticker imports this
// rather than re-deriving the path (D44 discipline applied to a filesystem contract).
function exitFilePath(dataRoot, sessionId) {
  return path.join(dataRoot, 'exits', `${sessionId}.exit`);
}

function ensureExitFile(dataRoot, sessionId) {
  const exitDir = path.join(dataRoot, 'exits');
  fs.mkdirSync(exitDir, { recursive: true, mode: 0o700 });
  return exitFilePath(dataRoot, sessionId);
}

function createSpawnManager({ heartStore, configPath, logger = null, userManager = true }) {
  const config = loadConfig(configPath);
  const dataRoot = config.spawn.data_root;
  if (!dataRoot) {
    throw new SpawnError(E_MISSING_KEY, 'spawn.data_root is required', { key: 'spawn.data_root' });
  }

  // D58(1): the default (ticker) launch branch materializes `<workspaceRoot>/.rbtv/sessions/<exec-id>/`.
  // The sessions root is derived once, from the heart store's own `.rbtv/` location (guaranteeing the
  // session dir is a SIBLING of `.rbtv/heart/`, never a parent of it — D58(3)). index.js is frozen for
  // this task and does not pass the workspace root, so the module sources it here the same way.
  const workspaceRoot = resolveWorkspaceRoot(heartStore && heartStore.dbPath);
  const sessionsRoot = sessionsRootFor(workspaceRoot);

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  async function spawn(execId, profileName, sessionMode = 'headless', prompt = null, workdir = null, enqueuedBy = 'unknown') {
    // Strict request-key validation for object-style callers (gateway path).
    validateRequestKeys({ profile: profileName, session_mode: sessionMode, prompt, workdir });

    rejectFlagInjection(workdir, 'workdir');

    if (!config.profiles[profileName]) {
      throw new SpawnError(E_UNKNOWN_PROFILE, `unknown launch profile: ${profileName}`, { profile: profileName });
    }
    const profile = config.profiles[profileName];

    if (!SESSION_MODES.has(sessionMode)) {
      throw new SpawnError(E_UNKNOWN_MODE, `invalid session_mode: ${sessionMode}`, { sessionMode });
    }
    if (sessionMode === 'headed' && !profile.headed) {
      throw new SpawnError(E_HEADED_NOT_CAPABLE, `profile ${profileName} is not headed-capable`, { profile: profileName, sessionMode });
    }

    // NO prompt flag-injection guard: the carriage collapse (batch-08 item 4 half A — headless
    // `stdin` only, headed `file`|`keystroke` only) means NO carriage puts caller text on a
    // command line, so there is nothing for a prompt guard to protect. The prompt is 0600-file
    // DATA everywhere (a composed multi-turn transcript legitimately carries newlines and
    // parentheses). The workdir guard above stays UNCONDITIONAL: a workdir always rides
    // argv/unit properties.

    const resolvedWorkdir = resolveWorkdir(profile, workdir, config.default_workdir_root, configPath, { execId, sessionsRoot, workspaceRoot });

    // D58(4): materialize the advisory harness-local write-restraint config into the launch dir.
    // The kernel sandbox (resolveSandbox below) is the LOAD-BEARING layer; this is the second belt.
    const resolvedSandbox = resolveSandbox(profile.sandbox, resolvedWorkdir);
    const editablePaths = (() => {
      const rwp = resolvedSandbox && resolvedSandbox.ReadWritePaths;
      if (!rwp) return [];
      return (Array.isArray(rwp) ? rwp : [rwp]).filter((p) => p && p !== resolvedWorkdir);
    })();
    try {
      const hc = materializeHarnessConfig({ sessionDir: resolvedWorkdir, profile, editablePaths });
      if (hc && hc.written) log('info', 'harness config materialized', { harness: hc.harness, path: hc.written, enforceable: hc.enforceable });
    } catch (err) {
      log('warn', 'harness config materialization failed (advisory layer; kernel sandbox is authoritative)', { error: err.message });
    }

    const sessionId = generateSessionId();
    const logPath = ensureLogPath(dataRoot, sessionId);
    const { argv, stdinFile } = composeArgv(profile, sessionMode, sessionId, resolvedWorkdir, prompt, dataRoot);

    // D59: bwrap FS walls nested inside the systemd-run --user unit. The wrapped argv rides the
    // carrier opaquely (both systemd and setsid branches); the walls live in argv, not config.
    // No promptFile bind: the sole headless carriage is stdin (fd 0 opens before the wrap execs);
    // headed prompt files are bound by the pty host's own buildBwrapArgv call.
    const maskPaths = config.auth?.senders_file ? [path.dirname(config.auth.senders_file)] : [];
    const wrappedArgv = buildBwrapArgv({ argv, workdir: resolvedWorkdir, editablePaths, harness: harnessOf(profile), maskPaths });

    const carrier = selectCarrier(config.spawn.carrier, userManager);

    // Write the session_id and log_path immediately so the row is identifiable
    // even if the carrier launch fails part-way.
    heartStore.updateExecutionStatus(execId, {
      status: 'launching',
      sessionId,
      logPath,
    });

    const common = { sessionId, argv: wrappedArgv, workdir: resolvedWorkdir, logPath, stdinFile, exitFile: ensureExitFile(dataRoot, sessionId), caps: profile.caps, sandbox: resolvedSandbox, envFile: profile.env?.file, userManager };
    let launchResult;
    try {
      if (carrier === 'systemd') {
        launchResult = await spawnSystemd(common, log);
      } else {
        launchResult = await spawnSetsid(common, log);
      }
    } catch (err) {
      heartStore.updateExecutionStatus(execId, {
        status: 'failed',
        endedAt: new Date(),
      });
      throw new SpawnError(E_CARRIER_FAILED, `spawn failed for profile ${profileName}: ${err.message}`, { profile: profileName, execId, cause: err.code });
    }

    const sessionRef = captureSessionRef(profile, launchResult, resolvedWorkdir);
    let pid = launchResult.pid || null;
    const unitName = launchResult.unitName || null;
    if (carrier === 'systemd' && unitName && !pid) {
      const info = systemdStatus(unitName, userManager);
      pid = info.pid || null;
    }
    const pidStarttime = await resolvePidStarttime(carrier, pid, unitName);
    const startedAt = new Date();

    const updated = heartStore.updateExecutionStatus(execId, {
      status: 'running',
      carrier,
      unitName,
      pid,
      pidStarttime,
      sessionRef,
      startedAt,
      logPath,
      sessionId,
      profile: profileName,
      workdir: resolvedWorkdir,
    });

    // Return the fresh row with workdir filled from the original recordExecutionStart value.
    const fresh = heartStore.getExecution(execId);
    if (fresh) fresh.workdir = resolvedWorkdir;
    return fresh;
  }

  // ── Task 7.30 — the SEAT spawn: a headed session landing in a tmux pane (R7/R8/R15/R28) ────
  //
  // The gate does not move: this is still the daemon's own door, reached by profile NAME, and no
  // caller free text reaches argv. What moves is the TARGET — a pane in the goal's run-scoped room
  // instead of a server-owned pty unit. Composition (and the reasons for each layer) lives in
  // ./tmux.js; this function is the daemon-side half: resolve, compose, launch, record identity.
  //
  // R7's division of labour, which is the whole point of "profiles stay pure mechanism":
  //   the PROFILE gives  exec/argv, caps, sandbox binds, session_ref     — mechanism only
  //   the SEAT DESCRIPTOR gives  role, briefing, workdir                 — everything cognitive
  // So the briefing never rides argv. It is a FILE the harness reads from its own launch dir, which
  // is why `seatDir` here becomes the workdir and nothing else.
  //
  // `dryRun: true` composes and returns WITHOUT creating a pane or writing a store row. It exists
  // because composition is the half that is checkable off a live room — the probe uses it, and so
  // does any caller that wants to see the exact argv before it runs.
  async function spawnSeat(execId, profileName, { room, seatName, seatDir, dryRun = false, enqueuedBy = 'unknown' } = {}) {
    if (!config.profiles || !config.profiles[profileName]) {
      throw new SpawnError(E_UNKNOWN_PROFILE, `unknown profile: ${profileName}`, { profile: profileName });
    }
    const profile = config.profiles[profileName];
    if (!seatDir) {
      throw new SpawnError(E_BAD_REQUEST, 'seat spawn requires seatDir — the seat descriptor folder supplies role/briefing/workdir (R7)', { profile: profileName });
    }

    // The workdir gate is REUSED, not relaxed. A seat folder outside the profile's `workdir_root`
    // is refused with E_WORKDIR_ESCAPE — the same containment boundary every other spawn crosses.
    // DISCLOSED, not silently worked around: until task 7.11 redesigns the writable set (owner
    // ruling `r-711-write-bounds` pre-binds it to own seat folder + own worktree + git plumbing),
    // a seat folder living outside that root cannot be spawned into. That is a need to SURFACE,
    // which is exactly what the ruling's rider asks for — never a boundary to widen here.
    const resolvedWorkdir = resolveWorkdir(profile, seatDir, config.default_workdir_root, configPath, { execId, sessionsRoot, workspaceRoot });

    const resolvedSandbox = resolveSandbox(profile.sandbox, resolvedWorkdir);
    const editablePaths = (() => {
      const rwp = resolvedSandbox && resolvedSandbox.ReadWritePaths;
      if (!rwp) return [];
      return (Array.isArray(rwp) ? rwp : [rwp]).filter((p) => p && p !== resolvedWorkdir);
    })();

    // Headed argv when the profile is headed-capable, else its plain exec argv (R8: one door, the
    // existing mode flag). No prompt carriage: a seat is driven by its descriptor and by the room.
    const harnessArgv = (profile.headed && profile.headed.tui && profile.headed.tui.argv) || profile.exec.argv;
    const sessionId = generateSessionId();
    const maskPaths = config.auth?.senders_file ? [path.dirname(config.auth.senders_file)] : [];

    // Composition FIRST — and this ordering is the fail-closed guarantee, not a style choice.
    // composeSeatSpawn runs buildBwrapArgv before it builds any tmux argv, so on a box without
    // bwrap this throws E_FS_SANDBOX_UNAVAILABLE and NO PANE IS EVER CREATED: the seat is not
    // spawned unconfined, it is not spawned at all (D59, and 7.30's own criterion).
    const composed = composeSeatSpawn({
      room,
      windowName: seatName || profileName,
      sessionId,
      workdir: resolvedWorkdir,
      harnessArgv,
      caps: profile.caps,
      editablePaths,
      harness: harnessOf(profile),
      maskPaths,
      userManager,
    });

    if (dryRun) return { dryRun: true, sessionId, ...composed, workdir: resolvedWorkdir };

    heartStore.updateExecutionStatus(execId, { status: 'launching', sessionId });
    log('info', 'seat spawn', { room, seat: seatName, unit: composed.unitName, argv: composed.tmuxArgv });

    const { paneId, panePid } = await runTmux(composed.tmuxArgv);

    // Identity is recorded as the PAIR the daemon already trusts everywhere else — pid plus
    // /proc stat field 22 starttime — because a pid alone is reusable, and because the pane alone
    // is NOT identity either: an in-place respawn reuses the pane id (run issue G-12). The scope
    // unit name is the third handle, and the only one a respawn cannot reproduce.
    const pidStarttime = panePid ? (setsidStatus(panePid).pidStarttime || null) : null;
    // carrier stays `systemd`, and this is modelling rather than a workaround: the CARRIER — the
    // thing that holds the process and applies the caps — is still systemd, a --scope unit instead
    // of a transient service. What changed is the TARGET (a tmux pane), which is exactly how the
    // settle ledger frames it: "DEC-1 is amended in TARGET, never in gate" (R28). Writing a new
    // carrier value would also fail the heart store's CHECK constraint
    // (carrier IN ('systemd','setsid')) — a CERTIFIED schema whose reopen is owner-gated tonight
    // (`r-746-schema-pregrant`), and not something to widen from here.
    // SURFACED, not buried: the row therefore cannot distinguish a scope-in-a-pane from a
    // transient service, which matters to any liveness/kill path that switches on carrier. Filed
    // as a run issue for task 7.46's schema pass; the unit name + pane id below carry the truth in
    // the meantime.
    heartStore.updateExecutionStatus(execId, {
      status: 'running',
      carrier: 'systemd',
      unitName: composed.unitName,
      pid: panePid,
      pidStarttime,
      startedAt: new Date(),
      sessionId,
      profile: profileName,
      workdir: resolvedWorkdir,
    });

    return { sessionId, paneId, panePid, pidStarttime, unitName: composed.unitName, workdir: resolvedWorkdir, room, seat: seatName };
  }

  async function status(execId) {
    const row = heartStore.getExecution(execId);
    if (!row) throw new SpawnError(E_SESSION_NOT_FOUND, `session not found: ${execId}`, { execId });

    let carrierInfo;
    if (row.carrier === 'systemd' && row.unit_name) {
      carrierInfo = systemdStatus(row.unit_name, userManager);
    } else if (row.carrier === 'setsid' && row.pid) {
      carrierInfo = setsidStatus(row.pid, row.pid_starttime);
    } else {
      carrierInfo = { carrier: row.carrier || null, active: false };
    }

    return {
      execId,
      sessionId: row.session_id,
      profile: row.profile,
      sessionMode: row.session_mode,
      status: row.status,
      workdir: row.workdir,
      carrier: row.carrier,
      unitName: row.unit_name,
      pid: row.pid,
      exitCode: row.exit_code,
      logPath: row.log_path,
      sessionRef: row.session_ref,
      live: carrierInfo.active,
      carrierInfo,
    };
  }

  function logs(execId, { tailBytes = 0, follow = false } = {}) {
    const row = heartStore.getExecution(execId);
    if (!row || !row.log_path) throw new SpawnError(E_SESSION_NOT_FOUND, `no log for session: ${execId}`, { execId });
    if (!fs.existsSync(row.log_path)) return { exists: false, logPath: row.log_path };

    if (follow) {
      const proc = childSpawn('tail', tailBytes > 0 ? ['-c', String(tailBytes), '-f', row.log_path] : ['-f', row.log_path], { stdio: 'inherit' });
      return { exists: true, logPath: row.log_path, following: true, proc };
    }

    const stats = fs.statSync(row.log_path);
    const start = tailBytes > 0 && stats.size > tailBytes ? stats.size - tailBytes : 0;
    const data = fs.readFileSync(row.log_path, { start, encoding: 'utf8' });
    return { exists: true, logPath: row.log_path, data };
  }

  async function kill(execId) {
    const row = heartStore.getExecution(execId);
    if (!row) throw new SpawnError(E_SESSION_NOT_FOUND, `session not found: ${execId}`, { execId });

    let result;
    if (row.carrier === 'systemd' && row.unit_name) {
      result = await killSystemd(row.unit_name, config.spawn.kill_grace_seconds, userManager, log);
    } else if (row.carrier === 'setsid' && row.pid) {
      result = await killSetsid(row.pid, config.spawn.kill_grace_seconds, log);
    } else {
      throw new SpawnError(E_CARRIER_FAILED, `cannot kill session with unknown carrier`, { execId, carrier: row.carrier });
    }

    heartStore.updateExecutionStatus(execId, { status: 'killed', endedAt: new Date() });
    return { execId, killed: result.killed, signal: result.signal };
  }

  function list() {
    const rows = heartStore.dump().jobs_log;
    const anomalies = [];
    try {
      const units = listSystemdUnits('rbtv-worker-', userManager);
      for (const unit of units) {
        const sessionId = unit.unitName.replace(/^rbtv-worker-/, '').replace(/\.service$/, '');
        const match = rows.find((r) => r.session_id === sessionId || r.unit_name === unit.unitName);
        if (!match) {
          anomalies.push({ type: 'row-less-unit', unitName: unit.unitName, sessionId, active: unit.active });
        }
      }
    } catch (err) {
      anomalies.push({ type: 'list-error', error: err.message });
    }
    return { sessions: rows, anomalies };
  }

  async function orphanRescan() {
    const launching = heartStore.listExecutionsByStatus('launching');
    const running = heartStore.listExecutionsByStatus('running');
    const results = { reattached: [], markedFailed: [], rowLessUnits: [], errors: [] };

    for (const row of [...launching, ...running]) {
      try {
        let live = false;
        if (row.carrier === 'systemd' && row.unit_name) {
          live = systemdStatus(row.unit_name, userManager).active;
          if (!live) {
            const info = systemdStatus(row.unit_name, userManager);
            heartStore.updateExecutionStatus(row.exec_id, {
              status: 'failed',
              exitCode: info.exitCode,
              endedAt: new Date(),
            });
            results.markedFailed.push({ execId: row.exec_id, reason: 'unit inactive at boot rescan', carrierInfo: info });
          } else {
            results.reattached.push({ execId: row.exec_id, carrier: 'systemd', unitName: row.unit_name });
          }
        } else if (row.carrier === 'setsid' && row.pid && row.pid_starttime) {
          const info = setsidStatus(row.pid, row.pid_starttime);
          live = info.active && info.pidStarttime === row.pid_starttime;
          if (!live) {
            heartStore.updateExecutionStatus(row.exec_id, {
              status: 'failed',
              endedAt: new Date(),
            });
            results.markedFailed.push({ execId: row.exec_id, reason: 'PID dead or reused at boot rescan' });
          } else {
            results.reattached.push({ execId: row.exec_id, carrier: 'setsid', pid: row.pid });
          }
        } else {
          heartStore.updateExecutionStatus(row.exec_id, { status: 'failed', endedAt: new Date() });
          results.markedFailed.push({ execId: row.exec_id, reason: 'missing carrier metadata' });
        }
      } catch (err) {
        results.errors.push({ execId: row.exec_id, error: err.message });
      }
    }

    try {
      const units = listSystemdUnits('rbtv-worker-', userManager);
      const rows = heartStore.dump().jobs_log;
      for (const unit of units) {
        // list-units reports names WITH the `.service` suffix; stored unit_name has none.
        // Match on the bare unit name and the session_id-derived name to avoid false orphans.
        const bare = unit.unitName.replace(/\.service$/, '');
        const sid = bare.replace(/^rbtv-worker-/, '');
        const match = rows.find((r) => r.unit_name === unit.unitName || r.unit_name === bare || r.session_id === sid);
        if (!match) {
          results.rowLessUnits.push({ unitName: unit.unitName, active: unit.active });
          log('warn', 'row-less rbtv-worker unit found; NOT auto-killed', { unitName: unit.unitName });
        }
      }
    } catch (err) {
      results.errors.push({ error: `unit enumeration failed: ${err.message}` });
      throw new SpawnError(E_ORPHAN_RESCAN_FAILED, `orphan rescan unit enumeration failed: ${err.message}`, { results });
    }

    return results;
  }

  return {
    config,
    spawn,
    spawnSeat,
    status,
    logs,
    kill,
    list,
    orphanRescan,
  };
}

module.exports = { createSpawnManager, validateSpawnRequest, exitFilePath, ensureExitFile };

function validateSpawnRequest(req) {
  if (req === null || typeof req !== 'object' || Array.isArray(req)) {
    throw new SpawnError(E_BAD_REQUEST, 'spawn request must be an object', {});
  }
  validateRequestKeys(req);
}
