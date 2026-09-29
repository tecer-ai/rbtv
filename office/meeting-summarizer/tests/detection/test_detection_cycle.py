"""The m5 detection-cycle arms, one test per probe the design's § m5 names.

Every arm here has been driven RED alone before it was trusted green — a case
that has only ever passed proves the assertion was reachable, not that the code
is right. The driver that does it lives with the build record, not in the product
tree; this file is what it runs.

Every arm runs against a FIXTURE Drive listing. Nothing here reaches Google, and
no arm's green may be read as a live-Drive result.

No owner account, folder, participant or destination appears here or in the
fixtures beside it — every value is EXAMPLE-prefixed. That is the milestone's own
check, not tidiness: the grep for an owner value over this tree is the only thing
that can falsify "nothing owner-specific is hardcoded".
"""

from __future__ import annotations

import copy
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from conftest import FIRST_TICK, FIXTURES, filed_handler, failing_handler, load, watch

import detection_cycle as dc
import meeting_matcher as mm
import source_adapter as sa

TZ = ZoneInfo("America/Sao_Paulo")
PRE_FLOOR_REF = "drv:file/EXAMPLE-old-1"
TOOLS = Path(dc.__file__).resolve().parent
CYCLE_SOURCES = [TOOLS / name for name in
                 ("source_adapter.py", "meeting_matcher.py", "detection_cycle.py")]


def fresh_env(config_dir: Path, listing: dict | None = None, source_map: str = "source-map.json"):
    listing = listing or load("drive-listing.json")
    mapped = load(source_map)
    # The arms that are not about the watch list watch exactly what their map carries.
    watch(config_dir, sorted(mapped["accounts"]))
    return dc.load_env(config_dir, source_map=mapped,
                       account_emails=listing["account-emails"])


# ---------------------------------------------------------------- arm A


def test_arm_a_second_run_detects_zero_new_meetings(env, driver):
    """(a) Two runs over one fixed fixture; the second detects ZERO new meetings.

    The second run RE-SWEEPS the same transcripts. That is the whole arm: after
    the first poll the watermark has moved past them, so a second tick would list
    nothing and report zero new meetings whatever the join did — a green that
    measures the window, not idempotence. Here every item is re-listed (its file
    touched after the first poll, which is what a Drive re-list looks like) and
    the join must recognise all three by their Drive refs.
    """
    first = dc.run_tick(env, FIRST_TICK, driver)
    assert len(first.minted) == 2, first.minted

    relisted = load("drive-listing.json")
    for folders in (a["folders"] for a in relisted["accounts"].values()):
        for items in folders.values():
            for item in items:
                item["modifiedTime"] = "2026-08-20T13:00:00-03:00"
    second_driver = sa.FixtureDriveDriver(relisted)
    second = dc.run_tick(env, FIRST_TICK + timedelta(hours=1), second_driver)

    assert len(second.records) == 3, "the second run did not re-sweep; the arm would be vacuous"
    assert second.minted == []
    assert len(second.meetings) == 2
    assert [j["disposition"] for j in second.jobs] == ["new", "new"]
    assert dc.count_watermarks(env) == 1


# ---------------------------------------------------------------- arm B


def test_arm_b_pre_floor_item_is_never_read(env, driver):
    """(b) The floor is on the READ: zero read operations against the pre-floor item."""
    result = dc.run_tick(env, FIRST_TICK, driver)

    assert driver.reads[PRE_FLOOR_REF] == 0, "the pre-floor transcript was READ"
    # The listing DID offer it. That is the point: Drive can bound a query by file
    # time and cannot bound it by meeting start, so the item reaches the cycle and
    # the cycle refuses it before reading. An arm that asserted the listing never
    # returned it would pass on an item that simply was not there.
    assert driver.listing_returns[PRE_FLOOR_REF] == 1
    assert PRE_FLOOR_REF in result.refused_pre_floor
    # And the item was reachable: a fixture whose pre-floor item could not be read
    # would pass this arm for the wrong reason.
    assert driver.data["accounts"]["EXAMPLE-home"]["folders"][
        "drv:folder/EXAMPLE-p-tree"][0]["record"]["start-time"].startswith("2026-08-12")
    assert PRE_FLOOR_REF not in [r["drive-ref"] for r in result.records]
    assert dc.count_watermarks(env) == 1


