'use strict';

// probe-reserved-interactive-slot — D25 Fix B. Cap is 14 + 1 reserved interactive slot
// for chat-bridge owner summons. This fixture uses cap=2 (the gate reads
// cfg.max_live_agent_sessions; spawning 14 sleep processes would not test a different
// branch). Production default of 14 is asserted separately against DEFAULT_CONFIG.

const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture } = require('./lib');

const TICKER_PATH = path.join(__dirname, '..', 'ticker.js');

function registerChatAgentJob(ctx) {
  const existing = ctx.store.getJob('chat-agent-v3');
  if (existing) return existing;
  return ctx.store.registerJob({
    jobId: 'chat-agent-v3',
    actionType: 'launch-agent',
    function: 'launch-agent',
    argsSchema: JSON.stringify({
      required: {},
      optional: { prompt: 'string', workdir: 'string' },
    }),
  });
}

function fillCap(ctx, now, n) {
  registerLaunchAgentJob(ctx);
  for (let i = 0; i < n; i++) enqueueLaunchAgent(ctx, { runAt: now });
}

async function scenarioReservedAdmit(lines) {
  const ctx = setup({ max_live_agent_sessions: 2 });
  try {
    const now = new Date();
    fillCap(ctx, now, 2);
    registerChatAgentJob(ctx);
    enqueueLaunchAgent(ctx, {
      jobId: 'chat-agent-v3',
      runAt: now,
      enqueuedBy: 'chat-bridge-slack',
    });
    lines.push('cap=2 filled with 2 non-interactive + 1 chat-bridge chat-agent-v3');
    const r = await ctx.ticker.tick(now);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);
    const admits = r.actions.filter((a) => a.reason === 'reserved-interactive-slot');
    const dump = ctx.store.dump();
    if (admits.length !== 1) {
      throw new Error(`expected 1 reserved-interactive-slot admit, got ${JSON.stringify(admits)}`);
    }
    if (dump.jobs_log.length !== 3) {
      throw new Error(`expected 3 launches (2 cap + 1 reserved), got ${dump.jobs_log.length}`);
    }
    lines.push('PASS cap-full + interactive → fires via reserved slot');
    for (const exec of dump.jobs_log) {
      try { await ctx.mgr.kill(exec.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

async function scenarioSecondInteractiveDefers(lines) {
  const ctx = setup({ max_live_agent_sessions: 2 });
  try {
    const now = new Date();
    fillCap(ctx, now, 2);
    registerChatAgentJob(ctx);
    enqueueLaunchAgent(ctx, {
      jobId: 'chat-agent-v3',
      runAt: now,
      enqueuedBy: 'chat-bridge-slack',
    });
    let r = await ctx.ticker.tick(now);
    lines.push(`first tick (admit reserved): ${JSON.stringify(r.actions.filter((a) => a.phase === 'dispatch'))}`);
    enqueueLaunchAgent(ctx, {
      jobId: 'chat-agent-v3',
      runAt: new Date(),
      enqueuedBy: 'chat-bridge-slack',
    });
    r = await ctx.ticker.tick(new Date());
    lines.push(`second tick (2nd interactive): ${JSON.stringify(r.actions.filter((a) => a.phase === 'dispatch'))}`);
    const deferrals = r.actions.filter((a) => a.phase === 'dispatch' && a.action === 'defer' && a.reason === 'global-cap');
    if (deferrals.length < 1) {
      throw new Error(`expected 2nd interactive to defer global-cap, got ${JSON.stringify(r.actions)}`);
    }
    const reserved = r.actions.filter((a) => a.reason === 'reserved-interactive-slot');
    if (reserved.length !== 0) {
      throw new Error(`2nd interactive must not take another reserved slot, got ${JSON.stringify(reserved)}`);
    }
    lines.push('PASS cap-full + 2nd interactive live → defers global-cap');
    for (const exec of ctx.store.dump().jobs_log) {
      try { await ctx.mgr.kill(exec.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

async function scenarioNonInteractiveNeverReserved(lines) {
  const ctx = setup({ max_live_agent_sessions: 2 });
  try {
    const now = new Date();
    fillCap(ctx, now, 3);
    const r = await ctx.ticker.tick(now);
    lines.push(`non-interactive overflow tick: ${JSON.stringify(r.actions.filter((a) => a.phase === 'dispatch'))}`);
    const reserved = r.actions.filter((a) => a.reason === 'reserved-interactive-slot');
    if (reserved.length !== 0) {
      throw new Error(`non-interactive must never use reserved slot, got ${JSON.stringify(reserved)}`);
    }
    const deferrals = r.actions.filter((a) => a.reason === 'global-cap');
    if (deferrals.length !== 1) {
      throw new Error(`expected 1 global-cap deferral, got ${JSON.stringify(r.actions)}`);
    }
    if (ctx.store.dump().jobs_log.length !== 2) {
      throw new Error(`expected 2 launches (cap only), got ${ctx.store.dump().jobs_log.length}`);
    }
    lines.push('PASS non-interactive never uses slot 15');
    for (const exec of ctx.store.dump().jobs_log) {
      try { await ctx.mgr.kill(exec.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

async function scenarioDefaultIs14(lines) {
  const src = fs.readFileSync(TICKER_PATH, 'utf8');
  const m = src.match(/max_live_agent_sessions:\s*(\d+)/);
  if (!m || Number(m[1]) !== 14) {
    throw new Error(`DEFAULT_CONFIG.max_live_agent_sessions must be 14, found ${m && m[1]}`);
  }
  lines.push('PASS production default max_live_agent_sessions is 14');
}

async function scenarioRedByMutation(lines) {
  const src = fs.readFileSync(TICKER_PATH, 'utf8');
  const ANCHOR = 'if (interactive && liveAgentSessions < reservedCeiling)';
  if (!src.includes(ANCHOR)) {
    throw new Error('reserved-slot mutation anchor missing — red arm is not measuring the real gate');
  }
  const mut = new Module(TICKER_PATH, null);
  mut.filename = TICKER_PATH;
  mut.paths = Module._nodeModulePaths(path.dirname(TICKER_PATH));
  mut._compile(src.replace(ANCHOR, 'if (false && interactive && liveAgentSessions < reservedCeiling)'), TICKER_PATH);

  const ctx = setup({ max_live_agent_sessions: 2 });
  try {
    const now = new Date();
    fillCap(ctx, now, 2);
    registerChatAgentJob(ctx);
    enqueueLaunchAgent(ctx, {
      jobId: 'chat-agent-v3',
      runAt: now,
      enqueuedBy: 'chat-bridge-slack',
    });
    // Swap the fixture ticker for the mutated one.
    const { createTicker } = mut.exports;
    const broken = createTicker({
      heartStore: ctx.store,
      spawnManager: ctx.mgr,
      config: { tick_interval_ms: 10000, max_live_agent_sessions: 2, slot_max_repeats: 10 },
      feedPath: ctx.feedPath,
      logPath: ctx.logPath,
    });
    const r = await broken.tick(now);
    lines.push(`mutated tick: ${JSON.stringify(r.actions.filter((a) => a.phase === 'dispatch'))}`);
    const admits = r.actions.filter((a) => a.reason === 'reserved-interactive-slot');
    const deferrals = r.actions.filter((a) => a.reason === 'global-cap');
    if (admits.length !== 0 || deferrals.length < 1) {
      throw new Error(`mutated gate must defer the interactive row, got ${JSON.stringify(r.actions)}`);
    }
    lines.push('PASS red arm — without the reserved slot, cap-full + interactive DEFERS');
    for (const exec of ctx.store.dump().jobs_log) {
      try { await ctx.mgr.kill(exec.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

async function run(lines) {
  await scenarioDefaultIs14(lines);
  await scenarioReservedAdmit(lines);
  await scenarioSecondInteractiveDefers(lines);
  await scenarioNonInteractiveNeverReserved(lines);
  await scenarioRedByMutation(lines);
}

capture('probe-reserved-interactive-slot', run);
