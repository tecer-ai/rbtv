---
description: Use when creating a working primary agent — home, instructions, Slack channel, route, skills, and an optional schedule — by running ignite-agent create. Ask only for choices still missing, in one grouped question.
exposes-cli:
  - ignite-agent
inputs: the owner's request for a new primary agent, plus whatever of purpose, slug, channel name or DM, extra skills, reference paths, launch setting, schedule, and agent-specific settings they have already named
outcome: a primary agent exists and the owner has been told its channel link, or the owner has been told exactly which setup step is incomplete — never a checklist of steps the caller can run
outputs: the ignite-agent create result (channel link and self-check) reported to the owner
---

# create-primary-agent

Creating a primary agent is this command. Run `ignite-agent create --help` and use those flags. NEVER invent a flag. NEVER hand the owner a list of steps you can run.

## Resolve, then ask once

Collect purpose, slug, channel name or DM, extra skills, reference paths, launch setting, and any schedule from the request. Ask ONLY for what is still missing, in ONE grouped question. NEVER ask again on a later turn.

- Purpose MUST be the owner's words, written to a file you pass as `--purpose-file`. NEVER invent a purpose.
- Slug MUST match `[a-z0-9][a-z0-9-]{0,63}`. Derive it from the purpose when that derivation is one legal slug. Include it in the question only when the derivation is ambiguous.
- Channel: pass `--channel-name` or `--dm`. NEVER invent a channel name. Include the choice in the question when the owner has not made it.
- Skills: the command installs its template default set. Pass `--skill module/component#part` ONLY for an extra the purpose needs and the owner named. NEVER invent a skill id. A reusable ability MUST be an rbtv skill installed with `--skill`. NEVER put a value that belongs to this one agent inside a skill.
- Settings: values specific to this one agent MUST go in the home's `settings.json`, passed as `--settings-file`. Omit the flag and the command writes `{}`. A re-run keeps an existing `settings.json` unless you pass `--settings-file` again. NEVER invent a setting the owner did not name.
- Reference paths: pass `--reference` ONLY for a path the owner named that exists. NEVER invent a path.
- Launch: omit `--harness`, `--model`, and `--effort` to use the workspace default. If the owner named a different setting, pass all three. NEVER pass a number as the stored effort; the command stores the rung word. NEVER substitute a model the owner did not name.
- Schedule: pass `--schedule-json` ONLY when the owner asked for a schedule AND named both a cadence and a timezone. NEVER invent either. Omit the flag when they did not ask. The file MUST match the shape in `ignite-agent create --help`.

## Run

Run `ignite-agent create` yourself with the resolved flags. NEVER create the channel, the route, the home, or the installs by hand.

A re-run of the same slug resumes a partial setup. Use it after a failure. NEVER start a second slug to work around a partial one.

## Report

Report the `link:` line from the command output when it printed one. Report every self-check line that is not `ok`, verbatim. A DM agent has no channel link; say that.

NEVER say the agent is ready when the command exited non-zero or any self-check line is not `ok`. NEVER claim a channel, route, or skill install that the self-check did not mark ok.

A creation-time schedule is stored on a board conversation (`<team>:<channel>:board`) because no Slack thread exists yet. The board records the check. The agent reports a result of that check with `ignite-agent post` until a real thread exists. Say so when you created a schedule.
