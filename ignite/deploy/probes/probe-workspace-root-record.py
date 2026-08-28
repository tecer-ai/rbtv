#!/usr/bin/env python3
"""probe-workspace-root-record — the probe suite's scheduler resolves the workspace by the INSTALL
RECORD, and a bare `.rbtv/` never wins.

WHAT THIS EXISTS FOR (wave test 15, 2026-08-28). `probe-suite-scheduled.py#find_workspace_root`
walked up from the script's own folder and stopped at the first ancestor holding a `.rbtv/`
DIRECTORY. At 03:02:15Z the daemon watchdog, run from the rbtv repo root with no
`RBTV_WATCHDOG_WORKSPACE`, created `<repo>/.rbtv/runtime/watchdog/` — and from the 04:00Z fire this
walk stopped THERE, three levels below the real workspace. The suite wrote its liveness artifact
`latest.json` into the repo while the watchdog kept reading the vault copy, frozen at 03:20:11Z:
195 consecutive `probe-suite down — last fired 9026s ago` passes, a timer restart every minute and
an owner DM, all about a suite that was firing hourly. A stray `.rbtv/` is gitignored
(`**/.rbtv/`), so nothing in `git status` ever showed it.

THE CONTRACT (D27, implemented canonically by `ignite/ignite-cli/lib/config.js#findInstallRoot`):
the workspace is the NEAREST ancestor holding the committed endpoint record
`.rbtv/modules/ignite/server.json` — never any folder that happens to contain a `.rbtv/`.

THE FIXTURE is the outage in miniature:
    <ws>/.rbtv/modules/ignite/server.json      the real install
    <ws>/sub/repo/.rbtv/runtime/               the stray, planted by a cwd-defaulting writer
    <ws>/sub/repo/ignite/deploy/               where this scheduler lives
resolving from `<ws>/sub/repo/ignite/deploy/` MUST answer `<ws>`.

Exit 0 = all assertions held. Exit 1 = at least one failed.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEDULER = os.path.join(os.path.dirname(HERE), "probe-suite-scheduled.py")
OUT = os.path.join(HERE, "probe-workspace-root-record.out")
RECORD_REL = os.path.join(".rbtv", "modules", "ignite", "server.json")

# The resolution is a MODULE-LEVEL assignment (`WORKSPACE_ROOT = find_workspace_root(DEPLOY_DIR)`),
# so the honest way to exercise it is to import a copy planted at the real path inside the fixture
# and read what it resolved — not to call the function with a hand-supplied start and hope the
# module-level call passes the same thing. This driver prints the three resolved values plus the
# stderr the walk emitted, and the probe reads them back.
DRIVER = """
import json, sys
from importlib.machinery import SourceFileLoader
m = SourceFileLoader('pss', sys.argv[1]).load_module()
print(json.dumps({'root': m.WORKSPACE_ROOT, 'latest': m.LATEST,
                  'record_rel': m.INSTALL_RECORD_REL}))
