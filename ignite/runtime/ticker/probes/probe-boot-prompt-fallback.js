'use strict';

// E22 (owner ruling, 2026-08-23) — A PROMPT-LESS FIRST EXECUTION OF A DAEMON-LANE SEAT BOOTS ON ITS
// BOOT PROMPT, COMPOSED BY THE DAEMON AT DISPATCH.
//
// The leader-direct daemon-lane launch door (`coordinate launch …` on a goal whose `execution-lane`
// reads `daemon` — team-kit/coord.py#launch_daemon_lane) enqueues a seat sitting with NO `prompt`
// in its args, because a CAGED leader cannot read a sibling seat's descriptor and must not compose
// one (G-leader-0822-2058: "Read your briefing None first"). The ticker composes it at dispatch
// through the ONE composer the seeding pass and the watcher already ask (`engine/seeding.js#
// seatBootPrompt` → `coordinate boot-prompt --lane daemon`). This probe drives a REAL tick.
//
// THE THREE CLAIMS:
//   1. daemon-lane goal + a seat with a descriptor + a prompt-less enqueue → the spawn action says
//      `bootPrompt: composed` and the prompt file the harness reads on stdin carries the seat's
//      boot prompt ("Read your briefing …/seats/<seat>/seat.md first") — never empty bytes;
//   2. the SAME shape on a goal with NO lane marker (console, the default) is UNTOUCHED: the spawn
//      still happens, the action says `bootPrompt: unavailable` with reason `not-daemon-lane`, and
//      the prompt file carries NO boot prompt — only what HEAD already dispatched for a prompt-less
//      row: spawn.js's uniform descriptor carriage for a non-claude harness (seat.md + separator,
//      EMPTY message tail; measured byte-identical, 331 bytes, against HEAD's ticker.js on
//      2026-08-23). Every probe fixture and every hand `ignite add-job` keeps today's bytes — the
//      positive control for the bound;
//   3. daemon-lane goal but a seat coord CANNOT compose for (a descriptor with a cast but no
//      `seat:` key, so `boot-prompt` refuses it by name) FALLS BACK SOFTLY: the spawn still happens
//      on the carriage bytes and the action NAMES the composer's reason — a throw here would
//      abandon the whole tick, which is the one thing this fallback must never do.
//
// The tally is COUNTED, never typed (the folder's idiom).

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation — no-op under the runner
const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, registerLaunchAgentJob, capture } = require('./lib');

let scenarios = 0;

function promptFileOf(ctx, execRow) {
  return path.join(ctx.dataRoot, 'prompts', `${execRow.session_id}.txt`);
}

