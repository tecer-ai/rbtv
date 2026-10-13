# Model catalog

The model catalog is the table of the models one installation selects, with the columns `cast route` ranks them on. Each row names a harness and a model: a [supported model](supported-model.md) with a row is a [selected model](selected-model.md), so cast launches it in that installation and `cast route` may name it, and the row's columns decide when.

Read this entry before reading or editing a `models.csv`, or stating what a row or a column means. To choose the models of an installation, follow [Personalizing the model catalog](../tools/cast/documentation/personalizing-the-model-catalog.md). To add, replace, remove or edit a model cast supports, follow [Changing the supported models](../methods/changing-the-supported-models.md).

Three other things have nearby names. The supported models are what this copy of cast can launch; they are code, in `supported-models.js`. rbtv's source catalog is the list of modules, components and files rbtv installs, always written in full. A [routing table](../../../rbtv/capabilities/glossary/routing-table.md) is the rows that tell an agent which page to read. Write "model catalog" in full for this table and never for the other three.

## Files

| File | What it holds |
|---|---|
| `core/cast/capabilities/tools/cast/models.csv`, the shipped model catalog | The rows rbtv proposes: one for every supported model, with both override cells blank. |
| `<installation>/.rbtv/config/cast/models.csv`, the installation's model catalog | The rows this installation chose. It is committed with the installation, so every machine and the Ignite daemon read one choice. |

The model catalog in force is the installation's file when it has one, and the shipped one otherwise. The installation is the first folder, from the starting folder upward, that holds `.rbtv/config/install.json`: the agent's folder for `cast --agent`, the current folder for every other command. An installation with no file of its own, and a launch outside any installation, therefore has every supported model selected.

## Rows

A row selects its harness and model. Three cases follow from comparing the row with the supported models:

- A row whose model cast supports is launchable: by `cast <harness> <model>`, by `cast --agent`, by an Ignite turn and by `cast api`. It is also eligible: `cast route`, a fallback and a panel may name it, subject to its login, its level and what it can do. No column takes a selected model out of routing; to keep a model out, remove its row.
- A supported model with no row in the installation's file is not selected there. cast refuses to launch it and names `cast models add HARNESS MODEL`.
- A row whose model this copy of cast does not support is never launchable, and `cast route` excludes it with a warning on standard error. `cast models list --catalog` still shows it.

Keep one row per model line, at a pinned version: the latest version of that model, never a moving alias such as a `-latest` name, because what an alias launches changes without a change to the row. The shipped model catalog holds exactly one row per supported model, and `test_route.js` fails on any other count. An installation may give a model a second row at another level in its own file when the list price misstates what the model costs it, for example a model paid through a subscription. The two rows are identical in every cell except `level` and the two override columns, and both launch the same model. Adding a level to a model changes every verdict of the classes that reach it; it is the owner's decision.

## Columns

| Column | Values | Meaning |
|---|---|---|
| `mode` | `cli`, `api` | Launched through a harness, or called by `cast api`. |
| `harness` | `claude`, `codex`, `opencode`, `api` | The harness of a `cli` row; `api` for an `api` row. |
| `model` | the short name | The name a launch takes, as `cast models list` prints it. |
| `efforts` | a number | How many effort rungs the model has; `0` means it has no dial. |
| `image` | `Y`, `N` | `Y`: an image-generation model. It is chosen by `cast route --caps image` alone: no class ranks it, no fallback runs it and no panel seats it. Its `level`, `reasoning` and `coding` cells are blank, because the tiers and scores of text and code work do not apply to it. |
| `level` | `SOTA`, `L1`, `L2`, `L3` | The quality tier, and the class of work it serves: `SOTA` strategy and architecture (`planner`), `L1` a wide investigation that chooses its own approach (`broad`), `L2` a bounded problem solved with local implementation judgment (`bounded`), `L3` an explicit bounded operation with checks, extraction and classification included (`mechanical`). Each `cast route --class` reads exactly one. A blank level keeps the row out of every class. |
| `reasoning` | 1 to 7 | The score ranked for `--type text`. Blank reads as 0. |
| `coding` | 1 to 7 | The score ranked for `--type code`. Blank reads as 0. Both scores are a relative calibration among the rows of this table, not a measured benchmark result. |
| `cost` | a number | US dollars per million output tokens at the provider's standard API list price, at the base rate where the price rises with the size of the request, and never what a subscription makes it cost. Blank where no per-token price compares, as for an image model; a blank cost keeps the row out of every price ranking. [Sources of the shipped scores and costs](../methods/changing-the-supported-models/score-and-cost-sources.md) holds the source of each shipped cost. |
| `quality-override` | `Y`, `N` | `Y`: inside its own level, the row wins a `--optimize quality` ranking whatever the scores say. |
| `price-override` | `Y`, `N` | `Y`: inside its own level, the row wins a price ranking whatever the costs say. |

A blank override reads as `N`. An override never crosses a level: an `L2` row with `quality-override=Y` still loses to every eligible `L1` row. It never bypasses a filter either: login presence, `--access`, `--caps` and the class's level all run first, so an override only reorders rows that already qualify. `cast route` ranks on price when `--optimize` is omitted, so `price-override` acts there and `quality-override` acts only under `--optimize quality`. Several overriding rows in one level keep the normal tie-breaks among themselves.

## Who owns a cell

`mode`, `harness` and `model` name the row. rbtv proposes `efforts`, `image`, `level`, `reasoning`, `coding` and `cost`: they describe the model, and `cast models update` copies them from the shipped model catalog into the installation's file. The installation decides `quality-override` and `price-override`: the shipped model catalog leaves both blank for every model, `cast models set` writes them and `cast models update` never changes them. Which models have a row is the installation's choice too, made with `cast models add` and `cast models remove`.

## Fallback

A launch whose model fails to start can run another model of the same level in its place. The installation turns this on in its defaults, and the candidates are the other selected `cli` models of that level, never an image model: [cast](../tools/cast/cast.md#fallback) states the rule. The model catalog holds no column for it.

## How to work with it

Change the installation's file through `cast models`, never by hand: a file cast cannot read stops every launch, and each command checks its result before it replaces the file in one step, keeping the header and the line ending.

| To | Run |
|---|---|
| select or unselect a model | `cast models add HARNESS MODEL`, `cast models remove HARNESS MODEL`; `remove` first checks who in the installation still launches the model |
| make a model win its level | `cast models set HARNESS MODEL --quality-override Y\|N --price-override Y\|N`; an override of a model listed at two levels takes `--level` |
| take rbtv's current values for the cells it proposes | `cast models update`, or `cast models update HARNESS MODEL` for one model |

An installation with no file of its own gets one from the first `set` or `remove`, as a copy of the shipped one. Every command takes `--dry-run`. A value `set` and `update` cannot write, such as a level rbtv does not propose, is the one case for an edit by hand; run `cast models list --catalog` straight after it.

cast reads the installation's file strictly, because it gates every launch there, the daemon's included. A file it cannot read as a table is refused with the file and the line, and no model launches until it is corrected. [cast](../tools/cast/cast.md#the-model-catalog-and-the-launch-check) lists what makes a file unreadable and the refusal of each launch case.

## Checks

`cast models list --catalog` prints every row of the model catalog in force with its columns, `launchable` (cast supports the row) and `available` (its login is present), and names the file it read. Run it after every change. `cast doctor` counts the cells that differ from the shipped model catalog and names `cast models update --dry-run`, which lists them. To see how a changed cell moves a verdict, run the `cast route` command for the affected class with `--explain`: the trace names every row that dropped and why.
