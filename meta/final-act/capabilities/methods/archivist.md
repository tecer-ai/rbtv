# Archivist

The result: the done entries of the task files in scope are out of those files, deleted or moved verbatim to a file the user names. Open work is untouched.

Inputs: the scope (default: the task files this session changed; otherwise the files or folder the user names); the mode, delete or move; for move, the destination file. Ask for what the user has not said, once, in one question with the list of step 1 in front of them.

## 1. Find the done entries

In each task file in scope, a done entry is a top-level entry the file's format marks as finished: a checked box (`- [x]`) at column 0, or the done status the file's format uses. A checked sub-item under an open parent is not done; it stays. The entry is the whole block: its line and the indented lines under it.

When a tool owns the file's format (the task says so, or the file names one), list and remove through that tool and never hand-edit around it.

Show the list: per file, how many entries, and the first line of each.

## 2. Sweep

- **Move:** append each block, byte for byte, to the destination under a heading naming the source file and today's date (from the system clock). Create the destination only when the user named it; never invent a file. Re-read the destination and confirm every block is there before removing any from its source.
- **Delete:** remove each block from its source.

In both modes, remove nothing from a source until the step before it is verified. A remaining open entry that referred to a swept one (a dependency, a "done after") has that reference dropped, since a done task satisfies it; list each drop.

Never sweep an open entry, and never reformat or renumber what stays.

## 3. Report

One line: entries swept, from how many files, deleted or moved to which file, and the references dropped.
