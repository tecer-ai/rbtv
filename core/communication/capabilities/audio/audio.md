---
description: The audio capability — speech to text and text to speech through ElevenLabs, as one path-invoked CLI with three verbs. Transcribe a voice note, synthesize an mp3/ogg, switch the one language key both verbs read. It touches no chat service; a caller hands it a file and takes a file back.
---

# audio

> A capability of the `core/communication` component (relocated 2026-08-21 from the
> `communication/` module, where it was a component of its own). Seats reach it as
> `core/communication/audio`.

The owner talks to the agents from a phone. Typing a long request is slow and reading a wall of
text is slower, so a voice note is the natural input and an audio answer is often the natural
output — and until this component existed, a voice note that reached Slack was unusable by any
agent and every answer was text (goal `stools-canvas-audio-elevenlabs`, `goal.md`
job-to-be-done).

This capability is the CONVERSION half of that job, and only that half. **File logistics stay in
`stools`** — `stools download` fetches the voice note, `stools upload` posts the mp3 back (owner
constraint, `goal.md` § "Divisão de abstração"). It never speaks to Slack: it takes a
path and returns a path.

## The entry point

`audio.py` — one CLI, three verbs, machine-readable JSON on stdout:

| Verb | Does |
|------|------|
| `transcribe <file>` | an audio file → its text |
| `tts --text/--file --out <file>` | text → a playable mp3/ogg |
| `language [<code>]` | reads, or rewrites, the ONE language key both verbs above read |

It self-documents: `audio.py --help`, and `audio.py <verb> --help` for a verb. The command
inventory lives in the parser and nowhere else — this file does not restate flags, and neither
does the README.

## What a reader needs before entering

- **The key is the capability's own.** It is read from `credentials/elevenlabs.key` — the
  stools/gtools pattern, so a CLI released into a seat's cage carries its secret with it
  (owner-ruled, goal `decisions.md#d-elevenlabs-key-location-2026-08-18`). `ELEVENLABS_API_KEY`
  is accepted when that file holds nothing. Neither present → every verb refuses, exit != 0,
  naming both places. `README.md` is the one home of that detail.
- **One language key governs both verbs.** `config.json`'s `language` field, default `pt`. No
  verb pins a language anywhere else (`goal.md` clause 11), and the `language` verb is how it
  changes — including from the channel master's own hands (clause 12).
- **It is a `path` part, not a skill.** Nothing is installed on `PATH`: a seat reaches it because
  its `exposes:` names the `path` row in `exposure.csv`, and the cage binds the file.

## What this capability is NOT

- **Not a Slack surface.** No Slack SDK import, no call to Slack's web API, no channel ids — that
  split is the owner's, and `exposure.csv`'s row plus the README's command shapes are how a caller
  wires the two sides together.
- **Not a router.** Where a transcript or an mp3 lands is the caller's decision, governed by the
  workspace's own routing rules.
- **Not a voice library.** It sends the one default voice and model the README names as
  pt-capable, and takes a different one only when the caller passes it.
