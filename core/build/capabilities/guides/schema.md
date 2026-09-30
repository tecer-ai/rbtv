# Building a schema

A [schema](../glossary/schema.md) is the code-readable shape of a standard file, or of its frontmatter, which a program checks files against.

## Purpose

It lets a program refuse a file that does not match, instead of acting on it. Without it, a wrong or missing field is found only when something breaks. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- Every field a program reads is a property, required when the program cannot work without it; no other field is accepted ([Deterministic first](../principles/deterministic-first.md)).
- Each property's description says what it holds in one line.
- No field is added for a value with only one use today ([Keep it simple](../principles/kiss.md)).
- It holds no secret, and no field is meant to: a secret is named by its environment variable.

## Making it good

List what the program reads from the file, then write one property for each, with its type and a one-line description. Mark the ones the program cannot work without as required.
