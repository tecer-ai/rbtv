"""Shared ground for the detection-cycle arms.

Every arm runs against a throwaway config-module home under `tmp_path`, so the
stores a tick writes are this test's and nothing else's, and against a FIXTURE
Drive listing rather than live Drive. Nothing here reaches the network.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[2]
TOOLS = WORKFLOW / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The tick instants the arms fire at. Fixed, never `now`: a probe whose answer
# moves with the clock proves nothing on the day it is re-run.
FIRST_TICK = datetime.fromisoformat("2026-08-20T12:10:00-03:00")


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """A writable config-module home carrying only what the cycle reads."""
    home = tmp_path / "config-home"
    home.mkdir()
    for name in ("destination-routing.json", "sources.json", "summarize.json"):
        shutil.copyfile(FIXTURES / "config" / name, home / name)
    return home


def watch(config_dir: Path, accounts: list) -> None:
    """Point the config home's watch list (sources.json `accounts`) at these accounts."""
    path = config_dir / "sources.json"
    sources = json.loads(path.read_text(encoding="utf-8"))
    sources["accounts"] = list(accounts)
    path.write_text(json.dumps(sources, indent=2), encoding="utf-8")


@pytest.fixture
def env(config_dir: Path):
    import detection_cycle as dc

    listing = load("drive-listing.json")
    return dc.load_env(config_dir, source_map=load("source-map.json"),
                       account_emails=listing["account-emails"])


@pytest.fixture
def driver():
    import source_adapter as sa

    return sa.FixtureDriveDriver(load("drive-listing.json"))


def filed_handler(destination: dict | None = None):
    """A handler that files every job. Stands in for m6, which does not exist yet."""
    destination = destination or {"repo": "EXAMPLE-repo", "path": "EXAMPLE/notes/summary.md"}

    def handle(job: dict) -> dict:
        return {
            "kind": "per-meeting-outcome",
            "meeting-key": job["meeting-key"],
            "outcome": "amended" if job["disposition"] == "amend" else "filed",
            "destination": destination,
            "at": "2026-08-20T12:11:00-03:00",
        }

    return handle


def failing_handler(calls: list):
    def handle(job: dict) -> dict:
        calls.append(job["meeting-key"])
        return {
            "kind": "per-meeting-outcome",
            "meeting-key": job["meeting-key"],
            "outcome": "failed",
            "at": "2026-08-20T12:11:00-03:00",
        }

    return handle
