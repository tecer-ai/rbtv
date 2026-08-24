# 20260824-c-approval-thread-3-message-kind — approval thread: §3 message, kind fork, thread-bound pause

kind: creation
component: bridges
date: 2026-08-24
commit: 7f4fbefc
deployed: no
pin: bridges/chat/probes/probe-chat-approval.js

## Motivation
`spec-owner-io` §3 and §4.2 pin an approval that is GOAL-NAME-PROMINENT and THREAD-BOUND
[D-5-ruling, CF-7], and neither existed. Approval was a word with no home: an `approve` anywhere in
Slack could fire, the irreversible effect (execution starts) was never stated, the commit the
approval binds to [T5-R5] was never recorded in the message, and there were no separate reject
outcomes — a rejection could only be prose the next agent had to interpret.

## Design
Two modules, and the fork between them is the ask's `kind`, never the token.

`approval-thread.js#composeApprovalBody` builds the §3 body that goes UNDER `ask-thread.js`'s
opening line: the GOAL NAME and the IRREVERSIBLE EFFECT each as their own bold lead line before any
other body, then the phone-sized digest, the bound `commit_id`, the canvas link (or "none —
artifacts on disk"), and the six accepted tokens. It THROWS without a goal name or a commit rather
than composing an unbound approval — an approval that names no commit approves whatever the tree
holds later.

`approval-thread.js#createApprovalDispatch` decides what an outcome DOES, above the release door.
Rejected shapes: putting the fork inside `reply-grammar.js` (the parser is ONE for both thread kinds
by §4, and a kind-aware parser is two parsers), and putting it inside `ask-thread.js#release` (that
module is the release RULE — exact thread, authorized sender, parse, reap — and an effect table
inside it is what grows a second door).

Every effect is an INJECTED PORT — `materialize` (D12, `planning/path_b.py#run_path_b`), `closeGoal`,
`pauseGoal`, `relaunchDraftVerify` — because `probes/probe-chat-boundary.js` forbids this process a
spawn path, a store handle and a sibling require. A port that refuses, INCLUDING one that is not
wired, reports back into the SAME approval thread [C-16] and leaves the thread usable.

## How it works
`chat-bridge.js#postOwnerAsk` gained `kind` and `commitId`; the `askThreads` entry carries both plus
`paused`, persisted additively with `STATE_VERSION` unchanged. `releaseAskFor` runs the release
first (auth + parse + reap are unchanged), then forks: only `entry.kind === 'approval'` reaches
`dispatch`. `approve` there is D12; the same word in any other thread is the outcome the release
already delivered to the seat.

`reject-and-close` and `close` close the planning goal and the bridge forgets the thread.
`reject-and-retry` and `retry with:` call `relaunchDraftVerify` with the comments as the findings
list [T3-R21] and keep the thread. `reject-and-pause` pauses the goal and turns the thread into the
ONLY door out [T3-R22]: the entry keeps `paused: true`, and `ask-thread.js#release` is then called
with the new `reap: false` knob so the later reads are authorized and parsed by the same door
without reaping a second time — a second reap is a second relaunch signal on a seat nobody re-asked.
Inside that pause only `retry with:` / `approve` / `close` are exits; any other recognized token
changes nothing and is answered in-thread, because silence there rebuilds [F-owner-ux-2].

## Consequences
Nothing was replaced or deleted. `ask-thread.js` gained exactly one parameter (`reap`), default
`true`, so every existing caller behaves identically — `probe-chat-ask-release` stayed green
unchanged. `ask-store.js` was not touched: `kind` is a bridge-side routing fact and the
`record-owner-ask` intent's payload schema is closed at the gateway.

NOT REACHABLE IN PRODUCTION. `index.js#main()` wires no `approvalPorts`. The bridge is a separate
process reaching the daemon only over the gateway, whose intent set (`gateway/parse.js#INTENTS`)
carries no materialize intent; minting a fourteenth is an owner act, as the thirteenth
(`record-owner-ask`) was on 2026-08-24. Until then `approve` posts the [C-16] failure into the
thread — loud, never silent.

## Verification
`probes/probe-chat-approval.js`, new, 22 checks, EXIT=0: the four §3 first-message properties
(goal-name bold lead line, irreversible bold lead line, bound commit, published tokens) plus the
composer's refusal to compose unbound; `approve` in an ORDINARY thread released to the seat with the
materialize port counted at ZERO, and the same word in the approval thread firing it EXACTLY ONCE
with the right commit and ask id; each of the five other outcomes dispatching to its own port; the
[T3-R22] pause proven by a non-exit token calling no port at all and by all three keys exiting; the
`kind` and pause flag surviving a state write; and a materialize refusal posting back into the same
thread with the thread left usable for the retry that follows. Red-armed by mutation: forcing
`isApproval = true` reddens B1–B3, and deleting the pause gate reddens D2. `node --check` exit 0 on
every touched file. `node deploy/probe-suite.js --dir bridges/chat/probes` 25/25 GREEN. Not deployed
— worktree branch `ignite/core-redesign`.

## ATTENTION
1. THE FORK IS `kind`, NEVER THE TOKEN. A future edit that dispatches on the word `approve` alone re-creates exactly the defect this replaces: a bare `approve` typed in any goal channel thread would start an execution goal. The `askThreads` entry's `kind` is the whole guard, and it is why `kind` had to become persisted state.
2. `reap: false` EXISTS FOR ONE CALLER. A `reject-and-pause`d approval thread was already released and reaped; the later `retry with:` / `approve` / `close` must be authorized and parsed by the same door but must not reap again. Passing `reap: true` there fires a second relaunch signal on a seat nobody re-asked.
3. A MISSING PORT IS REPORTED AS A [C-16] FAILURE, NOT AS SUCCESS AND NOT AS SILENCE. An embedder who stubs `materialize` to `{ok: true}` to "make it work" produces a bridge that tells the owner execution started when nothing did — the worst possible lie on this surface.
4. THE THREE PAUSE KEYS ARE A CLOSED LIST AND THE NON-EXIT ANSWER IS AUTHORED PROSE, not one of the two §4.5 verbatim NACKs. Those two answer an UNPARSED token; a token that parsed and simply is not a key is a different message, and posting a §4.5 NACK there would tell the owner their vocabulary was wrong when it was not.
5. THE §3 BODY IS THE SAFETY DEVICE. The two bold lead lines are load-bearing [D-5-ruling] — the failure they replace is an owner approving on a phone without seeing which goal is about to execute. A reflow that merges them into a paragraph, or that moves the digest above them, silently removes the guard while every test that only greps for the strings still passes.
- The dispatch fork is the ask's kind, never the token — dispatching on the word approve re-creates the D-5-ruling defect
