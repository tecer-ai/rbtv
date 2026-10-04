#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { loadConfig, agentHome, storePath, slackToken } = require('./config.js');
const { Store, procStart } = require('./store.js');
const { handleEvent } = require('./ingress.js');
const { runOnce } = require('./turn-loop.js');
const { deliverPending } = require('./outbox.js');
const { Slack } = require('./slack.js');
const { Audio } = require('./audio.js');
const { refreshBoard } = require('./board.js');
const { runDreamer, getState, saveState } = require('./dreamer.js');
const { checkMemory } = require('./memory.js');
const { acquireMemoryLock } = require('./memory-write.js');
const cli = require('./cli.js');

const TICK_MS = 30_000;
const SWEEP_MS = 1_000;
const DREAMER_HOUR = '03';
const DREAMER_TIME_ZONE = 'America/Sao_Paulo';
const DREAMER_WATCHDOG_MS = 48 * 60 * 60_000;
const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const dreamerClock = new Intl.DateTimeFormat('en-CA', {
  timeZone: DREAMER_TIME_ZONE,
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23',
});

function log(fields) {
  process.stdout.write(`${JSON.stringify({ ts: new Date().toISOString(), ...fields })}\n`);
}

function holderOf(lockPath) {
  try { return JSON.parse(fs.readFileSync(lockPath, 'utf8')); } catch { return null; }
}

function holderAlive(holder) {
  if (!holder?.pid) return false;
  try { process.kill(holder.pid, 0); } catch { return false; }
  if (!holder.start) return true;
  const start = procStart(holder.pid);
  return start == null || String(start) === String(holder.start);
}

function acquireLock(lockPath) {
  fs.mkdirSync(path.dirname(lockPath), { recursive: true });
  const body = JSON.stringify({ pid: process.pid, start: procStart(process.pid) });
  for (let attempt = 0; attempt < 2; attempt++) {
    let fd;
    try {
      fd = fs.openSync(lockPath, 'wx');
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      const holder = holderOf(lockPath);
      if (attempt === 0 && holder?.pid && !holderAlive(holder)) {
        try { fs.unlinkSync(lockPath); continue; } catch { /* raced */ }
      }
      const who = holder?.pid ? ` (pid ${holder.pid})` : '';
      const refused = new Error(`daemon already running${who}: ${lockPath}`);
      refused.exitCode = 1;
      throw refused;
    }
    fs.writeFileSync(fd, body);
    fs.fsyncSync(fd);
    fs.closeSync(fd);
    return { lockPath, body };
  }
  const refused = new Error(`daemon already running: ${lockPath}`);
  refused.exitCode = 1;
  throw refused;
}

function releaseLock(held) {
  if (!held) return;
  let current;
  try { current = fs.readFileSync(held.lockPath, 'utf8'); } catch { return; }
  if (current !== held.body) return;
  try { fs.unlinkSync(held.lockPath); } catch { /* already gone */ }
}

