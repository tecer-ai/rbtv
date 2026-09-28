#!/usr/bin/env python3
"""detection_cycle — the tick that turns one Drive poll into per-meeting work.

One tick does exactly this, in this order:

  1. open a window from the ONE whole-poll watermark to now,
  2. sweep every watched account's live sources through `source_adapter`
     (folders by id, floor on the read, every item classified by source kind),
  3. join what came back into meetings through `meeting_matcher`, against the
     meetings earlier polls already minted, so the join stays open,
  4. persist those meetings, so detection survives whatever happens next,
  5. give every meeting a disposition from the durable processed record — a
     meeting that so far holds only Gemini notes gets a job only when it starts on
     or after the configured `notes-only-from` date (clause 19 as amended by owner
     ruling r-gemini-notes-alone-triggers-summary, 2026-09-27),
  6. dispatch the ones that need work under a per-meeting single-flight claim,
  7. record each outcome, and park a meeting that has failed three cycles,
  8. advance the watermark — and ONLY if every account's sweep completed.

Four properties this file exists to hold, each guarded by a named test case:

  * **ONE whole-poll watermark.** Not one per account, not one per source: a
    single record, rewritten after a poll in which every account was covered. A
    poll that lost an account leaves it where it was, which is the whole of
    clause 12's downtime catch-up — the next window simply opens where the last
    good one closed, however long ago that was.

  * **Single-flight does NOT suppress the cadence.** Clause 21 keeps one claim per
    meeting key; clause 2 keeps the tick firing hourly. Both hold at once here
    because the claim is taken per MEETING, after detection, and a tick that
    cannot take a claim still swept, still joined, still persisted, and still
    returned. An implementation that skipped the tick would pass a single-flight
    test and break the contract.

  * **A claim dies with the process that holds it.** The claim is an exclusive
    `flock` on a file, so a tick killed mid-flight has its claim released by the
    kernel — the meeting is dispatchable again on the next tick, with no stale-lock
    sweeper to get wrong and no timeout to tune.

  * **Three failures park; there is no fourth attempt.** Clause 25b. The park is
    durable and is cleared by exactly one act, the owner's `retry`.

Step 6 takes a HANDLER. m5 builds the spine, not the summarizer: with no handler
the tick detects, joins, persists and disposes, and dispatches nothing. That is
the honest seam for m6 to land in, and it is what every detection-side probe runs
against.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import destination_resolver as dr  # noqa: E402
import meeting_matcher  # noqa: E402
import source_adapter  # noqa: E402
from source_adapter import DriverError, Refused, failure_event  # noqa: E402
from verify_access import build_validator, seam_schema  # noqa: E402

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_REFUSED = 2

# Seam ENTRY IDS. Every shape below is resolved through `seams/index.csv` at run
# time; no schema filename and no store location is written down in this file.
WATERMARK_ENTRY = "poll-watermark-store"
PROCESSED_ENTRY = "processed-transcript-store"
JOB_ENTRY = "per-meeting-job"
OUTCOME_ENTRY = "failure-event-and-outcome"
MEETING_ENTRY = "meeting-key-and-source-set"

# The cycle's OWN durable state. These are not crossings between pieces — no other
# piece of the product reads them — so the seam set declares no shape for them and
# they are config keys of this module. They are deliberately NOT watermark-shaped:
# the whole-poll watermark is the seam's single record and has no sibling here.
MEETINGS_KEY = "stores/detected-meetings"
ATTEMPTS_KEY = "stores/job-attempts"
CLAIMS_KEY = "stores/in-flight-claims"

# The component's ONE timezone, declared once, at the key m3's resolver declares it
# under (`d-m3-timezone-is-config`: required, no default). Reading it rather than
# copying it is what stops two files disagreeing about an owner ruling.
TIMEZONE_KEY = "destination-routing"
TIMEZONE_FIELD = "timezone"

# The accounts to poll and the name tokens items are classified by, declared by
# m2's grounding configuration. Its `accounts` list IS the watch list: the source
# map is verify-access's record of what it found, and may still carry an account
# the owner has since stopped watching (owner ruling 2026-09-26).
SOURCES_FILE = "sources.json"
SOURCE_MAP_FILE = "verified-source-map.json"

# goal.md clause 25b. The one place the park threshold is written down.
PARK_AFTER = 3

CADENCE_MINUTE = 10  # clause 2: hourly, at :10 past the hour.


def _refuse(what: str, fix: str) -> None:
    raise Refused(f"{what}\n  fix: {fix}")


def _stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)


# --------------------------------------------------------------------------
# stores — a config KEY resolves to a file; no literal path is written here
# --------------------------------------------------------------------------


def read_jsonl(path: Path) -> list:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, value) -> None:
    """Atomic: a torn store read as a good one is worse than no store at all."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_name(path.name + ".tmp")
    scratch.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(scratch, path)


