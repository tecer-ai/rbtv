"""`rbtv providers`: saved logins, switching, usage, and the help pages.

Every check runs against a throwaway home folder and installation, and the
network reader is replaced: no check reads a real login or opens a connection.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import time
from pathlib import Path
from unittest.mock import patch

from lib import providers, usage
from lib.commands import main
from lib.constants import PROVIDERS_REL, STATE_REL
from lib.parser import build_parser

from .fixture import _w

CLAUDE_URL = "https://api.anthropic.com/api/oauth/usage"
DEEPSEEK_URL = "https://api.deepseek.com/user/balance"


def _run(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    """One command line, run from `cwd`: exit code, standard output, standard error."""
    out, err = io.StringIO(), io.StringIO()
    before = Path.cwd()
    os.chdir(cwd)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["providers", *argv])
    finally:
        os.chdir(before)
    return code, out.getvalue(), err.getvalue()


def _claude_login(home: Path, uuid: str, token: str, *, expires_ms: int | None = None) -> None:
    far = int((time.time() + 86400) * 1000)
    _w(home / ".claude/.credentials.json", json.dumps({"claudeAiOauth": {
        "accessToken": token, "expiresAt": far if expires_ms is None else expires_ms,
        "refreshTokenExpiresAt": far}}))
    _w(home / ".claude.json", json.dumps({
        "keep": "me", "oauthAccount": {"accountUuid": uuid,
                                       "emailAddress": f"{uuid}@example.invalid"}}))


def provider_accounts(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    print("\nPROV — rbtv providers")
    home, ws = tmp / "prov-home", tmp / "prov-installation"
    home.mkdir()
    _w(ws / STATE_REL, "{}\n")
    agent_home = ws / ".rbtv/agents/scout"
    agent_home.mkdir(parents=True)
    env = {key: value for key, value in os.environ.items()
           if not key.endswith("_API_KEY")}
    env.update(HOME=str(home), USERPROFILE=str(home), XDG_DATA_HOME=str(home / "xdg"),
               RBTV_AGENT_HOME=str(agent_home))
    env.pop("NO_COLOR", None)
    calls: list[tuple[str, dict]] = []

    def fake_get_json(url: str, headers: dict) -> dict:
        calls.append((url, headers))
        if url == CLAUDE_URL:
            return {"limits": [{"kind": "session", "percent": 1},
                               {"kind": "weekly_all", "percent": 2},
                               {"kind": "weekly_scoped", "percent": 3,
                                "scope": {"model": {"display_name": "Fable"}}}]}
        if url == DEEPSEEK_URL:
            return {"balance_infos": [{"total_balance": "9.5", "currency": "USD"}]}
        raise ConnectionError(url)

    def js(argv: list[str], cwd: Path = ws) -> tuple[int, dict]:
        code, out, _err = _run([*argv, "--json"], cwd)
        return code, json.loads(out)

    root = ws / PROVIDERS_REL
    saved = root / "claude"
    with patch.dict(os.environ, env, clear=True), patch("lib.usage.get_json", fake_get_json):
        data = providers.load()
        check("PROV-file — providers.json loads and names known harnesses only",
              len(data["providers"]) == 8 and providers.switchable(data) == ["claude", "codex"])

        code, listed = js(["list"])
        claude = next(row for row in listed["providers"] if row["provider"] == "claude")
        check("PROV-list-empty — no saved login: every provider has a row, none logged in",
              code == 0 and listed["ok"] and listed["installation"] == str(ws)
              and len(listed["providers"]) == 8
              and not any(row["logged_in"] for row in listed["providers"])
              and claude["saved"] == [] and not claude["live_unsaved"], repr(listed))
        check("PROV-list-empty-writes-nothing — a read creates no folder", not root.exists())

        code, supported = js(["list", "--supported"])
        check("PROV-supported — providers only: lab, harnesses, login, usage source",
              code == 0 and [row["provider"] for row in supported["supported"]]
              == list(data["providers"])
              and set(supported["supported"][0])
              == {"provider", "lab", "harnesses", "login", "env_var", "switchable", "usage"},
              repr(supported))

        _claude_login(home, "u-a", "tokA9")
        code, listed = js(["list", "claude"])
        check("PROV-list-unsaved — a live login under no name is flagged",
              listed["providers"][0]["logged_in"] and listed["providers"][0]["live_unsaved"])
        code, preview = js(["name", "claude", "work", "--dry-run"])
        check("PROV-name-dry-run — the preview writes nothing",
              code == 0 and preview["dry_run"] and not preview["changed"] and not root.exists(),
              repr(preview))
        code, named = js(["name", "claude", "work"])
        check("PROV-name — the live login is saved in the installation, not the agent folder",
              code == 0 and named["changed"] and not named["refreshed"]
              and named["path"] == str(saved / "work.json") and (saved / "work.json").is_file()
              and not (agent_home / ".rbtv").exists(), repr(named))
        ignore = root / ".gitignore"
        check("PROV-gitignore — the first write adds a .gitignore holding *",
              ignore.is_file() and ignore.read_text(encoding="utf-8") == "*\n")
        if os.name != "nt":
            check("PROV-modes — folder 700, saved login 600",
                  (root.stat().st_mode & 0o777, saved.stat().st_mode & 0o777,
                   (saved / "work.json").stat().st_mode & 0o777) == (0o700, 0o700, 0o600))
        code, listed = js(["list", "claude"])
        check("PROV-list-saved — name then list shows it as the live one",
              listed["providers"][0]["saved"] == [
                  {"name": "work", "live": True, "email": "u-a@example.invalid",
                   "valid_until": listed["providers"][0]["saved"][0]["valid_until"],
                   "expired": False}]
              and not listed["providers"][0]["live_unsaved"], repr(listed))
        code, text, _err = _run(["list"], ws)
        check("PROV-list-text — the title, the starred live name and the next command",
              code == 0 and text.startswith("rbtv — providers list\n\n")
              and "* claude:work" in text and "Next: rbtv providers usage" in text, text)

        # A second account logs in: the name `work` holds a different one.
        _claude_login(home, "u-b", "tokB9")
        code, refused = js(["switch", "claude", "work"])
        check("PROV-switch-unsaved — an unsaved live login is never overwritten",
              code == 1 and refused["error"]["code"] == "login-unsaved"
              and refused["changed"] is False and "target" in refused
              and refused["next"] == "rbtv providers name claude NAME"
              and "tokB9" in (home / ".claude/.credentials.json").read_text(encoding="utf-8"),
              repr(refused))
        code, refused = js(["name", "claude", "work"])
        check("PROV-name-taken — a name that holds a different account is refused",
              code == 1 and refused["error"]["code"] == "name-taken"
              and '"tokA9"' in (saved / "work.json").read_text(encoding="utf-8"), repr(refused))
        js(["name", "claude", "other"])
        _claude_login(home, "u-b", "tokB9x")  # the harness renewed its token
        code, switched = js(["switch", "claude", "work"])
        live = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
        check("PROV-switch — the saved login becomes live and the rest of the file stays",
              code == 0 and switched["changed"] and switched["previous"] == "other"
              and live == {"keep": "me", "oauthAccount": {
                  "accountUuid": "u-a", "emailAddress": "u-a@example.invalid"}}
              and '"tokA9"' in (home / ".claude/.credentials.json").read_text(encoding="utf-8"),
              repr(switched))
        check("PROV-switch-saves-back — the outgoing login keeps its newest token",
              '"tokB9x"' in (saved / "other.json").read_text(encoding="utf-8"))
        code, again = js(["switch", "claude", "work"])
        check("PROV-switch-noop — switching to the live name changes nothing",
              code == 0 and again["changed"] is False)

        code, refused = js(["remove-name", "claude", "other"])
        check("PROV-remove-needs-yes — without --yes nothing is deleted",
              code == 1 and refused["error"]["code"] == "confirmation-required"
              and refused["next"] == "rbtv providers remove-name claude other --yes"
              and (saved / "other.json").is_file(), repr(refused))
        code, refused = js(["remove-name", "claude", "work", "--yes"])
        check("PROV-remove-live — the live name is refused",
              code == 1 and refused["error"]["code"] == "name-live"
              and (saved / "work.json").is_file(), repr(refused))

        for bad in ("../x", "a:b", "Work", "x" * 41):
            code, refused = js(["name", "claude", bad])
            check(f"PROV-account-name — {bad[:8]!r} is refused as invalid arguments",
                  code == 2 and refused["error"]["code"] == "usage"
                  and sorted(path.name for path in saved.iterdir())
                  == ["other.json", "work.json"]
                  and not (root / "x.json").exists(), repr(refused))
        code, refused = js(["name", "zai", "main"])
        check("PROV-not-switchable — a key provider has no login to save",
              code == 2 and "claude, codex" in refused["error"]["message"], repr(refused))
        code, refused = js(["list", "claud"])
        check("PROV-provider-unknown — the refusal names the close and the known providers",
              code == 2 and "Did you mean: claude?" in refused["error"]["message"]
              and "deepseek" in refused["error"]["message"], repr(refused))
        code, _out, err = _run(["switch", "claude", "nope"], ws)
        check("PROV-account-unknown — the refusal lists the saved names",
              code == 2 and "REFUSED [usage]" in err and "other, work" in err
              and "--target" not in err, err)

        # A changing verb without ACCOUNT: refused with the saved names and the next command.
        for verb, next_cmd in (("switch", "rbtv providers switch claude other"),
                               ("name", "rbtv providers name claude NAME"),
                               ("remove-name", "rbtv providers remove-name claude other")):
            code, refused = js([verb, "claude"])
            check(f"PROV-account-missing — a bare {verb} lists the saved names",
                  code == 2 and refused["error"]["code"] == "usage"
                  and "other, work" in refused["error"]["message"]
                  and refused["next"] == next_cmd and refused["changed"] is False
                  and sorted(path.name for path in saved.iterdir())
                  == ["other.json", "work.json"], repr(refused))
        code, _out, err = _run(["switch", "codex"], ws)
        check("PROV-account-missing-none — with no saved name the next command saves one",
              code == 2 and "Saved codex names: none" in err
              and "next: rbtv providers name codex NAME" in err, err)

        # Usage: the stored token of each saved name; a key from opencode's store.
        _w(home / "xdg/opencode/auth.json", json.dumps({
            "deepseek": {"type": "api", "key": "sk-secret-1"},
            "xai": {"type": "oauth", "access": "tok-secret-2", "refresh": "r"}}))
        stale = json.loads((saved / "other.json").read_text(encoding="utf-8"))
        stale["credentials"]["claudeAiOauth"]["expiresAt"] = 1000
        _w(saved / "other.json", json.dumps(stale))
        calls.clear()
        code, out, _err = _run(["usage", "--json"], ws)
        read = json.loads(out)
        by_label = {row["label"]: row for row in read["rows"]}
        check("PROV-usage-json — {ok, installation, rows, errors}; a row is "
              "{provider, account, live, label, data}",
              code == 0 and read["ok"] and read["installation"] == str(ws)
              and all(set(row) == {"provider", "account", "live", "label", "data"}
                      for row in read["rows"])
              and [w["label"] for w in by_label["claude:work*"]["data"]["windows"]]
              == ["5h", "7d", "7d fable"], out)
        check("PROV-usage-expired — an expired token is reported, never an empty window",
              "expired" in by_label["claude:other"]["data"]["error"]
              and "windows" not in by_label["claude:other"]["data"], out)
        check("PROV-usage-rows-with-errors — unread rows are counted and the exit is 0",
              read["errors"] == sum(1 for row in read["rows"] if "error" in row["data"])
              and read["errors"] >= 3)
        check("PROV-usage-store — a key and an account entry of opencode's store both count",
              by_label["deepseek"]["data"] == {"balance": "9.5", "currency": "USD"}
              and by_label["xai"]["data"]["note"].startswith("logged in"), out)
        check("PROV-usage-own-address — each key goes to its own provider only",
              sorted(calls, key=lambda call: call[0]) == [
                  (CLAUDE_URL, {"Authorization": "Bearer tokA9",
                                "anthropic-beta": "oauth-2025-04-20"}),
                  (DEEPSEEK_URL, {"Authorization": "Bearer sk-secret-1"})], repr(calls))
        code, text, _err = _run(["usage"], ws)
        listing = _run(["list"], ws)[1] + _run(["list", "--json"], ws)[1]
        check("PROV-no-secret — no key or token appears in any output",
              not any(secret in out + text + listing
                      for secret in ("tokA9", "tokB9x", "sk-secret-1", "tok-secret-2")))
        check("PROV-usage-text — led by the count of rows that could not be read",
              code == 0 and text.startswith("rbtv — providers usage\n\n")
              and re.search(r"^\d+ of \d+ rows could not be read\.$", text, re.M) is not None,
              text)
        for argv, label in ((["usage", "claude", "nope"], "an unknown saved name"),
                            (["usage", "zai", "main"], "an account on a key provider"),
                            (["usage", "--posh"], "--posh with --json"),
                            (["usage", "--interval", "60"], "--interval without --posh")):
            code, refused = js(argv)
            check(f"PROV-usage-refuses — {label}",
                  code == 2 and refused["error"]["code"] == "usage", repr(refused))
        with patch("lib.tui.RICH_MODE_OVERRIDE", False):
            code, _out, err = _run(["usage", "--posh"], ws)
        check("PROV-posh-needs-terminal — refused when output is not a terminal",
              code == 2 and "needs a terminal" in err, err)

        code, removed = js(["remove-name", "claude", "other", "--yes"])
        check("PROV-remove — with --yes the saved login is deleted",
              code == 0 and removed["changed"] and not (saved / "other.json").exists(),
              repr(removed))

        # No installation: the current folder and a bare `.rbtv/` never stand in.
        bare = tmp / "prov-none"
        (bare / ".rbtv").mkdir(parents=True)
        code, refused = js(["list"], bare)
        check("PROV-no-installation — refused in the one JSON form, naming no target",
              code == 1 and refused == {
                  "ok": False, "changed": False,
                  "error": {"code": "installation-unknown",
                            "message": refused["error"]["message"]}}
              and STATE_REL.as_posix() in refused["error"]["message"], repr(refused))
        code, _out, err = _run(["name", "claude", "work"], bare)
        check("PROV-no-installation-text — the text refusal, and nothing written",
              code == 1 and "REFUSED [installation-unknown]" in err
              and not (bare / PROVIDERS_REL).exists(), err)
        code, _out, err = _run(["list", "--target", str(ws)], ws)
        check("PROV-no-target — these verbs take no --target", code == 2, err)

    # The parsers and the full-screen frame, on measured reply shapes.
    check("PROV-parse-zai", usage.parse_zai({"data": {"level": "pro", "limits": [
        {"type": "TOKENS_LIMIT", "unit": 3, "number": 5, "percentage": 12.5,
         "nextResetTime": 1786000000000}]}}) == {
             "windows": [{"label": "5h", "pct": 12.5, "resets_at": 1786000000}], "plan": "pro"}
          and "error" in usage.parse_zai({"data": {"limits": []}}))
    kimi = usage.parse_kimi({
        "usage": {"limit": "100", "used": "3", "resetTime": "2026-08-17T16:45:32+00:00"},
        "limits": [{"window": {"duration": 300, "timeUnit": "TIME_UNIT_MINUTE"},
                    "detail": {"limit": "100", "used": "1",
                               "resetTime": "2026-08-14T13:45:32+00:00"}}]})
    check("PROV-parse-kimi — string counts, a 300-minute window",
          [(w["label"], w["pct"]) for w in kimi["windows"]] == [("5h", 1.0), ("plan", 3.0)]
          and "error" in usage.parse_kimi({"limits": [], "usage": {}}))
    sessions = tmp / "prov-codex-sessions"
    _w(sessions / "2026/10/07/rollout-1.jsonl", "not json rate_limits\n" + json.dumps({
        "payload": {"rate_limits": {
            "plan_type": "pro", "primary": {"used_percent": 5, "window_minutes": 300},
            "secondary": {"used_percent": 9, "window_minutes": 10080}}}}) + "\n")
    codex = usage.parse_codex_sessions(sessions)
    check("PROV-parse-codex — the newest session file's last rate limits",
          [w["label"] for w in codex.get("windows", [])] == ["5h", "7d"]
          and codex.get("plan") == "pro"
          and "error" in usage.parse_codex_sessions(tmp / "prov-no-sessions"), repr(codex))
    long_row = [{"provider": "claude", "account": "x", "live": True, "label": "claude:x",
                 "data": {"error": "token expired " + "y" * 200}}]
    with patch.dict(os.environ, {}, clear=True):
        frame = usage.posh_lines(long_row, 60, time.time())
    check("PROV-posh-fits — every line of the frame fits the terminal width",
          "\033[" in "".join(frame)
          and all(len(re.sub(r"\033\[[0-9;]*m", "", line)) <= 60 for line in frame))
    with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=True):
        check("PROV-posh-no-color — NO_COLOR removes every colour",
              "\033[" not in "".join(usage.posh_lines(
                  [{**long_row[0], "data": {"windows": [
                      {"label": "5h", "pct": 50.0, "resets_at": None}]}}],
                  80, time.time())))

    # Every option and positional a `providers` command takes is named on its page.
    group = next(action for action in build_parser()._actions
                 if isinstance(action, argparse._SubParsersAction)).choices["providers"]
    verbs = next(action for action in group._actions
                 if isinstance(action, argparse._SubParsersAction)).choices
    check("PROV-help-verbs — the group page names every verb",
          all(f"  {verb} " in group.format_help() for verb in verbs), repr(list(verbs)))
    for verb, sub in verbs.items():
        page = sub.format_help()
        usage_lines = page.split("\n\n")[1]
        missing = []
        for action in sub._actions:
            names = action.option_strings or [action.metavar]
            listed = re.search(rf"^  (?:-\w, )?{re.escape(max(names, key=len))}\b", page, re.M)
            if not listed or not any(name in usage_lines for name in names):
                missing.append(names[-1])
        check(f"PROV-help-options — providers {verb} names every option on its page",
              not missing, repr(missing))
