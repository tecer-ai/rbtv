# Building a capability

A [capability](../glossary/capability.md) is reusable instructions, knowledge, a template, or a [tool](tool.md), shared by more than one [cognitive unit](../glossary/cognitive-unit.md).

## Purpose

It is the one home for text a second cognitive unit needs. Without it, that text stays inside one unit, or each unit keeps a copy. The choice of unit is [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- A second cognitive unit points to it, or the same change names that second user. A file only one cognitive unit needs is not a capability. ([Single source of truth](../principles/single-source-of-truth.md))
- One purpose. An unrelated second method fails. ([Micro agency](../principles/micro-agency.md))
- A step with an exact answer names the [tool](../glossary/tool.md) that runs it. ([Deterministic first](../principles/deterministic-first.md))
- Read with only the passed inputs, a builder can follow it. It names no file the pointer did not pass.
- No other file restates its content. ([Single source of truth](../principles/single-source-of-truth.md))
- Every pointer names the moment to open it. A bare link fails. ([Progressive disclosure](../principles/progressive-disclosure.md))
- No channel id, absolute path, account, host, or credential is typed into it: these belong to one installation and are read at run time from its configuration, settings, or task ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Pass in every fact the text uses; do not assume the caller's other files or an earlier task.
