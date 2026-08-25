# master-profile — the channel master choosing its own harness and model

> ⚠ **`#d-abolish-profile-names` (owner, 2026-08-12) — task 7.787.** Profile NAMES are abolished as a caller-selectable variable everywhere in ignite. A seat runs the launch spec its CAST resolves (`launch-specs:` in `envelope/spawn-profiles.yaml`, keyed by `(harness, model)`); an UNCAST seat is a NAMED refusal. Retired in the same change: `rbtv run --profile`, `rbtv-goal scaffold/lane --profile`, the `execution-lane` marker's second token, `cli add-job --profile`, the chat bridge's `session_profile`, and `launch-agent`'s `profile` argument. The KG term **launch profile** is RETIRED — its successor is **launch spec** (`#d-abolition-terminology`).


Issue **C-1** (owner-ruled 2026-08-10). Twin of `goal-launch-delay`: same ruling, same two-part
transport, different file, different validator, different last act.

The tool is `tool/rbtv-master-profile`.

## What the knob actually is

⚠ **RETARGETED 2026-08-12** (task *"RETARGET master-profile request/apply onto the bindings path"*,
core-build). Until then the knob was `master_profile` in `.rbtv/config/chat-bridge-config.json`,
boot-read by the bridge and selected per SURFACE by `forward-path.js#profileFor`. The launch-cast
unification (owner ruling **D2**, 2026-08-11) deleted that key's readers, and this tool was parked
on a refusal naming the correct target rather than half-retargeted — the right interim call, and a
dead CLI for a day. Owner's words at the door: *"THERE IS A REASON I CREATED A CLI FOR MASTER TO
CHANGE MODEL, AND EFFORT."*

The knob is the master's own **casting sheet**:

```
.rbtv/config/modules/meta/master/bindings/channel-master.json
  → seats["channel-master"].{harness, model, effort}
```

which is the same kind of file `rbtv-bindings` writes for every workflow seat. Per
`d-master-is-cast-like-any-other-seat` the SEAT governs and this CLI's job is to **re-cast the
seat** — never to pass a per-dispatch override on the wire. `materialize-seats.py --repass`
re-renders `seat.md` from the sheet, and every launch door resolves the cast from that descriptor
(`supervisor/launch-profiles/catalog.js#specForSeatCast`, `readFileSync` per launch, never boot-cached).

⚠ **THE AGENT-FACING UNIT IS `harness` + `model`, NOT A NAME** (`#d-abolish-profile-names`, 2026-08-12 — `request <harness> <model> [--effort N]`). The capability KEEPS ITS OWN NAME (`#d-master-profile-keeps-its-name`); only its caller contract changed. The sentence that stood here — "the agent-facing unit is still a spawn-profile NAME from `profiles:` in `envelope/spawn-profiles.yaml`"
— one profile IS one harness+model pair (`r-seats-only-architecture`), so a name is a complete cast
and the requester keeps one vocabulary. `show` prints the askable set rather than this document
restating it, because a roster written into a document goes stale silently.

⚠ **THE PAIRS OFFERED ARE THE CASTABLE ONES, WHICH IS NARROWER THAN `launch-specs:`.** The old
validator accepted every declared key; the sheet must hold a pair `coord.py#validate_seat` accepts,
because that is the predicate `materialize-seats.py`'s F6 gate runs over the whole batch. `test-sleep`
is the sharp case — a declared profile that is not castable, and the old validator waved it through.

## The effort rung — a wall until 2026-08-11, built since

⚠ **THIS SECTION REPLACES A REFUSAL, AND THE REFUSAL WAS RIGHT WHEN IT WAS WRITTEN.** Until
2026-08-11 this document carried a measured trace ending *"shipping `--effort` here would have
written a value nothing reads — a knob that turns and does nothing"*. Every line of that trace was
true at its HEAD: `forward-path.js` composed `args: {profile, prompt}`; the `chat-agent` job's
registered `args_schema` admitted no `effort` and `register-job` is create-only, so it could not be
widened; `ticker.js#launchAgent` read three arg keys and called a seven-parameter `spawn(...)`; and
the profiles' `effort:` tables had, in `dispatch.js`'s own words, **"NO daemon caller today"**.

