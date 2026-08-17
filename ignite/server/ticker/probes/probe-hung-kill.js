'use strict';

// THE HUNG-KILL RUNG — the rung above `stalled` on the ticker's stall ladder (owner-ruled).
//
// The bar: a turn that is ALREADY `stalled`, whose log has not grown AND whose process has burnt
// no CPU time across the kill window, is HUNG — the ticker kills it, freeing its seat. `stalled`
// itself is unchanged: it still pages, it is still non-terminal, and the owner should still look.
//
// ⚠ THE ARM THAT MAKES THE OTHERS EVIDENCE IS #2. Check 1 alone would pass against a rung that
// killed every stalled turn on sight — a guard that is merely REACHABLE is not a guard that
// DISCRIMINATES. So the identical scenario is replayed with the CPU counter ADVANCING and nothing
// else changed, and it MUST NOT kill. Checks 3 and 4 are the other two ways the rung must hold its
// fire: no CPU signal at all (every setsid exec — owner ruled one frozen signal too weak to kill
// on), and the rung switched off.
//
// The spawn manager is a STUB, deliberately: the rung's inputs are `status().cpuNsec` and the log
// size, and a real worker cannot be made to freeze its CPU on demand. What the stub does NOT fake
// is the store — the turn is fired through the real dispatch path and the terminal write is the
// store's own `endTurnAndCloseSession`, exactly as `spawnManager.kill` performs it.

const path = require('node:path');
const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture } = require('./lib');
const { createTicker } = require('../ticker');
const { seatKeyOf } = require('../../heart/heart-store');

// A spawn manager whose only real act is the terminal store write a kill performs. `cpu` is a
// function of the call so a scenario can freeze or advance the counter.
function stubManager(ctx, { cpu, killCalls }) {
  return {
    config: ctx.mgr.config,
    spawn: async () => {},
    status: async (execId) => {
      const cpuNsec = cpu();
      return { execId, live: true, exitCode: null, cpuNsec, carrierInfo: { carrier: 'systemd', active: true, cpuNsec } };
    },
    kill: async (execId) => {
      killCalls.push(execId);
      // What the real `spawn.js#kill` does after the carrier act: ONE store call ending both
      // levels. Faking anything softer here would let the probe pass on a rung that frees nothing.
      ctx.store.endTurnAndCloseSession(execId, {
        turnStatus: 'killed', sessionStatus: 'killed', endedAt: new Date(),
        reason: 'stub kill (probe-hung-kill)',
      });
    },
  };
}

// Fire one launch-agent row, then tick until the rung fires or `maxTicks` is spent.
// Returns everything the checks read: whether a kill happened, the final row, the notes.
async function scenario({ cpu, tickerConfig, maxTicks = 24 }) {
  const ctx = setup();
  const killCalls = [];
  try {
    registerLaunchAgentJob(ctx);
    const ticker = createTicker({
      heartStore: ctx.store,
      spawnManager: stubManager(ctx, { cpu, killCalls }),
      config: {
        tick_interval_ms: 10000, stall_warn_ticks: 1, stall_halt_ticks: 2,
        max_live_agent_sessions: 2, slot_max_repeats: 10,
        ...tickerConfig,
      },
      feedPath: ctx.feedPath,
      logPath: ctx.logPath,
    });

    const t0 = new Date();
    const queued = enqueueLaunchAgent(ctx, { runAt: t0 });
    const seatKey = seatKeyOf(ctx.store.getJob('launch-agent'), JSON.parse(queued.args));

    const hungActions = [];
    let ticks = 0;
    for (let i = 0; i < maxTicks; i++) {
      const r = await ticker.tick(new Date());
      ticks = r.tick;
      for (const a of r.actions) {
        if (a.phase === 'enforce' && a.action === 'hung-kill') hungActions.push(a);
      }
      // NO early break: every scenario runs the full budget so a rung that fires TWICE — or a
      // stall note that repeats now that stalled rows stay on the ladder — is caught rather than
      // assumed absent.
    }

    const dump = ctx.store.dump();
    const row = dump.jobs_log[0];
    const notes = dump.messages.filter((m) => m.type === 'note' && m.sender === 'ticker');
    return {
      killCalls, hungActions, ticks, seatKey,
      status: row ? row.status : null,
      execId: row ? row.exec_id : null,
      holder: ctx.store.findSeatHolder(seatKey),
      stallNotes: notes.filter((m) => m.corpus.includes('slot stalled after')).length,
      killNotes: notes.filter((m) => m.corpus.includes('hung slot killed')),
    };
  } finally {
    teardown(ctx);
  }
}

