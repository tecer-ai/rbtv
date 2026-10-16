#!/usr/bin/env node
'use strict';

// Suite for the messaging contract (connectors/messaging/capabilities/methods/messaging-contract.md).
// It parses no JavaScript: two lists beside the contract name every occurrence of one word, found
// with one regular expression on each file's lines, and what each one is.
//   slack-uses.json: every occurrence of the word `slack` (\bslack\b, in code, string or comment) in
//     every production file (a .js file under core/ignite/ other than slack.js and the test programs),
//     with its `kind`: call:<Method> (the Slack class methods reached from it, on the line or through
//     the name the line binds the client to, several joined by commas), config, path, message,
//     binding or comment. The contract's Checks section defines the kinds.
//   payload-uses.json: every occurrence of the word `payload` in the files the contract tags `panel`,
//     with `reads`: the payload field paths read on the line, or through the name the line binds.
// A list is `uses`: each entry the file (relative to this folder), the trimmed line text and the 0-based
// nth occurrence of that text in the file. A live occurrence not listed fails, a listed one no longer
// live fails, a kind or reads of "?" fails. Every call:<Method> needs a contract call-site row for
// that file and method, with a tag, and every row needs a call entry; every read must be a field path
// of the contract's Slash command or Buttons and forms tables. A file that binds the client or the
// payload to a name (a binding, call: or "?" entry; every panel file for payload) can gain a call or a
// read through that name on a line holding neither word, so `files` maps each such file to the sha256
// of its content (CRLF read as LF) and the test fails when the file changed. The inbound fixtures are
// checked against the contract's inbound event table. `--write-fixture` rewrites both lists from the
// live occurrences, keeping what is known and putting "?" on each new entry for the author to fill in;
// on a changed file it records the new hash and resets that file's binding, call: and reads entries to
// "?", so the test fails until the author restates by hand what the bound name reaches.

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const IGNITE = path.resolve(HERE, '..', '..', '..');
const METHODS = path.resolve(IGNITE, '..', '..', 'connectors', 'messaging', 'capabilities', 'methods');
const CONTRACT = path.join(METHODS, 'messaging-contract.md');
const FIXTURES = path.join(METHODS, 'messaging-contract');
const TAGS = ['message', 'panel', 'ignite-internal'];
const KINDS = ['config', 'path', 'message', 'binding', 'comment'];
const REQUIRED_READS = ['trigger_id', 'actions[0].action_id', 'view.callback_id', 'view.state.values'];
const read = (file) => fs.readFileSync(file, 'utf8');
const keyOf = (e) => `${e.file}\u0000${e.line}\u0000${e.nth}`;
const fixtureOf = (word) => path.join(FIXTURES, `${word}-uses.json`);
const hashOf = (abs) => crypto.createHash('sha256').update(read(abs).replace(/\r\n/g, '\n')).digest('hex');
// An entry whose file may bind the client or the payload to a name: hashed, and reset when the file changed.
const binds = (entry, field) => field === 'reads' || ['binding', '?'].includes(entry.kind) || String(entry.kind).startsWith('call:');
const boundFiles = (uses, field) => new Set(uses.filter((e) => binds(e, field)).map((e) => e.file));

// The methods of the Slack class: each `  name(` or `  async name(` line of slack.js's class body.
function slackMethods() {
  const body = read(path.join(HERE, 'slack.js')).split('class Slack {')[1];
  assert.ok(body, 'slack.js declares class Slack');
  return [...body.matchAll(/^ {2}(?:async )?([A-Za-z_$][\w$]*)\s*\(/gm)].map((m) => m[1]).filter((n) => n !== 'constructor');
}

function productionFiles(dir = IGNITE, found = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, entry.name);
    if (entry.isDirectory()) { if (entry.name !== 'node_modules' && entry.name !== '.git') productionFiles(abs, found); continue; }
    if (entry.name.endsWith('.js') && !entry.name.startsWith('test_') && abs !== path.join(HERE, 'slack.js')) found.push({ file: path.relative(HERE, abs).split(path.sep).join('/'), abs });
  }
  return found.sort((a, b) => a.file.localeCompare(b.file));
}

// Every occurrence of `word` in the files: file, trimmed line text, nth occurrence of that text, where.
function occurrences(files, word) {
  const found = [];
  for (const { file, abs } of files) {
    const seen = new Map();
    read(abs).split(/\r?\n/).forEach((raw, i) => {
      const line = raw.trim();
      for (const _ of line.matchAll(new RegExp(`\\b${word}\\b`, 'g'))) {
        const nth = seen.get(line) || 0;
        seen.set(line, nth + 1);
        found.push({ file, line, nth, at: `${file}:${i + 1}` });
      }
    });
  }
  return found;
}

