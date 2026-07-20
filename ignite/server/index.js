'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { openHeartStore, closeHeartStore, isHeartStoreOpen } = require('./heart/heart-store');
const { createSpawnManager } = require('./spawn/spawn');
const { createTicker } = require('./ticker/ticker');
const { selectCarrier } = require('./spawn/carrier');
const { createInternalApi } = require('./internal-api/dispatch');
const { createPtyHost } = require('./pty');
const { createGateway } = require('../gateway/gateway');
const { loadSendersFile } = require('../gateway/sender-auth');

// Smoke mode is an ARGV flag, never an environment variable: EnvironmentFile= and
// inherited environments can carry an env var into a production boot by accident,
// and a daemon that stops after one tick would exit 0 — which Restart=on-failure
// reads as success, leaving the unit silently dead. ExecStart never passes this flag.
// Smoke mode does NOT bypass the daemon loop; it drives the real loop and the real
// shutdown path, then signals itself (see main()).
const SMOKE_TEST = process.argv.includes('--smoke-test');

// The seed config ships this placeholder for the D22-required default_workdir_root
// (never a hardcoded instance path, D9/D26(3)). It must be substituted per instance.
const WORKDIR_ROOT_PLACEHOLDER = '/path/set-at-setup';

// One config file feeds two modules with different root-key vocabularies. spawn/config.js
// validates against a STRICT root-key allowlist (bind, auth, spawn, profiles,
// default_workdir_root) and THROWS on any other root key. These namespaces belong to the
// daemon (ticker tunables) and the heart store (tools/workflows catalogues), so spawn must
// never be handed them — otherwise the first operator to configure a ticker cadence, a
// tool, or a workflow kills the daemon at boot with a spawn config error.
const DAEMON_ONLY_ROOT_KEYS = ['ticker', 'tools', 'workflows', 'network'];

// ── p5-2 network posture (network-posture-spec.md) ──────────────────────────
//
// The fail-closed bind guard's typed error. OWNER-APPROVED name (D77(C), D23 mint,
// D66(B) `E_QUEUE_ROW_NOT_FOUND` precedent) — use exactly this string.
const E_BIND_FORBIDDEN = 'E_BIND_FORBIDDEN';

// The standing-warning kind raised when the tailnet bind cannot be established within
// the retry budget (Design 2, rule 3). ⚑ NEW term, NOT yet registered in the canonical
// kind registry (server/heart/warnings.js WARNING_KINDS) — that file is OUTSIDE 5.2's
// allowlist. Surfaced correctly by `ignite status` regardless (inspect daemon lists ALL
// standing warnings by kind). See the dispatch return's concerns: term ratification +
// registry registration are a task-7.5 follow-up, the E_BIND_FORBIDDEN-class pattern.
const TAILNET_BIND_DEGRADED = 'tailnet-bind-degraded';
const TAILNET_WARNING_SUBJECT = 'gateway-tailnet-bind';

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function log(level, message, extra = {}) {
  const line = JSON.stringify({ ts: isoNow(), level, message, ...extra });
  console.log(line);
}

function resolveIgniteSrc() {
  return process.env.RBTV_IGNITE_SRC || path.resolve(__dirname, '..');
}

// The workspace is the folder that roots `.rbtv/` (module CLAUDE.md). It is NEVER the
// ignite source tree: D26(3) and the repo's ignite rule 3 forbid instance files inside
// the code. cwd is a convenience default for dev runs, so a run started from inside
// {ignite-src} would otherwise silently write .rbtv/modules/ignite/* into the repo.
function resolveWorkspaceRoot(igniteSrc) {
  const workspaceRoot = path.resolve(process.env.RBTV_IGNITE_WORKSPACE_ROOT || process.cwd());
  const src = path.resolve(igniteSrc);
  if (workspaceRoot === src || workspaceRoot.startsWith(src + path.sep)) {
    throw new Error(
      `workspace root must not live inside the ignite source tree (D26(3): no instance files inside the code). ` +
      `Resolved workspaceRoot=${workspaceRoot} is inside igniteSrc=${src}. ` +
      `Set RBTV_IGNITE_WORKSPACE_ROOT to the workspace that roots .rbtv/, or run from that workspace.`
    );
  }
  return workspaceRoot;
}

function resolveConfigPath(igniteSrc) {
  return process.env.RBTV_IGNITE_CONFIG_PATH || path.join(igniteSrc, 'config', 'spawn-profiles.yaml');
}

// The named-sender registry's path. The LIVE file is deployed OUTSIDE the repo
// (D27: credentials never in git), so this resolves from config with an env override
// for the unit's EnvironmentFile — never a literal path in code (D26(3)).
function resolveSendersFilePath(mergedConfig) {
  return process.env.RBTV_IGNITE_SENDERS_FILE || (mergedConfig.auth && mergedConfig.auth.senders_file) || null;
}

