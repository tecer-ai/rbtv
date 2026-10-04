# Building a board

A [board](../glossary/board.md) is the short-term memory of what matters in one folder, by subject.

## Purpose

It tells a wake what matters and where to resume or answer. Without it, a wake with only a check name has to guess, and a correction is asked again the same day. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md). The board is not one of those units. The agent maintains it. Ignite writes timers and flags. The dreamer only shortens a subject and moves detail out.

## What good looks like

- All four sections are present, empty when unused.
- One subject is one noun-phrase title, one to three state lines, then Threads, Detail, and Flags. A second fact is not folded into a state line.
- Threads are links the agent added. Ignite did not add one ([Single source of truth](../principles/single-source-of-truth.md)).
- A watch-out is a correction of this agent's behaviour, recorded in the same turn. A fact about the owner is not stored here.
- An over-cap write is refused, not shortened ([Deterministic first](../principles/deterministic-first.md)).
- Timers, flags, and Recently closed are not hand-edited.
- Closing a subject writes Recently closed. Nothing is deleted on a timer.

## Making it good

Copy the board, edit subjects or watch-outs, and submit the whole candidate with `ignite-agent board write --file <path>`. Keep Timers, Recently closed, and existing Flags unchanged. Close with `ignite-agent board close <subject> <outcome> [thread]`. Do not edit the board file directly. When six closed lines already exist, archive old lines before closing another. A refused watch-out is still followed in the conversation; say so. The dreamer still receives it from the transcript.

## Traps

- Free-editing the file. The check refuses a bad form, and a hand edit races the dreamer.
- Putting the check's details only in the wake. The wake names the check. The board holds the details.
