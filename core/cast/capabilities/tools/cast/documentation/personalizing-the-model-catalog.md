# Personalizing the model catalog

Change which models an installation launches and how `cast route` ranks them: select or unselect a [supported model](../../../glossary/supported-model.md), change a row's overrides, set the installation's defaults, or take the values rbtv now ships. Every change touches files of the installation only. Read [Model catalog](../../../glossary/model-catalog.md) first for what a row and each column mean; this page gives the work.

The caller supplies the harness and model names. When the request names a model without its harness, ask before changing anything. When the model is not in `cast models list --supported`, or the request is to add, replace, remove or edit a model rbtv supports, the change is to rbtv's source: follow [Changing the supported models](../../../methods/changing-the-supported-models.md), which returns here for each installation.

## 1. Choose models for this installation

Run every command from a folder inside the installation; `cast models` acts on the installation that holds the current folder and names it in every result.

1. List what can be chosen and what is chosen: `cast models list --supported`.
2. Select a model with `cast models add HARNESS MODEL`. Unselect one with `cast models remove HARNESS MODEL`. Run either with `--dry-run` first and read what would change. `remove` is refused while an agent under `.rbtv/agents/` still launches the model, and lists them: give each another model with `rbtv agent configure AGENT --model M` first. `--force` removes the model anyway and leaves those agents refused at launch. `remove` does not see agents kept outside `.rbtv/agents/` or a component's settings that name a model; the result says so, and you check those yourself. A legacy `dreamer` section in the Ignite config is not a user.
3. Every selected model competes at its level: `cast route`, a fallback and a panel may name it, and no setting keeps a selected model out of them. A model that must not be routed is unselected in step 2. To make a row win its level, run `cast models set HARNESS MODEL --price-override Y` or `--quality-override Y`, with `--level LEVEL` for a model listed at two levels. The shipped model catalog sets no override: each installation names its own favorites, one per level and ranking at most, because several overriding rows in one level fall back to the normal tie-breaks among themselves. An installation that has no file of its own gets one from the first `cast models set` or `cast models remove`, as a copy of the shipped file; `cast models add` does not create it.
4. To take the values rbtv now ships for a model's level, scores, cost, effort count and image flag, run `cast models update --dry-run`, read the cells it lists, then run it without `--dry-run`. `cast models update HARNESS MODEL` does one model. The two overrides and the set of selected models are never changed by it. `cast doctor` says how many cells differ.
5. To choose how `cast route` ranks when a call gives no `--optimize`, and whether a launch falls back, run `cast models defaults --route price|quality --fallback off|price|quality`. `cast models defaults` alone shows both. [cast](../cast.md#fallback) states what a fallback does; read it before turning one on.
6. Run `cast models list --catalog` and read every row: a file cast cannot read as a table stops every launch in the installation. Then run `cast doctor`; it shows which selected models have the login of their provider on this machine.
7. Commit `.rbtv/config/cast/models.csv` and `.rbtv/config/cast/defaults.json` with the installation. They are the one choice every machine and the daemon read; a change counts from the next launch.

A changed level, score, cost or override changes verdicts of `cast route`. Tell the owner which classes are affected; adding a level to a model is the owner's decision.

## 2. Replace a model that agents use

Do this after the Ignite daemon runs a copy of rbtv that supports the new model; [Changing the supported models](../../../methods/changing-the-supported-models.md), section 5, gives that order. A model the daemon's copy does not support is refused in every daemon turn.

1. Select the new model: `cast models add HARNESS MODEL`.
2. Switch each agent that used the old model: `rbtv agent configure AGENT --model M`, then `cast --agent AGENT -p ok --dry-run`, which must exit 0 and name the new model.
3. Run `cast models remove HARNESS MODEL --dry-run` for the old model: it is refused and names each remaining user until none is left. A legacy `dreamer` section in `.rbtv/config/ignite/config.json` does not refuse the remove. Then run it without `--dry-run`, and commit the installation's changed files.

A change to an agent in use waits for the owner's instruction.

## 3. A file that still has a `use` column

The model catalog has no `use` column and no `L4` level. cast refuses an installation's file whose header names `use`, as it refuses any unknown column, and no model launches there until the file is corrected: `cannot read the model catalog <file> line 1: unknown column 'use'`. A file written by a copy of cast that had the column is in that state.

1. Read the rows whose `use` cell is `off` or `panel`. Once the column is gone every remaining row is eligible for `cast route`, for a fallback and for a panel. Delete the line of each model that must stay out of them; nothing else keeps a selected model out.
2. Delete `use` from the header and the `use` cell from every row, so that each line has one cell fewer. This is an edit by hand: `cast models` cannot read the file until it is done.
3. Run `cast models list --catalog`, then `cast models update --dry-run` and `cast models update`: a row still at `L4`, a cost of `999` and the zero scores of an image model take the values rbtv ships. A row whose model cast no longer supports is listed with `launchable` `no`; remove it with `cast models remove HARNESS MODEL`. A model the file lists at two levels where rbtv ships one is named under `not compared`; delete the line of the level you no longer want.
4. Run the `cast route` command of each class once and read which model now wins: the rows that were `off` now compete.

Do this before the Ignite daemon is redeployed with a copy of cast that has no `use` column. A deployed copy that still has the column reads a file without it, and treats every row as routed; a copy without the column refuses a file that still has it.
