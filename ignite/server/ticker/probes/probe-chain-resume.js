'use strict';

// r-chat-chain-resumes-session (owner, 2026-08-07) — a chained launch-agent turn RESUMES the
// predecessor's harness session instead of respawning with the transcript re-embedded.
//
//   A. RESUME: predecessor has a session_ref + the profile carries a resume template + the turn
//      is not a compaction turn  ->  the launch uses the RESUME argv with the PREDECESSOR's ref,
//      and the prompt is ONLY the owner's new message(s) — no transcript, no CONTINUE header.
//   B. FALLBACK (no session_ref): the same profile, predecessor's ref cleared -> the EXEC argv
//      and the full transcript-embed prompt, byte-for-byte the pre-ruling shape.
//   C. FALLBACK (no resume template): a profile declaring none never resumes, however good its
//      ref is. (This is the shape every OTHER ticker probe's `test-chat` profile has, which is
//      why their expectations are untouched by the ruling.)
//
// The worker echoes WHICH template ran and WITH WHICH REF, as a stream-json result line:
// MODE-<exec|resume>-REF-<ref>. Distinguishing the two argvs is the whole point, so the mode is
// read off the completion corpus rather than inferred from anything the ticker reports.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, sleep, capture } = require('./lib');

// \173/\175 are printf octal escapes for { } — ANY literal brace in a profile argv reads as a
// template slot to the config validator. $0/$1 are the two argv words after `bash -c <script>`.
const ECHO = 'printf \'\\173"type":"result","result":"MODE-%s-REF-%s"\\175\\n\' "$0" "$1"';

// ⚠ argv[0] IS NAMED `claude`, AND THAT IS THE FIXTURE'S POINT, not a disguise. `harnessOf` reads
// `basename(exec.argv[0])`, and owner ruling `d-uniform-descriptor-carriage` (2026-08-12) makes a
// NON-claude harness carry its seat descriptor on the FIRST MESSAGE — which would prepend hundreds
// of bytes to every prompt this probe measures byte-exactly, testing that ruling instead of this
// probe's subject. A claude-named shim takes the descriptor on the FLAG instead (argv, which
// nothing here asserts on), so the prompt bytes stay the prompt bytes. The shim is a symlink to
// `bash`, so what actually runs is unchanged.
const HARNESS_DIR = fs.mkdtempSync(path.join(require('node:os').tmpdir(), 'claude-shim-'));
const CLAUDE_SHIM = path.join(HARNESS_DIR, 'claude');
try { fs.symlinkSync('/bin/bash', CLAUDE_SHIM); } catch { /* already there */ }

