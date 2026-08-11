#!/usr/bin/env python3
"""nudge.py — a deterministic nudge loop that fires at a named seat every N seconds.

WHY THIS EXISTS. Owner ruling `r-cos-self-nudge-timer` (goal `decisions.md`): the
`chief-of-staff` seat must, as its first act after check-in, have a timer nudging it every ONE
MINUTE to run its checks. The failure it fixes is PASSIVITY — a seat that is alive, in context
and in RAM, and simply not running its sweep. The ruling's own recorded residual is that a
stopped timer is SILENT and indistinguishable from a quiet room; that residual is why every tick
here carries a MONOTONIC SEQUENCE NUMBER and appends to a heartbeat file, and why `check` mode
exists: a gap or a stall must be readable from the heartbeat file ALONE, by a consumer that never
saw the loop run.

WHAT THIS IS NOT. It is NOT the ignite runtime's `ticker engine` (KG: the runtime's SINGLE
time-based duty loop; "a second identical scheduler would be a defect"). This is a run-local
operational nudge loop for one recipient in one run package. It realizes no KG record, claims no
`realizes:` edge, and must never be wired into the runtime's clock. The word `seat` is the KG term
for a run participant; the word "worker" appears here only inside the frozen roster grammar it
must parse (`workers.md`), never as a name for a participant.

PANE RESOLUTION — THE STANDING BAR. The recipient's pane is RESOLVED FROM THE ROSTER AT EVERY
TICK and is NEVER remembered, cached, or accepted as a literal on the command line. There is
deliberately no `--pane` flag. In this run the owner door moved four times in one night and every
recorded pane id went stale; a loop holding a literal `%n` protects a dead pane and leaves the
real recipient un-nudged. Resolution follows `coord.py`'s own recipient semantics exactly
(`cmd_send`'s wake block, coord.py:4448-4470): latest roster row for the name wins, then
`active != yes` -> departed, empty pane -> no pane, else that pane.

TRANSPORTS are pluggable so the loop can be built and proven without touching tmux:
  stdout  — writes the nudge to stdout. Fully implemented, fully tested.
  file    — appends the nudge to a file. Fully implemented, fully tested.
  tmux    — builds an EXPLICIT `tmux send-keys -t <pane> ...` argv from the freshly resolved
            pane. Under `--dry-run` the argv is recorded and NOT executed. It never relies on an
            ambient `TMUX_PANE`; the target is always named.

KNOWN LIMITATIONS, stated rather than discovered:
  - ONE loop per (heartbeat file). Enforced with an exclusive `flock` on `<heartbeat>.lock`; a
    second loop refuses with exit code 3, because two loops sharing a heartbeat would each resume
    the sequence from the same max and emit duplicate seqs, destroying the gap signal.
  - No heartbeat rotation. The file grows one JSON line per tick (~200 bytes; ~0.3 MB/day at 60s).
  - `check` mode's staleness verdict needs a clock; it compares the last record's epoch against
    `time.time()`. A consumer on another box with a skewed clock reads it wrong.
  - This loop does NOT write to the coordination bus. It types into a pane (or a file, or stdout).
    Routing nudges through `coordinate send` instead would give threading and a delivery record;
    that is a design choice for whoever lands this, not a defect of this loop.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

# The roster row grammar. This is a DELIBERATE COPY of `WORKER_ROW` in
# `3-resources/tools/rbtv/ignite/team-kit/coord.py` (coord.py:157-161), not an import: coord.py is
# under another seat's custody, it is 600 KB, and importing it for a regex would couple this loop
# to that module's import-time behaviour — a broken save there already took `coordinate` down
# room-wide once. The copy is drift-checked by `test_nudge.py` claim C6, which re-extracts the
# pattern from coord.py's source and compares it to this one.
WORKER_ROW = re.compile(
    r"^\|\s*(?P<agent>[^|]+?)\s*\|\s*(?P<active>yes|no)\s*\|\s*(?P<pane>[^|]*?)\s*"
    r"\|\s*(?P<summary>[^|]*?)\s*\|\s*(?P<checkin>[^|]*?)\s*\|\s*(?P<checkout>[^|]*?)\s*"
    r"\|\s*(?P<lastread>[^|]*?)\s*\|$"
)

DEFAULT_INTERVAL = 60.0
DEFAULT_MESSAGE = ("self-nudge timer — run your standing checks now "
                   "(`coordinate status`, then your playbook sweep). "
                   "If there is nothing to do, say so and keep the beat.")
# A stall verdict needs a threshold. 2.5 intervals: one missed tick alone is jitter (a slow
# transport, a busy box); two consecutive misses is not.
STALE_FACTOR = 2.5


# ---------------------------------------------------------------- roster resolution

def load_roster_rows(package: Path):
    """Every parsed row of the package roster, in file order. [] when the file is absent."""
    path = Path(package) / "coordination" / "workers.md"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = WORKER_ROW.match(line.rstrip("\n"))
        if m and m.group("agent") != "agent":
            rows.append({k: (v or "").strip() for k, v in m.groupdict().items()})
    return rows


def resolve_recipient(package: Path, to: str):
    """(pane, reason) for a recipient name, resolved FRESH from the roster on disk.

    Mirrors coord.py's wake-target semantics (coord.py:4448-4470) so a nudge reaches exactly the
    seats a `coordinate send` wake would reach, and skips for the same stated reasons:
        (None, 'not-launched')  no row at all — named or briefed, never checked in
        (None, 'departed')      had a row, checked out or closed
        (None, 'no-pane')       checked in without a pane
        (pane, 'ok')            live row with a pane
    Latest row wins: `coordinate checkin` appends, so the newest row is the current sitting.
    """
    rows = [r for r in load_roster_rows(package) if r["agent"] == to]
    if not rows:
        return None, "not-launched"
    row = rows[-1]
    if row["active"] != "yes":
        return None, "departed"
    if not row["pane"]:
        return None, "no-pane"
    return row["pane"], "ok"


# ---------------------------------------------------------------- approval gate

# G-289. A pane parked on its harness's interactive approval modal is a BLIND GATE: the pane is
# frozen, so a nudge typed into it is not read and lands as stray text INSIDE the modal's own
# input — corrupting the very gate the leader has to answer. coord.py already owns that detection
# (`at_approval_gate`, pane TITLE only) and `deliver_wakes` already skips on it; this loop CALLS
# that function instead of growing a second detector that could drift from it.
#
# Imported LAZILY and never fatally, unlike the WORKER_ROW grammar above (copied for exactly these
# reasons): coord.py is 2 MB, is under another seat's custody, and a broken save there has taken
# the room's messaging down at import once already. A loop that cannot tick because coord.py is
# mid-save is a worse failure than an undetected gate, so a failed import turns detection OFF and
# says so on stderr — the same fail-open direction as at_approval_gate itself, which returns False
# on any missing signal rather than declaring a seat gated.
_COORD_GATE = None          # coord.at_approval_gate; False once the import has failed


def at_approval_gate(pane):
    """True when coord.py says this pane is parked on an interactive approval prompt."""
    global _COORD_GATE
    if _COORD_GATE is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            from coord import at_approval_gate as gate
        except Exception as exc:
            print(f"[nudge] coord.py unavailable ({type(exc).__name__}: {exc}) — approval-gate "
                  f"detection is OFF for this loop", file=sys.stderr, flush=True)
            gate = False
        _COORD_GATE = gate
    if not _COORD_GATE:
        return False
    try:
        return _COORD_GATE(pane)
    except Exception:
        # The detector shells out to tmux; if tmux is gone it RAISES rather than returning False.
        # A gate check must never be the thing that stops a tick — same fail-safe direction as
        # at_approval_gate's own "missing signal is not a gate".
        return False


# ---------------------------------------------------------------- transports

# Every transport returns (outcome, delivered). `delivered` is what the heartbeat's `ok` field
# means, and it is a SEPARATE fact from "the tick ran": a --dry-run tick ran fine and delivered
# NOTHING. Recording it as ok=true would make the heartbeat confidently wrong — a consumer
# counting delivered nudges would count rehearsals as arrivals. That is the misgrading shape, so
# the honest half is returned by the transport instead of sniffed from the outcome string.

def transport_stdout(text, pane, dry_run):
    print(text, flush=True)
    return "sent:stdout", True


def transport_file(text, pane, dry_run, out_path):
    with open(out_path, "a", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return f"sent:file:{out_path}", True


def tmux_argvs(pane, text):
    """The EXPLICIT argv pair this loop would run. The pane is always named with `-t`; nothing is
    ever left to an ambient TMUX_PANE. Mirrors coord.py's tmux_send_text/tmux_send_enter pair
    (coord.py:1031-1040): literal text first, then a separate Enter."""
    return (["tmux", "send-keys", "-t", pane, "-l", text],
            ["tmux", "send-keys", "-t", pane, "Enter"])


def transport_tmux(text, pane, dry_run):
    argv_text, argv_enter = tmux_argvs(pane, text)
    rendered = f"{shlex.join(argv_text)} && {shlex.join(argv_enter)}"
    if dry_run:
        print(f"[nudge dry-run] {rendered}", file=sys.stderr, flush=True)
        return f"dry-run:{rendered}", False      # rehearsed, NOT delivered
    r1 = subprocess.run(argv_text, capture_output=True, text=True)
    if r1.returncode != 0:
        raise RuntimeError(f"tmux send-keys -l failed: {r1.stderr.strip() or r1.returncode}")
    r2 = subprocess.run(argv_enter, capture_output=True, text=True)
    if r2.returncode != 0:
        raise RuntimeError(f"tmux send-keys Enter failed: {r2.stderr.strip() or r2.returncode}")
    return f"sent:tmux:{pane}", True


def deliver(cfg, text, pane):
    if cfg.transport == "stdout":
        return transport_stdout(text, pane, cfg.dry_run)
    if cfg.transport == "file":
        return transport_file(text, pane, cfg.dry_run, cfg.out)
    if cfg.transport == "tmux":
        return transport_tmux(text, pane, cfg.dry_run)
    raise ValueError(f"unknown transport {cfg.transport!r}")


# ---------------------------------------------------------------- heartbeat

def read_records(path):
    """Every parsed heartbeat record. Unparseable lines are SKIPPED but counted by the caller via
    the returned bad-line list — a truncated tail from a killed process must not make the whole
    file unreadable, and must not be silent either."""
    good, bad = [], []
    p = Path(path)
    if not p.exists():
        return good, bad
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except (ValueError, TypeError):
            bad.append(i)
            continue
        if isinstance(rec, dict) and isinstance(rec.get("seq"), int):
            good.append(rec)
        else:
            bad.append(i)
    return good, bad


def next_seq(path):
    """The seq this loop must start at: one past the highest already on disk.

    Resuming (rather than restarting at 1) is the whole point — a restarted loop that re-emitted
    seq 1 would make its own restart invisible and would put duplicate seqs in the file, which is
    the one thing the gap detector cannot interpret."""
    recs, _ = read_records(path)
    return (max((r["seq"] for r in recs), default=0)) + 1


def append_record(path, rec):
    """Append ONE record as one line. Opened in append mode per tick so a consumer tailing the
    file sees each tick as it lands, and a killed loop loses at most the line it was writing."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


