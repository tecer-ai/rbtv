# 20260824-i-path-links-unusable-on-windows — PATH links unusable on Windows: no symlink, no shebang

kind: issue
component: meta-installer
date: 2026-08-24
commit: 419f5e22
deployed: no
pin: NONE
components: cli

## Observed
On the Windows desktop (`C:\Users\henri\Documents\second-brain`), 2026-08-24, `install.py add`
refused every PATH link with `EFUSED [path-link-failed] ... [WinError 1314] O cliente não tem o
privilégio necessário` — symlink creation into `~/.rbtv/bin` needs a privilege a stock Windows
account lacks. After the owner enabled Developer Mode the links minted, but every one of the
seven names (`acct`, `audio`, `capture-cli`, `cast`, `install`, `rbtv`, `rbtv-commit`) was still
"not recognized" in PowerShell: an extensionless symlink to a `#!` script is not executable on
Windows. The printed shell line (`export PATH=...`) was also bash syntax no PowerShell profile
can use. HEAD and the tree agree; platform-specific, not drift.

## Mechanism
Two independent POSIX assumptions in `meta/installer/lib/pathlinks.py`. (1) `link_one()` called
`Path.symlink_to()` unconditionally — on Windows that syscall is privileged, and even when it
succeeds the result is inert, because Windows has no shebang layer and `CreateProcess` will not
launch an extensionless text file (the exact gap memory `20260824-i-rbtv-direct-delegates-unrunnab`
documents for the CLI's delegates). (2) `shell_rc()` knew only `.bashrc`/`.zshrc` and
`PATH_BOOTSTRAP` in `lib/constants.py` was a bash `export` literal, so `--write-path` had no
valid Windows destination or syntax.

## Attempts
First attempt held — checked: `meta-installer/_issues.md` and `_creations.md` (empty of prior
Windows work), a memory-wide grep for `windows|symlink|pathlink|shim` (sole relevant hit: the
cli delegate entry above), `design-decisions.md` D9/D12, and `selftest/test_pathlinks.py`.
`rbtv embed-search` could not be consulted — the CLI was itself unrunnable on this machine until
this class of fix; the grep floor stood in.

## Fix
Commit 419f5e22. On `os.name == "nt"`, `link_one()` writes a regular `<part-id>.cmd` shim instead
of a symlink: line 1 `@rem rbtv-shim -> <abs target>` is simultaneously the D12 ownership marker
and the recorded target (standing in for `readlink`), line 2 spawns the interpreter parsed from
the target's shebang (env-form handled; extension fallback .py/.js/.sh) with the resolutions the
delegate fix settled — `python3` spawns as `python` (not a stock Windows PATH name), `bash`/`sh`
resolves through `where git` to git's own `bin/bash.exe` with the script path forward-slashed
(PATH bash is usually WSL's, which cannot see `C:` paths). Ownership tests (`link_one`,
`unlink_one`, `gate_path_links`) accept "symlink OR marked shim"; `link_points_at` compares the
whole shim text so an edited shebang reads as stale and relinks. `shell_rc()` on Windows asks
PowerShell itself for `$PROFILE` (Documents can be OneDrive-redirected — guessing the path is
wrong on real machines), and `PATH_BOOTSTRAP` becomes `$env:Path = "$HOME\.rbtv\bin;" + $env:Path`
under the same `# rbtv2` fences. Recorded as D9b in `design-decisions.md`. Rejected: requiring
Developer Mode / admin (fixes the privilege, not the execution gap); a per-row interpreter field
in `exposure.csv` (duplicates what the shebang already carries — same rejection as the delegate
fix); `.ps1` wrappers (cmd.exe cannot run them; `.cmd` runs from both shells).

## Consequences
POSIX behaviour is byte-identical — every Windows branch is gated on `os.name`. Selftest
assertions in `test_pathlinks.py`, `test_install.py`, and `test_hub.py` moved from raw
`.is_symlink()`/bare-name checks to the new exported `link_path()`/`link_points_at()` helpers,
which reduce to the old semantics on POSIX. `link_one` also deletes a leftover bare symlink at
the unsuffixed name when writing its shim, so pre-fix runs self-clean. Nothing else deleted or
replaced.

## Verification
`install.py selftest` on the Windows desktop: baseline via `git stash` fails 5 pre-existing
checks (mojibake encoding on managed banners, S2/S5/S7 skill-folder byte checks,
SURF-doctor-not-exec); with the fix, the same 5 and no new failures — the two mid-work
regressions (test_install green-path, test_hub H-realize-path) were the bare-name assertions and
were fixed in the same commit. Live end-to-end on this machine: `install.py add -c core/providers
--write-path` minted seven `.cmd` shims, removed the stale bare symlinks, wrote the fenced
PowerShell block into `$PROFILE` (line 332), and `acct -h` plus `rbtv install li` ran through the
shims in PowerShell. Not deployed — inert on the VPS by construction.

## ATTENTION
- A green selftest on the VPS proves nothing about the Windows arm: every `os.name == "nt"`
  branch is dead code there. Windows-touching changes to pathlinks need one run on the Windows
  desktop, where the pre-existing failure floor is 5 (encoding + doctor-not-exec), not 0.
- The shim's first line is load-bearing twice over — ownership marker AND recorded target. A
  "cosmetic" reformat of `_SHIM_MARK` or that line orphans every deployed shim: the installer
  stops recognizing them as ours and refuses with path-collision.
- `test_pathlinks.py` still creates one real symlink (the unbooked "stranger") — on Windows the
  selftest itself needs Developer Mode or admin, even though the installer no longer does.
- Selftest assertions about `~/.rbtv/bin` must go through `link_path()`/`link_points_at()` — a
  raw `bin_dir() / name` or `.is_symlink()` check passes on POSIX and fails on Windows, which is
  exactly how the two mid-work regressions in test_install/test_hub arose.
- Windows arm of pathlinks is dead code on the VPS — verify on the Windows desktop, failure floor 5
