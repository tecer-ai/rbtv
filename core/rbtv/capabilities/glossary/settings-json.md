# `settings.json`

`settings.json` holds the job-specific values an agent’s tasks use, beside `prompt.md` and [agent.json](agent-json.md). It is configuration data, not a [cognitive unit](cognitive-unit.md).

Add a value when a current task needs it and it changes independently of the prompt. Do not repeat a value already owned by the prompt, agent record or another configuration file. Group values by tool or concern, with one top-level key for each.

Write paths relative to the installation root. For secrets, store the environment-variable name the consumer expects, not the value; [Config](config.md) routes to the value store. Keep this machine’s settings out of git rather than assuming the installer excludes them automatically. Follow [Agent](agent.md) when sharing the folder’s other content.

rbtv creates an empty object when the file is missing and preserves an existing file during agent updates. Edit the settings here and verify them through a task or tool that consumes them. The file remains one record; do not split it into a folder of settings files.

Use the consumer’s required JSON type for each value:

```text
{
  "<tool-or-concern>": {
    "<setting>": <value>
  }
}
```
