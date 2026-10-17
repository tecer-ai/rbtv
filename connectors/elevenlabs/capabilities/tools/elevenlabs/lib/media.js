'use strict';

// Node media adapter for the same speech endpoints as elevenlabs.py. Credentials
// and language are read at call time; importing the adapter makes no API call.
const fs = require('node:fs');
const path = require('node:path');
const FORMATS = { '.mp3': 'mp3_44100_128', '.ogg': 'opus_48000_128', '.opus': 'opus_48000_128' };

function settings(workspace) {
  let key = (process.env.ELEVENLABS_API_KEY || '').trim();
  let key_source = 'env';
  if (!key && workspace) {
    const file = path.join(workspace, '.rbtv', 'config', 'env', '.env');
    let text = '';
    try { text = fs.readFileSync(file, 'utf8'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    for (const line of text.split(/\r?\n/)) {
      const match = line.match(/^\s*(?:export\s+)?ELEVENLABS_API_KEY\s*=\s*(.*)$/);
      if (match) {
        key = match[1].trim().replace(/^(['"])(.*)\1$/, '$2');
        if (key) { key_source = 'env-file'; break; }
      }
    }
  }
  if (!key) throw new Error('ELEVENLABS_API_KEY is unset; configure the process environment or .rbtv/config/env/.env');
  let language = 'pt';
  if (workspace) {
    const file = path.join(workspace, '.rbtv', 'config', 'elevenlabs', 'config.json');
    try {
      const config = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (!config || typeof config !== 'object' || Array.isArray(config)) throw new Error(`${file}: expected an object`);
      language = config.language || language;
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  if (typeof language !== 'string' || !/^[a-z]{2,3}$/.test(language)) throw new Error('ElevenLabs language must be an ISO 639 code');
  return { key, key_source, language };
}

function createOperations(fetchImpl = fetch) {
  async function request(endpoint, config, init = {}) {
    const base = (process.env.ELEVENLABS_API_URL || 'https://api.elevenlabs.io').replace(/\/$/, '');
    const response = await fetchImpl(`${base}${endpoint}`, { ...init,
      headers: { ...init.headers, 'xi-api-key': config.key }, signal: AbortSignal.timeout(300_000) });
    if (!response.ok) throw new Error(`ElevenLabs HTTP ${response.status}`);
    return response;
  }

  async function transcribe({ file, model = 'scribe_v2', workspace }) {
    const bytes = await fs.promises.readFile(file);
    if (!bytes.length) throw new Error('ElevenLabs requires a nonempty audio file');
    const config = settings(workspace);
    const form = new FormData();
    form.set('file', new Blob([bytes]), path.basename(file));
    form.set('model_id', model);
    form.set('language_code', config.language);
    const response = await request('/v1/speech-to-text', config, { method: 'POST', body: form });
    const body = await response.json();
    const text = typeof body.text === 'string' ? body.text.trim() : '';
    if (!text) throw new Error('ElevenLabs returned no transcript');
    return { text, language: body.language_code || config.language, language_requested: config.language,
      model_id: model, source: file, key_source: config.key_source, chars: [...text].length };
  }

  async function speak({ text, out, voice, model = 'eleven_flash_v2_5', workspace }) {
    if (typeof text !== 'string' || !text.trim()) throw new Error('ElevenLabs requires text');
    const format = FORMATS[path.extname(out || '').toLowerCase()];
    if (!format) throw new Error('ElevenLabs output must end in .mp3, .ogg or .opus');
    if (!fs.statSync(path.dirname(out)).isDirectory()) throw new Error('ElevenLabs output folder missing');
    const config = settings(workspace);
    const voice_source = voice ? 'flag' : 'account';
    if (!voice) {
      const response = await request('/v2/voices?page_size=100', config);
      voice = (await response.json()).voices?.find((row) => row.voice_id)?.voice_id;
      if (!voice) throw new Error('ElevenLabs account has no voices; choose a voice');
    }
    const body = { text, model_id: model };
    if (!model.includes('multilingual_v2')) body.language_code = config.language;
    const response = await request(`/v1/text-to-speech/${encodeURIComponent(voice)}?output_format=${format}`, config,
      { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    const bytes = Buffer.from(await response.arrayBuffer());
    if (!bytes.length) throw new Error('ElevenLabs returned no audio');
    await fs.promises.writeFile(out, bytes);
    return { path: path.resolve(out), bytes: bytes.length, output_format: format, voice_id: voice,
      voice_source, model_id: model, language: body.language_code || '(carried by the text — this model takes no language code)',
      key_source: config.key_source, chars: [...text].length };
  }

  return { 'media.transcribe': transcribe, 'media.speak': speak };
}

module.exports = { operations: createOperations(), createOperations };
