"""The third source and the watch list, at the detection side.

Owner rulings 2026-09-26: a meeting's inputs are the Meet transcript, the Tactiq
transcript AND the Gemini notes file; and the watch list is the sources config's
`accounts`, not whatever the verified source map happens to carry.

The listing below is shaped on the real Meet layout measured that day: the tree
folder holds one subfolder per meeting, the legacy folder sits INSIDE the tree,
names read `<title> - <YYYY/MM/DD HH:MM> <zone> - <kind>`, and a meeting someone
else organised arrives as a shortcut. Every value is EXAMPLE-prefixed.
"""

from __future__ import annotations

import copy
from datetime import timedelta

import pytest

from conftest import FIRST_TICK, filed_handler, load, watch

import detection_cycle as dc
import source_adapter as sa

ACCOUNT = "EXAMPLE-work"
EMAIL = "owner@EXAMPLE-work.test"
TREE = "drv:folder/EXAMPLE-w-tree"
LEGACY = "drv:folder/EXAMPLE-w-legacy"
MEETING_DIR = "drv:folder/EXAMPLE-w-tree/sync"

SOURCE_MAP = {
    "generated-at": "2026-08-13T18:00:00-03:00",
    "accounts": {ACCOUNT: {"sources": [
        {"layout": "legacy-meet-recordings", "verdict": "live", "folder-ref": LEGACY},
        {"layout": "google-meet-tree", "verdict": "live", "folder-ref": TREE},
        {"layout": "tactiq-autosave", "verdict": "dead"},
    ]}},
}


def item(ref: str, name: str, modified: str, mime: str = "application/vnd.google-apps.document",
         record: dict | None = None) -> dict:
    # An empty record is the live read's real answer for a Google Doc today: the
    # head carries no title and no start, so both must come from the NAME.
    return {"id": ref, "name": name, "mimeType": mime, "modifiedTime": modified,
            "record": record if record is not None else {}}


NOTES = item("drv:file/EXAMPLE-notes", "EXAMPLE sync - 2026/08/20 10:00 GMT-03:00 - Notes by Gemini",
             "2026-08-20T10:47:00-03:00")
TRANSCRIPT = item("drv:file/EXAMPLE-transcript",
                  "EXAMPLE sync - 2026/08/20 10:00 GMT-03:00 - Transcript 2",
                  "2026-08-20T10:44:00-03:00")
RECORDING = item("drv:file/EXAMPLE-recording",
                 "EXAMPLE sync - 2026/08/20 10:00 GMT-03:00 - Recording",
                 "2026-08-20T10:41:00-03:00", mime="video/mp4")
SHORTCUT = item("drv:file/EXAMPLE-shortcut",
                "EXAMPLE other - 2026/08/20 09:00 GMT-03:00 - Notes by Gemini (English)",
                "2026-08-20T09:40:00-03:00", mime="application/vnd.google-apps.shortcut")
# A TRANSCRIPT of a meeting whose title carries the notes words. Only reading the
# kind after the date stamp tells it apart; a whole-name match calls it notes.
TITLED_AFTER_NOTES = item(
    "drv:file/EXAMPLE-titled", "Notes by Gemini rollout - 2026/08/20 11:00 GMT-03:00 - Transcript",
    "2026-08-20T11:40:00-03:00")


def listing(tree_items: list, legacy_items: list | None = None) -> dict:
    return {
        "account-emails": {ACCOUNT: EMAIL},
        "accounts": {ACCOUNT: {
            # The legacy folder is a CHILD of the tree, exactly as measured live.
            "subfolders": {TREE: [MEETING_DIR, LEGACY]},
            "folders": {TREE: [], MEETING_DIR: list(tree_items), LEGACY: list(legacy_items or [])},
        }},
    }


@pytest.fixture
def env(config_dir):
    watch(config_dir, [ACCOUNT])
    return dc.load_env(config_dir, source_map=copy.deepcopy(SOURCE_MAP),
                       account_emails={ACCOUNT: EMAIL})


def sources_of(result) -> dict:
    return {record["drive-ref"]: record["source"] for record in result.records}


# ------------------------------------------------------------ classification


