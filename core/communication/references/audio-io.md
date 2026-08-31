---
id: audio-io
description: "How an agent works with audio through the ElevenLabs capability: turn a voice note into text (`transcribe`), turn text into a playable file (`tts`), and switch the one language key both directions read. Channel-agnostic — it takes a path and returns a path, and never touches Slack or any other chat surface."
---

<reference>
Form: PROCEDURAL (command recipes) with a normative edge (the full-path rule and the
config-key-not-a-flag rule are binding).
Enforcement: advisory. Reach: any agent that must hear or speak.

## What this capability is, and what it is NOT

The owner talks to agents from a phone: a voice note is the natural input and a spoken answer is
often the natural output. This capability is the CONVERSION half of that, and ONLY that half —
it takes a file path and returns a file path.

**It touches no chat service.** Moving a file between a channel and disk belongs to that
channel's own tool — over Slack that is `stools`, and the `slack-message-format` skill carries
those recipes. Today Slack is the only channel; that is exactly why the two halves are separate
skills. Never look for a channel id, a workspace flag or an upload verb here: none exists.

## How you reach it

**Which command NAME works depends on your vantage, and the vantages disagree.** Measured
2026-08-28 and 2026-08-31:

| Your vantage | A bare `audio <verb>` | Why |
|---|---|---|
| a CAGED seat that declares `audio` in its `exposed-clis` | **works** | the sandbox materializes a `~/.rbtv-bin/audio` SYMLINK from that declaration |
| a CAGED seat that does not declare it | **exits 127**, command not found | `~/.rbtv-bin` is built inside a sandbox; it does not exist on the real filesystem at all |
| an UNCAGED daemon-spawned staff sitting, on a box where `python3 core/communication/link-tools.py` has been run | **works** | `~/.local/bin/audio` (the link that script installs) is on PATH via `spawn.js`'s `local-bin: true` grant |
| an UNCAGED chair on a box that has never run that install step (a fresh clone, an unrebuilt box) | **exits 127**, command not found | the symlink does not exist yet — running the install step, once per box, is what creates it |

Uncaged means unmasked, NOT better-equipped — the uncaged chairs never declared this CLI, so a
caged shim was never on the table for them; the install step above gives them a different route to
the same bare name, conditional on having been run on that box.

**So DEFAULT to the full path form.** It is the one form correct in EVERY vantage, which is what
any instruction that cannot know its reader's cage needs; the bare name is a caged-seat
convenience, never the documented recipe. Every path below is relative to the workspace root.

| What | Where |
|---|---|
| the CLI | `3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py` |
| the ElevenLabs key | `.user/config/env/elevenlabs.key` — one line, the key itself |
| the language, for both directions | `3-resources/tools/rbtv/core/communication/capabilities/audio/config.json` |

Every verb prints ONE JSON object on stdout; refusals print `what / why / fix` on stderr and exit
non-zero — **2** when the CLI refused locally (no key, unreadable input, unusable `--out`), **1**
when the call failed or came back unusable. It never exits 0 with an empty transcript or a 0-byte
audio file.

## Listening — an audio file becomes text

The file is a POSITIONAL argument, and there is no language flag:

```
python3 3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py transcribe /tmp/voice-note.m4a
```

Read `.text` from the JSON. A silent or speech-free recording exits non-zero rather than handing
you an empty transcript — never read a non-zero exit as "the speaker said nothing".

**A transcript is garbled input, not finished text.** Dictation carries self-corrections, hesitant
numbers and mangled names. The `audio-aware` skill of this same component is what ungarbles one;
apply it before you act on a transcript or write any of it into the vault.

## Speaking — text becomes a playable file

`--out` is required and its EXTENSION picks the format (`.mp3`, `.ogg`, `.opus`):

```
python3 3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py tts --file ./answer.txt --out /tmp/answer.mp3
```

Prefer `--file` over `--text` for prose — the shell mangles backticks, quotes and `$(...)` before
the CLI ever sees them; `--file -` reads stdin. `--voice <id>` pins a voice, otherwise the
account's first voice is used. `--text` and `--file` are mutually exclusive and one is required.

**Write for the ear, not for the eye.** Speech carries no formatting: a file path, an id, a table
or a bulleted list read aloud is noise. Speak the outcome and the reasoning; leave paths, ids and
anything the listener must copy in the accompanying text message.

## The language is a config key, not a flag

Both verbs read `language` from this component's `config.json` (default `pt`). No verb takes a
language flag, and none is compiled into the CLI. Change it for the whole integration — both
directions at once — with the `language` verb; the change persists and the next `transcribe` or
`tts` reads it.

## What a caged seat can and cannot do today

**A caged seat cannot reach the ElevenLabs key, so it cannot transcribe or synthesize.** Measured
2026-08-28: `ELEVENLABS_API_KEY` is unset inside cages, and the key store is masked there by the
cage's `**/*.key` pattern floor — a cage sees a zero-length character device, which is a MASK and
NOT an absent key. Never read that as "the key is missing" and never go asking for one to be
placed. Every verb refuses in-cage with exit 2, naming both key routes; that refusal is correct
behaviour, not a broken install.

- **Who can run it today:** the uncaged chairs — a seat running outside a cage, and the owner's
  own console — where the key store is a real file.
- **What a caged seat does instead:** hand the CONVERSION to an uncaged chair by mail, rather than
  retrying against a wall known to stand. Only this capability needs the key; a channel tool that
  merely moves the file is unaffected, so a caged seat can still fetch the note and still post the
  answer.
- **What would change it:** a caged seat reads the key only if its own descriptor SPELLS
  `.user/config/env/elevenlabs.key` — the exact path, never a parent of it, because a merely
  broader grant does not pierce the mask — or if it is handed `ELEVENLABS_API_KEY`. Either takes
  effect at that seat's NEXT launch, never inside a live session.

Flags are documented by the CLI itself — `<path> --help`, and `<path> <verb> --help` — and in
`3-resources/tools/rbtv/core/communication/capabilities/audio/README.md`. This reference does not
restate them, because the second copy is the one that goes stale.
</reference>
