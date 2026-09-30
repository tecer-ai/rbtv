# communication

`communication/` holds the parts whose subject is the message between the owner and the agents:
the MEDIUM it travels in — turning a voice note into text an agent can act on, turning an
agent's answer into audio the owner can listen to — and, since 2026-08-21 (owner instruction),
the STYLE agents talk to the owner in, as three always-on rules. Since 2026-09-27 (owner
ruling) it also holds the SHAPE of what is written into a Slack thread: the
`slack-message-format` skill. Delivering a message —
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

The owner's split is: **file logistics stay in `stools`** — downloading a voice note from
Slack, uploading an mp3 back to a channel — **and conversion lives here**. Nothing in the `audio`
capability speaks to Slack; the caller hands it a file and takes a file back — the Slack side of
that handoff (addressing the thread, carrying the file) is `slack-message-format`'s, per the
owner's audio/Slack skills split of 2026-08-30.

| Capability | Answers |
|---|---|
| `audio` | **How does a message change medium?** Speech ↔ text through ElevenLabs: transcribe an audio file, synthesize an mp3/ogg, and switch the one language key both verbs read. One CLI, one key in the workspace env file, no Slack surface. |

## Entry points

- `rules/` — the three rule units (installed verbatim into
  each harness's rules scaffolding, e.g. `.claude/rules/`), and the skill units
  (`audio-aware`, `audio-io`, `slack-message-format`), each reached through a thin loader.
- `capabilities/audio/audio.md` (the manual). The CLI, `config.json`, and `test_audio.py` sit in `capabilities/tools/audio/`. Run it by path; `capabilities/tools/audio/audio.json` inventories the `audio` tool.
  `python test_audio.py` must be green after any edit.
- `rules/` — one rule unit per file (`plain-language`, `non-technical-user`, `concise-chat`); `skills/` — `audio-aware`, `audio-io`, `slack-message-format`; `capabilities/tools/link-tools/link-tools.json` — the `link-tools` tool.
- `link-tools.py` — legacy per-box helper that puts `audio` on `~/.local/bin`.
  Installing the component now books `audio` in `~/.rbtv/bin` and puts that
  directory on the user PATH; the helper remains for existing callers.

**RELOCATED 2026-08-21** from the `communication/` MODULE (`mirror/communication/audio/`) to
`meta/communication/`, where the former component `audio` is now a capability — owner instruction.
This resolves the one-component tension (the KG's module membership
test asks for ≥2 components; that module had one). At component depth inside `core/`, the reference resolves as
`meta/communication/audio` with no such tension. The registry settles formal membership
(`PRIN-10`).