async function run(lines) {
  let failures = 0;
  const check = (name, ok, detail) => {
    if (!ok) failures += 1;
    lines.push(`  ${name.padEnd(40)} ${ok ? 'PASS' : 'FAIL'}  ${detail}`);
  };

  // ── 1. FROZEN log + FROZEN cpu → killed exactly once, terminally, seat freed ────────────────
  const frozen = await scenario({ cpu: () => 100, tickerConfig: { stall_kill_ticks: 5 }, maxTicks: 12 });
  check('frozen-cpu-kills-once',
    frozen.killCalls.length === 1 && frozen.hungActions.length === 1,
    `kill() calls=${frozen.killCalls.length} hung-kill actions=${frozen.hungActions.length} at silence=${frozen.hungActions.map(a => a.silenceTicks)}`);
  check('turn-is-terminal',
    frozen.status === 'killed',
    `jobs_log status=${frozen.status} (exec ${frozen.execId})`);
  check('seat-is-freed',
    frozen.holder === null,
    `findSeatHolder(${frozen.seatKey}) = ${JSON.stringify(frozen.holder)}`);
  check('owner-note-names-both-signals',
    frozen.killNotes.length === 1 && /frozen at 0 bytes/.test(frozen.killNotes[0].corpus)
      && /CPU time frozen at 100 ns/.test(frozen.killNotes[0].corpus),
    frozen.killNotes.length ? frozen.killNotes[0].corpus : 'NO hung-kill note on owner-feed');
  check('stall-note-fires-exactly-once',
    frozen.stallNotes === 1,
    `'slot stalled after' notes = ${frozen.stallNotes} (stalled rows now stay on the ladder — a repeat here is the noise the guard prevents)`);

  // ── 2. THE DISCRIMINATING ARM · same scenario, cpu ADVANCING → NO kill ──────────────────────
  let n = 100;
  const moving = await scenario({ cpu: () => (n += 7), tickerConfig: { stall_kill_ticks: 5 }, maxTicks: 12 });
  check('advancing-cpu-does-NOT-kill',
    moving.killCalls.length === 0 && moving.hungActions.length === 0 && moving.status === 'stalled',
    `kill() calls=${moving.killCalls.length} status=${moving.status} after ${moving.ticks} ticks — the guard must DISCRIMINATE, not merely be reachable`);

  // ── 3. NEGATIVE CONTROL · no cpu signal at all (every setsid exec) → NO kill ────────────────
  const nocpu = await scenario({ cpu: () => null, tickerConfig: { stall_kill_ticks: 5 }, maxTicks: 12 });
  check('null-cpu-setsid-does-NOT-kill',
    nocpu.killCalls.length === 0 && nocpu.status === 'stalled',
    `kill() calls=${nocpu.killCalls.length} status=${nocpu.status} — owner ruled one frozen signal too weak`);

  // ── 4. NEGATIVE CONTROL · the rung switched off ────────────────────────────────────────────
  const off = await scenario({ cpu: () => 100, tickerConfig: { stall_kill_ticks: 0 }, maxTicks: 12 });
  check('stall_kill_ticks-0-disables-the-rung',
    off.killCalls.length === 0 && off.status === 'stalled',
    `kill() calls=${off.killCalls.length} status=${off.status}`);

  lines.push(`FAILURES: ${failures}`);
  if (failures) throw new Error(`${failures} check(s) failed`);
}

capture('probe-hung-kill', run);
