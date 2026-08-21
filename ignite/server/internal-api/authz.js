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
// ⚑ UPDATED BY TASK 7.10 — CMP-13 HAS NOW LANDED, and exactly as promised: one
// additional resolver (`seatPrincipalResolver`), NO call site changed.
//   • `master` and `leader` are now PROVABLE and are ARMED. The proof is a seat
//     resolved by MEASURING the connection, not a sender kind.
//   • The creator APPROXIMATION is NOT yet retired, and the two paragraphs above
//     still describe the shipped behaviour. Retiring it needs (a) the identity
//     columns in `sessions.csv` (task 7.37 — until then G-123 means NO live seat
//     resolves, so retiring would remove the only principal a live agent holds),
//     and (b) a column recording the enqueuing SEAT, which no table has. Issue
//     G-137 carries both. Until then this file's model is UNCHANGED for every
//     decision that rests on the approximation.
//
// ⚑ UPDATED BY TASK 7.389 — G-137's precondition (b) IS NOW MET; (a) IS NOT, so the retirement is
// STILL BLOCKED and the approximation STILL STANDS. `queue.enqueuing_seat` / `jobs_log.enqueuing_seat`
// are the column (b) said no table had, and `seatPrincipalResolver` now grants `creator-seat` off
// them as a genuine seat-to-seat check. What did NOT change, deliberately: the approximation in
// `tokenKindResolver` is untouched and armed. Dropping it while (a) stands would remove the only
// principal a live agent can hold — `p-g137-retirement-falsified-approximations-stay-armed` ruled
// precisely that, and it is why this task landed the column WITHOUT the retirement. The new grant
// is purely ADDITIVE (the chain unions), so it can only widen who holds `creator-seat`, never
// narrow it, and every pre-existing refusal path behaves exactly as it did.
// So the honest reading of "what v1 can prove" is now: owner (kind), master and leader (seat), and
// creator — a real SEAT check wherever a seat was proven at BOTH enqueue and call, and the
// unretired, shared-token-coarse approximation everywhere else. Assume the approximation unless
// you know both ends proved a seat.
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
    // TWO grants now reach this principal, and they are NOT the same claim — task 7.389 added the
    // second WITHOUT retiring the first (G-137's other half; see seatPrincipalResolver):
    //   1. the sender-id APPROXIMATION (`tokenKindResolver`) — a DEVICE identity compared to an
    //      audit column, exact only at 1:1 sender:seat and coarser under a shared token;
    //   2. the SEAT check (`seatPrincipalResolver`) — `enqueuing_seat === the proven seat`, which is
    //      what the ruling actually says and carries none of (1)'s coarseness.
    // While (1) stands, the WEAKER of the two is what a reader must assume held for any given
    // grant, so do not describe this principal as seat-based on the strength of (2) alone.
    enforcedInV1: true,
    provenBy: 'EITHER the seat check (enqueuing_seat === the CMP-13-proven seat, task 7.389) OR the older APPROXIMATION (enqueued_by === authenticated sender-id; exact only at 1:1 sender:seat, coarser under a shared token) — the approximation is NOT retired, so assume the weaker one',
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
    // for canRemoveQueueRow / canKillSession the moment any resolver
    // emitted the string — and adding a resolver is exactly what task 7.10 (CMP-13)
    // will do. That would silently widen three authorization decisions the 2026-07-25
    // ruling never touched. The window is real, not theoretical, and a code comment is
    // not a mechanism — so the flag is the mechanism. (Adversarial review, 2026-07-25.)
    // canRegisterJob does not consult this flag: it tests `sender.kind` directly, so
    // the approximation stays confined to the ONE decision that was ruled.
    enforcedInV1: false,
    provenBy: 'APPROXIMATION: sender.kind === "agent" — i.e. ANY enrolled agent token, not the master specifically',
  }),
  // ⚑ ARMED BY TASK 7.10, and this is a genuine WIDENING — say so rather than let it read as a
  // typo fix. D65(B) authorized these two all along; they were inert ONLY because no resolver
  // could prove them. `seatPrincipalResolver` now can, so the flag stops being a lie and starts
  // being a gate. Arming it makes master and leader authorized for canRemoveQueueRow /
  // canKillSession — which is what the ruling says, and what "the principals the
  // shipped policy records but cannot prove become enforceable" asks for.
  //
  // This is NOT the widening the `master-approximation` note above warns against. That warning is
  // about arming an APPROXIMATION (`kind === 'agent'`, i.e. any enrolled token) for three
  // decisions it was never ruled for. Here the principal is PROVEN — a specific seat, matched by
  // folder, descriptor, roster, live run and (pid, pid-starttime). The approximation stays
  // `enforcedInV1: false` and stays confined to canRegisterJob, exactly as that note requires.
  //
  // Inert in practice today: G-123 means no live seat resolves at all (see seatPrincipalResolver).
  master: Object.freeze({
    id: 'master',
    describes: 'the system-plane agent with system-wide oversight (registry concept, DRAFT)',
    enforcedInV1: true,
    provenBy: 'CMP-13 seat gate: the connection resolves to a seat named `master`, matched by folder + descriptor + roster + live run + (pid, pid-starttime)',
  }),
  leader: Object.freeze({
    id: 'leader',
    describes: 'the team agent that unblocks workers and is the sole team voice to the owner (registry concept, DRAFT)',
    enforcedInV1: true,
    provenBy: 'CMP-13 seat gate: the connection resolves to a seat named `leader`, matched by folder + descriptor + roster + live run + (pid, pid-starttime)',
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

// ── The CMP-13 seat principal resolver (task 7.10) ───────────────────────────
//
// This is the resolver every comment above promised: it lands as an ADDITIONAL entry in the chain
// and no call site changes. It reads `sender.seat` — a PROVEN seat, attached at the ingress by
// measuring the connection (gateway/sender-auth.js `attachProvenSeat`), never a claim the caller
// made — and answers which principals that seat holds.
//
// ⚑ WHAT IT PROVES, AND THE LINE UNDER IT. The gate proves WHICH SEAT the caller occupies: the
// folder, the descriptor naming that folder, the roster row, the live run, and the (pid,
// pid-starttime) match. It does NOT prove that seat's ROLE, because no record states one —
// measured 2026-07-27: `taskforce.csv`'s header is
// `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id`, with no `role` column
// anywhere. So the seat NAME is the mapping, declared in the table below rather than inferred by
// pattern-matching a string at a call site. When a role column exists, this table reads it and the
// function keeps its shape.
const SEAT_NAME_PRINCIPALS = Object.freeze({
  master: ['master'],
  leader: ['leader'],
});

// ⚠ RETIREMENT IS GATED ON TASK 7.37, AND SHIPPING IT UNGATED WOULD BE A SILENT REGRESSION.
//
// 7.10's criteria retire the sender-id creator APPROXIMATION. This does NOT do that yet, and the
// reason is measured, not cautious: G-123 — NEITHER live run's `sessions.csv` carries the `pid` /
// `pid-starttime` columns identity is decided on (run-2's header is
// `seat,session-id,harness,native-session-id,model,workdir,started,ended`; run-1's differs in
// order AND set). So the seat resolver refuses EVERY real seat today and `sender.seat` is
// undefined for all of them.
//
// Retiring an approximation now would therefore not tighten authorization — it would REMOVE the
// only principal any live agent can hold, turning register-job and cancel into owner-only, and it
// would do so at the NEXT DAEMON START, which no seat can perform. Fixtures would not catch it:
// a fixture writes the columns, so every test would pass on the one path that works.
//
// That is `p-green-harness-over-a-broken-mechanism` at the deployment layer, and it is the same
// shape the leader ruled on for the schema half of this task. So the approximations STAY ARMED and
// this resolver is purely ADDITIVE — it can only ever GRANT a principal, never remove one. The
// retirement is a one-line change (drop `master-approximation` from canRegisterJob and the
// creator branch from tokenKindResolver) and belongs to whoever lands 7.37's columns. Issue G-137.
//
// ⚑ `creator-seat` IS NOW RETURNED HERE — TASK 7.389 LANDED THE COLUMN THE PARAGRAPH BELOW SAID
// WAS MISSING, and the paragraph is kept because it is the reason the grant looks the way it does:
//
//   "`creator-seat` is NOT returned here either, and that is a SCHEMA fact rather than a choice:
//   `queue.enqueued_by` and `jobs_log.enqueued_by` are sender-ids and no column records the
//   enqueuing SEAT. Proving creator-seat needs that column."
//
// `queue.enqueuing_seat` / `jobs_log.enqueuing_seat` are that column (G-137 precondition (b)). This
// grant is a SEAT-TO-SEAT comparison — the proven seat behind the connection against the seat
// recorded at enqueue — so it is NOT the sender-id approximation `tokenKindResolver` still makes.
//
// ⚠ BUT IT DOES NOT REMOVE THAT APPROXIMATION'S SHARED-TOKEN COARSENESS, AND SAYING OTHERWISE IS
// THE EASY MISREADING. Two seats behind ONE token prove DIFFERENT seats here and this resolver
// refuses the second — and the request still succeeds, because `principalsOf` UNIONS the chain and
// `tokenKindResolver` granted `creator-seat` on `enqueued_by === sender.id` regardless. THE WEAKER
// GRANT IS DECISIVE while both are armed. So this resolver TIGHTENS nothing on its own; it adds a
// path that is exact where the approximation had none (a seat whose sender-id differs from the
// row's). The coarseness closes only at the RETIREMENT, which is G-137's other half and is blocked
// on task 7.37. `probe-remove-job` arm (f) pins this as a live assertion rather than a comment.
//
// ⚑ IT IS STILL PURELY ADDITIVE, which is what keeps it safe to ship beside the approximation. The
// resolver chain UNIONS what its members return (`principalsOf`), so this can only ever GRANT
// `creator-seat` to a caller the approximation would have refused — never REMOVE it from one the
// approximation grants. Retiring the approximation remains G-137's separate half and is NOT done
// here: doing both at once is what `p-g137-retirement-falsified-approximations-stay-armed` refused.
//
// ⚑ BOTH SIDES MUST BE NON-EMPTY STRINGS, and that is the load-bearing line rather than defensive
// noise. A row with no recorded seat holds NULL, an unproven caller holds no `seat`, and if either
// absence were allowed to compare equal to the other then EVERY unproven caller would hold
// `creator-seat` over EVERY pre-7.389 row — the exact inversion of what this column is for. The
// store normalizes `''` to NULL at both write sites for the same reason; this is the read-side half
// of that pair, so neither half is the only thing standing between absence and a grant.
function seatPrincipalResolver(sender, subject) {
  const held = [];
  if (!sender || typeof sender.seat !== 'string' || sender.seat.length === 0) return held;
  for (const p of SEAT_NAME_PRINCIPALS[sender.seat] || []) held.push(p);

  if (subject && typeof subject.enqueuing_seat === 'string' && subject.enqueuing_seat.length > 0
      && subject.enqueuing_seat === sender.seat) {
    held.push('creator-seat');
  }
  return held;
}

function createAuthzPolicy({ resolvers = [tokenKindResolver, seatPrincipalResolver] } = {}) {
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
  // added to `tokenKindResolver`: that resolver feeds canRemoveQueueRow / canKillSession
  // too, and widening it would silently loosen authorization decisions this ruling never
  // touched. Two mechanisms hold that confinement — this function tests `sender.kind`
  // directly rather than reading the PRINCIPALS flag, AND the `master-approximation` entry
  // is `enforcedInV1: false`, so even a future resolver that emitted the string could not
  // arm the other queries. (The flag half was added after adversarial review found the
  // comment alone was doing the work.) The set was THREE until task 7.29 retired
  // canDriveSession with the session surface it authorized.
  //
  // ⚑ `verb` (task 7.364) exists ONLY so the refusal can name the command the sender
  // actually typed. `deregister-job` shares this policy BY DESIGN, not by convenience:
  // both are catalogue WRITES, and the 2026-07-25 ruling's subject is who may change
  // what the daemon is ABLE to do — retiring a capability is that same subject. If a
  // later ruling splits them, split this function; never widen one caller quietly.
  function canRegisterJob({ sender, verb = 'register-job' }) {
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
        : `${verb} requires the owner or an enrolled AGENT token; you are ${seenAs}`,
    };
  }

  // Task 7.364 — the catalogue's DISABLE arm asks the SAME question as its create arm
  // (see canRegisterJob's `verb` note); only the name in the refusal differs.
  function canDeregisterJob({ sender }) {
    return canRegisterJob({ sender, verb: 'deregister-job' });
  }

  // May this attested sender record the OWNER'S ANSWER on a goal's coordination bus
  // (task 7.771, owner ruling 2026-08-11 § D8)?
  //
  // BRIDGE ONLY — the narrowest predicate in this module, and deliberately narrower than every
  // sibling above. The act is not "write a message": it is ASSERTING THAT THE HUMAN ANSWERED, and
  // the row it writes clears a seat's mechanical hold — since W2 that hold is the `HELD` verdict
  // `coord.py ready-seats` computes for ANY seat with an unanswered owner ask (universal: no
  // `fallback:` arm gates it), which `engine/seeding.js#recordView` reads to keep the seat's
  // dependents waiting.
  // A forged one lets a run walk past a question the owner never saw — the exact failure D8 exists
  // to prevent, reached through the door built to prevent it.
  //
  // ⚑ `kind: agent` IS REFUSED, and that is the whole point of the predicate: an ordinary seat
  // token could otherwise release its OWN hold. `enqueue-job` and `send-message` are open to an
  // agent token precisely because neither can do that.
  // ⚑ `kind: owner` IS REFUSED TOO — not because a human owner may not answer, but because he has
  // no need of this door: he is already at the seat's bus with `coordinate send` and at Slack with
  // the bridge. A kind with no caller is dead flexibility on an authorization surface. Widen it the
  // day something owner-shaped needs it, and say what.
  // ⚑ NOT ASKED THROUGH `principalsOf`, and the reason is `canRegisterJob`'s verbatim: the resolver
  // chain feeds canRemoveQueueRow / canKillSession too, so teaching it a bridge principal would
  // silently widen decisions this ruling never touched. This function tests `sender.kind` directly
  // and mints no PRINCIPALS entry, so nothing else can ever inherit the grant.
  function canRecordBusAnswer({ sender }) {
    const allowed = !!sender && sender.kind === 'bridge';
    const seenAs = !sender ? 'no attested sender at all'
      : (typeof sender.kind === 'string' && sender.kind
        ? `a ${sender.kind} token`
        : 'a sender carrying no attested kind');
    return {
      allowed,
      principals: allowed ? ['bridge'] : [],
      // S-3's rule, applied: state the predicate ACTUALLY ENFORCED and the kind SEEN.
      reason: allowed
        ? 'authorized as: the chat bridge'
        : `record-bus-answer requires the chat BRIDGE token; you are ${seenAs}`,
    };
  }

  function canSecretAdd({ sender }) {
    const SECRET_ADD_MASTERS = ['goal-master', 'channel-master', 'console-master'];
    const bareSeat = (sender && typeof sender.seat === 'string' && sender.seat.length > 0)
      ? (sender.seat.includes('/') ? sender.seat.split('/').pop() : sender.seat)
      : '';
    const owner = !!sender && sender.kind === 'owner';
    const provenMaster = !!sender && sender.kind === 'agent' && SECRET_ADD_MASTERS.includes(bareSeat);
    const agentApprox = !!sender && sender.kind === 'agent' && !bareSeat;
    const allowed = !!(owner || provenMaster || agentApprox);
    const seenAs = !sender ? 'no attested sender at all'
      : (bareSeat
        ? `a ${sender.kind || 'untyped'} token occupying proven seat '${bareSeat}'`
        : (typeof sender.kind === 'string' && sender.kind
          ? `a ${sender.kind} token`
          : 'a sender carrying no attested kind'));
    return {
      allowed,
      principals: allowed ? (owner ? ['owner'] : provenMaster ? ['secret-add-master'] : ['agent-approximation']) : [],
      reason: allowed
        ? `authorized as: ${owner ? 'owner' : provenMaster ? `proven master seat ${bareSeat}` : 'enrolled agent token (no proven seat)'}`
        : `secret-add requires the owner, a proven master seat (${SECRET_ADD_MASTERS.join(', ')}), or an enrolled AGENT token with no proven seat; you are ${seenAs}`,
    };
  }

  return { canRemoveQueueRow, canSnoozeWarning, canKillSession, canRegisterJob, canDeregisterJob, canRecordBusAnswer, canSecretAdd, principalsOf, PRINCIPALS };
}

module.exports = { createAuthzPolicy, tokenKindResolver, PRINCIPALS };
