'use strict';

// Exported API — other seats treat this file as read-only.
// Audio({ workspace?, home?, command?, voice?, spawn?, loadAdapter? })
// forAgent(home) shares adapter lifecycles and reads that agent's model overrides.
// transcribe(file) -> { text }; speak(text, { voice?, out? }) -> file path.
// Each operation resolves transcription_model/generation_model from agent.json
// then install.json, routing connector/model to lib/media.js. No cloud fallback.
// With no selection, preserves tools.audio's transcribe/tts CLI calls.
// close() releases resident processes at service shutdown.

const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const fs = require('node:fs');
const { readAgent } = require('../../../../cast/capabilities/tools/cast/lib/agent');

const REPO = path.resolve(__dirname, '..', '..', '..', '..', '..');
const MODEL = /^[a-z0-9][a-z0-9-]{0,63}\/[A-Za-z0-9][A-Za-z0-9_.-]*$/;

// Read on each operation: an empty agent field inherits the current installation value.
// A missing selection preserves tools.audio for installations that have not selected models.
function modelFor(workspace, home, field) {
  const checked = (value, file) => {
    if (value == null) return '';
    if (typeof value !== 'string' || (value.trim() && !MODEL.test(value.trim()))) {
      throw new Error(`${file}: ${field} must be blank or connector/model`);
    }
    return value.trim();
  };
  let local = '';
  if (home) {
    const read = readAgent(home);
    if (!read.agent) throw new Error(read.why);
    local = checked(read.agent[field === 'transcription_model' ? 'transcriptionModel' : 'generationModel'], path.join(home, 'agent.json'));
  }
  const file = path.join(workspace, '.rbtv', 'config', 'install.json');
  const record = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!record || typeof record !== 'object' || Array.isArray(record)) throw new Error(`${file}: expected an object`);
  const global = checked(record[field], file);
  return local || global;
}

function loadAdapter(name, workspace) {
  const mirror = path.join(workspace, '.rbtv', 'mirror', 'connectors', name);
  const folder = fs.existsSync(mirror) ? mirror : path.join(REPO, 'connectors', name);
  return require(path.join(folder, 'capabilities', 'tools', name, 'lib', 'media.js'));
}

class Audio {
  constructor({ command, voice, spawn: spawnImpl, workspace, home, loadAdapter: loader, adapters } = {}) {
    if (!command && !workspace) throw new Error('Audio requires the audio command or installation');
    this.command = command;
    this.voice = voice || null;
    this.spawn = spawnImpl || spawn;
    this.workspace = workspace;
    this.home = home;
    this.loadAdapter = loader || loadAdapter;
    this.adapters = adapters || new Set();
  }

  forAgent(home) {
    return new Audio({ command: this.command, voice: this.voice, spawn: this.spawn,
      workspace: this.workspace, home, loadAdapter: this.loadAdapter, adapters: this.adapters });
  }

  selection(field, operation) {
    const chosen = this.workspace ? modelFor(this.workspace, this.home, field) : '';
    if (!chosen) return null;
    const [connector, model] = chosen.split('/');
    const adapter = this.loadAdapter(connector, this.workspace);
    const fn = adapter?.operations?.[operation];
    if (typeof fn !== 'function') throw new Error(`${connector} does not provide ${operation}`);
    this.adapters.add(adapter);
    return (args) => fn({ ...args, model, workspace: this.workspace });
  }

  async close() {
    await Promise.all([...this.adapters].map((adapter) => adapter.close?.()));
    this.adapters.clear();
  }

  call(args, input) {
    return new Promise((resolve, reject) => {
      const child = this.spawn(this.command, args, { stdio: ['pipe', 'pipe', 'pipe'] });
      let stdout = '';
      let stderr = '';
      child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
      child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
      child.on('error', reject);
      child.on('close', (code) => {
        if (code !== 0) return reject(new Error(`audio exited ${code}: ${stderr.trim()}`));
        try { resolve(JSON.parse(stdout)); } catch { reject(new Error('audio returned invalid JSON')); }
      });
      // A child that exits without reading fails this write; its exit decides the result.
      child.stdin.on('error', () => {});
      if (input == null) child.stdin.end();
      else child.stdin.end(input);
    });
  }

  async transcribe(file) {
    if (!file) throw new Error('transcribe requires file');
    const selected = this.selection('transcription_model', 'media.transcribe');
    const result = selected ? await selected({ file }) : await this.call(['transcribe', file]);
    const text = typeof result.text === 'string' ? result.text.trim() : '';
    if (!text) throw new Error('audio returned no transcript');
    return { text };
  }

  async speak(text, options = {}) {
    const body = typeof text === 'string' ? text : '';
    if (!body.trim()) throw new Error('speak requires text');
    const voice = options.voice || this.voice;
    const out = options.out || path.join(os.tmpdir(), `ignite-${randomBytes(8).toString('hex')}.mp3`);
    const selected = this.selection('generation_model', 'media.speak');
    const result = selected ? await selected({ text: body, voice, out })
      : await this.call(['tts', '--file', '-', '--out', out,
        ...(voice ? ['--voice', voice] : [])], body);
    const file = result.path || out;
    if (!file) throw new Error('audio returned no file');
    return file;
  }
}

module.exports = { Audio, modelFor };