"""


def plant_record(root):
    d = os.path.join(root, ".rbtv", "modules", "ignite")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "server.json"), "w") as f:
        f.write('{"machines": {}}\n')


def main():
    log, fails = [], []

    def check(name, ok, detail=""):
        log.append("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                                  ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    scratch = tempfile.mkdtemp(prefix="rbtv-wsroot-")
    driver = os.path.join(scratch, "driver.py")
    with open(driver, "w") as f:
        f.write(DRIVER)

    def build(where, source):
        """Plant a copy of the scheduler at `<where>/ignite/deploy/` and resolve from it."""
        deploy = os.path.join(where, "ignite", "deploy")
        os.makedirs(deploy, exist_ok=True)
        target = os.path.join(deploy, "probe-suite-scheduled.py")
        with open(target, "w") as fh:
            fh.write(source)
        p = subprocess.run([sys.executable, driver, target], capture_output=True, text=True,
                           timeout=120, cwd=scratch)
        return p

    try:
        source = open(SCHEDULER).read()

        # ── the fixture: a real workspace, a nested repo carrying a stray `.rbtv/` ────────
        ws = os.path.join(scratch, "ws")
        plant_record(ws)
        repo = os.path.join(ws, "sub", "repo")
        os.makedirs(os.path.join(repo, ".rbtv", "runtime", "watchdog"))
        p = build(repo, source)
        resolved = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ""
        import json as _json
        got = _json.loads(resolved) if resolved.startswith("{") else {}

        check("1a: resolves to the install root, NOT the nested repo",
              got.get("root") == ws, "got=%s want=%s" % (got.get("root"), ws))
        check("1b: the liveness artifact therefore lands in the real workspace",
              got.get("latest") == os.path.join(ws, ".rbtv", "runtime", "probe-suite",
                                                "latest.json"),
              "got=%s" % got.get("latest"))
        check("1c: the rule it walks by IS the install record",
              got.get("record_rel") == RECORD_REL, "got=%s" % got.get("record_rel"))
        named = [l for l in p.stderr.splitlines() if repo in l and ".rbtv" in l]
        check("1d: the skipped bare .rbtv/ is NAMED on stderr as not a workspace",
              len(named) == 1 and "NOT a workspace" in named[0],
              (named[0] if named else p.stderr.strip()[:200]))
        check("1e: resolving created nothing — the stray .rbtv/ gained no probe-suite dir",
              not os.path.exists(os.path.join(repo, ".rbtv", "runtime", "probe-suite")))

        # ── nearest-ancestor-wins is preserved: a REAL nested install still shadows ───────
        ws2 = os.path.join(scratch, "ws2")
        plant_record(ws2)
        inner = os.path.join(ws2, "sub", "inner")
        plant_record(inner)
        got2 = _json.loads(build(inner, source).stdout.strip().splitlines()[-1])
        check("2: a NESTED folder that does root an install still wins (nearest-ancestor-wins)",
              got2.get("root") == inner, "got=%s want=%s" % (got2.get("root"), inner))

        # ── no record anywhere above: a refusal that names what it looked for ────────────
        orphan = os.path.join(scratch, "orphan")
        os.makedirs(os.path.join(orphan, ".rbtv"))
        p3 = build(orphan, source)
        check("3: no install record above => RuntimeError naming the record, never a guess",
              p3.returncode != 0 and RECORD_REL in p3.stderr and "no workspace root" in p3.stderr,
              "rc=%s err=%s" % (p3.returncode, p3.stderr.strip().splitlines()[-1:] or ""))

        # ── RED CONTROL: the pre-fix bare-directory test lands in the nested repo ────────
        fixed = "        if os.path.isfile(os.path.join(d, INSTALL_RECORD_REL)):\n"
        assert source.count(fixed) == 1, "the mutation target moved — this control is vacuous"
        mutant = source.replace(fixed, "        if os.path.isdir(os.path.join(d, '.rbtv')):\n")
        ws3 = os.path.join(scratch, "ws3")
        plant_record(ws3)
        repo3 = os.path.join(ws3, "sub", "repo")
        os.makedirs(os.path.join(repo3, ".rbtv", "runtime", "watchdog"))
        got3 = _json.loads(build(repo3, mutant).stdout.strip().splitlines()[-1])
        check("4: RED CONTROL — the pre-fix bare-.rbtv/ test resolves to the NESTED repo",
              got3.get("root") == repo3, "got=%s want=%s" % (got3.get("root"), repo3))

        # ── the live box: whatever this scheduler resolves TODAY roots a real install ────
        live = subprocess.run([sys.executable, driver, SCHEDULER], capture_output=True,
                              text=True, timeout=120, cwd=scratch)
        gotl = _json.loads(live.stdout.strip().splitlines()[-1])
        check("5: LIVE — the installed scheduler's own workspace root holds the install record",
              os.path.isfile(os.path.join(gotl.get("root", ""), RECORD_REL)),
              "root=%s" % gotl.get("root"))
    except Exception as ex:  # noqa: BLE001 — a probe that cannot run proves nothing
        check("probe ran to completion", False, "%s: %s" % (type(ex).__name__, ex))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.append("")
    log.append("PROBE %s (%d failure%s)" % ("PASS" if not fails else "FAIL",
                                            len(fails), "" if len(fails) == 1 else "s"))
    text = "\n".join(log) + "\n"
    with open(OUT, "w") as f:
        f.write(text)
    sys.stdout.write(text)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
