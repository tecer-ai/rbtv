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

## ⚠ There is no `--effort` flag, and that is a MEASUREMENT, not an oversight

The question was asked directly and traced end to end (2026-08-10). **Reasoning effort is not
carried on the master-sitting spawn path**, at three independent points:

| Where | What was found |
|---|---|
| `bridges/chat/forward-path.js` | the session-create enqueue is composed as `args: { profile, prompt }` — no effort key. The `chat-agent` job's registered `args_schema` is `{required:{profile}, optional:{prompt, workdir}}`, so a row carrying one would be **refused at the enqueue door** — and `register-job` is create-only, so that schema cannot be widened in place |
| `server/ticker/ticker.js#launchAgent` | reads exactly `args.profile` / `args.prompt` / `args.workdir`, then calls `spawnManager.spawn(execId, profileName, sessionMode, prompt, workdir, enqueuedBy, resumeRef)` — a seven-parameter signature with **no effort parameter at all** |
| the `effort:` block each profile declares | consumed only by `launch-profiles/resolveProfile`. `server/internal-api/dispatch.js` states its own status verbatim: `E_UNKNOWN_EFFORT` is *"raised only inside resolveProfile (the effort translation table), which has **NO daemon caller today**"*. `server/spawn/spawn.js` resolves `exec.argv` directly and never appends the effort argv |

So the dial exists in the config vocabulary and is **not connected**. Shipping `--effort` here would
have written a value nothing reads — a knob that turns and does nothing, which is worse than no
knob. Wiring it is a daemon change (tasks 7.43 / 7.54, both unbuilt), not a tool change.

What the master CAN change today is the profile, and a profile pins its model (`--model` is in every
`exec`/`resume` argv, and `headed.tui` pins it too since `d-s21-headed-tui-pins-model`).

## The three verbs

| Verb | What it does | Who runs it |
|---|---|---|
| `show [--json]` | the profile in force, whether it is explicit or the `session_profile` fallback, the exact `file:line`, and the **names that may be requested** | anyone, including a caged seat |
| `request <profile> --inbox D [--chat-thread C:TS]` | validate against the live roster → stage `{"master-profile": "<name>"}` (plus the thread id when given) → `ignite add-job` | **the seat** |
| `apply --inbox D --config F --profiles P [--no-restart]` | drain, edit the JSON, record the outcome, **report into the requester's chat thread**, restart `rbtv-chat-bridge` LAST | **the daemon**, via `tools: master-profile` |

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

```bash
# what is it now, and what may I ask for?
.../capabilities/master-profile/tool/rbtv-master-profile show

# change it (validates against the live roster, stages, enqueues — one command)
# `--chat-thread` is YOUR thread: the plain `chat-thread:` line at the top of your prompt.
.../capabilities/master-profile/tool/rbtv-master-profile request claude-opus \
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
from — and it keeps the probe off the live bus.
