---
name: manage-components
description: Discover, install, or remove RBTV modules, components, skills, and rules for the current workspace or another agent home.
exposes-cli:
  - meta/installer/install
---

# Manage RBTV components

Use `rbtv install` for the current workspace. Run `rbtv install status` first to see its target and saved settings. Run `rbtv install list [QUERY]` to find copyable names, then `rbtv install show NAME` to inspect one choice. Use the stable name from `show` with `rbtv install add NAME` or `rbtv install remove NAME`.

For another agent or workspace, pass `--target PATH` to each command. Use `--dry-run` before a change when its scope is uncertain. Follow `rbtv install --help` for module-wide operations, harness settings, and any confirmation the command requires. Report the result's resolved target and next action.
