#!/usr/bin/env python3
"""test_nudge.py — every claim about nudge.py, each with a CONTROL that must go red.

WHY THE CONTROLS. This run has produced fourteen checks that could not have caught what they were
built for. A test that passes proves nothing on its own: it may be blind (it cannot fail), it may
misgrade (it runs but its verdict is read wrong), or it may be hostile (it encodes the defect as
expected behaviour). So for every claim, the SAME assertion is run a second time against a
deliberately broken copy of nudge.py, and the run FAILS unless that copy goes red.

The mutation itself is checked: `variant()` asserts each textual substitution applied EXACTLY
once. A control built from a substitution that silently matched nothing is a copy of the original
— it would pass, and a passing control is indistinguishable from an unrun one. That assertion is
the thing standing between this file and becoming the fifteenth blind check.

Run:  python3 test_nudge.py
Exit: 0 only when every claim passed AND every control went red.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUDGE = HERE / "nudge.py"
# `coord.py` is a SIBLING in the team-kit; resolve it relatively so the drift check (C6) works
# from any checkout. Before the 2026-08-10 promotion into the kit this was an absolute path into
# one instance's vault, which the rbtv repo's General rule bars.
COORD_PY = HERE / "coord.py"

ROSTER_HEADER = (
    "# workers — agent sessions (script-managed, do not edit by hand)\n"
    "\n"
    "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
    "|-------|--------|-----------|------------|------------|-------------|-----------|\n"
)


# ------------------------------------------------------------------ fixtures

def make_package(tmp, rows):
    pkg = Path(tmp) / "pkg"
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    write_roster(pkg, rows)
    return pkg


def write_roster(pkg, rows):
    body = "".join(
        f"| {a} | {act} | {pane} | doing things | 2026-07-28 09:00 |  | 0 |\n"
        for a, act, pane in rows)
    (Path(pkg) / "coordination" / "workers.md").write_text(ROSTER_HEADER + body, encoding="utf-8")


def write_hb(path, records):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, sort_keys=True) + "\n")


def hb_record(seq, *, ts_epoch=None, interval=60.0, ok=True, recipient="chief-of-staff",
              transport="stdout", pane="%10"):
    ts_epoch = time.time() if ts_epoch is None else ts_epoch
    return {"seq": seq, "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts_epoch)),
            "ts_epoch": round(ts_epoch, 3), "recipient": recipient, "transport": transport,
            "pane": pane, "outcome": "sent:stdout", "ok": ok, "interval_s": interval, "pid": 1}


def read_hb(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def run_nudge(mod, args, env=None, timeout=60):
    e = dict(os.environ)
    e.pop("TMUX", None)
    e.pop("TMUX_PANE", None)
    if env:
        e.update(env)
    return subprocess.run([sys.executable, str(mod)] + [str(a) for a in args],
                          capture_output=True, text=True, timeout=timeout, env=e)


def variant(tag, subs):
    """A deliberately broken copy of nudge.py. Each substitution MUST apply exactly once."""
    src = NUDGE.read_text(encoding="utf-8")
    for old, new in subs:
        n = src.count(old)
        assert n == 1, (f"control '{tag}' is VACUOUS: its substitution matched {n} times, not 1.\n"
                        f"  looking for: {old!r}")
        src = src.replace(old, new, 1)
    d = Path(tempfile.mkdtemp(prefix="nudge-control-"))
    p = d / "nudge.py"
    p.write_text(src, encoding="utf-8")
    return p


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------ claims
# Every assertion function takes the path to a nudge.py (the real one, or a broken copy) and
# raises AssertionError when the behaviour is absent.

def a_seq_resumes_across_restarts(mod):
    """C1a — three separate `--once` invocations produce seq 1, 2, 3. Never a repeat."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%10")])
        hb = Path(tmp) / "hb.jsonl"
        for i in range(3):
            r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                                "--transport", "stdout", "--once", "--heartbeat", hb])
            assert r.returncode == 0, f"invocation {i} exited {r.returncode}: {r.stderr}"
        seqs = [x["seq"] for x in read_hb(hb)]
        assert seqs == [1, 2, 3], f"expected seq [1, 2, 3] across restarts, got {seqs}"
        assert len(set(seqs)) == len(seqs), f"seq repeated: {seqs}"


