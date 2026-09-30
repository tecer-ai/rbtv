---
name: create-agent
description: "Use when creating a working Ignite agent: resolve the missing choices in one grouped question, write the agent file, then run ignite-agent install and ignite-agent connect. Covers the agent file, the launch setting, the Slack channel or direct messages, and an optional schedule. Never an owner checklist. Do not use it to change a launch setting or a schedule on an agent that already exists."
---

# create-agent

Creating an Ignite agent is two commands. Run `ignite-agent install --help` and `ignite-agent connect --help` and use those flags. NEVER invent a flag. NEVER hand the owner a list of steps you can run.

## Resolve, then ask once

Collect the agent file (name, purpose, and any skills or reference paths the owner named), the launch setting, channel name or DM, and any schedule from the request. Ask ONLY for what is still missing, in ONE grouped question. NEVER ask again on a later turn.

- Purpose MUST be the owner's words, written into the agent file you pass to `ignite-agent install`. NEVER invent a purpose. The file's frontmatter `name` MUST match `[a-z0-9][a-z0-9-]{0,63}`. Derive the name from the purpose when that derivation is one legal slug. Include it in the question only when the derivation is ambiguous.
- Launch: `ignite-agent install` requires `--harness`, `--model`, and `--effort` together. If the owner named them, pass all three. NEVER pass a number as the stored effort; the installer stores the rung word. NEVER substitute a model the owner did not name. Include the three in the question when any is missing.
- Channel: `ignite-agent connect` takes `--channel-name` or `--dm`. NEVER invent a channel name. Include the choice in the question when the owner has not made it.
- Skills: Ignite installs its standard units. The agent file lists ONLY an extra the purpose needs and the owner named. NEVER invent a skill id. A reusable ability MUST be a skill named in the agent file. NEVER put a value that belongs to this one agent inside a skill.
- Reference paths: pass a path the owner named that exists, in the agent file's `folders` or its body. NEVER invent a path.
- Settings: values specific to this one agent go in the home's `settings.json` after install. NEVER invent a setting the owner did not name. The installer writes `{}` when they named none.
- Schedule: pass `--schedule-json` to `ignite-agent connect` ONLY when the owner asked for a schedule AND named both a cadence and a timezone. NEVER invent either. Omit the flag when they did not ask. The file MUST match the shape in `ignite-agent connect --help`.

## Run

Write the agent file, then run `ignite-agent install` and `ignite-agent connect` yourself. NEVER create the channel, the route, the home, or the installs by hand.

If install refuses because the agent exists, run `ignite-agent update` for the units and `ignite-agent connect` to finish a partial connection. NEVER start a second agent to work around a partial one.

## Report

Report the `link:` line from connect when it printed one. A DM agent has no channel link; say that.

NEVER say the agent is ready when a command exited non-zero. NEVER claim a channel, route, or unit install that the command did not confirm.

A creation-time schedule is stored on a board conversation (`<team>:<channel>:board`) because no Slack thread exists yet. The board records the check. The agent reports a result of that check with `ignite-agent post` until a real thread exists. Say so when you created a schedule.
