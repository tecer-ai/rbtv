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
// job names, gateway address) may come from a JSON config file OR env.

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
  systemChannelId: 'RBTV_SYSTEM_CHANNEL_ID', // the ONE system channel [T5-R1] — daemon-level events, alarms, the §5 digest
};

const DEFAULT_SLACK_API_BASE = 'https://slack.com/api';

// The non-secret config file shape (all fields optional; env overrides win):
//   {
//     "gateway_addr": "127.0.0.1:7431",
//     "session_job_id": "chat-launch",     // catalogue slug: a launch-agent job
//     "send_message_job_id": "send-message", // catalogue slug: a send-message action-type job
//     "workdir": "/abs/path",              // optional workdir for the session
//     "workspace_root": "/abs/path",       // workspace whose .rbtv/goals/ homes goal-master seats
//     "channel_prefix": "goal-",           // goal↔channel name derivation (task 7.58)
//     "master_profile": "master",          // profile for DM (master) traffic; defaults to session_profile
//     "goal_profile": "worker",            // profile for goal-channel traffic; defaults to session_profile
//     "state_file": "/abs/path/chat-state.json", // conversation state across restarts (opt-in; see below)
//     "live_sessions": true,               // try the warm (live-session) leg before the cold path
//     "bus_ferry": false,                  // push coordination-bus rows addressed to `master` to the owner DM
//     "bus_ferry_dm_user": "U0123ABC",     // whose DM (default: the FIRST allowlist entry)
//     "owner_user": "U0123ABC",            // the ONE user auto-invited to a new REAL goal channel
//                                          // (default: the FIRST allowlist entry)
//     "system_channel_id": "C0123ABC",     // the ONE system channel [T5-R1]: daemon-level events
//                                          // and the 2-hourly system digest (spec-owner-io §5)
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
  const sendMessageJobId =
    overrides.sendMessageJobId || file.send_message_job_id || 'send-message';
  const workdir = overrides.workdir || file.workdir || null;
  // The workspace whose `.rbtv/goals/` holds the goal runs. A goal-channel session is
  // homed at that goal's OPEN run's `goal-master` seat (forward-path.js), so the seat's
  // own descriptor chain carries its identity — the bridge ships no behavioural text.
  // Unconfigured is not fatal: master/mention traffic is unaffected, and goal traffic
  // refuses loudly with an owner-facing notice rather than launching somewhere arbitrary.
  const workspaceRoot = overrides.workspaceRoot || file.workspace_root || null;

  // Task 7.58 — the goal↔channel surface. `channelPrefix` is what makes the
  // goal→channel name a BIJECTION (goal-channel-map.js); it also bounds which
  // channels this bridge will ever create, so a deployment under a test-channels-only
  // ruling sets it to `test-` and the bridge cannot create anything outside that
  // namespace.
  const channelPrefix =
    overrides.channelPrefix || file.channel_prefix || 'goal-';

  // ── `master_profile` · `goal_profile` · `master_effort` — DELETED 2026-08-11 ─────────────────
  // (launch-cast unification, owner ruling D2. Design: `build/launch-cast-unification.md`.)
  //
  // THE TRANSPORT DOES NOT NAME EXECUTION. These three keys let the surface a message arrived on
  // decide which harness, model and reasoning rung an agent ran at — so one seat answered a DM as
  // one model and the same seat answered a goal thread as another, with its own `seat.md` saying
  // a third thing. The seat's record is the authority now, resolved daemon-side at every launch
  // door (`launch-profiles/catalog.js#specForSeatCast`), and a seat that declares no cast REFUSES
  // rather than inheriting whatever the transport happened to carry.
  //
  // ── `session_profile` — DELETED 2026-08-12 (`#d-abolish-profile-names`, task 7.787) ──────────
  // It was the LAST of the four, and it survived the 2026-08-11 cut for exactly one reason its own
  // comment stated: it "decides NOTHING" but `launch-agent` required a non-empty `profile`
  // argument, so the enqueue had to carry SOMETHING. That requirement is gone — `launch-agent`'s
  // REQUIRED_ARGS is now empty and the daemon derives every launch from the seat's own descriptor
  // — so the key has nothing left to satisfy and is removed rather than left as a value nobody
  // reads. This bridge now names no execution at all, in any field.
  //
  // A deployment still carrying any of the four keys is not broken by their presence: they are
  // simply never read.

  // Conversation state across restarts (chat-bridge.js § persistence). NON-SECRET
  // (conversation ids and Slack channel/thread ids only — never a token), so it may
  // come from the config file. UNSET is the default and means exactly today's
  // in-memory behaviour: persistence is strictly opt-in. MUST be absolute — a
  // relative path would resolve against the daemon's cwd, so the same config would
  // read a different file depending on how the unit was started; that is a silent
  // amnesia, which is the exact bug this key exists to fix. Refused loudly instead.
  const stateFile = overrides.stateFile || file.state_file || null;
  if (stateFile && !path.isAbsolute(stateFile)) {
    throw new Error(`chat-bridge state_file must be an absolute path, got: ${stateFile}`);
  }

  // ── The warm leg (live-session-design.md §1/§4) ────────────────────────────────────────────
  // DEFAULT ON. The flag is the bridge's own decision — whether to TRY the warm path before the
  // cold one — and it is the only one of the design's three knobs that belongs here. The other
  // two (`live_session_idle_ms`, `live_session_max`) govern processes the DAEMON holds and the
  // memory they occupy, so they are the daemon's knobs and are read there from
  // RBTV_IGNITE_LIVE_IDLE_MS / RBTV_IGNITE_LIVE_MAX on its unit; a bridge that could set them
  // would be dictating another process's resource policy over the wire. Turning this flag off
  // restores the pre-live behaviour exactly: every message takes the cold path.
  const liveSessions = overrides.liveSessions != null
    ? Boolean(overrides.liveSessions)
    : (file.live_sessions != null ? Boolean(file.live_sessions) : true);

  const allowlist = Array.isArray(overrides.allowlist)
    ? overrides.allowlist
    : (Array.isArray(file.allowlist) ? file.allowlist : []);

  // The bus ferry (bus-ferry.js): coordination bus → owner DM, one way. OPT-IN and
  // NON-SECRET, so it lives in the config file. It needs `workspace_root` to know what
  // to enumerate; enabled without one it logs loudly and stays disabled rather than
  // guessing a tree. The DM target defaults to the FIRST allowlist entry — the owner is
  // who the allowlist exists for, and a ferry with no addressee is a no-op.
  const busFerry = overrides.busFerry != null ? Boolean(overrides.busFerry) : Boolean(file.bus_ferry);
  const busFerryDmUser =
    overrides.busFerryDmUser || file.bus_ferry_dm_user || (allowlist.length ? allowlist[0] : null);

  // The owner's Slack user id — the ONLY id `goal-channel-map.js#ensureChannel` may
  // invite into a channel it just created (owner ruling 2026-08-10, issue C-3). Same
  // default as the ferry's DM target and for the same reason: the allowlist exists for
  // the owner, so its first entry IS the owner. Unset ⇒ no invite is ever attempted.
  const ownerUser =
    overrides.ownerUser || file.owner_user || (allowlist.length ? allowlist[0] : null);

  // The system channel — where daemon-level events and the 2-hourly system digest go [T5-R1,
  // spec-owner-io §5]. NON-SECRET (a channel id), so it may come from the config file; the ENV name
  // is the SAME one `capabilities/daemon-watchdog/tool/watchdog-alarm.js` reads, because there is
  // one system channel and two processes that post to it. Unset is not fatal and is not guessed:
  // the digest is not wired and says so (`glance.js`), and every other surface is unaffected.
  const systemChannelId =
    overrides.systemChannelId || env[ENV.systemChannelId] || file.system_channel_id || null;

  const slackApiBase =
    overrides.slackApiBase || env[ENV.slackApiBase] || file.slack_api_base || DEFAULT_SLACK_API_BASE;
  const slackAppToken = overrides.slackAppToken || env[ENV.slackAppToken] || null;
  const slackBotToken = overrides.slackBotToken || env[ENV.slackBotToken] || null;

  return {
    gatewayAddr,
    bridgeToken,
    sessionJobId,
    sendMessageJobId,
    workdir,
    workspaceRoot,
    channelPrefix,
    stateFile,
    busFerry,
    busFerryDmUser,
    liveSessions,
    ownerUser,
    systemChannelId,
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
