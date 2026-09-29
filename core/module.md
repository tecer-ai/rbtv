---
description: "The core module — the components every agent in the workspace works through: how it behaves, how it talks to the owner, how it codes and commits, how it runs sub-agents, plus the shared function skills and the provider seam."
---

<module>

# core

The `core/` module hosts the agent-facing components — the parts that shape how ANY agent in the
workspace behaves and works, as opposed to `meta/` (the agents, workflows, and CLIs that operate
the rbtv system itself) and `ignite/` (the daemon).

The ElevenLabs key is `ELEVENLABS_API_KEY` in the workspace env file (`env_file` in `rbtv.json`),
never in the repo tree — a secret never sits where a repo push can carry it.

## Components

| Component | What it is |
|-----------|-----------|
| `behaviour/` | Always-on behaviour rules — how an agent thinks and decides: `kiss` (simplicity before work starts), `root-cause` (fix at the cause), `challenging` (pre-agreement gate, position stability), `problem-framing` (read requests as questions). |
| `communication/` | How agents talk to the owner: the `concise-chat`, `plain-language`, `non-technical-user` rules, the `audio-aware` skill, the `slack-message-format` skill (the shape of what is written into a Slack thread), and the `audio` capability (ElevenLabs transcribe/tts CLI). |
| `coding/` | The code an agent leaves behind: the `coding` skill (four hygiene disciplines), the `commit` skill + its deterministic `tool/commit.py`, and the `improve-codebase-architecture` scan. |
| `functions/` | Cross-cutting function skills — `brainstorm`, `interview`, `investignosis`, `handoff`, `triage`. |
| `providers/` | The seam between the workspace and whoever supplies its compute — the `acct` capability (parked provider logins). |
| `sub-agents/` | Running work through sub-agents: the `sub-agents`, `swarm`, `panel` skills and the `cast` CLI (worker routing and API runs). |
