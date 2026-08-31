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

// ── The account shape (`d-credential-account-shape`, `d-ask17-credential-token-broker`) ──────
//
// A `credentialNames` entry may now be a bare string (the ONLY shape above ever knew, resolved
// against `.env`, unchanged) OR a typed object `{ type: 'gtools-account', account: '<name>' }` —
// a gtools OAuth account (a directory under `gtools/credentials/<account>/`, never `.env`). This
// function is the admission-time half only (§10a of `cred-account-shape-design.md`): it answers
// "does this account's login exist on disk", the SAME "exists, non-empty" bar `resolveCredentials`
// already applies to a `.env` key — never whether the login is still valid at Google, which only
// the broker's live mint (`credential-broker.js`) can answer, deliberately not duplicated here.
const ACCOUNT_CREDENTIAL_FILES = ['credentials.json', 'token.json'];

function isAccountCredentialEntry(entry) {
  return Boolean(entry) && typeof entry === 'object' && entry.type === 'gtools-account';
}

// `gtoolsRoot` is the directory that holds `credentials/<account>/…` (today, always
// `<workspaceRoot>/3-resources/tools/gtools` — threaded as an argument, never hardcoded here,
// so a fixture can point it anywhere without touching a real account).
function accountCredentialDir(gtoolsRoot, account) {
  return path.join(gtoolsRoot, 'credentials', account);
}

function resolveAccountCredentials(entries, gtoolsRoot) {
  const missing = [];
  for (const entry of entries || []) {
    const account = entry && entry.account;
    if (!account || typeof account !== 'string') {
      missing.push(`gtools-account:${JSON.stringify(account)}`);
      continue;
    }
    const dir = accountCredentialDir(gtoolsRoot, account);
    const ok = ACCOUNT_CREDENTIAL_FILES.every((f) => {
      try { return fs.statSync(path.join(dir, f)).size > 0; } catch { return false; }
    });
    if (!ok) missing.push(`gtools-account:${account}`);
  }
  if (missing.length) return { ok: false, missing };
  return { ok: true };
}

module.exports = {
  STORE_REL,
  storePath,
  parseDotenv,
  loadCentralStore,
  resolveCredentials,
  injectDeclaredEnv,
  ACCOUNT_CREDENTIAL_FILES,
  isAccountCredentialEntry,
  accountCredentialDir,
  resolveAccountCredentials,
};
