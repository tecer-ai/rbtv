#!/usr/bin/env python3
"""source_adapter — ONE Drive poll, every watched account, all three sources.

What this module is for: turning a `verified-source-map` plus a `poll-window`
into the `records-in-window` answer the detection cycle joins into meetings. It
is the only place in the product that talks to Drive, and the only place the
hard processing floor is enforced.

Three properties are the whole point, and each is guarded by a named test case:

  * **A watched folder is reached BY DRIVE ID, never by display name.** The only
    folder handle this module accepts is the `folder-ref` the verified source map
    carries. There is no name lookup anywhere below, which is what makes clause 26
    hold: a folder the owner renames keeps being watched, and a folder that stops
    resolving is a named failure rather than a silent empty.

  * **The floor is on the READ.** goal.md clause 15 fixes 2026-08-13 and says
    nothing older is ever read — so a pre-floor item must not merely produce no
    output, it must never be fetched. The sweep therefore decides from the LISTING
    alone whether an item may be read, and an item dated before the floor is
    dropped before `read_record` is ever called. The floor value itself is read out
    of the `window-contract` seam, never typed here.

  * **An item is CLASSIFIED before it is read.** A Meet folder holds Meet
    transcripts, "Notes by Gemini" files, recordings and chat logs side by side;
    only the first two are sources, and they are different sources. The kind is
    decided from the item's NAME against the owner-configured tokens, and an item
    no token claims is never read — it is listed out of band as `unclassified`,
    never parsed as a transcript by default.

  * **A failure is an EVENT, never an exception that ends the poll.** An account
    whose sweep cannot complete comes back `covered: false` with a failure event
    naming the cause; the other account's records still come back. The cycle needs
    that distinction: a poll that did not cover an account must not advance the
    watermark.

The account value written into every record is the account's EMAIL address, not
the internal gtools account key — the route table m3 built is keyed on the email
(`d-m3-declared-source`, and the m3 report's own note that "m5's detection cycle
must populate `account` with the account email").
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from artifact_reader import utterances  # noqa: E402
from verify_access import seam_schema, workspace_root  # noqa: E402

EXIT_OK = 0
EXIT_REFUSED = 2

# Which seam entry carries which shape. Entry IDS, resolved through
# `seams/index.csv` at run time — never a schema filename typed here.
WINDOW_ENTRY = "window-contract"
SOURCE_MAP_ENTRY = "verified-source-map"
RECORD_ENTRY = "transcript-record"

FOLDER_MIME = "application/vnd.google-apps.folder"
# A Drive shortcut is a pointer to a file another account owns (a meeting someone
# else organised). It has no content of its own, so reading it fails — and a read
# failure holds the watermark — so it is never classified as a source.
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"

# The source values, as the seam set declares them (`transcript-record`
# $defs/source). The two transcript sources carry spoken words; the notes source
# is a model-written summary and is supplementary input only (goal.md clause 19,
# owner ruling r-meet-source-a-plus-gemini-notes-third-source).
TRANSCRIPT_SOURCES = ("meet", "tactiq")
NOTES_SOURCE = "gemini-notes"

# The layouts of the source map (`verified-source-map` $defs/layout) and what each
# yields. Everything in the Tactiq auto-save folder is a Tactiq transcript; a Meet
# folder yields two sources told apart by NAME (see classify()). The tree layout
# keeps each meeting, or recurring series, in its own subfolder.
TACTIQ_LAYOUT = "tactiq-autosave"
TREE_LAYOUTS = frozenset({"google-meet-tree"})

# The ONE home of the file-name words that tell notes from transcripts: the
# `summarize` config's `artifact-kinds`, which the artifact reader also uses. Which
# artifact kind's words claim an item for which Meet-folder source:
SUMMARIZE_FILE = "summarize.json"
NAME_TOKEN_KINDS = {NOTES_SOURCE: "meeting-notes", "meet": "transcript"}

# The most items one Drive search may return. A listing that comes back exactly
# this full cannot prove it saw everything, so it is a failure, never a silent cut.
SEARCH_CAP = 1000

# A date, and optionally a time, as a Meet or transcript filename carries it
# ("2026/09/16 14:28" in Meet's own names). Used to decide whether an item may be
# read at all and to split a Meet name into title and kind; the authoritative
# start time comes from the record itself once reading is permitted.
FILENAME_STAMP = re.compile(
    r"(?P<date>\d{4}[-/]\d{2}[-/]\d{2})(?:[ T_](?P<hour>\d{1,2})[:._-](?P<minute>\d{2}))?"
)

# Tactiq's own head line: "<day> <month> <year> | <meeting title>" (verified on the
# first real Tactiq save, 2026-09-27: "27 Sept 2026 | Teste ignite"). Tactiq writes
# no start time and no date stamp in the file name — see parse_transcript_head().
TACTIQ_HEAD = re.compile(r"^\s*\d{1,2} \S+ \d{4} \| (?P<title>.+?)\s*$")

# Absolute paths never reach a failure event: a token store or a host can ride
# inside a tool's error text, and a failure event is written down.
ABSPATH = re.compile(r"(?<![\w-])/[^\s'\"]*")


class Refused(Exception):
    """The adapter could not run at all. Never a sweep answer."""


class DriverError(RuntimeError):
    """One outside call could not be completed. Becomes a failure EVENT."""


class AccountUnreachable(DriverError):
    """The ACCOUNT could not be reached. Its remaining sources are not attempted.

    One outage is one failure note, not one per folder the outage happened to
    hide — clause 12 asks for a named cause, and the same cause repeated per
    folder buries it.
    """


class FolderUnresolved(DriverError):
    """A watched folder no longer resolves to its Drive id — clause 26's own case.

    Distinct from an account outage because the answer is different: the account
    is fine, one folder the owner moved, deleted or lost access to is not. It gets
    its own note, and the account's other sources are still swept.
    """


def _refuse(what: str, fix: str) -> None:
    raise Refused(f"{what}\n  fix: {fix}")


def scrub(text: str) -> str:
    return ABSPATH.sub("<path>", (text or "").strip())


# --------------------------------------------------------------------------
# the seam set — the vocabulary and the constants this module speaks
# --------------------------------------------------------------------------


def seams_dir(start: Path | None = None) -> Path:
    return (start or TOOL_DIR.parent) / "seams"


def seam_instances(seams: Path, entry_id: str) -> list[dict]:
    """The reference instances one seam row names, resolved THROUGH index.csv."""
    index = seams / "index.csv"
    if not index.is_file():
        _refuse(f"no seam index at {index}", "point at the seam set this workflow was built against")
    with index.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("entry-id") == entry_id:
                files = [p for p in (row.get("instance-files") or "").split(";") if p.strip()]
                out = []
                for name in files:
                    path = seams / name.strip()
                    if not path.is_file():
                        _refuse(f"seam entry {entry_id} names a missing instance: {name}",
                                "re-validate the seam set with validate_seams.py")
                    out.append(json.loads(path.read_text(encoding="utf-8")))
                return out
    _refuse(f"seam entry {entry_id} is absent from the seam index",
            "re-validate the seam set with validate_seams.py")
    return []


def floor_date(seams: Path) -> str:
    """The hard processing floor, READ OUT OF the window-contract seam.

    goal.md clause 15 ratified the value; the seam pins it as a `const`. Reading
    it here rather than writing it down is what keeps the two from drifting.
    """
    schema = seam_schema(seams, WINDOW_ENTRY)
    value = schema.get("properties", {}).get("floor", {}).get("const")
    if not isinstance(value, str):
        _refuse("the window-contract seam pins no floor const",
                "re-validate the seam set with validate_seams.py")
    return value


def floor_start(seams: Path, tz: ZoneInfo) -> datetime:
    """The instant the floor opens: local midnight of the floor date.

    Owner ruling 2026-08-28 — every date in this product is computed in the
    configured timezone, from the meeting's START time. The floor is a DATE, so
    its instant is that date's local midnight and nothing else.
    """
    return datetime.fromisoformat(floor_date(seams) + "T00:00:00").replace(tzinfo=tz)


# --------------------------------------------------------------------------
# the window
# --------------------------------------------------------------------------


def poll_window(seams: Path, until: datetime, since: datetime | None = None) -> dict:
    """The `poll-window` shape the cycle hands this adapter."""
    window = {"kind": "poll-window", "floor": floor_date(seams), "until": _stamp(until)}
    if since is not None:
        window["since"] = _stamp(since)
    return window


def _stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)


# --------------------------------------------------------------------------
# drivers — the one place an outside call is made
# --------------------------------------------------------------------------


class GtoolsDriveDriver:
    """The live driver: Drive, reached through the gtools CLI.

    `list_folder` is a Drive query over a PARENT ID with a server-side time bound.
    Two consequences the contract depends on: a folder is never named, and an item
    outside the window never crosses the wire at all.
    """

    def __init__(self, gtools: Path, timeout: int = 180) -> None:
        self.gtools = Path(gtools)
        self.timeout = timeout
        self.calls: list[dict] = []

    def _search(self, account: str, query: str) -> list:
        args = ["drive", "search", "-q", query, "--max-results", str(SEARCH_CAP)]
        items = self._run(account, "drive.search", args)
        if len(items) >= SEARCH_CAP:
            raise DriverError(f"drive.search: the listing hit its {SEARCH_CAP}-item cap "
                              "and cannot prove it is complete")
        return items

    def _run(self, account: str, operation: str, args: list[str]):
        cmd = [sys.executable, str(self.gtools), *args, "--account", account, "--json"]
        self.calls.append({"account": account, "operation": operation})
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            raise DriverError(f"{operation}: timed out")
        if proc.returncode != 0:
            lines = [ln.strip() for ln in (proc.stderr or "").splitlines() if ln.strip()]
            reason = scrub(lines[-1]) if lines else "failed"
            # Which of the two faults this is decides whether the account's other
            # sources are still swept, so it is classified rather than lumped.
            fault = FolderUnresolved if _reads_as_missing(reason) else AccountUnreachable
            raise fault(f"{operation}: {reason}")
        try:
            return json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            raise DriverError(f"{operation}: unparseable JSON on stdout")

    def list_folder(self, account: str, folder_ref: str, since: datetime, until: datetime):
        query = (
            f"'{folder_ref}' in parents and trashed = false"
            f" and modifiedTime >= '{since.astimezone().isoformat(timespec='seconds')}'"
            f" and modifiedTime <= '{until.astimezone().isoformat(timespec='seconds')}'"
        )
        return [item for item in self._search(account, query)
                if item.get("mimeType") != FOLDER_MIME]

    def list_subfolders(self, account: str, folder_ref: str) -> list[str]:
        """The Drive ids of a folder's child folders — no time bound, see list_source()."""
        query = f"'{folder_ref}' in parents and trashed = false and mimeType = '{FOLDER_MIME}'"
        return [item["id"] for item in self._search(account, query) if item.get("id")]

    def read_record(self, account: str, item: dict) -> dict:
        """THE READ — the operation clause 15 forbids against a pre-floor item."""
        file_id = (item.get("id") or "").strip()
        if not file_id:
            raise DriverError("drive.download: a listed item carries no Drive id")
        with tempfile.TemporaryDirectory() as scratch:
            downloaded = self.download_text(account, file_id, Path(scratch) / "transcript.txt")
        saved = item.get("createdTime")
        return parse_transcript_head(downloaded["text"], _parse(saved) if saved else None)

    def download_text(self, account: str, file_id: str, output: Path) -> dict:
        """Download one Drive artifact as text, returning its path and source name."""
        downloaded = self._run(
            account, "drive.download",
            ["drive", "download", "--file-id", file_id, "--output", str(output),
             "--format", "txt"])
        if not isinstance(downloaded, dict) or not downloaded.get("path"):
            raise DriverError("drive.download: no output path returned")
        if not Path(downloaded["path"]).is_file():
            raise DriverError("drive.download: the reported output file does not exist")
        if not str(downloaded.get("mimeType", "")).startswith("text/"):
            raise DriverError("drive.download: the artifact is not text")
        try:
            downloaded["text"] = Path(downloaded["path"]).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise DriverError("drive.download: the artifact is not UTF-8 text")
        return downloaded


