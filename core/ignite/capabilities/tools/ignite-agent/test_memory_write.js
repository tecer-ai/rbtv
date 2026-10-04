'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { safeWritePath, writeRoot, acquireMemoryLock, withMemoryLock } = require('./memory-write.js');
const tests = [];
const test = (name, fn) => tests.push([name, fn]);
const lockPath = (dir) => path.join(dir, '.rbtv', 'runtime', 'ignite-memory.lock');

test('all installed boards and the shared inbox resolve the same lock root', (dir) => {
  for (const name of ['.rbtv/memory/inbox.md', '.rbtv/agents/one/_artifacts/board.md', '.rbtv/agents/two/_artifacts/board.md']) {
    assert.equal(writeRoot(path.join(dir, name)), dir);
  }
  assert.throws(() => safeWritePath(dir, path.join(dir, '..', 'escape.md')), /outside installation/);
});

test('lock releases after success and exceptions', (dir) => {
  assert.equal(withMemoryLock(dir, () => { assert.ok(fs.existsSync(lockPath(dir))); return 42; }), 42);
  assert.equal(fs.existsSync(lockPath(dir)), false);
  assert.throws(() => withMemoryLock(dir, () => { throw new Error('fixture failure'); }), /fixture failure/);
  assert.equal(fs.existsSync(lockPath(dir)), false);
});

test('the lock records the holder pid and host, and release preserves a different owner', (dir) => {
  const release = acquireMemoryLock(dir);
  const owner = JSON.parse(fs.readFileSync(lockPath(dir), 'utf8'));
  assert.equal(owner.pid, process.pid);
  assert.equal(owner.hostname, os.hostname());
  assert.equal(typeof owner.token, 'string');
  const replacement = JSON.stringify({ ...owner, token: 'different owner' });
  fs.writeFileSync(lockPath(dir), replacement, 'utf8');
  release();
  assert.equal(fs.readFileSync(lockPath(dir), 'utf8'), replacement);
});

test('an abandoned lock is recovered only after 60 seconds', (dir) => {
  const child = spawnSync(process.execPath, ['-e', `
    require(process.argv[1]).acquireMemoryLock(process.argv[2]);
  `, path.join(__dirname, 'memory-write.js'), dir], { encoding: 'utf8' });
  assert.equal(child.status, 0, child.stderr);
  const before = fs.readFileSync(lockPath(dir), 'utf8');
  const owner = JSON.parse(before);
  assert.throws(() => process.kill(owner.pid, 0), { code: 'ESRCH' });
  const clock = Date.now;
  let now = clock();
  Date.now = () => (now += 5001);
  try {
    assert.throws(() => acquireMemoryLock(dir), /lock busy/);
    assert.equal(fs.readFileSync(lockPath(dir), 'utf8'), before);
  } finally { Date.now = clock; }
  const stale = new Date(Date.now() - 61_000);
  fs.utimesSync(lockPath(dir), stale, stale);
  const release = acquireMemoryLock(dir);
  try {
    assert.equal(JSON.parse(fs.readFileSync(lockPath(dir), 'utf8')).pid, process.pid);
  } finally { release(); }
  assert.equal(fs.existsSync(lockPath(dir)), false);
});

test('a competing process times out after five seconds against a live holder older than 60 seconds', (dir) => {
  const release = acquireMemoryLock(dir);
  const stale = new Date(Date.now() - 61_000);
  fs.utimesSync(lockPath(dir), stale, stale);
  const before = fs.readFileSync(lockPath(dir));
  const start = Date.now();
  try {
    const child = spawnSync(process.execPath, ['-e', `
      const assert = require('node:assert/strict');
      assert.throws(() => require(process.argv[1]).acquireMemoryLock(process.argv[2]), /lock busy/);
    `, path.join(__dirname, 'memory-write.js'), dir], { encoding: 'utf8', timeout: 10_000 });
    assert.equal(child.status, 0, child.stderr);
    assert.ok(Date.now() - start >= 4900 && Date.now() - start < 8000);
    assert.deepEqual(fs.readFileSync(lockPath(dir)), before);
  } finally { release(); }
  withMemoryLock(dir, () => {});
});

