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

WHO ACTUALLY READS IT — corrected 2026-08-10 (task 7.107). The text that stood here claimed the
chief-of-staff pulls this on its per-pass sweep, "a PULL mechanism that already exists and
demonstrably fires". ⚠⚠ NO SUCH MECHANISM EXISTS — verified absent across all 50 seat directories
(2026-07-29). That false sentence is what kept a RED verdict sitting unread for ~22h: a reader
checking whether RED reaches anyone found a line saying it did. The TRUE delivery state:
  · WRITTEN — `latest.json` (rewritten on every fire) plus the per-run summary. Both land on disk.
  · READ — the CMP-28 daemon-watchdog
    (`ignite/capabilities/daemon-watchdog/tool/rbtv-ignite-watchdog`, `probe_probe_suite`) reads
    this artifact for BOTH liveness AND the correctness verdict: a live suite reporting RED is
    delivered to the operator as an `alarm` (no restart fixes a failing probe). This CLOSED the
    gap that let a RED sit unread — owner ruling `d-probe-suite-verdict-delivery` (2026-08-10),
    part 2. Part 1 of that ruling gave the runner an INOPERATIVE class (exit 2) distinct from
    `failed`, so the verdict the watchdog reads is meaningful and not permanently RED on the
    by-design unattended refusals (task 7.107).
⚠ This script MUST NOT be extended to notify anyone itself: the obvious route
is `watch.py`, which is `ignite/coord/` and barred to this seat (r-engineer-not-team-kit).

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
import shutil
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

# ⚠ THE BINARIES A RUN ACTUALLY SPAWNS — `node` (this file spawns the suite with it), `python3`
# (probe-suite.js spawns every `.py` probe with it, :182) and `claude` (probes that shell out to
# the CLI). Measured 2026-08-10 (task 7.685): over a plain SSH shell PATH lacks `~/.local/bin`,
# `claude` is ENOENT, and FOUR probes report `spawnSync claude ENOENT` REDS with nothing naming the
# cause — a 6-minute run that reads as four defects. The systemd unit sets its own PATH (it carries
# `%h/.local/bin`) and passes this check unchanged.
# ⚠ REFUSING IS NOT NOTIFYING (this file's standing bar, header): nothing is sent to anyone — the
# run simply does not start, and the refusal rides the SAME liveness artifact every other outcome
# does, so a timer whose environment broke reports itself instead of emitting four false reds.
REQUIRED_BINARIES = ('node', 'python3', 'claude')

# How many past runs stay on disk. Each fire leaves `<stamp>.txt` + `<stamp>-captures/` and nothing
# ever removed them: measured 2026-08-10 on the VPS, 1015 stamps / 981 capture trees / 231 MB
# (task 7.698). 48 = two days of hourly fires — enough to walk back over a night's reds, bounded.
# The daemon's own retention (task 7.13, runtime/retention.js) does NOT cover this: it enumerates
# the PER-MACHINE state root's classes, and this pile is per-WORKSPACE (.rbtv/runtime/).
RETAINED_RUNS = int(os.environ.get('PROBE_SUITE_RETAINED_RUNS', 48))

# ⚠ EXCLUDED BY CONSTRUCTION, WITH ITS REASON IN THE SAME PLACE AS THE EXCLUSION (leader ratified).
# ⚠ THE SHAPE IS A DICT, `{dir: why}` — the `why` is read below into `latest.json`'s `excluded`
# block, so an exclusion carries its reason to the artifact's reader and not only to this file.
# Written out because the shape was NOT stated here and the next author wrote a SET: subscripting it
# raised `TypeError: 'set' object is not subscriptable` inside the payload build, the whole hourly
# run reported `verdict: ERROR`, and the exclusion meant to drop ONE directory from coverage dropped
# the VERDICT for every probe on the box (measured on the 2026-08-08T20:00:13Z fire).
#
# Empty since `r-seats-only-architecture` (2026-08-06) deleted capabilities/sub-agent-dispatch/
# (its probes made real PAID claude calls, G-213); the mechanism stays for the next paid probe.
# capabilities/goal-creation-request/probes was excluded on 2026-08-08 for the same paid-call class
# and is RESTORED here (task 7.553 criterion 3). `probe-planning-entry.py` (the probe whose
# `claude` stub this restoration was about) was itself DELETED in task 7.778, along with
# `probe-sensor-start.py` and `probe-launcher-attribution.py` — all three asserted the deleted
# `workflow_launcher.py` (see goal-creation-request.md § the three surviving probes). The three
# probes that remain at this path (probe-goal-creation-request.py, probe-goal-type-carrier.py,
# probe-execution-mode-birth.py) make no real claude/execFileSync call today (checked).
EXCLUDED_DIRS = {}
# ⚠ MECHANIZED, not documented: on 2026-08-08 an interim exclusion wrote a SET here while :202
# reads this as a MAPPING, so every hourly fire died `TypeError: 'set' object is not subscriptable`
# and the whole box lost its verdict for two hours. A prose note would not have caught it — while
# this dict is EMPTY, :202 never evaluates, so the shape is unexercised until the day it matters.
assert isinstance(EXCLUDED_DIRS, dict), "EXCLUDED_DIRS must be a dict {dirname: why} — :202 subscripts it"

