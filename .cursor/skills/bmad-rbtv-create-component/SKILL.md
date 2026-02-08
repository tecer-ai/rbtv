---
name: create-component
description: RBTV BMAD Builder - create components in BMAD architecture. Use when creating new BMAD components, building agents, workflows, or tasks.
---

# Create Component Skill

**Purpose:** Load and execute the BMAD component builder agent.

**When to use:**
- Creating new BMAD components
- Building agents, workflows, or tasks
- Extending BMAD architecture
- User asks to create or build a component

---

## Activation

<agent-activation CRITICAL="TRUE">
1. LOAD the FULL agent file from agents/god.md
2. READ its entire contents
3. FOLLOW every step in the <activation> section precisely
4. After activation, process the user's request using the agent's menu handlers
</agent-activation>

> **ADMIN MODE:** Before proceeding, load and read `.cursor/rules/admin-rbtv-bmad-mirror.mdc` for path resolution and config values. Key: `.cursor/` and `tasks/` are at workspace root.
