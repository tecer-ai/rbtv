# Exposure method

The way a component makes instructions or an agent definition available through a harness:

- [Skill](skill.md): chosen by an agent.
- [Rule](rule.md): always presented to an agent.
- [Command](command.md): invoked by a human.
- [Agent](agent.md): a named agent available for invocation, installed as its own agent folder and, where a harness has its own sub-agent definitions, translated into them.
- [Hook](hook.md): a command the harness runs when an event happens.
- [MCP server](mcp-server.md): a program that offers the agent extra actions.

Hooks and MCP servers are not cognitive units; the installer translates each into the harness's own settings.

Instructions that reach an agent because it works in a folder are [folder instructions](folder-instructions.md), not an exposure method. The folder a skill, rule, command, agent, hook, or MCP server sits in (`skills/`, `rules/`, `commands/`, `agents/`, `hooks/`, or `mcp-servers/`) decides its exposure method. Executable [tools](tool.md), kept in `capabilities/tools/`, are installed on [`PATH`](path.md); harness exposure can also instruct agents about them.
