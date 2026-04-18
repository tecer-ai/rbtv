---
name: Component Creation
description: Unified component builder for RBTV and vault/non-RBTV systems. Acts as critical design partner — challenges assumptions and forces design decisions before building.
nextStep: workflows/component-creation/step-01-analyze.md
---

# Component Creation

## Purpose

Unified builder replacing both the RBTV create-component workflow and any vault-specific component builder. Handles two targets:

- **RBTV components** — standard placement in the RBTV source repo, bootstrapped to all instances via re-install
- **Non-RBTV / vault components** — placement governed by workspace conventions read from the target CLAUDE.md

## Activation Sequence

1. Load `{rbtv_path}/workflows/component-creation/data/component-patterns.md` — internalize naming standards, size limits, and compliance rules
2. Load `{rbtv_path}/workflows/component-creation/data/rbtv-architecture.md` — component decision guide and design principles
3. Proceed to Step 01
