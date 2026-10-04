---
name: build
description: "Use before creating, changing, or reviewing any rbtv unit — a skill, rule, command, agent, hook, MCP server, tool, component, module, folder instructions file, or one of their records — so the result is what the installer recognises and follows the principles. Situations: 'create a skill', 'add a rule', 'write an agent file', 'new component', 'review this skill', 'turn this conversation into a skill or command', 'save what we just did as a skill', or any edit inside an rbtv component folder or the mirror. Not for using an existing unit without changing it."
---

# Build

The building documentation is this component's capabilities, in `../capabilities/` next to this file. This skill only routes you there; it never restates it.

1. Open `../capabilities/capabilities.md` and follow it: it names which page to open at each moment — `rbtv.md` to understand rbtv, the glossary for exact meanings, the guide for the unit you build, the templates and schemas for its shape.
2. When the unit comes from a conversation that just happened, start with `../capabilities/guides/building-from-a-conversation.md`.
3. Before writing a new unit, find what exists with `rbtv list`, `search`, and `show`; build only what nothing listed covers.
4. Every design choice meets the principles in `../capabilities/principles/`.
5. The unit is done when `rbtv add` or `rbtv update` accepts it — the rbtv command checks its frontmatter or record against its schema and refuses a mismatch — and its documentation is updated as `../capabilities/guides/documenting-a-change.md` says.
6. An rbtv agent (a folder holding `agent.md` and `agent.json`) is built by the agent guide, `../capabilities/guides/agent.md`, and then added with `rbtv agent add`.
7. When the change is to this documentation itself, follow `../CLAUDE.md`.
