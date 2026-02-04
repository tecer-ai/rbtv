# Evaluate Inject-Rules (Inject-Standards–Style)

**Status:** To evaluate  
**Category:** Command / Skill  
**Purpose:** Decide whether to add a capability that injects relevant rules (and optionally skills) into context by scenario, with optional auto-suggest or explicit paths

## Overview

[agent-os inject-standards](https://github.com/buildermethods/agent-os/blob/main/commands/agent-os/inject-standards.md) supports two modes: (1) auto-suggest — analyze context and suggest relevant standards; (2) explicit — inject specified standards by path. It detects scenario (Conversation, Creating a Skill, Shaping/Planning) and formats output accordingly (full content vs file references). It uses an index of standards and can surface related skills.

**To evaluate:** Whether Robotville should implement something similar, mapping "standards" to **rules** (and optionally skills), using [system/map/rules.md](system/map/rules.md) and [system/map/skills.md](system/map/skills.md) as the index, and aligning scenarios with Robotville (conversation, skill authoring, plan creation/execution).

## Evaluation Questions

- **Fit:** Do rules (and skills) need on-demand injection, or is current always-apply + @-mention sufficient?
- **Index:** Is rules.md/skills.md sufficient as the "index" for matching, or is a separate index (e.g. YAML) required?
- **Scenario detection:** How to reliably detect "creating a skill" vs "plan mode" vs "conversation" in Cursor?
- **Capability type:** Command (legacy), skill (user-triggered), or integrated into an existing flow (e.g. plan workflow)?
- **Scope:** Rules only, or rules + skills? References only, or optional inline content?

## Reference

- [inject-standards.md](https://github.com/buildermethods/agent-os/blob/main/commands/agent-os/inject-standards.md) — Source pattern (agent-os)
