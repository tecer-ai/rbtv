#!/usr/bin/env python3
"""stools_wrapper — the ONE entry point every seat and the host PATH resolve `stools` to.

Owner ruling `d-slack-identity-a` (2026-08-31, design in
`1-projects/build-ignite/build/redesign-continue-1/slack-send-identity-design.md`): sending to
Slack as the BOT is unrestricted; sending AS THE OWNER (`--workspace ignite-owner`, the xoxp
user token) is refused unless a live, owner-recorded grant matches this sitting. This module is
that gate. It is not a stools source edit — stools stays third-party-managed and unaware of
grants; this wrapper execs the real `stools.py` unchanged once (or if) it decides to allow the
call through.

Gate logic (write verbs only — send/upload/react/canvas; every read verb passes straight through,
by design: `search:read` has no bot-token equivalent, so reads are never gated):
  1. `--dry-run` always passes through — it makes no Slack API call either way, so an ungranted
     agent may still preview what a real send would have done.
  2. The target workspace's `config.yaml` entry is checked for `writes: false`. Absent that key
     (e.g. workspace `ignite`, the bot), the call passes through ungated. When the stools venv or
     config cannot be read or parsed, the write is still refused — fail closed — but as
     `config-unavailable`, naming the path and the read/parse error: an UNKNOWN config state is
     never reported as a known `writes: false` setting and gets no grant advice.
  3. On a `writes: false` workspace, `.rbtv/config/stools-as-owner-grants.yaml` is checked for an
     `active` grant naming that workspace and verb, scoped to cover this sitting's cwd. A match
     execs the real stools.py; no match exits 2 with a named refusal and makes NO exec, NO
     subprocess call, and NO import of anything Slack-API-facing — the refusal is structurally
     incapable of reaching the network.
"""

import os
import subprocess
import sys
from pathlib import Path


def workspace_root():
    """First ancestor holding `.rbtv/config` — from this file's real location (PATH links are
    symlinks on POSIX, so resolve first), else from the cwd. Same discovery rule as the installer's
    `workspace_root()`; a fixed path broke every machine but the one it named."""
    for start in (Path(__file__).resolve().parent, Path.cwd().resolve()):
        for p in (start, *start.parents):
            if (p / ".rbtv" / "config").is_dir():
                return p
    sys.exit("stools: no workspace found — no ancestor of this wrapper or the cwd holds .rbtv/config")


VAULT_ROOT = workspace_root()
STOOLS_ROOT = Path(os.environ.get("SLACK_TOOLS_ROOT") or (VAULT_ROOT / "3-resources/tools/stools"))
REAL_STOOLS = STOOLS_ROOT / "stools.py"
GRANTS_FILE = VAULT_ROOT / ".rbtv/config/stools-as-owner-grants.yaml"

WRITE_VERBS = {"send", "upload", "react", "canvas"}


def die_refused(workspace, verb):
    print("stools: as-owner-write-refused", file=sys.stderr)
    print(f"  why: --workspace {workspace} is an owner-identity write (writes: false) "
          f"and no active grant covers '{verb}' for this sitting", file=sys.stderr)
    print("  fix: get an owner-recorded grant in .rbtv/config/stools-as-owner-grants.yaml, "
          "or send as the bot with --workspace ignite, or preview with --dry-run", file=sys.stderr)
    sys.exit(2)


def die_config_unavailable(workspace, reason):
    print("stools: config-unavailable", file=sys.stderr)
    print(f"  why: cannot read the workspace config to decide whether --workspace {workspace} "
          f"permits writes — {reason}", file=sys.stderr)
    print("  fix: repair the stools venv/config named above and retry — this refusal does not "
          "mean a writes: false setting was read", file=sys.stderr)
    sys.exit(2)


def exec_real(argv):
    if os.name == "nt":
        # Windows has no shebang exec and its os.execv detaches the child from the console, so
        # run the real script under this interpreter and pass its exit code through.
        sys.exit(subprocess.call([sys.executable, str(REAL_STOOLS)] + argv))
    os.execv(str(REAL_STOOLS), [str(REAL_STOOLS)] + argv)


def extract_workspace(args):
    for i, a in enumerate(args):
        if a == "--workspace" and i + 1 < len(args):
            return args[i + 1]
        if a.startswith("--workspace="):
            return a.split("=", 1)[1]
    return None


def load_workspaces():
    """Read config.yaml's `workspaces:` section via stools.py's OWN reader (`workspaces_of`) —
    one source, not a second parser. Not `auth.py`: it imports slack_sdk at module level, which
    lives only inside stools' venv, and this wrapper must run under the system interpreter (it
    execs, never imports, the rest of stools). Returns `(workspaces, None)`, or `(None, reason)`
    when the venv or config cannot be read or parsed — the caller fails CLOSED on that,
    consistent with every other unresolved-input case here, and reports the reason verbatim.
    """
    sys.path.insert(0, str(STOOLS_ROOT))
    import stools as stools_cli
    py = stools_cli.venv_python()
    if py is None:
        return None, f"stools venv not found at {STOOLS_ROOT / '.venv'}"
    workspaces = stools_cli.workspaces_of(py)
    if workspaces is None:
        cfg = STOOLS_ROOT / "config.yaml"
        if not cfg.exists():
            return None, f"stools config not found at {cfg}"
        return None, f"stools config at {cfg} could not be read or parsed"
    return workspaces, None


def workspace_gated(workspace):
    """`(gated, reason)`: gated is True only when the PARSED config shows `writes: false` for
    the workspace, False when it clearly does not, and None when the venv/config could not be
    read or parsed — unknown is still default deny, but the caller must report it as
    config-unavailable, not as a writes:false refusal."""
    workspaces, error = load_workspaces()
    if workspaces is None:
        return None, error
    entry = workspaces.get(workspace) or {}
    return entry.get("writes") is False, None


def sitting_in_scope(scope):
    kind_path = (scope or {}).get("path")
    if not kind_path:
        return False
    root = (VAULT_ROOT / kind_path).resolve()
    try:
        Path.cwd().resolve().relative_to(root)
        return True
    except ValueError:
        return False


def matching_grant(workspace, verb):
    if not GRANTS_FILE.exists():
        return None
    import yaml
    data = yaml.safe_load(GRANTS_FILE.read_text(encoding="utf-8")) or {}
    for grant in data.get("grants") or []:
        if grant.get("status") != "active":
            continue
        if grant.get("workspace") != workspace:
            continue
        if verb not in (grant.get("verbs") or []):
            continue
        if not sitting_in_scope(grant.get("scope") or {}):
            continue
        return grant
    return None


def main(argv):
    if not argv or argv[0] not in WRITE_VERBS:
        exec_real(argv)
        return

    verb, rest = argv[0], argv[1:]
    if "--dry-run" in rest:
        exec_real(argv)
        return

    workspace = extract_workspace(rest)
    if workspace is None:
        exec_real(argv)
        return

    gated, config_error = workspace_gated(workspace)
    if gated is None:
        die_config_unavailable(workspace, config_error)
    if not gated:
        exec_real(argv)
        return

    if matching_grant(workspace, verb) is not None:
        exec_real(argv)
        return

    die_refused(workspace, verb)


if __name__ == "__main__":
    main(sys.argv[1:])
