'use strict';

// The ONE function in this CLI that opens a socket. Every subcommand builds a
// plain `{ intent, payload }` and hands it here — no subcommand imports
// node:http itself, and NOTHING in this file (or anywhere else in cli/)
// requires server/heart, server/spawn, server/spawn/config, or
// server/internal-api: the CLI reaches the daemon ONLY through this HTTP
// request, mirroring gateway/probes/probe-gateway-live.js's own live client.
//
// Wire shape (gateway/gateway.js, internal-api-contract-spec.md §2): POST /
// with `Authorization: Bearer <token>` and body `{ intent, payload }`; the
// gateway answers `{ ok: true, result }` or `{ ok: false, error: { code,
// message, details? } }`. The HTTP status is a courtesy, never the contract —
// this client reads ok/error off the JSON body, never the status code.

const http = require('node:http');
const { CliTransportError } = require('./errors');

const DEFAULT_TIMEOUT_MS = 10000;

function callGateway({ addr, token, intent, payload, timeoutMs = DEFAULT_TIMEOUT_MS }) {
  return new Promise((resolve, reject) => {
    const body = Buffer.from(JSON.stringify({ intent, payload }), 'utf8');
    const headers = { 'content-type': 'application/json', 'content-length': body.length };
    if (token) headers['authorization'] = `Bearer ${token}`;

    let settled = false;
    const req = http.request(
      { host: addr.host, port: addr.port, method: 'POST', path: '/', headers, timeout: timeoutMs },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          if (settled) return;
          settled = true;
          let envelope;
          try {
            envelope = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          } catch (err) {
            reject(new CliTransportError(`gateway response was not valid JSON: ${err.message}`));
            return;
          }
          resolve({ status: res.statusCode, envelope });
        });
      }
    );

    // gateway-cli-spec.md § Edge Cases: "the daemon not running / gateway
    // unreachable -> the CLI fails loud with a connect error (exit 5), never a
    // silent hang." Every failure path below rejects with CliTransportError —
    // there is no path that resolves a hang past timeoutMs.
    req.once('timeout', () => {
      if (settled) return;
      settled = true;
      req.destroy();
      reject(new CliTransportError(`gateway at ${addr.host}:${addr.port} did not respond within ${timeoutMs}ms`));
    });
    req.once('error', (err) => {
      if (settled) return;
      settled = true;
      reject(new CliTransportError(`could not reach gateway at ${addr.host}:${addr.port}: ${err.message}`));
    });

    req.end(body);
  });
}

module.exports = { callGateway };
