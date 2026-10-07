# Supported model

A supported model is a model this copy of cast can launch: a row of `core/cast/capabilities/tools/cast/supported-models.js`, which holds its harness, its short name, the id the harness knows it by, its effort ladder and its [provider](../../../rbtv/capabilities/glossary/provider.md).

Supported is a fact about the rbtv source, the same for every installation that runs that copy. Whether an installation launches the model is a separate fact: it must also be a [selected model](selected-model.md) there. The routing columns of a model (level, scores, cost) are not part of this file; they are in the [model catalog](model-catalog.md).

Two copies of rbtv on one machine can support different models. The Ignite daemon runs its own deployed copy, so a model added to the working copy is supported for a terminal launch before it is supported for a daemon turn.

`cast models list --supported` prints every supported model with `selected` yes or no for the installation of the current folder. A launch that names any other model is refused with the closest supported name. To add, replace or remove a supported model, follow [Personalizing the model catalog](../personalizing-the-model-catalog.md); it is a change to rbtv's source, with its tests.
