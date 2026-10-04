'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { readBoard, readTurnMemory, composeTurn } = require('./prompt.js');
const { EMPTY_BOARD, boardPath } = require('./board.js');
const { Store } = require('./store.js');

let passed = 0;
let failed = 0;
function test(name, fn) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite prompt-'));
  try { fn(home); passed++; console.log(`PASS ${name}`); }
  catch (error) { failed++; console.log(`FAIL ${name}: ${error.stack}`); }
  finally { fs.rmSync(home, { recursive: true, force: true }); }
}

test('a deleted canonical board loads HEAD and ignores an invalid legacy board', (home) => {
  const text = EMPTY_BOARD.replace(/\n/g, '\r\n');
  write(boardPath(home), text);
  for (const args of [['init', '--quiet'], ['add', '.'], ['commit', '--quiet', '-m', 'board fixture']]) {
    const result = spawnSync('git', ['-C', home, '-c', 'user.name=Memory Test', '-c', 'user.email=memory@example.invalid',
      '-c', 'commit.gpgsign=false', '-c', 'core.autocrlf=false', ...args], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
  }
  write(path.join(home, 'board.md'), 'invalid obsolete board');
  fs.unlinkSync(boardPath(home));
  const alerts = [];
  assert.equal(readBoard(home, null, Date.now(), alerts), text);
  assert.match(alerts[0], /Loaded checked HEAD/);
  assert.equal(fs.existsSync(boardPath(home)), false);
  assert.equal(fs.readFileSync(path.join(home, 'board.md'), 'utf8'), 'invalid obsolete board');
});

test('missing and unreadable boards are visible and never fall back over a new path', (home) => {
  assert.match(readBoard(home), /MISSING MEMORY/);
  fs.mkdirSync(boardPath(home), { recursive: true });
  fs.writeFileSync(path.join(home, 'board.md'), 'old', 'utf8');
  assert.match(readBoard(home), /MISSING MEMORY/);
});

test('readBoard refreshes schedules before returning prompt text', (home) => {
  fs.mkdirSync(path.dirname(boardPath(home)));
  fs.writeFileSync(boardPath(home), EMPTY_BOARD, 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    store.upsertConversation({ key: 'k', agent: 'sample', workspace: 'T1', channel: 'C1' });
    store.upsertSchedule({ id: 'check', conversationKey: 'k', cadence: 'every:1h', timezone: 'fixed',
      nextAt: Date.parse('2026-10-02T12:00:00Z'), note: 'Read café notes' });
    assert.match(readBoard(home, store), /2026-10-02 12:00 UTC \| check \| Read café notes \| none/);
    assert.equal(fs.existsSync(path.join(home, 'board.md')), false);
  } finally { store.close(); }
});

test('a broken board is saved and replaced by a missing note when HEAD is unavailable', (home) => {
  fs.mkdirSync(path.dirname(boardPath(home)));
  fs.writeFileSync(boardPath(home), 'legacy café\r\n', 'utf8');
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    const alerts = [];
    const text = readBoard(home, store, Date.now(), alerts);
    assert.match(text, /MISSING MEMORY/);
    assert.doesNotMatch(text, /legacy café/);
    assert.match(alerts[0], /Broken copy saved/);
    assert.equal(fs.readFileSync(boardPath(home), 'utf8'), 'legacy café\r\n');
  } finally { store.close(); }
});

function write(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text, 'utf8');
}

function fixture(workspace) {
  const home = path.join(workspace, '.rbtv', 'agents', 'sample');
  const root = path.join(workspace, '.rbtv', 'memory');
  write(boardPath(home), EMPTY_BOARD);
  write(path.join(home, 'memory', 'learned.md'), '# Learned rules — sample\n');
  write(path.join(root, 'profile.md'), '# Profile — Sam\n\n## Who\n- PROFILE_CAFÉ. (2026-10-01 · source.md)\n\n## Working with Sam\n\n## Now\n');
  write(path.join(root, 'inbox.md'), '# Inbox — waiting to be filed\n- INBOX_CAFÉ. (2026-10-01 · sample)\n');
  write(path.join(root, '_artifacts', 'index.md'), '# Memory index\n| Open | When |\n|---|---|\n| [../knowledge/](../knowledge/) | WHEN needed. |\n');
  return { home, root };
}

const WORKSPACE = '---\ndescription: when working here\ntype: workspace\npaths: [projects/shared]\n---\n# PRIVATE_CAFÉ\n';

