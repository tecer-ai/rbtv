'use strict';

// API
// runCheck({ home, tool, timeoutMs?, env?, onChild? }) → Promise<{ answer, details?, failure? }>
//   Starts the stored check tool once, with the agent home as working folder and RBTV_AGENT_HOME.
//   answer is 'nothing', 'new' (with details) or 'failed' (with failure, and with details when
//   the tool printed a usable "something new" answer before it failed). Never rejects.
// createChecks({ log, now?, env? }) → { run, stop }
//   run({ slug, home, store, schedule }) → Promise<outcome>, or null while the same check of the
//   same agent is still running. The outcome is settled in the agent's store: nothing new
//   advances the timer, something new records one wake, a failure is counted. The third failure
//   in a row queues one Slack notice and writes one board watch-out; the first success clears
//   the count. stop() kills every running check and settles none of them.
// This file starts no model and posts nothing itself: a wake goes through store.fireSchedule and
// a notice through the outbox.

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { spawnable } = require('../../../../cast/capabilities/tools/cast/lib/win-exec');
const { nextOccurrence } = require('./schedule.js');
const { boardPath, parseBoard, writeBoard } = require('./board.js');

const TIMEOUT_MS = 60_000;
const FAILURES_BEFORE_NOTICE = 3;
const MAX_ANSWER_BYTES = 1024 * 1024;
const STDERR_TAIL = 300;

function failed(failure, details) {
  return details === undefined ? { answer: 'failed', failure } : { answer: 'failed', failure, details };
}

// The answer a check printed, or null when it is not one of the two forms.
function readAnswer(stdout) {
  let body;
  try { body = JSON.parse(stdout); } catch { return null; }
  if (!body || typeof body !== 'object' || Array.isArray(body)) return null;
  if (body.new === false) return { answer: 'nothing' };
  if (body.new === true && body.details != null) return { answer: 'new', details: body.details };
  return null;
}

// A check's children die with it: on POSIX it leads its own process group.
function killTree(child) {
  try {
    if (process.platform === 'win32') child.kill('SIGKILL');
    else process.kill(-child.pid, 'SIGKILL');
  } catch { /* already gone */ }
}

function runCheck({ home, tool, timeoutMs = TIMEOUT_MS, env = process.env, onChild }) {
  return new Promise((resolve) => {
    const target = spawnable(tool.includes('/') ? path.join(home, tool) : tool, [], process.platform, env);
    let child;
    try {
      child = spawn(target.cmd, target.args, {
        cwd: home,
        env: { ...env, RBTV_AGENT_HOME: home },
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: process.platform !== 'win32',
        ...target.opts,
      });
    } catch (error) {
      resolve(failed(`check did not start: ${error.message}`));
      return;
    }
    if (onChild) onChild(child);
    const stdout = [];
    let bytes = 0;
    let stderr = '';
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      killTree(child);
      finish(failed(`check timed out after ${timeoutMs / 1000} s`));
    }, timeoutMs);
    child.stdout.on('data', (chunk) => {
      bytes += chunk.length;
      if (bytes <= MAX_ANSWER_BYTES) { stdout.push(chunk); return; }
      killTree(child);
      finish(failed(`check printed more than ${MAX_ANSWER_BYTES} bytes`));
    });
    child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr = (stderr + chunk).slice(-STDERR_TAIL); });
    child.once('error', (error) => finish(failed(`check did not start: ${error.message}`)));
    child.once('close', (code, signal) => {
      const answer = readAnswer(Buffer.concat(stdout).toString('utf8'));
      if (code === 0) {
        finish(answer || failed('check exited 0 without {"new":false} or {"new":true,"details":…}'));
        return;
      }
      const how = signal ? `check was killed by ${signal}` : `check exited ${code}`;
      const said = stderr.trim();
      finish(failed(said ? `${how}: ${said}` : how, answer?.details));
    });
  });
}

function stateKey(scheduleId) {
  return `timer_check:${scheduleId}`;
}

function readState(store, scheduleId) {
  const row = store.db.prepare('SELECT value FROM settings WHERE key=?').get(stateKey(scheduleId));
  return row ? JSON.parse(row.value) : { failures: 0 };
}

function writeState(store, scheduleId, state, now) {
  store.db.prepare(`INSERT INTO settings(key,value,updated_at) VALUES (?,?,?)
    ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at`)
    .run(stateKey(scheduleId), JSON.stringify(state), now);
}

function watchOutLine(slug, schedule, since) {
  return `- Timer check ${schedule.id} (${schedule.check_tool}) failed ${FAILURES_BEFORE_NOTICE} times in a row `
    + `from ${new Date(since).toISOString()} and has not succeeded since (${new Date(since).toISOString().slice(0, 10)} · ${slug})`;
}

// Adds or removes one watch-out through writeBoard, which checks the whole board.
function editWatchOuts(home, store, now, edit) {
  const file = boardPath(home);
  const text = fs.readFileSync(file, 'utf8');
  const board = parseBoard(text);
  const lines = board.lines.slice();
  edit(lines, board.sections[1]);
  return writeBoard(file, lines.join(text.includes('\r\n') ? '\r\n' : '\n'), { store, now });
}

