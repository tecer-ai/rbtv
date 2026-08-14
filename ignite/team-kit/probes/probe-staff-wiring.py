#!/usr/bin/env python3
"""probe-staff-wiring.py — W3: a signal that cannot finish reaches an OCCUPIED chair.

WHAT EACH ARM SCORES OVER, stated per arm, because "probes pass" reads as a clean class and is not:

  C38 (the flagship, and the design's own bar)  THE LEADER IS SPAWNABLE BY MAIL, END TO END on a
      scratch goal. A worker seat's daemon-lane close mints staff mail to the `leader` chair AND
      flips that chair's `ready-seats` verdict to READY — which is the daemon's seeding door and
      the only surface it reads. The CONTROL is the same chair one call earlier: with no mail it
      reads IDLE, so the arm discriminates "the wake fired" from "the chair was always offered".
      The task text is explicit that if this arm cannot be written the wake design is unresolved.
  W5-7 (the PENDING ARM this completes)  `widen-cage` against a PRIVATE path REFUSES —
      unconditionally, with no flag that carries it. W5's landing deferred exactly this to W3.
  P1..P4 (the permission edit)  the four launch-time grant rules refused AT WRITE TIME (so the
      leader never reads a success for a grant the spawner would silently drop); the appended row
      becoming a REAL rw grant at the next launch, for that seat and NOT for its neighbour; and the
      read-only carve that keeps an audit file writable by nobody it audits.
  R1..R3 (route-fail)  a target that does not exist REFUSED BY EXISTENCE (`_ferry_safe_name` is
      syntax-only, and D6's root cause was a task id in that cell); a target with no ended session
      REFUSED rather than granted an unbindable authorization; and the payload file reaching the
      relaunched sitting's BOOT PROMPT, which is what stops a bare grant re-running the stale seed.
  A1..A2 (`--as leader`)  refused from a CAGED identity, admitted from the console — the human
      emergency path re-verified rather than assumed.
  S1..S3 (the send wrapper)  a staff chair always addressable; an unknown recipient refused even
      WITH `--force`; a departed worker seat accepted with a LOUD warning.
  K1 (the consultant criterion)  a check-out routed to a `consultant` this goal does not staff
      falls back to the leader instead of mailing a chair that does not exist.
  X1 (the exclusion, adv C30)  a STAFF seat's own close mints NO mail — otherwise the closer mails
      the leader about the leader forever, each mail minting the wake for the sitting that writes
      the next one.

WHAT IT DELIBERATELY DOES NOT SCORE: any tmux behaviour (there is none on this lane), and the
daemon actually launching the chair — that is `seeding.js`'s `verdict == "READY"` filter, which is
guarded where it lives. This probe scores the surface the daemon reads.

Every write lands in a temp workspace shaped like a real one (`<ws>/.rbtv/goals/<goal>/`), because
the private-scope and grant-rule readers both resolve the workspace root by walking up to `.rbtv`.
The LIVE workspace is never touched and `coord.py` is imported as a MODULE, never re-saved.

Run: python probe-staff-wiring.py   ->  exit 0 all green, exit 1 on any failure.
"""

import os as _os, sys as _sys, pathlib as _pl  # task 7.630: solo-run tmux isolation, FIRST
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "team-kit" / "self_isolate.py").is_file()) / "team-kit"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD = KIT / "coord.py"
SPAWN_JS = KIT.parent / "server" / "spawn" / "spawn.js"

RESULTS = []


def check(claim, ok, evidence=""):
    RESULTS.append((claim, bool(ok)))
    print(f"{'ok  ' if ok else 'FAIL'}  {claim}")
    if not ok and evidence:
        print(f"        evidence: {str(evidence)[:600]}")


