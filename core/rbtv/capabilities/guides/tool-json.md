# Building a `<tool>.json`

A [`<tool>.json`](../glossary/tool-json.md) is the [folder artifact](../glossary/folder-artifact.md) that records one [tool](../glossary/tool.md).

## Purpose

The [rbtv](../glossary/rbtv-cli.md) reads it to tell agents the tool exists. Without it, agents are not told the tool exists. The choice of unit is [Choosing what to build](../choosing-what-to-build.md).

## What good looks like

- From `description` alone, a reviewer picks this tool over a neighbour or correctly skips it. "Helps with files" fails. ([Progressive disclosure](../principles/progressive-disclosure.md))
- `description` has no steps and no when-to-run sentence. That sentence lives in a [skill](../glossary/skill.md), [rule](../glossary/rule.md), or [command](../glossary/command.md). ([Single source of truth](../principles/single-source-of-truth.md))

## Making it good

Write `description` as one line a reviewer uses to pick this tool or skip it, and nothing else.
