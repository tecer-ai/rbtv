'use strict';

// THE FORWARD-PATH CONTRACT (chat-bridge-spec.md § Forward path, D104/D105) — the
// heart of the bridge. A chat message from an ADMITTED principal becomes ONE of
// exactly two gateway calls, both `enqueue-job` (the bridge adds NO new intent —
// D90; the set stays SEVEN, and the bridge speaks only add-job here):
//
//   1. FIRST message in a new chat thread  → a SESSION-CREATING job:
//        enqueue-job naming a launch-agent function + a named launch profile
//        (DEC-1 R3). The bridge NEVER spawns; the ticker's Dispatch phase does.
//
//   2. FOLLOW-UP in an already-mapped thread → a `send-message` ACTION-TYPE job
//        addressed to the mapped turn-chain's thread (`exec-<first exec_id>`).
//        Reply type is PINNED (D105): `answer` when it responds to a pending
//        `ask`, else `note` — the closed CMP-8 five-type vocabulary (mint nothing).
//
// ⚑ NEVER `send-to-session` (D104). That intent's ratified re-validation required
// the execution to be `session_mode: headed` AND live (the pty keystroke rung —
// internal-api-contract-spec.md §1), while chat rides the HEADLESS model's turn-
// boundary ceiling (notes §7b). The follow-up leg is the SAME add-job path as the
// first leg — a send-message job on the chain's thread — consumed at the next turn
// boundary. There is no send-to-session code path in this file, by construction.

//
// ⚑ THE BRIDGE CARRIES NO BEHAVIOURAL TEXT (owner ruling 2026-08-06). A session-create
// prompt is the user's BARE MESSAGE. Who the session is and how it behaves travel with
// the seat it is homed at — its `seat.md` and the auto-injected CLAUDE.md chain above
// it — so identity lives in one place that the seat's owner edits, not in a constant
// inside a transport. A charter here would also be an instance-specific path in repo
// source, which this repo forbids.

const fs = require('node:fs');
const path = require('node:path');
const { nowIsoUtc } = require('./config');

// The five CMP-8 message types (closed vocabulary — mint nothing). Only `answer`
// and `note` are produced by the follow-up leg per D105; the full set is stated
// so a future producer never invents a sixth.
const CMP8_TYPES = new Set(['completion', 'ask', 'answer', 'verdict', 'note']);

// D111 part 2 — the honest decline notice. When a MAPPED conversation's follow-up
// cannot reach the running work (chain unresolved, or the gateway refused the
// enqueue), the owner sees this ONE fixed line instead of silence. Fixed string,
// NO internals (never leak a reason / thread / queue id into chat).
const DECLINE_NOTICE = "⚠ couldn't route your reply to the running work — please try again shortly";

// The same mechanics for the OTHER honest refusal: goal-channel traffic that has no
// goal-master seat to land in. Fixed string, no internals — it names the human act that
// fixes it, because the owner reading it in Slack is the one who can.
const NO_GOAL_SEAT_NOTICE = "⚠ no goal-master seat is open for this goal — ask the run's owner to seat one";

// The THIRD honest refusal, same mechanics again: the daemon's idempotent door suppressed this
// session-create because the seat is still busy with a live turn, so NOTHING was enqueued
// (ruling `d-q9-door`). Fixed string, no internals — it states the outcome the owner cannot
// otherwise see (his message did NOT land) and the act that fixes it (send it again), because
// unlike the two notices above, nobody else can act on this one: it clears on its own.
const SEAT_BUSY_NOTICE = "⚠ that work is still busy with the previous message — yours was NOT delivered, please send it again shortly";

// Where a goal-channel session is HOMED: the goal-master seat of that goal's OPEN run.
//   <workspaceRoot>/.rbtv/goals/<goalId>/runs.csv  → the row with state=open
//   <workspaceRoot>/.rbtv/goals/<goalId>/runs/<run-id>/seats/goal-master
// Every step is a refusal point, and each returns a REASON rather than a fallback: an
// unresolvable seat must never degrade into launching at some default workdir, where the
// session would run with no descriptor and no goal identity at all.
// ponytail: plain split on ',' — runs.csv columns are ids and timestamps, no quoted
// fields; if a column ever needs escaping this needs a real CSV reader.
function resolveGoalMasterSeat(workspaceRoot, goalId) {
  if (!workspaceRoot) return { ok: false, reason: 'no-workspace-root-configured' };
  const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', String(goalId));
  const runsCsv = path.join(goalDir, 'runs.csv');
  let raw;
  try { raw = fs.readFileSync(runsCsv, 'utf8'); } catch { return { ok: false, reason: 'runs-csv-unreadable' }; }
  const rows = raw.split('\n').map((l) => l.trim()).filter(Boolean).slice(1); // drop the header
  const open = rows.map((l) => l.split(',')).find((c) => (c[2] || '').trim() === 'open');
  if (!open) return { ok: false, reason: 'no-open-run' };
  const runId = (open[0] || '').trim();
  if (!runId) return { ok: false, reason: 'no-open-run' };
  const seatDir = path.join(goalDir, 'runs', runId, 'seats', 'goal-master');
  // The seat must EXIST — a run can be open with no goal-master seated, and launching
  // at a path that is not there is the failure this check exists to make visible.
  try {
    if (!fs.statSync(seatDir).isDirectory()) return { ok: false, reason: 'goal-master-seat-missing', seatDir };
  } catch { return { ok: false, reason: 'goal-master-seat-missing', seatDir }; }
  return { ok: true, runId, seatDir };
}

