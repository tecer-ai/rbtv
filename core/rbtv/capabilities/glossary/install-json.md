# `install.json`

The record of the installation root: the file in [`.rbtv/config/`](config.md) that contains the root's chosen units and packs, the harnesses that receive its files, and the record of the files the [`rbtv` CLI](rbtv-cli.md) generated for it. The root is an [rbtv agent](agent.md#rbtv-agent) with no `agent.md` and no stored harness, model or effort: the person chooses them when they open it. Its fields are defined by its [schema](../templates/install-json.schema.json), and they are the same as an agent's [`agent.json`](agent-json.md) except that it has no `name`, `description`, `harness`, `model`, `effort` or `voice`. It has `harnesses`, a list, instead.

Who writes which field: `rbtv configure` creates the file and writes `harnesses`; `rbtv add` and `rbtv remove` change its `files` and `packs`; rbtv writes the record of generated files. A person may also edit it by hand; a hand edit is applied by `rbtv update all`.

The file contains nothing tied to one machine: no absolute path and no timestamp. It is not shared through git. It stays on each machine, and a machine that has the root's units runs `rbtv update all` to make its folder match.

The file also books ownership of shared-file keys and sections; per-unit generated files carry `rbtv-managed`, guidance copies carry a generated banner, and PATH shortcuts have a separate [`~/.rbtv/path-owners.json`](path-owners-json.md) record. CLIs read the record; the `rbtv` CLI reads it to update or remove what it generated.
