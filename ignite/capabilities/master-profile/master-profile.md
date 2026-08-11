# master-profile — the channel master choosing its own harness and model

Issue **C-1** (owner-ruled 2026-08-10). Twin of `goal-launch-delay`: same ruling, same two-part
transport, different file, different validator, different unit restarted.

The tool is `tool/rbtv-master-profile`.

## What the knob actually is

`master_profile` in `.rbtv/config/chat-bridge-config.json`. The bridge reads it at boot
(`bridges/chat/config.js`) and `forward-path.js#profileFor` selects it for **master (DM)** traffic:

```js
return config.masterProfile || config.sessionProfile;
```

so an absent or empty `master_profile` silently falls back to `session_profile` — which is why this
tool **refuses to create the key** rather than inventing one (below). The value is a spawn-profile
NAME from `profiles:` in `config/spawn-profiles.yaml`; today's live set is fourteen names
(`claude-fable` · `claude-opus` · `claude-sonnet` · `claude-haiku` · `codex-gpt-5-5` · `kimi` · the
`opencode-*` set · `test-sleep`), and `show` prints it rather than restating it here, because a
roster written into a document goes stale silently.

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
| `bridges/chat/config.js` | reads `master_effort` (integer, shape-checked at boot) |
| `bridges/chat/forward-path.js#effortFor` | pairs it with the **master** profile and puts it in the enqueue `args` (goal/agent traffic carries none) |
| the catalogue job id | a **new** id whose `args_schema` declares `"effort": "integer"`, named by `session_job_id`. Registration is create-only, so the old id could not be widened — it stays registered and still refuses, retired in place |
| `server/ticker/ticker.js#launchAgent` | reads `args.effort`, passes it to `spawnManager.spawn(...)` |
| `server/spawn/spawn.js#composeArgv` | composes it through `resolveEffort()` — the **same** function `launch-profiles/resolveProfile` calls, never a second reading of the table |

`dispatch.js`'s five "re-rule at 7.43/7.54" notes are now four: `E_UNKNOWN_EFFORT` is re-ruled and
raised live. **Half selection is still refused** (G-144) and still belongs to 7.43/7.54 — the
effort ladder was separable from it, which is why this could ship without that refactor.

