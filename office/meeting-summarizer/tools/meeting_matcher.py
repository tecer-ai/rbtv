#!/usr/bin/env python3
"""meeting_matcher — the workflow's ONE meeting-identity rule, with one home.

goal.md clause 16: two transcripts are the same meeting when their start times
fall on the same day and within 15 minutes, AND their titles or their participants
agree; authoritative metadata beats filename parsing; and the join stays open
across polls.

Four things that rule turns into, each of which a named case guards:

  * **Same day is the same day IN THE CONFIGURED TIMEZONE** (owner ruling
    2026-08-28: every date in this product is computed in `America/Sao_Paulo`, from
    the meeting's START time). A record's own carried UTC offset is not the
    question — two records either fall on the same local calendar date or they do
    not, and around local midnight those answers differ.

  * **Fifteen minutes is measured from the MEETING's start**, which is the
    EARLIEST start across the records already paired to it
    (`d-m3-timezone-is-config`: "a meeting's start is the earliest start across its
    paired source records"). A later transcriber joining does not move the meeting.

  * **Agreement is SLUG agreement.** Titles agree when their slugs are equal and
    non-empty; participants agree when their sets of slugged names are equal and
    non-empty. Two untitled transcripts do not "agree on a title", and raw-string
    equality would pair nothing real: the same meeting reaches Drive with two
    transcribers' spellings of one name.

  * **An authoritative handle OUTRANKS all three fields.** Where both records
    carry a `metadata-handle` of the same kind, an equal `ref` pairs them however
    the title, start and participants read, and a differing `ref` keeps them apart
    however those read. `drive-ref` is never parsed and never decides identity.

  * **A late Tactiq transcript pairs by NAME.** Tactiq saves to Drive late, so
    its start can trail the meeting's by far more than fifteen minutes (owner
    ruling r-tactiq-late-pairs-by-name, 2026-09-27). A Tactiq record pairs with a
    non-Tactiq record of the same title, same day, starting up to sixty minutes
    after it. Where several meetings qualify, the EARLIEST one that does not yet
    hold a record of that source wins: Tactiq saves in meeting order, so the
    first meeting's transcript fills the first meeting even when it arrives after
    a second same-titled meeting has started. "Closest start" would hand it to
    the second, because a late save moves the transcript's start later.

The join stays open because `pair` takes the sets earlier polls minted and returns
them grown: a Tactiq twin arriving a day after the Meet transcript joins the
meeting the Meet transcript already minted, rather than minting a second one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

EXIT_OK = 0

# goal.md clause 16's window, and the ONE place it is written down.
PAIR_WINDOW = timedelta(minutes=15)

# Owner ruling r-tactiq-late-pairs-by-name: how far AFTER a meeting's start a
# same-titled Tactiq transcript may start and still be that meeting.
LATE_WINDOW = timedelta(minutes=60)
LATE_SOURCE = "tactiq"

NON_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    """The one normalization: strip marks, lowercase, runs of other -> '-', trim."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return NON_SLUG.sub("-", stripped.lower()).strip("-")


def _start(record: dict) -> datetime:
    return datetime.fromisoformat(record["start-time"])


def meeting_start(source_set: list) -> datetime:
    """A meeting starts when its EARLIEST paired record starts."""
    return min(_start(record) for record in source_set)


def local_date(moment: datetime, tz: ZoneInfo) -> str:
    return moment.astimezone(tz).date().isoformat()


def _titles_agree(a: dict, b: dict) -> bool:
    left, right = slug(a.get("title", "")), slug(b.get("title", ""))
    return bool(left) and left == right


def _participants_agree(a: dict, b: dict) -> bool:
    left = {slug(p) for p in a.get("participants", []) if slug(p)}
    right = {slug(p) for p in b.get("participants", []) if slug(p)}
    return bool(left) and left == right


def _handle_verdict(a: dict, b: dict):
    """True/False when an authoritative handle decides; None when it does not."""
    left, right = a.get("metadata-handle"), b.get("metadata-handle")
    if not left or not right or left.get("kind") != right.get("kind"):
        return None
    return left.get("ref") == right.get("ref")


def same_meeting(record: dict, source_set: list, tz: ZoneInfo) -> bool:
    """Does `record` belong to the meeting `source_set` currently binds?"""
    for member in source_set:
        verdict = _handle_verdict(record, member)
        if verdict is not None:
            return verdict
    anchor = meeting_start(source_set)
    start = _start(record)
    if local_date(start, tz) != local_date(anchor, tz):
        return False
    if abs(start - anchor) <= PAIR_WINDOW and any(
            _titles_agree(record, member) or _participants_agree(record, member)
            for member in source_set):
        return True
    return any(_late_pair(record, member) or _late_pair(member, record) for member in source_set)


def _late_pair(late: dict, other: dict) -> bool:
    """Is `late` a Tactiq transcript of `other`'s meeting, saved late?"""
    if late.get("source") != LATE_SOURCE or other.get("source") == LATE_SOURCE:
        return False
    delay = _start(late) - _start(other)
    return timedelta(0) <= delay <= LATE_WINDOW and _titles_agree(late, other)


def mint_key(record: dict) -> str:
    """Opaque, deterministic, minted once from the meeting's first record.

    Deterministic so a replay of the same detection mints the same key; opaque
    because the seam types it as compared-for-equality and never parsed.
    """
    digest = hashlib.sha256(record["drive-ref"].encode("utf-8")).hexdigest()
    return "mtg-" + digest[:8]


def pair(records: list, existing_sets: list, tz: ZoneInfo) -> tuple[list, list]:
    """(sets, minted-keys). `existing_sets` is what keeps the join open."""
    sets = [{"meeting-key": s["meeting-key"], "source-set": list(s["source-set"])}
            for s in existing_sets]
    known = {record["drive-ref"] for s in sets for record in s["source-set"]}
    minted: list = []
    for record in sorted(records, key=_start):
        if record["drive-ref"] in known:
            continue
        known.add(record["drive-ref"])
        matches = [candidate for candidate in sets
                   if same_meeting(record, candidate["source-set"], tz)]
        if matches:
            open_ = [c for c in matches
                     if all(m["source"] != record["source"] for m in c["source-set"])]
            chosen = min(open_ or matches, key=lambda c: meeting_start(c["source-set"]))
            chosen["source-set"].append(record)
        else:
            key = mint_key(record)
            sets.append({"meeting-key": key, "source-set": [record]})
            minted.append(key)
    for entry in sets:
        entry["source-set"].sort(key=_start)
    return sets, minted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="meeting_matcher",
        description="Join transcript records into meetings (goal.md clause 16).",
    )
    parser.add_argument("--records", required=True, help="JSON list of transcript-records")
    parser.add_argument("--existing", help="JSON list of meeting-key-and-source-set, prior polls")
    parser.add_argument("--timezone", required=True, help="the timezone dates are computed in")
    args = parser.parse_args(argv)

    records = json.loads(Path(args.records).read_text(encoding="utf-8"))
    existing = json.loads(Path(args.existing).read_text(encoding="utf-8")) if args.existing else []
    sets, minted = pair(records, existing, ZoneInfo(args.timezone))
    print(json.dumps({"sets": sets, "minted": minted}, indent=2, ensure_ascii=False))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
