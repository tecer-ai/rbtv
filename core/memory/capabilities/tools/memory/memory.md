# memory

`memory` is the shared board, capture and publication tool. Its program is `memory.js` in this folder. `-h` is the interface reference.

The library entry is `lib/index.js`. Ignite calls that file by a repository-relative require. Albert and the migration tool call the same exports.

A refusal from `validate` and `publish` is a list. Each item has `path`, `operation`, `requirement`, `expected` and `reason`. The command does not stop at the first failed requirement when a later check can still run. It does not print memory text the caller did not submit.

Proposal field names are not restated here. The consolidation tool's `-h` teaches that structure.
