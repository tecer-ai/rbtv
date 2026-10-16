#!/usr/bin/env node
'use strict';

// Suite for the messaging contract (connectors/messaging/capabilities/methods/messaging-contract.md):
// every Slack class method Ignite's production files call is listed there with a tag, the contract
// names every field the panel reads from a slash-command or interactive payload, and the inbound
// fixtures beside the contract fit its inbound event shape.
//
// A production file is a .js file anywhere under core/ignite/ other than the client (slack.js)
// and the test programs. A call site is a (file, method) at which such a file reaches a method
// of the Slack class through a name that holds the client. In each file the holders are `slack`
// (bare, `deps.slack`, `slack()`, `this.slack` and the like), every name assigned from a holder
// or from `new Slack(`, and a method name taken out of a holder by destructuring; a holder's
// method is reached by property (`slack.postMessage(`, `s.postMessage ({`, `deps.slack?.openIm`),
// by index in a file that calls the client that way (status-ticker.js calls `client[method](...)`,
// so a method named as a string there is a call site) or bare after destructuring. The contract's
// call-site table has one row per file and method: | `file.js` | `method` | tag | ... | with tag
// message, panel or ignite-internal, the file written relative to this folder. An untagged
// production call site fails, and so does a row whose call site no longer exists.
//
// The slash-command and interactive payloads are the contract's sections "Slash command" and
// "Buttons and forms". Every top-level field the panel's files read from a payload
// (`payload.trigger_id`, `payload.view`) is named in one of those sections' Field column.
//
// The inbound event shape is the contract's table under "## Inbound event": | `field` | type |
// required or optional | ... |. Each fixture in messaging-contract/inbound-*.json must hold every
// required field with its type, only fields of the table, and nothing of another type.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const IGNITE = path.resolve(HERE, '..', '..', '..');
const REPO = path.resolve(IGNITE, '..', '..');
const CLIENT = path.join(HERE, 'slack.js');
const CONTRACT = path.join(REPO, 'connectors', 'messaging', 'capabilities', 'methods', 'messaging-contract.md');
const FIXTURES = path.join(REPO, 'connectors', 'messaging', 'capabilities', 'methods', 'messaging-contract');
const TAGS = new Set(['message', 'panel', 'ignite-internal']);
const INTERACTION_SECTIONS = ['Slash command', 'Buttons and forms'];
const SKIPPED_DIRS = new Set(['node_modules', '.git']);

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
  const text = fs.readFileSync(CLIENT, 'utf8');
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

// Every production file under core/ignite/, each named relative to this folder.
function productionFiles() {
  const found = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const abs = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (!SKIPPED_DIRS.has(entry.name)) walk(abs);
        continue;
      }
      if (!entry.name.endsWith('.js') || entry.name.startsWith('test_') || abs === CLIENT) continue;
      found.push({ file: path.relative(HERE, abs).split(path.sep).join('/'), abs });
    }
  };
  walk(IGNITE);
  return found.sort((a, b) => a.file.localeCompare(b.file));
}

// The code of each line: a whole-line comment is dropped, and so is a trailing ` // ...`.
function codeLines(text) {
  return text.split(/\r?\n/).map((line) => line.replace(/^\s*\/\/.*$/, '').replace(/\s\/\/.*$/, ''));
}

// A receiver that holds the client: an optional property chain ending in a holder name, optionally
// called (`slack()`), as a regular-expression source.
function holderExpr(names) {
  return `(?:[\\w$]+\\??\\.)*(?:${[...names].map(escapeReg).join('|')})(?:\\(\\))?`;
}

// The names that hold the Slack client in one file, and the method names taken out of one by
// destructuring. Grows until no assignment adds a name.
function holders(code) {
  const names = new Set(['slack']);
  const bare = new Set();
  const lhs = '(?:^|[^\\w$.])(?:(?:const|let|var)\\s+)?([A-Za-z_$][\\w$]*)\\s*=\\s*';
  for (;;) {
    const before = names.size + bare.size;
    const holder = holderExpr(names);
    const assigned = new RegExp(`${lhs}(?:await\\s+)?${holder}(?:\\s*\\|\\|\\s*null)?\\s*(?:;|$)`);
    const ternary = new RegExp(`${lhs}[^;]*\\?\\s*${holder}\\s*:`);
    const made = new RegExp(`${lhs}new Slack\\s*\\(`);
    const taken = new RegExp(`(?:const|let|var)\\s*\\{([^}]*)\\}\\s*=\\s*(?:await\\s+)?${holder}\\s*(?:;|$)`);
    for (const line of code) {
      for (const form of [assigned, ternary, made]) {
        const match = line.match(form);
        if (match) names.add(match[1]);
      }
      const match = line.match(taken);
      if (match) {
        for (const part of match[1].split(',')) {
          const name = part.split(':').pop().trim().replace(/\s*=.*$/, '');
          if (/^[A-Za-z_$][\w$]*$/.test(name)) bare.add(name);
        }
      }
    }
    if (names.size + bare.size === before) return { names, bare };
  }
}

