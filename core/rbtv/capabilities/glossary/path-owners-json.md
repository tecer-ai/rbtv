# `path-owners.json`

The [rbtv CLI](rbtv-cli.md)'s record, in [`~/.rbtv/`](rbtv-home-folder.md), of each command it placed on `PATH`: the tool's CLI that the command runs and the installations that installed it. A command is removed only when its last installation uninstalls it. CLIs read it; agents do not.
