'use strict';

const fs = require('node:fs');
const path = require('node:path');

const STORE_REL = path.join('.rbtv', 'config', '.env');

function storePath(workspaceRoot) {
  return path.join(workspaceRoot, STORE_REL);
}

function parseDotenv(text) {
  const out = {};
  for (const line of String(text).split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const i = trimmed.indexOf('=');
    if (i <= 0) continue;
    out[trimmed.slice(0, i)] = trimmed.slice(i + 1);
  }
  return out;
}

function loadCentralStore(workspaceRoot) {
  const p = storePath(workspaceRoot);
  if (!fs.existsSync(p)) return {};
  return parseDotenv(fs.readFileSync(p, 'utf8'));
}

function resolveCredentials(names, store) {
  const missing = [];
  for (const name of names || []) {
    const value = store[name];
    if (value == null || String(value) === '') missing.push(name);
  }
  if (missing.length) return { ok: false, missing };
  return { ok: true };
}

function injectDeclaredEnv(names, store) {
  const env = {};
  for (const name of names || []) {
    if (Object.prototype.hasOwnProperty.call(store, name)) env[name] = store[name];
  }
  return env;
}

module.exports = {
  STORE_REL,
  storePath,
  parseDotenv,
  loadCentralStore,
  resolveCredentials,
  injectDeclaredEnv,
};
