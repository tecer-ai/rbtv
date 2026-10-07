# Selected model

A selected model is a [supported model](supported-model.md) that one installation chose to launch: a model with a row in that installation's [model catalog](model-catalog.md). While an installation has no model catalog of its own, every supported model is selected.

Selection gates every launch in the installation. `cast <harness> <model>`, `cast --agent`, an Ignite turn and `cast api` refuse a model that is not selected, and the refusal names `cast models add HARNESS MODEL`. `rbtv agent add` and `rbtv agent configure` check an agent's model the same way. `cast route` names only selected models, and among them only rows whose `use` is `route`.

Selected does not mean usable now. A selected model also needs the login of its provider on the machine; `cast doctor` shows, for each selected model, whether that login is present.

Write "selected model" in full. rbtv's "saved selection" is a different thing: the files and packs an installation or an agent has chosen to install.

`cast models list` prints the selected models of the installation that holds the current folder, each with what every effort number means on it. Change the selection only with `cast models add` and `cast models remove`; [Personalizing the model catalog](../tools/cast/documentation/personalizing-the-model-catalog.md) gives the order to follow when agents or the daemon use the model.
