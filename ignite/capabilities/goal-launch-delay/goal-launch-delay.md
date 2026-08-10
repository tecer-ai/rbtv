# goal-launch-delay — the channel master retiming its own queue delay

Issue **C-1** (owner-ruled 2026-08-10). One of two capabilities built the same day for the same
reason: the channel master had no self-service control over two of its own operating parameters.
Its twin is `master-profile`.

The tool is `tool/rbtv-goal-launch-delay`.

## What the knob actually is

**There is no "delay setting" in this system.** The delay is the operand of `--delay-seconds` in
the `tools: goal-creation-request:` argv of `config/spawn-profiles.yaml`, read by
`goal_creation_request.py#scaffold_and_queue` and turned into the queued job's `--at`. When the flag
is **absent** from that argv, the tool's own argparse default (600) applies — so *absent* and *600*
are the same effective value reached two different ways, and `show` says which of the two is in
force rather than printing a number that hides the difference.

The owner's ruling was explicit about the shape: **do not change the system; give the agent a tool
to interact with it in its native place.** So this capability edits those two lines of YAML and
nothing else. No settings file, no mirrored value, and **never a YAML round trip** — that document
is ~1300 lines whose comments are its documentation, and a dump-and-rewrite would delete them.

## The three verbs

| Verb | What it does | Who runs it |
|---|---|---|
| `show [--json]` | the delay in force, whether it is explicit or the tool default, the exact `file:line` it comes from, and the reminder that it is boot-read | anyone, including a caged seat — the cage's bind is read-only, not unreadable |
| `request <seconds> --inbox D [--chat-thread C:TS]` | validate → stage `{"delay-seconds": N}` (plus the thread id when given) into the seat's own folder → `ignite add-job` the daemon-side job | **the seat** |
| `apply --inbox D --config F [--no-restart]` | drain the inbox, edit the YAML, record the outcome, **report into the requester's chat thread**, restart `rbtv-ignite` LAST | **the daemon**, via `tools: goal-launch-delay` |

Exit 0 when everything drained was accepted (or the inbox was empty), 1 otherwise — the same
per-fire exit convention as `goal-creation-request`, with the same consequence: **one junk file
staged by the requester marks the whole `fire-tool` execution `failed`** even when a real request in
the same fire succeeded. `failed` here means "not every request succeeded", never "nothing
happened"; the per-request truth is in `done/` vs `refused/`.

## Why the transport is split in two, and why neither half is a preference

Measured — the same measurement `goal-creation-request` was built on, re-confirmed for this file:

| Measured | Reading | Consequence |
|---|---|---|
| The channel master's cage binds the rbtv repo **read-only** (`touch` → `Read-only file system`) | A CLI run by the seat cannot write `spawn-profiles.yaml`, and no care taken in the tool changes that | The edit MUST happen daemon-side |
| The same seat CAN write inside its own seat folder | The payload transport | The requested value is **file-staged** there |
| `fire-tool` argv is **static** — only `args.workdir` crosses from a queue row | No gateway verb can carry a request BODY to a fired tool | Hence a file, and hence a drained DIRECTORY: one fixed argument must serve every request |
| `enqueue-job` carries **no authz gate** (owner ✅ agent ✅ bridge ✅), while `register-job` is refused to a `bridge` token | The trigger works whichever sender kind the master presents | The trigger is `enqueue-job` |

## ⚠ The restart is the LAST act, and the ordering is load-bearing

`spawn-profiles.yaml` is boot-read (`loadMergedConfig`, no `fs.watch`), so an edit not followed by a
daemon restart changes nothing observable. But a fired tool restarting the daemon that fired it is a
process asking to be killed mid-run. Two things make that safe, and neither is a promise:

1. **It is not actually a child.** `runToolLikeExec` launches through `systemd-run --user`, which
   creates its own transient unit under the user manager — not a process inside
   `rbtv-ignite.service`'s cgroup. It survives the restart. *Measured at build time: the live test's
   own outcome record was written after the restart it performed.*
2. **We do not lean on that anyway.** The YAML is written with tmp + `os.replace` (atomic) and every
   outcome record is on disk **before** the restart is invoked. A kill mid-restart loses nothing but
   the `restart` field's final value, which then honestly reads `pending`.

**One restart per fire, not one per request** — restarting three times because a requester staged
three files would take supervision down three times to reach one end state.

Auto-restart by the seat is owner-approved (`d-master-zero-restrictions-accepted`).

## What is validated, and where

The **same** validator runs in both halves. The client so a typo refuses in the sitting that made
it; the daemon because a client-side check is not a check — the payload file is written by the
requester and can be edited between staging and the fire.

- an integer, and only an integer: `"600"` and `1.5` are **refused, not coerced** (the coercion is
  where a `1.5` becomes a `1`);
- inside `[1, 86400]` (one day). Over-ceiling is **refused, not clamped**: a silently clamped value
  hides the mistake behind a plausible number;
- the payload's key set must be exactly `{"delay-seconds"}`.

