'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-secret-add.out');
fs.writeFileSync(outPath, '');

const { createInternalApi, ENVELOPE_VERSION } = require('../dispatch');
const { parseRequest } = require('../../../gateway/parse');
const { createAuthzPolicy } = require('../authz');
const { applySecretAdd, envFileHasName } = require('../secret-add');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('evidence-class: FIXTURE in-process parse+dispatch+authz; scratch env under os.tmpdir(); never the live .env');

  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'secret-add-probe-'));
  const envPath = path.join(root, '.rbtv', 'config', '.env');
  fs.mkdirSync(path.dirname(envPath), { recursive: true });
  fs.writeFileSync(envPath, '# fixture\nKEEP_ME=1\n', 'utf8');
  fs.writeFileSync(path.join(root, 'rbtv.json'), JSON.stringify({ env_file: '.rbtv/config/.env' }), 'utf8');

  const DUMMY = 'dummy-secret-add2-dispatch-a1b2c3';
  const NAME = 'TEST_SECRET_ADD2_DISPATCH';

  const secret = crypto.randomBytes(32).toString('hex');
  const logs = [];
  const api = createInternalApi({
    heartStore: {},
    spawnManager: {},
    secret,
    workspaceRoot: root,
    logger: (row) => logs.push(row),
  });

  const OWNER = { id: 'probe-owner', kind: 'owner' };
  const AGENT = { id: 'probe-agent', kind: 'agent' };
  const WORKER = { id: 'probe-agent', kind: 'agent', seat: 'crashy' };
  const MASTER = { id: 'probe-agent', kind: 'agent', seat: 'goal-master' };
  const BRIDGE = { id: 'probe-bridge', kind: 'bridge' };

  async function call(sender, payload) {
    let parsed;
    try {
      parsed = parseRequest({ intent: 'secret-add', payload });
    } catch (err) {
      return { body: { ok: false, error: { code: err.code, message: err.message } }, gatewayRefused: true };
    }
    const res = await api.dispatch({
      v: ENVELOPE_VERSION,
      id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      auth: secret,
      sender,
      intent: 'secret-add',
      payload: parsed,
    });
    return { body: res, gatewayRefused: false };
  }

  const policy = createAuthzPolicy();
  check('authz: owner allowed', policy.canSecretAdd({ sender: OWNER }).allowed === true);
  check('authz: agent with no proven seat allowed (G-123 approximation)',
    policy.canSecretAdd({ sender: AGENT }).allowed === true);
  check('authz: proven goal-master allowed',
    policy.canSecretAdd({ sender: MASTER }).allowed === true);
  check('authz: proven worker refused',
    policy.canSecretAdd({ sender: WORKER }).allowed === false,
    policy.canSecretAdd({ sender: WORKER }).reason);
  check('authz: bridge refused',
    policy.canSecretAdd({ sender: BRIDGE }).allowed === false);

  let r = await call(BRIDGE, { name: NAME, from_file: '/tmp/x' });
  check('wire: bridge is UNAUTHORIZED_SENDER',
    r.body.error && r.body.error.code === 'UNAUTHORIZED_SENDER' && r.gatewayRefused === false,
    `code=${r.body.error && r.body.error.code}`);

  r = await call(WORKER, { name: NAME, from_file: '/tmp/x' });
  check('wire: proven worker is UNAUTHORIZED_SENDER',
    r.body.error && r.body.error.code === 'UNAUTHORIZED_SENDER',
    r.body.error && r.body.error.message);

  const drop = path.join(root, 'key.txt');
  fs.writeFileSync(drop, DUMMY + '\n', 'utf8');
  r = await call(OWNER, { name: NAME, from_file: drop });
  const envText = fs.readFileSync(envPath, 'utf8');
  check('happy: owner appends, drop consumed, value not in result',
    r.body.ok === true
      && r.body.result && r.body.result.appended === true
      && r.body.result.name === NAME
      && !fs.existsSync(drop)
      && envText.includes(NAME + '=' + DUMMY)
      && !JSON.stringify(r.body.result).includes(DUMMY),
    `ok=${r.body.ok} result=${JSON.stringify(r.body.result)} env_has=${envText.includes(NAME + '=')}`);

  const logBlob = JSON.stringify(logs);
  check('happy: dummy VALUE absent from logger rows',
    !logBlob.includes(DUMMY),
    `log_hits=${logBlob.includes(DUMMY)}`);

  const drop2 = path.join(root, 'key2.txt');
  fs.writeFileSync(drop2, DUMMY + '\n', 'utf8');
  r = await call(OWNER, { name: NAME, from_file: drop2 });
  check('duplicate NAME: VALIDATION_FAILED already exists, drop left',
    r.body.ok === false
      && r.body.error && r.body.error.code === 'VALIDATION_FAILED'
      && /already exists/.test(r.body.error.message)
      && fs.existsSync(drop2)
      && !r.body.error.message.includes(DUMMY),
    r.body.error && r.body.error.message);

  const goalsDrop = path.join(root, '.rbtv', 'goals', 'g', 'mailbox.txt');
  fs.mkdirSync(path.dirname(goalsDrop), { recursive: true });
  fs.writeFileSync(goalsDrop, DUMMY + '\n', 'utf8');
  r = await call(OWNER, { name: 'TEST_SECRET_ADD2_GOALS', from_file: goalsDrop });
  check('drop under .rbtv/goals/: refused, drop left',
    r.body.ok === false && /\.rbtv\/goals\//.test(r.body.error && r.body.error.message)
      && fs.existsSync(goalsDrop) && !(r.body.error.message || '').includes(DUMMY),
    r.body.error && r.body.error.message);

  r = await call(OWNER, { name: NAME, from_file: drop2, env_file: '/tmp/nope' });
  check('caller cannot redirect: unknown field env_file refused at the door',
    r.gatewayRefused === true,
    `gatewayRefused=${r.gatewayRefused} err=${r.body.error && r.body.error.message}`);

  check('envFileHasName sees KEEP_ME and the appended NAME',
    envFileHasName(envText, 'KEEP_ME') && envFileHasName(envText, NAME));

  const mutDir = fs.mkdtempSync(path.join(os.tmpdir(), 'secret-add-mut-'));
  const srcPath = path.join(__dirname, '..', 'secret-add.js');
  const src = fs.readFileSync(srcPath, 'utf8');
  const needle = "if (line.split('=', 1)[0].trim() === name) return true;";
  const repl = "if (line.split('=', 1)[0].trim() === name) return false;";
  check('red-proof: mutation needle found', src.includes(needle));
  if (src.includes(needle)) {
    const mutPath = path.join(mutDir, 'secret-add.js');
    fs.writeFileSync(mutPath, src.replace(needle, repl, 1), 'utf8');
    const mut = require(mutPath);
    const drop3 = path.join(root, 'key3.txt');
    fs.writeFileSync(drop3, DUMMY + '\n', 'utf8');
    const mutOut = mut.applySecretAdd({ workspaceRoot: root, name: NAME, fromFile: drop3 });
    const mutText = fs.readFileSync(envPath, 'utf8');
    const dupCount = mutText.split(NAME + '=').length - 1;
    check('red-proof: duplicate-check mutated away → second append lands (COPY, discarded)',
      mutOut.ok === true && dupCount >= 2 && !fs.existsSync(drop3),
      `ok=${mutOut.ok} dup_count=${dupCount}`);
  }

  try { fs.rmSync(root, { recursive: true, force: true }); } catch {}
  try { fs.rmSync(mutDir, { recursive: true, force: true }); } catch {}

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`RESULT: ${failed.length ? 'FAIL' : 'PASS'} — ${checks.length - failed.length}/${checks.length} checks`);
  out(`WALL_MS ${Date.now() - start}`);
  out(`EXIT ${failed.length ? 1 : 0}`);
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(failed.length ? 1 : 0);
}

main().catch((err) => {
  out(`PROBE FAULT: ${err && err.stack ? err.stack : err}`);
  out('EXIT 1');
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(1);
});
