---
id: master-instruments
description: "Read at the moment a master sitting has decided it needs a tool and is choosing WHICH — the instrument roster: when each one is reached, what it refuses, and the judgment its own `--help` cannot carry. Applied, never executed."
---

<reference>
Form: NORMATIVE (which instrument is reached at which moment) over a referential roster.
Enforcement: judgment. Reach: every master sitting, channel spawn or console spawn.
Every flag list, usage line and option default is the instrument's OWN `--help` and MUST be read
there; NEVER carry one from memory into a command.

## Standing rules over every instrument

- MUST reach a named instrument below before improvising — a shell pipeline, a `find`, or an `rg`
  sweep over the tree is NEVER the first move where an instrument covers the ask.
- MUST render every statement about current state from an ACTUAL read at answer time. A remembered
  or reasoned value is NEVER an answer.
- MUST verify at the PRODUCT, never at a command's own success line. A tool reporting on itself
  certifies nothing about the state it claims to have produced.
- MUST report a refusal as the refusal it is. NEVER report it as a capability this seat lacks, and
  NEVER work around it by hand.
- Holding these instruments NEVER widens the mandate. Work that belongs to a goal is still promoted
  into that goal and done by its seats.

## The coordination bus — `coordinate`

Reached when: something must be said to a seat, or something a seat said must be read, or who is
alive in a goal must be established.

- The FULL feature set is yours — send to any seat, read the WHOLE message log including messages
  addressed to others, `workers` (the roster: one CURRENT row per agent), check-in and check-out.
  NEVER treat any leg of it as another seat's to run.
- There is NO standalone wake and no `wake` verb. `send` wakes the recipients' panes as PART of
  sending, and that wake is BEST-EFFORT while the log is the truth: a sent message is delivered
  whether or not a pane stirred. A quiet pane is therefore NEVER a failed send, NEVER a thing to
  report as a failing wake, and NEVER evidence that this seat lacks a leg.
- Disturbance is the cost this seat minimises: MUST prefer a READ of the log over an ask, and ONE
  seat over the room.
- NEVER answer or absorb traffic addressed to a goal's own agent. Reading it is a grant this seat
  holds; handling it is not.
- Routing a bus row back INTO a Slack thread is `send --chat-thread <channel>:<ts>` — a HEADER
  flag since W4, not a `[chat-thread: …]` token typed into the body. Beside it, `--deliver post`
  posts the row verbatim with no sitting minted, `--deliver wake` posts it AND mints one to act on
  it; `--deliver` alone, with no `--chat-thread`, names no destination and is refused at send. The
  bracketed body tokens still parse (rows already on live buses carry only that form) but are a
  documented FALLBACK — never what this seat writes. The thread id is the one injected into this
  sitting, per the card.

## The owner's owed answers — `owed-answers`

Reached when: a cold contact opens, before anything else.

The words "owed answers" resolve to NO record of their own — `sd-graph show "owed answers"` returns
nothing. They are AUTHORED in `sd-graph show master` § owed answers at cold contact, over the join
`sd-graph show threads-store` defines. Cite those two when explaining the term, and NEVER present
it as a registry identity.

- MUST run it and trust what it says. It runs the store's own open-ask AND open-escalation
  predicates over every live goal in ~0.15 s and returns the count, then the list capped at 5 —
  unanswered escalations FIRST (each tagged `⛔ RUN HALTED`; an escalation halts its goal), then
  asks oldest-first — each item with its thread pointer, already the shape the owner is shown.
- NEVER derive this debt any other way: NEVER search the vault for it, NEVER `find` or `rg` for
  stores, NEVER open a goal's `threads.sql` (that file is not a database), and NEVER probe
  `coordinate` to work out which command derives it. Hand-derivation is not thoroughness — it cost
  a measured ~120 s of silence in front of the owner before the first word of an answer.
- `no owed answers` means the debt is ZERO. Say nothing about it and get on with the message.
- The ONE case that admits hand-derivation: the command is missing, or it prints that a package was
  UNREADABLE. Only then derive per package with `coordinate --package <goal> --as owner pending`,
  and say on that turn that you did.

## Who is working, and on what quota — `ignite`, `coordinate workers`, `acct`

Reached when: the ask is what is running, who is working, or whether a provider limit is blocking
work.

- There is NO dashboard to open. The renderer that used to answer this (`teamview`) and the sensor
  behind it were DELETED, and nothing replaced them: there is no snapshot to read and no snapshot
  age to judge. MUST answer from the two LIVE reads below, and NEVER report the absence of a
  dashboard as an inability to answer.
