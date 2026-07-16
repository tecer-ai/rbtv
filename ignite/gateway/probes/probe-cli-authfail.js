'use strict';

// probe-cli-authfail — gateway-cli-spec.md test 3 + spawn-profiles-spec.md test 8
// ("unauth refused even locally") and test 9 (sender identity in the audit trail),
// plus internal-api-contract-spec.md test 2 (only the gateway can call dispatch).
//
// The criterion, in the spec's own words: "Typed `auth-refused` every time — never a
// parse/shape error for the unauthenticated malformed request — exit 3, BEFORE the
// server core (server log shows no forwarded request)."
//
// THE LOAD-BEARING ASSERTION IS THE ORDER, and it is asserted OBSERVABLY rather than
// by reading the code: a spy dispatch counts calls, so "nothing reached the server
// core" is a measured fact, not a claim about the source.
//
// Localhost is not trust (DEC-3) — every refusal below is from loopback, and every
// one of them is refused anyway.
//
// MUTATION: a green refusal proves the door said no; it does NOT prove the door can
// ever say yes, and a gateway that refused EVERYTHING would pass every refusal check.
// So each guard is mutated in the direction that would matter — a parse-first
// pipeline is shown to answer a NON-auth error (so the order assertion discriminates),
// and the valid-token / correct-secret paths are shown to SUCCEED.
//
// The capture is truncated at module load, BEFORE any work (D51 evidence-husk
// hazard: a probe that dies at start must leave an EMPTY capture, never the previous
// run's stale `EXIT: 0`). The process exit code remains the truth.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-authfail.out');
fs.writeFileSync(outPath, '');

const { createGateway } = require('../gateway');
const { hashToken } = require('../sender-auth');
const { parseRequest } = require('../parse');
const { createInternalApi } = require('../../server/internal-api/dispatch');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
const skipped = 0;
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Real tokens, minted per run. Only their HASHES reach the registry file, exactly as
// the live deployment works. They are never printed into this capture — a token in
// evidence is a leaked token (gateway-cli-spec.md § Client config).
const OWNER_TOKEN = crypto.randomBytes(16).toString('hex');
const AGENT_TOKEN = crypto.randomBytes(16).toString('hex');
const DISABLED_TOKEN = crypto.randomBytes(16).toString('hex');

const sendersFile = path.join(os.tmpdir(), `ignite-probe-senders-${Date.now()}-${process.pid}.yaml`);

function writeSendersFile() {
  fs.writeFileSync(sendersFile, [
    'senders:',
    '  - sender-id: probe-owner',
    '    kind: owner',
    `    token-hash: ${hashToken(OWNER_TOKEN)}`,
    '    enabled: true',
    '  - sender-id: probe-agent',
    '    kind: agent',
    `    token-hash: ${hashToken(AGENT_TOKEN)}`,
    '    enabled: true',
    '  - sender-id: probe-revoked',
    '    kind: agent',
    `    token-hash: ${hashToken(DISABLED_TOKEN)}`,
    '    enabled: false',
    '',
  ].join('\n'), { mode: 0o600 });
  fs.chmodSync(sendersFile, 0o600);
}

