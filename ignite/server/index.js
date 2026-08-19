'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { closeHeartStore, isHeartStoreOpen } = require('./heart/heart-store');
const { WARNING_KINDS } = require('./heart/warnings');
// Task 7.44 — ONE implementation of workflow advancement, TWO attachments (owner ruling
// decisions.md#d-attached-run-embedded-engine). The daemon no longer composes the store, the spawn
// manager and the ticker itself: it boots THE SAME library the `rbtv run` verb boots, and adds
// only what is genuinely daemon-side (gateway, internal-api, cockpit, retention, settings,
// tailnet bind). Its headed fork rides the decorate hook, which routes headed spawns to the
// tmux seat path (task 7.29 retired the server-owned pty the hook used to fork to).
const { createEngine } = require('../engine');
const { runLaneWatch } = require('../engine/lane-watch');
const { runQueueRequestPass } = require('../engine/queue-request');
const { selectCarrier } = require('./spawn/carrier');
const { createLiveSessions } = require('./spawn/live-sessions');
const { SpawnError, E_HEADED_NOT_CAPABLE } = require('./spawn/errors');
const { createInternalApi } = require('./internal-api/dispatch');
const { captureLoadedCode, writeCodeMarker } = require('./code-fingerprint');
const { parseRetentionDays, sweepRetention } = require('./retention');
const settings = require('./settings');
const { createGateway } = require('../gateway/gateway');
const { resolvePeerSeat } = require('./seat-identity/peer-identity');
const { loadSendersFile } = require('../gateway/sender-auth');
const { validateCataloguePaths } = require('./heart/catalogue-paths');
const { ensureCockpit } = require('./cockpit');

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
// validates against a STRICT root-key allowlist (bind, auth, spawn, launch-specs, jobs,
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
// the retry budget (Design 2, rule 3) is WARNING_KINDS.TAILNET_BIND_DEGRADED —
// registered canonically in server/heart/warnings.js (task 7.8, D80 ratified).
const TAILNET_WARNING_SUBJECT = 'gateway-tailnet-bind';

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function log(level, message, extra = {}) {
  const line = JSON.stringify({ ts: isoNow(), level, message, ...extra });
  console.log(line);
}

// D6 pin: ExecStart and RBTV_IGNITE_CONFIG_PATH resolve into the pinned deploy
// tree; RBTV_IGNITE_SRC names the live per-invocation tree (team-kit, coord.py).
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
      _note: 'install truth is DERIVED from server.json (isServerJsonValid) — this file never stores an installed flag (task 7.9, D81)',
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

