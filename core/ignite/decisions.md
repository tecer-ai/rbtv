# Ignite decisions

## Live status

[Live status](capabilities/glossary/live-status.md) shows each owner message's state in three layers: system, agent and task. Owner decisions, 2026-10-15:

- **Ignite owns the states; connectors own the medium.** Ignite names no emoji. Each communication connector shows the states in its own medium; Slack is the one built. A new medium adds a connector, not a state.
- **Only the agent state moves.** A tick removes the agent's frame and then adds the next, so the order system, then agent or task, holds by itself. The owner prefers a brief gap to two frames shown at once.
- **The agent declares only what it is doing.** `ignite status <state>` takes no message, thread or Slack argument. Ignite sets `working` at every turn start, so an agent that never declares still shows as working.
- **The task state comes from the turn result**: the disposition, plus `caveats` on `completed`. The command sets a task state only for an earlier message.
- **The waking service shows the states.** The command records the state and exits. The service sees every agent, so it alone shares Slack's reaction budget among them: 45 adds a minute across all agents, half the rate at which Slack answered HTTP 429 in a measured burst.
- **The Slack side is pure logic in the Slack connector**, handed the reaction functions by its caller, so it works with Ignite's own Slack client.
- **Waiting on workers is an agent state.** It is not a task or system state: a turn ending `waiting_workers` shows the agent waiting, ticking slowly, until the next turn of that conversation starts or the work stops waiting (stopped or held).

## Payment gate

The [payment gate](capabilities/glossary/payment-gate.md) decides whether an agent's payment may leave the owner's account. Owner decisions, 2026-10-15:

- **Payments are approved outside any model.** Ignite holds the gate, its settings and its ledger, because Ignite already receives the owner's Slack actions over its socket and is the one process the agents do not control. The Slack connector writes with the owner's token, so nothing an agent can type, post or edit in Slack is an approval.
- **Manual approval is a button that opens a PIN form**, never a typed message, a canvas or a slash command carrying the PIN: an agent cannot click a button or submit a modal. The PIN is asked on every approval the owner makes and on every settings save.
- **The owner sets the mode and limits in `/payments`**, a modal the agents do not see. Automatic always has a ceiling: it is refused on save with no limit set.
- **The gate is bank-neutral; the bank lives in its connector.** A provider's tool resolves the recipient and asks; Ignite's service sends what was approved by running that tool, and answers the bank's withdrawal validation from the ledger, so an API call that skipped the gate is refused even with the key.

Choices made when the gate was built, 2026-10-15, open to the owner's review:

- **One ledger per installation**, not per agent: the limits are the owner's account's, so every agent's requests count against the same day, week and month.
- **Ignite sends only through a provider whose withdrawal validation it can read.** A provider without one could move money with no check after the gate.

Fix rounds, 2026-10-15 (reviews of the first build and of the first fix round; master's rulings, open to the owner's review):

- **The bank's half lives in its connector.** Each provider's webhook path, token header and variable, and body reading are an adapter `connectors/<name>/capabilities/tools/<name>/lib/withdrawal-validation.js`, which Ignite loads by the names in `payments.providers`; Ignite keeps only the bank-neutral checks. The time zone and currency of the limits are `payments.timeZone` and `payments.currency`, so nothing of one bank or one country is fixed in Ignite.
- **A send that may have paid stays counted.** A lost answer, a stop mid-send, or a provider id or withdrawal approval on a request that would otherwise fail leaves it `uncertain`, counted toward the limits until the provider's status proves it sent or failed. Releasing it earlier lets automatic approval spend money that may already be gone.
- **The withdrawal validation approves once, and an exact retry again.** The bank retries a call it did not get an answer to; the retry repeats the same operation, amount and recipient, and only that is approved again. A bank that takes no request id (a Pix QR code payment, a mobile top-up) is matched by the operation id Ignite recorded when it paid.
- **The owner approves only what the service resolved.** Before a pending request is shown, the service resolves its recipient through the provider; Approve is offered and accepted only after that resolution succeeded, so a request whose resolution failed stays pending with Refuse alone, and the runner never sends an owner's approval of an unchecked request. The agent's description is shown only as a labelled note, and a resolution that differs from the request refuses it. A rule-approved request is not resolved first: no one reads it before it is sent, and the withdrawal validation still matches its amount and recipient.
- **The withdrawal validation answers from its own thread.** The service's main thread makes blocking SQLite calls, for the ledger and for every agent's store, so a listener there waits whenever any of them waits. The listener runs in a worker thread with its own ledger connection, which never waits on a lock: a busy ledger is tried again without blocking and refused 600 ms after the call arrived, so every answer arrives within 1 s.
- **Every Socket Mode envelope is acknowledged on arrival**, before and apart from its processing, so no handler, error or busy ledger can miss Slack's 3 s. A submitted form therefore shows "Checking…" and its outcome arrives by `views.update`; an owner message whose processing fails after its acknowledgement is logged, not redelivered.
- **Settings forms carry their revision, and each owner interaction is recorded by its key**, so a replayed or stale submission changes nothing; only the key is kept, never a payload.
