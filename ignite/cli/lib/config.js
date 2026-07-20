'use strict';

// Client config resolution — gateway-cli-spec.md § Client config + ADX-3/D27
// (the ignite install model, canonically stated in `ignite/CLAUDE.md` §
// Installation model).
//
// Resolution order for the gateway address:
//   1. IGNITE_GATEWAY_ADDR env var — explicit override, always wins when set.
//   2. The workspace's COMMITTED endpoint record `.rbtv/modules/ignite/server.json`
//      (D27): tailnet address preferred. The SSH-tunnel fallback is DERIVABLE
//      from that record's ssh_host/ssh_user/ssh_port fields, but this thin CLI
//      does not establish the tunnel itself (that is an operator action,
//      out of the gateway-API-wrapping charter this task builds to) — it
//      prints the exact command instead.
//
// The sender token is UNCHANGED by any of this — resolved only from the
// untracked env surface (IGNITE_SENDER_TOKEN), never from server.json
// (credentials never travel in git, D27).
//
// Field names/shape mirror server/index.js's OWN resolution verbatim
// (resolveWorkspaceRoot / ensureInstallState / isServerJsonValid) so the CLI
// and the daemon agree on where a workspace's install state lives. This file
// only READS that state — it never writes `.rbtv/modules/ignite/*`.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { CliUsageError } = require('./errors');

function resolveWorkspaceRoot() {
  return path.resolve(process.env.RBTV_IGNITE_WORKSPACE_ROOT || process.cwd());
}

function serverJsonPath(workspaceRoot) {
  return path.join(workspaceRoot, '.rbtv', 'modules', 'ignite', 'server.json');
}

// Returns the parsed record, or null when no server.json exists yet (never
// installed for this workspace). Malformed JSON is a loud CliUsageError, not
// a silent null — a corrupt endpoint record is a real problem to surface.
function readServerJson(workspaceRoot) {
  const p = serverJsonPath(workspaceRoot);
  let raw;
  try {
    raw = fs.readFileSync(p, 'utf8');
  } catch {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new CliUsageError(
      `the endpoint record at ${p} is not valid JSON — reinstall ignite for this workspace, ` +
      `or fix the file by hand.`
    );
  }
}

// Accepts a bare `host:port`, a bare host (defaults to port 80), or a full
// URL. gateway-cli-spec.md does not fix the env value's exact shape, so this
// is deliberately lenient — any of these should just work off a terminal.
function parseAddr(raw) {
  let value = raw;
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(value)) value = `http://${value}`;
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new CliUsageError(`IGNITE_GATEWAY_ADDR "${raw}" is not a valid host[:port] or URL`);
  }
  const port = url.port ? Number(url.port) : (url.protocol === 'https:' ? 443 : 80);
  return { host: url.hostname, port };
}

// server.json is a MACHINE-KEYED MAP (batch-08 item 10 state-layout boundary,
// owner-ruled 2026-07-20): it travels via git to EVERY machine, so each machine's
// install — endpoint fields plus its per-machine state-root path — is recorded
// under `machines[<hostname>]`; a single flat value would be right on one machine
// and wrong on every other. Selection: this machine's own entry when it records a
// server (a session spawned ON the server machine resolves its own daemon), else
// the one entry that does; several remote candidates are ambiguous and ask for
// IGNITE_GATEWAY_ADDR. The legacy flat shape (endpoint fields at top level) is
// still accepted so a workspace pulled at either side of the shape change resolves.
function selectMachineEntry(record, recordPath) {
  if (!record || typeof record !== 'object') return record;
  const machines = record.machines;
  if (!machines || typeof machines !== 'object') return record; // legacy flat shape
  const hasServer = (m) => m && typeof m === 'object' && typeof m.tailnet_host === 'string' && m.tailnet_host.length > 0;
  const own = machines[os.hostname()];
  if (hasServer(own)) return own;
  const servers = Object.values(machines).filter(hasServer);
  if (servers.length === 1) return servers[0];
  if (servers.length > 1) {
    throw new CliUsageError(
      `${recordPath} records ${servers.length} machines running a server — ambiguous from this ` +
      `machine. Set IGNITE_GATEWAY_ADDR to the gateway you mean.`
    );
  }
  // No entry names a server; fall back to the machine's own entry (it may still
  // carry the ssh_* fields) so the existing error paths below stay accurate.
  return own || null;
}

function resolveGatewayAddr() {
  const envAddr = process.env.IGNITE_GATEWAY_ADDR;
  if (envAddr && envAddr.length > 0) return parseAddr(envAddr);

  const workspaceRoot = resolveWorkspaceRoot();
  const recordPath = serverJsonPath(workspaceRoot);
  const record = selectMachineEntry(readServerJson(workspaceRoot), recordPath);

  if (record && typeof record.tailnet_host === 'string' && record.tailnet_host.length > 0) {
    if (!Number.isInteger(record.gateway_port)) {
      throw new CliUsageError(
        `${recordPath} names a tailnet host but no integer gateway_port — reinstall ignite for ` +
        `this workspace, or set IGNITE_GATEWAY_ADDR explicitly.`
      );
    }
    return { host: record.tailnet_host, port: record.gateway_port };
  }

  if (record && typeof record.ssh_host === 'string' && record.ssh_host.length > 0) {
    const port = Number.isInteger(record.gateway_port) ? record.gateway_port : '<gateway_port>';
    throw new CliUsageError(
      `${recordPath} has no tailnet address on record yet — only the SSH-tunnel fallback is ` +
      `derivable. This CLI does not open the tunnel itself; open it yourself, then point ` +
      `IGNITE_GATEWAY_ADDR at the local end:\n` +
      `  ssh -L ${port}:127.0.0.1:${port} -p ${record.ssh_port || 22} ${record.ssh_user || '<ssh_user>'}@${record.ssh_host}\n` +
      `  IGNITE_GATEWAY_ADDR=127.0.0.1:${port} ignite ...`
    );
  }

  throw new CliUsageError(
    `no gateway address configured. Set IGNITE_GATEWAY_ADDR, or run ignite from a workspace where ` +
    `${recordPath} names an installed server (D27 install model — ignite/CLAUDE.md § Installation model).`
  );
}

// ⚑ The token NEVER appears in argv or a URL (gateway-cli-spec.md § Client
// config — process lists and access logs leak both): env only. A missing
// token is deliberately NOT a local error here — the request still goes out
// with no credential so the gateway's real AUTH_REFUSED path is the one that
// answers (gateway-cli-spec.md behavior row 6), never a client-side fake.
function resolveToken() {
  const t = process.env.IGNITE_SENDER_TOKEN;
  return typeof t === 'string' && t.length > 0 ? t : null;
}

module.exports = {
  resolveWorkspaceRoot,
  serverJsonPath,
  readServerJson,
  selectMachineEntry,
  resolveGatewayAddr,
  resolveToken,
};
