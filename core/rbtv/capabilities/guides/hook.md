# Building a hook

A [hook](../glossary/hook.md) is a command a harness runs when an event happens.

## Purpose

It makes something happen at a fixed moment, such as a check before a tool runs, without an agent having to remember it. Without it, that step depends on the agent's attention. Which kind of unit to build is in [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>).

## What good looks like

- The description alone tells a reviewer when the hook runs and what it does ([Progressive disclosure](../principles/progressive-disclosure.md)).
- The command is exact and repeatable, such as a [tool](../glossary/tool.md) on `PATH`, not a request to the model ([Deterministic first](../principles/deterministic-first.md)).
- No instruction to an agent is written as a hook; that is a [rule](../glossary/rule.md) or a [skill](../glossary/skill.md).

## Making it good

Name the event and, where it takes one, the tools the hook applies to. Point the command at a tool that does the work, and give it a timeout when it could hang.
