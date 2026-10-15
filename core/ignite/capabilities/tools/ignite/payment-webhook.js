'use strict';

// The withdrawal validation: before money leaves the account, the bank asks Ignite whether the
// operation is one the payment gate approved. The waking service answers from the ledger alone, never
// from a model and never over the network. Bank-neutral: each bank's half (where it calls, the token's
// header and variable, how its body reads) is a provider adapter in that bank's connector.
//
// API
// loadProvider(name, { root? }) → the provider's adapter { path, header, tokenEnv, read(body) }, required from
//   <root>/connectors/<name>/capabilities/tools/<name>/lib/withdrawal-validation.js, root being this repository.
//   read(body) → { method, reference, operationId, amountCents, recipientKey } | { refuse: reason }. Throws for a
//   name that is not a slug, an absent file, or an adapter of another shape.
// validate(gate, provider, adapter, headers, body, token) → { status: 'APPROVED', id } | { status: 'REFUSED', refuseReason, id, busy? }
//   REFUSED unless the token is configured and the adapter's header equals it, the adapter reads the body as an
//   operation, and gate.answer approves it (payments.js). A ledger still busy after the gate's own wait is REFUSED
//   with that reason and busy: true.
// createWebhook({ gate, providers, token, port, host?, log? }) → { listen() → Promise<port>, close() → Promise }
//   gate: a Gate on its own connection whose busy wait is 0, so no call blocks. providers: { name: adapter };
//   token(name) → that provider's configured token or null. An HTTP listener on host (127.0.0.1) and port. A busy
//   ledger is tried again every 20 ms without blocking, so calls never queue behind one another; one still busy
//   600 ms after its call arrived is answered REFUSED with the reason. A path no provider owns gets 404, another
//   method 405; a body over 64 KB or not read within 1 s is refused. Each answer is logged as
//   { event: 'payment-webhook', provider, id, status, reason }.
// startWebhook({ workspace, timeZone, currency, providers, port, host?, log? }) → { listen() → Promise<port>, close() → Promise }
//   The waking service's listener: createWebhook in a worker thread of its own, with its own ledger connection, so
//   nothing the service's main thread waits for (a ledger or a store another process holds, a long pass) delays an
//   answer. providers: the provider names; the worker loads their adapters and reads each token by its adapter's
//   variable (process environment, then .rbtv/config/env/.env) on every call. Its log lines arrive through log.

const http = require('node:http');
const path = require('node:path');
const crypto = require('node:crypto');
const { Worker, isMainThread, parentPort, workerData } = require('node:worker_threads');

const MAX_BODY = 64 * 1024;
const READ_MS = 1_000;
const BUSY_WAIT_MS = 600;
const BUSY_RETRY_MS = 20;
const CLOSE_MS = 2_000;
const REPO = path.resolve(__dirname, '..', '..', '..', '..', '..');
const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const ENV_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;

function loadProvider(name, { root = REPO } = {}) {
  if (typeof name !== 'string' || !SLUG.test(name)) throw new Error(`payment provider ${name} is not a provider name`);
  const file = path.join(root, 'connectors', name, 'capabilities', 'tools', name, 'lib', 'withdrawal-validation.js');
  let adapter;
  try {
    adapter = require(file);
  } catch (error) {
    throw new Error(`payment provider ${name} has no withdrawal validation at ${file}: ${error.message}`);
  }
  const ok = adapter && typeof adapter.path === 'string' && adapter.path.startsWith('/')
    && typeof adapter.header === 'string' && adapter.header === adapter.header.toLowerCase()
    && typeof adapter.tokenEnv === 'string' && ENV_NAME.test(adapter.tokenEnv) && typeof adapter.read === 'function';
  if (!ok) throw new Error(`payment provider ${name}: ${file} must export path, header (lowercase), tokenEnv and read(body)`);
  return adapter;
}

