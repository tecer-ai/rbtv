'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {
  selectCarrier,
  spawnSystemd,
  spawnSetsid,
  generateSessionId,
  toolExecEnv,
} = require('../spawn/carrier');
const { exitFilePath, ensureExitFile, closeSeatSessionRow, applyDispositionGrants } = require('../spawn/spawn');
const { runWarningCheck } = require('./warnings-check');
// Constants only — the ticker's store is INJECTED (`heartStore`), and this require never
// constructs or opens one. Imported rather than re-spelled so the crash sweep's notion of "the
// turn already reported" is the store's, not a second copy that can drift from it.
// `seatKeyOf` rides along for the same reason: the dispatch phase's seat-busy gate must ask the
// idempotent door's question with the door's own key, never a second spelling of it.
const { TERMINAL_TURN_STATUSES, sessionStatusForEndedTurn, seatKeyOf } = require('../heart/heart-store');
// Task C5 — the ONE definition of what a row may template into an exec'd argv, shared with the
// store's enqueue gate so the two ends can never disagree about what a legal value is.
const { expandArgv, checkFireToolWorkdir } = require('../heart/argv-template');
// Task 7.12 — the job->seat pointer (`r-job-seat-home`). The RESOLVER is imported, never
// re-implemented: `seat-folder.js` is the one definition of what a seat folder is, and a second
// spelling here would be a second definition that drifts (that module's own opening argument).
const { resolveSeatHome } = require('../seat-identity/seat-folder');
const { resolveWorkspaceRoot } = require('../spawn/config');
// Task 7.129 (7.77 / R9) — the one-live-execution rule. The DECISION lives in its own module and
// the liveness EVIDENCE in `server/lease/lease.js` (7.607 E1; the register read that used to sit in
// seat-folder.js is gone with the layer); dispatch below only obeys the decision. Keeping the rule
// out of this function is what makes it unit-checkable without a tick.
const { oneLiveRunDecision } = require('./one-live-run');
// Task 7.130 (7.77 / R9) — the other half of the same rule: a queued start tells the owner. Rendering
// and delivery live in that module; the branch below only calls it and records what came back. Its
// deliverer is INJECTED and the one wired here is credential-free (the owner feed) — nothing in the
// daemon resolves a credentialed transport, because arming one is a cutover (`r-cutover-gated`).
const { createQueuedStartNotifier, ownerFeedDeliverer } = require('./queued-start-notify');
// Task C3 — the goal's Slack channel at its workflow start. The DECISION (is this row a run start,
// is the goal interactive, what is the invocation) lives in its own module and is unit-checkable
// without a tick; the branch below only performs what came back. Same split as one-live-run above,
// and for the same reason.
const { channelEnsureDecision } = require('./goal-channel-start');

// D25 — owner summons (chat-bridge `chat-agent*` rows) may take ONE extra live slot
// past `max_live_agent_sessions`. Non-interactive rows never use it.
const RESERVED_INTERACTIVE_SLOTS = 1;
const CHAT_BRIDGE_ENQUEUED_BY = 'chat-bridge-slack';

function isReservedInteractiveRow(queueRow, job) {
  if (!queueRow || queueRow.enqueued_by !== CHAT_BRIDGE_ENQUEUED_BY) return false;
  const id = (job && job.job_id) || queueRow.job_id || '';
  return typeof id === 'string' && id.startsWith('chat-agent');
}

const DEFAULT_CONFIG = {
  tick_interval_ms: 10000,
  stall_warn_ticks: 12,
  stall_halt_ticks: 24,
  // The HUNG-KILL rung, above `stalled` on the same ladder. Total ticks of silence (not ticks
  // since the stall) at which a turn that is ALREADY `stalled` and whose process has written no
  // log bytes AND burnt no CPU time is killed, freeing its seat. ~10s per tick → ~10 minutes.
  // `0` disables the rung entirely; `stalled` keeps its meaning either way — it still pages, it is
  // still non-terminal, and it is still the owner's cue to look.
  stall_kill_ticks: 60,
  max_live_agent_sessions: 14,
  slot_max_repeats: 10,
  history_compact_chars: 60000,
  // How long a queue row deferred by the seat-busy gate may keep waiting. An hour-old chat
  // message must not fire as if it were fresh, so past this the row is REMOVED with an owner note
  // — never silently.
  seat_queue_max_age_s: 3600,
};

// Private marker carried in a re-dispatch queue row's args JSON so the ticker
// can pass parent_exec_id to fireQueueRow. The queue table has no column for
// this in the v1 schema; this marker is stripped before spawn and before the
// args are persisted in jobs_log.
const CHAIN_MARKER = '__rbtv_chain_parent_exec_id';
// W1 — how many seat session rows the closer may close in ONE tick. See its use in `enforce`.
const CLOSER_MAX_PER_TICK = 5;
// W1 — how often the enforce phase scans for row-less `rbtv-worker-*` units. See its use in
// `enforce`: the scan reads the WHOLE store, and nothing acts on its finding automatically.
const ROWLESS_UNIT_SCAN_EVERY_TICKS = 30;

// Private marker PERSISTED in a compaction turn's jobs_log args (unlike
// CHAIN_MARKER it must survive the fire: Advance keys the always-re-dispatch
// branch on it, and prompt composition keys the summary splice on it). A
// compaction turn is a normal worker session whose only task is summarizing
// its chain's conversation — the chain's SHORT-TERM memory only (owner ruling
// 2026-07-18: long-term memory across conversations is a separate, undefined
// process — never this marker's business).
const COMPACT_MARKER = '__rbtv_compact_turn';

// Private marker persisted in the args of an AUTOMATIC re-dispatch — v1: only
// the answering turn a compaction-recycle enqueues. Together with
// COMPACT_MARKER it identifies the automatic executions the budget counts
// (heart-store countAutomaticChainRecycles); sender-triggered re-dispatches
// (recycle-on-pending, wake) are UNMARKED and never consume the automatic
// budget (owner ruling 2026-07-18).
const AUTO_MARKER = '__rbtv_auto_redispatch';
const AUTOMATIC_MARKER_KEYS = [COMPACT_MARKER, AUTO_MARKER];

// Prompt templates for chained (re-dispatched) launch-agent turns. The
// transcript is DERIVED from the store at spawn time, never stored back into
// args ("ready is computed, never stored" applied to conversation history).
const CONTINUE_PROMPT_HEADER = 'You are continuing an ongoing conversation with the owner. The conversation so far:\n\n';
const CONTINUE_PROMPT_FOOTER = "\n\nReply to the owner's latest message(s).";
const COMPACT_PROMPT_HEADER = 'Compact the following conversation into a concise summary that preserves every fact, decision, number, constraint, and open question needed to continue the conversation faithfully. Reply with ONLY the summary.\n\n';

// Bounded tail the clean-exit answer extraction reads. The result line is the
// log's LAST line, so a bounded read from the end always sees it.
const RESULT_TAIL_BYTES = 262144;