function isExecutableFile(file) {
  try {
    if (!fs.statSync(file).isFile()) return false;
    fs.accessSync(file, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function resolveHarness(name, pathEnv) {
  if (!name || name.includes('/') || name.includes('\\')) {
    return path.isAbsolute(name) && isExecutableFile(name) ? name : null;
  }
  for (const dir of String(pathEnv || '').split(path.delimiter)) {
    if (!dir) continue;
    const candidate = path.join(dir, name);
    if (isExecutableFile(candidate)) return candidate;
  }
  return null;
}

function namedHarnesses(config) {
  const names = new Set();
  for (const slug of agentSlugs(config.workspace)) {
    const file = path.join(agentHome(config, slug), 'agent.json');
    if (!fs.existsSync(file)) continue;
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (typeof raw.harness === 'string' && raw.harness.trim()) names.add(raw.harness.trim());
  }
  return [...names];
}

function assertHarnesses(config) {
  const pathEnv = process.env.PATH || '';
  const missing = namedHarnesses(config).filter((name) => !resolveHarness(name, pathEnv));
  const tool = resolveHarness('ignite-agent', pathEnv);
  if (!missing.length && tool) return;
  for (const harness of missing) {
    log({ event: 'error', harness, path: pathEnv, message: `harness not on PATH: ${harness}` });
  }
  if (!tool) log({ event: 'error', tool: 'ignite-agent', path: pathEnv, message: 'ignite-agent not on PATH' });
  const parts = missing.map((name) => `harness not on PATH: ${name}`);
  if (!tool) parts.push('ignite-agent not on PATH');
  const error = new Error(parts.join('; '));
  error.exitCode = 1;
  throw error;
}

function agentSlugs(workspace) {
  const dir = path.join(workspace, '.rbtv', 'agents');
  let names;
  try { names = fs.readdirSync(dir, { withFileTypes: true }); } catch { return []; }
  return names
    .filter((ent) => ent.isDirectory() && SLUG.test(ent.name))
    .map((ent) => ent.name)
    .filter((name) => {
      const home = path.join(dir, name);
      return fs.existsSync(path.join(home, 'agent.md')) && fs.existsSync(path.join(home, 'agent.json'));
    });
}

function dreamerSlugs(config) {
  return [...new Set([config.dmAgent, ...Object.values(config.routes || {})].filter(Boolean))].sort();
}

function dreamerSlot(now) {
  const parts = Object.fromEntries(dreamerClock.formatToParts(new Date(now))
    .filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]));
  return parts.hour === DREAMER_HOUR ? `${parts.year}-${parts.month}-${parts.day}` : null;
}

function expiredUntilDate(workspace, slugs, now) {
  const parts = Object.fromEntries(dreamerClock.formatToParts(new Date(now))
    .filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]));
  const today = `${parts.year}-${parts.month}-${parts.day}`;
  const roots = [path.join(workspace, '.rbtv', 'memory')];
  for (const slug of slugs) {
    const home = path.join(workspace, '.rbtv', 'agents', slug);
    roots.push(path.join(home, 'memory'), path.join(home, '_artifacts', 'board.md'));
  }
  const expired = (file) => fs.readFileSync(file, 'utf8').split(/\r?\n/).some((line) => {
    const text = line.trimEnd();
    const body = text.match(/^(.*) \(\d{4}-\d{2}-\d{2} · .+\)$/)?.[1] ?? text;
    const until = body.match(/\buntil (\d{4}-\d{2}-\d{2})\.?$/)?.[1];
    return until && Number.isFinite(Date.parse(`${until}T00:00:00Z`)) &&
      new Date(`${until}T00:00:00Z`).toISOString().slice(0, 10) === until && until < today;
  });
  const visit = (file) => {
    let stat;
    try { stat = fs.lstatSync(file); } catch (error) { if (error.code === 'ENOENT') return false; throw error; }
    if (stat.isSymbolicLink()) return false;
    if (stat.isFile()) return path.extname(file) === '.md' && expired(file);
    if (!stat.isDirectory()) return false;
    for (const entry of fs.readdirSync(file, { withFileTypes: true })) {
      if (entry.name === '4-archives' || entry.name === 'archive') continue;
      if (visit(path.join(file, entry.name))) return true;
    }
    return false;
  };
  return roots.some(visit);
}

function dreamerStores(config, openStore, owned) {
  if (openStore) return openStore;
  return (slug) => {
    const home = agentHome(config, slug);
    if (!fs.existsSync(home)) return null;
    const store = new Store(storePath(config, slug));
    owned.push(store);
    return store;
  };
}

function hasNewOwnerMessage(config, openStore) {
  for (const slug of dreamerSlugs(config)) {
    const store = openStore(slug);
    if (!store) return true;
    try {
      const state = getState(store);
      const rows = store.db.prepare("SELECT rowid, metadata FROM messages WHERE role='owner' AND rowid>? ORDER BY rowid").all(state.cursor);
      if (rows.some((row) => {
        const source = JSON.parse(row.metadata).source;
        return !source || source === 'slack' || source === 'used-text';
      })) return true;
    } catch {
      return true;
    }
  }
  return false;
}

function hasInboxWork(workspace) {
  const text = fs.readFileSync(path.join(workspace, '.rbtv', 'memory', 'inbox.md'), 'utf8');
  checkMemory('inbox', text);
  return text.split(/\r?\n/).some((line) => line.startsWith('- '));
}

