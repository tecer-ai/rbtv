# Building `launch.json`

[`launch.json`](../glossary/launch-json.md) holds an installed agent's live harness, model, and effort.

## Purpose

Everything that runs the agent from its folder reads the same values here. Without it, each program would keep its own copy of the agent's model and they would drift apart. It is not hand-written.

## What good looks like

- The agent's harness, model, and effort have one home, this file; no other file of the agent repeats them ([Single source of truth](../principles/single-source-of-truth.md)).
- Whoever installs the agent chose each value; none came from a default that nobody chose.
