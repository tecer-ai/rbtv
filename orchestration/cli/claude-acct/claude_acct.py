#!/usr/bin/env python3
"""claude-acct — switch the `claude` CLI between Claude accounts without re-logging-in.

  claude-acct ls           list slots (* = active, with each login's expiry)
  claude-acct add <name>   snapshot the CURRENT login into slot <name>
  claude-acct use <name>   save the live tokens back to the active slot, then activate <name>
  claude-acct rm <name> --force   delete a slot (costs that account a re-login)

A slot holds the two places the Claude CLI keeps a login: the OAuth blob in
`~/.claude/.credentials.json` and the `oauthAccount` key of `~/.claude.json`. Slots live in
`{workspace}/.rbtv/env/claude-accts/` (mode 600, gitignored). Which slot is ACTIVE is derived
from the live login's account uuid — there is no marker file to drift out of sync.

Tokens ROTATE — `use` writes the live credentials back to the outgoing slot before swapping, so a
slot never holds a superseded refresh token. Switching affects NEW sessions only: a running
`claude` process holds its token in memory and writes its own back on refresh.
"""
import datetime
import json
import os
import pathlib
import sys

HOME = pathlib.Path.home()
CREDS = HOME / ".claude" / ".credentials.json"
CONF = HOME / ".claude.json"


def workspace_root():
    """The workspace this CLI is installed into — the nearest ancestor holding `rbtv.json`."""
    if env := os.environ.get("RBTV_WORKSPACE"):
        return pathlib.Path(env)
    for p in pathlib.Path(__file__).resolve().parents:
        if (p / "rbtv.json").exists():
            return p
    sys.exit("cannot resolve the workspace root (no rbtv.json above this script) — set RBTV_WORKSPACE")


DIR = workspace_root() / ".rbtv" / "env" / "claude-accts"


def slot(name):
    return DIR / f"{name}.json"


def live_uuid():
    return (json.loads(CONF.read_text()).get("oauthAccount") or {}).get("accountUuid")


def active():
    """The slot matching the login the CLI is currently using — derived, never a marker file.

    A marker file is a second source of truth that silently drifts out of sync with the real
    credential store; the account uuid in `~/.claude.json` IS the answer.
    """
    uuid = live_uuid()
    for n in names():
        d = json.loads(slot(n).read_text())
        if uuid and (d.get("oauthAccount") or {}).get("accountUuid") == uuid:
            return n
    return None


def names():
    return sorted(p.stem for p in DIR.glob("*.json"))


def save(name):
    """Write the CURRENT live login into slot `name`."""
    DIR.mkdir(parents=True, exist_ok=True)
    p = slot(name)
    p.write_text(json.dumps({
        "credentials": json.loads(CREDS.read_text()),
        "oauthAccount": json.loads(CONF.read_text()).get("oauthAccount"),
    }, indent=2))
    p.chmod(0o600)


def cmd_add(name):
    save(name)
    print(f"saved the current login as '{name}' (now active)")


def cmd_use(name):
    if not slot(name).exists():
        sys.exit(f"no such slot: {name} (have: {', '.join(names()) or 'none'})")
    cur = active()
    if cur == name:
        print(f"'{name}' is already active")
        return
    if cur:
        save(cur)  # tokens rotate — park the live ones before swapping them out
    elif names():
        # Overwriting a login held by no slot would lose it: its refresh token exists nowhere else.
        sys.exit("the current login is not saved in any slot — run `claude-acct add <name>` first")
    data = json.loads(slot(name).read_text())
    CREDS.write_text(json.dumps(data["credentials"], indent=2))
    CREDS.chmod(0o600)
    if data.get("oauthAccount"):
        conf = json.loads(CONF.read_text())
        conf["oauthAccount"] = data["oauthAccount"]
        CONF.write_text(json.dumps(conf, indent=2))
    print(f"active account: {name} — start a NEW `claude` session to use it")


def cmd_rm(name, force=False):
    if not slot(name).exists():
        sys.exit(f"no such slot: {name}")
    if active() == name:
        sys.exit(f"'{name}' is the active account — `use` another slot first")
    # A parked slot is the ONLY copy of that account's refresh token: deleting it costs a re-login.
    if not force:
        sys.exit(f"deleting slot '{name}' loses its login — that account would need `claude /login` "
                 f"again. Re-run with: claude-acct rm {name} --force")
    slot(name).unlink()
    print(f"removed slot '{name}'")


def cmd_ls():
    if not names():
        print(f"no slots yet in {DIR} — run: claude-acct add <name>")
        return
    cur = active()
    for n in names():
        d = json.loads(slot(n).read_text())
        oauth = d["credentials"]["claudeAiOauth"]
        exp = datetime.datetime.fromtimestamp(oauth["refreshTokenExpiresAt"] / 1000)
        mail = (d.get("oauthAccount") or {}).get("emailAddress", "?")
        stale = " STALE" if exp < datetime.datetime.now() else ""
        print(f"{'*' if n == cur else ' '} {n:12} {mail:40} login valid until {exp:%Y-%m-%d}{stale}")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "ls"
    arg = argv[2] if len(argv) > 2 else None
    if cmd in ("add", "use", "rm"):
        if not arg:
            sys.exit(f"usage: claude-acct {cmd} <name>")
        if cmd == "rm":
            cmd_rm(arg, force="--force" in argv)
        else:
            {"add": cmd_add, "use": cmd_use}[cmd](arg)
    elif cmd in ("ls", "list"):
        cmd_ls()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