def store_container(seams: Path, entry_id: str) -> dict:
    """A seam-declared store's `container` — its config KEY and its format.

    Read off the seam's reference instance, so the location this module writes to
    is the location the seam pins, not a location this module remembers.
    """
    for instance in source_adapter.seam_instances(seams, entry_id):
        container = instance.get("container")
        if isinstance(container, dict) and container.get("location"):
            return container
    _refuse(f"the {entry_id} seam's reference instance declares no container",
            "re-validate the seam set with validate_seams.py")
    return {}


def resolve_store(key: str, config_dir: Path, suffix: str) -> Path:
    """THE binding: a store config KEY -> the file it names.

    The rule is the component's live one, read off `channel_protocol.resolve_store`
    rather than invented here: a key `<group>/<leaf>` is looked up in
    `<group>.json` under the config-module home at object key `<leaf>`. Absent
    there, the key's own relative form under that home is the default, so the
    cycle is runnable before anyone writes a `stores.json` and every location is
    still a key rather than a path in code.
    """
    group, _, leaf = key.partition("/")
    if not leaf:
        _refuse(f"store key {key!r} is not of the form <group>/<leaf>",
                "name the store by the config key its seam declares")
    declared = config_dir / f"{group}.json"
    if declared.is_file():
        value = json.loads(declared.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get(leaf), str):
            path = Path(value[leaf]).expanduser()
            return path if path.is_absolute() else (config_dir / path)
    return config_dir / group / f"{leaf}{suffix}"


def processed_store_path(config_dir: Path) -> Path:
    """Where `publish_job.py` already writes every settled meeting's record.

    Not resolved through `resolve_store`'s generic `<config_dir>/<group>/<leaf>`
    default: that default landed this store UNDER THE CONFIG ROOT
    (`<config_dir>/stores/processed-transcripts.jsonl`), a file nothing else in
    this capability ever writes to — `publish_job.py` writes
    `<state>/processed-transcripts.jsonl` (`PROCESSED`). Two files, one tick
    reading the always-empty one, forever re-emitting a filed meeting as `new`
    (measured live, rounds 3 and 4: a fix that made the STATE-dir location
    reachable only through an extra flag the agent's own turn had to remember
    to pass, in the right order, before the tick — dead the moment a turn ran
    the tick first — was correctly judged "a prompt, not a fix").

    The agent home's layout is FIXED, not a per-deployment choice this
    capability guesses at: `<home>/config/` (materialized from settings.json)
    and `<home>/state/` (durable) are always siblings. `--config-dir` is
    always `<home>/config`, so `<home>/state` is ALWAYS `config_dir.parent /
    "state"` — derived here directly, needing no flag, no call order, and no
    file anything has to write first. A `stores.json` override (the same
    config-key redirect every other store here still honours) wins if one is
    ever declared, for a deployment where this derivation would be wrong;
    absent one — the ordinary case — the sibling `state/` is used directly.
    """
    declared = config_dir / "stores.json"
    if declared.is_file():
        value = json.loads(declared.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("processed-transcripts"), str):
            path = Path(value["processed-transcripts"]).expanduser()
            return path if path.is_absolute() else (config_dir / path)
    return Path(config_dir).resolve().parent / "state" / "processed-transcripts.jsonl"


