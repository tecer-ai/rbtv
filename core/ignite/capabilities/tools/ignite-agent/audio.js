'use strict';

// Exported API — other seats treat this file as read-only.
// Audio({ command, voice?, spawn? })   command: the audio tool's name on PATH (config.json tools.audio), run directly
// transcribe(file) → { text }   <command> transcribe FILE. Empty or failed → throw, never { text: '' }.
// speak(text, { voice?, out? }) → file path   <command> tts --file - --out PATH [--voice ID]

const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');

class Audio {
  constructor({ command, voice, spawn: spawnImpl } = {}) {
    if (!command) throw new Error('Audio requires the audio command');
    this.command = command;
    this.voice = voice || null;
    this.spawn = spawnImpl || spawn;
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
      if (input == null) child.stdin.end();
      else child.stdin.end(input);
    });
  }

  async transcribe(file) {
    if (!file) throw new Error('transcribe requires file');
    const result = await this.call(['transcribe', file]);
    const text = typeof result.text === 'string' ? result.text.trim() : '';
    if (!text) throw new Error('audio returned no transcript');
    return { text };
  }

  async speak(text, options = {}) {
    const body = typeof text === 'string' ? text : '';
    if (!body.trim()) throw new Error('speak requires text');
    const voice = options.voice || this.voice;
    const out = options.out || path.join(os.tmpdir(), `ignite-${randomBytes(8).toString('hex')}.mp3`);
    const result = await this.call(['tts', '--file', '-', '--out', out,
      ...(voice ? ['--voice', voice] : [])], body);
    const file = result.path || out;
    if (!file) throw new Error('audio returned no file');
    return file;
  }
}

module.exports = { Audio };
