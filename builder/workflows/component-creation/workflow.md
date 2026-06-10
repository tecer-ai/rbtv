---
name: Component Creation
description: Unified component builder for RBTV and vault/non-RBTV systems. Acts as critical design partner — challenges assumptions and forces design decisions before building.
nextStep: ./step-01-analyze.md
---

# Component Creation

## Purpose

Unified builder replacing both the RBTV create-component workflow and any vault-specific component builder. Handles two targets:

- **RBTV components** — standard placement in the RBTV source repo, bootstrapped to all instances via re-install
- **Non-RBTV / vault components** — placement governed by workspace conventions read from the target CLAUDE.md

## Modes

| Mode | Trigger | Entry |
|------|---------|-------|
| Create / Edit / Understand | Building, modifying, or understanding a component | Activation Sequence below |
| Review (token efficiency) | The owner asks to review, diagnose, audit, or trim a component's token cost | Load `{rbtv_path}/builder/workflows/component-review/workflow.md` and follow it — skip the Activation Sequence |

## Critical Rules

- 🛑 NEVER generate content without user input
- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 🎯 ALWAYS follow the exact instructions in the step file
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER create mental todo lists from future steps

## Activation Sequence

1. Load `{rbtv_path}/builder/workflows/component-creation/data/component-patterns.md` — internalize naming standards, size limits, and compliance rules
2. Load `{rbtv_path}/builder/workflows/component-creation/data/rbtv-architecture.md` — component decision guide and design principles
3. Proceed to Step 01
