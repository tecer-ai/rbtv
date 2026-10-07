#!/usr/bin/env python3
"""stools_wrapper — the ONE entry point every seat and the host PATH resolve `stools` to.

Owner ruling `d-slack-identity-a` (2026-08-31, design in
`1-projects/build-ignite/build/redesign-continue-1/slack-send-identity-design.md` — deleted 2026-09-28; in git history): sending to
Slack as the BOT is unrestricted; sending AS THE OWNER (`--workspace ignite-owner`, the xoxp
user token) is refused unless a live grant matches this sitting. A grant is recorded only
after the owner's explicit approval, and an agent may record exactly that approved grant.
This module is that gate. It is not a stools source edit — stools stays third-party-managed and unaware of
grants; this wrapper execs the real `stools.py` once (or if) it decides to allow the
call through. stools.py itself is not modified.

Gate logic (write verbs only — send/upload/react/canvas; every read verb passes straight through,
by design: `search:read` has no bot-token equivalent, so reads are never gated):
  1. A write loads workspace metadata once (`load_workspaces`). If the venv or config cannot
     be read or parsed, the write is refused as `config-unavailable` before parsing — including
     argv that looks like help or dry-run. Unknown config is never treated as ungated and is
     never reported as a known `writes: false`.
  2. The account is the one selected by the same parser the command executes
     (`scripts/write_args.py`), not a scan of argv. Help that parser treats as help, including
     qualified help, exits 0 with that parser's native text and prog and does not consult
     grants. `--help` as an option value is not help. Malformed arguments exit 2 with the
     parser's own error and do not write. A parsed `--dry-run` (including an unambiguous
     abbreviation) forwards the original argv with no grant check: it does not post, it may
     contact Slack, and it does not check grant coverage.
  3. On a `writes: false` workspace, `.rbtv/config/communication/stools-as-owner-grants.yaml` is checked for an
     `active` grant naming that workspace and verb, scoped to cover this sitting's cwd. A match
     execs the real stools.py; no match exits 2 with a named refusal that launches no FINAL
     executor, no Slack client, and no Slack SDK import. One local subprocess does run before the
     decision: the step-1 metadata read (`load_workspaces` launches stools.py's venv python to
     read config.yaml). After that read, the refusal path launches nothing further and is
     structurally incapable of reaching the network.
  4. An allowed parsed write is forwarded as the original argv plus a single trailing
     `--workspace=<effective account>` argument (equals form), after canvas subcommand
     arguments. The equals form is load-bearing: a configured account name may itself
     begin with a dash (for example `-owner`) or even be the literal `--help`, and a
     separate two-token `--workspace VALUE` tail would let the executor's parser read
     such a value as an option. Help and dry-run keep the original argv. The trailing
     option binds the gated account if the command re-reads config and the default has
     changed; a removed account fails in that parser instead of switching identity.

Declared precedence for write verbs: config-unavailable, then native help (exit 0) or native
parser error (exit 2), then dry-run pass-through, then grant match, then refusal. Post-parse
content errors inside the command are reached only after the gate allows the exec.
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
GRANTS_FILE = VAULT_ROOT / ".rbtv/config/communication/stools-as-owner-grants.yaml"

WRITE_VERBS = {"send", "upload", "react", "canvas"}


def die_refused(workspace, verb):
    print("stools: as-owner-write-refused", file=sys.stderr)
    print(f"  why: --workspace {workspace} is an owner-identity write (writes: false) "
          f"and no active grant covers '{verb}' for this sitting", file=sys.stderr)
    print("  fix: get the owner's explicit approval for the account, verb, working folder and purpose.\n"
          "       After approval, an agent may append exactly that grant to .rbtv/config/communication/stools-as-owner-grants.yaml.\n"
          "       Preserve existing grants; do not broaden the approved folder or verbs.\n"
          "       Run stools send --help for the grant format and scope guidance.", file=sys.stderr)
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
