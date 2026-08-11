#!/usr/bin/env python3
"""probe-headless-retention-unknown.py — the live-worker count goes UNKNOWN when a headless row
aged out of the bounded view (task 7.556).

WHAT IT SCORES. `team_monitor.headless()` reads `jobs_log` through a BOUNDED view: a row is
dropped from `rows` once it is older than `HEADLESS_WINDOW_S` AND beyond its own `(job_id, seat)`
group's `HEADLESS_KEEP` newest — and it counts every row it drops into
`source['retention_dropped']` (closure guarantee: `scoped == emitted + retention_dropped +
unattributed`, stated in its own docstring). `goal-watcher-job.py`'s `headless_live()` used to
count non-terminal rows in that bounded view directly, so a dropped row that was STILL RUNNING
made the live-worker count read as a smaller, confident, WRONG number rather than as unknown.

⚠⚠ THE FIXTURE IS A REAL `heart.db`, BUILT AGAINST THE SHIPPING `team_monitor.headless()` — not a
hand-built snapshot dict. C0 proves the drop actually happened (`retention_dropped == 1`) before
anything else is asserted, per the task's own criterion (2): a fixture in which nothing could have
dropped proves nothing.

ARMS
  C0  the fixture drops exactly the ONE row built to be dropped: 6 headless `jobs_log` rows share
      one `(job_id, seat)` group; 5 are recent (kept regardless of count); the 6th is older than
      `HEADLESS_WINDOW_S` and beyond the group's `HEADLESS_KEEP` newest, so `headless()` itself
      drops it and reports `retention_dropped == 1`. `emitted == 5`, `scoped == 6`.
  R1  RED-FIRST, WHAT THE OLD FORMULA WOULD HAVE SAID. The pre-fix body of `headless_live` —
      `sum(1 for r in headless_rows if r['outcome'] is None)` — is exercised directly here (it is
      the shipping code's OWN one-line body, quoted, not reimplemented) against the SAME emitted
      rows: a confident, non-None integer. This is the wrong-but-confident number the old code
      would have reported for this exact view.
  R2  GREEN, THE FIX. `goal_watcher.headless_live()` on the identical snapshot returns `(None,
      why)` — never a number, never 0 — and `why` names `retention_dropped`. Revert task 7.556's
      change to `headless_live` and this arm reds (R1 and R2 both become confident integers).
  R3  the unknown does NOT silently become a stall action. `run_stall()` over a snapshot shaped
      `ready>0, live=0, queued=0` with this SAME dropped-row headless view returns UNDECIDABLE
      (naming `headless-live`), not the RUN-STALL nudge a real `hl == 0` would fire — proving the
      unknown value is not read as zero downstream (task criterion 3).
  C1  NEGATIVE CONTROL. A clean run of the SAME shape with only 3 rows (nothing old enough or
      numerous enough to drop) has `retention_dropped == 0`, and `headless_live()` still returns a
      real number — the fix does not degrade every pass to unknown, only a run that actually lost
      a row.

Run it through the suite — `node deploy/probe-suite.js --only headless-retention-unknown` — never
by hand (`G-163`).
Exit 0 = every property holds · 1 = a property is broken · 2 = INOPERATIVE.
"""
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe-headless-retention-unknown.out"
JOB = HERE.parent / "goal-watcher-job.py"
TEAM_MONITOR = HERE.parents[2] / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"

lines, failures, inoperative = [], [], []


def say(s):
    lines.append(s)


def check(arm, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {arm}  {detail}")
    if not ok:
        failures.append(arm)


def stop(arm, why):
    say(f"INOPERATIVE  {arm}  {why}")
    inoperative.append(arm)


def load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def build_db(db_path, package_root, job_id, seat, now, n_recent, n_old):
    """`jobs_log` rows for one (job_id, seat) group: `n_recent` fresh non-terminal rows plus
    `n_old` rows started well outside HEADLESS_WINDOW_S — all non-terminal (`status='running'`,
    so `outcome` reads None), all scoped to `package_root` via `workdir`."""
    con = sqlite3.connect(str(db_path))
    con.execute("""CREATE TABLE jobs_log (
        exec_id INTEGER PRIMARY KEY, parent_exec_id INTEGER, job_id TEXT, action_type TEXT,
        session_mode TEXT, status TEXT, session_id TEXT, pid INTEGER, exit_code INTEGER,
        started_at TEXT, ended_at TEXT, log_path TEXT, workdir TEXT, completion_msg_id TEXT)""")
    exec_id = 0
    started_ats = ([now - 7200 - i for i in range(n_old)]      # old rows: exec_ids 1..n_old,
                    + [now - 60 - i for i in range(n_recent)])  # processed LAST (exec_id DESC),
                                                                 # so they rank beyond HEADLESS_KEEP.
    session_seats = []
    for started in started_ats:
        exec_id += 1
        sid = f"sess-{exec_id}"
        con.execute(
            "INSERT INTO jobs_log (exec_id, parent_exec_id, job_id, action_type, session_mode,"
            " status, session_id, pid, exit_code, started_at, ended_at, log_path, workdir,"
            " completion_msg_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (exec_id, None, job_id, "job", "headless", "running", sid, 1234, None,
             iso(started), None, "", str(package_root), None))
        session_seats.append((sid, seat))
    con.commit()
    con.close()
    return session_seats


