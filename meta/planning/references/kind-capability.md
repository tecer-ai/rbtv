---
description: Decide when a reusable component capability needs its own instructions
tags: [planning]
---

# Capability — reusable means

A capability is an ability several consumers can invoke. Reuse an existing tool first. If its `-h` already teaches the operation, register the tool and route to it; write a capability guide only for decision rules or context the tool cannot explain.

An agent's specific settings MUST live in its home `settings.json`, referenced by its
`AGENTS.md` and `CLAUDE.md`. Reusable abilities MUST live in rbtv skills; NEVER put an
agent-specific value in their source. When reusing a capability in a new home, rewrite it in
that home's vocabulary and layout; NEVER wire old documents to new ones.

For the skill and CLI route, use `exposure.md`. Then run `component-lint` and reinstall its
loader if it has one.
