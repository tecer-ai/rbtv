# Port command

A port command is the command agents call for a [port](port.md), which picks the [connector](connector.md): `message send --to Pia "…"`, `pay pix …`, `calendar list`. The agent names the [operation](operation.md) and its inputs; the port command holds the port's policy, chooses the connector that provides the operation and hands it the work. Swapping a connector is then invisible to agents.

`cast` is the port command of `agent.run`: it launches an agent on any harness, the harnesses are its adapters and the AI labs are its [providers](provider.md). `message` and `pay` are not built; until `pay` holds the payment gate, `asaas pay` calls the gate itself, and neither path ever exists without the gate.

## What a port command owns

- **Policy.** `pay` owns the [payment gate](../../../ignite/capabilities/glossary/payment-gate.md) call; `message send` checks the recipient's permission before any connector is called. A connector executes what the port command allowed and holds no policy of its own.
- **The choice of connector.** When one installed connector provides the operation, it is used. When more than one can, a person is asked and the agent path passes a flag that names the connector, so no agent path waits on a question ([Agent parity](../principles/agent-parity.md)).
- **Only what every connector of the port can deliver.** A service's own feature stays in the connector's command and is used only when an agent's prompt says so.

A port command lives in the port's component under `connectors/`: `connectors/messaging` holds `message`, `connectors/payments` holds `pay`. Core keeps only the harness connection, `cast`. The command is a [Tool](tool.md), built with [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md); the connectors it calls are built with [Building a connector](../methods/building-a-connector.md).
