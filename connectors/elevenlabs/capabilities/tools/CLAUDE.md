# elevenlabs tools

This folder holds the tool of the `elevenlabs` component: `elevenlabs` (ElevenLabs speech-to-text and text-to-speech from one command: transcribe, tts, voices, language). A tool's program, record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [elevenlabs](elevenlabs/elevenlabs.md) | What the `elevenlabs` CLI is: its verbs, key and language resolution, models and voices, and its self-check | Start any work on the tool from its own description | changing, reviewing or debugging a file under `elevenlabs/` |
| [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding or changing a verb, an option, help text, output or an error message of `elevenlabs` |
