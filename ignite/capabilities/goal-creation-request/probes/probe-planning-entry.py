#!/usr/bin/env python3
"""probe-planning-entry.py — the planning entry, end to end, from the SHIPPED config (task C5E).

WHAT THIS GUARDS THAT NOTHING ELSE DOES. `probe-argv-template.js` certifies the templating
MECHANISM (a row's args expand into a registered argv) and `probe-goal-creation-request.py`
certifies the create act's SHAPE. Neither reads `config/spawn-profiles.yaml`. So the composition —
the SHIPPED `workflows: planning-deprecated:` argv, expanded against the args the SHIPPED
`goal-creation-request` entry actually produces, handed to the program that argv names — was
guarded by nothing, and it is the whole surface between a certified mechanism and a goal that
plans itself.

⚠ EVERY INPUT IS READ OFF THE SHIPPED CONFIG, NEVER TYPED HERE. A probe that hand-types the flag
values it checks tests its own transcription: the config could drift to a different bindings file
or a different catalog root and this file would keep passing. So the flag values below are PARSED
out of `config/spawn-profiles.yaml` — the same bytes the daemon boot-reads — and the queue-row args
are CAPTURED from a real drain rather than composed by hand.

⚠ NOTHING HERE TOUCHES THE LIVE DAEMON, THE LIVE STORE, OR A LIVE ROOM. The goals root is a
tempdir; `ignite` is a STUB that records its argv and exits 0 (`--ignite-bin` is an existing seam,
so no code is bent to be testable); and every tmux act runs on a PRIVATE `-L` socket, never the
socket live rooms are on. No real goal is created and no queue row is ever enqueued.

⚠⚠ AND NO PAID AGENT BOOTS — ASSERTED BY ARM `P5c`, NOT CLAIMED (task 7.553). Until 7.553 this file
called itself hermetic "by PATH only" and every single run booted a REAL `claude --effort max` with
a full seat prompt into the seat pane, then killed the room out from under it: a PATH shim binds
only what inherits the launcher's environment, and tmux starts a pane's shell as a LOGIN shell whose
profile RE-PREPENDS the real `~/.local/bin` (§2 review of `73823ab`, finding F1 — measured three
times). It survived in three documents for one reason: NOTHING CHECKED IT. Both halves of the fix
are measurements from task 7.552, not guesses — (i) the seat's pane must be a NON-LOGIN shell, which
is `default-command` set on THIS probe's own private socket, and (ii) that socket's SERVER must
itself carry the shimmed PATH, since a non-login pane inherits the server's environment. A `HOME`
redirect does NOT help (the prepended path is a literal) and is ruled out rather than retried. The
stub records its argv in a marker file and `P5c` reads it back, so the day the binding breaks this
probe goes RED instead of going quietly expensive.

BOUNDARY, STATED RATHER THAN IMPLIED: this probe does not fire the row through a live ticker. The
real-fire path is `probe-argv-template.js`'s (scratch store, real `fireQueueRow`, real expansion).
What is proven here instead is that the composed argv is ACCEPTED BY THE REAL PROGRAM — the exact
composed command line is EXECUTED, with `--dry-run` appended and a private tmux socket, so the
program, its flags and every value are exercised. The one-flag delta is named here so no reader
takes this for a live fire.

Exit 0 GREEN · 1 RED · 2 INOPERATIVE (a red arm that failed to go red has scored nothing).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

CAP = Path(__file__).resolve().parents[1]
IGNITE = CAP.parents[1]
HANDLER = CAP / "tool" / "goal_creation_request.py"
LAUNCHER = CAP / "tool" / "workflow_launcher.py"
CONFIG = IGNITE / "config" / "spawn-profiles.yaml"
ARGV_TEMPLATE = IGNITE / "server" / "heart" / "argv-template.js"
CARRIER = IGNITE / "server" / "spawn" / "carrier.js"
TEAM_MONITOR = IGNITE.parent / "orchestration" / "cli" / "team-monitor" / "team_monitor.py"

SOCKET = "probe-planning-entry"          # a PRIVATE tmux socket; never the default one

FAILED = []
INOPERATIVE = []
CHECKS = []


def refusal_detail(out):
    """WHY a drain did not accept, with the TYPED reason WHOLE (task 7.604).

    This was `json.dumps(out)[:400]`, and those 400 chars are the inbox path, the counters and the
    head of the first request's paths — every one of them known before the run. The one fact the
    capture existed to carry, the typed reason, sits at char ~3900 behind a 2 KB copy of
    `create-goal`'s stdout, so it was truncated away EVERY time: during task 7.598 the decisive
    `bindings-missing-seat` was invisible here and cost a standalone repro arm to surface.

    So name the field instead of slicing the blob: the reason lives in
    `requests[*]['stated-refusal']`, which the handler ALREADY bounds at composition
    (`goal_creation_request.py:678` — a step name plus `stderr[-800:]`, so ≈860 chars per refused
    request). The raw payload stays as the fallback for an outcome that carries no `requests` at
    all (`UNPARSEABLE`), bounded at 2000. This changes what the capture SHOWS, never what any
    check DECIDES — every arm still grades `out['outcome']`.
    """
    stated = [r.get("stated-refusal") for r in out.get("requests", [])
              if r.get("outcome") != "ACCEPTED"]
    return " | ".join(s for s in stated if s)[:2000] or json.dumps(out)[:2000]


def report(check, arm, ok, expected, detail=""):
    CHECKS.append(check)
    verdict = "GREEN" if ok else "RED"
    good = (ok == expected)
    print(f"  [{'ok ' if good else 'BAD'}] {check} · {arm} -> {verdict} "
          f"(expected {'GREEN' if expected else 'RED'})" + (f" — {detail}" if detail else ""))
    if not good:
        (FAILED if expected else INOPERATIVE).append(f"{check}/{arm}")
    return good


# ─────────────────────────────────────────── the shipped config, parsed not typed

def shipped():
    """(tool_flags, workflow_argv) read out of spawn-profiles.yaml."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    argv = cfg["tools"]["goal-creation-request"]["argv"]
    flags = {}
    for i, tok in enumerate(argv):
        if isinstance(tok, str) and tok.startswith("--") and i + 1 < len(argv):
            flags[tok] = argv[i + 1]
    return flags, cfg["workflows"][flags["--workflow"]]["argv"]


