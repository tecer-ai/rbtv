---
description: "The communication component — how a message travels between the owner and the agents (medium capabilities; today: audio) and how agents talk to the owner (the three always-on chat style rules: plain-language, non-technical-user, concise-chat)."
---

# communication

`communication/` holds the parts whose subject is the message between the owner and the agents:
the MEDIUM it travels in — turning a voice note into text an agent can act on, turning an
agent's answer into audio the owner can listen to — and, since 2026-08-21 (owner instruction),
the STYLE agents talk to the owner in, as three always-on rules. Where a message lands
(Slack, files) is still never this component's business.

| Reference | Answers |
|---|---|
| `plain-language` | **How is every word kept understandable?** Define every term on first use, no analogies, no bare name-drops, phases named with their purpose, no unexpanded acronyms, existing terminology only. |
| `non-technical-user` | **How is code talked about with a non-technical owner?** Every technical name paired with a plain translation the owner learns from, every coding decision framed as a behavior change, no raw output dumps. |
| `concise-chat` | **What shape does a chat message take?** Fewest words that carry the message, lead with the decision, never restate file contents, TLDR bullets on long explanations, and the fixed max-3 question format with named options and a recommendation. |

The three are deliberately MECE (mutually exclusive, collectively exhaustive): word-level
clarity in `plain-language`, the code-specific overlay in `non-technical-user`, message shape in
`concise-chat` — each carries a boundary note naming the others and restates nothing.

The split that mints it is the owner's (goal `stools-canvas-audio-elevenlabs`, `goal.md`
§ "Divisão de abstração"): **file logistics stay in `stools`** — downloading a voice note from
Slack, uploading an mp3 back to a channel — **and conversion lives here**. Nothing here speaks to
Slack; the caller hands it a file and takes a file back.

| Capability | Answers |
|---|---|
| `audio` | **How does a message change medium?** Speech ↔ text through ElevenLabs: transcribe an audio file, synthesize an mp3/ogg, and switch the one language key both verbs read. One CLI, one key in its own `credentials/`, no Slack surface. |

## Entry points

- `references/` — the three rule bodies, exposed with `method: rule` (installed verbatim into
  each harness's rules scaffolding, e.g. `.claude/rules/`).
- `capabilities/audio/` — `audio.md` (the manual) + `audio.py` (the CLI), its `config.json`,
  `credentials/`, and `test_audio.py`. Not on PATH: a seat reaches it because its `exposes:` names
  the `path` row in `exposure.csv` (`core/communication/audio`) and the cage binds the file.
  `python test_audio.py` must be green after any edit.
- `exposure.csv` — the `audio` row (the mandatory first-party tool inventory) plus one
  `reference`/`rule` row per file in `references/`, plus `link-tools`.
- `link-tools.py` — puts `audio` on `~/.local/bin`, idempotently, so an UNCAGED chair (which never
  gets a cage's `~/.rbtv-bin` shim) can also reach it bare-name: an uncaged daemon-spawned sitting
  gets `~/.local/bin` on PATH via `ignite/supervisor/spawn/spawn.js`'s `local-bin: true` grant.
  Run it once per box (`python3 core/communication/link-tools.py`) — analogous to, and
  deliberately separate from, `ignite/deploy/link-tools.py` (that script is scoped to the ignite
  module only, by its own docstring). Without it, `audio` is a manual per-box symlink that does not
  survive a rebuild or a second machine (measured 2026-08-31).

**RELOCATED 2026-08-21** from the `communication/` MODULE (`mirror/communication/audio/`) to
`core/communication/`, where the former component `audio` is now a capability — owner instruction.
This resolves the one-component tension the old `module.md` recorded (the KG's module membership
test asks for ≥2 components; that module had one, and sat at module depth only so a seat's
`exposes:` could resolve it). At component depth inside `core/`, the reference resolves as
`core/communication/audio` with no such tension. The registry settles formal membership
(`PRIN-10`).
