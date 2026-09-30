# `~/.rbtv/`

The folder in the user's home that rbtv keeps for one person across all their installations, separate from any installation's [`.rbtv/`](rbtv-folder.md). It holds `bin/`, where the [installer](rbtv-installer.md) places the commands that make [tools](tool.md) runnable through [`PATH`](path.md), and [`path-owners.json`](path-owners-json.md), its record of those commands. Each command in `bin/` is a link to its tool's program, or on Windows a small launcher file that runs it; rbtv fixes no text for them beyond pointing at that program. It is not hand-written.
