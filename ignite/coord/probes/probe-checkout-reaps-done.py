#!/usr/bin/env python3
"""probe-checkout-reaps-done.py — a process must not outlive its own `done` (or incomplete) row.

G-leader-0823-0217-2 / task 131: checkout recorded `done` and only armed `arm_pid_reaper` for
`ephemeral: yes`. Persistent seats leaked for days. death-stamp confirm-and-reap only runs after
an observed death, so a living process never reached it.

This probe:
  * locates `process.arm_pid_reaper` in `cmd_checkout` BEFORE the ephemeral pane-kill branch
  * drives a real stub harness through a persistent done checkout and an incomplete checkout
    and shows the process gone (pid+starttime)
  * locates the crash arm on death-stamp (`confirmAndReap` after a `failed` stamp)
  * RED: a scratch mutant that deletes the checkout reaper call leaves the process alive
"""

import os as _os, sys as _sys, pathlib as _pl
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "coord" / "self_isolate.py").is_file()) / "coord"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import argparse
import importlib.util
import os
import shutil
import subprocess as real_subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD = KIT / "coord.py"
CHECKOUT = KIT / "checkout.py"
DEATH = KIT.parent / "supervisor" / "death-stamp.js"
RESULTS = []
PROCS = []


def check(claim, ok, detail=""):
    RESULTS.append((claim, bool(ok)))
    print(f"{'ok  ' if ok else 'FAIL'}  {claim}" + (f" — {detail}" if detail else ""))


class _NoTmux:
    class _R:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(self, *_a, **_k):
        return self._R()

    def Popen(self, argv, *a, **k):  # noqa: N802
        if isinstance(argv, (list, tuple)) and argv and os.path.basename(str(argv[0])) == "tmux":
            return real_subprocess.Popen(["true"], *a, **k)
        return real_subprocess.Popen(argv, *a, **k)

    def __getattr__(self, name):
        return getattr(real_subprocess, name)


