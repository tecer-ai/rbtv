# `<component>.json`

The [folder artifact](folder-artifact.md) containing each component's structured record, named after the component: `<module>/<component>/<component>.json`. The `rbtv` CLI reads it for:

- The component's description.
- The outside software it requires.

It does not record exposure methods: the folder a skill, rule, command, agent, hook, or MCP server sits in decides how it is exposed.