def test_the_sweep_classifies_every_item_and_reads_only_sources(env):
    driver = sa.FixtureDriveDriver(listing([NOTES, TRANSCRIPT, RECORDING, SHORTCUT]))
    result = dc.run_tick(env, FIRST_TICK, driver)

    assert sources_of(result) == {NOTES["id"]: "gemini-notes", TRANSCRIPT["id"]: "meet"}
    assert sorted(result.unclassified) == sorted([RECORDING["id"], SHORTCUT["id"]])
    # Never parsed as a transcript by default: an unclassified item is never READ.
    assert driver.reads[RECORDING["id"]] == 0 and driver.reads[SHORTCUT["id"]] == 0
    assert result.failure_events == [] and result.watermark_advanced


def test_the_kind_is_read_after_the_date_stamp_never_from_the_title(env):
    result = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(listing([TITLED_AFTER_NOTES])))
    assert sources_of(result) == {TITLED_AFTER_NOTES["id"]: "meet"}


def test_the_summarize_config_must_declare_the_notes_tokens(config_dir):
    import json

    path = config_dir / "summarize.json"
    kinds = json.loads(path.read_text(encoding="utf-8"))
    del kinds["artifact-kinds"]["meeting-notes"]
    path.write_text(json.dumps(kinds), encoding="utf-8")
    watch(config_dir, [ACCOUNT])
    env = dc.load_env(config_dir, source_map=copy.deepcopy(SOURCE_MAP),
                      account_emails={ACCOUNT: EMAIL})
    with pytest.raises(sa.Refused, match="meeting-notes"):
        dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(listing([NOTES])))


# ------------------------------------------------------------ the tree layout


def test_the_tree_layout_is_swept_one_level_down_and_nothing_twice(env):
    driver = sa.FixtureDriveDriver(listing([TRANSCRIPT], legacy_items=[NOTES]))
    result = dc.run_tick(env, FIRST_TICK, driver)

    assert sources_of(result) == {TRANSCRIPT["id"]: "meet", NOTES["id"]: "gemini-notes"}
    # The legacy folder is a child of the tree AND a watched source: swept once.
    assert driver.reads[NOTES["id"]] == 1
    assert driver.listing_returns[NOTES["id"]] == 1


# ------------------------------------------------------------ names carry the meeting


def test_a_slash_dated_name_gives_the_start_and_the_title(env):
    result = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(listing([NOTES])))
    (record,) = result.records
    assert record["start-time"] == "2026-08-20T10:00:00-03:00"
    assert record["title"] == "EXAMPLE sync"


def test_notes_and_transcript_of_one_meeting_pair_from_their_names_alone(env):
    result = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(listing([NOTES, TRANSCRIPT])))
    assert len(result.meetings) == 1
    assert {r["source"] for r in result.meetings[0]["source-set"]} == {"meet", "gemini-notes"}


# ------------------------------------------------------------ dispatch


def test_a_notes_only_meeting_waits_and_its_transcript_brings_it_in(env):
    calls = []

    def handler(job):
        calls.append(job)
        return filed_handler()(job)

    first = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(listing([NOTES])), handler=handler)
    assert calls == [], "a Gemini notes file alone dispatched a summary (clause 19)"
    # No job is EMITTED either: the runtime seat forwards every emitted job.
    assert first.jobs == []
    assert first.awaiting_transcript == first.minted and len(first.minted) == 1
    assert first.outcomes == [] and first.parked == []
    assert first.watermark_advanced

    late = copy.deepcopy(TRANSCRIPT)
    late["modifiedTime"] = "2026-08-20T12:40:00-03:00"
    second = dc.run_tick(env, FIRST_TICK + timedelta(hours=1),
                         sa.FixtureDriveDriver(listing([NOTES, late])), handler=handler)
    assert second.minted == [], "the transcript minted a second meeting instead of joining"
    assert second.awaiting_transcript == []
    (job,) = calls
    assert job["meeting-key"] == first.minted[0] and job["disposition"] == "new"
    assert {r["source"] for r in job["source-set"]} == {"meet", "gemini-notes"}


def test_late_notes_amend_the_filed_meeting_in_place(env):
    first = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(listing([TRANSCRIPT])),
                        handler=filed_handler())
    assert [o["outcome"] for o in first.outcomes] == ["filed"]

    late = copy.deepcopy(NOTES)
    late["modifiedTime"] = "2026-08-20T12:40:00-03:00"
    second = dc.run_tick(env, FIRST_TICK + timedelta(hours=1),
                         sa.FixtureDriveDriver(listing([TRANSCRIPT, late])), handler=filed_handler())
    (job,) = [j for j in second.jobs if j["disposition"] != "already-done"]
    assert job["disposition"] == "amend" and job["amend"]["coverage"] == ["meet"]
    assert [o["outcome"] for o in second.outcomes] == ["amended"]


