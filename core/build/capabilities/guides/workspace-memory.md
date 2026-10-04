# Building workspace memory

[Workspace memory](../glossary/workspace-memory.md) is private notes about a shared repository or workspace.

## Purpose

It gives those notes one home that a shared repository cannot hold. Without it, private cautions are either missing or committed where other people can read them. Which kind of unit to build is in [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>). Do not put the notes in the shared repository.

## What good looks like

- Every line would be wrong or private in the shared repository's own docs ([Single source of truth](../principles/single-source-of-truth.md)).
- The shared docs are linked, not copied.
- The file is injected only when the working directory is under its declared paths. It is not injected on every turn ([Progressive disclosure](../principles/progressive-disclosure.md)).
- At most 3,000 characters. Over cap is refused, never truncated.
- The dreamer wrote it.

## Making it good

Use `ignite remember` for a private fact about a shared repository, and name the repository in the text. Do not edit the workspace file by hand, and do not commit the note into the shared repository. The dreamer files it.

## Traps

- A path that is not the repository the note is about. The file is injected for every working directory under its paths, so a wide path leaks the note into unrelated turns.