// Selects `systemd-run --user` vs `--system` for worker carriage. Defaults to true, which
// D46 settles as CORRECT rather than a downgrade: ignite runs as a systemd USER unit with
// lingering, so the user manager is the carrier and no root is in the deploy path. It stays
// reachable from the unit's EnvironmentFile for the operator who must override it, and
// setting it false trips the boot-time degradation warning below — an unprivileged daemon
// cannot drive the SYSTEM manager, so `--system` carriage means no containment in practice.
function resolveUserManager() {
  const raw = process.env.RBTV_IGNITE_USER_MANAGER;
  if (raw === undefined || raw === '') return true;
  return raw === '1' || raw.toLowerCase() === 'true';
}

function ensureDir(p, mode = 0o700) {
  fs.mkdirSync(p, { recursive: true, mode });
}

// A raw EACCES from mkdirSync names no cause and no remedy. The daemon runs unprivileged as
// the user owning the systemd user manager (D46 — the unit carries no User=; it runs as its
// owning user by construction), so an unprovisioned root is the expected first-boot failure:
// report which configured root failed and how to supply it.
function ensureConfiguredDir(dirPath, label, envVar) {
  try {
    ensureDir(dirPath);
  } catch (err) {
    throw new Error(
      `cannot create ${label} at ${dirPath}: ${err.message}. ` +
      `Point ${envVar} at a path this user owns (via the unit's EnvironmentFile), ` +
      `or have the unit pre-provision it (systemd StateDirectory=).`
    );
  }
}

function ensureInstallState(workspaceRoot) {
  const moduleDir = path.join(workspaceRoot, '.rbtv', 'modules', 'ignite');
  ensureDir(moduleDir);

  const statusPath = path.join(moduleDir, 'status.json');
  if (!fs.existsSync(statusPath)) {
    fs.writeFileSync(statusPath, JSON.stringify({
      installed: false,
      version: '0.1.0',
      first_run_at: isoNow(),
    }, null, 2));
  }

  // server.json is a MACHINE-KEYED MAP (batch-08 item 10 state-layout boundary,
  // owner-ruled 2026-07-20): the file is git-tracked so the installation travels to
  // every machine, so a single flat endpoint/state-root value would be right on one
  // machine and wrong on every other. Each machine's install — its endpoint fields
  // and its per-machine state-root path — lives under `machines[<hostname>]`.
  const serverPath = path.join(moduleDir, 'server.json');
  if (!fs.existsSync(serverPath)) {
    fs.writeFileSync(serverPath, JSON.stringify({
      name: null,
      machines: {},
    }, null, 2));
  }

  const settingsPath = path.join(moduleDir, 'settings.json');
  if (!fs.existsSync(settingsPath)) {
    fs.writeFileSync(settingsPath, JSON.stringify({}, null, 2));
  }

  const historyPath = path.join(moduleDir, 'settings-history.jsonl');
  if (!fs.existsSync(historyPath)) {
    fs.writeFileSync(historyPath, '');
  }

  return { moduleDir, statusPath, serverPath, settingsPath, historyPath };
}

// "Installed" = the endpoint record names at least one machine running a server.
// Accepts BOTH shapes: the machine-keyed map (`machines[<hostname>]` entries — the
// current shape, batch-08 item 10) and the legacy flat record (fields at top level),
// so a workspace pulled at either side of the shape change still validates.
function isServerJsonValid(serverJsonPath) {
  try {
    const data = JSON.parse(fs.readFileSync(serverJsonPath, 'utf8'));
    if (!data || typeof data !== 'object') return false;
    const entries = (data.machines && typeof data.machines === 'object')
      ? Object.values(data.machines)
      : [data];
    return entries.some((e) => e && typeof e === 'object' && typeof e.tailnet_host === 'string' && e.tailnet_host.length > 0);
  } catch {
    return false;
  }
}

function loadMergedConfig(configPath) {
  const raw = fs.readFileSync(configPath, 'utf8');
  const cfg = yaml.load(raw);

  if (process.env.RBTV_IGNITE_DATA_ROOT) {
    cfg.spawn = cfg.spawn || {};
    cfg.spawn.data_root = process.env.RBTV_IGNITE_DATA_ROOT;
  }
  if (process.env.RBTV_IGNITE_CARRIER) {
    cfg.spawn = cfg.spawn || {};
    cfg.spawn.carrier = process.env.RBTV_IGNITE_CARRIER;
  }
  if (process.env.RBTV_IGNITE_WORKDIR_ROOT) {
    cfg.default_workdir_root = process.env.RBTV_IGNITE_WORKDIR_ROOT;
  }

  return cfg;
}

