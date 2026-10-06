# `path-owners.json`

`path-owners.json` is rbtv’s record of shared commands in [`~/.rbtv/`](rbtv-home-folder.md): each command’s executable and the installations that use it. Its [schema](../templates/path-owners-json.schema.json) defines the fields. Each installation’s selections belong in its own record, not here.

Change ownership by adding or removing tools through [rbtv CLI](rbtv-cli.md); do not edit this record by hand. When the executable still exists, removing one installation’s selection keeps the command for its other owners; the last removal deletes it. If the recorded executable has disappeared, removal clears the broken command and its ownership entry even when other owners remain recorded.

Use `rbtv doctor` to check this installation’s command ownership. To find claims belonging to absent installations, use `rbtv doctor --cleanup-audit` and follow its reported preview and release commands. An unreadable ownership record blocks command changes; repair the reported defect before retrying rather than discarding other installations’ claims.
