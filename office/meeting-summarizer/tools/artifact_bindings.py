#!/usr/bin/env python3
"""Download a detected job set and bind every Drive ref to local text bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import source_adapter


def build(jobs: list[dict], driver: source_adapter.GtoolsDriveDriver,
          account_keys: dict[str, str], out_dir: Path) -> dict:
    """Return the artifact-reader map; leave no map for an incomplete download."""
    out_dir.mkdir(parents=True, exist_ok=False)
    bindings: dict[str, dict] = {}
    for job in jobs:
        for record in job["source-set"]:
            ref = record["drive-ref"]
            if ref in bindings:
                continue
            email = record["account"]
            if email not in account_keys:
                raise ValueError(f"no watched account key for {email}")
            output = out_dir / (hashlib.sha256(ref.encode("utf-8")).hexdigest() + ".txt")
            downloaded = driver.download_text(account_keys[email], ref, output)
            bindings[ref] = {"location": downloaded["path"],
                             "name": downloaded["name"],
                             "media-type": downloaded["mimeType"]}
    return {"artifacts": bindings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", required=True, type=Path,
                        help="JSON list of per-meeting jobs or detection tick output with jobs")
    parser.add_argument("--out-dir", required=True, type=Path,
                        help="new directory for downloaded text and bindings.json")
    parser.add_argument("--config-dir", required=True, type=Path,
                        help="meeting-summarizer config module home")
    args = parser.parse_args(argv)

    data = json.loads(args.jobs.read_text(encoding="utf-8"))
    jobs = data["jobs"] if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        parser.error("--jobs must contain a list or an object with a jobs list")
    sources = json.loads((args.config_dir / "sources.json").read_text(encoding="utf-8"))
    gtools = Path(sources["gtools-path"])
    if not gtools.is_absolute():
        gtools = source_adapter.workspace_root(Path(__file__).resolve()) / gtools
    emails = source_adapter.account_emails(gtools, sources["accounts"])
    keys = {email: key for key, email in emails.items()}
    bindings = build(jobs, source_adapter.GtoolsDriveDriver(gtools), keys, args.out_dir)
    path = args.out_dir / "bindings.json"
    path.write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"map": str(path), "artifacts": len(bindings["artifacts"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
