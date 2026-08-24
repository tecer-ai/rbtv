---
description: The staffing-discovery surface — list the component databases (agent cards, kind-filtered cognitive units, seats, tasks, workflows) blurb-first, or search them by meaning; binding nothing.
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
rbtv teambuild search "<need>"   rank every database by MEANING — the semantic search
rbtv teambuild selftest      this browse's own mechanics, red arm included
```

Flags: `--root <dir>` (the mirror root; default is the nearest `.rbtv/mirror` walking up from cwd)
· `--kind <k>` (units only) · `--module <m>` / `--component <c>` · `--json` · `--pretty`
· search only: `--top <n>` · `--index <f>` · `--preamble`.
Exit codes: `0` success · `1` refusal · `2` usage error.

## search — the semantic half (core-build task 7.434, design `W11-semantic-search-provider-module`)

`search` ranks the same blurbs by meaning, not by keyword: a Portuguese query returns the right
English entries, and there is **no lexical fallback** — a search that cannot reach its provider
refuses with a named error class and a non-zero exit rather than quietly ranking by word overlap.

**One vendor boundary.** Every provider call goes through `tool/lib/provider.js`, whose header
states the contract a provider satisfies (`id`, `model`, `dim`, `batchLimit`, `embedDocuments`,
`embedQuery`). `tool/lib/search.js` takes a provider as a PARAMETER and knows no vendor. Swapping
providers is safe rather than merely possible: `id`/`model`/`dim`/`normalizer` are index header
fields, and a header mismatch discards every stored vector instead of ranking new queries against
an old model's embeddings.

**The index** lives at `<workspace>/.rbtv/runtime/teambuild/index.json` — gitignored, never
committed, never reviewed. Its lifecycle is `mrd-w9-refresh-story.md` §3.4, implemented not
reinvented: every invocation re-walks the corpus from disk, diffs a `sha256` per blurb taken over
the exact text sent to the provider, embeds only what changed, drops what disappeared, persists
atomically, then ranks. Staleness is therefore **zero for every blurb readable at invocation** —
the refresh is not an act anyone can forget, it is the first five steps of the search. The one
residual is enumerated, never implied: entries whose re-embed failed are listed as `unindexed`,
so a ranking over a partial corpus says so.

**The key.** `VOYAGE_API_KEY` is resolved OS-environment-first, then by this module's own sourcing
of the file named by `env_file` in the workspace's `rbtv.json` — nothing else in the workspace loads
that file into a process environment, so the module does it at use. `search --preamble` asserts, in
order: the file is present BY NAME → sourcing was performed → the variable is present. The order is
what discriminates: an absent **file** is a supply question only the owner can answer; an empty
**variable** after sourcing is a wiring defect in this module. The key's value is never printed,
logged, committed, or passed as an argument — name and length only.

## The parity constraint — ONE code path

**This is the only implementation of the browse.** The console's disconnected-mode scaffolding
browse and any future panel client **ride this command** — they call it and render its `--json`;
they do not get a second enumerator. Nothing panel-shaped is built here. A second reader landing
anywhere is the defect this constraint exists to prevent, not a variant of it, and
`rbtv teambuild selftest` asserts the property rather than trusting this paragraph.

The corpus enumerator is `tool/lib/corpus.js`, and the semantic search rides **it** rather than
re-walking the tree: `search.js` obtains every entry through `require('./corpus')` and enumerates
nothing itself. Two modules now sit beside `corpus.js` in `tool/lib/` — `provider.js` (the vendor
boundary, which never touches the corpus) and `search.js` — and neither is a second reader.

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

## Read-only over the corpus

`teambuild` binds nothing, and it never writes to the component databases. The one file it does
write is `search`'s own index under `.rbtv/runtime/` — a derived, gitignored artifact, never corpus
content and never a second copy of a blurb. The staffing recommendations it surfaces on an agent
card are **hints** the staffer carries into the executor binding, never a binding themselves — late
binding stands, and the seat catalog's `staffing-hints` override them per pairing.

## Known bound

Seats are read from `seats.csv` only. The office-scaffold prototype's `seats/*.seat.json` is
**not** read: that shape was ruled against (`office-scaffold.md` § Post-mint status, item 2), and
reading it here would adopt a superseded schema through a browse.
