# `ignite/config.json`

`.rbtv/config/ignite/config.json` configures Ignite for one installation on the machine running its agents. It identifies the Slack workspace, channel-to-agent connections, direct-message agent and commands Ignite uses. Keep it machine-local so two machines do not answer the same route.

The installation names the agent for a live owner-message test in `.rbtv/config/ignite/test-agent.md`. [Testing an owner message](../methods/testing-an-owner-message.md) states the lines.

Write the initial configuration using the [configuration schema](../../../rbtv/capabilities/templates/ignite-config.schema.json) as the field reference. Ignite’s [config.js](../tools/ignite/config.js) validates the record directly; it does not load that schema. Use values selected for this installation, not examples copied from another user. Agent harness, model and effort choices belong in the [Agent record](../../../rbtv/capabilities/glossary/agent-json.md). A leftover `dreamer` section is not a setting: the loader ignores it, and the next write omits it. No verb answers to that name.

An optional `payments` section turns the [payment gate](payment-gate.md)'s service side on, with the withdrawal validation's port, the payments connectors Ignite sends through (`payments.connectors`; `payments.providers` is its older spelling, accepted until the next deploy), and the time zone and currency of the limits; the gate's mode, limits and PIN are set by the owner in `/payments`, never in this file.

An optional `listeners` section names the owner allowlist for WhatsApp and Gmail. Each adapter stays off until `owner` is set. WhatsApp also needs `account` (the linked number) and `secretEnv` (the variable in the env file that holds the HMAC secret). It listens on `127.0.0.1` and `port` (8791 when absent). Ignite starts and stops `whatsapp sync` on the installation store; do not start a second sync, and do not put the secret on a command line. Gmail also needs `account` (the `google --account` name), `mailbox` (the address Gmail's profile must return) and `agent` (the mail default). `pollMs` is the poll cadence in milliseconds; absent, Gmail is not polled and no timer is started. Do not guess an address or a cadence.

Store environment-variable names for tokens, never token values. Follow [Installation environment file](../../../rbtv/capabilities/glossary/environment-file.md) for loading behavior and nonsecret verification. Agents consume the resulting capabilities; this record is not their prompt.

Use `ignite connect` and `ignite disconnect` to change connections; they update configuration as well as the managed agent setup. Follow the [operator runbook](../tools/ignite/documentation/runbook.md) for connection and deployment. A configuration edit does not prove a running service has used it. Albert's schedules are the consolidation controls.

Verify the record through `loadConfig` in an isolated installation, then exercise the operation consuming the changed setting. Include a rejected field or missing required value and confirm that the error identifies the field without printing a credential. Do not connect a live account just to test the record’s shape.
