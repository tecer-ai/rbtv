---
name: albert-memory-operations
description: "CONTAINS: when Albert stays quiet, where he reports failures, and what the Friday summary includes PURPOSE: autonomous memory runs stay quiet unless the owner must act, and applied changes are reported once ALWAYS LOAD WHEN: Albert is connected to Ignite and may run or report memory work DO NOT LOAD WHEN: the agent is not Albert, or Albert is not connected to Ignite"
---

When an autonomous memory run needs no action and no owner attention, stay quiet. Do not send a routine success acknowledgement. Keep an ordinary successful memory change for the Friday report.

When a check or publication blocks, report it in this agent's own channel. Never report it in the owner's direct messages. Name what failed, what remains pending, and the action needed. Do not announce the same unchanged problem again.

On Friday at 08:45 America/Sao_Paulo, report the changes actually applied since the previous report. Use the retained change records from `albert report`. Include each item's stable reference so the owner can request a reversal. List pending global-rule approvals apart from applied changes, and list unresolved conflicts apart from both. Never describe a proposal as applied. A proposal is applied only after `albert apply` succeeds.

When the owner asks for a reversal, pass the item reference to `albert reverse`. Confirm completion only after that command succeeds.

When a behavior rule would apply to all agents, leave it pending until the owner approves it, unless his correction explicitly made it global. Bring that decision in this channel. An ordinary pending item can accompany the Friday report. A blocking problem is reported when it occurs.

When the owner speaks to you directly, answer his request. The quiet-run rule applies to autonomous runs, not to a direct request.

The proposal structure is taught by `albert apply -h`, and only there. Read that help before writing a proposal. Do not restate the structure from this rule.
