# audio — ElevenLabs speech-to-text and text-to-speech

One CLI, three verbs, JSON on stdout. It converts; it never fetches or posts — a Slack voice note
reaches disk through `stools download`, and an answer reaches a channel through `stools upload`
as separate steps.

**Paths on this workspace** (everything below is relative to the workspace root):

| What | Where |
|------|-------|
| the CLI | `3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py` |
| the config | `3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/config.json` |
| the key | `ELEVENLABS_API_KEY` in the workspace env file (`env_file` in `rbtv.json` — see "The key") |
| the checks | `3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/test_audio.py` — `python3 test_audio.py`, no network |

Run it by path, or install `meta/communication` and use the bare `audio`
command from a new shell. `link-tools.py` is the older `~/.local/bin` helper.
`python3` and `requests` are the only requirements (`dependencies.txt`).

## The three verbs

```bash
# audio file -> text            (exit 0 + {"text": ...}; a silent recording exits non-zero)
3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py transcribe ./voice-note.m4a

# text -> a playable file       (the --out extension picks the format: .mp3, .ogg, .opus)
3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py tts --text "Bom dia." --out ./answer.mp3
3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py tts --file ./answer.txt --out ./answer.mp3
cat answer.txt | 3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py tts --file - --out ./answer.ogg

# read the language both verbs above run in
3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py language

# rewrite it — takes effect immediately, for the WHOLE integration
3-resources/tools/rbtv/meta/communication/capabilities/tools/audio/audio.py language <2-or-3-letter-code>
```

`--file` exists because the shell mangles inline text carrying backticks, quotes or `$(...)`
before the CLI ever sees it. For prose — which is what this tool is given — prefer it.

Flags are documented by the CLI itself: `audio.py --help`, `audio.py <verb> --help`. This README
does not restate them, because the second copy is the one that goes stale.

**Output.** Every verb prints ONE JSON object on stdout and nothing else. Every refusal prints
`what / why / fix` on stderr and exits non-zero: **2** when this CLI refused locally (no key, an
unreadable input, a bad language code, an unusable `--out`), **1** when the remote call failed or
came back unusable (invalid key, an API error, a silent recording, empty audio). It never exits 0
with an empty transcript or a 0-byte audio file.

## The key

The key lives in the WORKSPACE's env file, outside the component's folder and outside every repo
push (owner ruling 2026-09-27: every key lives in one gitignored `.env`). `audio.py` finds the
workspace by walking up from its own location to the directory holding `rbtv.json`, and reads the
env file that file's `env_file` field names (default `.rbtv/config/env/.env`).

1. **`ELEVENLABS_API_KEY=<key>`** — one line in that env file. This is the primary source; when it
   holds a key, that key is used. The vault `.gitignore` excludes the file.
2. **`ELEVENLABS_API_KEY` in the process environment** — read when the env file has no such line,
   and the route for a seat that cannot read the env file.

Neither present → **every verb** exits non-zero and names both places, with no traceback.

To place the key (the owner's step), add the line `ELEVENLABS_API_KEY=<key>` to the env file
(`chmod 600` on the file).

The `language` verb demands the key too, though it makes no API call. To read the language of an
install that has no key, read `config.json` — it is one JSON object.

## The one language key

`config.json`:

```json
{
  "language": "pt"
}
```

`language` is the ONLY place a language is set for this component's whole ElevenLabs integration —
transcription and synthesis both. The default is `pt`. No verb takes a language flag and no
language is compiled into the CLI (`test_audio.py` asserts that against the source). Change it
with the `language` verb. The change persists in `config.json`; the next `transcribe` or `tts`
reads it.

## Models and voices — what the defaults are, and why

Sourced 2026-08-18 from `api.elevenlabs.io/openapi.json` and the docs pages beside it; the full
findings with URLs were recorded in the original audio research notes.

- **Transcription: `scribe_v2`.** ElevenLabs' current batch STT model (`scribe_v1` is marked
  deprecated on `docs/overview/models`). Portuguese sits in its top accuracy tier — the capability
  page lists "Portuguese (por)" under *Excellent (≤ 5% WER)*. The config's language is sent as
  `language_code`, which the docs describe as improving accuracy when the language is known.
- **Synthesis: `eleven_flash_v2_5`, and this is a deliberate trade.** The docs recommend
  `eleven_multilingual_v2` for quality and it does support Portuguese — but the same docs say
  `language_code` "is not supported for multilingual_v2 models", which would leave the language
  key unable to reach TTS at all. `eleven_flash_v2_5` covers "all `eleven_multilingual_v2`
  languages plus `hu`, `no`, `vi`" (`docs/models`), so it is pt-capable, and it takes the language
  code. For maximum fidelity pass `--model eleven_multilingual_v2` — then the language rides in
  the text you send, not in the config key.
- **Voice: resolved at run time, never compiled in.** The CLI calls `GET /v2/voices` and uses the
  account's first voice unless `--voice <id>` pins one. The docs' own example voices (`George`,
  `JBFqnCBsd6RMkjVDRZzb`) are *Default voices*, which per
  `docs/help-center/product/voices/my-voices/what-are-default-voices` **expire 2026-12-31 and are
  unavailable to accounts created after March 2026** — a hardcoded id would ship broken for a
  newly provisioned account. On Portuguese: `docs/capabilities/voices` says "All ElevenLabs voices
  support multiple languages" and advises choosing an accent matching the target language; no docs
  page maps a voice id to a language, so pick one per account with the List-voices `language`
  filter and each voice's `verified_languages`, then pin it with `--voice`.

## What it is not

No Slack SDK import, web API call, or channel id is needed here. The config is JSON and read
through Python's standard library.