class FixtureDriveDriver:
    """The offline driver every probe runs against. Same surface, no network.

    It COUNTS, per Drive ref, how many listings returned the item and how many
    times it was read. Those two counters are what makes the floor arm provable:
    "nothing was written" cannot tell a skipped item from a read-then-discarded
    one, and a read count can.
    """

    def __init__(self, data: dict) -> None:
        self.data = data
        self.listing_returns: Counter = Counter()
        self.reads: Counter = Counter()
        self.calls: list[dict] = []

    def _bucket(self, account: str, operation: str) -> dict:
        bucket = self.data.get("accounts", {}).get(account)
        if bucket is None:
            raise AccountUnreachable(f"{operation}: no such account in fixture")
        if bucket.get("fault"):
            raise AccountUnreachable(f"{operation}: {bucket['fault']}")
        return bucket

    def list_folder(self, account: str, folder_ref: str, since: datetime, until: datetime):
        bucket = self._bucket(account, "drive.search")
        self.calls.append({"account": account, "operation": "drive.search", "folder": folder_ref})
        folders = bucket.get("folders", {})
        if folder_ref not in folders:
            raise FolderUnresolved(f"drive.search: folder {folder_ref} no longer resolves")
        out = []
        for item in folders[folder_ref]:
            # The server-side time bound of the live query, honoured here so the
            # probe measures the same thing the live poll would.
            stamp = _parse(item["modifiedTime"])
            if stamp < since or stamp > until:
                continue
            self.listing_returns[item["id"]] += 1
            out.append(dict(item))
        return out

    def list_subfolders(self, account: str, folder_ref: str) -> list[str]:
        bucket = self._bucket(account, "drive.search")
        self.calls.append({"account": account, "operation": "drive.search",
                           "subfolders-of": folder_ref})
        return list(bucket.get("subfolders", {}).get(folder_ref, []))

    def read_record(self, account: str, item: dict) -> dict:
        self._bucket(account, "drive.download")
        self.calls.append({"account": account, "operation": "drive.download", "file": item["id"]})
        self.reads[item["id"]] += 1
        body = item.get("record")
        if body is None:
            raise DriverError(f"drive.download: fixture item {item['id']} carries no record")
        return dict(body)


