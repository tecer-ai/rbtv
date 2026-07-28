#!/usr/bin/env python3
"""probe-suite-scheduled — the thing that FIRES the verification machinery, and says so every time.

G-221 ruling (leader, 2026-07-28 #1373): A+B. This is B — a trigger that lives OUTSIDE the daemon.

⚠⚠ WHY OUTSIDE, and it is not "because the daemon is busy": A CHECKER THAT LIVES INSIDE THE SYSTEM
IT CHECKS SHARES ITS FAILURE MODE (bars.md 11's family). If the daemon stops, an in-daemon job stops
with it, AND ITS SILENCE LOOKS EXACTLY LIKE HEALTH. Measured the same day this was written:
`selfheal-watch` and `selfheal-room` — the self-healing jobs — last fired 2026-07-27T16:31:32Z and
were dead for 23 hours with nothing reporting it (G-254). The in-daemon job (A) is ALSO ruled and is
NOT replaced by this one; B is not a stopgap and must never be called one.

⚠⚠ THE BINDING PROPERTY, and it is the whole reason this file is more than a cron line
(leader #1373): IT EMITS A POSITIVE LIVENESS SIGNAL ON EVERY FIRE — GREEN AS WELL AS RED — CARRYING
ITS INSTANT. A trigger that speaks only when something is RED is INDISTINGUISHABLE FROM A DEAD ONE.
Without this we would have built the fourth silent instrument inside the change meant to end them.

⇒ Concretely: `latest.json` is rewritten on EVERY fire, whatever the outcome, including when the
suite crashes or times out. It carries `fired_at`, `interval_seconds` and `stale_after` SO THAT A
READER CAN TELL "DEAD" FROM "QUIET" WITHOUT KNOWING THE SCHEDULE OUT OF BAND. A consumer that has to
already know the cadence to interpret the artifact is a consumer that will read a stopped timer as
a quiet one.

WHO READS IT (half 2 of the ruling): the chief-of-staff, on its per-pass sweep — a PULL mechanism
that already exists and demonstrably fires. That wiring is a seat-descriptor change and is the
LEADER'S to arrange. ⚠ This script MUST NOT be extended to notify anyone itself: the obvious route
is `watch.py`, which is `ignite/team-kit/` and barred to this seat (r-engineer-not-team-kit).

COVERAGE — derived, never hand-listed:
    dirs to run = every discovered probe dir MINUS the excluded ones
so a NEW probe directory is covered automatically. ⚠ A HAND-WRITTEN DIR LIST SILENTLY STOPS COVERING
WHATEVER IS ADDED LATER, and the author of this file proved it the same day: a 13-dir hand list read
`discovered: 98` against an expectation of 97 and was briefly misread as the PAID probe having run.
The completeness assertion below exists because of that: attempted + excluded MUST equal discovered,
or the run is reported as a COVERAGE MISMATCH rather than as a verdict.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

# Resolved from __file__, NEVER from cwd. Four separate wrong-directory results landed in this run
# in one day — a clean result taken from the wrong place (bars.md 10).
DEPLOY_DIR = os.path.dirname(os.path.abspath(__file__))
IGNITE_ROOT = os.path.dirname(DEPLOY_DIR)
SUITE = os.path.join(DEPLOY_DIR, 'probe-suite.js')


def find_workspace_root(start):
    """Walk up to the directory that ROOTS `.rbtv/`. That is the definition of the workspace root.

    ⚠⚠ THE FIRST VERSION OF THIS COUNTED HOPS — `os.path.join(IGNITE_ROOT, '..', '..', '..')` —
    COPIED FROM `probe-suite.js`, WHICH COUNTS FROM THE *REPO* ROOT WHILE THIS FILE SITS ONE LEVEL
    DEEPER IN `ignite/`. It resolved to `3-resources/`, silently CREATED `3-resources/.rbtv/`, and
    wrote the liveness artifact there — the one file whose entire purpose is that a reader finds it
    at a known path. Every check I had passed: the units substituted, the runner was executable, the
    suite went green. **Nothing detects an artifact that was successfully written to the wrong
    place.** It was caught only by looking for the file where I had told its consumer to read.

    ⇒ THE REPAIR IS NOT "ADD ONE MORE `..`" — that is the same fragile counting, correct until the
    module moves. Deriving the root by its DEFINING PROPERTY survives any move of this file.
    """
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, '.rbtv')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise RuntimeError(
                f'no workspace root above {start}: walked to the filesystem root without finding a '
                'directory containing .rbtv/'
            )
        d = parent


WORKSPACE_ROOT = find_workspace_root(DEPLOY_DIR)
RUNTIME_DIR = os.path.join(WORKSPACE_ROOT, '.rbtv', 'runtime', 'probe-suite')
LATEST = os.path.join(RUNTIME_DIR, 'latest.json')

# ⚠ EXCLUDED BY CONSTRUCTION, WITH ITS REASON IN THE SAME PLACE AS THE EXCLUSION (leader ratified).
# Not a flag someone remembers to pass: this probe makes real PAID `claude` calls on every run
# (G-213), and a scheduled trigger would bill them on every fire, unattended, forever.
EXCLUDED_DIRS = {
    'capabilities/sub-agent-dispatch/probes': 'makes real PAID claude API calls on every run (G-213)',
}

DEFAULT_INTERVAL_SECONDS = 3600
# How long after a fire the artifact should be considered stale. Deliberately > interval so a single
# slow or skipped fire is not read as death, and deliberately WRITTEN INTO THE ARTIFACT so the
# reader needs no out-of-band knowledge of the cadence.
STALE_MULTIPLIER = 2.5


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def write_latest(payload):
    """Atomic, and it happens on EVERY path including failure. This function IS the liveness signal."""
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=RUNTIME_DIR, prefix='.latest-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write('\n')
        os.replace(tmp, LATEST)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def discover():
    """Every probe the suite can see, as repo-relative paths."""
    out = subprocess.run(
        ['node', SUITE, '--list'],
        cwd=IGNITE_ROOT, capture_output=True, text=True, timeout=120,
    )
    probes, discovered = [], None
    for line in out.stdout.splitlines():
        line = line.strip()
        m = re.match(r'^discovered:\s*(\d+)$', line)
        if m:
            discovered = int(m.group(1))
            continue
        if line.endswith('.js') or line.endswith('.py'):
            probes.append(line)
    if discovered is None:
        raise RuntimeError(f'probe-suite --list printed no discovery count (exit {out.returncode})')
    # The list and the count must agree, or every number below is derived from a partial parse.
    if len(probes) != discovered:
        raise RuntimeError(f'parsed {len(probes)} probe paths but --list says {discovered}')
    return probes, discovered


def main():
    started = time.time()
    interval = int(os.environ.get('PROBE_SUITE_INTERVAL_SECONDS', DEFAULT_INTERVAL_SECONDS))
    payload = {
        'fired_at': now_iso(),
        'interval_seconds': interval,
        'stale_after_seconds': int(interval * STALE_MULTIPLIER),
        'verdict': 'UNKNOWN',
        'note': 'run did not complete; this artifact was written by the failure path',
    }

    try:
        probes, discovered = discover()

        all_dirs = sorted({os.path.dirname(p) for p in probes})
        run_dirs = [d for d in all_dirs if d not in EXCLUDED_DIRS]
        excluded_probes = [p for p in probes if os.path.dirname(p) in EXCLUDED_DIRS]

        # An excluded dir that has stopped existing is not a safe no-op: it means the exclusion is
        # no longer doing anything and nobody would know. Say so rather than silently covering it.
        missing_exclusions = [d for d in EXCLUDED_DIRS if d not in all_dirs]

        proc = subprocess.run(
            ['node', SUITE] + [arg for d in run_dirs for arg in ('--dir', d)],
            cwd=IGNITE_ROOT, capture_output=True, text=True, timeout=3600,
        )
        tail = proc.stdout[-4000:]

        def num(field):
            m = re.search(rf'^{field}:\s*(\d+)$', tail, re.M)
            return int(m.group(1)) if m else None

        attempted, passed, failed = num('attempted'), num('passed'), num('failed')
        run_discovered = num('discovered')
        verdict_m = re.search(r'SUITE-COMPLETE verdict=(\w+)', tail)
        summary_m = re.search(r'^summary:\s*(\S+)$', tail, re.M)

        # ⚠ THE COMPLETENESS ASSERTION. Everything attempted, plus everything deliberately excluded,
        # must account for everything discovered. This is what turns "98 ran" from a number into
        # coverage — and it is the exact check whose absence let a 97-vs-98 discrepancy be misread.
        expected = discovered - len(excluded_probes)
        coverage_ok = (run_discovered == expected) and (attempted == expected)

        payload.update({
            'verdict': (verdict_m.group(1) if verdict_m else 'INCOMPLETE'),
            'exit_code': proc.returncode,
            'discovered_total': discovered,
            'expected_to_run': expected,
            'attempted': attempted,
            'passed': passed,
            'failed': failed,
            'excluded': [{'probe': p, 'why': EXCLUDED_DIRS[os.path.dirname(p)]} for p in excluded_probes],
            'coverage_ok': coverage_ok,
            'summary_path': summary_m.group(1) if summary_m else None,
            'duration_seconds': round(time.time() - started, 1),
            'note': None,
        })

        if missing_exclusions:
            payload['exclusion_dirs_not_found'] = sorted(missing_exclusions)
            payload['coverage_ok'] = False

        # ⚠⚠ THE ARTIFACT MUST LAND BESIDE THE SUITE'S OWN SUMMARY. This is a SECOND, INDEPENDENT
        # derivation of where the runtime dir is: `summary_path` is produced by probe-suite.js from
        # ITS root, this file resolves the workspace root from ITS own location, and the two must
        # agree. When they did not, the artifact was silently written into a `.rbtv/` this script
        # had created one level up from the real one — successfully written, and nowhere its reader
        # would ever look. A single derivation cannot catch that; a disagreement between two can.
        if payload.get('summary_path'):
            suite_runtime_dir = os.path.dirname(os.path.abspath(payload['summary_path']))
            if os.path.abspath(RUNTIME_DIR) != suite_runtime_dir:
                payload['verdict'] = 'ARTIFACT-PATH-MISMATCH'
                payload['coverage_ok'] = False
                payload['note'] = (
                    f'this runner resolved the runtime dir to {RUNTIME_DIR} but the suite wrote its '
                    f'summary to {suite_runtime_dir}. The liveness artifact is not where its reader '
                    'looks, so no verdict is reported for this run.'
                )

        if not coverage_ok:
            payload['verdict'] = 'COVERAGE-MISMATCH'
            payload['note'] = (
                f'discovered {discovered}, excluded {len(excluded_probes)}, so {expected} should have '
                f'run; the suite reports discovered={run_discovered} attempted={attempted}. '
                'A verdict is NOT reported for this run: the number of probes that ran is not the '
                'number that exist.'
            )

    except Exception as exc:  # noqa: BLE001 — every failure must still leave a liveness signal
        payload['verdict'] = 'ERROR'
        payload['error'] = f'{type(exc).__name__}: {exc}'
        payload['duration_seconds'] = round(time.time() - started, 1)
        payload['note'] = 'the trigger fired and failed — this is a LIVE trigger reporting a problem, not a dead one'

    write_latest(payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload['verdict'] == 'GREEN' else 1


if __name__ == '__main__':
    sys.exit(main())
