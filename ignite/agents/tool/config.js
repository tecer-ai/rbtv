'use strict';

// API
// loadConfig(workspace) — read and validate <workspace>/.rbtv/agents/ignite.json
// agentHome(config, slug) — <workspace>/.rbtv/agents/<slug>
// storePath(config, slug) — <agentHome>/state.sqlite

const fs = require('node:fs');
const path = require('node:path');

const TOP_KEYS = ['workspace', 'slack', 'tools', 'defaultLaunch', 'dmAgent', 'routes'];
const SLACK_KEYS = ['team', 'botUserId', 'ownerUserId', 'botTokenFile', 'appTokenSource', 'ownerTokenFile', 'stoolsWorkspace'];
const TOOL_KEYS = ['cast', 'stools', 'audio'];
const LAUNCH_KEYS = ['harness', 'model', 'effort', 'voice'];
const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;

function samePath(left, right) {
  const norm = (value) => {
    const abs = path.resolve(value);
    try { return fs.realpathSync(abs); } catch { return abs; }
  };
  return norm(left) === norm(right);
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

function reqAbs(obj, key, label) {
  const value = reqString(obj, key, label);
  if (!path.isAbsolute(value)) throw new Error(`${label} must be an absolute path`);
  return value;
}

function reqSlug(value, label) {
  if (typeof value !== 'string' || !SLUG.test(value)) throw new Error(`${label} must be a slug`);
  return value;
}

function reqWorkspaceName(value) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('slack.stoolsWorkspace required');
  if (value.includes('/') || value.includes('\\') || path.isAbsolute(value)) {
    throw new Error('slack.stoolsWorkspace must be a stools workspace name, not a path');
  }
  return value;
}

function reqTokenSource(value) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('slack.appTokenSource required');
  if (value.includes('/') || value.startsWith('.')) {
    if (!path.isAbsolute(value)) throw new Error('slack.appTokenSource path must be absolute');
    return value;
  }
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(value)) {
    throw new Error('slack.appTokenSource must be an env var name or an absolute path');
  }
  return value;
}

function loadConfig(workspace) {
  if (!workspace || typeof workspace !== 'string') throw new Error('workspace path required');
  const file = path.join(workspace, '.rbtv', 'agents', 'ignite.json');
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    throw new Error(`cannot load workspace config: ${error.message}`);
  }
  rejectUnknown(raw, TOP_KEYS, 'config');
  if (!samePath(reqString(raw, 'workspace', 'workspace'), workspace)) {
    throw new Error('config workspace does not match the runtime workspace path');
  }
  rejectUnknown(raw.slack, SLACK_KEYS, 'slack');
  reqString(raw.slack, 'team', 'slack.team');
  reqString(raw.slack, 'botUserId', 'slack.botUserId');
  reqString(raw.slack, 'ownerUserId', 'slack.ownerUserId');
  reqAbs(raw.slack, 'botTokenFile', 'slack.botTokenFile');
  reqAbs(raw.slack, 'ownerTokenFile', 'slack.ownerTokenFile');
  reqTokenSource(raw.slack.appTokenSource);
  reqWorkspaceName(raw.slack.stoolsWorkspace);
  rejectUnknown(raw.tools, TOOL_KEYS, 'tools');
  for (const key of TOOL_KEYS) reqString(raw.tools, key, `tools.${key}`);
  rejectUnknown(raw.defaultLaunch, LAUNCH_KEYS, 'defaultLaunch');
  reqString(raw.defaultLaunch, 'harness', 'defaultLaunch.harness');
  reqString(raw.defaultLaunch, 'model', 'defaultLaunch.model');
  reqString(raw.defaultLaunch, 'effort', 'defaultLaunch.effort');
  if (raw.defaultLaunch.voice != null && typeof raw.defaultLaunch.voice !== 'string') {
    throw new Error('defaultLaunch.voice must be a string');
  }
  reqSlug(raw.dmAgent, 'dmAgent');
  if (!raw.routes || typeof raw.routes !== 'object' || Array.isArray(raw.routes)) {
    throw new Error('routes must be an object');
  }
  for (const [channelId, slug] of Object.entries(raw.routes)) {
    if (!channelId.trim()) throw new Error('routes channel id required');
    reqSlug(slug, `routes.${channelId}`);
  }
  return raw;
}

function agentHome(config, slug) {
  if (!config?.workspace) throw new Error('config.workspace required');
  reqSlug(slug, 'agent slug');
  return path.join(config.workspace, '.rbtv', 'agents', slug);
}

function storePath(config, slug) {
  return path.join(agentHome(config, slug), 'state.sqlite');
}

module.exports = { loadConfig, agentHome, storePath };