function sameToken(given, wanted) {
  const a = Buffer.from(String(given ?? ''), 'utf8');
  const b = Buffer.from(String(wanted), 'utf8');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function busy(error) {
  return error?.errcode === 5 || error?.errcode === 6 || /database is (locked|busy)/i.test(String(error?.message));
}

function validate(gate, provider, adapter, headers, body, token) {
  const refused = (refuseReason, id = null) => ({ status: 'REFUSED', refuseReason, id });
  if (!adapter) return refused(`unknown provider ${provider}`);
  if (!token) return refused('the webhook token is not configured in Ignite');
  if (!sameToken(headers?.[adapter.header], token)) return refused('bad token');
  const op = adapter.read(body);
  if (op.refuse) return refused(op.refuse);
  let answer;
  try {
    answer = gate.answer({ provider, ...op });
  } catch (error) {
    if (busy(error)) return { ...refused(`the ledger is busy (${error.message}): nothing was approved`), busy: true };
    return refused(`Ignite could not check it: ${error.message}`);
  }
  if (answer.status === 'APPROVED') return { status: 'APPROVED', id: answer.id };
  return refused(answer.reason, answer.id);
}

function createWebhook({ gate, providers = {}, token, port, host = '127.0.0.1', log = () => {} } = {}) {
  const routes = new Map(Object.entries(providers).map(([name, adapter]) => [adapter.path, name]));
  const retries = new Set();
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
    const arrived = Date.now();
    const provider = routes.get(String(req.url || '').split('?')[0]);
    if (!provider) return reply(res, 404, { error: 'not found' });
    if (req.method !== 'POST') return reply(res, 405, { error: 'POST only' });
    const chunks = [];
    let size = 0;
    let done = false;
    let retry = null;
    const finish = (answer) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (retry) { clearTimeout(retry); retries.delete(retry); }
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
      const attempt = () => {
        if (retry) { retries.delete(retry); retry = null; }
        if (done) return;
        let answer;
        try {
          answer = validate(gate, provider, providers[provider], req.headers, body, token(provider));
        } catch (error) {
          answer = { status: 'REFUSED', refuseReason: `Ignite could not check it: ${error.message}` };
        }
        if (answer.busy && Date.now() + BUSY_RETRY_MS < arrived + BUSY_WAIT_MS) {
          retry = setTimeout(attempt, BUSY_RETRY_MS);
          retries.add(retry);
          return;
        }
        finish(answer);
      };
      attempt();
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
    for (const timer of retries) clearTimeout(timer);
    retries.clear();
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

function startWebhook({ workspace, timeZone, currency, providers = [], port, host = '127.0.0.1', log = () => {} } = {}) {
  let worker = null;
  let exited = Promise.resolve();

  function listen() {
    return new Promise((resolve, reject) => {
      const own = new Worker(__filename, { workerData: { paymentWebhook: { workspace, timeZone, currency, providers, port, host } } });
      worker = own;
      exited = new Promise((done) => own.once('exit', done));
      own.on('message', (message) => {
        if (message?.log) {
          try { log(message.log); } catch { /* answering comes first */ }
        } else if (message?.listening != null) {
          resolve(message.listening);
        } else if (message?.failed) {
          reject(new Error(message.failed));
        }
      });
      own.on('error', (error) => {
        reject(error);
        try { log({ event: 'error', what: 'payment-webhook', message: `the withdrawal validation stopped: ${error.message}` }); } catch { /* logged or not */ }
      });
    });
  }

  function close() {
    const own = worker;
    worker = null;
    if (!own) return exited;
    own.postMessage({ close: true });
    const timer = setTimeout(() => { own.terminate(); }, CLOSE_MS);
    return exited.then(() => clearTimeout(timer));
  }

  return { listen, close };
}

// The worker thread startWebhook starts: its own adapters, ledger connection and listener.
function serve({ workspace, timeZone, currency, providers, port, host }) {
  const { Gate } = require('./payments.js');
  const { envValue } = require('./config.js');
  let gate = null;
  let hook = null;
  const end = () => {
    try { gate?.close(); } catch { /* closing */ }
    parentPort.close();
  };
  try {
    const adapters = Object.fromEntries(providers.map((name) => [name, loadProvider(name)]));
    gate = new Gate({ workspace, timeZone, currency, busyMs: 0 });
    hook = createWebhook({
      gate,
      providers: adapters,
      token: (name) => envValue(workspace, adapters[name].tokenEnv),
      port,
      host,
      log: (fields) => parentPort.postMessage({ log: fields }),
    });
  } catch (error) {
    parentPort.postMessage({ failed: error.message });
    end();
    return;
  }
  parentPort.on('message', (message) => {
    if (message?.close) hook.close().then(end);
  });
  hook.listen().then((bound) => parentPort.postMessage({ listening: bound }), (error) => {
    parentPort.postMessage({ failed: error.message });
    end();
  });
}

if (!isMainThread && workerData?.paymentWebhook) serve(workerData.paymentWebhook);

module.exports = { loadProvider, validate, createWebhook, startWebhook };
