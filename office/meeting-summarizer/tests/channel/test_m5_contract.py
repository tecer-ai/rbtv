"""Milestone m5 (channel-protocol) acceptance suite.

One test per arm of milestones.csv row m5's done contract (the counting rules of
goal.md clauses 10 and 11). Every threshold is arithmetic over the constants of
stream.py (N, D, U, F); every payload replayed derives from the seam reference
instances. Each test was seen red during authoring via its named falsifier
(CHANNEL_SUITE_MUTATE — the mapping is recorded in stream.py) before its green.
"""

import json
import re

import stream
from stream import N, D, U, F, MEETINGS


# arm: filed-notes == N and each names its destination path
def test_filed_notes_count_and_destinations(replay):
    notes = replay.messages("filed-note")
    assert len(notes) == N
    by_key = {m["meeting-key"]: m for m in notes}
    for label in stream.FILED:
        mtg = MEETINGS[label]
        note = by_key.get(mtg["key"])
        assert note is not None, f"no filed-note for {label}"
        dest = mtg["destination"]
        assert f"{dest['repo']}:{dest['path']}" in note["text"], (
            f"filed-note for {label} does not name its destination: {note['text']}")
    # the withheld meeting gets NO filed-note (U disjoint from N)
    for label in stream.UNROUTABLE:
        assert MEETINGS[label]["key"] not in by_key


# arm: owner-need threads == D+U and each is scoped to exactly one meeting
def test_owner_need_threads_count_and_scope(replay):
    records = replay.map_records()
    threads = {r["thread"] for r in records}
    assert len(threads) == D + U
    # each thread binds exactly one meeting, and each mapped meeting one thread
    thread_to_meetings = {}
    for r in records:
        thread_to_meetings.setdefault(r["thread"], set()).add(r["meeting-key"])
    assert all(len(ks) == 1 for ks in thread_to_meetings.values()), (
        f"a thread spans meetings: {thread_to_meetings}")
    expected_keys = {MEETINGS[l]["key"] for l in stream.DOUBTED + stream.UNROUTABLE}
    assert {k for ks in thread_to_meetings.values() for k in ks} == expected_keys
    # every threaded message in the log sits on its meeting's own thread
    for m in replay.log():
        if m["thread"]:
            assert thread_to_meetings[m["thread"]] == {m["meeting-key"]}


# arm: the second doubt reuses its meeting's thread — new threads from it == 0
def test_second_doubt_reuses_thread(replay):
    label = f"doubt:{stream.SECOND_DOUBT_MEETING}:2"
    res = replay.steps[label]
    assert res["counts"]["threads-created"] == 0
    assert res["counts"]["threads-reused"] == 1
    first = replay.steps[f"doubt:{stream.SECOND_DOUBT_MEETING}:1"]
    assert res["threads"][0]["thread"] == first["threads"][0]["thread"]


# arm: the unroutable ask strictly precedes its write-gate token release;
#      token releases before an ask == 0
def test_unroutable_ask_precedes_token_release(replay):
    log = replay.log()
    releases = [m for m in log if m["type"] == "token-release"]
    assert len(releases) == U  # one gate per withheld meeting, no strays
    early = 0
    for tok in releases:
        asks = [m for m in log if m["type"] == "routing-ask"
                and m["meeting-key"] == tok["meeting-key"]
                and m["seq"] < tok["seq"]]
        if not asks:
            early += 1
    assert early == 0, f"{early} token release(s) not strictly preceded by an ask"
    # the durable token files each name the ask they followed
    for tf in replay.token_files():
        assert tf["after-seq"] < tf["release-seq"]


# arm: failure notes == F and each names its event's cause
def test_failure_notes_count_and_causes(replay):
    notes = replay.messages("failure-note")
    assert len(notes) == F
    for ev in stream.FAILURE_EVENTS:
        named = [n for n in notes if ev["cause"] in n["text"]]
        assert len(named) == 1, (
            f"failure cause {ev['cause']!r} named by {len(named)} notes")


def _grounding_account_blocks(text):
    """The grounding note -> {account: {precondition-name: field-text}}.

    An `account <name>:` header line opens a block; the two-space-indented
    `<precondition>: <verdict>[ — <detail>]` lines that follow belong to THAT
    block until any non-indented line (the next header, or `dead sources (n):`)
    closes it. Attribution is structural — no precondition is ever matched
    against the note as a whole, so a line under the wrong account is a miss.
    """
    blocks, current = {}, None
    for raw in text.splitlines():
        header = re.fullmatch(r"account (\S+):", raw)
        if header:
            current = blocks.setdefault(header.group(1), {})
            continue
        if current is not None and raw.startswith("  "):
            name, sep, field = raw[2:].partition(": ")
            assert sep, f"unparsable precondition line: {raw!r}"
            assert name not in current, f"{name!r} listed twice in one block"
            current[name] = field
            continue
        current = None
    return blocks


def _grounding_dead_roll(text):
    """The grounding note's `dead sources (n):` roll -> the set of lines in it.

    Returned as a SET so the assertion below can compare it for equality with
    the payload's own dead-sources. Membership alone is not enough: a note that
    names every real dead source AND one live source passes a membership check
    and is a false alarm about a source that works.
    """
    roll, inside = set(), False
    for raw in text.splitlines():
        if re.fullmatch(r"dead sources \(\d+\):", raw):
            inside = True
            continue
        if not inside:
            continue
        if raw.startswith("  "):
            entry = raw[2:].strip()
            if entry and entry != "none":
                roll.add(entry)
            continue
        break
    return roll


