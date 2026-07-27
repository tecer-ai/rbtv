#!/usr/bin/env python3
"""probe-defect-fix.py — the fix-wave probes for the coord.py half (campaign issues S-4(b), S-6(a),
S-7, S-8(c)).

WHAT THIS SCORES OVER — stated per defect, because "probes pass" reads as a clean class and is not:

  S-4(b) shell substitution — a body sent POSITIONALLY through `sh -c`. It scores the refusal, that
      nothing is appended on refusal, that an identical body sent via --file is ACCEPTED with its
      backticks intact, and — the red half — that forcing past the gate logs a body the author
      never wrote. It does NOT score an interactive human shell: there is no `-c` string to compare
      against there, that case is genuinely undetectable, and the code says so.
  S-6(a) gate split — `coordinate gates --json` agreeing with GATE_FLAGS, and recover-room.py
      REFUSING against a mutant coord.py whose flags have been recombined. The mutant is the point:
      an assertion that cannot go red is not an assertion.
  S-7 unclosable ask — an `ask` from an identity with no roster row / briefing / group is refused
      and nothing is appended; the SAME sender's `note` is accepted, and an ADDRESSABLE sender's
      `ask` is accepted. Without those two the probe would not distinguish the fix from a blanket ban.
  S-8(c) refusal wording — memory_gate's refusal names `--force-memory` and no longer tells the
      operator to reach for `--force`. Paired with a behavioural check that `--force` alone really
      does NOT lift the memory gate, so the wording is verified against conduct, not itself.

Every write lands in a temp package. The LIVE run package and the live message log are never
touched. HOME is redirected into the temp tree for every subprocess (G-75: a mutation test runs the
mutant with the full write authority of the real program).

Run: python3 probe-defect-fix.py    ->  exit 0 all green, exit 1 on any failure.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD = KIT / "coord.py"
RECOVER = KIT.parent / "jobs" / "recover-room.py"

RESULTS = []


def check(label, cond, detail=""):
    RESULTS.append((bool(cond), label))
    print(("ok    " if cond else "FAIL  ") + label + (f"\n        {detail}" if detail and not cond else ""))


def make_pkg(root: Path) -> Path:
    pkg = root / "pkg"
    (pkg / "coordination").mkdir(parents=True)
    (pkg / "workers").mkdir()
    (pkg / "workers" / "leader.md").write_text("---\nagent: leader\n---\nbrief\n", encoding="utf-8")
    (pkg / "workers" / "sender-seat.md").write_text("---\nagent: sender-seat\n---\nbrief\n",
                                                    encoding="utf-8")
    return pkg


def env_for(home: Path, agent: str = ""):
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"))
    env.pop("TMUX_PANE", None)          # no pane -> the daemon-job shape, and no roster binding
    env.pop("COORD_AGENT", None)
    if agent:
        env["COORD_AGENT"] = agent
    return env


def shell_send(pkg: Path, home: Path, agent: str, shell_line: str, keep_shell=True):
    """Run a coordinate send THROUGH `bash -c` — the shape every agent harness and every scripted
    caller uses, and the only one in which the pre-substitution text survives in /proc.

    `keep_shell` appends a TRAILING no-op so bash does not exec-optimize itself away. That
    optimization is real and is the gate's blind spot: when the -c string ENDS with the command,
    bash REPLACES itself with it, so the substitution still happens but no shell parent remains.
    Only a trailing command keeps a shell alive — a leading one does not, which was measured, not
    assumed. Agent harnesses always have a trailing command (the Claude Code Bash tool ends every
    line with a `pwd -P` write), so the shapes that produced all three real incidents are covered;
    the blind spot is asserted explicitly below rather than left to be discovered."""
    # The trailing command must also PRESERVE the exit status, or every refusal reads as a
    # success and the probe scores nothing. `exit $rc` is a builtin, so bash still survives.
    line = (shell_line + "; __rc=$?; exit $__rc") if keep_shell else shell_line
    return subprocess.run(["/bin/bash", "-c", line], capture_output=True, text=True,
                          timeout=120, env=env_for(home, agent), cwd=str(pkg))


def log_text(pkg: Path) -> str:
    p = pkg / "coordination" / "messages.md"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def main():
    with tempfile.TemporaryDirectory(prefix="probe-defect-fix-") as td:
        td = Path(td)
        home = td / "home"
        home.mkdir()
        pkg = make_pkg(td)
        base = f'{sys.executable} {COORD} --package {pkg} send'

        # ── S-4(b) ─────────────────────────────────────────────────────────
        # A body whose backticks the shell substitutes away before coord.py is even started.
        r = shell_send(pkg, home, "sender-seat",
                       f'{base} leader --type note "status is `echo SUBSTITUTED` right now"')
        check("S-4(b): a positional body whose backticks the shell ATE is REFUSED",
              r.returncode == 1 and "SUBSTITUTED" in r.stderr, r.stderr[:300])
        check("S-4(b): ...and NOTHING is appended — the corrupted body never reaches the log",
              "right now" not in log_text(pkg))
        check("S-4(b): ...and the refusal shows the shell's ORIGINAL line, so the author can see "
              "what was eaten", "original line" in r.stderr)

        # The control that stops this being a blanket ban on positional bodies.
        r = shell_send(pkg, home, "sender-seat",
                       f'{base} leader --type note "an ordinary body with no substitution"')
        check("S-4(b): a positional body from a shell is refused DETERMINISTICALLY, not only when "
              "damage can be proven — a gate that silently stops working is worse than none",
              r.returncode == 1 and "typed on a shell command line" in r.stderr, r.stderr[:300])
        r = shell_send(pkg, home, "sender-seat",
                       f'{base} leader --type note --inline "an ordinary body with no substitution"')
        check("S-4(b) control: --inline sends the same body as typed — a short safe body stays a "
              "one-liner",
              r.returncode == 0 and "an ordinary body" in log_text(pkg), r.stderr[:300])
        before = log_text(pkg)
        r = shell_send(pkg, home, "sender-seat",
                       f'{base} leader --type note --inline "inline does not cover `echo PROVEN`"')
        check("S-4(b): --inline does NOT cover a PROVEN substitution — the assertion it carries "
              "(\'nothing here to eat\') is contradicted by evidence, so it is refused anyway",
              r.returncode == 1 and "SUBSTITUTED" in r.stderr and log_text(pkg) == before,
              r.stderr[:300])

        # --file is the form that cannot be eaten: the backticks must SURVIVE into the log.
        bodyf = td / "body.txt"
        bodyf.write_text("literal backticks `echo SUBSTITUTED` survive via --file\n", encoding="utf-8")
        r = shell_send(pkg, home, "sender-seat", f'{base} leader --type note --file {bodyf}')
        check("S-4(b): the SAME text sent via --file is accepted AND its backticks survive verbatim",
              r.returncode == 0 and "`echo SUBSTITUTED`" in log_text(pkg), r.stderr[:300])

        # The red half: the gate genuinely stands between the author and a corrupted record.
        before = log_text(pkg)
        r = shell_send(pkg, home, "sender-seat",
                       f'{base} leader --type note --force --inline "forced: `echo EATENHERE` gone"')
        added = log_text(pkg)[len(before):]
        check("S-4(b) red half: it takes BOTH --force and --inline to get past, and what lands "
              "then is a body the author never wrote — backticks gone, the command's OUTPUT in the "
              "record. That is what used to happen with no flags at all",
              r.returncode == 0 and "EATENHERE" in added and "`echo EATENHERE`" not in added,
              added[:300])

        # THE BLIND SPOT, asserted so it is a KNOWN bound and not a discovery. `bash -c` given ONE
        # simple command execs itself away: the substitution still happens, but no shell parent
        # survives for the gate to compare against, so this body IS logged corrupted. Agent
        # harnesses do not hit it (they chain setup commands); a hand-written one-shot script can.
        before = log_text(pkg)
        r = shell_send(pkg, home, "sender-seat",
                       f'{base} leader --type note "blindspot `echo EXECOPT` here"',
                       keep_shell=False)
        added = log_text(pkg)[len(before):]
        check("S-4(b) KNOWN BOUND: a bash -c ONE-COMMAND invocation execs the shell away, so the "
              "gate cannot see it and the corrupted body IS logged — the fix covers the shell "
              "shapes agents actually use, not every shape",
              r.returncode == 0 and "EXECOPT" in added and "`echo EXECOPT`" not in added,
              added[:300])

        # ── S-7 ────────────────────────────────────────────────────────────
        before = log_text(pkg)
        r = shell_send(pkg, home, "goal-watcher-detector",
                       f'{base} leader --type ask --file {bodyf}')
        check("S-7: an `ask` from an identity with no roster row, briefing or group is REFUSED",
              r.returncode == 1 and "cannot receive a reply" in r.stderr, r.stderr[:300])
        check("S-7: ...and nothing is appended — no unclosable thread is created",
              log_text(pkg) == before)

        r = shell_send(pkg, home, "goal-watcher-detector",
                       f'{base} leader --type note --file {bodyf}')
        check("S-7 control: the SAME unaddressable sender's `note` is still accepted — the gate is "
              "on the ask/identity PAIRING, not on daemon senders",
              r.returncode == 0, r.stderr[:300])

        r = shell_send(pkg, home, "sender-seat", f'{base} leader --type ask --file {bodyf}')
        check("S-7 control: an ADDRESSABLE sender's `ask` is still accepted",
              r.returncode == 0, r.stderr[:300])

        # ── S-6(a) ─────────────────────────────────────────────────────────
        r = subprocess.run([sys.executable, str(COORD), "gates", "--json"],
                           capture_output=True, text=True, timeout=60, env=env_for(home))
        gates = json.loads(r.stdout) if r.returncode == 0 else {}
        check("S-6(a): `gates --json` publishes the flag->gate map",
              r.returncode == 0 and gates.get("--force") == ["role"]
              and gates.get("--force-memory") == ["memory"], r.stdout[:200])

        recover_args = ["--session", "tw-probe-never-created", "--package", str(pkg),
                        "--seat", "tw-x", "--dry-run"]
        r = subprocess.run([sys.executable, str(RECOVER), "--coord", str(COORD)] + recover_args,
                           capture_output=True, text=True, timeout=120, env=env_for(home))
        check("S-6(a): the unattended recovery path ASSERTS the split and proceeds when it holds",
              r.returncode == 0 and "precondition OK" in r.stdout, (r.stdout + r.stderr)[:300])

        # The mutant: the two gates recombined onto --force, exactly the silent recombination the
        # standing rule forbids and nothing used to detect.
        mutant = td / "coord-mutant.py"
        src = COORD.read_text(encoding="utf-8")
        old = '    "--force": ("role",),'
        check("S-6(a) mutation is constructible — GATE_FLAGS is where the probe thinks it is",
              src.count(old) == 1)
        mutant.write_text(src.replace(old, '    "--force": ("role", "memory"),', 1), encoding="utf-8")
        r = subprocess.run([sys.executable, str(mutant), "gates", "--json"],
                           capture_output=True, text=True, timeout=60, env=env_for(home))
        mgates = json.loads(r.stdout) if r.returncode == 0 else {}
        check("S-6(a): the mutant's map really did change (the map is the mechanism, not a label)",
              "memory" in (mgates.get("--force") or []))
        r = subprocess.run([sys.executable, str(RECOVER), "--coord", str(mutant)] + recover_args,
                           capture_output=True, text=True, timeout=120, env=env_for(home))
        check("S-6(a) RED HALF: against the recombined map the unattended recovery REFUSES (exit 2) "
              "instead of silently arming a memory override at 4am",
              r.returncode == 2 and "REFUSING to recover" in r.stdout, (r.stdout + r.stderr)[:300])

        # ── S-8(c) ─────────────────────────────────────────────────────────
        sys.path.insert(0, str(KIT))
        import coord  # noqa: E402  — the module under test, imported after its path is known
        refusal = coord.memory_gate(1, 100)
        check("S-8(c): the memory-gate refusal names `--force-memory`", "--force-memory" in refusal)
        check("S-8(c): ...and no longer tells the operator to override with `--force`",
              "override with --force " not in refusal and "override with --force." not in refusal,
              refusal[-200:])
        check("S-8(c) paired behaviour: `--force` really does NOT carry the memory gate, so the "
              "new wording matches conduct rather than itself",
              coord.gate_forced(_ns(force=True), "memory") is False
              and coord.gate_forced(_ns(force_memory=True), "memory") is True)

    failed = [l for ok, l in RESULTS if not ok]
    print(f"\nprobe-defect-fix: {'PASS' if not failed else 'FAIL'} "
          f"({len(RESULTS) - len(failed)}/{len(RESULTS)} checks)")
    for l in failed:
        print("  failed: " + l)
    return 1 if failed else 0


class _ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)


if __name__ == "__main__":
    sys.exit(main())
