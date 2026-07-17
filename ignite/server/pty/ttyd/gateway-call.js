'use strict';

// The ONE function in the ttyd render layer that opens a socket to the ignite gateway.
//
// The mediated (c-ii) attach client is an AUTHENTICATED SENDER on the gateway — it reaches
// the server-owned pty ONLY through the daemon's intent surface (session-surface-spec.md
// Design 4), never a pty handle. So this file speaks the exact ratified wire the CLI speaks
// (internal-api-contract-spec.md §2): POST / with `Authorization: Bearer <token>` and a body
// `{ intent, payload }`; the gateway answers `{ ok: true, result }` or
// `{ ok: false, error: { code, message, details? } }`. ok/error is read off the JSON body —
// the HTTP status is a courtesy, never the contract (mirrors cli/lib/gateway-client.js).
//
// ⚑ RELOCATABILITY (ignite CLAUDE.md rule 4): this render layer is a self-contained subtree.
// It deliberately does NOT `require('../../cli/lib/gateway-client')` — a reach into a sibling
// module folder — even though the wire is identical. node:http only; zero npm deps.

const http = require('node:http');

const DEFAULT_TIMEOUT_MS = 10000;

// addr is "host:port"; token is the sender's Bearer token (an owner-kind token for the
// terminal — control actions on ANY headed session need `kind: owner` OR the creator
// approximation, D89). Resolves { ok, result, error, status } — NEVER rejects on a typed
// gateway refusal (that is data); rejects ONLY on transport failure (unreachable/timeout/
// non-JSON), so a caller can distinguish "the daemon said no" from "the daemon is gone".
function call(addr, token, intent, payload, { timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const [host, portStr] = String(addr).split(':');
  const port = Number(portStr);
  return new Promise((resolve, reject) => {
    const body = Buffer.from(JSON.stringify({ intent, payload }), 'utf8');
    const headers = { 'content-type': 'application/json', 'content-length': body.length };
    if (token) headers['authorization'] = `Bearer ${token}`;

    let settled = false;
    const req = http.request(
      { host, port, method: 'POST', path: '/', headers, timeout: timeoutMs },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          if (settled) return;
          settled = true;
          let env;
          try {
            env = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          } catch (err) {
            reject(new Error(`gateway response was not valid JSON: ${err.message}`));
            return;
          }
          resolve({
            status: res.statusCode,
            ok: Boolean(env && env.ok),
            result: env && env.result,
            error: env && env.error,
          });
        });
      }
    );
    req.once('timeout', () => {
      if (settled) return;
      settled = true;
      req.destroy();
      reject(new Error(`gateway at ${host}:${port} did not respond within ${timeoutMs}ms`));
    });
    req.once('error', (err) => {
      if (settled) return;
      settled = true;
      reject(new Error(`could not reach gateway at ${host}:${port}: ${err.message}`));
    });
    req.end(body);
  });
}

module.exports = { call };
