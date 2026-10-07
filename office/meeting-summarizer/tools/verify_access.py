#!/usr/bin/env python3
"""verify_access — the pre-first-poll verification pass.

Establishes, by running against the live accounts, that every transcript source
this workflow watches is reachable and pinned by its Drive **id**. Produces the
four grounding artifacts under the component's runtime folder
(`.rbtv/runtime/<component>/` of the installation the config-module home is in):

  verify-access-verdict.json   per-account, per-precondition verdicts + observations
  verified-source-map.json     the source map the live poll reads, keyed by Drive id
  grounding-findings.json      the findings-payload the channel's grounding note carries
  verify-access-calls.log      every outside call, by NAME, with its exit code

Two boundaries this tool holds and never crosses:

  * The five precondition ids and the three folder layouts are READ FROM THE SEAM
    SET at run time (seams/index.csv -> the schema files it names). Nothing here
    is a remembered constant, so a seam change moves this tool with it.
  * Account keys and folder names are OWNER CONFIGURATION, read from the
    config-module home at run time. No account name and no folder name is
    program text.

It looks at folders, files and transcripts, and at nothing the owner has already
settled by attestation (seams/attestation-boundary.md) — a check of a settled
fact is a defect, not a safeguard, so none is written here.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_REFUSED = 2

CONFIG_ROOT_ENV = "MEETING_SUMMARIZER_CONFIG_ROOT"
CONFIG_FILE = "sources.json"

VERDICT_FILE = "verify-access-verdict.json"
SOURCE_MAP_FILE = "verified-source-map.json"
FINDINGS_FILE = "grounding-findings.json"
CALL_LOG_FILE = "verify-access-calls.log"

# Which seam entry carries which vocabulary. Resolved through seams/index.csv,
# never read from a path typed here.
FINDINGS_ENTRY = "findings-payload"
SOURCE_MAP_ENTRY = "verified-source-map"

# Which precondition each folder layout answers. The layout names come from the
# seam set; this maps them onto the precondition ids the seam set also names.
LAYOUT_PRECONDITION = {
    "legacy-meet-recordings": "legacy-meet-recordings-folder",
    "google-meet-tree": "google-meet-tree",
    "tactiq-autosave": "tactiq-autosave-folder",
}
TRANSCRIPT_PRECONDITION = "meet-transcription-config"
NAMING_PRECONDITION = "tactiq-naming-discriminator"
NAMING_LAYOUT = "tactiq-autosave"

FOLDER_MIME = "application/vnd.google-apps.folder"

# Absolute paths never reach an artifact: a token store, a host or an instance id
# can ride inside a tool's error text, and the call log is a file that is kept.
ABSPATH = re.compile(r"(?<![\w-])/[^\s'\"]*")


def refuse(what: str, fix: str) -> None:
    print(f"REFUSED: {what}", file=sys.stderr)
    print(f"  fix: {fix}", file=sys.stderr)
    sys.exit(EXIT_REFUSED)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def scrub(text: str) -> str:
    """Strip absolute paths out of anything that will be written down."""
    return ABSPATH.sub("<path>", (text or "").strip())


# --------------------------------------------------------------------------
# the seam set — the vocabulary this tool speaks
# --------------------------------------------------------------------------


def workspace_root(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / ".rbtv" / "config").is_dir():
            return candidate
    return None


def runtime_dir(config_dir: Path) -> Path:
    """The runtime folder of the installation whose config-module home this is.

    The config-module home is `<installation>/.rbtv/config/<component>/`; what the
    tools write while running goes in `<installation>/.rbtv/runtime/<component>/`.
    The tool that writes there creates it.
    """
    home = Path(config_dir).expanduser().resolve()
    if home.parent.name != "config" or home.parent.parent.name != ".rbtv":
        refuse(f"{home} is not an installation's .rbtv/config/<component>/ folder, "
               "so it names no runtime folder",
               "pass the installation's .rbtv/config/meeting-summarizer as the config-module home")
    return home.parent.parent / "runtime" / home.name


def seam_schema(seams_dir: Path, entry_id: str) -> dict:
    """Resolve one seam entry's schema THROUGH seams/index.csv."""
    index = seams_dir / "index.csv"
    if not index.is_file():
        refuse(f"no seam index at {index.name} under the seams dir",
               "point --seams at the seam set this workflow was built against")
    import csv

    with index.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("entry-id") == entry_id:
                schema_file = (row.get("schema-file") or "").strip()
                if not schema_file:
                    refuse(f"seam entry {entry_id} names no schema file",
                           "the seam set is not the one this tool binds to")
                path = seams_dir / schema_file
                if not path.is_file():
                    refuse(f"seam entry {entry_id} names a missing schema: {schema_file}",
                           "re-validate the seam set with validate_seams.py")
                return json.loads(path.read_text(encoding="utf-8"))
    refuse(f"seam entry {entry_id} is absent from the seam index",
           "re-validate the seam set with validate_seams.py")
    return {}


