# communication tools

This folder holds the tools of the `communication` component: `audio` (transcribes audio to text and speaks text as audio), `gtools` (Google Workspace from one command) and `stools` (the entry point for the Slack command, which allows a post made as the owner only under a recorded grant). The program of `gtools` is outside this repository, at the path its record names. Only `audio` has a page. A tool's program, record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [audio](audio/audio.md) | The three verbs of `audio`, its key, its one language setting and what the tool does not do | Change or call the tool within its boundary | changing, reviewing or debugging a file under `audio/`, or wiring a caller to it |
| [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding or changing a verb, an option, help text, output or an error message of a tool in this folder |
