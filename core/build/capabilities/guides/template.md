# Building a template

A [template](../glossary/template.md) is the agent-readable shape of a standard file, which an agent reads and fills.

## Purpose

It gives every file of one kind the same sections, so an agent writing one knows what to fill and a reviewer knows what to check. Without it, each author invents a shape and readers cannot find what they need. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- It holds only decided sections and fields. An undecided part is left out, not written as a placeholder.
- Where the file also has a [schema](../glossary/schema.md) part, the template's frontmatter keys are exactly the schema's properties, no more and no fewer; the schema is the authority ([Single source of truth](../principles/single-source-of-truth.md)).
- Each placeholder says what goes there in one line, not how to write it; the how is in the file's guide ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Copy the sections the file's guide requires, in order, and replace their content with one-line placeholders. When the schema changes, change the template's frontmatter in the same change.
