'use strict';

// Chat-bridge configuration resolution (chat-bridge-spec.md; D104/D105).
//
// The bridge is ONE authenticated gateway SENDER (a `kind: bridge` row in the
// daemon's senders registry — gateway-cli-spec.md § Sender auth). It holds a
// bridge token and the gateway address, plus the chat transport's own credentials.
// It holds NO store handle, NO spawn path, NO queue handle (chat-bridge-spec.md
// § Forward path) — this file resolves configuration only, never capability.
//
// ⚑ SECRETS COME FROM THE ENVIRONMENT, NEVER FROM A COMMITTED FILE (D27:
// credentials never travel in git). Tokens are read from the process environment
// and never written back to disk or logged. The non-secret settings (allowlist,
// job/profile names, gateway address) may come from a JSON config file OR env.

const fs = require('node:fs');
const path = require('node:path');

// Fixed-width ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ). The gateway's enqueue-job
// parse requires exactly this shape for run_at (gateway/parse.js ISO_UTC), and
// the store's due test is a lexicographic compare that assumes it (heart-store).
function nowIsoUtc() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

// The environment variable names the bridge reads. Grouped here so the surface
// is auditable in one place; the SECRET ones are never echoed anywhere.
const ENV = {
  gatewayAddr: 'IGNITE_GATEWAY_ADDR',      // host[:port] of the daemon gateway (loopback/tailnet)
  bridgeToken: 'IGNITE_BRIDGE_TOKEN',      // SECRET — this bridge's gateway sender token (kind: bridge)
  configFile: 'IGNITE_CHAT_BRIDGE_CONFIG', // path to the non-secret JSON config
  slackAppToken: 'SLACK_APP_TOKEN',        // SECRET — Socket Mode app-level token (xapp-…)
  slackBotToken: 'SLACK_BOT_TOKEN',        // SECRET — bot token for chat.postMessage (xoxb-…)
  slackApiBase: 'SLACK_API_BASE',          // override for the Slack Web API base (tests point it at a mock)
};

const DEFAULT_SLACK_API_BASE = 'https://slack.com/api';

// The non-secret config file shape (all fields optional; env overrides win):
//   {
//     "gateway_addr": "127.0.0.1:7431",
//     "session_job_id": "chat-launch",     // catalogue slug: a launch-agent job
//     "session_profile": "worker",         // named launch profile the session runs
//     "send_message_job_id": "send-message", // catalogue slug: a send-message action-type job
//     "workdir": "/abs/path",              // optional workdir for the session
//     "allowlist": ["U0123ABC", "U0456DEF"] // Slack user IDs allowed to drive the bridge
//   }
function readConfigFile(filePath) {
  if (!filePath) return {};
  let raw;
  try {
    raw = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new Error(`chat-bridge config file not readable at ${filePath}: ${err.message}`);
  }
  try {
    const doc = JSON.parse(raw);
    if (doc === null || typeof doc !== 'object' || Array.isArray(doc)) {
      throw new Error('config must be a JSON object');
    }
    return doc;
  } catch (err) {
    throw new Error(`chat-bridge config file at ${filePath} is not valid JSON: ${err.message}`);
  }
}

// Resolve the effective config. `overrides` lets a probe/test inject values
// without touching the process environment. Overrides > env > config-file >
// built-in default, per field — an EXPLICIT override always wins, so a probe
// pointing at a throwaway daemon can never be silently redirected by an ambient
// IGNITE_GATEWAY_ADDR/SLACK_* in the shell (which could aim test traffic at the
// LIVE daemon or real Slack).
function resolveConfig(overrides = {}) {
  const env = process.env;
  const filePath = overrides.configFile || env[ENV.configFile] || null;
  const file = readConfigFile(filePath);

  const gatewayAddr =
    overrides.gatewayAddr || env[ENV.gatewayAddr] || file.gateway_addr || null;

  const bridgeToken = overrides.bridgeToken || env[ENV.bridgeToken] || null;

  const sessionJobId =
    overrides.sessionJobId || file.session_job_id || 'chat-launch';
  const sessionProfile =
    overrides.sessionProfile || file.session_profile || null;
  const sendMessageJobId =
    overrides.sendMessageJobId || file.send_message_job_id || 'send-message';
  const workdir = overrides.workdir || file.workdir || null;

  const allowlist = Array.isArray(overrides.allowlist)
    ? overrides.allowlist
    : (Array.isArray(file.allowlist) ? file.allowlist : []);

  const slackApiBase =
    overrides.slackApiBase || env[ENV.slackApiBase] || file.slack_api_base || DEFAULT_SLACK_API_BASE;
  const slackAppToken = overrides.slackAppToken || env[ENV.slackAppToken] || null;
  const slackBotToken = overrides.slackBotToken || env[ENV.slackBotToken] || null;

  return {
    gatewayAddr,
    bridgeToken,
    sessionJobId,
    sessionProfile,
    sendMessageJobId,
    workdir,
    allowlist,
    slack: {
      apiBase: slackApiBase,
      appToken: slackAppToken,
      botToken: slackBotToken,
    },
    configFilePath: filePath ? path.resolve(filePath) : null,
  };
}

module.exports = { resolveConfig, nowIsoUtc, ENV, DEFAULT_SLACK_API_BASE };
