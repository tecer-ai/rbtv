# `agent.json`

`agent.json` is an agent’s setup record beside `prompt.md`. rbtv reads its selections to generate the agent’s files; launchers read its installed launch settings. The record is the one home of the agent's name, which equals the folder name. The prompt’s instructions belong in `prompt.md`.

Use the [schema](../templates/agent-json.schema.json) for fields. Before creating the record or changing its description or selections, follow [Agent](agent.md) for the prompt-first writing order, matching names and placement. A component’s shipped record has no harness, model or effort; the person installing it chooses all three.

In an installation, rbtv adds the launch settings and generated-file record. Change launch settings through [rbtv CLI](rbtv-cli.md), which checks that the model is one of the installation's [selected models](../../../cast/capabilities/glossary/selected-model.md) and that the model accepts the effort, and regenerates affected files. Keep those settings here rather than repeating them in the prompt or another file.

The author may write file and [pack](pack.md) selections; rbtv also changes them through its add and remove operations. File selections use full `module/component#name` identifiers. Apply a hand-edited selection with the refresh specified by rbtv CLI, then check the generated files against it.

Keep machine-specific paths, timestamps and accounts out of the record so another machine can rebuild the agent from it. Harness sessions and live data stay outside it; a Slack connection belongs in [Ignite configuration](../../../ignite/capabilities/glossary/ignite-config.md). The installation root instead uses [install.json](install-json.md).

The author-written record starts with this layout. Include selection lists only when needed; the schema owns their fields and types.

```json
{
  "name": "<folder name>",
  "description": "<description written using Agent>"
}
```