DEFAULT_INTERVAL_SECONDS = 3600
# How long after a fire the artifact should be considered stale. Deliberately > interval so a single
# slow or skipped fire is not read as death, and deliberately WRITTEN INTO THE ARTIFACT so the
# reader needs no out-of-band knowledge of the cadence.
STALE_MULTIPLIER = 2.5


def preflight():
    """Refuse at the start, naming the binary and the PATH searched. NEVER notifies anyone."""
    searched = os.environ.get('PATH', '')
    missing = [b for b in REQUIRED_BINARIES if shutil.which(b) is None]
    if missing:
        msg = (
            'PREFLIGHT REFUSED: required binaries not on PATH: ' + ', '.join(missing)
            + f' — searched PATH={searched!r}. No probe was run: a binary missing from the '
            'environment surfaces as a spawn failure INSIDE whichever probes touch it, which is '
            'indistinguishable from those probes being broken.'
        )
        print(msg, file=sys.stderr)
        raise EnvironmentError(msg)


def prune_runs(runtime_dir=None, keep=None):
    """Keep the newest `keep` runs; delete the older ones, stamp AND captures tree together.

    Age comes off mtime, NOT off the name: the dir holds at least two stamp shapes plus hand-named
    runs (`w7552r-runA.txt`), and a name parser silently retains forever every shape it fails to
    parse. `latest.json` and the `.latest-*.json` temps match neither suffix, so they are never
    candidates — the liveness artifact cannot be pruned by construction.
    """
    runtime_dir = RUNTIME_DIR if runtime_dir is None else runtime_dir
    keep = RETAINED_RUNS if keep is None else keep
    runs = {}
    for name in os.listdir(runtime_dir) if os.path.isdir(runtime_dir) else []:
        if name.endswith('.txt'):
            key = name[:-len('.txt')]
        elif name.endswith('-captures'):
            key = name[:-len('-captures')]
        else:
            continue
        path = os.path.join(runtime_dir, name)
        try:
            runs.setdefault(key, []).append((os.path.getmtime(path), path))
        except OSError:
            pass
    newest_first = sorted(runs, key=lambda k: max(m for m, _ in runs[k]), reverse=True)
    pruned = []
    for key in newest_first[keep:]:
        for _, path in runs[key]:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        pruned.append(key)
    return pruned


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
        preflight()

        pruned = prune_runs()
        # Recorded BEFORE the suite runs, so a run that later dies still reports what it pruned.
        payload['retained_runs'] = RETAINED_RUNS
        payload['pruned_runs'] = len(pruned)
        payload['pruned_oldest'] = pruned[-1] if pruned else None
        payload['pruned_newest'] = pruned[0] if pruned else None

        probes, discovered = discover()

        all_dirs = sorted({os.path.dirname(p) for p in probes})
        run_dirs = [d for d in all_dirs if d not in EXCLUDED_DIRS]
        excluded_probes = [p for p in probes if os.path.dirname(p) in EXCLUDED_DIRS]

        # An excluded dir that has stopped existing is not a safe no-op: it means the exclusion is
        # no longer doing anything and nobody would know. Say so rather than silently covering it.
        missing_exclusions = [d for d in EXCLUDED_DIRS if d not in all_dirs]

        # ⚠ THE SUMMARY DESTINATION IS NAMED HERE, EXPLICITLY (7.607 E3, review F5). `probe-suite.js`
        # used to DEFAULT its summary into the workspace `.rbtv/runtime/probe-suite/`, which is
        # exactly where this runner's liveness artifact lives — so the agreement below held by
        # coincidence of two independent derivations. E3 moved that default to the OS temp dir (a
        # read-only check must not write into the goals workspace as the price of running), and the
        # first scheduled fire after the change reported `ARTIFACT-PATH-MISMATCH` and no verdict.
        # A summary worth keeping is one whose destination is named, so this names it.
        #
        # ⚠⚠ AND NAMING IT SPENDS THE SECOND DERIVATION — say so rather than inherit the old claim
        # (7.607 E3 review). The check below was two INDEPENDENT derivations of the runtime dir
        # disagreeing; dictating `--summary` leaves ONE, and the suite echoes back the very string
        # it was handed. Measured: inject the exact defect that check was written for (a suite
        # resolving a DIFFERENT `.rbtv/`) and the no-`--summary` shape catches it while this shape
        # does not. What survives below is narrower and still worth keeping — a suite that IGNORED
        # the flag, and an artifact that never landed — so it is asserted for what it now proves.
        # THE ORIGINAL DEFECT (this runner's OWN workspace derivation being wrong) is no longer
        # detectable here at all: the summary would follow RUNTIME_DIR wherever it pointed.
        stamp = time.strftime('%Y-%m-%dT%H-%M-%SZ', time.gmtime())
        summary_path = os.path.join(RUNTIME_DIR, f'{stamp}.txt')
        os.makedirs(RUNTIME_DIR, exist_ok=True)   # the suite mkdir -p's it too; belt and braces
        proc = subprocess.run(
            ['node', SUITE, '--summary', summary_path]
            + [arg for d in run_dirs for arg in ('--dir', d)],
            cwd=IGNITE_ROOT, capture_output=True, text=True, timeout=3600,
        )
        tail = proc.stdout[-4000:]

        def num(field):
            m = re.search(rf'^{field}:\s*(\d+)$', tail, re.M)
            return int(m.group(1)) if m else None

        attempted, passed, failed = num('attempted'), num('passed'), num('failed')
        inoperative = num('inoperative')
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
            'inoperative': inoperative,
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

        # ⚠⚠ THE ARTIFACT MUST LAND WHERE ITS READER LOOKS. Historically this compared TWO
        # independent derivations of the runtime dir — the suite's own and this file's — because
        # when they disagreed the artifact was silently written into a `.rbtv/` one level up from
        # the real one: successfully written, and nowhere its reader would ever look. Since the
        # destination is DICTATED above there is only one derivation left, so what is asserted here
        # is the pair of things still falsifiable: the suite HONOURED the path it was handed, and
        # the file is ACTUALLY THERE afterwards (a crash between the echo and the write, or a suite
        # that reported a path it never opened, both red this).
        if payload.get('summary_path'):
            suite_runtime_dir = os.path.dirname(os.path.abspath(payload['summary_path']))
            if os.path.abspath(RUNTIME_DIR) != suite_runtime_dir:
                payload['verdict'] = 'ARTIFACT-PATH-MISMATCH'
                payload['coverage_ok'] = False
                payload['note'] = (
                    f'this runner handed the suite --summary under {RUNTIME_DIR} but the suite '
                    f'reported writing to {suite_runtime_dir} — the flag was not honoured. The '
                    'liveness artifact is not where its reader looks, so no verdict is reported.'
                )
            elif not os.path.isfile(payload['summary_path']):
                payload['verdict'] = 'ARTIFACT-MISSING'
                payload['coverage_ok'] = False
                payload['note'] = (
                    f"the suite reported writing {payload['summary_path']} and no file is there. "
                    'The run reported itself; its artifact did not land, so no verdict is reported.'
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


def selftest():
    """The one runnable check: prune_runs keeps the newest N runs and takes captures with them."""
    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        for i in range(10):
            open(os.path.join(d, f'run-{i:02d}.txt'), 'w').close()
            os.makedirs(os.path.join(d, f'run-{i:02d}-captures'))
            open(os.path.join(d, f'run-{i:02d}-captures', 'x.out'), 'w').close()
            for n in (f'run-{i:02d}.txt', f'run-{i:02d}-captures'):
                os.utime(os.path.join(d, n), (1000 + i, 1000 + i))
        open(os.path.join(d, 'latest.json'), 'w').close()
        pruned = prune_runs(d, keep=3)
        left = sorted(os.listdir(d))
        assert pruned == ['run-06', 'run-05', 'run-04', 'run-03', 'run-02', 'run-01', 'run-00'], pruned
        assert left == ['latest.json', 'run-07-captures', 'run-07.txt', 'run-08-captures',
                        'run-08.txt', 'run-09-captures', 'run-09.txt'], left
    print('selftest OK')
    return 0


if __name__ == '__main__':
    sys.exit(selftest() if '--selftest' in sys.argv else main())
