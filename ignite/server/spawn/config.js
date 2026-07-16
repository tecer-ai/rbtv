'use strict';

const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const {
  SpawnError,
  E_CONFIG_LOAD,
  E_DUPLICATE_PROFILE,
  E_UNKNOWN_SLOT,
  E_MISSING_KEY,
  E_WORKDIR_ESCAPE,
  E_WORKDIR_MISSING,
} = require('./errors');

const KNOWN_TOP_KEYS = new Set(['bind', 'auth', 'spawn', 'profiles', 'default_workdir_root']);
const KNOWN_PROFILE_KEYS = new Set([
  'exec', 'resume', 'session_ref', 'headed', 'workdir_root', 'caps', 'sandbox', 'env',
]);
const KNOWN_EXEC_KEYS = new Set(['argv', 'prompt']);
const KNOWN_RESUME_KEYS = new Set(['argv', 'prompt']);
const KNOWN_HEADED_KEYS = new Set(['tui']);
const KNOWN_TUI_KEYS = new Set(['argv']);
const KNOWN_PROMPT_VALUES = new Set(['stdin', 'file', 'argv-last']);
const KNOWN_SESSION_REF_SOURCES = new Set([
  'stdout-json', 'stdout-json-event', 'cwd-implicit',
]);
const KNOWN_CAPS_KEYS = new Set(['memory_max', 'cpu_quota', 'runtime_max', 'tasks_max']);
const KNOWN_SANDBOX_KEYS = new Set([
  'ProtectSystem', 'ReadWritePaths', 'PrivateTmp', 'NoNewPrivileges',
]);
const KNOWN_ENV_KEYS = new Set(['file']);
const CLOSED_SLOTS = new Set(['{workdir}', '{prompt_file}', '{session_ref}']);
const SLOT_RE = /\{(workdir|prompt_file|session_ref)\}/g;
const UNKNOWN_SLOT_RE = /\{[^}]+\}/g;

function assertObject(value, name, filePath) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new SpawnError(E_CONFIG_LOAD, `${name} must be an object`, { file: filePath, key: name });
  }
}

function assertString(value, name, filePath) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new SpawnError(E_MISSING_KEY, `${name} must be a non-empty string`, { file: filePath, key: name });
  }
}

function assertArrayOfStrings(value, name, filePath) {
  if (!Array.isArray(value) || value.some((x) => typeof x !== 'string')) {
    throw new SpawnError(E_CONFIG_LOAD, `${name} must be an array of strings`, { file: filePath, key: name });
  }
}

function checkUnknownKeys(obj, knownSet, prefix, filePath) {
  for (const key of Object.keys(obj)) {
    if (!knownSet.has(key)) {
      throw new SpawnError(E_CONFIG_LOAD, `unknown key in ${prefix}: ${key}`, { file: filePath, key: `${prefix}.${key}` });
    }
  }
}

function detectUnknownSlots(value, prefix, filePath) {
  const str = typeof value === 'string' ? value : JSON.stringify(value);
  const matches = str.match(UNKNOWN_SLOT_RE);
  if (matches) {
    for (const m of matches) {
      if (!CLOSED_SLOTS.has(m)) {
        throw new SpawnError(E_UNKNOWN_SLOT, `unknown template slot ${m} in ${prefix}`, { file: filePath, key: prefix, slot: m });
      }
    }
  }
}

function validateSessionRef(sessionRef, profileName, filePath) {
  assertObject(sessionRef, `profiles.${profileName}.session_ref`, filePath);
  if (!sessionRef.source || !KNOWN_SESSION_REF_SOURCES.has(sessionRef.source)) {
    throw new SpawnError(E_CONFIG_LOAD, `profiles.${profileName}.session_ref.source must be one of ${Array.from(KNOWN_SESSION_REF_SOURCES).join(', ')}`, { file: filePath, key: `profiles.${profileName}.session_ref.source` });
  }
  if (sessionRef.source === 'stdout-json' && !sessionRef.field) {
    throw new SpawnError(E_MISSING_KEY, `profiles.${profileName}.session_ref.field is required for source stdout-json`, { file: filePath, key: `profiles.${profileName}.session_ref.field` });
  }
  if (sessionRef.source === 'stdout-json-event' && (!sessionRef.event || !sessionRef.field)) {
    throw new SpawnError(E_MISSING_KEY, `profiles.${profileName}.session_ref.event and field are required for source stdout-json-event`, { file: filePath, key: `profiles.${profileName}.session_ref` });
  }
}