⚠ **The MODEL half is built too** (ruling D19, 2026-08-11, run `ignite-planning-hardening`). Task
7.54's `(harness, model) → profile-name` catalog is live — `launch-profiles/catalog.js`, applied at
`server/spawn/spawn.js#profileForSeatCast` — so a seat that declares `harness:`/`model:` in its own
`seat.md` now launches on the profile it is cast as, on every lane, including a chat revival. That
does **not** touch this capability: the channel master declares no cast by design
(`materialize-seats.py#open_binding` — its harness and model stay the chat bridge's to name), which
is exactly the fallback case the catalog leaves alone, so the master's profile knob behaves as
documented above.

## ⚠ What a rung IS — a number, 1..N, in **that profile's** ladder

Owner ruling **`d-0811lp-effort-numeric-per-profile`**: *"use N levels (1-N), from lower to higher
reasoning. this way each harness/model can have as many as they want."* Rung 1 is the lowest
reasoning, rung N the highest, and **N differs per profile** because each harness's real dial does:

| Profile | Ladder | Mechanism |
|---|---|---|
| `claude-fable` · `claude-opus` · `claude-sonnet` | 1..5 — low · medium · high · xhigh · max | `--effort <level>` |
| `codex-gpt-5-5` | 1..3 — low · medium · high | `-c model_reasoning_effort=<level>` |
| `kimi` | 1..2 — `--no-thinking` · `--thinking` | the rung IS the flag |
| `claude-haiku`, every `opencode-*`, `test-sleep` | **inert** | no dial exists — measured, not assumed |

- **Out of range is refused, loudly, naming the range** — at `request`, again at `apply`, and again
  at the spawn. A rung is only meaningful against a profile, so it is always checked against the
  profile the request is switching **to**, never the one in force.
- **An inert profile ACCEPTS a rung and applies none** (G-270), and says so. So a rung set while
  the master runs on `claude-haiku` visibly does nothing — the honest report, not a defect.
- **No rung at all = the harness default**, which is exactly the behaviour before this existed.
- `show` prints every profile's ladder, so nobody has to know N out of band.

## ⚠ The rung is written WITH the profile, and an omitted rung CLEARS the old one

`request claude-opus --effort 4` writes both fields. `request codex-gpt-5-5` — no `--effort` —
writes the profile and **removes** `master_effort`. That is not tidiness: rung 4 chosen for a
five-rung harness, left behind across a switch to a three-rung one, passes every door in this tool
and then **refuses at the spawn**, one owner message later — the exact failure the profile-name
validation exists to prevent, one field over.

(`master_profile` itself is still never *created* by this tool — see below. `master_effort` is,
because an absent `master_effort` has no second meaning: it is simply "harness default", and a knob
that can be turned up but never down is worse than no knob.)

## The three verbs

| Verb | What it does | Who runs it |
|---|---|---|
| `show [--json]` | the profile **and rung** in force, whether the profile is explicit or the `session_profile` fallback, the exact `file:line`, and **every profile with the rungs it admits** | anyone, including a caged seat |
| `request <profile> [--effort N] --inbox D [--chat-thread C:TS]` | validate the name against the live roster **and the rung against that profile's ladder** → stage `{"master-profile": …, "effort": N}` (plus the thread id when given) → `ignite add-job` | **the seat** |
| `apply --inbox D --config F --profiles P [--no-restart]` | drain, re-validate, edit **both** JSON fields, record the outcome, **report into the requester's chat thread**, restart `rbtv-chat-bridge` LAST | **the daemon**, via `tools: master-profile` |

Exit 0 when everything drained was accepted (or the inbox was empty), 1 otherwise.

## Why the transport is split in two

Identical to `goal-launch-delay` and to `goal-creation-request` before it, and the reasoning is not
restated here (`goal-launch-delay.md` § *Why the transport is split in two* carries it): the cage
binds `.rbtv/config` read-only, `fire-tool` argv is static so the payload travels as a file, and
`enqueue-job` is the one gateway verb open to a `bridge` token.

## ⚠ Validation is against the LIVE roster, at both halves

An unknown profile name **does not fail at the bridge**. It fails at the *spawn*, one owner message
later, with the sitting already accounted for — which is why the name is checked at the door and
again at the fire, and why the refusal names the whole live set back to the requester.

The roster is **read** from `spawn-profiles.yaml`, never carried as a copy: a list frozen in the tool
would refuse a profile that exists or admit one that was removed, the second being the failure that
reaches the spawn. Adding a profile to that file needs no edit here.

*ponytail:* the read is a line scan of the two-space keys under `profiles:`, not a YAML parse.
Ceiling: a profile declared with a non-standard indent or a quoted key would be missed. Upgrade path
if that ever happens: PyYAML is already a daemon dependency — but a parse here would be the only
reader of this document that needs one, for a question a scan answers exactly.

## ⚠ An absent `master_profile` refuses rather than being created

If the key is not in the file, master traffic is riding `session_profile` **by fallback** — a live
configuration choice. Minting the key would split the two surfaces apart without anyone deciding to.
That is an operator's edit (one line of JSON), not a requester's; once it exists, this tool owns it.

## ⚠ The restart ends the owner's live chat session

`rbtv-chat-bridge.service` is boot-read, so there is no cheaper way to apply this — and the sitting
that made the request is the one that dies. Hence the ordering, which is the same as the twin's and
for the same reason: **edit (atomic `os.replace`) → outcome record on disk → restart last**. The
next sitting reads what happened to the request the previous one made. `request` says this out loud
in its own output rather than leaving the seat to discover it.

The restart is delegated to `daemon-operator` (`restart --service chat-bridge`), never
re-implemented (`PRIN-11`) — which is also what lets `RBTV_IGNITE_UNIT` steer the probe at a
throwaway unit.

## ⚠ `--chat-thread` — the outcome reports itself back into the owner's thread

Issue `i-profile-switch-no-feedback` (owner-ruled 2026-08-10). The outcome record in `done/` is
durable but **silent**: the sitting that asked is killed by the restart, and the owner watches a
thread where nothing ever answers. So `request` takes `--chat-thread <channel>:<ts>` — the sitting's
own thread, which it already knows from the plain `chat-thread:` line at the top of every prompt —
the staged payload carries it as `"chat-thread"`, and `apply` reports the outcome there.

**This tool posts nothing.** It appends ONE row to the requesting goal's coordination bus
(`<goal>/coordination/messages.md`, derived from the inbox — never a named goal), addressed
`to: owner`, whose body carries the **bracketed** `[chat-thread: <id>]` token;
`bridges/chat/bus-ferry.js`'s return leg is what carries it into the thread. Bracketed is the
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
`wake` sibling: `bridges/chat/bus-ferry.js` § `deliverToken`; design `live-session-design.md` §3a.

| Property | Why |
|---|---|
| ACCEPTED **and** refused both report | "your switch did not happen, and here is why" is the answer the owner is owed most |
| the report precedes the restart | restart-last is the ruled invariant above, so the row **cannot** state the restart's exit code — it states what is *about to* happen. The rc stays in the outcome record |
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
and a request naming **no** effort omits the rung rather than guessing one.

```bash
# what is it now, and what may I ask for?
.../capabilities/master-profile/tool/rbtv-master-profile show

# change it (validates name AND rung against the live config, stages, enqueues — one command)
# `--chat-thread` is YOUR thread: the plain `chat-thread:` line at the top of your prompt.
# `--effort` is OPTIONAL: omit it for the harness default — and note that omitting it CLEARS any
# rung currently set, because a rung belongs to the profile it was chosen for.
.../capabilities/master-profile/tool/rbtv-master-profile request claude-opus --effort 4 \
  --chat-thread C0ABCDEFG:1754812345.123456 \
  --inbox /home/henri/ht-wkdir/second-brain/.rbtv/goals/_channel-master/settings-requests/master-profile

# what happened to the request the last sitting made?
ls .../settings-requests/master-profile/done .../settings-requests/master-profile/refused
```

## Arming it — three gated acts, in this order

1. create the inbox directory the entry names
   (`.rbtv/goals/_channel-master/settings-requests/master-profile`);
2. restart the daemon — `spawn-profiles.yaml` is boot-read;
3. `ignite register-job master-profile --action-type fire-tool --args-schema '{"required":{"tool":"string"}}'`.

`register-job` is create-only and refused to a `bridge` token — an operator act, done once. The seat
only ever needs `add-job`, which the `request` verb issues for it.

## Probe

`probes/probe-master-profile.py` — run it through the enumerator
(`node deploy/probe-suite.js --only probe-master-profile`). Entirely under `tempfile` on a byte-copy
of the live bridge config with the restart stubbed. It proves: the edit lands and is read back from
the file; the restart is invoked **at the bridge unit and never at the ignite unit**, and the config
as the restart saw it already carried the new value; four refusal shapes leave the file's sha256
unchanged with no restart fired, the unknown-name refusal naming the live set back; validation reads
the roster **live** (a profile present only in a copy is accepted against that copy, and one absent
from a copy is refused against it — a hard-coded roster fails this and only this); an absent key
refuses instead of being created; exactly one line moves and the document's own indentation survives;
and a **mutant** with the membership check neutered goes green, so the refusal is proven to come
from that check. Check 9 covers the self-report: `--chat-thread` stages the id and an unroutable one
refuses at request time; a threaded apply appends **exactly one** row, parsed back the way the ferry
parses it (fields by key) with the bracketed token, the old→new line and the scope line, ending in a
newline; the restart stub's **snapshot of the bus** already holds that row (report precedes restart);
an untokened request appends nothing; a refused one reports its refusal. The fixture's inbox has the
real `<goal>/settings-requests/<capability>` shape, because that is what the bus path is derived
from — and it keeps the probe off the live bus. Check 10 covers the effort rung end to end: the
ladders are read off the LIVE `spawn-profiles.yaml` per profile; `request --effort` stages the rung
and `apply` writes `master_effort` beside `master_profile` **in the file**, read back off the file
rather than off the record; the SAME rung is refused on a shorter-laddered profile and accepted on a
longer one, which is what proves the range is the profile's and not a global ceiling; an inert
profile accepts it and records `effort-inert`; and a switch with no rung clears the stale one. Check
10b proves a refused rung rides the SAME `[deliver: wake]` outcome mapping check 9c proves for a
refused profile name — one outcome path, not a second.

The daemon side of the lane has its own probe, `server/spawn/probes/probe-effort-lane.js`: the
composer applies a rung on three differently-spelled harnesses, refuses out of range naming it,
leaves an inert profile's argv byte-identical, is byte-identical again when no rung is asked for,
and — the control that matters — shows the pre-ruling `args_schema` shape STILL refusing `effort`
with `unknown argument: effort` while the new one admits it.