# ---------------------------------------------------------------- the loop

def do_tick(cfg, seq):
    """One beat. Returns the heartbeat record. Raises only on a programming error — every
    expected failure (no roster, dead recipient, transport blew up) becomes an outcome string."""
    # RESOLVED HERE, INSIDE THE TICK, EVERY TICK. Hoisting this call out of the loop is the
    # cached-pane defect this loop exists to avoid; test_nudge.py C3 runs that hoist as a control.
    pane, why = resolve_recipient(cfg.package, cfg.to)
    text = f"[nudge #{seq}] {cfg.message}"
    ok = False
    if pane is None:
        outcome = f"skipped:{why}"
    elif cfg.transport == "tmux" and at_approval_gate(pane):
        # Only the tmux transport can be corrupted by a modal — a stdout or file nudge is not
        # typed into the pane. Scoping the check here also keeps those transports tmux-free:
        # coord.py's detector SHELLS OUT to tmux, and subprocess raises (not returncode!=0) when
        # tmux is not installed, so an unconditional check turns every tick on a tmux-less box
        # into a tick-error. Measured 2026-08-10.
        outcome = "skipped:at-approval-gate"
    else:
        try:
            outcome, ok = deliver(cfg, text, pane)
        except Exception as exc:            # transport failure: recorded, never fatal
            outcome = f"error:{type(exc).__name__}:{exc}"
            print(f"[nudge #{seq}] transport failed: {outcome}", file=sys.stderr, flush=True)
    now = time.time()
    return {
        "seq": seq,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
        "ts_epoch": round(now, 3),
        "recipient": cfg.to,
        "transport": cfg.transport,
        "pane": pane,
        "outcome": outcome,
        "ok": ok,
        "interval_s": cfg.interval,
        "pid": os.getpid(),
    }


