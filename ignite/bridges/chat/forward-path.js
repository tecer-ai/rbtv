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
// otherwise see (his message did NOT land) and what happens next.
//
// ⚑ IT NO LONGER ASKS THE HUMAN TO RE-SEND (owner ruling 2026-08-11, task 7.541). The bridge
// re-submits the message itself when the seat frees (chat-bridge.js § pending re-submit). The old
// wording was an INSTRUCTION to re-send, and following it now would deliver the message twice —
// once by hand and once by the retry. So the wording and the guard shipped together: a manual
// re-send on the thread DROPS the pending retry, and the notice stops asking for one.
const SEAT_BUSY_NOTICE = "⚠ that work is still busy with the previous message — yours was NOT delivered yet; it will be sent again automatically as soon as it frees";

// The give-up twin of the notice above: the seat stayed busy past the retry window, so the
// re-submit was abandoned. Only HERE does the owner get told to send it again — and by then there
// is no pending retry left to double with.
const SEAT_BUSY_GAVE_UP_NOTICE = "⚠ that work stayed busy — your message was NOT delivered, please send it again";

// The FOURTH honest refusal (ratified 2026-08-09): the owner replied in an agent's own thread,
// but that agent's seat is no longer on disk — it was never materialized, or it was cleaned up.
// Nothing is enqueued, and the owner is told in the thread he typed in, because silence there
// reads as the agent ignoring him. Fixed string, no internals: which seat and which goal are the
// deployment's business, not chat's.
const NO_AGENT_SEAT_NOTICE = "⚠ that agent's seat is no longer open — its thread can't be answered";

// Where a session on a GOAL surface is HOMED: a named seat of that goal.
//   <workspaceRoot>/.rbtv/goals/<goalId>/seats/<seatName>
//
// ⚠ GOAL-DIRECT SINCE 7.607 (E3). This used to read the goal's `runs.csv` for a `state=open` row
// and compose `runs/<run-id>/seats/<seat>` — the SECOND independent parser of that register
// (inventory #36), reading a stored status to answer a question that was never about liveness.
// A seat folder is GOAL-DURABLE now (design-lock items 1 and 8): the seat either exists on disk
// or it does not, and that is the whole question a session home has to answer. The register read
// could only ever have made this WRONG — a goal whose row read `closed` had its live goal-master
// declared unreachable, and a goal whose row read `open` after the room died resolved a seat dir
// under a run folder that no longer exists.
//
// Every step is a refusal point, and each returns a REASON rather than a fallback: an
// unresolvable seat must never degrade into launching at some default workdir, where the
// session would run with no descriptor and no goal identity at all.
//
// ⚑ THE SEAT NAME IS A PARAMETER (ratified 2026-08-09), because there are now two homes on
// the goal surface and they answer different questions. Channel traffic goes to the goal's
// standing `goal-master` — the surface has no other addressee. A reply in an AGENT'S OWN
// THREAD goes to THAT AGENT's seat: the owner is answering the seat that asked, and homing the
// answer anywhere else is what would need a relay to carry the question back — the exact thing
// the no-LLM-in-the-middle ruling forbids. `goal-master` stays the default, so every existing
// caller is byte-identical in behaviour.
//
// ⚑ THE NAME IS VALIDATED, because it now comes from a bus row's `from:` field rather than
// from a literal in this file. A name carrying `..` or a separator would resolve a seat dir
// OUTSIDE the goal — and that dir becomes a session's cwd.
//
// ⚑ `owner` IS A RESERVED ADDRESS, NEVER A SEAT (ruling `d-agents-address-owner-not-master`): no
// seat may carry the name, so a seat dir called `owner` is a question with no answer and is
// refused rather than resolved. Without this a goal that materialized such a folder would make
// the bus's owner ADDRESS resolvable as a session home.
const SEAT_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const RESERVED_SEAT_NAME = 'owner';