# --------------------------------------------------------------------------
# the environment one tick runs in
# --------------------------------------------------------------------------


class Env:
    """What one tick runs against.

    The source map and the account addresses are resolved LAZILY, on first use.
    Only the poll needs them; `schedule`, `status` and `retry` do not, and an
    environment that refused to load without a grounded map would make the
    cadence and the ledger unreachable exactly when the grounding is what is
    broken — the moment an operator most needs to look.
    """

    def __init__(self, config_dir: Path, seams: Path, tz: ZoneInfo, stores: dict,
                 source_map=None, account_emails=None) -> None:
        self.config_dir = config_dir
        self.seams = seams
        self.tz = tz
        self.stores = stores
        self._source_map = source_map
        self._account_emails = account_emails
        self._sources = None
        self._validator = None

    @property
    def sources(self) -> dict:
        if self._sources is None:
            path = self.config_dir / SOURCES_FILE
            if not path.is_file():
                _refuse(f"no {SOURCES_FILE} under the config-module home",
                        "declare the watched accounts and the source name tokens there")
            self._sources = json.loads(path.read_text(encoding="utf-8"))
        return self._sources

    @property
    def source_map(self) -> dict:
        if self._source_map is None:
            path = self.config_dir / SOURCE_MAP_FILE
            if not path.is_file():
                _refuse(f"no {SOURCE_MAP_FILE} under the config-module home",
                        "run verify-access: the poll watches folders by the Drive ids it pins, "
                        "and there is no second way to learn them")
            self._source_map = json.loads(path.read_text(encoding="utf-8"))
        return watched_accounts(self._source_map, self.sources.get("accounts") or [])

    @property
    def tokens(self) -> dict:
        return source_adapter.name_tokens(self.config_dir)

    @property
    def account_emails(self) -> dict:
        if self._account_emails is None:
            gtools = Path(self.sources["gtools-path"])
            if not gtools.is_absolute():
                root = source_adapter.workspace_root(TOOL_DIR)
                if root is None:
                    _refuse("no workspace root above this tool", "run inside the workspace")
                gtools = root / gtools
            self._account_emails = source_adapter.account_emails(
                gtools, sorted((self.source_map.get("accounts") or {}).keys()))
        # Only watched accounts: an address the sweep is handed is an account it
        # answers for, and an unwatched one would read as covered with no records.
        watched = self.source_map.get("accounts") or {}
        return {key: email for key, email in self._account_emails.items() if key in watched}

    @property
    def validator(self):
        if self._validator is None:
            self._validator = build_validator(self.seams)
        return self._validator


def watched_accounts(source_map: dict, accounts: list) -> dict:
    """The source map cut down to the accounts the sources config watches.

    An account the config watches and the map does not carry was never verified,
    and polling around it would be a silent skip — so it is refused, never dropped.
    """
    mapped = source_map.get("accounts") or {}
    missing = [account for account in accounts if account not in mapped]
    if missing:
        _refuse(f"watched account(s) {missing} are absent from the verified source map",
                "run verify-access for them; an account is polled only by the folder ids it pins")
    return {**source_map, "accounts": {account: mapped[account] for account in accounts}}


def component_timezone(config_dir: Path) -> ZoneInfo:
    path = dr.config_path(TIMEZONE_KEY, override=config_dir)
    if not path.is_file():
        _refuse(f"no {path.name} under the config-module home",
                f"declare {TIMEZONE_FIELD!r} at the config key {TIMEZONE_KEY!r}")
    value = json.loads(path.read_text(encoding="utf-8")).get(TIMEZONE_FIELD)
    if not value:
        _refuse(f"{path.name} declares no {TIMEZONE_FIELD!r}",
                "the timezone every date is computed in is required and has no default")
    return ZoneInfo(value)