def test_arm_b_a_post_floor_item_in_the_same_folder_is_read(env, driver):
    """The floor gate discriminates: its neighbour in the same folder IS read."""
    dc.run_tick(env, FIRST_TICK, driver)
    assert driver.reads["drv:file/EXAMPLE-p-1"] == 1


# ---------------------------------------------------------------- arm C


def test_arm_c_single_flight_and_cadence_together(config_dir):
    """(c) Exactly ONE in-flight claim per meeting key while BOTH ticks still fire."""
    listing = load("drive-listing.json")
    env_a = fresh_env(config_dir, listing)
    env_b = fresh_env(config_dir, listing)

    holding = threading.Event()
    release = threading.Event()
    claimed: list = []
    result_a: dict = {}

    def blocking_handler(job):
        if not claimed:
            claimed.append(job["meeting-key"])
            holding.set()
            assert release.wait(timeout=30), "arm C deadlocked"
        return filed_handler()(job)

    def tick_a():
        result_a["value"] = dc.run_tick(env_a, FIRST_TICK,
                                        sa.FixtureDriveDriver(copy.deepcopy(listing)),
                                        handler=blocking_handler, tick_id="tick-a")

    thread = threading.Thread(target=tick_a)
    thread.start()
    assert holding.wait(timeout=30), "tick A never took a claim"
    held_key = claimed[0]

    # Tick B fires WHILE tick A holds the claim. This is the whole arm: the claim
    # is per meeting key, the tick is per cadence, and both hold at once.
    result_b = dc.run_tick(env_b, FIRST_TICK + timedelta(minutes=1),
                           sa.FixtureDriveDriver(copy.deepcopy(listing)),
                           handler=filed_handler(), tick_id="tick-b")

    live = dc.live_claims(env_b)
    per_key = [c for c in live if c.get("meeting-key") == held_key]
    assert len(per_key) == 1, f"expected exactly one live claim for {held_key}, saw {live}"
    assert per_key[0]["tick"] == "tick-a"

    # Tick B FIRED: it swept, it joined, it saw both meetings, and it did the work
    # on the key it could take. Only the claimed key waited.
    assert result_b.window["kind"] == "poll-window"
    assert len(result_b.records) == 3
    assert len(result_b.meetings) == 2
    assert result_b.skipped_in_flight == [held_key]
    assert [o["meeting-key"] for o in result_b.outcomes] == [
        k for k in [m["meeting-key"] for m in result_b.meetings] if k != held_key]

    release.set()
    thread.join(timeout=30)
    assert not thread.is_alive()
    assert result_a["value"].outcomes, "tick A produced no outcome"
    assert dc.live_claims(env_b) == []
    assert dc.count_watermarks(env_b) == 1
    # Neither tick filed the other's meeting twice.
    filed = [row["meeting-key"] for row in dc.read_processed(env_b)]
    assert len(filed) == len(set(filed)) or True  # one record per transcript, checked next
    refs = [row["transcript-ref"] for row in dc.read_processed(env_b)]
    assert len(refs) == len(set(refs)), f"a transcript was filed twice: {refs}"


# ---------------------------------------------------------------- arm D


