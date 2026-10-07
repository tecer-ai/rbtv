"""Provider accounts: the supported providers, an installation's saved logins,
and switching the live login of a provider between them.

A saved login is a copy of the files that make up one login of a provider, at
`<installation>/.rbtv/config/rbtv/providers/<provider>/<account>.json`. Which
saved login is live is read from the account id inside the live files, never
from a marker. Nothing here prints a key or a token.
"""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from discovery import Refuse

from . import present
from .constants import ENV_FILE_REL, HARNESSES, PROVIDERS_FILE, PROVIDERS_REL
from .selection import close_names, close_names_sentence
from .shared_links import installation_mutation_lock

ACCOUNT_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
# The file that keeps every saved login out of git, in any clone or worktree.
IGNORE_FILE = ".gitignore"
IGNORE_TEXT = "*\n"
# A harness key of providers.json that is no harness: the provider is also
# reached by `cast api`.
API_HARNESS = "api"


def usage_refusal(message: str, next_cmd: str) -> Refuse:
    exc = Refuse("usage", message)
    exc.next = next_cmd
    return exc


# --- the providers file ------------------------------------------------------


def load() -> dict:
    """The supported providers and the harness stores, as providers.json holds them."""
    try:
        data = json.loads(PROVIDERS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refuse("providers-unreadable",
                     f"{PROVIDERS_FILE}: not readable JSON ({exc})",
                     str(PROVIDERS_FILE)) from exc
    for name, spec in data["providers"].items():
        unknown = sorted(set(spec["harnesses"]) - {*HARNESSES, API_HARNESS})
        if unknown:
            raise Refuse("providers-unreadable",
                         f"provider {name!r} names unknown harness(es): {', '.join(unknown)}",
                         str(PROVIDERS_FILE))
    return data


def provider(data: dict, name: str, verb: str) -> dict:
    """One provider's entry; an unknown name is refused with the known ones."""
    known = list(data["providers"])
    if name not in known:
        raise usage_refusal(f"unknown provider {name!r}. {close_names_sentence(close_names(name, known))} "
                     f"Providers: {', '.join(known)}", f"rbtv providers {verb} -h")
    return data["providers"][name]


def switchable(data: dict) -> list[str]:
    return [name for name, spec in data["providers"].items() if "saved_login" in spec]


def saved_login_spec(data: dict, name: str, verb: str) -> dict:
    """The saved-login description of a provider whose login can be saved."""
    spec = provider(data, name, verb)
    if "saved_login" not in spec:
        raise usage_refusal(f"{name} holds one key, so it has no login to save or switch. "
                     f"Providers with saved logins: {', '.join(switchable(data))}",
                     f"rbtv providers list {name}")
    return spec["saved_login"]


# --- reading logins ----------------------------------------------------------


def _dig(value, keys):
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _jwt_claim(token, claim: str):
    """One claim of a token's payload. Identity only: never verified, never printed."""
    try:
        segment = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))).get(claim)
    except Exception:  # noqa: BLE001 - a credential that is no such token has no claim
        return None


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _home_path(raw: str) -> Path:
    return Path(os.path.expanduser(raw))


def live_login(login: dict) -> dict | None:
    """The live login in saved-login shape, or None when not logged in."""
    found = {}
    for label, place in login["files"].items():
        doc = _read_json(_home_path(place["path"]))
        part = _dig(doc, [place["key"]]) if "key" in place else doc
        if part is None:
            return None
        found[label] = part
    return found


def account_id(login: dict, saved: dict | None):
    return _dig(saved, login["id"])


def email(login: dict, saved: dict | None) -> str | None:
    where = login.get("email")
    if isinstance(where, dict):
        return _jwt_claim(_dig(saved, where["jwt"]), where["claim"])
    return _dig(saved, where) if where else None


def valid_until(login: dict, saved: dict | None) -> datetime | None:
    where = login.get("valid_until_ms")
    try:
        return datetime.fromtimestamp(_dig(saved, where) / 1000) if where else None
    except (TypeError, ValueError, OSError):
        return None


def folder(target: Path, name: str) -> Path:
    return target / PROVIDERS_REL / name


def saved_names(target: Path, name: str) -> list[str]:
    return sorted(path.stem for path in folder(target, name).glob("*.json"))


def read_saved(target: Path, name: str, account: str) -> dict | None:
    return _read_json(folder(target, name) / f"{account}.json")


