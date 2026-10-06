# `settings.json`

The file in an [rbtv agent](agent.md#rbtv-agent)'s folder that contains values specific to that agent's job, such as the sources it works from. The agent reads it when a task needs one of them, so it is a [cognitive unit](cognitive-unit.md). Its contents depend on the agent, but its layout follows one convention: one top-level key per tool or concern, such as `slack` or `sources`, with the paths written relative to the installation root, and no secrets. A secret, such as a token, is named by the environment variable that contains it, as in [configuration](config.md). Its [template](../templates/settings-json.md) shows that convention. The file is one file in the agent's folder, not a folder of files.

The file is not shared through git. The agent's `agent.md`, `agent.json`, `memory/` folder, and `_artifacts/board.md` are tracked instead.
