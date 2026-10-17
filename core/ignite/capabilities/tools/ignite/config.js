'use strict';

// API
// configPath(workspace)        — <installation>/.rbtv/config/ignite/config.json
// loadConfig(workspace)        — read and validate that file directly (field reference: core/rbtv/capabilities/templates/ignite-config.schema.json);
//                                returns the parsed object plus `workspace` (the absolute path it was read for);
//                                a legacy dreamer section is ignored and omitted from the result
// updateConfig(workspace, fn)  — read, let fn(config) change it, validate, write atomically; returns the new config;
//                                the next write omits a legacy dreamer section
// agentHome(config, slug)      — <installation>/.rbtv/agents/<slug>
// ignitePaths(home)            — database, conversations and turns under <agent>/runtime/ignite/
// resolveIgniteRuntime(home)   — those paths, or a refusal when the agent root still holds them
// storePath(config, slug)      — resolveIgniteRuntime(agentHome).database
// MIGRATION_COMMAND            — ignite runtime migrate
// envValue(workspace, name, env?) — a variable's value: process/supplied environment first, then <installation>/.rbtv/config/env/.env; null when unset
// slackToken(config, key)      — the token the config names under slack.<key>Env ('app' | 'bot' | 'owner'); throws when unset
// paymentsConfig(config)       — { webhookPort, connectors, timeZone, currency } with their defaults (8787, ['asaas'],
//                                America/Sao_Paulo, BRL) when the config has a payments section, which turns the payment
//                                gate's service side on; else null. payments.providers, the older spelling of
//                                payments.connectors, is read as connectors; both given is refused
// listenersConfig(config)      — { whatsapp?, google? } for each listener whose owner allowlist is set; a section
//                                without owner is omitted (that adapter stays off). google.pollMs is kept only when
//                                it is a positive integer. null when the config has no listeners section
// timeZoneProblem(zone) / currencyProblem(code) — null for an IANA time zone / an ISO 4217 code with two decimals,
//                                else the reason; the one check of both, used here and by the payment gate

const fs = require('node:fs');
const path = require('node:path');
const { agentHomeIn } = require('../../../../cast/capabilities/tools/cast/lib/agent');

const TOP_KEYS = ['slack', 'tools', 'dmAgent', 'routes', 'payments', 'listeners'];
const LEGACY_CONFIG_KEY = 'dreamer';
const SLACK_KEYS = ['team', 'botUserId', 'ownerUserId', 'appTokenEnv', 'botTokenEnv', 'ownerTokenEnv', 'stoolsWorkspace'];
const TOOL_KEYS = ['cast', 'stools', 'audio'];
const PAYMENT_KEYS = ['webhookPort', 'connectors', 'providers', 'timeZone', 'currency']; // providers: the older spelling of connectors
const LISTENER_KEYS = ['whatsapp', 'google'];
const WHATSAPP_LISTENER_KEYS = ['account', 'owner', 'secretEnv', 'port'];
const GOOGLE_LISTENER_KEYS = ['account', 'mailbox', 'owner', 'agent', 'pollMs'];
const PAYMENT_DEFAULTS = Object.freeze({ webhookPort: 8787, connectors: ['asaas'], timeZone: 'America/Sao_Paulo', currency: 'BRL' });
const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const ENV_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;

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

function dropLegacySection(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || !Object.hasOwn(raw, LEGACY_CONFIG_KEY)) return raw;
  if (TOP_KEYS.includes(LEGACY_CONFIG_KEY)) return raw;
  const next = { ...raw };
  delete next[LEGACY_CONFIG_KEY];
  return next;
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
  if (raw.dmAgent !== undefined) reqSlug(raw.dmAgent, 'dmAgent');
  if (!raw.routes || typeof raw.routes !== 'object' || Array.isArray(raw.routes)) {
    throw new Error('routes must be an object');
  }
  for (const [channelId, slug] of Object.entries(raw.routes)) {
    if (!channelId.trim()) throw new Error('routes channel id required');
    reqSlug(slug, `routes.${channelId}`);
  }
  if (raw.payments !== undefined) {
    rejectUnknown(raw.payments, PAYMENT_KEYS, 'payments');
    const port = raw.payments.webhookPort;
    if (port !== undefined && (!Number.isInteger(port) || port < 1 || port > 65535)) {
      throw new Error('payments.webhookPort must be a port number from 1 to 65535');
    }
    if (raw.payments.connectors !== undefined && raw.payments.providers !== undefined) { // older spelling
      throw new Error('payments.connectors replaces payments.providers: give one'); // older spelling
    }
    for (const key of ['connectors', 'providers']) { // providers: the older spelling
      const list = raw.payments[key];
      if (list !== undefined && (!Array.isArray(list) || !list.every((name) => typeof name === 'string' && SLUG.test(name)))) {
        throw new Error(`payments.${key} must be a list of connector names, such as ["asaas"]`);
      }
    }
    const zone = raw.payments.timeZone;
    if (zone !== undefined && timeZoneProblem(zone)) throw new Error(`payments.timeZone ${timeZoneProblem(zone)}`);
    const currency = raw.payments.currency;
    if (currency !== undefined && currencyProblem(currency)) throw new Error(`payments.currency ${currencyProblem(currency)}`);
  }
  if (raw.listeners !== undefined) validateListeners(raw.listeners);
  return raw;
}

function noColon(value, label) {
  const text = reqString({ value }, 'value', label);
  if (text.includes(':')) throw new Error(`${label} cannot contain a colon`);
  return text;
}

