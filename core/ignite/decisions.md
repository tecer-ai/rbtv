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
- **Ignite sends only through a provider whose withdrawal validation it can read** (`payment-webhook.js` `PROVIDERS`). A provider without one could move money with no check after the gate.