test('turn memory injects all five files from the installation and agent home', (workspace) => {
  const { home } = fixture(workspace);
  const loaded = readTurnMemory(home);
  assert.deepEqual(loaded.alerts, []);
  assert.equal(loaded.memory.length, 4);
  const prompt = composeTurn({ ...loaded, inputs: [], recent: [], stored: [] });
  for (const marker of ['PROFILE_CAFÉ', '# Learned rules — sample', '## What matters now', '# Memory index', 'INBOX_CAFÉ']) assert.ok(prompt.includes(marker), marker);
});

test('private workspace injection matches exact folders and descendants, never prefix siblings', (workspace) => {
  const { home, root } = fixture(workspace);
  const file = path.join(root, 'workspaces', 'shared.md');
  write(file, WORKSPACE.replace(/\n/g, '\r\n'));
  for (const folder of ['projects/shared', 'projects/shared/sub', 'projects/shared-other', 'elsewhere']) {
    const loaded = readTurnMemory(home, path.join(workspace, folder));
    assert.equal(loaded.memory.some((item) => item.path === file), ['projects/shared', 'projects/shared/sub'].includes(folder));
    assert.deepEqual(loaded.alerts, []);
  }
});

test('a deleted or broken workspace recovers its HEAD paths and text; unknown paths never inject', (workspace) => {
  const { home, root } = fixture(workspace);
  const file = path.join(root, 'workspaces', 'shared.md');
  write(file, WORKSPACE);
  const git = (...args) => {
    const result = spawnSync('git', ['-C', workspace, '-c', 'user.name=Memory Test', '-c', 'user.email=memory@example.invalid', '-c', 'commit.gpgsign=false', ...args], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
  };
  git('init', '--quiet'); git('add', '.'); git('commit', '--quiet', '-m', 'memory fixture');
  for (const broken of [null, 'broken paths']) {
    if (broken === null) fs.unlinkSync(file);
    else write(file, broken);
    const loaded = readTurnMemory(home, path.join(workspace, 'projects/shared/sub'));
    assert.equal(loaded.memory.find((item) => item.path === file).text, WORKSPACE);
    assert.match(loaded.alerts[0], /Loaded checked HEAD/);
    assert.equal(readTurnMemory(home, path.join(workspace, 'elsewhere')).memory.some((item) => item.path === file), false);
  }
  const unknown = path.join(root, 'workspaces', 'unknown.md');
  write(unknown, 'no paths');
  const loaded = readTurnMemory(home);
  assert.equal(loaded.memory.some((item) => item.path === unknown), false);
  assert.ok(loaded.alerts.some((line) => line.includes('unknown.md')));
});

test('a failed matching workspace with no HEAD injects a missing note, never rejected text', (workspace) => {
  const { home, root } = fixture(workspace);
  const file = path.join(root, 'workspaces', 'shared.md');
  write(file, WORKSPACE + 'broken content');
  const loaded = readTurnMemory(home, path.join(workspace, 'projects/shared'));
  assert.match(loaded.memory.find((item) => item.path === file).text, /MISSING MEMORY/);
  assert.equal(loaded.alerts.length, 1);
});

test('HEAD board recovery still renders live timers without rewriting the broken original', (workspace) => {
  const { home } = fixture(workspace);
  for (const args of [['init', '--quiet'], ['add', '.'], ['commit', '--quiet', '-m', 'board fixture']]) {
    const result = spawnSync('git', ['-C', workspace, '-c', 'user.name=Memory Test', '-c', 'user.email=memory@example.invalid', '-c', 'commit.gpgsign=false', ...args], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
  }
  write(boardPath(home), 'broken board');
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    store.upsertConversation({ key: 'k', agent: 'sample', workspace: 'T1', channel: 'C1' });
    store.upsertSchedule({ id: 'live-timer', conversationKey: 'k', cadence: 'every:1h', timezone: 'fixed', nextAt: Date.now(), note: 'Current note' });
    const loaded = readTurnMemory(home, home, store);
    assert.match(loaded.board, /live-timer \| Current note/);
    assert.match(loaded.alerts[0], /Loaded checked HEAD/);
    assert.equal(fs.readFileSync(boardPath(home), 'utf8'), 'broken board');
  } finally { store.close(); }
});

console.log(`${passed} passed, ${failed} failed`);
if (failed) process.exit(1);
