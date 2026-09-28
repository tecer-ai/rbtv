"""The `~/.rbtv/bin` shortcuts and the shell PATH line."""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from discovery import EXPOSURE_NAME, Refuse, scan_all

from lib.constants import (
    PATH_BOOTSTRAP,
    PATH_FENCE_END,
    PATH_FENCE_START,
    STATE_REL,
    WS_PREFIX,
    _RUNTIME,
)
from lib.pathlinks import (bin_dir, gate_path_links, link_path,
                           link_points_at, unlink_one)
from lib import pathlinks
from lib.state import read_state
from lib.operations import do_install, do_uninstall


def path_links(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nL — PATH links (part-id name, book-aware, rebound bindir)")

    def _lsnap(root: Path) -> set[str]:
        if not root.exists():
            return set()
        return {p.relative_to(root).as_posix()
                for p in root.rglob("*")
                if p.is_file() or p.is_symlink()}

    def _lcomp(root: Path, mod: str, name: str, pid: str, entry: str,
               body: str = "print(1)\n") -> dict[str, dict]:
        cdir = root / mod / name
        cdir.mkdir(parents=True)
        dest = cdir / Path(entry)
        if not str(entry).startswith(WS_PREFIX):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("#!/usr/bin/env python3\n" + body,
                            encoding="utf-8")
            dest.chmod(0o755)
        (cdir / EXPOSURE_NAME).write_text(
            "part-id,part-kind,method,rbtv-cli,entry-point,description,"
            "write-roots\n"
            f"{pid},tool,path,,{entry},,\n", encoding="utf-8")
        cat, _ = scan_all(tmp / "no-mirror-l", root)
        return cat

    lsrc = tmp / "lsrc"
    lws = tmp / "ws-path-add"
    lws.mkdir()
    lcat = _lcomp(lsrc, "lmod", "ladd", "ladd-bin", "impl.py")

    badsrc = tmp / "bad-path-src"
    badws = tmp / "bad-path-ws"
    badws.mkdir()
    badcat = _lcomp(badsrc, "badmod", "badcomp", "badbin", "bad.py")
    badtool = badsrc / "badmod/badcomp/bad.py"
    for kind, body, mode in (("no-shebang", "print(1)\n", 0o755),
                             ("no-execute", "#!/usr/bin/env python3\n", 0o644)):
        badtool.write_text(body, encoding="utf-8")
        badtool.chmod(mode)
        before = (set(badws.iterdir()), set(bin_dir().iterdir()))
        try:
            do_install(badws, badcat, ["badmod/badcomp"], ["claude"],
                       dry_run=True)
            code = "no refusal"
        except Refuse as exc:
            code = exc.code
        check(f"L-{kind} — invalid PATH target refuses during planning",
              (code == "path-not-runnable" if os.name != "nt" else
               code == "no refusal")
              and before == (set(badws.iterdir()), set(bin_dir().iterdir())),
              code)
    badtool.write_text("# reference\n", encoding="utf-8")
    badtool.rename(badtool.with_suffix(".md"))
    (badsrc / "badmod/badcomp" / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "badbin,tool,path,,bad.md,,\n", encoding="utf-8")
    badcat, _ = scan_all(tmp / "no-mirror-l", badsrc)
    try:
        do_install(badws, badcat, ["badmod/badcomp"], ["claude"],
                   dry_run=True)
        code = "no refusal"
    except Refuse as exc:
        code = exc.code
    check("L-markdown — data file refuses on every platform",
          code in ("path-not-runnable", "path-link-failed")
          and not (badws / STATE_REL).exists(), code)

    lr = do_install(lws, lcat, ["lmod/ladd"], ["claude"], dry_run=False)
    check("L-add — link on add, name is the part-id not the basename",
          link_points_at(link_path(bin_dir(), "ladd-bin"),
                         (lsrc / "lmod/ladd/impl.py").resolve())
          and not link_path(bin_dir(), "impl.py").exists()
          and not (lws / "ladd-bin").exists()
          and read_state(lws)["components"]["lmod/ladd"]["path_links"]
          == ["ladd-bin"]
          and "ladd-bin" in (lr["report"].get("path") or {}).get(
              "linked", []),
          str(lr["report"].get("path")))
    twin = link_path(bin_dir(), "ladd-bin").with_suffix("")
    check("L-bash-twin — on Windows an extensionless LF sh launcher sits "
          "beside the .cmd (git bash never resolves <name>.cmd)",
          os.name != "nt" or (twin.is_file()
                              and b"\r" not in twin.read_bytes()
                              and twin.read_bytes().startswith(b"#!/bin/sh")))
    rc = Path(_RUNTIME["rc"])
    first = rc.read_text(encoding="utf-8")
    check("L-auto-path — install writes one marked PATH block",
          first.count(PATH_FENCE_START) == 1
          and PATH_BOOTSTRAP in first)
    do_install(lws, lcat, ["lmod/ladd"], ["claude"], dry_run=False)
    check("L-auto-path-idempotent — reinstall keeps the block unchanged",
          rc.read_text(encoding="utf-8") == first)

    do_uninstall(lws, lcat, ["lmod/ladd"], dry_run=False)
    check("L-auto-path-survives-rm — last uninstall leaves user PATH",
          rc.read_text(encoding="utf-8") == first)
    check("L-rm — unlink on rm; directory kept if anything else remains",
          not link_path(bin_dir(), "ladd-bin").exists()
          and not twin.exists()
          and bin_dir().is_dir(),
          str(list(bin_dir().iterdir()) if bin_dir().is_dir() else None))

    cws = tmp / "ws-path-coll"
    cws.mkdir()
    csrc = tmp / "csrc"
    ccat = _lcomp(csrc, "cmod", "ccoll", "hitfile", "x.py")
    bin_dir().mkdir(parents=True, exist_ok=True)
    link_path(bin_dir(), "hitfile").write_text("not a symlink\n", encoding="utf-8")
    snap_c, snap_b = _lsnap(cws), _lsnap(bin_dir())
    try:
        do_install(cws, ccat, ["cmod/ccoll"], ["claude"], dry_run=False)
        check("L-collision — path-collision on a regular file", False,
              "no refusal")
    except Refuse as exc:
        check("L-collision — path-collision on a regular file",
              exc.code == "path-collision"
              and _lsnap(cws) == snap_c
              and _lsnap(bin_dir()) == snap_b
              and not (cws / STATE_REL).exists()
              and link_path(bin_dir(), "hitfile").is_file()
              and not link_path(bin_dir(), "hitfile").is_symlink(),
              exc.code)
    link_path(bin_dir(), "hitfile").unlink()

    stranger = bin_dir() / "unbooked-stranger"
    (tmp / "stranger-tgt").write_text("x\n", encoding="utf-8")
    stranger.symlink_to(tmp / "stranger-tgt")
    uws = tmp / "ws-path-unbooked"
    uws.mkdir()
    do_install(uws, lcat, ["lmod/ladd"], ["claude"], dry_run=False)
    check("L-unbooked — an unbooked symlink is left untouched",
          stranger.is_symlink()
          and stranger.resolve() == (tmp / "stranger-tgt").resolve()
          and "unbooked-stranger" not in
          (read_state(uws)["components"]["lmod/ladd"].get("path_links")
           or []))
    do_uninstall(uws, lcat, ["lmod/ladd"], dry_run=False)
    check("L-unbooked-survives-rm — still there after we unlink ours",
          stranger.is_symlink() and bin_dir().is_dir())

    # unlink_one must REFUSE a non-symlink sitting at a booked name rather
    # than delete it. Without this arm, neutering that refusal left the suite
    # green: L-collision covers the PRE-WRITE gate on add, and nothing covered
    # the REMOVE path — the destructive one, where a user's real file has
    # replaced a link we once booked.
    usurper = link_path(bin_dir(), "usurper")
    bin_dir().mkdir(parents=True, exist_ok=True)
    usurper.write_text("a real file, not ours\n", encoding="utf-8")
    try:
        unlink_one(bin_dir(), "usurper", dry=False)
        ucode = "no refusal"
    except Refuse as exc:
        ucode = exc.code
    check("L-unlink-refuses-regular-file — a booked name now holding a real "
          "file is never deleted",
          ucode == "path-collision"
          and usurper.is_file()
          and not usurper.is_symlink()
          and usurper.read_text(encoding="utf-8") == "a real file, not ours\n",
          f"code={ucode} exists={usurper.exists()}")
    usurper.unlink()

    bindir = bin_dir()
    bindir.mkdir(parents=True, exist_ok=True)
    victim = link_path(bindir, "gate-drop")
    victim.write_text("real file\n", encoding="utf-8")
    try:
        gate_path_links(bindir, {}, {"gate-drop"})
        check("L-gate-drop-refuses-regular", False, "no refusal")
    except Refuse as exc:
        check("L-gate-drop-refuses-regular",
              exc.code == "path-collision" and victim.is_file()
              and victim.read_text(encoding="utf-8") == "real file\n", exc.code)
    victim.unlink()

    n1 = tmp / "n1src"
    n2 = tmp / "n2src"
    nws = tmp / "ws-path-twoname"
    nws.mkdir()
    cat1 = _lcomp(n1, "amod", "acomp", "samename", "a.py", "A\n")
    cat2 = _lcomp(n2, "bmod", "bcomp", "samename", "b.py", "B\n")
    both = {**cat1, **cat2}
    snap_n, snap_nb = _lsnap(nws), _lsnap(bin_dir())
    try:
        do_install(nws, both, ["amod/acomp", "bmod/bcomp"], ["claude"],
                   dry_run=False)
        check("L-name-collision — two components, one name", False,
              "no refusal")
    except Refuse as exc:
        check("L-name-collision — two components, one name",
              exc.code == "path-name-collision"
              and _lsnap(nws) == snap_n
              and _lsnap(bin_dir()) == snap_nb
              and not (nws / STATE_REL).exists(),
              exc.code)

    wsrc = tmp / "wsrc"
    wws = tmp / "ws-path-ws"
    wws.mkdir()
    (wws / "tools").mkdir()
    (wws / "tools" / "from-ws.py").write_text(
        "#!/usr/bin/env python3\nprint('ws')\n", encoding="utf-8")
    (wws / "tools" / "from-ws.py").chmod(0o755)
    wcat = _lcomp(wsrc, "wmod", "wcomp", "wsbin", "ws:tools/from-ws.py")
    wr = do_install(wws, wcat, ["wmod/wcomp"], ["claude"], dry_run=False)
    check("L-ws — ws: entry-point resolves workspace-root-relative",
          link_points_at(link_path(bin_dir(), "wsbin"),
                         (wws / "tools/from-ws.py").resolve())
          and not (wsrc / "wmod/wcomp" / "ws:tools").exists(),
          str(wr["report"].get("path")))
    do_uninstall(wws, wcat, ["wmod/wcomp"], dry_run=False)

    esrc = tmp / "esrc"
    ews = tmp / "ws-path-esc"
    ews.mkdir()
    ecat = _lcomp(esrc, "emod", "ecomp", "escbin", "ws:../secret.py")
    (tmp / "secret.py").write_text("nope\n", encoding="utf-8")
    snap_e = _lsnap(ews)
    try:
        do_install(ews, ecat, ["emod/ecomp"], ["claude"], dry_run=False)
        check("L-escape — .. refuse", False, "no refusal")
    except Refuse as exc:
        check("L-escape — .. refuse",
              exc.code == "entry-point-escape"
              and _lsnap(ews) == snap_e
              and not (ews / STATE_REL).exists()
              and not (bin_dir() / "escbin").exists(),
              exc.code)

    fws = tmp / "ws-path-flag"
    fws.mkdir()
    do_install(fws, lcat, ["lmod/ladd"], ["claude"], dry_run=False)
    rc_txt = Path(_RUNTIME["rc"]).read_text(encoding="utf-8") \
        if Path(_RUNTIME["rc"]).is_file() else ""
    check("L-profile — add writes a fenced bootstrap block",
          PATH_FENCE_START in rc_txt and PATH_BOOTSTRAP in rc_txt
          and PATH_FENCE_END in rc_txt
          and rc_txt.index(PATH_BOOTSTRAP)
          > rc_txt.index(PATH_FENCE_START))
    do_uninstall(fws, lcat, ["lmod/ladd"], dry_run=False)
    rc_after = Path(_RUNTIME["rc"]).read_text(encoding="utf-8") \
        if Path(_RUNTIME["rc"]).is_file() else ""
    check("L-profile-survives-rm — full rm keeps the fenced block",
          PATH_FENCE_START in rc_after
          and PATH_BOOTSTRAP in rc_after)

    key = MagicMock()
    key.__enter__.return_value = key
    values = {"Path": (r"C:\Windows", 1)}
    fake_reg = SimpleNamespace(
        HKEY_CURRENT_USER=1, KEY_READ=2, KEY_WRITE=4, REG_EXPAND_SZ=2,
        CreateKeyEx=lambda *args: key,
        QueryValueEx=lambda unused, name: values[name],
        SetValueEx=lambda unused, name, zero, kind, value:
            values.__setitem__(name, (value, kind)))
    notice = MagicMock()
    with patch.dict(sys.modules, {"winreg": fake_reg}), patch.object(
            pathlinks, "bin_dir", return_value=Path(r"C:\Users\test\.rbtv\bin")), \
            patch("ctypes.windll", create=True) as windll:
        windll.user32.SendMessageTimeoutW = notice
        pathlinks._write_windows_user_path()
        pathlinks._write_windows_user_path()
    check("L-windows-user-path — registry PATH is written once and notified",
          values["Path"][0].count(r"C:\Users\test\.rbtv\bin") == 1
          and notice.call_count == 1)
    ctx.keep(locals())