def _reads_as_missing(reason: str) -> bool:
    """Does this call failure read as "that folder is gone" rather than "you are out"?

    Classified from the Google CLI's own error text, which is the only signal a
    failed call carries. UNVERIFIED against live Drive: the OAuth grant has been
    down since before this module was written, so the fixture driver is the only
    place the two faults have actually been told apart. Filed in the goal's
    issues.md for the first live run to confirm.
    """
    lowered = (reason or "").lower()
    return any(token in lowered for token in ("notfound", "not found", "404"))


def parse_transcript_head(text: str, saved_at: datetime | None = None) -> dict:
    """Title, start and participants as a downloaded transcript's head carries them.

    Deliberately small: the authoritative fields are whatever the source wrote at
    the top of the file. Summarization is m6's business and reads the body itself.

    A head that states no start (Tactiq's) gets one DERIVED from `saved_at`, the
    file's creation time: the transcript is saved when the meeting ends, and its
    last utterance offset is how long it ran. Without this the start would be the
    end, and a meeting longer than the pairing window would never pair.
    """
    head: dict = {"title": "", "participants": []}
    for line in (text or "").splitlines()[:40]:
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        if key in ("title", "meeting", "meeting title"):
            head.setdefault("_title", value)
        elif key in ("start", "start time", "started"):
            head.setdefault("_start", value)
        elif key in ("participants", "attendees"):
            head["participants"] = [p.strip() for p in value.split(",") if p.strip()]
        elif key in ("conference record", "conference-record"):
            head["metadata-handle"] = {"kind": "conference-record", "ref": value}
    if "_title" not in head:
        for line in (text or "").splitlines()[:40]:
            match = TACTIQ_HEAD.match(line)
            if match:
                head["_title"] = match.group("title")
                break
    if "_title" in head:
        head["title"] = head.pop("_title")
    if "_start" in head:
        head["start-time"] = head.pop("_start")
    elif saved_at is not None:
        spoken = utterances(text)
        if spoken:
            head["start-time"] = _stamp(saved_at - timedelta(seconds=_offset_seconds(spoken[-1]["at"])))
    return head


