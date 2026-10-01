# Building a capability

A [capability](../glossary/capability.md) is reusable instructions, knowledge, a template, or a [tool](tool.md) in a component.

## Purpose

It holds the substance behind a skill or command. The entry point holds the procedure and routes in plain prose to the component's capabilities index, which says when to open each page. Several entry points can route to the same capabilities. The choice of unit is [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- Each page serves the component's purpose; use only the kinds its domain needs: a reader page for what the domain is, a glossary for exact terms, guides for how to do each thing, templates and schemas for output shapes, and principles for what good means. [core/build's capabilities](../capabilities.md) show this shape. No folder is empty, and no page is a placeholder.
- One purpose. An unrelated second method fails. ([Micro agency](../principles/micro-agency.md))
- A step with an exact answer names the [tool](../glossary/tool.md) that runs it. ([Deterministic first](../principles/deterministic-first.md))
- Read with only the passed inputs, a builder can follow it. It names no file the pointer did not pass.
- No other file restates its content. ([Single source of truth](../principles/single-source-of-truth.md))
- Every pointer names the moment to open it. A bare link fails. ([Progressive disclosure](../principles/progressive-disclosure.md))
- No channel id, absolute path, account, host, or credential is typed into it: these belong to one installation and are read at run time from its configuration, settings, or task ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Pass in every fact the text uses; do not assume the caller's other files or an earlier task.