async function deliverOutbox(store, deps, now) {
  const delivered = await deliverPending(store, deps);
  for (const row of delivered) {
    if (!row.delivered || !/^(?:post:)?dreamer:/.test(row.id)) continue;
    store.db.prepare(`INSERT INTO settings(key,value,updated_at) VALUES ('dreamer_digest',?,?)
      ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at`)
      .run(JSON.stringify({ conversationKey: row.conversationKey }), now);
  }
  return delivered;
}

async function enqueueDreamerNotice({ config, openStore, text, now, slack, depsFor }) {
  const slug = config.dmAgent;
  if (!slug) throw new Error('dreamer requires config.dmAgent for owner alerts');
  const store = openStore(slug);
  if (!store) throw new Error(`dreamer direct-message agent missing: ${slug}`);
  let conversationKey = null;
  try {
    const saved = JSON.parse(store.db.prepare("SELECT value FROM settings WHERE key='dreamer_digest'").get()?.value || 'null');
    if (typeof saved?.conversationKey === 'string' && store.getConversation(saved.conversationKey)) {
      conversationKey = saved.conversationKey;
    }
  } catch { /* Start a new owner digest thread if its saved state is malformed. */ }
  const id = `dreamer:${Date.now()}:${Math.random().toString(36).slice(2)}`;
  let outboxId;
  if (conversationKey) {
    outboxId = id;
    store.enqueueOutbox({ id: outboxId, conversationKey, payload: { text, audio: false, files: [] } });
  } else {
    const started = store.beginProactive({
      id,
      agent: slug,
      workspace: config.slack.team,
      channel: config.slack.ownerUserId,
      payload: { text, audio: false, files: [], imUser: config.slack.ownerUserId },
    });
    outboxId = started.outboxId;
  }
  if (!slack) return { queued: true, delivered: false, outboxId };
  const delivered = await deliverOutbox(store, depsFor(slug, store), now);
  const sent = delivered.find((row) => row.id === outboxId && row.delivered);
  return { queued: true, delivered: Boolean(sent), outboxId };
}

function busyDreamer(error) {
  return {
    ok: false, busy: true, quiet: false, changed: false, alert: null,
    digestQueued: false, noticeQueued: false, delivered: false, conflictsSaved: false, error,
  };
}