for (const kind of ['foreign host', 'unknown owner', 'invalid pid', 'EPERM']) {
  test(`an aged lock with ${kind} is not reclaimed`, (dir) => {
    const release = acquireMemoryLock(dir);
    const owner = JSON.parse(fs.readFileSync(lockPath(dir), 'utf8'));
    if (kind === 'foreign host') owner.hostname += '-other';
    if (kind === 'invalid pid') owner.pid = -1;
    const before = kind === 'unknown owner' ? 'legacy token' : JSON.stringify(owner);
    fs.writeFileSync(lockPath(dir), before, 'utf8');
    const stale = new Date(Date.now() - 61_000);
    fs.utimesSync(lockPath(dir), stale, stale);
    const clock = Date.now;
    const kill = process.kill;
    let now = clock();
    let checked = false;
    Date.now = () => (now += 5001);
    process.kill = (pid, signal) => {
      checked = true;
      assert.equal(pid, owner.pid);
      assert.equal(signal, 0);
      throw Object.assign(new Error('not permitted'), { code: 'EPERM' });
    };
    try {
      assert.throws(() => acquireMemoryLock(dir), /lock busy/);
      assert.equal(checked, kind === 'EPERM');
      assert.equal(fs.readFileSync(lockPath(dir), 'utf8'), before);
    } finally { Date.now = clock; process.kill = kill; release(); }
  });
}

test('a lock exactly 60 seconds old does not trigger a liveness probe', (dir) => {
  const release = acquireMemoryLock(dir);
  const now = Date.now();
  fs.utimesSync(lockPath(dir), new Date(now - 60_000), new Date(now - 60_000));
  const before = fs.readFileSync(lockPath(dir), 'utf8');
  const clock = Date.now;
  const kill = process.kill;
  let calls = 0;
  let probed = false;
  Date.now = () => ++calls < 3 ? now : now + 5000;
  process.kill = () => { probed = true; throw Object.assign(new Error('absent'), { code: 'ESRCH' }); };
  try {
    assert.throws(() => acquireMemoryLock(dir), /lock busy/);
    assert.equal(probed, false);
    assert.equal(fs.readFileSync(lockPath(dir), 'utf8'), before);
  } finally { Date.now = clock; process.kill = kill; release(); }
});

test('a competing process retries and enters only after the holder releases', async (dir) => {
  const release = acquireMemoryLock(dir);
  const stale = new Date(Date.now() - 61_000);
  fs.utimesSync(lockPath(dir), stale, stale);
  const entered = path.join(dir, 'entered');
  const child = spawn(process.execPath, ['-e', `
    const fs = require('node:fs');
    require(process.argv[1]).withMemoryLock(process.argv[2], () => fs.writeFileSync(process.argv[3], 'entered', 'utf8'));
  `, path.join(__dirname, 'memory-write.js'), dir, entered], { stdio: 'ignore' });
  const done = new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', (code) => code === 0 ? resolve() : reject(new Error('writer failed')));
  });
  try {
    await new Promise((resolve) => setTimeout(resolve, 150));
    assert.equal(fs.existsSync(entered), false);
  } finally { release(); }
  await done;
  assert.equal(fs.readFileSync(entered, 'utf8'), 'entered');
});

(async () => {
  let failed = 0;
  for (const [name, fn] of tests) {
    const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-memory-write-')));
    try { await fn(dir); console.log(`PASS ${name}`); }
    catch (error) { failed++; console.log(`FAIL ${name}: ${error.stack}`); }
    finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }
  console.log(`${tests.length - failed} passed, ${failed} failed`);
  if (failed) process.exitCode = 1;
})();
