# Building `runtime/`

[`runtime/`](../glossary/runtime.md) is the folder for operational data created while components run.

## Purpose

It contains data a component creates while it runs, so that data stays out of source. Without it, that data has no home. The folder is not hand-written.

## What good looks like

- The record has fixed fields a CLI can read, not free prose ([Deterministic first](../principles/deterministic-first.md)).
- No copy of that data sits in source or in [`mirror/`](mirror.md) ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Write a record here when a component creates data while it runs, such as data its [tool](../glossary/tool.md) produces. Do not write that data in the component source or in the mirror.
