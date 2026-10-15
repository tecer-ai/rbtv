# asaas

The command an agent runs on an Asaas bank account: balance, statement, who owns a Pix key, what a Pix QR code charges, and payments by Pix key and by bill, which only Ignite's [payment gate](../../../../../core/ignite/capabilities/glossary/payment-gate.md) can let through. `asaas -h` and each command's `-h` are the interface reference.

## Paying

`asaas pay pix KEY AMOUNT --note TEXT` and `asaas pay bill LINE --note TEXT` run inside an Ignite turn. Each resolves the recipient first (the Pix key's owner, or the bill's simulation with its amount and fee), records a request with `ignite payment request`, and prints the gate's answer:

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
| `refused` | Payments are off | 1 |

A `pay` command never calls a paying endpoint. Ignite's waking service runs `asaas --json pay execute ID` with the approved request on stdin; that command alone calls `POST /transfers` or `POST /bill`, with the request id as `externalReference`. Asaas then asks Ignite's withdrawal validation, which approves only the request that id names, at its amount and recipient. A call to the API that did not pass the gate is refused, even with the key. `pay status ID` is the service's read of a sent operation.

`asaas payments`, `asaas payment ID` and `asaas cancel ID` read this agent's requests and withdraw a pending one; `cancel` on a sent payment cancels it at Asaas while Asaas still allows it.

Pix QR codes and mobile top-ups are not paid (`pay pix` refuses a QR code's copy-and-paste text and says so): Asaas takes no `externalReference` on `POST /pix/qrCodes/pay` or `POST /mobilePhoneRecharges`, so the withdrawal validation could not tie the operation to a gate request.

## Results

- `balance`: the available balance. `--json` gives `{"balance": <number>}`.
- `statement`: newest first, 20 rows by default. When Asaas has more, the last text line is the next invocation (`More: asaas statement --offset N ...`); `--json` gives `has_more` and `total`. Purchases with the account's debit card appear as `ASAAS_CARD_*` types; the card has no other API.
- `pix lookup KEY`: the owner's name, masked CPF or CNPJ, and bank. Asaas allows 5 lookups a minute and keeps a token bucket per account (60 for a personal account; a key that does not exist costs 10), so look up a key once per payment. `pay pix` makes that lookup itself.
- `pix decode PAYLOAD`: amount, receiver and whether Asaas would accept paying it; `asaas pay` pays no QR code in this version. An invalid payload is Asaas's 400, reported with its reason.
- `pay pix`, `pay bill`: `--json` gives the gate's request (`ignite payment request -h` lists its fields).

## Key

`$ASAAS_API_KEY` from the process environment first, then the `ASAAS_API_KEY=` line of the installation's `.rbtv/config/env/.env`, read literally. An Asaas key starts with `$`, so never load that file with a shell (`source`, `set -a; .`): the shell expands `$aact_...` to nothing and Asaas answers 401.

## Maintenance

- Source: the [Asaas API reference](https://docs.asaas.com/reference/llms.txt) and the [withdrawal validation](https://docs.asaas.com/docs/mechanism-for-validating-withdrawals-via-webhooks.md). Endpoints read: `GET /finance/balance`, `GET /financialTransactions`, `GET /pix/addressKeys/external`, `POST /pix/qrCodes/decode`, `POST /bill/simulate`, `GET /transfers/{id}`, `GET /bill/{id}`. Endpoints that pay, `pay execute` only: `POST /transfers`, `POST /bill`. Cancels: `DELETE /transfers/{id}/cancel`, `POST /bill/{id}/cancel`.
- `pay` finds the gate as `ignite` on PATH. `ASAAS_IGNITE` names Ignite's `cli.js` instead, run with node, and `ASAAS_GATE_WAIT` the seconds `pay` waits for a send (30); the tests use both.
- Checks: `python3 test_asaas.py` runs the real command against a local stub server with sentinel keys, and the `pay` commands against Ignite's real gate in a temporary installation. Its guard on the literal `$` key goes red when a shell-style expansion is put back; its paying-endpoint guard goes red when a `pay` command calls one.
- `ASAAS_API_URL` points the command at another base URL; the tests use it, and the sandbox is `https://api-sandbox.asaas.com/v3`.
