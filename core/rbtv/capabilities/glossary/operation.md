# Operation

An operation is one named exchange of a [port](port.md), written `<noun>.<verb>` in lower-case kebab-case: `message.send`, `message.receive`, `approval.secure`, `payment.send`, `agent.run`. A [connector](connector.md)'s record lists the operations it delivers under `provides`, a component lists those it requires under `needs`, and the installer matches a need to a provider by operation name, never by connector name; [Component record](component-json.md) states the fields.

The noun is the one the port's [port command](port-command.md) acts on, not the port's name: the `messaging` port's operations are `message.*` and `group.*`, the `payments` port's are `payment.*`. Types alone cannot say what a connector can do, so a need names the operation: a payment requires `approval.secure`, which WhatsApp cannot deliver, and refuses WhatsApp with no special case.

A port's contract page names its operations and says which are optional; [Messaging contract](../../../../connectors/messaging/capabilities/methods/messaging-contract.md) is the one written. Where a port has no contract page, the operations are the ones its connectors' records declare, each naming an exchange the connector's command or adapter performs today; declare nothing speculative, and give the contract page the names when it is written.

An operation is not a command verb. `asaas pay pix KEY AMOUNT` is a service's command; `payment.send` is the operation it delivers, which `pay pix` will call through whichever payments connector is installed. One operation may take several of a service's calls (Slack's `postMessage` and `openIm` are both `message.send`), and one service call that no port names (a canvas) is no operation.
