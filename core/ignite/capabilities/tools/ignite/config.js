'use strict';

// API
// configPath(workspace)        — <installation>/.rbtv/config/ignite/config.json
// loadConfig(workspace)        — read and validate that file directly (field reference: core/rbtv/capabilities/templates/ignite-config.schema.json);
//                                returns the parsed object plus `workspace` (the absolute path it was read for);
//                                refuses dreamer.enabled true without dreamer.model
// updateConfig(workspace, fn)  — read, let fn(config) change it, validate, write atomically; returns the new config
// agentHome(config, slug)      — <installation>/.rbtv/agents/<slug>
// ignitePaths(home)            — database, conversations and turns under <agent>/runtime/ignite/
// resolveIgniteRuntime(home)   — those paths, or a refusal when the agent root still holds them
// storePath(config, slug)      — resolveIgniteRuntime(agentHome).database
// MIGRATION_COMMAND            — ignite runtime migrate
// envValue(workspace, name)    — a variable's value: the OS environment first, then <installation>/.rbtv/config/env/.env; null when unset
// slackToken(config, key)      — the token the config names under slack.<key>Env ('app' | 'bot' | 'owner'); throws when unset
// DREAMER_MODEL                — the model `ignite dreamer enable` records when dreamer.model is absent; never read at run time
// dreamerModelRequired(when)   — the refusal text for a missing dreamer.model: the key and an example value

const fs = require('node:fs');
const path = require('node:path');
const { agentHomeIn } = require('../../../../cast/capabilities/tools/cast/lib/agent');

const TOP_KEYS = ['slack', 'tools', 'dmAgent', 'routes', 'dreamer'];
const SLACK_KEYS = ['team', 'botUserId', 'ownerUserId', 'appTokenEnv', 'botTokenEnv', 'ownerTokenEnv', 'stoolsWorkspace'];
const TOOL_KEYS = ['cast', 'stools', 'audio'];
const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const ENV_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
const DREAMER_MODEL = Object.freeze({ harness: 'codex', model: 'gpt-6.1-sol', effort: 3 });

function configPath(workspace) {
  return path.join(workspace, '.rbtv', 'config', 'ignite', 'config.json');
}

// The installation a folder belongs to: the nearest folder, from start upward, holding ignite's config.
function findWorkspace(start) {
  let dir = path.resolve(start);
  for (;;) {
    if (fs.existsSync(configPath(dir))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function dreamerModelRequired(when) {
  return `dreamer.model required ${when}: add "model": ${JSON.stringify(DREAMER_MODEL)} under "dreamer" in .rbtv/config/ignite/config.json`;
}

function rejectUnknown(obj, allowed, label) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) throw new Error(`${label} must be an object`);
  for (const key of Object.keys(obj)) {
    if (!allowed.includes(key)) throw new Error(`unknown ${label} field: ${key}`);
  }
}

function reqString(obj, key, label) {
  const value = obj[key];
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} required`);
  return value;
}

function reqSlug(value, label) {
  if (typeof value !== 'string' || !SLUG.test(value)) throw new Error(`${label} must be a slug`);
  return value;
}

function reqEnvName(obj, key) {
  const value = reqString(obj, key, `slack.${key}`);
  if (!ENV_NAME.test(value)) throw new Error(`slack.${key} must be an environment variable name`);
  return value;
}

function reqWorkspaceName(value) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('slack.stoolsWorkspace required');
  if (value.includes('/') || value.includes('\\') || path.isAbsolute(value)) {
    throw new Error('slack.stoolsWorkspace must be a stools workspace name, not a path');
  }
  return value;
}

function validate(raw) {
  rejectUnknown(raw, TOP_KEYS, 'config');
  rejectUnknown(raw.slack, SLACK_KEYS, 'slack');
  reqString(raw.slack, 'team', 'slack.team');
  reqString(raw.slack, 'botUserId', 'slack.botUserId');
  reqString(raw.slack, 'ownerUserId', 'slack.ownerUserId');
  reqEnvName(raw.slack, 'appTokenEnv');
  reqEnvName(raw.slack, 'botTokenEnv');
  reqEnvName(raw.slack, 'ownerTokenEnv');
  reqWorkspaceName(raw.slack.stoolsWorkspace);
  rejectUnknown(raw.tools, TOOL_KEYS, 'tools');
  for (const key of TOOL_KEYS) reqString(raw.tools, key, `tools.${key}`);
  if (raw.dreamer !== undefined) {
    rejectUnknown(raw.dreamer, ['enabled', 'model'], 'dreamer');
    if (raw.dreamer.enabled !== undefined && typeof raw.dreamer.enabled !== 'boolean') throw new Error('dreamer.enabled must be a boolean');
    if (raw.dreamer.model !== undefined) {
      const model = raw.dreamer.model;
      rejectUnknown(model, ['harness', 'model', 'effort'], 'dreamer.model');
      if (!['codex', 'opencode', 'claude'].includes(model.harness)) throw new Error('dreamer.model.harness must be codex, opencode or claude');
      const name = reqString(model, 'model', 'dreamer.model.model');
      if (/\s/.test(name) || name.startsWith('-')) throw new Error('dreamer.model.model must be a cast model name');
      if (!Number.isInteger(model.effort) || model.effort < 1 || model.effort > 5) throw new Error('dreamer.model.effort must be an integer 1-5');
    } else if (raw.dreamer.enabled === true) {
      throw new Error(dreamerModelRequired('when dreamer.enabled is true'));
    }
  }
  if (raw.dmAgent !== undefined) reqSlug(raw.dmAgent, 'dmAgent');
  if (!raw.routes || typeof raw.routes !== 'object' || Array.isArray(raw.routes)) {
    throw new Error('routes must be an object');
  }
  for (const [channelId, slug] of Object.entries(raw.routes)) {
    if (!channelId.trim()) throw new Error('routes channel id required');
    reqSlug(slug, `routes.${channelId}`);
  }
  return raw;
}

function loadConfig(workspace) {
  if (!workspace || typeof workspace !== 'string') throw new Error('installation path required');
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(configPath(workspace), 'utf8'));
  } catch (error) {
    throw new Error(`cannot load Ignite config: ${error.message}`);
  }
  validate(raw);
  return { ...raw, dreamer: { enabled: false, ...raw.dreamer }, workspace: path.resolve(workspace) };
}

function updateConfig(workspace, change) {
  const { workspace: _unused, ...raw } = loadConfig(workspace);
  const next = change(raw) || raw;
  validate(next);
  const file = configPath(workspace);
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(next, null, 2)}\n`, 'utf8');
  fs.renameSync(tmp, file);
  return { ...next, dreamer: { enabled: false, ...next.dreamer }, workspace: path.resolve(workspace) };
}