def expand(argv, args):
    """The REAL expander — `argv-template.js` run through node. Never a python re-implementation:
    a second expander would agree with the first only until one of them changed."""
    script = (f"const t=require({json.dumps(str(ARGV_TEMPLATE))});"
              f"console.log(JSON.stringify(t.expandArgv({json.dumps(argv)},{json.dumps(args)})));")
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        return {"refused": f"node failed: {r.stderr.strip()[:200]}"}
    return json.loads(r.stdout)


# ─────────────────────────────────────────── F1 · the two PATHs, both read from their real source

def manager_path():
    """The systemd --user MANAGER's PATH — what a `systemd-run --user` child actually inherits.

    MEASURED, never typed: this is the environment the daemon-fired exec really lands in, and the
    whole of F1 is that it differs from the operator's."""
    r = subprocess.run(["systemctl", "--user", "show-environment"], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("PATH="):
            return line[len("PATH="):]
    return None


def carrier_tool_path():
    """The PATH the CARRIER now composes for every fired tool — asked of the real module.

    ⚠ ASKED, NOT REPRODUCED. A python re-implementation of `toolExecEnv()` would agree with the
    carrier only until one of them changed, and this arm's whole claim is about what the daemon
    does. Returns None if the carrier exports no composer (the pre-fix shape)."""
    script = (f"const c=require({json.dumps(str(CARRIER))});"
              "process.stdout.write(c.toolExecEnv?c.toolExecEnv().PATH:'');")
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    return r.stdout.strip() or None


def tmux(*a):
    exe = shutil.which("tmux")
    return subprocess.run([exe, "-L", SOCKET, *a], capture_output=True, text=True) if exe else None


def make_shims(d, marker):
    """The fixture for the REAL-fire arms (P5/P6), built out of PATH and nothing else.

    ⚠ WHY A `tmux` SHIM AND NOT A FLAG. The launcher takes `--tmux-socket`, but it does NOT pass one
    to the `coordinate launch` it delegates to — and coord.py has no socket option at all (it calls
    bare `tmux`). So on a private socket the launcher would open the room there and hand coord a
    pane id that does not exist on the socket coord actually talks to. PATH is therefore the ONLY
    seam that isolates the whole composed act, and it is the same seam the F1 arms below already
    use. NOTHING in the product is bent to be testable.

    ⚠ THE `claude` STUB'S SHAPE IS `acceptance-room.py`'s `STUB_BODY`, NOT AN INVENTION — a bash
    COPY used as the script's SHEBANG INTERPRETER. `coord.py`'s `wait_harness_up` polls
    `pane_harness_pids`, which matches a HARNESS process under the pane, so a stub that `exec
    sleep`s is POSITIVE ABSENCE ("only its shell is there", G-11): the seat is refused and the
    launch exits 1 (measured on 7.552's fixture). `printf` and `read` are builtins, so the stub
    itself stays the pane's foreground process. PATH ALONE DOES NOT MAKE IT BIND — see the module
    docstring; the caller must also put the pane on a non-login shell and hand the tmux server this
    PATH. The `marker` is the other half: the stub records that it ran, and `P5c` reads it back.
    """
    d.mkdir(parents=True, exist_ok=True)
    real = shutil.which("tmux")
    t = d / "tmux"
    t.write_text(f'#!/bin/sh\nexec {real} -L {SOCKET} "$@"\n', encoding="utf-8")
    hb = d / ".hb"
    hb.mkdir(exist_ok=True)
    shutil.copy2("/bin/bash", hb / "claude")
    (d / "claude").write_text(
        f"#!{hb / 'claude'}\n"
        "# stub harness — no model, no network, no cost. Flags are deliberately ignored.\n"
        f'printf "%s\\n" "$*" >> {marker}\n'
        "while :; do read -rt 3600 _ || true; done\n", encoding="utf-8")
    for f in ("tmux", "claude"):
        (d / f).chmod(0o755)
    return d


def kill_socket():
    tmux("kill-server")


# ─────────────────────────────────────────── P1 · a REAL drain against a fixture

def drain(tmp, flags, goal="probe-fresh-goal", bindings=None, request=None, path=None):
    """Run scaffold-and-queue for real against a scratch goals root with a STUB ignite.

    Returns (result_json, captured_ignite_argvs, goals_root).

    `path` overrides PATH for this drain ONLY — everything else in the environment is inherited
    unchanged, so an arm that sets it differs from the default arm on exactly one variable. That is
    what makes the F1 pair below a control rather than two unrelated runs.

    ⚠ THE FIXTURE ROOT CARRIES `.rbtv/goals` SEGMENTS ON PURPOSE. `argv-template.js`'s `workdirRule`
    proves containment LEXICALLY, from the path's own segments after normalisation, because the
    workspace root is not knowable inside the module. A fixture rooted at a bare tempdir is
    therefore refused by the real rule — which is the rule working, not a defect. The first draft of
    this probe used `tmp/goals` and went RED at P2 for exactly that reason; making the fixture look
    like production is the fix, and weakening the arm would have been the bug."""
    root = tmp / ".rbtv" / "goals"
    inbox = root / "_requester" / "requests"
    inbox.mkdir(parents=True)
    payload = request if request is not None else {
        "goal-name": goal, "goal-type": "one-shot", "goal-kind": "interactive",
        "goal-contract": "# Contract\n\nProbe fixture. Nothing real depends on this.\n"}
    (inbox / "req.json").write_text(json.dumps(payload), encoding="utf-8")

    capture = tmp / "ignite-calls.jsonl"
    stub = tmp / "ignite-stub"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json,sys\n"
        f"open({json.dumps(str(capture))},'a').write(json.dumps(sys.argv[1:])+'\\n')\n"
        "sys.exit(0)\n", encoding="utf-8")
    stub.chmod(0o755)

    cmd = [sys.executable, str(HANDLER), "scaffold-and-queue",
           "--inbox", str(inbox), "--goals-root", str(root),
           "--workflow", flags["--workflow"], "--entry-seat", flags["--entry-seat"],
           "--catalog-root", flags["--catalog-root"],
           "--bindings", bindings if bindings is not None else flags["--bindings"],
           "--conduct", flags["--conduct"], "--claude-md", flags["--claude-md"],
           "--budget-json", flags["--budget-json"],
           "--ignite-bin", str(stub)]
    env = None
    if path is not None:
        env = dict(os.environ)
        env["PATH"] = path
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    try:
        out = json.loads(r.stdout)
    except ValueError:
        out = {"outcome": "UNPARSEABLE", "stdout": r.stdout[-500:], "stderr": r.stderr[-500:]}
    calls = [json.loads(ln) for ln in capture.read_text().splitlines()] if capture.exists() else []
    return out, calls, root