function validateExecOrResume(block, blockName, profileName, filePath) {
  assertObject(block, `profiles.${profileName}.${blockName}`, filePath);
  checkUnknownKeys(block, blockName === 'exec' ? KNOWN_EXEC_KEYS : KNOWN_RESUME_KEYS, `profiles.${profileName}.${blockName}`, filePath);
  assertArrayOfStrings(block.argv, `profiles.${profileName}.${blockName}.argv`, filePath);
  if (!block.prompt || !KNOWN_PROMPT_VALUES.has(block.prompt)) {
    throw new SpawnError(E_CONFIG_LOAD, `profiles.${profileName}.${blockName}.prompt must be one of stdin|file|argv-last`, { file: filePath, key: `profiles.${profileName}.${blockName}.prompt` });
  }
  for (let i = 0; i < block.argv.length; i++) {
    detectUnknownSlots(block.argv[i], `profiles.${profileName}.${blockName}.argv[${i}]`, filePath);
  }
}

function validateCaps(caps, profileName, filePath) {
  assertObject(caps, `profiles.${profileName}.caps`, filePath);
  checkUnknownKeys(caps, KNOWN_CAPS_KEYS, `profiles.${profileName}.caps`, filePath);
  for (const key of KNOWN_CAPS_KEYS) {
    if (caps[key] !== undefined) {
      const ok = (typeof caps[key] === 'string' && caps[key].length > 0) || Number.isInteger(caps[key]);
      if (!ok) {
        throw new SpawnError(E_CONFIG_LOAD, `profiles.${profileName}.caps.${key} must be a non-empty string or integer`, { file: filePath, key: `profiles.${profileName}.caps.${key}` });
      }
    }
  }
}

function validateSandbox(sandbox, profileName, filePath) {
  assertObject(sandbox, `profiles.${profileName}.sandbox`, filePath);
  checkUnknownKeys(sandbox, KNOWN_SANDBOX_KEYS, `profiles.${profileName}.sandbox`, filePath);
  if (sandbox.ReadWritePaths !== undefined) {
    const arr = Array.isArray(sandbox.ReadWritePaths) ? sandbox.ReadWritePaths : [sandbox.ReadWritePaths];
    for (let i = 0; i < arr.length; i++) {
      detectUnknownSlots(arr[i], `profiles.${profileName}.sandbox.ReadWritePaths[${i}]`, filePath);
    }
  }
}

function validateEnv(env, profileName, filePath) {
  assertObject(env, `profiles.${profileName}.env`, filePath);
  checkUnknownKeys(env, KNOWN_ENV_KEYS, `profiles.${profileName}.env`, filePath);
  if (env.file !== undefined) assertString(env.file, `profiles.${profileName}.env.file`, filePath);
}

function validateHeaded(headed, profileName, filePath) {
  assertObject(headed, `profiles.${profileName}.headed`, filePath);
  checkUnknownKeys(headed, KNOWN_HEADED_KEYS, `profiles.${profileName}.headed`, filePath);
  if (!headed.tui || typeof headed.tui !== 'object') {
    throw new SpawnError(E_MISSING_KEY, `profiles.${profileName}.headed.tui must be an object`, { file: filePath, key: `profiles.${profileName}.headed.tui` });
  }
  checkUnknownKeys(headed.tui, KNOWN_TUI_KEYS, `profiles.${profileName}.headed.tui`, filePath);
  assertArrayOfStrings(headed.tui.argv, `profiles.${profileName}.headed.tui.argv`, filePath);
  for (let i = 0; i < headed.tui.argv.length; i++) {
    detectUnknownSlots(headed.tui.argv[i], `profiles.${profileName}.headed.tui.argv[${i}]`, filePath);
  }
}

function validateProfile(profile, name, filePath) {
  assertObject(profile, `profiles.${name}`, filePath);
  checkUnknownKeys(profile, KNOWN_PROFILE_KEYS, `profiles.${name}`, filePath);

  if (!profile.exec) {
    throw new SpawnError(E_MISSING_KEY, `profiles.${name}.exec is required`, { file: filePath, key: `profiles.${name}.exec` });
  }
  validateExecOrResume(profile.exec, 'exec', name, filePath);

  if (!profile.resume) {
    throw new SpawnError(E_MISSING_KEY, `profiles.${name}.resume is required`, { file: filePath, key: `profiles.${name}.resume` });
  }
  validateExecOrResume(profile.resume, 'resume', name, filePath);

  if (!profile.session_ref) {
    throw new SpawnError(E_MISSING_KEY, `profiles.${name}.session_ref is required`, { file: filePath, key: `profiles.${name}.session_ref` });
  }
  validateSessionRef(profile.session_ref, name, filePath);

  if (profile.headed) {
    validateHeaded(profile.headed, name, filePath);
  }

  if (!profile.workdir_root) {
    throw new SpawnError(E_MISSING_KEY, `profiles.${name}.workdir_root is required`, { file: filePath, key: `profiles.${name}.workdir_root` });
  }
  assertString(profile.workdir_root, `profiles.${name}.workdir_root`, filePath);

  if (!profile.caps) {
    throw new SpawnError(E_MISSING_KEY, `profiles.${name}.caps is required`, { file: filePath, key: `profiles.${name}.caps` });
  }
  validateCaps(profile.caps, name, filePath);

  if (profile.sandbox) validateSandbox(profile.sandbox, name, filePath);
  if (profile.env) validateEnv(profile.env, name, filePath);
}

