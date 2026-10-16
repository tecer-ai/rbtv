# Port

A port is a family of [operations](operation.md) the inside of rbtv states it needs from outside [services](service.md), named as a type: `messaging`, `payments`, `media`, `calendar`, `storage`, `judgment`. Each [connector](connector.md) delivers some of a port's operations through its own service; the inside of rbtv (Ignite, the [port command](port-command.md), an agent's prompt) names the port and the operation, never the service, so a service can be swapped or a second one added without the inside changing.

A connector's record names the port it is listed under as `type` and the other ports it covers as `serves`; [Component record](component-json.md) states the fields. Declare a port only where there is a real exchange or install today: a type with no connector performing one of its operations is a word, not a port.

## What a port has

| Part | Where | Today |
|---|---|---|
| A contract: its operations, each required or optional, the shape of its inbound events and what its adapter exports | A capability page in the port's component, `connectors/<port>/` | [Messaging contract](../../../../connectors/messaging/capabilities/methods/messaging-contract.md). Payments has no contract page; its operations are the ones `connectors/asaas` declares and the [payment gate](../../../ignite/capabilities/glossary/payment-gate.md) governs |
| A port command, which agents call and which picks the connector | The same component | `cast` is the port command of `agent.run`; `message` (`connectors/messaging`) and `pay` (`connectors/payments`) are the port commands of messaging and payments, built in phase 2 of the connector architecture. `asaas pay pix\|qr\|bill\|recharge` still call the gate themselves until the hand-over ends (the R$1 test through `pay`, Sara's tool switched) |
| A [listener](../../../ignite/capabilities/glossary/listener.md), the inbound side, when Ignite consumes the port | Ignite | Ignite listens to Slack through its own client |

Policy lives in the port layer, in the port command: the payment gate for money, the recipient's permission for an outgoing message. A connector executes what the port layer allowed.

A port is not a module and not a component: the `connectors` module holds the connectors of every port, and one component per port holds that port's contract and command.
