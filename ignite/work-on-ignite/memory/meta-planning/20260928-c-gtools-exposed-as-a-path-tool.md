# 20260928-c-gtools-exposed-as-a-path-tool — gtools exposed as a PATH tool

kind: creation
component: meta-planning
date: 2026-09-28
commit: ad1597ce
deployed: no
pin: NONE

## Motivation
Agents on both machines had no `gtools` command: Google Workspace work meant calling `<repo>/.venv/<python> scripts/<name>.py` by absolute path, which differs between the Windows desktop and the VPS and which agents kept rediscovering. The google-tools repo already carries a one-command CLI (`gtools.py`, on the owner's branch `feat/gtools-cli`) that finds its own venv on either OS; it simply was never linked onto PATH by the rbtv installer, unlike `stools` and `sd-graph`.

## Design
A single `method=path` row, `gtools`, in `meta/planning/exposure.csv`, whose entry point is `ws:3-resources/tools/gtools/gtools.py` — the same workspace-relative form the `sd-graph` row already uses for a tool living outside rbtv. Chosen over a wrapper script inside rbtv (a second file that would only forward arguments) and over a hand-made `~/.local/bin` symlink per machine (the anti-pattern `link-tools.py` warns against: a second machine or a redeploy loses it). `meta/planning` hosts it because it already hosts the other non-rbtv PATH tools.

## How it works
The installer resolves the `ws:` entry against the workspace root and links `~/.rbtv/bin/gtools`: a symlink on POSIX, or on Windows a `.cmd` shim plus the extensionless bash twin added in b6ff0e0d. The shim spawns the system `python` on `gtools.py`, which then locates `.venv/Scripts/python.exe` or `.venv/bin/python` inside the google-tools repo and runs the requested script there with `subprocess.call`, passing its exit code back. For the POSIX symlink to run, `gtools.py` must carry the executable bit, set in google-tools commit e653d20.

## Consequences
The row only resolves on a workspace whose google-tools clone is on `feat/gtools-cli` (or a later branch carrying `gtools.py`); on a clone still on `main` the installer refuses with `entry-point-missing` for that row. On the Windows desktop the link was minted directly through `link_one` rather than a full `install add`, so `.rbtv/config/install.json` does not book `gtools` yet; the next full install run books it, and until then a reconcile reports it as unbooked (reported, never deleted). The desktop's google-tools clone moved from `main` to `feat/gtools-cli` with main merged in (google-tools 30484ad).

## Verification
Windows desktop, 2026-09-28: `gtools --help` prints the CLI usage from git bash and from PowerShell with the cwd at `C:\`, and `gtools doctor` reports the venv, `config.yaml` and all scripts present (Google tokens are not set up on this machine, which is an owner login step). google-tools test suite: 27 tests pass on the merged branch. VPS not yet linked; handed to the emperor session.

## ATTENTION
- The entry point assumes the google-tools clone sits at `3-resources/tools/gtools/` in the workspace; a clone elsewhere makes the installer refuse this row rather than guess.
- `gtools.py` must stay executable in git (100755): Windows checkouts cannot set the bit on disk, so a commit that rewrites it from Windows with a pathspec silently drops the mode change.
- A pre-existing hand-made `gtools` in `~/.local/bin` is not a collision (different folder), but `~/.rbtv/bin` comes first on PATH and wins.
- gtools.py must stay 100755; entry resolves only on a clone carrying gtools.py
