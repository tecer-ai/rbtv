# ElevenLabs

`elevenlabs` transcribes audio, synthesizes speech, lists available voices and manages the installation's language setting. Run `elevenlabs --help` and the selected verb's help for inputs, outputs and examples.

Install with `rbtv add --component connectors/elevenlabs`. Python and the `requests` package must be available to the interpreter that runs the command. `rbtv doctor` reports whether those dependencies are present. Use your Python environment's package installer to add `requests` when needed; do not override an operating system's package protections.

The process environment's `ELEVENLABS_API_KEY` takes precedence over `.rbtv/config/env/.env`. The installation is the first ancestor of the working folder with `.rbtv/config/install.json`. Outside an installation, only the process environment supplies the key. Help and local language operations do not require or read credentials.

Language is saved in `.rbtv/config/elevenlabs/config.json`, never in source. The default is Portuguese (`pt`). The language command accepts two- or three-letter codes, normalizing case; the provider decides which languages each model supports. Outside an installation it can read the default but refuses to persist a change.

Transcription uses `scribe_v2` by default; synthesis uses `eleven_flash_v2_5`. A caller can select another model in the command interface. Synthesis resolves the first available account voice unless `--voice` selects an exact voice. `voices` returns identifiers and a continuation token when further pages exist; an empty list succeeds. The [provider's voice-list contract](https://elevenlabs.io/docs/api-reference/voices/search) defines pagination. Speech generation still requires an available voice.

Use `--file` or stdin for prose that contains shell-sensitive characters. Apply the installation glossary to uncertain names and terms in transcripts; an empty transcription is a failure, not evidence that the speaker said nothing. Write spoken replies as sentences, leaving paths, identifiers and copyable material in accompanying text. When Ignite already generates audio from a reply, do not generate a second copy manually.

File transfer belongs to the channel's tool, such as `slack download` or `slack upload`. This command takes local files or text and returns text or an audio-file path.

For offline verification, run `python test_elevenlabs.py` from this folder. Tests use temporary installations, synthetic keys and a local HTTP stub. `ELEVENLABS_API_URL` selects a test API base; production defaults to ElevenLabs. Never point a process carrying a real key at an untrusted base URL.
