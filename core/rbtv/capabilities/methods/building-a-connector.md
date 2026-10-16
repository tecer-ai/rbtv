# Building a connector

Build a [connector](../glossary/connector.md): a component under `connectors/` that joins rbtv to one outside [service](../glossary/service.md) through two parts, a command agents run and an [adapter](../glossary/adapter.md) Ignite loads. The result is the component with its record filled, its command answering `-h`, one adapter per [port](../glossary/port.md) it names exporting that port's shape, one real read performed on the service, and its tests; the shape check at the end confirms it. A read-only connector ends there; a connector that writes (a payment, a message) continues with the section Writes.

Required inputs, from the task or the owner: the service and where its API is documented; the account to use, with no money on it or none at risk; the ports the connector serves and the operations it performs; for anything that moves money or speaks for the owner, the owner's authorization and the review rounds in the estimate. When one is missing, stop and name it; do not pick an account or a port yourself.

This page adds what a connector needs beyond a tool. The command's design, help, output and blind usability pass are governed by [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md), which this page does not repeat: read it before the command's first verb and run its sequence at the step below that names it.

## The shape

A connector has two parts with separate entry points. Both are required for every connector, whatever its port and whether it writes: Ignite reaches every service through an adapter, and the port's shape, not what Ignite loads today, says what the adapter exports.

| Part | What it is | Who runs it |
|---|---|---|
| Command | A [tool](../glossary/tool.md) at `capabilities/tools/<name>/`, in any language (Asaas: Python), that knows nothing of Ignite. It carries every operation an agent runs on the service and the service's own features | Agents, from their turns |
| Adapter | A Node module under `capabilities/tools/<name>/lib/`, one per port the record names in `type` and `serves`, named by the rule below and exporting the shape of the table below, which translates the service into the port's [operations](../glossary/operation.md) | Ignite, in its own process, loaded by the connector's name |

The adapter is in-process because Ignite is a daemon that reacts, polls and ticks; a command started per call is not viable there. When the command and the adapter are in different languages (Asaas: a Python command, a Node adapter), the connector may carry two implementations of one service call, one in each part; keep them in agreement by testing both against the same fixtures of the service's bodies. When both are Node, share one implementation, the command requiring the adapter's module or both requiring one module under `lib/`, so the service call has one home ([Single source of truth](../principles/single-source-of-truth.md)).

Policy is not the connector's. The payment gate decides in Ignite, and a message's permission is checked by the port command: the connector resolves, asks and executes what was allowed.

### The adapter file and what it exports

The adapter of a port is `capabilities/tools/<name>/lib/<port>.js` (`lib/messaging.js`, `lib/calendar.js`). The one exception is the payments adapter, `lib/withdrawal-validation.js`: Ignite's `payment-webhook.js` loads it at that name, and the exception lasts until that loader changes.

| Port | Exports |
|---|---|
| `payments` | `path`, `header`, `tokenEnv` and `read(body)`, as the [payment gate](../../../ignite/capabilities/glossary/payment-gate.md)'s withdrawal validation states; Ignite's `payment-webhook.js` loads it by the connector's name and refuses another shape |
| `messaging` | `operations`, as the [messaging contract](../../../../connectors/messaging/capabilities/methods/messaging-contract.md)'s Adapter section states: one async function per operation of the contract the record `provides`, keyed by the operation's name, with the input and result fields that section names |
| Any other port (`media`, `judgment`, `calendar`, `storage`, or a port this connector is the first of) | `operations`: an object with one async function per operation the record `provides` for that port, keyed by the operation's name (`operations['media.transcribe']`). Each takes one object and returns one object whose fields are the ones the command's verb for the same operation takes and prints in its structured output, so the two parts describe one operation. A token is read by its environment variable name inside the function, never when the module loads |

A connector that serves several ports has one module per port, each holding the operations of its port.

## Where and what to name

Place the component as [Choosing where to build](choosing-where-to-build.md) says: `connectors/<service>/`, one component per service, named for the service in lower case (`slack`, `asaas`). When a component for the service exists, extend it; a second port the same service serves is `serves`, not a second component. A new port with no connector yet is declared only once a connector performs one of its operations.

Fill the record ([Component record](../glossary/component-json.md)):

| Field | How to fill it |
|---|---|
| `type` | The one port the connector is listed under. Required under `connectors/`; the installer refuses the scan without it |
| `serves` | The other ports it also covers; omit when none |
| `provides` | The operations the command or adapter performs today, by the port's contract names (`message.send`, `payment.validate`). A port with no contract page takes `<noun>.<verb>` with the port's noun (`media.transcribe`). Nothing the connector might do later |
| `needs` | Operations it requires another component to provide; omit when none. The installer refuses a need no component provides |
| `dependencies` | Outside software only, with its install command |
| `description` | The service and what the command does with it, then the nearest excluded work |

## The order that worked

The Asaas connector took about ten hours from nothing to a working connector with a live gate. This order kept the risk late and the learning early; follow it, port by port.

1. **Read commands first, on the real account, with no money on it.** Balance, statement, who owns a key; the account's own shapes are the fixtures for everything after. Keep a short script until a durable command is needed.
2. **The adapter.** Its port's module, named and shaped as The adapter file and what it exports states, tested with recorded bodies of the service: from Ignite's suite when Ignite loads it ([Testing Ignite](../../../ignite/capabilities/methods/testing-ignite.md)), otherwise from a test program beside the connector's command.
3. **The blind usability pass of the command**, as Building a command-line interface runs it: cold users with the installed command and realistic jobs, nothing else. Repair what they could not do before any real exchange.
4. **The shape check** below, then [Documenting a change](documenting-a-change.md).