function makeCtx(configOverrides = {}) {
  return setup(configOverrides, {}, ({ workRoot }) => ({
    claude: {
      // Resumable: assigns its ref at spawn and carries both templates.
      'test-resumable': {
        // 7.787: `--model <the key's model>` so the argv agrees with the key it is filed under
        // (`profiles.js#validateSpecKey`). It lands in bash's positional params, unread.
        exec: { argv: [CLAUDE_SHIM, '-c', ECHO, 'exec', '{session_ref}', '--model', 'test-resumable'], prompt: 'stdin' },
        resume: { argv: [CLAUDE_SHIM, '-c', ECHO, 'resume', '{session_ref}', '--model', 'test-resumable'], prompt: 'stdin' },
        session_ref: { source: 'assigned' },
        workdir_root: workRoot,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
      // Not resumable: a ref on record (cwd-implicit) but NO resume template.
      'test-no-resume': {
        exec: { argv: [CLAUDE_SHIM, '-c', ECHO, 'exec', '{workdir}', '--model', 'test-no-resume'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: workRoot,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
    },
  }));
}

async function tickUntil(ctx, pred, maxTicks = 40, stepMs = 250) {
  const all = [];
  for (let i = 0; i < maxTicks; i++) {
    const res = await ctx.ticker.tick(new Date(Date.now() + 2000));
    all.push(...res.actions);
    if (pred(all)) return all;
    await sleep(stepMs);
  }
  throw new Error(`tickUntil: predicate not satisfied after ${maxTicks} ticks; actions=${JSON.stringify(all.filter(a => a.action))}`);
}

const findAll = (actions, name) => actions.filter((a) => a.action === name);

function promptFileOf(ctx, execId) {
  const row = ctx.store.getExecution(execId);
  if (!row || !row.session_id) throw new Error(`no session_id on exec ${execId}`);
  return fs.readFileSync(path.join(ctx.dataRoot, 'prompts', `${row.session_id}.txt`), 'utf8');
}

function assertEq(label, got, want) {
  if (got !== want) throw new Error(`${label}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
}
function assertIncludes(label, hay, needle) {
  if (!hay.includes(needle)) throw new Error(`${label}: expected ${JSON.stringify(needle)} in ${JSON.stringify(hay.slice(0, 400))}…`);
}
function assertExcludes(label, hay, needle) {
  if (hay.includes(needle)) throw new Error(`${label}: expected NOT to find ${JSON.stringify(needle)} in ${JSON.stringify(hay.slice(0, 400))}…`);
}

// Turn 1 of a chain: enqueue, run to `end`, return its exec row.
// `model` names which of the fixture's launch specs the seat this turn homes at is CAST to — the
// only way a launch selects one since `#d-abolish-profile-names`. It is not a value on the wire.
async function firstTurn(ctx, model, prompt) {
  enqueueLaunchAgent(ctx, { jobId: 'chat-agent', cast: { harness: 'claude', model }, prompt, runAt: new Date() });
  const acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1);
  return ctx.store.getExecution(findAll(acts, 'spawn')[0].execId);
}

// A sender reply lands on the chain's thread; return the chained turn's spawn action.
async function replyAndWake(ctx, exec1, reply) {
  ctx.store.recordMessage({ type: 'note', sender: 'probe-bridge', thread: exec1.thread, corpus: reply, createdAt: new Date() });
  const acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1 && findAll(all, 'spawn').length >= 1);
  const spawn2 = findAll(acts, 'spawn')[0];
  if (!spawn2) throw new Error('chained turn: no spawn action');
  return { spawn2, acts };
}

capture('probe-chain-resume', async (lines) => {
  // ── A · the resume path ─────────────────────────────────────────────────────
  let ctx = makeCtx({ history_compact_chars: 100000 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    const Q1 = 'Q1-resume-scenario';
    const exec1 = await firstTurn(ctx, 'test-resumable', Q1);

    // The ref is ASSIGNED at spawn and equals the session id the daemon minted — recorded before
    // the worker produced a byte, so it is on the row whatever the turn did next.
    assertEq('turn 1 session_ref', exec1.session_ref, exec1.session_id);
    const comp1 = ctx.store.getMessage(exec1.completion_msg_id);
    assertEq('turn 1 template', comp1.corpus, `MODE-exec-REF-${exec1.session_id}`);

    const R1 = 'REPLY-1-only-this-should-be-the-prompt';
    const { spawn2 } = await replyAndWake(ctx, exec1, R1);
    const exec2 = ctx.store.getExecution(spawn2.execId);

    assertEq('turn 2 chain path', spawn2.chain, 'resume');
    assertEq('turn 2 chain reason', spawn2.chainReason, 'predecessor-session-resumable');
    // The RESUME argv ran, with the PREDECESSOR's ref.
    const comp2 = ctx.store.getMessage(exec2.completion_msg_id);
    assertEq('turn 2 template + ref', comp2.corpus, `MODE-resume-REF-${exec1.session_ref}`);
    // The ref carries forward unchanged, so turn 3 resumes the same session.
    assertEq('turn 2 session_ref carried', exec2.session_ref, exec1.session_ref);
    // The prompt is ONLY the new message.
    const prompt2 = promptFileOf(ctx, exec2.exec_id);
    assertEq('turn 2 prompt is new-messages-only', prompt2, R1);
    assertExcludes('turn 2 prompt', prompt2, Q1);
    assertExcludes('turn 2 prompt', prompt2, 'You are continuing an ongoing conversation');
    // Chain semantics untouched.
    assertEq('turn 2 parent', exec2.parent_exec_id, exec1.exec_id);
    assertEq('turn 2 thread', exec2.thread, exec1.thread);

    // Two queued replies join in msg_id order, both in one resumed prompt.
    const R2a = 'REPLY-2a';
    const R2b = 'REPLY-2b';
    ctx.store.recordMessage({ type: 'note', sender: 'probe-bridge', thread: exec1.thread, corpus: R2a, createdAt: new Date() });
    const { spawn2: spawn3 } = await replyAndWake(ctx, exec1, R2b);
    const exec3 = ctx.store.getExecution(spawn3.execId);
    assertEq('turn 3 chain path', spawn3.chain, 'resume');
    assertEq('turn 3 prompt joins queued messages', promptFileOf(ctx, exec3.exec_id), `${R2a}\n\n${R2b}`);

    lines.push(`A PASS: chained turn used the RESUME argv with the predecessor ref (${exec1.session_ref}); `
      + 'prompt was the new message(s) only; ref carried forward; parent/thread unchanged');
  } finally {
    teardown(ctx);
  }

  // ── B · fallback: no session_ref on the predecessor ──────────────────────────
  ctx = makeCtx({ history_compact_chars: 100000 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    const Q1 = 'Q1-no-ref-scenario';
    const exec1 = await firstTurn(ctx, 'test-resumable', Q1);
    const A1 = `MODE-exec-REF-${exec1.session_id}`;
    // Clear the ref the way a pre-ruling row (or a harness that never reported one) looks.
    ctx.store._prepare('UPDATE jobs_log SET session_ref = NULL WHERE exec_id = ?').run(exec1.exec_id);

    const R1 = 'REPLY-1-fallback';
    const { spawn2 } = await replyAndWake(ctx, exec1, R1);
    const exec2 = ctx.store.getExecution(spawn2.execId);
    assertEq('fallback chain path', spawn2.chain, 'transcript');
    assertEq('fallback reason', spawn2.chainReason, 'no-session-ref');
    assertEq('fallback template', ctx.store.getMessage(exec2.completion_msg_id).corpus, `MODE-exec-REF-${exec2.session_id}`);
    // The pre-ruling prompt shape, unchanged.
    const prompt2 = promptFileOf(ctx, exec2.exec_id);
    assertIncludes('fallback prompt', prompt2, 'You are continuing an ongoing conversation');
    assertIncludes('fallback prompt', prompt2, `[owner] ${Q1}`);
    assertIncludes('fallback prompt', prompt2, `[assistant] ${A1}`);
    assertIncludes('fallback prompt', prompt2, `[owner] ${R1}`);
    assertIncludes('fallback prompt', prompt2, "Reply to the owner's latest message(s).");
    lines.push('B PASS: no session_ref -> EXEC argv + full transcript-embed prompt (pre-ruling shape intact)');
  } finally {
    teardown(ctx);
  }

  // ── C · fallback: the profile carries no resume template ─────────────────────
  ctx = makeCtx({ history_compact_chars: 100000 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    const Q1 = 'Q1-no-template-scenario';
    const exec1 = await firstTurn(ctx, 'test-no-resume', Q1);
    if (!exec1.session_ref) throw new Error('C: fixture broken — cwd-implicit should record a ref');

    const { spawn2 } = await replyAndWake(ctx, exec1, 'REPLY-1-no-template');
    const exec2 = ctx.store.getExecution(spawn2.execId);
    assertEq('no-template chain path', spawn2.chain, 'transcript');
    assertEq('no-template reason', spawn2.chainReason, 'no-resume-template');
    assertIncludes('no-template prompt', promptFileOf(ctx, exec2.exec_id), 'You are continuing an ongoing conversation');
    lines.push('C PASS: a ref with no resume template never resumes — the ruling\'s second fallback arm');
  } finally {
    teardown(ctx);
  }

  // ── D · a compaction turn keeps the transcript path ──────────────────────────
  ctx = makeCtx({ history_compact_chars: 150 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    const exec1 = await firstTurn(ctx, 'test-resumable', 'Q1-compaction-scenario-question-with-some-length-to-it');
    ctx.store.recordMessage({
      type: 'note', sender: 'probe-bridge', thread: exec1.thread,
      corpus: 'REPLY-1-long-enough-to-push-the-transcript-over-the-tiny-compaction-bound-for-sure-really',
      createdAt: new Date(),
    });
    const acts = await tickUntil(ctx, (all) => findAll(all, 'compaction-recycle').length >= 1);
    const compactSpawn = findAll(acts, 'spawn').find((a) => a.compact === true);
    if (!compactSpawn) throw new Error('D: no compact:true spawn action');
    assertEq('compaction chain path', compactSpawn.chain, 'transcript');
    assertEq('compaction reason', compactSpawn.chainReason, 'compaction-turn');
    assertIncludes('compaction prompt', promptFileOf(ctx, compactSpawn.execId), 'Compact the following conversation');

    // And the ANSWERING turn after it: its predecessor IS the compaction session, whose harness
    // session only ever saw a summarize instruction — resuming that would continue the summarizer
    // and discard the summary splice. Transcript path, named reason.
    const acts2 = await tickUntil(ctx, (all) => findAll(all, 'spawn').some((a) => !a.compact));
    const answerSpawn = findAll(acts2, 'spawn').find((a) => !a.compact);
    assertEq('post-compaction chain path', answerSpawn.chain, 'transcript');
    assertEq('post-compaction reason', answerSpawn.chainReason, 'parent-compaction');
    assertIncludes('post-compaction prompt', promptFileOf(ctx, answerSpawn.execId), '[summary of earlier conversation]');
    lines.push('D PASS: the compaction turn AND the answering turn after it both keep the transcript path');
  } finally {
    teardown(ctx);
  }

  // ── E · a resume that fails AT THE CARRIER retries once, fresh ───────────────
  // The failure is injected at the spawn-manager seam because the daemon has no other way to
  // make a resume fail on demand — and the real trigger it stands for (a harness session that is
  // gone, so `--resume <id>` exits) has no fixture either. What is proven is the ticker's
  // recovery: the chain does NOT die on a failed resume, it re-runs as the transcript spawn it
  // displaced, on the SAME exec row.
  ctx = makeCtx({ history_compact_chars: 100000 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    const Q1 = 'Q1-resume-failure-scenario';
    const exec1 = await firstTurn(ctx, 'test-resumable', Q1);

    const realSpawn = ctx.mgr.spawn;
    let refused = 0;
    ctx.mgr.spawn = (...a) => {
      // ⚠ INDEX 5, NOT 6 (7.787). `spawn`'s signature lost its `profileName` operand — the
      // argument `#d-abolish-profile-names` deletes — so every positional after it shifted left.
      // A stale index here reads `enqueuedBy` (always truthy), which would have made this arm
      // refuse EVERY spawn and pass for the wrong reason.
      if (a[5]) { refused++; throw new Error('injected: resume spawn failed at the carrier'); }
      return realSpawn(...a);
    };

    const R1 = 'REPLY-1-after-a-failed-resume';
    const { spawn2, acts } = await replyAndWake(ctx, exec1, R1);
    ctx.mgr.spawn = realSpawn;

    if (refused !== 1) throw new Error(`E: expected exactly 1 refused resume, got ${refused}`);
    const failAction = findAll(acts, 'resume-spawn-failed')[0];
    if (!failAction) throw new Error('E: the failed resume was not recorded as its own action');
    assertEq('retry chain path', spawn2.chain, 'transcript');
    assertEq('retry reason', spawn2.chainReason, 'resume-spawn-failed');
    const exec2 = ctx.store.getExecution(spawn2.execId);
    assertEq('retry ran on the same exec row', exec2.exec_id, failAction.execId);
    assertEq('retry used the EXEC argv', ctx.store.getMessage(exec2.completion_msg_id).corpus, `MODE-exec-REF-${exec2.session_id}`);
    const prompt2 = promptFileOf(ctx, exec2.exec_id);
    assertIncludes('retry prompt', prompt2, 'You are continuing an ongoing conversation');
    assertIncludes('retry prompt', prompt2, `[owner] ${Q1}`);
    assertIncludes('retry prompt', prompt2, `[owner] ${R1}`);
    lines.push('E PASS: a carrier-level resume failure retried ONCE as the fresh transcript spawn, same exec row, chain alive');
  } finally {
    teardown(ctx);
  }
});