def _offset_seconds(offset: str) -> int:
    """An utterance offset ("mm:ss" or "h:mm:ss") in seconds."""
    seconds = 0
    for part in offset.split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


# --------------------------------------------------------------------------
# the sweep
# --------------------------------------------------------------------------


def live_sources(source_map: dict) -> list[tuple[str, str, str]]:
    """(account key, layout, folder-ref) for every LIVE source, by id only.

    A dead source is skipped — it is recorded dead, never absent, so skipping it
    here loses nothing. A live source carrying no `folder-ref` is a refusal: the
    watch list is keyed by Drive id, and a source with no id cannot be watched.
    """
    out = []
    for account, entry in sorted((source_map.get("accounts") or {}).items()):
        for source in entry.get("sources", []):
            if source.get("verdict") != "live":
                continue
            ref = (source.get("folder-ref") or "").strip()
            if not ref:
                _refuse(f"source map: live source {source.get('layout')} on {account} carries no folder-ref",
                        "re-run verify-access; a live source is pinned by Drive id or it is not live")
            out.append((account, source["layout"], ref))
    return out


def name_tokens(config_dir: Path) -> dict:
    """Meet-folder source -> the name tokens that claim an item for it.

    Read from the `summarize` config's `artifact-kinds` — the same words the
    artifact reader tells notes from transcripts by, so the two never drift
    (they did: the Portuguese Gemini name was in one list and not the other).
    Both lists are required: a missing one would leave every file of that kind
    unclassified, which is a silent loss dressed as a quiet poll.
    """
    path = Path(config_dir) / SUMMARIZE_FILE
    if not path.is_file():
        _refuse(f"no {SUMMARIZE_FILE} under the config-module home",
                "declare 'artifact-kinds' there: the file-name words of notes and transcripts")
    kinds = json.loads(path.read_text(encoding="utf-8")).get("artifact-kinds") or {}
    out = {}
    for source, kind in NAME_TOKEN_KINDS.items():
        tokens = [str(t) for t in (kinds.get(kind, {}).get("name-contains") or []) if str(t).strip()]
        if not tokens:
            _refuse(f"{SUMMARIZE_FILE} declares no artifact-kinds.{kind}.name-contains",
                    f"list the words a {source} file's name carries there")
        out[source] = tokens
    return out


