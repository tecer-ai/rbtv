# Exposure method

The way a component makes instructions or an agent definition available through a harness:

- [Skill](skill.md): chosen by an agent.
- [Rule](rule.md): always presented to an agent.
- [Command](command.md): invoked by a human.
- [Harness-native sub-agent](agent.md#harness-native-sub-agent): a file in a harness's own sub-agent format, shipped in `sub-agents/` and called through that harness's own tool.
- [Hook](hook.md): a command the harness runs when an event happens.
- [MCP server](mcp-server.md): a program that offers the agent extra actions.

An rbtv agent shipped in a component's `agents/<name>/` folder is not an exposure method of the receiving harness. The [`rbtv` command](rbtv-command.md) places it in `.rbtv/agents/` and manages it there as an agent.

Hooks and MCP servers are not cognitive units; the `rbtv` command translates each into the harness's own settings.

Instructions that reach an agent because it works in a folder are [folder instructions](folder-instructions.md), not an exposure method. The folder a skill, rule, command, harness-native sub-agent, hook, or MCP server sits in (`skills/`, `rules/`, `commands/`, `sub-agents/`, `hooks/`, or `mcp-servers/`) decides its exposure method. Executable [tools](tool.md), kept in `capabilities/tools/`, are installed on [`PATH`](path.md); harness exposure can also instruct agents about them.
