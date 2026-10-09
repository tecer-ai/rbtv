#!/usr/bin/env python3
"""Launch Slack operations, enforcing grants for accounts configured with writes: false.

Help uses the command parser without loading account metadata. Other writes resolve
account metadata before checking grants; unavailable metadata fails closed.
Dry runs do not post and do not establish permission or grant coverage.
"""

import os
import subprocess
import sys
from pathlib import Path


def workspace_root():
    """Find the installation record above cwd, then above the resolved wrapper."""
    for start in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        for p in (start, *start.parents):
            if (p / ".rbtv/config/install.json").is_file():
                return p
    sys.exit("slack: no installation found — run inside a folder holding .rbtv/config/install.json")


VAULT_ROOT = workspace_root()
STOOLS_ROOT = Path(os.environ.get("SLACK_TOOLS_ROOT") or Path(__file__).resolve().parents[3] / "repository")
os.environ.setdefault("SLACK_TOOLS_CONFIG", str(VAULT_ROOT / ".rbtv/config/slack/config.yaml"))
REAL_STOOLS = STOOLS_ROOT / "stools.py"
GRANTS_FILE = VAULT_ROOT / ".rbtv/config/slack/write-grants.yaml"

WRITE_VERBS = {"send", "upload", "react", "canvas"}


def die_refused(workspace, verb):
    print("slack: as-owner-write-refused", file=sys.stderr)
    print(f"  why: --workspace {workspace} is an owner-identity write (writes: false) "
          f"and no active grant covers '{verb}' for this sitting", file=sys.stderr)
    print("  fix: get the owner's explicit approval for the account, verb, working folder and purpose.\n"
          "       After approval, an agent may append exactly that grant to .rbtv/config/slack/write-grants.yaml.\n"
          "       Preserve existing grants; do not broaden the approved folder or verbs.\n"
          "       Run slack send --help for the grant format and scope guidance.", file=sys.stderr)
    sys.exit(2)


def die_config_unavailable(workspace, reason):
    print("slack: config-unavailable", file=sys.stderr)
    print(f"  why: cannot read the workspace config to decide whether --workspace {workspace} "
          f"permits writes — {reason}", file=sys.stderr)
    print("  fix: repair the slack venv/config named above and retry — this refusal does not "
          "mean a writes: false setting was read", file=sys.stderr)
    sys.exit(2)


def exec_real(argv):
    if os.name == "nt":
        # Windows has no shebang exec and its os.execv detaches the child from the console, so
        # run the real script under this interpreter and pass its exit code through.
        sys.exit(subprocess.call([sys.executable, str(REAL_STOOLS)] + argv))
    os.execv(str(REAL_STOOLS), [str(REAL_STOOLS)] + argv)


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
        return None, f"slack venv not found at {STOOLS_ROOT / '.venv'}"
    workspaces = stools_cli.workspaces_of(py)
    if workspaces is None:
        cfg = Path(os.environ["SLACK_TOOLS_CONFIG"])
        if not cfg.exists():
            return None, f"slack config not found at {cfg}"
        return None, f"slack config at {cfg} could not be read or parsed"
    return workspaces, None


def workspace_gated(workspaces, workspace):
    """True only when the already-loaded config shows `writes: false`.

    Any other value, including a missing key, is not gated. Unknown config never
    reaches here: the caller fails closed before parsing.
    """
    entry = workspaces.get(workspace) or {}
    return entry.get("writes") is False


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
    import stools as stools_cli
    data = stools_cli.yaml_file_of(stools_cli.venv_python(), GRANTS_FILE)
    if not isinstance(data, dict):
        die_config_unavailable(workspace, f"cannot read grant metadata at {GRANTS_FILE}")
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


def load_write_args():
    scripts = str(STOOLS_ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import write_args
    return write_args


def command_prog(verb):
    root = str(STOOLS_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    import stools as stools_cli
    return f"{stools_cli.PROG} {verb}"


def main(argv):
    if not argv or argv[0] not in WRITE_VERBS:
        exec_real(argv)
        return

    verb, rest = argv[0], argv[1:]
    if load_write_args().show_write_help(verb, rest, command_prog(verb)):
        return

    workspaces, error = load_workspaces()
    if workspaces is None:
        die_config_unavailable("unresolved", error)
        return

    args = load_write_args().parse_write_context(verb, rest, workspaces, command_prog(verb))
    if args.dry_run:
        exec_real(argv)
        return

    workspace = args.workspace
    if workspace_gated(workspaces, workspace) and matching_grant(workspace, verb) is None:
        die_refused(workspace, verb)
        return
    exec_real(argv + [f"--workspace={workspace}"])


if __name__ == "__main__":
    main(sys.argv[1:])