def a_seq_increments_within_a_run(mod):
    """C1b — one process, four ticks, seq 1..4 strictly increasing and never repeated."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%10")])
        hb = Path(tmp) / "hb.jsonl"
        r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                            "--transport", "stdout", "--interval", "0", "--max-ticks", "4",
                            "--heartbeat", hb])
        assert r.returncode == 0, f"exited {r.returncode}: {r.stderr}"
        seqs = [x["seq"] for x in read_hb(hb)]
        assert seqs == [1, 2, 3, 4], f"expected seq [1, 2, 3, 4] in one run, got {seqs}"
        assert all(b - a == 1 for a, b in zip(seqs, seqs[1:])), f"not monotonic by 1: {seqs}"


def a_gap_detectable_from_file_alone(mod):
    """C2a — a heartbeat missing seq 3 and 4 is reported as a GAP by `check`, which sees nothing
    but the file. A contiguous file is reported clean."""
    with tempfile.TemporaryDirectory() as tmp:
        gapped = Path(tmp) / "gapped.jsonl"
        write_hb(gapped, [hb_record(1), hb_record(2), hb_record(5)])
        r = run_nudge(mod, ["check", "--heartbeat", gapped])
        assert r.returncode == 1, f"gapped file should exit 1, got {r.returncode}: {r.stdout}"
        assert "GAP" in r.stdout, f"no GAP finding in: {r.stdout}"
        assert "[3, 4]" in r.stdout, f"missing seqs not named in: {r.stdout}"

        clean = Path(tmp) / "clean.jsonl"
        write_hb(clean, [hb_record(1), hb_record(2), hb_record(3)])
        r2 = run_nudge(mod, ["check", "--heartbeat", clean])
        assert r2.returncode == 0, f"clean file should exit 0, got {r2.returncode}: {r2.stdout}"
        assert "GAP" not in r2.stdout, f"false GAP on a contiguous file: {r2.stdout}"


def a_stall_detectable_from_file_alone(mod):
    """C2b — a heartbeat whose newest tick is far older than its own declared interval reads as
    STALE. This is the ruling's recorded residual: a stopped timer must not look like calm."""
    with tempfile.TemporaryDirectory() as tmp:
        old = Path(tmp) / "stale.jsonl"
        t0 = time.time() - 600
        write_hb(old, [hb_record(1, ts_epoch=t0, interval=60.0),
                       hb_record(2, ts_epoch=t0 + 60, interval=60.0)])
        r = run_nudge(mod, ["check", "--heartbeat", old])
        assert r.returncode == 1, f"stale file should exit 1, got {r.returncode}: {r.stdout}"
        assert "STALE" in r.stdout, f"no STALE finding in: {r.stdout}"

        fresh = Path(tmp) / "fresh.jsonl"
        write_hb(fresh, [hb_record(1, ts_epoch=time.time() - 1, interval=60.0)])
        r2 = run_nudge(mod, ["check", "--heartbeat", fresh])
        assert "STALE" not in r2.stdout, f"false STALE on a fresh file: {r2.stdout}"
        assert r2.returncode == 0, f"fresh file should exit 0: {r2.stdout}"


def a_duplicate_seq_detectable(mod):
    """C2c — the same seq twice (two loops on one heartbeat) is reported, because the gap
    arithmetic cannot be trusted while it holds."""
    with tempfile.TemporaryDirectory() as tmp:
        dupe = Path(tmp) / "dupe.jsonl"
        write_hb(dupe, [hb_record(1), hb_record(2), hb_record(2)])
        r = run_nudge(mod, ["check", "--heartbeat", dupe])
        assert r.returncode == 1, f"duplicate file should exit 1, got {r.returncode}: {r.stdout}"
        assert "DUPLICATE" in r.stdout, f"no DUPLICATE finding in: {r.stdout}"


