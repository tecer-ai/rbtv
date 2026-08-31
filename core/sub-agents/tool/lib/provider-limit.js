'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const SIGS = [
  /Usage limit reached/i,
  /usage limit for this billing cycle/i,
  /Insufficient Balance/i,
  /\bHTTP 429\b/,
  /["']statusCode["']\s*:\s*429/,
  /status code 429/i,
];

function opencodeLogPath() {
  const root = process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local/share');
  return path.join(root, 'opencode', 'log', 'opencode.log');
}

function tailFile(file, maxBytes = 65536) {
  try {
    const st = fs.statSync(file);
    const len = Math.min(st.size, maxBytes);
    if (len <= 0) return '';
    const buf = Buffer.alloc(len);
    const fd = fs.openSync(file, 'r');
    fs.readSync(fd, buf, 0, len, st.size - len);
    fs.closeSync(fd);
    return buf.toString('utf8');
  } catch {
    return '';
  }
}

function parseReset(text) {
  const at = text.match(/limit will reset at ([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8})/i);
  if (at) return at[1];
  if (/refreshed in the next cycle/i.test(text)) return 'next cycle';
  return null;
}

function parseProvider(text, fallback) {
  const m = text.match(/providerID=(\S+)/);
  return m ? m[1] : fallback;
}

function lineTime(line) {
  const m = line.match(/timestamp=(\S+)/);
  return m ? Date.parse(m[1]) : null;
}

function matchLimit(text, { t0, model } = {}) {
  if (!text) return null;
  for (const line of text.split('\n')) {
    if (!line) continue;
    const ts = lineTime(line);
    if (ts && t0 && ts < t0) continue;
    if (model && line.includes('modelID=') && !line.includes(`modelID=${model}`)) continue;
    if (!SIGS.some((re) => re.test(line))) continue;
    return {
      provider: parseProvider(line, model || 'unknown'),
      reset: parseReset(line),
    };
  }
  return null;
}

function formatReason(hit) {
  return `provider-limit: ${hit.provider} resets ${hit.reset || 'unknown'}`;
}

function detectProviderLimit({ harness, model, t0, capturePath, text, logText }) {
  const chunks = [];
  if (text) chunks.push(text);
  if (capturePath) chunks.push(tailFile(capturePath));
  if (logText) chunks.push(logText);
  else if (harness === 'opencode') chunks.push(tailFile(opencodeLogPath(), 256 * 1024));
  const fallback = model || harness || 'unknown';
  for (const chunk of chunks) {
    const hit = matchLimit(chunk, { t0, model });
    if (hit) {
      if (!hit.provider) hit.provider = fallback;
      return hit;
    }
  }
  return null;
}

module.exports = {
  SIGS, opencodeLogPath, tailFile, parseReset, parseProvider,
  matchLimit, formatReason, detectProviderLimit,
};
