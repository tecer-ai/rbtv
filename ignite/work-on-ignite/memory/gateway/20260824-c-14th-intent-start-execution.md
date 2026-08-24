# 20260824-c-14th-intent-start-execution — 14th intent: start-execution

kind: creation
component: gateway
date: 2026-08-24
commit: a49f9df8,dae7b4f5
deployed: no
pin: ignite/server/internal-api/probes/probe-start-execution.js
components: bridges,server,capabilities

## Motivation
`spec-owner-io` §4.2 makes `approve` in a `kind=approval` thread the D12 trigger that BIRTHS an
execution goal [D-5-ruling, CF-7], and `planning/path_b.py#run_path_b` is the supervised birth it
must call. The bridge could not call it: `bridges/chat` is a SEPARATE PROCESS and
`probes/probe-chat-boundary.js` forbids a child process, a store handle and a sibling require in
that subtree. So `approval-thread.js` shipped (7f4fbefc) with `materialize` as an injected port and
nothing legal to inject — every `approve` in production would have posted the [C-16] failure into
the thread instead of starting anything. The same wall the thirteenth intent hit for `open_asks`,
one layer up: the capability is real, the process that witnesses the owner act may not hold it.

## Design
The owner ruled option (b) on 2026-08-24 (`redesign-implementation/decisions.md`, the 14th-intent
entry): mint ONLY `start-execution`, whose daemon-side executor calls the Path-B birth, same
pattern as the thirteenth (`record-owner-ask`). The ruling is cited in `gateway/parse.js` and
`dispatch.js` the way the twelfth and thirteenth cite theirs, because a new intent widens the
daemon's authenticated surface and is an owner act, not an implementation detail. The PAUSE-word
intent was deliberately not minted — pause stays store-side until the old execution-lane reconcile
gate converges onto the goal-state row — so the pause path is untouched by this landing.

ONE act, and that is the ruling's shape, not a simplification: the verb it would have forked
against is the one the owner declined. The payload is therefore a closed three-key set rather than
a per-act union, refused key by key — `goal`, `thread`, `commit`. Two things it deliberately does
NOT carry. There is no plan and no `execution_goal`: WHAT gets built is the approve-package the
planning goal already holds at `planning/approve-package.json`, read daemon-side, so a caller
cannot approve one plan and start another. And there is no `comments` field: the owner's prose
after `approve` is a retry's findings list [T3-R21], and a birth determined by a package and a
commit has no use for it — with the schema closed, sending it is a REFUSAL rather than an ignored
key.

The rejected shape was keeping `materialize` injectable at `chat-bridge.js` and wiring the real
sender as its default. It was rejected because that seam is exactly where an embedder writes
`materialize: async () => ({ok: true})` to make a test pass, and the resulting bridge tells the
owner an execution started when nothing did — the worst lie available on this surface. An injected
`materialize` is now REFUSED at construction.

## How it works
`bridges/chat/start-execution.js#createExecutionStart({forwarder})` is the sender and fills the
port `approval-thread.js` was already written against; that module is byte-unchanged. It forwards
`{goal, thread, commit}` with a per-call timeout override — `live-feed`'s precedent, one intent's
patience rather than a raised default — because a birth is scaffold + mint under the materialize
lock, not a store write. `chat-bridge.js` builds it from the forwarder it already holds, always.

`gateway/parse.js` registers the intent and checks SHAPE only: the two names against `BUS_NAME_RE`,
the commit against lowercase hex 7-64. A REF NAME is refused there and again at the core — a branch
or tag is a MOVING binding standing in for the tree the owner actually read [T5-R5].
`internal-api/dispatch.js#handleStartExecution` runs the ladder every sibling uses (strict schema,
shape, authorization, act) and `authz.canStartExecution` is BRIDGE-ONLY, joint-narrowest with the
twelfth's and thirteenth's predicates and with the largest consequence of the three.

`server/heart/start-execution.js` performs the act and trusts the bridge for NOTHING about the
approval: a `kind=approval` thread is a fact of the CALLING process's own map and therefore not
evidence. It checks the record the daemon itself wrote — the thirteenth intent's `open_asks` row:
the thread is an ask this daemon opened (`ask_id` IS the Slack thread [T5-R7]), it is bound to the
goal the caller names, and it carries an `authorized_reply_at`, which only `reapAndRelaunch` stamps
and only the §2.4 release door reaches (exact thread, authorized sender, parse, reap). That last
check is what makes a NON-APPROVAL-THREAD caller a refusal instead of an execution goal. Then it
compares the caller's commit to the package's `bound_commit`, stamps the three fields the daemon
owns (`planning_goal`, `goals_root`, `origin_id` = the approval thread) rather than reading them
from the file, and runs `path_b.py --package` through `wrapper.py#supervised_materialize`. A
package naming a different planning goal or goals root is refused rather than silently overwritten,
so a stale copy cannot read as this goal's plan.