async function runInstalledDreamer(opts = {}) {
  const config = opts.config;
  if (!config?.workspace) throw new Error('workspace required');
  const workspace = fs.realpathSync(config.workspace);
  let release;
  try {
    release = acquireMemoryLock(workspace);
  } catch (error) {
    if (/lock busy/.test(error.message)) return busyDreamer(error.message);
    throw error;
  }
  const owned = [];
  const openStore = dreamerStores(config, opts.openStore, owned);
  const log = opts.log || (() => {});
  const now = typeof opts.now === 'function' ? opts.now() : (opts.now ?? Date.now());
  const stamp = opts.stamp || (() => now);
  let released = false;
  const unlock = () => {
    if (released) return;
    released = true;
    release();
  };
  try {
    let needed;
    try {
      // Folding also needs unread owner thread evidence; a watch-out alone is
      // deferred, while every explicit remember line is work in its own right.
      needed = hasNewOwnerMessage(config, openStore) || hasInboxWork(config.workspace) ||
        expiredUntilDate(config.workspace, dreamerSlugs(config), now);
    } catch (error) {
      needed = true;
      log({ event: 'dreamer-check', message: error.message });
    }
    let result;
    try {
      if (needed) {
        // Consolidation locks its snapshot and publication separately; models
        // must leave the shared lock available to remember and board refreshes.
        unlock();
        result = await (opts.runDreamer || runDreamer)({ config, openStore, now });
      } else {
        for (const slug of dreamerSlugs(config)) {
          const store = openStore(slug);
          saveState(store, { ...getState(store), lastSuccessAt: now }, now);
        }
        result = { ok: true, changed: false, digest: null, alert: null };
      }
    } catch {
      result = { ok: false, alert: 'Dreamer failed.' };
    }
    log({ event: 'dreamer', ok: Boolean(result?.ok), changed: Boolean(result?.changed), alert: Boolean(result?.alert),
      ...(result?.alert ? { message: result.alert } : {}) });
    unlock();
    let digestQueued = false;
    let noticeQueued = false;
    let delivered = false;
    let conflictsSaved = false;
    let notificationError = null;
    try {
      if (!result?.ok || result.alert) {
        const sent = await enqueueDreamerNotice({
          config, openStore, text: `Memory alert: ${result?.alert || 'Dreamer failed.'}`,
          now: stamp(), slack: opts.slack, depsFor: opts.depsFor,
        });
        noticeQueued = Boolean(sent.queued);
        delivered = Boolean(sent.delivered);
      } else if (result.digest?.text) {
        const sent = await enqueueDreamerNotice({
          config, openStore, text: result.digest.text, now: stamp(), slack: opts.slack, depsFor: opts.depsFor,
        });
        digestQueued = Boolean(sent.queued);
        delivered = Boolean(sent.delivered);
        if (delivered && result.digest.conflicts?.length) {
          for (const slug of dreamerSlugs(config)) {
            const store = openStore(slug);
            const state = getState(store);
            saveState(store, { ...state,
              reportedConflicts: [...new Set([...(state.reportedConflicts || []), ...result.digest.conflicts])] }, now);
          }
          conflictsSaved = true;
        }
      }
    } catch (error) {
      notificationError = error.message;
      log({ event: 'dreamer-alert', message: error.message });
    }
    return {
      ok: Boolean(result?.ok && !notificationError), busy: false,
      quiet: Boolean(!needed && result?.ok && !result.alert),
      changed: Boolean(result?.changed), alert: result?.alert || null,
      digestQueued, noticeQueued, delivered, conflictsSaved, error: notificationError,
    };
  } finally {
    unlock();
    for (const store of owned) {
      try { store.close(); } catch { /* caller-owned */ }
    }
  }
}

function parseArgs(argv) {
  let workspace = null;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--workspace') {
      workspace = argv[i + 1];
      if (!workspace || workspace.startsWith('--')) throw new Error('--workspace requires a path');
      i += 1;
    } else if (arg === '--help' || arg === '-h') {
      process.stdout.write('usage: daemon.js --workspace <path>\n');
      process.exit(0);
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  if (!workspace) throw new Error('--workspace required');
  return { workspace: path.resolve(workspace) };
}

async function start(opts = {}) {
  if (!opts.workspace) throw new Error('--workspace required');
  const workspace = path.resolve(opts.workspace);
  const lockPath = opts.lockPath || path.join(workspace, '.rbtv', 'agents', '.daemon.lock');
  const held = acquireLock(lockPath);
  try {
    return await startLocked(opts, workspace, held);
  } catch (error) {
    releaseLock(held);
    throw error;
  }
}

