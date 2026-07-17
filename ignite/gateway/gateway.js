'use strict';

// The gateway module — the daemon's INGRESS half (DEC-4 bounded module).
//
// It is the ONLY code that parses raw sender input and the ONLY code that holds
// sender auth. It holds NO queue handle, NO spawn capability, and NO launch-profile
// config: its ONLY outbound dependency is the internal-API client it is handed.
//
// ⚑ THE BOUNDARY IS THE POINT, and it is enforced by CONSTRUCTION here, not by
// good intentions: this module requires nothing from ../server/heart, ../server/spawn,
// or ../server/spawn/config. It cannot open the store or spawn a process because it
// has no way to name either. A require() of any of them is a boundary violation and
// probe-gateway-boundary fails on it (gateway-cli-spec.md test 4 / internal-api test 3).
//
// Request path, in order (gateway-cli-spec.md § Gateway Pipeline):
//   1. Accept on the configured bind ADDRESSES (p5-2: loopback AND this node's tailnet
//      address — network-posture-spec.md Design 1). Steps 2-6 are identical on every
//      address: which socket accepted a connection is not an input to any of them.
//   2. AUTHENTICATE THE SENDER FIRST — before the body is interpreted at all.
//   3. Parse + shape-check into a typed request envelope.
//   4. Attach the resolved sender identity.
//   5. Forward over the server core's internal-only API.
//   6. Render the typed response or typed error back to the sender.

const http = require('node:http');
const crypto = require('node:crypto');

const { GatewayError, AUTH_REFUSED, SHAPE_INVALID, UNKNOWN_INTENT } = require('./errors');
const { parseRequest } = require('./parse');
const { loadSendersFile, createSenderAuthenticator } = require('./sender-auth');

// Cap the accepted body. An unbounded read on an ingress is a trivial memory DoS,
// and no legitimate request comes close.
const MAX_BODY_BYTES = 256 * 1024;

// The envelope is authoritative for the sender's exit-code mapping; these statuses
// are a courtesy to ordinary HTTP clients, never the contract.
const STATUS_FOR = {
  [AUTH_REFUSED]: 401,
  [SHAPE_INVALID]: 400,
  [UNKNOWN_INTENT]: 400,
  AUTH_FAILED: 500,        // an L2 failure is a DAEMON fault, never the sender's
  VERSION_MISMATCH: 400,
  BAD_ENVELOPE: 400,
  VALIDATION_FAILED: 400,
  NOT_FOUND: 404,
  UNAUTHORIZED_SENDER: 403,
  INTERNAL: 500,
};

