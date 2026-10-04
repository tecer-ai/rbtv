---
name: manage-components
description: "Discover and manage RBTV modules components skills and rules in a workspace or agent home"
---

# Manage RBTV components

Use `rbtv` for the current workspace. Run `rbtv status` first to see its target and saved settings. Bare `rbtv list` shows modules; `list NAME` opens an exact module, component, or item. Use `rbtv search WORDS` to search names and descriptions broadly, then `rbtv show NAME` to inspect one choice. Use the stable item ID from `show` with `rbtv add NAME` or `rbtv remove NAME`. A pack (a named list of units turned on together) is turned on or off with `--pack NAME`.

On a fresh target, use `rbtv configure --harness NAMES --guidance NAME` before adding items, or supply both settings on the first `add`. `rbtv update guidance` copies maintained human text into configured instruction files while keeping each file's generated sections. `rbtv update scaffolding` refreshes selected files and generated sections in every configured instruction file while keeping human text outside them. `rbtv update all` does both from local source. These commands do not change the selected items. For another agent or workspace, pass `--target PATH` to each command. Use `--dry-run` before a change when its scope is uncertain. Follow `rbtv --help` for filters, exclusions, and required confirmation. Report the resolved target and next action.

An rbtv agent (a folder holding `agent.md` and `agent.json`) is managed with `rbtv agent add | remove | configure | update | list`, not with the root verbs. Its harness, model and effort are changed only by `rbtv agent configure`.