// S-6(b) — the boot-time catalogue path check. The validator itself lives in
// server/heart/catalogue-paths.js so it can be exercised without booting a daemon; this wrapper
// owns only the REPORTING, which is where the defect was: a broken entry produced silence.
// It logs and does NOT refuse the boot — see that module for why.
function reportCataloguePaths(mergedConfig) {
  const findings = validateCataloguePaths(mergedConfig);
  for (const f of findings) {
    log('error', 'catalogue entry references a path that does not exist', {
      // `argvIndex` locates an argv finding, `key` an allowlist one — exactly one is set, and
      // JSON.stringify drops the other. Without `key` an operator meeting a stale-permission error
      // learned WHICH PATH was stale but not WHICH allowlist key declared it (task 7.577).
      check: 'catalogue-paths', section: f.section, entry: f.name,
      argvIndex: f.index, key: f.key, path: f.path, why: f.why,
    });
  }
  log(findings.length ? 'error' : 'info', 'catalogue path validation complete', {
    check: 'catalogue-paths', broken: findings.length,
    entries: Object.keys(mergedConfig.tools || {}).length
      + Object.keys(mergedConfig.workflows || {}).length,
  });
  return findings;
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
  // Derived install test (D81): valid server.json = installed. Computed BEFORE this
  // boot's own endpoint write (updateEndpointRecord fires later, on a successful
  // tailnet bind), so the field name says what it is — the value at boot entry,
  // NOT a verdict on whether this boot is installing.
  const serverJsonValidAtBoot = isServerJsonValid(installState.serverPath);
  log('info', 'install state ready', { moduleDir: installState.moduleDir, server_json_valid_at_boot: serverJsonValidAtBoot });

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

  // S-6(b): every catalogue path is checked HERE, at boot, so a broken entry is an ERROR in the
  // journal rather than a silence that surfaces months later as a confusing probe failure.
  reportCataloguePaths(mergedConfig);

  // Task 7.13: the retention window is a BOOT-TIME config knob with a fail-closed floor —
  // parse it before anything opens, so a sub-7-day typo refuses the boot loudly instead of
  // booting a daemon that would erase the audit trail. Default 90; 0 = never delete.
  const retentionDays = parseRetentionDays(process.env.RBTV_IGNITE_LOG_RETENTION_DAYS);
  log('info', 'log retention window resolved', { retentionDays });

  // ── Task 7.66: the settings.json overlay — the file's FIRST reader ─────────────────────────
  //
  // `.rbtv/modules/ignite/settings.json` carries this machine's operator-set runtime values
  // (`machines.<hostname>.<block>.<key>`, CMP-1 § Ticker settings schema). It is overlaid onto the
  // merged config HERE, before anything reads `mergedConfig.ticker`, so every later consumer —
  // the heart store's snooze conversion, the internal-api `config` block, and the tick timer
  // itself — sees ONE resolved cadence and cannot disagree about it.
  //
  // FAIL-CLOSED, the sibling of the retention floor directly above and the same idiom: a value
  // outside the configured floor/ceiling, or a misspelled key, REFUSES THE BOOT with a named
  // error. That is the second of the design's two enforcement points (§ 2.4) — the operator
  // surface refuses the same value before writing it, and this catches a file hand-edited past
  // that surface. A surface-only bound is not a bound.
  const settingsProblems = settings.validateMachine(workspaceRoot);
  if (settingsProblems.length) {
    throw new Error(
      `${settings.settingsPaths(workspaceRoot).settingsPath} is invalid for this machine ` +
      `(${settings.thisMachine()}) and the daemon REFUSES TO START:\n` +
      settingsProblems.map((p) => `  - ${p}`).join('\n') +
      `\nEdit it with \`rbtv ignite ticker set-interval <dur>\`, which refuses a bad value before writing it.`
    );
  }
  const tickerSettings = settings.effectiveBlock(workspaceRoot, 'ticker');
  mergedConfig.ticker = { ...(mergedConfig.ticker || {}), ...tickerSettings };
  // Stated at boot, in the journal, naming the SOURCE — so "the cadence I set is running" is an
  // observation and never an inference. This is also the line the end-to-end probe reads to prove
  // a restart actually adopted the edit.
  log('info', 'ticker settings resolved', {
    machine: settings.thisMachine(),
    tick_interval_ms: mergedConfig.ticker.tick_interval_ms,
    source: ((settings.readSettings(workspaceRoot).machines[settings.thisMachine()] || {}).ticker || {})
      .tick_interval_ms === undefined ? 'default' : 'settings.json',
    settings_path: settings.settingsPaths(workspaceRoot).settingsPath,
  });

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

  // tick_interval_ms is a TICKER-namespaced key (ticker.js DEFAULT_CONFIG). Reading it
  // from the config top level meant an operator's configured cadence was honoured by the
  // ticker's own config but silently ignored by the daemon loop that actually drives it.
  const tickerConfig = mergedConfig.ticker || {};

  // Task 7.30 — the headed TARGET moves from the server-owned pty to a tmux pane (R7/R8/R15/R28).
  //
  // The switch is ONE environment variable on the unit, and that is deliberate (`r-cutover-gated`):
  // unset — the default, and what every existing deployment gets — the headed fork behaves exactly
  // as before and the pty path is untouched. Set, headed sessions land in that tmux room instead.
  // So the new path is OFF unless someone turns it on, and turning it back off is one line in the
  // unit file plus a restart: the fallback stays one command away rather than one revert away.
  //
  // The ROOM IS NOT A CALLER ARGUMENT, and that is the load-bearing part. It comes from the
  // daemon's own environment, so no caller — gateway sender, ticker job, or agent — can choose
  // which room a seat lands in, or name one at all. That strengthens DEC-1's R3 rather than
  // widening it: the request surface gains no key (comm-bridge's #157 point stands — an unknown
  // key against a live args_schema is refused anyway), and caller free text still never reaches
  // argv. The seat's launch dir rides the EXISTING `workdir` argument, already validated by the
  // profile's `workdir_root` gate.
  const tmuxRoom = process.env.RBTV_IGNITE_TMUX_ROOM || null;

  // ── The engine (task 7.44) ─────────────────────────────────────────────────────────────────
  //
  // The store, the fire path and the tick algorithm are composed by the LIBRARY now — the same
  // one `rbtv run` boots in-process (owner ruling decisions.md#d-attached-run-embedded-engine:
  // one implementation of workflow advancement, two attachments). Everything below this call is
  // daemon-side and stays daemon-side.
  //
  // The store's placement is UNCHANGED and is the daemon's kind of store: `{data_root}/heart.db`,
  // the per-machine state root (batch-08 item 10 state-layout boundary, checked immediately
  // above). CMP-2 § Two store kinds: an attached run passes its OWN run-folder path here and never
  // this one; the daemon never passes anything else.
  //
  const engine = createEngine({
    dbPath: path.join(dataRoot, 'heart.db'),
    tools: mergedConfig.tools || {},
    workflows: mergedConfig.workflows || {},
    // The snooze minutes→ticks conversion lives in the store (D44) and needs the live
    // cadence. TICKER-namespaced key, same as the daemon loop below reads it.
    tickIntervalMs: tickerConfig.tick_interval_ms,
    spawnConfigPath: effectiveConfigPath,
    userManager,
    tickerConfig,
    feedPath: dataRoot ? path.join(dataRoot, 'feed.jsonl') : null,
    logPath: dataRoot ? path.join(dataRoot, 'ticker.log') : null,
    logger: (m) => log(m.level || 'info', m.message, m),
    decorateSpawnManager: (spawnManager, heartStore) => {
  // ── The headed session surface, after task 7.29 ────────────────────────────────────────────
  //
  // This hook used to construct the server-owned pty host and fork headed spawns to it. Task 7.29
  // deleted that module outright ("keep = nothing dormant"): tmux holds the headed session now,
  // SSH is the human trust boundary, and the web terminal, its three-gate security model and the
  // keystroke/screen audit contract are gone with it. What survives is the FORK ITSELF — headless
  // one-shot is still the DEFAULT and still rides the sole-spawn-path UNCHANGED; the decoration
  // routes ONLY session_mode:headed elsewhere. Only its TARGET moved, which is exactly how the
  // settle ledger frames the whole cutover ("DEC-1 is amended in TARGET, never in gate", R28).
  return {
    ...spawnManager,
    // ⚑ THIS PASS-THROUGH IS NO LONGER ARITY-PINNED, and that is the fix for a CLASS, not for one
    // operand. The ticker passes every operand positionally, so a wrapper that names a fixed list
    // silently eats whatever was added to `spawn()` after the list was written. It has done so
    // twice: `resumeRef` (r-chat-chain-resumes-session) measured 2026-08-08 on execs
    // 24666/24669/24672 — the tick log said `chain: resume`, the argv ran the exec template, and
    // the sitting answered the owner with no thread history — and `effort`
    // (`d-0811lp-effort-lane-build-now`), wired end to end on 2026-08-11 through every layer BUT
    // this one, so a daemon seat ran the harness default while the tick log reported its rung.
    // The headless path therefore forwards `...rest` WHOLE and cannot drop an operand again;
    // `probe-effort-lane` leg 8 holds that shape. Only the headed branch names positions, because
    // it must hand `spawnSeat` its arguments by name — a headed seat carries no prompt and never
    // resumes, so those two are skipped.
    spawn: (execId, sessionMode = 'headless', ...rest) => {
      if (sessionMode !== 'headed') {
        return spawnManager.spawn(execId, sessionMode, ...rest);
      }
      const [, workdir, enqueuedBy = 'unknown', , effort = null] = rest;
      // ⚑ THE ROOM IS NOW REQUIRED FOR A HEADED SPAWN, and that is a real behavior change, not a
      // tidy-up: `RBTV_IGNITE_TMUX_ROOM` unset used to mean "fall back to the pty path" (the
      // `r-cutover-gated` posture — the new target OFF unless someone turned it on). There is no
      // path left to fall back to, so an unset room is refused TYPED here rather than reaching
      // spawnSeat and failing on an empty tmux target.
      //
      // Refused per-spawn, NOT at boot, deliberately: a headless-only deployment never spawns
      // headed and must not be made to fail to start over a knob it does not use.
      //
      // The CODE is the existing E_HEADED_NOT_CAPABLE rather than a newly minted one — no second
      // classification obligation for a path that is ticker-spawn-only and never wire-triggered.
      // The message carries what the code alone does not: the refusal is the DAEMON's missing
      // target, not this profile's shape. DISCLOSED as the seat's own choice, in the 7.29 record;
      // if a distinct code is wanted, it is a one-row change here plus one NOT_WIRE_REACHABLE row.
      if (!tmuxRoom) {
        throw new SpawnError(
          E_HEADED_NOT_CAPABLE,
          'headed spawn requires a tmux room: this daemon has no RBTV_IGNITE_TMUX_ROOM set, and the '
          + 'server-owned pty fallback was retired by task 7.29 — set the variable on the unit and restart',
          { workdir, sessionMode, check: 'tmux-room-configured' },
        );
      }
      // NO `seatName` IS SUPPLIED, and its absence is the point (task 7.11 — G9, verified by
      // execution rather than read). `seatName` does two jobs inside spawnSeat: it is an IDENTITY
      // ASSERTION checked against the seat folder ("the folder is the identity; a supplied name
      // never overrides it" — the G-111 lesson), and it is the tmux window name. This call site
      // only ever wanted the second. Supplying `seat-${execId}` for the window name made an
      // identity claim this layer has no standing to make, and spawnSeat REFUSED it with
      // E_NOT_A_SEAT_FOLDER for every REAL seat — a real seat folder is never named
      // `seat-<execId>`. That left this, the ONLY route to spawnSeat, able to spawn nothing but a
      // folder literally named `seat-<execId>`.
      //
      // The window name is now DERIVED by spawnSeat from the resolved seat folder, which is
      // strictly safer than the string this site used to compose: it has already passed
      // resolveWorkdir's containment gate and parseSeatPath's shape check, so it is not a caller
      // string either — and tmux.js still refuses `:`/`.`/whitespace outright (assertTmuxName).
      return spawnManager.spawnSeat(execId, {
        room: tmuxRoom,
        seatDir: workdir,
        enqueuedBy,
        effort,
      });
    },
    // ⚑ THE HEADED exit_code OVERRIDE IS GONE, and what it guarded is stated rather than assumed
    // away. It existed because the pty path put a dtach HOLDER in the transient unit: for a dead
    // headed session the unit's ExecMainStatus was the HOLDER's exit and MASKED the harness's
    // (M3: child exited 42, unit reported 0), and the ticker's crash sweep copies status().exitCode
    // onto the row — so without the shim the sweep wrote a forbidden masked 0. Both the holder and
    // the shim that sourced around it are deleted with the pty module (task 7.29), so the override
    // has nothing left to read and `spawnManager.status` is again the single reading.
    //
    // NOT PROVEN BY THIS CHANGE, and named in the 7.29 record rather than left implicit: that the
    // tmux seat path reports a TRUE harness exit code. Its masking behaviour belongs to the seat
    // spawn (7.30 / R8), the probe that measured the pty masking died with server/pty/probes/, and
    // this seat ran no experiment on the tmux carrier. What is claimed here is only that the shim
    // could not survive its module — never that the problem it solved is known to be absent.
  };
    },
  });

  // The daemon's own handles on the engine it just booted. `decoratedSpawnManager` is what the
  // internal API is handed, and it is the SAME decorated object the ticker above was built with —
  // the decoration is applied once, inside the composition, not twice. (It was
  // `spawnManagerWithPty` until task 7.29; the name is updated with the thing it names, because a
  // handle called ...WithPty over a manager that has no pty is the kind of residue this
  // retirement exists to remove.)
  const { heartStore, ticker } = engine;
  const decoratedSpawnManager = engine.spawnManager;

  // ── The live-session manager (live-session-design.md §1/§4, owner ruling 2026-08-10) ─────────
  //
  // Constructed HERE for the same reason `onEnqueue` is wired here: the composition root is the
  // only place holding both the daemon's config and the internal API. It is FAIL-SOFT at boot —
  // a manager that cannot be built leaves `liveSessions` null, `live-feed` answers
  // `live-sessions-not-armed`, and every conversation keeps the cold path it has today. A latency
  // optimization must never be able to stop the daemon from starting.
  let liveSessions = null;
  try {
    liveSessions = createLiveSessions({
      configPath: effectiveConfigPath,
      workspaceRoot,
      logger: (m) => log(m.level || 'info', m.message, m),
      idleMs: Number(process.env.RBTV_IGNITE_LIVE_IDLE_MS) || undefined,
      maxSessions: Number(process.env.RBTV_IGNITE_LIVE_MAX) || undefined,
    });
    log('info', 'live sessions armed', { idleMs: liveSessions.config.idleMs, maxSessions: liveSessions.config.maxSessions, turnTimeoutMs: liveSessions.config.turnTimeoutMs });
  } catch (err) {
    log('warn', 'live sessions NOT armed — every conversation keeps the cold path', { error: err.message });
  }

  // Captured once at boot for `inspect daemon` uptime reporting.
  const daemonStartTime = Date.now();

  // G-188 stage 2: what code THIS process loaded, captured ONCE, here, from file bytes over the
  // require closure. Answers "is the daemon running current code" — a question the run could only
  // answer by INFERENCE (start time later than commit time), which is the reasoning G-158 exists
  // to replace. FAIL-SOFT BY CONTRACT: captureLoadedCode never throws and returns null on any
  // failure, because this runs at boot and a boot throw reaches the hard exit below — the daemon
  // must never refuse to start because of the machinery watching whether it started.
  const daemonLoadedCode = captureLoadedCode(__dirname);
  // G-188 stage 3: publish it where a CREDENTIAL-FREE reader can find it. `inspect daemon` needs
  // auth, so a continuously-watching loop would have to hold the owner's token for its whole life
  // (standing bar 11: read at call time, never held) — refused on principle by leader #840. The
  // marker is gitignored and stamps this boot's pid + INVOCATION_ID, because A MARKER OUTLIVES THE
  // PROCESS THAT WROTE IT and a reader must correlate it against the live unit before trusting it.
  // Fail-soft: returns false, never throws — see the boot bar in code-fingerprint.js.
  writeCodeMarker(workspaceRoot, daemonLoadedCode);

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
    spawnManager: decoratedSpawnManager,
    secret: internalSecret,
    logger: (m) => log(m.level || 'info', m.message, m),
    daemonStartTime,
    daemonLoadedCode,
    // Task 7.13: the retention window rides the daemon-config knobs so `inspect daemon`
    // surfaces it read-only on its existing `config` block (never a new intent).
    daemonConfig: { ...tickerConfig, log_retention_days: retentionDays },
    // Task 7.66: a LIVE read of settings.json at request time, so `inspect daemon` can report a
    // cadence edit that is written but not yet restarted into effect. `daemonConfig` above is the
    // value materialized at THIS boot and can never show that.
    readConfiguredTickIntervalMs: () => settings.effectiveBlock(workspaceRoot, 'ticker').tick_interval_ms,
    // New EXTERNAL work does not wait out the cadence: a successful enqueue (the path the chat
    // bridge uses) runs one extra, debounced tick. The `setInterval` below is untouched — this is
    // an additional tick, never a rescheduled one. Wired HERE because the composition root is the
    // only place holding both the ticker and the internal API.
    onEnqueue: () => ticker.nudge('enqueue'),
    // live-session-design.md §1: the ONE handle the `live-feed` intent reaches. Null when the
    // manager failed to build, which the handler reports rather than faulting on.
    liveSessions,
    // Task 7.771: `record-bus-answer` addresses a GOAL, and a goal folder is per-WORKSPACE state
    // (`.rbtv/goals/<goal>`), so the handler needs the root this daemon serves. Passed as plain
    // data, like every other value here — the internal API resolves no paths of its own.
    workspaceRoot,
  });

  const gateway = createGateway({
    dispatch: internalApi.dispatch,
    internalSecret,
    sendersFilePath,
    logger: (m) => log(m.level || 'info', m.message, m),
    // CMP-13 (task 7.10): the seat resolver is INJECTED here, at the composition root — the one
    // place allowed to know both the gateway and the server core. The gateway must never require
    // it; probe-gateway-boundary enforces that and caught exactly that import when 7.10 landed.
    checkPeerSeat: resolvePeerSeat,
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
    const stale = heartStore.getStandingWarning({ kind: WARNING_KINDS.TAILNET_BIND_DEGRADED, subject: TAILNET_WARNING_SUBJECT });
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
    heartStore.raiseWarning({ kind: WARNING_KINDS.TAILNET_BIND_DEGRADED, subject: TAILNET_WARNING_SUBJECT, raisedAtTick: warnTick });
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
      warningKind: WARNING_KINDS.TAILNET_BIND_DEGRADED,
      subject: TAILNET_WARNING_SUBJECT,
    });
  }

  log('info', 'daemon composed', {
    heartStoreOpen: isHeartStoreOpen(),
    gatewayBind: tailnetBound ? `${bindHost}:${bindPort} + ${tailnetBound}:${bindPort}` : `${bindHost}:${bindPort} (loopback-only)`,
  });

  // ── Task 7.36: the BOOT COCKPIT (settle ledger R6/R15) ──────────────────────
  //
  // A goal's tmux room is RUN-scoped and torn down at run close, so between runs the owner has
  // nothing to attach to. This spawns the cockpit: teamview plus a LAZY master pane (cd'd to
  // place, harness NOT launched — the owner types to start it).
  //
  // It is spawned BY THE DAEMON and is NOT a second systemd unit — the cockpit is a tmux session,
  // so the daemon stays the sole systemd citizen (task 7.36's criterion). It takes NO caller
  // argument and is exposed through no gateway intent, so DEC-1's R3 sole-spawn-path is unchanged.
  //
  // FAIL-SOFT, and deliberately BEFORE the first tick: a box without tmux or teamview must not be
  // stopped from running the control plane, so ensureCockpit reports and swallows every failure
  // (it never throws) — but it always logs a REASON, so a missing cockpit is never mistaken for a
  // healthy one. `RBTV_IGNITE_COCKPIT=off` disables it.
  //
  // `installed` gates the spawn on the D81 install test computed at boot entry above. Without it
  // EVERY throwaway daemon — the ones probes boot — leaves a persistent cockpit session behind,
  // because a cockpit is designed to outlive its daemon. Measured: a probe-suite run left a stray
  // `rbtv-cockpit` on this box. See cockpit.js for why this gate rather than a path heuristic.
  ensureCockpit({
    workspaceRoot,
    igniteSrc,
    installed: serverJsonValidAtBoot,
    goalRoom: tmuxRoom,
    logger: (m) => log(m.level || 'info', m.message, m),
  });

  // ── Task 7.13: the retention sweep — at boot, then daily ────────────────────
  //
  // Age-based only (NO size cap, by ruling) over the ENUMERATED per-machine artifact classes;
  // `heart.db` and `.runtime-config/` are never visited by construction (retention.js header).
  // A LIVE session's artifacts are never swept: the predicate consults the store per pass.
  const runRetentionSweep = () => {
    try {
      const liveIds = new Set(
        ['running', 'launching', 'stalled']
          .flatMap((s) => heartStore.listExecutionsByStatus(s))
          .map((r) => r.session_id)
          .filter(Boolean)
      );
      sweepRetention({
        dataRoot,
        retentionDays,
        isSessionLive: (sid) => liveIds.has(sid),
        logger: (m) => log(m.level || 'info', m.message, m),
      });
    } catch (err) {
      // The sweep is housekeeping: a failed pass is logged loudly and retried at the next
      // scheduled pass — it never takes the daemon down.
      log('error', 'retention sweep failed', { error: err.message });
    }
  };
  runRetentionSweep();
  const retentionTimer = setInterval(runRetentionSweep, 24 * 60 * 60 * 1000);
  if (retentionTimer.unref) retentionTimer.unref();

  // ⚠ THE LOOP TICKS THROUGH `engine.tick`, NOT `ticker.tick`, AND THE DIFFERENCE IS LOAD-BEARING.
  // `engine.tick` is `ticker.tick` PLUS the publish into each goal's execution record
  // (`engine/execution-record.js`, owner ruling decisions.md#d-s23-single-execution-record-now).
  // Calling the raw ticker here left the daemon lane writing NOTHING to that record — so a
  // daemon-run seat was invisible to it and the attached lane re-ran it, which is the exact
  // double-run the record ends and the v1 guard used to refuse. Caught in review of `142737a28`.
  // If a future change reaches for `ticker.tick()` again, it silently un-publishes this lane.
  //
  // ⚠ AND THE LANE WATCH RUNS IMMEDIATELY BEFORE EACH TICK — THIS IS THE DAEMON'S GOAL PICKUP
  // (owner ruling decisions.md#d-daemon-lane-button). It reads each goal's `execution-lane` marker
  // and calls `engine.seedGoal` for the ones assigned `daemon`; without this call the daemon still
  // writes the execution record every tick but never adopts a goal folder by itself, which is
  // exactly the state the ruling closed. BEFORE the tick, not after: a seat seeded by the pass is
  // then dispatched by the tick that follows it rather than a cadence later.
  const goalsRoot = path.join(workspaceRoot, '.rbtv', 'goals');
  const laneWatchPass = () => {
    // Never fatal: one bad goal folder must not take the loop down. `runLaneWatch` already guards
    // per goal; this is the outer belt for anything it did not anticipate.
    try {
      runLaneWatch({ goalsRoot, engine, logger: (m) => log(m.level || 'info', m.message, m) });
    } catch (err) {
      log('error', 'lane watch pass failed', { error: err.message });
    }
  };

  // ⚠ THE QUEUE-REQUEST PASS RUNS **BEFORE** THE LANE WATCH, NOT AFTER. It consumes each goal's
  // `queue-request` rows and splices the newly unblocked milestone's planning pass into
  // `taskforce.csv` (`engine/queue-request.js`, W7); the lane watch then seeds that same registry
  // in the same cadence, and the tick that follows dispatches it. Reversed, every wave boundary
  // would cost one extra cadence for no reason. Same outer belt as the lane watch: one bad goal
  // folder must never take the loop down.
  const queueRequestPass = () => {
    try {
      runQueueRequestPass({ goalsRoot, engine, logger: (m) => log(m.level || 'info', m.message, m) });
    } catch (err) {
      log('error', 'queue-request pass failed', { error: err.message });
    }
  };

  queueRequestPass();
  laneWatchPass();
  const tickResult = await engine.tick();
  log('info', 'initial tick complete', { tick: tickResult.tick, actionCount: tickResult.actions.length });

  const intervalMs = Number(tickerConfig.tick_interval_ms) || 10000; // ticker.js DEFAULT_CONFIG default
  const timer = setInterval(() => {
    queueRequestPass();
    laneWatchPass();
    engine.tick().catch((err) => log('error', 'tick failed', { error: err.message }));
  }, intervalMs);

  function shutdown(signal) {
    return async () => {
      log('info', `received ${signal}, shutting down`);
      clearInterval(timer);
      clearInterval(retentionTimer);
      // ⚠ TWO TICK DRIVERS, AND THE `clearInterval` ABOVE REACHES ONLY ONE. The ticker's nudge
      // chain re-arms itself with `setTimeout` on every nudged tick, so it survived this handler
      // and kept DISPATCHING after SIGTERM — measured 2026-08-12, ticks 241907-241912 launching
      // workers at 21:06:29 and 21:06:41 out of a process systemd was already stopping. Latching
      // the ticker is what makes "stops NEW dispatches immediately" true.
      ticker.stop();
      // Close the ingress FIRST: a request accepted after the store closes would
      // fault on a dead handle instead of being refused cleanly.
      try {
        await gateway.close();
      } catch (err) {
        log('error', 'error closing gateway', { error: err.message });
      }
      // No orphans: every warm child gets EOF and is awaited out before the daemon goes. A live
      // session outliving its manager would hold a seat, a unit and 240-600MB with nothing left
      // that knows how to reach it.
      try {
        if (liveSessions) {
          const n = liveSessions.stop();
          if (n) log('info', 'live sessions closed at shutdown', { count: n });
        }
      } catch (err) {
        log('error', 'error closing live sessions', { error: err.message });
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
