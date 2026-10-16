# Listener

A listener is the inbound side of a [port](../../../rbtv/capabilities/glossary/port.md) in Ignite: one per port, it receives each [connector](../../../rbtv/capabilities/glossary/connector.md)'s events in the port's one inbound shape and hands them to Ignite's dispatch, which decides whom to wake. The messaging listener is the operation `message.receive`; its inbound event (who, group, thread, text, with optional parts) is the one the [messaging contract](../../../../connectors/messaging/capabilities/methods/messaging-contract.md) states, and every messaging connector's [adapter](../../../rbtv/capabilities/glossary/adapter.md) delivers that shape, whatever the service's own.

Today Ignite has one inbound path, Slack's Socket Mode through its own client (`daemon.js` connects, `ingress.js` classifies), and no listener for another service: WhatsApp is read by `whatsapp sync` and mail by `google`, and each agent sets its own timers to look again. The connector-neutral listener is phase 3a of the connector architecture. Its design, recorded in that project's decisions: Slack keeps Ignite's socket; WhatsApp pushes (`wacli sync --webhook URL --webhook-secret …`) into a localhost receiver built on the `payment-webhook.js` pattern; mail, which has no push in the google connector, is polled on a timer.

## What the listener decides

Routing is Ignite's dispatch, never an adapter's. For each event, in this order: admission (today every event not from the owner is dropped; a [subscription](subscription.md) is the only thing that opens it), thread affinity (a reply follows its thread's agent before any rule), the most specific matching subscription, a judged subscription (a TypeSafe judgment at entry, configured per subscription), then the port's default agent (a Slack DM: the configured DM agent; mail: the configured mail agent). Every decision is logged; nothing is dropped silently. No model judges anything at exit, and a judged route never grants a permission.

An adapter delivers events and keeps the session with its service; the listener receives, admits and routes; a subscription says who is woken. A schedule wakes an agent by time, not by an event.
