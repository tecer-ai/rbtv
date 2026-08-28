#!/usr/bin/env python3
"""probe-watchdog-workspace-refusal — a watchdog with no workspace REFUSES; it never invents one.

WHAT THIS EXISTS FOR (wave test 15, 2026-08-28). `WORKSPACE` defaulted to `os.getcwd()`, and every
path this tool writes is `<WORKSPACE>/.rbtv/runtime/…`. So a pass launched from a directory that is
not a workspace — the rbtv repo root, in the measured case, by
`probe-watchdog-staged-failure` at 03:02:15Z with no `RBTV_WATCHDOG_WORKSPACE` — CREATED
`<cwd>/.rbtv/runtime/watchdog/`. That stray folder then out-voted the real install for
`ignite/deploy/probe-suite-scheduled.py#find_workspace_root`, which stopped at the first ancestor
holding a bare `.rbtv/`: from 04:00Z the probe suite wrote `latest.json` into the repo while this
tool read the vault copy frozen at 03:20:11Z, reported `probe-suite down — last fired 9026s ago`
for 195 consecutive passes, restarted `rbtv-probe-suite.timer` once a minute and DM'd the owner —
about a suite that had fired at 04:00, 05:00, 06:00 and 07:00.

THE CONTRACT (D27, and `ignite/ignite-cli/lib/config.js#findInstallRoot`): a workspace is the folder
that ROOTS THE INSTALL — the one holding `.rbtv/modules/ignite/server.json` — never any folder that
happens to contain a `.rbtv/` directory.

THE ARMS
  1  cwd with NO install record, no env      -> exit 2, one refusal line, and NOTHING written
  2  cwd holding a bare `.rbtv/`, no env     -> still exit 2 (the exact stray-folder shape), and
                                               the bare `.rbtv/` gains no `runtime/`
  3  cwd that DOES root an install, no env   -> ACCEPTED (not a blanket refusal) and it writes
                                               into that workspace
  4  RED CONTROL — a copy of the tool with the pre-fix `os.getcwd()` default, run from arm 2's
     fixture: it does NOT refuse and it PLANTS `<cwd>/.rbtv/runtime/watchdog/`, reproducing the
     03:02:15Z event. Without this arm, arms 1–2 would pass identically against a tool that
     refused for some unrelated reason.

CONFINEMENT — no live unit is read, started or stopped. Only the `probe-suite` row runs; its
restart lever is pointed at `/bin/true` through `RBTV_WATCHDOG_OPERATOR`, so the real
`rbtv-probe-suite.timer` is never named to systemd, and `RBTV_WATCHDOG_NOTIFY_FILE` makes a real
Slack DM structurally impossible even if the shell carries a bot token.

Exit 0 = all assertions held. Exit 1 = at least one failed.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WATCHDOG = os.path.join(os.path.dirname(HERE), "tool", "rbtv-ignite-watchdog")
OUT = os.path.join(HERE, "probe-watchdog-workspace-refusal.out")
RECORD_REL = os.path.join(".rbtv", "modules", "ignite", "server.json")


def plant_record(root):
    """The minimum that makes a directory a workspace by D27: the install record exists."""
    d = os.path.join(root, ".rbtv", "modules", "ignite")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "server.json"), "w") as f:
        f.write('{"machines": {}}\n')


def tree(root):
    found = []
    for base, dirs, files in os.walk(root):
        for n in list(dirs) + files:
            found.append(os.path.relpath(os.path.join(base, n), root))
    return sorted(found)


def main():
    log, fails = [], []

    def check(name, ok, detail=""):
        log.append("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                                  ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    scratch = tempfile.mkdtemp(prefix="rbtv-watchdog-wsrefusal-")
    notify_file = os.path.join(scratch, "notify.jsonl")

    base_env = {k: v for k, v in os.environ.items() if k != "RBTV_WATCHDOG_WORKSPACE"}
    base_env.update({
        "RBTV_WATCHDOG_TARGETS": "probe-suite",
        # The restart lever, pointed at a no-op binary: `restart_via_operator` runs
        # `<operator> restart` with the unit in RBTV_IGNITE_UNIT, so /bin/true consumes the
        # action and no unit name ever reaches systemd.
        "RBTV_WATCHDOG_OPERATOR": "/bin/true",
        "RBTV_WATCHDOG_NOTIFY_FILE": notify_file,
        "RBTV_WATCHDOG_NOTIFY_PREFIX": "",
    })

    def run_watchdog(tool, cwd, extra=None):
        e = dict(base_env)
        e.update(extra or {})
        p = subprocess.run([sys.executable, tool], cwd=cwd, env=e,
                           capture_output=True, text=True, timeout=180)
        return p.returncode, p.stdout, p.stderr

    try:
        # ── arm 1: a plain non-workspace cwd ──────────────────────────────────────────────
        bare = os.path.join(scratch, "not-a-workspace")
        os.makedirs(bare)
        rc, out, err = run_watchdog(WATCHDOG, bare)
        check("1a: no env + a cwd that roots no install exits 2", rc == 2, "rc=%s" % rc)
        refusal = [l for l in err.strip().splitlines() if l.startswith("refusing:")]
        check("1b: the refusal is ONE line naming the cwd and the install record",
              len(refusal) == 1 and bare in refusal[0] and RECORD_REL in refusal[0],
              (refusal[0] if refusal else err.strip()[:200]))
        check("1c: the refused pass wrote NOTHING at all", tree(bare) == [],
              "found %s" % (tree(bare)[:6],))

        # ── arm 2: the stray-folder shape — a bare `.rbtv/` with no install record ────────
        stray = os.path.join(scratch, "stray")
        os.makedirs(os.path.join(stray, ".rbtv"))
        rc2, _out2, err2 = run_watchdog(WATCHDOG, stray)
        check("2a: a cwd holding a bare .rbtv/ but no install record STILL exits 2",
              rc2 == 2, "rc=%s" % rc2)
        check("2b: nothing was written under the bare .rbtv/",
              tree(os.path.join(stray, ".rbtv")) == [],
              "found %s" % (tree(os.path.join(stray, ".rbtv"))[:6],))

        # ── arm 3: the default still WORKS where the cwd is genuinely a workspace ─────────
        real = os.path.join(scratch, "real-workspace")
        os.makedirs(real)
        plant_record(real)
        rc3, out3, err3 = run_watchdog(WATCHDOG, real)
        check("3a: a cwd that roots the install is ACCEPTED (not a blanket refusal)",
              rc3 == 0 and "refusing:" not in err3, "rc=%s err=%s" % (rc3, err3.strip()[:160]))
        ledger3 = os.path.join(real, ".rbtv", "runtime", "watchdog", "outage-ledger.jsonl")
        check("3b: and it writes into THAT workspace, under its own .rbtv/",
              os.path.isfile(ledger3), "probe-suite row output: %s" % out3.strip()[:160])

        # ── arm 4: RED CONTROL — the pre-fix cwd default plants the stray folder ──────────
        mutant = os.path.join(scratch, "mutant-watchdog")
        src = open(WATCHDOG).read()
        fixed = ("def resolve_workspace():\n"
                 '    explicit = env("RBTV_WATCHDOG_WORKSPACE")\n'
                 "    if explicit:\n"
                 "        return explicit\n"
                 "    cwd = os.getcwd()\n"
                 "    return cwd if roots_install(cwd) else None\n")
        assert src.count(fixed) == 1, "the mutation target moved — this control is vacuous"
        with open(mutant, "w") as f:
            f.write(src.replace(fixed,
                                "def resolve_workspace():\n"
                                '    return env("RBTV_WATCHDOG_WORKSPACE", os.getcwd())\n'))
        stray2 = os.path.join(scratch, "stray-mutant")
        os.makedirs(os.path.join(stray2, ".rbtv"))
        rc4, _out4, err4 = run_watchdog(mutant, stray2)
        check("4a: RED CONTROL — the pre-fix default does NOT refuse",
              rc4 != 2 and "refusing:" not in err4, "rc=%s" % rc4)
        planted = os.path.join(stray2, ".rbtv", "runtime", "watchdog", "outage-ledger.jsonl")
        check("4b: RED CONTROL — and it PLANTS <cwd>/.rbtv/runtime/watchdog/, the 03:02:15Z event",
              os.path.isfile(planted), "tree=%s" % (tree(os.path.join(stray2, ".rbtv"))[:6],))
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
