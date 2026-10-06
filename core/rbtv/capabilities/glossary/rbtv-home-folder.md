# `~/.rbtv/`

`~/.rbtv/` is the user’s rbtv home folder, shared by that user’s installations on one machine. It is separate from an installation’s [`.rbtv/`](rbtv-folder.md) and is not by itself an installation marker.

Its `bin/` folder holds command shortcuts to tool executables: links on Linux and launcher files on Windows. `PATH` is the operating system’s list of command-search folders; rbtv handles the machine-specific setup that makes these commands available. [rbtv CLI](rbtv-cli.md) owns executable resolution and installation checks.

Manage the shortcuts through rbtv rather than writing or replacing them by hand. [path-owners.json](path-owners-json.md) records which installations use each managed command; follow that entry when checking or releasing ownership. Do not assume every file in `bin/` is managed or that a saved ownership entry proves its shortcut still exists. Use rbtv’s diagnostics to check the selected commands and their ownership.
