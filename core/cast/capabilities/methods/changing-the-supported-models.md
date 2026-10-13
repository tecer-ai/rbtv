# Changing the supported models

Add, replace, remove or edit a [supported model](../glossary/supported-model.md), so that rbtv's source, its tests, the Ignite daemon and every machine end on the same list. This is a change to rbtv's source, made by editing two tables by hand; no command writes them.

The caller supplies the harness and the model, and which change is wanted: a new model, a new version in place of an old one, a removal, or a different launch fact or routing cell of a model already supported. When the request names a model without its harness, ask before changing anything. When the request is about the models one installation launches, the change is not this one: follow [Personalizing the model catalog](../tools/cast/documentation/personalizing-the-model-catalog.md).

## 1. Establish what exists

The harness's own list is the authority for which models exist and for their exact ids. A release note, an article or the wording of the request is a hint to check, not a fact.

| Harness | Its list | Its effort ladder |
|---|---|---|
| Codex | `codex debug models` | The model's `supported_reasoning_levels` in that list |
| OpenCode | `opencode models <provider> --verbose` | The `variants` keys. The list has named a rung the provider refuses and has left out one it accepts: section 4 launches the lowest and the highest rung before the ladder is final |
| Claude Code | `claude --help` lists the effort words | Whether a model has a dial is measured: launch it at the lowest and at the highest word with `--output-format json`, and compare the thinking tokens the two results report |

A model of a provider that [providers.json](../tools/cast/providers.json) does not hold needs that provider first: follow [Provider](../../../rbtv/capabilities/glossary/provider.md), then return here.

The supported list keeps one row per model line, at a pinned version. Take the version from the harness's list, and never list a moving alias such as a `-latest` name: what it launches changes without a change in rbtv. Before editing, write down per model line the row that survives and the rows that leave.

A model line with no newer version stays supported, also when the rest of its family has moved on. Name each such model in the report of section 6 as a candidate for removal.

## 2. Obtain the owner's rulings

A model's level, its two scores and its removal are the owner's decisions. Prepare them and ask once, before editing:

- **A new model:** propose its level and scores as a tie with the models it stands beside in that level, and say that the proposal has no measurement behind it.
- **A new version:** it takes the old row's level, `reasoning` and `coding`, with its own `cost`. Those scores were given to the earlier version: name the row as carrying unreviewed scores.
- **A removal:** list who launches the model. `cast models remove HARNESS MODEL --dry-run`, run inside an installation, names its agents; the Ignite setting `dreamer.model` and any component setting that names a model are searched by hand.

Do not present a score as a benchmark result. A score is the owner's placement of one model beside the others of its level. An image model has no level and no score.

Read the cost on the provider's own pricing page, under the rules of [Sources of the shipped scores and costs](changing-the-supported-models/score-and-cost-sources.md).

## 3. Edit the two tables

1. Run the suites before editing and keep the result: `node core/cast/capabilities/tools/cast/test_cast.js`, `node core/cast/capabilities/tools/cast/test_route.js`, the spark suite and the Ignite suites.
2. Edit [supported-models.js](../tools/cast/supported-models.js) (harness, short name, the harness's id, effort ladder, provider) and the shipped [models.csv](../tools/cast/models.csv) in the same change. [Model catalog](../glossary/model-catalog.md) states what each column of the second holds. The two agree on harness and model. When the evidence for a ladder is a measurement, record it in the comment at the head of `supported-models.js`, where the other ladders have theirs.
3. In `test_route.js`, the check of the shipped table lists the approved level and scores of every model. Change that list to what the owner ruled in section 2, in the same change.
4. When the model that leaves is the Dreamer's default, `DREAMER_MODEL` in `core/ignite/capabilities/tools/ignite/config.js`, change that line to a supported model the owner names. It is the one setting in rbtv's source that names a model.
5. Record each new or changed cost, and each score that has no measurement, in [Sources of the shipped scores and costs](changing-the-supported-models/score-and-cost-sources.md).
6. Run the same suites again. Three failures have a fixed meaning:

| Failure | What to do |
|---|---|
| The shipped table's check fails on structure | Correct the row it names: one row per supported model, every cell a value of its column, both override cells blank, no level or score on an image model, every level still holding a model |
| `no supported model is <property>: the arm that asked has lost its subject` | The model that left was the only one with that property, and a test depended on it. Decide with the owner whether cast still handles that property. When it does not, remove the test and the code only that test reached |
| `test_route.js` lists lines that name a supported model | A test asks `example-models.js` for a model by a property, help text takes its example from the table, and a document writes `HARNESS MODEL`. Replace the name the way the file's neighbours do |

No other file changes for an added or a replaced model. A test never names a supported model: it asks [example-models.js](../tools/cast/example-models.js) for one by a property, and a property a test needs is stated in its failure.

## 4. Launch each new model

Launch each new model once, for real, at effort 1 with a one-line task, and read the reply; for an OpenCode model, launch its highest rung too. A dry run proves the arguments, not that the harness accepts the id. A harness too old for a model can answer with an error about the account: upgrade the harness before concluding that the login is at fault.

A launch spends the provider's plan and needs the provider's login on the machine. Launch when the task authorizes launches; otherwise report the launch as not done.

## 5. Bring a live installation and a second machine to the change

The Ignite daemon runs its own deployed copy of rbtv, with its own supported models. The commands on `PATH` run the working copy. A model the working copy supports and the deployed copy does not is refused in every daemon turn. Keep this order:

1. Commit the rbtv change.
2. Redeploy the daemon at that commit: [Ignite runbook](../../../ignite/capabilities/tools/ignite/documentation/runbook.md), Deploy.
3. In the installation, select each new model, switch each agent and setting that named an old model, then unselect the old model: [Personalizing the model catalog](../tools/cast/documentation/personalizing-the-model-catalog.md), sections 1 and 2.
4. On each other machine, pull the rbtv repository and the installation together; one without the other leaves agents naming a model the local cast does not support. Compare the harness versions with the first machine's. Then repeat there the suites of section 3 and the launch of section 4.

Switching an agent before the redeploy breaks it in the daemon. Removing a supported model from the working copy before its agents are switched leaves `rbtv agent configure` unable to set them back.

A push, a daemon restart, a change to an agent in use and a harness upgrade each wait for the owner's instruction.

## 6. Report

Report to the owner: the rows added, replaced and removed; each row that carries unreviewed scores; each cost with its conditions and any end date; each model that stays although its family has moved on; each launch done or not done, and on which machine; and each step of section 5 that still waits for the owner's instruction.
