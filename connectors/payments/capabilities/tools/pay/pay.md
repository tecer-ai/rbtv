# pay

`pay` is the [port command](../../../../../core/rbtv/capabilities/glossary/port-command.md) of the payments [port](../../../../../core/rbtv/capabilities/glossary/port.md): an agent pays by Pix key (`pix`), QR code (`qr`), bill (`bill`) or mobile top-up (`recharge`) from a named account, through Ignite's [payment gate](../../../../../core/ignite/capabilities/glossary/payment-gate.md), reads (`list`, `show`), withdraws (`cancel`) and fetches the receipt (`receipt`) of its own requests, and lists the accounts it may pay from (`accounts`). It holds the gate call for every bank: it asks the account's connector command to resolve the recipient (`<connector> --json pay resolve draft`, the draft on stdin), records the request with `ignite --json payment request --connector NAME --request -`, waits up to 30 s for a rule-approved send, and prints the gate's answer. It never calls a paying endpoint; Ignite's waking service does, by running the connector's own `pay execute` and `pay status`. `pay -h` and each verb's `-h` are the interface reference; the specification it was built to is the connector architecture's `spec-pay.md` (phase 2, 2026-10-16).

## Nothing defaulted

Every paying verb requires `--from ACCOUNT`, the destination (`--to KEY`, `--code PAYLOAD`, `--line DIGITS`, `--number PHONE`), `--amount VALUE` where the destination does not fix it, and `--note TEXT` (top-ups included). A missing part is refused by name with the full example line, exit 2; nothing is guessed, even with one account configured. Destinations are options, not positionals, so a missing word is named instead of shifting the next one into its place.

## Accounts

`--from` names an entry of Ignite's payments configuration, `payments.connectors` (`payments.providers`, the older spelling, is read too; `["asaas"]` when neither is written). In phase 2 an account is a connector: a component under `connectors/` of the payments port whose command is on PATH under that name and whose `lib/withdrawal-validation.js` Ignite's loader accepts. `pay accounts` lists them with both facts, contacting no bank. No payments section in Ignite's `config.json` refuses every verb that needs the gate and names the runbook.

## What each verb returns

- `pix`, `qr`, `bill`, `recharge`: the rows `Recipient` (as the connector resolved it), `Amount`, `State` (`sent: approved by rule (within the limits)`, `pending: over the daily limit (…)`, `refused: payments are off`), `Request` (`P-0003, asaas id tra_…, receipt …` once sent; `P-0004, sent to the owner for approval` while pending) and `Next` while the outcome is still to come; `bill` prints a `Simulated` line (amount, fee, due date) first. `--json`: the ledger row as `ignite payment show --json` returns it (`connector`, `connector_id`, `connector_status` among its fields). Exit 0 for sent, approved, pending and uncertain; 1 for refused, failed and cancelled, the row still printed on stdout.
- `list [--state]`: one line per request, newest first, 20 at most; `No … payment requests.` when none; `--json` `{payments: [row…]}`.
- `show ID`: `Request`, `Recipient`, `Key`, `Amount`, `Note`, `State`, `Connector` (name, id, status), `Receipt`.
- `cancel ID`: a pending request is withdrawn (`Cancelled   P-0004: withdrawn before the owner decided`); a sent Pix or bill is cancelled at the bank through the connector's `cancel` while it can be; a sent QR payment or top-up, and any other state, is refused with the reason.
- `receipt REF [--out PATH]`: the connector saves the PDF (`Saved … (41 KB)`, `Receipt …`), never over an existing file; a request without a receipt yet is refused naming its state. `--json` `{path, bytes, receipt_url}`.
- `accounts`: a table `Account Connector Command Adapter`; `--json` `{accounts: [{name, connector, command, adapter}]}`.

A connector's refusal passes through as its three lines with `pay:` in front of the first. Every refusal and failure is three stderr lines, `pay: WHAT`, `  why:`, `  fix:`; with `--json` nothing is printed on stdout for one.

## Hand-over

Until the live R$1 test through `pay` and the switch of Sara's tool, `asaas pay pix|qr|bill|recharge` still call the gate themselves; both paths are gated, and `asaas pay`'s paying verbs are removed after the switch (spec-pay.md 3.10, step 5). A PIN never passes through `pay`; the API key is read by the connector; neither stream prints either.

## Maintenance

- `test_pay.js` beside the program runs every cell of the specification's result matrix against a stub `ignite` whose ledger is in memory and a stub `asaas` connector, both injected through `main(argv, deps).run`: `node test_pay.js`, one `PASS` line per test, exit 0.
- The program is one file on Node's standard library; `main(argv, deps)` takes `cwd`, `env`, `stdout`, `stderr`, `run`, `which` and `root`. `PAY_GATE_WAIT` is the seconds `pay` waits for a rule-approved send to finish (30); the tests set it to 0.
- `pay accounts` loads a connector's withdrawal validation through Ignite's own loader (`core/ignite/capabilities/tools/ignite/payment-webhook.js`, `loadConnector`), so what it calls found is what Ignite accepts.