function enqueuePromptless(ctx, jobId, workdir) {
  return ctx.store.enqueue({
    jobId,
    args: JSON.stringify({ workdir }),
    sessionMode: 'headless',
    triggerKind: 'scheduled',
    runAt: new Date(Date.now() - 1000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe',
  });
}

function seatOf(ctx, goalDir, seat, { named = true } = {}) {
  const dir = path.join(goalDir, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  // `named: false` keeps the CAST (so the spawn door admits the seat) but drops the `seat:` key,
  // so coord's `boot-prompt` finds no descriptor for the name and refuses — the composer's own
  // refusal, reached through the real subprocess.
  const head = named ? `seat: ${seat}\n` : '';
  fs.writeFileSync(path.join(dir, 'seat.md'), `---\n${head}harness: bash\nmodel: test-sleep\n---\nprobe brief\n`);
  return dir;
}

// The descriptor carriage spawn.js rides on a non-claude harness's first message: seat.md, a
// separator paragraph, then the message. With an EMPTY message the bytes end at the carriage's own
// last line. Asserted by SHAPE (starts with the descriptor, ends with the carriage's closing
// sentence, no boot-prompt sentence) rather than by restating spawn.js's literal here.
function isCarriageOnly(bytes, seatDir) {
  const seatText = fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8');
  return bytes.startsWith(seatText) && /follows:\n\n$/.test(bytes) && !/Read your briefing/.test(bytes);
}

async function tickAndSpawnOf(ctx, jobId) {
  const r = await ctx.ticker.tick(new Date());
  const spawn = r.actions.find((a) => a.action === 'spawn');
  if (!spawn) throw new Error(`expected a spawn action, got ${JSON.stringify(r.actions)}`);
  const execRow = ctx.store.dump().jobs_log.find((x) => x.job_id === jobId);
  if (!execRow) throw new Error(`no jobs_log row for ${jobId}`);
  return { spawn, execRow, actions: r.actions };
}

async function run(lines) {
  const ctx = setup();
  try {
    // ── 1 · DAEMON LANE + DESCRIPTOR → composed ────────────────────────────────────────────────
    // The fixture's goal folder IS `<work>/.rbtv/goals/probe-goal` (lib.js); flip it to the daemon
    // lane with the one-word marker the goals-tree grammar reads.
    fs.writeFileSync(path.join(ctx.runDir, 'execution-lane'), 'daemon\n');
    fs.mkdirSync(path.join(ctx.runDir, 'coordination'), { recursive: true });
    registerLaunchAgentJob(ctx, 'job-daemon');
    const seatA = seatOf(ctx, ctx.runDir, 'seat-composed');
    enqueuePromptless(ctx, 'job-daemon', seatA);
    let { spawn, execRow } = await tickAndSpawnOf(ctx, 'job-daemon');
    lines.push(`daemon-lane spawn action: ${JSON.stringify(spawn)}`);
    if (spawn.bootPrompt !== 'composed') {
      throw new Error(`expected bootPrompt=composed on the daemon lane, got ${JSON.stringify(spawn)}`);
    }
    const bytesA = fs.readFileSync(promptFileOf(ctx, execRow), 'utf8');
    if (!/Read your briefing .*\/seats\/seat-composed\/seat\.md first/.test(bytesA)) {
      throw new Error(`the prompt file does not carry the seat's boot prompt: ${JSON.stringify(bytesA.slice(0, 200))}`);
    }
    lines.push(`PASS  daemon lane: a prompt-less first execution booted on its composed boot prompt (${bytesA.length} bytes, names ${path.basename(seatA)}/seat.md)`);
    scenarios += 1;
    try { await ctx.mgr.kill(execRow.exec_id); } catch { /* best effort */ }

    // ── 2 · NO LANE MARKER (console) → untouched: empty bytes, reason named ───────────────────
    fs.rmSync(path.join(ctx.runDir, 'execution-lane'));
    registerLaunchAgentJob(ctx, 'job-console');
    const seatB = seatOf(ctx, ctx.runDir, 'seat-console');
    enqueuePromptless(ctx, 'job-console', seatB);
    ({ spawn, execRow } = await tickAndSpawnOf(ctx, 'job-console'));
    lines.push(`console-lane spawn action: ${JSON.stringify(spawn)}`);
    if (spawn.bootPrompt !== 'unavailable' || spawn.bootPromptReason !== 'not-daemon-lane') {
      throw new Error(`expected bootPrompt=unavailable/not-daemon-lane off the daemon lane, got ${JSON.stringify(spawn)}`);
    }
    const bytesB = fs.readFileSync(promptFileOf(ctx, execRow), 'utf8');
    if (!isCarriageOnly(bytesB, seatB)) {
      throw new Error(`off the daemon lane the prompt must be HEAD's bytes — the descriptor carriage with an EMPTY message, no boot prompt — got ${bytesB.length} bytes: ${JSON.stringify(bytesB.slice(0, 120))}`);
    }
    lines.push(`PASS  no lane marker: the spawn happened on the bytes HEAD already dispatched (descriptor carriage, empty message, ${bytesB.length} bytes, no boot prompt), and the action names why (not-daemon-lane)`);
    scenarios += 1;
    try { await ctx.mgr.kill(execRow.exec_id); } catch { /* best effort */ }

    // ── 3 · DAEMON LANE, NO DESCRIPTOR → soft fallback, reason named, tick not abandoned ──────
    fs.writeFileSync(path.join(ctx.runDir, 'execution-lane'), 'daemon\n');
    registerLaunchAgentJob(ctx, 'job-nodesc');
    const seatC = seatOf(ctx, ctx.runDir, 'seat-nodesc', { named: false });
    enqueuePromptless(ctx, 'job-nodesc', seatC);
    let r3;
    try {
      r3 = await tickAndSpawnOf(ctx, 'job-nodesc');
    } catch (err) {
      // The TICK must have completed and a spawn action must be recorded; what is forbidden is an
      // abandoned tick with no action at all.
      throw new Error(`scenario 3 could not observe a spawn action: ${err.message}`);
    }
    lines.push(`no-descriptor spawn action: ${JSON.stringify(r3.spawn)}`);
    if (r3.spawn.bootPrompt !== 'unavailable' || !r3.spawn.bootPromptReason || r3.spawn.bootPromptReason === 'not-daemon-lane') {
      throw new Error(`expected a named soft fallback from the COMPOSER, got ${JSON.stringify(r3.spawn)}`);
    }
    const bytesC = fs.readFileSync(promptFileOf(ctx, r3.execRow), 'utf8');
    if (!isCarriageOnly(bytesC, seatC)) throw new Error(`soft fallback must keep HEAD's carriage bytes, got ${bytesC.length}: ${JSON.stringify(bytesC.slice(0, 120))}`);
    lines.push(`PASS  unnamed-descriptor seat: the tick completed, the spawn kept HEAD's bytes, and the action names the composer's reason: ${r3.spawn.bootPromptReason}`);
    scenarios += 1;
    try { await ctx.mgr.kill(r3.execRow.exec_id); } catch { /* best effort */ }

    lines.push(`PASS  probe-boot-prompt-fallback: ${scenarios}/${scenarios} scenarios`);
  } finally {
    teardown(ctx);
  }
}

capture('probe-boot-prompt-fallback', run);
