'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { Audio } = require('./audio.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

function fakeSpawn(script) {
  const calls = [];
  function spawn(cmd, args) {
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stderr = new EventEmitter();
    child.stdout.setEncoding = () => child.stdout;
    child.stderr.setEncoding = () => child.stderr;
    child.stdin = { ended: null, end(data) { this.ended = data == null ? null : String(data); } };
    calls.push({ cmd, args, child });
    return child;
  }
  return { spawn, calls, script };
}

function finish(child, { code = 0, stdout = '', stderr = '' } = {}) {
  queueMicrotask(() => {
    if (stdout) child.stdout.emit('data', stdout);
    if (stderr) child.stderr.emit('data', stderr);
    child.emit('close', code);
  });
}

test('transcribe', async () => {
  const fake = fakeSpawn();
  const audio = new Audio({ script: 'audio.py', spawn: fake.spawn });
  const pending = audio.transcribe('clip.mp3');
  assert.deepEqual(fake.calls[0].args, ['audio.py', 'transcribe', 'clip.mp3']);
  finish(fake.calls[0].child, { stdout: JSON.stringify({ text: '  hello  ', language: 'pt' }) });
  assert.deepEqual(await pending, { text: 'hello' });
});

test('transcribe-empty-errors', async () => {
  const fake = fakeSpawn();
  const audio = new Audio({ script: 'audio.py', spawn: fake.spawn });
  const pending = audio.transcribe('clip.mp3');
  finish(fake.calls[0].child, { stdout: JSON.stringify({ text: '   ' }) });
  await assert.rejects(pending, /no transcript/);
});

test('transcribe-nonzero-errors', async () => {
  const fake = fakeSpawn();
  const audio = new Audio({ script: 'audio.py', spawn: fake.spawn });
  const pending = audio.transcribe('clip.mp3');
  finish(fake.calls[0].child, { code: 1, stderr: 'audio: empty' });
  await assert.rejects(pending, /exited 1/);
});

test('transcribe-invalid-json-errors', async () => {
  const fake = fakeSpawn();
  const audio = new Audio({ script: 'audio.py', spawn: fake.spawn });
  const pending = audio.transcribe('clip.mp3');
  finish(fake.calls[0].child, { stdout: 'not-json' });
  await assert.rejects(pending, /invalid JSON/);
});

test('speak', async () => {
  const fake = fakeSpawn();
  const audio = new Audio({ script: 'audio.py', voice: 'default-voice', spawn: fake.spawn });
  const pending = audio.speak('ola', { voice: 'V1', out: 'out.mp3' });
  assert.deepEqual(fake.calls[0].args, ['audio.py', 'tts', '--file', '-', '--out', 'out.mp3', '--voice', 'V1']);
  assert.equal(fake.calls[0].child.stdin.ended, 'ola');
  finish(fake.calls[0].child, { stdout: JSON.stringify({ path: 'out.mp3', bytes: 4 }) });
  assert.equal(await pending, 'out.mp3');
});

test('speak-default-voice', async () => {
  const fake = fakeSpawn();
  const audio = new Audio({ script: 'audio.py', voice: 'V0', spawn: fake.spawn });
  const pending = audio.speak('ola', { out: 'out.mp3' });
  assert.equal(fake.calls[0].args.at(-1), 'V0');
  finish(fake.calls[0].child, { stdout: JSON.stringify({ path: 'out.mp3' }) });
  assert.equal(await pending, 'out.mp3');
});

(async () => {
  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      await fn();
      process.stdout.write(`PASS ${name}\n`);
    } catch (error) {
      failed += 1;
      process.stdout.write(`FAIL ${name}: ${error.stack || error.message}\n`);
    }
  }
  process.stdout.write(`audio: ${tests.length - failed} passed, ${failed} failed\n`);
  process.exit(failed ? 1 : 0);
})();
