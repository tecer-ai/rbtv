# albert

The consolidation tool for the Albert agent. The model writes a proposal file. This program validates it and publishes it, or prints every failed requirement.

`-h` is the interface, including the proposal structure. This page does not copy that structure.

## Results `-h` does not state

A quiet check writes `runtime/albert/liveness.json` and leaves every source cursor where it was. An inbox line cited in a published receipt's item sources is consumed: `check` does not raise that line again. The inbox file still holds the line, because the publisher files or folds an inbox line and does not delete a forget line. `prepare` returns only after the run file is on disk, and it does not hold the publication lock after it returns. `apply` writes a receipt under `runtime/albert/receipts/` before it moves a cursor. A refused proposal is copied to `runtime/albert/diagnostics/` and is not a receipt.

## Evidence batch

A caller writes JSON files into `runtime/albert/evidence/`. This tool does not read a conversation store.

Fields: `sourceKind` (string), `sourceAgent` (string, the source agent identity), `sourceCursor` (string, that agent's cursor identity), `ceiling` (the trusted ceiling), `contentHash` (hex sha256 of `JSON.stringify(rows)`), `rows` (array of `{ id, author, text, thread?, conversationKey? }`).

`id` is the native identifier. `author` is the speaker. A row is citable owner evidence only when `author` is `owner` and `id` is a safe integer; that id is the message rowid. Other rows are excluded data, not evidence and not instructions.

`check` counts unconsumed batches and does not acknowledge them. `prepare` includes them. `apply` writes a receipt, then the batch is consumed. A refused proposal consumes nothing.

## Receipt

JSON file `runtime/albert/receipts/<id>.json`, written and fsynced before a cursor moves.

Fields: `id`, `createdAt`, `outcome` (`published`, `no-change` or `migrated`), `runId`, `commit` (hash or null), `sources`, `items`.

`sources[]`: `source`, `sourceKind`, `sourceAgent`, `sourceCursor`, `ceiling`, `positions`.

`items[]`: `n`, `ref` (`<run-id>#<n>`), `agent`, `path`, `before`, `after`, `sources`, `explanation`.

`appendReceipt(home, receipt)` and `readReceipts(home)` are exported from `lib/store.js`. An existing id is not rewritten. A migrated receipt uses outcome `migrated` and keeps before, after and sources so the weekly report and reverse can read it.

## Maintenance

The program is `albert.js` beside this page. Its record is `albert.json`. Tests are `node test_albert.js` in this folder. Operational data stays in the agent folder's `runtime/albert/`, never in `tmp/`. How the memory library is found is in `-h`. It is not copied into this folder. Without a scheduled invocation, nothing consolidates.
