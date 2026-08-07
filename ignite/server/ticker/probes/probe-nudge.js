'use strict';

// The nudge: an enqueue over the internal API runs an extra tick instead of waiting out the
// 10 s cadence. Four things must hold, and each fails loudly here if the logic breaks.
//
//   A · a nudge runs ONE extra tick, soon (well inside a cadence interval)
//   B · a burst of nudges coalesces into ONE tick (debounce)
//   C · re-entrancy — a nudge fired while a tick runs never starts a second concurrent tick,
//       and produces exactly ONE follow-on after it
//   D · loop guard — a CADENCE tick never chains, and a nudged tick with no new external work
//       schedules nothing
//   E · the chat pipeline's first hop — a NUDGED tick that fires a `send-message` row (the chat
//       bridge's note onto a chain thread) schedules the follow-on that runs the wake scan,
//       instead of leaving that message to the next cadence interval
//
// No spawn, no systemd: the nudge is pure scheduling, so this probe drives the ticker with an
// empty queue and counts ticks.

const { setup, teardown, sleep, capture } = require('./lib');

async function run(lines) {
  const ctx = setup();
  try {
    const { ticker } = ctx;

    // A · one nudge -> one extra tick, promptly.
    const before = ticker.getTickNumber();
    ticker.nudge('probe-a');
    await sleep(600);
    const afterA = ticker.getTickNumber();
    lines.push(`A: tick ${before} -> ${afterA} after one nudge + 600ms`);
    if (afterA !== before + 1) throw new Error(`expected exactly 1 nudged tick, got ${afterA - before}`);

    // B · a burst coalesces. Five nudges inside the debounce window are one tick.
    for (let i = 0; i < 5; i++) ticker.nudge('probe-burst');
    await sleep(600);
    const afterB = ticker.getTickNumber();
    lines.push(`B: tick ${afterA} -> ${afterB} after a burst of 5 nudges`);
    if (afterB !== afterA + 1) throw new Error(`burst did not coalesce: ${afterB - afterA} ticks`);

    // C · re-entrancy. Nudge while a tick is in flight: the in-flight tick must not be joined by
    // a second one, and exactly one follow-on must run after it.
    const inFlight = ticker.tick();
    ticker.nudge('probe-reentrant', 1);
    ticker.nudge('probe-reentrant-2', 1);
    await inFlight;
    const afterInFlight = ticker.getTickNumber();
    await sleep(600);
    const afterC = ticker.getTickNumber();
    lines.push(`C: in-flight tick ended at ${afterInFlight}, follow-on settled at ${afterC}`);
    if (afterInFlight !== afterB + 1) throw new Error(`the in-flight tick was not exactly one tick: ${afterInFlight - afterB}`);
    if (afterC !== afterInFlight + 1) throw new Error(`expected exactly 1 follow-on tick, got ${afterC - afterInFlight}`);

    // D · loop guard. A plain cadence tick (never nudged, empty queue) chains nothing, and the
    // nudged ticks above produced no NUDGE_AFTER action so they chained nothing either.
    const r = await ticker.tick();
    const nudgePhase = r.actions.find(a => a.phase === 'nudge');
    lines.push(`D: cadence tick nudge phase = ${JSON.stringify(nudgePhase)}`);
    if (!nudgePhase || nudgePhase.skipped !== true) throw new Error('a cadence tick scheduled a nudge');
    if (nudgePhase.nudged) throw new Error('a cadence tick reported itself as nudged');
    const settled = ticker.getTickNumber();
    await sleep(1500);
    lines.push(`D: tick ${settled} -> ${ticker.getTickNumber()} after 1500ms of quiet`);
    if (ticker.getTickNumber() !== settled) throw new Error('the loop did not converge — a tick chained with no new work');

    // E · the chat pipeline's first hop, with no spawn: a nudged tick that fires a send-message
    // row must schedule the follow-on tick whose wake scan sees that message.
    ctx.store.registerJob({
      jobId: 'chat-note',
      actionType: 'send-message',
      function: 'send-message',
      argsSchema: JSON.stringify({ required: { type: 'string', thread: 'string', corpus: 'string' } }),
    });
    ctx.store.enqueue({
      jobId: 'chat-note',
      args: JSON.stringify({ type: 'note', thread: 'exec-1', corpus: 'owner says hi' }),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt: new Date(Date.now() - 1000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      enqueuedBy: 'probe',
    });
    const beforeE = ticker.getTickNumber();
    ticker.nudge('enqueue');
    await sleep(600);
    const eTick = ctx.store.getLastTick();
    const eActions = JSON.parse(eTick.actions_json);
    const eNudge = eActions.find(a => a.phase === 'nudge');
    lines.push(`E: fired=${eActions.some(a => a.action === 'send-message')} nudge phase=${JSON.stringify(eNudge)}`);
    if (!eActions.some(a => a.action === 'send-message')) throw new Error('the nudged tick did not fire the send-message row');
    if (!eNudge || eNudge.scheduled !== 'send-message') throw new Error('firing a send-message row scheduled no follow-on tick');
    await sleep(1600);
    const afterE = ticker.getTickNumber();
    lines.push(`E: tick ${beforeE} -> ${afterE} (fire + follow-on)`);
    if (afterE !== beforeE + 2) throw new Error(`expected exactly 2 ticks (fire + one follow-on), got ${afterE - beforeE}`);

    // The nudged ticks are labelled for the operator reading the journal.
    const last = ctx.store.getLastTick();
    lines.push(`last recorded tick: ${last.tick}`);
  } finally {
    teardown(ctx);
  }
}

capture('probe-nudge', run);