def live_name(target: Path, name: str, login: dict, live: dict | None) -> str | None:
    """The saved name that holds the live login's account, or None."""
    wanted = account_id(login, live)
    if not wanted:
        return None
    for account in saved_names(target, name):
        if account_id(login, read_saved(target, name, account)) == wanted:
            return account
    return None


def env_file_value(target: Path, variable: str) -> str | None:
    """The value the installation's environment file gives a variable, or None."""
    try:
        text = (target / ENV_FILE_REL).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        key, eq, value = line.strip().partition("=")
        if not eq or key.strip() != variable or line.lstrip().startswith("#"):
            continue
        value = value.strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if value:
            return value
    return None


def store_entry(data: dict, harness: str, key: str) -> dict:
    store = data["stores"].get(harness)
    if store is None:
        return {}
    base = os.environ.get(store["base_env"]) or os.path.expanduser(store["base_default"])
    return _dig(_read_json(Path(base) / store["path"]), [key]) or {}


def credential(data: dict, spec: dict, target: Path) -> tuple[str | None, str | None]:
    """A key provider's credential and where it was found. The first is a
    secret: it is sent to the provider's own usage address and never printed."""
    variable = spec.get("env_var")
    if variable and os.environ.get(variable):
        return os.environ[variable], f"{variable} in the environment"
    if variable and (value := env_file_value(target, variable)):
        return value, f"{variable} in the environment file"
    for harness, how in spec["harnesses"].items():
        entry = store_entry(data, harness, how["store_key"]) if "store_key" in how else {}
        # A key entry holds `key`; an account entry holds `access` and no `key`.
        if value := entry.get("key") or entry.get("access"):
            return value, f"{harness} store"
    return None, None


# --- writing -----------------------------------------------------------------


def _write_private(path: Path, text: str) -> None:
    """Replace `path` through a temporary file created readable by its owner
    only. A write cut short leaves the previous content, which may be the only
    copy of a login."""
    temp = path.with_name(path.name + ".rbtv-tmp")
    handle = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
        out.write(text)
    os.replace(temp, path)


def _save(target: Path, name: str, account: str, login: dict) -> None:
    root = target / PROVIDERS_REL
    for made in (root, root / name):
        if not made.is_dir():
            made.mkdir(parents=True)
            made.chmod(0o700)
    if not (root / IGNORE_FILE).is_file():
        _write_private(root / IGNORE_FILE, IGNORE_TEXT)
    _write_private(root / name / f"{account}.json", json.dumps(login, indent=2) + "\n")


def _write_live(login: dict, saved: dict) -> None:
    """Put a saved login in the live files. A file that holds the login under
    one key keeps everything else it holds."""
    for label, place in login["files"].items():
        path = _home_path(place["path"])
        doc = saved[label]
        if "key" in place:
            doc = {**(_read_json(path) or {}), place["key"]: saved[label]}
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_private(path, json.dumps(doc, indent=2))


# --- the verbs ---------------------------------------------------------------


def _account(target: Path, name: str, account: str | None, verb: str) -> str:
    """The account name a changing verb was given. A call without one is
    refused with the saved names and the command to run next."""
    if account is None:
        names = saved_names(target, name)
        pick = "NAME" if verb == "name" or not names else names[0]
        raise usage_refusal(f"rbtv providers {verb} {name} needs an account name. "
                            f"Saved {name} names: {', '.join(names) or 'none'}",
                            f"rbtv providers {verb if pick != 'NAME' else 'name'} {name} {pick}")
    if not ACCOUNT_NAME.match(account):
        raise usage_refusal(f"account name {account!r} is not valid: use 1 to 40 lowercase letters, "
                     "digits and hyphens, starting with a letter or a digit",
                     f"rbtv providers {verb} -h")
    return account


def _saved_account(target: Path, name: str, account: str | None, verb: str) -> dict:
    names = saved_names(target, name)
    if _account(target, name, account, verb) not in names:
        raise usage_refusal(f"no {name} login is saved as {account!r}. "
                     f"Saved names: {', '.join(names) or 'none'}", f"rbtv providers list {name}")
    saved = read_saved(target, name, account)
    if saved is None:
        raise Refuse("saved-login-unreadable",
                     f"the {name} login saved as {account!r} is not readable JSON",
                     str(folder(target, name) / f"{account}.json"))
    return saved


