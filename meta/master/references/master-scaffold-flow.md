---
id: master-scaffold-flow
description: "Read at the moment a master seat has classified a request as NEW and is about to act on it — the sequence from raw ask to a goal that will actually run, carrying both seat arms of the lane assignment."
---

<reference>
Form: NORMATIVE — a sequence, and every step of it binding.
Enforcement: binding. Reach: the NEW disposition of a master seat, in either spawn.
The lane step carries TWO arms, each labeled with the seat it binds. Read YOUR arm and act on it;
the other arm binds a seat you are not.

## 1. Name the goal, and write the RAW ASK as its contract

**The contract content is the RAW ASK, UNREFINED** — what the requester actually said, passed
through as written. You NEVER sharpen it, expand it, or fill its gaps. Understanding the goal —
elicitation, refinement, the missing pieces of what was asked — belongs to the workflow's own
agents inside that goal, and there is no interrogation at this door.

Judgment call: the goal NAME is yours to mint. It MUST be lowercase letters, digits and single
hyphens, and it MUST be unused in the goals root — creation REFUSES a name already taken.

## 2. Resolve the execution mode BEFORE you create

### Which workflows EXIST — walk the tree; there is no flat catalog

**The COMPONENT TREE IS THE CATALOG.** No command prints a flat workflow list, and that is
deliberate: a flat catalog would be a second source for a fact the tree already carries. Walk it
with the `rbtv` drill, which DELIVERS CONTENT at three levels:

```
rbtv                        level 0 — the installed modules
rbtv <module>               level 1 — that module's components, blurb-first
rbtv <module> <component>   level 2 — that component's entry points, its workflows among them
```

A component that owns workflows names each one at level 2, with the folder holding it
(`workflows/<name>/`) and the orientation its own `workflow.md` carries. The planning workflows sit
under `meta/planning` today — `rbtv meta planning` names `plan-console`, `forge` and `d13-replan` —
but MUST be discovered by walking, NEVER carried from memory: a workflow added to any component
appears in the drill and never in a remembered list.

### The mode itself

The execution mode is the per-goal OWNER-CONTACT policy — `interactive | autonomous` — and it is
gate 2 of every agent-initiated message that reaches the owner. The creation act is what writes it,
so it MUST be resolved BEFORE that act and NEVER patched in after it.

Read the target workflow's own scaffolding: `default-execution-mode:` in that workflow's
`workflow.md`. Where the workflow declares none, derive it from that workflow's manifest — any row
whose Modality reads `interactive` means `interactive`, none means `autonomous`.

- **Resolved `autonomous` → carry it and ASK NOTHING.** A workflow with no interactive seat has
  nobody who would reach the owner, so there is no decision to put to them.
- **Resolved `interactive` → CONFIRM IT WITH THE OWNER BEFORE YOU CREATE.** Put it in their words:
  *this goal has a seat whose job is to ask you questions — do you want it reaching you while it
  runs (interactive), or should it resolve its own doubts and leave them in the goal's ledger for
  you to read afterwards (autonomous)?* Recommend `interactive` and say why: the workflow was built
  around a seat that asks.

NEVER carry a value the owner did not choose while presenting it as theirs. Through the
goal-creation request the `execution-mode` field is OPTIONAL, and omitting it means "use the
workflow's default" — which is exactly what to send when the owner confirmed exactly that. Running
the creation verb directly, that verb DERIVES NOTHING: the word you resolved here is the word you
pass it as `--execution-mode`, and a goal created without one is born `autonomous`.

This is a CONFIRMATION about who the goal is allowed to talk to. It is NEVER elicitation about the
work, which stays the launched workflow's seats' to perform.

## 3. Create the goal INTO ITS LANE — ONE act

**The lane is assigned AT BIRTH.** A goal is NEVER created first and lane-assigned by a second
call afterwards: the lane rides in the same act that writes `goal.md`.

### Which write route is yours FOLLOWS FROM THE LANE — never from what you may write

Writability decides nothing here. `rbtv goal scaffold` writes the goal folder and its contract and
does **NOT** write `taskforce.csv` — the file the daemon requires before it will pick a goal up at
all, and whose only writer in the system is `scaffold-seats`. So the verb REFUSES `--lane daemon`
outright, before its first write, with code `daemon-lane-unmaterialized`, and names the two routes
that do produce a taskforce. Which one is yours is decided by the LANE your seat assigns, below.

