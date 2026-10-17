'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createOperations } = require('./lib/media');
const fixture = require('./media-fixtures.json');

test('media adapter sends the selected model and language, preserves voice and audio bytes', async (t) => {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'eleven-media-'));
  t.after(() => fs.rmSync(workspace, { recursive: true, force: true }));
  const env = path.join(workspace, '.rbtv/config/env');
  fs.mkdirSync(env, { recursive: true });
  fs.writeFileSync(path.join(env, '.env'), 'ELEVENLABS_API_KEY="$fixture"\n');
  const config = path.join(workspace, '.rbtv/config/elevenlabs');
  fs.mkdirSync(config);
  fs.writeFileSync(path.join(config, 'config.json'), '{"language":"en"}');
  const old = process.env.ELEVENLABS_API_KEY;
  delete process.env.ELEVENLABS_API_KEY;
  t.after(() => { if (old === undefined) delete process.env.ELEVENLABS_API_KEY; else process.env.ELEVENLABS_API_KEY = old; });
  const calls = [];
  const ops = createOperations(async (url, init) => {
    calls.push({ url, init });
    assert.equal(init.headers['xi-api-key'], '$fixture');
    return url.includes('speech-to-text')
      ? new Response(JSON.stringify(fixture.transcript))
      : new Response(Buffer.from(fixture.audio));
  });
  const file = path.join(workspace, 'sample.m4a');
  fs.writeFileSync(file, 'fixture');
  const transcript = await ops['media.transcribe']({ file, model: 'scribe_v2', workspace });
  assert.equal(transcript.text, 'hello');
  assert.equal(calls[0].init.body.get('language_code'), 'en');
  assert.equal(calls[0].init.body.get('model_id'), 'scribe_v2');
  assert.equal(await calls[0].init.body.get('file').text(), 'fixture');
  const out = path.join(workspace, 'output.mp3');
  await ops['media.speak']({ text: 'hello', voice: 'owner-voice', out, workspace, model: 'eleven_flash_v2_5' });
  assert.equal(fs.readFileSync(out, 'utf8'), 'fixture-audio');
  assert.match(calls[1].url, /owner-voice\?output_format=mp3_44100_128$/);
  assert.deepEqual(JSON.parse(calls[1].init.body), { text: 'hello', model_id: 'eleven_flash_v2_5', language_code: 'en' });
  await ops['media.speak']({ text: 'hello', voice: 'owner-voice', out, workspace, model: 'eleven_multilingual_v2' });
  assert.equal(Object.hasOwn(JSON.parse(calls[2].init.body), 'language_code'), false);
  const fail = createOperations(async () => new Response('', { status: 429 }));
  await assert.rejects(fail['media.transcribe']({ file, workspace }), /HTTP 429/);
  const empty = createOperations(async () => new Response('{"text":" "}'));
  await assert.rejects(empty['media.transcribe']({ file, workspace }), /no transcript/);
  fs.writeFileSync(path.join(config, 'config.json'), 'broken');
  await assert.rejects(ops['media.transcribe']({ file, workspace }), /JSON/);
});