def name_login(data: dict, target: Path, name: str, account: str | None, dry: bool) -> dict:
    login = saved_login_spec(data, name, "name")
    path = folder(target, name) / f"{_account(target, name, account, 'name')}.json"
    live = live_login(login)
    if live is None:
        files = ", ".join(place["path"] for place in login["files"].values())
        raise Refuse("login-missing",
                     f"no live {name} login to save (looked in {files}). "
                     "Log in with the harness first")
    held = path.is_file()
    if held and account_id(login, read_saved(target, name, account)) != account_id(login, live):
        exc = Refuse("name-taken",
                     f"{account!r} already holds a different {name} account. Saving over it "
                     "would delete that account's only saved login. Remove it first, or "
                     "choose another name")
        exc.next = f"rbtv providers remove-name {name} {account} --yes"
        raise exc
    if not dry:
        _save(target, name, account, live)
    return {"provider": name, "account": account, "path": str(path), "refreshed": held,
            "changed": not dry, "dry_run": dry,
            "next": f"rbtv providers {'name' if dry else 'list'} {name}" + f" {account}" * dry}


def switch_login(data: dict, target: Path, name: str, account: str | None, dry: bool) -> dict:
    login = saved_login_spec(data, name, "switch")
    saved = _saved_account(target, name, account, "switch")
    live = live_login(login)
    current = live_name(target, name, login, live)
    out = {"provider": name, "account": account, "previous": current, "dry_run": dry,
           "next": f"rbtv providers usage {name}"}
    if current == account:
        return {**out, "changed": False}
    if dry:
        out["next"] = f"rbtv providers switch {name} {account}"
    if live is not None and current is None:
        exc = Refuse("login-unsaved",
                     f"the live {name} login is saved under no name, and switching would "
                     "overwrite its only copy. Save it first")
        exc.next = f"rbtv providers name {name} NAME"
        raise exc
    if not dry:
        if current:
            # Tokens change as they are used: the live ones go back under their name.
            _save(target, name, current, live)
        _write_live(login, saved)
    return {**out, "changed": not dry}


def remove_name(data: dict, target: Path, name: str, account: str | None, yes: bool,
                dry: bool) -> dict:
    login = saved_login_spec(data, name, "remove-name")
    _saved_account(target, name, account, "remove-name")
    path = folder(target, name) / f"{account}.json"
    if live_name(target, name, login, live_login(login)) == account:
        exc = Refuse("name-live",
                     f"{account!r} is the live {name} login. Switch to another saved login first")
        exc.next = f"rbtv providers list {name}"
        raise exc
    confirm = f"rbtv providers remove-name {name} {account} --yes"
    out = {"provider": name, "account": account, "path": str(path), "dry_run": dry}
    if dry:
        return {**out, "changed": False, "next": confirm}
    if not yes:
        exc = Refuse("confirmation-required",
                     f"this would delete {path}, the only copy of the {name} login saved as "
                     f"{account!r}: using that account again would need a new login. "
                     "Re-run with --yes to delete it")
        exc.next = confirm
        exc.path = str(path)
        raise exc
    path.unlink()
    return {**out, "changed": True, "next": f"rbtv providers list {name}"}


def list_logins(data: dict, target: Path, only: str | None) -> list[dict]:
    """One row per provider: whether this machine is logged in, and the saved logins."""
    rows = []
    for name in ([only] if only else data["providers"]):
        spec = provider(data, name, "list")
        login = spec.get("saved_login")
        row = {"provider": name, "login": spec["login"], "switchable": login is not None}
        if login is None:
            _secret, source = credential(data, spec, target)
            rows.append({**row, "logged_in": source is not None, "source": source})
            continue
        live = live_login(login)
        current = live_name(target, name, login, live)
        saved = []
        for account in saved_names(target, name):
            held = read_saved(target, name, account)
            until = valid_until(login, held)
            saved.append({"name": account, "live": account == current,
                          "email": email(login, held),
                          "valid_until": f"{until:%Y-%m-%d}" if until else None,
                          "expired": bool(until and until < datetime.now())})
        rows.append({**row, "logged_in": live is not None,
                     "source": "live login files" if live is not None else None,
                     "saved": saved, "live_unsaved": live is not None and current is None})
    return rows


def list_supported(data: dict, only: str | None) -> list[dict]:
    rows = []
    for name in ([only] if only else data["providers"]):
        spec = provider(data, name, "list")
        usage = spec["usage"]
        rows.append({"provider": name, "lab": spec["lab"], "harnesses": list(spec["harnesses"]),
                     "login": spec["login"], "env_var": spec.get("env_var"),
                     "switchable": "saved_login" in spec,
                     "usage": {"source": usage["source"],
                               "from": usage.get("url") or usage.get("path")}})
    return rows


# --- text --------------------------------------------------------------------