function materializeEffectiveConfig(configPath, dataRoot, workspaceRoot) {
  const cfg = loadMergedConfig(configPath);

  const hasEnvOverrides = Boolean(
    process.env.RBTV_IGNITE_DATA_ROOT ||
    process.env.RBTV_IGNITE_CARRIER ||
    process.env.RBTV_IGNITE_WORKDIR_ROOT
  );
  const daemonOnlyKeys = DAEMON_ONLY_ROOT_KEYS.filter((key) => cfg[key] !== undefined);

  // Nothing to rewrite: no env override to fold in and no daemon-only key for spawn to
  // choke on, so spawn can read the config file as committed.
  if (!hasEnvOverrides && daemonOnlyKeys.length === 0) {
    return { effectiveConfigPath: configPath, mergedConfig: cfg, tempConfigDir: null, daemonOnlyKeys };
  }
  // Keep runtime-only config material inside the configured data root so no
  // ephemeral file lands in arbitrary temp directories outside the workspace.
  // With no data root configured, fall back to the workspace's `.rbtv/` runtime
  // root — runtime material belongs under the runtime root, never loose at the
  // workspace root. resolveWorkspaceRoot() guarantees this is outside {ignite-src}.
  const tempConfigDir = path.join(dataRoot || path.join(workspaceRoot, '.rbtv'), '.runtime-config');
  ensureDir(tempConfigDir);
  const effectiveConfigPath = path.join(tempConfigDir, 'spawn-profiles.yaml');

  // The daemon keeps the FULL merged config (it owns the ticker/tools/workflows blocks);
  // spawn receives a copy carrying only the root keys its allowlist accepts.
  const spawnConfig = { ...cfg };
  for (const key of daemonOnlyKeys) delete spawnConfig[key];
  fs.writeFileSync(effectiveConfigPath, yaml.dump(spawnConfig));

  return { effectiveConfigPath, mergedConfig: cfg, tempConfigDir, daemonOnlyKeys };
}

function cleanupTempConfig(tempConfigDir) {
  if (!tempConfigDir) return;
  try {
    fs.rmSync(tempConfigDir, { recursive: true, force: true });
  } catch (err) {
    log('warn', 'failed to remove temp config dir', { tempConfigDir, error: err.message });
  }
}

// Classify a bind host by ADDRESS CLASS, never by port (peerapi ports are ephemeral and
// MOVE across restarts — network-posture-spec.md Edge Cases). Only literal IP addresses
// are classifiable: a hostname (`localhost`, a MagicDNS name) is refused, because the
// guard cannot prove where a name resolves and fail-closed forbids a public bind.
function isLoopbackAddress(host) {
  const kind = net.isIP(host);
  if (kind === 4) return host.startsWith('127.');
  if (kind === 6) return host === '::1' || host === '0:0:0:0:0:0:0:1';
  return false;
}

// Is this IP within Tailscale's OWN address space? IPv4 CGNAT 100.64.0.0/10 (Tailscale's
// pool) or the tailnet ULA prefix fd7a:115c:a1e0::/48. This is the intrinsic ADDRESS-CLASS
// test the guard needs: `tailnetAddrs` is populated partly from RBTV_IGNITE_TAILNET_ADDR,
// an env var any operator/unit file can set — so membership in that list is NOT by itself
// proof of a tailnet address (an override of `0.0.0.0` or a public IP would otherwise
// classify as `tailnet` and defeat the guard). Fail-closed: anything not provably in-range
// is not tailnet.
function isTailscaleAddress(host) {
  const kind = net.isIP(host);
  if (kind === 4) {
    const o = host.split('.').map((n) => Number(n));
    // 100.64.0.0/10 → first octet 100, second octet 64–127.
    return o[0] === 100 && o[1] >= 64 && o[1] <= 127;
  }
  if (kind === 6) {
    // Tailscale ULA fd7a:115c:a1e0::/48 — the first three hextets are fixed. Tailscale
    // always spells the /48 prefix out, so a group-wise prefix match is exact.
    const groups = host.toLowerCase().split(':');
    return groups[0] === 'fd7a' && groups[1] === '115c' && groups[2] === 'a1e0';
  }
  return false;
}

function classifyBindHost(host, tailnetAddrs) {
  if (isLoopbackAddress(host)) return 'loopback';
  // BOTH conditions: the address must be one this node actually resolved AND fall within
  // Tailscale's address space. The range test is what makes the guard's notion of "tailnet"
  // independent of the env-supplied list — an out-of-range override never passes.
  if (tailnetAddrs.includes(host) && isTailscaleAddress(host)) return 'tailnet';
  return 'public';
}

