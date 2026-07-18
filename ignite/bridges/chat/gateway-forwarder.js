'use strict';

// The bridge's ONE outbound path to the daemon: an ordinary authenticated
// SENDER on the narrow gateway API (chat-bridge-spec.md § Forward path). It
// speaks the SAME wire the CLI speaks — POST / with `Authorization: Bearer
// <token>` and body `{ intent, payload }`; the gateway answers `{ ok: true,
// result }` or `{ ok: false, error: { code, message, details? } }` (internal-
// api-contract-spec.md §2; gateway/gateway.js).
//
// ⚑ RELOCATABLE SUBTREE (ignite/CLAUDE.md rule 4): this file deliberately does
// NOT require ../../cli/lib/gateway-client — a bridge must not reach into a
// sibling module at import level. It re-implements the tiny HTTP client itself,
// mirroring that pattern. Its ONLY dependency is node:http.
//
// ⚑ NO STORE, NO SPAWN, NO QUEUE HANDLE. The forwarder can reach the daemon ONLY
// through this HTTP request. It holds no other capability — that is the bridge's
// whole invariant (chat-bridge-spec.md Behavior #5; the gateway re-validates and
// the server core re-validates again, DEC-3 defense-in-depth).

const http = require('node:http');

const DEFAULT_TIMEOUT_MS = 10000;

// Accept a bare `host:port`, a bare host, or a full URL — the same lenience the
// CLI applies (cli/lib/config.js parseAddr).
function parseAddr(raw) {
  if (raw && typeof raw === 'object' && raw.host) {
    return { host: raw.host, port: Number(raw.port) || 80 };
  }
  let value = String(raw || '');
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(value)) value = `http://${value}`;
  const url = new URL(value);
  const port = url.port ? Number(url.port) : (url.protocol === 'https:' ? 443 : 80);
  return { host: url.hostname, port };
}

function createGatewayForwarder({ gatewayAddr, token, timeoutMs = DEFAULT_TIMEOUT_MS, httpImpl = http }) {
  if (!gatewayAddr) throw new Error('createGatewayForwarder requires a gateway address');
  const addr = parseAddr(gatewayAddr);

  // One request → one response envelope, unwrapped to { ok, result, error, status }.
  // A transport failure resolves { ok:false, error:{ code:'TRANSPORT', … } } — the
  // bridge decides what to do; it never throws a hang (gateway-cli-spec.md: fail loud,
  // never a silent hang).
  function call(intent, payload) {
    return new Promise((resolve) => {
      const body = Buffer.from(JSON.stringify({ intent, payload: payload ?? {} }), 'utf8');
      const headers = { 'content-type': 'application/json', 'content-length': body.length };
      // ⚑ The token rides the Authorization header, NEVER argv or a URL (process
      // lists / access logs leak both — gateway-cli-spec.md § Client config).
      if (token) headers['authorization'] = `Bearer ${token}`;

      let settled = false;
      const done = (v) => { if (!settled) { settled = true; resolve(v); } };

      const req = httpImpl.request(
        { host: addr.host, port: addr.port, method: 'POST', path: '/', headers, timeout: timeoutMs },
        (res) => {
          const chunks = [];
          res.on('data', (c) => chunks.push(c));
          res.on('end', () => {
            let envelope;
            try {
              envelope = JSON.parse(Buffer.concat(chunks).toString('utf8'));
            } catch (err) {
              done({ ok: false, error: { code: 'TRANSPORT', message: `gateway response not JSON: ${err.message}` }, status: res.statusCode });
              return;
            }
            done({
              ok: Boolean(envelope && envelope.ok),
              result: envelope && envelope.result != null ? envelope.result : null,
              error: envelope && envelope.error ? envelope.error : null,
              status: res.statusCode,
            });
          });
        }
      );

      req.once('timeout', () => {
        req.destroy();
        done({ ok: false, error: { code: 'TRANSPORT', message: `gateway at ${addr.host}:${addr.port} did not respond within ${timeoutMs}ms` } });
      });
      req.once('error', (err) => {
        done({ ok: false, error: { code: 'TRANSPORT', message: `could not reach gateway at ${addr.host}:${addr.port}: ${err.message}` } });
      });

      req.end(body);
    });
  }

  // Convenience: an `inspect` read (a NON-mutating intent). The bridge uses it to
  // navigate job-id → exec-id → chain-thread id (D69) and to read owner-facing
  // output the daemon has broadcast — it never opens the store to do so.
  function inspect(target, extra = {}) {
    return call('inspect', { target, ...extra });
  }

  return { forward: call, inspect, addr };
}

module.exports = { createGatewayForwarder, parseAddr };
