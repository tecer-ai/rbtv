# Subscription

A subscription is a record that says which agent an inbound event wakes: for a group, a contact or a kind of event on a [port](../../../rbtv/capabilities/glossary/port.md), the agent, set by the owner as data and never as code an agent writes. The [listener](listener.md) reads subscriptions when it routes; subscriptions and the routing rules are one store, which the `/messages` panel will manage.

Today the only subscriptions are Ignite's fixed configuration: `dmAgent`, the agent of the owner's Slack DM, and `routes`, one agent per channel; a channel with no route is ignored, and every event not from the owner is dropped before routing (`ingress.js`). A subscription that admits another sender is phase 3b of the connector architecture: owner-only stays the default, a subscription is the only thing that opens it, and a non-owner event with no subscription is still dropped.

## Kinds

| Kind | Wakes | Example |
|---|---|---|
| By place | The agent of a group or a contact | The owner's DM wakes master; the gaming channel wakes the gaming agent |
| Judged | The agent when a TypeSafe judgment at entry says the event is about a theme, configured per subscription | Mail about a client's project wakes Sara |
| Default | The port's default agent when no subscription matches | A Slack DM: master; mail: Sara |

A subscription routes; it grants nothing. What an admitted sender may ask for is the permission ladder per contact, category or group (blocked, asks me, replies only, talks freely, with sign-as and an expiry, plus can pay and can instruct), a separate record of the same `/messages` panel. A reply follows its thread's agent before any subscription is read. A turn that ends waiting for an event no subscription or timer will deliver is to be refused by Ignite (proposed, to be confirmed with the owner before it is built).
