---
description: Discover and manage RBTV modules, components, and exposed parts in a workspace or agent home.
---

# Installer

`rbtv install` is the one command for discovering, installing, and removing RBTV content. A module is a bundle of components; a component groups related content; a skill or rule is one exposed part of a component. A harness is an AI coding tool, such as Claude Code or Codex, that receives installed files.

Start with `rbtv install status` to see the current target and its saved harness settings. Use `list [QUERY]` for a short catalog, `show NAME` for one full description, `add NAME` to install, and `remove NAME` to remove. These commands accept `--target PATH` when operating on another workspace or agent home. `doctor` diagnoses installer state. Run `rbtv install --help` for all selectors and options.

The `manage-components` skill at `manage-components.md` gives agents the same command route. The implementation is `install.py`; historical design rulings live in `design-decisions.md`.
