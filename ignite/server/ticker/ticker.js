'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {
  selectCarrier,
  spawnSystemd,
  spawnSetsid,
  generateSessionId,
} = require('../spawn/carrier');
const { runWarningCheck } = require('./warnings-check');

const DEFAULT_CONFIG = {
  tick_interval_ms: 10000,
  stall_warn_ticks: 12,
  stall_halt_ticks: 24,
  max_live_agent_sessions: 2,
  slot_max_repeats: 10,
};

// Private marker carried in a re-dispatch queue row's args JSON so the ticker
// can pass parent_exec_id to fireQueueRow. The queue table has no column for
// this in the v1 schema; this marker is stripped before spawn and before the
// args are persisted in jobs_log.
const CHAIN_MARKER = '__rbtv_chain_parent_exec_id';

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

  // Delegates to the store's ONE determination of recycle-budget consumption,
  // so the advance/re-dispatch gates below and the warning check read the same
  // number. Semantics are unchanged (chain-total recycles).
  function countRecycles(execId) {
    return heartStore.countChainRecycles({ execId });
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
  function insertQueueRow({ jobId, args, sessionMode, triggerKind, runAt, enqueuedBy, parentExecId }) {
    const argsObj = typeof args === 'string' ? safeJsonParse(args, {}) : (args || {});
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

    if (parentExecId) {
      updateArgs(exec.exec_id, cleanedArgs);
    }

    try {
      await spawnManager.spawn(exec.exec_id, profileName, queueRow.session_mode, prompt, workdir, queueRow.enqueued_by);
      actions.push({ phase: 'dispatch', action: 'spawn', execId: exec.exec_id, queueId: queueRow.queue_id, profile: profileName });
    } catch (err) {
      actions.push({ phase: 'dispatch', action: 'spawn-failed', execId: exec.exec_id, error: err.message });
    }
  }

  function ensureLogPath(dataRoot, sessionId) {
    const logDir = path.join(dataRoot, 'logs');
    fs.mkdirSync(logDir, { recursive: true, mode: 0o700 });
    return path.join(logDir, `${sessionId}.log`);
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
    const unrouted = heartStore.getMessages({ unroutedOnly: true });
    for (const msg of unrouted) {
      if (msg.type !== 'completion') continue;

      const exec = findExecForCompletion(msg);
      if (!exec) {
        heartStore.recordMessage({
          type: 'note',
          sender: 'ticker',
          thread: OWNER_NOTE_THREAD,
          corpus: `anomaly: unrouted completion for unknown/inactive thread: ${msg.thread}`,
          createdAt: now,
        });
        stampMessageRouted(msg.msg_id, tick);
        actions.push({ phase: 'advance', action: 'anomaly', msgId: msg.msg_id, reason: 'unknown-thread' });
        continue;
      }

      const status = msg.status;
      if (status === 'done') {
        const pending = hasPendingInput(exec, msg.msg_id);
        if (pending) {
          const recycles = countRecycles(exec.exec_id);
          if (recycles >= cfg.slot_max_repeats) {
            heartStore.recordMessage({
              type: 'note',
              sender: 'ticker',
              thread: OWNER_NOTE_THREAD,
              corpus: `slot automatic-recycle budget exhausted (${cfg.slot_max_repeats})`,
              createdAt: now,
            });
            heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'done', endedAt: now, routedAtTick: tick });
            actions.push({ phase: 'advance', action: 'budget-exhausted', execId: exec.exec_id, recycles });
          } else {
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
          }
        } else {
          heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'done', endedAt: now, routedAtTick: tick });
          actions.push({ phase: 'advance', action: 'end', execId: exec.exec_id });
        }
      } else if (status === 'blocked') {
        heartStore.resolveCompletion({ msgId: msg.msg_id, execId: exec.exec_id, status: 'blocked', endedAt: now, routedAtTick: tick });
        actions.push({ phase: 'advance', action: 'blocked', execId: exec.exec_id });
      } else if (status === 'failed') {
        heartStore.recordMessage({
          type: 'note',
          sender: 'ticker',
          thread: OWNER_NOTE_THREAD,
          corpus: `slot halted: session failed (exec ${exec.exec_id})`,
          createdAt: now,
        });
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
        heartStore.recordMessage({
          type: 'note',
          sender: 'ticker',
          thread: OWNER_NOTE_THREAD,
          corpus: `slot automatic-recycle budget exhausted (${cfg.slot_max_repeats}); blocked re-dispatch halted`,
          createdAt: now,
        });
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
    const liveBeforeCrash = liveExecutions();
    const crashedThisTick = new Set();
    for (const exec of liveBeforeCrash) {
      let info;
      try { info = await spawnManager.status(exec.exec_id); } catch { continue; }
      if (!info.live) {
        const exitCode = info.exitCode ?? info.carrierInfo?.exitCode ?? null;
        const tail = tailBytes(exec.log_path, 4096);
        const corpus = `crash sweep: exit=${exitCode}\n--- log tail ---\n${tail}`;
        const msg = heartStore.recordMessage({
          type: 'completion',
          sender: 'ticker',
          thread: exec.thread || `exec-${exec.exec_id}`,
          corpus,
          status: 'failed',
          createdAt: now,
        });
        heartStore.recordMessage({
          type: 'note',
          sender: 'ticker',
          thread: OWNER_NOTE_THREAD,
          corpus: `slot halted: session crashed (exec ${exec.exec_id})`,
          createdAt: now,
        });
        heartStore.updateExecutionStatus(exec.exec_id, { status: 'failed', exitCode, endedAt: now });
        crashedThisTick.add(exec.exec_id);
        actions.push({ phase: 'enforce', action: 'crash-sweep', execId: exec.exec_id, exitCode, completionMsgId: msg.msg_id });
      }
    }

    // Stall ladder.
    const lastSessions = lastEnforceSessions();
    const sessions = {};
    for (const exec of liveExecutions()) {
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
        heartStore.recordMessage({
          type: 'note',
          sender: 'ticker',
          thread: OWNER_NOTE_THREAD,
          corpus: `slot stalled after ${silenceTicks} ticks of silence`,
          createdAt: now,
        });
        actions.push({ phase: 'enforce', action: 'stalled', execId: exec.exec_id, silenceTicks });
      } else if (silenceTicks >= cfg.stall_warn_ticks) {
        heartStore.recordMessage({
          type: 'note',
          sender: 'ticker',
          thread: OWNER_NOTE_THREAD,
          corpus: `silent warning after ${silenceTicks} ticks of silence`,
          createdAt: now,
        });
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
      runWarningCheck({ heartStore, tick, now, slotMaxRepeats: cfg.slot_max_repeats, actions });
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
