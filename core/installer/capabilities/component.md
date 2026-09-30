# Installer

`rbtv install` is the one command for discovering, installing, removing, and locally regenerating RBTV content. A module is a bundle of components; a component groups related items; a skill or rule is an item type. A harness is an AI coding tool, such as Claude Code or Codex, that receives installed files.

Start with `rbtv install status` to see the target and saved settings. `list` opens the module catalog; `list NAME` opens an exact scope; `search WORDS` finds matching names and descriptions; `show NAME` explains one selection. `configure` sets up receiving tools and guidance, `add NAME` installs, and `remove NAME` removes. `update guidance` copies maintained human text while preserving generated sections; `update scaffolding` regenerates selected files and generated sections in every configured instruction file while preserving other human text; `update all` runs both from local source. `doctor` checks installer state and selected shortcuts. Pass `--target PATH` for another workspace or agent home. Run `rbtv install --help` for filters and options.

The `manage-components` skill at `skills/manage-components.md` gives agents the same command route. The implementation is `install.py`; historical design rulings live in `design-decisions.md`.
