---
description: Decide when a reusable component capability needs its own instructions
tags: [planning]
---

# Capability — reusable means

A capability is an ability several consumers can invoke. Reuse an existing tool first. If its `-h` already teaches the operation, register the tool and route to it; write a capability guide only for decision rules or context the tool cannot explain.

Keep instance credentials and paths in runtime configuration. Register a first-party CLI in the owning component’s `exposure.csv`, then use `component-lint` and reinstall its loader if it has one.
