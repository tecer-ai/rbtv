#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const { loadConfig, agentHome, storePath, slackToken, paymentsConfig } = require('./config.js');
const { agentsFolder, holdsAgentFile, readAgent } = require('../../../../cast/capabilities/tools/cast/lib/agent');
const { procStart } = require('../../../../cast/capabilities/tools/cast/lib/handles');
const { Store } = require('./store.js');
const { handleEvent } = require('./ingress.js');
const { runOnce } = require('./turn-loop.js');
const { deliverPending } = require('./outbox.js');
const { createTicker } = require('./status-ticker.js');
const { Slack } = require('./slack.js');
const { Audio } = require('./audio.js');
const { refreshBoard } = require('./board.js');
const { createChecks } = require('./timer-check.js');
const { runtimeFolder } = require('./memory-write.js');
const cli = require('./cli.js');
const deferred = require('./deferred-deploy.js');
const { Gate } = require('./payments.js');
const { createPaymentPanel } = require('./payment-panel.js');
const { createLegend } = require('./legend.js');
const { createPaymentRunner } = require('./payment-runner.js');
const { startWebhook, loadProvider } = require('./payment-webhook.js');

const TICK_MS = 30_000;
const SWEEP_MS = 1_000;
// How often the live status ticker runs a pass; its frames and budget are its own (status-ticker.js).
const STATUS_MS = 250;
// How long a stop waits for the live status pass in flight before it releases the lock anyway. The
// ticker aborts its call in flight at stop, and every call ends within its CALL_MS (4 s), so the pass
// ends first.
const STATUS_STOP_MS = 5_000;
// How long the service's main thread waits for a payment ledger another process is writing. Its SQLite calls
// block the event loop, so the wait is short and the socket keeps acking. The withdrawal validation does not wait
// on this thread: it has a worker thread and a ledger connection of its own (payment-webhook.js startWebhook).
const PAYMENT_BUSY_MS = 500;
// The live status budget and 429 pause, kept across a restart, beside the lock.
const PACE_FILE = 'live-status-pace.json';
const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;

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

// The ticker's pace in one JSON file, replaced whole so that a stop never leaves half of it.
function filePace(file) {
  return {
    load() {
      try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
    },
    save(state) {
      const temp = `${file}.${process.pid}.tmp`;
      fs.writeFileSync(temp, JSON.stringify(state));
      fs.renameSync(temp, file);
    },
  };
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
    const read = readAgent(agentHome(config, slug));
    if (read.agent) names.add(read.agent.harness.trim());
  }
  return [...names];
}

function assertHarnesses(config) {
  const pathEnv = process.env.PATH || '';
  const missing = namedHarnesses(config).filter((name) => !resolveHarness(name, pathEnv));
  const tool = resolveHarness('ignite', pathEnv);
  if (!missing.length && tool) return;
  for (const harness of missing) {
    log({ event: 'error', harness, path: pathEnv, message: `harness not on PATH: ${harness}` });
  }
  if (!tool) log({ event: 'error', tool: 'ignite', path: pathEnv, message: 'ignite not on PATH' });
  const parts = missing.map((name) => `harness not on PATH: ${name}`);
  if (!tool) parts.push('ignite not on PATH');
  const error = new Error(parts.join('; '));
  error.exitCode = 1;
  throw error;
}

// Every agent folder, including one cast would not launch: a broken folder is named at start
// (logUnlaunchable) and at each turn it receives, never dropped.
function agentSlugs(workspace) {
  const dir = agentsFolder(workspace);
  let names;
  try { names = fs.readdirSync(dir, { withFileTypes: true }); } catch { return []; }
  return names
    .filter((ent) => ent.isDirectory() && SLUG.test(ent.name))
    .map((ent) => ent.name)
    .filter((name) => holdsAgentFile(path.join(dir, name)));
}

function logUnlaunchable(config) {
  for (const slug of agentSlugs(config.workspace)) {
    const read = readAgent(agentHome(config, slug));
    if (read.problem) log({ event: 'error', slug, message: read.why });
  }
}

