# Component

A component is a folder grouping one subject's files inside a module: `<module>/<component>/`, with the record `<component>.json`. The record identifies the component; subfolders determine how its files are exposed.

Use [Choosing where to build](../choosing-where-to-build.md) to decide whether the work needs a component and whether it belongs in the repository or mirror. This entry describes the component once that placement is settled.

## Boundary and record

Name the folder with a lower-case noun and hyphens. Keep the record filename equal to the folder name. Use [component-json.schema.json](../templates/component-json.schema.json) for the description and external-dependency fields.

The description owns the subject boundary. Its first sentence identifies what belongs and the nearest excluded work. Follow Choosing where to build for the visible listing's length and sentence boundary. Write plain prose, not a four-field routing description, and do not copy the boundary into a second file.

Before adding a file, check that boundary. A different file kind does not make a different subject. If the purpose changes, update the description in the same change; if the file falls outside it, choose another home.

## Source layout

| Content | Folder |
|---|---|
| Skills, rules and commands | `skills/`, `rules/`, `commands/` |
| Agents | `agents/<name>/`, containing `prompt.md` and `agent.json` |
| Hooks, MCP servers and packs | `hooks/`, `mcp-servers/`, `packs/` |
| Guidance shipped into other folders | `folder-instructions/` |
| Methods, principles and glossary entries | `capabilities/`, with the glossary in `capabilities/glossary/` |
| Tools | `capabilities/tools/<tool>/` |

Use the concrete kind's entry for its file and schema. [rbtv CLI](rbtv-cli.md) is authoritative for discovery and validation. Root-level `references/`, `prompts/`, `workflows/` and `tools/` do not replace the scanned folders. Capability prose is read from source through routes, not installed.

The component's glossary defines its own terms and the [Folder artifacts](folder-artifact.md) used by work it organizes. Write those entries with the first use. Shared rbtv terms remain in rbtv's glossary. Do not keep work-folder conventions only in one skill.

What a component's programs write in an installation lives outside its source, under the component's name: what the user chose or supplied (settings, choices, credentials, keys) in `.rbtv/config/<component>/`, as [Config](config.md) specifies, and operational data (state, caches, locks, logs) in `.rbtv/runtime/<component>/`, as [Runtime](runtime.md) specifies. Those folders carry the name without the module, so no component of another module may use the same name.

Do not create `capabilities.md`, `principles.md`, `glossary.md` or another directory index. Routes name pages directly.

## Local instructions and decisions

Instructions for editing this component belong in its own folder-instructions file. Sources in `folder-instructions/` are for guidance shipped to target folders; the two purposes are different.

Create `decisions.md` at the component root only when there are standing decisions to record. Operational pages describe the current design. Comparisons with older designs belong in decisions; replace superseded decisions rather than retaining conflicting rulings.

## Changes and review

Rename the folder, record and current callers together. When converting, classify each file and use the scanned layout; an outside package record is not `<component>.json`. Keep installation-specific material in the mirror.

Review all files against the description and list the component with rbtv. Check that no intended file disappeared because it was placed outside discovery folders. Have a reader place a new matching file and a neighboring excluded file using only the description.
