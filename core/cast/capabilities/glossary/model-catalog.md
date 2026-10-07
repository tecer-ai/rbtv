# Model catalog

The model catalog is the table of the models one installation selects, with the columns `cast route` ranks them on. Each row names a harness and a model: a [supported model](supported-model.md) with a row is a [selected model](selected-model.md), so cast launches it in that installation, and the row's columns decide whether and when `cast route` names it.

Read this entry before reading or editing a `models.csv`, or stating what a row, a column or a `use` value means. To choose the models of an installation, or to make cast support a new one, follow [Personalizing the model catalog](../personalizing-the-model-catalog.md).

Three other things have nearby names. The supported models are what this copy of cast can launch; they are code, in `supported-models.js`. rbtv's source catalog is the list of modules, components and files rbtv installs, always written in full. A [routing table](../../../rbtv/capabilities/glossary/routing-table.md) is the rows that tell an agent which page to read. Write "model catalog" in full for this table and never for the other three.

## Files

| File | What it holds |
|---|---|
| `core/cast/capabilities/tools/cast/models.csv`, the shipped model catalog | The rows rbtv proposes: at least one for every supported model. |
| `<installation>/.rbtv/config/cast/models.csv`, the installation's model catalog | The rows this installation chose. It is committed with the installation, so every machine and the Ignite daemon read one choice. |

The model catalog in force is the installation's file when it has one, and the shipped one otherwise. The installation is the first folder, from the starting folder upward, that holds `.rbtv/config/install.json`: the agent's folder for `cast --agent`, the current folder for every other command. An installation with no file of its own, and a launch outside any installation, therefore has every supported model selected.

## Rows

A row selects its harness and model. Three cases follow from comparing the row with the supported models:

- A row whose model cast supports is launchable: by `cast <harness> <model>`, by `cast --agent`, by an Ignite turn and by `cast api`.
- A supported model with no row in the installation's file is not selected there. cast refuses to launch it and names `cast models add HARNESS MODEL`.
- A row whose model this copy of cast does not support is never launchable, and `cast route` excludes it with a warning on standard error. `cast models list --catalog` still shows it.

Keep one row per model line: the latest version of that model. A model may have a second row at another level when its list price misstates what it costs the installation, for example a model paid through a subscription. The two rows are identical in every cell except `level` and the two override columns, and both launch the same model. Two rows for one model that differ in any other cell are an error, and `test_route.js` fails on them in the shipped file. Adding a level to a model changes every verdict of the classes that reach it; it is the owner's decision.

## Columns

| Column | Values | Meaning |
|---|---|---|
| `mode` | `cli`, `api` | Launched through a harness, or called by `cast api`. |
| `harness` | `claude`, `codex`, `opencode`, `api` | The harness of a `cli` row; `api` for an `api` row. |
| `model` | the short name | The name a launch takes, as `cast models list` prints it. |
| `efforts` | a number | How many effort rungs the model has; `0` means it has no dial. |
| `image` | `Y`, `N` | Whether the model generates images. |
| `level` | `SOTA`, `L1`, `L2`, `L3`, `L4` | The quality tier. Each `cast route --class` reads exactly one of the first four; `L4` is reached only by `--caps image`. A blank level takes the row out of routing. |
| `reasoning` | 1 to 7 | The score ranked for `--type text`. Blank reads as 0. |
| `coding` | 1 to 7 | The score ranked for `--type code`. Blank reads as 0. |
| `cost` | a number | Dollars per million output tokens at the provider's public list price, never what a subscription makes it cost. A blank cost keeps the row out of every price ranking. |
| `use` | `route`, `panel`, `off` | Who may see the row; see below. Blank reads as `route`. |
| `quality-override` | `Y`, `N` | `Y`: inside its own level, the row wins a `--optimize quality` ranking whatever the scores say. |
| `price-override` | `Y`, `N` | `Y`: inside its own level, the row wins a price ranking whatever the costs say. |

`use` has three values:

- `route`: the row competes for verdicts.
- `panel`: no verdict names it. It stays in `cast models list --catalog`, where a panel takes its seats: [Panel](../../../../meta/sub-agents/capabilities/panel.md). Use it for a model worth a second opinion and never worth being the single answer.
- `off`: routing ignores the row. The model stays selected, so it launches by name and stays in `cast models list --catalog`.

A `use` value that is none of the three drops the row from routing with a warning on standard error. One column carries the three states because two yes-or-no columns would allow a row that is both routed and panel-only, a state with no meaning.

An override never crosses a level: an `L2` row with `quality-override=Y` still loses to every eligible `L1` row. It never bypasses a filter either: login presence, `--access`, `--caps` and the class's level all run first, so an override only reorders rows that already qualify. `cast route` ranks on price when `--optimize` is omitted, so `price-override` acts there and `quality-override` acts only under `--optimize quality`. Several overriding rows in one level keep the normal tie-breaks among themselves.

## How to work with it

Select and unselect a model with `cast models add HARNESS MODEL` and `cast models remove HARNESS MODEL`. They keep the file's header and line ending, replace the file in one step, and `remove` first checks who in the installation still launches the model. Edit a routing cell by hand in the installation's file; cast has no command for that.

cast reads the installation's file strictly, because it gates every launch there, the daemon's included. A file it cannot read as a table is refused with the file and the line, and no model launches until it is corrected. [cast](../cast.md#the-model-catalog-and-the-launch-check) lists what makes a file unreadable and the refusal of each launch case.

## Checks

`cast models list --catalog` prints every row of the model catalog in force with its columns, `launchable` (cast supports the row) and `available` (its login is present), and names the file it read. Run it after every change. To see how a changed cell moves a verdict, run the `cast route` command for the affected class with `--explain`: the trace names every row that dropped and why.