The two failure shapes are different in kind on purpose. A refusal above is a typed error: nothing
was attempted. A supervised-materialize failure comes back as DATA carrying the wrapper's six-field
record — already written onto the PLANNING goal by `record_goal_folder=`, because a birth that
failed has no execution goal to stamp — because the caller's job with that record is to put it in
front of the owner in the approval thread [C-16], which is a report, not an error to swallow.

## Consequences
Nothing was deleted except one seam: `approvalPorts.materialize` is no longer accepted and an
embedder passing one is refused at construction. `approval-thread.js`, `ask-thread.js` and
`ask-store.js` are untouched. `endingStore` and the other three approval ports (`closeGoal`,
`pauseGoal`, `relaunchDraftVerify`) remain unwired and still degrade loudly — the pause-word intent
they wait on is the one the ruling declined.

`probe-chat-approval` was rewired at the cause rather than patched: its D12 counter used to be a
stub port, which could only prove the bridge calls a function. It now counts `start-execution`
forwards on the fake forwarder, so the approve-fires-exactly-once checks measure the daemon
CROSSING — the same lesson the thirteenth's ATTENTION-3 records about naming call logs and job logs
differently, reached from the other side.

The approve-package location is a NEW CONVENTION this landing establishes and nothing writes yet:
the planning pipeline must leave `planning/approve-package.json` on the planning goal. Until it
does, a genuine `approve` refuses `no-approve-package` and says so in the thread — an honest,
loud gap, not a silent one.

## Verification
`probe-start-execution.js`, new, 20 checks EXIT 0: bridge-only authz (agent, proven goal-master and
even the owner refused), four gateway shape refusals (unknown `comments` key, ref-name commit, path
separators in the goal, missing commit), five binding refusals (`no-approval-record`,
`ask-not-released`, `ask-not-bound-here`, `commit-not-bound`, `no-approve-package`), the happy birth
with its daemon-stamped package fields, the six-field failure record coming back as data, a package
bound elsewhere, and a red arm by mutation. Red-before proven on the LIVE file, not assumed: with
the `no-approval-record` guard removed, R1 reaches the real `path_b.py` subprocess and tries to
birth a goal from a thread nobody approved in; restored, 20/20.

`probe-chat-approval` 24 checks EXIT 0 with D12 counted at the gateway, including the two added legs
(the crossing's intent name / three-key payload / longer timeout, and the construction refusal of an
injected `materialize`). `probe-chat-boundary` PASS — the bridge subtree still holds no store handle,
no child process and no sibling require. Chunked with `RBTV_IGNITE_SRC` on the worktree:
`bridges/chat` + `gateway` + `server/internal-api` + `cli` 55/55 GREEN; `planning` + `server/heart`
27/27 GREEN. `probe-intent-drift` green, which is what proves the three copies of the closed intent
set moved in lockstep. `node --check` exit 0 on every touched file. Not deployed — worktree branch
`ignite/core-redesign`.

## ATTENTION
1. THE DAEMON MUST NEVER TRUST THE BRIDGE'S `kind=approval`. That flag lives in the calling process's own map, so an editor who "simplifies" the executor by accepting a `kind` field in the payload deletes the entire guard: anything holding a bridge token could then name any thread and start an execution goal. The proof is the `authorized_reply_at` stamp on the daemon's OWN ask row, and nothing else is proof.
2. A SUPERVISED-MATERIALIZE FAILURE IS DATA, A BINDING REFUSAL IS A TYPED ERROR, AND THE TWO MUST NOT BE MERGED. The record already exists on disk and the owner has to read it in the thread; a typed error would lose it, and data-for-everything would let a refused caller read as "it tried".
3. `materialize` IS NOT AN INJECTABLE PORT ANY MORE, and re-opening that seam to make a test easier re-creates the one lie this surface cannot tell. If a probe needs to count D12, count the `start-execution` forward, as `probe-chat-approval` now does.
4. THE APPROVE-PACKAGE IS A CONVENTION WITH NO WRITER YET. `planning/approve-package.json` on the planning goal is where the birth reads its plan; a seat that starts producing one must not also start passing `planning_goal` or `goals_root`, because a disagreement with the daemon's own derivation is REFUSED (deliberately — that is how a package copied from another goal is caught).
5. THE PAUSE-WORD INTENT WAS DECLINED, NOT FORGOTTEN. The same 2026-08-24 ruling keeps pause store-side until the execution-lane reconcile gate converges onto the goal-state row. Minting one here to "finish the wiring" would take an owner decision inside an implementation seat.
- The daemon must never trust the bridge's kind=approval — the proof is the authorized_reply_at stamp on the daemon's own ask row