async function deliverOutbox(store, deps) {
  return deliverPending(store, deps);
}

function parseArgs(argv) {
  let workspace = null;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--installation') {
      workspace = argv[i + 1];
      if (!workspace || workspace.startsWith('--')) throw new Error('--installation requires a path');
      i += 1;
    } else if (arg === '--help' || arg === '-h') {
      process.stdout.write('usage: daemon.js --installation <path>\n');
      process.exit(0);
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  if (!workspace) throw new Error('--installation required');
  return { workspace: path.resolve(workspace) };
}

async function start(opts = {}) {
  if (!opts.workspace) throw new Error('--installation required');
  const workspace = path.resolve(opts.workspace);
  const lockPath = opts.lockPath || path.join(runtimeFolder(workspace), 'daemon.lock');
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
  // Settled once a stop has closed every agent's database: at once when no turn is running,
  // otherwise when the last running turn ends.
  let drained;
  const closed = new Promise((resolve) => { drained = resolve; });
  let socket = opts.socket || null;
  const timers = [];
  // Settles once the live status pass in flight at a stop has ended; the lock is released then.
  let statusDone = Promise.resolve();
  let stop = (reason) => {
    log({ event: 'stop', reason, left: [] });
    try { socket?.stop(); } catch (error) { log({ event: 'socket-stop', message: error.message }); }
    releaseLock(held);
  };
  if (opts.signals !== false) {
    process.once('SIGTERM', () => { stop('SIGTERM'); statusDone.then(() => process.exit(0)); });
    process.once('SIGINT', () => { stop('SIGINT'); statusDone.then(() => process.exit(0)); });
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

  function closeStore(slug) {
    const store = stores.get(slug);
    if (!store) return;
    stores.delete(slug);
    try { store.close(); } catch (error) { log({ event: 'store-close', message: error.message }); }
  }

  let config = loadConfig(workspace);
  const fake = process.env.IGNITE_DAEMON_FAKE === '1' && !opts.slack;
  let slack = opts.slack || null;
  const audio = opts.audio || (fake ? null : new Audio({ command: config.tools.audio }));
  if (!socket && fake) socket = { async connect() {}, stop() {} };

  const ctx = {
    config,
    slack,
    log,
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
      turnCommand: opts.turnCommand,
      castEnv: opts.castEnv,
      now: opts.now,
      log(fields) { log({ slug, ...fields }); },
    };
  }

  // The payment gate's service side, on when the config has a payments section: each provider's withdrawal
  // validation adapter (loaded by name from its connector), the owner's panel and buttons, the runner that
  // resolves, posts, sends and reports, and the withdrawal validation listener in its own worker thread. The
  // gate opens first, so a ledger of an earlier release is upgraded before the listener reads it.
  const payments = paymentsConfig(config);
  const adapters = {};
  for (const name of payments?.providers || []) {
    try {
      adapters[name] = loadProvider(name);
    } catch (error) {
      log({ event: 'error', what: 'payment-provider', provider: name, message: error.message });
    }
  }

  // A check tool or a payment provider's tool is given the service's environment without its Slack
  // tokens and the payment webhook tokens.
  function toolEnv() {
    const env = { ...process.env };
    for (const name of ['appTokenEnv', 'botTokenEnv', 'ownerTokenEnv']) delete env[config.slack[name]];
    for (const adapter of Object.values(adapters)) delete env[adapter.tokenEnv];
    return env;
  }

  const checks = createChecks({ log, now: clock, env: toolEnv });

  const gate = payments
    ? new Gate({ workspace, timeZone: payments.timeZone, currency: payments.currency, busyMs: PAYMENT_BUSY_MS })
    : null;
  const panel = createPaymentPanel({
    gate: () => gate,
    slack: () => slack,
    config: () => config,
    log,
    kick: () => { paymentStep(); },
  });
  const legend = createLegend({ slack: () => slack, log });
  // Slack's interactions: the payment panel answers its own at the ACK; /legend needs only the bare ACK.
  const interactions = {
    ack: panel.ack,
    async handle(type, payload) {
      await legend.handle(type, payload);
      await panel.handle(type, payload);
    },
  };
  const runner = gate ? createPaymentRunner({
    gate,
    slack: () => slack,
    store: (slug) => getStore(slug),
    providers: Object.keys(adapters),
    run: opts.paymentRun,
    env: toolEnv,
    cwd: workspace,
    log,
    kick: (slug) => kick(slug),
  }) : null;
  const webhook = gate ? startWebhook({
    workspace,
    timeZone: payments.timeZone,
    currency: payments.currency,
    providers: Object.keys(adapters),
    port: opts.webhookPort ?? payments.webhookPort,
    log,
  }) : null;

  function paymentStep() {
    if (stopping || !runner) return;
    runner.step().catch((error) => log({ event: 'payments', action: 'pass-failed', message: error.message }));
  }

  // Starts the due timer's check and returns at once: the tick never waits for a check tool.
  function startCheck(slug, scheduleId) {
    const store = getStore(slug);
    const schedule = store?.getSchedule(scheduleId);
    if (!schedule?.check_tool) return;
    const run = checks.run({ slug, home: agentHome(config, slug), store, schedule });
    if (!run) {
      log({ event: 'check', slug, schedule: scheduleId, answer: 'still running' });
      return;
    }
    run.then((outcome) => { if (outcome.wake?.inserted) kick(slug); })
      .catch((error) => log({ event: 'check', slug, schedule: scheduleId, message: error.message }));
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
        await deliverOutbox(store, depsFor(slug, store));
      }
    } catch (error) {
      log({ event: 'turn-error', slug, message: error.message });
    } finally {
      inflight.delete(slug);
      if (stopping) {
        statusDone.then(() => {
          closeStore(slug);
          if (inflight.size === 0) drained();
        });
      }
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
    const iso = new Date(clock()).toISOString();
    for (const slug of agentSlugs(workspace)) {
      if (stopping) return;
      const out = [];
      try {
        cli.main([
          '--installation', workspace,
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
        for (const row of body.results || []) if (row.reason === 'check') startCheck(slug, row.id);
      } catch (error) {
        log({ event: 'schedules-due', slug, message: error.message });
      }
      await pump(slug);
    }
    if (!stopping) deployAfterTurn();
  }

  // An agent's ignite deploy --after-turn: started once no turn runs, reported to the conversation
  // that asked, as a wake when its work waits for workers, otherwise as a post.
  function deployAfterTurn() {
    try {
      deferred.step({
        installation: workspace,
        busy: () => inflight.size > 0 || agentSlugs(workspace).some((slug) => getStore(slug)?.liveRun()),
        start(req) {
          if (opts.deployStart) return opts.deployStart(req);
          const ignite = resolveHarness('ignite', process.env.PATH || '');
          if (!ignite) return { ok: false, error: 'ignite not on PATH' };
          const [program, args] = deferred.startCommand(req, workspace, process.env, ignite);
          const result = spawnSync(program, args, { encoding: 'utf8' });
          if (result.error || result.status !== 0) {
            return { ok: false, error: result.error?.message || `${program} exited ${result.status}: ${(result.stderr || '').trim()}` };
          }
          return { ok: true };
        },
        report(req, text) {
          const store = getStore(req.agent);
          if (!store) throw new Error(`agent folder missing: ${req.agent}`);
          const woke = store.wake({ conversationKey: req.conversation, note: text });
          if (!woke.inserted) {
            store.enqueueOutbox({ id: `deploy:${req.commit}:${req.startedAt}`, conversationKey: req.conversation,
              payload: { text, audio: false, files: [] } });
          }
          kick(req.agent);
        },
        now: clock(),
        log,
      });
    } catch (error) {
      log({ event: 'deploy-after-turn', message: error.message });
    }
  }

  // Live status pacing follows Slack's real rate limits, so it reads the real clock, not opts.now.
  const ticker = createTicker({
    stores: () => [...stores.entries()].map(([slug, store]) => ({ slug, store })),
    slack: () => slack,
    log,
    pace: filePace(path.join(path.dirname(held.lockPath), PACE_FILE)),
  });

  // The pass in flight ends first, its call aborted, so no reaction call of this service is live and
  // its record is written before another service can start; a pass that does not end is given up
  // after STATUS_STOP_MS.
  function stopStatus() {
    return Promise.race([ticker.stop(), new Promise((resolve) => setTimeout(resolve, STATUS_STOP_MS).unref())]);
  }

  // The payment pass in flight ends before the ledger closes; the listener stops answering at once.
  let paymentsDone = Promise.resolve();
  let listening = null;
  function stopPayments() {
    paymentsDone = Promise.all([
      webhook ? webhook.close() : null,
      runner ? runner.stop() : null,
    ]).then(() => { try { gate?.close(); } catch (error) { log({ event: 'payments', message: error.message }); } });
    return paymentsDone;
  }

  async function drain() {
    if (stopping) return;
    for (const slug of agentSlugs(workspace)) {
      if (stopping || inflight.has(slug)) continue;
      const store = getStore(slug);
      if (!store) continue;
      try {
        await deliverOutbox(store, depsFor(slug, store));
      } catch (error) {
        log({ event: 'outbox', slug, message: error.message });
      }
    }
  }

  stop = function stop(reason) {
    if (stopping) return closed;
    stopping = true;
    for (const timer of timers) clearInterval(timer);
    checks.stop();
    stopPayments();
    const left = [];
    for (const slug of inflight) {
      const run = stores.get(slug)?.getActiveRun();
      left.push({ slug, runId: run?.id || null, pid: run?.pid || null });
      log({ event: 'turn-left', slug, runId: run?.id || null, pid: run?.pid || null, reason });
    }
    log({ event: 'stop', reason, left });
    try { socket?.stop(); } catch (error) { log({ event: 'socket-stop', message: error.message }); }
    statusDone = Promise.all([stopStatus(), paymentsDone]).then(() => {
      releaseLock(held);
      for (const slug of [...stores.keys()]) {
        if (!inflight.has(slug)) closeStore(slug);
      }
      if (inflight.size === 0) drained();
    });
    return closed;
  }

  try {
    logUnlaunchable(config);
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
    // Live status runs from the start: the first scheduling pass below may run whole turns.
    for (const slug of agentSlugs(workspace)) getStore(slug);
    timers.push(setInterval(() => { if (!stopping) ticker.step(); }, opts.statusMs ?? STATUS_MS));
    if (gate) {
      const interrupted = gate.interrupted();
      if (interrupted.length) log({ event: 'payments', action: 'interrupted', ids: interrupted });
      try {
        const port = await webhook.listen();
        listening = port;
        log({ event: 'payment-webhook', action: 'listening', host: '127.0.0.1', port });
      } catch (error) {
        log({ event: 'error', what: 'payment-webhook', message: `the withdrawal validation cannot listen: ${error.message}` });
      }
      timers.push(setInterval(paymentStep, opts.paymentMs ?? SWEEP_MS));
    }
    if (socket) await socket.connect(onEvent, interactions);
    await tick();
    timers.push(setInterval(() => { tick().catch((error) => log({ event: 'tick', message: error.message })); }, opts.tickMs ?? TICK_MS));
    timers.push(setInterval(() => {
      if (stopping) return;
      for (const slug of agentSlugs(workspace)) kick(slug);
    }, opts.sweepMs ?? SWEEP_MS));
    timers.push(setInterval(() => { drain().catch((error) => log({ event: 'outbox', message: error.message })); }, opts.drainMs ?? SWEEP_MS));
    log({ event: 'ready', pid: process.pid, installation: workspace });
    return { stop, config, onEvent, webhookPort: listening };
  } catch (error) {
    for (const timer of timers) clearInterval(timer);
    await Promise.all([stopStatus(), stopPayments()]);
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

module.exports = { start, acquireLock, releaseLock };
