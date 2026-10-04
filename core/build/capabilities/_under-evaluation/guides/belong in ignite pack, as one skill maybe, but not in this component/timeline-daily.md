# Building a daily timeline

A [daily timeline](../glossary/timeline-daily.md) file is the episodes of one day of work between the owner and their agents.

## Purpose

It answers what happened on that day without injecting the day into every turn, and without copying the owner's periodic note. Without it, that question has only the raw transcripts. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md). Do not write the file from a turn.

## What good looks like

- The dreamer wrote it. A day with no agent activity has no file.
- The owner's periodic note is linked, not copied ([Single source of truth](../principles/single-source-of-truth.md)).
- Each episode is one line and points at the thread. It is not the only home of a durable fact.
- The file is read on demand and never injected ([Progressive disclosure](../principles/progressive-disclosure.md)).

## Making it good

Do not create or edit the file by hand. A durable fact from the day goes through `ignite-agent remember` so the dreamer can file it into the profile, knowledge, or an entity. The timeline is not that filing.

## Traps

- Treating a missing file as broken memory. No file means no agent activity that day.
