# Capability

Reusable content kept under a component's `capabilities/` folder and shared by its skills, rules, commands, and agents: instructions, knowledge, templates, or [tools](tool.md). A capability has no exposure method of its own; a skill, rule, command, or agent points to it. Tools sit at `capabilities/tools/<tool>/`, where the installer finds them.