// A SPY standing in for the server core. Its only job is to answer the question the
// spec actually asks — "did anything reach the server core?" — as a counted fact.
function makeSpyDispatch() {
  const calls = [];
  const fn = async (env) => {
    calls.push({ intent: env.intent, sender: env.sender, auth: env.auth });
    return { v: 1, id: env.id, ok: true, result: { spy: true }, error: null };
  };
  fn.calls = calls;
  return fn;
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  writeSendersFile();

  const secret = crypto.randomBytes(32).toString('hex');
  let spy = makeSpyDispatch();
  let gw = createGateway({ dispatch: spy, internalSecret: secret, sendersFilePath: sendersFile });

  const validBody = { intent: 'inspect', payload: { target: 'queue' } };
  // Deliberately shape-INVALID: an unknown intent AND a malformed payload. If parse
  // ran before auth, THIS is what would produce a shape error instead of a refusal.
  const garbageBody = { intent: 'not-an-intent', payload: 'not-an-object' };

  // --- 1. No token at all -> typed auth-refused, nothing forwarded.
  let r = await gw.handleRequest({ credential: null, body: validBody, source: '127.0.0.1' });
  check('no token -> typed AUTH_REFUSED', r.body.error && r.body.error.code === 'AUTH_REFUSED', `code=${r.body.error && r.body.error.code}`);
  check('no token -> HTTP 401-class', r.status === 401, `status=${r.status}`);
  check('no token -> NOTHING reached the server core', spy.calls.length === 0, `dispatch calls=${spy.calls.length}`);

  // --- 2. Wrong token -> same uniform refusal.
  r = await gw.handleRequest({ credential: 'not-the-token', body: validBody, source: '127.0.0.1' });
  check('wrong token -> typed AUTH_REFUSED', r.body.error && r.body.error.code === 'AUTH_REFUSED', `code=${r.body.error && r.body.error.code}`);
  check('wrong token -> NOTHING reached the server core', spy.calls.length === 0, `dispatch calls=${spy.calls.length}`);

  // --- 3. A DISABLED sender's REAL token -> refused. Revocation works.
  r = await gw.handleRequest({ credential: DISABLED_TOKEN, body: validBody, source: '127.0.0.1' });
  check('a DISABLED sender is refused (revocation is effective)', r.body.error && r.body.error.code === 'AUTH_REFUSED', `code=${r.body.error && r.body.error.code}`);
  check('a disabled sender -> NOTHING reached the server core', spy.calls.length === 0, `dispatch calls=${spy.calls.length}`);

  // --- 4. THE UNIFORM-REFUSAL PROPERTY: the three refusals are byte-identical.
  // A refusal that varied by cause would be an ORACLE — it would let an unauthenticated
  // caller enumerate senders and tell "revoked" apart from "never existed".
  const rNo = await gw.handleRequest({ credential: null, body: validBody });
  const rBad = await gw.handleRequest({ credential: 'nope', body: validBody });
  const rOff = await gw.handleRequest({ credential: DISABLED_TOKEN, body: validBody });
  const bodies = [JSON.stringify(rNo.body), JSON.stringify(rBad.body), JSON.stringify(rOff.body)];
  check('the refusal is UNIFORM — no-token / bad-token / disabled are indistinguishable',
    bodies[0] === bodies[1] && bodies[1] === bodies[2],
    `identical payload: ${bodies[0]}`);
  check('the refusal leaks NO detail (no token echo, no field name, no sender roster)',
    !bodies[0].includes('token-hash') && !bodies[0].includes('probe-') &&
    !bodies[0].includes(OWNER_TOKEN) && !bodies[0].includes(DISABLED_TOKEN) && !bodies[0].includes('details'),
    bodies[0]);

  // --- 5. AUTH PRECEDES PARSE (the spec's explicit "never a parse/shape error").
  spy = makeSpyDispatch();
  gw = createGateway({ dispatch: spy, internalSecret: secret, sendersFilePath: sendersFile });
  r = await gw.handleRequest({ credential: null, body: garbageBody, source: '127.0.0.1' });
  check('AUTH PRECEDES PARSE: an unauthenticated MALFORMED request is AUTH_REFUSED, never a shape error',
    r.body.error && r.body.error.code === 'AUTH_REFUSED',
    `code=${r.body.error && r.body.error.code} (a SHAPE_INVALID/UNKNOWN_INTENT here would prove the body was interpreted first)`);
  check('the unauthenticated malformed request reached NOTHING', spy.calls.length === 0, `dispatch calls=${spy.calls.length}`);

  // --- 6. MUTATION: parsing that same body BEFORE auth answers a NON-auth error.
  // Proves the assertion above is testing the ORDER, not merely that some error came back.
  const parseFirstAnswer = (() => {
    try {
      parseRequest({ intent: garbageBody.intent, payload: garbageBody.payload });
      return 'NO ERROR';
    } catch (err) {
      return err.code; // what a parse-BEFORE-auth gateway would have answered
    }
  })();
  check('MUTATION: a parse-first pipeline would answer a NON-auth error (so the order assertion discriminates)',
    parseFirstAnswer !== 'AUTH_REFUSED' && parseFirstAnswer !== 'NO ERROR',
    `parse-first would answer "${parseFirstAnswer}" instead of AUTH_REFUSED`);

  // --- 7. The door CAN say yes — a refuse-everything gateway passes every check above.
  spy = makeSpyDispatch();
  gw = createGateway({ dispatch: spy, internalSecret: secret, sendersFilePath: sendersFile });
  r = await gw.handleRequest({ credential: AGENT_TOKEN, body: validBody, source: '127.0.0.1' });
  check('a VALID token is accepted and forwarded (the guard DISCRIMINATES, not just denies)',
    r.body.ok === true && spy.calls.length === 1,
    `ok=${r.body.ok} dispatch calls=${spy.calls.length}`);

  // --- 8. The forwarded envelope carries the RESOLVED sender identity (D6; spawn
  // spec test 9 — `enqueued_by` = the sender name), and the sender never supplies it.
  const fwd = spy.calls[0];
  check('the forwarded envelope carries the RESOLVED sender id + kind (the audit trail)',
    fwd && fwd.sender && fwd.sender.id === 'probe-agent' && fwd.sender.kind === 'agent',
    `sender=${JSON.stringify(fwd && fwd.sender)}`);
  check('the forwarded envelope carries the L2 client secret, NOT the sender token',
    fwd && fwd.auth === secret && fwd.auth !== AGENT_TOKEN,
    'auth === the per-boot internal secret (value withheld from evidence)');

  // A sender cannot forge its own audit identity: `enqueued_by` is refused at the
  // gateway's shape-check rather than silently overwritten downstream.
  r = await gw.handleRequest({
    credential: AGENT_TOKEN,
    body: { intent: 'enqueue-job', payload: { job_id: 'x', trigger_kind: 'scheduled', run_at: '2026-01-01T00:00:00Z', enqueued_by: 'owner' } },
  });
  check('a sender CANNOT supply enqueued_by (audit forgery refused at shape-check)',
    r.body.error && r.body.error.code === 'SHAPE_INVALID' && JSON.stringify(r.body.error.details || {}).includes('enqueued_by'),
    `code=${r.body.error && r.body.error.code} details=${JSON.stringify(r.body.error && r.body.error.details)}`);

  // --- 9. L2 — ONLY the gateway can call dispatch (internal-api-contract-spec test 2).
  // Exercised against the REAL internal API, not the spy: this is the guard that makes
  // "the server authenticates its single client" a real check in-process (DEC-3).
  const fakeStore = {
    listQueue: () => [],
    listJobs: () => [],
    getQueueRow: () => null,
    getExecution: () => null,
  };
  const realApi = createInternalApi({ heartStore: fakeStore, spawnManager: { config: { profiles: {} } }, secret });
  const envelope = (auth) => ({
    v: 1, id: 'probe-1', ts: new Date().toISOString(), auth,
    sender: { id: 'probe-agent', kind: 'agent', via: 'cli' },
    intent: 'inspect', payload: { target: 'queue' },
  });

  let d = await realApi.dispatch(envelope(undefined));
  check('L2: dispatch with NO secret -> AUTH_FAILED', d.error && d.error.code === 'AUTH_FAILED', `code=${d.error && d.error.code}`);
  d = await realApi.dispatch(envelope('wrong-secret'));
  check('L2: dispatch with a WRONG secret -> AUTH_FAILED', d.error && d.error.code === 'AUTH_FAILED', `code=${d.error && d.error.code}`);
  d = await realApi.dispatch(envelope(secret));
  check('L2 MUTATION: the CORRECT secret is accepted (the L2 guard DISCRIMINATES)', d.ok === true, `ok=${d.ok}`);

  // AUTH BEFORE INTENT DISPATCH: an unauthenticated caller naming a bogus intent gets
  // AUTH_FAILED, not UNKNOWN_INTENT — the contract vocabulary is not an oracle either.
  d = await realApi.dispatch({ ...envelope('wrong-secret'), intent: 'not-an-intent' });
  check('L2: auth is refused BEFORE intent dispatch (bogus intent + bad secret -> AUTH_FAILED)',
    d.error && d.error.code === 'AUTH_FAILED', `code=${d.error && d.error.code}`);
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SKIPPED_COUNT: ${skipped}`);
  out(`AUTHFAIL_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}).catch((err) => {
  out('ERROR:', err.message, err.stack);
  out(`SKIPPED_COUNT: ${skipped}`);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
}).finally(() => {
  try { fs.unlinkSync(sendersFile); } catch {}
});
