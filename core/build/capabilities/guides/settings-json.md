# Building `settings.json`

[`settings.json`](../glossary/settings-json.md) holds the values one installed agent's job needs.

## Purpose

It gives the agent values its tasks use but its prompt should not carry, such as the sources it works from. Without it, those values end up written into the prompt, where each change means editing the agent file. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- Each value is one some task of this agent uses; a value with no use today is not added ([Keep it simple](../principles/kiss.md)).
- No value repeats something the agent file, [`launch.json`](launch-json.md), or another file already holds ([Single source of truth](../principles/single-source-of-truth.md)).
- No secret is written in it: it names the environment variable that holds one.

## Making it good

Add a value when a task of this agent needs it and it changes independently of the prompt. Name each key for what it holds.
