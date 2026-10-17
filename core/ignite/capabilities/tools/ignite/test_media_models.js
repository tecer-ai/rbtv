'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Audio } = require('./audio');

test('independent defaults, live agent overrides, blank inheritance and no cloud fallback', async (t) => {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'media-models-'));
  t.after(() => fs.rmSync(workspace, { recursive: true, force: true }));
  const home = path.join(workspace, '.rbtv', 'agents', 'scout');
  const install = path.join(workspace, '.rbtv', 'config', 'install.json');
  fs.mkdirSync(home, { recursive: true });
  fs.mkdirSync(path.dirname(install), { recursive: true });
  const save = (file, value) => fs.writeFileSync(file, JSON.stringify(path.basename(file) === 'agent.json'
    ? { harness: 'codex', model: 'example', effort: 'medium', ...value } : value));
  fs.writeFileSync(path.join(home, 'prompt.md'), 'Test agent.');
  save(install, { transcription_model: 'onnx-asr/parakeet-v3', generation_model: 'elevenlabs/flash' });
  const agent = path.join(home, 'agent.json');
  save(agent, { transcription_model: '', generation_model: null });
  const calls = [];
  const adapters = Object.fromEntries(['onnx-asr', 'elevenlabs'].map((name) => [name, {
    operations: {
      'media.transcribe': async (args) => { calls.push([name, args]); return { text: ' hello ' }; },
      'media.speak': async (args) => { calls.push([name, args]); return { path: args.out }; },
    },
  }]));
  const root = new Audio({ workspace, loadAdapter: (name) => adapters[name] });
  const audio = root.forAgent(home);
  assert.deepEqual(await audio.transcribe('note.m4a'), { text: 'hello' });
  assert.deepEqual(calls.pop(), ['onnx-asr', { file: 'note.m4a', model: 'parakeet-v3', workspace }]);
  await audio.speak('hello', { voice: 'scout-voice', out: 'note.mp3' });
  assert.deepEqual(calls.pop(), ['elevenlabs', { text: 'hello', voice: 'scout-voice', out: 'note.mp3', model: 'flash', workspace }]);
  save(agent, { transcription_model: 'elevenlabs/scribe_v2' });
  await audio.transcribe('note.m4a');
  assert.equal(calls.pop()[0], 'elevenlabs');
  save(agent, { transcription_model: '  ' });
  save(install, { transcription_model: 'onnx-asr/new-model', generation_model: 'elevenlabs/flash' });
  await audio.transcribe('note.m4a');
  assert.equal(calls.pop()[1].model, 'new-model');
  adapters['onnx-asr'].operations['media.transcribe'] = async () => { throw new Error('local model unavailable'); };
  await assert.rejects(audio.transcribe('note.m4a'), /local model unavailable/);
  assert.equal(calls.length, 0, 'a failed local model must not spend cloud credits');
  save(agent, { transcription_model: '../outside/model' });
  await assert.rejects(audio.transcribe('note.m4a'), /connector\/model/);
  save(agent, { transcription_model: 42 });
  await assert.rejects(audio.transcribe('note.m4a'), /connector\/model/);
  save(agent, { generation_model: 'missing/model' });
  await assert.rejects(audio.speak('hello'), /does not provide media.speak/);
  let closed = 0;
  adapters['onnx-asr'].close = async () => { closed++; };
  await root.close();
  assert.equal(closed, 1, 'agent views share the lifecycle of the resident model');
});

test('installation mirror replaces the complete media connector', async (t) => {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'media-mirror-'));
  t.after(() => fs.rmSync(workspace, { recursive: true, force: true }));
  const config = path.join(workspace, '.rbtv/config');
  fs.mkdirSync(config, { recursive: true });
  fs.writeFileSync(path.join(config, 'install.json'), '{"transcription_model":"fixture/local"}');
  const folder = path.join(workspace, '.rbtv/mirror/connectors/fixture/capabilities/tools/fixture/lib');
  fs.mkdirSync(folder, { recursive: true });
  fs.writeFileSync(path.join(folder, 'media.js'), "module.exports = {operations:{'media.transcribe':async ({model})=>({text:'mirror '+model})}};");
  const audio = new Audio({ workspace });
  assert.deepEqual(await audio.transcribe('fixture.m4a'), { text: 'mirror local' });
  await audio.close();
});
