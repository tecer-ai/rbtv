'use strict';

// probe-g222-terminal-turn — the crash sweep must never overwrite a turn that ALREADY REPORTED.
//
// G-222. Before 7.46 the sweep's set was `running` + `launching` + `stalled`, so a turn that had
// already reported was STRUCTURALLY EXCLUDED from it. 7.46 re-keyed the set on
// `sessions.status = 'alive'` (heart-store.js listTurnsOfLiveSessions — "sessions.status is the
// ONLY predicate deciding membership"), which is faithful to that function's name and lost the
// exclusion. The sweep then observes a PROCESS end — a session fact — and writes a TURN outcome
// over one that exists: a `done` turn becomes `failed`, with a manufactured crash completion and
// a "slot halted" note for a session that ended normally.
//
// ⚠ THE EXPOSED STATE IS NOT A FIXTURE CONTRIVANCE. `updateExecutionStatus()` structurally cannot
// end a session (7.46's design), and five production sites write a TERMINAL turn status through it
// while closing nothing: spawn.js orphanRescan (:786/:799/:808 — the daemon's own boot rescan) and
// pty-host.js (:289/:327 — a headed launch that fails; the file was deleted at task 7.29, and the
// citation is kept as the provenance of this probe's construction, not as a live path). This
// probe reaches the state the same way
// they do, through that same store call.
//
// ⚠⚠ WHAT MAKES THIS PROBE DISCRIMINATE, and it is why the session assertion is here at all: the
// obvious repair — excluding terminal turns from listTurnsOfLiveSessions() — preserves the turn AND
// leaves the session `alive` forever, because the sweep is the only thing that ever closes a leaked
// session. That repair passes check 1 and 3 and FAILS check 2. Measured before this probe existed
// (three arms, seats/engineer/FINDING-G222-predicate-vs-write.md), so check 2 is not decoration:
// without it this probe would ratify a fix that trades a loud corruption for a silent permanent one.
//
// The last scenario is the POSITIVE CONTROL: a genuinely non-terminal turn whose process dies is
// still swept to `failed` with its completion. "The sweep no longer rewrites terminal turns" and
// "the sweep no longer runs" produce the same output on scenario 1 alone.

const { execFileSync } = require('node:child_process');
const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture, sleep } = require('./lib');

function killUnit(unitName) {
  try {
    execFileSync('systemctl', ['--user', 'kill', '--signal=SIGKILL', unitName], { stdio: 'ignore', timeout: 10000 });
  } catch { /* best effort — liveness is asserted below, never assumed from this call */ }
}

// One live agent turn, spawned through the production path and then killed under the daemon.
async function spawnAndKill(ctx, lines, label) {
  enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: new Date() });
  const r = await ctx.ticker.tick(new Date());
  lines.push(`[${label}] dispatch tick ${r.tick}`);
  const rows = ctx.store.dump().jobs_log;
  const exec = rows[rows.length - 1];
  await sleep(500);
  const info = await ctx.mgr.status(exec.exec_id);
  killUnit(info.unitName);
  await sleep(500);
  const dead = await ctx.mgr.status(exec.exec_id);
  if (dead.live) throw new Error(`[${label}] the process is still live after SIGKILL — the sweep would not fire and nothing below would be evidence`);
  lines.push(`[${label}] exec ${exec.exec_id} spawned and killed (unit ${info.unitName})`);
  return ctx.store.getExecution(exec.exec_id);
}

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);

    // ── 1 · a turn that ALREADY REPORTED, under a session nothing closed ──────────────────────
    const exec = await spawnAndKill(ctx, lines, 'reported');
    // The five sites' own call: a terminal turn status, with no session close.
    ctx.store.updateExecutionStatus(exec.exec_id, { status: 'done', endedAt: new Date() });

    const before = ctx.store.getExecution(exec.exec_id);
    const sessBefore = ctx.store.getSession(before.session_pk);
    lines.push(`PRECONDITION: turn=${before.status} session=${sessBefore.status}`);
    if (before.status !== 'done' || sessBefore.status !== 'alive') {
      throw new Error(`the exposed state was not established (turn=${before.status} session=${sessBefore.status}) — else this probe tests nothing`);
    }
    const msgsBefore = ctx.store.dump().messages.length;

    const r = await ctx.ticker.tick(new Date());
    lines.push(`sweep tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    // CHECK 1 — the reported outcome survives. RED on the unfixed code.
    const after = ctx.store.getExecution(exec.exec_id);
    lines.push(`after sweep: turn=${after.status}`);
    if (after.status !== 'done') {
      throw new Error(`the crash sweep OVERWROTE a turn that had already reported: done -> ${after.status}`);
    }

    // CHECK 2 — the session it observed ending is CLOSED. RED on the exclusion-only repair.
    const sessAfter = ctx.store.getSession(before.session_pk);
    lines.push(`after sweep: session=${sessAfter.status} reason=${sessAfter.close_reason}`);
    if (sessAfter.status === 'alive') {
      throw new Error('the sweep saw the process was gone and left the session ALIVE — nothing else ever closes a leaked session, so this is permanent');
    }
    if (sessAfter.status !== 'closed') {
      throw new Error(`a turn that reported 'done' must close its session 'closed', not '${sessAfter.status}' — the session level must not invent a crash the turn did not report`);
    }

    // CHECK 3 — no manufactured crash record. A completion and an owner note for a session that
    // ended normally are what an operator would act on.
    const dump = ctx.store.dump();
    const newMsgs = dump.messages.slice(msgsBefore);
    const fabricated = newMsgs.filter((m) => (m.type === 'completion' && m.thread === after.thread)
      || (m.type === 'note' && (m.corpus || '').includes(`slot halted: session crashed (exec ${after.exec_id})`)));
    lines.push(`messages written by the sweep for a turn that had reported: ${fabricated.length}`);
    if (fabricated.length !== 0) {
      throw new Error(`the sweep manufactured a crash record for a turn that had already reported: ${JSON.stringify(fabricated.map((m) => m.corpus))}`);
    }

    // ── 2 · POSITIVE CONTROL: the sweep still sweeps ──────────────────────────────────────────
    // Same fixture, same tick, a turn that never reported. If this does not go to `failed` with a
    // completion, the checks above were satisfied by a sweep that had stopped working.
    const live = await spawnAndKill(ctx, lines, 'control');
    const liveBefore = ctx.store.getExecution(live.exec_id);
    if (!['running', 'launching'].includes(liveBefore.status)) {
      throw new Error(`[control] the control turn must be NON-terminal to exercise the sweep, got ${liveBefore.status}`);
    }
    const r2 = await ctx.ticker.tick(new Date());
    lines.push(`control sweep tick ${r2.tick}: ${JSON.stringify(r2.actions)}`);
    const controlAfter = ctx.store.getExecution(live.exec_id);
    lines.push(`[control] after sweep: turn=${controlAfter.status}`);
    if (controlAfter.status !== 'failed') {
      throw new Error(`[control] a turn that never reported must still be swept to failed, got ${controlAfter.status} — the sweep is not doing its job`);
    }
    const controlCompletion = ctx.store.dump().messages
      .find((m) => m.type === 'completion' && m.thread === controlAfter.thread && m.status === 'failed');
    if (!controlCompletion) {
      throw new Error('[control] the swept turn got no crash completion — the sweep is inert, so scenario 1 proved nothing');
    }
    lines.push('[control] the sweep still records a crash for a turn that never reported');
  } finally {
    teardown(ctx);
  }
}

capture('probe-g222-terminal-turn', run);
