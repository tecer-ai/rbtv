'use strict';

// THE FORWARD-PATH CONTRACT (chat-bridge-spec.md § Forward path, D104/D105) — the
// heart of the bridge. A chat message from an ADMITTED principal becomes ONE of
// exactly two gateway calls, both `enqueue-job` (the bridge adds NO new intent —
// D90; the set stays SEVEN, and the bridge speaks only add-job here):
//
//   1. FIRST message in a new chat thread  → a SESSION-CREATING job:
//        enqueue-job naming a launch-agent function (7.787: and nothing about execution)
//        (DEC-1 R3). The bridge NEVER spawns; the ticker's Dispatch phase does.
//
//   2. FOLLOW-UP in an already-mapped thread → a `send-message` ACTION-TYPE job
//        addressed to the mapped turn-chain's thread (`exec-<first exec_id>`).
//        Reply type is PINNED (D105): `answer` when it responds to a pending
//        `ask`, else `note` — from the closed CMP-8 vocabulary (mint nothing).
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

// The EIGHT CMP-8 message types (closed vocabulary — mint nothing; W4 closed it at seven and D2's
// routed types widened it to eight with `stuck`).
// Only `answer` and `note` are produced by the follow-up leg per D105; the full set is stated
// so a future producer never invents a ninth. See heart-store.js MESSAGE_TYPES for the site list.
const CMP8_TYPES = new Set(['completion', 'ask', 'answer', 'verdict', 'note', 'queue-request', 'escalation', 'stuck']);

// D111 part 2 — the honest decline notice. When a MAPPED conversation's follow-up
// cannot reach the running work (chain unresolved, or the gateway refused the
// enqueue), the owner sees this ONE fixed line instead of silence. Fixed string,
// NO internals (never leak a reason / thread / queue id into chat).
const DECLINE_NOTICE = "⚠ couldn't route your reply to the running work — please try again shortly";

// The same mechanics for the OTHER honest refusal: goal-channel traffic that has no
// goal-master seat to land in. The refusal is unchanged (nothing enqueued). The notice
// tells the owner WHERE to reply — an agent thread already open in this channel — because
// "seat a goal-master" is not an act this workspace has. Empty-channel fallback is fixed
// text; live threads are enumerated (agent name + Slack permalink), no internals.
const NO_GOAL_SEAT_NOTICE = "⚠ no goal-master seat is open for this goal — no agent thread is open yet in this channel — an agent will open one when it needs you";

function slackThreadPermalink(channelId, threadTs) {
  const p = String(threadTs).replace('.', '');
  return `https://slack.com/archives/${channelId}/p${p}`;
}

function formatNoGoalSeatNotice({ channelId, threads } = {}) {
  const live = [];
  for (const t of threads || []) {
    if (!t || !t.agent || !t.threadTs) continue;
    live.push({ agent: String(t.agent), threadTs: String(t.threadTs) });
  }
  live.sort((a, b) => a.agent.localeCompare(b.agent));
  if (live.length === 0) return NO_GOAL_SEAT_NOTICE;
  const lines = live.map((t) => {
    const url = channelId ? slackThreadPermalink(channelId, t.threadTs) : null;
    return url ? `• *${t.agent}* — <${url}|thread>` : `• *${t.agent}*`;
  });
  return `⚠ no goal-master seat is open for this goal — reply in an agent thread:\n${lines.join('\n')}`;
}

// The THIRD notice, same mechanics again — and since `on_seat_busy: 'queue'` (P2) it is no longer
// a REFUSAL. The seat is busy with a live turn, so the daemon puts this message in its persistent
// queue and launches it when the turn finishes. The owner cannot see any of that, so he is told the
// one fact that matters: it is queued and it will be delivered.
//
// ⚑ IT NO LONGER ASKS THE HUMAN TO RE-SEND, and it no longer promises a BRIDGE-side re-send either
// (the pending-retry machinery is deleted — chat-bridge.js). A manual re-send would now be a
// SECOND queued row, which is exactly the double this wording exists to prevent.
//
// ⚑ IT STILL RIDES THE `deduped` BRANCH, which is reachable only if the daemon REJECTS or ignores
// the flag — an honest "not delivered yet" is then still the truth, so one string serves both.
const SEAT_BUSY_NOTICE = "⚠ that work is busy with the previous message — yours is queued behind it and will be delivered as soon as that finishes";