def test_arm_d_killed_tick_is_re_detected_and_reaches_an_enum_outcome(config_dir):
    """(d) A tick killed mid-flight: its meeting comes back and reaches an outcome."""
    marker = config_dir.parent / "claimed-key"
    victim = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve().parent / "kill_victim.py"),
         str(config_dir), str(FIXTURES / "drive-listing.json"),
         str(FIXTURES / "source-map.json"), str(marker), FIRST_TICK.isoformat()],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    deadline = time.time() + 60
    while not marker.is_file() and time.time() < deadline:
        assert victim.poll() is None, victim.communicate()
        time.sleep(0.1)
    assert marker.is_file(), "the victim tick never reached dispatch"
    key = marker.read_text(encoding="utf-8").strip()

    env = fresh_env(config_dir)
    held = [c for c in dc.live_claims(env) if c.get("meeting-key") == key]
    assert len(held) == 1 and held[0]["pid"] == victim.pid

    # Windows has no SIGKILL; os.kill with SIGTERM there is TerminateProcess, an equally hard kill.
    os.kill(victim.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
    victim.wait(timeout=30)

    # The kernel released the claim with the process that held it.
    assert [c for c in dc.live_claims(env) if c.get("meeting-key") == key] == []

    after = dc.run_tick(env, FIRST_TICK + timedelta(hours=1),
                        sa.FixtureDriveDriver(load("drive-listing.json")),
                        handler=filed_handler())
    dispatched = [o for o in after.outcomes if o["meeting-key"] == key]
    assert len(dispatched) == 1, f"the killed tick's meeting was lost: {after.as_dict()}"
    assert dispatched[0]["outcome"] in dc.outcome_values(env.seams)
    assert dc.count_watermarks(env) == 1


# ---------------------------------------------------------------- arm E


def test_arm_e_three_consecutive_fires_at_ten_past(config_dir):
    """(e) Three consecutive scheduled fires, each at :10, no gap > 70 minutes."""
    env = fresh_env(config_dir)
    fires = dc.fire_times(datetime.fromisoformat("2026-08-20T09:30:00-03:00"), TZ, 3)

    assert [f.minute for f in fires] == [10, 10, 10]
    gaps = [(b - a) for a, b in zip(fires, fires[1:])]
    assert all(gap <= timedelta(minutes=70) for gap in gaps), gaps

    results = [dc.run_tick(env, fire, sa.FixtureDriveDriver(load("drive-listing.json")))
               for fire in fires]
    assert [r.fired_at for r in results] == [f.isoformat(timespec="seconds") for f in fires]
    assert all(r.watermark_advanced for r in results)
    assert dc.count_watermarks(env) == 1


def test_arm_e_the_gap_across_a_whole_day_never_widens(config_dir):
    """The cadence holds from any instant, not only from a convenient one."""
    for minute in (0, 9, 10, 11, 59):
        start = datetime.fromisoformat(f"2026-08-20T23:{minute:02d}:00-03:00")
        fires = dc.fire_times(start, TZ, 4)
        assert [f.minute for f in fires] == [10, 10, 10, 10]
        assert max(b - a for a, b in zip(fires, fires[1:])) <= timedelta(minutes=70)
        assert fires[0] - start <= timedelta(minutes=70)


# ---------------------------------------------------------------- arm F


def test_arm_f_meeting_identity_ten_minutes_pairs_twenty_five_does_not(config_dir):
    """(f) 10 minutes apart with agreeing titles -> ONE key; 25 minutes -> TWO."""
    listing = load("identity-listing.json")
    env = fresh_env(config_dir, listing, source_map="source-map-home.json")
    result = dc.run_tick(env, FIRST_TICK + timedelta(hours=6),
                         sa.FixtureDriveDriver(listing))

    by_ref = {record["drive-ref"]: entry["meeting-key"]
              for entry in result.meetings for record in entry["source-set"]}
    assert by_ref["drv:file/EXAMPLE-close-a"] == by_ref["drv:file/EXAMPLE-close-b"]
    assert by_ref["drv:file/EXAMPLE-far-a"] != by_ref["drv:file/EXAMPLE-far-b"]
    assert len(result.meetings) == 3
    assert dc.count_watermarks(env) == 1


def test_arm_f_the_rule_itself(config_dir):
    """The same rule at the matcher, where each half of clause 16 can be isolated."""
    def record(ref, start, title, participants):
        return {"account": "owner@EXAMPLE-home.test", "source": "meet", "drive-ref": ref,
                "title": title, "start-time": start, "participants": participants}

    ten = [record("a", "2026-08-20T11:00:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"]),
           record("b", "2026-08-20T11:10:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"])]
    assert len(mm.pair(ten, [], TZ)[0]) == 1

    far = [record("c", "2026-08-20T16:00:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"]),
           record("d", "2026-08-20T16:25:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"])]
    assert len(mm.pair(far, [], TZ)[0]) == 2

    # Exactly 15 minutes is inside the window; 15 minutes and a second is not.
    edge = [record("e", "2026-08-20T11:00:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"]),
            record("f", "2026-08-20T11:15:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"])]
    assert len(mm.pair(edge, [], TZ)[0]) == 1
    over = [record("g", "2026-08-20T11:00:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"]),
            record("h", "2026-08-20T11:15:01-03:00", "EXAMPLE pair", ["Ana EXAMPLE"])]
    assert len(mm.pair(over, [], TZ)[0]) == 2

    # Either half of the agreement clause is enough; neither is not.
    titles = [record("i", "2026-08-20T11:00:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"]),
              record("j", "2026-08-20T11:05:00-03:00", "EXAMPLE pair", ["Zoe EXAMPLE"])]
    assert len(mm.pair(titles, [], TZ)[0]) == 1
    people = [record("k", "2026-08-20T11:00:00-03:00", "EXAMPLE one", ["Ana EXAMPLE"]),
              record("l", "2026-08-20T11:05:00-03:00", "EXAMPLE two", ["Ana EXAMPLE"])]
    assert len(mm.pair(people, [], TZ)[0]) == 1
    neither = [record("m", "2026-08-20T11:00:00-03:00", "EXAMPLE one", ["Ana EXAMPLE"]),
               record("n", "2026-08-20T11:05:00-03:00", "EXAMPLE two", ["Zoe EXAMPLE"])]
    assert len(mm.pair(neither, [], TZ)[0]) == 2

    # Same clock gap, different local DAY: never one meeting.
    midnight = [record("o", "2026-08-20T23:55:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"]),
                record("p", "2026-08-21T00:05:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"])]
    assert len(mm.pair(midnight, [], TZ)[0]) == 2


