# Building `~/.rbtv/`

[`~/.rbtv/`](../glossary/rbtv-home-folder.md) is the folder in the user's home where rbtv keeps what serves every installation.

## Purpose

It contains the commands that make tools runnable through `PATH`, and the record of which installation owns each. Without it, each installation would put its own copy on `PATH`. It is not hand-written.

## What good looks like

- Every command in `bin/` has an entry in [`path-owners.json`](../glossary/path-owners-json.md), and every entry has its command.