def classify(layout: str, item: dict, tokens: dict) -> str | None:
    """Which source this listed item is, from the LISTING alone — or None.

    Meet names every artifact `<title> - <date> <time> <zone> - <kind>`, so the
    tokens are matched against the part AFTER the date stamp: a meeting titled
    after a transcript cannot pass its notes off as one. Notes tokens are tried
    first. None means the item is not a source (a recording, a chat log, a
    shortcut) and is never read.
    """
    if item.get("mimeType") == SHORTCUT_MIME:
        return None
    if layout == TACTIQ_LAYOUT:
        return "tactiq"
    name = item.get("name") or ""
    stamp = FILENAME_STAMP.search(name)
    tail = (name[stamp.end():] if stamp else name).casefold()
    for source in (NOTES_SOURCE, "meet"):
        if any(token.casefold() in tail for token in tokens[source]):
            return source
    return None


def list_source(driver, account: str, layout: str, folder_ref: str,
                since: datetime, until: datetime, watched: set) -> list:
    """Every item one live source holds inside the window.

    A tree layout keeps its items one level down, one subfolder per meeting or
    recurring series. Subfolders are listed WITHOUT a time bound: Drive does not
    move a folder's modifiedTime when a file lands in it (measured 2026-09-26 — a
    series folder stamped 09-08 held notes dated 09-22). A subfolder that is itself
    a watched source is left to that source, so nothing is swept twice.
    """
    refs = [folder_ref]
    if layout in TREE_LAYOUTS:
        refs += [ref for ref in driver.list_subfolders(account, folder_ref) if ref not in watched]
    items = []
    for ref in refs:
        items += driver.list_folder(account, ref, since, until)
    return items


