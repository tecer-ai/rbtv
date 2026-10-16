# Service

A service is the outside party a [connector](connector.md) joins rbtv to: Slack, WhatsApp, Google Workspace, ElevenLabs, TypeSafe, Asaas. It holds the account, the data, the rate limits and the shapes of its own API; rbtv reaches it only through its connector.

Name the service when the question is which outside system acts, holds the account or sets the limits. Name the connector when the question is which component, command or adapter does the work. Name the [port](port.md) when the question is what rbtv needs, whichever service answers. An AI lab account whose models a harness runs is a [provider](provider.md), not a service, even when the same company offers both; a service that answers a model question through its own API, such as TypeSafe, is a service.

A service's own features that no port names (a Slack canvas, a WhatsApp voice note, an Asaas receipt page) stay in the connector's command and are used only when an agent's prompt says so; a [port command](port-command.md) offers only what every connector of the port can deliver.
