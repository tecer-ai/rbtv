# Building a connector

Build a [connector](../glossary/connector.md): a component under `connectors/` that joins rbtv to one outside [service](../glossary/service.md) through a command agents run and, where its [port](../glossary/port.md) has one, an [adapter](../glossary/adapter.md) Ignite loads. The result is the component with its record filled, its command answering `-h`, its adapter exporting the port's shape, one real read performed on the service, and its tests; the shape check at the end confirms it.

Required inputs, from the task or the owner: the service and where its API is documented; the account to use, with no money on it or none at risk; the ports the connector serves; for anything that moves money or speaks for the owner, the owner's authorization and the review rounds in the estimate. When one is missing, stop and name it; do not pick an account or a port yourself.

This page adds what a connector needs beyond a tool. The command's design, help, output and blind usability pass are governed by [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md), which this page does not repeat: read it before the command's first verb and run its sequence at the step below that names it.

## The shape

A connector has two parts with separate entry points.

| Part | What it is | Who runs it |
|---|---|---|
| Command | A [tool](../glossary/tool.md) at `capabilities/tools/<name>/`, in any language (Asaas: Python), that knows nothing of Ignite. It carries every operation an agent runs on the service and the service's own features | Agents, from their turns |
| Adapter | A Node module at `capabilities/tools/<name>/lib/<file>.js` exporting the shape its port names, which translates the service into the port's [operations](../glossary/operation.md) | Ignite, in its own process, loaded by the connector's name |

The adapter is in-process because Ignite is a daemon that reacts, polls and ticks; a command started per call is not viable there. The consequence: a connector may carry two implementations of one service call, one in the command and one in the adapter (Asaas reads a Pix key's owner in Python for `asaas pay` and reads the bank's validation body in Node for Ignite). Keep them in agreement by testing both against the same fixtures of the service's bodies; do not try to share code across the two, and do not expect one implementation.

Policy is not the connector's. The payment gate decides in Ignite, and a message's permission is checked by the port command: the connector resolves, asks and executes what was allowed.

## Where and what to name

Place the component as [Choosing where to build](choosing-where-to-build.md) says: `connectors/<service>/`, one component per service, named for the service in lower case (`slack`, `asaas`). When a component for the service exists, extend it; a second port the same service serves is `serves`, not a second component. A new port with no connector yet is declared only once a connector performs one of its operations.

Fill the record ([Component record](../glossary/component-json.md)):

| Field | How to fill it |
|---|---|
| `type` | The one port the connector is listed under. Required under `connectors/`; the installer refuses the scan without it |
| `serves` | The other ports it also covers; omit when none |
| `provides` | The operations the command or adapter performs today, by the port's contract names (`message.send`, `payment.validate`). Nothing the connector might do later |
| `needs` | Operations it requires another component to provide; omit when none. The installer refuses a need no component provides |
| `dependencies` | Outside software only, with its install command |
| `description` | The service and what the command does with it, then the nearest excluded work |

## The order that worked

The Asaas connector took about ten hours from nothing to a working connector with a live gate. This order kept the risk late and the learning early; follow it, port by port.

1. **Read commands first, on the real account, with no money on it.** Balance, statement, who owns a key; the account's own shapes are the fixtures for everything after. Keep a short script until a durable command is needed.
2. **The port's protection.** For money, the gate's request, the ledger and the resolution of the recipient (section Money). For messages, the listener's inbound shape and the permission check (section Messaging).
3. **The adapter and its inbound path.** The withdrawal validation for money; the receiver or poller for messages. Test it from Ignite's suite with recorded bodies.
4. **The blind usability pass of the command**, as Building a command-line interface runs it: cold users with the installed command and realistic jobs, nothing else. Repair what they could not do before any real exchange.
5. **One real small exchange.** A payment of a few reais to a known recipient; one message to the owner. The owner approves it; the receipt or the arrival is the evidence.

Then [Documenting a change](documenting-a-change.md), and [Testing Ignite](../../../ignite/capabilities/methods/testing-ignite.md) when Ignite loads the adapter.

