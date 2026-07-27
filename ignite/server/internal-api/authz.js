'use strict';

// Cancel-authorization policy (owner ruling D65(B); build shape ADX-20 §2).
//
// ────────────────────────────────────────────────────────────────────────────
// READ THIS BEFORE "FIXING" ANYTHING HERE. The model below is KNOWINGLY WEAKER
// than the policy it records. That is an OWNER DECISION (D65(B)), not an
// oversight, and it is recorded at the seam deliberately rather than silently
// approximated into "close enough".
// ────────────────────────────────────────────────────────────────────────────
//
// THE POLICY (all four principals, recorded in full — the ruling):
//   • master        — the system-plane agent with system-wide oversight
//                     (registry concept, status DRAFT)
//   • leader        — the team agent that unblocks workers and is the sole team
//                     voice to the owner (registry concept, status DRAFT)
//   • creator seat  — the SEAT that queued the job. A `seat` is executor + task,
//                     a workflow node addressed via a slot (e.g. `client-x/leader`).
//                     "creator" is NOT a registry term and does NOT mean "sender".
//   • owner         — the human.
//
// WHAT v1 CAN ACTUALLY PROVE — three of the four: NO.
//   The ratified sender registry is `{sender-id, kind: owner|agent|bridge,
//   token-hash, enabled}` (spawn-profiles-spec.md:70). A master, a leader, and an
//   ordinary worker are ALL merely `kind: agent` — the ingress cannot tell them
//   apart. D15 DEFERRED the CMP-13 seat-identity gate (the checker that resolves
//   an agent's seat from the folder it runs from) behind a pluggable resolver
//   seam. And senders are DEVICES/BRIDGES, so `enqueued_by` (a sender-id) is NOT
//   a seat address.
//
// SO v1 ENFORCES EXACTLY TWO:
//   1. owner   — `kind: 'owner'` may cancel anything.
//   2. creator APPROXIMATION — `enqueued_by === authenticated sender-id` may
//      cancel their own. ⚑ THIS IS AN APPROXIMATION, NOT A SEAT CHECK. It is
//      exact ONLY where a sender maps 1:1 to a seat, and it is COARSER than the
//      ruling wherever a token is SHARED: every seat behind a shared `agent`
//      token can cancel another seat's job. Do not describe it as seat-based.
//
// `master`, `leader`, and true seat-identity are RECORDED below as authorized
// principals but are INERT in v1 — no such sender kind exists and the resolver
// that would prove them is deferred. They activate ADDITIVELY when CMP-13 lands:
// a new resolver is registered here, and NO call site changes.
//
// EXPLICITLY DECLINED (D65(B) — do not "improve" these):
//   • extending the sender `kind` enum with master/leader — it would bake two
//     DRAFT registry terms into the ingress AUTH schema before ratification;
//   • building the CMP-13 seat-identity checker — out of v1 scope.
//
// This is a POLICY MODULE, not scattered `if`s at the call site: every
// authorization question in the internal API is asked here and nowhere else.

