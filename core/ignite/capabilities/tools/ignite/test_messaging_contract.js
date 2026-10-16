#!/usr/bin/env node
'use strict';

// Suite for the messaging contract (connectors/messaging/capabilities/methods/messaging-contract.md):
// every Slack class method Ignite's production files call is listed there with a tag, and the
// inbound fixtures beside the contract fit its inbound event shape.
//
// A call site is a file of this folder, other than slack.js and the test programs, that calls a
// method of the Slack class (slack.js) on the client, reached in Ignite as `slack`, `deps.slack`,
// `slack()`, `client` or `socket`. In a file that indexes the client by a variable
// (status-ticker.js calls `client[method](...)`), a method named as a string is a call site too;
// elsewhere a string is a word, not a call. The contract's call-site table has one row per file and method:
// | `file.js` | `method` | tag | ... | with tag message, panel or ignite-internal. An untagged
// production call site fails, and so does a row whose call site no longer exists.
//
// The inbound event shape is the contract's table under "## Inbound event": | `field` | type |
// required or optional | ... |. Each fixture in messaging-contract/inbound-*.json must hold every
// required field with its type, only fields of the table, and nothing of another type.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const REPO = path.resolve(HERE, '..', '..', '..', '..', '..');
const CONTRACT = path.join(REPO, 'connectors', 'messaging', 'capabilities', 'methods', 'messaging-contract.md');
const FIXTURES = path.join(REPO, 'connectors', 'messaging', 'capabilities', 'methods', 'messaging-contract');
const RECEIVERS = ['slack', 'deps.slack', 'slack()', 'client', 'socket'];
const TAGS = new Set(['message', 'panel', 'ignite-internal']);

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

function lines(file) {
  return fs.readFileSync(file, 'utf8').split(/\r?\n/);
}

