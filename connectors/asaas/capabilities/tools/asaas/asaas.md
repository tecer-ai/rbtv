# asaas

The command an agent runs to read an Asaas bank account: balance, statement, who owns a Pix key, and what a Pix QR code charges. This version moves no money; payment commands arrive with Ignite's payment gate, designed in the vault at `projects/ignite-0.2.2/asaas-connector/specification.md`. `asaas -h` is the interface reference.

## Results

- `balance`: the available balance. `--json` gives `{"balance": <number>}`.
- `statement`: newest first, 20 rows by default. When Asaas has more, the last text line is the next invocation (`More: asaas statement --offset N ...`); `--json` gives `has_more` and `total`. Purchases with the account's debit card appear as `ASAAS_CARD_*` types; the card has no other API.
- `pix lookup KEY`: the owner's name, masked CPF or CNPJ, and bank. Asaas allows 5 lookups a minute and keeps a token bucket per account (60 for a personal account; a key that does not exist costs 10), so look up a key once per payment.
- `pix decode PAYLOAD`: amount, receiver and whether it can be paid. An invalid payload is Asaas's 400, reported with its reason.

## Key

`$ASAAS_API_KEY` from the process environment first, then the `ASAAS_API_KEY=` line of the installation's `.rbtv/config/env/.env`, read literally. An Asaas key starts with `$`, so never load that file with a shell (`source`, `set -a; .`): the shell expands `$aact_...` to nothing and Asaas answers 401.

## Maintenance

- Source: the [Asaas API reference](https://docs.asaas.com/reference/llms.txt); the endpoints used are `GET /finance/balance`, `GET /financialTransactions`, `GET /pix/addressKeys/external` and `POST /pix/qrCodes/decode`.
- Checks: `python3 test_asaas.py` runs the real command against a local stub server with sentinel keys. Its guard on the literal `$` key goes red when a shell-style expansion is put back.
- `ASAAS_API_URL` points the command at another base URL; the tests use it, and the sandbox is `https://api-sandbox.asaas.com/v3`.