// The list of `word` and its problems against the live occurrences of the files: a new use, a stale
// entry, a "?", a bound file whose content differs from its recorded hash.
function compare(word, files, field) {
  const { files: hashes, uses: listed } = JSON.parse(read(fixtureOf(word)));
  const live = occurrences(files, word);
  const known = new Set(listed.map(keyOf));
  const alive = new Set(live.map(keyOf));
  const problems = live.filter((e) => !known.has(keyOf(e))).map((e) => `new use of ${word} ${e.at}: ${e.line}: add it to ${word}-uses.json with its ${field}`);
  for (const e of listed) {
    if (!alive.has(keyOf(e))) problems.push(`stale entry in ${word}-uses.json ${e.file}: ${e.line} (${e.nth}): the line is gone; remove it`);
    else if (e[field] === '?' || e[field] === undefined) problems.push(`${word}-uses.json ${e.file}: ${e.line} (${e.nth}): fill in its ${field}`);
  }
  const [what, restate] = field === 'kind' ? ['the client', 'its call: and binding entries'] : ['the payload', 'its reads'];
  for (const file of boundFiles(listed, field)) {
    const abs = files.find((f) => f.file === file)?.abs;
    if (!abs || hashes[file] === undefined) problems.push(`file ${file} binds ${what} to a name and ${word}-uses.json holds no hash of it; run --write-fixture`);
    else if (hashes[file] !== hashOf(abs)) problems.push(`changed file ${file} binds ${what} to a name; re-run --write-fixture and restate ${restate}`);
  }
  return { listed, problems };
}

// The contract's call-site rows (| `file.js` | `method` | tag |), its inbound event table and its sections.
function contract() {
  const rows = new Map();
  const shape = [];
  const sections = new Map();
  let section = null;
  for (const line of read(CONTRACT).split(/\r?\n/)) {
    if (line.startsWith('## ')) { section = line.slice(3).trim(); sections.set(section, []); continue; }
    if (section) sections.get(section).push(line);
    const call = line.match(/^\| `([\w./-]+\.js)` \| `([A-Za-z_$][\w$]*)` \| ([a-z-]+) \|/);
    if (call) rows.set(`${call[1]}:${call[2]}`, call[3]);
    const field = section === 'Inbound event' && line.match(/^\| `(\w+)` \| ([^|]+?) \| (required|optional) \|/);
    if (field) shape.push({ field: field[1], type: field[2].trim(), presence: field[3] });
  }
  return { rows, shape, sections };
}