def sweep(
    driver,
    source_map: dict,
    window: dict,
    account_emails: dict,
    tz: ZoneInfo,
    seams: Path | None = None,
    *,
    tokens: dict,
) -> dict:
    """ONE poll: every watched account, every live source, into `records-in-window`.

    Returns the seam's `records-in-window` shape plus three out-of-band keys the
    cycle needs and the seam does not carry (`failure-events`, `refused-pre-floor`,
    `unclassified`), stripped by `records_in_window()` before anything validates.
    """
    seams = seams or seams_dir()
    opens_at = floor_start(seams, tz)
    since = max(_parse(window["since"]), opens_at) if window.get("since") else opens_at
    until = _parse(window["until"])

    accounts: dict = {}
    events: list[dict] = []
    refused: list[str] = []
    unclassified: list[str] = []
    unreachable: set = set()
    sources = live_sources(source_map)
    watched = {ref for _, _, ref in sources}
    for account, layout, folder_ref in sources:
        email = account_emails.get(account)
        if not email:
            _refuse(f"no address configured for account key {account!r}",
                    "declare every polled account's address in the accounts source")
        slot = accounts.setdefault(email, {"covered": True, "records": []})
        if account in unreachable:
            # The account is already down and already named. Asking again would
            # bury the one cause under a note per folder.
            continue
        try:
            items = list_source(driver, account, layout, folder_ref, since, until, watched)
        except AccountUnreachable as exc:
            unreachable.add(account)
            slot["covered"] = False
            events.append(failure_event(str(exc), "account", until, account=email))
            continue
        except DriverError as exc:
            slot["covered"] = False
            events.append(failure_event(str(exc), "account", until, account=email))
            continue
        for item in items:
            ref = item.get("id") or ""
            source = classify(layout, item, tokens)
            if source is None:
                unclassified.append(ref)
                continue
            # THE FLOOR GATE. Decided from the LISTING alone, before any read.
            listed_start = listing_start(item, tz)
            if listed_start is None or listed_start < opens_at:
                refused.append(ref)
                continue
            try:
                detail = driver.read_record(account, item)
            except DriverError as exc:
                slot["covered"] = False
                events.append(failure_event(str(exc), "account", until, account=email))
                continue
            record = build_record(email, source, item, detail, listed_start)
            if _parse(record["start-time"]) < opens_at:
                # The listing said in-window and the authoritative metadata says
                # otherwise. The item is dropped and the disagreement is named —
                # never silently kept, never silently lost.
                events.append(failure_event(
                    f"item {ref} listed after the floor but carries a pre-floor start time",
                    "poll", until))
                continue
            slot["records"].append(record)

    for email in account_emails.values():
        accounts.setdefault(email, {"covered": True, "records": []})

    return {
        "kind": "records-in-window",
        "floor": floor_date(seams),
        "window": {"start": _stamp(since), "end": _stamp(until)},
        "accounts": accounts,
        "failure-events": events,
        "refused-pre-floor": refused,
        "unclassified": unclassified,
    }


def records_in_window(swept: dict) -> dict:
    """The swept answer as the SEAM declares it — the out-of-band keys removed."""
    return {k: v for k, v in swept.items() if k in ("kind", "floor", "window", "accounts")}


def listing_start(item: dict, tz: ZoneInfo) -> datetime | None:
    """The earliest start this item could have, from its LISTING alone.

    Filename first — a transcript filename carries the meeting's own date, which
    the file's Drive timestamps do not. `createdTime` is the fallback. Returning
    the earlier of what is known is deliberate: the floor gate must never let an
    item through on an optimistic reading.
    """
    candidates = []
    match = FILENAME_STAMP.search(item.get("name") or "")
    if match:
        hour = int(match.group("hour") or 0)
        minute = int(match.group("minute") or 0)
        candidates.append(
            datetime.fromisoformat(match.group("date").replace("/", "-"))
            .replace(hour=hour, minute=minute, tzinfo=tz)
        )
    for key in ("createdTime", "modifiedTime"):
        if item.get(key):
            candidates.append(_parse(item[key]).astimezone(tz))
    return min(candidates) if candidates else None


