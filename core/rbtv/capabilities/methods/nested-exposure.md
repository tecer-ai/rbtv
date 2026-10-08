# Nested exposure

Nested exposure places several capabilities under one exposure method. The agent encounters that entry point first and reads a capability only when its case applies.

Use it when capabilities share a purpose or the same working documents. It reduces the choices made before work starts without putting every method into the always-read body.

## Group or separate

Group capabilities when one purpose covers them without including a neighboring job, or when they operate on the same documents. Do not group them when the reader must distinguish their mutually exclusive situations before choosing either entry point.

For example, committing a change and reviewing a change need separate descriptions when the reader must know which of the two it is doing before it selects an entry point. Do not hide that distinction inside a shared skill.

Split a group when one description, rule-installation condition or folder boundary cannot cover it without matching unrelated work. The resulting entry points do not route to one another.

## Build the group

Choose the exposure method with [Choosing what to build](choosing-what-to-build.md). Write its body using [Entry point](../glossary/entry-point.md), its rows using [Routing table](../glossary/routing-table.md), and each target using [Capability](../glossary/capability.md).

| Method | What grouping requires |
|---|---|
| Skill | One description covers all supported capabilities. Do not also expose each capability as its own skill. |
| Command | One invocation supplies the input selecting the capability. Do not require a second command or menu. |
| Rule | Its table is present on every task where installed. Keep required standing guidance available; route task-specific methods instead of pasting them. |
| Folder instructions | The table is supplied with folder guidance. Keep only visit-wide information in the body and route case-specific work. |

Rows name capability files directly. They do not name skills, commands, rules, folder instructions or index-only pages. Agents and prompts are not exposure methods. Folder instructions retain their own placement and path rules.

## Changes and verification

Recheck grouping when adding a new exposed file. When converting a skill package or related commands, preserve the supported cases without creating one exposure method per supporting file.

Review every exposure method the reader would encounter, not only the new parent. Check for duplicate exposure of a nested capability. Test one task per capability: the agent must select the shared entry point and then the correct page. Include a neighboring task that should select neither.