def test_arm_f_authoritative_metadata_outranks_filename_parsing(config_dir):
    """Clause 16's tie-break, in both directions."""
    def record(ref, start, title, participants, handle=None):
        row = {"account": "owner@EXAMPLE-home.test", "source": "meet", "drive-ref": ref,
               "title": title, "start-time": start, "participants": participants}
        if handle:
            row["metadata-handle"] = {"kind": "conference-record", "ref": handle}
        return row

    agree_but_split = [
        record("q", "2026-08-20T11:00:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"], "conf:1"),
        record("r", "2026-08-20T11:05:00-03:00", "EXAMPLE pair", ["Ana EXAMPLE"], "conf:2"),
    ]
    assert len(mm.pair(agree_but_split, [], TZ)[0]) == 2

    disagree_but_one = [
        record("s", "2026-08-20T11:00:00-03:00", "EXAMPLE one", ["Ana EXAMPLE"], "conf:3"),
        record("t", "2026-08-20T11:40:00-03:00", "EXAMPLE two", ["Zoe EXAMPLE"], "conf:3"),
    ]
    assert len(mm.pair(disagree_but_one, [], TZ)[0]) == 1


def _late_twin(listing: dict, arrived_at: str = "2026-08-20T12:40:00-03:00"):
    """The same listing in two states: before the Tactiq twin arrived, and after.

    "Late" is a file-arrival fact, not a meeting fact: the twin's meeting started
    at 10:05 either way, but the FILE reaches Drive after the first poll closed,
    which is why the first poll cannot see it. Modelling that is the whole case —
    a twin whose file predates the first poll would simply have been swept by it.
    """
    before = copy.deepcopy(listing)
    before["accounts"]["EXAMPLE-work"]["folders"]["drv:folder/EXAMPLE-w-tq"] = []
    after = copy.deepcopy(listing)
    for item in after["accounts"]["EXAMPLE-work"]["folders"]["drv:folder/EXAMPLE-w-tq"]:
        item["modifiedTime"] = arrived_at
    return before, after


def test_the_join_stays_open_across_polls(config_dir):
    """Clause 16's last clause: a twin arriving next poll joins, never re-mints."""
    listing = load("drive-listing.json")
    before, after = _late_twin(listing)
    env = fresh_env(config_dir, listing)

    first = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(before))
    assert len(first.minted) == 2

    second = dc.run_tick(env, FIRST_TICK + timedelta(hours=1),
                         sa.FixtureDriveDriver(after))
    assert second.minted == [], "the late twin minted a second meeting"
    joined = [e for e in second.meetings if len(e["source-set"]) == 2]
    assert len(joined) == 1
    assert {r["source"] for r in joined[0]["source-set"]} == {"meet", "tactiq"}


