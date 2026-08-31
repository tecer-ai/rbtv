#!/usr/bin/env python3
"""probe-outputs-template.py — a <placeholder> declared output is not a file path.

Checkout used to demand the literal string (`findings-<dimension>.md`,
`deltas-<seat-id>-round-<n>.md`) and refuse finished work. This probe pins the
three consequence arms on a scratch package, plus the mutation that restores
the literal demand.
"""
import os as _os, sys as _sys, pathlib as _pl
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "coord" / "self_isolate.py").is_file()) / "coord"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import argparse
import importlib.util
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD = KIT / "coord.py"
OUT = HERE / "probe-outputs-template.out"
RESULTS = []
lines = []


def say(s):
    lines.append(s)
    print(s, flush=True)


def check(claim, ok):
    RESULTS.append((claim, bool(ok)))
    say(f"{'ok  ' if ok else 'FAIL'}  {claim}")


class _NoTmux:
    class _R:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(self, *_a, **_k):
        return self._R()

    def __getattr__(self, name):
        import subprocess as _s
        return getattr(_s, name)


def load_coord(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    mod.subprocess = _NoTmux()
    return mod


def ns(mod, pkg, **kw):
    d = {"package": str(pkg), "base": None, "workers_dir": None, "as_agent": None, "force": False}
    d.update(kw)
    return argparse.Namespace(**d)


def write_seat(pkg, seat, token):
    d = Path(pkg) / "seats" / seat
    d.mkdir(parents=True, exist_ok=True)
    (d / "seat.md").write_text(
        f"---\nagent: {seat}\nmodel: opus\n---\nbrief\n\n<io-spec>\n## Outputs\n"
        f"- Schema: the record at `{token}`.\n</io-spec>\n",
        encoding="utf-8")


def checkin(mod, pkg, seat, pane):
    seat_dir = Path(pkg) / "seats" / seat
    mod.harness_outcome(mod.cmd_checkin,
                        ns(mod, pkg, agent=seat, summary="probe", pane=pane, force=False))
    mod.session_open(ns(mod, pkg),
                     {"agent": seat, "harness": "probe", "model": "opus",
                      "cwd": str(seat_dir)},
                     since=time.time(), wait=0.0)


def checkout(mod, pkg, seat):
    out, err, code = mod.harness_outcome(
        mod.cmd_checkout,
        ns(mod, pkg, agent=seat, no_export=True, renew=False, handoff=None,
           handoff_file=None, incomplete=None, pane=None))
    rec = mod.ending_store.get_current_ending(pkg, seat) or {}
    return (out or "") + (err or ""), (0 if code is None else code), rec


def build_mutant(dest_dir):
    src = (KIT / "checkout.py").read_text(encoding="utf-8")
    old = "            if is_output_template(_d):\n                continue\n"
    new = "            if False and is_output_template(_d):\n                continue\n"
    if old not in src:
        return None, f"mutation seam NOT FOUND: {old!r}"
    src = src.replace(old, new, 1)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    for sib in KIT.glob("*.py"):
        shutil.copyfile(sib, dest / sib.name)
    sup_src = KIT.parent / "supervisor"
    sup_dest = dest.parent / "supervisor"
    sup_dest.mkdir(parents=True, exist_ok=True)
    for sup in sup_src.glob("*.py"):
        shutil.copyfile(sup, sup_dest / sup.name)
    (dest / "checkout.py").write_text(src, encoding="utf-8")
    return dest / "coord.py", ""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="probe-outputs-template-"))
    _rec = tmp / ".rbtv" / "modules" / "ignite" / "server.json"
    _rec.parent.mkdir(parents=True, exist_ok=True)
    _rec.write_text('{"machines": {}}\n', encoding="utf-8")
    try:
        mod = load_coord(COORD, "coord_tmpl")
        pkg = tmp / "live"
        (pkg / "coordination").mkdir(parents=True, exist_ok=True)
        dims = ("edges", "resources", "permissions", "scope", "clarity", "consistency")
        write_seat(pkg, "tmplhit", "planning/current/findings-<dimension>.md")
        write_seat(pkg, "tmplmiss", "planning/current/deltas-<seat-id>-round-<n>.md")
        write_seat(pkg, "tmpldelta", "planning/current/deltas-<seat-id>-round-<n>.md")
        cur = pkg / "planning" / "current"
        cur.mkdir(parents=True, exist_ok=True)
        for d in dims:
            (cur / f"findings-{d}.md").write_text(f"{d}\n", encoding="utf-8")
        (cur / "deltas-tmpldelta-round-1.md").write_text("delta\n", encoding="utf-8")
        literal = cur / "findings-<dimension>.md"
        check("no literal findings-<dimension>.md on disk", not literal.exists())

        checkin(mod, pkg, "tmplhit", "%1")
        out_h, code_h, rec_h = checkout(mod, pkg, "tmplhit")
        check("placeholder + six real findings-* files checkouts done, no literal file",
              code_h == 0 and rec_h.get("ending") == "done"
              and rec_h.get("who_stamped") == "seat"
              and "MISSING" not in out_h
              and not literal.exists())

        checkin(mod, pkg, "tmplmiss", "%2")
        out_m, code_m, rec_m = checkout(mod, pkg, "tmplmiss")
        check("conditional deltas template with no matching file is not refused",
              code_m == 0 and rec_m.get("ending") == "done" and "MISSING" not in out_m)

        checkin(mod, pkg, "tmpldelta", "%3")
        out_d, code_d, rec_d = checkout(mod, pkg, "tmpldelta")
        check("route-back that instantiated deltas-*-round-1.md checkouts done",
              code_d == 0 and rec_d.get("ending") == "done" and "MISSING" not in out_d)

        mdir = tmp / "mutant" / "coord"
        mpath, err = build_mutant(mdir)
        if mpath is None:
            check(f"mutation seam found: {err}", False)
        else:
            mut = load_coord(mpath, "coord_tmpl_mut")
            mpkg = tmp / "mutant-run"
            (mpkg / "coordination").mkdir(parents=True, exist_ok=True)
            write_seat(mpkg, "tmplhit", "planning/current/findings-<dimension>.md")
            mcur = mpkg / "planning" / "current"
            mcur.mkdir(parents=True, exist_ok=True)
            for d in dims:
                (mcur / f"findings-{d}.md").write_text(f"{d}\n", encoding="utf-8")
            checkin(mut, mpkg, "tmplhit", "%4")
            _out_x, _code_x, rec_x = checkout(mut, mpkg, "tmplhit")
            check("RED: revert the template skip and the six real files are refused",
                  rec_x.get("ending") == "failed"
                  and rec_x.get("reason_class") == "outputs-missing"
                  and "MISSING" in _out_x)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [c for c, ok in RESULTS if not ok]
    say("")
    say(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} green" if not failed
        else f"RESULT: FAIL — {len(failed)}: {'; '.join(failed)}")
    if not failed:
        say("RESULT: PASS — placeholder declared outputs are not demanded as literal paths")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