function validateListeners(raw) {
  rejectUnknown(raw, LISTENER_KEYS, 'listeners');
  if (raw.whatsapp !== undefined) {
    rejectUnknown(raw.whatsapp, WHATSAPP_LISTENER_KEYS, 'listeners.whatsapp');
    if (raw.whatsapp.account !== undefined) noColon(raw.whatsapp.account, 'listeners.whatsapp.account');
    if (raw.whatsapp.owner !== undefined) noColon(raw.whatsapp.owner, 'listeners.whatsapp.owner');
    if (raw.whatsapp.secretEnv !== undefined && !ENV_NAME.test(raw.whatsapp.secretEnv)) {
      throw new Error('listeners.whatsapp.secretEnv must be an environment variable name');
    }
    const port = raw.whatsapp.port;
    if (port !== undefined && (!Number.isInteger(port) || port < 1 || port > 65535)) {
      throw new Error('listeners.whatsapp.port must be a port number from 1 to 65535');
    }
  }
  if (raw.google !== undefined) {
    rejectUnknown(raw.google, GOOGLE_LISTENER_KEYS, 'listeners.google');
    if (raw.google.account !== undefined) reqSlug(raw.google.account, 'listeners.google.account');
    if (raw.google.mailbox !== undefined) noColon(raw.google.mailbox, 'listeners.google.mailbox');
    if (raw.google.owner !== undefined) noColon(raw.google.owner, 'listeners.google.owner');
    if (raw.google.agent !== undefined) reqSlug(raw.google.agent, 'listeners.google.agent');
    const poll = raw.google.pollMs;
    if (poll !== undefined && (!Number.isInteger(poll) || poll < 1)) {
      throw new Error('listeners.google.pollMs must be a positive number of milliseconds');
    }
  }
}

function timeZoneProblem(zone) {
  if (typeof zone !== 'string' || !zone.trim()) return 'must be an IANA time zone, such as America/Sao_Paulo';
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: zone });
    return null;
  } catch {
    return 'must be an IANA time zone, such as America/Sao_Paulo';
  }
}

// Amounts are kept in hundredths, so only a currency with two decimals fits.
function currencyProblem(code) {
  if (typeof code !== 'string' || !/^[A-Z]{3}$/.test(code)) return 'must be an ISO 4217 currency code, such as BRL';
  if (typeof Intl.supportedValuesOf === 'function' && !Intl.supportedValuesOf('currency').includes(code)) {
    return 'must be an ISO 4217 currency code, such as BRL';
  }
  const digits = new Intl.NumberFormat('en', { style: 'currency', currency: code }).resolvedOptions().maximumFractionDigits;
  return digits === 2 ? null : 'must be a currency with two decimals: amounts are kept in hundredths';
}

function listenersConfig(config) {
  const raw = config?.listeners;
  if (!raw) return null;
  const out = {};
  const whatsapp = raw.whatsapp;
  if (whatsapp?.owner && whatsapp.account && whatsapp.secretEnv) {
    out.whatsapp = { account: whatsapp.account, owner: whatsapp.owner, secretEnv: whatsapp.secretEnv, port: whatsapp.port || 8791 };
  }
  const google = raw.google;
  if (google?.owner && google.account && google.mailbox && google.agent) {
    out.google = {
      account: google.account,
      mailbox: google.mailbox,
      owner: google.owner,
      agent: google.agent,
      ...(Number.isInteger(google.pollMs) && google.pollMs > 0 ? { pollMs: google.pollMs } : {}),
    };
  }
  return out;
}

function paymentsConfig(config) {
  if (!config?.payments) return null;
  const { providers, ...section } = config.payments; // older spelling of connectors
  if (providers !== undefined && section.connectors === undefined) section.connectors = providers; // older spelling
  return { ...PAYMENT_DEFAULTS, ...section };
}

function loadConfig(workspace) {
  if (!workspace || typeof workspace !== 'string') throw new Error('installation path required');
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(configPath(workspace), 'utf8'));
  } catch (error) {
    throw new Error(`cannot load Ignite config: ${error.message}`);
  }
  validate(dropLegacySection(raw));
  return { ...dropLegacySection(raw), workspace: path.resolve(workspace) };
}

function updateConfig(workspace, change) {
  const { workspace: _unused, ...raw } = loadConfig(workspace);
  const next = dropLegacySection(change(raw) || raw);
  validate(next);
  const file = configPath(workspace);
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(next, null, 2)}\n`, 'utf8');
  fs.renameSync(tmp, file);
  return { ...next, workspace: path.resolve(workspace) };
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

// Ordinary/exported assignments and matching quotes are read literally, first nonempty value.
// An explicit environment lets callers preserve their process-value normalization.
function envValue(workspace, name, env = process.env) {
  if (env[name]) return env[name];
  let text;
  try { text = fs.readFileSync(path.join(workspace, '.rbtv', 'config', 'env', '.env'), 'utf8'); } catch { return null; }
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 0 || trimmed.slice(0, eq).trim().replace(/^export\s+/, '') !== name) continue;
    let value = trimmed.slice(eq + 1).trim();
    if (value.length > 1 && ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'")))) {
      value = value.slice(1, -1);
    }
    if (value) return value;
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
  configPath, findWorkspace, loadConfig, updateConfig, agentHome, storePath, envValue, slackToken, paymentsConfig, listenersConfig,
  timeZoneProblem, currencyProblem,
  ignitePaths, resolveIgniteRuntime, legacyLayout,
  migrationGuardPath, migrationInvocation, MIGRATION_COMMAND, MARKER_NAME, DATABASE_NAME,
  LEGACY_FILES, LEGACY_DIRS,
};