def logins_lines(rows: list[dict]) -> list[str]:
    lines = []
    for row in rows:
        name = row["provider"]
        if not row["switchable"]:
            state = f"key present ({row['source']})" if row["logged_in"] else "no key"
            if row["login"] == "account":
                state = (f"logged in ({row['source']})" if row["logged_in"] else "not logged in")
            lines.append(f"  {name:<20} {state}")
            continue
        for saved in row["saved"]:
            tail = ""
            if saved["valid_until"]:
                tail = (f"  login valid until {saved['valid_until']}"
                        + (" (expired)" if saved["expired"] else ""))
            lines.append(f"{'*' if saved['live'] else ' '} {name + ':' + saved['name']:<20} "
                         f"{saved['email'] or '?'}{tail}")
        if row["live_unsaved"]:
            lines.append(f"  {name:<20} logged in, saved under no name. Save it before you "
                         f"switch: rbtv providers name {name} NAME")
        elif not row["saved"]:
            lines.append(f"  {name:<20} not logged in")
    return lines


def supported_lines(rows: list[dict]) -> list[str]:
    def usage_from(usage: dict) -> str:
        if usage["source"] == "endpoint":
            return urlsplit(usage["from"]).netloc
        return usage["from"] if usage["source"] == "local" else f"console: {usage['from']}"

    table = present.render_table(
        ["Provider", "Lab", "Harness", "Login", "Key variable", "Usage from"],
        [[row["provider"], row["lab"], ", ".join(row["harnesses"]),
          "account" if row["login"] == "account" else "API key",
          row["env_var"] or "-", usage_from(row["usage"])] for row in rows])
    saved = [row["provider"] for row in rows if row["switchable"]]
    return [*table, "", "Logins that can be saved and switched: "
            + (", ".join(saved) or "none") + "."]


def change_title_and_rows(verb: str, out: dict) -> tuple[str, list[tuple[str, str]]]:
    """The title and the labeled rows of a switch, name or remove-name result."""
    dry, changed = out["dry_run"], out["changed"]
    rows = [("Provider", out["provider"]), ("Account", out["account"])]
    if verb == "switch":
        title = ("switch preview" if dry else "login switched" if changed
                 else "switch, nothing to do")
        rows.append(("Live before", out["previous"] or "not logged in"))
        if changed or dry:
            rows.append(("Sessions", "running sessions keep their account; new sessions use "
                         + out["account"]))
        else:
            rows.append(("State", f"{out['account']} is already the live login"))
    elif verb == "name":
        title = "name preview" if dry else "login saved"
        rows.append(("Would write" if dry else "Wrote", out["path"]))
        rows.append(("Name", "refreshes the login it already held" if out["refreshed"]
                     else "new"))
    else:
        title = "remove-name preview" if dry else "saved login deleted"
        rows.append(("Would delete" if dry else "Deleted", out["path"]))
    return title, rows


# --- the command -------------------------------------------------------------


def command(args, data: dict, target: Path) -> int:
    """`rbtv providers list|switch|name|remove-name`: run the verb, print its result."""
    verb, as_json = args.providers_verb, bool(args.json)
    if verb == "list":
        rows = (list_supported(data, args.provider) if args.supported
                else list_logins(data, target, args.provider))
        next_cmd = "rbtv providers list" if args.supported else "rbtv providers usage"
        if as_json:
            print(json.dumps({"ok": True, "installation": str(target),
                              "supported" if args.supported else "providers": rows,
                              "next": next_cmd}, indent=2))
            return 0
        print(present.title("supported providers" if args.supported else "providers list"))
        print()
        if args.supported:
            print("\n".join(supported_lines(rows)))
        else:
            print(f"Installation: {target}")
            print("\n".join(logins_lines(rows)))
        print()
        print("Next: " + next_cmd)
        return 0
    dry = bool(args.dry_run)

    def change() -> dict:
        if verb == "switch":
            return switch_login(data, target, args.provider, args.account, dry)
        if verb == "name":
            return name_login(data, target, args.provider, args.account, dry)
        return remove_name(data, target, args.provider, args.account, bool(args.yes), dry)

    if dry:
        out = change()
    else:
        with installation_mutation_lock(target):
            out = change()
    if as_json:
        print(json.dumps({"ok": True, "installation": str(target), **out}, indent=2))
        return 0
    title, rows = change_title_and_rows(verb, out)
    print(present.title(title))
    print()
    print("\n".join(present.fields([*rows, ("Installation", str(target))])))
    print()
    print("Next: " + out["next"])
    return 0