## Money

A payments connector moves the owner's money, so the [payment gate](../../../ignite/capabilities/glossary/payment-gate.md) is the one place that lets a payment leave: the command resolves the recipient, records a request with `ignite payment request`, and prints the gate's answer; Ignite's waking service runs the command's service verbs (`pay resolve ID`, `pay execute ID`, `pay status ID`, each with the request on stdin) and only `pay execute` calls a paying endpoint, with the request id as the operation's reference where the service takes one. The adapter is the withdrawal validation: it exports `path`, `header`, `tokenEnv` and `read(body)`, and Ignite's `payment-webhook.js` loads it with `loadProvider(name)` and answers the bank from the ledger alone. A paying call that did not pass the gate is refused by that validation even with the account's key. `asaas pay` calls the gate itself until `pay` holds it; neither path ever exists without the gate.

The review loop, not the API, dominates the time: Asaas's API and command were quick, and the gate took seven review rounds by a second model, each finding rarer cases in recovery paths (restarts, locks, notices); rounds five to seven found nothing that moves money. Put the review rounds in the estimate from the start, review the gate's code and its recovery paths rather than the happy path, and stop looping when a round's findings stop touching the risk; file what remains as fail-safe defects and let the owner rule on deploying with them.

## Messaging

A messaging connector delivers the [messaging contract](../../../../connectors/messaging/capabilities/methods/messaging-contract.md): the operations it provides, each in the contract's words (group, contact, thread), and every inbound event in the contract's one shape, with the connector's own event kept under `raw`. The [listener](../../../ignite/capabilities/glossary/listener.md) is Ignite's and routes by [subscription](../../../ignite/capabilities/glossary/subscription.md); the adapter only delivers.

The inbound path is the service's. A service that pushes delivers into a localhost receiver built on the `payment-webhook.js` pattern, with the push verified by a shared secret the service sends (WhatsApp: `wacli sync --webhook URL --webhook-secret …`). A service with no push is polled on a timer by its adapter (mail through the google connector). Read the installed program's help or its source for the push before deciding it polls; documentation alone had WhatsApp as polling.

Speaking for the owner is the risk here as money is above: the recipient's permission is checked by `message send` before any connector, and a message to a contact is never sent by `slack send`, `ignite post` or the connector's command once the port command exists. Estimate the review rounds the same way.

## Security rules

- The Ignite server is closed to the internet. Anything a service must reach goes through the one tunnel the owner runs, to a path on `127.0.0.1` that the service owns; every other path answers 404. Never propose opening a port.
- Never print a secret: not in a log, a report, a payload or a test fixture. A payload may hold a PIN; never log one.
- The installation's environment file values can start with `$`. Read the file literally; never `source` it.
- A documentation server with an action that executes requests never sits beside an account key. Install it, read, remove it.
- Agents and Ignite share the operating system user. The owner accepted that for the trial only; it is not a design to build on, and separating them is its own project before more money moves.

## The shape check

Run these from the repository root, with the connector's name in place of `<name>` and its port's adapter file in place of `<adapter>`; every line exits 0 or the connector is not in shape.

```sh
rbtv show connectors/<name> | grep -q '^Type: '        # the record is valid and names its type
<name> -h > /dev/null                                   # the command answers help
node -e "const a = require('./connectors/<name>/capabilities/tools/<name>/lib/<adapter>.js'); for (const k of process.argv.slice(1)) if (!(k in a)) process.exit(1)" path header tokenEnv read
<name> <one read verb> > /dev/null                      # one real read on the account
```

The third line lists the exported names the port requires: `path header tokenEnv read` for a payments adapter; the messaging contract's names for a messaging adapter. A connector of a port with no adapter skips that line. `rbtv show` runs the installer's scan, so a record without `type`, or a need no component provides, fails the first line with the installer's refusal.

The check confirms the shape, not the behaviour: the tests of the command and of Ignite's suite, the blind pass and the real exchange are the evidence that it works.
