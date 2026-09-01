# 20260901-c-control-panel-a-page-over-the — control-panel: a page over the scaffolding

kind: creation
component: meta-control-panel
date: 2026-09-01
commit: 4318426c
deployed: no
pin: NONE
components: meta-installer

## Motivation
The scaffolding had no view of itself. Answering "what seats exist, what does each one
actually do, which are mine and which shipped, and is any of it broken" meant reading four
`seats.csv` files by hand, then opening a prompt and a task file per seat. A reviewed design
existed as a mockup (`1-projects/build-ignite/control-panel-mockup/control-panel-v3.html`)
but it was a frozen snapshot with hand-authored data, not a thing that reads disk. The owner
ruled this component IS the real control panel, built in pieces — not a prototype to replace
later — so the shell was built to take further views rather than as a single-view page.

## Design
A CLI that scans and a page that renders, split at a generated data file.

Scope was ruled at design time and is deliberately narrow: SEATS AND WORKFLOWS ONLY, and
SCAFFOLDING ONLY. Nothing under `.rbtv/goals/` is read — no execution records, no bindings,
no seat memory. The catalog's `staffing-hints` is displayed as the hint it is, because the
real harness/model binding is decided late at goal-materialize and does not belong on a page
about what a seat IS. Run history was offered and rejected: it lives in a different place,
goes stale the moment anything runs, and multiplies the scan cost.

No skill row. The owner dropped it: the CLI self-documents via `-h` and the page reads
itself, so a skill would be a third place stating the same thing.

The mirror is handled as the concept defines it, not as an installed-copy comparison. An
earlier draft of `assemble()` read both roots in full and reconciled seat rows afterwards.
That was wrong at the contract: `concepts/mirror.md` § path shadowing is per-file and
WHOLE-FILE, "never a merge". The reconciliation both kept shipped rows the mirror does not
repeat (which the supersession should have removed with the file) and mutated the list it
was iterating, skipping the element after any superseded seat and then raising `KeyError`
on it. Shadowing is now resolved BEFORE reading and a shadowed file is never opened.

Alternatives rejected: baking data into the page (a whole-file diff on every refresh);
serving over HTTP (a server to start before the page can ever be opened); keeping the
generated output inside the component folder (one install's state inside content every
install receives).

## How it works
`rbtv control-panel update` walks `<module>/<component>/` at depth exactly 2 in both the
shipped tree and `.rbtv/mirror/`, reading `seats.csv`, `prompts/<executor>.md`,
`tasks/<task>.md`, `workflows/<name>/<name>.csv` and `workflow.md`. Each catalog is parsed
by its OWN header row — `meta/master`'s columns already differ from `meta/planning`'s, so a
fixed schema would silently drop cells. `shadow_map()` computes the superseded relative
paths first; `scan_root()` takes them as `shadowed` and skips those files entirely.

Output is INSTALL STATE and never lands in the shipped tree: `write_atomic` puts
`panel-data.js` and a copy of `panel.html` in `<runtime>/control-panel/` (default
`.rbtv/control-panel/`). They are SIBLINGS because a browser refuses a `file://` page's
`fetch` of a sibling `.json` but allows `<script src>` — so the data is a `.js` file
assigning `window.PANEL_DATA`, and the page opens by double-click with no server. The
shipped `tool/panel.html` is the template; opened directly it has no data sibling and
renders an empty state naming the command. Same out-of-tree discipline as `embed-search`'s
index.

Health findings ride the seat or workflow they belong to AND a topbar count: a missing
prompt or task file, a manifest naming a seat no catalog carries, a workflow folder with no
manifest, a duplicate seat-id, an unparseable catalog. A page that silently drops a broken
seat is worse than no page, so the flag is the product.

Registration: an `exposure.csv` tool-inventory row, a `meta/module.md` row, and a
`control-panel` route in `meta/rbtv-cli/tool/lib/verbs.js` (`exec: 'direct'`, which is why
the CLI carries a `#!/usr/bin/env python3` shebang).

## Consequences
Replaced nothing; deleted nothing. `control-panel-v3.html` stays in place as the reviewed
design reference and is cited from `component.md`.

Two registration defects were caught by `component-lint` after the first draft copied a
stale comment from `meta/embed-search/exposure.csv`: a `method=path` row must leave
`rbtv-cli` and `description` EMPTY, and a `write-roots` entry must carry the `!` danger
marker and use the `ws:` grammar for a workspace-root path. Both fixed;
`component-lint --component meta/control-panel` now reports 0 findings.

Pre-existing and NOT fixed here, surfaced only: `meta/embed-search/exposure.csv` fails the
same `exposure-canon` check (its filled `rbtv-cli` cell is what misled this build), and
`meta/module.md` carries no row for the `installer`, `leader` or `memory` components.

## Verification
`rbtv-control-panel selftest` — 17 checks, all green. Red arms that genuinely fire: a
missing prompt file, a manifest seat in no catalog, a manifest-less workflow folder. Four
checks cover whole-file shadowing specifically, including one asserting a shipped row the
mirror does not repeat is GONE and one placing a mirror row AFTER the superseding row so a
skip-an-element bug is observable — an earlier fixture seeded one mirror seat and could not
have caught it either way.

Live tree: 25 seats (24 shipped, 1 mirror), 4 workflows, 1 health error. Generated page
driven in headless Chromium via `agent-browser`: no console output, 25 rows, the mirror
seat's origin badge, `plan-console`'s 5-node 5-layer diagram, the manifest-less workflow's
error in place of its diagram, the topbar reading "1 error, 0 warnings".

Not deployed — this is workspace-installed content, not daemon code.

## ATTENTION
1. A `method=path` exposure row must leave BOTH `rbtv-cli` and `description` empty and mark
   every `write-roots` entry `!<path>`. The `rbtv <verb>` route lives in `verbs.js`, never
   in that cell — `meta/embed-search`'s row fills it and FAILS `exposure-canon`, so copying
   a sibling's row is how this trap fires.
2. A `write-roots` path is resolved COMPONENT-RELATIVE unless prefixed `ws:`. A bare
   `.rbtv/control-panel` is read as a directory inside the component folder and refused for
   not existing, which reads like a typo and is a grammar error.
3. Mirror shadowing is WHOLE-FILE and must be decided before reading, not reconciled after.
   Reading both roots then merging keeps shipped rows the mirror deliberately dropped —
   the page then shows seats the install has superseded, and looks correct while doing it.
4. Seat catalogs do NOT share a schema. `meta/master/seats.csv` has no `goal-writes` or
   `on-fail-relaunch` column. Any reader assuming `meta/planning`'s header loses cells with
   no error.
5. Every workflow manifest on disk today is a straight chain — no forks, joins or loops.
   A diagram built from `after` alone therefore draws a line; the v3 mockup's branching
   picture came from hand-authored fields (`phases`, `altLane`, `loops`) that no manifest
   carries. Do not add those fields to make the picture richer without a ruling.
- A method=path exposure row leaves rbtv-cli and description EMPTY and marks write-roots '!<path>'; embed-search's row fills rbtv-cli and fails exposure-canon, so copying a sibling row is the trap.
- A write-roots path resolves component-relative unless prefixed 'ws:'; a bare .rbtv/... is refused for not existing and reads like a typo.
- Mirror shadowing is whole-file and decided BEFORE reading; merging after keeps shipped rows the mirror dropped, and the page looks correct while showing superseded seats.
- Seat catalogs share no schema — meta/master has no goal-writes or on-fail-relaunch column; assuming meta/planning's header loses cells silently.
