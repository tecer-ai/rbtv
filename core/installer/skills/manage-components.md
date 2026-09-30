---
name: manage-components
description: "Discover and manage RBTV modules components skills and rules in a workspace or agent home"
---

# Manage RBTV components

Use `rbtv install` for the current workspace. Run `rbtv install status` first to see its target and saved settings. Bare `rbtv install list` shows modules; `list NAME` opens an exact module, component, or item. Use `rbtv install search WORDS` to search names and descriptions broadly, then `rbtv install show NAME` to inspect one choice. Use the stable item ID from `show` with `rbtv install add NAME` or `rbtv install remove NAME`.

On a fresh target, use `rbtv install configure --harness NAMES --guidance NAME` before adding items, or supply both settings on the first `add`. `rbtv install update guidance` copies maintained human text into configured instruction files while keeping each file's generated sections. `rbtv install update scaffolding` refreshes selected files and generated sections in every configured instruction file while keeping human text outside them. `rbtv install update all` does both from local source. These commands do not change the selected items. For another agent or workspace, pass `--target PATH` to each command. Use `--dry-run` before a change when its scope is uncertain. Follow `rbtv install --help` for filters, exclusions, and required confirmation. Report the resolved target and next action.
