'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { EMPTY_BOARD } = require('./board.js');
const { checkMemory, readMemory, remember, workspaceFromHome, workspacePaths, workspaceMatches, workspaceFiles } = require('./memory.js');

const tests = [];
function test(name, fn) { tests.push([name, fn]); }
const PROFILE = '# Profile — Sam\n\n## Who\n- Sam. (2026-10-01 · source.md)\n\n## Working with Sam\n\n## Now\n';
const LEARNED = '# Learned rules — sample\n\n- [correction] Send one PDF. Why: owner correction. (2026-10-01 · sample/[thread](https://example.com/1))\n';
const INDEX = '# Memory index\n\n| Open | When |\n|---|---|\n| [../knowledge/](../knowledge/) | WHEN checking a fact. |\n';
const WORKSPACE = '---\ndescription: when working in the shared repo\ntype: workspace\naliases: [sample]\npaths: [projects/shared, "projects/with spaces"]\n---\n# Shared — private notes\n\n- Café review. (2026-10-01 · source.md)\n';
const SAMPLES = { profile: PROFILE, learned: LEARNED, index: INDEX, workspace: WORKSPACE, inbox: '# Inbox — waiting to be filed\n\n- Café. (2026-10-01 · sample)\n', board: EMPTY_BOARD };

function write(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text, 'utf8');
}

