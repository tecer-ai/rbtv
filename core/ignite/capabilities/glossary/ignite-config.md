# `ignite/config.json`

`.rbtv/config/ignite/config.json` configures Ignite for one installation on the machine running its agents. It identifies the Slack workspace, channel-to-agent connections, direct-message agent and commands Ignite uses. Keep it machine-local so two machines do not answer the same route.

Write the initial configuration using the [configuration schema](../../../rbtv/capabilities/templates/ignite-config.schema.json) as the field reference. Ignite’s [config.js](../tools/ignite/config.js) validates the record directly; it does not load that schema. Use values selected for this installation, not examples copied from another user. Agent harness, model and effort choices belong in the [Agent record](../../../rbtv/capabilities/glossary/agent-json.md); `dreamer.model` configures consolidation separately. It is required while `dreamer.enabled` is true: Ignite holds no model of its own at run time, and the loader refuses an enabled Dreamer without one.

Store environment-variable names for tokens, never token values. Follow [Installation environment file](../../../rbtv/capabilities/glossary/environment-file.md) for loading behavior and nonsecret verification. Agents consume the resulting capabilities; this record is not their prompt.

Use `ignite connect` and `ignite disconnect` to change connections; they update configuration as well as the managed agent setup. Use `ignite dreamer enable` and `ignite dreamer disable` to turn the nightly consolidation on and off for the whole installation; `enable` records `dreamer.model` when it is absent. Change the Dreamer's model by editing `dreamer.model`. Follow the [operator runbook](../runbook.md) for connection, deployment and Dreamer operation. A configuration edit does not prove a running service has used it.

Verify the record through `loadConfig` in an isolated installation, then exercise the operation consuming the changed setting. Include a rejected field or missing required value and confirm that the error identifies the field without printing a credential. Do not connect a live account just to test the record’s shape.
