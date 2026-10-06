# `agent.json`

The record of an [rbtv agent](agent.md#rbtv-agent), in its folder beside `agent.md`. It holds the agent's description, its harness, model, effort and voice, the units and [packs](pack.md) chosen for it, and the record of the files the [`rbtv` CLI](rbtv-cli.md) generated for it. Its fields are defined by its [schema](../templates/agent-json.schema.json). CLIs read it, and the agent's own commands read it too; the agent's prompt does not depend on it.

Who writes which field:

- The author writes `name`, `description`, `harness`, `model` and `effort`, and may write [`files`](rbtv-cli.md) and `packs` by hand. `name` must equal the folder name and the `name` in `agent.md`; rbtv checks the three before every change and refuses a disagreement. `harness`, `model` and `effort` are checked against `cast list`. `effort` is stored as the model's own word.
- `rbtv agent configure` is the only command that changes `harness`, `model` and `effort` after the first time, and it writes `voice`. `voice` is optional and is not checked.
- `rbtv agent add` and `remove` change `files` and `packs`; `rbtv` writes the record of generated files. A hand-written file needs only the author's fields; rbtv adds the record at the first `rbtv agent add`.

`files` lists the [files](rbtv-cli.md) chosen on their own, as full ids `<module>/<component>#<name>`. rbtv saves the full id even when the author wrote a short name that is unique in the catalog. The record of generated files lists what rbtv wrote for the agent, so that `rbtv agent update` can rebuild or remove it on any machine.

```json
{
  "name": "researcher",
  "description": "Investigates a defined question and reports evidence.",
  "harness": "claude",
  "model": "sonnet-5-5",
  "effort": "medium",
  "files": ["meta/functions#investignosis"],
  "packs": ["ignite"]
}
```

The file is shared through git, so it contains nothing tied to one machine: no absolute path and no timestamp. The agent's harness sessions, its Slack connection and the files themselves are not in it. The Slack connection is recorded in the machine's [Ignite configuration](ignite-config.md).

The root of an installation has no `agent.json`: its record is [`install.json`](install-json.md).
