#!/usr/bin/env python3
"""probe-g158-stale-code — does anything notice a kit file changing UNDER a running process?

WHAT IT PROVES, and why watch.py's selftest does not already prove it. The selftest corrupts a
stamped sha and checks the verdict: that exercises the READER. The decision this fix turns on is on
the WRITER side — the fingerprint is captured at IMPORT, once, and never recomputed. Only changing
a file after import can tell those two designs apart, and the wrong one is the one a reasonable
person writes.

  arm A (the shipped fix)  — must DETECT the change
  arm B (the mutation)     — recomputes the fingerprint when it stamps, and must FAIL to detect it,
                             because hashing a file against itself can never disagree. It reports a
                             healthy loop over the exact defect: a green harness in the fix for the
                             green-harness class.

A probe that only ran arm A would pass just as happily over a detector that can never fire.

HERMETIC BY CONSTRUCTION, and this is a safety property, not tidiness. The experiment MUTATES a
coord.py, and coord.py is the only messaging path every seat in a room shares — a probe that edited
the live one would take the room down for as long as it ran, and forever if it died mid-way. So it
copies the kit to a temp dir and does all of its work on the copy. It never writes inside the kit
it was launched from. Run it from anywhere.

  python3 probes/probe-g158-stale-code.py      # exit 0 = the detector discriminates
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
INNER = "G158_PROBE_INNER"


def inner():
    """Runs INSIDE the temp kit copy. Import, change a file, stamp, read the verdict back."""
    kit = Path(__file__).resolve().parent
    sys.path.insert(0, str(kit))
    import watch
    import coord

    base = Path(tempfile.mkdtemp()) / "coordination"
    base.mkdir(parents=True)

    target = kit / "coord.py"
    original = target.read_bytes()
    # The moment the defect models: a fix lands while the process is running. Python bound the
    # source at import, so this process can never pick it up — it just keeps heartbeating.
    target.write_bytes(original + b"\n# a fix landed while this process was running\n")
    try:
        if os.environ.get("MUTATION") == "1":
            watch.LOADED_CODE = watch._loaded_code_fingerprint()
        watch.save_heartbeat(base, 10)
        hb = coord.watcher_heartbeat(base)
        print(json.dumps({"code_known": hb.get("code_known"),
                          "code_drifted": hb.get("code_drifted")}))
    finally:
        target.write_bytes(original)
    return 0


def main():
    if os.environ.get(INNER) == "1":
        return inner()

    tmp = Path(tempfile.mkdtemp(prefix="g158-kit-"))
    try:
        for py in KIT.glob("*.py"):
            shutil.copy2(py, tmp / py.name)
        shutil.copy2(Path(__file__).resolve(), tmp / "inner.py")
        if not (tmp / "coord.py").exists() or not (tmp / "watch.py").exists():
            print("REFUSED: the kit copy is missing coord.py or watch.py — nothing to probe.",
                  file=sys.stderr)
            return 2

        results = {}
        for arm, mutation in (("A-fix", "0"), ("B-mutation", "1")):
            env = dict(os.environ, **{INNER: "1", "MUTATION": mutation})
            r = subprocess.run([sys.executable, str(tmp / "inner.py")],
                               capture_output=True, text=True, timeout=180, env=env, cwd=str(tmp))
            if r.returncode != 0:
                print(f"FAIL {arm}: inner run exited {r.returncode}\n{r.stderr.strip()}",
                      file=sys.stderr)
                return 1
            try:
                results[arm] = json.loads(r.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                print(f"FAIL {arm}: inner run printed no verdict:\n{r.stdout}", file=sys.stderr)
                return 1

        a, b = results["A-fix"], results["B-mutation"]
        a_detects = a.get("code_known") is True and "coord.py" in (a.get("code_drifted") or [])
        b_detects = bool(b.get("code_drifted"))

        print(f"A (shipped fix): code_known={a['code_known']} drifted={a['code_drifted']}")
        print(f"B (recompute-at-stamp mutation): code_known={b['code_known']} "
              f"drifted={b['code_drifted']}")
        if a_detects and not b_detects:
            print("PASS — the detector fires on a file changed under a running process, and the "
                  "recompute-at-stamp design does NOT. The import-time capture is load-bearing.")
            return 0
        if not a_detects:
            print("FAIL — the shipped fix did not detect a file changed under a running process. "
                  "The detector cannot fire; that is G-158 itself.", file=sys.stderr)
        else:
            print("FAIL — the mutation ALSO detected it, so this probe does not discriminate the "
                  "two designs and proves nothing about the import-time capture.", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