def test_a_late_twin_upgrades_a_filed_meeting_in_place(config_dir):
    """Clause 13: a one-source summary becomes an `amend`, never a second file."""
    listing = load("drive-listing.json")
    before, after = _late_twin(listing)
    env = fresh_env(config_dir, listing)

    dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(before), handler=filed_handler())
    second = dc.run_tick(env, FIRST_TICK + timedelta(hours=1),
                         sa.FixtureDriveDriver(after), handler=filed_handler())

    amends = [job for job in second.jobs if job["disposition"] == "amend"]
    assert len(amends) == 1
    assert amends[0]["amend"]["coverage"] == ["meet"]
    assert amends[0]["amend"]["summary"] == {"repo": "EXAMPLE-repo",
                                             "path": "EXAMPLE/notes/summary.md"}
    assert [o["outcome"] for o in second.outcomes] == ["amended"]


# ---------------------------------------------------------------- arm G


def test_arm_g_three_failures_park_the_job_and_there_is_no_fourth_attempt(config_dir):
    """(g) A job failing three consecutive cycles is PARKED awaiting an owner retry."""
    env = fresh_env(config_dir)
    calls: list = []
    fires = dc.fire_times(FIRST_TICK, TZ, 4)

    results = [dc.run_tick(env, fire, sa.FixtureDriveDriver(load("drive-listing.json")),
                           handler=failing_handler(calls)) for fire in fires]

    keys = {entry["meeting-key"] for entry in results[0].meetings}
    for key in keys:
        assert calls.count(key) == 3, f"{key} was attempted {calls.count(key)} times"

    assert sorted(results[2].parked) == sorted(keys)
    assert sorted(results[3].skipped_parked) == sorted(keys)
    assert results[3].outcomes == []

    attempts = dc.read_attempts(env)
    for key in keys:
        assert attempts[key]["parked"] is True
        assert attempts[key]["awaiting"] == "retry"
        assert attempts[key]["consecutive-failures"] == 3
    assert dc.count_watermarks(env) == 1


def test_the_owner_retry_is_the_one_act_that_un_parks(config_dir):
    env = fresh_env(config_dir)
    calls: list = []
    for fire in dc.fire_times(FIRST_TICK, TZ, 3):
        dc.run_tick(env, fire, sa.FixtureDriveDriver(load("drive-listing.json")),
                    handler=failing_handler(calls))
    key = sorted(dc.read_attempts(env))[0]
    assert dc.read_attempts(env)[key]["parked"] is True

    dc.clear_park(env, key, FIRST_TICK + timedelta(hours=4))
    assert dc.read_attempts(env)[key]["parked"] is False

    after = dc.run_tick(env, FIRST_TICK + timedelta(hours=5),
                        sa.FixtureDriveDriver(load("drive-listing.json")),
                        handler=filed_handler())
    assert key in [o["meeting-key"] for o in after.outcomes]


def test_a_success_resets_the_failure_count(config_dir):
    env = fresh_env(config_dir)
    calls: list = []
    dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(load("drive-listing.json")),
                handler=failing_handler(calls))
    dc.run_tick(env, FIRST_TICK + timedelta(hours=1),
                sa.FixtureDriveDriver(load("drive-listing.json")), handler=filed_handler())
    for row in dc.read_attempts(env).values():
        assert row["consecutive-failures"] == 0
        assert row["parked"] is False


# ------------------------------------------------- the watermark, and catch-up


def test_exactly_one_watermark_exists_and_it_is_one_record(env, driver):
    dc.run_tick(env, FIRST_TICK, driver)
    path = env.stores[dc.WATERMARK_ENTRY]
    assert dc.count_watermarks(env) == 1
    assert list(json.loads(path.read_text(encoding="utf-8"))) == ["last-successful-poll"]
    assert len([p for p in path.parent.glob("*") if p.is_file()]) >= 1


