# Memory index

The always-loaded router of general [memory](memory.md), at `.rbtv/memory/_artifacts/index.md`. One row per folder, plus `workstreams.md`. It is injected into every turn of every agent, including a scheduled wake. It does not grow with the files, so the always-loaded part stays bounded.

It is written once, when general memory is created, and edited only when a folder is added or removed, in that same change. The dreamer does not regenerate it. The [profile](profile.md) and the [inbox](inbox.md) are listed nowhere: they are always loaded. Agent topics are listed nowhere here: they route through the agent's [board](board.md) and that agent's memory index.

Each folder under the root that holds files has its own generated [index file](<../_under-evaluation/guides/folder artifacts/glossary/index-file.md>), read on demand. A parent folder lists its subfolders, not their files. No file appears in both this index and a folder index. Generated indexes have no row cap.
