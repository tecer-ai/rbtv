'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { Resident } = require('./lib/media');

test('resident serializes concurrent calls and reuses one child', async (t) => {
  let starts = 0;
  const worker = new Resident({}, () => {
    starts++;
    return spawn(process.execPath, ['-e', `
      const lines = require('node:readline').createInterface({input: process.stdin});
      let busy = false;
      lines.on('line', line => {
        if (busy) process.exit(9);
        busy = true;
        setTimeout(() => { console.log(JSON.stringify({text: JSON.parse(line).file})); busy = false; }, 10);
      });`], { stdio: ['pipe', 'pipe', 'pipe'] });
  });
  t.after(() => worker.close());
  const results = await Promise.all([worker.transcribe('first'), worker.transcribe('second')]);
  assert.deepEqual(results.map((r) => r.text), ['first', 'second']);
  assert.equal(starts, 1);
});

test('worker death rejects current call and a later call starts a fresh child', async (t) => {
  let starts = 0;
  const worker = new Resident({}, () => {
    starts++;
    const script = starts === 1 ? 'process.exit(7)' : `
      require('node:readline').createInterface({input: process.stdin}).on('line', () => console.log('{"text":"recovered"}'));`;
    return spawn(process.execPath, ['-e', script], { stdio: ['pipe', 'pipe', 'pipe'] });
  });
  t.after(() => worker.close());
  await assert.rejects(worker.transcribe('first'), /exited 7/);
  assert.equal((await worker.transcribe('second')).text, 'recovered');
  assert.equal(starts, 2);
});

test('close rejects in-flight and queued calls without restarting', async () => {
  let starts = 0;
  const worker = new Resident({}, () => {
    starts++;
    return spawn(process.execPath, ['-e', 'process.stdin.resume()'], { stdio: ['pipe', 'pipe', 'pipe'] });
  });
  const first = assert.rejects(worker.transcribe('first'), /stopped/);
  const second = assert.rejects(worker.transcribe('second'), /stopped/);
  await new Promise((resolve) => setTimeout(resolve, 20));
  worker.close();
  await Promise.all([first, second]);
  assert.equal(starts, 1);
});

test('malformed protocol and explicit inference errors reject rather than invent text', async (t) => {
  for (const [body, message] of [['not JSON', /JSON/], ['{"error":"no speech recognized"}', /no speech recognized/], ['{"text":" "}', /no transcript/]]) {
    const worker = new Resident({}, () => spawn(process.execPath, ['-e', `
      require('node:readline').createInterface({input:process.stdin}).on('line', () => console.log(${JSON.stringify(body)}));
    `], { stdio: ['pipe', 'pipe', 'pipe'] }));
    t.after(() => worker.close());
    await assert.rejects(worker.transcribe('fixture'), message);
  }
});