def a_pane_reresolved_each_tick(mod):
    """C3 — the roster is rewritten with a different pane WHILE the loop runs; tick 1 and tick 2
    must record the two different panes. A loop that cached the first resolution records the old
    pane twice — which is the standing-bar violation this run has paid for four times."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%10")])
        hb = Path(tmp) / "hb.jsonl"
        e = dict(os.environ)
        e.pop("TMUX", None)
        e.pop("TMUX_PANE", None)
        p = subprocess.Popen(
            [sys.executable, str(mod), "run", "--package", str(pkg), "--to", "chief-of-staff",
             "--transport", "stdout", "--interval", "3", "--max-ticks", "2",
             "--heartbeat", str(hb)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=e)
        try:
            time.sleep(1.5)                      # after tick 1 (t=0), well before tick 2 (t=3)
            write_roster(pkg, [("chief-of-staff", "yes", "%20")])
            p.wait(timeout=30)
        finally:
            if p.poll() is None:
                p.kill()
        panes = [x["pane"] for x in read_hb(hb)]
        assert panes == ["%10", "%20"], (
            f"expected the pane to be re-resolved each tick -> ['%10', '%20'], got {panes} "
            f"(identical entries mean the resolution was cached)")


def a_latest_roster_row_wins(mod):
    """C7 — a seat with two roster rows resolves to the LATEST, matching coord.py's semantics
    (checkin appends; the newest row is the current sitting). Resolving the first row would nudge
    a pane the seat left."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%10"),
                                 ("chief-of-staff", "yes", "%20")])
        hb = Path(tmp) / "hb.jsonl"
        r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                            "--transport", "stdout", "--once", "--heartbeat", hb])
        assert r.returncode == 0, f"exited {r.returncode}: {r.stderr}"
        panes = [x["pane"] for x in read_hb(hb)]
        assert panes == ["%20"], f"latest roster row must win; got pane {panes}"


def a_departed_recipient_is_skipped(mod):
    """C7b — a recipient whose latest row is inactive is SKIPPED with a named reason, not nudged
    at its last known pane."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "no", "%10")])
        hb = Path(tmp) / "hb.jsonl"
        r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                            "--transport", "stdout", "--once", "--heartbeat", hb])
        assert r.returncode == 0, f"exited {r.returncode}: {r.stderr}"
        recs = read_hb(hb)
        assert len(recs) == 1, f"expected one record, got {len(recs)}"
        assert recs[0]["outcome"] == "skipped:departed", f"got outcome {recs[0]['outcome']!r}"
        assert recs[0]["pane"] is None, f"a departed seat must resolve to no pane: {recs[0]}"


def a_loop_survives_transport_failure(mod):
    """C4 — the file transport is pointed at a DIRECTORY, so every write raises. The loop must
    complete all three ticks, record all three as `error:`, and exit 0."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%10")])
        hb = Path(tmp) / "hb.jsonl"
        bad_out = Path(tmp) / "a-directory"
        bad_out.mkdir()
        r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                            "--transport", "file", "--out", bad_out,
                            "--interval", "0", "--max-ticks", "3", "--heartbeat", hb])
        assert r.returncode == 0, (
            f"the loop must survive transport failure; it exited {r.returncode}\n{r.stderr}")
        recs = read_hb(hb)
        assert len(recs) == 3, f"expected 3 ticks despite failures, got {len(recs)}"
        assert [x["seq"] for x in recs] == [1, 2, 3], f"seq broke under failure: {recs}"
        bad = [x["outcome"] for x in recs]
        assert all(o.startswith("error:") for o in bad), (
            f"a transport failure must be recorded as `error:` at the transport layer, got {bad}")
        assert not any(x["ok"] for x in recs), f"failed ticks must not be ok=true: {recs}"


def _tmux_shim(tmp):
    """A fake `tmux` on PATH that records its argv and does nothing else. The real tmux is never
    reached: the test asserts `which tmux` resolves to this shim before running anything, and the
    roster pane is %999999, which no tmux server can own."""
    d = Path(tmp) / "bin"
    d.mkdir(parents=True, exist_ok=True)
    shim = d / "tmux"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json, os\n"
        "with open(os.environ['NUDGE_TMUX_MARKER'], 'a') as f:\n"
        "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n",
        encoding="utf-8")
    shim.chmod(0o755)
    marker = Path(tmp) / "tmux-calls.jsonl"
    env = {"PATH": f"{d}{os.pathsep}{os.environ.get('PATH', '')}",
           "NUDGE_TMUX_MARKER": str(marker)}
    assert shutil.which("tmux", path=env["PATH"]) == str(shim), (
        "SAFETY ABORT: the fake tmux does not win on PATH — refusing to run a tmux transport test")
    return env, marker