def main():
    if shutil.which("tmux") is None:
        print("VERDICT: INOPERATIVE — tmux is absent, so the room arms cannot run")
        return 2
    flags, wf_argv = shipped()
    print(f"shipped tool flags parsed from {CONFIG.name}: "
          f"{ {k: v for k, v in flags.items() if k != '--inbox'} }")

    tmpdir = Path(tempfile.mkdtemp(prefix="probe-planning-entry-"))
    args = None
    pkg5 = None          # bound at the real-fire arms; read by the teardown
    try:
        # ---- P1 · the goal is born WITH a run package and an open register row -----
        out, calls, root = drain(tmpdir / "a", flags)
        goal_dir = root / "probe-fresh-goal"
        # 7.607 E2b — THE PACKAGE IS THE GOAL FOLDER (design-lock item 8). There is no
        # `runs/run-1` compartment, no run id, and no run register.
        pkg = goal_dir
        report("P1 goal scaffolded", "green", out.get("outcome") == "ACCEPTED", True,
               f"outcome={out.get('outcome')} "
               f"{'' if out.get('outcome') == 'ACCEPTED' else refusal_detail(out)}")
        report("P1 goal-direct package created", "green", pkg.is_dir(), True, str(pkg))
        seats = sorted(p.name for p in (pkg / "seats").iterdir()) if (pkg / "seats").is_dir() else []
        report("P1 whole planning DAG materialized", "green", len(seats) == 9, True,
               f"{len(seats)} seats: {seats}")
        # ⚠ 7.607 E2b — THE REGISTER IS EXTINGUISHED, so this arm is INVERTED rather than
        # deleted: it used to assert `runs.csv` carries a `state=open` row, and it now asserts the
        # file is NEVER MINTED. A shorter arm list would stop CHECKING for the register; it would
        # not notice one being written again. The `state=open` row this replaces IS the 7.608
        # deadlock's own carrier (a stored status that outlived what it described), which is why
        # its absence is worth an assertion rather than a deletion.
        report("P1 NO run register is minted (item 8: runs.csv is extinguished)", "green",
               not (goal_dir / "runs.csv").exists(), True,
               "runs.csv absent" if not (goal_dir / "runs.csv").exists()
               else (goal_dir / "runs.csv").read_text(encoding="utf-8").strip())
        report("P1 NO runs/ compartment is minted either", "green",
               not (goal_dir / "runs").exists(), True, str(goal_dir / "runs"))

        # The queue row's args, CAPTURED from the stub rather than composed here.
        addjob = [c for c in calls if c and c[0] == "add-job"]
        report("P1 one workflow row queued", "green", len(addjob) == 1, True, f"{len(addjob)} add-job call(s)")
        if addjob:
            args = json.loads(addjob[0][addjob[0].index("--args-json") + 1])
            report("P1 args carry all four template keys", "green",
                   set(args) == {"workflow", "entry-seat", "goal", "workdir"}, True, json.dumps(args))
            report("P1 workdir IS the run package (ruling clause 3)", "green",
                   args.get("workdir") == str(pkg), True, args.get("workdir", ""))
            # ---- P7 · THE ROW IS ONE-SHOT, which is what keeps the launcher's failure
            # exit from minting the failure-per-cadence pattern. `fireQueueRow` DELETES a
            # `scheduled` row carrying no repeat rule at fire (heart-store.js), so the
            # `failed` completion a no-seat fire records happens ONCE and has no cadence to
            # recur on. The day this row becomes periodic that exit writes a `failed` every
            # pass — the owner-killed pattern — so the enqueue shape is pinned HERE, read off
            # the captured argv rather than off the source that composed it.
            repeaters = [t for t in addjob[0]
                         if t in ("--every", "--cron", "--repeat", "--repeat-rule",
                                  "--interval", "--interval-seconds", "--max-fires")]
            report("P7 the workflow row is queued ONE-SHOT (no cadence to pollute)", "green",
                   "--trigger" in addjob[0]
                   and addjob[0][addjob[0].index("--trigger") + 1] == "scheduled"
                   and "--at" in addjob[0] and not repeaters, True,
                   f"trigger=scheduled --at present; repeat flags: {repeaters or 'none'}")

            regjob = [c for c in calls if c and c[0] == "register-job"]
            schema = json.loads(regjob[0][regjob[0].index("--args-schema") + 1]) if regjob else {}
            report("P1 all four declared required", "green",
                   set(schema.get("required", {})) == {"workflow", "entry-seat", "goal", "workdir"},
                   True, json.dumps(schema))

        # ---- P2 · the SHIPPED argv composes byte-exactly against those args -------
        if args:
            composed = expand(wf_argv, args)
            expected = [t if not (isinstance(t, str) and t.startswith("{{"))
                        else args[t[2:-2]] for t in wf_argv]
            report("P2 shipped argv expands", "green", "argv" in composed, True,
                   composed.get("refused", ""))
            report("P2 composed argv is byte-exact", "green", composed.get("argv") == expected, True,
                   " ".join(composed.get("argv", []))[:220])
            report("P2 argv[0] is the interpreter, not a placeholder", "green",
                   wf_argv[0] == "/usr/bin/python3", True, wf_argv[0])
            report("P2 launcher named in argv exists on disk", "green",
                   Path(wf_argv[1]).is_file() and Path(wf_argv[1]) == LAUNCHER, True, wf_argv[1])

            # ---- P3 · the real program ACCEPTS the composed command line ----------
            # The composed argv verbatim, plus --dry-run and a private socket. Nothing is created.
            # Guarded on the expansion having produced one: a P2 refusal must be reported as itself,
            # never crash the run and take every later arm — including the RED ones — with it.
            r = (subprocess.run(composed["argv"] + ["--dry-run", "--tmux-socket", SOCKET],
                                capture_output=True, text=True) if "argv" in composed else None)
            report("P3 composed argv accepted by the real launcher", "green",
                   r is not None and r.returncode == 0, True,
                   "" if r is None else ((r.stdout + r.stderr).strip().splitlines() or [""])[-1][:200])
            report("P3 session name is the BARE GOAL NAME (item 2: one room per goal)", "green",
                   r is not None and f"'{args['goal']}'" in r.stdout
                   and f"'{args['goal']}-run-1'" not in r.stdout, True,
                   "" if r is None else
                   next((l for l in r.stdout.splitlines() if "room for this goal" in l), "")[:160])

            # ---- RED · the injection arms, on the SHIPPED argv --------------------
            # ⚠ `ok` IS "DID IT COMPOSE", NEVER "DID IT REFUSE" — the same polarity every arm above
            # uses. The first draft passed "did it refuse" here and all four arms reported BAD while
            # their own detail text quoted the refusal they had just correctly produced. A red arm
            # whose polarity is inverted reads as an INOPERATIVE instrument, which is the honest
            # failure, but it is still the probe being wrong about a product that was right.
            def red(check, args_in, argv_in=None):
                res = expand(argv_in if argv_in is not None else wf_argv, args_in)
                report(check, "hostile row", "argv" in res, False, res.get("refused", "")[:120])

            red("R1 shell metacharacter in a row value",
                dict(args, **{"entry-seat": "elicitator; rm -rf /"}))
            red("R2 workdir outside the goals containment", dict(args, workdir="/etc"))
            red("R3 a row may not choose the program", args, ["{{goal}}"] + wf_argv[1:])
            red("R4 a missing operand refuses, never empties",
                {k: v for k, v in args.items() if k != "workdir"})

        # ---- P4 · the room, for real, on a private socket ------------------------
        sys.path.insert(0, str(LAUNCHER.parent))
        import workflow_launcher as wl                       # noqa: E402 — the real thing

        name = wl.session_name("probe-fresh-goal", pkg)
        report("P4 name derivation is the BARE GOAL (item 2)", "green",
               name == "probe-fresh-goal", True, name)
        pane, prov = wl.ensure_session(name, str(tmpdir), SOCKET)
        live = tmux("has-session", "-t", f"={name}").returncode == 0
        report("P4 detached session created", "green", live and bool(pane), True, f"{pane} — {prov}")
        pane2, prov2 = wl.ensure_session(name, str(tmpdir), SOCKET)
        n_sessions = len([l for l in tmux("list-sessions", "-F", "#{session_name}").stdout.splitlines() if l.strip()])
        report("P4 re-fire is idempotent (joins, never doubles)", "green",
               pane2 == pane and n_sessions == 1, True, f"{n_sessions} session(s), pane {pane2}")

        # ---- RED · the launcher's own refusals ----------------------------------
        r = subprocess.run([sys.executable, str(LAUNCHER), "--package", str(tmpdir / "nope"),
                            "--goal", "probe-fresh-goal", "--entry-seat", "elicitator",
                            "--coord", str(IGNITE / "team-kit" / "coord.py"),
                            "--tmux-socket", SOCKET], capture_output=True, text=True)
        report("R5 absent run package", "refused", r.returncode == 0, False,
               (r.stdout.strip().splitlines() or [""])[-1][:140])
        try:
            wl.session_name("bad.name", pkg)
            bad_ok = True
        except ValueError as err:
            bad_ok, why = False, str(err)
        report("R6 a session name carrying a tmux separator", "refused", bad_ok, False,
               "" if bad_ok else why[:140])

        # tmux absent -> an honest refusal, never a guessed target.
        saved = os.environ.get("PATH", "")
        os.environ["PATH"] = str(tmpdir / "empty")
        try:
            wl.ensure_session(name, str(tmpdir), SOCKET)
            noexe_ok = True
        except RuntimeError as err:
            noexe_ok, why2 = False, str(err)
        finally:
            os.environ["PATH"] = saved
        report("R7 tmux absent from PATH", "refused", noexe_ok, False,
               "" if noexe_ok else why2[:140])

        # ---- RED · a missing bindings file refuses the REQUEST, queues nothing ---
        out2, calls2, _ = drain(tmpdir / "b", flags, goal="probe-nobind",
                                bindings=str(tmpdir / "absent-bindings.json"))
        report("R8 absent bindings file", "refused",
               out2.get("outcome") == "ACCEPTED" or any(c and c[0] == "add-job" for c in calls2),
               False,
               f"outcome={out2.get('outcome')}, add-job calls={sum(1 for c in calls2 if c and c[0] == 'add-job')}")
        disclosed = out2.get("requests", [{}])[0]
        # 7.607 E2a renamed the disclosure keys `run-package*` -> `package*` (the package IS the
        # goal folder); this arm's SUBJECT — a refusal DISCLOSES what it left on disk rather than
        # unwinding it — is unchanged.
        report("R8b the partial state is DISCLOSED, not unwound", "green",
               "package" in disclosed and "goal-dir" in disclosed, True,
               f"goal-exists={disclosed.get('goal-exists')} package-exists={disclosed.get('package-exists')}")

        # ---- F1 · THE ENVIRONMENT ARM the reviewer's finding said this probe could not see ------
        #
        # THE BLIND SPOT, NAMED. Every arm above drains through `subprocess.run` inheriting THIS
        # process's environment — the operator's. The daemon's fired exec inherits the systemd
        # --user MANAGER's instead, and the two differ on exactly the one variable that decides the
        # outcome: `~/.local/bin`, where the ruled name `scaffold-seats` lives. So this probe was
        # green while every daemon-fired creation refused and orphaned its goal (C5E review, F1).
        # The pair below is that variable, changed once, with the handler run for real on both sides.
        mpath, cpath = manager_path(), carrier_tool_path()
        print(f"  manager PATH  : {mpath}")
        print(f"  carrier PATH  : {cpath}")

        # F1a · RED ARM — the PRE-FIX condition, still reproducible on demand. Under the bare
        # manager PATH the ruled name does not resolve and the request MUST refuse. If this ever
        # goes green the box is carrying ~/.local/bin from somewhere else and F1b proves nothing.
        if mpath is None:
            INOPERATIVE.append("F1a/no-manager-path")
            print("  [BAD] F1a · the manager PATH could not be measured — the pair scores nothing")
        else:
            out3, calls3, _ = drain(tmpdir / "f1a", flags, goal="probe-f1-manager", path=mpath)
            report("F1a ruled name under the MANAGER PATH (the pre-fix condition)", "refused",
                   out3.get("outcome") == "ACCEPTED", False,
                   f"outcome={out3.get('outcome')}, add-job calls="
                   f"{sum(1 for c in calls3 if c and c[0] == 'add-job')}")

        # F1b · GREEN ARM — the SAME drain under the environment the carrier now composes for every
        # fired tool. This is the fix, exercised end to end through the real handler.
        if cpath is None:
            FAILED.append("F1b/no-composer")
            print("  [BAD] F1b · the carrier exports no toolExecEnv() — nothing composes a fired "
                  "tool's environment, so the F1 class is still open")
        else:
            out4, calls4, root4 = drain(tmpdir / "f1b", flags, goal="probe-f1-carrier", path=cpath)
            report("F1b ruled name under the CARRIER-COMPOSED PATH (the fix)", "green",
                   out4.get("outcome") == "ACCEPTED", True,
                   f"outcome={out4.get('outcome')} "
                   f"{'' if out4.get('outcome') == 'ACCEPTED' else refusal_detail(out4)}")
            report("F1b the goal is born WITH its working surfaces under the fired environment",
                   "green",
                   (root4 / "probe-f1-carrier" / "seats").is_dir()
                   and not (root4 / "probe-f1-carrier" / "runs").exists(), True,
                   "goal-direct seats/ present, no runs/ compartment")
            report("F1b the workflow row is queued under the fired environment", "green",
                   sum(1 for c in calls4 if c and c[0] == "add-job") == 1, True,
                   f"add-job calls={sum(1 for c in calls4 if c and c[0] == 'add-job')}")

        # ---- P5 / P6 · THE REAL FIRE (task 7.548) — no `--dry-run`, the seat's pane asserted ----
        #
        # WHAT THIS GUARDS THAT P3 CANNOT. P3 executes the composed argv with `--dry-run` APPENDED,
        # so it proves the command line is accepted and opens nothing. The claim that actually
        # decides whether arming goal-creation is safe — a brand-new goal's FIRST fire opens its
        # entry seat — was guarded by nothing, and the launcher, this capability's contract doc and
        # `spawn-profiles.yaml` all asserted the OPPOSITE ("opens the room and NO SEAT, and exits
        # 0") until 7.548 measured it. Both arms run the SHIPPED launcher for real.
        marker = tmpdir / "claude-stub-ran.txt"
        shims = make_shims(tmpdir / "shims", marker)
        fire_env = dict(os.environ)
        fire_env["PATH"] = f"{shims}{os.pathsep}{os.environ.get('PATH', '')}"
        fire_env.pop("TMUX", None)            # a fired exec inherits neither; neither does this
        fire_env.pop("TMUX_PANE", None)
        fire_env.pop("COORD_LAUNCH_TARGET", None)
        _, calls5, root5 = drain(tmpdir / "c", flags, goal="probe-firstfire")
        pkg5 = root5 / "probe-firstfire"
        room = "probe-firstfire"

        # ⚠ THE STUB BINDS ONLY IF BOTH OF THESE HOLD, and neither is optional (task 7.553):
        #   (1) the seat's pane is a NON-LOGIN shell — `default-command`, which is a SERVER option,
        #       so it must be set BEFORE that pane opens; and
        #   (2) the tmux SERVER itself carries the shimmed PATH, because a non-login pane inherits
        #       the SERVER's environment — and this socket's server was started back at P3/P4,
        #       before the shims existed. Setting only (1) leaves the pane inheriting a shim-free
        #       PATH; setting only (2) leaves the login shell re-prepending the real `~/.local/bin`
        #       over it. Either one alone boots a real paid agent, which is why F1 was invisible.
        # The room is therefore pre-created HERE rather than by the launcher. `ensure_session` is
        # idempotent by design and joins it ("existing session"), and session CREATION is P4's
        # claim above, not this arm's — the same boundary `probe-sensor-start.py` draws.
        kill_socket()
        os.environ["PATH"] = fire_env["PATH"]   # so the server started below carries the shims
        tmux("new-session", "-d", "-s", room, "-c", str(pkg5))
        tmux("set-option", "-g", "default-command", "bash --noprofile --norc")
        fire = [sys.executable, str(LAUNCHER), "--package", str(pkg5), "--goal", "probe-firstfire",
                "--entry-seat", flags["--entry-seat"],
                "--coord", str(IGNITE / "team-kit" / "coord.py")]

        def room_panes():
            r = tmux("list-panes", "-s", "-t", f"={room}", "-F", "#{pane_id}\t#{pane_current_command}")
            return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r and r.returncode == 0 else []

        virgin = not any((pkg5 / m).exists() for m in
                         ("state.json", "sessions.csv", "coordination/team-monitor.log"))
        report("P5 the scaffolded package is VIRGIN before the first fire", "green", virgin, True,
               "state.json / sessions.csv / team-monitor.log all absent")
        r5 = subprocess.run(fire, capture_output=True, text=True, env=fire_env, timeout=600)
        o5, panes5 = r5.stdout + r5.stderr, room_panes()
        report("P5 first fire on a virgin package EXITS 0", "green", r5.returncode == 0, True,
               f"exit={r5.returncode} :: " + (o5.strip().splitlines() or [""])[-1][:200])
        report("P5 cold-start admission is what admits it", "green", "COLD-START" in o5, True,
               next((l for l in o5.splitlines() if "COLD-START" in l), "")[:180])
        report("P5 a SEAT PANE actually opened", "green",
               len(panes5) >= 2 and any("claude" in p for p in panes5), True,
               f"{len(panes5)} pane(s): {panes5}")

        # ---- P5c · THE HARNESS IN THAT PANE IS THE STUB, so nothing here booted a paid agent ----
        # The arm that did not exist while the claim was false. It reads a marker the stub itself
        # appends to on execution: an EMPTY marker beside an open seat pane means the pane is
        # running the REAL `claude --effort max`, which is exactly the pre-7.553 state. Note what
        # this pins and what it does not: a green here says the probe is free, NOT that a real
        # agent would boot — that is the launcher's own boundary (exit 0 = a seat pane opened).
        ran = marker.read_text(encoding="utf-8").strip() if marker.exists() else ""
        report("P5c the `claude` stub ACTUALLY EXECUTED (no paid agent booted)", "green",
               bool(ran), True,
               (ran.splitlines() or [""])[0][:150] or "MARKER EMPTY — a REAL agent booted instead")

        # ---- P5b · THE SENSOR IS UP (task 7.552) --------------------------------------------
        # `coordinate launch` now hands `team_monitor.py ensure` the ROOM'S SESSION — the one it
        # just launched into — so the census sensor starts with the room's first seat instead of
        # refusing on a roster no seat has checked into yet. ASSERTED from the lock slot and the
        # snapshot on disk, never inferred from the launch having exited 0. Until 7.552 every fire
        # here ended with `WARNING team-monitor start FAILED … the room runs UNOBSERVED`.
        def mon_pid():
            try:
                pid = int((pkg5 / "coordination" / "team-monitor.lock")
                          .read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                return None
            return pid if pid and Path(f"/proc/{pid}").exists() else None

        for _ in range(60):
            if mon_pid() and (pkg5 / "state.json").is_file():
                break
            time.sleep(0.25)
        report("P5b the census sensor STARTED with the room's first seat", "green",
               bool(mon_pid()) and (pkg5 / "state.json").is_file(), True,
               f"lock pid={mon_pid()}, state.json="
               f"{'present' if (pkg5 / 'state.json').is_file() else 'ABSENT'}")

        # P6 · THE SAME FIRE AGAIN WITH THE SENSOR KILLED, and this is the DISCRIMINATING arm. The
        # first fire left `sessions.csv` behind, so the package is no longer VIRGIN and the
        # cold-start bound cannot fire twice; killing the sensor and its snapshot removes the only
        # other way to count the room. That is exactly the state `coordinate launch` defers on:
        # CAP UNENFORCEABLE, every counted candidate deferred, EXIT 0 — and it is precisely the
        # state the launcher's own WAIT text names ("a package whose team-monitor sensor is down").
        # ⚠ IT IS REACHED DELIBERATELY BECAUSE IT NO LONGER ARRIVES ON ITS OWN. Before 7.552 the
        # sensor never started at all, so the second fire hit this state by default; the honesty
        # semantics of `73823ab` must still hold when the census is genuinely gone, and that is what
        # this arm — now a CONTROL rather than an observation — exists to keep pinned.
        # ⚠ THE ROOM HOLDS 2 PANES, so the pre-7.548 verdict — `len(panes) <= 1` — would have read
        # "LAUNCHED" and exited 0, writing a `done` completion for a fire that opened NOTHING
        # (C5E-review C1). This arm goes RED against that rule and green only against a verdict
        # computed from the panes THIS fire added.
        subprocess.run([sys.executable, str(TEAM_MONITOR), "stop", "--package", str(pkg5)],
                       capture_output=True, text=True, env=fire_env, timeout=60)
        (pkg5 / "state.json").unlink(missing_ok=True)
        report("P6 the census is genuinely gone before this fire (the arm's premise)", "green",
               mon_pid() is None and not (pkg5 / "state.json").exists(), True,
               "sensor stopped, state.json removed")
        r6 = subprocess.run(fire, capture_output=True, text=True, env=fire_env, timeout=600)
        o6, panes6 = r6.stdout + r6.stderr, room_panes()
        report("P6 a fire that opens no seat EXITS NON-ZERO (never a false `done`)", "green",
               r6.returncode == wl.EXIT_NO_SEAT and r6.returncode != 0, True,
               f"exit={r6.returncode} (EXIT_NO_SEAT={wl.EXIT_NO_SEAT})")
        report("P6 the deferral is named LOUDLY, typed, in the launcher's own output", "green",
               "CAP UNENFORCEABLE" in o6 and "WAIT" in o6, True,
               next((l for l in o6.splitlines() if l.startswith("workflow-launcher: WAIT")), "")[:200])
        report("P6 no pane opened, while the ROOM still holds more than one", "green",
               len(panes6) == len(panes5) and len(panes6) > 1, True,
               f"{len(panes6)} pane(s), unchanged — a count-based verdict would have said LAUNCHED")
    finally:
        # The sensor this run started is a DETACHED process; it exits on its own once the room is
        # gone, but stopping it here means no probe run ever leaves one polling a deleted package.
        if pkg5 is not None:
            subprocess.run([sys.executable, str(TEAM_MONITOR), "stop", "--package", str(pkg5)],
                           capture_output=True, text=True)
        kill_socket()
        shutil.rmtree(tmpdir, ignore_errors=True)

    print()
    if INOPERATIVE:
        print(f"VERDICT: INOPERATIVE — {len(INOPERATIVE)} red arm(s) did not go red, so they have "
              f"scored nothing: {INOPERATIVE}")
        return 2
    if FAILED:
        print(f"VERDICT: RED — {len(FAILED)} check(s) failed: {FAILED}")
        return 1
    print(f"VERDICT: GREEN — {len(CHECKS)} checks, every gating green paired with a red arm that "
          f"fired. Boundary: firing the QUEUE ROW through a live ticker is probe-argv-template.js's; "
          f"here P3 executes the composed argv with --dry-run appended, and P5/P6 run the shipped "
          f"launcher FOR REAL (no --dry-run) against a scaffolded fixture, on a private tmux socket "
          f"whose panes are NON-LOGIN shells so the `claude` stub actually binds — ASSERTED by P5c "
          f"from a marker the stub writes, never claimed (until task 7.553 the stub was inert and "
          f"every run of this file booted a real paid agent). What P5 proves is therefore the SEAT'S "
          f"PANE and a harness coming up in it, never the agent that would boot for real.")
    return 0


class _Tee:
    """stdout, plus a transcript for the adjacent `.out` this probe is expected to leave.

    The capture is THIS run's output and is untracked (G-171): the file beside a probe is no
    longer a frozen snapshot restored after the run, which is precisely how a stale capture once
    reported a debt 15x too small while the live probe said otherwise.
    """

    def __init__(self, real):
        self.real, self.buf = real, []

    def write(self, s):
        self.real.write(s)
        self.buf.append(s)
        return len(s)

    def flush(self):
        self.real.flush()


if __name__ == "__main__":
    tee = _Tee(sys.stdout)
    sys.stdout = tee
    try:
        rc = main()
    finally:
        sys.stdout = tee.real
        (Path(__file__).with_suffix(".out")).write_text("".join(tee.buf), encoding="utf-8")
    sys.exit(rc)
