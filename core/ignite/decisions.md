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
