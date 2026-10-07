# Personalizing the model catalog

Change which models an installation launches and how `cast route` ranks them, or change which models cast supports, so that every session, the Ignite daemon and every machine end on the same list. Read [Model catalog](../../../glossary/model-catalog.md) first for what a row and each column mean; this page gives the work.

The caller supplies the harness and model names, and which of two changes is wanted:

- A change for one installation: select or unselect a [supported model](../../../glossary/supported-model.md), or edit a row's routing columns. It touches one file of the installation. Sections 1 and 5 apply.
- A change to what cast supports: a new model, a new version replacing an old one, or a removal. It is a change to rbtv's source. Sections 2 to 6 apply, then section 1 in each installation.

When the request does not say which, or names a model without its harness, ask before changing anything.

## 1. Choose models for this installation

Run every command from a folder inside the installation; `cast models` acts on the installation that holds the current folder and names it in every result.

1. List what can be chosen and what is chosen: `cast models list --supported`.
2. Select a model with `cast models add HARNESS MODEL`. Unselect one with `cast models remove HARNESS MODEL`. Run either with `--dry-run` first and read what would change. `remove` is refused while an agent under `.rbtv/agents/` or the Dreamer still launches the model, and lists them: give each another model with `rbtv agent configure AGENT --model M` first. `--force` removes the model anyway and leaves those agents refused at launch. `remove` does not see agents kept outside `.rbtv/agents/` or a component's settings that name a model; the result says so, and you check those yourself.
3. To keep a model launchable by name and out of routing, leave its row and set `use` to `off`. To change how a model ranks, edit `level`, `reasoning`, `coding`, `cost`, `use` or an override cell of its row by hand in `.rbtv/config/cast/models.csv`. An installation that has no such file yet gets one in one of two ways. The first `cast models remove` creates it from the shipped file, without the rows of the removed model. To get an editable file without removing a model, copy the shipped file, which `cast models list --catalog` names, to `.rbtv/config/cast/models.csv`. `cast models add` does not create the file.
4. Run `cast models list --catalog` and read every row: a file cast cannot read as a table stops every launch in the installation. Then run `cast doctor`; it shows which selected models have the login of their provider on this machine.
5. Commit `.rbtv/config/cast/models.csv` with the installation. The file is the one choice every machine and the daemon read; a change counts from the next launch.

A changed level, score, cost or override changes verdicts of `cast route`. Tell the owner which classes are affected; adding a level to a model is the owner's decision.

## 2. Establish what "latest" means

The harness's own list is the authority for which models exist, their exact ids and their effort ladders. A release note, an article or the wording of the request is a hint to check, not a fact.

- Codex: `codex debug models`.
- OpenCode: `opencode models <provider> --verbose`; the ladder is the `variants` keys.

The [model catalog](../../../glossary/model-catalog.md) keeps one row per model line; take the version from the harness's list. A model line with no newer version stays as it is. Write down, per model line, the row that survives and the rows that leave, before editing.

## 3. Scores when a model replaces another

A new version takes the old row's `level`, `reasoning`, `coding`, overrides and `use`, with its own `cost` at the provider's list price. Those scores were given to the earlier version, so name every such row in your report to the owner as carrying unreviewed scores. Do not invent new scores.

## 4. Support a new model in rbtv

1. Run the suites before editing and keep the result: `node core/cast/capabilities/tools/cast/test_cast.js`, `node core/cast/capabilities/tools/cast/test_route.js`, the spark suite and the Ignite suites.
2. Edit `supported-models.js` (harness, short name, the harness's id, effort ladder, provider) and the shipped `models.csv` in the same change. The two agree on harness and model: `test_route.js` fails when a supported model has no shipped row or a shipped row has no supported model. A provider named by a new row must already be in `providers.json`.
3. Search the repository for every old name the change removes: tests that use the model as their example, help text, documents, and settings that hold a model. A test whose subject was a removed model (the only model with a four-rung ladder, or with no effort dial) moves to another model with the same property.
4. Run the same suites again. `test_route.js` checks verdicts against a table the suite writes for itself, so a changed level, score or cost in the shipped file fails no verdict check. One check reads the shipped file and validates its structure: every row names a supported model, every cell holds a value of its column, no row is repeated and every class still has a model to route to. When that check fails, correct the shipped row it names.
5. Launch each new model once, for real, at effort 1 with a one-line task, and read the reply. A dry run proves the arguments, not that the harness accepts the id. A launch spends the provider's plan: do it when the task authorizes launches, and otherwise report the launch as not done.

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
