'use strict';

// start-execution — the bridge's SENDER for the approval thread's D12 materialize. It holds no
// child process and no store handle: it turns the approval dispatch's `materialize` port into a
// `start-execution` gateway call and reports what came back.
//
// ⚠ THIS FILE IS WHY `approve` FINALLY DOES SOMETHING. `approval-thread.js` was built with
// `materialize` as an INJECTED PORT and nothing to inject: the birth it names is
// `planning/path_b.py#run_path_b`, a CHILD PROCESS, and `probes/probe-chat-boundary.js` forbids
// this process one — so production wired no port and every `approve` posted the [C-16] failure
// into the thread instead. The owner ruled option (b) on 2026-08-24
// (`redesign-implementation/decisions.md`, the 14th-intent entry): the start gets its own gateway
// intent, and a daemon-side executor runs the supervised Path-B birth. That is the same
// authorizing shape the thirteenth intent (`record-owner-ask`) cites, and the same division of
// labour — the bridge keeps a caller, the capability stays server-side
// (`server/heart/start-execution.js`).
//
// THREE CONSEQUENCES FOLLOW, AND NONE IS AN OVERSIGHT:
//
//   1. THE PAYLOAD CARRIES NO PLAN. It names the planning goal, the approval thread, and the bound
//      commit [T5-R5] — nothing else. WHAT gets built is the approve-package the planning goal
//      already carries, read daemon-side, so a caller cannot approve one plan and start another.
//   2. THE OWNER'S COMMENTS AFTER `approve` DO NOT TRAVEL. They are a retry's findings list
//      [T3-R21]; a birth is fully determined by the package and the commit, and the intent's
//      payload schema is closed at the gateway, so sending them would be a REFUSAL, not an
//      ignored key. They stay in the thread, where the owner wrote them.
//   3. THE CALL IS SLOW ON PURPOSE. A Path-B birth scaffolds a goal folder and mints its roster
//      through the materialize lock; that is minutes, not the 10s every store-write intent gets.
//      This module passes a per-call timeout override, which is `live-feed`'s precedent exactly
//      (one intent's patience, never a raised default for everything else).
//
// ⚠ EVERY FAILURE IS A `{ok:false, error}` THE APPROVAL THREAD WILL SHOW THE OWNER, never a throw
// and never a silent success. `createApprovalDispatch` posts that error back into the SAME thread
// [C-16] and leaves the thread usable for the retry that follows. An `{ok:true}` here means an
// execution goal EXISTS — the one lie this surface must never tell.

// A Path-B birth is scaffold + mint under the lock. The daemon's own subprocess timeout is 120s
// (`server/heart/start-execution.js#PATH_B_TIMEOUT_MS`); this is deliberately LONGER, so a slow
// birth is answered by the daemon's own refusal rather than abandoned mid-mint by the client.
const START_TIMEOUT_MS = 180000;

function createExecutionStart({ forwarder, logger = null, timeoutMs = START_TIMEOUT_MS } = {}) {
  if (!forwarder || typeof forwarder.forward !== 'function') {
    throw new Error('createExecutionStart requires the gateway forwarder — D12 crosses the daemon boundary as an intent');
  }
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  // The `materialize` port `approval-thread.js#createApprovalDispatch` was written against, filled.
  async function materialize({ goalId, commitId, askId }) {
    // Defense in depth: `composeApprovalBody` already REFUSES to compose an approval with no
    // commit, so an approval thread without one should not exist. If one does, it is unbound, and
    // an unbound approval approves whatever the tree holds later [T5-R5].
    if (!commitId) {
      log('warn', 'D12 NOT started — this approval thread carries no bound commit [T5-R5]', { goalId, askId });
      return { ok: false, error: 'this approval names no bound commit, so there is nothing safe to build [T5-R5]' };
    }
    if (!askId) {
      return { ok: false, error: 'this approval has no thread id, and the thread IS the approval record [T5-R7]' };
    }
    let res;
    try {
      res = await forwarder.forward('start-execution',
        { goal: String(goalId), thread: String(askId), commit: String(commitId) },
        { timeoutMs });
    } catch (err) {
      log('warn', 'D12 NOT started — the start call THREW', { goalId, askId, error: err.message });
      return { ok: false, error: err.message };
    }
    if (!res.ok) {
      const code = (res.error && res.error.code) || 'unknown';
      const message = (res.error && res.error.message) || code;
      log('warn', 'D12 NOT started — the gateway REFUSED the start', { goalId, askId, error: code });
      return { ok: false, error: `${code}: ${message}` };
    }
    const result = res.result || {};
    if (result.started !== true) {
      // The daemon refused, or the supervised materialize failed and wrote its six-field record
      // onto the planning goal. Either way the owner is about to read this line in the thread, so
      // it carries the REASON and, when there is one, the record's own code.
      const record = result.record || null;
      const detail = result.detail || (record && (record.reason || record.code)) || 'no reason given';
      log('warn', 'D12 did not start the execution goal', {
        goalId, askId, reason: result.reason, detail, code: record && record.code,
      });
      return { ok: false, error: `${result.reason || 'refused'} — ${detail}`, record };
    }
    log('info', 'D12: the execution goal was born through the supervised Path-B materialize', {
      goalId, askId, executionGoal: result.execution_goal,
    });
    return { ok: true, execution_goal: result.execution_goal };
  }

  return { materialize };
}

module.exports = { createExecutionStart, START_TIMEOUT_MS };
