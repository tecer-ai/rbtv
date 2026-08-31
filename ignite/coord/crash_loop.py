"""Seat crash-loop alarm: ≥2 pre-checkin deaths of one seat in a bounded window.

Named `seat-crash-loop`. Distinct from `observation/daemon-watchdog`'s systemd
`NRestarts` crash-loop. Visible outside executions.csv as
`{package}/coordination/seat-crash-loop.json` plus one stderr line. Raised once
per (package, seat) episode, not once per death.
"""
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ALARM_NAME = "seat-crash-loop"
WINDOW_SEC = 3600
THRESHOLD = 2
ENDED_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ")


def alarm_path(pkg):
    return Path(pkg) / "coordination" / "seat-crash-loop.json"


def _parse_ended(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ENDED_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def precheckin_deaths(pkg, seat, *, now=None, window_sec=WINDOW_SEC):
    """Ended sessions.csv rows for `seat` with an empty checkin cell inside the window."""
    path = Path(pkg) / "sessions.csv"
    if not path.is_file():
        return []
    now = now or datetime.now()
    cutoff = now - timedelta(seconds=window_sec)
    out = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("seat") or "").strip() != seat:
                continue
            if (row.get("checkin") or "").strip():
                continue
            ended_raw = (row.get("ended") or "").strip()
            if not ended_raw:
                continue
            ended_at = _parse_ended(ended_raw)
            if ended_at is not None and ended_at < cutoff:
                continue
            out.append(row)
    return out


def _load(path):
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def note_failed_death(pkg, seat, *, session="", result=None, now=None, window_sec=WINDOW_SEC):
    """Raise `seat-crash-loop` when this failed death is the second+ pre-checkin in the window.

    Returns the alarm dict when raised this call, the existing dict when already open,
    or None when the threshold is unmet / the ending is not failed.
    """
    if (result or {}).get("ending") != "failed":
        return None
    now = now or datetime.now()
    deaths = precheckin_deaths(pkg, seat, now=now, window_sec=window_sec)
    if len(deaths) < THRESHOLD:
        return None
    path = alarm_path(pkg)
    store = _load(path)
    existing = store.get(seat)
    if isinstance(existing, dict) and existing.get("alarm") == ALARM_NAME:
        return existing
    alarm = {
        "alarm": ALARM_NAME,
        "seat": seat,
        "count": len(deaths),
        "window_sec": window_sec,
        "raised_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "session": str(session or ""),
        "sessions": [(r.get("session-id") or "").strip() for r in deaths],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    store[seat] = alarm
    path.write_text(json.dumps(store, indent=2) + "\n", encoding="utf-8")
    print(f"{ALARM_NAME}: seat={seat} count={alarm['count']} window={window_sec}s "
          f"path={path}", file=sys.stderr)
    return alarm


def observe_failed_death(pkg, seat, *, session="", result=None, now=None):
    """Door hook: never raises. A closer that cannot alarm still stamped."""
    try:
        return note_failed_death(pkg, seat, session=session, result=result, now=now)
    except Exception as exc:  # noqa: BLE001
        print(f"{ALARM_NAME}: observe failed — {exc}", file=sys.stderr)
        return None


def selftest():
    import tempfile

    failures = []

    def check(label, cond):
        if cond:
            print(f"PASS {label}")
        else:
            failures.append(label)
            print(f"FAIL {label}")

    tmp = Path(tempfile.mkdtemp(prefix="test-seat-crash-loop-"))
    pkg = tmp / "pkg"
    (pkg / "coordination").mkdir(parents=True)
    now = datetime(2026, 8, 31, 16, 0)
    header = "session-id,seat,ended,checkin\n"

    def write_rows(rows):
        (pkg / "sessions.csv").write_text(header + rows, encoding="utf-8")

    write_rows("s1,alpha,2026-08-31 15:50,\n")
    one = note_failed_death(pkg, "alpha", session="s1",
                            result={"ending": "failed"}, now=now)
    check("one pre-checkin death does not raise", one is None and not alarm_path(pkg).exists())

    write_rows("s1,alpha,2026-08-31 15:50,\n"
               "s2,alpha,2026-08-31 15:55,\n")
    first = note_failed_death(pkg, "alpha", session="s2",
                             result={"ending": "failed"}, now=now)
    check("two pre-checkin deaths raise seat-crash-loop once",
          isinstance(first, dict) and first.get("alarm") == ALARM_NAME
          and first.get("count") == 2 and alarm_path(pkg).is_file())

    write_rows("s1,alpha,2026-08-31 15:50,\n"
               "s2,alpha,2026-08-31 15:55,\n"
               "s3,alpha,2026-08-31 15:59,\n")
    again = note_failed_death(pkg, "alpha", session="s3",
                             result={"ending": "failed"}, now=now)
    text = alarm_path(pkg).read_text(encoding="utf-8")
    check("a third death does not emit a second alarm",
          again == first and text.count(f'"{ALARM_NAME}"') == 1)

    skip = note_failed_death(pkg, "alpha", result={"ending": "done"}, now=now)
    check("a done ending is not a crash-loop", skip is None)

    other = tmp / "other"
    (other / "coordination").mkdir(parents=True)
    (other / "sessions.csv").write_text(
        header + "s1,beta,2026-08-31 12:00,\ns2,beta,2026-08-31 12:05,\n", encoding="utf-8")
    stale = note_failed_death(other, "beta", result={"ending": "failed"}, now=now)
    check("deaths outside the window do not raise", stale is None)

    checked = tmp / "checked"
    (checked / "coordination").mkdir(parents=True)
    (checked / "sessions.csv").write_text(
        header + "s1,gamma,2026-08-31 15:50,2026-08-31 15:40\n"
        "s2,gamma,2026-08-31 15:55,2026-08-31 15:41\n", encoding="utf-8")
    post = note_failed_death(checked, "gamma", result={"ending": "failed"}, now=now)
    check("checked-in deaths are not pre-checkin", post is None)

    if failures:
        raise SystemExit(f"{len(failures)} FAIL: {failures}")
    print("ALL PASS")


if __name__ == "__main__":
    selftest()
