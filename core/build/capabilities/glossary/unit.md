# Unit

A unit is one thing that the [`rbtv` command](rbtv-command.md) can add to an installation or to an agent: a skill, rule, command, agent, sub-agent, hook, MCP server, tool, or folder instructions. Its full id is `module/component#name`, and a record saves that full id. A [cognitive unit](cognitive-unit.md) is the kind of unit an agent reads. Hooks, MCP servers and tools are units that are not cognitive units. A [pack](pack.md) is a named list of units, turned on only with `--pack`.
