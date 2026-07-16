'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const yaml = require('js-yaml');
const { openHeartStore, closeHeartStore, isHeartStoreOpen } = require('./heart/heart-store');
const { createSpawnManager } = require('./spawn/spawn');
const { createTicker } = require('./ticker/ticker');
const { selectCarrier } = require('./spawn/carrier');
const { createInternalApi } = require('./internal-api/dispatch');
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
const DAEMON_ONLY_ROOT_KEYS = ['ticker', 'tools', 'workflows'];

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

  const serverPath = path.join(moduleDir, 'server.json');
  if (!fs.existsSync(serverPath)) {
    fs.writeFileSync(serverPath, JSON.stringify({
      name: null,
      tailnet_host: null,
      tailnet_ip: null,
      gateway_port: null,
      ssh_host: null,
      ssh_user: null,
      ssh_port: null,
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

function isServerJsonValid(serverJsonPath) {
  try {
    const data = JSON.parse(fs.readFileSync(serverJsonPath, 'utf8'));
    return data && typeof data === 'object' && typeof data.tailnet_host === 'string' && data.tailnet_host.length > 0;
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

  const heartStore = openHeartStore({
    runtimeStateRoot: workspaceRoot,
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

  // tick_interval_ms is a TICKER-namespaced key (ticker.js DEFAULT_CONFIG). Reading it
  // from the config top level meant an operator's configured cadence was honoured by the
  // ticker's own config but silently ignored by the daemon loop that actually drives it.
  const tickerConfig = mergedConfig.ticker || {};

  // Captured once at boot for `inspect daemon` uptime reporting.
  const daemonStartTime = Date.now();

  const ticker = createTicker({
    heartStore,
    spawnManager,
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
    spawnManager,
    secret: internalSecret,
    logger: (m) => log(m.level || 'info', m.message, m),
    daemonStartTime,
    daemonConfig: tickerConfig,
  });

  const gateway = createGateway({
    dispatch: internalApi.dispatch,
    internalSecret,
    sendersFilePath,
    logger: (m) => log(m.level || 'info', m.message, m),
  });

  // Loopback through Batch 4 (spawn-profiles-spec.md Design 4: "the gateway listens
  // on loopback (127.0.0.1) through Batches 2-4"); p5-2 wires the tailnet bind under
  // the network-posture spec. Binding 0.0.0.0 or any public interface is a build
  // defect that spec hard-gates.
  // Env overrides join the existing RBTV_IGNITE_* family (data_root, carrier,
  // workdir_root). They exist so a probe can bring the ingress up WITHOUT colliding
  // with the live daemon's bind — never to widen exposure: the network-posture spec
  // hard-gates a non-loopback bind, and p5-2 owns the tailnet rewiring.
  const bindHost = process.env.RBTV_IGNITE_BIND_HOST || mergedConfig.bind?.host || '127.0.0.1';
  const bindPort = Number(process.env.RBTV_IGNITE_BIND_PORT || mergedConfig.bind?.port) || 7431;
  await gateway.listen({ host: bindHost, port: bindPort });

  log('info', 'daemon composed', { heartStoreOpen: isHeartStoreOpen(), gatewayBind: `${bindHost}:${bindPort}` });

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
