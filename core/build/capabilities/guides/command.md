# Building a command

A [command](../glossary/command.md) is a [cognitive unit](../glossary/cognitive-unit.md) a human invokes; the agent reads its instructions only then.

## Purpose

It lets a human choose the moment an action runs, and names what that action needs. Without it, the human has no way to invoke the action, or the agent chooses the moment. Follow the [entry point and capabilities shape](capability.md) and the choice in [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>).

## What good looks like

- The name is not one a [harness](../glossary/harness.md) already uses for its own command.
- Name and description alone: the first sentence makes a human pick this command for one matching action. The rest, not the body, names one similar action this command must not take. The first sentence does not carry the refusal ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Every required input is named. A missing input has a stated result. The body asks no question the invocation could have answered ([Agent parity](../principles/agent-parity.md)).
- One invocation, one judgeable result ([Micro agency](../principles/micro-agency.md)).
- If an agent must perform the same action, the method is not only in this command ([Single source of truth](../principles/single-source-of-truth.md), [Agent parity](../principles/agent-parity.md)).
- Every exact-answer step names a [tool](../glossary/tool.md) ([Deterministic first](../principles/deterministic-first.md)).
- Removing any sentence loses a requirement ([Keep it simple](../principles/kiss.md)).

## Making it good

Write the description a human sees before invoking, and name each input at invocation, not mid-run. Write the body as that one action, and order steps that change the same file ([Micro agency](../principles/micro-agency.md)).

## Traps

- The description overlaps another command, so the human invokes the wrong one.