async function startLocked(opts, workspace, held) {
  const stores = new Map();
  const inflight = new Set();
  let stopping = false;
  let dreamerNight = null;
  let watchdogAlertAt = null;
  let socket = opts.socket || null;
  const timers = [];
  let stop = (reason) => {
    log({ event: 'stop', reason, left: [] });
    try { socket?.stop(); } catch (error) { log({ event: 'socket-stop', message: error.message }); }
    releaseLock(held);
  };
  if (opts.signals !== false) {
    process.once('SIGTERM', () => { stop('SIGTERM'); process.exit(0); });
    process.once('SIGINT', () => { stop('SIGINT'); process.exit(0); });
  }

  function clock() {
    return opts.now ? opts.now() : Date.now();
  }

  function getStore(slug) {
    if (stores.has(slug)) return stores.get(slug);
    const home = agentHome(config, slug);
    if (!fs.existsSync(home)) return null;
    const store = new Store(storePath(config, slug));
    stores.set(slug, store);
    return store;
  }

  let config = loadConfig(workspace);
  const fake = process.env.IGNITE_DAEMON_FAKE === '1' && !opts.slack;
  let slack = opts.slack || null;
  const audio = opts.audio || (fake ? null : new Audio({ command: config.tools.audio }));
  if (!socket && fake) socket = { async connect() {}, stop() {} };

  const ctx = {
    config,
    slack,
    openStore(slug) {
      const home = agentHome(config, slug);
      if (!fs.existsSync(home)) throw new Error(`agent home missing: ${slug}`);
      const store = getStore(slug);
      if (!store) throw new Error(`agent home missing: ${slug}`);
      return store;
    },
  };

  function depsFor(slug, store) {
    return {
      home: agentHome(config, slug),
      store,
      slack,
      audio,
      castCmd: opts.castCmd || config.tools.cast,
      castEnv: opts.castEnv,
      now: opts.now,
      log(fields) { log({ slug, ...fields }); },
    };
  }

  async function notifyDreamer(text) {
    return enqueueDreamerNotice({
      config, openStore: getStore, text, now: clock(), slack,
      depsFor: (slug, store) => depsFor(slug, store),
    });
  }

  function syncDreamerEnabled() {
    for (const slug of dreamerSlugs(config)) {
      const store = getStore(slug);
      if (!store) continue;
      const row = store.db.prepare("SELECT value FROM settings WHERE key='dreamer_enabled_at'").get();
      const since = row ? JSON.parse(row.value) : null;
      const next = config.dreamer.enabled ? (since ?? clock()) : null;
      if (next !== since) store.db.prepare(`INSERT INTO settings(key,value,updated_at) VALUES ('dreamer_enabled_at',?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at`)
        .run(JSON.stringify(next), clock());
    }
  }

  function dreamerWatchdogSince() {
    let last = Infinity;
    for (const slug of dreamerSlugs(config)) {
      const store = getStore(slug);
      if (!store) return null;
      try {
        const enabledAt = JSON.parse(store.db.prepare("SELECT value FROM settings WHERE key='dreamer_enabled_at'").get()?.value || 'null');
        if (!Number.isFinite(enabledAt)) return null;
        last = Math.min(last, Math.max(enabledAt, getState(store).lastSuccessAt ?? enabledAt));
      } catch {
        return null;
      }
    }
    return last === Infinity ? null : last;
  }

  async function runNightDreamer() {
    const now = clock();
    const slot = dreamerSlot(now);
    if (!slot || dreamerNight === slot) return;
    dreamerNight = slot;
    const result = await module.exports.runInstalledDreamer({
      config, openStore: getStore, now, runDreamer: opts.runDreamer, slack, log, stamp: clock,
      depsFor: (slug, store) => depsFor(slug, store),
    });
    if (result.busy) dreamerNight = null;
  }

  async function watchdogDreamer() {
    const now = clock();
    const last = dreamerWatchdogSince();
    if (last == null || now - last <= DREAMER_WATCHDOG_MS) return;
    if (watchdogAlertAt != null && now - watchdogAlertAt < DREAMER_WATCHDOG_MS) return;
    watchdogAlertAt = now;
    try {
      const sent = await notifyDreamer('Memory alert: Dreamer has not completed a successful run in 48 hours.');
      log({ event: 'dreamer-watchdog', lastSuccessAt: last,
        digestQueued: false, noticeQueued: Boolean(sent.queued), delivered: Boolean(sent.delivered) });
    } catch (error) {
      log({ event: 'dreamer-alert', message: error.message });
    }
  }

  async function pump(slug) {
    if (stopping || inflight.has(slug)) return;
    const store = getStore(slug);
    if (!store) return;
    inflight.add(slug);
    try {
      for (;;) {
        if (stopping) break;
        const result = await runOnce(slug, depsFor(slug, store));
        if (!result?.claimed) break;
        log({
          event: 'turn',
          slug,
          runId: result.runId || null,
          disposition: result.disposition || null,
          failed: Boolean(result.failed),
        });
        await deliverOutbox(store, depsFor(slug, store), clock());
      }
    } catch (error) {
      log({ event: 'turn-error', slug, message: error.message });
    } finally {
      inflight.delete(slug);
    }
  }

  function kick(slug) {
    if (!stopping) pump(slug).catch((error) => log({ event: 'turn-error', slug, message: error.message }));
  }

  function refreshConfig() {
    try {
      const next = loadConfig(workspace);
      config = next;
      ctx.config = next;
    } catch (error) {
      log({ event: 'config', message: error.message });
    }
  }

  const onEvent = (event) => {
    refreshConfig();
    return handleEvent(event, ctx).then((result) => {
      if (result?.ignored) {
        log({
          event: 'ignored',
          reason: result.ignored,
          channel: event?.channel || null,
          channelType: event?.channelType || null,
        });
      }
      if (result?.agent) {
        try {
          refreshBoard(agentHome(config, result.agent), getStore(result.agent), clock());
        } catch (error) {
          log({ event: 'board', slug: result.agent, message: error.message });
        }
        kick(result.agent);
      }
      return result;
    });
  };

  async function tick() {
    if (stopping) return;
    refreshConfig();
    syncDreamerEnabled();
    if (config.dreamer.enabled) {
      await runNightDreamer();
      await watchdogDreamer();
    } else {
      dreamerNight = null;
      watchdogAlertAt = null;
    }
    const iso = new Date(clock()).toISOString();
    for (const slug of agentSlugs(workspace)) {
      if (stopping) return;
      const out = [];
      try {
        cli.main([
          '--workspace', workspace,
          '--agent', slug,
          '--json',
          'schedules-due',
          '--now', iso,
        ], {
          stdout: (text) => out.push(text),
          env: { ...process.env, RBTV_AGENT_HOME: '' },
        });
        const body = JSON.parse(out.join('') || '{}');
        if (body.results?.length) log({ event: 'schedules-due', slug, results: body.results });
      } catch (error) {
        log({ event: 'schedules-due', slug, message: error.message });
      }
      await pump(slug);
    }
  }

  async function drain() {
    if (stopping) return;
    for (const slug of agentSlugs(workspace)) {
      if (stopping || inflight.has(slug)) continue;
      const store = getStore(slug);
      if (!store) continue;
      try {
        await deliverOutbox(store, depsFor(slug, store), clock());
      } catch (error) {
        log({ event: 'outbox', slug, message: error.message });
      }
    }
  }

  stop = function stop(reason) {
    if (stopping) return;
    stopping = true;
    for (const timer of timers) clearInterval(timer);
    const left = [];
    for (const slug of inflight) {
      const run = stores.get(slug)?.getActiveRun();
      left.push({ slug, runId: run?.id || null, pid: run?.pid || null });
      log({ event: 'turn-left', slug, runId: run?.id || null, pid: run?.pid || null, reason });
    }
    log({ event: 'stop', reason, left });
    try { socket?.stop(); } catch (error) { log({ event: 'socket-stop', message: error.message }); }
    releaseLock(held);
    if (inflight.size === 0) {
      for (const store of stores.values()) {
        try { store.close(); } catch (error) { log({ event: 'store-close', message: error.message }); }
      }
      stores.clear();
    }
  }

  try {
    assertHarnesses(config);
    if (!slack && !fake) {
      const appToken = slackToken(config, 'app');
      const botToken = slackToken(config, 'bot');
      slack = new Slack({
        botToken,
        appToken,
        stoolsWorkspace: config.slack.stoolsWorkspace,
        stools: config.tools.stools,
        log: (level, message) => log({ event: 'slack', level, message }),
      });
      await slack.auth();
      ctx.slack = slack;
      socket = slack;
    }
    if (socket) await socket.connect(onEvent);
    await tick();
    timers.push(setInterval(() => { tick().catch((error) => log({ event: 'tick', message: error.message })); }, opts.tickMs ?? TICK_MS));
    timers.push(setInterval(() => {
      if (stopping) return;
      for (const slug of agentSlugs(workspace)) kick(slug);
    }, opts.sweepMs ?? SWEEP_MS));
    timers.push(setInterval(() => { drain().catch((error) => log({ event: 'outbox', message: error.message })); }, opts.drainMs ?? SWEEP_MS));
    log({ event: 'ready', pid: process.pid, workspace });
    return { stop, config, onEvent };
  } catch (error) {
    releaseLock(held);
    throw error;
  }
}

if (require.main === module) {
  start(parseArgs(process.argv.slice(2))).catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exit(error.exitCode || 1);
  });
}

module.exports = { start, expiredUntilDate, runInstalledDreamer };
