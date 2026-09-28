# 20260928-i-path-tools-invisible-to-git-ba — PATH tools invisible to git bash on Windows: .cmd only

kind: issue
component: meta-installer
date: 2026-09-28
commit: b6ff0e0d
deployed: no
pin: NONE
components: meta-planning

## Observed
On the Windows desktop, 2026-09-28, an agent's `cast route` call from the Bash tool (git bash) failed with "command not found", so it fell back to launching a default Claude worker instead of the routed model; a later agent had to discover by trial that `cast` ran only from PowerShell. `command -v cast` in git bash returned nothing while PowerShell resolved `C:\Users\henri\.rbtv\bin\cast.cmd`. `~/.rbtv/bin` WAS on the bash PATH (inherited from the Windows PATH) — the folder was reachable, the name was not. All thirteen PATH tools in that folder (acct, audio, cast, stools, sd-graph, rbtv, rbtv-commit, ...) shared the gap.

## Mechanism
The 2026-08-24 fix (419f5e22) made `link_one()`/`_make_link()` in `meta/installer/lib/pathlinks.py` write only `<part-id>.cmd` on Windows. PowerShell and cmd.exe append PATHEXT extensions when resolving a bare name; git bash does not — it resolves only the exact file name (or `<name>.exe`), so `cast` never matches `cast.cmd`. That fix was verified only in PowerShell, which is why the bash arm was never exercised, while agents on Windows run their shell commands through git bash.

## Attempts
Prior fix 419f5e22 (memory `20260824-i-path-links-unusable-on-windows`) solved symlink privilege and the missing shebang layer by moving to `.cmd` shims; it rejected `.ps1` wrappers but never considered a bash consumer, and verified with `acct -h` in PowerShell only. The per-session workaround that followed was an auto-memory note telling agents to run cast from PowerShell — a symptom patch that does not reach other tools, other agents, or the Linux box. Checked: meta-installer `_issues.md`/`_creations.md`, grep of memory for `.cmd|pathlinks|rbtv/bin`, `design-decisions.md` D9/D9b.

## Fix
Commit b6ff0e0d. Beside every `.cmd` shim the installer now writes an extensionless twin `<part-id>`: `#!/bin/sh`, line 2 `# rbtv-shim -> <target>` as the ownership marker, line 3 `exec "<interp>" "<target>" "$@"` with both paths forward-slashed and the same interpreter resolution as the `.cmd`. Written as bytes so it carries LF endings (text mode on Windows writes CRLF, which sh rejects). `link_points_at` treats a missing or differing twin as stale, so every existing install heals on its next run with no per-tool edit; `unlink_one` removes an owned twin with its `.cmd`; `_make_link` and `gate_path_links` refuse path-collision on a foreign file at the twin's name. Chosen over rewriting each CLI as a packaged entry point (touches every tool) and over a rule telling agents to use PowerShell (does not fix anything and has no Linux meaning). Recorded under D9b in `design-decisions.md`.

## Consequences
POSIX untouched: every twin branch is gated on `os.name == "nt"` via `_sh_twin()`. The old "delete a bare symlink at the unsuffixed name" cleanup in `link_one` still runs, and `_make_link` also unlinks a symlink at the twin path before writing. On this desktop the 13 shims were relinked in place through `link_one` (not a full `install add`, which would also have rewritten `.mcp.json`, `opencode.json` and 212 AGENTS.md mirrors carrying other sessions' uncommitted edits). Separately observed, not caused here: `stools` fails in both shells because its wrapper `execv`s a real stools binary absent on this machine.

## Verification
`install.py selftest` on the Windows desktop: HEAD baseline (scratch worktree) = 4 failures (mojibake banner, S2, S5, S7) plus the known WinError 1314 crash at the unbooked-stranger symlink; with the fix, identical floor and the new `L-bash-twin` check passes, `L-rm` confirms the twin is removed. Live: after relinking, `cast`, `acct`, `audio`, `sd-graph`, `rbtv`, `rbtv-commit`, `capture-cli` all run by bare name from git bash, and `cast --help` still runs from PowerShell. Not deployed to the VPS — inert there by construction.

## ATTENTION
- Any Windows PATH-link change must be proven from BOTH PowerShell and git bash: agents run commands through git bash, and a PowerShell-only check is exactly how the twin gap shipped.
- The twin must stay LF-only: writing it through `write_text` on Windows produces CRLF and sh fails with a confusing `\r` error.
- The twin's line 2 `# rbtv-shim -> ` is its ownership marker; reformatting it makes the installer refuse its own twins as path-collision.
- A full `install add` to refresh links also rewrites shared config and mirrors; to relink only, drive `link_one` over the existing shims.
- Prove Windows PATH-link changes from both PowerShell and git bash; twin must stay LF
