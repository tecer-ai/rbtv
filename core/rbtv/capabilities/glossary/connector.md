# Connector

A connector is a component of the `connectors` module that joins rbtv to one outside [service](service.md), such as Slack, Asaas or WhatsApp. It has two parts with separate entry points, both required: a command, which agents run and which knows nothing of Ignite, and an [adapter](adapter.md) per [port](port.md) it serves, a Node module Ignite loads in-process that translates the service into the port's [operations](operation.md). Its record names the port it is listed under and the operations it delivers, so a need stated by operation can be met by any connector that provides it and a second connector can stand beside the first without the inside of rbtv changing.

Use the word for the component. The outside party is the service; the AI lab account whose models a harness runs is a [provider](provider.md), and a page an agent reads is a [capability](capability.md); neither is a connector. The component of a port itself (`connectors/messaging`, which holds the port's contract and its [port command](port-command.md)) is not a connector either: it joins rbtv to no service.

## Parts and record

| Part | Where | What it is for |
|---|---|---|
| Command | `capabilities/tools/<name>/`, as [Tool](tool.md) places it, in any language | Every operation an agent runs on the service, and the service's own features (a Slack canvas, a WhatsApp voice note), which an agent uses only when its prompt says so |
| Adapter | `capabilities/tools/<name>/lib/<port>.js`, one per port in `type` and `serves` | What Ignite needs in its own process, in the shape the port names: the withdrawal validation of a payments connector, the operations of a messaging connector (its inbound events, sends and live status mapping), the operations of any other port |
| Record | `<name>.json` | `type`, `serves`, `provides`, `needs` and the outside software, as [Component record](component-json.md) states |

A connector lives in one place and is named for its service, as [Component](component.md) names a component that wraps one product. One port is its `type`; the other ports it covers are its `serves`. A connector that reaches two ports still carries one command.

Policy is not the connector's: the payment gate decides in Ignite and `pay` will own it, and `message send` checks a recipient's permission before any connector; the connector resolves, asks and executes.

## Build and check

Follow [Building a connector](../methods/building-a-connector.md): the shape, the record, the order of work, the rules for money and for messages, and the mechanical shape check a finished connector passes. Asaas is the reference: `connectors/asaas/capabilities/tools/asaas/asaas.py` is its command and `lib/withdrawal-validation.js` its adapter, loaded by name through Ignite's `payment-webhook.js`.