- WHAT IS RUNNING, across the whole system, is the DAEMON'S OWN READ — `ignite status` for daemon
  health, live agent-session count and queue depth, and `ignite inspect …` for a named job,
  execution or queue row. Both are READ-ONLY. MUST read it there rather than infer it from a quiet
  room.
- WHO IS WORKING, inside ONE goal, is `coordinate workers` — the roster: one CURRENT row per agent
  (alive, `DEAD?`, or checked out), what each is working on, and each one's unread lag. ACTIVE rows
  are VERIFIED against live tmux panes, so a `DEAD?` row is a pane that is gone rather than a guess.
- Plan limits are in NEITHER read. MUST take them through `acct` (`acct usage`, `--posh` for live
  bars): accounts and their windows are a property of the BOX, where the daemon read is per-daemon
  and the roster read is per-goal.
- `acct` also SWITCHES a provider between accounts without a re-login, so a burnt weekly window is
  a switch rather than a stop.
- What a provider can SWITCH and what it can REPORT are different sets, and per-account usage is a
  narrower set still. MUST establish which from `acct` itself before promising the owner either;
  NEVER state a limit for a provider that exposes none.

## The owner's own surfaces — `sb-task`, `gtools`, `stools`

Reached when: the ask is about the owner's vault tasks, the owner's mail, or Slack outside the
thread this contact arrived on.

- `sb-task` is how a vault task is read and written. NEVER hand-edit a task's main line or its
  structured sub-bullets while this CLI answers — it enforces the task contract mechanically, and a
  hand edit silently breaks it. MUST `--dry-run` every edit before making it.
- `sb-task` does NOT route: it creates a task in whatever file it is given. MUST establish which
  file a new task belongs in before creating it, and NEVER let the choice fall out of a name
  substring that happened to match.
- `gtools` reads and sends the owner's mail; `stools` READS Slack beyond this thread — a channel, a
  thread, a search, a file off a message.
- MUST start with that tool's own `doctor` when either behaves oddly: it reports venv, config,
  accounts and token state, and a missing token scope is the usual answer.
- The configured Slack token BOUNDS what `stools` can see — a bot token cannot search at all and
  sees only channels it was invited to. A result of nothing MUST be reported as possibly a scope
  bound; NEVER as proof that nothing was said.
- `stools send`, `react` and `upload` are WRITES to Slack. Each needs the owner's explicit approval
  in the SAME turn, and approvals are NEVER batched.
- Your reply to the owner NEVER goes through `stools`. It goes into the thread the contact arrived
  on.
- Both tool repos are third-party and READ-ONLY: NEVER edit, commit, or push either.

## Goals — `rbtv goal`, `scaffold-seats`

Reached when: a goal must be created, its lane read or written, or one more seat materialized into
a goal that already has a taskforce.

- `rbtv goal scaffold` creates the goal folder and its contract, and is CREATE-ONLY. It does NOT
  write `taskforce.csv` — the file the daemon requires before it picks a goal up — so it REFUSES
  `--lane daemon` outright, before its first write, with code `daemon-lane-unmaterialized`. WHICH
  ROUTE IS YOURS FOLLOWS FROM THE LANE, never from what you may write: writability decides nothing
  here and there is no EROFS fallback to wait for.
  - **CHANNEL MASTER** — you assign `daemon` on every goal, so this verb is NEVER your route. Yours
    is the GOAL-CREATION REQUEST, always: validate it, then STAGE it in your own seat folder's
    `requests/` inbox and stop there. The DAEMON drains that inbox with `scaffold-and-queue` on its
    own cadence (every 300 seconds), which scaffolds AND materializes in one act — you NEVER run
    `scaffold-and-queue` and NEVER run `scaffold-seats` from this door. Tool — full path
    `3-resources/tools/rbtv/ignite/operator/goal-creation-request/tool/rbtv-goal-request`.
  - **CONSOLE MASTER** — run the verb DIRECTLY for a CONSOLE-lane goal. Where the owner answers
    `daemon` it refuses you the same way, and your route is then either the request route above, or
    the sequence the refusal names as THREE acts in ONE sitting: `--lane console`, then
    `scaffold-seats --package <ABSOLUTE goal folder> --workflow <workflow> --catalog-root <root>`,
    then `rbtv goal lane <goal> --set daemon`. All three, or the goal is not born.
  NEVER hand-queue a daemon job that runs the scaffold command for you, and NEVER pass
  `--materialize-follows` to get past the refusal — it is the request route's DECLARATION that it
  materializes in the same act, not an override. Full sequence: `master-scaffold-flow` § 3.
