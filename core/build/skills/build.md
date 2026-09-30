---
name: build
description: "Use before creating, changing, or reviewing any rbtv unit — a skill, rule, command, agent, hook, MCP server, tool, component, module, folder instructions file, or one of their records — so the result is what the installer recognises and follows the principles. Situations: 'create a skill', 'add a rule', 'write an agent file', 'new component', 'review this skill', or any edit inside an rbtv component folder or the mirror. Not for using an existing unit without changing it."
---

# Build

The building documentation is this component's capabilities, in `../capabilities/` next to this file. This skill only routes you there; it never restates it.

1. Open `../capabilities/capabilities.md` and follow it: it names which page to open at each moment — `rbtv.md` to understand rbtv, the glossary for exact meanings, the guide for the unit you build, the templates and schemas for its shape.
2. Before writing a new unit, find what exists with `rbtv install list`, `search`, and `show`; build only what nothing listed covers.
3. Every design choice meets the principles in `../capabilities/principles/`.
4. The unit is done when `rbtv install add` or `rbtv install update` accepts it: the installer checks its frontmatter or record against its schema and refuses a mismatch.
5. When the change is to this documentation itself, follow `../CLAUDE.md`.
