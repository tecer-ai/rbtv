# Adapter

An adapter is the half of a [connector](connector.md) that Ignite loads in its own process: a Node module under the connector's `capabilities/tools/<name>/lib/`, exporting the shape its [port](port.md) names, which translates the [service](service.md) into the port's [operations](operation.md). Ignite loads it by the connector's name and never names a field of the service; the connector's command, in any language, is the other half and knows nothing of Ignite.

Two exist. `connectors/asaas/capabilities/tools/asaas/lib/withdrawal-validation.js` is the payments adapter for the [payment gate](../../../ignite/capabilities/glossary/payment-gate.md)'s withdrawal validation: it exports `path` (where the bank calls), `header` and `tokenEnv` (the token's header and variable) and `read(body)` (the bank's body as an operation the gate can check); Ignite's `payment-webhook.js` loads it with `loadProvider(name)` and refuses a module of another shape. `connectors/slack/capabilities/tools/slack/lib/live-status.js` is the Slack side of live status: the emoji for each state, their order rules and the legend, pure logic handed the reaction functions by Ignite's `status-ticker.js`.

An adapter is a Node module because Ignite is a daemon that reacts to events, polls and ticks status; starting a command per call is not viable there. The consequence is that a connector may hold two implementations of one service call, one in its command (Asaas: Python) and one in its adapter (Node); the two are kept in agreement by testing both against the same fixtures, not by sharing code.

## Write one

1. Take the shape from the port: the exported names and what each returns are stated by the page that loads it (the payment gate for withdrawal validation; the [messaging contract](../../../../connectors/messaging/capabilities/methods/messaging-contract.md) for a messaging adapter's inbound event and sends). Export exactly those names; the loader refuses another shape.
2. Make the module pure where it can be: translate shapes, map names, read a body. What must call the service receives Ignite's functions or clock as arguments, as `live-status.js` receives `addReaction` and `removeReaction`, so Ignite's tests run the adapter with a stand-in.
3. Read a token by its variable name only, from the process environment and then the installation's [environment file](environment-file.md); never print it and never log a payload that may hold one.
4. Test it from Ignite's suite, the one that loads it ([Testing Ignite](../../../ignite/capabilities/methods/testing-ignite.md)): the asaas adapter's tests are in `test_payments.js`, the Slack live status in `test_live_status.js`.

The shape check of [Building a connector](../methods/building-a-connector.md) confirms the exports from the command line.
