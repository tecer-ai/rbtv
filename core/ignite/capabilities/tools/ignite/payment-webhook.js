'use strict';

// The withdrawal validation: before money leaves the account, the bank asks Ignite whether the
// operation is one the payment gate approved. The waking service answers from the ledger alone, never
// from a model and never over the network, so it answers in milliseconds.
//
// API
// PROVIDERS — the providers Ignite sends through, each with its webhook path and the reading of its
//   validation body. asaas: POST /asaas/withdrawal-validation, token in the asaas-access-token header.
//   Asaas accepts our request id as externalReference on transfers (Pix key) and bill payments only, so
//   TRANSFER and BILL are matched; any other type (PIX_QR_CODE, MOBILE_PHONE_RECHARGE, PIX_REFUND,
//   PAYMENT_SPLIT) carries no request id and is refused.
// readAsaas(body) → { method, reference, operationId, amountCents, recipientKey } | { refuse: reason }
// validate(gate, provider, headers, body, token) → { status: 'APPROVED' } | { status: 'REFUSED', refuseReason }
//   REFUSED unless the token is configured and the header equals it, the body is the provider's
//   validation of a gated method, and gate.answer approves it (payments.js: the request the reference
//   names, sent by Ignite, not answered for another operation, same amount, same recipient).
// createWebhook({ gate, token, port, host?, log? }) → { listen() → Promise<port>, close() → Promise }
//   An HTTP listener on host (127.0.0.1) and port; token() → the configured token or null. A request
//   to a path no provider owns gets 404, another method 405, a body over 64 KB or not read within
//   1.5 s is refused. Each answer is logged as { event: 'payment-webhook', id, status, reason }.

const http = require('node:http');
const crypto = require('node:crypto');

const MAX_BODY = 64 * 1024;
const READ_MS = 1_500;

function cents(value) {
  return typeof value === 'number' && Number.isFinite(value) ? Math.round(value * 100) : null;
}

function readAsaas(body) {
  const type = body?.type;
  if (type === 'TRANSFER') {
    const op = body.transfer || {};
    return {
      method: 'pix',
      reference: op.externalReference || null,
      operationId: op.id == null ? null : String(op.id),
      amountCents: cents(op.value),
      recipientKey: op.bankAccount?.pixAddressKey || null,
    };
  }
  if (type === 'BILL') {
    const op = body.bill || {};
    return {
      method: 'bill',
      reference: op.externalReference || null,
      operationId: op.id == null ? null : String(op.id),
      amountCents: cents(op.value),
      recipientKey: op.identificationField || null,
    };
  }
  return { refuse: `${type || 'an operation with no type'} is not paid through the payment gate` };
}

const PROVIDERS = Object.freeze({
  asaas: { path: '/asaas/withdrawal-validation', header: 'asaas-access-token', read: readAsaas },
});

function sameToken(given, wanted) {
  const a = Buffer.from(String(given ?? ''), 'utf8');
  const b = Buffer.from(String(wanted), 'utf8');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function validate(gate, provider, headers, body, token) {
  const spec = PROVIDERS[provider];
  const refused = (refuseReason, id = null) => ({ status: 'REFUSED', refuseReason, id });
  if (!spec) return refused(`unknown provider ${provider}`);
  if (!token) return refused('the webhook token is not configured in Ignite');
  if (!sameToken(headers?.[spec.header], token)) return refused('bad token');
  const op = spec.read(body);
  if (op.refuse) return refused(op.refuse);
  const answer = gate.answer({ provider, ...op });
  if (answer.status === 'APPROVED') return { status: 'APPROVED', id: answer.id };
  return refused(answer.reason, answer.id);
}

function createWebhook({ gate, token, port, host = '127.0.0.1', log = () => {} } = {}) {
  const routes = new Map(Object.entries(PROVIDERS).map(([name, spec]) => [spec.path, name]));
  let server = null;

  function note(fields) {
    try { log({ event: 'payment-webhook', ...fields }); } catch { /* answering comes first */ }
  }

  function reply(res, status, body) {
    const data = JSON.stringify(body);
    res.writeHead(status, { 'content-type': 'application/json', 'content-length': Buffer.byteLength(data) });
    res.end(data);
  }

  function handle(req, res) {
    const provider = routes.get(String(req.url || '').split('?')[0]);
    if (!provider) return reply(res, 404, { error: 'not found' });
    if (req.method !== 'POST') return reply(res, 405, { error: 'POST only' });
    const chunks = [];
    let size = 0;
    let done = false;
    const finish = (answer) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      note({ provider, id: answer.id || null, status: answer.status, reason: answer.refuseReason || null });
      const body = answer.status === 'APPROVED' ? { status: 'APPROVED' } : { status: 'REFUSED', refuseReason: answer.refuseReason };
      reply(res, 200, body);
    };
    const timer = setTimeout(() => finish({ status: 'REFUSED', refuseReason: 'the body did not arrive in time' }), READ_MS);
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY) {
        finish({ status: 'REFUSED', refuseReason: 'the body is too large' });
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('error', () => finish({ status: 'REFUSED', refuseReason: 'the request failed' }));
    req.on('end', () => {
      if (done) return;
      let body;
      try { body = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch {
        finish({ status: 'REFUSED', refuseReason: 'the body is not JSON' });
        return;
      }
      try {
        finish(validate(gate, provider, req.headers, body, token()));
      } catch (error) {
        finish({ status: 'REFUSED', refuseReason: `Ignite could not check it: ${error.message}` });
      }
    });
    return undefined;
  }

  function listen() {
    return new Promise((resolve, reject) => {
      server = http.createServer(handle);
      server.once('error', reject);
      server.listen(port, host, () => {
        server.off('error', reject);
        resolve(server.address().port);
      });
    });
  }

  function close() {
    return new Promise((resolve) => {
      if (!server) return resolve();
      server.close(() => resolve());
      server.closeAllConnections?.();
      server = null;
      return undefined;
    });
  }

  return { listen, close };
}

module.exports = { PROVIDERS, readAsaas, validate, createWebhook };