function validateSpawnBlock(spawn, filePath) {
  assertObject(spawn, 'spawn', filePath);
  const known = new Set(['data_root', 'carrier', 'kill_grace_seconds']);
  checkUnknownKeys(spawn, known, 'spawn', filePath);
  if (spawn.data_root !== undefined) assertString(spawn.data_root, 'spawn.data_root', filePath);
  if (spawn.carrier !== undefined && !['auto', 'systemd', 'setsid'].includes(spawn.carrier)) {
    throw new SpawnError(E_CONFIG_LOAD, `spawn.carrier must be one of auto|systemd|setsid`, { file: filePath, key: 'spawn.carrier' });
  }
  if (spawn.kill_grace_seconds !== undefined && (!Number.isInteger(spawn.kill_grace_seconds) || spawn.kill_grace_seconds <= 0)) {
    throw new SpawnError(E_CONFIG_LOAD, `spawn.kill_grace_seconds must be a positive integer`, { file: filePath, key: 'spawn.kill_grace_seconds' });
  }
}

function validateBindBlock(bind, filePath) {
  assertObject(bind, 'bind', filePath);
  const known = new Set(['host', 'port']);
  checkUnknownKeys(bind, known, 'bind', filePath);
}

function validateAuthBlock(auth, filePath) {
  assertObject(auth, 'auth', filePath);
  const known = new Set(['senders_file']);
  checkUnknownKeys(auth, known, 'auth', filePath);
}

function loadConfig(filePath) {
  let raw;
  try {
    raw = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new SpawnError(E_CONFIG_LOAD, `cannot read config file: ${err.message}`, { file: filePath });
  }

  let parsed;
  try {
    parsed = yaml.load(raw);
  } catch (err) {
    throw new SpawnError(E_CONFIG_LOAD, `malformed YAML: ${err.message}`, { file: filePath });
  }

  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new SpawnError(E_CONFIG_LOAD, 'config must be a YAML mapping', { file: filePath });
  }

  checkUnknownKeys(parsed, KNOWN_TOP_KEYS, 'config root', filePath);

  if (parsed.bind) validateBindBlock(parsed.bind, filePath);
  if (parsed.auth) validateAuthBlock(parsed.auth, filePath);
  if (parsed.spawn) validateSpawnBlock(parsed.spawn, filePath);

  if (!parsed.default_workdir_root) {
    throw new SpawnError(E_MISSING_KEY, 'default_workdir_root is required at the top level', { file: filePath, key: 'default_workdir_root' });
  }
  assertString(parsed.default_workdir_root, 'default_workdir_root', filePath);

  if (!parsed.profiles || typeof parsed.profiles !== 'object' || Array.isArray(parsed.profiles)) {
    throw new SpawnError(E_MISSING_KEY, 'profiles must be a mapping', { file: filePath, key: 'profiles' });
  }

  const seen = new Set();
  for (const name of Object.keys(parsed.profiles)) {
    if (seen.has(name)) {
      throw new SpawnError(E_DUPLICATE_PROFILE, `duplicate profile: ${name}`, { file: filePath, key: `profiles.${name}` });
    }
    seen.add(name);
    validateProfile(parsed.profiles[name], name, filePath);
  }

  const config = {
    bind: parsed.bind || {},
    auth: parsed.auth || {},
    spawn: {
      data_root: parsed.spawn?.data_root || null,
      carrier: parsed.spawn?.carrier || 'auto',
      kill_grace_seconds: parsed.spawn?.kill_grace_seconds ?? 10,
    },
    default_workdir_root: parsed.default_workdir_root,
    profiles: parsed.profiles,
  };

  return config;
}

function resolveTemplateSlots(template, values) {
  return template.map((element) => {
    let out = element;
    SLOT_RE.lastIndex = 0;
    const matches = [...out.matchAll(SLOT_RE)];
    for (const m of matches) {
      const slot = m[0];
      const key = m[1];
      if (!(key in values)) {
        throw new SpawnError(E_MISSING_KEY, `template slot ${slot} has no value`, { slot });
      }
      out = out.replace(slot, values[key]);
    }
    return out;
  });
}

function canonicalizeWorkdir(requested, filePath) {
  if (requested === undefined || requested === null) return null;
  if (typeof requested !== 'string' || requested.length === 0) {
    throw new SpawnError(E_CONFIG_LOAD, 'workdir must be a non-empty string', { file: filePath });
  }
  try {
    const resolved = fs.realpathSync(path.resolve(requested));
    return resolved;
  } catch (err) {
    throw new SpawnError(E_CONFIG_LOAD, `workdir does not exist or is not resolvable: ${requested}`, { workdir: requested });
  }
}

