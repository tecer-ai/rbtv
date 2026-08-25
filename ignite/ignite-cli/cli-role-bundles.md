---
description: Read when deciding which router skills a role's prompt should load — the per-role bundle table, and the one caveat that keeps a skill from being mistaken for a grant.
---

# CLI role bundles

Which roles load which function-bundle router skills. Law:
`1-projects/build-ignite/redesign/specs/spec-component-map.md` **§7.4**. This file is the
transcription of that table onto the component-first tree — it mints no role and no bundle.

The bundles themselves are §7.2 and live beside this file:
[`daemon-ops.md`](daemon-ops.md) · [`goal-ops.md`](goal-ops.md) ·
[`observe.md`](observe.md) · [`staffing.md`](staffing.md) · [`coord-ops.md`](coord-ops.md).
Who each underlying tool is FOR is [`cli-audience-map.md`](cli-audience-map.md) (§7.1).

## The table

| Role | Bundles |
|---|---|
| owner-console | `daemon-ops`, `observe`, `goal-ops`, `staffing` |
| channel-master | `staffing`, `observe` |
| goal-master | `goal-ops`, `staffing`, `observe`, `coord-ops` |
| leader | `coord-ops`, `observe`, `staffing`, `goal-ops` |
| worker (caged) | `coord-ops` only, and only when the seat's `exposes: path:` already names the underlying tool |
| daemon / internal | none — internal-daemon CLIs are not skills |

A role not listed for a bundle does not get that skill in its prompt `exposes:`.

## A skill is discovery, not a grant

The caged-worker row is the one that is misread. A router skill tells a seat which tool
answers its need; what the seat may actually RUN is its generated `seat.md`
`exposed-clis:` block and, for a caged seat, the sandbox built from it. Loading
`coord-ops` into a caged worker's prompt grants nothing on its own — the underlying tool
must already be named by that seat's `exposes: path:`, or the invocation is a refusal at
the sandbox boundary, not a missing skill.

## What this table is not

Not an audience map: a bundle may route to a tool a given role is not granted, because the
bundle is shaped by FUNCTION (owner rulings A-a / B-a), not by audience. The audience label
of each tool is the other table, one file over.
