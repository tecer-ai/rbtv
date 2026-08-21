'use strict';

const fs = require('node:fs');
const path = require('node:path');

const NAME_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const CANONICAL_REL = path.join('.rbtv', 'config', '.env');

function envFileHasName(text, name) {
  for (const raw of String(text).split(/\n/)) {
    let line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    if (line.startsWith('export ')) line = line.slice(7).trimStart();
    if (!line.includes('=')) continue;
    if (line.split('=', 1)[0].trim() === name) return true;
  }
  return false;
}

function dropUnderGoals(absPath) {
  const parts = path.resolve(absPath).split(path.sep);
  for (let i = 0; i < parts.length - 1; i++) {
    if (parts[i] === '.rbtv' && parts[i + 1] === 'goals') return true;
  }
  return false;
}

function resolveSecretEnvFile(workspaceRoot) {
  const override = String(process.env.RBTV_IGNITE_SECRET_ENV_FILE || '').trim();
  if (override) return path.resolve(override);
  if (!workspaceRoot) return null;
  let rel = CANONICAL_REL;
  try {
    const cfg = path.join(workspaceRoot, 'rbtv.json');
    const data = JSON.parse(fs.readFileSync(cfg, 'utf8'));
    if (typeof data.env_file === 'string' && data.env_file.trim()) {
      rel = data.env_file.trim();
    }
  } catch {
    // absent / unreadable rbtv.json → default
  }
  return path.resolve(workspaceRoot, rel);
}

function applySecretAdd({ workspaceRoot, name, fromFile }) {
  if (typeof name !== 'string' || !NAME_RE.test(name)) {
    return { ok: false, wire: 'VALIDATION_FAILED', check: 'name-shape',
      message: 'NAME must be a shell env identifier: letters, digits, underscore, not starting with a digit. The value is never taken from the wire.' };
  }
  if (typeof fromFile !== 'string' || fromFile.length === 0 || !path.isAbsolute(fromFile)) {
    return { ok: false, wire: 'VALIDATION_FAILED', check: 'from_file-shape',
      message: 'from_file must be an absolute path to the drop file. The value is never taken from the wire.' };
  }
  const dropRes = path.resolve(fromFile);
  if (dropUnderGoals(dropRes)) {
    return { ok: false, wire: 'VALIDATION_FAILED', check: 'drop-under-goals',
      message: `drop file is under .rbtv/goals/ — live goal ledgers are not a mailbox. Leave the file where it is. path: ${dropRes}` };
  }
  const envPath = resolveSecretEnvFile(workspaceRoot);
  if (!envPath) {
    return { ok: false, wire: 'INTERNAL', check: 'env-path',
      message: 'this daemon has no workspace root and no RBTV_IGNITE_SECRET_ENV_FILE, so it can reach no env file' };
  }
  if (dropRes === envPath) {
    return { ok: false, wire: 'VALIDATION_FAILED', check: 'drop-is-env',
      message: 'drop file must not be the env file itself.' };
  }
  let st;
  try { st = fs.statSync(dropRes); } catch (err) {
    return { ok: false, wire: 'NOT_FOUND', check: 'drop-missing',
      message: `drop file does not exist or is not a file: ${dropRes}` };
  }
  if (!st.isFile()) {
    return { ok: false, wire: 'VALIDATION_FAILED', check: 'drop-not-file',
      message: `drop file does not exist or is not a file: ${dropRes}` };
  }
  let envSt;
  try { envSt = fs.statSync(envPath); } catch {
    return { ok: false, wire: 'NOT_FOUND', check: 'env-missing',
      message: `env file does not exist: ${envPath}. The owner creates it; this intent only appends.` };
  }
  if (!envSt.isFile()) {
    return { ok: false, wire: 'VALIDATION_FAILED', check: 'env-not-file',
      message: `env file does not exist: ${envPath}. The owner creates it; this intent only appends.` };
  }
  let existing;
  try { existing = fs.readFileSync(envPath, 'utf8'); } catch (err) {
    return { ok: false, wire: 'INTERNAL', check: 'env-read',
      message: `cannot read env file ${envPath}: ${err.code || err.message}` };
  }
  if (envFileHasName(existing, name)) {
    return { ok: false, wire: 'VALIDATION_FAILED', check: 'name-exists',
      message: `NAME ${name} already exists in ${envPath}. Append-only: no update, no delete, no read-back. The drop file was left in place.` };
  }
  let raw;
  try { raw = fs.readFileSync(dropRes, 'utf8'); } catch (err) {
    return { ok: false, wire: 'INTERNAL', check: 'drop-read',
      message: `cannot read drop file ${dropRes}: ${err.code || err.message}` };
  }
  const value = String(raw).trim();
  if (!value || value.includes('\n') || value.includes('\r') || value.includes('\0')) {
    return { ok: false, wire: 'VALIDATION_FAILED', check: 'value-shape',
      message: `drop file ${dropRes} is empty or not a single-line value. File left in place.` };
  }
  try {
    const text = fs.readFileSync(envPath, 'utf8');
    if (envFileHasName(text, name)) {
      return { ok: false, wire: 'VALIDATION_FAILED', check: 'name-exists',
        message: `NAME ${name} already exists in ${envPath}. Append-only: no update, no delete, no read-back. The drop file was left in place.` };
    }
    const prefix = (text && !text.endsWith('\n')) ? '\n' : '';
    fs.appendFileSync(envPath, prefix + name + '=' + value + '\n');
  } catch (err) {
    return { ok: false, wire: 'INTERNAL', check: 'env-append',
      message: `cannot append to env file ${envPath}: ${err.code || err.message}` };
  }
  let dropConsumed = false;
  try {
    fs.unlinkSync(dropRes);
    dropConsumed = true;
  } catch {
    dropConsumed = false;
  }
  return {
    ok: true,
    result: { appended: true, name, env_file: envPath, drop_consumed: dropConsumed, drop_file: dropRes },
  };
}

module.exports = {
  NAME_RE,
  envFileHasName,
  dropUnderGoals,
  resolveSecretEnvFile,
  applySecretAdd,
};
