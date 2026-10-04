---
name: manage-components
description: "Discover and manage RBTV modules components skills and rules in an installation or agent home"
---

# Manage RBTV components

Use `rbtv` for the current installation. Run `rbtv status` first to see its target and saved settings. Bare `rbtv list` shows modules; `list NAME` opens an exact module, component, or unit. Use `rbtv search WORDS` to search names and descriptions broadly, then `rbtv show NAME` to inspect one choice. Use the stable unit ID from `show` with `rbtv add NAME` or `rbtv remove NAME`. A pack (a named list of units turned on together) is turned on or off with `--pack NAME`.

On a fresh target, use `rbtv configure --harness NAMES --guidance NAME` before adding units, or supply both settings on the first `add`. `rbtv update guidance` copies maintained human text into configured instruction files while keeping each file's generated sections. `rbtv update scaffolding` refreshes selected files and generated sections in every configured instruction file while keeping human text outside them. `rbtv update all` does both from local source. These commands do not change the selected units. For another agent or installation, pass `--target PATH` to each command. Use `--dry-run` before a change when its scope is uncertain. Follow `rbtv --help` for filters, exclusions, and required confirmation. Report the resolved target and next action.

An rbtv agent (a folder holding `agent.md` and `agent.json`) is managed with `rbtv agent add | remove | configure | update | list`, not with the root verbs. Its harness, model and effort are changed only by `rbtv agent configure`.

An agent that a component ships (a unit of type `agent`; see `rbtv list --type agent`) installs in two forms, and both may exist together. As an rbtv agent in its own folder: `rbtv agent add NAME --harness HARNESS --model MODEL --effort EFFORT` (the three flags are required, because a shipped agent names none of them). As a harness-native sub-agent of a target (the harness's own sub-agent file): `rbtv add NAME --on HARNESS:MODEL:EFFORT`, with `--on` once per harness; each harness must be one the target receives, and the file is written only for the harnesses given. Run `cast list` for the harnesses, models and efforts. Run the same `rbtv add` again to change a harness's model and effort; `rbtv remove NAME` removes the sub-agent for every harness. After `rbtv configure --harness` adds a harness, follow the command its result gives for each sub-agent: rbtv does not choose a model or an effort by itself.
