# 20260928-i-stools-wrapper-dead-on-windows — stools wrapper dead on Windows: fixed VPS path

kind: issue
component: meta-planning
date: 2026-09-28
commit: 95a9b53c
deployed: no
pin: NONE

## Observed
On the Windows desktop, 2026-09-28, `stools --help` failed from both git bash and PowerShell with a Python traceback ending in `os.execv(str(REAL_STOOLS), ...)` → `FileNotFoundError: [Errno 2] No such file or directory`. The PATH launcher itself resolved (after b6ff0e0d gave git bash its twin); the failure was inside the wrapper, so every agent on Windows had no working stools command at all, reads included.

## Mechanism
`meta/planning/capabilities/stools-wrapper/tool/stools_wrapper.py` fixed `VAULT_ROOT = Path("/home/henri/ht-wkdir/second-brain")`, a VPS-only path, and derived both the real `stools.py` location and the grants file from it; on Windows that folder does not exist, so `REAL_STOOLS` pointed nowhere. Independently, `exec_real()` used `os.execv` on the `.py` file itself, which relies on a shebang — Windows has none, so even a correct path would fail there.

## Attempts
First attempt held — checked: meta-planning `_creations.md` entry `20260902-c-stools-send-as-owner-wrapper-e` (the wrapper's creation; it chose the fixed root after `ignite/coord/coord.py`'s convention and was verified only on the VPS), grep of memory for `stools`, and the installer's `workspace_root()` discovery rule in `meta/installer/lib/pathlinks.py`.

## Fix
Commit 95a9b53c. `VAULT_ROOT` is now found at runtime as the first ancestor holding `.rbtv/config`, walking from the wrapper's resolved file (POSIX PATH links are symlinks, so resolving first is required) and falling back to the cwd — the same discovery rule the installer uses, so one rule serves both machines and any workspace. On Windows `exec_real()` runs `stools.py` under `sys.executable` via `subprocess.call` and exits with its code; POSIX keeps `os.execv`. The refusal path is untouched and still makes no exec or subprocess call. Rejected: a second hardcoded Windows path (breaks the rbtv General rule and a third machine); an env var only (every caller would need it set).

## Consequences
On the VPS the resolved-file walk reaches the same vault root the constant named, so uncaged behaviour is unchanged. A caged or deploy-mirror copy of the wrapper whose ancestors lack `.rbtv/config` now falls back to the cwd instead of the constant; if neither holds it, the wrapper exits naming the missing workspace rather than exec'ing a wrong path. The Windows desktop still has no `stools/config.yaml` (Slack workspaces and tokens), so real Slack calls there need an owner setup step; that is configuration, not this defect.

## Verification
Windows desktop: `stools --help` prints the stools usage from git bash and from PowerShell with the cwd at `C:\` (outside the vault), proving the walk resolves from the wrapper's own location. A `--dry-run` send reached the real stools and stopped at the missing `config.yaml`, proving the handoff. VPS verification requested from the emperor session; not deployed.

## ATTENTION
- Never reintroduce a fixed vault path in an rbtv tool: it silently breaks every machine except the one it names, and the Windows desktop is one of two daily machines.
- Resolve `__file__` before walking parents: on POSIX the wrapper is reached through a `~/.rbtv/bin` or `~/.local/bin` symlink, whose parents are not the workspace.
- On Windows use subprocess with the exit code passed through, never `os.execv`: Windows execv detaches the child from the console and cannot run a `.py` directly.
- Never hardcode a vault path in an rbtv tool; resolve __file__ before walking
