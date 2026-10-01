# Capability

Reusable content kept under a component's `capabilities/` folder: instructions, knowledge, templates, or [tools](tool.md). Capabilities usually sit under one skill or command that routes to them. A capability has no exposure method of its own; a skill or command points to it, or, when an agent's whole work is the domain, its rule or prompt routes to it. Updating one capability keeps every unit that routes to it current. Tools sit at `capabilities/tools/<tool>/`, where the installer finds them.