def precondition_ids(seams_dir: Path) -> list[str]:
    schema = seam_schema(seams_dir, FINDINGS_ENTRY)
    required = schema.get("$defs", {}).get("precondition-verdicts", {}).get("required")
    if not required:
        refuse("the findings-payload seam names no required precondition ids",
               "re-validate the seam set with validate_seams.py")
    return list(required)


def layout_names(seams_dir: Path) -> list[str]:
    schema = seam_schema(seams_dir, SOURCE_MAP_ENTRY)
    enum = schema.get("$defs", {}).get("layout", {}).get("enum")
    if not enum:
        refuse("the verified-source-map seam names no folder layouts",
               "re-validate the seam set with validate_seams.py")
    return list(enum)


def build_validator(seams_dir: Path):
    """A draft 2020-12 validator with every seam schema preloaded for $ref."""
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012
    except ImportError as exc:
        refuse(f"the jsonschema/referencing libraries are not importable: {exc}",
               "python3 -m pip install jsonschema")
    registry = Registry()
    for path in sorted(seams_dir.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        registry = registry.with_resources(
            [(path.name, resource), (path.relative_to(seams_dir).as_posix(), resource)]
        )

    def validate(instance, entry_id: str) -> list[str]:
        schema = seam_schema(seams_dir, entry_id)
        validator = Draft202012Validator(schema, registry=registry)
        return [
            f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
            for err in validator.iter_errors(instance)
        ]

    return validate


# --------------------------------------------------------------------------
# configuration — owner values, read at run time, never program text
# --------------------------------------------------------------------------


def load_config(config_dir: Path) -> dict:
    path = config_dir / CONFIG_FILE
    if not path.is_file():
        refuse(f"no {CONFIG_FILE} under the config-module home",
               f"write {CONFIG_FILE} declaring 'accounts' and 'folder-names'")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        refuse(f"{CONFIG_FILE} is not readable JSON: {exc}", "fix the config file")
    accounts = config.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        refuse(f"{CONFIG_FILE} declares no accounts",
               "'accounts' is a non-empty list of gtools account keys")
    if not isinstance(config.get("folder-names"), dict):
        refuse(f"{CONFIG_FILE} declares no folder-names",
               "'folder-names' maps each layout to the folder names to look for")
    # The transcript file-name words have ONE home, shared with detection and the
    # artifact reader (no default: Meet names artifacts in the ACCOUNT's locale).
    # Imported here, not at module level: source_adapter imports this module.
    from source_adapter import Refused, name_tokens
    try:
        config["transcript-tokens"] = name_tokens(config_dir)["meet"]
    except Refused as exc:
        refuse(str(exc).split("\n  fix: ")[0], str(exc).split("\n  fix: ")[-1])
    return config


# --------------------------------------------------------------------------
# drivers — the one place an outside call is made
# --------------------------------------------------------------------------


class CallLog:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def record(self, account: str, operation: str, exit_code: int, outcome: str) -> None:
        self.rows.append({
            "at": now_iso(),
            "account": account,      # an account KEY: a name, never a credential value
            "operation": operation,
            "exit": exit_code,
            "outcome": scrub(outcome),
        })

    def text(self) -> str:
        head = ("# verify-access call log — account KEYS and operation names only.\n"
                "# No credential value, store path, host or instance id is recorded here.\n")
        return head + "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in self.rows)


class DriverError(RuntimeError):
    """An outside call could not be completed. Never a verdict of 'dead'."""


class GtoolsDriver:
    """The live driver: the Google surface, reached through the gtools CLI."""

    def __init__(self, gtools: Path, log: CallLog, timeout: int = 180) -> None:
        self.gtools = gtools
        self.log = log
        self.timeout = timeout

    def _run(self, account: str, operation: str, args: list[str]):
        cmd = [sys.executable, str(self.gtools), *args, "--account", account, "--json"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            self.log.record(account, operation, -1, "timeout")
            raise DriverError(f"{operation}: timed out")
        if proc.returncode != 0:
            reason = _error_class(proc.stderr)
            self.log.record(account, operation, proc.returncode, reason)
            raise DriverError(f"{operation}: {reason}")
        try:
            payload = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            self.log.record(account, operation, proc.returncode, "unparseable JSON on stdout")
            raise DriverError(f"{operation}: unparseable JSON on stdout")
        self.log.record(account, operation, proc.returncode, f"{len(payload)} item(s)")
        return payload

    def drive_search(self, account: str, query: str) -> list[dict]:
        return self._run(account, "drive.search", ["drive", "search", "-q", query])

    def drive_list(self, account: str, folder_id: str) -> list[dict]:
        return self._run(account, "drive.list",
                         ["drive", "list", "--folder-id", folder_id, "--max-results", "50"])



class FixtureDriver:
    """The offline driver the selftest runs against. Same surface, no network."""

    def __init__(self, data: dict, log: CallLog) -> None:
        self.data = data
        self.log = log

    def _get(self, account: str, operation: str, key: str):
        bucket = self.data.get(account)
        if bucket is None:
            self.log.record(account, operation, 1, "no such account in fixture")
            raise DriverError(f"{operation}: no such account in fixture")
        value = bucket.get(key)
        if value == "ERROR":
            self.log.record(account, operation, 1, "fixture: call refused")
            raise DriverError(f"{operation}: fixture: call refused")
        value = value or []
        self.log.record(account, operation, 0, f"{len(value)} item(s)")
        return value

    def drive_search(self, account: str, query: str) -> list[dict]:
        """Both query forms this tool issues: an exact folder name, and a name substring.

        The substring form reads a DIFFERENT bucket (`files`) from the folder form
        (`folders`), so a fixture can refuse one without touching the other — which
        is what lets case 7 break exactly one call.
        """
        token = _contains_token(query)
        if token:
            files = self._get(account, "drive.search", "files")
            return [f for f in files if token in (f.get("name") or "")]
        name = _quoted_name(query)
        folders = self._get(account, "drive.search", "folders")
        return [f for f in folders if f.get("name") == name]

    def drive_list(self, account: str, folder_id: str) -> list[dict]:
        listings = self._get(account, "drive.list", "listings")
        return list(listings.get(folder_id, [])) if isinstance(listings, dict) else []



def _error_class(stderr: str) -> str:
    """The last meaningful line of a failed call, scrubbed. Never the whole trace."""
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    return scrub(lines[-1]) if lines else "failed with no message"


def _quoted_name(query: str) -> str:
    match = re.search(r"name\s*=\s*'([^']*)'", query)
    return match.group(1) if match else ""


def _contains_token(query: str) -> str:
    match = re.search(r"name\s+contains\s+'([^']*)'", query)
    return match.group(1) if match else ""


def folder_query(name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace("'", "\\'")
    return f"name = '{escaped}' and mimeType = '{FOLDER_MIME}' and trashed = false"


def transcript_query(token: str, since: str) -> str:
    """Files whose name carries a Meet transcript's own token, inside the window.

    A LISTING, never a read: clause 15's floor governs fetching a transcript's
    CONTENT, which this pass never does — `source_adapter` enforces the floor on
    the read. The window here is the pre-flight question "is transcription
    producing anything at all", and it opens well after the floor.
    """
    escaped = token.replace("\\", "\\\\").replace("'", "\\'")
    return f"name contains '{escaped}' and modifiedTime > '{since}' and trashed = false"


# --------------------------------------------------------------------------
# the five checks
# --------------------------------------------------------------------------


def check_folder(driver, account: str, names: list[str]) -> dict:
    """Live + a Drive id, or dead. A folder without an id is NEVER recorded."""
    for name in names:
        hits = driver.drive_search(account, folder_query(name))
        for hit in hits:
            if hit.get("mimeType") != FOLDER_MIME:
                continue
            folder_id = (hit.get("id") or "").strip()
            if not folder_id:
                # A name with no id is unusable: the watch list is keyed by id so
                # that a rename cannot silently empty it. Refuse, never fall back.
                raise DriverError("a matching folder carries no Drive id")
            return {"verdict": "live", "folder-ref": folder_id,
                    "detail": "folder resolved to a Drive id"}
    return {"verdict": "dead", "detail": "no folder found for any configured name"}


def check_transcripts(driver, account: str, days: int, tokens: list[str]) -> dict:
    """Meet is producing transcript FILES in the window — an output, not a setting.

    Observed in DRIVE, where the product actually consumes them, and deliberately
    NOT through the Meet API. The settled route is one Drive poll over both
    sources (`goal.md`), `source_adapter` is the only Drive reader in the product,
    and nothing in the product calls the Meet API at all. Verifying this
    precondition through an API no part of the product uses would make the
    pre-flight pass depend on a Cloud-console activation that is neither of the
    two one-time owner setups the contract fixes at two.

    The tokens are OWNER CONFIGURATION, because Meet names its artifacts in the
    account's own locale: a token list typed here would read a Portuguese account
    as dead. Only a COUNT reaches the verdict — a meeting title is the owner's
    content and this file's output is written down and posted.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for token in tokens:
        hits = driver.drive_search(account, transcript_query(token, since))
        files = [h for h in hits if h.get("mimeType") != FOLDER_MIME]
        if files:
            return {"verdict": "live",
                    "detail": f"{len(files)} transcript file(s) matching a configured "
                              f"name token in the last {days} day(s)"}
    return {"verdict": "dead",
            "detail": f"no file matching any of the {len(tokens)} configured transcript "
                      f"name token(s) in the last {days} day(s)"}


def check_naming(driver, account: str, folder_ref: str | None, pattern: str) -> dict:
    """Saved names carry their own discriminator, so two same-day meetings differ."""
    if not folder_ref:
        return {"verdict": "dead", "detail": "no auto-save folder to read names from"}
    entries = driver.drive_list(account, folder_ref)
    names = [e.get("name", "") for e in entries if e.get("mimeType") != FOLDER_MIME]
    if not names:
        return {"verdict": "dead", "detail": "auto-save folder holds no saved file to judge"}
    compiled = re.compile(pattern)
    matched = [n for n in names if compiled.search(n)]
    if len(matched) == len(names):
        return {"verdict": "live",
                "detail": f"all {len(names)} saved name(s) carry the discriminator"}
    return {"verdict": "dead",
            "detail": f"{len(names) - len(matched)} of {len(names)} saved name(s) "
                      "carry no per-occurrence discriminator"}


def verify_account(driver, account: str, config: dict, layouts: list[str],
                   ids: list[str]) -> dict:
    """One account's five verdicts and its source entries. Raises on a dead call."""
    folder_names = config["folder-names"]
    sources: list[dict] = []
    preconditions: dict[str, dict] = {}

    for layout in layouts:
        names = folder_names.get(layout) or []
        result = check_folder(driver, account, names)
        entry = {"layout": layout, "verdict": result["verdict"]}
        if result["verdict"] == "live":
            entry["folder-ref"] = result["folder-ref"]
            if layout == NAMING_LAYOUT:
                entry["saves-into-account"] = account
        else:
            entry["notes"] = result["detail"]
        sources.append(entry)
        preconditions[LAYOUT_PRECONDITION[layout]] = {
            "verdict": result["verdict"], "detail": result["detail"]
        }

    preconditions[TRANSCRIPT_PRECONDITION] = check_transcripts(
        driver, account, int(config.get("meet-window-days", 30)),
        config["transcript-tokens"],
    )
    autosave = next((s for s in sources if s["layout"] == NAMING_LAYOUT), None)
    preconditions[NAMING_PRECONDITION] = check_naming(
        driver, account, (autosave or {}).get("folder-ref"),
        config.get("naming-discriminator-pattern", r"\d{4}-\d{2}-\d{2}")
    )

    # Two layouts resolving to the SAME Drive id is a silently-halved poll: the
    # sweep would visit one folder twice and never look in the other. It is a
    # configuration mistake (a name list whose entries overlap, and folder lookup
    # takes the first match), so it fails the pass rather than producing a map
    # that looks complete. Measured on the live accounts 2026-09-26: both
    # "Meet Recordings" and "Google Meet" exist, and the tree layout's name list
    # led with the legacy folder's name.
    by_ref: dict[str, str] = {}
    for entry in sources:
        ref = entry.get("folder-ref")
        if not ref:
            continue
        if ref in by_ref:
            raise DriverError(
                f"layouts {by_ref[ref]} and {entry['layout']} resolved to the same "
                "Drive folder; one watched source would never be read")
        by_ref[ref] = entry["layout"]

    missing = [i for i in ids if i not in preconditions]
    if missing:
        raise DriverError(f"the pass produced no verdict for: {', '.join(missing)}")
    return {"preconditions": {i: preconditions[i] for i in ids}, "sources": sources}


# --------------------------------------------------------------------------
# the pass
# --------------------------------------------------------------------------


def run_pass(driver, accounts: list[str], config: dict, layouts: list[str],
             ids: list[str]) -> dict:
    stamp = now_iso()
    verdict = {"verified-at": stamp, "accounts": {}, "errors": {}}
    for account in accounts:
        try:
            verdict["accounts"][account] = verify_account(driver, account, config, layouts, ids)
        except DriverError as exc:
            verdict["errors"][account] = scrub(str(exc))
    verdict["verdict"] = "pass" if (verdict["accounts"] and not verdict["errors"]) else "fail"
    return verdict


def to_source_map(verdict: dict) -> dict:
    return {
        "generated-at": verdict["verified-at"],
        "accounts": {a: {"sources": v["sources"]} for a, v in verdict["accounts"].items()},
    }


def to_findings(verdict: dict) -> dict:
    dead = [
        {"account": account, "layout": source["layout"],
         "why": source.get("notes") or "reported dead by the verification pass"}
        for account, value in verdict["accounts"].items()
        for source in value["sources"] if source["verdict"] == "dead"
    ]
    return {
        "verified-at": verdict["verified-at"],
        "accounts": {a: {"preconditions": v["preconditions"]}
                     for a, v in verdict["accounts"].items()},
        "dead-sources": dead,
    }


def write_artifacts(out_dir: Path, verdict: dict, log: CallLog, validate) -> list[str]:
    """Verdict and call log always land. Map and findings land only on a clean pass.

    A half-map is worse than no map: the poll would read it and skip in silence.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    def dump(name: str, payload) -> None:
        (out_dir / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(name)

    dump(VERDICT_FILE, verdict)
    (out_dir / CALL_LOG_FILE).write_text(log.text(), encoding="utf-8")
    written.append(CALL_LOG_FILE)

    if verdict["verdict"] != "pass":
        return written

    source_map = to_source_map(verdict)
    findings = to_findings(verdict)
    problems = (validate(source_map, SOURCE_MAP_ENTRY)
                + validate(findings, FINDINGS_ENTRY))
    if problems:
        verdict["verdict"] = "fail"
        verdict["errors"]["<schema>"] = problems
        dump(VERDICT_FILE, verdict)
        return written
    dump(SOURCE_MAP_FILE, source_map)
    dump(FINDINGS_FILE, findings)
    return written


# --------------------------------------------------------------------------
# selftest — every case green AND red against the bundled fixture
# --------------------------------------------------------------------------


def _fixture_base() -> dict:
    """One account, everything healthy. Account key is fixture data, not a real key."""
    return {
        "acct-a": {
            "folders": [
                {"id": "drv-legacy-1", "name": "FX-Legacy", "mimeType": FOLDER_MIME},
                {"id": "drv-tree-1", "name": "FX-Tree", "mimeType": FOLDER_MIME},
                {"id": "drv-tq-1", "name": "FX-Tactiq", "mimeType": FOLDER_MIME},
            ],
            "listings": {"drv-tq-1": [
                {"id": "f1", "name": "Standup 2026-09-24 09:30.txt", "mimeType": "text/plain"},
                {"id": "f2", "name": "Standup 2026-09-24 16:00.txt", "mimeType": "text/plain"},
            ]},
            "files": [
                {"id": "tx1", "mimeType": "application/vnd.google-apps.document",
                 "name": "FX Weekly - 2026/09/24 09:30 GMT-03:00 - FX-Transcript"},
            ],
        }
    }


def _fixture_config() -> dict:
    return {
        "accounts": ["acct-a"],
        "folder-names": {
            "legacy-meet-recordings": ["FX-Legacy"],
            "google-meet-tree": ["FX-Tree"],
            "tactiq-autosave": ["FX-Tactiq"],
        },
        "meet-window-days": 30,
        "transcript-tokens": ["FX-Transcript"],
        "naming-discriminator-pattern": r"\d{4}-\d{2}-\d{2}[ T]\d{1,2}[:.]\d{2}",
    }


def _pass_with(data: dict, config: dict, layouts, ids) -> dict:
    return run_pass(FixtureDriver(data, CallLog()), config["accounts"], config, layouts, ids)


def _addressed(verdict: dict) -> set:
    """Every account key the pass touched — the ones it resolved AND the ones it failed on."""
    return set(verdict["accounts"]) | set(verdict["errors"])


def selftest(seams_dir: Path) -> dict:
    """Each case states what it expects, then proves it goes RED when broken."""
    ids = precondition_ids(seams_dir)
    layouts = layout_names(seams_dir)
    validate = build_validator(seams_dir)
    config = _fixture_config()
    cases: list[dict] = []

    def case(arm: str, expect: str, green: bool, red: bool, detail: str = "") -> None:
        cases.append({"arm": arm, "expect": expect, "green": bool(green),
                      "red-when-broken": bool(red), "detail": detail})

    healthy = _pass_with(_fixture_base(), config, layouts, ids)
    healthy_pre = healthy["accounts"]["acct-a"]["preconditions"]

    # 1-3 — one case per folder layout.
    for layout in layouts:
        broken = _fixture_base()
        broken["acct-a"]["folders"] = [
            f for f in broken["acct-a"]["folders"]
            if f["name"] != config["folder-names"][layout][0]
        ]
        after = _pass_with(broken, config, layouts, ids)
        pid = LAYOUT_PRECONDITION[layout]
        case(f"folder:{layout}",
             f"{pid} is live with a Drive id when the folder exists, dead when it does not",
             healthy_pre[pid]["verdict"] == "live"
             and healthy["accounts"]["acct-a"]["sources"][layouts.index(layout)].get("folder-ref"),
             after["accounts"]["acct-a"]["preconditions"][pid]["verdict"] == "dead")

    # 4 — Meet is producing transcripts.
    no_tx = _fixture_base()
    no_tx["acct-a"]["files"] = []
    after = _pass_with(no_tx, config, layouts, ids)
    case(f"precondition:{TRANSCRIPT_PRECONDITION}",
         "live when the window holds a transcript, dead when it holds none",
         healthy_pre[TRANSCRIPT_PRECONDITION]["verdict"] == "live",
         after["accounts"]["acct-a"]["preconditions"][TRANSCRIPT_PRECONDITION]["verdict"] == "dead")

    # 5 — saved names discriminate two meetings on the same day.
    flat = _fixture_base()
    flat["acct-a"]["listings"]["drv-tq-1"] = [
        {"id": "f1", "name": "Standup 2026-09-24.txt", "mimeType": "text/plain"},
        {"id": "f2", "name": "Standup 2026-09-24.txt", "mimeType": "text/plain"},
    ]
    after = _pass_with(flat, config, layouts, ids)
    case(f"precondition:{NAMING_PRECONDITION}",
         "live when every saved name carries date AND time, dead when the time is missing",
         healthy_pre[NAMING_PRECONDITION]["verdict"] == "live",
         after["accounts"]["acct-a"]["preconditions"][NAMING_PRECONDITION]["verdict"] == "dead")

    # 5b — two layouts may never resolve to one folder id.
    collide = _fixture_base()
    for folder in collide["acct-a"]["folders"]:
        folder["id"] = "drv-same-1"
    collide_config = json.loads(json.dumps(config))
    after = _pass_with(collide, collide_config, layouts, ids)
    case("one-folder-per-layout",
         "each layout resolves to its OWN Drive folder; two layouts sharing one id "
         "fails the pass instead of writing a map that silently halves the poll",
         len({s["folder-ref"] for s in healthy["accounts"]["acct-a"]["sources"]
              if s.get("folder-ref")}) == len(
             [s for s in healthy["accounts"]["acct-a"]["sources"] if s.get("folder-ref")]),
         after["verdict"] == "fail" and "acct-a" in after["errors"])

    # 6 — every live source carries a Drive id; a name-only folder is refused.
    nameless = _fixture_base()
    for folder in nameless["acct-a"]["folders"]:
        folder["id"] = ""
    after = _pass_with(nameless, config, layouts, ids)
    live_entries = [s for s in healthy["accounts"]["acct-a"]["sources"] if s["verdict"] == "live"]
    case("id-not-name",
         "a live source always carries folder-ref; a folder with no id fails the pass "
         "instead of being recorded by display name",
         bool(live_entries) and all(s.get("folder-ref") for s in live_entries),
         after["verdict"] == "fail" and "acct-a" in after["errors"])

    # 7 — a refused call is an error, never a verdict of dead.
    refused = _fixture_base()
    refused["acct-a"]["files"] = "ERROR"
    after = _pass_with(refused, config, layouts, ids)
    case("call-failure-is-not-dead",
         "a call that could not be made fails the pass; it never reports the source dead",
         healthy["verdict"] == "pass" and not healthy["errors"],
         after["verdict"] == "fail" and "acct-a" in after["errors"])

    # 8 — the produced artifacts validate against their seam schemas.
    good_map = to_source_map(healthy)
    good_findings = to_findings(healthy)
    bad_map = json.loads(json.dumps(good_map))
    bad_map["accounts"]["acct-a"]["sources"][0]["layout"] = "not-a-layout"
    bad_findings = json.loads(json.dumps(good_findings))
    bad_findings["accounts"]["acct-a"]["preconditions"].pop(ids[0])
    case("seam-conformance",
         "the source map and the findings payload validate against the seam schemas, "
         "and a mutated one is refused",
         not validate(good_map, SOURCE_MAP_ENTRY) and not validate(good_findings, FINDINGS_ENTRY),
         bool(validate(bad_map, SOURCE_MAP_ENTRY)) and bool(validate(bad_findings, FINDINGS_ENTRY)))

    # 9 — a failed pass writes no source map, so no poll can read a half-map.
    # The broken arm has TWO accounts and loses only one: a one-account fixture
    # would leave an empty map that schema validation refuses anyway, and the
    # guard under test would never be what stopped the write.
    partial_data = _fixture_base()
    partial_data["acct-b"] = json.loads(json.dumps(partial_data["acct-a"]))
    partial_data["acct-b"]["files"] = "ERROR"
    partial_config = json.loads(json.dumps(config))
    partial_config["accounts"] = ["acct-a", "acct-b"]
    partial = _pass_with(partial_data, partial_config, layouts, ids)
    with tempfile.TemporaryDirectory() as tmp:
        ok_dir = Path(tmp) / "ok"
        written_ok = write_artifacts(ok_dir, json.loads(json.dumps(healthy)), CallLog(), validate)
        bad_dir = Path(tmp) / "bad"
        written_bad = write_artifacts(bad_dir, partial, CallLog(), validate)
    case("no-half-map",
         "a clean pass writes all four artifacts; a pass that reached one account of two "
         "writes the verdict and the call log and NO source map",
         SOURCE_MAP_FILE in written_ok and FINDINGS_FILE in written_ok
         and CALL_LOG_FILE in written_ok and VERDICT_FILE in written_ok,
         bool(partial["accounts"]) and bool(partial["errors"])
         and SOURCE_MAP_FILE not in written_bad and FINDINGS_FILE not in written_bad
         and VERDICT_FILE in written_bad and CALL_LOG_FILE in written_bad)

    # 10 — the accounts come from configuration, not from this file. "Addressed"
    # counts errors too: an account key baked in here would show up as a failed
    # call, not as a missing result, so a check on the results alone is blind.
    other = {"acct-z": _fixture_base()["acct-a"]}
    other_config = json.loads(json.dumps(config))
    other_config["accounts"] = ["acct-z"]
    renamed = _pass_with(other, other_config, layouts, ids)
    case("accounts-from-config",
         "the pass addresses exactly the account keys configuration names — no more, "
         "no fewer; an account key is never program text",
         _addressed(healthy) == {"acct-a"},
         _addressed(renamed) == {"acct-z"})

    # 11 — the vocabulary comes from the seam set, not from memory.
    case("ids-from-seams",
         "the five precondition ids and the three layouts are resolved through "
         "seams/index.csv at run time",
         len(ids) == 5 and len(layouts) == 3 and set(healthy_pre) == set(ids),
         _ids_move_with_the_seams(seams_dir))

    # 12 — the call log carries names only.
    leaky = CallLog()
    leaky.record("acct-a", "drive.search", 1,
                 "RefreshError: the stored grant at /fixture/redaction-probe is invalid")
    case("call-log-carries-no-paths",
         "an absolute path in a tool's error text never reaches the call log",
         "/fixture/" not in leaky.text(),
         "<path>" in leaky.text())

    ok = all(c["green"] and c["red-when-broken"] for c in cases)
    return {
        "cases": cases,
        "discriminating": all(c["red-when-broken"] for c in cases),
        "ok": ok,
    }


def _ids_move_with_the_seams(seams_dir: Path) -> bool:
    """Red arm for case 11: rename an id in a COPY of the seam set and watch it move."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "seams"
        shutil.copytree(seams_dir, copy)
        schema_path = copy / "findings-payload.schema.json"
        text = schema_path.read_text(encoding="utf-8").replace(
            "google-meet-tree", "mutated-precondition-id")
        schema_path.write_text(text, encoding="utf-8")
        return "mutated-precondition-id" in precondition_ids(copy)


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------


def cmd_run(args) -> int:
    seams_dir = args.seams or (Path(__file__).resolve().parent.parent / "seams")
    config_dir = args.config_dir or os.environ.get(CONFIG_ROOT_ENV)
    if config_dir is None:
        refuse("no config-module home could be resolved",
               f"pass --config-dir, or set {CONFIG_ROOT_ENV}")
    config_dir = Path(config_dir)
    out_dir = Path(args.out_dir) if args.out_dir else runtime_dir(config_dir)

    ids = precondition_ids(seams_dir)
    layouts = layout_names(seams_dir)
    validate = build_validator(seams_dir)
    config = load_config(config_dir)
    accounts = [a for a in config["accounts"] if not args.account or a in args.account]
    unknown = [a for a in (args.account or []) if a not in config["accounts"]]
    if unknown:
        refuse(f"account(s) not declared in {CONFIG_FILE}: {', '.join(unknown)}",
               f"add them to 'accounts' in {CONFIG_FILE}, or drop --account")

    # The Google CLI's location is configuration too: a path typed into product
    # code is an owner-specific value, and this tree carries none.
    declared = config.get("gtools-path")
    if not declared:
        refuse(f"{CONFIG_FILE} declares no gtools-path",
               "'gtools-path' is the Google CLI's path, absolute or workspace-relative")
    gtools = Path(declared)
    if not gtools.is_absolute():
        root = workspace_root(Path(__file__).resolve())
        gtools = (root / declared) if root else gtools
    if not gtools.is_file():
        refuse("the gtools CLI is not at the declared gtools-path",
               f"correct 'gtools-path' in {CONFIG_FILE}")

    log = CallLog()
    verdict = run_pass(GtoolsDriver(gtools, log), accounts, config, layouts, ids)
    written = write_artifacts(out_dir, verdict, log, validate)

    if args.json:
        print(json.dumps({"verdict": verdict, "written": written}, indent=2, ensure_ascii=False))
    else:
        print(f"verified-at: {verdict['verified-at']}")
        for account, value in verdict["accounts"].items():
            print(f"[{account}]")
            for pid in ids:
                entry = value["preconditions"][pid]
                print(f"  {entry['verdict']:5}  {pid}  — {entry.get('detail', '')}")
        for account, why in verdict["errors"].items():
            print(f"[{account}] ERROR: {why}")
        print(f"written: {', '.join(written)}")
        print(f"verdict: {verdict['verdict']}")
    return EXIT_OK if verdict["verdict"] == "pass" else EXIT_FAIL


def cmd_selftest(args) -> int:
    seams_dir = args.seams or (Path(__file__).resolve().parent.parent / "seams")
    result = selftest(seams_dir)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for case in result["cases"]:
            mark = "PASS" if case["green"] and case["red-when-broken"] else "FAIL"
            print(f"  {mark}  {case['arm']}")
            print(f"        expect: {case['expect']}")
            if mark == "FAIL":
                print(f"        green={case['green']} red-when-broken={case['red-when-broken']}")
        print(f"discriminating: {result['discriminating']}")
        print("ok" if result["ok"] else "NOT ok")
    return EXIT_OK if result["ok"] else EXIT_FAIL


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_access.py",
        description="The pre-first-poll verification pass: reach every configured account, pin "
                    "every watched folder by Drive id, write the four grounding artifacts. "
                    "Never probes a fact settled by owner attestation.")
    parser.add_argument("--json", action="store_true", help="one JSON object on stdout")
    subs = parser.add_subparsers(dest="operation", required=True)

    run_p = subs.add_parser("run", help="verify the configured accounts and write the artifacts")
    run_p.add_argument("--account", action="append", metavar="KEY",
                       help="limit the pass to this configured account key (repeatable)")
    run_p.add_argument("--config-dir", type=Path, default=None,
                       help=f"component config dir holding {CONFIG_FILE} "
                            f"(default: ${CONFIG_ROOT_ENV})")
    run_p.add_argument("--out-dir", type=Path, default=None,
                       help="where the four artifacts land (default: the installation's "
                            ".rbtv/runtime/<component>/ beside the config dir)")
    run_p.add_argument("--seams", type=Path, default=None,
                       help="seam set the vocabulary and the artifacts bind to "
                            "(default: ../seams beside this tool)")
    run_p.set_defaults(func=cmd_run)

    st_p = subs.add_parser("selftest", help="prove every case green AND red on a fixture")
    st_p.add_argument("--seams", type=Path, default=None)
    st_p.set_defaults(func=cmd_selftest)

    args = parser.parse_args(argv)
    args.json = args.json or getattr(args, "json", False)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
