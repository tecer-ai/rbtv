# The shortcut ledger

The result: every deliberate shortcut in a codebase listed in one ledger, each with its ceiling and the trigger to revisit it, and the ones with no trigger flagged, so that a deferral cannot quietly become permanent. The ledger is reported; nothing in the code changes.

Inputs: the tree to search, a repository or a folder. When the user names none, search the current repository.

## Search

A shortcut is marked as [Shortcut](../glossary/shortcut.md) defines: a comment whose text starts with `shortcut:`. Search the tree for comment lines carrying it, skipping `node_modules`, `.git` and build output; for example:

    grep -rnE '(#|//|--|<!--) ?shortcut:' . --exclude-dir=node_modules --exclude-dir=.git

Add the comment prefix of any other language the tree uses. The comment prefix is what keeps a line of prose that merely mentions the word out of the ledger.

## Output

One row per marker, grouped by file:

`<file>:<line>: <what was simplified>. ceiling: <the limit the marker names>. upgrade: <the trigger it names>.`

Take the ceiling and the trigger from the marker's own text. A marker that names no upgrade trigger gets the tag `no-trigger`; those are the shortcuts that rot. When the user wants an owner per row, add `git blame -L<line>,<line> <file>`.

Close with `<N> markers, <M> with no trigger.` When nothing is found, write `No shortcuts marked. Clean ledger.`

Report the ledger in the message. Write it to a file only when the user names one.
