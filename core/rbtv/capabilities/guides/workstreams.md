# Building workstreams

[Workstreams](../glossary/workstreams.md) is the map of everything active: one line each, pointing at the folder and the board.

## Purpose

It lets an agent see what is active without reading every board. Without it, planning has no single map, or the map copies state that goes stale. Which kind of unit to build is in [Choosing what to build](../choosing-what-to-build.md). Do not add a second map.

## What good looks like

- One line per active project, area, or agent subject. The line names where it lives and does not state progress ([Single source of truth](../principles/single-source-of-truth.md)).
- Past 60 lines the owner is alerted. The file does not refuse a line ([Deterministic first](../principles/deterministic-first.md)).
- The dreamer wrote it. A line that left has a reason in the run's commit.

## Making it good

Do not edit the file by hand. Close or archive the subject, project, or area; the dreamer updates the map. If the digest says the file is past 60 lines, review the map with the owner. Do not delete lines to get under the threshold.

## Traps

- Copying board state into the line. The board is the state. The line is the pointer.