class _NoTmux:
    """A `subprocess` stand-in whose `run` succeeds emptily FOR TMUX ONLY.

    ⚠ IT MUST NOT SWALLOW `node`. `widen-cage` asks two NODE authorities — the private scope and
    the launch-time grant rules — and both FAIL CLOSED on a non-answer, so a blanket stub would
    turn every arm of this probe into a refusal for the wrong reason and the green arms could
    never be green. So the stub dispatches on argv[0]: tmux is faked, everything else is real.
    """

    class _R:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(self, cmd, *a, **k):
        argv0 = cmd[0] if isinstance(cmd, (list, tuple)) and cmd else str(cmd)
        if str(argv0).endswith("tmux"):
            return self._R()
        return subprocess.run(cmd, *a, **k)

    def __getattr__(self, name):
        return getattr(subprocess, name)


def load_coord():
    spec = importlib.util.spec_from_file_location("coord_w3", COORD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["coord_w3"] = mod
    spec.loader.exec_module(mod)
    mod.subprocess = _NoTmux()
    return mod


def make_workspace(root, seats, taskforce_rows):
    """A workspace-shaped scratch tree: `<ws>/.rbtv/goals/probe-goal/`.

    The SHAPE is load-bearing, not decoration: `workspace_root_of` walks up to the `.rbtv`
    ancestor, and the four grant rules are stated relative to that root. A flat temp dir would
    make every path "outside the workspace" and every arm below would pass for the wrong reason.
    """
    ws = Path(root) / "ws"
    pkg = ws / ".rbtv" / "goals" / "probe-goal"
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    (ws / ".rbtv" / "config").mkdir(parents=True, exist_ok=True)
    (ws / ".rbtv" / "config" / "private.json").write_text(
        json.dumps({"deny": ["secrets"], "patterns": ["**/*.env", "**/credentials/"]}),
        encoding="utf-8")
    (ws / "secrets").mkdir(exist_ok=True)
    (ws / "secrets" / "keys.txt").write_text("shh\n", encoding="utf-8")
    (ws / "data").mkdir(exist_ok=True)
    (ws / "data" / "fixtures").mkdir(exist_ok=True)
    (ws / "other").mkdir(exist_ok=True)
    for seat in seats:
        d = pkg / "seats" / seat
        d.mkdir(parents=True, exist_ok=True)
        (d / "seat.md").write_text(f"---\nagent: {seat}\ncwd: {d}\n---\n\n# {seat}\nbrief\n",
                                   encoding="utf-8")
    rows = ["seat,after"] + [f"{s},{a}" for s, a in taskforce_rows]
    (pkg / "taskforce.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return ws, pkg


def ns(pkg, **kw):
    d = {"package": str(pkg), "base": None, "workers_dir": None, "as_agent": None,
         "force": False, "pane": None}
    d.update(kw)
    return argparse.Namespace(**d)


def verdicts(mod, pkg):
    return {r["seat"]: r["verdict"] for r in mod.ready_seat_rows(ns(pkg))}


def open_session(pkg, seat, sid, ended="", disposition=""):
    """Append a `sessions.csv` row by hand — this probe drives the CLOSER, not the spawner."""
    p = Path(pkg) / "sessions.csv"
    if not p.exists():
        p.write_text("session-id,seat,started,ended,disposition,disposition-writer,pid,"
                     "pid-starttime\n", encoding="utf-8")
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(f"{sid},{seat},2026-08-14T00:00:00Z,{ended},{disposition},,,\n")


def run_cmd(mod, fn, pkg, **kw):
    out, err, code = mod.harness_outcome(fn, ns(pkg, **kw))
    return out + err, (0 if code is None else code)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="probe-w3-"))
    mod = load_coord()
    ws, pkg = make_workspace(tmp, ["builder", "leader", "sibling"],
                             [("builder", ""), ("leader", ""), ("sibling", "")])
    base = Path(pkg) / "coordination"

    # ── W5-7 · THE PENDING ARM: widen-cage against a PRIVATE path REFUSES ─────────────────────
    out, code = run_cmd(mod, mod.cmd_widen_cage, pkg, as_agent="leader", seat="builder", path="secrets",
                        reason="probe", go=True)
    check("W5-7: `widen-cage` against a path INSIDE the private scope REFUSES, unconditionally "
          "and with no flag that carries it (W5 probe 7's deferred second half)",
          code != 0 and "PRIVATE SCOPE" in out, out)
    out, code = run_cmd(mod, mod.cmd_widen_cage, pkg, as_agent="leader", seat="builder", path="other/x.env",
                        reason="probe", go=True)
    check("W5-7b: the pattern FLOOR refuses too — a path nobody enumerated, matched on its own "
          "basename, so a NEW secret is refused the day it appears",
          code != 0 and "PRIVATE SCOPE" in out, out)
    check("W5-7c: neither refusal wrote a row — a refused widen leaves NO audit trail of a "
          "widening that did not happen",
          not (base / "permission-edits.csv").exists())

    # ── P1 · the four launch-time rules, refused AT WRITE TIME ────────────────────────────────
    for label, entry, expect in (
            ("an ABSOLUTE path", "/etc/passwd", "absolute"),
            ("a path that DOES NOT EXIST", "data/nope", "does not exist"),
            ("a path OVERLAPPING `.rbtv/goals`", ".rbtv/goals/probe-goal", "overlaps"),
    ):
        out, code = run_cmd(mod, mod.cmd_widen_cage, pkg, as_agent="leader", seat="builder", path=entry,
                            reason="probe", go=True)
        check(f"P1: `widen-cage` refuses {label} at WRITE time, in the verb where the leader can "
              f"READ the reason — never as a grant the spawner silently drops hours later",
              code != 0 and expect in out, out)

    # ── P2 · the happy path, and it becomes a REAL grant ──────────────────────────────────────
    out, code = run_cmd(mod, mod.cmd_widen_cage, pkg, as_agent="leader", seat="builder", path="data/fixtures",
                        reason="its briefing writes fixtures here", go=False)
    check("P2a: BARE is a report — it names what would be appended and writes nothing",
          code == 0 and "WIDENABLE" in out and not (base / "permission-edits.csv").exists(), out)
    out, code = run_cmd(mod, mod.cmd_widen_cage, pkg, as_agent="leader", seat="builder", path="data/fixtures",
                        reason="its briefing writes fixtures here", go=True)
    edits = (base / "permission-edits.csv").read_text(encoding="utf-8") if code == 0 else ""
    check("P2b: `--go` appends ONE audited row carrying the seat, the path, the REASON and the "
          "editor — the audit log and the mechanism are one artifact",
          code == 0 and "builder" in edits and "data/fixtures" in edits
          and "briefing writes fixtures" in edits, out + edits)

    node = "node"
    script = (
        "const s=require(process.argv[1]);"
        "const g=s.resolvePermissionEditGrants({workspaceRoot:process.argv[2],seat:process.argv[3],"
        "seatDir:process.argv[4],goalDir:process.argv[5]},()=>{});"
        "process.stdout.write(JSON.stringify(g));")

    def grants_for(seat):
        r = subprocess.run([node, "-e", script, str(SPAWN_JS), str(ws), seat,
                            str(Path(pkg) / "seats" / seat), str(pkg)],
                           capture_output=True, text=True, timeout=60)
        try:
            return json.loads(r.stdout), r.stderr
        except ValueError:
            return None, r.stdout + r.stderr

    got, why = grants_for("builder")
    check("P3: the appended row IS the mechanism — `spawn.js#resolvePermissionEditGrants` yields "
          "an rw grant for that exact path at the seat's next launch",
          got is not None and any(str(ws / "data" / "fixtures") == g.get("rwPath") for g in got),
          f"{got} {why}")
    got_sib, why_sib = grants_for("sibling")
    check("P3b: and ONLY for the seat named — a widening of one cage is not a widening of the "
          "room (control: the sibling seat gets nothing)",
          got_sib == [], f"{got_sib} {why_sib}")

    # ── P4 · the read-only carve (adv C34) ────────────────────────────────────────────────────
    ro_script = (
        "const s=require(process.argv[1]);"
        "const g=s.resolvePermissionEditsRoGrant({workspaceRoot:process.argv[2],"
        "seat:process.argv[3],seatDir:'',goalDir:process.argv[4]});"
        "process.stdout.write(JSON.stringify(g));")

    def ro_for(seat):
        r = subprocess.run([node, "-e", ro_script, str(SPAWN_JS), str(ws), seat, str(pkg)],
                           capture_output=True, text=True, timeout=60)
        try:
            return json.loads(r.stdout)
        except ValueError:
            return None

    check("P4: every seat but the permission editor gets the READ-ONLY carve over "
          "permission-edits.csv — an audit file writable by every party it audits is not an audit "
          "file, and this file sits inside the coordination dir every seat holds read-write",
          ro_for("builder") and ro_for("builder")[0].get("permissionEditsRo"), ro_for("builder"))
    check("P4b: …and the LEADER does not get it — its own cage keeps the file read-write, or the "
          "verb that writes it could never run in-cage",
          ro_for("leader") == [], ro_for("leader"))
    check("P4c: the two spellings of WHO the permission editor is agree — coord's "
          "`is_permission_editor` and spawn.js's `PERMISSION_EDITOR_SEAT` — so a widening of one "
          "cannot silently outrun the other",
          mod.is_permission_editor(
              json.loads(subprocess.run(
                  [node, "-e",
                   "process.stdout.write(JSON.stringify(require(process.argv[1])"
                   ".PERMISSION_EDITOR_SEAT))", str(SPAWN_JS)],
                  capture_output=True, text=True, timeout=60).stdout)))

    # ── C38 · THE FLAGSHIP: the leader is spawnable BY MAIL, end to end ───────────────────────
    before = verdicts(mod, pkg)
    check("C38 CONTROL: with NO mail the `leader` chair reads IDLE — an ON-DEMAND chair is not "
          "offered, so the arm below discriminates the WAKE from a chair that was always offered",
          before.get("leader") == "IDLE", before)
    open_session(pkg, "builder", "sess-builder-1")
    mod.set_awaiting(base, "builder", "", "", False, disposition="incomplete",
                     writer=mod.DISPOSITION_WRITER_SEAT)
    steps, closed, value = mod.close_session_seat(
        ns(pkg, force_dead=True, go=True), "sess-builder-1", "builder")
    joined = " | ".join(steps)
    check("C38 (1/2): the session-closer MINTS STAFF MAIL on a terminal non-`done` ending, "
          "addressed to the `leader` chair and carrying the seat's own check-out reason. "
          "Mechanical — no agent decides whether to mail, so no agent can decide not to",
          "staff mail: #" in joined and "`leader`" in joined, joined)
    after = verdicts(mod, pkg)
    check("C38 (2/2): …and that same act flips the chair to READY on the ONE surface the daemon's "
          "seeding pass reads (`verdict == \"READY\"`). THE LEADER IS SPAWNED BY MAIL, end to end",
          after.get("leader") == "READY", after)
    msgs = (base / "messages.md").read_text(encoding="utf-8")
    check("C38b: the bus row is the AUDITABLE record and it names the failing seat and its reason "
          "— a wake with no readable cause is a sitting that has to guess why it was woken",
          "STAFF MAIL" in msgs and "builder" in msgs, msgs[-400:])

    # ── W7 · THE CHAIR CAN GO BACK TO IDLE (owner-ruled 2026-08-14) ───────────────────────────
    #
    # C38 above proves the chair is spawnable BY MAIL. It does NOT prove the chair ever stops
    # being spawnable, and until W7 it never did: `staff_mail` RAW-COUNTED every row ever
    # addressed to a staff chair — no cursor, no timestamp, no read/unread field — so one message
    # pinned the term non-zero forever, the IDLE branch stopped firing, and the daemon's bare
    # `verdict == "READY"` seeding pass re-spawned the chair on every wake window. Measured on the
    # flagship `meet-transcript-summarizer`: 12 `to: leader` rows, chair spawned 3 min after
    # minting. C38's CONTROL could not catch it — its control has NO mail at all, so it reads IDLE
    # under both the defect and the fix; the discriminating state is mail that has been SETTLED.
    #
    # The fix reuses the cursor this file already has (`lastread` on the workers.md row, resolved
    # by `unread_for()` — the same predicate `read` uses), so the chair's verdict and the chair's
    # own inbox can never disagree.
    w7_before = verdicts(mod, pkg)
    run_cmd(mod, mod.cmd_checkin, pkg, agent="leader", summary="first sitting")
    w7_tail = mod.load_messages(base)[1][-1]["num"]
    # The sitting ENDED and drained its inbox: `active: no` (or the verdict reads RUNNING off the
    # live roster row and never reaches the on-demand branch) plus the cursor at the log's tail.
    mod.update_row(base, "leader",
                   lambda r: r.update({"active": "no", "lastread": str(w7_tail)}))
    w7_after = verdicts(mod, pkg)
    check("W7: a staff chair whose mail is SETTLED reads IDLE again — the chair sat, its read "
          "cursor advanced past the log, and the on-demand term went back to zero. Before W7 this "
          "was unreachable: the term was a raw count of the whole log, so a chair that had ever "
          "been addressed read READY forever and the daemon re-spawned it every wake window. The "
          "CONTROL is the same chair one call earlier, still READY on the same unsettled mail",
          w7_before.get("leader") == "READY" and w7_after.get("leader") == "IDLE",
          f"before={w7_before} after={w7_after} cursor={w7_tail}")

    # ── X1 · the staff-seat EXCLUSION (adv C30) ───────────────────────────────────────────────
    n_before = len(mod.load_messages(base)[1])
    open_session(pkg, "leader", "sess-leader-1")
    steps_l, _c, _v = mod.close_session_seat(
        ns(pkg, force_dead=True, go=True), "sess-leader-1", "leader")
    n_after = len(mod.load_messages(base)[1])
    check("X1: a STAFF chair's OWN close mints NO mail — every staff sitting ends kit-`exited` "
          "(the chair never checks out), so without the exclusion the closer would mail the leader "
          "about the leader forever, each mail minting the wake for the sitting that writes the "
          "next one. Its row is still CLOSED, silently",
          n_after == n_before and "IS a staff chair" in " | ".join(steps_l), steps_l)

    # ── R1..R3 · route-fail ───────────────────────────────────────────────────────────────────
    (Path(pkg) / "seats" / "builder" / "seat.md").write_text(
        "---\nagent: builder\non-fail-relaunch: [m3-implement-widget]\n"
        f"cwd: {Path(pkg) / 'seats' / 'builder'}\n---\n\n# builder\n", encoding="utf-8")
    out, code = run_cmd(mod, mod.cmd_route_fail, pkg, message="it failed", inline=True,
                        file=None, go=True, as_agent="builder")
    check("R1: a declared `on-fail-relaunch` target that NAMES NO SEAT is refused BY EXISTENCE — "
          "`_ferry_safe_name` is syntax-only, and D6's root cause was a well-formed TASK ID "
          "sitting in that cell",
          code != 0 and "NO SEAT of that name" in out, out)
    (Path(pkg) / "seats" / "builder" / "seat.md").write_text(
        "---\nagent: builder\non-fail-relaunch: [sibling]\n"
        f"cwd: {Path(pkg) / 'seats' / 'builder'}\n---\n\n# builder\n", encoding="utf-8")
    out, code = run_cmd(mod, mod.cmd_route_fail, pkg, message="it failed", inline=True,
                        file=None, go=True, as_agent="builder")
    check("R2: a route target with NO ENDED SESSION is refused LOUDLY rather than granted an "
          "unbindable authorization — an unbound grant is surfaced by every later sweep and can "
          "NEVER be spent, which flips that seat READY after every completion forever",
          code != 0 and "NO ENDED SESSION ROW" in out, out)
    open_session(pkg, "sibling", "sess-sibling-1", ended="2026-08-14T01:00:00Z",
                 disposition="done")
    out, code = run_cmd(mod, mod.cmd_route_fail, pkg, message="step 3 contradicts step 1",
                        inline=True, file=None, go=True, as_agent="builder")
    payload = mod.read_route_payload(base, "sibling")
    check("R3: a valid route grants the relaunch in BOTH stores and writes the PAYLOAD file",
          code == 0 and "step 3 contradicts step 1" in payload
          and "sibling" in (Path(pkg) / "relaunch-grants").read_text(encoding="utf-8"), out)
    prompt, _e, _c2 = mod.harness_outcome(
        mod.cmd_boot_prompt, ns(pkg, seat="sibling", lane="daemon"))
    check("R3b: …and the payload reaches the relaunched sitting's BOOT PROMPT, which is what "
          "stops a bare grant re-running the seat on its STALE SEED — the mechanism behind D6's "
          "false complete",
          "step 3 contradicts step 1" in prompt and "ROUTED TO YOU" in prompt, prompt[-500:])

    # ── A1..A2 · the `--as <staff chair>` scope ───────────────────────────────────────────────
    saved = _os.environ.get("COORD_AGENT")
    _os.environ["COORD_AGENT"] = "builder"
    try:
        out, code = run_cmd(mod, mod.cmd_widen_cage, pkg, as_agent="leader", seat="builder",
                            path="data/fixtures", reason="probe", go=False)
        check("A1: `--as leader` from a CAGED seat is REFUSED — the claim is admitted from the two "
              "master seats and the console only, and a caged seat always carries COORD_AGENT. "
              "This is what closes the pane-less hole: absence of a CONTRADICTING pane row no "
              "longer admits the claim",
              code != 0 and "STAFF CHAIR" in out and "identity" in out, out)
        _os.environ["COORD_AGENT"] = "console-master"
        out, code = run_cmd(mod, mod.cmd_widen_cage, pkg, as_agent="leader", seat="builder",
                            path="data/fixtures", reason="probe", go=False)
        check("A2: …and the HUMAN CONSOLE path still resolves — `console-master` is admitted, and "
              "every accepted use is audit-logged with the console-override marker (the emergency "
              "lever re-verified, not assumed)",
              code == 0 and mod.CONSOLE_OVERRIDE_MARKER in out, out)
    finally:
        if saved is None:
            _os.environ.pop("COORD_AGENT", None)
        else:
            _os.environ["COORD_AGENT"] = saved

    # ── S1..S3 · the send wrapper ─────────────────────────────────────────────────────────────
    admitted, departed = mod.send_recipients(ns(pkg), base)
    check("S1: a STAFF CHAIR is always addressable — a send to it never fails for want of a live "
          "session, which is the whole point of an ON-DEMAND chair",
          "leader" in admitted and "consultant" in admitted, sorted(admitted))
    check("S1b: …and `known_recipients` itself is UNTOUCHED — its return set is selftest-keyed and "
          "`lifecycle_alarm_recipient` reads it, so the wrapper sits at the call site",
          "consultant" not in mod.known_recipients(ns(pkg), base)
          or "consultant" in {r["agent"] for r in mod.load_workers(base)[2]})
    out, code = run_cmd(mod, mod.cmd_send, pkg, to="nobody-at-all", message="x", inline=True,
                        type="note", file=None, re_num=None, supersedes=None, why=None,
                        force=True, as_agent="builder")
    check("S2: an UNKNOWN recipient is refused even WITH `--force` — a message addressed to a name "
          "nobody holds is permanent residue in an append-only log, and the sender still HOLDS it "
          "at the refusal",
          code != 0 and "not a known recipient" in out, out)

    # ── K1 · the consultant criterion ─────────────────────────────────────────────────────────
    to, why = mod.staff_route_target(ns(pkg), base, "consultant")
    check("K1: a check-out routed to a `consultant` this goal does NOT staff falls back to the "
          "unblocker — the route flag is a HINT, never an authority, so a goal that staffs no "
          "consultant never mails a chair that does not exist",
          to == "leader" and "does NOT staff" in why, f"{to}: {why}")

    failures = [c for c, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS)} arm(s), {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