def a_tmux_dry_run_builds_argv_without_executing(mod):
    """C5a — under --dry-run the tmux transport records an EXPLICIT `-t <pane>` argv and executes
    nothing. Proven by a fake tmux on PATH that would leave a marker file if it were called."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%999999")])
        hb = Path(tmp) / "hb.jsonl"
        env, marker = _tmux_shim(tmp)
        r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                            "--transport", "tmux", "--dry-run", "--once", "--heartbeat", hb],
                      env=env)
        assert r.returncode == 0, f"exited {r.returncode}: {r.stderr}"
        assert not marker.exists(), (
            f"--dry-run EXECUTED tmux: {marker.read_text(encoding='utf-8')!r}")
        recs = read_hb(hb)
        assert len(recs) == 1, f"expected one record, got {recs}"
        out = recs[0]["outcome"]
        assert out.startswith("dry-run:"), f"outcome should be a dry-run record, got {out!r}"
        assert "-t %999999" in out, f"the argv must name the pane explicitly with -t: {out!r}"
        assert "send-keys" in out, f"not a send-keys argv: {out!r}"


def a_tmux_live_argv_names_the_pane(mod):
    """C5b — with --dry-run OFF, the transport runs `tmux send-keys -t <pane> -l <text>` then
    `tmux send-keys -t <pane> Enter`, against the FAKE tmux only. This is what proves the argv is
    both explicit and correct; the dispatcher runs the same path against the real one."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%999999")])
        hb = Path(tmp) / "hb.jsonl"
        env, marker = _tmux_shim(tmp)
        r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                            "--transport", "tmux", "--once", "--heartbeat", hb,
                            "--message", "CHECKS"], env=env)
        assert r.returncode == 0, f"exited {r.returncode}: {r.stderr}"
        assert marker.exists(), "the live tmux transport called nothing"
        calls = [json.loads(ln) for ln in marker.read_text(encoding="utf-8").splitlines() if ln]
        assert len(calls) == 2, f"expected a text call and an Enter call, got {calls}"
        assert calls[0] == ["send-keys", "-t", "%999999", "-l", "[nudge #1] CHECKS"], calls[0]
        assert calls[1] == ["send-keys", "-t", "%999999", "Enter"], calls[1]
        assert read_hb(hb)[0]["outcome"] == "sent:tmux:%999999", read_hb(hb)[0]


def a_ticks_are_spaced_by_the_interval(mod):
    """C10 — the loop actually WAITS --interval between ticks, measured from the timestamps it
    wrote itself. Without this claim, `--interval` could be ignored entirely: every other timing
    check here either uses interval 0 or would still pass on a loop that spun flat out."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%10")])
        hb = Path(tmp) / "hb.jsonl"
        t0 = time.monotonic()
        r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                            "--transport", "stdout", "--interval", "1", "--max-ticks", "3",
                            "--heartbeat", hb])
        wall = time.monotonic() - t0
        assert r.returncode == 0, f"exited {r.returncode}: {r.stderr}"
        ts = [x["ts_epoch"] for x in read_hb(hb)]
        assert len(ts) == 3, f"expected 3 ticks, got {len(ts)}"
        deltas = [round(b - a, 3) for a, b in zip(ts, ts[1:])]
        assert all(0.8 <= d <= 1.6 for d in deltas), (
            f"ticks must be ~1s apart at --interval 1; got deltas {deltas}")
        assert wall >= 1.8, f"3 ticks at 1s cannot complete in {wall:.2f}s wall time"


def a_dry_run_is_not_recorded_as_delivered(mod):
    """C9 — a --dry-run tick ran, but delivered NOTHING, and the heartbeat must say so. An `ok`
    that reads true for a rehearsal is the misgrading shape: a consumer counting delivered nudges
    would count rehearsals as arrivals and read a silent room as a served one."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%999999")])
        hb = Path(tmp) / "hb.jsonl"
        env, marker = _tmux_shim(tmp)
        r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                            "--transport", "tmux", "--dry-run", "--once", "--heartbeat", hb],
                      env=env)
        assert r.returncode == 0, f"exited {r.returncode}: {r.stderr}"
        rec = read_hb(hb)[0]
        assert rec["outcome"].startswith("dry-run:"), rec
        assert rec["ok"] is False, f"a dry-run tick must NOT be recorded as delivered: {rec}"
        c = run_nudge(mod, ["check", "--heartbeat", hb])
        assert "did not deliver" in c.stdout, (
            f"`check` must surface the non-delivery from the file alone: {c.stdout}")


def a_second_loop_is_refused(mod):
    """C8 — a second loop on the same heartbeat is refused (exit 3), because two loops resuming
    from the same max seq would emit duplicates and destroy the gap signal."""
    import fcntl
    with tempfile.TemporaryDirectory() as tmp:
        pkg = make_package(tmp, [("chief-of-staff", "yes", "%10")])
        hb = Path(tmp) / "hb.jsonl"
        held = open(str(hb) + ".lock", "w", encoding="utf-8")
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            r = run_nudge(mod, ["run", "--package", pkg, "--to", "chief-of-staff",
                                "--transport", "stdout", "--once", "--heartbeat", hb])
        finally:
            held.close()
        assert r.returncode == 3, (
            f"a second loop must be refused with exit 3, got {r.returncode}: {r.stdout}{r.stderr}")
        assert read_hb(hb) == [], "the refused loop wrote a heartbeat record anyway"


