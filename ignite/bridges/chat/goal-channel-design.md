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

**v1 caller, disclosed:** the goal-registration hook does not exist tonight — task 7.63's
`rbtv goal scaffold` is the natural caller and lands at m3. Under the pre-ruled degrade
(`milestone-dag.md` §1 / this seat's briefing, Branch B3), the settled answer ships as the
CALLABLE surface (`ensureGoalChannel`) with the hook as its named build follow-up; tonight's
channel is created by an explicit call, not by a registration event. The answer is not
degraded — only its caller is.

**Never-invite, by construction.** The bridge has NO `conversations.invite` code path at all.
Membership is a human act in the Slack UI. This is what makes `r-slack-etiquette`'s "the owner
is added to NO test channel" mechanically true rather than a policy nobody enforces — a probe
asserts the string's absence from the source, the same shape as `probe-chat-boundary`.

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
- **Who calls it:** goal close, by the same machinery that registers the goal — symmetric with
  (a), same caller, same missing-hook disclosure.

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