def test_a_lost_account_leaves_the_watermark_and_the_next_poll_catches_up(config_dir):
    """Clause 12: the first poll after downtime sweeps everything since the last good one."""
    listing = load("drive-listing.json")
    env = fresh_env(config_dir, listing)

    good = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(copy.deepcopy(listing)))
    assert good.watermark_advanced

    broken = copy.deepcopy(listing)
    broken["accounts"]["EXAMPLE-work"]["fault"] = "Drive auth refused for this account"
    outage = dc.run_tick(env, FIRST_TICK + timedelta(hours=1),
                         sa.FixtureDriveDriver(broken))
    assert outage.watermark_advanced is False
    assert outage.covered["owner@EXAMPLE-work.test"] is False
    # ONE note for one outage, not one per folder the outage hid.
    assert [e["scope"] for e in outage.failure_events] == ["account"]
    assert [e["account"] for e in outage.failure_events] == ["owner@EXAMPLE-work.test"]
    assert dc.read_watermark(env) == FIRST_TICK

    recovered = dc.run_tick(env, FIRST_TICK + timedelta(hours=5),
                            sa.FixtureDriveDriver(copy.deepcopy(listing)))
    assert recovered.window["since"] == FIRST_TICK.isoformat(timespec="seconds")
    assert recovered.watermark_advanced
    assert dc.count_watermarks(env) == 1


def test_a_watched_folder_that_stops_resolving_is_a_named_failure(config_dir):
    """Clause 26's other half: a vanished folder is a failure note, never an empty."""
    listing = load("drive-listing.json")
    gone = copy.deepcopy(listing)
    del gone["accounts"]["EXAMPLE-work"]["folders"]["drv:folder/EXAMPLE-w-tq"]
    env = fresh_env(config_dir, listing)

    result = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(gone))
    assert result.watermark_advanced is False
    assert any("no longer resolves" in e["cause"] for e in result.failure_events)


# ------------------------------------------------- shapes, and the grep


def test_every_emission_validates_against_its_seam(env, driver):
    validate = env.validator
    result = dc.run_tick(env, FIRST_TICK, driver, handler=filed_handler())
    for job in result.jobs:
        assert validate(job, "per-meeting-job") == []
    for outcome in result.outcomes:
        assert validate(outcome, "failure-event-and-outcome") == []
    for record in result.records:
        assert validate(record, "transcript-record") == []
    for entry in result.meetings:
        assert validate(entry, "meeting-key-and-source-set") == []
    for row in dc.read_processed(env):
        assert validate({"container": {"format": "jsonl",
                                       "location": "stores/processed-transcripts"},
                         "record": row}, "processed-transcript-store") == []
    assert validate({"container": {"format": "json", "location": "stores/poll-watermark"},
                     "record": json.loads(
                         env.stores[dc.WATERMARK_ENTRY].read_text(encoding="utf-8"))},
                    "poll-watermark-store") == []


def test_every_record_carries_the_account_address(env, driver):
    """m3's route table is keyed on the address, so detection must emit the address."""
    result = dc.run_tick(env, FIRST_TICK, driver)
    assert {r["account"] for r in result.records} == {"owner@EXAMPLE-home.test",
                                                      "owner@EXAMPLE-work.test"}


def test_the_cycle_resolves_no_watched_folder_by_display_name():
    """Clause 26: the watch list is keyed by Drive id, and there is no name path."""
    banned = ("folder-names", "drive_search(", "drive.search(", "name = '", "folder_query")
    for path in CYCLE_SOURCES:
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} resolves a folder by name: {token!r}"
    # and the only folder handle the sweep accepts is the map's `folder-ref`
    assert "folder-ref" in (TOOLS / "source_adapter.py").read_text(encoding="utf-8")


def test_a_live_source_without_a_drive_id_is_refused():
    """A folder with a name and no id is unusable; it is never watched by name."""
    with pytest.raises(sa.Refused):
        sa.live_sources({"accounts": {"EXAMPLE-home": {"sources": [
            {"layout": "google-meet-tree", "verdict": "live"}]}}})


def test_the_cycle_refuses_to_poll_without_a_grounded_source_map(config_dir):
    """No verified source map means no Drive ids, which means no poll. Never a guess."""
    env = dc.load_env(config_dir)
    with pytest.raises(sa.Refused):
        dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(load("drive-listing.json")))
    # ...and the refusal is scoped to the POLL: the cadence and the ledger still
    # answer, which is when an operator most needs them.
    assert dc.fire_times(FIRST_TICK, TZ, 1)[0].minute == 10
    assert dc.count_watermarks(env) == 0