function addWatchOut(home, store, now, line) {
  return editWatchOuts(home, store, now, (lines, section) => {
    const last = section.rows.at(-1);
    if (last) lines.splice(last.index + 1, 0, line);
    else lines.splice(section.start + 1, 0, '', line);
  });
}

function removeWatchOut(home, store, now, line) {
  return editWatchOuts(home, store, now, (lines, section) => {
    const row = section.rows.find((item) => item.line === line);
    if (row) lines.splice(row.index, 1);
  });
}

// Records one finished check in the agent's store. The timer and the count move in one
// transaction; the board follows, and its refusal is logged, never thrown.
function settle({ slug, home, store, schedule, result, now, log }) {
  const current = store.getSchedule(schedule.id);
  if (!current?.enabled || current.next_at !== schedule.next_at) {
    log({ event: 'check', slug, schedule: schedule.id, answer: result.answer, dropped: 'timer changed while its check ran' });
    return { answer: result.answer, wake: null };
  }
  const nextAt = nextOccurrence(schedule.cadence, schedule.timezone, now);
  const before = readState(store, schedule.id);
  let wake = null;
  let state = before;
  let notice = false;
  let recovered = false;
  store.transaction(() => {
    if (result.answer !== 'failed') {
      if (result.answer === 'new') wake = store.fireSchedule({ schedule, nextAt, details: { found: result.details } });
      else store.advanceSchedule(schedule.id, schedule.next_at, nextAt);
      recovered = before.failures > 0;
      if (recovered) {
        state = { failures: 0, recovered: { at: now, after: before.failures, since: before.since, last: before.last } };
        writeState(store, schedule.id, state, now);
      }
      return;
    }
    if (result.details !== undefined) {
      wake = store.fireSchedule({ schedule, nextAt, details: { found: result.details, failure: result.failure } });
    } else if (nextAt != null) {
      // A one-time timer has no next occurrence: it stays due and its check runs again next tick.
      store.advanceSchedule(schedule.id, schedule.next_at, nextAt);
    }
    state = {
      failures: before.failures + 1,
      since: before.failures ? before.since : now,
      last: { at: now, failure: result.failure },
      watchOut: before.failures ? before.watchOut : undefined,
      recovered: before.recovered,
    };
    notice = state.failures === FAILURES_BEFORE_NOTICE;
    if (notice) {
      const conv = store.getConversation(schedule.conversation_key);
      store.beginProactive({
        id: `check:${schedule.id}:${state.since}`,
        agent: conv.agent,
        workspace: conv.workspace,
        channel: conv.channel,
        payload: {
          text: `Timer check failed ${FAILURES_BEFORE_NOTICE} times in a row: timer ${schedule.id}, check ${schedule.check_tool}. `
            + `Last failure: ${result.failure}. The timer stays on; this is the only notice until the check succeeds and fails again.`,
          audio: false,
          files: [],
        },
      });
      state.watchOut = watchOutLine(slug, schedule, state.since);
    }
    writeState(store, schedule.id, state, now);
  });
  log({
    event: 'check', slug, schedule: schedule.id, answer: result.answer,
    ...(wake ? { wake: wake.reason } : {}),
    ...(result.failure ? { failure: result.failure, failures: state.failures } : {}),
  });
  if (notice) log({ event: 'check-notice', slug, schedule: schedule.id, failures: state.failures, since: state.since });
  if (recovered) log({ event: 'check-recovered', slug, schedule: schedule.id, after: before.failures, since: before.since });
  const board = notice ? addWatchOut : (recovered && before.watchOut ? removeWatchOut : null);
  if (board) {
    try { board(home, store, now, notice ? state.watchOut : before.watchOut); }
    catch (error) { log({ event: 'check-watch-out', slug, schedule: schedule.id, message: error.message }); }
  }
  return { answer: result.answer, wake, failures: state.failures, notice };
}

function createChecks({ log, now = Date.now, env = () => process.env }) {
  const running = new Map();
  let stopped = false;

  function run({ slug, home, store, schedule }) {
    const key = `${slug}:${schedule.id}`;
    if (stopped || running.has(key)) return null;
    running.set(key, null);
    let folder;
    try { folder = fs.realpathSync(home); } catch { folder = home; }
    return runCheck({
      home: folder, tool: schedule.check_tool, env: env(),
      onChild(child) { running.set(key, child); },
    }).then((result) => {
      running.delete(key);
      if (stopped) return { answer: result.answer, wake: null };
      return settle({ slug, home: folder, store, schedule, result, now: now(), log });
    });
  }

  function stop() {
    stopped = true;
    for (const child of running.values()) if (child) killTree(child);
  }

  return { run, stop };
}

module.exports = { runCheck, createChecks, FAILURES_BEFORE_NOTICE };