// Every (file, method) at which Ignite reaches the Slack client, with the lines it was seen on.
function callSites(methods) {
  const found = new Map();
  const note = (file, method, index) => {
    const key = `${file}:${method}`;
    if (!found.has(key)) found.set(key, { file, method, lines: [] });
    found.get(key).lines.push(index + 1);
  };
  for (const { file, abs } of productionFiles()) {
    const code = codeLines(fs.readFileSync(abs, 'utf8'));
    const { names, bare } = holders(code);
    const holder = holderExpr(names);
    const indexed = new RegExp(`(?:^|[^\\w$])${holder}\\s*\\[\\s*[^\\]]+\\s*\\]\\s*\\(`).test(code.join('\n'));
    code.forEach((line, index) => {
      for (const method of methods) {
        const property = new RegExp(`(?:^|[^\\w$])${holder}\\s*\\??\\.\\s*${method}\\b`);
        const named = new RegExp(`['"\`]${method}['"\`]`);
        const direct = new RegExp(`(?:^|[^\\w$.])${method}\\s*\\(`);
        if (property.test(line) || (indexed && named.test(line)) || (bare.has(method) && direct.test(line))) {
          note(file, method, index);
        }
      }
    });
  }
  return found;
}

function contractRows() {
  const rows = new Map();
  const shape = [];
  const sections = new Map();
  let section = null;
  for (const line of lines(CONTRACT)) {
    if (line.startsWith('## ')) {
      section = line.slice(3).trim();
      sections.set(section, []);
      continue;
    }
    if (section) sections.get(section).push(line);
    const call = line.match(/^\| `([\w./-]+\.js)` \| `([A-Za-z_$][\w$]*)` \| ([a-z-]+) \|/);
    if (call) {
      rows.set(`${call[1]}:${call[2]}`, { file: call[1], method: call[2], tag: call[3] });
      continue;
    }
    if (section === 'Inbound event') {
      const field = line.match(/^\| `(\w+)` \| ([^|]+?) \| (required|optional) \|/);
      if (field) shape.push({ field: field[1], type: field[2].trim(), presence: field[3] });
    }
  }
  return { rows, shape, sections };
}

// The first segment of every field a section's table names in its Field column: `user.id` → user,
// `actions[0].action_id` → actions.
function sectionFields(sectionLines) {
  const fields = new Set();
  let column = -1;
  for (const line of sectionLines) {
    if (!line.startsWith('|')) continue;
    const cells = line.split('|').slice(1, -1).map((cell) => cell.trim());
    if (column < 0) {
      column = cells.indexOf('Field');
      continue;
    }
    if (column >= cells.length || /^-+$/.test(cells[column])) continue;
    for (const span of cells[column].match(/`[^`]+`/g) || []) {
      for (const part of span.slice(1, -1).split(/,|\s+or\s+/)) {
        const head = part.trim().match(/^[A-Za-z_$][\w$]*/);
        if (head) fields.add(head[0]);
      }
    }
  }
  return fields;
}

// Every top-level field the given files read from a payload: `payload.user_id`, `payload?.view`.
function payloadFields(files) {
  const read = new Map();
  for (const { file, abs } of files) {
    codeLines(fs.readFileSync(abs, 'utf8')).forEach((line, index) => {
      for (const match of line.matchAll(/\bpayload\??\.([A-Za-z_$][\w$]*)/g)) {
        if (!read.has(match[1])) read.set(match[1], []);
        read.get(match[1]).push(`${file}:${index + 1}`);
      }
    });
  }
  return read;
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

test('the contract names every payload field the panel reads from a slash command, a button or a form', () => {
  const { rows, sections } = contractRows();
  const named = new Set();
  for (const name of INTERACTION_SECTIONS) {
    assert.ok(sections.has(name), `the contract has a section "${name}"`);
    for (const field of sectionFields(sections.get(name))) named.add(field);
  }
  const forms = sections.get('Buttons and forms').join('\n');
  assert.ok(forms.includes('`block_actions`') && forms.includes('`view_submission`'), 'Buttons and forms covers block_actions and view_submission');
  const panelFiles = new Set([...rows.values()].filter((row) => row.tag === 'panel').map((row) => row.file));
  assert.ok(panelFiles.size > 0, 'the contract tags a panel call site');
  const read = payloadFields(productionFiles().filter((entry) => panelFiles.has(entry.file)));
  assert.ok(read.has('trigger_id') && read.has('view'), `the panel reads payload fields: ${[...read.keys()].join(', ')}`);
  const uncovered = [...read.entries()].filter(([field]) => !named.has(field));
  assert.deepEqual(uncovered.map(([field, at]) => `${field} (${at.join(', ')})`), [], 'payload fields the contract does not name');
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