// The authorized principals, in full (the ruling). `enforcedInV1` records —
// honestly and in code — which of them the shipped runtime can actually prove.
const PRINCIPALS = Object.freeze({
  owner: Object.freeze({
    id: 'owner',
    describes: 'the human owner',
    enforcedInV1: true,
    provenBy: 'sender.kind === "owner" in the ratified senders_file',
  }),
  'creator-seat': Object.freeze({
    id: 'creator-seat',
    describes: 'the seat that queued the job (seat = executor + task)',
    // Enforced only as the sender-id APPROXIMATION below — never as a seat check.
    enforcedInV1: true,
    provenBy: 'APPROXIMATION: enqueued_by === authenticated sender-id (exact only at 1:1 sender:seat; coarser under a shared token)',
  }),
  // The master APPROXIMATION (owner ruling 2026-07-25, task 7.12, build (ii)) —
  // recorded here so the honest name of what is enforced appears beside the honest
  // name of what is meant. It is NOT reachable from the resolver chain: only
  // canRegisterJob adds it, so the three authorization decisions that predate this
  // ruling are unaffected by its presence. Retire it when CMP-13 lands (task 7.10).
  'master-approximation': Object.freeze({
    id: 'master-approximation',
    describes: 'stands in for `master` until the seat-identity gate can prove one',
    // ⚑ enforcedInV1 is FALSE ON PURPOSE, and canRegisterJob still honours this
    // principal — the two are not in conflict, so do not "fix" either one.
    // WHY: every OTHER query here authorizes with
    //   principals.some(p => PRINCIPALS[p] && PRINCIPALS[p].enforcedInV1)
    // over whatever the RESOLVER CHAIN returned. Marking this entry true would arm it
    // for canRemoveQueueRow / canDriveSession / canKillSession the moment any resolver
    // emitted the string — and adding a resolver is exactly what task 7.10 (CMP-13)
    // will do. That would silently widen three authorization decisions the 2026-07-25
    // ruling never touched. The window is real, not theoretical, and a code comment is
    // not a mechanism — so the flag is the mechanism. (Adversarial review, 2026-07-25.)
    // canRegisterJob does not consult this flag: it tests `sender.kind` directly, so
    // the approximation stays confined to the ONE decision that was ruled.
    enforcedInV1: false,
    provenBy: 'APPROXIMATION: sender.kind === "agent" — i.e. ANY enrolled agent token, not the master specifically',
  }),
  master: Object.freeze({
    id: 'master',
    describes: 'the system-plane agent with system-wide oversight (registry concept, DRAFT)',
    enforcedInV1: false,
    provenBy: null, // no such sender kind exists; CMP-13 resolver deferred (D15)
  }),
  leader: Object.freeze({
    id: 'leader',
    describes: 'the team agent that unblocks workers and is the sole team voice to the owner (registry concept, DRAFT)',
    enforcedInV1: false,
    provenBy: null, // no such sender kind exists; CMP-13 resolver deferred (D15)
  }),
});

// ── The resolver seam (D15's pluggable sender-identity resolver, server side) ──
//
// A principal resolver answers ONE question: which principals does this attested
// sender hold, for this subject row? v1 ships `tokenKindResolver` — everything it
// can prove comes from the ratified senders_file shape plus the row's own
// `enqueued_by`. The CMP-13 seat-identity resolver lands here as an ADDITIONAL
// entry in the chain; it will be able to return 'master'/'leader'/'creator-seat'
// truthfully, and no caller of `canRemoveQueueRow` changes when it does.
function tokenKindResolver(sender, subject) {
  const held = [];
  if (!sender || typeof sender !== 'object') return held;

  if (sender.kind === 'owner') held.push('owner');

  // The creator APPROXIMATION. See the header: this compares a DEVICE identity to
  // an audit column, not a seat to a seat.
  if (subject && typeof subject.enqueued_by === 'string' &&
      typeof sender.id === 'string' && sender.id.length > 0 &&
      subject.enqueued_by === sender.id) {
    held.push('creator-seat');
  }

  // 'master' and 'leader' are UNREACHABLE from this resolver by construction —
  // the ratified `kind` enum is owner|agent|bridge and carries no way to assert
  // either. That absence is the honest v1 answer, not a gap to paper over.
  return held;
}

