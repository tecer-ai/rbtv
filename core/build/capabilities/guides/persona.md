# Building a persona

A [persona](../glossary/persona.md) is who the agent is: the standpoint inside the [role](role.md) that shapes the choices the [procedure](procedure.md) and the task's [done contract](done-contract.md) leave open.

## Purpose

It fixes those open choices — when to stop, how broadly to explore, how to weigh risk, how to break a tie — so they come out under this standpoint; without it, those choices have no standpoint and vary. Write one only when a different standpoint would change them; a mostly mechanical agent gets a thin persona or none, and when no judgment is left open, do not write one. Where that work belongs instead is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- The persona names one standpoint in two sentences or fewer.
- Removing it would change the agent's choice on at least one open judgment: stopping, breadth, risk, or a tie. If none changes, delete it ([Keep it simple](../principles/kiss.md)).
- No line restates a done-contract condition or a procedure step ([Single source of truth](../principles/single-source-of-truth.md)).
- Two agents whose personas lead to the same choices on every open judgment are one agent ([Micro agency](../principles/micro-agency.md)).

## Making it good

Write one or two sentences naming the standpoint, such as "a skeptical reviewer who assumes the change is broken until shown otherwise", and check each against the open choices it must shape.

## Traps

- A theatrical costume or voice, added so two agents differ while their decisions match.
- The persona judges the result, restating what finished means; the done contract owns that.
- "Be thorough" or "think hard": a trait that names no standpoint and changes no choice.
- The standpoint is rewritten as trigger-and-default pairs, which duplicates the procedure.
