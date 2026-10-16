# adapter-check

`adapter-check` checks the adapters of one connector against its record: the third line of the shape check in [Building a connector](../../methods/building-a-connector.md), which names the step that runs it and the adapter file each port has. `adapter-check -h` is the interface reference.

## What a run returns

| Exit status | Standard output | Standard error |
|---|---|---|
| 0 | `shape ok`, then one line per port: the port, its adapter file and what it exports | nothing |
| 1 | nothing | one line per defect, then the invocation to run again |
| 2 | nothing | the usage |

A payments adapter is loaded by Ignite's own loader (`loadProvider` in `core/ignite/capabilities/tools/ignite/payment-webhook.js`), so a module that passes here is the module Ignite accepts, and a module it refuses is reported with the loader's reason. Any other port's adapter must export `operations`, an object with one function per operation the record `provides` for that port, keyed by the operation's name; a key of another port's operation, a key the record does not provide, a provided operation with no key, and a value that is not a function are each a defect. The messaging port's operations are the rows of the [messaging contract](../../../../../connectors/messaging/capabilities/methods/messaging-contract.md)'s Operations table; another port's are `<port>.<verb>`. An operation in `provides` that belongs to no port of the record is a defect too.

The check loads the modules, so an adapter that calls its service or reads a token when it loads runs that code here; Building a connector requires neither.

## Maintenance

The program is one file, `adapter-check.js`, on Node's standard library; Node is the dependency the `rbtv` component's record (`core/rbtv/rbtv.json`) declares, and `rbtv doctor` reports it present or absent with its install address. It resolves the repository from its own location and reads the connector under `connectors/<name>/`; `check(name, { root })` is exported so its tests point it at a temporary tree. Run the checks with `node test_adapter_check.js` from this folder: they hold the real Asaas adapter, an adapter the loader refuses, operations of another port, swapped modules, an unprovided operation, a missing adapter and the command's three exit statuses.