function createAuthzPolicy({ resolvers = [tokenKindResolver] } = {}) {
  function principalsOf(sender, subject) {
    const held = new Set();
    for (const resolve of resolvers) {
      for (const p of resolve(sender, subject) || []) held.add(p);
    }
    return Array.from(held);
  }

  // May this attested sender remove this queue row?
  // Returns { allowed, principals, reason } — a DECISION as data, never a throw:
  // the caller maps a denial onto the ratified UNAUTHORIZED_SENDER wire code.
  function canRemoveQueueRow({ sender, row }) {
    const principals = principalsOf(sender, row);
    const allowed = principals.some((p) => PRINCIPALS[p] && PRINCIPALS[p].enforcedInV1);
    return {
      allowed,
      principals,
      reason: allowed
        ? `authorized as: ${principals.join(', ')}`
        : 'the attested sender is neither the owner nor the sender that enqueued this row',
    };
  }

  // May this attested sender SNOOZE a standing warning? OWNER-ONLY (owner rulings
  // D45 / D71): the MASTER may snooze and v1's owner IS the master; a warning is
  // SYSTEM-raised, so — unlike canRemoveQueueRow — there is NO creator seat to
  // approximate, and the sender-id creator APPROXIMATION deliberately does NOT apply
  // here. Only the `owner` principal (proven by `kind: owner`) is authorized;
  // `master` and `leader` stay INERT in v1 exactly as they do for removal, and the
  // `kind` enum is NOT extended (D65(B) deliberately-weak model). Returns a DECISION
  // as data — the caller maps a denial onto the ratified UNAUTHORIZED_SENDER wire
  // code. `subject` is passed null so the creator approximation is unreachable by
  // construction, never merely unused.
  function canSnoozeWarning({ sender }) {
    const principals = principalsOf(sender, null);
    const allowed = principals.includes('owner') && PRINCIPALS.owner.enforcedInV1;
    return {
      allowed,
      principals,
      reason: allowed
        ? 'authorized as: owner'
        : 'snooze is owner-only; the attested sender is not the owner',
    };
  }

  // May this attested sender DRIVE this headed session — inject keystrokes into it
  // (`send-to-session`) or read its rendered screen (`capture-session-screen`)?
  //
  // OWNER RULING D89: both Batch-6 session-surface intents REUSE the D65(B) model — the SAME
  // model canRemoveQueueRow applies: `kind: owner` OR the creator APPROXIMATION
  // (`enqueued_by === authenticated sender-id`). NOT owner-only (that is snooze's model,
  // D45/D71 — a warning is SYSTEM-raised so there is no creator to approximate; a session HAS
  // one, so removal's model is the fit). The `subject` row here is the jobs_log row, which
  // carries `enqueued_by` exactly as a queue row does (schema.sql:56).
  //
  // ⚑ There is NO second implementation of the model here: the principal resolution lives
  // ONCE, in the resolver chain (`tokenKindResolver` → `principalsOf`), and this function only
  // asks the question for this action — the same one-question-per-function shape
  // canRemoveQueueRow and canSnoozeWarning already use. When the CMP-13 seat-identity resolver
  // lands it registers in that ONE chain and this call site does not change.
  //
  // ⚑ This is a DEVICE-identity approximation of a creator — NOT a seat check. Do not describe
  // it as seat-based (D65(B)); wherever a token is SHARED it is COARSER than the ruling: every
  // seat behind a shared `agent` token can drive another seat's session.
  function canDriveSession({ sender, row }) {
    const principals = principalsOf(sender, row);
    const allowed = principals.some((p) => PRINCIPALS[p] && PRINCIPALS[p].enforcedInV1);
    return {
      allowed,
      principals,
      reason: allowed
        ? `authorized as: ${principals.join(', ')}`
        : 'the attested sender is neither the owner nor the sender that enqueued this session',
    };
  }

  // May this attested sender KILL this session — the spawn module's kill surface
  // (TERM → grace → KILL of the whole tree, status → `killed`)?
  //
  // OWNER RULING D65(B), applied to kill by the cli-expansion run (ce-4): kill follows the
  // SAME v1 policy as cancel — `kind: owner` may kill anything; the creator APPROXIMATION
  // (`enqueued_by === authenticated sender-id`) may kill their own. NOT owner-only (that is
  // snooze's model — a warning is SYSTEM-raised so there is no creator to approximate; a
  // session HAS one, so removal's model is the fit, exactly as D89 reasoned for the session
  // surface). The `subject` row is the jobs_log row, which carries `enqueued_by` exactly as
  // a queue row does.
  //
  // ⚑ There is NO second implementation of the model here: the principal resolution lives
  // ONCE, in the resolver chain (`tokenKindResolver` → `principalsOf`), and this function
  // only asks the question for this action — the same one-question-per-function shape the
  // three queries above use. When the CMP-13 seat-identity resolver lands it registers in
  // that ONE chain and this call site does not change.
  //
  // ⚑ This is a DEVICE-identity approximation of a creator — NOT a seat check. Do not
  // describe it as seat-based (D65(B)); wherever a token is SHARED it is COARSER than the
  // ruling: every seat behind a shared `agent` token can kill another seat's session.
  function canKillSession({ sender, row }) {
    const principals = principalsOf(sender, row);
    const allowed = principals.some((p) => PRINCIPALS[p] && PRINCIPALS[p].enforcedInV1);
    return {
      allowed,
      principals,
      reason: allowed
        ? `authorized as: ${principals.join(', ')}`
        : 'the attested sender is neither the owner nor the sender that enqueued this session',
    };
  }

  // May this attested sender REGISTER a catalogue job — add to the set of things the
  // daemon is ABLE to do (task 7.12)?
  //
  // OWNER RULING 2026-07-25 (Call 1): "humans AND the master agent"; ordinary worker
  // agents are refused. The owner was then given the two builds that ruling admits and
  // chose (ii) — the MASTER APPROXIMATION below — with the exposure stated.
  //
  // ⚑ THE MASTER APPROXIMATION — READ THIS BEFORE "FIXING" IT.
  //   The daemon CANNOT prove a sender is the master: the ratified sender kinds are
  //   owner|agent|bridge, and a master, a leader, and an ordinary worker are ALL merely
  //   `kind: agent` (see this file's header). Until the CMP-13 seat-identity gate lands
  //   (task 7.10, blocked on seats existing at all), "the master" is approximated as
  //   `kind: 'agent'` — i.e. ANY sender holding an enrolled agent token.
  //   The exposure this buys, stated plainly and ACCEPTED by the owner at the ruling:
  //   any agent behind that token can extend what the daemon is able to do. It is the
  //   same shape as the creator approximation above, one step wider, on a more
  //   consequential subject — registration changes what the system CAN do, where
  //   enqueue only changes WHEN it does something already sanctioned.
  //   `kind: 'bridge'` is REFUSED: a chat bridge relays other people's words and is not
  //   a master under any reading of the ruling.
  //   When CMP-13 lands, DELETE the approximation branch — the resolver chain will
  //   return a truthful 'master' and this function keeps its shape.
  //
  // The approximation is asked HERE, in the one policy module, and deliberately NOT
  // added to `tokenKindResolver`: that resolver feeds canRemoveQueueRow /
  // canDriveSession / canKillSession too, and widening it would silently loosen three
  // authorization decisions this ruling never touched. Two mechanisms hold that
  // confinement — this function tests `sender.kind` directly rather than reading the
  // PRINCIPALS flag, AND the `master-approximation` entry is `enforcedInV1: false`, so
  // even a future resolver that emitted the string could not arm the other three
  // queries. (The flag half was added after adversarial review found the comment alone
  // was doing the work.)
  function canRegisterJob({ sender }) {
    const principals = principalsOf(sender, null);
    const owner = principals.includes('owner') && PRINCIPALS.owner.enforcedInV1;
    const masterApprox = !!sender && sender.kind === 'agent';
    if (masterApprox) principals.push('master-approximation');
    const allowed = owner || masterApprox;
    // ── S-3: the refusal names the predicate ACTUALLY ENFORCED and the sender kind SEEN ──────
    // It used to read "register-job is owner-and-master-only". That sentence asserted a gate that
    // DOES NOT EXIST — `PRINCIPALS.master` is `enforcedInV1: false, provenBy: null`, there is no
    // master sender kind in v1 at all — while CONCEALING the one that does: `owner || kind ===
    // 'agent'`, i.e. any enrolled agent token. It also pointed at the owner as the route, and the
    // cost was measured: a seat reported an owner-only act it could not perform, the leader relayed
    // that unchecked, and a command was one step from being handed to the owner that no owner
    // needed to run. An error message is evidence of a REFUSAL, never of a POLICY.
    //
    // So: state the real predicate, and state what this sender was seen AS — "you are a bridge
    // token; this needs an agent token" ends it in one read. `master` is deliberately not named,
    // here or anywhere a caller can see: naming a principal the runtime cannot prove is the defect.
    const seenAs = !sender ? 'no attested sender at all'
      : (typeof sender.kind === 'string' && sender.kind
        ? `a ${sender.kind} token`
        : 'a sender carrying no attested kind');
    return {
      allowed,
      principals,
      reason: allowed
        ? `authorized as: ${principals.join(', ')}`
        : `register-job requires the owner or an enrolled AGENT token; you are ${seenAs}`,
    };
  }

  return { canRemoveQueueRow, canSnoozeWarning, canDriveSession, canKillSession, canRegisterJob, principalsOf, PRINCIPALS };
}

module.exports = { createAuthzPolicy, tokenKindResolver, PRINCIPALS };