Owner ruling **`d-0811lp-effort-lane-build-now`** (run `exec-0811-live-proofs`) ruled the LANE
built rather than the knob dropped, explicitly overriding that reservation. What changed, in order:

| Link | What it does now |
|---|---|
| ~~`chat/config.js` reads `master_effort`~~ | **HISTORY.** Deleted by D2 the same week it shipped — the transport names no execution |
| ~~`forward-path.js#effortFor`~~ · ~~the widened job id~~ | **HISTORY**, same ruling. The per-SURFACE effort lane is gone |
| `runtime/ticker/ticker.js#launchAgent` | reads `args.effort`, passes it to `spawnManager.spawn(...)` |
| `supervisor/spawn/spawn.js#composeArgv` | composes it through `resolveEffort()` — the **same** function `launch-profiles/resolveProfile` calls, never a second reading of the table |

⚠ **The first two rows are history and the last two are the load-bearing half.** The rung reaches
`composeArgv` from the SEAT'S DESCRIPTOR now, on every lane, so the effort this tool writes is
honoured whether the master is reached over chat or spawned by the daemon.

`dispatch.js`'s five "re-rule at 7.43/7.54" notes are now four: `E_UNKNOWN_EFFORT` is re-ruled and
raised live. **Half selection is still refused** (G-144) and still belongs to 7.43/7.54 — the
effort ladder was separable from it, which is why this could ship without that refactor.

⚠ **The MODEL half is built too** (ruling D19, 2026-08-11, run `ignite-planning-hardening`). Task
7.54's `(harness, model) → profile-name` catalog is live — `supervisor/launch-profiles/catalog.js`, applied at
`supervisor/spawn/spawn.js#profileForSeatCast` — so a seat that declares `harness:`/`model:` in its own
`seat.md` now launches on the profile it is cast as, on every lane, including a chat revival. That
is now the mechanism this capability RUNS ON. ⚠ The sentence that stood here until 2026-08-12 —
*"the channel master declares no cast by design … its harness and model stay the chat bridge's to
name"* — was already false when D2 retired `open_binding` for this seat. The master declares its
cast like everyone else, and this tool is how it changes it.

## ⚠ What a rung IS — a number, 1..N, in **that profile's** ladder

Owner ruling **`d-0811lp-effort-numeric-per-profile`**: *"use N levels (1-N), from lower to higher
reasoning. this way each harness/model can have as many as they want."* Rung 1 is the lowest
reasoning, rung N the highest, and **N differs per profile** because each harness's real dial does:

| Profile | Ladder | Mechanism |
|---|---|---|
| `claude-fable` · `claude-opus` · `claude-sonnet` | 1..5 — low · medium · high · xhigh · max | `--effort <level>` |
| `codex-gpt-5-5` | 1..3 — low · medium · high | `-c model_reasoning_effort=<level>` |
| `claude-haiku`, every `opencode-*`, `test-sleep` | **inert** | no dial exists — measured, not assumed |

- **Out of range is refused, loudly, naming the range** — at `request`, again at `apply`, and again
  at the spawn. A rung is only meaningful against a profile, so it is always checked against the
  profile the request is switching **to**, never the one in force.
- **An inert profile ACCEPTS a rung and the sheet records `inert`** — owner ruling
  `d-effort-refuses-only-where-a-dial-exists`: *refuse only where a dial EXISTS and the level is out
  of its range*. ⚠ **The sheet REFUSED one between the 2026-08-12 retarget and later that same day**,
  on the reasoning that a stored level no harness honours is the knob-that-does-nothing G-270 exists
  to expose. What that missed: the refusal also POPPED the field, and
  `materialize-seats.py#open_binding` refuses a half-declared triple on a standing seat — so the
  channel master's `claude-haiku` cast (the warm-session latency fix) was **un-makeable through this
  tool** and its sheet had to be hand-written. The word `inert` is the honest storage: not a rung
  name (an inert profile has no ladder to name one from), and every reader of the field —
  `profiles.js#resolveEffort`, `catalog.js#effortRungFor`, `coord.py#validate_seat` — reports inert
  before it looks at the word.
