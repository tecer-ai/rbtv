'use strict';

const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const { openHeartStore, closeHeartStore, isHeartStoreOpen } = require('./heart/heart-store');
const { createSpawnManager } = require('./spawn/spawn');
const { createTicker } = require('./ticker/ticker');

const SMOKE_TEST = process.env.RBTV_IGNITE_SMOKE_TEST === '1';

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

function resolveWorkspaceRoot() {
  return process.env.RBTV_IGNITE_WORKSPACE_ROOT || process.cwd();
}

function resolveConfigPath(igniteSrc) {
  return process.env.RBTV_IGNITE_CONFIG_PATH || path.join(igniteSrc, 'config', 'spawn-profiles.yaml');
}

function ensureDir(p, mode = 0o700) {
  fs.mkdirSync(p, { recursive: true, mode });
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
  const overrides = {};
  if (process.env.RBTV_IGNITE_DATA_ROOT) overrides.data_root = process.env.RBTV_IGNITE_DATA_ROOT;
  if (process.env.RBTV_IGNITE_CARRIER) overrides.carrier = process.env.RBTV_IGNITE_CARRIER;
  if (process.env.RBTV_IGNITE_WORKDIR_ROOT) overrides.workdir_root = process.env.RBTV_IGNITE_WORKDIR_ROOT;

  if (Object.keys(overrides).length === 0) {
    return { effectiveConfigPath: configPath, mergedConfig: loadMergedConfig(configPath), tempConfigDir: null };
  }

  const cfg = loadMergedConfig(configPath);
  // Keep runtime-only config material inside the configured data root so no
  // ephemeral file lands in arbitrary temp directories outside the workspace.
  const tempConfigDir = path.join(dataRoot || workspaceRoot, '.runtime-config');
  ensureDir(tempConfigDir);
  const effectiveConfigPath = path.join(tempConfigDir, 'spawn-profiles.yaml');
  fs.writeFileSync(effectiveConfigPath, yaml.dump(cfg));
  return { effectiveConfigPath, mergedConfig: cfg, tempConfigDir };
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
  const workspaceRoot = resolveWorkspaceRoot();
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

  const { effectiveConfigPath, mergedConfig, tempConfigDir } = materializeEffectiveConfig(configPath, dataRoot, workspaceRoot);
  if (effectiveConfigPath !== configPath) {
    log('info', 'runtime config overrides materialized', { effectiveConfigPath });
  }

  if (dataRoot) ensureDir(dataRoot);
  if (mergedConfig.default_workdir_root) ensureDir(mergedConfig.default_workdir_root);

  const heartStore = openHeartStore({
    runtimeStateRoot: workspaceRoot,
    profiles: mergedConfig.profiles || {},
    tools: mergedConfig.tools || {},
    workflows: mergedConfig.workflows || {},
  });

  const spawnManager = createSpawnManager({
    heartStore,
    configPath: effectiveConfigPath,
    logger: (m) => log(m.level || 'info', m.message, m),
    userManager: true,
  });

  const ticker = createTicker({
    heartStore,
    spawnManager,
    config: mergedConfig.ticker || {},
    logger: (m) => log(m.level || 'info', m.message, m),
    feedPath: dataRoot ? path.join(dataRoot, 'feed.jsonl') : null,
    logPath: dataRoot ? path.join(dataRoot, 'ticker.log') : null,
  });

  log('info', 'daemon composed', { heartStoreOpen: isHeartStoreOpen() });

  const tickResult = await ticker.tick();
  log('info', 'initial tick complete', { tick: tickResult.tick, actionCount: tickResult.actions.length });

  if (SMOKE_TEST) {
    log('info', 'smoke test complete, stopping cleanly');
    cleanupTempConfig(tempConfigDir);
    closeHeartStore();
    log('info', 'daemon stopped');
    return;
  }

  const intervalMs = Number(mergedConfig.tick_interval_ms) || 10000;
  const timer = setInterval(() => {
    ticker.tick().catch((err) => log('error', 'tick failed', { error: err.message }));
  }, intervalMs);

  function shutdown(signal) {
    return async () => {
      log('info', `received ${signal}, shutting down`);
      clearInterval(timer);
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
}

main().catch((err) => {
  log('error', 'daemon failed to start', { error: err.message, stack: err.stack });
  process.exit(1);
});