- A goal's LANE is what decides whether anything ever runs it, and an ABSENT assignment means
  `console`. NEVER leave the lane to a default.
- `rbtv goal lane <goal>` with NO `--set` READS the marker back. That read is the verification, and
  MUST be taken over the setting command's own success line — an unwritten lane assignment is the
  quietest failure at this door, because the goal simply never runs, in either lane.
- The goal-creation request is a JSON file staged in your OWN seat folder's `requests/` inbox. Its
  field set is CLOSED — five REQUIRED, two optional — and a name outside it is a refusal, never a
  passthrough:

  | Field | Required | Value |
  |---|---|---|
  | `goal-name` | yes | lowercase-kebab, unused in the goals root |
  | `goal-type` | yes | `one-shot` \| `recurring` |
  | `goal-contract` | yes | the RAW ASK, non-empty |
  | `goal-kind` | yes | `interactive` \| `non-interactive` |
  | `execution-lane` | yes | `daemon` \| `console` — ONE word. From the channel master this is ALWAYS `daemon` |
  | `execution-mode` | no | `interactive` \| `autonomous`; omit to take the workflow's default |
  | `due-date` | no | — |

- PRE-FLIGHT EVERY REQUEST BEFORE YOU STAGE IT. `.../tool/rbtv-goal-request validate <file>`
  performs NO act, needs no goals-root access, and NAMES every field it checked. Exit 0 means the
  daemon will accept it. Both 2026-08-12 refusals (`goal-kind-absent`, `execution-lane-absent`) cost
  a full watch-pass round trip and would each have been caught by that one command.
- Nothing else about the request is yours to choose. The workflow, the component catalog, the
  bindings sheet and the starter set are FIXED on the daemon's own entry. A request carrying a
  `workflow` field is refused `[S2] field-name-not-in-the-five`.
- There is no profile to name, at any door. `#d-abolish-profile-names` (2026-08-12) removed
  `--profile` from `rbtv goal scaffold`, from `lane --set daemon` and from the request schema. What a
  seat runs is its CAST; an UNCAST seat is a NAMED refusal at every door, and the fix is
  `rbtv-bindings inspect` → discuss with the owner → `rbtv-bindings set-many <workflow.csv>
  <casts.json>` — never a profile name, and never a question to the owner about one.
- The owner may flip a goal to the `console` lane at any moment. That is the supported act, not a
  fault, and NEVER yours to flip back.
- `scaffold-seats` materializes ONE cataloged seat into a goal and appends its taskforce row. Its
  `--package` is the GOAL FOLDER itself, absolute — NEVER a run folder (no such layer exists) and
  never inferred.
- MUST reach it by its PATH name `scaffold-seats`, NEVER by the script path behind it.
- `--repass` is what you reach for when the seat already exists: it RE-RENDERS that seat's
  descriptor. Reaching the plain call at an existing seat is the wrong verb, not a fresh start.
- Once a goal HAS a taskforce, a `scaffold-seats` call belongs to the seat holding that goal's
  authority. NEVER run one into a goal whose authority is not yours.

## The daemon — `ignite`

Reached when: the daemon's own state is the question — whether it is up, what is queued, what
became of an execution.

- `ignite status` and `ignite inspect …` are READ-ONLY and are the answer to "is the system
  running", "what is queued", and "what happened to that job". MUST read daemon health there rather
  than infer it from a quiet room.
- NEVER queue a job to launch a goal you created. The queued `<goal>-workflow-start` row and the
  launcher it fired are DELETED; a goal advances from its lane assignment alone, and a hand-queued
  launch is a row nothing consumes.
- `ignite status` is ALSO the STANDING-CONDITION read, and it answers from TWO fields, not one.
  There is no separate warnings verb. A status answer states BOTH:
  - `standing_warnings` — the daemon's OWN warning rows (what `ignite snooze` acts on).
  - `open_conditions` — every alarm any component raised through the one alarm emitter: the
    out-of-process watchdog's row alarms (a probe suite that is live but RED, a bridge that cannot
    reconnect, a gateway refusing the watchdog's token) and the frozen-goal invariant.
  An EMPTY list on either means no condition is standing on that side — never that the surface is
  missing. ⚠ A `null` on `open_conditions` is DIFFERENT from an empty list: it means this daemon
  cannot read the alarm registry at all, so report it as UNKNOWN, never as "nothing is standing".
  ⚠ Answering from `standing_warnings` alone is how a live owner question was answered "no standing
  warnings" on 2026-08-26 while the watchdog had held an alarm for hours.
- NEVER snooze a standing warning on your own initiative. `ignite snooze` SUPPRESSES a warning for a
  stated number of minutes and NEVER clears it — the condition is still there when it returns.
