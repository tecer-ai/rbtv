'use strict';

// The chat-user allowlist + OpenClaw-style DM pairing — the BRIDGE's OWN admission
// gate (chat-bridge-spec.md § Authorization & pairing model; D77(B)/D89).
//
// ⚑ WHAT THIS IS, AND IS NOT (D65(B), do NOT "repair"):
//   • It decides WHICH chat principals (Slack user IDs) may drive the bridge.
//     All allowlisted principals forward under the ONE bridge sender token, so
//     they SHARE the bridge's sender identity at the daemon — this gate bounds
//     WHO reaches the bridge; it does NOT isolate them at the daemon.
//   • It mints NO daemon-side principal, adds NO seat-identity check, and does
//     NOT extend the `kind` enum. The daemon's v1 authz (kind: owner OR
//     enqueued_by == authenticated sender-id) is deliberately weak and is NOT
//     this file's to fix. This is admission control, nothing more.
//
// DM PAIRING: an unknown chat principal's first contact is REFUSED and recorded
// as a pending pairing. The owner PAIRS it out-of-band (an owner-only action that
// adds the id to the allowlist). Pairing is the bridge admitting a chat id; it
// mints no daemon principal.

function createAllowlist({ allowed = [], logger = null } = {}) {
  // Set of admitted chat-user ids (Slack user IDs / Telegram chat IDs).
  const admitted = new Set(allowed.map(String));
  // Ids seen but not admitted — the owner's pairing queue. Recorded once per id.
  const pending = new Map(); // id -> { firstSeenAt, count }

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // The admission decision, taken BEFORE any forward (chat-bridge-spec.md
  // Behavior #2). Returns { allowed: boolean, reason }.
  function check(chatUserId) {
    const id = String(chatUserId);
    if (admitted.has(id)) return { allowed: true, reason: 'admitted' };
    // Record the pairing request — the owner pairs out-of-band.
    const prior = pending.get(id);
    if (prior) {
      prior.count += 1;
    } else {
      pending.set(id, { firstSeenAt: new Date().toISOString(), count: 1 });
      log('warn', 'chat principal refused — pending owner pairing', { chatUserId: id });
    }
    return { allowed: false, reason: 'not-paired' };
  }

  // Owner-only, out-of-band: admit a chat id (moves it out of the pending queue).
  function pair(chatUserId) {
    const id = String(chatUserId);
    admitted.add(id);
    pending.delete(id);
    log('info', 'chat principal paired (admitted)', { chatUserId: id });
    return { paired: true, id };
  }

  // Owner-only: revoke admission.
  function unpair(chatUserId) {
    const id = String(chatUserId);
    const had = admitted.delete(id);
    return { unpaired: had, id };
  }

  function isAdmitted(chatUserId) {
    return admitted.has(String(chatUserId));
  }

  // The owner's pairing queue (ids seen but not yet admitted).
  function pendingPairings() {
    return [...pending.entries()].map(([id, meta]) => ({ id, ...meta }));
  }

  function admittedIds() {
    return [...admitted];
  }

  return { check, pair, unpair, isAdmitted, pendingPairings, admittedIds };
}

module.exports = { createAllowlist };