def run_loop(cfg):
    """Tick until told to stop. NOTHING raises out of this body: a tick that explodes still
    produces a record, because a loop that dies on one bad tick reintroduces exactly the silence
    the sequence number was added to break."""
    seq = next_seq(cfg.heartbeat)
    ticks = 0
    while True:
        started = time.monotonic()
        try:
            rec = do_tick(cfg, seq)
        except Exception as exc:            # belt-and-braces: resolution/format bugs, not transport
            rec = {"seq": seq, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "ts_epoch": round(time.time(), 3), "recipient": cfg.to,
                   "transport": cfg.transport, "pane": None,
                   "outcome": f"tick-error:{type(exc).__name__}:{exc}", "ok": False,
                   "interval_s": cfg.interval, "pid": os.getpid()}
            print(f"[nudge #{seq}] TICK ERROR: {rec['outcome']}", file=sys.stderr, flush=True)
        try:
            append_record(cfg.heartbeat, rec)
        except Exception as exc:
            # The heartbeat is the loop's only proof of life. If it cannot be written, say so on
            # stderr every time — never swallow it, and never stop ticking over it.
            print(f"[nudge #{seq}] HEARTBEAT WRITE FAILED: {type(exc).__name__}: {exc}",
                  file=sys.stderr, flush=True)
        seq += 1
        ticks += 1
        if cfg.once or (cfg.max_ticks and ticks >= cfg.max_ticks):
            return 0
        remaining = cfg.interval - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)


