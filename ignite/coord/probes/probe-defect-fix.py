#!/usr/bin/env python3
"""probe-defect-fix.py — the fix-wave probes for the coord.py half (campaign issues S-4(b), S-7,
S-8(c)).

WHAT THIS SCORES OVER — stated per defect, because "probes pass" reads as a clean class and is not:

  S-4(b) shell substitution — a body sent POSITIONALLY through `sh -c`. It scores the refusal, that
      nothing is appended on refusal, that an identical body sent via --file is ACCEPTED with its
      backticks intact, and — the red half — that forcing past the gate logs a body the author
      never wrote. It does NOT score an interactive human shell: there is no `-c` string to compare
      against there, that case is genuinely undetectable, and the code says so.
  S-6(a) gate split — DELETED [T2-R10, D24, F-simplicity-7]. It probed `coordinate gates --json`
      against `GATE_FLAGS` and recover-room.py's split-verification, both removed with the ROLE
      gate `--force` used to carry: there is no second gate left for `--force-memory` to be
      recombined with, so nothing here is left to mutate.
  S-7 unclosable ask — an `ask` from an identity with no roster row / briefing / group is refused
      and nothing is appended; the SAME sender's `note` is accepted, and an ADDRESSABLE sender's
      `ask` is accepted. Without those two the probe would not distinguish the fix from a blanket ban.
  S-8(c) refusal wording — memory_gate's refusal names `--force-memory` and no longer tells the
      operator to reach for `--force`.

Every write lands in a temp package. The LIVE run package and the live message log are never
touched. HOME is redirected into the temp tree for every subprocess (G-75: a mutation test runs the
mutant with the full write authority of the real program).

Run: python3 probe-defect-fix.py    ->  exit 0 all green, exit 1 on any failure.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD = KIT / "coord.py"

RESULTS = []
SKIPPED = []


def check(label, cond, detail=""):
    RESULTS.append((bool(cond), label))
    print(("ok    " if cond else "FAIL  ") + label + (f"\n        {detail}" if detail and not cond else ""))


def skip(label, why):
    """Record a check that COULD NOT RUN. Run issue G-194(b).

    ⚠ WHY THIS EXISTS: `RECOVER` sits OUTSIDE this kit (`KIT.parent/"jobs"`), so a copy of
    `coord` alone cannot find it — and this probe used to report that as TWO FAILING ASSERTIONS.
    Identical bytes gave 20/21 in the live kit and 18/21 in a copy. A failed assertion claims THE
    BEHAVIOUR IS BROKEN; a missing dependency means THE PROBE COULD NOT RUN, and they are different
    claims. The false red mattered because copy-and-run is a documented gating practice in this
    room, so the lie was produced on every use.

    Skipped checks are listed IN FULL, never counted: a count in permanent output has no maintainer
    and only grows. Exit status is 2 (INOPERATIVE), never 0 and never 1 — a probe that could not run
    has proven nothing, and reporting that as a pass is the absence-reads-as-health shape."""
    SKIPPED.append((label, why))
    print(f"SKIP  {label}\n        INOPERATIVE: {why}")


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

        # ⚠ THIS BOUND IS CLOSED, AND THE CHECK BELOW USED TO ASSERT THE OLD WORLD (run issue
        # G-194(a), 2026-07-28). It was written when the gate INFERRED shell provenance from a
        # surviving shell parent: `bash -c` with ONE simple command execs itself away, no parent
        # survived, and the corrupted body WAS logged. `4837088` ("the shell guard must assert, not
        # infer") removed that inference, so this shape is now REFUSED like any other.
        # ⇒ The check therefore asserted a VULNERABILITY as expected behaviour. It did not merely
        # fail to catch a defect — it DEFENDED one: the red it produced could only be "fixed" by
        # reintroducing the corruption, and a permanently-red probe teaches everyone to ignore it,
        # so a real red goes unread. It is now a REGRESSION TEST for the closed bound: if anyone
        # restores provenance-by-inference, this fails and says so.
        before = log_text(pkg)
        r = shell_send(pkg, home, "sender-seat",
                       f'{base} leader --type note "blindspot `echo EXECOPT` here"',
                       keep_shell=False)
        added = log_text(pkg)[len(before):]
        check("S-4(b) BOUND CLOSED: a bash -c ONE-COMMAND invocation is REFUSED like any other "
              "shell-typed body — the guard ASSERTS provenance instead of inferring it from a "
              "surviving shell parent (4837088), so no corrupted body is logged. This check once "
              "asserted the opposite and thereby defended the vulnerability (G-194(a))",
              r.returncode != 0 and "EXECOPT" not in added,
              f"rc={r.returncode} added={added[:200]!r}")

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

        # S-6(a) (the `gates`/GATE_FLAGS flag->gate split probe) is deleted along with the
        # mechanism it tested: the per-verb ROLE gate `--force` used to carry is gone whole
        # [T2-R10, D24, F-simplicity-7], so there is no second gate left for `--force-memory` to
        # be recombined with, and `coordinate gates` / `GATE_FLAGS` / `gate_forced` no longer
        # exist to probe.

        # ── S-8(c) ─────────────────────────────────────────────────────────
        sys.path.insert(0, str(KIT))
        import coord  # noqa: E402  — the module under test, imported after its path is known
        # ⚠ AN EXPLICIT FLOOR, BECAUSE THERE IS NO LONGER A DEFAULT ONE. Task 7.82 deleted
        # `LAUNCH_MEM_FLOOR_MB`: a module constant is the same class of copy as an argv literal, so
        # `memory_gate` now REQUIRES `floor_mb` and the caller must have resolved a floor before it
        # may ask about one. This probe supplies a FIXTURE floor deliberately — S-8(c) is about the
        # refusal's WORDING, and keying it to whatever the live run declares today would make a
        # wording probe fail whenever a policy number moved.
        refusal = coord.process.memory_gate(1, 100, 2000)
        check("S-8(c): the memory-gate refusal names `--force-memory`", "--force-memory" in refusal)
        check("S-8(c): ...and no longer tells the operator to override with `--force`",
              "override with --force " not in refusal and "override with --force." not in refusal,
              refusal[-200:])
        # The S-8(c) paired-behaviour check that used to run this wording assertion against
        # `coord.gate_forced` is deleted with that function [T2-R10, D24, F-simplicity-7]: there
        # is no indirection left between `--force-memory` and the memory gate to verify — the
        # live call site reads `args.force_memory` directly, and coord.py's own selftest (#230)
        # already drives `cmd_launch` end-to-end to prove `--force` alone does not lift it.

    failed = [l for ok, l in RESULTS if not ok]
    # THREE OUTCOMES, DISTINCT IN BOTH THE TEXT AND THE EXIT CODE, so a reader skimming exit codes
    # cannot mistake one for another (the bar on G-194(b)): FAIL means THE CODE IS BROKEN and
    # nothing else; INOPERATIVE means this probe could not run and has proven nothing; PASS means
    # every check ran and held.
    if failed:
        verdict, code = "FAIL", 1
    elif SKIPPED:
        verdict, code = "INOPERATIVE", 2
    else:
        verdict, code = "PASS", 0
    print(f"\nprobe-defect-fix: {verdict} "
          f"({len(RESULTS) - len(failed)}/{len(RESULTS)} checks ran and held"
          f"{f', {len(SKIPPED)} could not run' if SKIPPED else ''})")
    for l in failed:
        print("  failed: " + l)
    for l, why in SKIPPED:
        print(f"  could not run: {l}\n      because: {why}")
    if SKIPPED and not failed:
        print("  ⇒ INOPERATIVE, not passing: a probe that could not run has proven nothing.")
    return code


class _ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)


if __name__ == "__main__":
    sys.exit(main())
