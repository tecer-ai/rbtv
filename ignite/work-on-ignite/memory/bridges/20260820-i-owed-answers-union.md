# 20260820-i-owed-answers-union — owed-answers-union

kind: issue
component: bridges
date: 2026-08-20
commit: 61fc759f,17a28453,0a3a14d2,607014d4
deployed: yes
pin: NONE (not in rbtv probe-suite scope)
components: team-kit
seeded: true

## Seen
`owed-answers` missed halting escalations, then needed a durable owner-ask ferry with queueing for goal-master.

D30: `owed-answers` asked only `coord.open_asks(..., to=owner)`, whose filter is `type == "ask"`. An escalation — the message class that HALTS a goal on the owner — is structurally invisible to it. Measured: the digest printed `no owed answers` while escalation #523 halted `meet-transcript-summarizer`, and it repeated on #555. D57/D75/D89 (owner, 2026-08-22 ~15:58Z, seat 09 Q1–Q4): `goal-master` had no durable record of an unanswered owner ask to re-inject on its next daemon-fired sitting, and the first build of that record (`createAsk`) overwrote `store[seat]` wholesale — a second owner message arriving before the first was answered silently destroyed the first.

## Missed
none recorded in sources.

## Held
Union `open_escalations` into the owed-answers digest (never widen `coord.open_asks`); build a bridge-owned owner-asks ledger that queues instead of overwrites.

owed-answers union (61fc759f): the union lives in `owed-answers.py`, not in `coord.py` — ruling `p-owed-answers-locus` forbids widening `coord.open_asks`'s predicate, since four check-out hold gates read it and a widened one self-deadlocks the escalating seat at its own hold. `collect()` unions asks + `open_escalations` filtered to the owner, each row tagged `kind`; halts sort ABOVE asks so the CAP-5 truncation can never drop the row that means the run is stopped. `render()` prefixes `⛔ RUN HALTED · ` inside the existing `- ` item line so every consumer's format assertion still holds. `selfcheck()` adds four asserts on a throwaway fixture. 17a28453 then declares `owed-answers` a first-party tool in `exposure.csv` (it previously reached a shell only via a hand-made symlink — ten files, including the channel-master's own standing prompt, name the command and forbid the vault-search fallback).

Owner-ask ferry (0a3a14d2, D57/D75/D89): a durable record, answered mark, owed-answers surface, and re-inject firing point for an unanswered owner ask to `goal-master`. The record is a bridge-owned JSON file at `{goalDir}/coordination/owner-asks.json` — single writer (`ask-store.js`), read-only consumers (`coord.py`, `owed-answers.py`); `coord.py`'s `unanswered_ask_block()` folds into `boot_prompt()` scoped to `agent == "goal-master"` only, and never mints a sitting (D24 stands) — it only reads when a sitting is already being composed for other reasons. "Answered" = only a conformant reply (`verdict.ok === true`); system stand-in texts do NOT count (D89 Q1); no TTL — an ask stays re-injectable forever until answered (D89 Q2).

Queueing (607014d4, D89 Q4): `ask-store.js`'s `store[seat]` widens from one bare entry to a list, oldest-first; a pre-D89 legacy single-object file migrates on read. Every reader follows: `coord.py`'s `unanswered_ask_block` renders ALL open asks oldest-first, numbered; `owed-answers.py`'s `collect_unanswered_asks` emits one row per open ask with its own id. `markAnswered` settles an explicit `askId` if given, else the oldest open ask. Red-first: a two-asks-before-any-answer fixture against pre-D89 code lost the first ask silently (JS overwrite) and returned zero rows from `owed-answers.py` (list shape unrecognized) — confirmed on both, then green, plus a permanent queue+legacy arm added to `owed-answers.py`'s own selfcheck.

## commit
61fc759f,17a28453,0a3a14d2,607014d4

## files
ignite/team-kit/owed-answers.py (collect, render, selfcheck); ignite/exposure.csv; ignite/bridges/chat/ask-store.js (createAsk/markAnswered/getAsk); ignite/bridges/chat/chat-bridge.js; ignite/bridges/chat/forward-path.js; ignite/team-kit/coord.py (unanswered_ask_block, boot_prompt)

## deployed
yes — rbtv HEAD ac1c08d8, deployed 2026-08-21 18:14:37Z (61fc759f); later ferry commits (0a3a14d2, 607014d4, 17a28453) land 2026-08-22, effective on commit — coord.py/owed-answers.py are read live per invocation (D6 exception).

## pin
NONE (not in rbtv probe-suite scope) — team-kit/probes/probe-staff-wiring.py pins the related D24/CONVERSATIONAL_CHAIRS predicate, not this union.

## ATTENTION
- `owed-answers.py`'s union must stay a CALL into `coord.open_asks`, never a widen of that predicate's filter — four check-out hold gates read `coord.open_asks` directly and a widened filter self-deadlocks the escalating seat at its own hold (ruling `p-owed-answers-locus`).
- `packages()` in owed-answers.py double-counts `_channel-master` (seeded AND carries a `goals.csv` row) — pre-existing at HEAD, not fixed by this batch; it broke `--selfcheck` outright and would double-count halts if untriaged.
- `ask-store.js`'s list-of-asks shape has a legacy single-object migration path — any new reader of `owner-asks.json` must handle both shapes or silently drop pre-D89 files.
- No caller passes an explicit `askId` yet, so `markAnswered` always settles the oldest open ask — a future per-ask-thread caller must pass `askId` explicitly or it will settle the wrong ask.