- **CHANNEL MASTER → the GOAL-CREATION REQUEST, on every goal, always.** You assign the daemon
  lane (arm below), and a daemon-lane goal cannot be born by the creation verb alone. The request
  route is the one act that scaffolds AND materializes: you STAGE a validated request, and the
  DAEMON's drain job runs `rbtv-goal-request scaffold-and-queue --workflow <workflow> …` over your
  inbox on its own cadence. Staging is your WHOLE act — you never run `scaffold-and-queue`, and you
  never run `scaffold-seats`.
  1. **Write the payload.** JSON, one request per file. The field set is CLOSED and FIVE fields are
     REQUIRED — an unknown name is a refusal, never a passthrough (table: `master-instruments.md`
     § Goals). `execution-lane` is one of the five and from this door it is always `daemon`.
  2. **`rbtv-goal-request validate <file>` BEFORE you stage it.** It performs no act, needs no
     goals-root access, and names every field it checked. Exit 0 means the daemon will accept it;
     skipping it trades a refusal you fix in one second for one you learn about a drain pass later.
  3. **Stage the validated file** into your own seat folder's `requests/` inbox. Nothing else.
  4. **Report what is TRUE, in the owner's words:** the request is staged, and the goal is queued
     for the daemon's next drain pass, which runs every 300 seconds. What the owner will see next
     is the goal folder with its taskforce, and — on the goal's first seeding pass — its Slack
     channel. You CONFIRM at the product afterwards (step 4); you do not claim it now. If the
     entry rejects a field it writes a refusal record beside your staged request — read it and
     report the refusal as the refusal it is, naming the field.
- **CONSOLE MASTER → the creation verb DIRECTLY, for a CONSOLE-lane goal.**
  `rbtv goal scaffold <goal-name> --contract <file> --lane console --execution-mode <word>` — the
  contract flag takes a FILE, or `-` for stdin, and the lane and the mode ride on that SAME call.
  Where the owner answers **daemon** instead, that same call refuses, and the route the refusal
  names is THREE acts in ONE sitting with the owner present: `--lane console`, then
  `scaffold-seats --package <ABSOLUTE goal folder> --workflow <workflow> --catalog-root <root>`,
  then `rbtv goal lane <goal> --set daemon` to hand it over. All three, or the goal is not born.

### `daemon-lane-unmaterialized` — the refusal, and the ONE thing it permits

A refusal creates NOTHING: the goal name is still free and the right command can be run against it.
From the CHANNEL MASTER'S door there is exactly one answer to it — **stage a goal-creation request**
— and the following are DEFECTS, each one measured on this seat on 2026-08-27:

- **NEVER re-run it with `--lane console`.** The lane is the assignment this goal is born into, not
  an obstacle in front of the command. A console-lane goal from this door is a goal nobody runs:
  no daemon picks it up, and no owner is at a terminal to type `rbtv run`.
- **NEVER pass `--materialize-follows`.** It is not an override. It is the request route's
  DECLARATION that it invokes `scaffold-seats` in the same act; a caller that passes it and does not
  materialize re-creates, under a flag that says otherwise, the exact dead end the refusal prevents.
- **NEVER run `scaffold-seats` yourself** to repair a goal you just created. That is the console
  route's second act, and reaching for it here means the first act was already the wrong one.
- **NEVER perform the goal's own work inside your sitting**, and **NEVER call `finish-goal` on a
  goal you just created.** A master sitting that does the work and closes the goal reports a
  finished goal to the owner where nothing was ever staffed, and the work has no seat, no ledger and
  no record anyone can resume from. Your act ends at the verified goal (§ 5).

### The lane — CHANNEL MASTER

**ASSIGN THE DAEMON LANE, on every goal, WITHOUT ASKING.** You are not at a terminal, and a goal
nobody assigns is a goal nobody runs. You NEVER assign `console` from this door and NEVER flip a
goal back out of the daemon lane — the owner owns that switch.

### The lane — CONSOLE MASTER

**ASK THE OWNER WHICH LANE RUNS IT, and carry their answer.** The owner is sitting with you, so
this one is ASKED, never defaulted. Put it plainly: **(a) daemon** — the daemon picks the goal up
by itself and runs its seats unattended, with no terminal output; **(b) console** — nothing runs
until the owner types `rbtv run` against the goal folder, and it runs in front of them and dies
with the terminal. Recommend **(b)** while the owner is sitting with you.

### State the lane, or the creation is REFUSED

