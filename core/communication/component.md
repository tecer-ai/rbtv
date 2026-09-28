---
description: "The communication component — how a message travels between the owner and the agents (medium capabilities; today: audio) and how agents talk to the owner (the three always-on chat style rules: plain-language, non-technical-user, concise-chat — plus the slack-message-format skill for what is written into a Slack thread)."
---

# communication

`communication/` holds the parts whose subject is the message between the owner and the agents:
the MEDIUM it travels in — turning a voice note into text an agent can act on, turning an
agent's answer into audio the owner can listen to — and, since 2026-08-21 (owner instruction),
the STYLE agents talk to the owner in, as three always-on rules. Since 2026-09-27 (owner
ruling) it also holds the SHAPE of what is written into a Slack thread: the
`slack-message-format` skill, moved from the 0.1 `meta/master` component. Delivering a message —
which channel carries it, what posts it — remains the channel machinery's business, never this
component's.

| Reference | Answers |
|---|---|
| `plain-language` | **How is every word kept understandable?** Define every term on first use, no analogies, no bare name-drops, phases named with their purpose, no unexpanded acronyms, existing terminology only. |
| `non-technical-user` | **How is code talked about with a non-technical owner?** Every technical name paired with a plain translation the owner learns from, every coding decision framed as a behavior change, no raw output dumps. |
| `concise-chat` | **What shape does a chat message take?** Fewest words that carry the message, lead with the decision, never restate file contents, TLDR bullets on long explanations, and the fixed max-3 question format with named options and a recommendation. |
| `slack-message-format` | **How is a message written into a Slack thread?** mrkdwn not markdown, phone-first shape with the answer in the first line, the decision-ask format, the ❓/💭 markers, and moving files in and out of Slack with `stools`. |

The three are deliberately MECE (mutually exclusive, collectively exhaustive): word-level
clarity in `plain-language`, the code-specific overlay in `non-technical-user`, message shape in
`concise-chat` — each carries a boundary note naming the others and restates nothing.
`slack-message-format` is a different axis, not a fourth style rule: the Slack channel's own
structure (mrkdwn, the thread, file logistics), reached on demand as a skill rather than
always-on.

The split that mints it is the owner's (goal `stools-canvas-audio-elevenlabs`, `goal.md`
§ "Divisão de abstração"): **file logistics stay in `stools`** — downloading a voice note from
Slack, uploading an mp3 back to a channel — **and conversion lives here**. Nothing in the `audio`
capability speaks to Slack; the caller hands it a file and takes a file back — the Slack side of
that handoff (addressing the thread, carrying the file) is `slack-message-format`'s, per the
owner's audio/Slack skills split of 2026-08-30.

| Capability | Answers |
|---|---|
| `audio` | **How does a message change medium?** Speech ↔ text through ElevenLabs: transcribe an audio file, synthesize an mp3/ogg, and switch the one language key both verbs read. One CLI, one key in its own `credentials/`, no Slack surface. |

## Entry points

- `references/` — the three rule bodies, exposed with `method: rule` (installed verbatim into
  each harness's rules scaffolding, e.g. `.claude/rules/`), and the skill bodies this component
  exposes (`audio-aware`, `audio-io`, `slack-message-format`), each reached through a thin loader.
- `capabilities/audio/` — `audio.md` (the manual) + `audio.py` (the CLI), its `config.json`,
  `credentials/`, and `test_audio.py`. Not on PATH: a seat reaches it because its `exposes:` names
  the `path` row in `exposure.csv` (`core/communication/audio`) and the cage binds the file.
  `python test_audio.py` must be green after any edit.
- `exposure.csv` — the `audio` row (the mandatory first-party tool inventory), one row per file
  in `references/` (`rule` for the three style rules, `skill` for `audio-aware`, `audio-io`,
  `slack-message-format`), plus `link-tools`.
- `link-tools.py` — puts `audio` on `~/.local/bin`, idempotently, so a caller that
  has that directory on PATH can reach it bare-name. Run it once per box
  (`python3 core/communication/link-tools.py`). It links this component's tools only.
  Without it, `audio` is a manual per-box symlink that does not survive a rebuild or
  a second machine (measured 2026-08-31).

**RELOCATED 2026-08-21** from the `communication/` MODULE (`mirror/communication/audio/`) to
`core/communication/`, where the former component `audio` is now a capability — owner instruction.
This resolves the one-component tension the old `module.md` recorded (the KG's module membership
test asks for ≥2 components; that module had one, and sat at module depth only so a seat's
`exposes:` could resolve it). At component depth inside `core/`, the reference resolves as
`core/communication/audio` with no such tension. The registry settles formal membership
(`PRIN-10`).