A read-only connector is done after step 4. A connector that writes continues:

5. **The port's protection, before any write.** For money, the gate's request, the ledger and the resolution of the recipient (section Money). For messages, the inbound path and the permission check (section Messaging).
6. **One real small exchange.** A payment of a few reais to a known recipient; one message to the owner. The owner approves it; the receipt or the arrival is the evidence.

## Writes

The sections below apply only to a connector that writes: money leaving the account, a message leaving as the owner or an agent. Speaking for the owner carries the risk money does.

### Money

A payments connector moves the owner's money, so the [payment gate](../../../ignite/capabilities/glossary/payment-gate.md) is the one place that lets a payment leave. The `pay` [port command](../glossary/port-command.md) holds the gate call: it asks the connector's command to resolve the recipient (`<connector> pay resolve draft`, the draft request on stdin: a Pix key's owner, a QR code's receiver and amount, a bill's simulation), records the request with `ignite payment request --connector <name>`, and prints the gate's answer. Ignite's waking service then runs the connector's command directly, never through `pay`: `<connector> pay resolve ID` reads the recipient again before the owner sees the request, `<connector> pay execute ID` alone calls a paying endpoint, with the request id as the operation's reference where the service takes one, and `<connector> pay status ID` reads the operation, each with the request on stdin. So a payments connector's command carries exactly those four service verbs beside its reads; it has no paying verb of its own. The adapter is the withdrawal validation of the table above; Ignite's `payment-webhook.js` loads it with `loadConnector(name)` and answers the bank from the ledger alone. A paying call that did not pass the gate is refused by that validation even with the account's key.

The review loop, not the API, dominates the time: Asaas's API and command were quick, and the gate took seven review rounds by a second model, each finding rarer cases in recovery paths (restarts, locks, notices); rounds five to seven found nothing that moves money. Put the review rounds in the estimate from the start, review the gate's code and its recovery paths rather than the happy path, and stop looping when a round's findings stop touching the risk; file what remains as fail-safe defects and let the owner rule on deploying with them.

### Messaging

A messaging connector delivers the [messaging contract](../../../../connectors/messaging/capabilities/methods/messaging-contract.md): the operations it provides, each in the contract's words (group, contact, thread), and every inbound event in the contract's one shape, with the connector's own event kept under `raw`. The [listener](../../../ignite/capabilities/glossary/listener.md) is Ignite's and routes by [subscription](../../../ignite/capabilities/glossary/subscription.md); the adapter only delivers.

The inbound path is the service's. A service that pushes delivers into a localhost receiver built on the `payment-webhook.js` pattern, with the push verified by a shared secret the service sends (WhatsApp: `wacli sync --webhook URL --webhook-secret …`). A service with no push is polled on a timer by its adapter (mail through the google connector). Read the installed program's help or its source for the push before deciding it polls; documentation alone had WhatsApp as polling.

The recipient's permission is checked by `message send` before any connector, and a message to a contact is never sent by `slack send`, `ignite post` or the connector's command once the port command exists. Estimate the review rounds as for money.

## Security rules

- The Ignite server is closed to the internet. Anything a service must reach goes through the one tunnel the owner runs, to a path on `127.0.0.1` that the service owns; every other path answers 404. Never propose opening a port.
- Never print a secret: not in a log, a report, a payload or a test fixture. A payload may hold a PIN; never log one.
- The installation's environment file values can start with `$`. Read the file literally; never `source` it.
- A documentation server with an action that executes requests never sits beside an account key. Install it, read, remove it.
- Agents and Ignite share the operating system user. The owner accepted that for the trial only; it is not a design to build on, and separating them is its own project before more money moves.

## The shape check

Run these from the repository root with the connector's name in place of `<name>`; every line exits 0 or the connector is not in shape. Nothing else is filled in: the third line reads the ports, the operations and the adapter files from the record.

```sh
rbtv show connectors/<name>
<name> -h
adapter-check <name>
<name> <one read verb>
```

1. `rbtv show` runs the installer's scan: a record without `type`, or a need no component provides, fails with the installer's refusal; a valid record prints a `Type:` line. When `rbtv` is not on PATH, run `python3 core/rbtv/capabilities/tools/rbtv/install.py show connectors/<name>` (`python` on Windows).
2. The command answers help. Before the connector is installed, run the record's `entry` by its path with its interpreter instead of the shortcut.
3. [adapter-check](../tools/adapter-check/adapter-check.md) loads, for each port in `type` and `serves`, the adapter file the rule above names and checks its exports: a payments adapter through Ignite's own loader, so what passes here is what Ignite accepts; any other port's `operations`, one function per operation the record `provides` for that port, none of another port and none the record does not provide. Each defect is printed, one per line, and the run exits 1. Before the tool is installed, run `node core/rbtv/capabilities/tools/adapter-check/adapter-check.js <name>`.
4. One real read on the account, through the command.

The check confirms the shape, not the behaviour: the tests of the command and of the adapter, the blind pass and, for a connector that writes, the real exchange are the evidence that it works.