function escapeReg(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// The methods of the Slack class, read from slack.js: each `  name(` or `  async name(` line of the
// class body, constructor excluded.
function slackMethods() {
  const text = fs.readFileSync(path.join(HERE, 'slack.js'), 'utf8');
  const start = text.indexOf('class Slack {');
  assert.ok(start >= 0, 'slack.js declares class Slack');
  const body = text.slice(start);
  const names = new Set();
  for (const line of body.split(/\r?\n/)) {
    const match = line.match(/^ {2}(?:async )?([A-Za-z_$][\w$]*)\s*\(/);
    if (match && match[1] !== 'constructor') names.add(match[1]);
  }
  return [...names].sort();
}

function productionFiles() {
  return fs.readdirSync(HERE)
    .filter((name) => name.endsWith('.js') && !name.startsWith('test_') && name !== 'slack.js')
    .sort();
}

// Every (file, method) at which Ignite calls the Slack client, with the lines it was seen on.
function callSites(methods) {
  const found = new Map();
  const receiver = `(?:${RECEIVERS.map(escapeReg).join('|')})\\??`;
  for (const file of productionFiles()) {
    const text = fs.readFileSync(path.join(HERE, file), 'utf8');
    const indexed = new RegExp(`(^|[^\\w$.])${receiver}\\[\\w+\\]\\(`).test(text);
    text.split(/\r?\n/).forEach((line, index) => {
      const code = line.replace(/^\s*\/\/.*$/, '');
      for (const method of methods) {
        const direct = new RegExp(`(^|[^\\w$.])${receiver}\\.${method}\\(`);
        const named = new RegExp(`['"\`]${method}['"\`]`);
        if (direct.test(code) || (indexed && named.test(code))) {
          const key = `${file}:${method}`;
          if (!found.has(key)) found.set(key, { file, method, lines: [] });
          found.get(key).lines.push(index + 1);
        }
      }
    });
  }
  return found;
}

function contractRows() {
  const rows = new Map();
  const shape = [];
  let section = null;
  for (const line of lines(CONTRACT)) {
    if (line.startsWith('## ')) section = line.slice(3).trim();
    const call = line.match(/^\| `([\w.-]+\.js)` \| `([A-Za-z_$][\w$]*)` \| ([a-z-]+) \|/);
    if (call) {
      rows.set(`${call[1]}:${call[2]}`, { file: call[1], method: call[2], tag: call[3] });
      continue;
    }
    if (section === 'Inbound event') {
      const field = line.match(/^\| `(\w+)` \| ([^|]+?) \| (required|optional) \|/);
      if (field) shape.push({ field: field[1], type: field[2].trim(), presence: field[3] });
    }
  }
  return { rows, shape };
}

// A type cell: `string`, `number`, `boolean`, `array`, `object`, or those joined by ` or ` with `null`.
function fits(value, typeCell) {
  return typeCell.split(/\s+or\s+/).some((type) => {
    switch (type.trim()) {
      case 'null': return value === null;
      case 'string': return typeof value === 'string';
      case 'number': return typeof value === 'number' && Number.isFinite(value);
      case 'boolean': return typeof value === 'boolean';
      case 'array': return Array.isArray(value);
      case 'object': return value !== null && typeof value === 'object' && !Array.isArray(value);
      default: return false;
    }
  });
}

test('the contract exists beside its fixtures', () => {
  assert.ok(fs.existsSync(CONTRACT), `${CONTRACT} exists`);
  assert.ok(fs.existsSync(FIXTURES), `${FIXTURES} exists`);
});

test('every production call site of a Slack method is tagged in the contract', () => {
  const methods = slackMethods();
  assert.ok(methods.includes('postMessage') && methods.includes('connect'), `Slack methods read: ${methods.join(', ')}`);
  const sites = callSites(methods);
  assert.ok(sites.size > 0, 'Ignite calls the Slack client somewhere');
  const { rows } = contractRows();
  const untagged = [...sites.values()].filter((site) => !rows.has(`${site.file}:${site.method}`));
  const badTag = [...rows.values()].filter((row) => !TAGS.has(row.tag));
  assert.deepEqual(untagged.map((s) => `${s.file}:${s.method} (lines ${s.lines.join(', ')})`), [], 'untagged call sites');
  assert.deepEqual(badTag.map((r) => `${r.file}:${r.method}: ${r.tag}`), [], 'rows with a tag other than message, panel or ignite-internal');
  console.log(`  call sites: ${[...sites.values()].map((s) => `${s.file}:${s.method}`).join(', ')}`);
});

test('every call-site row of the contract still names a call site', () => {
  const sites = callSites(slackMethods());
  const { rows } = contractRows();
  const stale = [...rows.values()].filter((row) => !sites.has(`${row.file}:${row.method}`));
  assert.deepEqual(stale.map((r) => `${r.file}:${r.method}`), [], 'rows with no call site');
});

test('the inbound event shape names who, group, thread and text', () => {
  const { shape } = contractRows();
  const fields = shape.map((f) => f.field);
  for (const required of ['from', 'group', 'thread', 'text']) {
    assert.ok(fields.includes(required), `inbound shape has ${required}: ${fields.join(', ')}`);
  }
  assert.ok(shape.some((f) => f.presence === 'optional'), 'optional parts are marked');
});

test('the email and WhatsApp fixtures fit the inbound event shape', () => {
  const { shape } = contractRows();
  assert.ok(shape.length > 0, 'the contract has an inbound event table');
  const byField = new Map(shape.map((f) => [f.field, f]));
  const files = fs.readdirSync(FIXTURES).filter((name) => /^inbound-.*\.json$/.test(name)).sort();
  assert.ok(files.some((f) => f.includes('email')) && files.some((f) => f.includes('whatsapp')), `fixtures: ${files.join(', ')}`);
  for (const name of files) {
    const fixture = JSON.parse(fs.readFileSync(path.join(FIXTURES, name), 'utf8'));
    const problems = [];
    for (const { field, type, presence } of shape) {
      if (!(field in fixture)) {
        if (presence === 'required') problems.push(`${field} missing`);
        continue;
      }
      if (!fits(fixture[field], type)) problems.push(`${field} is not ${type}`);
    }
    for (const key of Object.keys(fixture)) {
      if (!byField.has(key)) problems.push(`${key} is not a field of the inbound event`);
    }
    assert.deepEqual(problems, [], `${name}`);
  }
});

(async () => {
  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      await fn();
      console.log(`PASS ${name}`);
    } catch (error) {
      failed += 1;
      console.log(`FAIL ${name}: ${error.message}`);
    }
  }
  process.exit(failed ? 1 : 0);
})();