def a_roster_grammar_matches_coord_py(mod):
    """C6 — the roster row grammar in nudge.py is byte-identical to coord.py's WORKER_ROW,
    re-extracted from coord.py's source at test time. A copied regex that drifts silently starts
    resolving the wrong pane, or none."""
    import ast
    assert COORD_PY.is_file(), f"coord.py not found at {COORD_PY}"
    tree = ast.parse(COORD_PY.read_text(encoding="utf-8"))
    found = None
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "WORKER_ROW"):
            found = ast.literal_eval(node.value.args[0])
    assert found, "could not extract WORKER_ROW from coord.py"
    m = load_module(mod, "nudge_under_test_" + str(abs(hash(str(mod)))))
    assert m.WORKER_ROW.pattern == found, (
        "roster grammar has DRIFTED from coord.py\n"
        f"  coord.py: {found!r}\n"
        f"  nudge.py: {m.WORKER_ROW.pattern!r}")


# ------------------------------------------------------------------ controls
# (claim id, description, assertion, [(control name, [(old, new), ...]), ...])

CACHE_SUBS = [
    ("DEFAULT_INTERVAL = 60.0",
     "DEFAULT_INTERVAL = 60.0\n_CACHED = None"),
    ("    pane, why = resolve_recipient(cfg.package, cfg.to)",
     "    global _CACHED\n"
     "    if _CACHED is None:\n"
     "        _CACHED = resolve_recipient(cfg.package, cfg.to)\n"
     "    pane, why = _CACHED"),
]

INNER_GUARD = """        try:
            outcome, ok = deliver(cfg, text, pane)
        except Exception as exc:            # transport failure: recorded, never fatal
            outcome = f"error:{type(exc).__name__}:{exc}"
            print(f"[nudge #{seq}] transport failed: {outcome}", file=sys.stderr, flush=True)"""
INNER_GUARD_REMOVED = """        outcome, ok = deliver(cfg, text, pane)"""

OUTER_GUARD = """        try:
            rec = do_tick(cfg, seq)
        except Exception as exc:            # belt-and-braces: resolution/format bugs, not transport"""
OUTER_GUARD_REMOVED = """        rec = do_tick(cfg, seq)
        if False:
            exc = None"""

