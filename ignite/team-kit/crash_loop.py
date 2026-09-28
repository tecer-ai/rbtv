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


def prune_stale(pkg, *, now=None, window_sec=WINDOW_SEC):
    """Drop every alarm entry whose raising has aged out of ITS OWN detection window.

    THE CLEARING RULE (chosen over "clear on the seat's next successful check-in"): an alarm
    entry ages out once `now` is a full `window_sec` past its `raised_at`. The alarm's own
    definition is already "N pre-checkin deaths inside window_sec" — once that much time has
    passed with no new one counted, the pattern it reported is no longer live, whether or not the
    seat has run again. A check-in-triggered clear would need a hook in `session_checkin`
    (`ignite/coord/records.py`), which is outside this seat's granted files (custody: only
    `crash_loop.py` + `supervisor_door.py` + `attest.py#close_session_seat`) and under `coord/`'s
    own save/selftest discipline; the window-based rule is self-contained — this module owns both
    the raise and the clear — and needs no cross-package hook.

    Returns the list of seats cleared. Rewrites (or removes) the file only when something changed.
    """
    now = now or datetime.now()
    path = alarm_path(pkg)
    store = _load(path)
    if not store:
        return []
    cleared = []
    kept = {}
    for seat, alarm in store.items():
        raised = _parse_ended((alarm or {}).get("raised_at", ""))
        window = (alarm or {}).get("window_sec", window_sec)
        if raised is not None and now - raised >= timedelta(seconds=window):
            cleared.append(seat)
            continue
        kept[seat] = alarm
    if cleared:
        if kept:
            path.write_text(json.dumps(kept, indent=2) + "\n", encoding="utf-8")
        else:
            path.unlink(missing_ok=True)
    return cleared


def note_failed_death(pkg, seat, *, session="", result=None, now=None, window_sec=WINDOW_SEC):
    """Raise `seat-crash-loop` when this failed death is the second+ pre-checkin in the window.

    Returns the alarm dict when raised this call, the existing dict when already open,
    or None when the threshold is unmet / the ending is not failed.

    Prunes stale entries FIRST, on every call — the disarming path, run from the same place
    (`supervisor_door.death_stamp`) that already calls this on every session close, crash or clean.
    """
    now = now or datetime.now()
    prune_stale(pkg, now=now, window_sec=window_sec)
    if (result or {}).get("ending") != "failed":
        return None
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
    check("alarm still flags alpha before its window elapses",
          "alpha" in _load(alarm_path(pkg)))

    # ── clearing: entries age out with the SAME window that raised them (the chosen rule) ──────
    before_clear = alarm_path(pkg).read_text(encoding="utf-8")
    later = now + timedelta(seconds=WINDOW_SEC)
    cleared = prune_stale(pkg, now=later)
    after_clear_exists = alarm_path(pkg).exists()
    check("prune_stale clears alpha's alarm once the window elapses",
          cleared == ["alpha"] and '"seat": "alpha"' in before_clear and not after_clear_exists)

    # the production hook: `note_failed_death` prunes FIRST on every call, including a clean
    # (non-crash) close — so an operator sees a disarmed alarm on the seat's next session close
    # of ANY kind once the window has passed, without a second death.
    write_rows("s1,alpha,2026-08-31 15:50,\n"
               "s2,alpha,2026-08-31 15:55,\n")
    re_raised = note_failed_death(pkg, "alpha", session="s2",
                                  result={"ending": "failed"}, now=now)
    check("alpha re-trips the alarm after a prior clear",
          isinstance(re_raised, dict) and re_raised.get("alarm") == ALARM_NAME)
    much_later = now + timedelta(seconds=WINDOW_SEC * 2)
    note_failed_death(pkg, "alpha", result={"ending": "done"}, now=much_later)
    check("a later clean close, once the window has passed, disarms via the prune-first hook",
          "alpha" not in _load(alarm_path(pkg)))

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
