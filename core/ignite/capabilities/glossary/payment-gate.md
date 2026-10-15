# Payment gate

The payment gate is the one place that decides whether an agent's payment may leave the owner's account. It decides by code, outside any model, from the owner's settings, or waits for the owner's own decision in Slack, so nothing an agent can type, edit or post approves a payment. It is bank-neutral: a payment tool (a provider, such as the `asaas` connector's command) resolves the recipient, asks the gate, and sends only what the gate approved, through Ignite's waking service.

| Part | What it is |
|---|---|
| Mode | `off` refuses every request; `automatic` approves a request that fits every limit set and waits for the owner otherwise; `case_by_case` waits for the owner on every request. `off` until the owner saves settings |
| Limits | Optional amounts per day, week (from Monday) and month, in America/Sao_Paulo calendar periods, counting the approved and sent payments of the period with their fees. `automatic` with no limit set is refused on save, so automatic always has a ceiling |
| Request | One ledger row: agent, conversation, provider, method, recipient (name, key or document, bank), amount and fee in cents, note, state, who decided (`rule` or `owner`) and when, the provider's operation id and receipt. Ids read `P-0007` |
| State | `pending` (waits for the owner), `approved` (Ignite is sending it), `sent` (the provider has it), `refused`, `cancelled` (withdrawn by the agent while pending), `failed` |
| PIN | Set by the owner on first use of `/payments`, kept as a salted scrypt hash in `.rbtv/config/ignite/payments-pin.json`, asked on every approval the owner makes and on every settings save. Five wrong PINs in a row lock PIN forms for 15 minutes |
| Withdrawal validation | The bank's call before money leaves: Ignite answers from the ledger alone, approving only the operation that names a request Ignite is sending or sent, at its amount and recipient, once |

The owner acts in Slack only: `/payments` opens a panel (mode, limits and what went out this day, week and month; pending requests with Approve and Refuse; the last ten sent with receipt links), and each pending request is also posted in its agent's thread with Approve and Refuse. Approve asks for the PIN; anyone but the owner is refused. An agent asks with `ignite payment request` through its payment tool, reads and withdraws its own requests, and is woken with the outcome; no verb approves, refuses or changes settings.

Ignite's [architecture](../tools/ignite/documentation/architecture.md) names the files of each part; the [runbook](../tools/ignite/documentation/runbook.md) has the owner's setup and the repairs; [decisions](../../decisions.md) records why the gate is shaped this way.
