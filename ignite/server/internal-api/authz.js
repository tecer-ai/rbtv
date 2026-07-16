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

  return { canRemoveQueueRow, principalsOf, PRINCIPALS };
}

module.exports = { createAuthzPolicy, tokenKindResolver, PRINCIPALS };
