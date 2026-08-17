#!/usr/bin/env python3
"""probe-disposition-grants.py — F3: leader mints a disposition grant; daemon drain applies it.

ARMS
  A1  caged `--go` mints the grant and does not traceback (goal dir RO, coordination/ RW)
  A2  drain applies the durable cell (writer stays `leader`) and spends the grant
  A3  after-edges see `done` only after apply, not off the unspent grant file
  A4  a second `--go` for the same (seat, session-id) refuses as already-granted

Run through the enumerator: `node deploy/probe-suite.js --only disposition-grants`.
"""

import os as _os, sys as _sys, pathlib as _pl
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "team-kit" / "self_isolate.py").is_file()) / "team-kit"))
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
OUT = HERE / "probe-disposition-grants.out"

lines, failures = [], []


def check(tag, ok, detail=""):
    lines.append(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def load_coord(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def ns(pkg, **kw):
    d = {"package": str(pkg), "base": None, "workers_dir": None,
         "as_agent": "leader", "force": False, "go": True,
         "seat": "pred", "disposition": "done", "anchor": "p-f3-probe"}
    d.update(kw)
    return argparse.Namespace(**d)


def seed_ended(mod, pkg, seat, disposition="exited"):
    path = mod.sessions_csv(pkg)
    header, rows = mod.read_csv_table(path, mod.SESSIONS_COLS)
    header, widened = mod.widen_header(header, mod.SESSIONS_COLS)
    if widened:
        rows = [mod.pad_row(r, header) for r in rows]
    idx = {c: i for i, c in enumerate(header)}
    new = ["" for _ in header]
    new[idx["session-id"]] = f"{seat}-sid"
    new[idx["seat"]] = seat
    new[idx["started"]] = mod.now()
    new[idx["ended"]] = mod.now()
    new[idx["disposition"]] = disposition
    rows.append(new)
    mod.write_csv_table(path, header, rows)


def session_cell(mod, pkg, seat):
    row = None
    header, rows = mod.read_csv_table(mod.sessions_csv(pkg), mod.SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    for r in rows:
        mod.pad_row(r, header)
        if r[idx["seat"]].strip() == seat:
            row = r
    if row is None:
        return {}
    return {c: row[idx[c]] for c in header}


def main():
    tmp = Path(tempfile.mkdtemp(prefix="probe-f3-disp-"))
    try:
        mod = load_coord(COORD, "coord_f3_disp")
        pkg = tmp / "pkg"
        (pkg / "coordination").mkdir(parents=True)
        seed_ended(mod, pkg, "pred", "exited")

        # A1 — cage shape: goal dir RO, coordination/ still writable
        _os.chmod(pkg, 0o555)
        try:
            out, err, code = mod.harness_outcome(mod.cmd_rule_disposition, ns(pkg))
        finally:
            _os.chmod(pkg, 0o755)
        grants = [g for _, g in mod.read_disposition_grants(pkg / "coordination")
                  if g["seat"] == "pred"]
        cell = session_cell(mod, pkg, "pred")
        check("A1",
              code is None
              and "GRANT MINTED" in out
              and "Traceback" not in (out + err)
              and len(grants) == 1
              and not grants[0]["spent-at"]
              and cell.get("disposition") == "exited",
              f"code={code!r} grants={len(grants)} cell={cell.get('disposition')!r}")

        # A3 before apply — after-edges must still see exited
        disp_before = mod.session_disposition(pkg, "pred")
        term_before = mod.terminal_disposition(pkg, pkg / "coordination", "pred")
        check("A3-before",
              disp_before == "exited"
              and term_before[0] == "exited",
              f"disp={disp_before!r} term={term_before!r}")

        # A2 — drain applies
        a_out, a_err, a_code = mod.harness_outcome(
            mod.cmd_apply_disposition_grants, ns(pkg, as_agent="ignite-daemon", go=False))
        cell_after = session_cell(mod, pkg, "pred")
        grants_after = [g for _, g in mod.read_disposition_grants(pkg / "coordination")
                        if g["seat"] == "pred"]
        check("A2",
              a_code is None
              and cell_after.get("disposition") == "done"
              and cell_after.get("disposition-writer") == "leader"
              and grants_after and grants_after[0]["spent-at"],
              f"code={a_code!r} cell={cell_after.get('disposition')!r} "
              f"writer={cell_after.get('disposition-writer')!r}")

        disp_after = mod.session_disposition(pkg, "pred")
        check("A3-after",
              disp_after == "done",
              f"disp={disp_after!r}")

        # A4 — remint same (seat, session-id) refuses (row is now done, but seed a fresh
        # ended+exited seat so the already-granted path is what fires)
        pkg2 = tmp / "pkg2"
        (pkg2 / "coordination").mkdir(parents=True)
        seed_ended(mod, pkg2, "dup", "exited")
        first_out, first_err, first_code = mod.harness_outcome(
            mod.cmd_rule_disposition, ns(pkg2, seat="dup", anchor="p-dup-1"))
        second_out, second_err, second_code = mod.harness_outcome(
            mod.cmd_rule_disposition, ns(pkg2, seat="dup", anchor="p-dup-2"))
        check("A4",
              first_code is None and "GRANT MINTED" in first_out
              and second_code == 1
              and "already carries a grant" in (second_out + second_err)
              and "Traceback" not in (second_out + second_err)
              and session_cell(mod, pkg2, "dup").get("disposition") == "exited",
              f"first={first_code!r} second={second_code!r}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


try:
    main()
except Exception as exc:  # noqa: BLE001
    check("harness", False, f"{exc.__class__.__name__}: {exc}")

body = "\n".join(lines) + "\n"
OUT.write_text(body, encoding="utf-8")
sys.stdout.write(body)
if failures:
    print(f"probe-disposition-grants: FAIL ({len(failures)}): {', '.join(failures)}")
    sys.exit(1)
print(f"probe-disposition-grants: PASS ({len(lines)} arms)")
sys.exit(0)