// The FOURTH honest refusal (ratified 2026-08-09): the owner replied in an agent's own thread,
// but that agent's seat is no longer on disk — it was never materialized, or it was cleaned up.
// Nothing is enqueued, and the owner is told in the thread he typed in, because silence there
// reads as the agent ignoring him. Fixed string, no internals: which seat and which goal are the
// deployment's business, not chat's.
const NO_AGENT_SEAT_NOTICE = "⚠ that agent's seat is no longer open — its thread can't be answered";

// The FIFTH honest refusal (2026-08-12, root-cause report § secondary defect 3): the GATEWAY
// refused the session-create outright — down, timing out, token rejected, payload re-validated
// away. Nothing was enqueued and nothing will retry it, so this branch was the one TRUE SILENCE
// left in the forward path: every sibling refusal above notifies, and this one logged a warn and
// returned while the owner watched an empty thread. Fixed string, no internals — a gateway error
// code is deployment business, and the owner's act is the same whatever it says.
const GATEWAY_REFUSED_NOTICE = "⚠ couldn't start work on that message — it was NOT delivered, please send it again shortly";

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

// The daemon's bound on `seat_shard` (gateway/parse.js and heart-store.js both enforce it). Checked
// HERE only so a thread id that could not satisfy it degrades to an unsharded enqueue instead of
// taking the owner's message down with a shape refusal — see the guard at the enqueue.
const SEAT_SHARD_RE = /^[^\s#]{1,200}$/;

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

function createForwardPath({ forwarder, threadMap, allowlist, config, logger = null, deliver = null, listAgentThreads = null }) {
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

  // ── THE OWNER ANSWERED: SAY SO ON THE BUS (task 7.771, owner ruling 2026-08-11 § D8) ─────────
  //
  // A reply in an AGENT'S OWN THREAD is delivered as a session-create at that seat's home — and
  // until this call NOTHING recorded anywhere that the ask had been answered. The coordination bus
  // kept every question and no reply, so nothing could see the pairing close and a run could walk
  // past a question the owner had answered. The pairing is now read by `coord.py ready-seats`,
  // which reports a seat with an unanswered owner ask as `HELD` (W2 — for every seat, with no
  // `fallback:` arm and no ferry-delivery gate deciding who qualifies); `engine/seeding.js
  // #recordView` treats that set as the seats whose dependents wait. This row is what releases it.
  //
  // ⚑ ONE GATEWAY CALL, NO SPAWN, NO SECOND WRITER. This subtree may not hold a child process
  // (`chat-bridge-spec.md` lines 14/26; `probes/probe-chat-boundary.js` scans every runtime `.js`
  // here and derives its file list from the directory), and `coordination/messages.md` may not gain
  // a JavaScript writer. So the bridge asks and the DAEMON acts — `engine/bus-answer.js` shells to
  // `coord.py send --type answer`, the file's one writer. Same split `live-sessions.js:10-15`
  // describes for the warm-session manager, for the same structural reason.
  //
  // ⚑ `kind: 'agent'` ONLY. A top-level message in a GOAL channel is the owner INITIATING with the
  // goal, not answering a seat, and writing an `answer` there would falsely clear goal-master's
  // open ask. Master/DM traffic has no seat and no bus at all.
  //
  // ⚑ DELIVERY NEVER FAILS BECAUSE THE BOOKKEEPING FAILED. The reply reaching the seat is the
  // load-bearing act and it has ALREADY HAPPENED when this runs. Every failure — gateway refusal,
  // transport down, coord refusing, a throw — is logged loudly and changes NEITHER the outcome nor
  // the exit path: the return value below is decoration on an already-successful result.
  //
  // ⚑ ONE IMPLEMENTATION, THREE CONSUMERS — owner review, 2026-08-11. "The owner answered" is ONE
  // FACT, and the first cut of this recorded it on the session-create leg ONLY. That is the same
  // single-source-of-truth defect this design exists to delete: `onChatMessage` forks on
  // `threadMap.has()` (legitimately — reviving a dead seat and speaking to a live one are different
  // acts) and `chat-bridge.js` tries the WARM path ahead of both, so one owner turn can arrive
  // through any of THREE doors. Recording it at one door meant building the same thing again at
  // the other two. Now every door calls THIS function; only the guard below is shared.
  //
  // ⚑ THE CALL STAYS ON EACH DOOR'S OWN SUCCESS PATH, and is NOT hoisted into `onChatMessage`
  // ahead of the fork. The reply has not been delivered at that point, and the seat-busy/deduped
  // branch deliberately does NOT deliver — it posts a decline notice and the text is re-submitted
  // later by `chat-bridge.js`. An answer recorded there would assert the owner answered while
  // nothing had reached the seat. Each door's honest success condition differs, and each states it:
  //   · session-create — the enqueue was accepted AND not suppressed at the idempotent door
  //   · follow-up      — same, plus NOT a corrective redispatch (below)
  //   · warm           — the session ANSWERED (`chat-bridge.js`), which is proof the owner's words
  //                      were consumed; whether the agent's reply then posted to Slack is a
  //                      different question and does not un-answer it
  // EXACTLY ONE fires per owner turn: a warm answer returns before the forward path is reached, and
  // the fork below is exclusive. No double write is possible by construction.
  async function recordBusAnswer({ route, text }) {
    if (!route || route.kind !== 'agent' || !route.goalId || !route.agent) return null;
    try {
      const res = await forwarder.forward('record-bus-answer', {
        goal: String(route.goalId), seat: String(route.agent), corpus: String(text || ''),
      });
      if (!res.ok) {
        log('warn', 'the owner\'s answer was DELIVERED but NOT recorded on the bus — the seat\'s ask stays open to every reader', { goalId: route.goalId, agent: route.agent, error: res.error });
        return { recorded: false, error: (res.error && res.error.code) || 'unknown' };
      }
      if (!res.result || res.result.recorded !== true) {
        log('warn', 'the owner\'s answer was DELIVERED but the daemon recorded no bus row', { goalId: route.goalId, agent: route.agent, reason: res.result && res.result.reason });
        return { recorded: false, reason: (res.result && res.result.reason) || 'unknown' };
      }
      log('info', 'recorded the owner\'s answer on the seat\'s coordination bus', { goalId: route.goalId, agent: route.agent, msgId: res.result.msg_id, re: res.result.re });
      return { recorded: true, msgId: res.result.msg_id, re: res.result.re };
    } catch (err) {
      log('warn', 'recording the owner\'s answer on the bus THREW — the reply was still delivered', { goalId: route.goalId, agent: route.agent, error: err.message });
      return { recorded: false, error: err.message };
    }
  }

  // ── THE TRANSPORT NAMES NO EXECUTION (launch-cast unification, owner ruling D2, 2026-08-11) ──
  //
  // This used to be a per-SURFACE profile choice (`master_profile` for DMs, `goal_profile` for
  // goal/agent threads) plus a master-only effort rung — so which harness, model and reasoning
  // level an agent ran at depended on where its message arrived from. The failure that earned this
  // rewrite: `plan-interviewer`, cast `claude-fable-5` at `effort: high` in its own `seat.md` and
  // in `taskforce.csv`, answered every Slack turn as `claude-sonnet-5` at the harness default.
  //
  // D19 had already ruled the seat's cast outranks the caller's profile — but it was enforced only
  // at `spawn()`, and the WARM leg (`server/spawn/live-sessions.js`) never went through `spawn()`.
  // So message #1 of a thread ran the cast and every message after it ran the transport's value,
  // at the same seat, in the same thread. Both doors resolve identically now, and an uncast seat
  // REFUSES (`catalog.js#E_UNCAST_SEAT`) instead of inheriting whatever the bridge carried.
  //
  // ⚠ AND `sessionProfile` IS GONE TOO (`#d-abolish-profile-names`, 2026-08-12). It was the last
  // remnant — a value that decided nothing, kept alive only because `launch-agent` required a
  // non-empty `profile` argument. That argument no longer exists, so `profileFor()` is deleted
  // rather than left returning a value with no consumer. The enqueue below carries `{prompt}` and,
  // where the surface homes one, `{workdir}` — and the workdir is the SEAT, which is the only
  // thing that decides what runs.

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
  //
  // ⚑ `master: true` ON THE FALLBACK ARM. Every DM/mention thread lands on that arm and gets the ONE
  // configured workdir, so the daemon's seat key was identical for all of them and the seat-busy
  // gate serialized every conversation the owner had. The flag is what lets the two callers that
  // must shard per conversation (this file's enqueue, chat-bridge's pre-enqueue guards) tell that
  // arm apart WITHOUT re-deriving the route predicate — one spelling of "is this the master seat?".
  function workdirFor(route) {
    if (!route || (route.kind !== 'goal' && route.kind !== 'agent')) return { ok: true, workdir: config.workdir || null, master: true };
    const seat = resolveGoalSeat(config.workspaceRoot, route.goalId, route.kind === 'agent' ? route.agent : 'goal-master');
    if (!seat.ok) return seat;
    return { ok: true, workdir: seat.seatDir, seat: seat.seat };
  }

  function sameWorkdir(a, b) {
    if (!a || !b) return false;
    return String(a).replace(/\/+$/, '') === String(b).replace(/\/+$/, '');
  }

  // Live-turn at this seat folder (staff-wake and chat-launch use different seat keys for the
  // same folder, so findSeatHolder on the chat job's key would miss the sitting). Ticker
  // `live_sessions` is the live-turn arm. Fail-open: an unreadable ticker enqueues as today.
  async function findLiveHolder(home) {
    if (!home || !home.workdir || home.master) return null;
    try {
      const res = await forwarder.inspect('ticker');
      if (!res || !res.ok) return null;
      const live = (res.result && res.result.live_sessions) || [];
      return live.find((s) => sameWorkdir(s.workdir, home.workdir)) || null;
    } catch {
      return null;
    }
  }

  async function nudgeLiveSitting({ workdir, text, execId, chatThreadId }) {
    try {
      const payload = {
        conversation: chatThreadId ? String(chatThreadId) : `seat:${workdir}`,
        prompt: String(text || ''),
        workdir,
        start: false,
      };
      if (execId != null && Number.isInteger(Number(execId))) payload.exec_id = Number(execId);
      const res = await forwarder.forward('live-feed', payload);
      if (!res.ok || !(res.result && res.result.fed)) {
        log('warn', 'live-holder nudge did not feed a warm session — NOTHING was delivered; falling through to a queued session-create', {
          workdir, execId, reason: (res.result && res.result.reason) || (res.error && res.error.code) || 'not-fed',
        });
        return { nudged: false, reason: (res.result && res.result.reason) || 'not-fed' };
      }
      return { nudged: true };
    } catch (err) {
      log('warn', 'live-holder nudge THREW — NOTHING was delivered; falling through to a queued session-create', { workdir, error: err.message });
      return { nudged: false, error: err.message };
    }
  }

  // A first message that STARTS work → a session-creating launch-agent job.
  //
  // ⚠ THE `retry` PARAMETER IS GONE (P2). It existed for ONE caller — `chat-bridge.js#retryPending`
  // — whose whole machinery is deleted now that the DAEMON queues a message that arrives at a busy
  // seat. Nothing re-fires this leg, so the two `!retry` notice guards below are gone with it: every
  // refusal notifies, unconditionally, which is what they did for every other caller anyway.
  async function forwardSessionCreate({ chatThreadId, text, route }) {
    const home = workdirFor(route);
    if (!home.ok) {
      // Nothing is enqueued. The owner gets a notice on the surface he typed on. Agent-thread
      // traffic names the missing seat; goal-channel traffic names the live agent threads he
      // can reply into (or says none are open). Refusal is unchanged.
      const isAgent = Boolean(route && route.kind === 'agent');
      log('warn', 'goal-surface session-create refused: no seat resolved', { chatThreadId, kind: route && route.kind, goalId: route && route.goalId, agent: route && route.agent, reason: home.reason });
      const threads = (!isAgent && typeof listAgentThreads === 'function' && route && route.goalId)
        ? listAgentThreads(route.goalId)
        : [];
      const notice = isAgent ? NO_AGENT_SEAT_NOTICE : formatNoGoalSeatNotice({ channelId: chatThreadId, threads });
      await postDeclineNotice(chatThreadId, notice);
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
    // ── A LIVE SITTING AT THIS SEAT: TRY TO FEED IT, AND FALL THROUGH IF IT CANNOT BE FED ──────
    //
    // ⚠ THIS BRANCH LOST AN OWNER MESSAGE (measured 2026-08-20 01:20:35Z, goal
    // `meet-transcript-summarizer`). It used to call `recordBusAnswer` and then return
    // `forwarded: true` whatever the nudge said, logging "bus write still stands". Two things were
    // false at once. `recordBusAnswer` is `kind: 'agent'` ONLY — deliberately, see its header: a
    // top-level post in a GOAL channel is the owner INITIATING, and recording an `answer` there
    // would falsely clear goal-master's open ask — so on the goal route it returned `null` before
    // writing anything. And the nudge only ever feeds a WARM session, while goal traffic rides the
    // headless model, so `no-warm-session` is its ordinary answer. Nothing was written, nothing was
    // enqueued, no thread was mapped — and the bridge logged a success. A whole-goal-folder scan
    // found no trace of the owner's text anywhere.
    //
    // So the nudge is now an OPTIMISATION with two honest outcomes, and neither drops the message:
    //   FED     → the live turn consumed the text. Map the thread and bind it to the holder's
    //             exec-id, which is the chain-stable address (`exec-<exec_id>`) the reply leg
    //             ferries the answer back on. Without this the owner got no reply path at all.
    //   NOT FED → fall through to the ordinary session-create below. `on_seat_busy: 'queue'` makes
    //             a busy seat LOSSLESS: the daemon holds the row and launches it when the seat
    //             frees, which is the path that demonstrably delivered on the sibling goal the same
    //             minute. A refusal there still posts the owner a notice.
    const holder = await findLiveHolder(home);
    if (holder) {
      log('info', 'live sitting at this seat — trying to feed it before enqueueing', {
        chatThreadId, route: route && route.kind, goalId: route && route.goalId,
        workdir: home.workdir, execId: holder.exec_id, status: holder.status,
      });
      const nudge = await nudgeLiveSitting({
        workdir: home.workdir, text, execId: holder.exec_id, chatThreadId,
      });
      const busAnswer = await recordBusAnswer({ route, text });
      const delivered = { forwarded: true, liveHolder: true, leg: 'session-create', execId: holder.exec_id,
        route: route && route.kind, goalId: (route && route.goalId) || null, nudge, ...(busAnswer ? { busAnswer } : {}) };
      if (busAnswer && busAnswer.recorded === true) {
        // AGENT route: the bus row IS the delivery — the seat reads its inbox at its next
        // checkin — and the agent thread carries its own reply address, so nothing is mapped here.
        return delivered;
      }
      if (nudge.nudged) {
        // The live turn consumed the text. Map the thread and bind the holder's exec-id so the
        // reply leg has the chain-stable address (`exec-<exec_id>`) to ferry the answer back on.
        threadMap.create(chatThreadId, { queueId: null });
        threadMap.bindSessionExecId(chatThreadId, holder.exec_id);
        log('info', 'fed the live sitting and mapped the thread to its chain', {
          chatThreadId, execId: holder.exec_id, route: route && route.kind, goalId: route && route.goalId,
        });
        return delivered;
      }
      log('warn', 'live sitting was NOT fed and no bus row was recorded — NOTHING delivered; falling through to a queued session-create', {
        chatThreadId, execId: holder.exec_id, route: route && route.kind, goalId: route && route.goalId,
        nudgeReason: nudge.reason || nudge.error || null,
      });
    }

    const prompt = chatThreadId ? `chat-thread: ${chatThreadId}\n\n${text}` : text;
    const payload = {
      job_id: config.sessionJobId,
      // The user text, behind at most the one correlation line above — the seat's descriptor
      // carries behaviour (see the header).
      args: { prompt },
      session_mode: 'headless',                 // chat rides the headless model (notes §7b)
      trigger_kind: 'scheduled',
      run_at: nowIsoUtc(),                      // due now: the next tick dispatches it
      // ⚑ QUEUE, DON'T DEDUPE (P2). The idempotent door's default is `dedupe`: a create arriving
      // while the seat holds a live turn is suppressed and its args — the owner's text — DISCARDED.
      // The bridge held that text and re-fired it, which is a queue reimplemented in a transport
      // that restarts. `queue` hands the row to the daemon's own persistent queue instead, launched
      // oldest-first when the seat frees. A daemon that does not know the flag falls back to its
      // dedupe behaviour and the `deduped` branch below still tells the owner the truth.
      on_seat_busy: 'queue',
    };
    if (home.workdir) payload.args.workdir = home.workdir;
    // ⚑ ONE SHARD PER CONVERSATION, ON THE MASTER SURFACE ONLY. `queue` above made a busy seat
    // lossless; it did not make it CONCURRENT, and on this surface the seat is shared by every DM
    // the owner has. So thread B's question waited behind thread A's turn — in order, delivered,
    // and half an hour late. The shard suffixes the daemon's seat key with this thread id, which
    // splits the gate exactly where the conversations are: two threads no longer see each other,
    // and two messages of ONE thread still serialize, because they carry the SAME shard.
    //
    // ⚠ MASTER ONLY, deliberately. A goal or agent thread homes at a REAL seat that is coordinating
    // a live taskforce; running two of those side by side in one seat folder is a different question
    // with a different answer, and it is not being answered here.
    //
    // ⚠ SHAPE-GUARDED HERE, AND FAIL-OPEN IS THE POINT. A shard the gateway would refuse takes the
    // WHOLE enqueue down with it — the owner's message would be lost to a formatting rule. A thread
    // id that does not fit (none does today: `D0BJ50Y1DC6:1786501607`) simply goes unsharded, which
    // is the serialized behaviour that shipped before this line.
    if (home.master && chatThreadId && SEAT_SHARD_RE.test(String(chatThreadId))) {
      payload.seat_shard = String(chatThreadId);
    }
    // NO `effort` KEY (launch-cast unification, 2026-08-11). The rung is the SEAT's declaration
    // now, read daemon-side off its descriptor at both launch doors — so putting one on the wire
    // here would be the transport naming execution again, in the one field it still touches.

    const res = await forwarder.forward('enqueue-job', payload);
    if (!res.ok) {
      log('warn', 'session-create enqueue refused by gateway', { chatThreadId, error: res.error });
      await postDeclineNotice(chatThreadId, GATEWAY_REFUSED_NOTICE);
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
      await postDeclineNotice(chatThreadId, SEAT_BUSY_NOTICE);
      // The undelivered text still rides the REFUSAL. Its pending-re-submit reader is gone (P2), but
      // the older degraded path remains: routeBusRowToMaster falls through to posting the row raw on
      // a not-forwarded result, and a caller that must not lose a payload should be able to see it.
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
    log('info', 'session-create job enqueued', { chatThreadId, queueId, route: route && route.kind, goalId: route && route.goalId, workdir: home.workdir || null });
    const busAnswer = await recordBusAnswer({ route, text });
    return { forwarded: true, leg: 'session-create', intent: 'enqueue-job', queueId, route: route && route.kind, goalId: (route && route.goalId) || null, ...(busAnswer ? { busAnswer } : {}) };
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
      // is not yet known. Do NOT forward with a guessed thread.
      //
      // `exec-id-unknown` used to be a TERMINAL decline (D111 notice, nothing
      // enqueued). That wedged both live goal channels on 2026-08-20: a no-spawn
      // disarm left the conversation mapped, every later owner post was read as a
      // follow-up to a chain that could never resolve, and each was declined.
      // A follow-up whose chain cannot be resolved now FALLS BACK to a fresh
      // session-create. The owner's message must always produce a sitting.
      // Other unresolved reasons (inspect-failed, unknown-conversation) still
      // decline — those are transient or unattributable, not a dead mapping.
      // A corrective turn is the reply-leg's own redispatch: the owner sent
      // nothing, so it must not mint a sitting.
      if (!corrective && resolved.reason === 'exec-id-unknown') {
        log('warn', 'follow-up chain unresolved — falling back to a fresh session-create', { chatThreadId, reason: resolved.reason });
        threadMap.drop(chatThreadId);
        const created = await forwardSessionCreate({ chatThreadId, text, route });
        return { ...created, fallback: 'exec-id-unknown' };
      }
      log('warn', 'follow-up not forwarded: chain thread unresolved', { chatThreadId, corrective, reason: resolved.reason });
      if (!corrective) await postDeclineNotice(chatThreadId);
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
    // THE SAME FACT, THIS DOOR (owner review 2026-08-11 — see `recordBusAnswer`'s header). Two
    // conditions ride with it here that the session-create leg does not have, and neither is a
    // style choice:
    //
    // ⚑ NOT A CORRECTIVE REDISPATCH — ruled, not inherited by accident. `chat-bridge.js` calls this
    // leg with `corrective: true` as the reply contract's REVIVE turn: the BRIDGE re-asking a
    // worker that returned a malformed reply. The owner sent nothing and said nothing, so recording
    // an `answer` on his behalf would clear a seat's hold on the strength of a schema complaint.
    // This is the same reasoning this function's own header already gives for why a corrective
    // posts no decline notice ("the owner sent nothing") and is never typed `answer`.
    //
    // ⚑ NOT `replyType === 'answer'`, THOUGH IT LOOKS LIKE THE OBVIOUS GATE — IT IS DEAD CODE.
    // `replyType` is `answer` only when `entry.pendingAsk`, and NOTHING SETS THAT TRUE in this
    // deployment: `setPendingAsk(true)` fires only from `deliverToOwner({ markAsk: true })`, and
    // every live call site passes `markAsk: false` (`reply-leg.js:489` says why — "ask-detection
    // out of scope v1"). A ferried agent ask does not set it either: `routeToAgentThread` posts
    // through `transport.sendToOwner`, which never touches the flag. So gating on it would look
    // exactly right, read as the tighter check, and never once fire — on the precise surface this
    // whole row exists for. Grep before restoring it.
    //
    // ⚑ AND NOT WHILE THE DOOR SUPPRESSED THE ENQUEUE. `heart-store.js#enqueue` returns
    // `{ deduped: true }` BEFORE the INSERT and DISCARDS the payload — the owner's corpus with it —
    // and its own comment makes the rule general: "a caller that must not lose its payload MUST
    // read `deduped` rather than treating a returned id as delivery." Whether a `send-message` job
    // can key that door depends on whether its catalogue row is HOMED, which is deployment state,
    // not something this file can know — so the write requires unambiguous delivery instead of
    // guessing. ⚠ This leg's own `forwarded: true` is UNCHANGED and still ignores `deduped`, which
    // is a latent gap the session-create leg does not have. Named here, not fixed here.
    const busAnswer = !corrective && !(res.result && res.result.deduped)
      ? await recordBusAnswer({ route, text })
      : null;
    return { forwarded: true, leg: 'follow-up', corrective, intent: 'enqueue-job', replyType, thread: resolved.chainThread, queueId: res.result && res.result.jobId, route: route && route.kind, goalId: (route && route.goalId) || null, ...(busAnswer ? { busAnswer } : {}) };
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

  // `workdirFor` is exposed so the WARM leg (live-sessions.js) resolves a conversation's home
  // through THIS function rather than a second copy of the
  // surface rules. A warm session must run at the same seat the cold path would
  // have used, or the two paths are two different agents wearing one thread.
  //
  // ⚑ `recordBusAnswer` IS EXPOSED FOR EXACTLY THAT REASON, one fact further on. The warm leg is
  // the THIRD door an owner answer can arrive through and it never touches either leg above
  // (`chat-bridge.js` returns before the forward path when a warm session answers), so without
  // this the same defect the owner caught on 2026-08-11 would simply reappear there. The bridge
  // calls THIS function; it does not get a second copy of the rule, exactly as it does not get a
  // second copy of the surface rules.
  return { onChatMessage, forwardSessionCreate, forwardFollowUp, workdirFor, recordBusAnswer, CMP8_TYPES };
}

module.exports = { createForwardPath, CMP8_TYPES, DECLINE_NOTICE, NO_GOAL_SEAT_NOTICE, formatNoGoalSeatNotice, NO_AGENT_SEAT_NOTICE, SEAT_BUSY_NOTICE, GATEWAY_REFUSED_NOTICE, resolveGoalSeat };
