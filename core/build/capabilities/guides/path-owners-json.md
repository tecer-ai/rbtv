# Building `path-owners.json`

[`path-owners.json`](../glossary/path-owners-json.md) is the installer's record of the commands it placed on `PATH` and the installations that own each.

## Purpose

It lets the installer remove a command only when no installation still uses it. Without it, uninstalling one installation could break another. It is not hand-written.

## What good looks like

- Each command lists every installation that installed it, and no installation that removed it.