The lane is REQUIRED on both routes: a creation that states no lane is refused before it writes
anything, never defaulted. On disk an ABSENT marker reads as `console`, and the daemon adopts ONLY
goals explicitly assigned to it — so the console arm writes `console` EXPLICITLY rather than leaving
it unsaid, because an unstated lane and a chosen one look identical to the next reader.
`execution-mode` is the one field with a resolve ladder behind it (request, then goal-kind, then the
workflow's default); the lane has none, deliberately.

### There is NO profile to name, at any door

`#d-abolish-profile-names` (2026-08-12) removed `--profile` from `rbtv goal scaffold`, from
`lane --set daemon` and from the goal-creation request schema. What a seat runs is its CAST; an
UNCAST seat is a NAMED refusal at every door, and the fix is `rbtv-bindings inspect` → discuss with
the owner → `rbtv-bindings set-many <workflow.csv> <casts.json>` — never a profile name, and NEVER a
question to the owner about one.

## 4. VERIFY AT THE PRODUCT

Verify at what was written, NEVER at the command's own success line: a tool reporting on itself
certifies nothing about the state it claims to have produced. Read back three things:

- the GOAL FOLDER the creation claims to have written;
- the `execution-mode` file — its ONE WORD is what step 2 actually produced;
- the `execution-lane` file, through `rbtv goal lane <goal>`.

An unwritten lane is the QUIETEST failure in this sequence: nothing errors, and the goal simply
never runs, in either lane.

### Through the request, the outcome is ASYNC — and "neither yet" is its OWN branch

The request route settles on the DAEMON's next DRAIN pass over your inbox (every 300 s), and the
goal is seeded on a later watch pass; nothing is pushed to you when either happens. So a read-back
has THREE outcomes, not two:

- **The goal folder exists** → created. Verify the two markers above and report it.
- **A refusal record sits beside your staged request** → refused. Report the refusal as the refusal
  it is, naming the field it rejected.
- **NEITHER exists yet** → NOTHING IS KNOWN. The daemon has not reached your request. You MUST NOT
  say `scaffolded`, `created`, `done`, `✅`, or any other success word: on 2026-08-12 this seat sent
  "✅ Goal scaffolded" 23 s after staging, when neither artifact existed — the REFUSAL landed three
  minutes later. Either re-poll after the drain interval, or tell the owner exactly
  this: *staged, not yet confirmed — I will confirm once the daemon picks it up.* A RE-STAGE after a
  fix is a NEW request with the same three outcomes: every owner-facing claim is re-verified against
  disk at the moment you make it, and NEVER inherited from the previous attempt.

A daemon-lane goal now also gets its Slack channel on its FIRST seeding pass, so the channel
appearing is a second confirmation the goal is live. Its ABSENCE within one cadence is NOT a refusal
and MUST never be reported as one — a non-interactive goal is ruled to get no channel at all.

## 5. Where the act ends

**Nothing is queued and nothing is delayed.** A created goal advances on its LANE: the daemon's
watch pass reads the `execution-lane` marker before every tick and seeds the goal off it, and a
console-lane goal waits for the owner to type `rbtv run`. There is NO job to enqueue and NO
scheduled start to time — a delayed-launch step here would be a step with no machinery behind it.

Your act ENDS at the verified goal. You NEVER nominate yourself into a seat of the goal you just
created, and no master session is born inside it.

## 6. Goal-master chair — AUTOMATIC at `goal-materialize` (D79, 2026-08-22)

The step named here is `goal-materialize` (`sd-graph show goal-materialize`); the bare word
"materialize" resolves to no record and is never the term to use in front of the owner.

D9 wants a `goal-master` sitting available on the next owner message. The leader chair staffs
itself on every later goal-materialize once `.rbtv/config/modules/meta/leader/bindings/leader.json`
exists. As of D79 the goal-master is minted automatically by the materialize staff pass
(`mint_staff_chairs`) on every goal whose catalog carries the seat and whose casting sheet exists —
at creation for the request path (`scaffold-seats --workflow plan-console`) and at materialize for a
console scaffold. It is **not** a staff chair.

**Never widen `STAFF_SEATS` to buy this mint.** The chair stays a SUMMONED seat
(`SUMMONED_SEATS = ("goal-master",)`): readiness IDLE, woken only by an owner message. History:
minting `goal-master` as `--root` used to land the row **READY** in `ready-seats` (measured
2026-08-19 on `roles-fixture-20260819`), which on a daemon-lane goal was a launch the owner did not
ask for; `--after` some unfinished seat landed it **BLOCKED** and could gate advancement. That
READY hole is closed — `ready-seats` reports summoned seats IDLE (mail is not a wake). A pre-D79
view parked the mint as MANUAL so it would not grow an arm on only one of the two births
(`goal_creation_request.py`); D79 lands it in the staff pass both births already share after a
later materialize.

For goals born BEFORE D79, the one-line manual mint is:

```
scaffold-seats --package <abs-goal-dir> --catalog-root <ws>/3-resources/tools/rbtv/meta --seat goal-master --root --bindings <ws>/.rbtv/config/modules/meta/master/bindings/goal-master.json --budget-json <that-goal-or-a-starter>/budget.json --claude-md <ws>/3-resources/tools/rbtv/ignite/coord/starter-set/CLAUDE.md
```

`--catalog-root <ws>/.rbtv/mirror` currently refuses (the file it named, `communication/module.md`,
is gone as of the 2026-08-21 move of that module into `core/communication/` — the mirror root is a
tree of MODULES, not of components, so a whole-mirror root is expected to keep refusing). Use
`3-resources/tools/rbtv/meta`. Then `resolveGoalSeat` returns ok and a goal-channel message can enqueue.

Covers: every goal that passes through materialize (request path at creation; console scaffold at
materialize).
</reference>