function agentHome(config, slug) {
  if (!config?.workspace) throw new Error('config.workspace required');
  reqSlug(slug, 'agent slug');
  return agentHomeIn(config.workspace, slug);
}

const MIGRATION_COMMAND = 'ignite runtime migrate';
const MARKER_NAME = 'MIGRATED';
const DATABASE_NAME = 'state.sqlite';
const LEGACY_FILES = [DATABASE_NAME, `${DATABASE_NAME}-wal`, `${DATABASE_NAME}-shm`];
const LEGACY_DIRS = ['conversations', 'turns'];

function ignitePaths(home) {
  const root = path.join(home, 'runtime', 'ignite');
  return {
    root,
    database: path.join(root, DATABASE_NAME),
    conversations: path.join(root, 'conversations'),
    turns: path.join(root, 'turns'),
    marker: path.join(root, MARKER_NAME),
  };
}

function migrationGuardPath(home) {
  return path.join(home, 'runtime', '.ignite-migrating');
}

function migrationInvocation(slug, workspace) {
  if (slug && workspace) return `${MIGRATION_COMMAND} --agent ${slug} --installation ${workspace}`;
  return MIGRATION_COMMAND;
}

function legacyLayout(home) {
  const found = [];
  for (const name of LEGACY_FILES) {
    const file = path.join(home, name);
    if (fs.existsSync(file)) found.push(file);
  }
  for (const name of LEGACY_DIRS) {
    const dir = path.join(home, name);
    if (fs.existsSync(dir)) found.push(dir);
  }
  return found;
}

function resolveIgniteRuntime(home, opts = {}) {
  if (!home) throw new Error('agent home required');
  if (fs.existsSync(migrationGuardPath(home))) {
    throw new Error(`Ignite runtime migration in progress at ${home}; retry after ${MIGRATION_COMMAND} finishes`);
  }
  const paths = ignitePaths(home);
  const legacy = legacyLayout(home);
  if (legacy.length && !fs.existsSync(paths.marker)) {
    if (fs.existsSync(paths.root)) {
      throw new Error(`ambiguous Ignite layout at ${home}: runtime/ignite exists without ${MARKER_NAME} and legacy files remain; refused`);
    }
    throw new Error(`legacy Ignite layout at ${home}; no fallback. Run ${migrationInvocation(opts.slug, opts.workspace)}`);
  }
  return paths;
}

function storePath(config, slug) {
  return resolveIgniteRuntime(agentHome(config, slug), { workspace: config.workspace, slug }).database;
}

function envValue(workspace, name) {
  if (process.env[name]) return process.env[name];
  let text;
  try { text = fs.readFileSync(path.join(workspace, '.rbtv', 'config', 'env', '.env'), 'utf8'); } catch { return null; }
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 0 || trimmed.slice(0, eq).trim() !== name) continue;
    let value = trimmed.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    return value || null;
  }
  return null;
}

function slackToken(config, key) {
  const name = config.slack[`${key}TokenEnv`];
  const value = envValue(config.workspace, name);
  if (!value) throw new Error(`Slack ${key} token ${name} is unset`);
  return value;
}

module.exports = {
  configPath, findWorkspace, loadConfig, updateConfig, agentHome, storePath, envValue, slackToken,
  DREAMER_MODEL, dreamerModelRequired, ignitePaths, resolveIgniteRuntime, legacyLayout,
  migrationGuardPath, migrationInvocation, MIGRATION_COMMAND, MARKER_NAME, DATABASE_NAME,
  LEGACY_FILES, LEGACY_DIRS,
};
