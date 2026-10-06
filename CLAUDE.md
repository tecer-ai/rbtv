# rbtv

This repository is rbtv's source: the modules and components that `rbtv` (the rbtv CLI, `core/rbtv/capabilities/tools/rbtv/install.py`) exposes to a target folder by managing its units. To learn what rbtv is and how its folders are laid out, read `core/rbtv/skills/framework.md`.

## Hard Rule — Build and Document Every Change

Before creating, changing, renaming, or deleting anything in this repository — a skill, rule, command, agent, hook, MCP server, tool, component, module, template, schema, or a kind of thing nothing defines yet — read and follow `core/rbtv/skills/framework.md`, the `framework` skill's entry file. Read it directly, whether or not the skill is installed. In the SAME change, document it as `core/rbtv/capabilities/documenting-a-change.md` says. A change without its documentation is incomplete.

## Hard Rule — rbtv Content Must Be General

rbtv ships to any user; an installation is one instance of it. Every unit, capability, and tool here MUST be usable by any user and MUST NOT contain anything specific to one installation: no hardcoded installation, vault, or host paths, no client or project names, no build-time task IDs or hypothesis/decision markers. Per-installation inputs (a project's reference set, an output location, a Slack identity) are resolved at runtime from configuration — never written into the file. Content that belongs to one installation only is built in that installation's `.rbtv/mirror/`, never here (`core/rbtv/capabilities/choosing-what-to-build.md`).

When carrying a file INTO this repository from an archive or an installation:

1. Read the original and CLASSIFY it: already general, or tweaked to one installation?
2. **Already general** → carry its body over unchanged to its home in rbtv's layout; its frontmatter or record must pass its schema (the rule above).
3. **Tweaked to an installation** → NEVER generalize it silently or autonomously. Show the owner the installation-specific parts, propose how to generalize each (parameterize paths, drop build-history scaffolding, turn per-user inputs into a runtime value), and build the general version together before writing it — or keep it in the mirror.

## Hard Rule — Linux AND Windows

Every component MUST work on both Linux and Windows — rbtv runs on Linux servers and Windows desktops. The one exception, by owner decision, is Ignite's waking service (`core/ignite/`'s service, its `deploy.sh`, and its systemd unit), which runs on Linux only; `rbtv agent add`, `rbtv agent update` and `ignite connect` still work on any machine. When you can only run one platform, design for both and state in your done report which platform you actually verified. On a Windows machine, WSL (Windows Subsystem for Linux, `wsl -d <distro>`) gives a real Linux run: clone the repository inside WSL rather than running over `/mnt/c`, so line endings and the home folder are Linux's. The rbtv selftest (`core/rbtv/capabilities/tools/rbtv/install.py selftest`) MUST pass on both before a change to rbtv's install code is committed.

Defects that have actually happened, each a rule:

1. **Text encoding is explicit.** Every text read/write passes `encoding="utf-8"` — Windows defaults to cp1252 and garbles any non-ASCII byte (`—` becomes `â€”`).
2. **Line endings are CRLF-tolerant.** A Windows checkout (`core.autocrlf`) delivers `\r\n`. Parse with `\r?\n` (never `startswith("---\n")` alone); decide "unchanged" by comparing the exact bytes you would write, not decoded text.
3. **A tool's CLI runs on both systems.** The CLI a `<tool>.json` `entry` names starts with a shebang line and is committed executable (git mode `100755`): Linux refuses a CLI without both (`path-not-runnable`). Git on Windows records no executable bit, so a CLI created or moved there is committed as mode `100644` — observed 2026-10-01, when moving every tool on Windows broke the VPS cutover. Mark each new or moved CLI with `git update-index --chmod=+x <file>` and commit that staged change from the index: `git commit -- <paths>` re-reads the files and silently drops it. The rbtv selftest (check D3) fails on any file with a `#!` first line stored without the bit. Windows picks the interpreter for its `.cmd` launcher from the shebang or the `.py`/`.js`/`.sh` extension, and refuses the install without one.
4. **No POSIX-only assumptions** — execute bits (`os.access X_OK` is always true on Windows), symlinks, `/tmp`, shell tools. Guard with `os.name` and give Windows its own path, or skip a POSIX-only selftest arm with `ctx.skip`, naming why.
5. **Windows file attributes.** Re-creating a Hidden or System file fails with a misleading `PermissionError`; rewrite in place (the `write_file` function in `core/rbtv/capabilities/tools/rbtv/lib/fsio.py`).
6. **`~/.rbtv/` is the rbtv home folder** (`~/.rbtv/bin`), present on every machine — never an installation marker. Code that walks up to find an installation root skips the home folder unless it holds a real install record (`.rbtv/config/install.json`).
7. **File and folder names are Windows-valid** — no `: * ? " < > | \`, no trailing dot or space, no reserved device names (`CON`, `NUL`, `COM1`…). Code that builds a name from a timestamp or user text sanitizes it.

## Command-line tools

Every new or edited rbtv command-line tool follows the `cli-creator` skill (`meta/code/skills/cli-creator.md`; read it directly whether or not the skill is installed); no edit lowers its standard.

## Installed is a subset

An installation carries only the units its user selected, chosen just in time, so a unit missing from an installation is normal, not a defect. Check what is installed with `rbtv list --installed` before treating anything as missing.
