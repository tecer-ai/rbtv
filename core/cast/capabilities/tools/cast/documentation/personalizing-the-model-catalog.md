# Personalizing the model catalog

Change which models an installation launches and how `cast route` ranks them, or change which models cast supports, so that every session, the Ignite daemon and every machine end on the same list. Read [Model catalog](../../../glossary/model-catalog.md) first for what a row and each column mean; this page gives the work.

The caller supplies the harness and model names, and which of two changes is wanted:

- A change for one installation: select or unselect a [supported model](../../../glossary/supported-model.md), or change a row's overrides, the installation's defaults, or take rbtv's current values. It touches one file of the installation. Sections 1 and 5 apply, and section 7 when cast refuses the file for a `use` column.
- A change to what cast supports: a new model, a new version replacing an old one, or a removal. It is a change to rbtv's source. Sections 2 to 6 apply, then section 1 in each installation.

When the request does not say which, or names a model without its harness, ask before changing anything.

## 1. Choose models for this installation

Run every command from a folder inside the installation; `cast models` acts on the installation that holds the current folder and names it in every result.

1. List what can be chosen and what is chosen: `cast models list --supported`.
2. Select a model with `cast models add HARNESS MODEL`. Unselect one with `cast models remove HARNESS MODEL`. Run either with `--dry-run` first and read what would change. `remove` is refused while an agent under `.rbtv/agents/` or the Dreamer still launches the model, and lists them: give each another model with `rbtv agent configure AGENT --model M` first. `--force` removes the model anyway and leaves those agents refused at launch. `remove` does not see agents kept outside `.rbtv/agents/` or a component's settings that name a model; the result says so, and you check those yourself.
3. Every selected model competes at its level: `cast route`, a fallback and a panel may name it, and no setting keeps a selected model out of them. A model that must not be routed is unselected in step 2. To make a row win its level, run `cast models set HARNESS MODEL --price-override Y` or `--quality-override Y`, with `--level LEVEL` for a model listed at two levels. The shipped model catalog sets no override: each installation names its own favorites, one per level and ranking at most, because several overriding rows in one level fall back to the normal tie-breaks among themselves. An installation that has no file of its own gets one from the first `cast models set` or `cast models remove`, as a copy of the shipped file; `cast models add` does not create it.
4. To take the values rbtv now ships for a model's level, scores, cost, effort count and image flag, run `cast models update --dry-run`, read the cells it lists, then run it without `--dry-run`. `cast models update HARNESS MODEL` does one model. The two overrides and the set of selected models are never changed by it. `cast doctor` says how many cells differ.
5. To choose how `cast route` ranks when a call gives no `--optimize`, and whether a launch falls back, run `cast models defaults --route price|quality --fallback off|price|quality`. `cast models defaults` alone shows both. [cast](../cast.md#fallback) states what a fallback does; read it before turning one on.
6. Run `cast models list --catalog` and read every row: a file cast cannot read as a table stops every launch in the installation. Then run `cast doctor`; it shows which selected models have the login of their provider on this machine.
7. Commit `.rbtv/config/cast/models.csv` and `.rbtv/config/cast/defaults.json` with the installation. They are the one choice every machine and the daemon read; a change counts from the next launch.

A changed level, score, cost or override changes verdicts of `cast route`. Tell the owner which classes are affected; adding a level to a model is the owner's decision.

## 2. Establish what "latest" means

The harness's own list is the authority for which models exist, their exact ids and their effort ladders. A release note, an article or the wording of the request is a hint to check, not a fact.

- Codex: `codex debug models`.
- OpenCode: `opencode models <provider> --verbose`; the ladder is the `variants` keys. That list has named a rung the provider refuses and has left out one it accepts, so launch the lowest and the highest rung once each before entering the ladder.
- Claude Code: `claude --help` lists the effort words. Whether a model has a dial is measured: launch it once at the lowest and once at the highest word with `--output-format json`, and compare the thinking tokens the two results report.

The [model catalog](../../../glossary/model-catalog.md) keeps one row per model line, at a pinned version; take the version from the harness's list, and never list a moving alias such as a `-latest` name. A model line with no newer version stays as it is. Write down, per model line, the row that survives and the rows that leave, before editing.

## 3. Scores and costs

### Scores

A new version takes the old row's `level`, `reasoning` and `coding`, and in an installation's file its overrides, with its own `cost`. Those scores were given to the earlier version, so name every such row in your report to the owner as carrying unreviewed scores. Do not invent new scores, and do not present a score as a benchmark result: a score is a relative calibration among the rows of the table, the owner's placement of one model beside the others.

These shipped scores were set on 2026-10-10 as provisional calibration, with no matched measurement behind them:

| Model | reasoning / coding | What supports it |
|---|---|---|
| `fugu-ultra` | 6 / 6 | The abstract of its paper, <https://huggingface.co/papers/2606.21228>, supports high capability. It gives no comparison with the other `L1` models. |
| `gemini-3.1-pro-preview` | 4 / 3 | The GLM-5.2 model card, <https://huggingface.co/zai-org/GLM-5.2>, reports Gemini's reasoning sometimes above GLM-5.2 and its coding below. That is indirect: it is not an assessment against `glm-5.3`. |
| `sakana-namazu` | 4 / 4 | No comparison was found. |
| `haiku-5-5` | 3 / 3 | No comparison was found. |
| `gemini-3.8-flash` | 3 / 3 | Taken from `gemini-3.7-flash`, the version it replaced. |

An image model has no score: its `level`, `reasoning` and `coding` cells stay blank.

### Costs

`cost` is the provider's standard API list price for output tokens, in US dollars per million tokens. Keep each cell by these rules:

1. Read the price on the provider's own pricing page, and record the page, the date read and every condition on the price in the table below, in the same change as the cell.
2. Never enter what a subscription or a coding plan makes the model cost, and never a placeholder: a cost that is not known stays blank, which keeps the row out of price rankings, as does the cost of an image model, which is not priced per text token.
3. Where the price rises with the size of the request, the cell holds the base rate, and the table records the higher rate and where it starts.
4. A promotional price is entered while it runs, with its end date in the table. Change the cell when that date passes.
5. A price published for a named version applies to a row only when the harness's id is that version. Where the id is an alias or carries no version, enter the price and record the link as not confirmed.
6. Review a cell when its model is replaced, when an end date in the table passes, and when the owner asks.

| Model | `cost` | Conditions | Source, read 2026-10-10 |
|---|---|---|---|
| `haiku-5-5` | 0.50 | Up to 100,000 input tokens; 2.50 above. | <https://www.anthropic.com/claude/haiku> |
| `gemini-3.8-flash` | 3.75 | Introductory price through 2026-12-31; 7.50 from 2027-01-01. | <https://ai.google.dev/gemini-api/docs/pricing>; OpenCode's model list gives 3.75 for `google/gemini-3.8-flash`. |
| `gemini-3.1-pro-preview` | 12 | Up to 200,000 input tokens; 18 above. | <https://ai.google.dev/gemini-api/docs/pricing>; OpenCode's model list gives 12, and 18 above 200,000, for `google/gemini-3.1-pro-preview`. |
| `fugu-ultra` | 30 | Up to 272,000 input tokens; 45 above. Orchestration is billed in addition. | <https://console.sakana.ai/pricing>, which prices Fugu Ultra v2.0. The harness id `sakana/fugu-ultra` is an alias; OpenCode's model list gives it and `sakana/fugu-ultra-20260615` the same 30 and 45. That the alias is v2.0 is not confirmed. |
| `sakana-namazu` | 4 | None. | <https://console.sakana.ai/pricing>, which prices Namazu v1.0. The harness id `sakana/sakana-namazu` carries no version, so the link is not confirmed; OpenCode's model list gives 4 for it. |

The costs of the other rows were entered before this table was kept and have no recorded source; add a row here when one of them is next read.

## 4. Support a new model in rbtv

1. Run the suites before editing and keep the result: `node core/cast/capabilities/tools/cast/test_cast.js`, `node core/cast/capabilities/tools/cast/test_route.js`, the spark suite and the Ignite suites.
2. Edit `supported-models.js` (harness, short name, the harness's id, effort ladder, provider) and the shipped `models.csv` in the same change. The two agree on harness and model: `test_route.js` fails when a supported model has no shipped row or a shipped row has no supported model. A provider named by a new row must already be in `providers.json`.
3. Search the repository for every old name the change removes: tests that use the model as their example, help text, documents, and settings that hold a model. A test whose subject was a removed model (the only model with a four-rung ladder, or with no effort dial) moves to another model with the same property.
4. Run the same suites again. `test_route.js` checks verdicts against a table the suite writes for itself. One check reads the shipped file: it holds exactly one row per supported model, every cell holds a value of its column, both override cells are blank, an image model has no level and no score, every level still has a model, and the level and the two scores of every model are the ones that check lists. When it fails on structure, correct the shipped row it names; when it fails on a level or a score the owner has approved, change the list in that check in the same change. A changed cost fails nothing.
5. Record each new or changed cost and each score without a measurement in section 3.
6. Launch each new model once, for real, at effort 1 with a one-line task, and read the reply. A dry run proves the arguments, not that the harness accepts the id. A launch spends the provider's plan: do it when the task authorizes launches, and otherwise report the launch as not done.

## 5. Order on a live installation

The Ignite daemon runs its own deployed copy of rbtv, with its own supported models. The commands on `PATH` run the working copy. A model the working copy supports and the deployed copy does not is refused in every daemon turn. Keep this order:

1. Commit the rbtv change.
2. Redeploy the daemon at that commit: [Ignite runbook](../../../../../ignite/capabilities/tools/ignite/documentation/runbook.md), Deploy.
3. In the installation: `cast models add` for a new model.
4. Switch each agent that used an old model: `rbtv agent configure AGENT --model M`, then `cast --agent AGENT -p ok --dry-run`, which must exit 0 and name the new model. If `dreamer.model` in `.rbtv/config/ignite/config.json` names the old model, change it to the new one by editing that file, as [Ignite configuration](../../../../../ignite/capabilities/glossary/ignite-config.md) says; while the Dreamer is on and names the old model, the `remove` of step 5 is refused. `cast models remove HARNESS MODEL --dry-run` is refused and names each remaining user until none is left.
5. `cast models remove` for the old model, then commit the installation's changed files.

Switching an agent before the redeploy breaks it in the daemon. Removing a supported model from the working copy before its agents are switched leaves `rbtv agent configure` unable to set them back. A push, a daemon restart, a change to an agent in use and a harness upgrade each wait for the owner's instruction.

## 6. The second machine

1. Pull the rbtv repository and the installation together. One without the other leaves agents naming a model the local cast does not support, or a model catalog row the local cast cannot launch.
2. Compare the harness versions with the first machine's. A harness too old for a model can answer with an error about the account instead of the model; upgrade the harness before concluding the login is at fault.
3. Repeat there: `cast models list --catalog`, the suites of section 4, `cast doctor`, the dry run of each switched agent, and the one real launch per new model.

## 7. A file that still has a `use` column

The model catalog has no `use` column and no `L4` level. cast refuses an installation's file whose header names `use`, as it refuses any unknown column, and no model launches there until the file is corrected: `cannot read the model catalog <file> line 1: unknown column 'use'`. A file written by a copy of cast that had the column is in that state.

1. Read the rows whose `use` cell is `off` or `panel`. Once the column is gone every remaining row is eligible for `cast route`, for a fallback and for a panel. Delete the line of each model that must stay out of them; nothing else keeps a selected model out.
2. Delete `use` from the header and the `use` cell from every row, so that each line has one cell fewer. This is an edit by hand: `cast models` cannot read the file until it is done.
3. Run `cast models list --catalog`, then `cast models update --dry-run` and `cast models update`: a row still at `L4`, a cost of `999` and the zero scores of an image model take the values rbtv ships. A row whose model cast no longer supports is listed with `launchable` `no`; remove it with `cast models remove HARNESS MODEL`. A model the file lists at two levels where rbtv ships one is named under `not compared`; delete the line of the level you no longer want.
4. Run the `cast route` command of each class once and read which model now wins: the rows that were `off` now compete.

Do this before the Ignite daemon is redeployed with a copy of cast that has no `use` column. A deployed copy that still has the column reads a file without it, and treats every row as routed; a copy without the column refuses a file that still has it.
