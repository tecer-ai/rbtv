#!/usr/bin/env python3
"""probe-checkout-disposition.py — checkout writes the ending store (spec §4.1 / §2.7)."""

import os as _os, sys as _sys, pathlib as _pl
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "coord" / "self_isolate.py").is_file()) / "coord"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import argparse
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD = KIT / "coord.py"
RESULTS = []


def check(claim, ok):
    RESULTS.append((claim, bool(ok)))
    print(f"{'ok  ' if ok else 'FAIL'}  {claim}")


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
                     since=__import__("time").time(), wait=0.0)


def checkout(mod, pkg, seat, **kw):
    d = {"agent": seat, "no_export": True, "renew": False, "handoff": None,
         "handoff_file": None, "incomplete": None, "pane": None}
    d.update(kw)
    out, err, code = mod.harness_outcome(mod.cmd_checkout, ns(mod, pkg, **d))
    return out + err, (0 if code is None else code)


def ending_of(mod, pkg, seat):
    try:
        return mod.ending_store.get_current_ending(pkg, seat)
    except Exception:
        return None


def session_ended(mod, pkg, seat):
    p = Path(pkg) / "sessions.csv"
    if not p.exists():
        return False
    header, rows = mod.read_csv_table(p, mod.SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    for r in rows:
        mod.pad_row(r, header)
        if r[idx["seat"]].strip() == seat and r[idx["ended"]].strip():
            return True
    return False


def active(mod, pkg, seat):
    _, _, rows = mod.load_workers(mod.base_dir(ns(mod, pkg)))
    row = mod.current_row(rows, seat)
    return bool(row) and row["active"] == "yes"


def build_mutant(dest_dir):
    subject = KIT / "checkout.py"
    src = subject.read_text(encoding="utf-8")
    seams = [
        ("    if not renew and not incomplete:\n        _declared, _missing",
         "    if False:\n        _declared, _missing"),
        ('checkout_disposition = ("renew" if renew else "unverified" if outputs_unverified\n'
         '                            else "incomplete" if incomplete else "done")',
         'checkout_disposition = "renew" if renew else "done"'),
    ]
    for old, new in seams:
        if old not in src:
            return None, f"mutation seam NOT FOUND, mutant not built: {old[:60]!r}"
        src = src.replace(old, new, 1)
    dest = Path(dest_dir) / "coord.py"
    for sib in KIT.glob("*.py"):
        shutil.copyfile(sib, Path(dest_dir) / sib.name)
    # ⚠ THE PRODUCT SPANS TWO COMPONENT FOLDERS — STAGE BOTH. Since the 2026-08-25 split,
    # `coord.py` imports six modules from `<its parent>/../supervisor/` and reads every product
    # file to build `PRODUCT_SOURCE`, so a mutant kit staged FLAT dies at load with
    # FileNotFoundError on `supervisor/process.py` and the A3 arm never runs. The sibling folder
    # is copied WHOLE, off disk, so a seventh module arriving there needs no edit here.
    sup_src = KIT.parent / "supervisor"
    sup_dest = Path(dest_dir).parent / "supervisor"
    sup_dest.mkdir(parents=True, exist_ok=True)
    for sup in sup_src.glob("*.py"):
        shutil.copyfile(sup, sup_dest / sup.name)
    (Path(dest_dir) / subject.name).write_text(src, encoding="utf-8")
    return dest, ""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="probe-7676-"))
    # THE FIXTURE ROOT IS A WORKSPACE, and it says so with the INSTALL RECORD — D27's
    # definition (`ignite-cli/lib/config.js#findInstallRoot`), never a bare `.rbtv/`.
    # `ending_store` resolves the store by that record and REFUSES above a folder that roots no
    # install, rather than minting a `.rbtv/` at the start dir — the fallback that planted the
    # stray `<repo>/.rbtv/runtime/ignite/heart.db` of 2026-08-28 [5815fbaa].
    _rec = tmp / ".rbtv" / "modules" / "ignite" / "server.json"
    _rec.parent.mkdir(parents=True, exist_ok=True)
    _rec.write_text('{"machines": {}}\n', encoding="utf-8")
    try:
        mod = load_coord(COORD, "coord_subject")
        pkg = make_package(tmp / "live", {"produced": "./deliverable.md", "barren": "./deliverable.md"})
        (pkg / "workers" / "produced" / "deliverable.md").write_text("the work\n", encoding="utf-8")

        checkin(mod, pkg, "produced", "%1")
        out_p, code_p = checkout(mod, pkg, "produced")
        rec_p = ending_of(mod, pkg, "produced")
        check("A1: declared output present stamps ending=done who_stamped=seat",
              code_p == 0 and rec_p is not None and rec_p.get("ending") == "done"
              and rec_p.get("who_stamped") == "seat")
        check("A1: sessions.csv row is ended (bookkeeping only)",
              session_ended(mod, pkg, "produced"))

        checkin(mod, pkg, "barren", "%2")
        out_b, code_b = checkout(mod, pkg, "barren")
        rec_b = ending_of(mod, pkg, "barren")
        check("A1: missing declared output stamps failed/outputs-missing, not done",
              rec_b is not None and rec_b.get("ending") == "failed"
              and rec_b.get("reason_class") == "outputs-missing"
              and "MISSING" in out_b)
        check("A1: missing-output path still closes the sitting",
              session_ended(mod, pkg, "barren") and not active(mod, pkg, "barren"))

        pkg2 = make_package(tmp / "inc", {"barren": "./deliverable.md"})
        checkin(mod, pkg2, "barren", "%3")
        out_i, code_i = checkout(mod, pkg2, "barren",
                                 incomplete="the spec I was to review was never written")
        rec_i = ending_of(mod, pkg2, "barren")
        check("A2: --incomplete stamps ending=incomplete armed=1",
              code_i == 0 and rec_i is not None and rec_i.get("ending") == "incomplete"
              and int(rec_i.get("armed") or 0) == 1
              and rec_i.get("who_stamped") == "seat")
        check("A2: incomplete closes the roster row",
              not active(mod, pkg2, "barren"))

        mdir = tmp / "mutant"
        mdir.mkdir()
        mpath, merr = build_mutant(mdir)
        if mpath is None:
            check(f"A3: the mutant could not be built — {merr}", False)
        else:
            mut = load_coord(mpath, "coord_mutant")
            mpkg = make_package(tmp / "mutant-run", {"barren": "./deliverable.md"})
            checkin(mut, mpkg, "barren", "%4")
            _out_m, _code_m = checkout(mut, mpkg, "barren")
            rec_m = ending_of(mut, mpkg, "barren")
            check("A3: mutant without the outputs gate stamps done on a barren seat",
                  rec_m is not None and rec_m.get("ending") == "done")

        check("A5: seat may not stamp failed — stamp_seat_declare refuses it",
              True)
        try:
            ending_store = mod.ending_store
            pkg3 = make_package(tmp / "refuse", {"x": "./a.md"})
            ending_store.stamp_seat_declare(pkg3, "x", "failed")
            check("A5: seat failed stamp was refused", False)
        except Exception:
            check("A5: seat failed stamp was refused", True)

        for shape, decl in (("one-line", "outputs: plan.md"),
                            ("block-YAML", "outputs:\n  - plan.md")):
            mp = make_package(tmp / f"retired-{shape}", {})
            d = mp / "workers" / "author"
            d.mkdir(parents=True, exist_ok=True)
            (d / "agent.md").write_text(
                f"---\nagent: author\n{decl}\ncwd: {d}\n---\n\n# author\nbrief\n",
                encoding="utf-8")
            (d / "plan.md").write_text("delivered\n", encoding="utf-8")
            checkin(mod, mp, "author", "%9")
            out_x, code_x = checkout(mod, mp, "author")
            check(f"A6({shape}): retired outputs: frontmatter key is refused",
                  code_x != 0 and "RETIRED" in out_x and "## Outputs" in out_x
                  and ending_of(mod, mp, "author") is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [c for c, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} green")
    if failed:
        print(f"FAILED {len(failed)}:")
        for c in failed:
            print(f"  - {c}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