def load_env(config_dir: Path, seams: Path | None = None, source_map: dict | None = None,
             account_emails: dict | None = None) -> Env:
    config_dir = Path(config_dir)
    seams = seams or source_adapter.seams_dir()
    stores = {
        WATERMARK_ENTRY: _seam_store(seams, config_dir, WATERMARK_ENTRY),
        PROCESSED_ENTRY: processed_store_path(config_dir),
        MEETINGS_KEY: resolve_store(MEETINGS_KEY, config_dir, ".jsonl"),
        ATTEMPTS_KEY: resolve_store(ATTEMPTS_KEY, config_dir, ".jsonl"),
        CLAIMS_KEY: resolve_store(CLAIMS_KEY, config_dir, ""),
    }
    return Env(config_dir, seams, component_timezone(config_dir), stores,
               source_map=source_map, account_emails=account_emails)


def _seam_store(seams: Path, config_dir: Path, entry_id: str) -> Path:
    container = store_container(seams, entry_id)
    suffix = "." + container["format"]
    return resolve_store(container["location"], config_dir, suffix)


# --------------------------------------------------------------------------
# the ONE whole-poll watermark
# --------------------------------------------------------------------------


def read_watermark(env: Env) -> datetime | None:
    path = env.stores[WATERMARK_ENTRY]
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8")).get("last-successful-poll")
    return _parse(record) if record else None


def write_watermark(env: Env, until: datetime) -> None:
    """ONE record, rewritten. Never appended to, never a second file."""
    write_json(env.stores[WATERMARK_ENTRY], {"last-successful-poll": _stamp(until)})


def count_watermarks(env: Env) -> int:
    """How many whole-poll watermark records exist anywhere the cycle writes.

    Counted, not asserted: the store's own record, plus any sibling file under the
    store root whose name or contents claim to be one. Two is a contract failure,
    and the only way to see it is to go looking.
    """
    path = env.stores[WATERMARK_ENTRY]
    found = 0
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        records = value if isinstance(value, list) else [value]
        found += sum(1 for r in records if isinstance(r, dict) and "last-successful-poll" in r)
    for sibling in sorted(path.parent.glob("*")) if path.parent.is_dir() else []:
        if sibling == path or not sibling.is_file():
            continue
        try:
            text = sibling.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found += text.count('"last-successful-poll"')
    return found


# --------------------------------------------------------------------------
# the meetings, the processed record, the attempts
# --------------------------------------------------------------------------


def read_meetings(env: Env) -> list:
    """The open join. Last row per meeting key wins; the store is append-only."""
    latest: dict = {}
    for row in read_jsonl(env.stores[MEETINGS_KEY]):
        latest[row["meeting-key"]] = row
    return [latest[key] for key in sorted(latest)]


def write_meetings(env: Env, sets: list, previous: list) -> list:
    """Append only the sets that changed. Returns what was appended."""
    before = {entry["meeting-key"]: [r["drive-ref"] for r in entry["source-set"]]
              for entry in previous}
    changed = [entry for entry in sets
               if before.get(entry["meeting-key"]) != [r["drive-ref"] for r in entry["source-set"]]]
    if changed:
        append_jsonl(env.stores[MEETINGS_KEY], changed)
    return changed


def read_processed(env: Env) -> list:
    return read_jsonl(env.stores[PROCESSED_ENTRY])


def processed_for(processed: list, meeting_key: str) -> list:
    return [row for row in processed if row.get("meeting-key") == meeting_key]


def read_attempts(env: Env) -> dict:
    latest: dict = {}
    for row in read_jsonl(env.stores[ATTEMPTS_KEY]):
        latest[row["meeting-key"]] = row
    return latest


def record_attempt(env: Env, meeting_key: str, failures: int, at: datetime) -> dict:
    row = {"meeting-key": meeting_key, "consecutive-failures": failures,
           "parked": failures >= PARK_AFTER, "at": _stamp(at)}
    if row["parked"]:
        row["awaiting"] = "retry"
        row["parked-at"] = _stamp(at)
    append_jsonl(env.stores[ATTEMPTS_KEY], [row])
    return row