// Owner-facing ticker notes are addressed to the owner, never to a seat's `exec-<N>`
// sub-thread — a note on a seat's address wakes that seat (owner ruling D39).
const OWNER_NOTE_THREAD = 'owner-feed';

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function toIsoUtc(d) {
  if (!(d instanceof Date)) d = new Date(d);
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function safeJsonParse(s, fallback = null) {
  try { return JSON.parse(s); } catch { return fallback; }
}

function logLine(logPath, line) {
  if (!logPath) return;
  try { fs.appendFileSync(logPath, line + '\n', 'utf8'); } catch {}
}

function tailBytes(logPath, n) {
  if (!logPath || !fs.existsSync(logPath)) return '';
  try {
    const stats = fs.statSync(logPath);
    const start = stats.size > n ? stats.size - n : 0;
    return fs.readFileSync(logPath, { start, encoding: 'utf8' });
  } catch { return ''; }
}

function createTicker({ heartStore, spawnManager, config = {}, logger = null, feedPath = null, logPath = null }) {
  const cfg = { ...DEFAULT_CONFIG, ...config };
  let ticking = false;
  let tickNumber = null;

  // Task 7.19 wake-scan bound state — in-memory CACHES only (safe to lose:
  // a restart's first tick falls back to one full tail scan). `wakeWatermark`
  // is the highest messages.msg_id already examined for wake candidates;
  // `pendingWakeThreads` holds wakes deferred while their slot was live/armed.
  let wakeWatermark = null;
  const pendingWakeThreads = new Set();

  // ── Nudge · the cadence is a FLOOR on latency, and new work does not have to wait it out ─────
  //
  // The loop runs every `tick_interval_ms` (10 s). An owner chat message arriving over the
  // internal API therefore cost up to two-plus cadence intervals before its agent spawned
  // (measured live: enqueued 22:03:28, spawned 22:03:59). `nudge()` runs ONE extra tick soon
  // after new EXTERNAL work lands. The cadence timer lives in the daemon boot and is never
  // touched here — a nudge is an EXTRA tick, never a rescheduled one.
  //
  // WHO MAY CALL IT: the enqueue path only (server/index.js wires it to the internal API's
  // enqueue-job success). The ticker's own writes NEVER call it directly — that would be a
  // self-trigger — which is why the follow-on below is scoped to ticks that were themselves
  // nudged and to the five actions that leave real work for the very next tick.
  const NUDGE_DEBOUNCE_MS = 250;
  // A queue row the ticker inserts is dated `now + 1000 ms` (every insertQueueRow call site), so
  // the follow-on tick that fires it MUST land after that — at the 250 ms debounce the row is
  // not yet due and the nudge chain would break exactly where it matters.
  // ponytail: this constant is COUPLED to the `now + 1000` literal at the insertQueueRow call
  // sites; change that offset and the follow-on fires early and the chain silently degrades to
  // cadence. Upgrade path if it ever moves: derive the delay from the row's own run_at.
  const NUDGE_FOLLOWON_MS = 1200;
  // The chat pipeline, as actions: a `send-message` row lands an owner message the wake scan has
  // not seen yet (it already ran this tick, before dispatch); the four re-dispatch actions insert
  // a queue row after this tick's dispatch phase is past. Everything else — `spawn`, `defer`,
  // `end`, the deferred wakes — leaves nothing for the next tick, so the chain terminates there.
  const NUDGE_AFTER = new Set([
    'send-message', 'wake-redispatch', 'blocked-redispatch', 'recycle', 'compaction-recycle',
  ]);

  let nudgeTimer = null;
  let nudgeDueAt = 0;
  let nudgePending = null; // { reason, delayMs } — the one nudge waiting on its timer or on the running tick
  let nudgedWith = null;   // reason the tick about to start was nudged with (consumed by tick())

  // ⚠ THE SHUTDOWN LATCH — the nudge chain is a SECOND tick driver, and the daemon's
  // `clearInterval(timer)` only ever stopped the FIRST one. Measured 2026-08-12 on the live VPS:
  // SIGTERM landed 21:20:35, `received SIGTERM, shutting down` logged 21:20:43, and ticks
  // 241980/241981/241982 still ran (and still DISPATCHED) at 21:21:01-21:21:05, because each
  // nudged tick re-arms the next through `nudge()` at the tail of `tick()` — a self-perpetuating
  // `setTimeout` the cadence `clearInterval` cannot reach. The daemon was launching new work out
  // of a process systemd was waiting to reap.
  //
  // The latch is checked in BOTH places on purpose: `nudge()` so nothing new is ever armed, and
  // `tick()` so a timer that already fired (or a cadence//caller tick racing the signal) still
  // dispatches nothing. One flag, both doors — a guard on the arming side alone loses the race
  // with a callback already queued on the event loop.
  let stopped = false;

  // Called from the daemon's SIGTERM path (server/index.js). Idempotent, and NOT a close: the
  // store, the spawn manager and any in-flight tick are somebody else's to wind down. This stops
  // the loop from STARTING anything more.
  function stop() {
    stopped = true;
    if (nudgeTimer) {
      clearTimeout(nudgeTimer);
      nudgeTimer = null;
    }
    nudgePending = null;
  }

  function nudge(reason = 'enqueue', delayMs = NUDGE_DEBOUNCE_MS) {
    if (stopped) return;
    const dueAt = Date.now() + delayMs;
    if (nudgeTimer) {
      // Debounce: a burst of enqueues coalesces into the pending nudge. A LATER-due request
      // EXTENDS it rather than folding into it — firing at the earlier time would run the tick
      // before the row the later request was scheduled for is due, and drop it.
      if (dueAt <= nudgeDueAt) return;
      clearTimeout(nudgeTimer);
    }
    nudgePending = { reason, delayMs };
    nudgeDueAt = dueAt;
    nudgeTimer = setTimeout(fireNudge, delayMs);
    if (typeof nudgeTimer.unref === 'function') nudgeTimer.unref();
  }

  function fireNudge() {
    nudgeTimer = null;
    if (!nudgePending) return;
    // Re-entrancy: never a second concurrent tick. `nudgePending` stays set and the running
    // tick's `finally` re-arms exactly ONE follow-on — one slot, so N nudges during one tick
    // still produce one tick after it.
    if (ticking) return;
    const { reason } = nudgePending;
    nudgePending = null;
    nudgedWith = reason;
    Promise.resolve(tick()).catch((err) => log('error', 'nudged tick failed', { error: err.message }));
  }

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  function getTickNumber() {
    if (tickNumber !== null) return tickNumber;
    const last = heartStore.getLastTick();
    return last ? last.tick : 0;
  }

  function setNextTickNumber() {
    tickNumber = getTickNumber() + 1;
    return tickNumber;
  }

  // Direct SQL helpers for gaps in the public heart-store API. All run on the
  // single writer connection held by heartStore.
  function runSql(sql, ...params) {
    const stmt = heartStore._prepare(sql);
    return stmt.run(...params);
  }

  function getSql(sql, ...params) {
    const stmt = heartStore._prepare(sql);
    return stmt.get(...params);
  }

  function allSql(sql, ...params) {
    const stmt = heartStore._prepare(sql);
    return stmt.all(...params);
  }

  function stampBroadcast(msgId, tick) {
    runSql('UPDATE messages SET broadcast_at_tick = ? WHERE msg_id = ?', tick, msgId);
  }

  function stampMessageRouted(msgId, tick) {
    runSql('UPDATE messages SET routed_at_tick = ? WHERE msg_id = ?', tick, msgId);
  }

  // Task 7.19 root fix (batch-08 item 10 part 1): a ticker-authored note to the
  // owner feed is informational — nothing routes it — so it is marked routed AT
  // WRITE. Left unstamped, every stall warning and crash note joins the
  // unrouted set permanently (74 of the 79 unrouted rows measured live were
  // these notes) and the per-tick scan grows monotonically. Every ticker-
  // authored owner-feed note MUST be written through this helper.
  function recordOwnerNote(corpus, now, tick) {
    const msg = heartStore.recordMessage({
      type: 'note',
      sender: 'ticker',
      thread: OWNER_NOTE_THREAD,
      corpus,
      createdAt: now,
    });
    stampMessageRouted(msg.msg_id, tick);
    return msg;
  }

  // Task 7.130 / M4-15 — built ONCE per ticker, not per tick, because its dedupe cache is the whole
  // reason it exists: a queued row stays due and is re-evaluated every tick, so a notifier rebuilt
  // each tick would announce the same held start every tick interval until that execution ended.
  // The deliverer is the owner feed — no credential, nothing leaves the box.
  const notifyQueuedStart = createQueuedStartNotifier({ deliver: ownerFeedDeliverer(recordOwnerNote) });

  function updateArgs(execId, argsJson) {
    runSql('UPDATE jobs_log SET args = ? WHERE exec_id = ?', argsJson, execId);
  }

  // Thread / chain helpers
  function rootExecId(execId) {
    const row = getSql(`
      WITH RECURSIVE chain(exec_id, parent_exec_id) AS (
        SELECT exec_id, parent_exec_id FROM jobs_log WHERE exec_id = ?
        UNION ALL
        SELECT j.exec_id, j.parent_exec_id
          FROM jobs_log j JOIN chain c ON j.exec_id = c.parent_exec_id
      )
      SELECT exec_id FROM chain WHERE parent_exec_id IS NULL LIMIT 1
    `, execId);
    return row ? row.exec_id : execId;
  }

  function chainThread(execId) {
    const root = rootExecId(execId);
    return root ? `exec-${root}` : null;
  }

  function chainExecIds(execId) {
    const root = rootExecId(execId);
    return allSql(`
      WITH RECURSIVE descendants(exec_id) AS (
        SELECT exec_id FROM jobs_log WHERE exec_id = ?
        UNION ALL
        SELECT j.exec_id FROM jobs_log j JOIN descendants d ON j.parent_exec_id = d.exec_id
      )
      SELECT exec_id FROM descendants ORDER BY exec_id
    `, root).map(r => r.exec_id);
  }

  // Delegates to the store's ONE determination of chain-total recycle
  // consumption — read by the blocked-slot gate and the warning check.
  // (p7-multiturn: the sender-triggered recycle/wake paths are UNGATED per the
  // owner's budget ruling; the AUTOMATIC budget is the separate
  // countAutomaticChainRecycles determination, consulted at compaction.)
  function countRecycles(execId) {
    return heartStore.countChainRecycles({ execId });
  }

  function countAutomaticRecycles(execId) {
    return heartStore.countAutomaticChainRecycles({ execId, markerKeys: AUTOMATIC_MARKER_KEYS });
  }

  // ── Task 7.46 · TWO readers, because there are two questions and they were never the same one.
  //
  // Before the split there was one function reading turn status, and the crash sweep (is the
  // PROCESS there?) and the agent cap (how many SESSIONS are running?) both asked their
  // session-level question of it. That is the inference the split exists to remove.
  //
  // They return the SAME SET today and must: every session the daemon spawns is a session with
  // exactly one turn (R16), so 1:1 holds and behaviour is unchanged — that degeneracy is what
  // keeps the existing ticker probes green. What changed is that the two answers now come from
  // two places, so when a session outlives its turn they diverge correctly instead of one
  // silently standing in for the other.

  // TURN level — is the WORK in flight? Reads jobs_log.status.
  function liveTurns() {
    return heartStore.listExecutionsByStatus('running')
      .concat(heartStore.listExecutionsByStatus('launching'));
  }

  // SESSION level — is the PROCESS there? Membership is decided by `sessions.status = 'alive'` and
  // by nothing else; the rows come back as TURN rows only because the carrier is keyed by exec_id
  // and the sweep needs pid / unit_name / log_path off them.
  function liveSessionTurns() {
    return heartStore.listTurnsOfLiveSessions();
  }

  // 7.46 · the ticker's own terminal writes end BOTH levels, explicitly and in that order.
  //
  // These are the paths where the ticker itself knows the process is over — a launch that threw, an
  // empty argv, a send-message that needed no process at all. The turn ends AND the session ends,
  // and both are written; nothing is inferred from the other. (The agent paths do not come through
  // here: a real agent's turn ends with a completion message, which the store handles.)
  //
  // Without this the session would stay `alive` forever and the agent cap would count ghosts — the
  // failure mode of adding a level and only remembering to close one of them.
  //
  // ⚠ G-225 — THE TWO WRITES ARE ONE STORE CALL, NOT TWO STATEMENTS. They used to be
  // `updateExecutionStatus()` followed by `closeSession()` with nothing around them, so a failure
  // or a daemon death BETWEEN them left a TERMINAL TURN UNDER AN `alive` SESSION. On the `:702`
  // send-message path that terminal turn is a `done` — the direction that destroys a real outcome
  // rather than merely adding noise, and the exact state `G-222`'s sweep used to overwrite.
  // `endTurnAndCloseSession()` lands both or neither.
  //
  // The `done ? closed : crashed` mapping is UNCHANGED and stays HERE rather than moving into the
  // store: it disagrees with the store's own `sessionStatusForEndedTurn()` on `blocked` (that one
  // maps `blocked`->`closed`), the disagreement predates this and is filed, and resolving it is a
  // behaviour change that must not ride in on an atomicity fix. No status reaching this function
  // today is `blocked` — the callers below pass `failed` and `done` only.
  function endTurnAndSession(execId, { status, endedAt, reason }) {
    const { exec } = heartStore.endTurnAndCloseSession(execId, {
      turnStatus: status,
      sessionStatus: status === 'done' ? 'closed' : 'crashed',
      endedAt,
      reason,
    });
    return exec;
  }

  // A turn can now reach a set from two directions (its session is alive AND its own status is
  // `stalled`). Sweeping it twice would record two completions for one exit, so the union is
  // deduped by exec_id rather than left to the caller to remember.
  function dedupeByExecId(rows) {
    const seen = new Set();
    const out = [];
    for (const r of rows) {
      if (seen.has(r.exec_id)) continue;
      seen.add(r.exec_id);
      out.push(r);
    }
    return out;
  }

  function findLiveExecutionForThread(thread) {
    for (const row of liveTurns()) {
      if (row.thread === thread) return row;
    }
    return null;
  }

  function hasMessagesSinceStart(execRow) {
    const thread = execRow.thread;
    if (!thread) return false;
    const startedAt = execRow.started_at || execRow.fired_at;
    if (!startedAt) return false;
    const rows = allSql(
      "SELECT 1 FROM messages WHERE thread = ? AND sender != 'ticker' AND created_at >= ? LIMIT 1",
      thread, startedAt
    );
    return rows.length > 0;
  }

  function hasPendingInput(execRow, completionMsgId) {
    const thread = execRow.thread;
    if (!thread) return false;
    const startedAt = execRow.started_at || execRow.fired_at;
    if (!startedAt) return false;
    const rows = allSql(
      "SELECT created_at FROM messages WHERE thread = ? AND sender != 'ticker' AND msg_id != ? ORDER BY created_at",
      thread, completionMsgId
    );
    for (const m of rows) {
      if (m.created_at >= startedAt) return true;
    }
    return false;
  }

  function hasNewInputSinceBlock(execRow) {
    const thread = execRow.thread;
    const watermark = execRow.completion_msg_id;
    if (!thread || !watermark) return false;
    const rows = allSql(
      'SELECT 1 FROM messages WHERE thread = ? AND msg_id > ? LIMIT 1',
      thread, watermark
    );
    return rows.length > 0;
  }

  // Wake test for a FINISHED (done) chain tail: a non-ticker, non-completion
  // message row newer than the turn's own completion. Ticker rows never wake a
  // seat (D39 — owner notes live on the feed, and a chain thread's only ticker
  // rows are its completions); completions are lifecycle, not input.
  function hasNewSenderInputSinceEnd(execRow) {
    const thread = execRow.thread;
    const watermark = execRow.completion_msg_id;
    if (!thread || !watermark) return false;
    const rows = allSql(
      "SELECT 1 FROM messages WHERE thread = ? AND msg_id > ? AND sender != 'ticker' AND type != 'completion' LIMIT 1",
      thread, watermark
    );
    return rows.length > 0;
  }

  function isSlotLiveOrRearmed(blockedExec) {
    if (findLiveExecutionForThread(blockedExec.thread)) return true;
    for (const row of heartStore.listQueue()) {
      const args = safeJsonParse(row.args, {});
      if (args[CHAIN_MARKER] === blockedExec.exec_id) return true;
    }
    return false;
  }

  function findExecForCompletion(msg) {
    if (!msg.thread || !msg.thread.startsWith('exec-')) return null;
    const rootId = parseInt(msg.thread.slice(5), 10);
    if (!Number.isInteger(rootId)) return null;

    const chainIds = chainExecIds(rootId);
    // Prefer the live execution in the chain.
    for (const id of chainIds) {
      const row = heartStore.getExecution(id);
      if (row && (row.status === 'running' || row.status === 'launching')) return row;
    }
    // Otherwise the most recent terminal execution (duplicate / late report).
    for (let i = chainIds.length - 1; i >= 0; i--) {
      const row = heartStore.getExecution(chainIds[i]);
      if (row && ['done', 'blocked', 'failed', 'stalled'].includes(row.status)) return row;
    }
    return null;
  }

  // Queue helpers
  function insertQueueRow({ jobId, args, sessionMode, triggerKind, runAt, enqueuedBy, parentExecId, autoRedispatch = false }) {
    const argsObj = typeof args === 'string' ? safeJsonParse(args, {}) : (args || {});
    // A re-dispatched turn is ALWAYS an answering turn: a compaction turn is
    // only ever minted at fire time (launchAgent). Stripping the markers here
    // keeps stale automatic marks from riding a sender-triggered re-dispatch;
    // only the compaction-recycle insert re-marks (autoRedispatch), so the
    // budget can tell the two apart.
    delete argsObj[COMPACT_MARKER];
    delete argsObj[AUTO_MARKER];
    if (autoRedispatch) argsObj[AUTO_MARKER] = true;
    argsObj[CHAIN_MARKER] = parentExecId;
    const argsJson = JSON.stringify(argsObj);
    const enqueuedAt = isoNow();
    // Task 7.389 — the enqueuing SEAT is INHERITED from the parent turn, derived HERE rather than
    // threaded through each of the four callers. Every one of them is a RECYCLE of `exec` (they
    // pass `parentExecId: exec.exec_id` beside `enqueuedBy: exec.enqueued_by`), and the recycled
    // turn is the same seat's work continuing — so the parent row already holds the answer and a
    // per-caller argument would be the same fact copied four times, free to drift three ways.
    // A chain root or a store predating the column yields NULL, which grants nothing.
    const parent = parentExecId != null ? heartStore.getExecution(parentExecId) : null;
    const enqueuingSeat = parent && parent.enqueuing_seat ? parent.enqueuing_seat : null;
    const result = runSql(`
      INSERT INTO queue (job_id, args, session_mode, trigger_kind, run_at, enqueued_by, enqueuing_seat, enqueued_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `, jobId, argsJson, sessionMode, triggerKind, runAt, enqueuedBy, enqueuingSeat, enqueuedAt);
    return Number(result.lastInsertRowid);
  }

  function extractChainMarker(queueRow) {
    const args = safeJsonParse(queueRow.args, {});
    const parentExecId = args[CHAIN_MARKER];
    if (parentExecId !== undefined) {
      delete args[CHAIN_MARKER];
      return { parentExecId, cleanedArgs: JSON.stringify(args) };
    }
    return { parentExecId: null, cleanedArgs: queueRow.args };
  }

  // The chain's conversation transcript, derived from the store at spawn time
  // and never stored back into args ("ready is computed, never stored" applied
  // to conversation history): the root turn's original prompt, then every
  // thread row in msg_id order — chain executions' `done` completions as
  // assistant items (their corpus is the turn's extracted answer; a compaction
  // turn's is its summary), every non-ticker row as owner input.
  //
  // Compaction geometry (the chain's SHORT-TERM memory — long-term memory
  // across conversations is a separate, undefined process): a summary covers
  // the dialogue up to its BOUNDARY — the completion of the compaction exec's
  // parent — because the compaction transcript is cut there: pending owner
  // replies stay OUT of the summary and appear verbatim in the answering
  // turn's prompt. Composition with a summary = the newest summary + every
  // non-summary item past its boundary. (Known degradation: two consecutive
  // compactions with no turn between them fold the pending replies into the
  // second summary — bounded by the recycle budget, surfaced not hidden.)
  //
  // `upToMsgId` cuts the tail for a COMPACTION turn's own prompt: it
  // summarizes completed dialogue only (items at or below the parent turn's
  // completion), never the pending replies.
  function composeChainTranscript(parentExecId, { upToMsgId = null } = {}) {
    const root = rootExecId(parentExecId);
    const thread = `exec-${root}`;
    const completionExecs = new Map();
    const execsById = new Map();
    for (const id of chainExecIds(parentExecId)) {
      const e = heartStore.getExecution(id);
      if (!e) continue;
      execsById.set(e.exec_id, e);
      if (e.completion_msg_id) completionExecs.set(e.completion_msg_id, e);
    }
    let summary = null; // newest compaction summary: { msgId, boundary }
    for (const e of execsById.values()) {
      if (!e.completion_msg_id || safeJsonParse(e.args, {})[COMPACT_MARKER] !== true) continue;
      if (!summary || e.completion_msg_id > summary.msgId) {
        const parent = e.parent_exec_id ? execsById.get(e.parent_exec_id) : null;
        summary = { msgId: e.completion_msg_id, boundary: (parent && parent.completion_msg_id) || 0 };
      }
    }
    const items = [];
    for (const m of allSql('SELECT msg_id, type, sender, corpus, status FROM messages WHERE thread = ? ORDER BY msg_id', thread)) {
      const ce = completionExecs.get(m.msg_id);
      if (ce) {
        if (m.status !== 'done') continue; // failed/blocked lifecycle rows are not dialogue
        items.push({ msgId: m.msg_id, text: m.corpus, isCompact: safeJsonParse(ce.args, {})[COMPACT_MARKER] === true });
      } else if (m.type !== 'completion' && m.sender !== 'ticker') {
        items.push({ msgId: m.msg_id, text: m.corpus, owner: true });
      }
    }
    const effective = [];
    if (summary && (upToMsgId === null || summary.msgId <= upToMsgId)) {
      const summaryItem = items.find((i) => i.msgId === summary.msgId);
      if (summaryItem) effective.push({ label: 'summary of earlier conversation', text: summaryItem.text });
      for (const i of items) {
        if (i.msgId <= summary.boundary || i.isCompact) continue;
        if (upToMsgId !== null && i.msgId > upToMsgId) continue;
        effective.push({ label: i.owner ? 'owner' : 'assistant', text: i.text });
      }
    } else {
      const rootRow = execsById.get(root) || heartStore.getExecution(root);
      const rootPrompt = safeJsonParse(rootRow ? rootRow.args : null, {}).prompt;
      if (rootPrompt) effective.push({ label: 'owner', text: rootPrompt });
      for (const i of items) {
        if (i.isCompact) continue;
        if (upToMsgId !== null && i.msgId > upToMsgId) continue;
        effective.push({ label: i.owner ? 'owner' : 'assistant', text: i.text });
      }
    }
    return effective.map((i) => `[${i.label}] ${i.text}`).join('\n\n');
  }

  // The owner's NEW message(s) since the predecessor turn ended — the same rows
  // composeChainTranscript appends at the end of a chained prompt, selected by the same predicate
  // the wake test uses (`hasNewSenderInputSinceEnd`): thread rows past the predecessor's own
  // completion, no ticker rows, no completions. This IS the whole prompt of a RESUMED turn
  // (r-chat-chain-resumes-session): the conversation is already in the session, so re-sending it
  // is the cost the ruling removes. Several queued messages join blank-line separated, in
  // msg_id order — the same order and the same text the transcript path would have shown.
  function composeNewSenderMessages(parentExecRow) {
    if (!parentExecRow || !parentExecRow.thread || !parentExecRow.completion_msg_id) return '';
    return allSql(
      "SELECT corpus FROM messages WHERE thread = ? AND msg_id > ? AND sender != 'ticker' AND type != 'completion' ORDER BY msg_id",
      parentExecRow.thread, parentExecRow.completion_msg_id,
    ).map((r) => r.corpus).join('\n\n');
  }

  // ── Task 7.12 · where a job's action RUNS (owner ruling `r-job-seat-home`, 2026-07-27) ────────
  //
  // "A job's action is always homed as a SEAT in a goal; the job itself is only the trigger." A
  // catalogue row carrying `goal_name`/`seat_name` launches into that seat's folder.
  //
  // ⚠ THE INTERIM `<ws>/.rbtv/sessions/<exec-id>/` BRANCH IS RETIRED (`r-seats-only-architecture`
  // (3), completing `r-711-staged-retirement` / `G-122`): a row WITHOUT goal/seat no longer falls
  // through to a flat dir. Either the queue args name a home (a workdir, judged by the spawn door's
  // own seat-folder gate), or the dispatch is REFUSED here, naming the missing fields. A job-born
  // seat whose folder does not yet exist is auto-materialized to the minimal valid shape by
  // resolveSeatHome (folder + generated seat.md), so the cage's ro-bind of seat.md has a target.
  //
  // ⚠ A FAILURE HERE IS LOUD AND NEVER A FALLBACK. If a row says it is homed and the seat cannot
  // be resolved, this THROWS — there is no interim path left to quietly launch into. A silent
  // fallback would undo the homing at the one moment nobody is watching, and would look identical
  // in the log to a job that was never homed at all. Thrown inside the caller's existing try, so it
  // lands as `spawn-failed` against a REAL `jobs_log` row with the reason attached, rather than as
  // a `defer` that retries every tick forever (the `unknown-tool` shape task 7.70 exists to fix).
  function resolveJobHome(queueRow, argsWorkdir) {
    const job = heartStore.getJob(queueRow.job_id);
    if (!job || !job.goal_name || !job.seat_name) {
      // Not homed by the catalogue row. A caller-named workdir is still a home candidate — the
      // spawn door verifies it is a canonical seat folder and refuses anything else. NO workdir
      // at all is a seatless dispatch, refused (r-seats-only-architecture: "a dispatch with no
      // home is a refusal, not a flat dir").
      if (argsWorkdir) return argsWorkdir;
      const jobId = (job && job.job_id) || queueRow.job_id || '(row-less dispatch)';
      throw new Error(
        `REFUSING SEATLESS DISPATCH: job "${jobId}" names no home — MISSING FIELDS: goal_name/seat_name `
        + '(jobs table) and no workdir in the queue args. The flat .rbtv/sessions/<exec-id>/ launch '
        + 'branch is RETIRED (r-seats-only-architecture); home the job at a (goal, seat) pair.',
      );
    }
    if (argsWorkdir) {
      // The catalogue row and the enqueue disagree about where this runs. Refused, not ranked:
      // preferring either one silently would let an enqueue-time argument move a job out of the
      // seat its DEFINITION assigns it — an asserted value outranking a declared one, which is
      // G-111 exactly.
      throw new Error(
        `job "${job.job_id}" is homed at ${job.goal_name}/${job.seat_name} but the queue row also `
        + `supplies workdir "${argsWorkdir}" — refusing rather than choosing between them`,
      );
    }
    const workspaceRoot = resolveWorkspaceRoot(heartStore.dbPath);
    if (!workspaceRoot) {
      throw new Error(
        `job "${job.job_id}" is homed at ${job.goal_name}/${job.seat_name} but no workspace root is `
        + 'resolvable from the heart store path',
      );
    }
    // r-seats-only-architecture: `materialize` makes a first-fire job-born seat's folder exist
    // (minimal shape: folder + generated seat.md naming seat/goal/spawning-job) instead of
    // refusing it as un-materialized. Descriptor agreement is still enforced inside.
    const home = resolveSeatHome({ workspaceRoot, goal: job.goal_name, seat: job.seat_name, materialize: { jobId: job.job_id } });
    if (!home.ok) {
      throw new Error(
        `job "${job.job_id}" is homed at ${job.goal_name}/${job.seat_name} but that seat cannot be `
        + `resolved: ${home.reason}`,
      );
    }
    return home.seatDir;
  }

  // Launch helpers
  async function launchAgent(queueRow, actions, tick, now) {
    const { parentExecId, cleanedArgs } = extractChainMarker(queueRow);
    const args = safeJsonParse(cleanedArgs, {});
    const prompt = args.prompt ?? null;
    const workdir = args.workdir ?? null;
    // The reasoning RUNG this row asks for (owner ruling `d-0811lp-effort-lane-build-now`,
    // 2026-08-11). Read here and passed straight through — the ticker validates nothing about it:
    // the enqueue door already type-checked it against the job's `args_schema`, and WHAT a rung
    // MEANS is the profile's ladder, read once in `resolveEffort`. Absent ⇒ harness default, which
    // is every row enqueued before this lane existed.
    const effort = args.effort ?? null;

    if (parentExecId) {
      const thread = chainThread(parentExecId);
      const live = findLiveExecutionForThread(thread);
      if (live) {
        actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'slot-live-session', thread });
        return;
      }
    }

    // 7.46: the cap counts live SESSIONS — it always did, in its own name; it just had to read
    // turn status to get the number. Now it reads the session table.
    //
    // D25 (2026-08-20): cap is 14 + 1 reserved interactive slot. Chat-bridge owner summons
    // (`enqueued_by = chat-bridge-slack`, job `chat-agent*`) may use the +1 when the 14 are
    // full; non-interactive rows never touch it. A second interactive past the +1 still
    // defers `global-cap`. Reserved admission is a tick action so the log names it.
    const liveAgentSessions = liveSessionTurns().filter(r => r.action_type === 'launch-agent').length;
    const cap = cfg.max_live_agent_sessions;
    if (liveAgentSessions >= cap) {
      const job = heartStore.getJob(queueRow.job_id);
      const interactive = isReservedInteractiveRow(queueRow, job);
      const reservedCeiling = cap + RESERVED_INTERACTIVE_SLOTS;
      if (interactive && liveAgentSessions < reservedCeiling) {
        actions.push({
          phase: 'dispatch',
          action: 'admit',
          queueId: queueRow.queue_id,
          reason: 'reserved-interactive-slot',
          live: liveAgentSessions,
          cap,
        });
      } else {
        actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'global-cap' });
        return;
      }
    }

    // ── THE SEAT-BUSY GATE — what makes `on_seat_busy: 'queue'` safe ──────────────────────────
    //
    // The Q9 idempotent door used to be the ONLY thing standing between two enqueues of one seat,
    // and it stood there by DROPPING the second one. A caller that must not lose its payload (a
    // chat message typed while the seat is mid-turn) now opts out with `on_seat_busy: 'queue'` and
    // gets a real row — which means several pending rows can address one seat, and something has
    // to serialize them. This is that something.
    //
    // It asks the DOOR'S OWN question, through the door's own key and the door's own lookup, so
    // "busy" can never mean one thing at the enqueue and another at the launch. `excludeQueueId`
    // is this row itself: it is pending, so it matches its own key, and without the exclusion every
    // row would defer behind itself forever. The remaining ordering falls out of `getQueueDue`'s
    // `(run_at, queue_id)` — the oldest row is the one no older row holds the seat against, so it
    // fires and its siblings wait.
    //
    // `return` leaves the row DUE and UNTOUCHED (`fireQueueRow` is not reached), exactly like the
    // pause and one-live-run gates above.
    const seatKey = seatKeyOf(heartStore.getJob(queueRow.job_id), args);
    if (seatKey) {
      // `pendingAheadOf` is THIS row: a pending sibling holds the seat against me only if it
      // dispatches BEFORE me. Without it two pending rows for one seat each see the other and both
      // defer forever — see findSeatHolder's header for the measurement.
      const holder = heartStore.findSeatHolder(seatKey, { excludeQueueId: queueRow.queue_id, pendingAheadOf: queueRow });
      if (holder) {
        // ── THE AGE BOUND. An hour-old chat message must NOT fire as if it were fresh — by then
        // the conversation has moved and the owner has usually asked again. Removed, never
        // silently: the owner note is the whole point, because what is being discarded is
        // something a human said.
        //
        // ⚠ MEASURED FROM `run_at`, NOT `enqueued_at`. A recurring row keeps its ORIGINAL
        // `enqueued_at` for the life of the row while `fireQueueRow` advances `run_at` on every
        // fire — so an `enqueued_at` clock would read a week-old periodic row as a week stale and
        // DELETE it on its first seat-busy defer. `run_at` is the clock that means "how long has
        // this row been due and unable to fire", which is the question being asked.
        //
        // ⚠ AND ONE-SHOT ROWS ONLY. Removal is permanent — there is no next fire to recover on —
        // so a RECURRING row is never dropped here no matter how long it waits. It is not stale
        // news; its whole contract is that it comes back. It defers, like any other busy row.
        const recurring = queueRow.interval_seconds != null || queueRow.repeat_rule != null;
        const runAt = Date.parse(queueRow.run_at);
        const ageS = Number.isNaN(runAt) ? 0 : (now.getTime() - runAt) / 1000;
        if (!recurring && cfg.seat_queue_max_age_s > 0 && ageS > cfg.seat_queue_max_age_s) {
          heartStore.removeQueueRow({ queueId: queueRow.queue_id });
          recordOwnerNote(
            `queued request DROPPED: queue row ${queueRow.queue_id} waited ${Math.round(ageS)}s for `
            + `seat ${seatKey} (held by ${holder.because}), past the ${cfg.seat_queue_max_age_s}s bound. `
            + `It was not run.`,
            now, tick,
          );
          actions.push({ phase: 'dispatch', action: 'seat-queue-expired', queueId: queueRow.queue_id, seatKey, ageS: Math.round(ageS) });
          return;
        }
        actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'seat-busy', seatKey });
        return;
      }
    }

    const exec = heartStore.fireQueueRow({ queueId: queueRow.queue_id, now, tick, parentExecId });
    if (!exec) {
      actions.push({ phase: 'dispatch', action: 'noop', queueId: queueRow.queue_id, reason: 'fire-failed' });
      return;
    }

    // A chained turn's prompt is the CONVERSATION, never the original args
    // verbatim (which would re-ask the FIRST question). Over the compaction
    // bound this turn becomes a COMPACTION turn instead: it summarizes the
    // transcript, and Advance re-dispatches the displaced answering turn once
    // the summary lands (linear chain: the answering turn's parent = this
    // exec). The persisted args stay the original job args — plus the
    // COMPACT_MARKER when this exec is a compaction turn, the one derived
    // fact Advance and composition must see.
    let spawnPrompt = prompt;
    let compactTurn = false;
    // ── r-chat-chain-resumes-session (owner, 2026-08-07) ─────────────────────────────────────
    // A chained turn RESUMES the predecessor's harness session and carries only the new
    // message(s); transcript-embed respawn is the FALLBACK. `resumeRef` non-null selects it, and
    // `chainPath` records WHICH path ran and WHY, per launch, in the tick log.
    let resumeRef = null;
    let chainPath = null;   // 'resume' | 'transcript' — null on a first (unchained) execution
    let chainReason = null;
    if (parentExecId) {
      const transcript = composeChainTranscript(parentExecId);
      if (transcript.length > cfg.history_compact_chars) {
        // The compaction turn summarizes COMPLETED dialogue only: cut at the
        // parent turn's completion so the pending owner replies stay out of
        // the summary and reach the answering turn verbatim.
        const parentRow = heartStore.getExecution(parentExecId);
        const cutoff = (parentRow && parentRow.completion_msg_id) || null;
        spawnPrompt = COMPACT_PROMPT_HEADER + composeChainTranscript(parentExecId, { upToMsgId: cutoff });
        compactTurn = true;
        // A compaction turn's INPUT *is* the transcript — never resumed (the ruling says so).
        chainPath = 'transcript';
        chainReason = 'compaction-turn';
        updateArgs(exec.exec_id, JSON.stringify({ ...args, [COMPACT_MARKER]: true }));
      } else {
        spawnPrompt = CONTINUE_PROMPT_HEADER + transcript + CONTINUE_PROMPT_FOOTER;
        const parentRow = heartStore.getExecution(parentExecId);
        // The seat's OWN launch spec — the same one `spawn()` will resolve, keyed by the cast in
        // its descriptor (7.787). It used to be `config.profiles[args.profile]`, the caller's
        // named profile, which ruling D19 had already stopped being what launches: a chain could
        // decide "resumable" off one spec and then resume against another. `homedWorkdir` is
        // resolved here rather than inside the attempt loop for exactly that reason — the seat
        // folder is the spec's only address.
        let profile = null;
        try { profile = spawnManager.specForSeat(resolveJobHome(queueRow, workdir)); } catch { profile = null; }
        const newMessages = composeNewSenderMessages(parentRow);
        // Every condition is a REASON, so a fallback in the journal names what was missing rather
        // than only that it fell back. `parent-compaction`: the predecessor is a compaction turn,
        // whose session only ever saw a summarize instruction — resuming THAT session would
        // continue the summarizer, not the conversation, and would throw away the summary splice
        // this branch's transcript composition performs correctly.
        const why = !parentRow ? 'no-parent-row'
          : !parentRow.session_ref ? 'no-session-ref'
          : !(profile && profile.resume) ? 'no-resume-template'
          : safeJsonParse(parentRow.args, {})[COMPACT_MARKER] === true ? 'parent-compaction'
          : !newMessages ? 'no-new-messages'
          : null;
        if (why === null) {
          resumeRef = parentRow.session_ref;
          spawnPrompt = newMessages;
          chainPath = 'resume';
          chainReason = 'predecessor-session-resumable';
        } else {
          chainPath = 'transcript';
          chainReason = why;
        }
        updateArgs(exec.exec_id, cleanedArgs);
      }
    }

    // A resume that fails AT THE CARRIER retries ONCE as the fallback it displaced — the fresh
    // transcript spawn that would have run had the ref been absent. Without it a chat chain dies
    // on a stale/purged harness session (`--resume <gone>` exits non-zero), and dies in the state
    // nothing re-dispatches: a `failed` tail is owner-halted, so the NEXT owner message wakes
    // nothing. One retry, then the normal spawn-failed path.
    // ponytail: covers the CARRIER-level failure only. A resume that launches and then dies is
    // swept `failed` like any crash and halts the chain — same as today's behaviour for any
    // crashed turn. Upgrade path if that turns out to bite: on the crash sweep, re-dispatch a
    // chain whose failed turn carried a resumeRef, once.
    const attempts = resumeRef
      ? [{ ref: resumeRef, prompt: spawnPrompt, path: 'resume', reason: chainReason },
         { ref: null, prompt: CONTINUE_PROMPT_HEADER + composeChainTranscript(parentExecId) + CONTINUE_PROMPT_FOOTER,
           path: 'transcript', reason: 'resume-spawn-failed' }]
      : [{ ref: null, prompt: spawnPrompt, path: chainPath, reason: chainReason }];

    for (let i = 0; i < attempts.length; i++) {
      const attempt = attempts[i];
      try {
        // Task 7.12 — resolved INSIDE the try so a homed job whose seat cannot be resolved fails
        // loud against this exec's own jobs_log row (see resolveJobHome above).
        const homedWorkdir = resolveJobHome(queueRow, workdir);
        await spawnManager.spawn(exec.exec_id, queueRow.session_mode, attempt.prompt, homedWorkdir, queueRow.enqueued_by, attempt.ref, effort);
        const spawnAction = { phase: 'dispatch', action: 'spawn', execId: exec.exec_id, queueId: queueRow.queue_id, thread: exec.thread };
        if (effort !== null) spawnAction.effort = effort;
        if (homedWorkdir !== workdir) spawnAction.homed = homedWorkdir;
        if (compactTurn) spawnAction.compact = true;
        if (attempt.path) { spawnAction.chain = attempt.path; spawnAction.chainReason = attempt.reason; }
        actions.push(spawnAction);
        return;
      } catch (err) {
        const last = i === attempts.length - 1;
        actions.push({
          phase: 'dispatch',
          action: last ? 'spawn-failed' : 'resume-spawn-failed',
          execId: exec.exec_id,
          chain: attempt.path,
          error: err.message,
        });
      }
    }
  }

  function ensureLogPath(dataRoot, sessionId) {
    const logDir = path.join(dataRoot, 'logs');
    fs.mkdirSync(logDir, { recursive: true, mode: 0o700 });
    const logPath = path.join(logDir, `${sessionId}.log`);
    // Pre-create 0600 so the tool-execution log is never born with the systemd
    // append: default mode (664 observed live) — same fix as the agent-session
    // transcript in spawn.js ensureLogPath (task 7.13 piece 4; applied here as
    // a conductor extension riding task 7.19). An existing file keeps its
    // mode; appendFileSync never truncates.
    fs.appendFileSync(logPath, '', { mode: 0o600 });
    return logPath;
  }

  function carrierConfig() {
    return {
      carrier: spawnManager.config.spawn.carrier || 'auto',
      dataRoot: spawnManager.config.spawn.data_root,
      defaultWorkdir: spawnManager.config.default_workdir_root,
      userManager: true,
    };
  }

  async function runToolLikeExec(exec, argv, workdir, actions, actionName) {
    const cc = carrierConfig();
    const sessionId = generateSessionId();
    const logPath = ensureLogPath(cc.dataRoot, sessionId);

    heartStore.updateExecutionStatus(exec.exec_id, {
      status: 'launching',
      sessionId,
      logPath,
    });

    const carrier = selectCarrier(cc.carrier, cc.userManager);
    const common = {
      sessionId,
      argv,
      workdir,
      logPath,
      // Tool-like execs sweep by the same exit marker as agent sessions, so a
      // clean tool exit records `done` (they had no other exit observation:
      // the carrier returns no child handle, so the exit listener below never
      // fires for detached runs).
      exitFile: ensureExitFile(cc.dataRoot, sessionId),
      caps: {},
      sandbox: {},
      envFile: null,
      // F1 (owner ruling `d-owner-f1-carrier-env-0808`) — the fired tool gets an environment in
      // which the RULED BARE TOOL NAMES RESOLVE. Without this a `systemd-run --user` child inherits
      // the MANAGER's PATH, which carries no `~/.local/bin`, so `scaffold-seats` exited 127 and
      // goal creation refused after having already scaffolded the goal — one orphan per fire, and
      // no retry could complete it (C5E review, F1).
      //
      // ⚠ THIS LINE FIXES THE WHOLE CLASS, which is why it is here and not at a call site: BOTH
      // `fire-tool` (launchFireTool) and `start-workflow` route through this one function, so every
      // present and future fired tool is covered by one composition. `envFile` stays null — that is
      // the CREDENTIAL channel and this is not a credential (carrier.js `toolExecEnv`).
      setenv: toolExecEnv(),
      userManager: cc.userManager,
    };

    try {
      let launchResult;
      if (carrier === 'systemd') {
        launchResult = await spawnSystemd(common, log);
      } else {
        launchResult = await spawnSetsid(common, log);
      }
      const pid = launchResult.pid || null;
      const unitName = launchResult.unitName || null;
      heartStore.updateExecutionStatus(exec.exec_id, {
        status: 'running',
        carrier,
        unitName,
        pid,
        logPath,
        sessionId,
        startedAt: new Date(),
      });
      actions.push({ phase: 'dispatch', action: actionName, execId: exec.exec_id });

      // Best-effort immediate completion recording on exit.
      const child = launchResult.proc || null;
      if (child && typeof child.on === 'function') {
        child.on('exit', (code) => {
          recordToolCompletion(exec.exec_id, code, logPath);
        });
      }
    } catch (err) {
      endTurnAndSession(exec.exec_id, { status: 'failed', endedAt: new Date(), reason: `launch threw (${actionName})` });
      actions.push({ phase: 'dispatch', action: `${actionName}-failed`, execId: exec.exec_id, error: err.message });
    }
  }

  function recordToolCompletion(execId, exitCode, logPath) {
    const exec = heartStore.getExecution(execId);
    if (!exec || ['done', 'blocked', 'failed', 'stalled'].includes(exec.status)) return;
    const tail = tailBytes(logPath, 4096);
    const corpus = `tool exit: ${exitCode}\n--- output tail ---\n${tail}`;
    const status = exitCode === 0 ? 'done' : 'failed';
    // Task 7.7: the store stamps jobs_log (status, completion_msg_id, ended_at,
    // exit_code) atomically with this INSERT — execId pins the tool's own row.
    // Advance still owns the ROUTING stamp (routed_at_tick) at its next tick.
    heartStore.recordMessage({
      type: 'completion',
      sender: 'ticker',
      thread: exec.thread || `exec-${execId}`,
      corpus,
      status,
      createdAt: new Date(),
      execId,
      exitCode,
    });
  }

  async function launchFireTool(queueRow, actions, tick, now) {
    const args = safeJsonParse(queueRow.args, {});
    const toolName = args.tool;
    const tool = Object.hasOwn(heartStore.config.tools || {}, toolName) ? heartStore.config.tools[toolName] : undefined;
    if (!tool) {
      actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'unknown-tool' });
      return;
    }

    const exec = heartStore.fireQueueRow({ queueId: queueRow.queue_id, now, tick });
    if (!exec) {
      actions.push({ phase: 'dispatch', action: 'noop', queueId: queueRow.queue_id, reason: 'fire-failed' });
      return;
    }

    const cc = carrierConfig();
    const workdir = args.workdir || cc.defaultWorkdir;

    // ── Task 7.562 · GOVERN THE CALLER-SUPPLIED WORKDIR. This is the BOUNDARY half (the enqueue
    // door in `heart-store.js` validateArgs is the UX half; the store on disk outlives this code
    // and rows predating that door are still fireable). The rule and the whole measurement live in
    // `heart/argv-template.js` above `checkFireToolWorkdir` — not restated here.
    //
    // ⚠ IT NARROWS, IT DOES NOT CLOSE. cwd is not a security boundary: this exec still runs with
    // the daemon user's full ambient authority. What it stops is a scheduled job being POINTED AT
    // A FOLDER THAT REDIRECTS ITS CREDENTIALS — `cli/lib/config.js` resolveToken walks UP from cwd
    // and the first `.rbtv/config/sender-token.env` wins, so a chosen cwd substitutes the sender
    // token of a job whose whole purpose is to call back through the door. It is not a
    // sandbox and must never be described as one.
    //
    // RECORDED, NOT THROWN — the shape every other refusal on this path uses: `tick()` has a
    // `finally` and no `catch`, so a throw abandons the rest of the tick.
    const workdirRefusal = checkFireToolWorkdir(args, cc.defaultWorkdir);
    if (workdirRefusal) {
      endTurnAndSession(exec.exec_id, { status: 'failed', endedAt: new Date(), reason: `workdir refused (fire-tool): ${workdirRefusal}` });
      actions.push({ phase: 'dispatch', action: 'fire-tool-failed', execId: exec.exec_id, error: `workdir: ${workdirRefusal}` });
      return;
    }

    const argv = Array.isArray(tool.argv) ? tool.argv : (tool.command ? [tool.command] : []);
    if (argv.length === 0) {
      endTurnAndSession(exec.exec_id, { status: 'failed', endedAt: new Date(), reason: 'empty argv (fire-tool)' });
      actions.push({ phase: 'dispatch', action: 'fire-tool-failed', execId: exec.exec_id, error: 'empty argv' });
      return;
    }

    // ── Task 7.559 · PER-RUN ARGUMENT ON A FIRE-TOOL ENTRY, ADMITTED BY IDENTITY ─────────────────
    // (owner ruling `d-owner-7559-design-rulings-0808`; design `dossiers/7559-argv-allowlist-design.md`.)
    //
    // An entry may declare `args_allowlist: { <key>: [ …literal values… ] }` in the BOOT-READ
    // merged config, and ONLY there — ruling B1, the whole security condition, argued in
    // `heart/argv-template.js`'s header. A row then SELECTS a member; it never supplies a string.
    //
    // ⚠ THIS IS A SECURITY BOUNDARY, NOT A CONVENIENCE FILTER, and the reason is one line up:
    // `runToolLikeExec` passes literal `caps: {}` / `sandbox: {}`, so a fired tool runs with no
    // memory cap, no task cap, no runtime cap and no filesystem namespace, as the daemon user. The
    // bytes it is handed are the whole containment. `enqueue-job` carries NO authz gate (every
    // sender kind may enqueue, including the chat `bridge`, which relays other people's words), so
    // the value space of a per-run argument is the value space a chat participant can reach.
    //
    // FROZEN BY DEFAULT SURVIVES, and the shape carries it rather than a promise: an entry that
    // declares no `args_allowlist` falls through both branches to the SAME call this function has
    // always ended with, with `tool.argv` untouched — byte-identical argv, today's behaviour.
    const allow = (tool && tool.args_allowlist) || null;
    const templated = argv.some((t) => typeof t === 'string' && t.includes('{{'));
    if (!allow && templated) {
      // FAIL CLOSED. Without this arm an entry that templates a value but declares no allowlist
      // would exec the LITERAL token `{{goal}}` as an operand — a silent wrong-command fire, which
      // is worse than a refusal and reads as a success in the log.
      endTurnAndSession(exec.exec_id, { status: 'failed', endedAt: new Date(), reason: 'fire-tool entry templates a value but declares no args_allowlist' });
      actions.push({ phase: 'dispatch', action: 'fire-tool-failed', execId: exec.exec_id, error: 'argv-template: no args_allowlist on a templated entry' });
      return;
    }
    if (allow) {
      // A REFUSAL IS RECORDED, NOT THROWN — the same shape as launchStartWorkflow below, for the
      // same two reasons: `tick()` has a `finally` and no `catch`, so a throw abandons the rest of
      // the tick; and a DEFERRED row that can never compose re-fires every cadence forever.
      const composed = expandArgv(argv, args, allow);
      if (composed.refused) {
        endTurnAndSession(exec.exec_id, { status: 'failed', endedAt: new Date(), reason: `argv template refused (fire-tool): ${composed.refused}` });
        actions.push({ phase: 'dispatch', action: 'fire-tool-failed', execId: exec.exec_id, error: `argv-template: ${composed.refused}` });
        return;
      }
      await runToolLikeExec(exec, composed.argv, workdir, actions, 'fire-tool');
      return;
    }
    await runToolLikeExec(exec, argv, workdir, actions, 'fire-tool');
  }

  // ── Task C3 — the goal's channel, caused to exist at the goal's workflow start ────────────────
  //
  // The DOD's "created by the daemon at an interactive goal's workflow start … as a job" (§ Comm).
  // What crosses the process boundary is an INVOCATION of the bridge's own `goal-channel-cli.js
  // ensure`, because the bridge is a separate OS process that opens no inbound listener and holds
  // the only chat credential — `goal-channel-start.js`'s header carries the whole argument.
  //
  // ⚑ THE CREDENTIAL NEVER ENTERS THIS PROCESS. `RBTV_IGNITE_CHAT_ENV_FILE` is a PATH, and it is
  // handed to the carrier as `EnvironmentFile=` — systemd reads the file into the CHILD. The
  // daemon reads no token, logs none, and holds none, which is `goal-channel-design.md`'s bound
  // kept mechanically rather than by care. UNSET is not an error and not a silent no-op either:
  // the ensure is recorded as skipped with that reason, because a deployment with no chat env
  // configured has no bridge either, and spawning a doomed exec at every run start would fill the
  // journal with a failure that is really a configuration state.
  //
  // ⚑ NOTHING IS AWAITED PAST THE FORK. The carriers resolve when the child is launched, not when
  // it finishes; the Slack round-trip happens in the child, off the tick. A tick must never block
  // on a network call — 10 s is the whole cadence.
  //
  // The `channel-ensure` action is pushed with its composed argv BEFORE the launch outcome is
  // known, and the outcome is its own action. Same discipline as the queued-run notice above: the
  // decision is a fact the moment it was made, and a launch failure must not be able to erase the
  // record that the daemon decided to ensure.
  // ⚠ THE SUBJECT IS `{ job }` OR `{ goal }`, AND THAT IS THE WHOLE OF WHAT TASK 7.789 CHANGED
  // HERE. The queued lane passes `{ job }` and reaches the identical body it always did; the
  // DAEMON lane (`engine/lane-watch.js`, on the pass that first adopts a goal) passes `{ goal }`.
  // The input is forwarded WHOLE to `channelEnsureDecision`, which owns the difference — this
  // function performs a decision and does not make one, so a second lane costs it no branch.
  //
  // `actions` defaults to its own array so the daemon-lane caller, which has no tick to attach to,
  // gets the same records back and can log them. It is returned for exactly that reason.
  //
  // ⚠ IT ALSO PERFORMS A DECISION IT DID NOT MAKE, and that is the whole of what the owner alarm
  // (Q3a, 2026-08-18) added here. `server/ticker/goal-stall-alarm.js` composes a
  // `goal-channel-cli.js post <goal> <text>` argv for a FROZEN goal; the credential-carrying half —
  // the env file, the systemd-only carrier, the log/exit files, the containment — is this
  // function's and must stay singular, so a caller with a decision in hand passes it as
  // `{ decision }` instead of a subject and falls into the identical body below. A second
  // performer would be a second place the daemon could grow a chat credential, which is the one
  // thing `goal-channel-design.md` forbids. The GO/NO-GO test is `decision.argv`, not the action
  // WORD: `ensure` and `post` are different acts and an argv-less decision is a skip in both.
  async function ensureGoalChannel(subject, actions = []) {
    const decision = (subject && subject.decision) || channelEnsureDecision({
      ...subject,
      resolveRoot: () => resolveWorkspaceRoot(heartStore.dbPath),
    });
    // The tick-log label rides the decision, defaulting to the one this function was born with, so
    // an alarm post is never recorded in the journal as a channel that was created.
    const act = decision.act || 'channel-ensure';
    if (!decision.argv) {
      actions.push({
        phase: 'dispatch',
        action: `${act}-skipped`,
        goal: decision.goal,
        kind: decision.kind,
        reason: decision.reason,
      });
      return actions;
    }

    const envFile = process.env.RBTV_IGNITE_CHAT_ENV_FILE || null;
    if (!envFile) {
      actions.push({
        phase: 'dispatch',
        action: `${act}-skipped`,
        goal: decision.goal,
        kind: decision.kind,
        reason: 'no-chat-env-file (RBTV_IGNITE_CHAT_ENV_FILE unset — no chat credential to give the child)',
      });
      return actions;
    }

    // ⚠ THE PREPARATION IS INSIDE THE TRY, not only the spawn (A3/C3 review, 2026-08-08). Three of
    // the calls below can throw BEFORE any carrier is reached — `ensureLogPath` (mkdir + append),
    // `ensureExitFile` (mkdir), and `selectCarrier`, which throws `E_SYSTEMD_NOT_AVAILABLE` when
    // `spawn.carrier: systemd` is configured on a box whose user manager is not up. `tick()` has a
    // `finally` and NO `catch`, so a throw escaping this function abandons the REST OF THE TICK:
    // enforce, the warning check, broadcast and `recordTick` never run and no `ticks` row is
    // written. A persistent cause — an unwritable data root, a misconfigured carrier — would then
    // break every tick that meets a due run-start row, for as long as the cause lasts. Containment
    // is what this function's own contract promises; before this it began one line too late.
    let sessionId = null;
    try {
      const cc = carrierConfig();
      const carrier = selectCarrier(cc.carrier, cc.userManager);

      // ⚑ ONLY SYSTEMD CAN CARRY THE CREDENTIAL, so only systemd may launch this. `envFile` reaches
      // the child as systemd's `EnvironmentFile=` property; `spawnSetsid` accepts no such option
      // (`spawn/carrier.js` destructures sessionId/argv/workdir/logPath/stdinFile/exitFile and
      // nothing else) and its child simply inherits THIS process's environment — which by design
      // holds no chat token. A setsid launch is therefore an exec that cannot succeed, recorded as
      // `channel-ensure-launched`: a false success, and the one outcome worse than a skip, because
      // the tick log would then say the daemon ensured a channel it did not. It skips for exactly
      // the reason an unset env file skips. ⚠ The fix is NOT to teach setsid to read the file —
      // that would load the token into the DAEMON's own memory and break
      // `goal-channel-design.md`'s bound ("the daemon holds no chat credential"), which is the
      // entire reason this act is a process rather than a function call.
      if (carrier !== 'systemd') {
        actions.push({
          phase: 'dispatch',
          action: `${act}-skipped`,
          goal: decision.goal,
          kind: decision.kind,
          reason: `carrier-cannot-carry-credential (${carrier} — EnvironmentFile is a systemd property; a ${carrier} child would run the ensure with no chat token)`,
        });
        return actions;
      }

      sessionId = generateSessionId();
      const logPath = ensureLogPath(cc.dataRoot, sessionId);
      const exitFile = ensureExitFile(cc.dataRoot, sessionId);
      actions.push({
        phase: 'dispatch',
        action: act,
        goal: decision.goal,
        kind: decision.kind,
        argv: decision.argv,
        sessionId,
        logPath,
      });

      const launchResult = await spawnSystemd({
        sessionId,
        argv: decision.argv,
        workdir: decision.goalDir,
        logPath,
        exitFile,
        caps: {},
        sandbox: {},
        envFile,
        userManager: cc.userManager,
      }, log);
      actions.push({
        phase: 'dispatch',
        action: `${act}-launched`,
        goal: decision.goal,
        sessionId,
        carrier,
        pid: launchResult.pid || null,
        unitName: launchResult.unitName || null,
      });
    } catch (err) {
      // Contained: a channel that could not be ensured is loud and is NOT allowed to abandon the
      // tick or stop the run it belongs to. The run start below proceeds either way — a goal with
      // no channel is degraded, a goal with no run is stopped. `sessionId` is null when the throw
      // landed before one was minted, and that is information, not a gap: it says the failure was
      // in the preparation rather than in the carrier.
      actions.push({
        phase: 'dispatch',
        action: `${act}-failed`,
        goal: decision.goal,
        sessionId,
        error: err.message,
      });
    }
    return actions;
  }

  async function launchStartWorkflow(queueRow, actions, tick, now) {
    const args = safeJsonParse(queueRow.args, {});
    const workflowName = args.workflow;
    const workflow = Object.hasOwn(heartStore.config.workflows || {}, workflowName) ? heartStore.config.workflows[workflowName] : undefined;
    if (!workflow) {
      actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'unknown-workflow' });
      return;
    }

    const exec = heartStore.fireQueueRow({ queueId: queueRow.queue_id, now, tick });
    if (!exec) {
      actions.push({ phase: 'dispatch', action: 'noop', queueId: queueRow.queue_id, reason: 'fire-failed' });
      return;
    }

    const cc = carrierConfig();
    const workdir = args.workdir || cc.defaultWorkdir;
    const argv = Array.isArray(workflow.argv) ? workflow.argv : (workflow.command ? [workflow.command] : []);
    if (argv.length === 0) {
      endTurnAndSession(exec.exec_id, { status: 'failed', endedAt: new Date(), reason: 'empty argv (start-workflow)' });
      actions.push({ phase: 'dispatch', action: 'start-workflow-failed', execId: exec.exec_id, error: 'empty argv' });
      return;
    }

    // ── Task C5 · PER-ROW ARGV TEMPLATING (ruling `d-owner-q10-launcher-0808` (2)) ──────────────
    //
    // The registered argv is a TEMPLATE: its `{{workflow}}` / `{{entry-seat}}` / `{{goal}}` /
    // `{{workdir}}` tokens are replaced by this row's own args, which is what lets ONE generic
    // launcher entry serve every workflow instead of one static entry per workflow. The whole
    // injection argument lives in `heart/argv-template.js`'s header — array in, array out,
    // whole-token only, one pass, closed key set — and is not restated here.
    //
    // ⚠ IT RE-VALIDATES WHAT ENQUEUE ALREADY VALIDATED, deliberately. The store gate refuses a bad
    // value at enqueue, but the store on disk outlives this code: rows written before that gate
    // existed are still fireable, and a row is read here as DATA, never as something a past
    // validation vouched for.
    //
    // A REFUSAL IS RECORDED, NOT THROWN. It lands exactly where `empty argv` above lands — the
    // turn ends `failed` and the action carries the typed reason — because the alternative shapes
    // are both worse: throwing abandons the rest of the tick (tick() has a `finally` and no
    // `catch`), and deferring leaves a row that can never compose re-firing every cadence forever.
    const composed = expandArgv(argv, args);
    if (composed.refused) {
      endTurnAndSession(exec.exec_id, { status: 'failed', endedAt: new Date(), reason: `argv template refused (start-workflow): ${composed.refused}` });
      actions.push({ phase: 'dispatch', action: 'start-workflow-failed', execId: exec.exec_id, error: `argv-template: ${composed.refused}` });
      return;
    }

    await runToolLikeExec(exec, composed.argv, workdir, actions, 'start-workflow');
  }

  async function launchSendMessage(queueRow, actions, tick, now) {
    const args = safeJsonParse(queueRow.args, {});
    const exec = heartStore.fireQueueRow({ queueId: queueRow.queue_id, now, tick });
    if (!exec) {
      actions.push({ phase: 'dispatch', action: 'noop', queueId: queueRow.queue_id, reason: 'fire-failed' });
      return;
    }

    try {
      heartStore.recordMessage({
        type: args.type,
        sender: queueRow.enqueued_by,
        thread: args.thread,
        corpus: args.corpus,
        status: args.status || null,
        createdAt: now,
      });
      endTurnAndSession(exec.exec_id, { status: 'done', endedAt: now, reason: 'send-message needs no process' });
      actions.push({ phase: 'dispatch', action: 'send-message', queueId: queueRow.queue_id });
    } catch (err) {
      endTurnAndSession(exec.exec_id, { status: 'failed', endedAt: now, reason: 'send-message failed' });
      actions.push({ phase: 'dispatch', action: 'send-message-failed', queueId: queueRow.queue_id, error: err.message });
    }
  }

  // Phases
  async function advance(now, tick, actions) {
    // Bounded fetch (task 7.19, batch-08 item 10 part 2): Advance consumes
    // COMPLETIONS only, so it asks the store for unrouted completions — never
    // the whole unrouted set. Backed by the partial index
    // idx_messages_unrouted_completion, per-tick work here tracks in-flight
    // completions (promptly routed below), not accumulated history — a future
    // writer that forgets to stamp a note cannot recreate the growth.
    //
    // Task 7.7 narrowed what this scan resolves: the jobs_log stamp (status,
    // completion_msg_id, ended_at) lands ATOMICALLY with the completion INSERT
    // in the store (recordMessage's one-transaction completion path), so a
    // half-recorded completion can no longer exist and this scan no longer
    // writes jobs_log. What it still catches — and still recovers after a
    // crash/restart, since an unrouted completion survives on disk: the
    // ROUTING half of D30's deferred resolution (recycle-on-pending-input,
    // compaction recycle, budget/failure owner notes, the wake interplay) and
    // the routed_at_tick stamp, plus the unknown-thread anomaly surface.
    const unrouted = heartStore.getMessages({ unroutedOnly: true, type: 'completion' });
    for (const msg of unrouted) {
      const exec = findExecForCompletion(msg);
      if (!exec) {
        recordOwnerNote(`anomaly: unrouted completion for unknown/inactive thread: ${msg.thread}`, now, tick);
        stampMessageRouted(msg.msg_id, tick);
        actions.push({ phase: 'advance', action: 'anomaly', msgId: msg.msg_id, reason: 'unknown-thread' });
        continue;
      }

      const status = msg.status;
      if (status === 'done' && safeJsonParse(exec.args, {})[COMPACT_MARKER] === true) {
        // A compaction turn's summary just landed: it exists only to displace
        // an answering turn, so ALWAYS re-dispatch that turn (parent = this
        // exec keeps the chain linear; composition now splices at the
        // summary). AUTOMATIC-budget-gated: compaction machinery is the one
        // automatic loop in v1, bounded by the consecutive-automatic count so
        // a runaway compact→compact cycle halts while sender-driven
        // conversations never do.
        const recycles = countAutomaticRecycles(exec.exec_id);
        if (recycles >= cfg.slot_max_repeats) {
          recordOwnerNote(`slot automatic-recycle budget exhausted after compaction (${cfg.slot_max_repeats})`, now, tick);
          stampMessageRouted(msg.msg_id, tick);
          actions.push({ phase: 'advance', action: 'compaction-budget-exhausted', execId: exec.exec_id, recycles });
        } else {
          insertQueueRow({
            jobId: exec.job_id,
            args: exec.args,
            sessionMode: exec.session_mode,
            triggerKind: 'scheduled',
            runAt: toIsoUtc(new Date(now.getTime() + 1000)),
            enqueuedBy: exec.enqueued_by,
            parentExecId: exec.exec_id,
            autoRedispatch: true,
          });
          stampMessageRouted(msg.msg_id, tick);
          actions.push({ phase: 'advance', action: 'compaction-recycle', execId: exec.exec_id, recycles });
        }
      } else if (status === 'done') {
        const pending = hasPendingInput(exec, msg.msg_id);
        if (pending) {
          // Pending input is by definition a sender message (hasPendingInput
          // filters ticker rows), so this recycle is sender-triggered and
          // UNGATED — sender-asked turns never consume the automatic budget
          // (owner ruling 2026-07-18; supersedes the former chain-total gate
          // here — spec Test Plan row 8's gesture, a task-7.5 divergence row).
          const recycles = countRecycles(exec.exec_id);
          insertQueueRow({
            jobId: exec.job_id,
            args: exec.args,
            sessionMode: exec.session_mode,
            triggerKind: 'scheduled',
            runAt: toIsoUtc(new Date(now.getTime() + 1000)),
            enqueuedBy: exec.enqueued_by,
            parentExecId: exec.exec_id,
          });
          stampMessageRouted(msg.msg_id, tick);
          actions.push({ phase: 'advance', action: 'recycle', execId: exec.exec_id, recycles });
        } else {
          stampMessageRouted(msg.msg_id, tick);
          actions.push({ phase: 'advance', action: 'end', execId: exec.exec_id });
        }
      } else if (status === 'blocked') {
        stampMessageRouted(msg.msg_id, tick);
        actions.push({ phase: 'advance', action: 'blocked', execId: exec.exec_id });
      } else if (status === 'failed') {
        recordOwnerNote(`slot halted: session failed (exec ${exec.exec_id})`, now, tick);
        stampMessageRouted(msg.msg_id, tick);
        actions.push({ phase: 'advance', action: 'failed-halt', execId: exec.exec_id });
      }
    }

    // Re-dispatch blocked slots when genuinely new input arrives on the thread.
    for (const exec of heartStore.listExecutionsByStatus('blocked')) {
      if (!hasNewInputSinceBlock(exec)) continue;
      if (isSlotLiveOrRearmed(exec)) {
        actions.push({ phase: 'advance', action: 'blocked-redispatch-deferred', execId: exec.exec_id, reason: 'slot-live-or-rearmed' });
        continue;
      }

      const recycles = countRecycles(exec.exec_id);
      if (recycles >= cfg.slot_max_repeats) {
        actions.push({ phase: 'advance', action: 'blocked-redispatch-budget-exhausted', execId: exec.exec_id, recycles });
        continue;
      }

      insertQueueRow({
        jobId: exec.job_id,
        args: exec.args,
        sessionMode: exec.session_mode,
        triggerKind: 'scheduled',
        runAt: toIsoUtc(new Date(now.getTime() + 1000)),
        enqueuedBy: exec.enqueued_by,
        parentExecId: exec.exec_id,
      });
      actions.push({ phase: 'advance', action: 'blocked-redispatch', execId: exec.exec_id, watermark: exec.completion_msg_id });
    }

    // Wake-on-message for FINISHED chains (ratified: ticker-engine-spec § the
    // recycle table / chat-bridge-spec § Forward path — "an ended chain becomes
    // due on the new message row and is re-dispatched fresh next tick"): a
    // launch-agent chain whose TAIL execution ended `done` re-dispatches when a
    // genuinely new sender message lands on its thread. `blocked` wakes via the
    // loop above; `failed`/`stalled` stay owner-halted.
    //
    // Bounded scan (task 7.19, batch-08 item 10 part 2): the loop is driven by
    // a MESSAGE WATERMARK instead of scanning every done tail each tick (which
    // grew monotonically with ended chains). Candidates are (a) threads that
    // received a non-ticker, non-completion row since the last examined msg_id,
    // plus (b) wakes deferred while their slot was live/armed, retried until
    // they land. The FIRST tick after boot does one full tail scan — it covers
    // messages that arrived while the daemon was down AND any deferral lost
    // with the process. The watermark and deferred set are in-memory CACHES,
    // safe to lose (boot rescan recovers), never authoritative state.
    let wakeCandidates = null; // null = boot tick: full tail scan
    // Snapshot BEFORE the candidate query, and advance the watermark to the
    // snapshot — never only to the last MATCHED row: rows the filter rejects
    // (ticker notes, completions) are examined too, and a watermark left
    // behind them would re-walk the same range every tick.
    const maxRow = getSql('SELECT MAX(msg_id) AS max_id FROM messages');
    const msgIdSnapshot = (maxRow && maxRow.max_id) || 0;
    if (wakeWatermark !== null) {
      wakeCandidates = new Set(pendingWakeThreads);
      for (const r of allSql(
        "SELECT thread FROM messages WHERE msg_id > ? AND msg_id <= ? AND sender != 'ticker' AND type != 'completion'",
        wakeWatermark, msgIdSnapshot
      )) {
        wakeCandidates.add(r.thread);
      }
    }
    wakeWatermark = Math.max(wakeWatermark ?? 0, msgIdSnapshot);
    pendingWakeThreads.clear();

    const doneTailIds = [];
    if (wakeCandidates === null) {
      for (const raw of allSql(`
        SELECT exec_id FROM jobs_log j
        WHERE j.status = 'done' AND j.action_type = 'launch-agent'
          AND NOT EXISTS (SELECT 1 FROM jobs_log c WHERE c.parent_exec_id = j.exec_id)
      `)) doneTailIds.push(raw.exec_id);
    } else {
      for (const thread of wakeCandidates) {
        if (typeof thread !== 'string' || !thread.startsWith('exec-')) continue;
        const rootId = parseInt(thread.slice(5), 10);
        if (!Number.isInteger(rootId)) continue;
        const raw = getSql(`
          WITH RECURSIVE descendants(exec_id) AS (
            SELECT exec_id FROM jobs_log WHERE exec_id = ?
            UNION ALL
            SELECT j.exec_id FROM jobs_log j JOIN descendants d ON j.parent_exec_id = d.exec_id
          )
          SELECT j.exec_id FROM jobs_log j JOIN descendants d ON j.exec_id = d.exec_id
          WHERE j.status = 'done' AND j.action_type = 'launch-agent'
            AND NOT EXISTS (SELECT 1 FROM jobs_log c WHERE c.parent_exec_id = j.exec_id)
          LIMIT 1
        `, rootId);
        if (raw) doneTailIds.push(raw.exec_id);
      }
    }

    for (const execId of doneTailIds) {
      const exec = heartStore.getExecution(execId);
      if (!exec || !hasNewSenderInputSinceEnd(exec)) continue;
      if (isSlotLiveOrRearmed(exec)) {
        pendingWakeThreads.add(exec.thread);
        actions.push({ phase: 'advance', action: 'wake-redispatch-deferred', execId: exec.exec_id, reason: 'slot-live-or-rearmed' });
        continue;
      }

      // Sender-triggered by construction (the wake test admits only non-ticker
      // rows) — UNGATED, per the budget ruling.
      insertQueueRow({
        jobId: exec.job_id,
        args: exec.args,
        sessionMode: exec.session_mode,
        triggerKind: 'scheduled',
        runAt: toIsoUtc(new Date(now.getTime() + 1000)),
        enqueuedBy: exec.enqueued_by,
        parentExecId: exec.exec_id,
      });
      actions.push({ phase: 'advance', action: 'wake-redispatch', execId: exec.exec_id, watermark: exec.completion_msg_id });
    }

    // Scan observability (task 7.19): the two per-tick scan figures the bound
    // governs, recorded every tick so a probe (and the tick log) can assert
    // scan work does not grow with accumulated notes/executions.
    actions.push({
      phase: 'advance',
      action: 'scan-stats',
      unroutedCompletionsScanned: unrouted.length,
      wakeCandidates: wakeCandidates === null ? doneTailIds.length : wakeCandidates.size,
      wakeBootScan: wakeCandidates === null,
      wakeWatermark,
    });
  }

  // ── THE PAUSE GATE'S GOAL RESOLUTION ────────────────────────────────────────────────────────
  //
  // Which goal would this due row spawn FOR? `rbtv-goal pause` promises "nothing new starts for
  // this goal", and until this gate the promise held only on the SEEDING path (`lane-watch.js`
  // reads a paused marker as not-`daemon`). Every OTHER goal-driven spawn went through here
  // unasked — measured on `system-health`: its `goal-watcher` fire-tool row (a periodic queue row
  // whose goal binding lives ONLY in `config.tools[...].argv` as `--package .../goals/<goal>`)
  // spawned workers straight through a paused landing, because its catalogue row carries no
  // `goal_name` and nothing on the dispatch path reads `execution-lane` at all.
  //
  // So the resolution is two-armed, covering both places a row's goal binding can live:
  //   · `job.goal_name` — the homed rows (`start-workflow` starts, seeded `launch-agent` seats);
  //   · for `fire-tool`, any argv/args string under `<workspace>/.rbtv/goals/<goal>` — the
  //     watchers and self-heal jobs, whose target is config-side.
  // A row binding NO goal (send-message, workspace-wide tools) is never gated. Absence of the
  // marker file is NOT paused — `pause` CREATES the file on a lane-less goal, so every goal is
  // pausable and an unpaused goal's behaviour is unchanged.
  //
  // Fail-open by construction (the outer catch): this gate is an operator convenience, and a
  // throw or misread inside it must neither abandon the tick nor silently park every row — the
  // conservative failure for a PAUSE is "did not pause", the opposite of the one-live gate's.
  function pausedGoalForRow(job, queueRow) {
    try {
      // Lazy: `lane-watch` → `attached-execution` → `engine/index` → this file (seeding.js:327's
      // own precedent for exactly this cycle).
      const { laneIsPaused } = require('../../engine/lane-watch');
      const workspaceRoot = resolveWorkspaceRoot(heartStore.dbPath);
      if (!workspaceRoot) return null;
      const goalsRoot = path.join(workspaceRoot, '.rbtv', 'goals');
      const goals = new Set();
      if (job.goal_name) goals.add(job.goal_name);
      if (job.action_type === 'fire-tool') {
        const args = safeJsonParse(queueRow.args, {});
        const tool = (heartStore.config.tools || {})[args.tool];
        const prefix = goalsRoot + path.sep;
        for (const s of [...((tool && tool.argv) || []), ...Object.values(args)]) {
          if (typeof s !== 'string' || !s.startsWith(prefix)) continue;
          const goal = s.slice(prefix.length).split(path.sep)[0];
          if (goal) goals.add(goal);
        }
      }
      for (const goal of goals) {
        if (laneIsPaused(path.join(goalsRoot, goal))) return goal;
      }
      return null;
    } catch {
      return null;
    }
  }

  async function dispatch(now, tick, actions) {
    const due = heartStore.getQueueDue(now);
    for (const queueRow of due) {
      const job = heartStore.getJob(queueRow.job_id);
      if (!job || !job.enabled) {
        actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'job-invalid' });
        continue;
      }

      // ── THE PAUSE GATE, BEFORE ANY ACTION BRANCH ──────────────────────────────────────────────
      // Like R9's gate below: the question "is this row's goal paused?" is about the ROW, not
      // about how it would be launched, and a gate inside one branch is a gate a later action
      // type silently escapes. `continue` leaves the row due and untouched — it fires by itself
      // on the first tick after `rbtv-goal resume`.
      const pausedGoal = pausedGoalForRow(job, queueRow);
      if (pausedGoal) {
        actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'goal-paused', goal: pausedGoal });
        continue;
      }

      // ── R9's one-live-run rule (task 7.129 / M4-14), BEFORE any action branch ─────────────────
      //
      // Placed here and not inside a branch: the question "would this start a second live run of
      // one goal?" is about the ROW, not about how the row would be launched, and a gate inside one
      // branch is a gate a later action type silently escapes. `continue` leaves the queue row
      // UNFIRED and UNTOUCHED — it stays due, is re-evaluated next tick, and starts by itself when
      // the open run closes. `fireQueueRow` (the only thing that removes or re-arms a row) is never
      // reached, so this can neither skip the start nor consume it.
      const oneLive = oneLiveRunDecision({
        job,
        queueRow,
        resolveRoot: () => resolveWorkspaceRoot(heartStore.dbPath),
      });
      if (oneLive.action === 'queued') {
        // `action: 'queued'` is its own tick action, never a `defer`: an operator reading the tick
        // log must be able to tell R9's refusal from a capacity deferral, and M4-15's notification
        // path fires on this event. The nested `action` inside `event` is 7.77's declared field and
        // is deliberately the same word.
        actions.push({
          phase: 'dispatch',
          action: 'queued',
          queueId: queueRow.queue_id,
          reason: oneLive.reason,
          event: oneLive.event,
        });

        // ── Task 7.130 / M4-15 — the queued run tells the owner ────────────────────────────────
        //
        // AFTER the `queued` action is already recorded, and before the `continue`. The order is
        // the design: the queueing is a fact the moment the decision was made, and it is recorded
        // unconditionally, so no outcome of the notification can alter it. A failed send below
        // therefore CANNOT turn a queued row into a skipped one — the thing it would have to
        // undo is already banked, and this call has no queue handle to undo it with. That is the
        // failure 7.77 designs out, made structural rather than promised.
        //
        // `notifyQueuedStart` never throws (its module's header says why, and 7.129 measured the
        // cost: a throw on this path abandons the whole tick). So there is deliberately NO try
        // around it — a second one here would suggest the containment is not already inside.
        const notice = await notifyQueuedStart(oneLive.event, { now, tick });
        if (notice.notified && !notice.delivered) {
          // SURFACED IN TWO PLACES, SWALLOWED IN NEITHER. Its own tick action, so an operator
          // reading the log sees the delivery failed and does not read the `queued` line above as
          // "the owner was told"; and an owner-feed note, because the owner feed is the surface a
          // human actually reads and a notification failure is exactly the thing that would
          // otherwise be visible only to whoever was tailing the tick log at the time.
          actions.push({
            phase: 'dispatch',
            action: 'queued-notify-failed',
            queueId: queueRow.queue_id,
            reason: oneLive.reason,
            error: notice.error,
          });
          recordOwnerNote(
            `ignite: a scheduled run start was QUEUED for goal ${job.goal_name} (queue row `
            + `${queueRow.queue_id}), and the notification about it FAILED to deliver `
            + `(${notice.error}). The start is queued, not lost — it resumes when the open run closes.`,
            now, tick,
          );
        } else if (notice.notified) {
          actions.push({
            phase: 'dispatch',
            action: 'queued-notified',
            queueId: queueRow.queue_id,
            reason: oneLive.reason,
            ts: notice.ts,
          });
        }
        continue;
      }

      const args = safeJsonParse(queueRow.args, {});
      if (job.action_type === 'launch-agent') {
        // ⚠ NO PRE-DISPATCH SPEC CHECK ANY MORE (7.787). This deferred a row whose `args.profile`
        // was not a key of the config — the one argument `#d-abolish-profile-names` deletes. There
        // is nothing here to check: the row names no spec, and the seat's cast is resolved inside
        // `spawn()`. The failure it used to catch does NOT become silent — an uncast or unmappable
        // seat throws `E_UNCAST_SEAT`/`E_UNMAPPED_BINDING` out of the spawn call below and is
        // recorded as `spawn-failed` against this exec's own `jobs_log` row, which is louder than
        // a `defer` that repeated every cadence with nobody reading it.
        await launchAgent(queueRow, actions, tick, now);
      } else if (job.action_type === 'fire-tool') {
        if (!args.tool || !Object.hasOwn(heartStore.config.tools || {}, args.tool)) {
          actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'unknown-tool' });
          continue;
        }
        await launchFireTool(queueRow, actions, tick, now);
      } else if (job.action_type === 'start-workflow') {
        if (!args.workflow || !Object.hasOwn(heartStore.config.workflows || {}, args.workflow)) {
          actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'unknown-workflow' });
          continue;
        }
        // Task C3 — BEFORE the workflow launches, not after: `goal-channel-design.md` (a) settles
        // that the 1:1 goal↔channel invariant holds from the goal's birth, so the seats this start
        // is about to launch must not be able to reach for a channel that is still being created.
        // Placed inside this branch and after the unknown-workflow guard because only a row that
        // will actually start a run is a workflow start; a deferred row is not one.
        await ensureGoalChannel({ job }, actions);
        await launchStartWorkflow(queueRow, actions, tick, now);
      } else if (job.action_type === 'send-message') {
        await launchSendMessage(queueRow, actions, tick, now);
      }
    }
  }

  // Read the carrier's exit marker for an ended execution. exitCode is null
  // for a signal death ($EXIT_STATUS carries the signal name, kept in `raw`).
  function readExitMarker(exec) {
    if (!exec.session_id) return { present: false, exitCode: null, raw: null };
    try {
      const raw = fs.readFileSync(exitFilePath(spawnManager.config.spawn.data_root, exec.session_id), 'utf8').trim();
      return { present: true, exitCode: /^\d+$/.test(raw) ? parseInt(raw, 10) : null, raw };
    } catch {
      return { present: false, exitCode: null, raw: null };
    }
  }

  // The worker's ANSWER: the last log line shaped { type:'result', result:'…' }
  // (`claude -p --output-format stream-json`). Attempted on every clean exit,
  // harness-agnostic by FALLBACK: a log with no parseable result line (another
  // harness, a tool) yields null and the caller records the log tail instead.
  // Bounded read — the result line is the log's last line.
  function extractResultFromLog(logPath) {
    let text = null;
    for (const line of tailBytes(logPath, RESULT_TAIL_BYTES).split('\n')) {
      if (!line) continue;
      let obj;
      try { obj = JSON.parse(line); } catch { continue; }
      if (obj && obj.type === 'result' && typeof obj.result === 'string') text = obj.result;
    }
    return text;
  }

  function getLogSize(logPath) {
    if (!logPath || !fs.existsSync(logPath)) return 0;
    try { return fs.statSync(logPath).size; } catch { return 0; }
  }

  function lastEnforceSessions() {
    const lastTick = heartStore.getLastTick();
    if (!lastTick) return {};
    const actions = safeJsonParse(lastTick.actions_json, []);
    for (let i = actions.length - 1; i >= 0; i--) {
      const a = actions[i];
      if (a.phase === 'enforce' && a.action === 'state' && a.sessions) {
        return a.sessions;
      }
    }
    return {};
  }

  async function enforce(now, tick, actions) {
    // Crash sweep first so stall ladder only applies to still-live sessions.
    //
    // `stalled` executions STAY in the swept set (owner ruling 2026-07-20,
    // batch-08 item 4 half B): `stalled` means "owner should look", never "no
    // longer tracked". A stalled worker whose unit later goes inactive still
    // gets its synthetic completion + exit code exactly as a `running` row
    // does — without this, the exit is recorded by nothing and the outcome is
    // unrecoverable. Dispatch semantics are unchanged: the stall ladder below
    // and every re-dispatch path still exclude `stalled` (owner-halted).
    // 7.46: the crash sweep asks a SESSION question — has the process gone? — so it reads the
    // session table. `stalled` turns stay in the swept set exactly as before (the owner ruling
    // above): stalled is a TURN state whose session is still alive, so those rows already arrive
    // via liveSessionTurns(); the explicit concat is kept for the case where a stalled turn's
    // session row is absent (a pre-7.46 row on a store not yet migrated), and the dedupe below
    // keeps a row from being swept twice.
    //
    // ── W1 · V1's FOLD-IN, FIRST HALF: `liveTurns()` JOINS THE SWEPT SET ────────────────────────
    //
    // The verification found `orphanRescan` runs NOWHERE in production — its only caller is its own
    // probe, and the "boot rescan" comments elsewhere are stale (`server/index.js` boots retention
    // → lane watch → first tick and never calls it). So the two classes it alone reached were
    // reached by NOTHING: (1) a `launching`/`running` turn whose session row is missing or no
    // longer `alive`, and (2) row-less `rbtv-worker-*` units. This union closes (1); the scan below
    // closes (2).
    //
    // ⚠ IT ADDS NO ROW ON THE HEALTHY PATH, and that is why it is safe to fold in rather than
    // gate: a turn row and its session row are born in ONE transaction (`fireQueueRow`), so every
    // live turn is ALREADY here via `liveSessionTurns()` and arrives deduped. What the union adds
    // is exactly the DIVERGENT rows — a turn left in flight under a session that is gone — which
    // is the state no sweep could see. Once here they take the same arms every other dead process
    // takes (completion recorded, exit code read from the carrier's marker, session-closer called)
    // instead of `orphanRescan`'s bare `status: failed` stamp with no completion and no closer.
    const liveBeforeCrash = dedupeByExecId(
      liveSessionTurns()
        .concat(heartStore.listExecutionsByStatus('stalled'))
        .concat(liveTurns())
    );
    const crashedThisTick = new Set();
    // Every `status()` this tick already paid for, keyed by exec — the stall ladder's hung-kill
    // rung needs `cpuNsec` for the same rows the sweep below is about to ask about, and asking
    // twice would double the `systemctl show` count on every tick of a live daemon.
    const statusThisTick = new Map();
    // ONE hung kill per tick. A kill is a process act with a grace period inside a loop that runs
    // INSIDE the tick — the same reason the session closer above is capped. A backlog drains one
    // per tick; nothing else clears it, so nothing is lost.
    let killBudget = 1;
    // ── W1 · THE SESSION-CLOSER'S BUDGET FOR THIS TICK (adv, C14) ──────────────────────────────
    // Each close is a BLOCKING `execFileSync` of python, and this loop runs INSIDE the tick. A
    // backlog — a daemon restarted onto a store holding dozens of leaked rows — would otherwise
    // stall the whole cadence on its first pass. Capped, so a backlog drains over several ticks
    // instead of stopping the heart for one; the rows that do not fit this tick are still there
    // next tick, because nothing else clears them.
    let closerBudget = CLOSER_MAX_PER_TICK;
    // F3 — drain leader-minted disposition grants, ONCE per tick, over every goal that carries
    // an unspent one. It hangs beside the sweep rather than inside it because the grant is a
    // fact about a GOAL's coordination folder, not about any exec: the goal it is minted on is
    // typically one whose seats are all dead, and a drain keyed off the swept execs never
    // reached it. The helper never throws.
    applyDispositionGrants({ workspaceRoot: resolveWorkspaceRoot(heartStore.dbPath), log });
    for (const exec of liveBeforeCrash) {
      let info;
      try { info = await spawnManager.status(exec.exec_id); } catch { continue; }
      statusThisTick.set(exec.exec_id, info);
      if (!info.live) {
        // ── W1 · CLOSE THE SEAT'S OWN SESSION ROW, and do it HERE — before the three arms below
        // fork — because all three mean the same thing to the seat trace: THE PROCESS IS GONE.
        // What the ENGINE observed (clean exit / crash / already-reported) is a fact about the
        // TURN; what the seat's row needs is the seat's OWN declaration, which coord reads off
        // `awaiting-close.json`. Passing the engine's verdict down would be the engine asserting
        // something about work only the occupant witnessed.
        //
        // Failure is never fatal and never breaks a `continue` below: the helper swallows and logs.
        if (closerBudget > 0 && exec.workdir && exec.session_id) {
          closerBudget -= 1;
          closeSeatSessionRow({ workdir: exec.workdir, sessionId: exec.session_id, log });
        }
        // ── G-222 · THE TURN ALREADY REPORTED. Write the SESSION, never the turn.
        //
        // What this sweep just observed is that a PROCESS is gone — a session-level fact. Before
        // 7.46 it could only ever reach non-terminal turns (`running`/`launching`/`stalled`), so
        // "the turn has not reported yet" was a STRUCTURAL property of the set and no code had to
        // state it. 7.46 re-keyed the set on `sessions.status = 'alive'` — correct for the
        // question the set asks — and the exclusion vanished with the old query. Measured: a turn
        // seeded `done` was rewritten to `failed` at the first tick, with a manufactured crash
        // completion and a "slot halted" owner note for a session that had ended normally.
        //
        // ⚠ THE EXCLUSION IS RESTORED HERE AND NOT IN listTurnsOfLiveSessions(), deliberately.
        // That function feeds the AGENT CAP too (`liveAgentSessions` above), and a turn-level
        // predicate there would hide a session that is alive with its turn reported — R16's
        // idle-between-turns session, the exact state the split exists to represent — from the cap
        // that must count it. It would also leave these sessions `alive` forever: this sweep is
        // the only thing that ever closes a leaked one.
        //
        // So the sweep still LOOKS at the row (it must — otherwise nothing closes the session) and
        // writes only what it actually observed.
        if (TERMINAL_TURN_STATUSES.has(exec.status)) {
          if (exec.session_pk) {
            heartStore.closeSession(exec.session_pk, {
              status: sessionStatusForEndedTurn(exec.status),
              reason: `process gone; turn ${exec.exec_id} had already reported '${exec.status}'`,
              closedAt: now,
            });
          }
          // Named its own action, not folded into `crash-sweep`: this tick ended a SESSION and
          // ended no turn, and an action log that calls both "crash-sweep" cannot tell an
          // operator which happened.
          actions.push({ phase: 'enforce', action: 'session-closed-turn-already-reported', execId: exec.exec_id, turnStatus: exec.status });
          continue;
        }

        // The carrier's exit marker is the ONLY honest exit observation for a
        // detached --collect unit: `systemctl show` on a collected unit
        // returns DEFAULT values (ExecMainStatus=0), so info.exitCode here is
        // fabricated. Marker present + 0 → an honest clean turn-end, recorded
        // `done` with the worker's extracted answer as the completion corpus —
        // Advance then recycles on pending input or ends the slot; NEVER the
        // failed-halt path. Marker present + non-zero (or a signal name) →
        // failed with the REAL code. Marker absent → the pre-marker crash
        // path, unchanged (genuine crash, pre-feature worker, daemon-restart
        // setsid loss).
        const marker = readExitMarker(exec);
        if (marker.present && marker.exitCode === 0) {
          const answer = extractResultFromLog(exec.log_path);
          const corpus = answer !== null
            ? answer
            : `clean exit: 0 (no parseable result line)\n--- log tail ---\n${tailBytes(exec.log_path, 4096)}`;
          // Task 7.7: message INSERT + jobs_log stamp are ONE store transaction
          // (execId pins the swept row — no thread re-resolution).
          const msg = heartStore.recordMessage({
            type: 'completion',
            sender: 'ticker',
            thread: exec.thread || `exec-${exec.exec_id}`,
            corpus,
            status: 'done',
            createdAt: now,
            execId: exec.exec_id,
            exitCode: 0,
          });
          actions.push({ phase: 'enforce', action: 'clean-exit-sweep', execId: exec.exec_id, completionMsgId: msg.msg_id, extracted: answer !== null });
          continue;
        }
        const exitCode = marker.present ? marker.exitCode : (info.exitCode ?? info.carrierInfo?.exitCode ?? null);
        const tail = tailBytes(exec.log_path, 4096);
        const corpus = `crash sweep: exit=${marker.present ? marker.raw : exitCode}\n--- log tail ---\n${tail}`;
        // Task 7.7: message INSERT + jobs_log stamp are ONE store transaction
        // (execId pins the swept row — no thread re-resolution).
        const msg = heartStore.recordMessage({
          type: 'completion',
          sender: 'ticker',
          thread: exec.thread || `exec-${exec.exec_id}`,
          corpus,
          status: 'failed',
          createdAt: now,
          execId: exec.exec_id,
          exitCode,
        });
        recordOwnerNote(`slot halted: session crashed (exec ${exec.exec_id})`, now, tick);
        crashedThisTick.add(exec.exec_id);
        actions.push({ phase: 'enforce', action: 'crash-sweep', execId: exec.exec_id, exitCode, completionMsgId: msg.msg_id });
      }
    }

    // ── W1 · V1's FOLD-IN, SECOND HALF: THE ROW-LESS `rbtv-worker-*` UNITS ──────────────────────
    //
    // A unit whose session id matches no `jobs_log` row at all — a worker the store lost, or one
    // left by a daemon that died between the spawn and the row. No sweep above can reach it,
    // because every sweep starts FROM a row. `spawnManager.list()` already computes exactly this
    // set (`anomalies`, type `row-less-unit`), so it is called rather than re-derived.
    //
    // ⚠ REPORTED, NEVER KILLED — `orphanRescan`'s own posture, kept: the daemon cannot prove a
    // stray unit is not doing useful work, and killing on a store's silence is how a healthy
    // worker gets shot for a bookkeeping gap.
    //
    // ⚠ THROTTLED, because `list()` dumps EVERY table of the store to answer it. At the tick
    // cadence that is a full-table read every few seconds for a pathology that appears once in a
    // daemon's lifetime; on the scan tick it is one dump. Detection latency of minutes is the
    // trade, and it is the right one — nothing acts on the finding automatically anyway.
    if (tick % ROWLESS_UNIT_SCAN_EVERY_TICKS === 0 && typeof spawnManager.list === 'function') {
      try {
        for (const a of (spawnManager.list().anomalies || [])) {
          if (a.type !== 'row-less-unit') continue;
          log('warn', 'row-less rbtv-worker unit found; NOT auto-killed', { unitName: a.unitName, sessionId: a.sessionId, active: a.active });
          actions.push({ phase: 'enforce', action: 'row-less-unit', unitName: a.unitName, sessionId: a.sessionId, active: a.active });
        }
      } catch (err) {
        log('warn', 'row-less unit scan failed', { error: err.message });
      }
    }

    // Stall ladder.
    const lastSessions = lastEnforceSessions();
    const sessions = {};
    // 7.46: the stall ladder is a TURN question — it asks whether the WORK is progressing, and it
    // writes `stalled`, a turn state whose session stays alive. (This seat's own design brief
    // listed it among the session-level readers; reading it settled that it is not. Corrected in
    // the design rather than quietly implemented the other way.)
    //
    // ── THE HUNG-KILL RUNG'S PREREQUISITE: `stalled` ROWS STAY ON THE LADDER ────────────────────
    //
    // They used to LEAVE it. `liveTurns()` is `launching` + `running`, so the tick that wrote
    // `stalled` was the last tick that tracked that exec's silence: its `sessions` entry stopped
    // being written, `lastEnforceSessions()` stopped carrying it, and the counter froze at the
    // value that tripped the stall. Nothing above `stalled` could ever be measured. Including the
    // stalled rows here is what makes a rung above it possible at all; the `stalled` WRITE and its
    // owner note are guarded on `exec.status !== 'stalled'` below so they still fire exactly once.
    for (const exec of dedupeByExecId(liveTurns().concat(heartStore.listExecutionsByStatus('stalled')))) {
      // (No guard needed against the sweep above: both queries here are re-read AFTER it, and a
      // swept row's status is already terminal, so it is not in either set.)
      // D101: headed sessions are EXEMPT from the silence stall ladder. A headed session emits no
      // `completion` and is expected to sit idle (an owner-driven terminal awaiting a human),
      // so silence must NEVER warn or stall it — that would drop it from the live-only session
      // picker while its pty stays fully attachable, breaking browser take-over. The CRASH SWEEP
      // above (a dead headed session → `failed`) still applies, and `runtime_max` / explicit kill
      // still bound it; only the silence warn/stall path is skipped.
      if (exec.session_mode === 'headed') continue;

      const last = lastSessions[exec.exec_id] || { lastActivityTick: exec.fired_tick, lastLogSize: 0 };
      let lastActivityTick = last.lastActivityTick;
      let lastLogSize = last.lastLogSize;

      if (hasMessagesSinceStart(exec)) {
        lastActivityTick = tick;
      }
      const currentLogSize = getLogSize(exec.log_path);
      if (currentLogSize > lastLogSize) {
        lastActivityTick = tick;
        lastLogSize = currentLogSize;
      }

      const silenceTicks = tick - lastActivityTick;

      // The SECOND silence signal, read for stalled rows only (the rung is the only reader, and a
      // `systemctl show` per live exec per tick for nobody is not worth paying). `null` where the
      // carrier reports no CPU accounting — a setsid exec, always.
      const lastCpuNsec = last.lastCpuNsec === undefined ? null : last.lastCpuNsec;
      let cpuNsec = lastCpuNsec;
      if (exec.status === 'stalled' && cfg.stall_kill_ticks > 0) {
        // The crash sweep above already asked `status()` for every row in its set — which
        // includes every `stalled` row — so this is a Map read, not a second systemctl call. The
        // fallback covers only a row the sweep could not reach.
        let info = statusThisTick.get(exec.exec_id);
        if (info === undefined) {
          try { info = await spawnManager.status(exec.exec_id); } catch { info = null; }
        }
        cpuNsec = info ? (info.cpuNsec ?? null) : null;
      }
      sessions[exec.exec_id] = { lastActivityTick, lastLogSize, silenceTicks, lastCpuNsec: cpuNsec };

      // ── THE HUNG-KILL RUNG (owner-ruled) ──────────────────────────────────────────────────────
      //
      // `stalled` says "the owner should look"; it pages and it is NOT terminal, and none of that
      // changes. This rung says something strictly narrower: this turn is already stalled AND its
      // process has written no log bytes AND burnt no CPU time across the kill window — it is not
      // slow, it is HUNG, and the seat it holds is dead capacity. Killing it frees the seat. No
      // new status word: `spawnManager.kill` writes the existing terminal `killed` through
      // `endTurnAndCloseSession` and closes the seat's session row.
      //
      // ⚠ ORDERING DEPENDENCY: the crash sweep runs BEFORE this loop and already handles a stalled
      // row whose PROCESS is gone. This rung is therefore only ever reached by a stalled row whose
      // process is still alive — which is exactly the case a sweep cannot see.
      //
      // ⚠ BOTH SIGNALS REQUIRED, and `cpuNsec === null` EXCLUDES rather than defaults (owner
      // ruling: one frozen signal is too weak to kill on). That excludes every setsid exec by
      // construction. The log-bytes half needs no separate test: any growth resets
      // `lastActivityTick` to this tick, so `silenceTicks >= stall_kill_ticks` already asserts it
      // — a second check here could never fail and would be evidence of nothing.
      if (killBudget > 0
          && cfg.stall_kill_ticks > 0
          && exec.status === 'stalled'
          && silenceTicks >= cfg.stall_kill_ticks
          && cpuNsec !== null && lastCpuNsec !== null && cpuNsec === lastCpuNsec) {
        killBudget -= 1;
        let how = 'killed';
        try {
          await spawnManager.kill(exec.exec_id);
        } catch (err) {
          // THE SEAT MUST BE FREED EITHER WAY. A carrier that cannot be killed is a worse reason
          // to leave a seat occupied forever than no reason at all, so the turn is ended
          // terminally here even though the process may survive — and the note says so.
          how = `unkillable (${err.message})`;
          try {
            heartStore.endTurnAndCloseSession(exec.exec_id, {
              turnStatus: 'failed',
              sessionStatus: 'crashed',
              endedAt: now,
              reason: `stall-kill: carrier unkillable`,
            });
          } catch (err2) {
            log('warn', 'hung-kill could not end the turn', { execId: exec.exec_id, error: err2.message });
          }
        }
        recordOwnerNote(
          `hung slot killed: exec ${exec.exec_id} was stalled and silent for ${silenceTicks} ticks `
          + `with its log frozen at ${lastLogSize} bytes and its CPU time frozen at ${cpuNsec} ns — ${how}`,
          now, tick,
        );
        actions.push({ phase: 'enforce', action: 'hung-kill', execId: exec.exec_id, silenceTicks });
        continue;
      }

      // A row already `stalled` has had its stall write and its owner note. Both fire exactly
      // once — without this the ladder would re-page it every tick now that stalled rows stay on
      // it, which is the noise `stalled` exists to replace.
      if (exec.status === 'stalled') continue;

      if (silenceTicks >= cfg.stall_halt_ticks) {
        heartStore.updateExecutionStatus(exec.exec_id, { status: 'stalled' });
        recordOwnerNote(`slot stalled after ${silenceTicks} ticks of silence`, now, tick);
        actions.push({ phase: 'enforce', action: 'stalled', execId: exec.exec_id, silenceTicks });
      } else if (silenceTicks >= cfg.stall_warn_ticks) {
        recordOwnerNote(`silent warning after ${silenceTicks} ticks of silence`, now, tick);
        actions.push({ phase: 'enforce', action: 'warn', execId: exec.exec_id, silenceTicks });
      }
    }

    actions.push({ phase: 'enforce', action: 'state', sessions });
  }

  async function broadcast(tick, actions) {
    const messages = heartStore.getMessages({ unbroadcastOnly: true });
    for (const msg of messages) {
      const line = JSON.stringify({
        ts: msg.created_at,
        msg_id: msg.msg_id,
        type: msg.type,
        sender: msg.sender,
        thread: msg.thread,
        status: msg.status,
        corpus: msg.corpus,
      });
      if (feedPath) {
        fs.appendFileSync(feedPath, line + '\n', 'utf8');
      }
      stampBroadcast(msg.msg_id, tick);
      actions.push({ phase: 'broadcast', msgId: msg.msg_id });
    }
  }

  async function tick(now = new Date()) {
    if (stopped) {
      const halted = { phase: 'tick', action: 'skipped-stopped' };
      return { tick: getTickNumber(), skipped: true, actions: [halted] };
    }
    if (ticking) {
      const skipped = { phase: 'tick', action: 'skipped-reentrant' };
      log('warn', 'tick skipped: already running');
      return { tick: getTickNumber(), skipped: true, actions: [skipped] };
    }
    ticking = true;
    const nudgedWithThisTick = nudgedWith;
    nudgedWith = null;
    const actions = [];
    try {
      const tick = setNextTickNumber();
      log('info', `tick ${tick} start${nudgedWithThisTick ? ` (nudged: ${nudgedWithThisTick})` : ''}`, { tick, nudged: nudgedWithThisTick });

      actions.push({ phase: 'apply-events', skipped: true });
      await advance(now, tick, actions);
      await dispatch(now, tick, actions);
      // Phase 4 · nudge — the declared no-op placeholder is now the loop's latency valve, and it
      // sits here because both producers have already run: Advance's wake/recycle inserts and
      // Dispatch's send-message fire are both in `actions` by this point.
      //
      // LOOP GUARD, in one line: only a tick that was ITSELF nudged may schedule another. A
      // cadence tick never chains, and a nudged tick that produced none of NUDGE_AFTER stops
      // dead. The chain that does run is the chat pipeline and it converges in three:
      // send-message -> wake-redispatch -> spawn (not in the set).
      const nudgeAction = { phase: 'nudge' };
      if (nudgedWithThisTick) nudgeAction.nudged = nudgedWithThisTick;
      const follow = nudgedWithThisTick ? actions.find(a => NUDGE_AFTER.has(a.action)) : null;
      if (follow) {
        nudgeAction.scheduled = follow.action;
        nudge(`tick-${tick}:${follow.action}`, NUDGE_FOLLOWON_MS);
      } else {
        nudgeAction.skipped = true;
      }
      actions.push(nudgeAction);
      await enforce(now, tick, actions);
      const preWarnActionCount = actions.length;
      runWarningCheck({ heartStore, tick, now, slotMaxRepeats: cfg.slot_max_repeats, tickIntervalMs: cfg.tick_interval_ms, actions });
      // The warning check writes its announce notes to the owner feed through
      // the store directly; stamp them routed in the same tick (task 7.19 —
      // a ticker-authored owner-feed note is informational, nothing routes
      // it, so it must never linger in the unrouted set).
      if (actions.slice(preWarnActionCount).some(a => a.phase === 'warnings' && a.action === 'announce')) {
        runSql(
          "UPDATE messages SET routed_at_tick = ? WHERE routed_at_tick IS NULL AND type = 'note' AND sender = 'ticker' AND thread = ?",
          tick, OWNER_NOTE_THREAD
        );
      }
      await broadcast(tick, actions);

      const ts = new Date();
      const actionsJson = JSON.stringify(actions);
      heartStore.recordTick({ tick, ts, actionsJson });
      logLine(logPath, `${toIsoUtc(ts)} tick=${tick} actions=${actionsJson}`);
      log('info', `tick ${tick} end`, { tick, actionCount: actions.length });

      return { tick, actions };
    } finally {
      ticking = false;
      // A nudge whose timer fired mid-tick is re-armed here, ONCE — never a concurrent tick.
      if (nudgePending && !nudgeTimer) nudge(nudgePending.reason, nudgePending.delayMs);
    }
  }

  // ⚠ `ensureGoalChannel` IS EXPOSED FOR THE DAEMON LANE, and for nothing else (task 7.789). The
  // performing half needs `spawnSystemd`, the carrier config and this store's data root — all of
  // which live in this closure — while the DECIDING half is `goal-channel-start.js`, imported.
  // `engine/lane-watch.js` reaches it as `engine.ticker.ensureGoalChannel`, which is why the
  // engine already publishes `ticker` on its surface (`engine/index.js`). Exposing it beats the
  // alternative shapes: re-implementing the spawn in the engine would be a second performer of an
  // act that must stay singular, and threading a callback down from `server/index.js` would put
  // the wire somewhere neither end can read.
  return { tick, getTickNumber, nudge, stop, ensureGoalChannel };
}

module.exports = { createTicker };
