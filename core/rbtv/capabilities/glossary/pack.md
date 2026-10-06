# Pack

A pack is a named list of installable files that several targets enable together. The files remain in the components that own them; the pack refers to their identifiers.

Use a pack when at least two agents or installations need the same group. A list needed by only one target belongs in that target's record.

## Define the shared group

Name the targets that need the group and a neighboring target that should not receive it. Include only files every intended target needs. Put target-specific additions in that target's selections or in a separate shared pack.

Declare the pack in the component whose work it supports, using [Choosing where to build](../choosing-where-to-build.md). Refer to files owned by other components without copying them. A same-name mirror replacement must still contain the referenced files.

Write `packs/<name>.json` to the [pack schema](../templates/pack.schema.json). The filename supplies the pack name; do not add a name field. Names are unique across components. Choose one that identifies the shared use, not a generic label such as “tools.”

The description is one line explaining what the group is for. It is not a routing description and should not merely list file kinds or repeat the declaring component's name.

```json
{
  "description": "<what the shared targets need this group for>",
  "files": ["<module>/<component>#<installed-name>"]
}
```

Use complete identifiers, not paths or shortened names. Include supported skills, rules, commands, hooks, MCP servers, tools and folder instructions. Do not include capabilities, whole-folder skills or other packs.

Do not use a pack to place agent folders. Agent placement needs launch settings the pack cannot carry. Even where the installer accepts an agent reference, enabling the pack alone does not supply those settings; follow [Agent](agent.md) for placement. A hook remains subject to harness support.

## Understand removal before choosing membership

A file remains installed while directly selected by the target or included by any enabled pack. Multiple selections install it once. Disabling a pack removes only files for which that pack was the last selection. Removing a file directly while an enabled pack still names it does not remove that pack's reason for keeping it.

If a target must keep a file after disabling the pack, select that file directly or retain another enabled pack that includes it. If disabling either of two packs must remove a file, do not select that file through both. Disabling a pack does not delete its source or the target agent's folder and work.

## Change and verify

Update identifiers in the same change as a file move or rename. The installer does not follow renamed sources automatically. Apply the updated pack through [rbtv CLI](rbtv-cli.md) before treating targets as current.

Renaming the pack creates a new name. Update target selections together: an installation can drop the unknown old selection during update, while an agent with an unknown pack can be refused. Do not assume targets follow the rename.

Test enabling the pack for two intended targets and excluding a neighboring target. Then disable it on a target that directly selects one member: that file must remain while members selected only through the pack are removed. Validation checks identifiers and record shape, not whether every target needs every member.
