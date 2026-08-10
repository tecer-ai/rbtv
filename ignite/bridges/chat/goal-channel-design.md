# goal↔channel — the two settled answers (task 7.58, `B1-bridge`)

Authored by the `comm-bridge` seat of run-1 / build-core-daemon-mvp, 2026-07-27 ~04:10 UTC,
BEFORE the implementation it governs. Task 7.58 carries two points the registry deliberately
left OPEN as Phase-7 build output (`concepts/channel.md` § v1 realization: *"The per-goal
channel's creation and close-time lifecycle (archive, retire) are OPEN — Phase-7 build output,
flagged not ruled"*). This file settles both, states why, and FLAGS each for registry
transcription. **Nothing here is applied to `system-definition/` from this project** — the
transcription is a separate act by whoever owns the registry (task 7.58 criterion 5).

Terminology per the KG (`sd-graph show channel` / `show thread`), not re-derived here:
**channel** = the transport a goal `thread` maps 1:1 onto; **thread** = the goal's message
registry; v1's interim thread handle is the chain-stable `exec-<first exec_id>`
(`concepts/thread.md` § v1 interim handle).

---

## (a) Channel CREATION — who, and when

**SETTLED: the BRIDGE creates it, at GOAL REGISTRATION, through one idempotent
name-derived call — `ensureGoalChannel(goalId)`.**

Three parts, each load-bearing:

1. **Who: the bridge.** Creation needs the Slack workspace credential
   (`conversations.create`, bot token). The daemon holds no chat credential and must not grow
   one — the bridge is the ONE process that speaks to the chat transport
   (`chat-bridge-spec.md`, and the boundary `probe-chat-boundary` enforces). Putting creation
   anywhere else means either duplicating a secret or adding a second Slack client. So the
   *decision* to register a goal belongs to the goal machinery; the *act* of creating its
   channel belongs to the bridge, invoked by that machinery.

2. **When: at goal registration**, not lazily on first message. A goal that exists with no
   channel has an unaddressable owner surface; the 1:1 invariant should hold from the goal's
   birth, not from its first message. This matches the registry's own open question wording
   ("who creates the per-goal channel and when (at goal registration?)") and matches
   `r-763-grammar-ruled` D4 — *a goal is born complete and validates immediately*.

3. **How: NAME-DERIVED and IDEMPOTENT.** The channel name is derived from the goal id by a
   pure function (`{prefix}{sanitized-goal-id}`), so the goal→channel mapping is
   RECOVERABLE FROM THE WORKSPACE ALONE. This is the property that makes the whole design
   work in v1: the bridge's state is in-memory and a restart forgets it (the same owner-known
   caveat as `thread-map` and `replyAddr`). Because the name is derived, a restarted bridge
   re-derives every mapping from `conversations.list` — no store handle, no persistence, no
   new capability. `conversations.create` returning `name_taken` is therefore not an error but
   the ADOPT path: resolve the existing channel by name and bind it.

**The caller (settled 2026-08-08, task C3): the daemon's ticker, at a goal's *run start*** —
`server/ticker/goal-channel-start.js`, gated on `one-live-run.js#isRunStart` and on the goal
resolving `interactive` through `seat-folder.js#goalKind` (owner ruling `d-owner-batch1` (2)).
It launches the CLI's own `ensure` verb as a child process, so the boundary in (1) holds
unchanged: the daemon composes an argv and never touches a token. Requires the systemd
carrier — the credential reaches the child only as `EnvironmentFile=`, which the setsid
carrier cannot set.

