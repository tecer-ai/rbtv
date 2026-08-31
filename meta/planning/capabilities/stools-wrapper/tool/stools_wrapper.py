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
     (e.g. workspace `ignite`, the bot), the call passes through ungated.
  3. On a `writes: false` workspace, `.rbtv/config/stools-as-owner-grants.yaml` is checked for an
     `active` grant naming that workspace and verb, scoped to cover this sitting's cwd. A match
     execs the real stools.py; no match exits 2 with a named refusal and makes NO exec, NO
     subprocess call, and NO import of anything Slack-API-facing — the refusal is structurally
     incapable of reaching the network.
"""

import os
import sys
from pathlib import Path

# Same fixed-VAULT_ROOT convention as ignite/coord/coord.py — a personal, single-machine repo has
# one home; a `Path(__file__)`-relative walk would have to reinvent that same fact per caller.
VAULT_ROOT = Path("/home/henri/ht-wkdir/second-brain")
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


def exec_real(argv):
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
    execs, never imports, the rest of stools). Returns None if the venv or config is unreadable —
    the caller fails CLOSED on that, consistent with every other unresolved-input case here.
    """
    sys.path.insert(0, str(STOOLS_ROOT))
    import stools as stools_cli
    py = stools_cli.venv_python()
    if py is None:
        return None
    return stools_cli.workspaces_of(py)


def workspace_gated(workspace):
    workspaces = load_workspaces()
    if workspaces is None:
        return True  # can't confirm the bit either way — default deny, not default allow
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
    import yaml
    data = yaml.safe_load(GRANTS_FILE.read_text()) or {}
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
    if workspace is None or not workspace_gated(workspace):
        exec_real(argv)
        return

    if matching_grant(workspace, verb) is not None:
        exec_real(argv)
        return

    die_refused(workspace, verb)


if __name__ == "__main__":
    main(sys.argv[1:])