def load_coord(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    mod.subprocess = _NoTmux()
    return mod


def make_package(root, seats):
    pkg = Path(root)
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    for seat, outputs in seats.items():
        d = pkg / "workers" / seat
        d.mkdir(parents=True, exist_ok=True)
        decl = ("\n<io-spec>\n## Outputs\n"
                + " ".join(f"`{t.strip()}`" for t in outputs.split(",") if t.strip())
                + "\n</io-spec>\n") if outputs else ""
        (d / "agent.md").write_text(
            f"---\nagent: {seat}\ncwd: {d}\n---\n\n# {seat}\nbrief\n{decl}", encoding="utf-8")
    return pkg


def ns(mod, pkg, **kw):
    d = {"package": str(pkg), "base": None, "workers_dir": None, "as_agent": None, "force": False}
    d.update(kw)
    return argparse.Namespace(**d)


def checkin(mod, pkg, seat, pane):
    mod.harness_outcome(mod.cmd_checkin,
                        ns(mod, pkg, agent=seat, summary="probe pass", pane=pane, force=False))
    seat_dir = Path(pkg) / "workers" / seat
    mod.session_open(ns(mod, pkg),
                     {"agent": seat, "harness": "probe", "model": "opus",
                      "cwd": str(seat_dir)},
                     since=time.time(), wait=0.0)


def checkout(mod, pkg, seat, **kw):
    d = {"agent": seat, "no_export": True, "renew": False, "handoff": None,
         "handoff_file": None, "incomplete": None, "pane": None}
    d.update(kw)
    out, err, code = mod.harness_outcome(mod.cmd_checkout, ns(mod, pkg, **d))
    return out + err, (0 if code is None else code)


def stub_harness(workdir, tag):
    stub = Path(workdir) / f"claude-{tag}" / "claude"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(3600)\n")
    stub.chmod(0o755)
    proc = real_subprocess.Popen([str(stub)], stdout=real_subprocess.DEVNULL,
                                 stderr=real_subprocess.DEVNULL)
    PROCS.append(proc)
    for _ in range(100):
        ident = None
        try:
            from pathlib import Path as P
            raw = P(f"/proc/{proc.pid}/cmdline").read_bytes()
        except OSError:
            raw = b""
        if raw:
            # process_identity lives on the live kit; resolve after load
            ident = proc.pid
            if ident:
                return proc, ident
        time.sleep(0.05)
    return proc, None


def ident_of(mod, pid):
    return mod.process.process_identity(pid)


def gone(mod, ident, wait_s=8.0):
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if not mod.process.ident_is_live_process(ident):
            return True
        time.sleep(0.1)
    return not mod.process.ident_is_live_process(ident)


def wire_idents(mod, ident):
    mod.process.pane_harness_idents = lambda pane: [ident] if pane else []
    mod.tmux_kill_pane = lambda pane: (True, "")


def locate_reaper_before_ephemeral(src):
    reaper = src.find("process.arm_pid_reaper(_idents_e)")
    eph = src.find('if _seat_e is not None and _seat_e.get("ephemeral")')
    return reaper >= 0 and eph >= 0 and reaper < eph


def build_mutant(dest_dir):
    src = CHECKOUT.read_text(encoding="utf-8")
    old = "                process.arm_pid_reaper(_idents_e)\n"
    if old not in src:
        return None, "mutation seam NOT FOUND"
    src = src.replace(old, "                pass  # RED: checkout does not reap\n", 1)
    dest = Path(dest_dir)
    for sib in KIT.glob("*.py"):
        shutil.copyfile(sib, dest / sib.name)
    sup_src = KIT.parent / "supervisor"
    sup_dest = dest.parent / "supervisor"
    sup_dest.mkdir(parents=True, exist_ok=True)
    for sup in sup_src.glob("*.py"):
        shutil.copyfile(sup, sup_dest / sup.name)
    (dest / CHECKOUT.name).write_text(src, encoding="utf-8")
    return dest / "coord.py", ""


def main():
    for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
        os.environ.pop(_v, None)
    tmp = Path(tempfile.mkdtemp(prefix="probe-checkout-reaps-"))
    _rec = tmp / ".rbtv" / "modules" / "ignite" / "server.json"
    _rec.parent.mkdir(parents=True, exist_ok=True)
    _rec.write_text('{"machines": {}}\n', encoding="utf-8")
    try:
        src = CHECKOUT.read_text(encoding="utf-8")
        check("locator: cmd_checkout arms arm_pid_reaper BEFORE the ephemeral pane-kill branch",
              locate_reaper_before_ephemeral(src))
        death = DEATH.read_text(encoding="utf-8")
        fail_idx = death.find("if (declared === 'failed')")
        reap_after = death.find("confirmAndReap(evidence, reapOpts)", fail_idx if fail_idx >= 0 else 0)
        check("crash arm: stampDeath confirmAndReaps a failed (no-checkout) death, not only done",
              fail_idx >= 0 and reap_after > fail_idx)

        mod = load_coord(COORD, "coord_reaps_subject")
        proc, pid = stub_harness(tmp / "stubs", "done")
        ident = ident_of(mod, pid)
        check("stub harness is a live (pid, starttime) pair",
              bool(ident) and mod.process.ident_is_live_process(ident),
              f"pid={pid} ident={ident}")
        wire_idents(mod, ident)
        pkg = make_package(tmp / "live", {"worker": "./deliverable.md"})
        (pkg / "workers" / "worker" / "deliverable.md").write_text("the work\n", encoding="utf-8")
        checkin(mod, pkg, "worker", "%1")
        print(f"ps before done checkout: pid {pid} ident={ident} "
              f"alive={mod.process.ident_is_live_process(ident)}")
        out, code = checkout(mod, pkg, "worker")
        check("done checkout succeeded and armed the reaper",
              code == 0 and "arming the exit reaper" in out
              and "killing own pane" not in out)
        check("done checkout: process gone (pid+starttime)",
              gone(mod, ident),
              f"pid {pid}")
        print(f"ps after done checkout: pid {pid} alive={mod.process.ident_is_live_process(ident)}")

        proc2, pid2 = stub_harness(tmp / "stubs", "inc")
        ident2 = ident_of(mod, pid2)
        wire_idents(mod, ident2)
        pkg2 = make_package(tmp / "inc", {"worker": "./deliverable.md"})
        checkin(mod, pkg2, "worker", "%2")
        print(f"ps before incomplete checkout: pid {pid2} alive={mod.process.ident_is_live_process(ident2)}")
        out_i, code_i = checkout(mod, pkg2, "worker",
                                 incomplete="failure-arm fixture — the work did not finish")
        check("incomplete checkout armed the same reaper",
              code_i == 0 and "arming the exit reaper" in out_i)
        check("incomplete checkout: process gone — failure arm does not leak",
              gone(mod, ident2), f"pid {pid2}")
        print(f"ps after incomplete checkout: pid {pid2} alive={mod.process.ident_is_live_process(ident2)}")

        mdir = tmp / "mutant-kit"
        mdir.mkdir()
        mpath, merr = build_mutant(mdir)
        if mpath is None:
            check(f"RED setup: mutant built — {merr}", False)
        else:
            mut = load_coord(mpath, "coord_reaps_mutant")
            proc3, pid3 = stub_harness(tmp / "stubs", "red")
            ident3 = ident_of(mut, pid3)
            wire_idents(mut, ident3)
            mpkg = make_package(tmp / "mutant-run", {"worker": "./deliverable.md"})
            (mpkg / "workers" / "worker" / "deliverable.md").write_text("the work\n", encoding="utf-8")
            checkin(mut, mpkg, "worker", "%3")
            checkout(mut, mpkg, "worker")
            time.sleep(6.0)
            still = mut.process.ident_is_live_process(ident3)
            check("RED: reverting the checkout reaper call leaves the process ALIVE after 6s",
                  still, f"pid {pid3} alive={still}")
            if still:
                try:
                    os.kill(pid3, 9)
                except OSError:
                    pass
    finally:
        for p in PROCS:
            if p.poll() is None:
                try:
                    p.kill()
                except OSError:
                    pass
                p.wait(timeout=2)
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [c for c, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} green")
    if failed:
        print("FAILED:")
        for c in failed:
            print(f"  - {c}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