function resolveGoalSeat(workspaceRoot, goalId, seatName = 'goal-master') {
  if (!workspaceRoot) return { ok: false, reason: 'no-workspace-root-configured' };
  if (!SEAT_NAME_RE.test(String(seatName))) return { ok: false, reason: 'seat-name-not-a-name' };
  if (String(seatName) === RESERVED_SEAT_NAME) return { ok: false, reason: 'owner-is-reserved' };
  const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', String(goalId));
  try {
    if (!fs.statSync(goalDir).isDirectory()) return { ok: false, reason: 'no-such-goal' };
  } catch { return { ok: false, reason: 'no-such-goal' }; }
  const seatDir = path.join(goalDir, 'seats', String(seatName));
  // The seat must EXIST — a goal can exist with the seat never materialized (or checked out and
  // cleaned up), and launching at a path that is not there is the failure this check exists to
  // make visible.
  try {
    if (!fs.statSync(seatDir).isDirectory()) return { ok: false, reason: 'seat-missing', seat: String(seatName), seatDir };
  } catch { return { ok: false, reason: 'seat-missing', seat: String(seatName), seatDir }; }
  return { ok: true, seatDir, seat: String(seatName) };
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
  // 'agent' rides the GOAL profile: an agent thread is goal work seen through one seat's
  // conversation, not cold-contact intake — and minting a third profile key would be a config
  // surface nobody asked for (ratified 2026-08-09).
  //
  // ⚑ THIS NAMES THE FALLBACK, NOT THE MODEL A SEAT RUNS ON (ruling D19, 2026-08-11). The profile
  // resolved here used to be the whole answer, and that was the defect: reviving an agent thread
  // launched the DEPLOYMENT'S chat profile at that agent's seat, so a seat cast `claude-fable-5`
  // in `taskforce.csv` and in its own `seat.md` ran `claude-sonnet-5` whenever the owner answered
  // it in Slack. The fix is NOT here and deliberately so — a seat's cast must win on every lane,
  // not only this one, and the bridge holds no profile roster to resolve it against (it knows
  // three profile NAMES from its own config and nothing about `spawn-profiles.yaml`, which is the
  // boundary `probe-chat-boundary` enforces). Resolution is DAEMON-SIDE, at the one point every
  // launch passes through: `server/spawn/spawn.js#profileForSeatCast`, over the shared catalog in
  // `launch-profiles/catalog.js`.
  //
  // So what this function returns is what a seat runs when it declares NO cast — the channel
  // master, by design (`materialize-seats.py#open_binding`: "the master's harness and model are
  // named by the chat bridge at spawn time"), which is precisely the case this surface split was
  // built for. Nothing here changed at D19, and nothing here should: the bridge names a fallback
  // and the seat's own record outranks it.
  function profileFor(route) {
    if (route && (route.kind === 'goal' || route.kind === 'agent')) return config.goalProfile || config.sessionProfile;
    return config.masterProfile || config.sessionProfile;
  }

  // The reasoning RUNG that rides with the profile, MASTER SURFACE ONLY (owner ruling
  // `d-0811lp-effort-lane-build-now`, 2026-08-11). Goal and agent traffic carry no effort key and
  // run the harness default — there is no `goal_effort`, and inventing one would be a config
  // surface nobody asked for (the same call `profileFor`'s header records for the third profile key).
  // ⚠ IT IS PAIRED WITH THE PROFILE, NOT INDEPENDENT OF IT: a rung is 1..N in the ladder THAT
  // profile declares, so `master_profile.py` writes the two together and clears the rung whenever
  // the profile changes without one. A rung surviving a switch to a shorter-laddered harness would
  // refuse at the spawn, one owner message later.
  function effortFor(route) {
    if (route && (route.kind === 'goal' || route.kind === 'agent')) return null;
    return config.masterEffort ?? null;
  }

  // WHERE the session runs, by surface. Master/mention traffic uses the configured
  // `workdir` as it always has. GOAL traffic is homed at that goal's OPEN run's
  // goal-master seat, so the session boots inside the seat folder whose descriptor
  // chain IS its identity — the reason the prompt can be the bare user text.
  //
  // 'agent' traffic (ratified 2026-08-09) is homed at THE ASKING AGENT'S OWN seat. That is what
  // makes the owner's reply reach the asker with NO relay in the middle: a session-create there
  // REVIVES that seat headless with the reply as its prompt, and a follow-up rides the chain the
  // seat already holds. The seat's descriptor supplies the identity, exactly as for goal-master.
  // Returns { ok, workdir } or { ok: false, reason } — never a fallback.
  function workdirFor(route) {
    if (!route || (route.kind !== 'goal' && route.kind !== 'agent')) return { ok: true, workdir: config.workdir || null };
    const seat = resolveGoalSeat(config.workspaceRoot, route.goalId, route.kind === 'agent' ? route.agent : 'goal-master');
    if (!seat.ok) return seat;
    return { ok: true, workdir: seat.seatDir, seat: seat.seat };
  }

  // A first message that STARTS work → a session-creating launch-agent job.
  // `retry` — this call IS the automatic re-submit of a message the door already refused
  // (chat-bridge.js § pending re-submit). Everything about the leg is identical; the ONE
  // difference is that a second seat-busy refusal posts NO notice. The owner was told once, and
  // a notice per poll pass would turn one honest line into a stream of them.
  async function forwardSessionCreate({ chatThreadId, text, route, retry = false }) {
    const profile = profileFor(route);
    if (!profile) {
      // A launch-agent job MUST name a profile (DEC-1 R3; the store re-validates it
      // exists). Missing config is a loud refusal, never a silent malformed forward.
      return { forwarded: false, leg: 'session-create', reason: 'no-session-profile-configured' };
    }
    const home = workdirFor(route);
    if (!home.ok) {
      // Nothing is enqueued. The owner gets a fixed notice on the surface he typed on, because
      // the fix — seating a goal-master on the goal, or accepting that an agent's seat is
      // gone — is a human act. The two surfaces get DIFFERENT notices: they name different acts.
      const isAgent = Boolean(route && route.kind === 'agent');
      log('warn', 'goal-surface session-create refused: no seat resolved', { chatThreadId, kind: route && route.kind, goalId: route && route.goalId, agent: route && route.agent, reason: home.reason });
      await postDeclineNotice(chatThreadId, isAgent ? NO_AGENT_SEAT_NOTICE : NO_GOAL_SEAT_NOTICE);
      return { forwarded: false, leg: 'session-create', reason: `${isAgent ? 'no-agent-seat' : 'no-goal-master-seat'}:${home.reason}`, goalId: (route && route.goalId) || null };
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
    // Only present when configured, so a deployment on the pre-ruling `chat-agent` job id — whose
    // args_schema admits no `effort` — is unaffected and enqueues exactly what it always did.
    const effort = effortFor(route);
    if (effort !== null) payload.args.effort = effort;

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
    //
    // ⚑ ON THE 'agent' LEG THIS DOOR IS THE WHOLE REVIVE MECHANISM, not a hazard to work around
    // (ratified 2026-08-09): a session-create at the asking agent's seat REVIVES it when its
    // chain is dead, and when a live turn still holds that seat the door suppresses the create
    // and the owner gets the seat-busy notice below — honest, and the same answer every other
    // shared-seat surface gets.
    if (res.result && res.result.deduped) {
      log('warn', 'session-create suppressed at the door — seat busy, NOTHING enqueued', {
        chatThreadId, route: route && route.kind, goalId: route && route.goalId,
        heldQueueId: res.result.jobId, because: res.result.because, seatKey: res.result.seat_key,
      });
      if (!retry) await postDeclineNotice(chatThreadId, SEAT_BUSY_NOTICE);
      // The undelivered text rides the REFUSAL — and since task 7.541 it has a PRODUCTION reader:
      // `chat-bridge.js` records it as a pending re-submit and this same leg re-fires it when the
      // seat frees. (It also still serves the older degraded path — routeBusRowToMaster falls
      // through to posting the row raw on a not-forwarded result.)
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
  //
  // ⚑ `corrective` — THE REPLY LEG'S REVIVE TURN (owner ruling 2026-08-10, reply-contract design
  // decision 7) rides this exact leg rather than a second enqueue path, because it IS the same
  // act: a message onto an existing chain, consumed at the next turn boundary. Two things must
  // differ, and only two:
  //   1. it is never an `answer`. A corrective turn responds to no `ask`, so consuming a pending
  //      one would mark the owner's real question answered by a schema complaint.
  //   2. it posts NO decline notice. The notices exist to tell the OWNER his message did not
  //      land; on a corrective turn the owner sent nothing, and "couldn't route your reply" in
  //      his thread would be a lie about an act he never performed. A refused corrective is
  //      returned to the reply leg instead, which delivers best-effort.
  async function forwardFollowUp({ chatThreadId, text, route, corrective = false }) {
    const entry = threadMap.get(chatThreadId);
    // Resolve the chain thread via inspect (D69) — the address for the message row.
    const resolved = await threadMap.resolveChainThread(chatThreadId, forwarder);
    if (!resolved.resolved) {
      // No chain thread yet: the session has not been dispatched, or the exec-id
      // is not yet known. Do NOT forward with a guessed thread (fail loud). The
      // reply stays with the owner's conversation state; a later turn consumes it
      // once the chain thread is resolvable.
      log('warn', 'follow-up not forwarded: chain thread unresolved', { chatThreadId, corrective, reason: resolved.reason });
      if (!corrective) await postDeclineNotice(chatThreadId); // D111: honest notice, never silence, on a mapped conversation
      return { forwarded: false, leg: 'follow-up', corrective, reason: `chain-unresolved:${resolved.reason}` };
    }

    // D105 reply type: `answer` on a pending ask, else `note` — and a corrective turn is always a
    // `note` (it answers nothing; see the header).
    const replyType = !corrective && entry && entry.pendingAsk ? 'answer' : 'note';
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
      log('warn', 'follow-up send-message enqueue refused by gateway', { chatThreadId, corrective, error: res.error });
      if (!corrective) await postDeclineNotice(chatThreadId); // D111: honest notice on a mapped conversation whose enqueue was refused
      return { forwarded: false, leg: 'follow-up', corrective, intent: 'enqueue-job', replyType, thread: resolved.chainThread, error: res.error };
    }
    if (replyType === 'answer') threadMap.setPendingAsk(chatThreadId, false); // the ask has now been answered
    log('info', 'follow-up send-message enqueued', { chatThreadId, corrective, replyType, thread: resolved.chainThread, route: route && route.kind, goalId: route && route.goalId, queueId: res.result && res.result.jobId });
    return { forwarded: true, leg: 'follow-up', corrective, intent: 'enqueue-job', replyType, thread: resolved.chainThread, queueId: res.result && res.result.jobId, route: route && route.kind, goalId: (route && route.goalId) || null };
  }

  // The single entry: an inbound chat message. Admission FIRST (chat-bridge-spec.md
  // Behavior #2) — a non-admitted principal is refused with NO forward. Then route
  // by whether the conversation already exists.
  //
  // `route` (task 7.58) is resolved by the bridge and says which surface the message
  // arrived on — 'master' (a DM, or a mention in an unmapped channel), 'goal' (a
  // mapped goal channel), or 'agent' (a thread in a goal channel that a named agent opened,
  // ratified 2026-08-09). It never changes the ADMISSION decision (DEC-6's gate is
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

  // `profileFor`/`workdirFor` are exposed so the WARM leg (live-sessions.js) resolves a
  // conversation's profile and home through THESE functions rather than a second copy of the
  // surface rules. A warm session must run the same profile at the same seat the cold path would
  // have used, or the two paths are two different agents wearing one thread.
  return { onChatMessage, forwardSessionCreate, forwardFollowUp, profileFor, workdirFor, CMP8_TYPES };
}

module.exports = { createForwardPath, CMP8_TYPES, DECLINE_NOTICE, NO_GOAL_SEAT_NOTICE, NO_AGENT_SEAT_NOTICE, SEAT_BUSY_NOTICE, SEAT_BUSY_GAVE_UP_NOTICE, resolveGoalSeat };