function createGateway({ dispatch, internalSecret, sendersFilePath, logger = null }) {
  if (typeof dispatch !== 'function') {
    throw new Error('createGateway requires the server core\'s internal-API dispatch endpoint');
  }
  if (typeof internalSecret !== 'string' || internalSecret.length === 0) {
    throw new Error('createGateway requires the per-boot internal-API client secret');
  }

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // The startup gate runs HERE, at construction, so a bad registry stops the daemon
  // at BOOT rather than at the first request (spawn-profiles-spec.md Design 4).
  const senders = loadSendersFile(sendersFilePath);
  log('info', 'sender registry loaded', { sendersFile: sendersFilePath, senderCount: senders.length });

  const authenticate = createSenderAuthenticator({ senders, logger });

  // ── The pipeline ───────────────────────────────────────────────────────────
  //
  // `credential` and `body` arrive SEPARATED on purpose. The body is not touched
  // until authentication has passed, which is what makes step 2-before-3 true rather
  // than merely intended.
  async function handleRequest({ credential, body, via = 'cli', source = null }) {
    let sender;
    try {
      // ⚑ AUTH PRECEDES PARSE. A malformed request from an unauthenticated sender is
      // answered `auth-refused`, NOT a parse error — the gateway leaks nothing about
      // its request vocabulary to unauthenticated callers, and NOTHING reaches the
      // server core. This ordering is load-bearing and probe-cli-authfail mutates it
      // to prove so.
      sender = authenticate(credential, { source });
    } catch (err) {
      return renderError(err);
    }

    let payload;
    let intent;
    try {
      if (body === null || typeof body !== 'object' || Array.isArray(body)) {
        throw new GatewayError(SHAPE_INVALID, 'request must be a JSON object with { intent, payload }');
      }
      intent = body.intent;
      payload = parseRequest({ intent, payload: body.payload });
    } catch (err) {
      return renderError(err);
    }

    // Step 4 — attach the resolved sender identity. The gateway's CLAIM about the
    // sender it authenticated; the core trusts it only as far as defense-in-depth
    // allows and re-validates the request's SUBSTANCE independently of who sent it.
    // CMP-8-shape-compatible (typed, `sender`, thread-ready) per D6, so later
    // message/mailbox surfaces are purely additive.
    const envelope = {
      v: 1,
      id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      auth: internalSecret,
      sender: { id: sender.id, kind: sender.kind, via },
      intent,
      payload,
    };

    let response;
    try {
      response = await dispatch(envelope);
    } catch (err) {
      // The contract says errors are DATA — a throw out of dispatch is a contract
      // breach, not a sender error. Surface it as a daemon fault; never let it look
      // like the sender's fault.
      log('error', 'internal API threw across the boundary (contract breach)', { error: err.message });
      return { status: 500, body: { ok: false, error: { code: 'INTERNAL', message: 'server-core fault' } } };
    }

    if (response && response.ok) {
      return { status: 200, body: { ok: true, result: response.result } };
    }

    const code = (response && response.error && response.error.code) || 'INTERNAL';
    if (code === 'AUTH_FAILED') {
      // L2 failed: the gateway's OWN secret was rejected. That is a composition bug
      // in the daemon, never anything the sender did — say so loudly rather than
      // handing the sender a misleading refusal.
      log('error', 'internal API rejected the gateway\'s own client secret (composition fault)');
    }
    return {
      status: STATUS_FOR[code] || 500,
      body: { ok: false, error: { code, message: (response.error && response.error.message) || 'refused', ...(response.error && response.error.details ? { details: response.error.details } : {}) } },
    };
  }

  function renderError(err) {
    const code = err instanceof GatewayError ? err.code : 'INTERNAL';
    const message = err instanceof GatewayError ? err.message : 'gateway fault';
    return {
      status: STATUS_FOR[code] || 500,
      body: { ok: false, error: { code, message, ...(err.details ? { details: err.details } : {}) } },
    };
  }

  // ── The listeners ──────────────────────────────────────────────────────────
  //
  // Bind values arrive as PLAIN DATA from the composition root — the gateway never
  // reads the config file (that would hand it server config it must not hold), and
  // it never resolves or CLASSIFIES an address either: which addresses are permitted
  // is the server core's bind guard (network-posture-spec.md Design 2), not the
  // gateway's. This module opens the sockets it is handed and nothing more.
  //
  // ⚑ The token travels in the Authorization header, NEVER in a URL or an argv:
  // process lists and access logs leak both (gateway-cli-spec.md § Client config).
  function createServer() {
    return http.createServer((req, res) => {
      const chunks = [];
      let size = 0;
      let aborted = false;

      req.on('data', (c) => {
        size += c.length;
        if (size > MAX_BODY_BYTES) {
          aborted = true;
          res.writeHead(413, { 'content-type': 'application/json' });
          res.end(JSON.stringify({ ok: false, error: { code: 'SHAPE_INVALID', message: 'request body too large' } }));
          req.destroy();
          return;
        }
        chunks.push(c);
      });

      req.on('end', async () => {
        if (aborted) return;
        const header = req.headers['authorization'] || '';
        const credential = header.startsWith('Bearer ') ? header.slice(7).trim() : null;
        const source = req.socket.remoteAddress || null;

        let body = null;
        let bodyOk = true;
        try {
          body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : null;
        } catch {
          bodyOk = false;
        }

        // ⚑ Even a body that is not JSON does NOT short-circuit to a parse error:
        // handleRequest authenticates FIRST, so an unauthenticated caller sending
        // garbage learns only that it is unauthenticated. The undecodable body
        // becomes a shape refusal ONLY once the sender has authenticated.
        const out = await handleRequest({
          credential,
          body: bodyOk ? body : { intent: null, payload: null },
          via: 'cli',
          source,
        });

        res.writeHead(out.status, { 'content-type': 'application/json' });
        res.end(JSON.stringify(out.body));
      });
    });
  }

  let servers = [];

  // ⚑ p5-2 (network-posture-spec.md Design 1, rule 2): the socket-opening path takes a
  // LIST of hosts. Node binds exactly ONE address per server.listen(), so the dual bind
  // (loopback AND this node's tailnet address) is N servers sharing this ONE handler —
  // `createServer()` is the same function for every address, which is what makes "the
  // tailnet is not trust" true by CONSTRUCTION: there is no per-address code path in
  // which a check could be skipped, and a request arriving over the tailnet is
  // authenticated by the same `handleRequest` as one arriving over loopback.
  //
  // Hosts ACCUMULATE across calls: the composition root binds loopback first,
  // unconditionally, then calls again to ADD the tailnet address once tailscaled
  // reports one (Design 2's readiness retry). A later call never replaces an earlier
  // listener. A scalar host is accepted as a one-element list.
  function listen({ hosts, port }) {
    const list = (Array.isArray(hosts) ? hosts : [hosts]).filter((h) => h !== null && h !== undefined && h !== '');
    if (list.length === 0) return Promise.reject(new Error('gateway.listen requires at least one bind host'));
    return Promise.all(list.map((host) => new Promise((resolve, reject) => {
      const srv = createServer();
      srv.once('error', reject);
      srv.listen(port, host, () => {
        servers.push(srv);
        const addr = srv.address();
        log('info', 'gateway listening', { host: addr.address, port: addr.port });
        resolve(addr);
      });
    })));
  }

  function close() {
    const open = servers;
    servers = [];
    return Promise.all(open.map((srv) => new Promise((resolve) => srv.close(() => resolve())))).then(() => undefined);
  }

  return { handleRequest, listen, close, senderCount: senders.length };
}

module.exports = { createGateway };
