"""Shared ground for the detection-cycle arms.

Every arm runs against a throwaway installation under `tmp_path` (its
`.rbtv/config/meeting-summarizer/` and an agent folder), so the stores a tick
writes are this test's and nothing else's, and against a FIXTURE Drive listing
rather than live Drive. Nothing here reaches the network.
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


def scratch_installation(root: Path) -> Path:
    """An installation's config-module home under `root`, carrying only what the cycle reads."""
    home = root / ".rbtv" / "config" / "meeting-summarizer"
    home.mkdir(parents=True)
    for name in ("destination-routing.json", "sources.json", "summarize.json"):
        shutil.copyfile(FIXTURES / "config" / name, home / name)
    return home


@pytest.fixture
def agent_home(tmp_path: Path, monkeypatch) -> Path:
    """The agent folder the turn names; its `state/` holds the agent's live data."""
    home = tmp_path / ".rbtv" / "agents" / "EXAMPLE-agent"
    (home / "state").mkdir(parents=True)
    monkeypatch.setenv("RBTV_AGENT_HOME", str(home))
    return home


@pytest.fixture
def config_dir(tmp_path: Path, agent_home: Path) -> Path:
    """A writable config-module home inside a throwaway installation."""
    return scratch_installation(tmp_path)


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
