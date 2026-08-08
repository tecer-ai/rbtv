'use strict';

// THE GOAL-CHANNEL OPERATOR SURFACE (task 7.58) — and, since task C3, the surface the
// daemon itself invokes.
//
// `goal-channel-design.md` settles WHO creates a goal's channel (the bridge, at goal
// registration) and WHAT happens at close (archive, never delete). This CLI was
// authored as the stand-in caller under the pre-ruled degrade (milestone-dag §1 branch
// B3) because no hook existed: same functions, same idempotence, invoked by hand
// instead of by an event.
//
// ⚑ THAT IS NO LONGER THE ONLY WAY IN (task C3, 2026-08-08). `server/ticker/
// goal-channel-start.js` composes `<node> <this file> ensure <goal>` and the daemon
// launches it at an INTERACTIVE goal's run start — so `ensure` now has a machine caller
// as well as a human one, and its argv is asserted BYTE-EXACT by
// `server/ticker/probes/probe-goal-channel-start.js`. Renaming this file, moving it, or
// changing the `ensure` verb's argument shape breaks that caller; the probe is what
// catches it. The hand-invoked path is unchanged and still supported.
//
// ⚑ SECRETS: `SLACK_BOT_TOKEN` comes from the environment and is NEVER printed,
// logged, or echoed — not even truncated. The only identity this prints is the one
// Slack itself reports back from `auth.test` (team + bot user), which is not a
// credential.
//
// ⚑ There is no invite/kick path here either — see goal-channel-map.js. This CLI
// cannot add anyone to a channel, which is what makes a "the owner is in no test
// channel" guarantee mechanical rather than procedural.
//
// Usage:
//   node goal-channel-cli.js whoami
//   node goal-channel-cli.js ensure <goal-id>   [--prefix test-]
//   node goal-channel-cli.js list               [--prefix test-]
//   node goal-channel-cli.js members <channel-id>
//   node goal-channel-cli.js post <goal-id> <text…>
//   node goal-channel-cli.js retire <goal-id>   [--prefix test-]

const { createSlackSocketMode } = require('./slack-socket-mode');
const { createGoalChannelMap, channelNameForGoal } = require('./goal-channel-map');

function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) { flags[argv[i].slice(2)] = argv[i + 1]; i += 1; }
    else positional.push(argv[i]);
  }
  return { positional, flags };
}

function out(obj) { process.stdout.write(JSON.stringify(obj, null, 2) + '\n'); }

async function main() {
  const { positional, flags } = parseArgs(process.argv.slice(2));
  const cmd = positional[0];
  const prefix = flags.prefix || process.env.IGNITE_CHANNEL_PREFIX || 'goal-';
  const botToken = process.env.SLACK_BOT_TOKEN || null;
  if (!botToken) { out({ ok: false, error: 'SLACK_BOT_TOKEN not set in the environment' }); process.exit(2); }

  const transport = createSlackSocketMode({
    appToken: process.env.SLACK_APP_TOKEN || null,
    botToken,
    apiBase: process.env.SLACK_API_BASE || undefined,
    onMessage: () => {},          // this CLI never listens; the callback is required by the factory
    logger: null,
  });
  const map = createGoalChannelMap({ slack: transport, prefix, logger: null });

  // A raw Slack read the map does not need but an operator does. Still an outbound
  // HTTPS call on the bot token — no new capability.
  //
  // ⚑ TRANSPORT MATTERS PER METHOD. Slack's cursor-paginated READ methods
  // (`conversations.members`, `conversations.list`, `users.*`) reject a JSON body
  // with `invalid_arguments` — they take GET query parameters (or form encoding).
  // Only the WRITE methods accept `application/json`. Found live: a JSON-bodied
  // `conversations.members` returned `invalid_arguments`, which reads like a bad
  // channel id and is nothing of the kind.
  async function rawGet(method, params) {
    const qs = new URLSearchParams(params || {}).toString();
    const res = await fetch(`${process.env.SLACK_API_BASE || 'https://slack.com/api'}/${method}?${qs}`, {
      method: 'GET',
      headers: { authorization: `Bearer ${botToken}` },
    });
    return res.json();
  }

  async function rawPost(method, body) {
    const res = await fetch(`${process.env.SLACK_API_BASE || 'https://slack.com/api'}/${method}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json; charset=utf-8', authorization: `Bearer ${botToken}` },
      body: JSON.stringify(body || {}),
    });
    return res.json();
  }

  switch (cmd) {
    case 'whoami': {
      const r = await rawPost('auth.test', {});
      out({ ok: Boolean(r && r.ok), team: r && r.team, user: r && r.user, user_id: r && r.user_id, bot_id: r && r.bot_id, error: r && r.error });
      process.exit(r && r.ok ? 0 : 1);
      break;
    }
    case 'ensure': {
      const goalId = positional[1];
      if (!goalId) { out({ ok: false, error: 'usage: ensure <goal-id>' }); process.exit(2); }
      const derived = channelNameForGoal(goalId, prefix);
      const res = await map.ensureChannel(goalId);
      out({ ...res, derivedName: derived });
      process.exit(res.ok ? 0 : 1);
      break;
    }
    case 'list': {
      const res = await map.recover();
      const bound = [];
      // `recover()` binds; report what it bound, plus the raw visible set for audit.
      const all = await transport.listChannels({ excludeArchived: false });
      out({ ...res, prefix, channels: (all.channels || []).map((c) => ({ id: c.id, name: c.name, is_archived: c.is_archived, goalId: map.goalForChannel(c.id) })), bound });
      process.exit(res.ok ? 0 : 1);
      break;
    }
    case 'members': {
      const channel = positional[1];
      if (!channel) { out({ ok: false, error: 'usage: members <channel-id>' }); process.exit(2); }
      const r = await rawGet('conversations.members', { channel, limit: 200 });
      out({ ok: Boolean(r && r.ok), channel, members: (r && r.members) || [], error: r && r.error });
      process.exit(r && r.ok ? 0 : 1);
      break;
    }
    case 'post': {
      const goalId = positional[1];
      const text = positional.slice(2).join(' ');
      if (!goalId || !text) { out({ ok: false, error: 'usage: post <goal-id> <text…>' }); process.exit(2); }
      await map.recover();
      const channel = map.channelForGoal(goalId);
      if (!channel) { out({ ok: false, error: `no channel bound for goal ${goalId}` }); process.exit(1); }
      const r = await transport.sendToOwner({ channel, threadTs: null, text });
      out({ ...r, goalId, channel });
      process.exit(r.delivered ? 0 : 1);
      break;
    }
    case 'retire': {
      const goalId = positional[1];
      if (!goalId) { out({ ok: false, error: 'usage: retire <goal-id>' }); process.exit(2); }
      await map.recover();
      const res = await map.retire(goalId);
      out(res);
      process.exit(res.ok ? 0 : 1);
      break;
    }
    default:
      out({ ok: false, error: 'usage: whoami | ensure <goal-id> | list | members <channel-id> | post <goal-id> <text…> | retire <goal-id>' });
      process.exit(2);
  }
}

main().catch((err) => { out({ ok: false, error: err.message }); process.exit(1); });
