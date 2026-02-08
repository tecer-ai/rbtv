---
name: doc
description: RBTV unified documentation generation (compound, handoff, product). Use when creating documentation, writing handoffs, or generating product docs.
---

# Doc Skill

**Purpose:** Load and execute the BMAD documentation agent.

**When to use:**
- Creating compound documentation
- Writing handoff documents
- Generating product documentation
- User asks for documentation or docs

---

## Activation

<agent-activation CRITICAL="TRUE">
1. LOAD the FULL agent file from agents/ana.md
2. READ its entire contents
3. FOLLOW every step in the <activation> section precisely
4. After activation, process the user's request using the agent's menu handlers
</agent-activation>

> **ADMIN MODE:** Before proceeding, load and read `.cursor/rules/admin-rbtv-bmad-mirror.mdc` for path resolution and config values. Key: `.cursor/` and `tasks/` are at workspace root.