def clear_park(env: Env, meeting_key: str, at: datetime) -> dict:
    """The owner's `retry`: the ONE act that un-parks a meeting."""
    row = {"meeting-key": meeting_key, "consecutive-failures": 0, "parked": False,
           "at": _stamp(at), "cleared-by": "retry"}
    append_jsonl(env.stores[ATTEMPTS_KEY], [row])
    return row


# --------------------------------------------------------------------------
# single-flight — one claim per meeting key, released by the kernel on a kill
# --------------------------------------------------------------------------


def claim_path(env: Env, meeting_key: str) -> Path:
    digest = hashlib.sha256(meeting_key.encode("utf-8")).hexdigest()[:16]
    return env.stores[CLAIMS_KEY] / f"{digest}.claim"


@contextlib.contextmanager
def claim_meeting(env: Env, meeting_key: str, tick_id: str, at: datetime):
    """Yields the claim, or None when another tick already holds this key."""
    path = claim_path(env, meeting_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(handle)
        yield None
        return
    payload = {"meeting-key": meeting_key, "tick": tick_id, "pid": os.getpid(),
               "claimed-at": _stamp(at)}
    os.ftruncate(handle, 0)
    os.write(handle, (json.dumps(payload) + "\n").encode("utf-8"))
    os.fsync(handle)
    try:
        yield payload
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        os.close(handle)
        path.unlink(missing_ok=True)


def live_claims(env: Env) -> list:
    """Every claim a LIVE holder still owns, measured by trying to take it.

    A claim file whose lock is free belonged to a tick that is gone — the kernel
    released it when that process died — so it is not in flight and is swept.
    """
    root = env.stores[CLAIMS_KEY]
    if not root.is_dir():
        return []
    held = []
    for path in sorted(root.glob("*.claim")):
        handle = os.open(path, os.O_RDWR)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            body = path.read_text(encoding="utf-8").strip()
            held.append(json.loads(body) if body else {"meeting-key": None})
            continue
        else:
            fcntl.flock(handle, fcntl.LOCK_UN)
            path.unlink(missing_ok=True)
        finally:
            os.close(handle)
    return held


# --------------------------------------------------------------------------
# cadence
# --------------------------------------------------------------------------


def next_fire(now: datetime, tz: ZoneInfo) -> datetime:
    """The next scheduled fire: the coming :10 past the hour, local time."""
    local = now.astimezone(tz)
    candidate = local.replace(minute=CADENCE_MINUTE, second=0, microsecond=0)
    if candidate <= local:
        candidate = (candidate + timedelta(hours=1)).replace(minute=CADENCE_MINUTE)
    return candidate


def fire_times(start: datetime, tz: ZoneInfo, count: int) -> list:
    fires = []
    moment = start
    for _ in range(count):
        moment = next_fire(moment, tz)
        fires.append(moment)
    return fires


# --------------------------------------------------------------------------
# dispositions
# --------------------------------------------------------------------------


def entry_of(sets: list, meeting_key: str) -> dict:
    for entry in sets:
        if entry["meeting-key"] == meeting_key:
            return entry
    raise KeyError(meeting_key)


def job_for(entry: dict, processed: list) -> dict:
    """One `per-meeting-job`. The durable processed record is the whole rule."""
    key = entry["meeting-key"]
    records = processed_for(processed, key)
    job = {"meeting-key": key, "source-set": list(entry["source-set"])}
    if not records:
        job["disposition"] = "new"
        return job
    latest = max(records, key=lambda row: row["processed-at"])
    covered = {source for row in records for source in row.get("coverage", [])}
    present = {record["source"] for record in entry["source-set"]}
    if present <= covered:
        job["disposition"] = "already-done"
        return job
    job["disposition"] = "amend"
    job["amend"] = {"summary": latest["summary"], "coverage": sorted(covered)}
    return job


def has_transcript(source_set: list) -> bool:
    return any(record["source"] in source_adapter.TRANSCRIPT_SOURCES for record in source_set)


def notes_only_from(env: Env):
    """The first local date whose notes-only meetings are summarized, or None.

    Owner configuration (`sources.json` → `notes-only-from`). Absent means no
    notes-only meeting is ever admitted — the pre-2026-09-27 behaviour.
    """
    value = env.sources.get("notes-only-from")
    return date.fromisoformat(value) if value else None


def notes_admitted(entry: dict, notes_from, tz: ZoneInfo) -> bool:
    """Does this notes-only meeting start on or after `notes_from`?

    The meeting's start is the earliest start across its records, on the
    configured timezone's calendar — the same reading meeting_matcher uses.
    """
    if notes_from is None:
        return False
    start = min(_parse(record["start-time"]) for record in entry["source-set"])
    return start.astimezone(tz).date() >= notes_from


def outcome_values(seams: Path) -> list:
    """The outcome enum, READ OUT OF the seam. Never a remembered four."""
    schema = seam_schema(seams, OUTCOME_ENTRY)
    for branch in schema.get("oneOf", []):
        enum = branch.get("properties", {}).get("outcome", {}).get("enum")
        if enum:
            return list(enum)
    _refuse("the failure-event-and-outcome seam names no outcome enum",
            "re-validate the seam set with validate_seams.py")
    return []


# --------------------------------------------------------------------------
# the tick
# --------------------------------------------------------------------------


class TickResult:
    def __init__(self) -> None:
        self.tick: str = ""
        self.fired_at: str = ""
        self.window: dict = {}
        self.records: list = []
        self.meetings: list = []
        self.minted: list = []
        self.jobs: list = []
        self.outcomes: list = []
        self.failure_events: list = []
        self.refused_pre_floor: list = []
        self.unclassified: list = []
        self.awaiting_transcript: list = []
        self.skipped_in_flight: list = []
        self.skipped_settled: list = []
        self.skipped_parked: list = []
        self.parked: list = []
        self.watermark: str | None = None
        self.watermark_advanced: bool = False
        self.covered: dict = {}

    def as_dict(self) -> dict:
        return {
            "tick": self.tick,
            "fired-at": self.fired_at,
            "window": self.window,
            "accounts-covered": self.covered,
            "records": len(self.records),
            "meetings": len(self.meetings),
            "new-meetings": self.minted,
            "jobs": self.jobs,
            "outcomes": self.outcomes,
            "failure-events": self.failure_events,
            "refused-pre-floor": self.refused_pre_floor,
            "unclassified": self.unclassified,
            "awaiting-transcript": self.awaiting_transcript,
            "skipped-in-flight": self.skipped_in_flight,
            "skipped-settled": self.skipped_settled,
            "skipped-parked": self.skipped_parked,
            "parked": self.parked,
            "watermark": self.watermark,
            "watermark-advanced": self.watermark_advanced,
        }


def run_tick(env: Env, now: datetime, driver, handler=None, tick_id: str | None = None,
             validate: bool = True) -> TickResult:
    """ONE tick. Detection always happens; dispatch happens only with a handler."""
    result = TickResult()
    result.tick = tick_id or uuid.uuid4().hex[:12]
    result.fired_at = _stamp(now)

    since = read_watermark(env)
    window = source_adapter.poll_window(env.seams, now, since)
    result.window = window
    swept = source_adapter.sweep(driver, env.source_map, window, env.account_emails,
                                 env.tz, env.seams, tokens=env.tokens)
    result.failure_events = list(swept["failure-events"])
    result.refused_pre_floor = list(swept["refused-pre-floor"])
    result.unclassified = list(swept["unclassified"])
    result.covered = {email: slot["covered"] for email, slot in swept["accounts"].items()}
    result.records = [record for slot in swept["accounts"].values() for record in slot["records"]]

    previous = read_meetings(env)
    sets, minted = meeting_matcher.pair(result.records, previous, env.tz)
    write_meetings(env, sets, previous)
    result.meetings = sets
    result.minted = minted

    processed = read_processed(env)
    attempts = read_attempts(env)
    notes_from = notes_only_from(env)
    for entry in sets:
        if has_transcript(entry["source-set"]) or notes_admitted(entry, notes_from, env.tz):
            result.jobs.append(job_for(entry, processed))
        else:
            # A notes-only meeting from before `notes-only-from` emits no job —
            # nothing fails and nothing parks (owner ruling
            # d-backfill-29-notes-only-meetings). The join stays open: a transcript
            # a later poll brings joins THIS meeting and carries the notes in.
            result.awaiting_transcript.append(entry["meeting-key"])

    if validate:
        _validate(env, records_seam=swept, jobs=result.jobs, events=result.failure_events)

    for job in result.jobs:
        key = job["meeting-key"]
        if job["disposition"] == "already-done":
            continue
        if (attempts.get(key) or {}).get("parked"):
            result.skipped_parked.append(key)
            continue
        if handler is None:
            continue
        with claim_meeting(env, key, result.tick, now) as claim:
            if claim is None:
                # Clause 21 holds and clause 2 is untouched: this tick fired, swept,
                # joined and persisted; only THIS key's dispatch waits for the tick
                # that holds it.
                result.skipped_in_flight.append(key)
                continue
            # The disposition was computed before the claim. Another tick may have
            # filed this meeting in the meantime, and filing it twice is exactly the
            # duplicate clause 13 forbids, so the answer is re-read under the claim.
            settled = job_for(entry_of(sets, key), read_processed(env))
            if settled["disposition"] == "already-done":
                result.skipped_settled.append(key)
                continue
            outcome, event = _dispatch(env, settled, handler, now)
        if event:
            result.failure_events.append(event)
        result.outcomes.append(outcome)
        _settle(env, settled, outcome, attempts, result, now)

    if validate and result.outcomes:
        _validate_outcomes(env, result.outcomes)

    result.watermark = _stamp(since) if since else None
    if all(slot["covered"] for slot in swept["accounts"].values()):
        write_watermark(env, now)
        result.watermark = _stamp(now)
        result.watermark_advanced = True
    return result


def _dispatch(env: Env, job: dict, handler, now: datetime):
    """Run the handler. A handler that dies becomes an outcome, never a silence."""
    try:
        outcome = handler(job)
    except Exception as exc:  # the handler is downstream code; it may do anything
        return (
            {"kind": "per-meeting-outcome", "meeting-key": job["meeting-key"],
             "outcome": "failed", "at": _stamp(now)},
            failure_event(f"handler raised: {exc}", "meeting", now,
                          meeting_key=job["meeting-key"]),
        )
    if not isinstance(outcome, dict) or outcome.get("outcome") not in outcome_values(env.seams):
        return (
            {"kind": "per-meeting-outcome", "meeting-key": job["meeting-key"],
             "outcome": "failed", "at": _stamp(now)},
            failure_event(f"handler answered outside the outcome enum: {outcome!r}", "meeting",
                          now, meeting_key=job["meeting-key"]),
        )
    return outcome, None


def _settle(env: Env, job: dict, outcome: dict, attempts: dict, result: TickResult,
            now: datetime) -> None:
    key = job["meeting-key"]
    verdict = outcome["outcome"]
    if verdict in ("filed", "amended"):
        coverage = sorted({record["source"] for record in job["source-set"]})
        append_jsonl(env.stores[PROCESSED_ENTRY], [
            {
                "transcript-ref": record["drive-ref"],
                "account": record["account"],
                "source": record["source"],
                "meeting-key": key,
                "processed-at": _stamp(now),
                "summary": outcome["destination"],
                "coverage": coverage,
            }
            for record in job["source-set"]
        ])
    if verdict == "failed":
        failures = (attempts.get(key) or {}).get("consecutive-failures", 0) + 1
        row = record_attempt(env, key, failures, now)
        attempts[key] = row
        if row["parked"]:
            result.parked.append(key)
    elif (attempts.get(key) or {}).get("consecutive-failures"):
        attempts[key] = clear_park(env, key, now)


def _validate(env: Env, records_seam: dict, jobs: list, events: list) -> None:
    validate = env.validator
    problems = validate(source_adapter.records_in_window(records_seam), "window-contract")
    for job in jobs:
        problems += validate(job, JOB_ENTRY)
    for event in events:
        problems += validate(event, OUTCOME_ENTRY)
    if problems:
        _refuse("an emission does not validate against its seam: " + "; ".join(problems[:5]),
                "the emission is wrong, or the seam set changed under this tool")


def _validate_outcomes(env: Env, outcomes: list) -> None:
    problems = []
    for outcome in outcomes:
        problems += env.validator(outcome, OUTCOME_ENTRY)
    if problems:
        _refuse("a per-meeting outcome does not validate: " + "; ".join(problems[:5]),
                "the handler's answer is wrong, or the seam set changed under this tool")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _driver_for(args, env: Env):
    if args.fixture:
        return source_adapter.FixtureDriveDriver(
            json.loads(Path(args.fixture).read_text(encoding="utf-8")))
    gtools = Path(env.sources["gtools-path"])
    if not gtools.is_absolute():
        gtools = source_adapter.workspace_root(TOOL_DIR) / gtools
    return source_adapter.GtoolsDriveDriver(gtools)


def _env_for(args) -> Env:
    config_dir = Path(args.config_dir) if args.config_dir else dr.config_root()
    emails = None
    source_map = None
    if args.fixture:
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        emails = data.get("account-emails")
    if args.source_map:
        source_map = json.loads(Path(args.source_map).read_text(encoding="utf-8"))
    return load_env(config_dir, source_map=source_map, account_emails=emails)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="detection_cycle",
        description="The detection tick: one poll, meetings, dispositions, single-flight, park.",
    )
    parser.add_argument("--config-dir", help="the config-module home (default: this component's)")
    parser.add_argument("--fixture", help="a fixture Drive listing; omit to poll live Drive")
    parser.add_argument("--source-map", help="a source map to poll (default: the grounded one)")
    sub = parser.add_subparsers(dest="op", required=True)

    tick = sub.add_parser("tick", help="run one detection tick")
    tick.add_argument("--now", help="the tick's instant (default: now)")

    schedule = sub.add_parser("schedule", help="print the next scheduled fires")
    schedule.add_argument("--from", dest="start", help="the instant to schedule from")
    schedule.add_argument("--count", type=int, default=3)

    retry = sub.add_parser("retry", help="the owner's answer that un-parks one meeting")
    retry.add_argument("--meeting-key", required=True)

    sub.add_parser("status", help="the watermark, the meetings, the parked jobs")
    sub.add_parser("keys", help="the config keys this cycle reads and the files they name")

    args = parser.parse_args(argv)

    try:
        env = _env_for(args)
        now = _parse(args.now) if getattr(args, "now", None) else datetime.now(env.tz)
        if args.op == "tick":
            result = run_tick(env, now, _driver_for(args, env))
            payload = result.as_dict()
            payload["watermark-count"] = count_watermarks(env)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return EXIT_FAIL if result.failure_events else EXIT_OK
        if args.op == "schedule":
            start = _parse(args.start) if args.start else datetime.now(env.tz)
            print(json.dumps({"fires": [_stamp(m) for m in fire_times(start, env.tz, args.count)]},
                             indent=2))
            return EXIT_OK
        if args.op == "retry":
            row = clear_park(env, args.meeting_key, datetime.now(env.tz))
            print(json.dumps(row, indent=2))
            return EXIT_OK
        if args.op == "status":
            attempts = read_attempts(env)
            print(json.dumps({
                "watermark": _stamp(read_watermark(env)) if read_watermark(env) else None,
                "watermark-count": count_watermarks(env),
                "meetings": len(read_meetings(env)),
                "processed-transcripts": len(read_processed(env)),
                "in-flight": [c.get("meeting-key") for c in live_claims(env)],
                "parked": sorted(k for k, row in attempts.items() if row.get("parked")),
            }, indent=2))
            return EXIT_OK
        if args.op == "keys":
            print(json.dumps({key: str(path) for key, path in env.stores.items()}, indent=2))
            return EXIT_OK
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except (DriverError, OSError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return EXIT_FAIL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
