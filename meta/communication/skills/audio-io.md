---
name: audio-io
description: "Use to transcribe or speak with audio, set its language, or check the older local audio PATH link with link-tools. Channel-agnostic: takes and returns file paths."
---

<reference>
Form: PROCEDURAL (command recipes) with a normative edge (the config-key-not-a-flag rule is binding).
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

After installing `meta/communication`, run `audio` by name from a new shell:
rbtv links it into `~/.rbtv/bin` and puts that directory on PATH.
The full script path below also works without an install.

`link-tools --check` inspects the older `~/.local/bin/audio` link. Run `link-tools`
to repair that link only when the task is to maintain the older local link.

| What | Where |
|---|---|
| the CLI | [audio.py](../capabilities/tools/audio/audio.py) |
| the ElevenLabs key | `ELEVENLABS_API_KEY` in the installation env file (`env_file` in `rbtv.json`) |
| the language, for both directions | [config.json](../capabilities/tools/audio/config.json) |

Every verb prints ONE JSON object on stdout; refusals print `what / why / fix` on stderr and exit
non-zero — **2** when the CLI refused locally (no key, unreadable input, unusable `--out`), **1**
when the call failed or came back unusable. It never exits 0 with an empty transcript or a 0-byte
audio file.

## Listening — an audio file becomes text

The file is a POSITIONAL argument, and there is no language flag:

```
python3 3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py transcribe /tmp/voice-note.m4a
```

Read `.text` from the JSON. A silent or speech-free recording exits non-zero rather than handing
you an empty transcript — never read a non-zero exit as "the speaker said nothing".

**A transcript is garbled input, not finished text.** Dictation carries self-corrections, hesitant
numbers and mangled names. The `audio-aware` skill of this same component is what ungarbles one;
apply it before you act on a transcript or write any of it into the vault.

## Speaking — text becomes a playable file

For an Ignite agent reply, `replies[].audio: true` already generates and attaches speech from
`replies[].text`. Do not run `audio tts` for that reply. Use this CLI when you need a separate
audio file; if you attach it through `replies[].files`, set `replies[].audio: false`.

`--out` is required and its EXTENSION picks the format (`.mp3`, `.ogg`, `.opus`):

```
python3 3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py tts --file ./answer.txt --out /tmp/answer.mp3
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

Flags are documented by the CLI itself — `<path> --help`, and `<path> <verb> --help` — and in
[README.md](../capabilities/tools/audio/README.md). This reference does not
restate them, because the second copy is the one that goes stale.
</reference>
