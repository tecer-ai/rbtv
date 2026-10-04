'use strict';

const { conversationKey } = require('./store.js');

function slackMillis(ts) {
  const n = Number(ts);
  return Number.isFinite(n) ? Math.round(n * 1000) : Date.now();
}

function asMessage(raw, ownerUserId, fallback) {
  const team = raw.team || fallback.team;
  const channel = raw.channel || fallback.channel;
  const ts = raw.ts;
  const role = raw.isBotOrSelf ? 'assistant' : (raw.user === ownerUserId ? 'owner' : 'user');
  return {
    id: `${team}:${channel}:${ts}`,
    role,
    text: raw.text || '',
    files: Array.isArray(raw.files) ? raw.files : [],
    team,
    channel,
    ts,
    createdAt: slackMillis(ts),
  };
}

function classify(event, config) {
  if (!event || event.isBotOrSelf) return { ignored: 'bot' };
  const ownerUserId = config?.slack?.ownerUserId;
  if (!ownerUserId) throw new Error('config.slack.ownerUserId required');
  if (!event.user || event.user !== ownerUserId) return { ignored: 'non-owner' };
  const team = event.team || config.slack.team;
  const channel = event.channel;
  const ts = event.ts;
  if (!team || !channel || !ts) return { ignored: 'malformed' };
  const thread = Boolean(event.threadTs && event.threadTs !== ts);
  const rootTs = thread ? event.threadTs : ts;
  const key = conversationKey(team, channel, rootTs);
  const base = {
    agent: null,
    team,
    channel,
    ts,
    rootTs,
    key,
    thread,
    event,
    ownerUserId,
    routed: false,
  };
  if (event.channelType === 'im') {
    if (!config.dmAgent) throw new Error('config.dmAgent required');
    return { ...base, agent: config.dmAgent };
  }
  const agent = config.routes?.[channel];
  if (!agent) return { ignored: 'unconfigured' };
  return { ...base, agent, routed: true };
}

function outcome(route, result) {
  if (result?.duplicate) return { ignored: 'duplicate', agent: route.agent, key: route.key };
  return { queued: true, agent: route.agent, key: route.key, workId: result.workId };
}

function ownerInput(route) {
  const message = asMessage(route.event, route.ownerUserId, route);
  return {
    key: route.key,
    agent: route.agent,
    workspace: route.team,
    channel: route.channel,
    rootTs: route.rootTs,
    activated: true,
    message,
    payload: {
      text: message.text,
      files: message.files,
      ts: route.ts,
      threadTs: route.rootTs,
    },
  };
}

async function saveOwner(store, route) {
  return outcome(route, await store.acceptOwnerInput(ownerInput(route)));
}

async function activateThread(store, slack, route) {
  if (typeof slack?.threadHistory !== 'function') throw new Error('slack.threadHistory required');
  const history = await slack.threadHistory(route.channel, route.rootTs);
  const result = store.transaction(() => {
    store.upsertConversation({
      key: route.key,
      agent: route.agent,
      workspace: route.team,
      channel: route.channel,
      rootTs: route.rootTs,
      activated: false,
    });
    for (const raw of history || []) {
      if (!raw?.ts || raw.ts === route.ts) continue;
      store.recordMessage(route.key, asMessage(raw, route.ownerUserId, route));
    }
    return store.acceptOwnerInput(ownerInput(route));
  });
  return outcome(route, result);
}

async function handleEvent(event, ctx) {
  const route = classify(event, ctx?.config);
  if (route.ignored) return route;
  if (typeof ctx?.openStore !== 'function') throw new Error('openStore required');
  const store = await ctx.openStore(route.agent);
  if (route.thread && route.routed) {
    const existing = await store.conversationByThread({
      workspace: route.team,
      channel: route.channel,
      rootTs: route.rootTs,
    });
    if (existing?.activated) return saveOwner(store, route);
    return activateThread(store, ctx.slack, route);
  }
  return saveOwner(store, route);
}

module.exports = { handleEvent };