- NEVER kill a session to tidy the board: `ignite kill` terminates a live seat's whole process tree.

## This sitting's cast, and a workflow's — `rbtv-master-profile`, `rbtv-bindings`

Both are reached BY FULL PATH. NEITHER is installed under a bare name, and typing one bare fails in
a way that reads like a missing tool:

- `3-resources/tools/rbtv/ignite/operator/master-profile/tool/rbtv-master-profile`
- `3-resources/tools/rbtv/ignite/operator/bindings/tool/rbtv-bindings`

`rbtv-master-profile` — this seat's own harness, model and reasoning rung for its NEXT sitting.

- MUST run `show` before naming a profile or a rung. It prints the cast in force, every name that
  may be requested, each one's ladder, and how a prose effort ask maps onto a rung. NEVER name
  either from memory: an inert profile refuses a rung, and a dialled one refuses without one.
- `request` is THIS seat's verb and `apply` is the DAEMON's. NEVER run `apply`.
- NOTHING is restarted and this conversation SURVIVES — the change lands on the owner's next
  message. NEVER warn the owner that switching will end the chat: it did until 2026-08-12, and it
  does not now.
- ALWAYS pass `--chat-thread <channel>:<ts>` for the thread this sitting is on. It is what makes the
  daemon report the outcome — accepted or refused — back INTO that thread instead of leaving the
  owner watching a thread where nothing ever answers. Omitting it is not a smaller request; it is a
  silent one.
- The thread id is NOT a field of this seat's descriptor. NEVER hunt for it there — it reaches the
  sitting from the bridge that spawned it on that thread.
- MUST change the cast through this tool rather than by editing the cast file. A cast recorded
  without the re-render never takes effect. D49 made this seat's own `seat.md` writable; still use
  `request` (never `apply`, never a hand edit of the descriptor) so the daemon's re-render is the
  one writer of the cast into the assembled file.

`rbtv-bindings` — the casting sheet that turns a workflow into a taskforce: which harness, model and
effort rung each seat runs on, and what the seat materializer reads as `--bindings`.

- Unlike the profile knob, this one is YOURS to run directly: no daemon half, no restart, nothing
  staged.
- MUST run `catalog` before naming any harness, model or effort number — it prints what this
  workspace can actually spawn, with each dial's numbers.
- NEVER hand-author the sheet's JSON. Every value is validated against `catalog`, and an invalid one
  refuses at goal-creation time, where nobody is watching.
- `inspect` names which seats of a workflow are still UNCAST. An uncast seat is what REFUSES at
  launch — there is no fallback profile behind it any more — so `inspect` is the first move whenever
  a launch names one, and `set-many <workflow.csv> <casts.json>` casts the whole batch in one
  validated act (partial input is refused whole, with a per-seat reason).
- ONE sheet per workflow, created on first use and reused by every later goal. `scaffold` REFUSES
  over an existing sheet rather than re-casting a taskforce that may already have run; MUST take
  that refusal as the answer and `set` the one seat that needs casting.

## Secrets — `coordinate secret-add`

Reached when: the owner has handed you a new integration key to land, append-only.

- The owner writes the key as ONE LINE in a `.txt` at a WORKSPACE path you can read. NEVER `/tmp`
  (the cage has its own tmpfs). NEVER under `.rbtv/goals/` (live goal ledgers are not a mailbox).
- They tell you the filename and the env NAME. You run:
  `coordinate secret-add THE_NAME --from-file /path/in/the/workspace/agreed.txt`
- The daemon (out of cage) appends `THE_NAME=…` to `.rbtv/config/.env` and deletes the drop. You
  NEVER read the value back, NEVER update, NEVER delete. Those stay the owner's, by opening the file.
- Refusals, and what each means:
  - `NAME … already exists` — append-only; the drop was left in place.
  - `drop file is under .rbtv/goals/` — not a mailbox; drop left in place.
  - `secret-add is a master act` / `you claimed '…' (--as)` — proven identity is not this master
    seat; there is no `--force`.
  - `UNKNOWN_INTENT` — the live daemon has not yet deployed the intent; do not retry as a paste.
- NEVER put the key in chat, in a command argument, or in a bus/ledger line.

## Every term of this system — `sd-graph`

Reached when: you are about to USE, DEFINE, or EXPLAIN a term of this system — in your own words or
in the owner's.

- MUST run `sd-graph show <term>` first.
- A term it cannot resolve is NOT a term of this system. Say so rather than inventing a meaning, and
  correct a misused term rather than adopting it.
</reference>
