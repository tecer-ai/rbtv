# Building a scope

A [scope](../glossary/scope.md) is the boundary of one [task](../glossary/task.md): what to examine, and what may change.

## Purpose

It keeps this task's boundary closed, so a reviewer can classify any action as in or out. Without it, related work is treated as in, and no action can be classified. The choice of unit is [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- A reviewer who has not seen the conversation classifies any candidate action as in or out. "Related files" fails.
- Examine and may-change are separate closed lists of named files, folders, or records.
- No sentence is true of every task of this agent. Standing remit stays in the [role](../glossary/role.md); standing limits stay in [constraints](../glossary/constraints.md). ([Single source of truth](../principles/single-source-of-truth.md))
- It bounds one purpose. Two results that can be judged apart are two tasks. ([Micro agency](../principles/micro-agency.md))
- It states no completion check. That check is the [done contract](done-contract.md). ([Single source of truth](../principles/single-source-of-truth.md))
- A sentence whose removal still leaves every action classifiable is absent. ([Keep it simple](../principles/kiss.md))

## Making it good

Name what to examine. Name what may change. Keep the two lists separate, and close both: only those names are in, and only the may-change names may change.

## Traps

- "Investigate this", with no names.
- "Add tests for foo.py" — a file name with no closed examine list and no closed may-change list.
