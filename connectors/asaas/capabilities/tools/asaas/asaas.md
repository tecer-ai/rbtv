# asaas

The command an agent runs on an Asaas bank account: balance, statement, who owns a Pix key, what a Pix QR code charges, and payments by Pix key, Pix QR code, bill and mobile top-up, which only Ignite's [payment gate](../../../../../core/ignite/capabilities/glossary/payment-gate.md) can let through. `asaas -h` and each command's `-h` are the interface reference.

## Paying

`asaas pay pix KEY AMOUNT --note TEXT`, `asaas pay qr PAYLOAD [--amount AMOUNT] --note TEXT`, `asaas pay bill LINE --note TEXT` and `asaas pay recharge PHONE AMOUNT` run inside an Ignite turn. Each resolves the recipient first (the Pix key's owner; the QR code's receiver and the amount it fixes, `--amount` being needed only when it fixes none; the bill's simulation, whose value and fee `pay bill` prints first and whose sum counts toward the limits; a top-up's phone, as 11 digits), records a request with `ignite payment request`, and prints the gate's answer:

```
Recipient   KENU EXAMPLE SILVA · ***.123.456-** · Nubank
Amount      R$ 99,00
State       pending: over the weekly limit (R$ 80,00 left of R$ 150,00)
Request     P-0007, sent to the owner for approval
Next        end this turn waiting_workers: Ignite wakes this conversation with the owner's decision; asaas payment P-0007 shows it meanwhile
```

| State | What happened | Exit |
|---|---|---|
| `pending` | The owner decides, with the request posted in this thread. End the turn `waiting_workers`: Ignite wakes this conversation with the outcome. Otherwise the outcome arrives in the thread as a system message | 0 |
| `sent` | Within the owner's limits: Ignite sent it, and the Request line names the Asaas id | 0 |
| `approved` | Ignite has not finished sending it after 30 s; the outcome arrives in this conversation | 0 |
| `uncertain` | Ignite lost Asaas's answer while sending it: it may have paid. Do not ask again; Ignite reads it at Asaas and wakes this conversation with the outcome | 0 |
| `refused` | Payments are off | 1 |

A `pay` command never calls a paying endpoint. Ignite's waking service runs the three service commands, each with the request on stdin: `pay resolve ID` reads the recipient again from Asaas before the owner is asked (a key, amount or fee that differs refuses the request); `pay execute ID` alone calls a paying endpoint, `POST /transfers` or `POST /bill` with the request id as `externalReference`, `POST /pix/qrCodes/pay` or `POST /mobilePhoneRecharges` without one, and with `--json` prints `{"created": false, "reason"}` when Asaas answered an error or no call was made, so the service fails the request instead of holding it uncertain; `pay status ID` reads the operation. Asaas then asks Ignite's withdrawal validation, which approves only the request that operation names (by `externalReference`, or for a QR code or a top-up by the operation id `pay execute` printed), at its amount and recipient. A call to the API that did not pass the gate is refused, even with the key.

`lib/withdrawal-validation.js` is Asaas's half of that validation: the path Asaas calls (`/asaas/withdrawal-validation`), the `asaas-access-token` header, the `ASAAS_WEBHOOK_TOKEN` variable, and how each body type (`TRANSFER`, `BILL`, `PIX_QR_CODE`, `MOBILE_PHONE_RECHARGE`) reads as an operation. Ignite's waking service loads it by the provider name `asaas`; it is JavaScript, run by Ignite's Node, and the Python command above does not use it. Its tests are Ignite's `test_payments.js`.

`asaas payments`, `asaas payment ID` and `asaas cancel ID` read this agent's requests and withdraw a pending one; `cancel` on a sent Pix key transfer or bill cancels it at Asaas while Asaas still allows it, and refuses a sent QR payment or top-up, which the owner cancels in the Asaas app. `pay pix` refuses a QR code's copy-and-paste text and names `pay qr`.

## Results

- `balance`: the available balance. `--json` gives `{"balance": <number>}`.
- `statement`: newest first, 20 rows by default. When Asaas has more, the last text line is the next invocation (`More: asaas statement --offset N ...`); `--json` gives `has_more` and `total`. Purchases with the account's debit card appear as `ASAAS_CARD_*` types; the card has no other API.
- `pix lookup KEY`: the owner's name, masked CPF or CNPJ, and bank. Asaas allows 5 lookups a minute and keeps a token bucket per account (60 for a personal account; a key that does not exist costs 10), so look up a key once per payment. `pay pix` makes that lookup itself.
- `pix decode PAYLOAD`: amount, receiver and whether Asaas would accept paying it, which `pay qr` does. An invalid payload is Asaas's 400, reported with its reason.
- `pay pix`, `pay qr`, `pay bill`, `pay recharge`: `--json` gives the gate's request (`ignite payment request -h` lists its fields).

## Key

`$ASAAS_API_KEY` from the process environment first, then the `ASAAS_API_KEY=` line of the installation's `.rbtv/config/env/.env`, read literally. An Asaas key starts with `$`, so never load that file with a shell (`source`, `set -a; .`): the shell expands `$aact_...` to nothing and Asaas answers 401.

## Maintenance

- Source: the [Asaas API reference](https://docs.asaas.com/reference/llms.txt) and the [withdrawal validation](https://docs.asaas.com/docs/mechanism-for-validating-withdrawals-via-webhooks.md). Endpoints read: `GET /finance/balance`, `GET /financialTransactions`, `GET /pix/addressKeys/external`, `POST /pix/qrCodes/decode`, `POST /bill/simulate`, `GET /transfers/{id}`, `GET /bill/{id}`, `GET /pix/transactions/{id}`, `GET /mobilePhoneRecharges/{id}`. Endpoints that pay, `pay execute` only: `POST /transfers`, `POST /bill`, `POST /pix/qrCodes/pay`, `POST /mobilePhoneRecharges`. Cancels: `DELETE /transfers/{id}/cancel`, `POST /bill/{id}/cancel`. The final statuses of a QR payment (`DONE`; `REFUSED`, `ERROR`, `CANCELLED`) and of a top-up (`CONFIRMED`; `CANCELLED`, `REFUNDED`, `FAILED`) are not yet confirmed against a live operation.
- `pay` finds the gate as `ignite` on PATH. `ASAAS_IGNITE` names Ignite's `cli.js` instead, run with node, and `ASAAS_GATE_WAIT` the seconds `pay` waits for a send (30); the tests use both.
- Checks: `python3 test_asaas.py` runs the real command against a local stub server with sentinel keys, and the `pay` commands against Ignite's real gate in a temporary installation. Its guard on the literal `$` key goes red when a shell-style expansion is put back; its paying-endpoint guard goes red when a `pay` command calls one.
- `ASAAS_API_URL` points the command at another base URL; the tests use it, and the sandbox is `https://api-sandbox.asaas.com/v3`.