# ---------------------------------------------------------------- check mode

def check_heartbeat(path, interval=None, now=None):
    """(exit_code, lines) — everything wrong with a heartbeat file, derived FROM THE FILE ALONE.

    Three distinct findings, because they have three different causes:
      GAP        seqs missing between the first and last recorded — the loop was down and came
                 back, or ticks were lost.  (Detectable only because seq is monotonic.)
      DUPLICATE  the same seq twice — two loops shared one heartbeat file, or one restarted
                 without resuming. The gap arithmetic cannot be trusted while this holds.
      STALE      the newest record is older than STALE_FACTOR * its own declared interval — the
                 loop is not ticking NOW. This is the reading that the ruling's recorded residual
                 asked for: a stopped timer must not look like a quiet room.
    """
    recs, bad = read_records(path)
    out, code = [], 0
    if not Path(path).exists():
        return 1, [f"MISSING: no heartbeat file at {path} — the loop has never ticked, or is "
                   f"writing somewhere else"]
    if bad:
        out.append(f"UNPARSEABLE: {len(bad)} line(s) at {bad[:10]}")
        code = 1
    if not recs:
        return 1, out + [f"EMPTY: {path} holds no parseable tick records"]
    seqs = [r["seq"] for r in recs]
    dupes = sorted({s for s in seqs if seqs.count(s) > 1})
    lo, hi = min(seqs), max(seqs)
    missing = sorted(set(range(lo, hi + 1)) - set(seqs))
    last = max(recs, key=lambda r: r["seq"])
    iv = float(interval if interval is not None else last.get("interval_s") or DEFAULT_INTERVAL)
    age = (time.time() if now is None else now) - float(last.get("ts_epoch") or 0)
    out.append(f"records={len(recs)} seq={lo}..{hi} recipient={last.get('recipient')} "
               f"transport={last.get('transport')} interval={iv}s last={last.get('ts')} "
               f"age={age:.1f}s")
    if dupes:
        out.append(f"DUPLICATE: seq repeated {dupes} — more than one loop is writing this file")
        code = 1
    if missing:
        out.append(f"GAP: {len(missing)} missing seq(s) {missing[:20]}"
                   f"{' ...' if len(missing) > 20 else ''}")
        code = 1
    if age > STALE_FACTOR * iv:
        out.append(f"STALE: last tick was {age:.1f}s ago, over {STALE_FACTOR}x the {iv}s "
                   f"interval — the loop is NOT ticking")
        code = 1
    failed = [r for r in recs if not r.get("ok")]
    if failed:
        out.append(f"note: {len(failed)}/{len(recs)} tick(s) did not deliver; newest "
                   f"non-delivery: #{failed[-1]['seq']} {failed[-1].get('outcome')}")
    if code == 0:
        out.append("OK: no gap, no duplicate, not stale")
    return code, out