- **The mirror-image rule holds too: a profile WITH a dial MUST be given a rung.** `materialize`
  refuses `effort-missing` on a dialled seat, so "no rung" is not a valid cast for `claude-opus`.
  An inert profile carries `inert` instead — never nothing, because a standing seat's triple is all
  three or none (`materialize-seats.py#open_binding`).
- `show` prints every profile's ladder, so nobody has to know N out of band.

## ⚠ The rung is written WITH the profile — never left over from the previous one

`request claude-opus --effort 4` writes all three fields. `request claude-haiku` — with or without
`--effort` — writes the pair and the word `inert`. That is not tidiness:
rung 4 chosen for a five-rung harness, left behind across a switch to a three-rung one, passes every
door in this tool and then **refuses at the spawn**, one owner message later — the exact failure the
profile-name validation exists to prevent, one field over.

⚠ **AND THE VALIDATOR IS `bindings.cast_seat`, NOT A CHECKER IN THIS TOOL.** `request` calls it with
`dry_run=True` and `apply` calls it for real — one function answers *"may I?"* and performs *"do
it"*, so the two answers cannot disagree. The tool's own `validate_effort` was DELETED rather than
kept beside it: a second effort validator over a file another capability owns is the drift the
ladder-reader collapse (below) was performed to end, one field over. The task's criterion 4 said
*"validate_effort already does this; keep it"* — the intent (the rung is checked against the TARGET
profile's ladder at request time) is met and made stricter; the named function is not kept, and
that divergence is deliberate.

## The three verbs

| Verb | What it does | Who runs it |
|---|---|---|
| `show [--json]` | the cast in force in BOTH vocabularies (harness/model/effort AND the profile name + rung it maps to), the sheet it came from, and **every castable profile with the rungs it admits** | anyone, including a caged seat |
| `request <harness> <model> [--effort N] [--inbox D] [--chat-thread C:TS]` | validate the PAIR against the live castable set **and the rung against that pair's ladder** → stage `{"harness": …, "model": …, "effort": N}` (plus the thread id when given) → `ignite add-job`. `--inbox` DEFAULTS to this workspace's channel-master inbox and REFUSES any path not shaped `<goal>/settings-requests/<capability>` — `apply`'s fired argv drains one fixed inbox, so a request staged anywhere else is orphaned while the stage reports ok (measured 2026-08-17: a sitting guessed `coordination/`) | **the seat** |
| `apply --inbox D --bindings F --seat S --catalog-root R --profiles P [--no-repass]` | drain, re-validate, write the **harness/model/effort triple**, record the outcome, **report into the requester's chat thread**, `--repass` the seat's descriptor LAST | **the daemon**, via `tools: master-profile` |

Exit 0 when everything drained was accepted (or the inbox was empty), 1 otherwise.

## Why the transport is split in two — and the reason NARROWED with the retarget

⚠ **IT IS NO LONGER "THE SEAT CANNOT WRITE THE FILE".** The bindings tree is in the channel master's
`rw-paths`, and the seat writes it directly — that is exactly why `capabilities/bindings` is a
one-part capability. The split survives for the **RE-RENDER**: `--repass` rewrites
`<goal>/seat.md`, and `spawn.js`'s `rw-paths` resolver refuses any grant overlapping `.rbtv/goals/`
by design, because a seat may not rewrite its own identity surface. So the seat can author the cast
and cannot make it take — the worst of both — and the split gives authoring to `request` and the
re-render to `apply`. Measured and filed as `i-cast-rerender-blocked` on the master's own issues
ledger (2026-08-11); closed by this change.

The transport itself is unchanged from `goal-launch-delay` and `goal-creation-request`
(`goal-launch-delay.md` § *Why the transport is split in two* carries the reasoning): `fire-tool`
argv is static so the payload travels as a file staged in the seat's own folder, and `enqueue-job`
is the one gateway verb open to a `bridge` token.

## ⚠ Validation is against the LIVE roster, at both halves

An unknown profile name **does not fail at the bridge**. It fails at the *spawn*, one owner message
later, with the sitting already accounted for — which is why the name is checked at the door and
again at the fire, and why the refusal names the whole live set back to the requester.

The roster is **read** from `spawn-profiles.yaml` through `bindings.catalog` — the ONE derivation
`rbtv-bindings catalog` prints and `rbtv-bindings set` enforces — never carried as a copy: a list
frozen in the tool would refuse a profile that exists or admit one that was removed, the second being
the failure that reaches the spawn. Adding a profile to that file needs no edit here.

⚠ **The line-scan of the `profiles:` keys is GONE, and it was not merely slower — it was WIDER.** It
answered "is this a declared key?", which admits `test-sleep` and any profile with no `exec:` half.
The sheet needs "is this a castable pair?", and only the catalog answers that.

## ⚠ An unknown SEAT refuses rather than being created

A sheet whose `seats` map does not carry the named seat is a refusal naming what it does carry.
Minting the entry would cast a seat nothing materializes. (This replaces the retired
*"an absent `master_profile` refuses rather than being created"* rule, which guarded the same class
of mistake one file over.)

## ⚠ Nothing is restarted, and the owner's chat session survives

This is the single biggest behavioural change of the retarget. The old apply restarted
`rbtv-chat-bridge.service` because the bridge boot-read the value, which killed the very
conversation that asked for the switch — a knob that cost the owner his session to turn.

A casting sheet is not boot-read by anything:

| Link | What makes the switch land |
|---|---|
| `supervisor/spawn/spawn.js` | reads `seat.md` per launch (`readFileSync`), never cached |
| `supervisor/launch-profiles/catalog.js#specForSeatCast` | maps the descriptor's `(harness, model)` to the profile name, and the seat's cast BEATS the caller's |
| `supervisor/spawn/live-sessions.js` | re-resolves the cast on EVERY owner message and REAPS a warm session whose conversation now names a different profile (§ *REAP ON A PROFILE SWITCH*) |

So the ordering is **write (atomic `os.replace` via `bindings._write`) → outcome record on disk →
re-render last**, the switch takes effect on the owner's next word, and the thread that requested it
is still there to read the report.

The re-render is delegated to `planning/materialize-seats.py`, the ONE renderer of a `seat.md`
(`PRIN-11`) — the same one goal creation runs. `--package` is DERIVED from `--inbox` (the inbox is
`<goal>/settings-requests/<capability>`, so its grandparent IS the goal folder), which keeps one
goal name out of the fired argv instead of two that could drift apart.

## ⚠ `--chat-thread` — the outcome reports itself back into the owner's thread

Issue `i-profile-switch-no-feedback` (owner-ruled 2026-08-10). The outcome record in `done/` is
durable but **silent**: the sitting that asked ended with its turn, and the owner watches a thread
where nothing ever answers. (When this was ruled, the restart also killed that sitting outright. The
sitting survives now; the silence does not fix itself.) So `request` takes `--chat-thread <channel>:<ts>` — the sitting's
own thread, which it already knows from the plain `chat-thread:` line at the top of every prompt —
the staged payload carries it as `"chat-thread"`, and `apply` reports the outcome there.

**This tool posts nothing.** It appends ONE row to the requesting goal's coordination bus
(`<goal>/coordination/messages.md`, derived from the inbox — never a named goal), addressed
`to: owner`, whose body carries the **bracketed** `[chat-thread: <id>]` token;
`chat/bus-ferry.js`'s return leg is what carries it into the thread. Bracketed is the
routing form — the plain form a prompt carries is deliberately inert — and the return leg is read
**before** the two contact gates, so the report travels on a goal that may not *initiate* contact.
The append goes through `coord.py#append_message`, the one allocator of bus ids (and the owner of
the header grammar, the package lock, and the trailing newline the ferry's torn-write rule needs).

**The row also carries `[deliver: post]`, and without it the report is not a report.** A bare
`[chat-thread:]` token means *hand this row to an AGENT on that thread*: the bridge mints a
channel-master sitting from it and posts **nothing** (ruled 2026-08-07, for a seat *answering* the
owner). Measured on this exact path at `2026-08-10T12:46:46Z` — the switch report minted queue row
361 and the owner was shown nothing. A settled switch is a fact this tool already composed, so it
asks to be POSTED verbatim: no agent, no inference, no ~12 s spawn pipeline. Vocabulary and the
`wake` sibling: `chat/bus-ferry.js` § `deliverToken`; design `live-session-design.md` §3a.

| Property | Why |
|---|---|
| ACCEPTED **and** refused both report | "your switch did not happen, and here is why" is the answer the owner is owed most |
| the report precedes the re-render | render-last is the ruled invariant above, so the row **cannot** state its exit code — it states what is *about to* happen. The rc stays in the outcome record, rewritten once the render returns |
| a failed append never aborts the apply | the switch is the job, the report is the courtesy — it is recorded as `chat-report.error` in the outcome record and the fire continues |
| no token → nothing is appended | pre-existing callers keep the behaviour they had |
| a token the ferry could not route is **refused**, at both halves | the shape mirrors `bus-ferry.js`'s `CHAT_THREAD_RE` anchored; an accepted-but-unroutable token is a report nobody receives |

The bracketed token is visible to the owner in the delivered message — unavoidable, since the token
must ride in the row's body for the ferry to route on it. It sits on the last line, as a footer.

## How the seat drives it

⚠ **The seat is asked for effort in PROSE** — *"switch to opus at high effort"*, *"think harder"*,
*"max reasoning"* — and must convert that itself. There is no word→number table anywhere in this
capability, deliberately: a table refuses the phrasing nobody anticipated. What the tool ships
instead is the SHAPE of the scale, printed by `show` and by `request --help` as `EFFORT_GUIDANCE`
— a rung is a *position* on the target profile's ladder, so the phrasing maps proportionally onto
1..N (minimal → 1, medium → the middle rung, high → just below N on a ladder of 4+, maximum → N),
and a request naming **no** effort still has to pick one when the target has a ladder (the middle
rung is the honest default for an unstated ask), because a dialled seat with no effort is refused.

```bash
# what is it now, and what may I ask for?
.../capabilities/master-profile/tool/rbtv-master-profile show

# change it (validates name AND rung against the live config, stages, enqueues — one command)
# `--chat-thread` is YOUR thread: the plain `chat-thread:` line at the top of your prompt.
# `--effort` is REQUIRED for a profile with a dial — the sheet must hold a rung `materialize`
# accepts. On an INERT profile it is optional and applies nothing: the sheet records `inert` either
# way, because a rung belongs to the profile it was chosen for. `show` says which profiles are inert.
.../capabilities/master-profile/tool/rbtv-master-profile request claude-opus --effort 4 \
  --chat-thread C0ABCDEFG:1754812345.123456 \
  --inbox /home/henri/ht-wkdir/second-brain/.rbtv/goals/_channel-master/settings-requests/master-profile

# what happened to the request the last sitting made?
ls .../settings-requests/master-profile/done .../settings-requests/master-profile/refused
```

## Arming it — three gated acts, in this order

1. create the inbox directory the entry names
   (`.rbtv/goals/_channel-master/settings-requests/master-profile`);
2. restart the daemon — `spawn-profiles.yaml` is boot-read. ⚠ **This is not a one-time step: the
   `tools:` argv is held in memory from boot (`heartStore.config.tools`, no reload path), so ANY
   edit to this capability's registered argv is inert until `rbtv-ignite-daemon restart` runs.
   Measured 2026-08-12 during the retarget — the new flags were on disk and the daemon kept firing
   the old ones;**
3. `ignite register-job master-profile --action-type fire-tool --args-schema '{"required":{"tool":"string"}}'`.

`register-job` is create-only and refused to a `bridge` token — an operator act, done once. The seat
only ever needs `add-job`, which the `request` verb issues for it.

## Probe

`probes/probe-master-profile.py` — run it through the enumerator
(`node deploy/probe-suite.js --only master-profile`). Entirely under `tempfile` on a byte-copy of
the live CASTING SHEET, with the re-render stubbed: the real one rewrites the channel master's own
descriptor, which decides what the owner's next sitting runs, and a probe may not move that.

It proves: the cast lands in the sheet and is read back **from the file**, with the harness's own
level string stored (never the rung number); the re-render is invoked with `--repass`, against the
`--package` DERIVED from the inbox, on the same seat and sheet the write just landed in, and the
sheet **as the render saw it** already carried the new cast (a render that preceded the write would
render the OLD cast and report success); five refusal shapes leave the sheet's sha256 unchanged with
no render fired — including `test-sleep`, a DECLARED profile that is not castable, whose refusal
must name `validate_seat`; validation reads the roster **live** (the same name accepted against the
live document and refused against a copy it was renamed out of); an unknown SEAT refuses instead of
being created; and a **mutant** with the name lookup neutered goes green, so the refusal is proven
to come from that lookup.

⚠ **Check 6 is the surgical-write control, and it is not decoration.** It asserts that every line of
the sheet which is not the seat's own casting fields survives BYTE FOR BYTE, and that no character
was escaped into a `\uXXXX` sequence. On 2026-08-12 `bindings._write` dumped without
`ensure_ascii=False`, so writing three fields also rewrote five lines of hand-authored prose
(`—` → `\u2014`) in keys nobody touched — a live regression caught only because a human diffed the
file. This arm is the machine that catches it next time.

Check 8 runs the argv the `tools: master-profile` entry actually declares, as a SUBPROCESS, and
asserts it RUNS CLEAN and LANDS its edit. ⚠ It was inverted for one day (2026-08-11) to assert a
REFUSAL, while the tool was parked out of service — an arm asserting that the one surface the daemon
fires refuses is an arm that goes green on a broken capability. Disclosed bound: `--no-repass` is
appended, because the real renderer needs a real goal package and the fixture is a bare inbox, so
the subprocess covers every declared token and the drain-and-write, not the render; the render's own
argv is covered at function level by check 2.

Check 9 covers the self-report: `--chat-thread` stages the id and an unroutable one refuses at
request time; a threaded apply appends **exactly one** row, parsed back the way the ferry parses it
(fields by key) with the bracketed token, the old→new line and the takes-effect-next-message line,
ending in a newline; the stub's **snapshot of the bus** already holds that row (report precedes
render); an untokened request appends nothing; a refused one reports its refusal. The fixture's
inbox has the real `<goal>/settings-requests/<capability>` shape, because that is what BOTH the bus
path and the `--package` are derived from — and it keeps the probe off the live bus and the live
seat.

Check 10 covers the effort rung end to end, including the two sheet-only rules that REVERSE the
retired target's behaviour: a rung on an INERT profile is refused rather than stored, and a DIALLED
profile with NO rung is refused naming `effort-missing`. Check 10b proves a refused rung rides the
SAME `[deliver: wake]` outcome mapping check 9c proves for a refused profile name — one outcome
path, not a second.

⚠ **Check 10d pins FIVE objects by identity, not by value** — `cast_seat`, `catalog`, `profile_row`,
`profile_effort` and `Refusal` are all `bindings`' own objects, and a mutation control proves
`apply`'s write actually routes through the imported writer rather than around it. Value equality is
the vacuous version: two copies of the ladder reader agreed on the day they were written and drifted
silently after, which is the defect that earned this check. `Refusal` joined the list on 2026-08-12
because the two classes being distinct made every refusal `cast_seat` raised escape `main`'s handler
as a traceback instead of the `{"ok": false, "refusal": …}` envelope.

The daemon side of the lane has its own probe, `supervisor/spawn/probes/probe-effort-lane.js`: the
composer applies a rung on three differently-spelled harnesses, refuses out of range naming it,
leaves an inert profile's argv byte-identical, is byte-identical again when no rung is asked for,
and — the control that matters — shows the pre-ruling `args_schema` shape STILL refusing `effort`
with `unknown argument: effort` while the new one admits it.