Two structural refusals sit above those: a `--delay-seconds` appearing **twice** in the target argv
(argparse takes the last; guessing which one the daemon honours is not this tool's call), and a
symlinked inbox or settle target — the inbox lives inside the *requester's* folder, so a
pre-created link would relocate the daemon's writes outside the cage. Both refuse the whole fire.

Every outcome — accepted or refused — is written as `<name>.outcome.json` beside the settled request
in `done/` or `refused/`, **inside the folder the requester staged into**. An outcome a caged
requester cannot read is a silent drop.

## ⚠ `--chat-thread` — the outcome reports itself back into the owner's thread

Issue `i-profile-switch-no-feedback` (owner-ruled 2026-08-10); the twin `master-profile` gets the
identical change, so the two knobs behave the same way. The outcome record in `done/` is durable but
**silent**: the sitting that asked has ended its turn, and the owner watches a thread where nothing
ever answers. So `request` takes `--chat-thread <channel>:<ts>` — the sitting's own thread, which it
already knows from the plain `chat-thread:` line at the top of every prompt — the staged payload
carries it as `"chat-thread"`, and `apply` reports the outcome there.

**This tool posts nothing.** It appends ONE row to the requesting goal's coordination bus
(`<goal>/coordination/messages.md`, derived from the inbox — never a named goal), addressed
`to: owner`, whose body carries the **bracketed** `[chat-thread: <id>]` token;
`bridges/chat/bus-ferry.js`'s return leg is what carries it into the thread. Bracketed is the
routing form — the plain form a prompt carries is deliberately inert — and the return leg is read
**before** the two contact gates, so the report travels on a goal that may not *initiate* contact.
The append goes through `coord.py#append_message`, the one allocator of bus ids (and the owner of
the header grammar, the package lock, and the trailing newline the ferry's torn-write rule needs).

| Property | Why |
|---|---|
| ACCEPTED **and** refused both report | "your change did not happen, and here is why" is the answer the owner is owed most |
| the report precedes the restart | restart-last is the ruled invariant above, so the row **cannot** state the restart's exit code — it states what is *about to* happen. The rc stays in the outcome record |
| a failed append never aborts the apply | the retiming is the job, the report is the courtesy — it is recorded as `chat-report.error` in the outcome record and the fire continues |
| no token → nothing is appended | pre-existing callers keep the behaviour they had |
| a token the ferry could not route is **refused**, at both halves | the shape mirrors `bus-ferry.js`'s `CHAT_THREAD_RE` anchored; an accepted-but-unroutable token is a report nobody receives |

The bracketed token is visible to the owner in the delivered message — unavoidable, since the token
must ride in the row's body for the ferry to route on it. It sits on the last line, as a footer.

## How the seat drives it

```bash
# what is it now?
.../capabilities/goal-launch-delay/tool/rbtv-goal-launch-delay show

# change it (validates, stages, enqueues — one command)
# `--chat-thread` is YOUR thread: the plain `chat-thread:` line at the top of your prompt.
.../capabilities/goal-launch-delay/tool/rbtv-goal-launch-delay request 900 \
  --chat-thread C0ABCDEFG:1754812345.123456 \
  --inbox /home/henri/ht-wkdir/second-brain/.rbtv/goals/_channel-master/settings-requests/goal-launch-delay

# what happened to the request the last sitting made?
ls .../settings-requests/goal-launch-delay/done .../settings-requests/goal-launch-delay/refused
```

The daemon fires within a tick or two; the value is live once `rbtv-ignite` finishes restarting.

## Arming it — three gated acts, in this order

Landing the catalogue entry does not arm it, exactly as for `goal-creation-request`:

1. create the inbox directory the entry names
   (`.rbtv/goals/_channel-master/settings-requests/goal-launch-delay`);
2. restart the daemon — `spawn-profiles.yaml` is boot-read;
3. `ignite register-job goal-launch-delay --action-type fire-tool --args-schema '{"required":{"tool":"string"}}'`.

Out of order, step 2 logs one `catalogue-paths` error per boot for an `--inbox` that does not exist
yet (that check logs; it never refuses the boot). `register-job` is create-only and is refused to a
`bridge` token — it is an operator act, done once; the seat only ever needs `add-job`, which the
`request` verb issues for it.

## Probe

`probes/probe-goal-launch-delay.py` — run it through the enumerator
(`node deploy/probe-suite.js --only probe-goal-launch-delay`), never by hand. It runs entirely under
`tempfile` on a byte-copy of the live YAML with the restart stubbed, and proves: the edit lands and
is read back **from the file**; the restart is invoked and the config **as the restart saw it**
already carried the new value (the check that discriminates edit-then-restart from
restart-then-edit); five refusal shapes each leave the config's sha256 unchanged with no restart
fired; an accepted edit moves **exactly one line** of 1316; the absent-flag insert arm works; and a
**mutant** that widens the ceiling goes green, so the over-ceiling refusal is proven to come from
the ceiling check rather than from something refusing everything. Check 8 covers the self-report:
`--chat-thread` stages the id and an unroutable one refuses at request time; a threaded apply
appends **exactly one** row, parsed back the way the ferry parses it (fields by key) with the
bracketed token and the old→new line, ending in a newline; the restart stub's **snapshot of the
bus** already holds that row (report precedes restart); an untokened request appends nothing; a
refused one reports its refusal. The fixture's inbox has the real
`<goal>/settings-requests/<capability>` shape, because that is what the bus path is derived from —
and it keeps the probe off the live bus.