# ---------------------------------------------------------------- cli

def default_heartbeat(package, to):
    return str(Path(package) / "coordination" / f"nudge-heartbeat-{to}.jsonl")


def build_parser():
    p = argparse.ArgumentParser(
        prog="nudge.py",
        description="Deterministic nudge loop for one named seat of one run package.")
    sub = p.add_subparsers(dest="mode")

    r = sub.add_parser("run", help="tick at a recipient every --interval seconds")
    r.add_argument("--package", required=True, help="absolute path to the run package")
    r.add_argument("--to", required=True, help="recipient SEAT NAME (never a pane id)")
    r.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                   help=f"seconds between ticks (default {DEFAULT_INTERVAL:g})")
    r.add_argument("--transport", choices=("stdout", "file", "tmux"), default="tmux")
    r.add_argument("--once", action="store_true", help="one tick, then exit")
    r.add_argument("--max-ticks", type=int, default=0, help="stop after N ticks (0 = forever)")
    r.add_argument("--dry-run", action="store_true",
                   help="tmux transport: build and record the argv, do NOT execute it")
    r.add_argument("--message", default=DEFAULT_MESSAGE)
    r.add_argument("--heartbeat", default=None,
                   help="heartbeat JSONL (default <package>/coordination/nudge-heartbeat-<to>.jsonl)")
    r.add_argument("--out", default=None, help="file transport: destination path")
    r.add_argument("--no-lock", action="store_true",
                   help="skip the single-loop lock (for tests only)")

    c = sub.add_parser("check", help="report gaps/duplicates/staleness from a heartbeat file alone")
    c.add_argument("--heartbeat", required=True)
    c.add_argument("--interval", type=float, default=None,
                   help="override the interval recorded in the file")
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # `run` is the default mode so the loop can be pasted as `nudge.py --package X --to Y`.
    if not argv or argv[0].startswith("-"):
        argv = ["run"] + argv
    args = build_parser().parse_args(argv)

    if args.mode == "check":
        code, lines = check_heartbeat(args.heartbeat, args.interval)
        for ln in lines:
            print(ln)
        return code

    args.package = Path(args.package)
    if not (args.package / "coordination").is_dir():
        print(f"refused: {args.package}/coordination is not a directory — "
              f"--package must be a run package root", file=sys.stderr)
        return 2
    if args.heartbeat is None:
        args.heartbeat = default_heartbeat(args.package, args.to)
    if args.transport == "file" and not args.out:
        args.out = str(Path(args.package) / "coordination" / f"nudge-{args.to}.log")

    lock_fh = None
    if not args.no_lock:
        Path(args.heartbeat).parent.mkdir(parents=True, exist_ok=True)
        lock_fh = open(str(args.heartbeat) + ".lock", "w", encoding="utf-8")
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print(f"refused: another nudge loop already holds {args.heartbeat}.lock — two loops "
                  f"on one heartbeat emit duplicate seqs and destroy the gap signal",
                  file=sys.stderr)
            return 3
        lock_fh.write(f"{os.getpid()}\n")
        lock_fh.flush()
    try:
        return run_loop(args)
    finally:
        if lock_fh is not None:
            lock_fh.close()


if __name__ == "__main__":
    sys.exit(main())
