---
description: The control panel — one page over the scaffolding itself, built from disk by its own command. Seats and workflows today; more views as they are built.
---

# control-panel — a page over the scaffolding

`rbtv control-panel` — scans the scaffolding on disk and renders it as one self-contained page. Not a mockup and not a report: **the real control panel, built in pieces.** Two views exist today, Seats and Workflows; the shell is built to take the rest.

```
rbtv control-panel update [--out DIR] [--json]   scan, then write panel.html + panel-data.js
rbtv control-panel status [--json]               where the data is, how old, what it holds
rbtv control-panel selftest                      fixture + red arms; exit 0/1
```

Flags: `--out <dir>` (default `<runtime>/control-panel`) · `--runtime-root <dir>` (default: the nearest `.rbtv/` walking up from cwd) · `--json`.
Exit codes: `0` success · `1` refusal · `2` usage error.

## what it is a view OF

The **scaffolding** — shipped `rbtv/` plus this install's `mirror` (`concepts/mirror.md`), which the shared machinery treats as native. Both roots are scanned; the mirror's path-shadowing is resolved, so a mirror row that supersedes a shipped one appears ONCE, marked, naming the file it suppresses (`d-mirror-path-shadowing`).

It is **not** a view of runs. Nothing under `.rbtv/goals/` is read: no execution records, no bindings, no seat memory. The catalog's `staffing-hints` is a hint and is shown as one — the real harness/model binding is decided late, at goal-materialize, and does not belong on a page about what a seat *is*.

## what it reads

Per component folder (`<module>/<component>/`, depth exactly 2, in each root):

| Source | Gives |
|---|---|
| `seats.csv` | one row per seat. Columns DIFFER between catalogs (`meta/master` carries no `goal-writes`); each catalog is read by its own header row, never a fixed schema |
| `prompts/<executor>.md` | the seat's contract — frontmatter (`id`, `description`, `staffing-recommendations`, `human-interactive`, `fallback`, `exposes`) over `<role>`, `<procedure>`, `<resources>`, `<io-spec>`, `<permissions>`, `<restrictions>`, `<constraints>` |
| `tasks/<task>.md` | the paired task — `<task-goal>`, `<scope>`, `<done-contract>` |
| `workflows/<name>/<name>.csv` | the manifest — `Seat/workflow,after,i/o,Modality`. `after` is the only ordering fact on disk, and the drawn diagram is layered from it alone |
| `workflows/<name>/workflow.md` | the workflow's own prose |

## what it flags

Health findings ride the seat or workflow they belong to AND a count in the topbar. A missing prompt or task file, a manifest naming a seat no catalog carries, a workflow folder with no manifest, a duplicate seat-id, a catalog that will not parse. A page that silently drops a broken seat is worse than no page: the flag is the product, not a diagnostic.

## where the output goes — and why not here

`update` writes to `<runtime>/control-panel/`, never into this component folder. The generated data describes THIS install's scaffolding at THIS moment: it is instance state, and shipped `rbtv/` is distributed content (`concepts/mirror.md` § differentiation, CMP-1). Writing it here would put one install's data inside content every install receives. Same discipline as `embed-search`, whose index is likewise never inside the tree it indexes.

The page and its data are written as **siblings** so the page loads over `file://` with no server: a browser refuses a local page's `fetch` of a sibling `.json`, but allows `<script src>`, so the data is a `.js` file assigning `window.PANEL_DATA`. The copy under the runtime root is the one to open. The shipped `tool/panel.html` is the template; opened directly it has no data sibling and renders its empty state naming the command.

Neither generated file is committed — the vault's `.gitignore` carries `.rbtv/control-panel/`. A refresh must never be a diff.

## what refuses (the red arms)

No `.rbtv/` found walking up from cwd, and no `--runtime-root` given, refuses naming the search. A `--runtime-root` that is not a directory refuses naming the path. A missing shipped page template refuses. An unknown verb is a usage error. `selftest` plants a missing prompt file, a manifest seat in no catalog, and a manifest-less workflow folder on a scratch tree and asserts all three are reported — plus a shipped-vs-mirror pair, asserting the mirror row wins, names the file it suppresses, and leaves no duplicate.

## design source

`1-projects/build-ignite/control-panel-mockup/control-panel-v3.html` is the reviewed design this page's visual system is taken from. It remains the design reference; this component is the product.
