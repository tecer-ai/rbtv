# Knowledge

Durable knowledge about the owner, under `.rbtv/memory/knowledge/`. One file per kind: `facts`, `preferences`, `decisions`, `self`, and `health`. Facts are what is true about the owner's life. Preferences are what they like and how they want things. Decisions are choices that bind the owner beyond one project. Self is a distilled self-model. Health holds only lines that change how agents act, and points at the owner's notes rather than copying them.

A fact that should shape nearly every turn belongs in the [profile](profile.md), never in both. The profile has no health section. Every agent may read all five files, health included. They are read on demand.

The [dreamer](dreamer.md) writes them, from transcripts and the [inbox](inbox.md). `facts`, `preferences`, and `decisions` are single files. A write that would pass a file's cap is refused and reported, never truncated; the file does not split. A folder's own decision register is `_artifacts/decisions.md`, a different file: knowledge decisions are the owner's life decisions.
