# Building a tool

A [tool](../glossary/tool.md) is an executable program: a [capability](capability.md), not a [cognitive unit](../glossary/cognitive-unit.md).

## Purpose

It returns an exact answer a caller can check, the same way every time. Without it, the agent estimates a count, date, or comparison, and a wrong answer can look right. The choice of unit is [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- Status 0 means the exact answer succeeded; any other status means it failed. A caller can tell which without reading prose. ([Deterministic first](../principles/deterministic-first.md))
- It asks no question. On failure it names the expected value and the received value. The answer is structured. Diagnostics are separate from the answer.
- Run on one input with a known answer and on one invalid input, the answer and the failure behavior match the documented invocation.
- Every record it reads or writes has fixed fields. ([Deterministic first](../principles/deterministic-first.md))
- At least one [skill](../glossary/skill.md), [rule](../glossary/rule.md), or [command](../glossary/command.md) names the tool and the moment to use it. A mention that does not name the moment fails. ([Deterministic first](../principles/deterministic-first.md))
- No second program performs the same operation. ([Single source of truth](../principles/single-source-of-truth.md))
- A human control for the same operation calls this tool, and an agent runs that same tool. ([Agent parity](../principles/agent-parity.md))
- Each option supports a choice a current caller needs; a value that never varies stays internal. ([Keep it simple](../principles/kiss.md))

## Making it good

Write one invocation a caller can run twice: the required inputs, the returned fields, and the failure behavior.

## Traps

- The step still tells the agent to count, compare, or check a date.