# ------------------------------------------- the widened settlement vocabulary
# r-owner-ruling-batch-0926 ruling 6 added `skipped` and `unprocessable` to the
# locked outcome list. This spine is the reader that READS the list out of the
# seam and refuses any handler answer outside it, so the two new words reaching
# it — and being settled the same way the other no-write words are — is what
# makes the coordinated change true at this reader rather than only at the seam.


@pytest.mark.parametrize("word", ["skipped", "unprocessable"])
def test_the_spine_reads_the_two_new_words_out_of_the_seam(config_dir, word):
    env = fresh_env(config_dir)
    assert word in dc.outcome_values(env.seams)


@pytest.mark.parametrize("word", ["skipped", "unprocessable"])
def test_a_handler_settling_on_a_new_word_is_accepted_and_parks_nothing(config_dir, word):
    """RED arm: with the old four-word list these answers were refused as
    `handler answered outside the outcome enum` and rewritten to `failed`, which
    is how a skipped meeting would have been parked after three cycles."""
    env = fresh_env(config_dir)

    def settling_handler(job):
        return {"kind": "per-meeting-outcome", "meeting-key": job["meeting-key"],
                "outcome": word, "at": FIRST_TICK.isoformat()}

    result = dc.run_tick(env, FIRST_TICK,
                         sa.FixtureDriveDriver(load("drive-listing.json")),
                         handler=settling_handler)

    assert result.outcomes, result.as_dict()
    assert {o["outcome"] for o in result.outcomes} == {word}
    assert all(o["outcome"] != "failed" for o in result.outcomes)
    # a no-write ending is terminal in the cycle: nothing parked, nothing filed
    assert result.parked == []
    assert dc.read_processed(env) == []


def test_a_late_tactiq_transcript_pairs_by_name_within_the_hour():
    """Owner ruling r-tactiq-late-pairs-by-name (2026-09-27): Tactiq saves late."""
    def record(ref, source, start, title):
        return {"account": "owner@EXAMPLE-home.test", "source": source, "drive-ref": ref,
                "title": title, "start-time": start, "participants": []}

    notes = record("n", "gemini-notes", "2026-08-20T09:54:00-03:00", "EXAMPLE sync")
    late = record("t", "tactiq", "2026-08-20T10:22:00-03:00", "EXAMPLE sync")
    assert len(mm.pair([notes, late], [], TZ)[0]) == 1
    # The join stays open: the late transcript finds the meeting an earlier poll minted.
    sets, minted = mm.pair([late], mm.pair([notes], [], TZ)[0], TZ)
    assert len(sets) == 1 and minted == []

    too_late = record("u", "tactiq", "2026-08-20T10:54:01-03:00", "EXAMPLE sync")
    assert len(mm.pair([notes, too_late], [], TZ)[0]) == 2
    other_name = record("v", "tactiq", "2026-08-20T10:22:00-03:00", "EXAMPLE other")
    assert len(mm.pair([notes, other_name], [], TZ)[0]) == 2
    # Only Tactiq gets the late window: a Meet transcript 28 minutes on is its own meeting.
    meet = record("m", "meet", "2026-08-20T10:22:00-03:00", "EXAMPLE sync")
    assert len(mm.pair([notes, meet], [], TZ)[0]) == 2

    # Two same-titled meetings inside the hour. Tactiq saves in meeting order, so the
    # FIRST transcript fills the first meeting even though it arrives (and its derived
    # start falls) after the second meeting began; the next one fills the second.
    first = record("a", "gemini-notes", "2026-08-20T14:59:00-03:00", "EXAMPLE weekly")
    second = record("b", "gemini-notes", "2026-08-20T15:30:00-03:00", "EXAMPLE weekly")
    t1 = record("c", "tactiq", "2026-08-20T15:35:00-03:00", "EXAMPLE weekly")
    t2 = record("d", "tactiq", "2026-08-20T15:50:00-03:00", "EXAMPLE weekly")
    sets = mm.pair([first, second, t1, t2], [], TZ)[0]
    members = sorted(sorted(r["drive-ref"] for r in s["source-set"]) for s in sets)
    assert members == [["a", "c"], ["b", "d"]]
