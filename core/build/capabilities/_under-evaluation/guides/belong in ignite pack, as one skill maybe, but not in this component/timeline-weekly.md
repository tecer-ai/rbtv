# Building a weekly timeline

A [weekly timeline](../glossary/timeline-weekly.md) file is the few events of one week that still matter.

## Purpose

It answers what happened that week without copying the daily files or the owner's weekly note. Without it, the question is a pile of daily files. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md). Do not write the file from a turn.

## What good looks like

- The dreamer wrote it, from that week's daily timeline.
- Each event links the daily file it comes from and does not repeat it ([Single source of truth](../principles/single-source-of-truth.md)).
- The owner's weekly note is linked, not copied.
- The file is read on demand and never injected ([Progressive disclosure](../principles/progressive-disclosure.md)).

## Making it good

Do not create or edit the file by hand. Correct a durable fact through `ignite-agent remember`, not by editing the week file.

## Traps

- Restating the daily episodes. The week keeps only what still matters, and points at the day.
