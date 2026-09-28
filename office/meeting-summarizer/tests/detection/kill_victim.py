#!/usr/bin/env python3
"""A tick that hangs mid-flight, so the kill arm has something real to kill.

Run as a child process by the kill-recovery arm. It runs one genuine tick, and
its handler blocks forever with the meeting's claim held — the state a tick is in
when the box goes down. The parent SIGKILLs it there.

It lives beside the arms rather than in the product tree on purpose: a hang is
test machinery, and product code that can be told to hang is a defect.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import detection_cycle as dc  # noqa: E402
import source_adapter as sa  # noqa: E402


def main() -> int:
    config_dir, fixture, source_map, marker, now = sys.argv[1:6]
    listing = json.loads(Path(fixture).read_text(encoding="utf-8"))
    env = dc.load_env(
        Path(config_dir),
        source_map=json.loads(Path(source_map).read_text(encoding="utf-8")),
        account_emails=listing["account-emails"],
    )

    def handle(job: dict) -> dict:
        Path(marker).write_text(job["meeting-key"], encoding="utf-8")
        time.sleep(600)
        raise AssertionError("the kill arm never lets this line run")

    dc.run_tick(env, datetime.fromisoformat(now), sa.FixtureDriveDriver(listing), handler=handle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
