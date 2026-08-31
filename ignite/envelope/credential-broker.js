'use strict';

// The token broker (`d-ask17-credential-token-broker`, `cred-account-shape-design.md` §11). A
// caged seat never holds a gtools account's login files — only a short-lived access token it
// gets by asking, over a socket that lives inside the goal's own already-RW scratch tree, so
// reaching it needs no new bind vocabulary and no manifest-visible grant.
//
// ⚠ NOT WIRED INTO THE LIVE LAUNCH PATH YET. `admitLaunch` (`envelope/launch.js`) stays fully
// synchronous — this module's `startBroker` is async (socket bind is inherently a libuv-async
// operation), and forcing that into `admitLaunch`'s contract would ripple into every caller
// (`spawn.js`, every selftest that calls `admitLaunch` synchronously) for a change bigger than
// this sitting's walls allow. `startBroker`/`stopBroker` are the integration point a follow-up
// change to `spawn.js` calls after `admitLaunch` succeeds — see the seat's report for the exact
// spot. Proven end-to-end here via `probes/probe-credential-broker.js` instead.

const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');

const SOCK_NAME = 'credential-broker.sock';
const LOG_NAME = 'credential-broker.log';

function socketPath(goalDir) {
  return path.join(goalDir, 'scratch', SOCK_NAME);
}

function logPath(goalDir) {
  return path.join(goalDir, 'scratch', LOG_NAME);
}

// Append-only, best-effort audit trail — §10b's answer to "surfaced, not swallowed" for the
// human/orchestrator investigating a stalled goal. NEVER a token value, NEVER a file's contents.
function appendLog(goalDir, fields) {
  const line = `${JSON.stringify({ ts: new Date().toISOString(), ...fields })}\n`;
  try { fs.appendFileSync(logPath(goalDir), line); } catch { /* audit trail is best-effort, never blocks a response */ }
}

function writeResponse(conn, goalDir, account, op, resp) {
  appendLog(goalDir, { op, account: account || null, ok: resp.ok, reason: resp.ok ? undefined : resp.reason });
  conn.end(`${JSON.stringify(resp)}\n`);
}

// `accounts` is the allow-list THIS goal's manifest declared (the same names
// `resolveAccountCredentials` already checked exist on disk at admission) — the broker mints
// ONLY for names in this set, never for whatever a request happens to ask, regardless of
// whether the account itself exists. `minter(account)` is injectable: production wires
// `gtools-token-minter.js`'s `gtoolsTokenMinter(gtoolsRoot)`; a probe wires a fixture that
// never touches a real account, Google, or the network.
function startBroker({ goalDir, accounts, minter }) {
  const allowed = new Set(accounts || []);
  const sock = socketPath(goalDir);
  fs.mkdirSync(path.dirname(sock), { recursive: true });
  try { fs.unlinkSync(sock); } catch { /* no stale socket to clear */ }

  const server = net.createServer((conn) => {
    let buf = '';
    conn.on('data', (chunk) => {
      buf += chunk.toString('utf8');
      const nl = buf.indexOf('\n');
      if (nl === -1) return;
      const line = buf.slice(0, nl);
      handleRequest(line, conn);
    });
    conn.on('error', () => { /* a dropped connection is the caller's business, not the broker's */ });
  });

  async function handleRequest(line, conn) {
    let req;
    try { req = JSON.parse(line); } catch {
      writeResponse(conn, goalDir, null, 'mint', { ok: false, reason: 'bad-request: not JSON' });
      return;
    }
    if (!req || req.op !== 'mint' || typeof req.account !== 'string' || !req.account) {
      writeResponse(conn, goalDir, req && req.account, req && req.op, {
        ok: false, reason: 'bad-request: expected {"op":"mint","account":"<name>"}',
      });
      return;
    }
    if (!allowed.has(req.account)) {
      writeResponse(conn, goalDir, req.account, 'mint', { ok: false, reason: 'account not declared for this goal' });
      return;
    }
    let resp;
    try {
      resp = await minter(req.account);
      if (!resp || typeof resp.ok !== 'boolean') resp = { ok: false, reason: 'minter returned a malformed response' };
    } catch (err) {
      resp = { ok: false, reason: `minter threw: ${err.message}` };
    }
    writeResponse(conn, goalDir, req.account, 'mint', resp);
  }

  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(sock, () => {
      server.removeListener('error', reject);
      resolve({
        sock,
        stop: () => new Promise((res) => {
          server.close(() => { try { fs.unlinkSync(sock); } catch { /* already gone */ } res(); });
        }),
      });
    });
  });
}

module.exports = { socketPath, logPath, startBroker };
