#!/usr/bin/env python3
"""One arm of the same-day collision probe, run as its own PROCESS.

Criterion 4 is not provable in one process. The defect it exists for is a
same-cycle race on a shared destination in which last-writer-wins, and a
sequential probe walks straight past it. So each meeting gets a process of its
own, and both wait on a file barrier until every arm has arrived — the overlap is
arranged, not hoped for.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import harness as H          # noqa: E402
import mutations             # noqa: E402
import publish_job as P      # noqa: E402

mutations.apply_from_env()


def barrier(path: Path, arms: int, mine: str, timeout: float = 30.0) -> float:
    """Every arm announces itself, then all of them leave together."""
    path.mkdir(parents=True, exist_ok=True)
    (path / mine).write_text("here", encoding="utf-8")
    deadline = time.monotonic() + timeout
    while len(list(path.iterdir())) < arms and time.monotonic() < deadline:
        time.sleep(0.005)
    return time.time()


def main() -> int:
    scratch_root, job_name, arms, mine = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    scratch = H.Scratch(Path(scratch_root))
    job = H.job(job_name)
    key = job["meeting-key"]
    summarizer = H.Summarizer(f"# resumo\n\nmeeting-key: {key}\n\nbody of {key}\n")
    released = barrier(Path(scratch_root) / "barrier", arms, mine)
    started = time.time()
    result = P.run_cycle(job, config_root=H.CONFIG_ROOT, checkout_root=scratch.checkouts,
                         state=scratch.state, transcripts=H.transcripts("meet"),
                         summarize=summarizer, bus=H.Bus())
    finished = time.time()
    print(json.dumps({"arm": mine, "released-at": released, "started-at": started,
                      "finished-at": finished, "result": result}, default=str))
    return 0 if result["outcome"] in ("filed", "amended") else 1


if __name__ == "__main__":
    raise SystemExit(main())
