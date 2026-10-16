#!/usr/bin/env node
'use strict';

// Suite for adapter-check: check() against temporary connectors and the real Asaas adapter, and the
// command's exit statuses.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const { check } = require('./adapter-check.js');
const PROGRAM = path.join(__dirname, 'adapter-check.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

// A temporary tree holding one connector: its record and the adapter modules given as { file: source }.
function connector(name, record, modules) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'adapter-check-'));
  const lib = path.join(root, 'connectors', name, 'capabilities', 'tools', name, 'lib');
  fs.mkdirSync(lib, { recursive: true });
  fs.writeFileSync(path.join(root, 'connectors', name, `${name}.json`), JSON.stringify({ description: 'probe', dependencies: [], ...record }));
  for (const [file, source] of Object.entries(modules)) fs.writeFileSync(path.join(lib, file), source);
  return root;
}

const fn = (names) => `module.exports = { operations: { ${names.map((n) => `'${n}': async () => ({})`).join(', ')} } };\n`;

test('the Asaas adapter passes through Ignite\'s loader', () => {
  const { defects, ports } = check('asaas');
  assert.deepEqual(defects, []);
  assert.equal(ports.length, 1);
  assert.equal(ports[0].port, 'payments');
  assert.match(ports[0].exports, /^path \/asaas\/withdrawal-validation, header asaas-access-token, tokenEnv ASAAS_WEBHOOK_TOKEN, read\(body\)$/);
});

test('a payments adapter the loader refuses is a defect with the loader\'s reason', () => {
  const root = connector('probepay', { type: 'payments', provides: ['payment.send'] }, {
    'withdrawal-validation.js': 'module.exports = { path: null, header: null, tokenEnv: null, read: 42 };\n',
  });
  const { defects } = check('probepay', { root });
  assert.equal(defects.length, 1);
  assert.match(defects[0], /^payments: payments connector probepay: .*must export path, header \(lowercase\), tokenEnv and read\(body\)$/);
});

test('an operation of another port exported from an adapter is a defect', () => {
  const root = connector('probestore', { type: 'storage', provides: ['storage.read'] }, { 'storage.js': fn(['storage.read', 'calendar.list']) });
  assert.deepEqual(check('probestore', { root }).defects, ["storage: operations['calendar.list'] is not an operation of the storage port"]);
});

test('two ports with their operations swapped fail on both', () => {
  const root = connector('probeswap', { type: 'calendar', serves: ['storage'], provides: ['calendar.list', 'storage.read'] }, {
    'calendar.js': fn(['storage.read']), 'storage.js': fn(['calendar.list']),
  });
  assert.deepEqual(check('probeswap', { root }).defects, [
    "calendar: operations['storage.read'] is not an operation of the calendar port",
    "calendar: no operations['calendar.list'] for the provided operation",
    "storage: operations['calendar.list'] is not an operation of the storage port",
    "storage: no operations['storage.read'] for the provided operation",
  ]);
});

test('an operation the record does not provide, a missing function and a non-function are defects', () => {
  const root = connector('probeextra', { type: 'storage', provides: ['storage.read', 'storage.list'] }, {
    'storage.js': "module.exports = { operations: { 'storage.read': async () => ({}), 'storage.write': async () => ({}), 'storage.list': 1 } };\n",
  });
  assert.deepEqual(check('probeextra', { root }).defects, [
    "storage: operations['storage.write'] is not in the record's provides",
    "storage: operations['storage.list'] is not a function",
  ]);
});

test('a provided operation of no port in the record, and a missing adapter, are defects', () => {
  const root = connector('probenone', { type: 'storage', provides: ['storage.read', 'calendar.list'] }, {});
  const { defects } = check('probenone', { root });
  assert.equal(defects[0], 'provides calendar.list, which belongs to no port in type or serves (storage)');
  assert.match(defects[1], /^storage: no adapter at connectors\/probenone\/capabilities\/tools\/probenone\/lib\/storage\.js /);
  assert.equal(defects.length, 2);
});

test('a messaging adapter takes the contract\'s operations and no other', () => {
  const ok = connector('probemsg', { type: 'messaging', provides: ['message.send', 'message.history'] }, { 'messaging.js': fn(['message.send', 'message.history']) });
  assert.deepEqual(check('probemsg', { root: ok }).defects, []);
  const bad = connector('probemsg2', { type: 'messaging', provides: ['message.send', 'message.pin'] }, { 'messaging.js': fn(['message.send', 'message.pin']) });
  assert.deepEqual(check('probemsg2', { root: bad }).defects, [
    'provides message.pin, which belongs to no port in type or serves (messaging)',
    "messaging: operations['message.pin'] is not an operation of the messaging port",
  ]);
});

test('a correct connector of another port passes and lists its operations', () => {
  const root = connector('probeok', { type: 'storage', provides: ['storage.read'] }, { 'storage.js': fn(['storage.read']) });
  const { defects, ports } = check('probeok', { root });
  assert.deepEqual(defects, []);
  assert.deepEqual(ports, [{ port: 'storage', file: 'connectors/probeok/capabilities/tools/probeok/lib/storage.js', exports: 'storage.read' }]);
});

test('no record, no type and a bad name are each one defect', () => {
  assert.match(check('no-such-connector').defects[0], /^no record at /);
  const root = connector('probetype', {}, {});
  assert.match(check('probetype', { root }).defects[0], /names no type/);
  assert.match(check('../asaas').defects[0], /is not a component name/);
});

test('the command exits 0 with shape ok, 1 with defects on standard error, 2 on usage', () => {
  const run = (...args) => spawnSync(process.execPath, [PROGRAM, ...args], { encoding: 'utf8', cwd: os.tmpdir() });
  const ok = run('asaas');
  assert.equal(ok.status, 0);
  assert.match(ok.stdout, /^shape ok\npayments  connectors\/asaas\/capabilities\/tools\/asaas\/lib\/withdrawal-validation\.js  path /);
  assert.equal(ok.stderr, '');
  const bad = run('no-such-connector');
  assert.equal(bad.status, 1);
  assert.equal(bad.stdout, '');
  assert.match(bad.stderr, /^no record at .*\nfix the adapter, then run again: adapter-check no-such-connector\n$/);
  assert.equal(run().status, 2);
  assert.equal(run('a', 'b').status, 2);
  const help = run('-h');
  assert.equal(help.status, 0);
  assert.match(help.stdout, /^adapter-check NAME\n/);
});

(async () => {
  let failed = 0;
  for (const { name, fn: body } of tests) {
    try {
      await body();
      console.log(`PASS ${name}`);
    } catch (error) {
      failed += 1;
      console.log(`FAIL ${name}: ${error.message}`);
    }
  }
  process.exit(failed ? 1 : 0);
})();
