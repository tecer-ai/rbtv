# Building `ignite/config.json`

[`ignite/config.json`](../glossary/ignite-config.md) is Ignite's configuration on the machine where the agents run.

## Purpose

It tells Ignite which Slack workspace to use and which agent answers each channel. Without it, a message has no agent to wake. It is not hand-written.

## What good looks like

- Each Slack channel connects to one agent, on one machine. The file is never shared with another machine, so no agent answers twice.
- No token is written in the file: it names the environment variable that holds each one.
- Every value in it is one the owner chose; no field sets a default for an agent's harness, model, or effort ([Single source of truth](../principles/single-source-of-truth.md)).
