#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { loadConfig, agentHome, storePath } = require('./config.js');
const { Store, procStart } = require('./store.js');
const { handleEvent } = require('./ingress.js');
const { runOnce } = require('./turn-loop.js');
const { deliverPending } = require('./outbox.js');
const { Slack } = require('./slack.js');
const { Audio } = require('./audio.js');
const cli = require('./cli.js');

const TICK_MS = 30_000;
const SWEEP_MS = 1_000;
const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;

function log(fields) {
  process.stdout.write(`${JSON.stringify({ ts: new Date().toISOString(), ...fields })}\n`);
}

function envFilePath(workspace) {
  const book = path.join(workspace, 'rbtv.json');
  let rel = '.rbtv/config/env/.env';
  if (fs.existsSync(book)) {
    const cfg = JSON.parse(fs.readFileSync(book, 'utf8'));
    if (typeof cfg.env_file === 'string' && cfg.env_file.trim()) rel = cfg.env_file.trim();
  }
  return path.isAbsolute(rel) ? rel : path.join(workspace, rel);
}

function envValue(workspace, name) {
  let text;
  try { text = fs.readFileSync(envFilePath(workspace), 'utf8'); } catch { return null; }
  for (const line of text.split('\n')) {
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

function readBotToken(file) {
  let data;
  try { data = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (error) {
    throw new Error(`cannot read bot token file: ${error.message}`);
  }
  if (typeof data.bot_token !== 'string' || !data.bot_token) throw new Error('bot token file has no bot_token');
  return data.bot_token;
}

function readAppToken(config) {
  const source = config.slack.appTokenSource;
  if (source.includes('/') || source.startsWith('.')) {
    const text = fs.readFileSync(source, 'utf8').trim();
    if (!text) throw new Error('app token file is empty');
    return text.split(/\s+/)[0];
  }
  if (process.env[source]) return process.env[source];
  const fromFile = envValue(config.workspace, source);
  if (fromFile) return fromFile;
  throw new Error(`app token ${source} is unset`);
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
  if (config.defaultLaunch?.harness) names.add(config.defaultLaunch.harness);
  for (const slug of agentSlugs(config.workspace)) {
    const file = path.join(agentHome(config, slug), 'launch.json');
    if (!fs.existsSync(file)) continue;
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (typeof raw.harness === 'string' && raw.harness.trim()) names.add(raw.harness.trim());
  }
  return [...names];
}

function assertHarnesses(config) {
  const pathEnv = process.env.PATH || '';
  const missing = namedHarnesses(config).filter((name) => !resolveHarness(name, pathEnv));
  if (!missing.length) return;
  for (const harness of missing) {
    log({ event: 'error', harness, path: pathEnv, message: `harness not on PATH: ${harness}` });
  }
  const error = new Error(`harness not on PATH: ${missing.join(', ')}`);
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
      return fs.existsSync(path.join(home, 'state.sqlite')) || fs.existsSync(path.join(home, 'launch.json'));
    });
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

  const config = loadConfig(workspace);
  const fake = process.env.IGNITE_DAEMON_FAKE === '1' && !opts.slack;
  let slack = opts.slack || null;
  const audio = opts.audio || (fake ? null : new Audio({ script: config.tools.audio }));
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
    };
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
        await deliverPending(store, depsFor(slug, store));
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

  const onEvent = (event) => handleEvent(event, ctx).then((result) => {
    if (result?.agent) kick(result.agent);
    return result;
  });

  async function tick() {
    if (stopping) return;
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
          env: { ...process.env, IGNITE_AGENT_HOME: '' },
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
        await deliverPending(store, depsFor(slug, store));
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
      slack = new Slack({
        botToken: readBotToken(config.slack.botTokenFile),
        appToken: readAppToken(config),
        workspace: config.workspace,
        toolsWrapper: config.tools.stools,
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

module.exports = { start };
