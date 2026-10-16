#!/usr/bin/env node
'use strict';

// adapter-check NAME — checks the adapters of the connector NAME under connectors/, the third line
// of the shape check in Building a connector (core/rbtv/capabilities/methods/building-a-connector.md).
// For each port the record names in `type` and `serves`, the adapter file that method names must
// load and export the port's shape:
//   payments        Ignite's own loader decides (core/ignite/capabilities/tools/ignite/payment-webhook.js
//                   loadProvider): path, header (lowercase), tokenEnv (a variable name) and read(body).
//                   The record's payment.* operations are covered by that validation.
//   any other port  `operations`, an object with one function per operation the record `provides`
//                   for that port, keyed by the operation's name; no operation of another port
//                   (the messaging port's operations are the rows of the messaging contract's
//                   Operations table; another port's are `<port>.<verb>`) and none the record
//                   does not provide.
// An operation in `provides` that belongs to no port of the record is a defect too.
// Exit 0: `shape ok` and one line per port on standard output. Exit 1: each defect on its own
// line on standard error, then the invocation to run again. Exit 2: usage.
//
// check(name, { root }) is exported for tests: root is the folder that holds connectors/; the
// loader and the messaging contract are always this repository's.

const fs = require('node:fs');
const path = require('node:path');

const REPO = path.resolve(__dirname, '..', '..', '..', '..', '..');
const LOADER = path.join(REPO, 'core', 'ignite', 'capabilities', 'tools', 'ignite', 'payment-webhook.js');
const CONTRACT = path.join(REPO, 'connectors', 'messaging', 'capabilities', 'methods', 'messaging-contract.md');
const COMPONENT_NAME = /^[a-z0-9][a-z0-9-]*$/;
const OPERATION = /^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*$/;

// The operations of the messaging port: the first cell of each row of the contract's Operations table.
function messagingOperations() {
  const text = fs.readFileSync(CONTRACT, 'utf8');
  const start = text.indexOf('\n## Operations');
  const end = text.indexOf('\n## ', start + 1);
  const found = new Set();
  for (const line of text.slice(start, end > 0 ? end : undefined).split(/\r?\n/)) {
    const match = line.match(/^\| `([a-z][a-z0-9-]*\.[a-z][a-z0-9-]*)` \|/);
    if (match) found.add(match[1]);
  }
  return found;
}

// Whether `operation` is one of `port`'s.
function belongs(port, operation, messaging) {
  if (port === 'payments') return operation.startsWith('payment.');
  if (port === 'messaging') return messaging.has(operation);
  return operation.startsWith(`${port}.`);
}

function adapterFile(port) {
  return port === 'payments' ? 'withdrawal-validation.js' : `${port}.js`;
}

function check(name, { root = REPO } = {}) {
  const defects = [];
  const ports = [];
  if (typeof name !== 'string' || !COMPONENT_NAME.test(name)) {
    return { defects: [`${name} is not a component name (lower-case letters, digits and dashes)`], ports };
  }
  const folder = path.join(root, 'connectors', name);
  const recordFile = path.join(folder, `${name}.json`);
  let record;
  try {
    record = JSON.parse(fs.readFileSync(recordFile, 'utf8'));
  } catch (error) {
    return { defects: [`no record at ${recordFile}: ${error.message}`], ports };
  }
  if (typeof record.type !== 'string' || !record.type) {
    return { defects: [`${recordFile} names no type: a connector's record names the port it is listed under`], ports };
  }
  const serves = Array.isArray(record.serves) ? record.serves : [];
  const provides = Array.isArray(record.provides) ? record.provides : [];
  const portNames = [record.type, ...serves];
  const lib = path.join(folder, 'capabilities', 'tools', name, 'lib');
  const messaging = portNames.includes('messaging') ? messagingOperations() : new Set();
  const shown = (file) => path.relative(root, file).split(path.sep).join('/');

  for (const operation of provides) {
    if (!OPERATION.test(operation)) defects.push(`provides ${operation}, which is not written <noun>.<verb>`);
    else if (!portNames.some((port) => belongs(port, operation, messaging))) {
      defects.push(`provides ${operation}, which belongs to no port in type or serves (${portNames.join(', ')})`);
    }
  }

  for (const port of portNames) {
    const file = path.join(lib, adapterFile(port));
    if (port === 'payments') {
      try {
        const { loadProvider } = require(LOADER);
        const adapter = loadProvider(name, { root });
        ports.push({ port, file: shown(file), exports: `path ${adapter.path}, header ${adapter.header}, tokenEnv ${adapter.tokenEnv}, read(body)` });
      } catch (error) {
        defects.push(`${port}: ${error.message}`);
      }
      continue;
    }
    let adapter;
    try {
      adapter = require(file);
    } catch (error) {
      defects.push(`${port}: no adapter at ${shown(file)} (${error.message.split('\n')[0]})`);
      continue;
    }
    const operations = adapter && adapter.operations;
    if (!operations || typeof operations !== 'object' || Array.isArray(operations)) {
      defects.push(`${port}: ${shown(file)} must export operations, an object keyed by operation name`);
      continue;
    }
    const expected = provides.filter((operation) => belongs(port, operation, messaging));
    for (const [operation, fn] of Object.entries(operations)) {
      if (typeof fn !== 'function') defects.push(`${port}: operations['${operation}'] is not a function`);
      if (!belongs(port, operation, messaging)) defects.push(`${port}: operations['${operation}'] is not an operation of the ${port} port`);
      else if (!provides.includes(operation)) defects.push(`${port}: operations['${operation}'] is not in the record's provides`);
    }
    for (const operation of expected) {
      if (!(operation in operations)) defects.push(`${port}: no operations['${operation}'] for the provided operation`);
    }
    ports.push({ port, file: shown(file), exports: Object.keys(operations).join(', ') || 'no operations' });
  }
  return { defects, ports };
}

const HELP = `adapter-check NAME

Checks the adapters of the connector NAME under connectors/: for each port in its
record's type and serves, the adapter file loads and exports the port's shape, and its
operations are the port's and the record's provides. A payments adapter is checked by
Ignite's own loader. Exits 0 and prints "shape ok" with one line per port; exits 1 and
prints each defect on standard error; exits 2 on usage.
`;

function main(argv) {
  if (argv.length === 1 && (argv[0] === '-h' || argv[0] === '--help')) {
    process.stdout.write(HELP);
    return 0;
  }
  if (argv.length !== 1 || argv[0].startsWith('-')) {
    process.stderr.write(`usage: adapter-check NAME\n${HELP}`);
    return 2;
  }
  const name = argv[0];
  const { defects, ports } = check(name);
  if (defects.length) {
    process.stderr.write(`${defects.join('\n')}\nfix the adapter, then run again: adapter-check ${name}\n`);
    return 1;
  }
  process.stdout.write(`shape ok\n${ports.map((p) => `${p.port}  ${p.file}  ${p.exports}`).join('\n')}\n`);
  return 0;
}

module.exports = { check };

if (require.main === module) process.exit(main(process.argv.slice(2)));
