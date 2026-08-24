# 20260824-c-fix-stale-rule-disposition-ref — Fix stale rule-disposition references cross-component

kind: change
component: engine
date: 2026-08-24
commit: a6913c6f
deployed: no
pin: NONE
components: bridges,capabilities,meta-leader,team-kit

## Motivation
Follow-up to `team-kit/20260824-c-delete-rule-disposition-ruled.md` (commit `7b978663`), which
deleted `cmd_rule_disposition`/`RULED_FLIP_FROM*` from `coord.py` under [T2-R12, T1-R9]. That
agent's grep floor was scoped to `ignite/team-kit/`; it correctly flagged (but did not fix) live
cross-component references outside its remit: `ignite/engine/reconcile.js` was still generating a
leader-wake message instructing the leader to run the deleted verb, with a selftest asserting that
text was present, and five docs (`meta/leader/prompts/{leader,consultant}.md`,
`meta/leader/tasks/serve-staff-mail.md`, `ignite/bridges/chat/README.md`,
`ignite/capabilities/attached-execution/attached-execution.md`) told operators/readers
"`rule-disposition ... --go` is the ONE sanctioned act." `reconcile.js` is named as a likely home
for this seat's D19 batch, so this is in-remit, not a hand-off.

## Design
No replacement instrument was invented — [T2-R5] forbids new daemon remedy verbs, and the owner-ask
door (T1-R9's actual replacement) is out of scope here (impl-slack). Every site now states plainly
that the act is gone and the door is not wired yet, rather than presenting a dead command as live.
`reconcile.js`'s `nontermPayload` still lists the two SURVIVING one-act doors (`launch --only <seat>
--rerun` and `--declare-only`) unchanged — only the two `rule-disposition` command lines and the
now-nonexistent `--hold` invocation were removed.

## How it works
`reconcile.js#nontermPayload`: replaced the two indented `rule-disposition ...` command lines (a
`done`/clear pair and a separate `--hold` line) with one paragraph stating no runtime ruling
instrument exists and naming the ruling [T2-R12, T1-R9]. A nearby comment (~line 299, inside the
D42 hold-anchor-skip block) that attributed the anchor's writer to `coord.py rule-disposition
--hold` now says that writer was deleted, while leaving the hold-anchor CELL/reader itself
untouched (explicitly out of scope — a separate store). `reconcile.selftest.js`'s payload-content
assertions dropped the two dead needles and gained an assertion that `rule-disposition` may still
be NAMED (to explain the gap) but never appears as an indented, runnable command
(`/^ {4}rule-disposition\b/m` must not match). `live-sessions.js`'s incident comment (2026-08-18)
now describes the OPEN-row hazard generically instead of naming the dead verb as the blocked
mechanism. `attached-execution.md` and `bridges/chat/README.md` both described the same "leader
rules the row" escape hatch for an unanswered owner-ask hold — both now say plainly that no escape
currently exists. The three `meta/leader` prompt/task docs all carried near-identical "ONE
sanctioned act" language — each rewritten to state the act is deleted, without inventing what
replaces it.

## Consequences
Nothing deleted whole in this follow-up — every touched file keeps its surrounding structure; only
the stale command references changed. `meta/leader/prompts/consultant.md` was touched minimally
(one line) — the whole `consultant` role/chair is a LATER subsystem's deletion target [T2-R17,
D-7-ruling]; this fix does not anticipate or block that later, larger rewrite.

## Verification
`node --check` clean on all touched `.js`. `node ignite/engine/reconcile.selftest.js` → full PASS
(`reconcile.selftest OK`), including the rewritten payload-content assertions. Grep floor: `git grep
-n -F 'rule-disposition' -- ignite meta | grep -v work-on-ignite/memory` — every remaining hit
(mostly `coord.py`, already fixed by the parent entry) is either inside `coord.py`'s own historical/
explanatory comments (parent entry's scope) or, in the files this entry touched, explanatory prose
naming the deleted verb to explain the gap — never a live binding or a runnable-command line.
Committed `a6913c6f` (worktree `5-workbench/rbtv-redesign`, branch `ignite/core-redesign`).

## ATTENTION
1. **`meta/leader/prompts/consultant.md` still describes a `consultant` chair in full** — this
   entry only fixed its one `rule-disposition` line. The chair itself is [T2-R17, D-7-ruling]'s
   deletion target (a later subsystem in this same D19 batch); do not read this entry as having
   touched that.
2. **No replacement ruling instrument exists anywhere in the tree now** — an unfinished session-log
   row (`exited`/empty/`unverified`/`incomplete`) has NO way to be ruled done or cleared by the
   leader until T1-R9's live-ask door is built (a separate, later seat's work, per this seat's own
   out-of-scope list). This is a real, currently-live operational gap, not a documentation nit.
3. **The hold-anchor CELL and its skip-logic in `reconcile.js` are unchanged** — only the comment
   explaining WHO used to write that cell was corrected. Do not read this entry as having touched
   the hold-anchor store itself (explicitly out of scope, a separate impl-state-store concern).
- no replacement ruling instrument exists yet — real operational gap, not doc nit
- consultant.md still describes the full chair; only its rule-disposition line was fixed