def write_sessions_csv(package, session_seat_pairs):
    lines_ = ["session-id,seat"] + [f"{sid},{seat}" for sid, seat in session_seat_pairs]
    (Path(package) / "sessions.csv").write_text("\n".join(lines_) + "\n", encoding="utf-8")


def main():
    for p in (JOB, TEAM_MONITOR):
        if not p.exists():
            return stop("FIXTURE", f"source missing: {p}")
    tm = load_by_path("team_monitor_under_probe", TEAM_MONITOR)
    gw = load_by_path("goal_watcher_under_probe", JOB)

    td = Path(tempfile.mkdtemp(prefix="probe-w7556-"))
    try:
        pkg = td / "run-1"
        pkg.mkdir(parents=True)
        pkg = pkg.resolve()  # scoped_execs matches `workdir` against Path(package).resolve()
        db_path = td / "heart.db"
        now = time.time()
        job_id, seat = "probe-job", "worker-a"

        session_seats = build_db(db_path, pkg, job_id, seat, now,
                                  n_recent=tm.HEADLESS_KEEP, n_old=1)
        write_sessions_csv(pkg, session_seats)

        gw_rows, incident, source = tm.headless(str(pkg), now, db_path=str(db_path))

        # ---- C0: the fixture actually dropped the one row built to be dropped ----------------
        check("C0", source.get("readable") is True and source.get("retention_dropped") == 1
              and source.get("scoped") == tm.HEADLESS_KEEP + 1
              and source.get("emitted") == tm.HEADLESS_KEEP
              and len(gw_rows) == tm.HEADLESS_KEEP,
              f"source={source}; emitted rows={len(gw_rows)} — a probe that could not drop a row "
              f"proves nothing about the fix")

        snap = {"headless": gw_rows, "headless_source": source}

        # ---- R1: the pre-fix formula, quoted verbatim, still returns a confident number -------
        pre_fix_count = sum(1 for r in (snap.get("headless") or []) if r.get("outcome") is None)
        check("R1", pre_fix_count is not None and isinstance(pre_fix_count, int),
              f"pre-fix formula over the SAME emitted view -> {pre_fix_count} (a confident "
              f"integer, undercounting the row that aged out unseen)")

        # ---- R2: GREEN — the shipping fix reports unknown, not a number, on this fixture ------
        hl, hl_why = gw.headless_live(snap)
        check("R2", hl is None and "retention_dropped" in hl_why,
              f"headless_live(snap) -> ({hl!r}, {hl_why!r}) — must be None with the dropped-count "
              f"named, never {pre_fix_count!r} again")

        # ---- R3: the unknown does not silently read as zero in the stall predicate ------------
        run_snap = dict(snap)
        run_snap["run"] = {"ready_rows": 1, "live_executors": 0, "queued": 0,
                            "source": {"ready_rows": "", "queued": {"reason": ""}}}
        args = gw._ns()
        decisions = gw.run_stall(run_snap, args)
        check("R3", len(decisions) == 1 and decisions[0]["nudge"] == ""
              and "UNDECIDABLE" in decisions[0]["action"]
              and "headless-live" in decisions[0]["action"],
              f"run_stall() over ready=1,live=0,queued=0 with the dropped-row view -> "
              f"{decisions!r} — must be UNDECIDABLE naming headless-live, never the RUN-STALL "
              f"nudge a real hl==0 would fire")

        # ---- C1: negative control — a clean run still returns a real number -------------------
        td2 = Path(tempfile.mkdtemp(prefix="probe-w7556-clean-"))
        try:
            pkg2 = td2 / "run-1"
            pkg2.mkdir(parents=True)
            pkg2 = pkg2.resolve()
            db2 = td2 / "heart.db"
            session_seats2 = build_db(db2, pkg2, "probe-job-clean", "worker-b", now,
                                       n_recent=3, n_old=0)
            write_sessions_csv(pkg2, session_seats2)
            gw_rows2, _, source2 = tm.headless(str(pkg2), now, db_path=str(db2))
            hl2, _ = gw.headless_live({"headless": gw_rows2, "headless_source": source2})
            check("C1", source2.get("retention_dropped") == 0 and hl2 == 3,
                  f"clean run: retention_dropped={source2.get('retention_dropped')}, "
                  f"headless_live={hl2!r} — the fix must not degrade every pass to unknown")
        finally:
            shutil.rmtree(td2, ignore_errors=True)
    finally:
        shutil.rmtree(td, ignore_errors=True)


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-headless-retention-unknown  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