def filename_title(name: str) -> str:
    """The meeting title a file name carries: everything before its date stamp.

    The fallback when the file's own head names no title. It is what lets a Meet
    transcript and the Gemini notes of the same meeting agree on a title — both
    names open with it — and without it neither ever pairs.
    """
    match = FILENAME_STAMP.search(name or "")
    return name[:match.start()].strip(" -(") if match else ""


def build_record(email: str, source: str, item: dict, detail: dict, listed_start: datetime) -> dict:
    """One `transcript-record`. Authoritative metadata beats filename parsing."""
    start = detail.get("start-time") or _stamp(listed_start)
    record = {
        "account": email,
        "source": source,
        "drive-ref": item["id"],
        "title": detail.get("title") or filename_title(item.get("name") or ""),
        "start-time": _stamp(_parse(start)),
        "participants": list(detail.get("participants") or []),
    }
    if detail.get("metadata-handle"):
        record["metadata-handle"] = dict(detail["metadata-handle"])
    return record


def failure_event(cause: str, scope: str, at: datetime, account: str | None = None,
                  meeting_key: str | None = None) -> dict:
    event = {"kind": "failure-event", "cause": scrub(cause), "scope": scope, "at": _stamp(at)}
    if account:
        event["account"] = account
    if meeting_key:
        event["meeting-key"] = meeting_key
    return event


# --------------------------------------------------------------------------
# accounts — owner configuration, read at run time
# --------------------------------------------------------------------------


def account_emails(gtools_path: Path, keys: list[str]) -> dict:
    """Account key -> address, read from the Google CLI's own account map.

    Addresses are NAMES, never credential values, and they live in exactly one
    place already. Copying them into this product's configuration would mint a
    second source for one fact and let the two drift.
    """
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment defect
        _refuse(f"the pyyaml library is not importable: {exc}", "python3 -m pip install pyyaml")
    config = Path(gtools_path).parent / "config.yaml"
    if not config.is_file():
        _refuse(f"no account map beside the Google CLI at {config.name}",
                "point --gtools at the Google CLI whose config.yaml carries the account map")
    declared = (yaml.safe_load(config.read_text(encoding="utf-8")) or {}).get("accounts") or {}
    out = {}
    for key in keys:
        address = (declared.get(key) or {}).get("email")
        if not address:
            _refuse(f"the account map declares no address for account key {key!r}",
                    "add the account to the Google CLI's config.yaml, or correct sources.json")
        out[key] = address
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="source_adapter",
        description="One Drive poll over the verified source map. Folders by id, floor on the read.",
    )
    parser.add_argument("--source-map", required=True, help="the verified-source-map to sweep")
    parser.add_argument("--sources", required=True,
                        help="the sources config carrying the name tokens items are classified by")
    parser.add_argument("--fixture", help="a fixture Drive listing; omit to sweep live Drive")
    parser.add_argument("--gtools", help="path to the Google CLI (live sweeps only)")
    parser.add_argument("--since", help="the last successful poll's watermark")
    parser.add_argument("--until", required=True, help="this poll's cutoff")
    parser.add_argument("--timezone", required=True, help="the timezone every date is computed in")
    parser.add_argument("--json", action="store_true", help="emit the swept answer as JSON")
    args = parser.parse_args(argv)

    try:
        tz = ZoneInfo(args.timezone)
        seams = seams_dir()
        source_map = _load(args.source_map)
        keys = sorted((source_map.get("accounts") or {}).keys())
        if args.fixture:
            data = _load(args.fixture)
            driver = FixtureDriveDriver(data)
            emails = data.get("account-emails") or {}
        else:
            if not args.gtools:
                _refuse("a live sweep needs the Google CLI", "pass --gtools, or pass --fixture")
            driver = GtoolsDriveDriver(Path(args.gtools))
            emails = account_emails(Path(args.gtools), keys)
        window = poll_window(seams, _parse(args.until),
                             _parse(args.since) if args.since else None)
        swept = sweep(driver, source_map, window, emails, tz, seams,
                      tokens=name_tokens(Path(args.sources).parent))
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(json.dumps(swept, indent=2, ensure_ascii=False))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