> **History (the pre-C3 degrade, superseded).** When this file was authored the
> goal-registration hook did not exist: under the pre-ruled degrade (`milestone-dag.md` §1 /
> this seat's briefing, Branch B3) the settled answer shipped as the CALLABLE surface
> (`ensureGoalChannel`) with the hook as its named build follow-up, and the channel was
> created by an explicit hand call. Task 7.63's `rbtv goal scaffold` was then named as the
> natural caller; C3 rejected scaffold-time creation because a goal may be scaffolded long
> before it ever runs, and an unrun goal's channel is an empty room. The answer was never
> degraded — only its caller was, and C3 closed that.

### Membership — the owner is INVITED at real-goal-channel creation

> **SUPERSEDED 2026-08-10 (owner ruling, issue C-3).** The paragraph this replaces read:
> *"**Never-invite, by construction.** The bridge has NO `conversations.invite` code path at
> all. Membership is a human act in the Slack UI. This is what makes `r-slack-etiquette`'s
> 'the owner is added to NO test channel' mechanically true rather than a policy nobody
> enforces — a probe asserts the string's absence from the source, the same shape as
> `probe-chat-boundary`."*

**SETTLED: the bridge invites the OWNER, and only the owner, into a REAL goal channel at the
moment it CREATES it. Four conjunctive conditions, all probe-asserted:**

1. **Owner only.** The one id resolved by `config.js` as `ownerUser` (config `owner_user`,
   defaulting to the first allowlist entry — the allowlist exists for the owner). Never a
   list, never a discovered member, never a second target.
2. **Real goals only.** Refused whenever the deployment's `channelPrefix` is a test namespace
   (`test-` / `test_`). The prefix bounds every name this map can create, so guarding on it
   guards the whole test surface — which is exactly and only what `r-slack-etiquette`
   protects.
3. **Resolution, not just creation** *(AMENDED by task 7.680, 2026-08-10 — was "creation
   only", the `created: true` arm alone)*. Both resolving arms of `ensureChannel` — created
   AND adopted — ensure the owner is in the channel; the call is idempotent at the Slack edge
   (`already_in_channel` is benign success). The creation-only rule left every channel created
   before the invite shipped (pre-2026-08-10 11:55) **permanently ownerless**: re-running
   `ensure` adopted the channel and invited nobody, and the `meeting-transcript-digest` goal
   sat blocked ~14 h on interview questions the owner could not see. Re-running `ensure` is
   now the repair path, and the daemon re-ensures at every workflow run start, so orphaned
   channels self-heal. `recover()` still never invites — it is a bulk map rebuild at boot,
   not the resolution of a channel about to carry goal traffic.
4. **Graceful degradation.** An invite refusal (missing scope, restricted workspace) is logged
   loudly and then discarded. Channel creation, the binding, and the goal's message flow never
   depend on it: the channel is the goal's surface whether or not the owner is in it yet.

**Why never-invite existed, and why it over-reached.** The construction made a real guarantee
cheap: an absence in the source cannot be forgotten under pressure at 4 AM, unlike a policy.
But the guarantee it was purchased for — `r-slack-etiquette` — is scoped to **test/throwaway
channels and overnight DM timing** ("no DM to the owner before morning, `test-*` channels
only"), not to every channel the bridge will ever make. Forbidding the whole mechanism to
enforce a rule about one namespace also forbade auto-inviting the owner into a channel the
owner had *just asked to be created*, leaving a manual join on every real goal. The mechanism
now exists in `slack-socket-mode.js#inviteToChannel`; the narrowness moved to the one caller,
where the etiquette rule's actual scope is expressed as condition 2 rather than as an absence.

**Required scope:** `channels:write.invites` (public) / `groups:write.invites` (private).
Absent, condition 4 carries it: every creation still succeeds and one loud warning names the
fix.

**FLAG → registry transcription:** `concepts/channel.md` § v1 realization (replace "creation …
OPEN" with this answer) and `DEC-6`. Filed, not applied.

---

## (b) CLOSE-TIME LIFECYCLE — archive or retire

**SETTLED: ARCHIVE, never delete — `retireGoalChannel(goalId)` = `conversations.archive` +
drop the in-memory binding. Idempotent; `already_archived` is success.**

- **Archive, not delete.** Deletion is irreversible and destroys the owner-side half of the
  goal's history. The `threads-store` is the registry of record for messages, but the channel
  carries what the owner actually saw and said, in the owner's own tool. An archived Slack
  channel stays searchable and can be un-archived; a deleted one is gone. Reversibility is the
  same principle `r-cutover-gated` applies to the run's own control loop.
- **Retire = archive + unbind.** After archiving, the bridge drops `goalId ↔ channelId` and
  the conversation's reply address, so a late inbound on that channel is no longer goal
  traffic. Slack itself stops new posts to an archived channel, so the two agree.
- **Name reuse is NOT blocked by an archived channel** — Slack frees an archived channel's
  name, so a re-created goal of the same id re-derives the same name and gets a fresh channel.
  Stated because the name-derivation in (a) depends on it.
- **Who calls it: NOBODY, YET — a NAMED, DATED GAP (recorded 2026-08-10, task 7.531).** The
  retire half is implemented (`goal-channel-map.js#retire`, hand-callable via the CLI's
  `retire` verb) but has NO machine caller: `ensureGoalChannel` got its hook at C3 (run start,
  (a) above); the close half is still in the pre-C3 state — invoked by hand, not by an event.
  **The trigger that closes this gap is goal/run CLOSE**: when the goal-close machinery
  materializes, it calls the retire half symmetrically with (a)'s run-start hook — same
  process boundary (the daemon composes `retire <goal-id>` argv, never touches a token).
  Ruled DOCUMENTED-GAP rather than built on 2026-08-10 because a caller is a behavior change
  needing design this task did not carry (conductor decision, task-batch-0810).

**FLAG → registry transcription:** `concepts/channel.md` § v1 realization (close-time
lifecycle) and `DEC-6`. Filed, not applied.

---

## What this build does NOT claim

- **Phase-owner voice is the SERVER's derivation, not the bridge's.** CMP-8 is explicit:
  *"A sender TYPES its message; it never addresses a recipient, and the server derives the
  recipient."* The bridge therefore reaches the current phase-owner voice BY NOT ADDRESSING
  ONE — it enqueues a `send-message` job carrying the goal thread and a CMP-8 type, and the
  routing that picks Master/Planner/Staffer/Leader is the server's. In v1 there is no
  phase-owner router yet (no goals store, no slots), so the thread collapses to the chain-
  stable `exec-<first exec_id>` and delivery reaches that chain's current turn. That is the
  honest v1 realization of criterion 3, and the gap is the registry's own known collapse
  (`concepts/thread.md` § v1 interim handle), not a new one this build introduces.
- **No persistence.** In-memory, restart-forgetting, recoverable by name (see (a).3).
- **No new gateway intent, no new inbound listener, no store handle.** The bridge stays the
  outbound-only thin sender it already is.