// D58 open-item ruling (smallest shape): the per-execution launch dir lives at
// `<workspaceRoot>/.rbtv/sessions/<exec-id>/`. The sessions root is DERIVED, never a new
// config key. It MUST be a sibling of the heart store's `.rbtv/` (D58(3): `.rbtv/heart/` — the
// control-plane store — stays out of every worker's reach), so it is sourced FROM the store's
// own db path (`<ws>/.rbtv/heart/heart.db`), which guarantees the sibling relationship. index.js
// is frozen for this task and cannot pass the workspace root in, so the fallback chain mirrors
// index.js's own machine-agnostic resolution: the store's `.rbtv/`, then RBTV_IGNITE_WORKSPACE_ROOT,
// else null (a store with no `.rbtv/` shape — a test-only flat db — yields null, and the default
// branch then bases the session dir on the profile's own workdir_root, which is still contained).
function resolveWorkspaceRoot(heartDbPath) {
  if (heartDbPath) {
    const parts = path.resolve(heartDbPath).split(path.sep);
    const idx = parts.lastIndexOf('.rbtv');
    if (idx > 0) return parts.slice(0, idx).join(path.sep) || path.sep;
  }
  const env = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  if (env) return path.resolve(env);
  return null;
}

function sessionsRootFor(workspaceRoot) {
  return workspaceRoot ? path.join(workspaceRoot, '.rbtv', 'sessions') : null;
}

// D56 fix (D58 contract). BOTH branches now pass the SAME fail-closed containment check —
// the resolved dir must sit inside the profile's workdir_root or the spawn REFUSES
// (E_WORKDIR_ESCAPE). The former default branch returned `default_workdir_root` UNCHECKED
// (the fail-open); it now materializes a per-execution launch dir under the sessions root and
// enforces it exactly as the caller branch enforces a caller-supplied workdir. A worker that
// cannot be contained does not run (the D48 fail-closed direction).
function resolveWorkdir(profile, requestedWorkdir, defaultWorkdirRoot, filePath, opts = {}) {
  const { execId, sessionsRoot = null, workspaceRoot = null } = opts;

  // Resolve the profile's containment boundary to an absolute path. A machine-agnostic
  // committed workdir_root may be workspace-relative (the D58 repoint `.rbtv/sessions`, D26(3)):
  // resolve it against the workspace root the daemon runs under, never a stray process cwd.
  const workdirRootAbs = path.isAbsolute(profile.workdir_root)
    ? profile.workdir_root
    : path.resolve(workspaceRoot || process.cwd(), profile.workdir_root);

  if (requestedWorkdir === undefined || requestedWorkdir === null) {
    if (execId === undefined || execId === null) {
      throw new SpawnError(E_WORKDIR_MISSING, 'default-branch launch requires an exec id to materialize the session dir', { profile });
    }
    // The session dir is sourced from the sessions root (workspace-derived), which is
    // INDEPENDENT of the profile's workdir_root — so this check is not vacuous: a sessions
    // root that falls outside workdir_root (misconfiguration, or a divergence a mutation test
    // injects) is REFUSED. In production the two coincide; the check proves they do.
    const base = sessionsRoot || workdirRootAbs;
    fs.mkdirSync(workdirRootAbs, { recursive: true, mode: 0o700 });
    const sessionDir = path.join(base, String(execId));
    fs.mkdirSync(sessionDir, { recursive: true, mode: 0o700 });
    const resolved = fs.realpathSync(sessionDir);
    const allowedRoot = fs.realpathSync(workdirRootAbs);
    if (resolved !== allowedRoot && !resolved.startsWith(allowedRoot + path.sep)) {
      throw new SpawnError(E_WORKDIR_ESCAPE, `resolved session dir ${resolved} is outside profile workdir_root ${allowedRoot}`, { workdir: resolved, allowedRoot });
    }
    return resolved;
  }

  const resolved = canonicalizeWorkdir(requestedWorkdir, filePath);
  const allowedRoot = fs.realpathSync(workdirRootAbs);
  if (resolved !== allowedRoot && !resolved.startsWith(allowedRoot + path.sep)) {
    throw new SpawnError(E_WORKDIR_ESCAPE, `workdir ${resolved} is outside profile workdir_root ${allowedRoot}`, { workdir: resolved, allowedRoot });
  }
  return resolved;
}

module.exports = {
  loadConfig,
  resolveTemplateSlots,
  resolveWorkdir,
  resolveWorkspaceRoot,
  sessionsRootFor,
  CLOSED_SLOTS,
};