// THE bind guard (Design 2, fail-closed). Permits a host ONLY if it is a loopback address
// OR one of this node's LIVE tailnet addresses. Anything else — `0.0.0.0`, `::`, a public
// interface, a bare hostname — throws E_BIND_FORBIDDEN and the daemon refuses to start.
// No override flag, no env escape, no "warn and continue". Runs BEFORE any socket opens.
function assertBindPermitted(host, tailnetAddrs) {
  const cls = classifyBindHost(host, tailnetAddrs);
  if (cls === 'public') {
    const err = new Error(
      `E_BIND_FORBIDDEN: refusing to bind ${host} — not a loopback address and not one of ` +
      `this node's live tailnet addresses [${tailnetAddrs.join(', ') || 'none resolved'}]. ` +
      `The daemon exposes NO public listener (DEC-3; network-posture-spec.md Design 2). ` +
      `There is no override.`
    );
    err.code = E_BIND_FORBIDDEN;
    throw err;
  }
  return cls;
}

// Resolve this node's tailnet addresses at RUNTIME (Design 1, rule 3 — never hardcoded in
// repo config; machine-agnostic per D9/D26(3)). Sources, in order:
//   RBTV_IGNITE_TAILNET_ADDR set to `none`  → [] (probe knob: force the unresolvable path,
//                                                 spec criterion 9)
//   RBTV_IGNITE_TAILNET_ADDR set to an IP   → [that IP] (explicit runtime override)
//   unset                                    → tailscaled's own report (`tailscale status
//                                                 --json` → Self.TailscaleIPs)
function resolveTailnetAddresses() {
  const override = process.env.RBTV_IGNITE_TAILNET_ADDR;
  if (override !== undefined && override !== '') {
    return override === 'none' ? [] : [override];
  }
  try {
    const out = execFileSync('tailscale', ['status', '--json'], { encoding: 'utf8', timeout: 5000 });
    const data = JSON.parse(out);
    const ips = (data && data.Self && data.Self.TailscaleIPs) || [];
    return Array.isArray(ips) ? ips.filter((ip) => net.isIP(ip)) : [];
  } catch {
    return [];
  }
}

// Best-effort MagicDNS name for the endpoint record — resolved from tailscaled independently
// of the address source, so an explicit address override (Design 1, rule 3) still yields a
// complete record when tailscaled is up. Returns null (never throws) when unavailable.
function resolveTailnetHostname() {
  try {
    const out = execFileSync('tailscale', ['status', '--json'], { encoding: 'utf8', timeout: 5000 });
    const data = JSON.parse(out);
    const dns = data && data.Self && data.Self.DNSName;
    return typeof dns === 'string' && dns.length ? dns.replace(/\.$/, '') : null;
  } catch {
    return null;
  }
}

// Materialize the D27 endpoint record's RUNTIME-resolvable fields into server.json,
// MERGING — owner-config fields (name, ssh_*) are never clobbered. server.json is the
// COMMITTED endpoint record (module CLAUDE.md § Installation model): it is meant to carry
// the tailnet host/IP + gateway port so a `git pull` on another machine finds this server.
// Writes THIS machine's install into `machines[<hostname>]` (batch-08 item 10:
// server.json is a machine-keyed map — see ensureInstallState). Merge, never clobber:
// other machines' entries and unrelated fields survive. A legacy flat record described
// the daemon's own machine, so its endpoint fields are folded into this machine's
// entry and dropped from the top level.
function updateEndpointRecord(serverPath, { tailnetHost, tailnetIp, gatewayPort, stateRoot }) {
  let record;
  try {
    record = JSON.parse(fs.readFileSync(serverPath, 'utf8'));
  } catch {
    record = {};
  }
  if (!record || typeof record !== 'object' || Array.isArray(record)) record = {};
  const next = { ...record };
  if (!next.machines || typeof next.machines !== 'object') next.machines = {};
  const legacy = {};
  for (const f of ['tailnet_host', 'tailnet_ip', 'gateway_port', 'ssh_host', 'ssh_user', 'ssh_port']) {
    if (next[f] !== undefined) {
      if (next[f] !== null) legacy[f] = next[f];
      delete next[f];
    }
  }
  const key = os.hostname();
  const entry = { ...legacy, ...(next.machines[key] || {}) };
  if (tailnetHost) entry.tailnet_host = tailnetHost;
  if (tailnetIp) entry.tailnet_ip = tailnetIp;
  if (Number.isInteger(gatewayPort)) entry.gateway_port = gatewayPort;
  if (stateRoot) entry.state_root = path.resolve(stateRoot);
  next.machines[key] = entry;
  fs.writeFileSync(serverPath, JSON.stringify(next, null, 2));
  return entry;
}

