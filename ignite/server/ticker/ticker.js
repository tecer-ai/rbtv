'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {
  selectCarrier,
  spawnSystemd,
  spawnSetsid,
  generateSessionId,
} = require('../spawn/carrier');
const { exitFilePath, ensureExitFile } = require('../spawn/spawn');
const { runWarningCheck } = require('./warnings-check');

const DEFAULT_CONFIG = {
  tick_interval_ms: 10000,
  stall_warn_ticks: 12,
  stall_halt_ticks: 24,
  max_live_agent_sessions: 2,
  slot_max_repeats: 10,
  history_compact_chars: 60000,
};

// Private marker carried in a re-dispatch queue row's args JSON so the ticker
// can pass parent_exec_id to fireQueueRow. The queue table has no column for
// this in the v1 schema; this marker is stripped before spawn and before the
// args are persisted in jobs_log.
const CHAIN_MARKER = '__rbtv_chain_parent_exec_id';

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

  function liveExecutions() {
    return heartStore.listExecutionsByStatus('running')
      .concat(heartStore.listExecutionsByStatus('launching'));
  }

  function findLiveExecutionForThread(thread) {
    for (const row of liveExecutions()) {
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
    const result = runSql(`
      INSERT INTO queue (job_id, args, session_mode, trigger_kind, run_at, enqueued_by, enqueued_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `, jobId, argsJson, sessionMode, triggerKind, runAt, enqueuedBy, enqueuedAt);
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

  // Launch helpers
  async function launchAgent(queueRow, actions, tick, now) {
    const { parentExecId, cleanedArgs } = extractChainMarker(queueRow);
    const args = safeJsonParse(cleanedArgs, {});
    const profileName = args.profile;
    const prompt = args.prompt ?? null;
    const workdir = args.workdir ?? null;

    if (parentExecId) {
      const thread = chainThread(parentExecId);
      const live = findLiveExecutionForThread(thread);
      if (live) {
        actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'slot-live-session', thread });
        return;
      }
    }

    const liveAgentSessions = liveExecutions().filter(r => r.action_type === 'launch-agent').length;
    if (liveAgentSessions >= cfg.max_live_agent_sessions) {
      actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'global-cap' });
      return;
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
        updateArgs(exec.exec_id, JSON.stringify({ ...args, [COMPACT_MARKER]: true }));
      } else {
        spawnPrompt = CONTINUE_PROMPT_HEADER + transcript + CONTINUE_PROMPT_FOOTER;
        updateArgs(exec.exec_id, cleanedArgs);
      }
    }

    try {
      await spawnManager.spawn(exec.exec_id, profileName, queueRow.session_mode, spawnPrompt, workdir, queueRow.enqueued_by);
      const spawnAction = { phase: 'dispatch', action: 'spawn', execId: exec.exec_id, queueId: queueRow.queue_id, profile: profileName, thread: exec.thread };
      if (compactTurn) spawnAction.compact = true;
      actions.push(spawnAction);
    } catch (err) {
      actions.push({ phase: 'dispatch', action: 'spawn-failed', execId: exec.exec_id, error: err.message });
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
      heartStore.updateExecutionStatus(exec.exec_id, { status: 'failed', endedAt: new Date() });
      actions.push({ phase: 'dispatch', action: `${actionName}-failed`, execId: exec.exec_id, error: err.message });
    }
  }

  function recordToolCompletion(execId, exitCode, logPath) {
    const exec = heartStore.getExecution(execId);
    if (!exec || ['done', 'blocked', 'failed', 'stalled'].includes(exec.status)) return;
    const tail = tailBytes(logPath, 4096);
    const corpus = `tool exit: ${exitCode}\n--- output tail ---\n${tail}`;
    const status = exitCode === 0 ? 'done' : 'failed';
    heartStore.recordMessage({
      type: 'completion',
      sender: 'ticker',
      thread: exec.thread || `exec-${execId}`,
      corpus,
      status,
      createdAt: new Date(),
    });
    // Leave the completion unresolved so Advance owns the lifecycle stamp.
  }

  async function launchFireTool(queueRow, actions, tick, now) {
    const args = safeJsonParse(queueRow.args, {});
    const toolName = args.tool;
    const tool = (heartStore.config.tools || {})[toolName];
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
    const argv = Array.isArray(tool.argv) ? tool.argv : (tool.command ? [tool.command] : []);
    if (argv.length === 0) {
      heartStore.updateExecutionStatus(exec.exec_id, { status: 'failed', endedAt: new Date() });
      actions.push({ phase: 'dispatch', action: 'fire-tool-failed', execId: exec.exec_id, error: 'empty argv' });
      return;
    }
    await runToolLikeExec(exec, argv, workdir, actions, 'fire-tool');
  }

  async function launchStartWorkflow(queueRow, actions, tick, now) {
    const args = safeJsonParse(queueRow.args, {});
    const workflowName = args.workflow;
    const workflow = (heartStore.config.workflows || {})[workflowName];
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
      heartStore.updateExecutionStatus(exec.exec_id, { status: 'failed', endedAt: new Date() });
      actions.push({ phase: 'dispatch', action: 'start-workflow-failed', execId: exec.exec_id, error: 'empty argv' });
      return;
    }
    await runToolLikeExec(exec, argv, workdir, actions, 'start-workflow');
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
      heartStore.updateExecutionStatus(exec.exec_id, { status: 'done', endedAt: now });
      actions.push({ phase: 'dispatch', action: 'send-message', queueId: queueRow.queue_id });
    } catch (err) {
      heartStore.updateExecutionStatus(exec.exec_id, { status: 'failed', endedAt: now });
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
          heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'done', endedAt: now, routedAtTick: tick });
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
          heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'done', endedAt: now, routedAtTick: tick });
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
          heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'done', endedAt: now, routedAtTick: tick });
          actions.push({ phase: 'advance', action: 'recycle', execId: exec.exec_id, recycles });
        } else {
          heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'done', endedAt: now, routedAtTick: tick });
          actions.push({ phase: 'advance', action: 'end', execId: exec.exec_id });
        }
      } else if (status === 'blocked') {
        heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'blocked', endedAt: now, routedAtTick: tick });
        actions.push({ phase: 'advance', action: 'blocked', execId: exec.exec_id });
      } else if (status === 'failed') {
        recordOwnerNote(`slot halted: session failed (exec ${exec.exec_id})`, now, tick);
        heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'failed', endedAt: now, routedAtTick: tick });
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

  async function dispatch(now, tick, actions) {
    const due = heartStore.getQueueDue(now);
    for (const queueRow of due) {
      const job = heartStore.getJob(queueRow.job_id);
      if (!job || !job.enabled) {
        actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'job-invalid' });
        continue;
      }

      const args = safeJsonParse(queueRow.args, {});
      if (job.action_type === 'launch-agent') {
        if (!args.profile || !(heartStore.config.profiles || {})[args.profile]) {
          actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'unknown-profile' });
          continue;
        }
        await launchAgent(queueRow, actions, tick, now);
      } else if (job.action_type === 'fire-tool') {
        if (!args.tool || !(heartStore.config.tools || {})[args.tool]) {
          actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'unknown-tool' });
          continue;
        }
        await launchFireTool(queueRow, actions, tick, now);
      } else if (job.action_type === 'start-workflow') {
        if (!args.workflow || !(heartStore.config.workflows || {})[args.workflow]) {
          actions.push({ phase: 'dispatch', action: 'defer', queueId: queueRow.queue_id, reason: 'unknown-workflow' });
          continue;
        }
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
    const liveBeforeCrash = liveExecutions()
      .concat(heartStore.listExecutionsByStatus('stalled'));
    const crashedThisTick = new Set();
    for (const exec of liveBeforeCrash) {
      let info;
      try { info = await spawnManager.status(exec.exec_id); } catch { continue; }
      if (!info.live) {
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
          const msg = heartStore.recordMessage({
            type: 'completion',
            sender: 'ticker',
            thread: exec.thread || `exec-${exec.exec_id}`,
            corpus,
            status: 'done',
            createdAt: now,
          });
          heartStore.updateExecutionStatus(exec.exec_id, { status: 'done', exitCode: 0, endedAt: now });
          actions.push({ phase: 'enforce', action: 'clean-exit-sweep', execId: exec.exec_id, completionMsgId: msg.msg_id, extracted: answer !== null });
          continue;
        }
        const exitCode = marker.present ? marker.exitCode : (info.exitCode ?? info.carrierInfo?.exitCode ?? null);
        const tail = tailBytes(exec.log_path, 4096);
        const corpus = `crash sweep: exit=${marker.present ? marker.raw : exitCode}\n--- log tail ---\n${tail}`;
        const msg = heartStore.recordMessage({
          type: 'completion',
          sender: 'ticker',
          thread: exec.thread || `exec-${exec.exec_id}`,
          corpus,
          status: 'failed',
          createdAt: now,
        });
        recordOwnerNote(`slot halted: session crashed (exec ${exec.exec_id})`, now, tick);
        heartStore.updateExecutionStatus(exec.exec_id, { status: 'failed', exitCode, endedAt: now });
        crashedThisTick.add(exec.exec_id);
        actions.push({ phase: 'enforce', action: 'crash-sweep', execId: exec.exec_id, exitCode, completionMsgId: msg.msg_id });
      }
    }

    // Stall ladder.
    const lastSessions = lastEnforceSessions();
    const sessions = {};
    for (const exec of liveExecutions()) {
      // D101: headed sessions are EXEMPT from the silence stall ladder. A headed session emits no
      // `completion` and is expected to sit idle (an owner-driven pty waiting for JOIN/TAKE-OVER),
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
      sessions[exec.exec_id] = { lastActivityTick, lastLogSize, silenceTicks };

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
    if (ticking) {
      const skipped = { phase: 'tick', action: 'skipped-reentrant' };
      log('warn', 'tick skipped: already running');
      return { tick: getTickNumber(), skipped: true, actions: [skipped] };
    }
    ticking = true;
    const actions = [];
    try {
      const tick = setNextTickNumber();
      log('info', `tick ${tick} start`, { tick });

      actions.push({ phase: 'apply-events', skipped: true });
      await advance(now, tick, actions);
      await dispatch(now, tick, actions);
      actions.push({ phase: 'nudge', skipped: true });
      await enforce(now, tick, actions);
      const preWarnActionCount = actions.length;
      runWarningCheck({ heartStore, tick, now, slotMaxRepeats: cfg.slot_max_repeats, actions });
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
    }
  }

  return { tick, getTickNumber };
}

module.exports = { createTicker };