function git(dir, ...args) {
  const result = spawnSync('git', ['-C', dir, '-c', 'user.name=Memory Test', '-c', 'user.email=memory@example.invalid',
    '-c', 'commit.gpgsign=false', '-c', 'core.autocrlf=false', ...args], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}

test('template forms accept UTF-8 and CRLF, empty skeletons and an overfull inbox', () => {
  for (const [kind, text] of Object.entries(SAMPLES)) {
    checkMemory(kind, text);
    checkMemory(kind, text.replace(/\n/g, '\r\n'));
  }
  checkMemory('learned', '# Learned rules — sample\n');
  checkMemory('inbox', '');
  checkMemory('inbox', '- Record. (2026-10-01 · sample)\n'.repeat(25));
  checkMemory('index', INDEX + '| [../folder/](../folder/) | WHEN checking. |\n'.repeat(45));
});

test('checkers reject broken shapes, missing provenance, invalid dates and caps', () => {
  for (const [kind, text] of Object.entries(SAMPLES)) {
    assert.throws(() => checkMemory(kind, 'broken'), /check failed|board refused/);
    assert.throws(() => checkMemory(kind, text + '\0'), /check failed|board refused/);
  }
  for (const text of [PROFILE.replace('## Now', '## Health'), PROFILE.replace(' (2026-10-01 · source.md)', ''),
    PROFILE.replace('2026-10-01', '2026-02-30'), PROFILE + ' '.repeat(4001)]) assert.throws(() => checkMemory('profile', text));
  for (const text of [LEARNED.replace('[correction]', '[note]'), LEARNED.replace('Why:', 'Because:'),
    '# Learned rules — sample\n' + LEARNED.split('\n').find((line) => line.startsWith('- ')).concat('\n').repeat(31)]) {
    assert.throws(() => checkMemory('learned', text));
  }
  assert.throws(() => checkMemory('index', INDEX.replace('| Open |', '| File |')));
  assert.throws(() => checkMemory('workspace', WORKSPACE + ' '.repeat(3001)));
  assert.throws(() => checkMemory('workspace', WORKSPACE.replace('type: workspace', 'type: place')));
});

test('inferred learned rules require two distinct conversation links', () => {
  const inferred = LEARNED.replace('[correction]', '[inferred]');
  assert.throws(() => checkMemory('learned', inferred), /two distinct/);
  assert.throws(() => checkMemory('learned', inferred.replace('https://example.com/1))', 'https://example.com/1) · sample/[again](https://example.com/1))')), /two distinct/);
  checkMemory('learned', inferred.replace('https://example.com/1))', 'https://example.com/1) · sample/[other](https://example.com/2))'));
});

test('workspace paths support inline and block lists, spaces, CRLF and Windows separators', () => {
  assert.deepEqual(workspacePaths(WORKSPACE), ['projects/shared', 'projects/with spaces']);
  const block = WORKSPACE.replace('paths: [projects/shared, "projects/with spaces"]', "paths:\n  - projects/shared\n  - 'projects/with spaces'");
  assert.deepEqual(workspacePaths(block.replace(/\n/g, '\r\n')), ['projects/shared', 'projects/with spaces']);
  assert.deepEqual(workspacePaths(WORKSPACE.replace('[projects/shared, "projects/with spaces"]', '["projects/one, two", \'projects/it\'\'s shared\']')), ['projects/one, two', "projects/it's shared"]);
  for (const value of ['[]', 'projects/shared', '[/etc]', '[../outside]', '[C:\\outside]', '[C:outside]', '[one,,two]', '[one,]', '["unfinished]']) {
    assert.throws(() => workspacePaths(WORKSPACE.replace('[projects/shared, "projects/with spaces"]', value)));
  }
  assert.equal(workspaceMatches('/install', '/install/projects/shared/sub', ['projects/shared'], path.posix), true);
  assert.equal(workspaceMatches('/install', '/install/projects/shared', ['projects/shared'], path.posix), true);
  assert.equal(workspaceMatches('/install', '/install/projects/shared-other', ['projects/shared'], path.posix), false);
  assert.equal(workspaceMatches('/install', '/outside', ['projects/shared'], path.posix), false);
  assert.equal(workspaceMatches('C:\\Install', 'c:\\install\\projects\\shared\\sub', ['projects/shared'], path.win32), true);
  assert.equal(workspaceMatches('C:\\Install', 'C:\\Install\\projects\\shared-other', ['projects\\shared'], path.win32), false);
  assert.equal(workspaceMatches('C:\\Install', 'D:\\Install\\projects\\shared', ['projects/shared'], path.win32), false);
});

test('installation root comes from the agent home, never the source checkout or global rbtv home', (dir) => {
  assert.equal(workspaceFromHome(path.join(dir, '.rbtv', 'agents', 'sample')), dir);
  assert.equal(workspaceFromHome(path.join(dir, '.rbtv')), null);
  assert.equal(workspaceFromHome(path.join(dir, 'source', 'sample')), null);
});

test('each file type saves exact rejected bytes then injects checked HEAD without overwriting', (dir) => {
  git(dir, 'init', '--quiet');
  for (const [kind, text] of Object.entries(SAMPLES)) write(path.join(dir, `${kind}.md`), text.replace(/\n/g, '\r\n'));
  git(dir, 'add', '.');
  git(dir, 'commit', '--quiet', '-m', 'memory fixture');
  for (const [kind, text] of Object.entries(SAMPLES)) {
    const file = path.join(dir, `${kind}.md`);
    const broken = Buffer.from('broken café\r\n');
    fs.writeFileSync(file, broken);
    const alerts = [];
    const loaded = readMemory(file, kind, alerts);
    assert.equal(loaded.text, text.replace(/\n/g, '\r\n'));
    assert.equal(loaded.source, 'HEAD');
    assert.deepEqual(fs.readFileSync(file), broken);
    const copies = fs.readdirSync(dir).filter((name) => name.startsWith(`${kind}.md.broken-`));
    assert.equal(copies.length, 1);
    assert.deepEqual(fs.readFileSync(path.join(dir, copies[0])), broken);
    assert.equal(/[:*?"<>|\\]/.test(copies[0]), false);
    assert.match(alerts[0], /Broken copy saved: .*Loaded checked HEAD/);
    fs.unlinkSync(file);
    const missingAlerts = [];
    assert.equal(readMemory(file, kind, missingAlerts).source, 'HEAD');
    assert.match(missingAlerts[0], /ENOENT/);
  }
});

test('missing HEAD, invalid HEAD, invalid UTF-8 and unreadable paths give visible notes and alerts', (dir) => {
  const file = path.join(dir, 'profile.md');
  let alerts = [];
  assert.match(readMemory(file, 'profile', alerts).text, /MISSING MEMORY/);
  assert.equal(alerts.length, 1);
  git(dir, 'init', '--quiet');
  write(file, 'broken\n');
  git(dir, 'add', 'profile.md');
  git(dir, 'commit', '--quiet', '-m', 'invalid memory fixture');
  fs.writeFileSync(file, Buffer.from([0xff, 0xfe, 0]));
  alerts = [];
  assert.match(readMemory(file, 'profile', alerts).text, /no valid HEAD/);
  assert.equal(alerts.length, 1);
  assert.ok(fs.readdirSync(dir).some((name) => name.startsWith('profile.md.broken-')));
  fs.unlinkSync(file);
  fs.mkdirSync(file);
  assert.doesNotThrow(() => readMemory(file, 'profile', []));
});

test('backup write failure still loads HEAD, leaves evidence and alerts', (dir) => {
  const file = path.join(dir, 'profile.md');
  git(dir, 'init', '--quiet');
  write(file, PROFILE);
  git(dir, 'add', 'profile.md');
  git(dir, 'commit', '--quiet', '-m', 'memory fixture');
  write(file, 'broken\n');
  const original = fs.writeFileSync;
  fs.writeFileSync = (target, ...args) => {
    if (String(target).includes('.broken-')) throw new Error('simulated disk failure');
    return original(target, ...args);
  };
  try {
    const alerts = [];
    assert.equal(readMemory(file, 'profile', alerts).text, PROFILE);
    assert.match(alerts[0], /Could not save the broken copy/);
    assert.equal(fs.readFileSync(file, 'utf8'), 'broken\n');
  } finally { fs.writeFileSync = original; }
});

test('invalid UTF-8 in an otherwise valid HEAD copy is not injected', (dir) => {
  const file = path.join(dir, 'profile.md');
  git(dir, 'init', '--quiet');
  const invalid = Buffer.from(PROFILE, 'utf8');
  invalid[invalid.indexOf('Sam.')] = 0xff;
  fs.writeFileSync(file, invalid);
  git(dir, 'add', 'profile.md');
  git(dir, 'commit', '--quiet', '-m', 'invalid encoding fixture');
  fs.unlinkSync(file);
  const alerts = [];
  assert.equal(readMemory(file, 'profile', alerts).source, null);
  assert.match(alerts[0], /No valid HEAD copy/);
});

test('workspace discovery includes deleted HEAD files but ignores backups and subdirectories', (dir) => {
  const folder = path.join(dir, '.rbtv', 'memory', 'workspaces');
  const file = path.join(folder, 'shared.md');
  git(dir, 'init', '--quiet');
  write(file, WORKSPACE);
  git(dir, 'add', '.rbtv/memory/workspaces/shared.md');
  git(dir, 'commit', '--quiet', '-m', 'workspace fixture');
  fs.rmSync(folder, { recursive: true });
  assert.deepEqual(workspaceFiles(folder), [file]);
  write(path.join(folder, 'local.md'), WORKSPACE);
  write(path.join(folder, 'local.md.broken-copy'), 'broken');
  write(path.join(folder, '_artifacts', 'index.md'), INDEX);
  assert.deepEqual(workspaceFiles(folder), [path.join(folder, 'local.md'), file]);
});

test('remember creates and appends one UTF-8 line, keeps broken bytes and never refuses over 20', (dir) => {
  const options = { agent: 'sample', now: Date.parse('2026-10-01T12:00:00Z') };
  const first = remember(dir, 'Café\r\nby the sea', options);
  assert.equal(first.appended, true);
  assert.equal(first.lines, 1);
  checkMemory('inbox', fs.readFileSync(first.path, 'utf8'));
  write(first.path, '# Inbox — waiting to be filed\r\n\r\n' + '- Fact. (2026-10-01 · sample)\r\n'.repeat(17));
  assert.equal(remember(dir, 'twentieth', options).warning, null);
  const full = remember(dir, 'twenty-first', options);
  assert.equal(full.lines, 21);
  assert.match(full.warning, /over 20/);
  const broken = Buffer.from('unfiled café without a newline');
  fs.writeFileSync(first.path, broken);
  remember(dir, 'a'.repeat(5000), options);
  const after = fs.readFileSync(first.path);
  assert.deepEqual(after.subarray(0, broken.length), broken);
  assert.match(after.toString('utf8'), /newline\n- a{5000}/);
});

test('simultaneous first appends from several processes preserve every complete line', async (dir) => {
  const program = `const {remember}=require(process.argv[1]); for(let i=0;i<25;i++) remember(process.argv[2], process.argv[3]+'-'+i, {agent:'sample'});`;
  await Promise.all(Array.from({ length: 4 }, (_, i) => new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['-e', program, path.join(__dirname, 'memory.js'), dir, `writer${i}`], { stdio: 'ignore' });
    child.once('error', reject);
    child.once('close', (code) => code === 0 ? resolve() : reject(new Error(`writer exit ${code}`)));
  })));
  const text = fs.readFileSync(path.join(dir, '.rbtv', 'memory', 'inbox.md'), 'utf8');
  checkMemory('inbox', text);
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  assert.equal(lines.length, 100);
  assert.equal(new Set(lines).size, 100);
});

(async () => {
  let failed = 0;
  for (const [name, fn] of tests) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite memory-'));
    try { await fn(dir); console.log(`PASS ${name}`); }
    catch (error) { failed++; console.log(`FAIL ${name}: ${error.stack}`); }
    finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }
  console.log(`${tests.length - failed} passed, ${failed} failed`);
  if (failed) process.exitCode = 1;
})();
