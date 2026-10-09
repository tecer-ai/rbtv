"""External component checkouts: discovery, add and update repositories.

Uses local git remotes only. Isolates HOME and git config. Does not call a
public remote or the live installation.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

from discovery import Refuse, file_rows, scan_all

from lib.agents import add_agent
from lib.commands import cmd_add, cmd_agent, cmd_show, cmd_update
from lib.help_pages import PAGES
from lib.interactive import interactive
from lib.parser import build_parser
from lib.pathlinks import bin_dir, link_path
from lib.schema import errors, load
from lib.state import read_state

from .fixture import _component, _w


def _git(cwd: Path | None, *args: str, env: dict) -> subprocess.CompletedProcess:
    cmd = ["git", *args]
    return subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False)


def _identity(cwd: Path | None, *args: str, env: dict) -> None:
    proc = _git(cwd, "-c", "user.name=rbtv-test", "-c",
                "user.email=rbtv-test@example.invalid", *args, env=env)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)


def _snap(root: Path) -> dict:
    out = {}
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            out[rel] = ("link", os.readlink(path))
        elif path.is_file():
            out[rel] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
        else:
            out[rel] = ("dir",)
    return out


def _run(handler, argv: list[str], target: Path, catalog: dict):
    out, err = io.StringIO(), io.StringIO()
    code = None
    exc = None
    import contextlib
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = handler(build_parser().parse_args(argv), target, catalog, [])
    except Refuse as caught:
        exc = caught
    return code, out.getvalue(), err.getvalue(), exc


def _tool(comp: Path, name: str) -> None:
    tool = comp / "capabilities" / "tools" / name
    _w(tool / f"{name}.json", json.dumps({
        "name": name, "description": f"The {name} tool", "entry": "wrapper.py"}))
    _w(tool / "wrapper.py", "#!/usr/bin/env python3\nprint('wrapper')\n")
    (tool / "wrapper.py").chmod(0o755)


def _record(comp: Path, url: str, branch: str, requirements: str | None) -> None:
    body = {"description": "A component with an external checkout",
            "dependencies": [],
            "repository": {"url": url, "branch": branch}}
    if requirements is not None:
        body["repository"]["requirements"] = requirements
    _w(comp / f"{comp.name}.json", json.dumps(body))


def repositories(ctx) -> None:
    check = ctx.check
    base = ctx.tmp / "repo-space dir"
    home = base / "home"
    home.mkdir(parents=True)
    env = os.environ.copy()
    env.update(HOME=str(home), USERPROFILE=str(home),
               XDG_CONFIG_HOME=str(home / "xdg"),
               GIT_CONFIG_GLOBAL=str(home / "gitconfig"),
               GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
    (home / "gitconfig").write_text("", encoding="utf-8")
    saved = {key: os.environ.get(key) for key in env}
    os.environ.update(env)
    print("\nRE — external component repositories")
    try:
        _repositories(ctx, check, base, env)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _repositories(ctx, check, base: Path, env: dict) -> None:
    bare = base / "remote.git"
    seed = base / "seed"
    _identity(None, "init", "--bare", str(bare), env=env)
    _identity(None, "init", "-b", "feat/cli", str(seed), env=env)
    (seed / "requirements.txt").write_text("", encoding="utf-8")
    _identity(seed, "add", "requirements.txt", env=env)
    _identity(seed, "commit", "-m", "init", env=env)
    _identity(seed, "remote", "add", "origin", str(bare), env=env)
    _identity(seed, "push", "-u", "origin", "feat/cli", env=env)
    url = str(bare.resolve())

    src = base / "src"
    comp = _component(src, "extmod", "extcomp")
    _record(comp, url, "feat/cli", "requirements.txt")
    _tool(comp, "exttool")
    catalog, _shadowed = scan_all(base / "mirror-empty", src)
    row = catalog["extmod/extcomp"]
    checkout = Path(row["path"]) / "repository"
    check("RE-discover — record is in the catalog before any checkout",
          row.get("repository", {}).get("branch") == "feat/cli"
          and not checkout.exists()
          and any(item["id"] == "exttool" for item in file_rows(row)),
          str(row.get("repository")))

    bad = base / "bad"
    bad_comp = _component(bad, "badmod", "badcomp")
    _record(bad_comp, url, "feat/cli", "../secret")
    refused = None
    try:
        scan_all(base / "bad-mirror", bad)
    except Refuse as exc:
        refused = exc
    schema_bad = errors({"description": "x", "dependencies": [],
                         "repository": {"url": url, "branch": "feat/cli",
                                        "requirements": "../secret", "hook": "rm -rf"}},
                        load("component-json"))
    dash_bad = errors({"description": "x", "dependencies": [],
                       "repository": {"url": "--upload-pack=touch", "branch": "feat/cli"}},
                      load("component-json"))
    check("RE-schema — requirements escape and an unknown field fail at discovery",
          refused is not None and refused.code == "record-invalid"
          and schema_bad, str(refused and refused.message))
    check("RE-schema-dash — a url that starts with a dash is not a record",
          bool(dash_bad), str(dash_bad))

    target = base / "inst"
    target.mkdir()
    before = (_snap(src), _snap(target), _snap(base / "home"))
    code, out, err, exc = _run(
        cmd_add, ["add", "exttool", "--harness", "claude", "--guidance", "none",
                  "--target", str(target), "--dry-run", "--json"],
        target, catalog)
    after = (_snap(src), _snap(target), _snap(base / "home"))
    preview = json.loads(out) if code == 0 else {}
    check("RE-dry-add — preview names the clone and writes nothing",
          code == 0 and exc is None
          and preview.get("repositories", [{}])[0].get("action") == "would-clone"
          and "space dir" in preview["repositories"][0]["path"]
          and not checkout.exists() and before == after,
          f"snap={before == after} exists={checkout.exists()} {out[:400]}")

    code, out, err, exc = _run(
        cmd_add, ["add", "exttool", "--harness", "claude", "--guidance", "none",
                  "--target", str(target), "--json"],
        target, catalog)
    added = json.loads(out) if code == 0 else {}
    head = _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip()
    stamp = checkout / ".venv" / ".rbtv-setup"
    check("RE-add — clones the configured branch and installs requirements",
          code == 0 and added.get("repositories", [{}])[0].get("action") == "cloned"
          and added["repositories"][0].get("setup") == "installed"
          and "space dir" in str(checkout) and checkout.is_dir()
          and head == _git(bare, "rev-parse", "feat/cli", env=env).stdout.strip()
          and stamp.is_file()
          and "extmod/extcomp#exttool" in read_state(target).get("files", []),
          out[:500] + err[:300])
    sentinel = checkout / ".venv" / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    stamp_m = stamp.stat().st_mtime_ns
    code, out, _err, exc = _run(
        cmd_add, ["add", "exttool", "--json"], target, catalog)
    again = json.loads(out) if code == 0 else {}
    check("RE-add-again — existing checkout is not fetched and setup is not repeated",
          code == 0 and again.get("repositories", [{}])[0].get("action") == "present"
          and again["repositories"][0].get("setup") == "skipped"
          and stamp.stat().st_mtime_ns == stamp_m and sentinel.read_text(encoding="utf-8") == "keep"
          and _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip() == head,
          out[:400])

    (seed / "marker.txt").write_text("one", encoding="utf-8")
    _identity(seed, "add", "marker.txt", env=env)
    _identity(seed, "commit", "-m", "marker", env=env)
    _identity(seed, "push", "origin", "feat/cli", env=env)
    code, out, _err, exc = _run(cmd_add, ["add", "exttool", "--json"], target, catalog)
    check("RE-add-no-pull — a later add leaves the checkout at the old commit",
          code == 0 and not (checkout / "marker.txt").exists()
          and _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip() == head,
          out[:300])
    code, out, err, exc = _run(
        cmd_update, ["update", "repositories", "--json"], target, catalog)
    updated = json.loads(out) if code == 0 else {}
    check("RE-update — fast-forwards and reruns setup",
          code == 0 and updated.get("repositories", [{}])[0].get("action") == "updated"
          and updated["repositories"][0].get("setup") == "installed"
          and (checkout / "marker.txt").read_text(encoding="utf-8") == "one"
          and stamp.stat().st_mtime_ns != stamp_m,
          out[:400] + err[:200])
    stamp_m = stamp.stat().st_mtime_ns
    current = _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip()
    code, out, _err, exc = _run(
        cmd_update, ["update", "repositories", "--json"], target, catalog)
    idle = json.loads(out) if code == 0 else {}
    check("RE-update-current — a second update does not reinstall",
          code == 0 and idle.get("repositories", [{}])[0].get("action") == "up-to-date"
          and idle["repositories"][0].get("setup") == "skipped"
          and stamp.stat().st_mtime_ns == stamp_m,
          out[:300])

    (seed / "later.txt").write_text("two", encoding="utf-8")
    _identity(seed, "add", "later.txt", env=env)
    _identity(seed, "commit", "-m", "later", env=env)
    _identity(seed, "push", "origin", "feat/cli", env=env)
    (checkout / "credentials.env").write_text("secret", encoding="utf-8")
    origin_ref = _git(checkout, "rev-parse", "origin/feat/cli", env=env).stdout.strip()
    code, out, err, exc = _run(
        cmd_update, ["update", "repositories"], target, catalog)
    check("RE-dirty — refuses, does not fetch, and keeps the untracked file",
          exc is not None and exc.code == "repository-dirty"
          and "credentials.env" in exc.message
          and (checkout / "credentials.env").read_text(encoding="utf-8") == "secret"
          and not (checkout / "later.txt").exists()
          and _git(checkout, "rev-parse", "origin/feat/cli", env=env).stdout.strip() == origin_ref,
          str(exc and exc.message))
    (checkout / "credentials.env").unlink()

    (checkout / "local.txt").write_text("local", encoding="utf-8")
    _identity(checkout, "add", "local.txt", env=env)
    _identity(checkout, "commit", "-m", "local", env=env)
    local_head = _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip()
    (seed / "other.txt").write_text("other", encoding="utf-8")
    _identity(seed, "add", "other.txt", env=env)
    _identity(seed, "commit", "-m", "other", env=env)
    _identity(seed, "push", "origin", "feat/cli", env=env)
    code, out, err, exc = _run(
        cmd_update, ["update", "repositories"], target, catalog)
    check("RE-diverged — refuses and does not reset",
          exc is not None and exc.code == "repository-diverged"
          and (checkout / "local.txt").is_file()
          and _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip() == local_head,
          str(exc and exc.message))

    saved_url = catalog["extmod/extcomp"]["repository"]["url"]
    catalog["extmod/extcomp"]["repository"]["url"] = str(base / "other.git")
    code, out, err, exc = _run(cmd_add, ["add", "exttool"], target, catalog)
    check("RE-remote — wrong origin is refused and the checkout is unchanged",
          exc is not None and exc.code == "repository-remote"
          and _git(checkout, "remote", "get-url", "origin", env=env).stdout.strip() == saved_url
          and _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip() == local_head,
          str(exc and exc.message))
    catalog["extmod/extcomp"]["repository"]["url"] = saved_url
    catalog["extmod/extcomp"]["repository"]["branch"] = "other"
    code, out, err, exc = _run(cmd_add, ["add", "exttool"], target, catalog)
    check("RE-branch — wrong branch is refused",
          exc is not None and exc.code == "repository-branch"
          and _git(checkout, "symbolic-ref", "--short", "HEAD", env=env).stdout.strip() == "feat/cli",
          str(exc and exc.message))
    catalog["extmod/extcomp"]["repository"]["branch"] = "feat/cli"

    absent_src = base / "absent-src"
    absent = _component(absent_src, "extmod", "absent")
    _record(absent, url, "feat/cli", None)
    _tool(absent, "absenttool")
    absent_catalog, _s = scan_all(base / "absent-mirror", absent_src)
    absent_target = base / "absent-inst"
    absent_target.mkdir()
    code, out, err, exc = _run(
        cmd_add, ["add", "absenttool", "--harness", "claude", "--guidance", "none",
                  "--json"], absent_target, absent_catalog)
    absent_checkout = Path(absent_catalog["extmod/absent"]["path"]) / "repository"
    check("RE-add-no-requirements — clones without creating a Python environment",
          code == 0 and absent_checkout.is_dir() and not (absent_checkout / ".venv").exists(),
          out[:300] + err[:200])
    import shutil
    shutil.rmtree(absent_checkout)
    code, out, err, exc = _run(
        cmd_update, ["update", "repositories"], absent_target, absent_catalog)
    check("RE-missing — update does not clone a missing checkout",
          exc is not None and exc.code == "repository-missing"
          and not absent_checkout.exists(),
          str(exc and exc.message))

    fail_src = base / "fail-src"
    fail = _component(fail_src, "extmod", "failcomp")
    _record(fail, str(base / "missing remote.git"), "feat/cli", "requirements.txt")
    _tool(fail, "failtool")
    fail_catalog, _s = scan_all(base / "fail-mirror", fail_src)
    fail_target = base / "fail-inst"
    fail_target.mkdir()
    code, out, err, exc = _run(
        cmd_add, ["add", "failtool", "--harness", "claude", "--guidance", "none"],
        fail_target, fail_catalog)
    check("RE-clone-fail — a missing remote refuses and does not install",
          exc is not None and exc.code == "repository-clone"
          and not (fail_target / ".rbtv" / "config" / "install.json").exists(),
          str(exc and exc.message))

    setup_src = base / "setup-src"
    setup = _component(setup_src, "extmod", "setupcomp")
    _record(setup, url, "feat/cli", "missing.txt")
    _tool(setup, "setuptool")
    setup_catalog, _s = scan_all(base / "setup-mirror", setup_src)
    setup_target = base / "setup-inst"
    setup_target.mkdir()
    code, out, err, exc = _run(
        cmd_add, ["add", "setuptool", "--harness", "claude", "--guidance", "none",
                  "--json"], setup_target, setup_catalog)
    setup_checkout = Path(setup_catalog["extmod/setupcomp"]["path"]) / "repository"
    setup_body = json.loads(out) if out.startswith("{") else {}
    check("RE-setup-fail — keeps the checkout and does not install the file",
          code == 1 and exc is None and "repository-setup" in (out + err)
          and "Nothing was changed" not in (out + err)
          and setup_body.get("repository_changed") is True
          and setup_body.get("changed") is False
          and setup_checkout.is_dir()
          and not (setup_target / ".rbtv" / "config" / "install.json").exists(),
          out[:400] + err[:300])

    shown_code, shown, _err, shown_exc = _run(
        cmd_show, ["show", "extmod/extcomp", "--json"], target, catalog)
    shown_data = json.loads(shown) if shown_code == 0 else {}
    repo = (shown_data.get("selection") or {}).get("repository") or {}
    check("RE-show — names the repository and whether the checkout exists",
          shown_exc is None and repo.get("url") == url and repo.get("present") is True,
          shown[:300])

    scope = build_parser().parse_args(["update", "repositories", "--dry-run"])
    agent_exc = None
    try:
        cmd_agent(build_parser().parse_args(
            ["agent", "update", "scout", "repositories"]), target, catalog, [])
    except Refuse as caught:
        agent_exc = caught
    check("RE-help — repositories is a root scope and not an agent scope",
          scope.scope == "repositories" and scope.dry_run
          and "repositories" in PAGES["update"]
          and "Does not clone" in PAGES["update"]
          and "not cloned" in PAGES["update repositories"]
          and "do not download a newer rbtv" in PAGES["update"]
          and "{guidance,scaffolding,all}" in PAGES["agent update"]
          and agent_exc is not None and agent_exc.code == "usage"
          and "repositories" in agent_exc.message,
          str(agent_exc and agent_exc.message))

    dry_before = _git(checkout, "rev-parse", "origin/feat/cli", env=env).stdout.strip()
    snap = _snap(checkout)
    code, out, err, exc = _run(
        cmd_update, ["update", "repositories", "--dry-run", "--json"], target, catalog)
    preview = json.loads(out) if code == 0 and out else {}
    check("RE-dry-update — preview does not fetch or write",
          code == 0 and exc is None
          and preview.get("repositories", [{}])[0].get("action") == "would-fetch"
          and _snap(checkout) == snap
          and _git(checkout, "rev-parse", "origin/feat/cli", env=env).stdout.strip() == dry_before,
          f"snap={_snap(checkout) == snap} {out[:400]}{err[:200]}")
    _boundary(check, base, env, url)


def _agent(root: Path) -> None:
    home = root / ".rbtv" / "agents" / "scout"
    _w(home / "prompt.md", "Follow this.\n")
    _w(home / "agent.json", json.dumps({
        "name": "scout", "description": "Scout.", "harness": "claude",
        "model": "haiku-4-5", "effort": "low", "files": [], "packs": []}) + "\n")


def _boundary(check, base: Path, env: dict, url: str) -> None:
    """Agent add, interactive, and scaffolding share install-mode preparation."""
    known = {"claude": {"haiku-4-5": {"rungs": ["low", "high"], "selected": True}}}
    src = base / "bound-src"
    comp = _component(src, "extmod", "boundcomp")
    _record(comp, url, "feat/cli", "requirements.txt")
    _tool(comp, "boundtool")
    _w(comp / "packs" / "boundkit.json", json.dumps({
        "description": "Pack that selects the external tool",
        "files": ["extmod/boundcomp#boundtool"]}))
    catalog, _shadowed = scan_all(base / "bound-mirror", src)
    checkout = Path(catalog["extmod/boundcomp"]["path"]) / "repository"
    root = base / "bound-inst"
    root.mkdir()
    _agent(root)
    with patch("lib.agents.cast_catalog", return_value=known):
        added = add_agent(root, "scout", [], {"boundkit"}, catalog, False)
    repos = (added.get("harness_files") or {}).get("repositories") or []
    head = _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip()
    check("RE-agent-add — a pack clones the tool checkout and installs requirements",
          repos and repos[0].get("action") == "cloned" and repos[0].get("setup") == "installed"
          and checkout.is_dir() and (checkout / ".venv" / ".rbtv-setup").is_file()
          and head == _git(base / "remote.git", "rev-parse", "feat/cli", env=env).stdout.strip(),
          str(repos)[:400])
    (base / "seed" / "bound-later.txt").write_text("later", encoding="utf-8")
    _identity(base / "seed", "add", "bound-later.txt", env=env)
    _identity(base / "seed", "commit", "-m", "bound later", env=env)
    _identity(base / "seed", "push", "origin", "feat/cli", env=env)
    with patch("lib.agents.cast_catalog", return_value=known):
        again = add_agent(root, "scout", [], set(), catalog, False)
    again_repos = (again.get("harness_files") or {}).get("repositories") or []
    check("RE-agent-readd — a second add does not fetch",
          again_repos and again_repos[0].get("action") == "present"
          and again_repos[0].get("setup") == "skipped"
          and not (checkout / "bound-later.txt").exists()
          and _git(checkout, "rev-parse", "HEAD", env=env).stdout.strip() == head,
          str(again_repos)[:300])

    menu_src = base / "menu-src"
    menu = _component(menu_src, "extmod", "menucomp")
    _record(menu, url, "feat/cli", "requirements.txt")
    _tool(menu, "menutool")
    menu_catalog, _s = scan_all(base / "menu-mirror", menu_src)
    menu_target = base / "menu-inst"
    menu_target.mkdir()
    menu_checkout = Path(menu_catalog["extmod/menucomp"]["path"]) / "repository"
    said = io.StringIO()
    import contextlib
    from selftest.test_interactive import _typed
    with _typed([str(menu_target), "1", "1", "", "y"]):
        with contextlib.redirect_stdout(said):
            code = interactive(menu_target, menu_catalog)
    text = said.getvalue()
    check("RE-interactive — the guided install uses the same checkout preparation",
          code == 0 and "would clone" in text and "cloned" in text
          and menu_checkout.is_dir()
          and (menu_checkout / ".venv" / ".rbtv-setup").is_file(),
          f"exit {code}; {text[:800]}")

    stamp = checkout / ".venv" / ".rbtv-setup"
    home = root / ".rbtv" / "agents" / "scout"
    import shutil
    shutil.rmtree(checkout / ".venv")
    origin = _git(checkout, "rev-parse", "origin/feat/cli", env=env).stdout.strip()
    code, out, err, exc = _run(
        cmd_update, ["update", "guidance", "--json"], home, catalog)
    check("RE-guidance — guidance does not create a checkout environment or fetch",
          code == 0 and exc is None and not (checkout / ".venv").exists()
          and not (checkout / "bound-later.txt").exists()
          and _git(checkout, "rev-parse", "origin/feat/cli", env=env).stdout.strip() == origin,
          out[:300] + err[:200])
    code, out, err, exc = _run(
        cmd_update, ["update", "scaffolding", "--json"], home, catalog)
    refreshed = json.loads(out) if code == 0 and out.startswith("{") else {}
    item = (refreshed.get("repositories") or [{}])[0]
    check("RE-scaffolding — missing packages are installed and the checkout is not pulled",
          code == 0 and exc is None and item.get("action") == "present"
          and item.get("setup") == "installed" and stamp.is_file()
          and not (checkout / "bound-later.txt").exists(),
          out[:400] + err[:200])
    shutil.rmtree(checkout / ".venv")
    code, out, err, exc = _run(cmd_update, ["update", "all", "--json"], home, catalog)
    refreshed = json.loads(out) if code == 0 and out.startswith("{") else {}
    item = (refreshed.get("repositories") or [{}])[0]
    check("RE-all — all installs missing packages and does not pull",
          code == 0 and exc is None and item.get("setup") == "installed"
          and (checkout / ".venv" / ".rbtv-setup").is_file()
          and not (checkout / "bound-later.txt").exists(),
          out[:400] + err[:200])

    foreign_src = base / "foreign-src"
    foreign = _component(foreign_src, "extmod", "foreigncomp")
    _record(foreign, url, "feat/cli", "requirements.txt")
    _tool(foreign, "foreigntool")
    foreign_catalog, _s = scan_all(base / "foreign-mirror", foreign_src)
    foreign_checkout = Path(foreign_catalog["extmod/foreigncomp"]["path"]) / "repository"
    _identity(None, "clone", "--branch", "feat/cli", url, str(foreign_checkout), env=env)
    keep = foreign_checkout / ".venv" / "keep.txt"
    keep.parent.mkdir()
    keep.write_text("owned-by-someone-else", encoding="utf-8")
    foreign_target = base / "foreign-inst"
    foreign_target.mkdir()
    code, out, err, exc = _run(
        cmd_add, ["add", "foreigntool", "--harness", "claude", "--guidance", "none"],
        foreign_target, foreign_catalog)
    check("RE-foreign-venv — a broken preexisting environment is refused and not deleted",
          (exc is not None and exc.code == "repository-setup" or "repository-setup" in (out + err))
          and keep.read_text(encoding="utf-8") == "owned-by-someone-else"
          and not (foreign_target / ".rbtv" / "config" / "install.json").exists(),
          str(exc and exc.message) + out[:200] + err[:200])

    # Turn that fixture into a working environment without removing its local file.
    import sys
    from lib.repositories import _venv_python
    made = subprocess.run([sys.executable, "-m", "venv", str(keep.parent)],
                          capture_output=True, text=True, env=env)
    assert made.returncode == 0, made.stderr
    code, out, err, exc = _run(
        cmd_add, ["add", "foreigntool", "--harness", "claude", "--guidance", "none", "--json"],
        foreign_target, foreign_catalog)
    reused = json.loads(out) if code == 0 and out.startswith("{") else {}
    check("RE-existing-venv — a healthy environment is reused without losing local contents",
          code == 0 and exc is None
          and reused.get("repositories", [{}])[0].get("setup") == "installed"
          and keep.read_text(encoding="utf-8") == "owned-by-someone-else",
          out[:400] + err[:200])
    _venv_python(keep.parent).unlink()
    code, out, err, exc = _run(
        cmd_add, ["add", "foreigntool", "--json"], foreign_target, foreign_catalog)
    check("RE-broken-stamped-venv — a setup stamp never permits deleting local contents",
          (exc is not None and exc.code == "repository-setup" or "repository-setup" in out + err)
          and keep.read_text(encoding="utf-8") == "owned-by-someone-else"
          and not _venv_python(keep.parent).exists(), out[:400] + err[:200])

    worktree_src = base / "worktree-src"
    worktree = _component(worktree_src, "extmod", "worktreecomp")
    _record(worktree, url, "preview", None)
    _tool(worktree, "worktreetool")
    worktree_catalog, _s = scan_all(base / "worktree-mirror", worktree_src)
    worktree_checkout = worktree / "repository"
    worktree_owner = base / "worktree-owner"
    _identity(None, "clone", "--branch", "feat/cli", url, str(worktree_owner), env=env)
    _identity(worktree_owner, "worktree", "add", "-b", "preview", str(worktree_checkout), env=env)
    worktree_target = base / "worktree-inst"
    worktree_target.mkdir()
    before = (_snap(worktree_owner), _snap(worktree_checkout), _snap(worktree_target))
    code, out, err, exc = _run(
        cmd_add, ["add", "worktreetool", "--harness", "claude", "--guidance", "none", "--dry-run", "--json"],
        worktree_target, worktree_catalog)
    check("RE-worktree-preview — a git worktree is accepted without writing or fetching",
          code == 0 and exc is None and (worktree_checkout / ".git").is_file()
          and before == (_snap(worktree_owner), _snap(worktree_checkout), _snap(worktree_target)),
          out[:400] + err[:200])

    clash_src = base / "clash-src"
    clash = _component(clash_src, "extmod", "clashcomp")
    _record(clash, url, "feat/cli", None)
    _tool(clash, "clashtool")
    clash_catalog, _s = scan_all(base / "clash-mirror", clash_src)
    clash_checkout = Path(clash_catalog["extmod/clashcomp"]["path"]) / "repository"
    clash_target = base / "clash-inst"
    clash_target.mkdir()
    planted = link_path(bin_dir(), "clashtool")
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text("not ours\n", encoding="utf-8")
    try:
        code, out, err, exc = _run(
            cmd_add, ["add", "clashtool", "--harness", "claude", "--guidance", "none"],
            clash_target, clash_catalog)
        check("RE-preflight — a path collision refuses before a clone",
              exc is not None and exc.code == "path-collision"
              and not clash_checkout.exists()
              and planted.read_text(encoding="utf-8") == "not ours\n",
              str(exc and (exc.code, exc.message)))
    finally:
        if planted.exists():
            planted.unlink()

    timeout_src = base / "timeout-src"
    timeout = _component(timeout_src, "extmod", "timeoutcomp")
    _record(timeout, url, "feat/cli", None)
    _tool(timeout, "timeouttool")
    timeout_catalog, _s = scan_all(base / "timeout-mirror", timeout_src)
    timeout_checkout = Path(timeout_catalog["extmod/timeoutcomp"]["path"]) / "repository"
    timeout_target = base / "timeout-inst"
    timeout_target.mkdir()
    real_run = subprocess.run

    def expire(argv, **kwargs):
        cmd = list(argv)
        if cmd and cmd[0] == "git" and "clone" in cmd:
            dest = Path(cmd[-1])
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "partial.txt").write_text("keep", encoding="utf-8")
            raise subprocess.TimeoutExpired(cmd, 120)
        return real_run(argv, **kwargs)

    with patch("lib.repositories.subprocess.run", side_effect=expire):
        code, out, err, exc = _run(
            cmd_add, ["add", "timeouttool", "--harness", "claude", "--guidance", "none"],
            timeout_target, timeout_catalog)
    said = (out + err) + str(exc and exc.message)
    check("RE-timeout — a clone timeout is a refusal and the partial checkout stays",
          "Traceback" not in said and "timed out after" in said and "120s" in said
          and (timeout_checkout / "partial.txt").read_text(encoding="utf-8") == "keep"
          and not (timeout_target / ".rbtv" / "config" / "install.json").exists()
          and "Nothing was changed" not in said,
          said[:500])

    dash_src = base / "dash-src"
    dash = _component(dash_src, "extmod", "dashcomp")
    _record(dash, url, "feat/cli", None)
    _tool(dash, "dashtool")
    dash_catalog, _s = scan_all(base / "dash-mirror", dash_src)
    dash_catalog["extmod/dashcomp"]["repository"]["url"] = "--upload-pack=touch"
    dash_target = base / "dash-inst"
    dash_target.mkdir()
    called = []

    def record_git(argv, **kwargs):
        called.append(list(argv))
        return real_run(argv, **kwargs)

    with patch("lib.repositories.subprocess.run", side_effect=record_git):
        code, out, err, exc = _run(
            cmd_add, ["add", "dashtool", "--harness", "claude", "--guidance", "none"],
            dash_target, dash_catalog)
    check("RE-dash-url — a dash-prefixed url is refused before git runs",
          exc is not None and exc.code == "repository-url"
          and not any("clone" in cmd for cmd in called)
          and not (Path(dash_catalog["extmod/dashcomp"]["path"]) / "repository").exists(),
          str(exc and exc.message) + str(called)[:200])
