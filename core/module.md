---
description: "The core module — the components every agent in the workspace works through: how it behaves, how it talks to the owner, how it codes and commits, how it runs sub-agents, plus the shared function skills and the provider seam."
---

<module>

# core

The `core/` module hosts the agent-facing components — the parts that shape how ANY agent in the
workspace behaves and works, as opposed to `meta/` (the agents, workflows, and CLIs that operate
the rbtv system itself) and `ignite/` (the daemon).

**Unified here 2026-08-23 (owner ruling).** These components previously lived install-local at
`.rbtv/mirror/core/`; the owner ruled the module into the repo, all together. In the same sitting
the module's former repo-side content left: the rbtv CLIs (`rbtv-cli`, `teambuild`, `embed-search`)
moved to `meta/` (each command a component), and the commit skill collapsed into `coding/` as one
reference. The ElevenLabs key moved OUT of the repo tree to the workspace key store
(`.user/config/env/elevenlabs.key`) — a secret never sits where a repo push can carry it.

## Components

| Component | What it is |
|-----------|-----------|
| `behaviour/` | Always-on behaviour rules — how an agent thinks and decides: `kiss` (simplicity before work starts), `root-cause` (fix at the cause), `challenging` (pre-agreement gate, position stability), `problem-framing` (read requests as questions). |
| `communication/` | How agents talk to the owner: the `concise-chat`, `plain-language`, `non-technical-user` rules, the `audio-aware` skill, and the `audio` capability (ElevenLabs transcribe/tts CLI). |
| `coding/` | The code an agent leaves behind: the `coding` skill (four hygiene disciplines), the `commit` skill + its deterministic `tool/commit.py`, and the `improve-codebase-architecture` scan. |
| `functions/` | Cross-cutting function skills — `brainstorm`, `interview`, `investignosis`, `handoff`, `triage`. |
| `providers/` | The seam between the workspace and whoever supplies its compute — the `acct` capability (parked provider logins). |
| `sub-agents/` | Running work through sub-agents: the `sub-agents`, `swarm`, `panel` skills and the `cast` CLI (worker routing and API runs). |