# ------------------------------------------------------------ the watch list


def test_the_watch_list_is_the_sources_config_not_the_source_map(config_dir):
    fixture = load("drive-listing.json")
    watch(config_dir, ["EXAMPLE-work"])
    env = dc.load_env(config_dir, source_map=load("source-map.json"),
                      account_emails=fixture["account-emails"])
    driver = sa.FixtureDriveDriver(fixture)
    result = dc.run_tick(env, FIRST_TICK, driver)

    assert {call["account"] for call in driver.calls} == {"EXAMPLE-work"}
    assert {record["account"] for record in result.records} == {"owner@EXAMPLE-work.test"}
    assert list(result.covered) == ["owner@EXAMPLE-work.test"]


def test_a_watched_account_the_source_map_never_verified_is_refused(config_dir):
    fixture = load("drive-listing.json")
    watch(config_dir, ["EXAMPLE-work", "EXAMPLE-unverified"])
    env = dc.load_env(config_dir, source_map=load("source-map.json"),
                      account_emails=fixture["account-emails"])
    with pytest.raises(sa.Refused, match="EXAMPLE-unverified"):
        dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(fixture))


# ------------------------------------------------------------ the live driver's cap


FAKE_GTOOLS = """import json, sys
args = sys.argv[1:]
with open(sys.argv[0] + ".calls", "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
cap = int(args[args.index("--max-results") + 1])
count = cap if "FULL" in args[args.index("-q") + 1] else 2
print(json.dumps([{"id": f"drv:file/EXAMPLE-{n}", "name": "x", "mimeType": "text/plain"}
                  for n in range(count)]))
"""


def test_a_live_listing_that_fills_its_cap_is_a_failure_never_a_silent_cut(tmp_path):
    gtools = tmp_path / "gtools.py"
    gtools.write_text(FAKE_GTOOLS, encoding="utf-8")
    driver = sa.GtoolsDriveDriver(gtools)
    since, until = FIRST_TICK - timedelta(hours=1), FIRST_TICK

    assert len(driver.list_folder(ACCOUNT, "drv:folder/EXAMPLE-some", since, until)) == 2
    with pytest.raises(sa.DriverError, match="cap"):
        driver.list_folder(ACCOUNT, "drv:folder/EXAMPLE-FULL", since, until)
    with pytest.raises(sa.DriverError, match="cap"):
        driver.list_subfolders(ACCOUNT, "drv:folder/EXAMPLE-FULL")
    calls = (tmp_path / "gtools.py.calls").read_text(encoding="utf-8").splitlines()
    assert all("--max-results" in call for call in calls) and len(calls) == 3


def test_notes_only_meetings_are_admitted_from_the_configured_date_only():
    # Clause 19 as amended 2026-09-27: before `notes-only-from` a notes-only
    # meeting keeps waiting (ruling d-backfill-29-notes-only-meetings).
    tz = sa.ZoneInfo("America/Sao_Paulo")
    entry = {"source-set": [{"source": "gemini-notes", "start-time": "2026-09-27T00:30:00-03:00"}]}
    assert dc.notes_admitted(entry, dc.date(2026, 9, 27), tz)
    assert not dc.notes_admitted(entry, dc.date(2026, 9, 28), tz)
    assert not dc.notes_admitted(entry, None, tz)


def test_a_tactiq_head_gives_the_title_and_a_start_derived_from_the_save():
    # Shaped on the first real Tactiq save (2026-09-27): no start line, a
    # "<date> | <title>" head, offsets relative to the transcript's start.
    text = ("Transcript delivered by Tactiq.io\n\n27 Sept 2026 | EXAMPLE-Alpha sync\n"
            "Attendees: EXAMPLE-Nara, EXAMPLE-Rui\n\nTranscript\n"
            "00:00 EXAMPLE-Nara: bom dia\n1:02:30 EXAMPLE-Rui: fechado\n")
    saved = sa._parse("2026-09-27T15:02:30+00:00")
    head = sa.parse_transcript_head(text, saved)
    assert head["title"] == "EXAMPLE-Alpha sync"
    assert head["participants"] == ["EXAMPLE-Nara", "EXAMPLE-Rui"]
    assert sa._parse(head["start-time"]) == sa._parse("2026-09-27T14:00:00+00:00")