// Every path a section's table names in its Field column (`user.id`, `actions[0].action_id`; a cell may
// name several, joined by `,` or ` or `).
function sectionFields(sectionLines) {
  const table = sectionLines.filter((l) => l.startsWith('|')).map((l) => l.split('|').slice(1, -1).map((c) => c.trim()));
  const column = table.length ? table[0].indexOf('Field') : -1;
  const cells = table.slice(1).flatMap((cells) => (cells[column] || '').match(/`[^`]+`/g) || []);
  return cells.flatMap((span) => span.slice(1, -1).split(/,|\s+or\s+/)).map((p) => p.trim()).filter((p) => /^[A-Za-z_$][\w$]*(?:\[\d+\]|\.[A-Za-z_$][\w$]*)*$/.test(p));
}

const panelFiles = () => {
  const tagged = new Set([...contract().rows].filter(([, tag]) => tag === 'panel').map(([key]) => key.split(':')[0]));
  return productionFiles().filter((entry) => tagged.has(entry.file));
};

// A type cell: `string`, `number`, `boolean`, `array`, `object`, or those joined by ` or ` with `null`.
const TYPES = { null: (v) => v === null, string: (v) => typeof v === 'string', boolean: (v) => typeof v === 'boolean',
  number: (v) => Number.isFinite(v), array: Array.isArray, object: (v) => v !== null && typeof v === 'object' && !Array.isArray(v) };
const fits = (value, typeCell) => typeCell.split(/\s+or\s+/).some((type) => (TYPES[type.trim()] || (() => false))(value));

if (process.argv.includes('--write-fixture')) {
  for (const [word, files, field] of [['slack', productionFiles(), 'kind'], ['payload', panelFiles(), 'reads']]) {
    const old = fs.existsSync(fixtureOf(word)) ? JSON.parse(read(fixtureOf(word))) : { files: {}, uses: [] };
    const known = new Map(old.uses.map((e) => [keyOf(e), e[field]]));
    const uses = occurrences(files, word).map(({ file, line, nth }) => ({ file, line, nth, [field]: known.has(keyOf({ file, line, nth })) ? known.get(keyOf({ file, line, nth })) : '?' }));
    const hashes = {};
    for (const file of boundFiles(uses, field)) {
      hashes[file] = hashOf(files.find((f) => f.file === file).abs);
      if (old.files[file] === undefined || old.files[file] === hashes[file]) continue;
      for (const e of uses) if (e.file === file && binds(e, field) && e[field] !== '?') { console.log(`reset ${file}: ${e.line} (${e.nth}): ${JSON.stringify(e[field])} -> "?"`); e[field] = '?'; }
    }
    fs.writeFileSync(fixtureOf(word), `${JSON.stringify({ files: hashes, uses }, null, 2)}\n`);
    console.log(`wrote ${word}-uses.json: ${uses.length} entries, ${uses.filter((e) => e[field] === '?').length} to fill in, ${Object.keys(hashes).length} files hashed`);
  }
  process.exit(0);
}

const tests = {
  'every use of the word slack in a production file is listed in slack-uses.json with its kind': () => {
    const methods = slackMethods();
    assert.ok(methods.includes('postMessage') && methods.includes('connect'), `Slack methods read: ${methods.join(', ')}`);
    const { listed, problems } = compare('slack', productionFiles(), 'kind');
    const { rows } = contract();
    const called = new Set();
    for (const entry of listed) {
      const where = `slack-uses.json ${entry.file}: ${entry.line} (${entry.nth})`;
      if (!String(entry.kind).startsWith('call:')) { if (entry.kind !== '?' && !KINDS.includes(entry.kind)) problems.push(`${where}: kind ${entry.kind} is not one of call:<Method>, ${KINDS.join(', ')}`); continue; }
      for (const method of entry.kind.slice(5).split(',')) {
        const tag = rows.get(`${entry.file}:${method}`);
        if (!methods.includes(method)) problems.push(`${where}: ${method} is not a method of the Slack class`);
        else if (!tag) problems.push(`${where}: call of ${method} has no call-site row for ${entry.file} in the contract; add one with its tag`);
        else if (!TAGS.includes(tag)) problems.push(`contract row ${entry.file} ${method}: tag ${tag} is not ${TAGS.join(', ')}`);
        called.add(`${entry.file}:${method}`);
      }
    }
    for (const key of rows.keys()) if (!called.has(key)) problems.push(`contract row ${key.replace(':', ' ')} has no call entry in slack-uses.json; remove the row`);
    assert.deepEqual(problems, [], 'slack uses');
    const counts = new Map();
    for (const kind of listed.map((e) => e.kind.replace(/:.*/, ''))) counts.set(kind, (counts.get(kind) || 0) + 1);
    console.log(`  call sites (${called.size}): ${[...called].join(', ')}\n  slack uses (${listed.length}): ${[...counts].map(([k, n]) => `${k} ${n}`).join(', ')}`);
  },
  'every read of a payload by the panel files is listed in payload-uses.json and named by the contract': () => {
    const { sections } = contract();
    const named = new Set();
    for (const name of ['Slash command', 'Buttons and forms']) {
      assert.ok(sections.has(name), `the contract has a section "${name}"`);
      for (const field of sectionFields(sections.get(name))) named.add(field);
    }
    const forms = sections.get('Buttons and forms').join('\n');
    assert.ok(forms.includes('`block_actions`') && forms.includes('`view_submission`'), 'Buttons and forms covers block_actions and view_submission');
    const files = panelFiles();
    assert.ok(files.length > 0, 'the contract tags a panel call site');
    const { listed, problems } = compare('payload', files, 'reads');
    const reads = new Set();
    for (const entry of listed) {
      for (const field of Array.isArray(entry.reads) ? entry.reads : []) {
        if (!named.has(field)) problems.push(`payload-uses.json ${entry.file}: ${entry.line} (${entry.nth}): reads ${field}, which no Slash command or Buttons and forms row names`);
        reads.add(field);
      }
    }
    for (const field of REQUIRED_READS) if (!reads.has(field)) problems.push(`no panel file reads ${field}`);
    assert.deepEqual(problems, [], 'payload reads');
    console.log(`  payload reads (${listed.length} uses): ${[...reads].sort().join(', ')}`);
  },
  'the inbound event shape names who, group, thread and text, and the fixtures fit it': () => {
    const { shape } = contract();
    const fields = shape.map((f) => f.field);
    for (const required of ['from', 'group', 'thread', 'text']) assert.ok(fields.includes(required), `inbound shape has ${required}: ${fields.join(', ')}`);
    assert.ok(shape.some((f) => f.presence === 'optional'), 'optional parts are marked');
    const files = fs.readdirSync(FIXTURES).filter((name) => /^inbound-.*\.json$/.test(name)).sort();
    assert.ok(files.some((f) => f.includes('email')) && files.some((f) => f.includes('whatsapp')), `fixtures: ${files.join(', ')}`);
    for (const name of files) {
      const fixture = JSON.parse(read(path.join(FIXTURES, name)));
      const problems = shape.filter((f) => !(f.field in fixture) && f.presence === 'required').map((f) => `${f.field} missing`);
      for (const { field, type } of shape) if (field in fixture && !fits(fixture[field], type)) problems.push(`${field} is not ${type}`);
      for (const key of Object.keys(fixture)) if (!fields.includes(key)) problems.push(`${key} is not a field of the inbound event`);
      assert.deepEqual(problems, [], name);
    }
  },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try { fn(); console.log(`PASS ${name}`); } catch (error) { failed += 1; console.log(`FAIL ${name}: ${error.message}`); }
}
process.exit(failed ? 1 : 0);