async function main() {
  const igniteSrc = resolveIgniteSrc();
  const workspaceRoot = resolveWorkspaceRoot(igniteSrc);
  log('info', 'ignite daemon starting', { igniteSrc, workspaceRoot, pid: process.pid, smokeTest: SMOKE_TEST });

  const installState = ensureInstallState(workspaceRoot);
  const installed = isServerJsonValid(installState.serverPath);
  log('info', 'install state ready', { moduleDir: installState.moduleDir, installed });

  const configPath = resolveConfigPath(igniteSrc);
  log('info', 'loading config', { configPath });

  const dataRoot = (() => {
    const cfg = loadMergedConfig(configPath);
    return process.env.RBTV_IGNITE_DATA_ROOT || cfg.spawn?.data_root || null;
  })();

  const { effectiveConfigPath, mergedConfig, tempConfigDir, daemonOnlyKeys } =
    materializeEffectiveConfig(configPath, dataRoot, workspaceRoot);
  if (effectiveConfigPath !== configPath) {
    log('info', 'runtime config overrides materialized', { effectiveConfigPath, daemonOnlyKeys });
  }

  // The seed placeholder is not a directory to create: mkdir'ing it either fails with a
  // bare EACCES or (where writable) silently manufactures a bogus root and boots the
  // daemon on a nonsense workdir. D22 requires a real per-instance value — fail fast.
  if (mergedConfig.default_workdir_root === WORKDIR_ROOT_PLACEHOLDER) {
    throw new Error(
      `default_workdir_root is still the seed placeholder ${WORKDIR_ROOT_PLACEHOLDER}; ` +
      `D22 requires it be set per instance. Set RBTV_IGNITE_WORKDIR_ROOT via the unit's ` +
      `EnvironmentFile (never by editing config/spawn-profiles.yaml in the repo — that ` +
      `would write an instance path into the code tree, violating D26(3)).`
    );
  }

  if (dataRoot) ensureConfiguredDir(dataRoot, 'spawn.data_root', 'RBTV_IGNITE_DATA_ROOT');
  if (mergedConfig.default_workdir_root) {
    ensureConfiguredDir(mergedConfig.default_workdir_root, 'default_workdir_root', 'RBTV_IGNITE_WORKDIR_ROOT');
  }

  // ── The sender-registry STARTUP GATE (spawn-profiles-spec.md Design 4) ──────
  //
  // Fires BEFORE the store is opened and before any listener exists: a missing,
  // empty, or group/world-readable senders_file makes the daemon REFUSE TO START,
  // loudly. Fail at boot, never at auth time.
  //
  // ⚑ OPERATOR: this gate is what makes the live senders_file a REQUIRED install
  // step. Until it is deployed (root-owned, 0600, outside the repo), the daemon will
  // not start. See config/senders.example.yaml for the deploy procedure. That is the
  // intended posture, not a defect — a control-plane ingress that cannot authenticate
  // anyone must not be running.
  const sendersFilePath = resolveSendersFilePath(mergedConfig);
  loadSendersFile(sendersFilePath);
  log('info', 'sender registry startup gate passed', { sendersFile: sendersFilePath });

  // State-layout boundary (batch-08 item 10, owner-ruled 2026-07-20): the heart store
  // is PER-MACHINE state — membership test "can the user work with this WITHOUT
  // ignite?" cuts through the store (the jobs catalogue is user-authorable, but
  // queue/jobs_log/messages are runtime) and the owner ruled it stays ONE file,
  // per-machine. So it lives at `{data_root}/heart.db`, never under the workspace's
  // `.rbtv/` (its pre-ruling home). Accepted consequence: the jobs catalogue is not
  // readable without the daemon.
  if (!dataRoot) {
    throw new Error(
      'the heart store is per-machine state and requires a configured data root ' +
      '(spawn.data_root or RBTV_IGNITE_DATA_ROOT) — batch-08 item 10 state-layout boundary.'
    );
  }
  const heartStore = openHeartStore({
    dbPath: path.join(dataRoot, 'heart.db'),
    profiles: mergedConfig.profiles || {},
    tools: mergedConfig.tools || {},
    workflows: mergedConfig.workflows || {},
  });

  // Worker containment (profile `caps:` and `sandbox:`) exists ONLY on the systemd carrier.
  // With carrier `auto`, an unreachable user manager silently degrades to setsid and drops
  // every cap and sandbox property — so state the resolved carriage mode at boot and warn
  // loudly when the resolved carrier is NOT the systemd user manager.
  const userManager = resolveUserManager();
  const configuredCarrier = mergedConfig.spawn?.carrier || 'auto';
  const resolvedCarrier = selectCarrier(configuredCarrier, userManager);
  log('info', 'spawn carriage', { configuredCarrier, resolvedCarrier, userManager });
  if (resolvedCarrier !== 'systemd' || !userManager) {
    log('warn', 'carrier degraded: workers will NOT run under systemd --user, so profile caps and sandbox are IGNORED', {
      configuredCarrier,
      resolvedCarrier,
      userManager,
    });
  }

  const spawnManager = createSpawnManager({
    heartStore,
    configPath: effectiveConfigPath,
    logger: (m) => log(m.level || 'info', m.message, m),
    userManager,
  });

  // ── The headed/pty session surface (task 6.2, session-surface-spec.md Design 1–3) ──────────
  //
  // The pty host is an EXTENSION at the existing spawn/kill/log owner: it OWNS only the headed
  // spawn path (the in-unit dtach holder + the vt-model screen capture + POST /keys/:id + the
  // watch-tee), reusing the spawn manager's config + kill/status surface. Headless one-shot stays
  // the DEFAULT and rides the sole-spawn-path UNCHANGED — the decoration below routes ONLY
  // session_mode:headed to the pty host and delegates everything else to spawnManager.spawn.
  // POST /keys/:id and screen capture are the server-core surface (ptyHost methods held here).
  // ⚑ UPDATED at p6-3a: that Batch-6 seam work (Amendment #2) IS now wired — the pty host is
  // threaded to the internal API below, where owner ruling D90's two additive intents
  // (`send-to-session` / `capture-session-screen`) expose it to authenticated senders through
  // the gateway. The daemon remains the SOLE keystroke mediator: no caller touches a pty.
  const ptyHost = createPtyHost({
    heartStore,
    spawnManager,
    dataRoot,
    userManager,
    logger: (m) => log(m.level || 'info', m.message, m),
  });
  const spawnManagerWithPty = {
    ...spawnManager,
    spawn: (execId, profileName, sessionMode = 'headless', prompt = null, workdir = null, enqueuedBy = 'unknown') =>
      sessionMode === 'headed'
        ? ptyHost.spawnHeaded(execId, profileName, prompt, workdir, enqueuedBy)
        : spawnManager.spawn(execId, profileName, sessionMode, prompt, workdir, enqueuedBy),
    // Headed exit_code sourcing (spec Behavior #8 / Design 2 caveat 1 — wired at the p6-2 review):
    // for a DEAD headed session the unit's ExecMainStatus is the HOLDER's exit and MASKS the
    // harness's (M3: child exited 42, unit reported 0) — and the ticker's crash sweep copies
    // status().exitCode onto the row. Without this override the sweep would write the forbidden
    // masked 0. The shim-sourced TRUE status replaces it; a non-integer source (status file
    // absent/malformed, or a signal death) becomes a typed null (honest absence, option ii) —
    // NEVER the masked ExecMainStatus.
    status: async (execId) => {
      const info = await spawnManager.status(execId);
      if (info.sessionMode === 'headed' && !info.live) {
        const src = ptyHost.sourceExitCode(execId);
        info.exitCode = Number.isInteger(src.exit_code) ? src.exit_code : null;
        info.exitCodeSource = src.source;
        // Scrub the carrier readout too: consumers fall back to carrierInfo.exitCode (the ticker
        // crash sweep's `info.exitCode ?? info.carrierInfo?.exitCode` chain), which would
        // re-introduce the masked ExecMainStatus whenever the shim source is a typed unknown.
        if (info.carrierInfo) info.carrierInfo = { ...info.carrierInfo, exitCode: info.exitCode };
      }
      return info;
    },
  };

  // tick_interval_ms is a TICKER-namespaced key (ticker.js DEFAULT_CONFIG). Reading it
  // from the config top level meant an operator's configured cadence was honoured by the
  // ticker's own config but silently ignored by the daemon loop that actually drives it.
  const tickerConfig = mergedConfig.ticker || {};

  // Captured once at boot for `inspect daemon` uptime reporting.
  const daemonStartTime = Date.now();

  const ticker = createTicker({
    heartStore,
    spawnManager: spawnManagerWithPty,
    config: tickerConfig,
    logger: (m) => log(m.level || 'info', m.message, m),
    feedPath: dataRoot ? path.join(dataRoot, 'feed.jsonl') : null,
    logPath: dataRoot ? path.join(dataRoot, 'ticker.log') : null,
  });

  // ── The composition root (internal-api-contract-spec.md § 4) ────────────────
  //
  // 1:1 is enforced BY CONSTRUCTION here, and this is the only place it can be:
  // the per-boot secret is minted now, handed to the server core (which registers
  // it) and to the GATEWAY module constructor — and to nothing else. The dispatch
  // endpoint is never exported globally and the server core accepts no second
  // client registration, so no other holder of the secret exists. Any other module,
  // any test bypass, any future code path calling dispatch() gets AUTH_FAILED.
  //
  // Random per BOOT (not persisted) because v1 is in-process and has nothing to
  // outlive the process. The split's shape is already designed: the same secret,
  // persisted 0600 under the runtime dir, PLUS socket peer credentials.
  const internalSecret = crypto.randomBytes(32).toString('hex');
  const internalApi = createInternalApi({
    heartStore,
    spawnManager: spawnManagerWithPty,
    secret: internalSecret,
    logger: (m) => log(m.level || 'info', m.message, m),
    daemonStartTime,
    daemonConfig: tickerConfig,
    // The pty host is threaded to the internal API so the Batch-6 session-surface intents
    // (`send-to-session` / `capture-session-screen`, owner ruling D90) can reach the headed
    // session they drive. ADDITIVE: the pty host is unchanged, every other intent is unchanged,
    // and the DAEMON — not the caller — stays the sole keystroke mediator and audit point.
    // Their authorization is the D89/D65(B) model, decided in authz.js like every other intent's.
    ptyHost,
  });

  const gateway = createGateway({
    dispatch: internalApi.dispatch,
    internalSecret,
    sendersFilePath,
    logger: (m) => log(m.level || 'info', m.message, m),
  });

  // ── The bind: loopback AND tailnet, never public (network-posture-spec.md) ──
  //
  // Design 1: the daemon binds `127.0.0.1` (always, first, unconditionally) AND this
  // node's tailnet address (when available), and NOTHING else. Loopback stays bound so
  // the SSH-tunnel fallback (`ssh -L <port>:127.0.0.1:<port>`) survives a tailnet outage
  // — the fallback must work exactly when the tailnet does not (Design 1, "Why loopback
  // MUST stay bound"). The env overrides join the RBTV_IGNITE_* family; they let a PROBE
  // bring an ingress up without colliding with the live daemon — never to widen exposure:
  // the guard below binds them too. `bindHost` MUST stay a loopback address (default
  // 127.0.0.1); it is the unconditional loopback listener, not a place to inject a public
  // interface — criterion 8 sets it to 0.0.0.0 to prove the guard refuses.
  const bindHost = process.env.RBTV_IGNITE_BIND_HOST || mergedConfig.bind?.host || '127.0.0.1';
  const bindPort = Number(process.env.RBTV_IGNITE_BIND_PORT || mergedConfig.bind?.port) || 7431;

  const netCfg = mergedConfig.network || {};
  const tailnetRetries = Number(process.env.RBTV_IGNITE_TAILNET_RETRIES ?? netCfg.tailnet_bind_retries ?? 3);
  const tailnetRetryMs = Number(process.env.RBTV_IGNITE_TAILNET_RETRY_MS ?? netCfg.tailnet_bind_retry_ms ?? 1000);

  // GUARD FIRST, bind second. The primary (loopback) host is classified BEFORE any socket
  // opens, so a configured public bind (`0.0.0.0`) makes the daemon refuse to start with
  // NOTHING bound — the fail-closed contract (Design 2; criterion 8).
  const initialTailnet = resolveTailnetAddresses();
  assertBindPermitted(bindHost, initialTailnet);
  await gateway.listen({ hosts: [bindHost], port: bindPort });
  log('info', 'gateway bound loopback', { host: bindHost, port: bindPort });

  // The tailnet bind is ADDITIONAL, attempted with a bounded, config-knobbed retry — each
  // attempt RE-RESOLVES the address, because tailscaled may not have assigned it yet
  // (Design 2, rule 2). On exhaustion the daemon KEEPS RUNNING loopback-only and raises a
  // standing warning; it NEVER exits and NEVER widens to 0.0.0.0 (rule 3).
  const lastTick = heartStore.getLastTick();
  const warnTick = lastTick ? lastTick.tick : 0;
  let tailnetBound = null;
  for (let attempt = 1; attempt <= Math.max(1, tailnetRetries); attempt += 1) {
    const addrs = resolveTailnetAddresses();
    const primary = addrs.find((a) => net.isIP(a) === 4) || addrs[0] || null;
    if (primary && primary === bindHost) {
      // The loopback bind above already opened this exact address (operator pointed the
      // primary bind at the tailnet address). It is bound; do not double-bind it.
      tailnetBound = primary;
      break;
    }
    if (primary) {
      assertBindPermitted(primary, addrs); // classifies as tailnet; a rogue value fails closed
      await gateway.listen({ hosts: [primary], port: bindPort });
      log('info', 'gateway bound tailnet', { host: primary, port: bindPort, attempt });
      tailnetBound = primary;
      break;
    }
    if (attempt < Math.max(1, tailnetRetries)) {
      log('warn', 'tailnet address not yet resolvable, retrying', { attempt, retries: tailnetRetries, retryMs: tailnetRetryMs });
      await new Promise((r) => setTimeout(r, tailnetRetryMs));
    }
  }

  if (tailnetBound) {
    // Self-heal: a prior degraded boot may have left a standing warning; clear it now that
    // the tailnet bind succeeded (uses the existing store API — no warnings.js edit).
    const stale = heartStore.getStandingWarning({ kind: TAILNET_BIND_DEGRADED, subject: TAILNET_WARNING_SUBJECT });
    if (stale) heartStore.clearWarning({ warningId: stale.warning_id, tick: warnTick });
    // D27 endpoint record: materialize the runtime-resolved fields under this
    // machine's key (merge, never clobber) — including the per-machine state root.
    const rec = updateEndpointRecord(installState.serverPath, {
      tailnetHost: resolveTailnetHostname(),
      tailnetIp: tailnetBound,
      gatewayPort: bindPort,
      stateRoot: dataRoot,
    });
    log('info', 'endpoint record updated', { serverPath: installState.serverPath, tailnet_host: rec.tailnet_host, tailnet_ip: rec.tailnet_ip });
  } else {
    // Runs loopback-only. The standing warning is surfaced by `ignite status` (Design 2,
    // rule 3). Runtime re-check is DEFERRED (rule 4 permits deferral) — the warning states
    // that an operator restart is the remedy, loudly, never implied.
    heartStore.raiseWarning({ kind: TAILNET_BIND_DEGRADED, subject: TAILNET_WARNING_SUBJECT, raisedAtTick: warnTick });
    heartStore.recordMessage({
      type: 'note',
      sender: 'daemon',
      thread: 'owner-feed',
      corpus: `warning: gateway is running LOOPBACK-ONLY — this node's tailnet address did not ` +
              `resolve within the bind-retry budget (${tailnetRetries} attempts). The daemon is ` +
              `alive and the SSH-tunnel fallback works; the tailnet path is unavailable until the ` +
              `daemon is restarted with tailscaled up. No public port was opened.`,
      createdAt: isoNow(),
    });
    log('warn', 'tailnet bind unavailable after retries; running loopback-only with a standing warning', {
      retries: tailnetRetries,
      warningKind: TAILNET_BIND_DEGRADED,
      subject: TAILNET_WARNING_SUBJECT,
    });
  }

  log('info', 'daemon composed', {
    heartStoreOpen: isHeartStoreOpen(),
    gatewayBind: tailnetBound ? `${bindHost}:${bindPort} + ${tailnetBound}:${bindPort}` : `${bindHost}:${bindPort} (loopback-only)`,
  });

  // Reconnect any headed sessions that SURVIVED a restart (session-surface-spec.md Behavior #7):
  // the holder + pty live in the transient unit, so a running row whose holder socket still exists
  // is re-attached and its vt model repaints on attach. Best-effort + non-fatal — a session that
  // did not survive is left to the ticker's own crash-sweep, never killed here.
  try {
    const runningHeaded = heartStore.listExecutionsByStatus('running').filter((r) => r.session_mode === 'headed');
    for (const row of runningHeaded) {
      try {
        const res = ptyHost.reconnect(row.exec_id);
        log('info', 'reconnected headed session after restart', { execId: row.exec_id, sock: res.sock });
      } catch (err) {
        log('warn', 'could not reconnect headed session (may not have survived)', { execId: row.exec_id, error: err.message });
      }
    }
  } catch (err) {
    log('warn', 'headed-session reconnect pass failed', { error: err.message });
  }

  const tickResult = await ticker.tick();
  log('info', 'initial tick complete', { tick: tickResult.tick, actionCount: tickResult.actions.length });

  const intervalMs = Number(tickerConfig.tick_interval_ms) || 10000; // ticker.js DEFAULT_CONFIG default
  const timer = setInterval(() => {
    ticker.tick().catch((err) => log('error', 'tick failed', { error: err.message }));
  }, intervalMs);

  function shutdown(signal) {
    return async () => {
      log('info', `received ${signal}, shutting down`);
      clearInterval(timer);
      // Detach the pty readers WITHOUT ending headed sessions: their holders live in their own
      // transient units, so closing the bridges lets each session survive for the next boot to
      // reconnect (session-surface-spec.md Behavior #7). NEVER kills a headed session on shutdown.
      try {
        ptyHost.shutdown();
      } catch (err) {
        log('error', 'error detaching pty host', { error: err.message });
      }
      // Close the ingress FIRST: a request accepted after the store closes would
      // fault on a dead handle instead of being refused cleanly.
      try {
        await gateway.close();
      } catch (err) {
        log('error', 'error closing gateway', { error: err.message });
      }
      cleanupTempConfig(tempConfigDir);
      try {
        if (isHeartStoreOpen()) closeHeartStore();
      } catch (err) {
        log('error', 'error closing heart store', { error: err.message });
      }
      log('info', 'daemon stopped');
      process.exit(0);
    };
  }

  process.on('SIGTERM', shutdown('SIGTERM'));
  process.on('SIGINT', shutdown('SIGINT'));

  // Smoke mode composes and runs the SAME production path above — real loop, real
  // signal handlers, real shutdown — and proves it by driving the real SIGTERM path,
  // rather than returning early through a test-only branch that skips the loop.
  if (SMOKE_TEST) {
    log('info', 'smoke test: initial tick done, exercising real shutdown path');
    process.kill(process.pid, 'SIGTERM');
  }
}

main().catch((err) => {
  log('error', 'daemon failed to start', { error: err.message, stack: err.stack });
  process.exit(1);
});
