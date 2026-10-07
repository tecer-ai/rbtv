# rbtv

This repository is rbtv's source: the modules and components that `rbtv` (the rbtv CLI, `core/rbtv/capabilities/tools/rbtv/install.py`) exposes to a target folder by managing its files. To learn what rbtv is and how its folders are laid out, read `core/rbtv/skills/framework.md`.

## Hard Rule — Build and Document Every Change

Before creating, changing, renaming, or deleting anything in this repository — a skill, rule, command, agent, hook, MCP server, tool, component, module, template, schema, or a kind of thing nothing defines yet — read and follow `core/rbtv/skills/framework.md`, the `framework` skill's entry file. Read it directly, whether or not the skill is installed. In the SAME change, document it as `core/rbtv/capabilities/methods/documenting-a-change.md` says. A change without its documentation is incomplete.

## Hard Rule — rbtv Content Must Be General

rbtv ships to any user; an installation is one instance of it. Every file, capability, and tool here MUST be usable by any user and MUST NOT contain anything specific to one installation: no hardcoded installation, vault, or host paths, no client or project names, no build-time task IDs or hypothesis/decision markers. Per-installation inputs (a project's reference set, an output location, a Slack identity) are resolved at runtime from configuration — never written into the file. Content that belongs to one installation only is built in that installation's `.rbtv/mirror/`, never here (`core/rbtv/capabilities/methods/choosing-what-to-build.md`).

When carrying a file INTO this repository from an archive or an installation:

1. Read the original and CLASSIFY it: already general, or tweaked to one installation?
2. **Already general** → carry its body over unchanged to its home in rbtv's layout; its frontmatter or record must pass its schema (the rule above).
3. **Tweaked to an installation** → NEVER generalize it silently or autonomously. Show the owner the installation-specific parts, propose how to generalize each (parameterize paths, drop build-history scaffolding, turn per-user inputs into a runtime value), and build the general version together before writing it — or keep it in the mirror.

## Hard Rule — Linux AND Windows

Every component MUST work on both Linux and Windows — rbtv runs on Linux servers and Windows desktops. The one exception, by owner decision, is Ignite's waking service (`core/ignite/`'s service, its `deploy.sh`, and its systemd unit), which runs on Linux only; `rbtv agent add`, `rbtv agent update` and `ignite connect` still work on any machine. When you can only run one platform, design for both and state in your done report which platform you actually verified. The rules that make a change run on both, the WSL run and the selftest requirement are in `core/rbtv/capabilities/methods/building-for-linux-and-windows.md`: read it before writing or changing code, a tool, a test or an installer-scanned file.

## Command-line tools

Every new or edited rbtv command-line tool follows the `cli-creator` skill (`meta/code/skills/cli-creator.md`; read it directly whether or not the skill is installed); no edit lowers its standard.

## Installed is a subset

An installation carries only the files its user selected, chosen just in time, so a file missing from an installation is normal, not a defect. Check what is installed with `rbtv list --installed` before treating anything as missing.
