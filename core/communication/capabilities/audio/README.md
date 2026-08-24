# audio — ElevenLabs speech-to-text and text-to-speech

One CLI, three verbs, JSON on stdout. It converts; it never fetches or posts — a Slack voice note
reaches disk through `stools download`, and an answer reaches a channel through `stools upload`
(the owner's split, `goal.md` § "Divisão de abstração").

**Paths on this workspace** (everything below is relative to the workspace root):

| What | Where |
|------|-------|
| the CLI | `3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py` |
| the config | `3-resources/tools/rbtv/core/communication/capabilities/audio/config.json` |
| the key | `.user/config/env/elevenlabs.key` (workspace key store — see "The key") |
| the checks | `3-resources/tools/rbtv/core/communication/capabilities/audio/test_audio.py` — `python3 test_audio.py`, no network |

Nothing is installed on `PATH`. A seat reaches it because its `exposes:` names the `path` row in
`exposure.csv`; a console session runs it by path. `python3` and `requests` are the only
requirements (`dependencies.txt`).

## The three verbs

```bash
# audio file -> text            (exit 0 + {"text": ...}; a silent recording exits non-zero)
3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py transcribe ./voice-note.m4a

# text -> a playable file       (the --out extension picks the format: .mp3, .ogg, .opus)
3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py tts --text "Bom dia." --out ./answer.mp3
3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py tts --file ./answer.txt --out ./answer.mp3
cat answer.txt | 3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py tts --file - --out ./answer.ogg

# read the language both verbs above run in
3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py language

# rewrite it — takes effect immediately, for the WHOLE integration
3-resources/tools/rbtv/core/communication/capabilities/audio/audio.py language <2-or-3-letter-code>
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

The key lives in the WORKSPACE's key store, outside the component's folder (owner ruling
2026-08-23, superseding `d-elevenlabs-key-location-2026-08-18` for this workspace: the component
moved into the rbtv REPO tree, and a secret never sits where a repo push can carry it). `audio.py`
resolves the store by walking up from its own location to the directory holding `.rbtv/`.

1. **`<workspace>/.user/config/env/elevenlabs.key`** — one line, the key itself. This is the
   primary source; when it holds a key, that key is used. The vault `.gitignore` excludes it.
2. **`ELEVENLABS_API_KEY`** — the override, read when the file above is missing or empty — and a
   caged seat's route, since the key store is masked inside cages.

Neither present → **every verb** exits non-zero and names both places, with no traceback.

To place the key (the owner's step, run from a normal shell at the workspace root):

```bash
printf '%s' 'YOUR-ELEVENLABS-KEY' > .user/config/env/elevenlabs.key
chmod 600 .user/config/env/elevenlabs.key
```

The expected filename is exactly **`elevenlabs.key`** — one line, the key itself, nothing else.

⚠ **A caged seat reads that file only if its own descriptor SPELLS
`.user/config/env/elevenlabs.key` — the exact path, not a parent of it.** The cage's pattern floor
carries `**/*.key` (`ignite/server/spawn/private-scope.js`, `DEFAULT_PATTERNS`) and the file also
sits on the private deny list, so it is masked for any seat that does not name it — a merely
BROADER grant is not enough (measured 2026-08-20 on the folder shape this key previously used:
only the spelled path read, unspelled sibling credential folders listed empty). Give any seat that
must read the key (the live prober, the channel master) that exact path in its descriptor, or hand
it `ELEVENLABS_API_KEY`; the grant is effective at that seat's NEXT launch, never inside a live
session.

The `language` verb demands the key too, though it makes no API call: the contract this component
is built to says every verb refuses without one (`goal.md` clause 9). To read the language of an
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
with the `language` verb, which any seat holding the CLI — the channel master included — can run;
the change persists in `config.json` and the next `transcribe` or `tts` reads it.

## Models and voices — what the defaults are, and why

Sourced 2026-08-18 from `api.elevenlabs.io/openapi.json` and the docs pages beside it; the full
findings with URLs are in this goal's `seats/audio-component-smith/scratchpad/probes/`.

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

No Slack surface: no Slack SDK import, no call to Slack's web API, no channel ids. The two greps
that check it (`goal.md` clause 5) find nothing here, and this sentence is written so that they
still find nothing when they run over this file. No PyYAML anywhere either — the
workspace's private-scope floor masks `yaml/tokens.py` and bricks that import inside every cage,
which is why the config is JSON.
