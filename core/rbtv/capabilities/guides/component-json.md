# Building a `<component>.json`

[`<component>.json`](../glossary/component-json.md) is the [folder artifact](<../_under-evaluation/guides/folder artifacts/glossary/folder-artifact.md>) that holds a component's description and the outside software it requires.

## Purpose

rbtv reads it to learn what the component is for and which outside programs it needs. Without it, rbtv reports the component folder as an error. Which folder artifact to add is in [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>).

## What good looks like

- From the description alone, a reviewer can accept or reject the component as relevant without opening the folder ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Outside software is a list of program names, not prose or objects ([Deterministic first](../principles/deterministic-first.md)).
- The record does not list how a skill, rule, command, agent, hook, or MCP server is exposed. The folder each one sits in is that record ([Single source of truth](../principles/single-source-of-truth.md)).
- The file name matches the component folder name exactly ([Terminology is king](../principles/terminology-is-king.md)).

## Making it good

Write the description as the sentence that decides relevance. Repeating the folder name fails that test. Name each outside program the component requires and does not include, and name none when there are none.
