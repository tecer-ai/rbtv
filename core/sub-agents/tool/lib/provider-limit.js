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

function lineSessionId(line) {
  const m = line.match(/session\.id=(\S+)/);
  return m ? m[1] : null;
}

// `shared` = the chunk is the SHARED opencode.log (every run on the box tails the same file), as
// opposed to a job's own captured stdout. A shared-chunk match is only THIS job's if the line
// carries the job's own bound `session.id` — when the caller has no bound sessionId to check
// against, the hit is real but not attributable, so it comes back `ambiguous: true` rather than
// pinned to this handle (measured 2026-08-31: the unfiltered shared tail let one job's usage-limit
// line flag onto a different handle running the same model, same attribution class as the
// foreign-recovered-tail defect this file's binding fix addresses).
function matchLimit(text, { t0, model, sessionId, shared } = {}) {
  if (!text) return null;
  for (const line of text.split('\n')) {
    if (!line) continue;
    const ts = lineTime(line);
    if (ts && t0 && ts < t0) continue;
    if (model && line.includes('modelID=') && !line.includes(`modelID=${model}`)) continue;
    if (!SIGS.some((re) => re.test(line))) continue;
    if (shared && sessionId && lineSessionId(line) !== sessionId) continue; // a sibling's line
    return {
      provider: parseProvider(line, model || 'unknown'),
      reset: parseReset(line),
      ambiguous: Boolean(shared && !sessionId),
    };
  }
  return null;
}

function formatReason(hit) {
  const label = hit.ambiguous
    ? `provider-limit (model-wide, ambiguous — could be a sibling job): ${hit.provider}`
    : `provider-limit: ${hit.provider}`;
  return `${label} resets ${hit.reset || 'unknown'}`;
}

function detectProviderLimit({ harness, model, t0, capturePath, text, logText, sessionId }) {
  const chunks = [];
  if (text) chunks.push({ body: text, shared: false });
  if (capturePath) chunks.push({ body: tailFile(capturePath), shared: false });
  if (logText) chunks.push({ body: logText, shared: true });
  else if (harness === 'opencode') chunks.push({ body: tailFile(opencodeLogPath(), 256 * 1024), shared: true });
  const fallback = model || harness || 'unknown';
  for (const chunk of chunks) {
    const hit = matchLimit(chunk.body, { t0, model, sessionId, shared: chunk.shared });
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
