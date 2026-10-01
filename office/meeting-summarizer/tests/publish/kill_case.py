#!/usr/bin/env python3
"""The partial-filing victim: a cycle killed after the summary lands, before the push.

The kill is a real SIGKILL of a real process (`os.kill(os.getpid(), SIGKILL)`),
not an exception a `finally:` could still tidy up after. A cycle that could clean
up after itself would prove nothing about recovery.
"""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import harness as H          # noqa: E402
import mutations             # noqa: E402
import publish_job as P      # noqa: E402

mutations.apply_from_env()


def main() -> int:
    scratch_root, job_name = sys.argv[1], sys.argv[2]
    scratch = H.Scratch(Path(scratch_root))
    job = H.job(job_name)
    key = job["meeting-key"]

    def die(*_args, **_kwargs):
        # Windows has no SIGKILL; SIGTERM there is TerminateProcess, an equally hard kill.
        os.kill(os.getpid(), getattr(signal, "SIGKILL", signal.SIGTERM))

    # The kill lands at the push: the summary and its transcripts are on disk and
    # committed, publication has not happened, and nothing downstream of it has.
    P.push = die
    P.run_cycle(job, config_root=H.CONFIG_ROOT, checkout_root=scratch.checkouts,
                state=scratch.state, transcripts=H.transcripts("meet"),
                summarize=H.Summarizer(f"# resumo\n\nmeeting-key: {key}\n\nbody\n"),
                bus=H.Bus())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
