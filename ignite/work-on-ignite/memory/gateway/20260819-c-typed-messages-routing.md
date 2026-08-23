# 20260819-c-typed-messages-routing — Typed messages routing

kind: creation
component: gateway
date: 2026-08-19
commit: af7c0f7b
deployed: yes
pin: server/heart/probes/probe-message-type-vocabulary.js; probe-migration-message-types.js
components: team-kit,server,bridges
seeded: true

## What it is
Typed messages + a system routing table; agents never pick recipients.

`gateway/parse.js` gains typed message parsing; `heart-store.js`/`migrations.js`/`schema.sql` add a system routing table; `coord.py` (346 new lines) and `bridges/chat/forward-path.js` are updated so agents no longer choose message recipients directly — routing is table-driven and typed.

## Why
D2: routing depended on agents picking recipients ad hoc.

`fix-inventory.csv` D2 — message routing previously depended on agents picking recipients ad hoc, flagged as a "gates never told to their subjects" structural cause (system-problems digest §4, one of D61's three named structural causes of edge cases).

## How to use & where wired
coord.py's send path looks up the typed routing table instead of a free-text recipient.

`coord.py`'s message-send path now looks up the typed routing table (`heart-store.js`) instead of taking a free-text recipient; `bridges/chat/forward-path.js` and `gateway/parse.js` consume the same typed schema.

## commit
af7c0f7b

## deployed
yes

## pin
server/heart/probes/probe-message-type-vocabulary.js; probe-migration-message-types.js (both scheduled)

## ATTENTION
- Foundational routing-table change touching team-kit, server/heart, and bridges/chat at once — a later change to the message-type vocabulary must update the SAME schema.sql/migrations.js pair or the two scheduled probes will catch a drift.
- "Agents never choose recipients" is the design invariant — any new message-producing path that lets an agent free-type a recipient string reopens the exact problem D2 closed.
- message-type vocabulary changes must update schema.sql/migrations.js together
- agents never choose recipients is the design invariant here
