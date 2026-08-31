---
description: Read at the moment a seat is about to background a check, arm a watcher, or end its turn expecting to be woken — and at the moment an orchestrator meets a seat that exited 0 with a stub report and uncommitted work.
tags: [planning]
---

# A headless seat cannot wait

A headless seat's SITTING lasts exactly as long as its TURN. There is no second turn to be woken into. A seat that ends its turn intending to continue later has ended the sitting, and everything it had not committed is orphaned.

This has cost FIVE sittings in one plan. It is not carelessness: every one of those seats wanted a GATE, and the gate they reached for was genuinely broken. A prohibition alone therefore fixes nothing — the working alternative is § *Scope the check down*, and it is the load-bearing half of this page.

## The mechanism

A headless seat is one agent process invoked non-interactively — `claude -p`, a `cast seat` launch, or a daemon-spawned sitting. The process runs ONE turn and exits. Nothing holds the session open between turns: there is no terminal reading from a person, no pump feeding new input, and no listener that can inject a message into a turn that has already ended.

Therefore:

- A notification, monitor ping, coordination message, or timer that arrives after the turn ends is delivered to NOTHING. It is not queued for the seat; the seat no longer exists.
- A process the seat backgrounded may keep running, but its result reaches no one — the reader of that result died with the turn.
- "I will wait for X and then commit" is not a plan. It is the end of the sitting, with the commit never made.

An INTERACTIVE sitting — a console session with a person at it — is the only place a wait is real, because the person supplies the next turn. NEVER carry a habit formed there into a seat.

## The signature — why it looks like success

The failure reports itself as a clean run. All four of these hold at once:

- exit code **0** — nothing errored; the agent chose to stop.
- a **stub report** — one sentence announcing the wait, and no findings. (Measured instance, 2026-08-31 19:44Z, seat `note-approval-gate`: the entire report was `I'll pause here and wait for the Monitor notification about coord.py selftest's outcome before proceeding to commit.`)
- **uncommitted work in the tree** — that seat left +61 lines in `ignite/coord/messages.py` and +40 in `ignite/coord/coord_selftest.py` unstaged.
- **no error anywhere** — no crash, no timeout, no refusal to point at.

An orchestrator reading only exit codes marks the seat done. An orchestrator reading only the report sees a seat that "is still working". Neither is true.

## The rule — run every check synchronously

A seat MUST run every check it depends on IN its own turn, in the foreground, and MUST read the result before that turn ends.

- NEVER background a check the seat's own conclusion depends on.
- NEVER arm a watcher, monitor, timer, or notification and end the turn expecting to be woken.
- NEVER end a turn with the words "wait", "pause here", "will continue when", or "then I will commit".

### Scope the check down

A check too slow to run whole is SCOPED DOWN, never deferred. In descending order of preference, stop at the first that fits inside the turn:

1. The single arm, case, or test that covers the change.
2. The one module, file, or suite section the change touches.
3. A cheaper check of the same property — a lint, a parse, a targeted grep, a direct call of the changed function.

Then REPORT the scoping in plain words: which check was run, what it covered, and what it did NOT cover. A scoped check honestly reported is a result. A full check nobody ran is nothing.

A check whose result the seat genuinely cannot obtain — the suite is red at pristine HEAD, the tool is broken, the gate does not run — is reported as an UNMET GATE with that reason named, and the seat finishes anyway. NEVER treat a broken gate as a reason to wait: waiting does not repair it.

## The one exception — hand back, never wait

A seat MAY leave work for ANOTHER agent to collect: an orchestrator, a successor seat on an `after` edge, or the owner. That is a HANDOFF and it is legitimate, because a different live agent does the collecting.

The line: a seat may hand work OVER; a seat may NEVER wait for it to come BACK. A handoff MUST be complete at the moment the turn ends — the collector holds everything it needs in the report and in what was committed, and needs nothing further from the seat that is gone.

## When a gate cannot be met — finish, do not stall

The seat MUST land at a clean checkpoint and report the gap:

1. Bring the work to a state that is provably correct on its own — the checks that DID run, run.
2. Commit that work by EXPLICIT PATHSPEC: `git commit -- <path> [<path>…]`. A shared, dirty tree makes any wider commit a theft of another session's lines. Immediately before staging, `git diff -- <your paths>` and confirm only your own delta is present.
3. Report, explicitly: what landed, which check was scoped or unmet and why, and what the next agent must verify.

An honest partial result that is COMMITTED beats a complete result that died uncommitted in a tree.

## For the orchestrator — detection and recovery

**Detect.** The three-part signature is mechanical, so check it on every seat return: exit 0 **and** a report with no findings **and** uncommitted changes on that seat's custody files. Any seat matching all three lost its sitting; NEVER mark it done on its exit code.

**Recover — resume the seat's OWN session; never re-launch it fresh.** A fresh seat re-derives from scratch and collides with the diff still sitting in the tree. The resume:

1. Locate that seat's session by its own id (identify it by its title tag from the session listing — a shared project store makes "the last session" the wrong session).
2. Point it back at ITS OWN surviving diff, naming the exact files.
3. NAME THE TRAP in the resume instruction: it ended its turn waiting, the wait can never be answered, and it MUST finish and commit synchronously in this turn.

Measured outcome: the resumed `note-approval-gate` seat carried its surviving diff forward, re-measured its own premise, and finished cleanly in one further turn.