function createForwardPath({ forwarder, threadMap, allowlist, config, logger = null, deliver = null }) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // Best-effort owner notice on a refusal the owner can act on (D111 part 2): a DROPPED
  // reply path in the follow-up leg, or a goal channel with no goal-master seat. Both
  // are ROUTABLE conversations — the human is addressing real work and deserves a line
  // instead of silence. Delivery is best-effort: when no reply address exists
  // deliverToOwner returns delivered:false and we drop; a failed post is logged and
  // dropped, NEVER retried (no notice loop). Notices are NEVER posted on
  // allowlist/pairing or unroutable-surface refusals — those return before either leg
  // (unadmitted or unattributable traffic gets nothing, by security posture, not a gap).
  async function postDeclineNotice(chatThreadId, text = DECLINE_NOTICE) {
    if (typeof deliver !== 'function') return;
    try {
      const d = await deliver({ chatThreadId, text, markAsk: false });
      if (d && d.delivered === false) {
        log('warn', 'decline notice not delivered (best-effort, dropped)', { chatThreadId, reason: d.reason || d.error || 'unknown' });
      } else {
        log('info', 'decline notice posted to owner thread', { chatThreadId });
      }
    } catch (err) {
      log('warn', 'decline notice threw (best-effort, dropped)', { chatThreadId, error: err.message });
    }
  }

  // The launch profile for a first message, by SURFACE (task 7.58). Master (DM) and
  // goal (channel) traffic are different work — cold-contact intake versus a message
  // on an existing goal's thread — so they may run different profiles. Both fall back
  // to the single `sessionProfile`, so an unconfigured deployment behaves exactly as
  // it did before this task. No new job payload field is introduced anywhere: the
  // surface distinction rides the EXISTING `profile` arg, because inventing a wire
  // field would put the bridge ahead of the job catalogue's own args schema.
  function profileFor(route) {
    if (route && route.kind === 'goal') return config.goalProfile || config.sessionProfile;
    return config.masterProfile || config.sessionProfile;
  }

  // WHERE the session runs, by surface. Master/mention traffic uses the configured
  // `workdir` as it always has. GOAL traffic is homed at that goal's OPEN run's
  // goal-master seat, so the session boots inside the seat folder whose descriptor
  // chain IS its identity — the reason the prompt can be the bare user text.
  // Returns { ok, workdir } or { ok: false, reason } — never a fallback.
  function workdirFor(route) {
    if (!route || route.kind !== 'goal') return { ok: true, workdir: config.workdir || null };
    const seat = resolveGoalMasterSeat(config.workspaceRoot, route.goalId);
    if (!seat.ok) return seat;
    return { ok: true, workdir: seat.seatDir, runId: seat.runId };
  }

  // A first message that STARTS work → a session-creating launch-agent job.
  async function forwardSessionCreate({ chatThreadId, text, route }) {
    const profile = profileFor(route);
    if (!profile) {
      // A launch-agent job MUST name a profile (DEC-1 R3; the store re-validates it
      // exists). Missing config is a loud refusal, never a silent malformed forward.
      return { forwarded: false, leg: 'session-create', reason: 'no-session-profile-configured' };
    }
    const home = workdirFor(route);
    if (!home.ok) {
      // Nothing is enqueued. The owner gets the fixed notice on the goal's own channel,
      // because the fix — seating a goal-master on the open run — is a human act.
      log('warn', 'goal session-create refused: no goal-master seat resolved', { chatThreadId, goalId: route && route.goalId, reason: home.reason });
      await postDeclineNotice(chatThreadId, NO_GOAL_SEAT_NOTICE);
      return { forwarded: false, leg: 'session-create', reason: `no-goal-master-seat:${home.reason}`, goalId: (route && route.goalId) || null };
    }
    // WHICH CHAT THREAD THIS SITTING IS — the ONE prefix the bare-prompt ruling admits
    // (owner amendment 2026-08-07, goal ledger `r-bare-prompt-admits-one-correlation-id`;
    // README § The prompt is the bare user text). The reply leg already routes a sitting's
    // ANSWER by thread id without the agent knowing one, and that is untouched. This exists
    // for the OTHER direction: a sitting relaying a question onto the coordination bus must
    // be able to say where the answer belongs, and it cannot say what it was never told.
    //
    // ⚑ ONE ADDRESSED FACT, NEVER BEHAVIOUR. The ban above is unchanged and total — no
    // charter, no identity, no instructions, no instance paths. The first attempt at this
    // line (2026-08-07, before the amendment) correctly turned two probes red; they are now
    // NARROWED to strip exactly this shape and still assert the remainder is the user text
    // verbatim, so a charter is caught exactly as before.
    //
    // ⚑ PLAIN HERE, BRACKETED ON THE WAY BACK — a LOOP GUARD, not formatting. Only
    // `[chat-thread: …]` routes a row (`bus-ferry.js`). If a relay carried the bracketed
    // form, the ferry would read the outbound question as an inbound answer and mint a
    // sitting from it — the question returning to its own thread.
    const prompt = chatThreadId ? `chat-thread: ${chatThreadId}\n\n${text}` : text;
    const payload = {
      job_id: config.sessionJobId,
      // The user text, behind at most the one correlation line above — the seat's descriptor
      // carries behaviour (see the header).
      args: { profile, prompt },
      session_mode: 'headless',                 // chat rides the headless model (notes §7b)
      trigger_kind: 'scheduled',
      run_at: nowIsoUtc(),                      // due now: the next tick dispatches it
    };
    if (home.workdir) payload.args.workdir = home.workdir;

    const res = await forwarder.forward('enqueue-job', payload);
    if (!res.ok) {
      log('warn', 'session-create enqueue refused by gateway', { chatThreadId, error: res.error });
      return { forwarded: false, leg: 'session-create', intent: 'enqueue-job', error: res.error };
    }
    // ⚠ A RETURNED QUEUE ID IS NOT DELIVERY — the door may have suppressed this create
    // (ruling `d-q9-door`; the discard bound is stated in heart-store.js at the guard).
    // The store dedups `launch-agent` enqueues on a (run, seat) key and returns BEFORE the
    // INSERT, so a suppressed call's `args` — the user's text included — are DISCARDED and the
    // caller is handed the HELD operation's id. This bridge is the caller that loses by it:
    // EVERY session it creates is homed at a SHARED seat — master traffic at `config.workdir`,
    // goal traffic at that goal's `goal-master` (see `workdirFor`) — so a new conversation
    // opening while that seat holds a live turn is precisely the suppressed case.
    //
    // Mapping the thread to that id would bind this conversation to a turn it did not create,
    // and the user's message would be neither enqueued nor delivered while the bridge logged a
    // success (measured, Q9 review 2026-08-08). So nothing is mapped and the human is told.
    if (res.result && res.result.deduped) {
      log('warn', 'session-create suppressed at the door — seat busy, NOTHING enqueued', {
        chatThreadId, route: route && route.kind, goalId: route && route.goalId,
        heldQueueId: res.result.jobId, because: res.result.because, seatKey: res.result.seat_key,
      });
      await postDeclineNotice(chatThreadId, SEAT_BUSY_NOTICE);
      // The undelivered text rides the REFUSAL so no caller has to reconstruct what was lost —
      // `chat-bridge.js` routeBusRowToMaster already falls through to posting the row raw on a
      // not-forwarded result, which turns this from silent loss into a degraded delivery.
      return {
        forwarded: false,
        leg: 'session-create',
        intent: 'enqueue-job',
        reason: `seat-busy-deduped:${res.result.because || 'unknown'}`,
        undeliveredText: text,
        route: route && route.kind,
        goalId: (route && route.goalId) || null,
      };
    }
    const queueId = res.result && res.result.jobId;
    threadMap.create(chatThreadId, { queueId });
    log('info', 'session-create job enqueued', { chatThreadId, queueId, route: route && route.kind, goalId: route && route.goalId, profile, workdir: home.workdir || null });
    return { forwarded: true, leg: 'session-create', intent: 'enqueue-job', queueId, route: route && route.kind, goalId: (route && route.goalId) || null };
  }

  // A follow-up in an already-mapped conversation → a send-message action-type
  // job on the chain's thread. NEVER send-to-session.
  async function forwardFollowUp({ chatThreadId, text, route }) {
    const entry = threadMap.get(chatThreadId);
    // Resolve the chain thread via inspect (D69) — the address for the message row.
    const resolved = await threadMap.resolveChainThread(chatThreadId, forwarder);
    if (!resolved.resolved) {
      // No chain thread yet: the session has not been dispatched, or the exec-id
      // is not yet known. Do NOT forward with a guessed thread (fail loud). The
      // reply stays with the owner's conversation state; a later turn consumes it
      // once the chain thread is resolvable.
      log('warn', 'follow-up not forwarded: chain thread unresolved', { chatThreadId, reason: resolved.reason });
      await postDeclineNotice(chatThreadId); // D111: honest notice, never silence, on a mapped conversation
      return { forwarded: false, leg: 'follow-up', reason: `chain-unresolved:${resolved.reason}` };
    }

    // D105 reply type: `answer` on a pending ask, else `note`.
    const replyType = entry && entry.pendingAsk ? 'answer' : 'note';
    if (!CMP8_TYPES.has(replyType)) {
      // Defensive: the closed vocabulary can never be violated from here.
      return { forwarded: false, leg: 'follow-up', reason: `bad-reply-type:${replyType}` };
    }

    const payload = {
      job_id: config.sendMessageJobId,
      args: { type: replyType, thread: resolved.chainThread, corpus: text },
      trigger_kind: 'scheduled',
      run_at: nowIsoUtc(),
    };
    const res = await forwarder.forward('enqueue-job', payload);
    if (!res.ok) {
      log('warn', 'follow-up send-message enqueue refused by gateway', { chatThreadId, error: res.error });
      await postDeclineNotice(chatThreadId); // D111: honest notice on a mapped conversation whose enqueue was refused
      return { forwarded: false, leg: 'follow-up', intent: 'enqueue-job', replyType, thread: resolved.chainThread, error: res.error };
    }
    if (replyType === 'answer') threadMap.setPendingAsk(chatThreadId, false); // the ask has now been answered
    log('info', 'follow-up send-message enqueued', { chatThreadId, replyType, thread: resolved.chainThread, route: route && route.kind, goalId: route && route.goalId, queueId: res.result && res.result.jobId });
    return { forwarded: true, leg: 'follow-up', intent: 'enqueue-job', replyType, thread: resolved.chainThread, queueId: res.result && res.result.jobId, route: route && route.kind, goalId: (route && route.goalId) || null };
  }

  // The single entry: an inbound chat message. Admission FIRST (chat-bridge-spec.md
  // Behavior #2) — a non-admitted principal is refused with NO forward. Then route
  // by whether the conversation already exists.
  //
  // `route` (task 7.58) is resolved by the bridge and says which surface the message
  // arrived on — 'master' (a DM, or a mention in an unmapped channel) or 'goal' (a
  // mapped goal channel). It never changes the ADMISSION decision (DEC-6's gate is
  // per-principal, not per-surface) and it never changes the forward CONTRACT (still
  // exactly two enqueue-job legs). It selects the launch profile AND the session's
  // workdir, and is logged, so a goal's traffic is attributable.
  //
  // THREE-VALUED, deliberately: an explicit `null` means the bridge RESOLVED the
  // surface and found it unattributable → refuse. `undefined` means no caller
  // supplied one at all (a pre-7.58 embedder) → master, the old behaviour. Collapsing
  // the two would either refuse legitimate callers or admit unattributable traffic.
  async function onChatMessage({ chatUserId, chatThreadId, text, route = { kind: 'master', goalId: null } }) {
    const admission = allowlist.check(chatUserId);
    if (!admission.allowed) {
      log('warn', 'chat message refused (not admitted) — no forward', { chatUserId, chatThreadId, reason: admission.reason });
      return { forwarded: false, refused: true, reason: admission.reason };
    }
    // Surface gate, AFTER admission (see the bridge's routeOf note): a message from
    // a channel that maps to no goal is unattributable and must never mint work.
    if (route === null) {
      log('warn', 'chat message refused — surface maps to no goal and is not a DM', { chatUserId, chatThreadId });
      return { forwarded: false, refused: true, reason: 'unroutable-surface' };
    }
    if (threadMap.has(chatThreadId)) {
      return forwardFollowUp({ chatThreadId, text, route });
    }
    return forwardSessionCreate({ chatThreadId, text, route });
  }

  return { onChatMessage, forwardSessionCreate, forwardFollowUp, CMP8_TYPES };
}

module.exports = { createForwardPath, CMP8_TYPES, DECLINE_NOTICE, NO_GOAL_SEAT_NOTICE, SEAT_BUSY_NOTICE, resolveGoalMasterSeat };
