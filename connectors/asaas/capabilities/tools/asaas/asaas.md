# asaas

The command an agent runs on an Asaas bank account: balance, statement, who owns a Pix key, what a Pix QR code charges, this agent's payment requests, withdrawing a pending one, cancelling a sent Pix or bill, and a receipt PDF. An agent pays with `pay pix|qr|bill|recharge --from asaas`, the payments [port command](../../../../../core/rbtv/capabilities/glossary/port-command.md), which holds Ignite's [payment gate](../../../../../core/ignite/capabilities/glossary/payment-gate.md). `asaas -h` and each command's `-h` are the interface reference.

## Paying

`asaas pay pix`, `asaas pay qr`, `asaas pay bill` and `asaas pay recharge` refuse, exit 2, and name `pay` with `--from asaas`. `asaas pay` keeps the three verbs Ignite's waking service runs, each with the request on stdin. `asaas pay -h` names them: resolve, execute, status. `pay resolve ID` reads the recipient again from Asaas before the owner is asked (a key, amount or fee that differs refuses the request), and `pay resolve draft` does the same lookup for `pay` before any request exists, from a draft `{connector, method, recipient: {key, key_type}, amount_cents, note}` on stdin, printing `{recipient, amount_cents, fee_cents, changeable, details}`. `pay execute ID` alone calls a paying endpoint, `POST /transfers` or `POST /bill` with the request id as `externalReference`, `POST /pix/qrCodes/pay` or `POST /mobilePhoneRecharges` without one, and with `--json` prints `{"created": false, "reason"}` when Asaas answered an error or no call was made, so the service fails the request instead of holding it uncertain. `pay status ID` reads the operation. Asaas then asks Ignite's withdrawal validation, which approves only the request that operation names (by `externalReference`, or for a QR code or a top-up by the operation id `pay execute` printed), at its amount and recipient. A call to the API that did not pass the gate is refused, even with the key.

`lib/withdrawal-validation.js` is Asaas's half of that validation: the path Asaas calls (`/asaas/withdrawal-validation`), the `asaas-access-token` header, the `ASAAS_WEBHOOK_TOKEN` variable, and how each body type (`TRANSFER`, `BILL`, `PIX_QR_CODE`, `MOBILE_PHONE_RECHARGE`) reads as an operation. Ignite's waking service loads it by the connector name `asaas` (`payments.connectors`); it is JavaScript, run by Ignite's Node, and the Python command above does not use it. Its tests are Ignite's `test_payments.js`.

`asaas payments`, `asaas payment ID` and `asaas cancel ID` read this agent's requests and withdraw a pending one; `cancel` on a sent Pix key transfer or bill cancels it at Asaas while Asaas still allows it, and refuses a sent QR payment or top-up, which the owner cancels in the Asaas app.

`asaas receipt ID [--out FILE]` saves a done payment's receipt as a PDF, from this agent's request id or from an Asaas receipt link (`https://www.asaas.com/...`, the link `asaas payment ID` shows). It reads the receipt page and follows that page's own PDF link; Asaas documents no receipt-PDF endpoint, so when the page changes the command says so and names the link to open in a browser. The file defaults to `<request id>.pdf` in the current folder and is never written over.

## Results

- `balance`: the available balance. `--json` gives `{"balance": <number>}`.
- `statement`: newest first, 20 rows by default. When Asaas has more, the last text line is the next invocation (`More: asaas statement --offset N ...`); `--json` gives `has_more` and `total`. Purchases with the account's debit card appear as `ASAAS_CARD_*` types; the card has no other API.
- `pix lookup KEY`: the owner's name, masked CPF or CNPJ, and bank. Asaas allows 5 lookups a minute and keeps a token bucket per account (60 for a personal account; a key that does not exist costs 10), so look up a key once per payment. `pay` asks `asaas pay resolve draft`, which makes that lookup.
- `pix decode PAYLOAD`: amount, receiver and whether Asaas would accept paying it. `pay qr` asks the same decode. An invalid payload is Asaas's 400, reported with its reason.

## Key

`$ASAAS_API_KEY` from the process environment first, then the `ASAAS_API_KEY=` line of the installation's `.rbtv/config/env/.env`, read literally. An Asaas key starts with `$`, so never load that file with a shell (`source`, `set -a; .`): the shell expands `$aact_...` to nothing and Asaas answers 401.

## Maintenance

- Source: the [Asaas API reference](https://docs.asaas.com/reference/llms.txt) and the [withdrawal validation](https://docs.asaas.com/docs/mechanism-for-validating-withdrawals-via-webhooks.md). Endpoints read: `GET /finance/balance`, `GET /financialTransactions`, `GET /pix/addressKeys/external`, `POST /pix/qrCodes/decode`, `POST /bill/simulate`, `GET /transfers/{id}`, `GET /bill/{id}`, `GET /pix/transactions/{id}`, `GET /mobilePhoneRecharges/{id}`. Endpoints that pay, `pay execute` only: `POST /transfers`, `POST /bill`, `POST /pix/qrCodes/pay`, `POST /mobilePhoneRecharges`. Cancels: `DELETE /transfers/{id}/cancel`, `POST /bill/{id}/cancel`. Receipts: the receipt page at `www.asaas.com` and its `/transactionReceipt/pdf/{n}` link, not part of the API. The final statuses of a QR payment (`DONE`; `REFUSED`, `ERROR`, `CANCELLED`) and of a top-up (`CONFIRMED`; `CANCELLED`, `REFUNDED`, `FAILED`) are not yet confirmed against a live operation.
- A gate row names its connector as `connector`, `connector_id` and `connector_status`; the older spelling `provider`, `provider_id` and `provider_status`, which an Ignite deployed before the rename still writes, is read too.
- `payments`, `payment`, `cancel` and `receipt` find the gate as `ignite` on PATH. `ASAAS_IGNITE` names Ignite's `cli.js` instead, run with node; the tests use it.
- Checks: `python3 test_asaas.py` runs the real command against a local stub server with sentinel keys, and the read and service verbs against Ignite's real gate in a temporary installation. Its guard on the literal `$` key goes red when a shell-style expansion is put back; its paying-endpoint guard goes red when a read or cancel calls one. Only `pay execute` calls a paying endpoint.
- `ASAAS_API_URL` points the command at another base URL; the tests use it, and the sandbox is `https://api-sandbox.asaas.com/v3`.
