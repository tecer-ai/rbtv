---
description: The staffing-discovery browse — list the component databases (agent cards, kind-filtered cognitive units, seats, tasks, workflows) blurb-first, read-only, binding nothing.
---

# teambuild — the staffing-discovery browse

`rbtv teambuild <database>` — the surface a staffer (or the console, or a human) drills to see what
the scaffolding offers **before** executors are bound. The contract, its rationale and the rejected
alternatives are the registry's (`concepts/teambuild.md`, `decisions.md#d-teambuild-discovery`) and
are not restated here (`PRIN-11`). Built for core-build task 7.433 (design `W10-teambuild-browse`).

```
rbtv teambuild agents        the agent cards — prompt rows + their staffing recommendations
rbtv teambuild units         cognitive units; --kind <k> filters (role, persona, procedure, …)
rbtv teambuild seats         seat rows (seats.csv — the settled catalog shape)
rbtv teambuild tasks         task rows
rbtv teambuild workflows     workflows, blurbed from their entry point
rbtv teambuild selftest      this browse's own mechanics, red arm included
```

Flags: `--root <dir>` (the mirror root; default is the nearest `.rbtv/mirror` walking up from cwd)
· `--kind <k>` (units only) · `--module <m>` / `--component <c>` · `--json` · `--pretty`.
Exit codes: `0` success · `1` refusal · `2` usage error.

## The parity constraint — ONE code path

**This is the only implementation of the browse.** The console's disconnected-mode scaffolding
browse and any future panel client **ride this command** — they call it and render its `--json`;
they do not get a second enumerator. Nothing panel-shaped is built here. A second reader landing
anywhere is the defect this constraint exists to prevent, not a variant of it, and
`rbtv teambuild selftest` asserts the property rather than trusting this paragraph.

The corpus enumerator is `tool/lib/corpus.js`, exported so the semantic search rides **it** rather
than re-walking the tree: `search` is deliberately **not** a verb of this family — it is built
behind its own provider-module boundary over the descriptions this module already yields.

## Blurb-first, from fields that already exist

No blurb field was added anywhere. The blurb is:

| Database | Blurb source |
|---|---|
| agents (prompts), tasks, seats | the catalog row's `description` **column** |
| cognitive units | the unit file's frontmatter `description` |
| workflows | the workflow entry point's frontmatter `description` |

A component that carries no description reads `(no description)` — the corpus reporting itself.
Manifest CSVs under `workflows/` carry no description column **by design** (they order seats, they
do not describe the workflow), which is why the workflow blurb comes from the entry point.

Both authored mirror layouts on this box are read: unit-kind directories are matched singular **or**
plural (`roles/` and `persona/` both occur), and the kind is reported as authored.

## What refuses (the red arm)

An **absent** catalog is skipped — a component need not carry every database. A **present but
malformed** catalog stops the whole listing and names the file: no header, no `description` column,
or no id column. Reading such a catalog positionally is how every field comes back as the value of
whatever sat at that index. An unresolvable mirror root refuses naming every directory it looked in.

## Read-only

`teambuild` binds nothing and writes nothing. The staffing recommendations it surfaces on an agent
card are **hints** the staffer carries into the executor binding, never a binding themselves — late
binding stands, and the seat catalog's `staffing-hints` override them per pairing.

## Known bound

Seats are read from `seats.csv` only. The office-scaffold prototype's `seats/*.seat.json` is
**not** read: that shape was ruled against (`office-scaffold.md` § Post-mint status, item 2), and
reading it here would adopt a superseded schema through a browse.