# arm: the grounding note carries the fixture findings-payload field-for-field,
#      every dead source named; a repeated invocation adds no second note
def test_grounding_note_field_for_field_and_once(replay):
    notes = replay.messages("grounding-note")
    assert len(notes) == 1
    text = notes[0]["text"]
    payload = stream.findings_payload()
    assert payload["verified-at"] in text
    # per-account binding: each block's parsed precondition fields EQUAL that
    # account's payload preconditions — names, verdicts and details together.
    blocks = _grounding_account_blocks(text)
    assert set(blocks) == set(payload["accounts"]), (
        f"note names accounts {sorted(blocks)}, payload has "
        f"{sorted(payload['accounts'])}")
    for account, body in payload["accounts"].items():
        expected = {}
        for name, pv in body["preconditions"].items():
            expected[name] = (f"{pv['verdict']} — {pv['detail']}"
                              if pv.get("detail") else pv["verdict"])
        assert blocks[account] == expected, (
            f"account {account} block is not its payload preconditions "
            f"field-for-field: {blocks[account]} != {expected}")
    # The dead-sources roll is compared for EQUALITY, not membership. A
    # membership check passes a note that names every real dead source and one
    # live source besides — a false alarm about a source that works, which is
    # the same failure as a missed dead source wearing the other sign.
    expected_dead = {f"{d['account']} / {d['layout']} — {d['why']}"
                     for d in payload["dead-sources"]}
    actual_dead = _grounding_dead_roll(text)
    assert actual_dead == expected_dead, (
        f"the dead-sources roll is not the payload's dead sources: "
        f"missing={sorted(expected_dead - actual_dead)} "
        f"invented={sorted(actual_dead - expected_dead)}")
    # And, independently of the payload's own roll: nothing whose precondition
    # verdict is `live` may be named dead. This catches a payload that
    # contradicts itself, which the equality check above would accept.
    live_named = [entry for entry in actual_dead
                  for account, body in payload["accounts"].items()
                  if entry.startswith(f"{account} / ")
                  and all(pv["verdict"] != "dead"
                          for pv in body["preconditions"].values())]
    assert not live_named, f"live sources named dead: {sorted(live_named)}"
    # posted once: the second invocation adds nothing
    first, second = replay.grounding
    assert first["already-posted"] is False
    assert second["already-posted"] is True
    assert second["counts"]["grounding-notes"] == 0


# arm: each owner reply on a mapped thread yields one schema-valid owner-answer
#      keyed to that thread's meeting; ingested answers == replies posted
def test_owner_replies_yield_keyed_schema_valid_answers(replay):
    answers = replay.ingest["owner-answers"]
    assert len(answers) == len(replay.replies_posted)
    assert replay.ingest["unmapped"] == []

    schema = json.loads((stream.workflow_root() / "seams"
                         / "owner-answer.schema.json").read_text(encoding="utf-8"))
    required = set(schema["required"])
    allowed = set(schema["properties"])
    kinds = set(schema["$defs"]["answer-kind"]["enum"])

    thread_to_key = {r["thread"]: r["meeting-key"] for r in replay.map_records()}
    expected_kind = {replay.thread_of(r["meeting"]): r["expected-kind"]
                     for r in stream.REPLIES}
    for a in answers:
        assert required <= set(a) <= allowed, f"not schema-shaped: {a}"
        assert a["kind"] in kinds, f"kind outside the schema enum: {a['kind']}"
        assert a["answer-text"], "empty answer-text"
        assert a["meeting-key"] == thread_to_key[a["thread"]], (
            "answer not keyed to its thread's meeting")
        assert a["kind"] == expected_kind[a["thread"]]


# arm: amendment one-liners attach as replies to their meeting's filed-note and
#      add zero owner-need threads; duplicate threads == 0; unconditional == 0
def test_amendments_attach_and_add_no_threads(replay):
    amendments = replay.messages("amendment")
    assert len(amendments) == 1
    amend = amendments[0]
    filed = {m["meeting-key"]: m for m in replay.messages("filed-note")}
    target = filed[MEETINGS[stream.AMENDED_MEETING]["key"]]
    assert amend["reply-to"] == target["id"], (
        f"amendment replies to {amend['reply-to']}, its filed-note is {target['id']}")
    assert amend["thread"] is None

    res = replay.steps[f"amendment:{stream.AMENDED_MEETING}"]
    assert res["counts"]["threads-created"] == 0
    assert res["channel-totals"]["owner-need-threads"] == D + U

    # duplicate threads == 0: distinct threads == mapped meetings, 1:1
    records = replay.map_records()
    threads = {r["thread"] for r in records}
    meetings = {r["meeting-key"] for r in records}
    assert len(threads) == len(meetings) == D + U
    # unconditional threads == 0: only doubted/unroutable meetings hold one
    owner_need = {MEETINGS[l]["key"] for l in stream.DOUBTED + stream.UNROUTABLE}
    assert meetings == owner_need
    for label in stream.FILED:
        if label not in stream.DOUBTED:
            assert replay.thread_of(label) is None, (
                f"clean meeting {label} got a thread")