CLAIMS = [
    ("C1a", "seq resumes across restarts and never repeats",
     a_seq_resumes_across_restarts,
     [("seq always restarts at 1",
       [("    return (max((r[\"seq\"] for r in recs), default=0)) + 1", "    return 1")])]),

    ("C1b", "seq increments within one run, monotonic by 1",
     a_seq_increments_within_a_run,
     [("seq frozen (no increment)", [("        seq += 1\n", "        seq += 0\n")])]),

    ("C2a", "a GAP is detectable from the heartbeat file alone",
     a_gap_detectable_from_file_alone,
     [("gap detector always reports none",
       [("    missing = sorted(set(range(lo, hi + 1)) - set(seqs))", "    missing = []")])]),

    ("C2b", "a STALLED loop is detectable from the heartbeat file alone",
     a_stall_detectable_from_file_alone,
     [("staleness check disabled",
       [("    if age > STALE_FACTOR * iv:", "    if False:")])]),

    ("C2c", "a DUPLICATE seq is detectable from the heartbeat file alone",
     a_duplicate_seq_detectable,
     [("duplicate detector always reports none",
       [("    dupes = sorted({s for s in seqs if seqs.count(s) > 1})", "    dupes = []")])]),

    ("C3", "the recipient's pane is re-resolved every tick, never cached",
     a_pane_reresolved_each_tick,
     [("resolution hoisted into a module-level cache", CACHE_SUBS)]),

    ("C7a", "the LATEST roster row wins, as in coord.py",
     a_latest_roster_row_wins,
     [("first roster row wins instead of the latest",
       [("    row = rows[-1]", "    row = rows[0]")])]),

    ("C7b", "a departed recipient is skipped, not nudged at its stale pane",
     a_departed_recipient_is_skipped,
     [("departed check removed",
       [("    if row[\"active\"] != \"yes\":\n        return None, \"departed\"\n", "")])]),

    ("C4", "the loop keeps ticking after a transport failure",
     a_loop_survives_transport_failure,
     [("both failure guards removed (loop dies on tick 1)",
       [(INNER_GUARD, INNER_GUARD_REMOVED), (OUTER_GUARD, OUTER_GUARD_REMOVED)]),
      ("transport-layer guard removed (outcome misattributed)",
       [(INNER_GUARD, INNER_GUARD_REMOVED)])]),

    ("C5a", "tmux --dry-run builds an explicit -t argv and executes nothing",
     a_tmux_dry_run_builds_argv_without_executing,
     [("dry-run gate bypassed (it executes)", [("    if dry_run:", "    if False:")]),
      ("argv drops the explicit -t target",
       [("    return ([\"tmux\", \"send-keys\", \"-t\", pane, \"-l\", text],\n"
         "            [\"tmux\", \"send-keys\", \"-t\", pane, \"Enter\"])",
         "    return ([\"tmux\", \"send-keys\", \"-l\", text],\n"
         "            [\"tmux\", \"send-keys\", \"Enter\"])")])]),

    ("C5b", "the live tmux argv names the pane explicitly (against a fake tmux)",
     a_tmux_live_argv_names_the_pane,
     [("argv drops the explicit -t target",
       [("    return ([\"tmux\", \"send-keys\", \"-t\", pane, \"-l\", text],\n"
         "            [\"tmux\", \"send-keys\", \"-t\", pane, \"Enter\"])",
         "    return ([\"tmux\", \"send-keys\", \"-l\", text],\n"
         "            [\"tmux\", \"send-keys\", \"Enter\"])")])]),

    ("C10", "ticks are spaced by --interval, measured from the heartbeat's own timestamps",
     a_ticks_are_spaced_by_the_interval,
     [("the interval wait is skipped (loop spins)",
       [("        remaining = cfg.interval - (time.monotonic() - started)",
         "        remaining = 0")])]),

    ("C9", "a --dry-run tick is recorded as NOT delivered",
     a_dry_run_is_not_recorded_as_delivered,
     [("dry-run claims delivery",
       [("        return f\"dry-run:{rendered}\", False      # rehearsed, NOT delivered",
         "        return f\"dry-run:{rendered}\", True")])]),

    ("C8", "a second loop on one heartbeat is refused",
     a_second_loop_is_refused,
     [("lock never taken",
       [("            fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)", "            pass")])]),

    ("C6", "the roster grammar has not drifted from coord.py's WORKER_ROW",
     a_roster_grammar_matches_coord_py,
     [("regex mutated", [("(?P<agent>[^|]+?)", "(?P<agent>[^|]+)")])]),
]


def main():
    failures = []
    print(f"nudge.py acceptance — {len(CLAIMS)} claims, each with at least one control\n"
          f"module under test: {NUDGE}\n")
    for cid, desc, fn, controls in CLAIMS:
        print(f"CLAIM {cid} — {desc}")
        t0 = time.monotonic()
        try:
            fn(NUDGE)
            print(f"  main   : PASS ({time.monotonic() - t0:.1f}s)")
        except Exception as exc:
            print(f"  main   : FAIL — {type(exc).__name__}: {exc}")
            failures.append(f"{cid} main: {exc}")
            # A failing claim still gets its controls run: a control that also fails tells us
            # nothing, and we want that visible rather than skipped.
        for name, subs in controls:
            try:
                broken = variant(f"{cid}/{name}", subs)
            except AssertionError as exc:
                print(f"  control: VACUOUS — {exc}")
                failures.append(f"{cid} control '{name}': vacuous mutation")
                continue
            try:
                fn(broken)
            except AssertionError as exc:
                first = str(exc).splitlines()[0][:140]
                print(f"  control: RED as required — '{name}' -> {first}")
                continue
            except Exception as exc:
                print(f"  control: RED as required — '{name}' -> "
                      f"{type(exc).__name__}: {str(exc).splitlines()[0][:120]}")
                continue
            finally:
                shutil.rmtree(broken.parent, ignore_errors=True)
            print(f"  control: *** DID NOT GO RED *** — '{name}' passed the same assertion. "
                  f"This check is BLIND.")
            failures.append(f"{cid} control '{name}': did not go red")
        print()

    if failures:
        print(f"RESULT: {len(failures)} problem(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"RESULT: all {len(CLAIMS)} claims passed and every control went red")
    return 0


if __name__ == "__main__":
    sys.exit(main())
