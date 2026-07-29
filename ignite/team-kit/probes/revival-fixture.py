#!/usr/bin/env python3
"""revival-fixture.py — the ONE room + the ONE reader set the three Stage-4 acceptance probes
(`s4-10`, `s4-11`, `s4-12`) share. It is a SUBSTRATE, not a probe: it asserts nothing, scores
nothing, and has no exit contract of its own.

WHY IT EXISTS AT ALL (`role.md` §1 — build a second one only if you can say why the first cannot
serve, in writing). The first IS `probes/acceptance-room.py` (`AcceptanceRoom`, `s4-09`) and it is
used exactly as it ships: the private tmux server, the `HOME` redirect, the stub bin, the stub
provenance assertion, the real `team_monitor.py` capture, the teardown, `leak_scan`. What it cannot
serve is TWO measured refusals of the LAUNCH path, both already paid for by `s3-11`:

  1. `model: stub-model` is UNLAUNCHABLE, and the launchable value is PER HARNESS. `validate_seat`
     refuses a claude seat whose model is neither a known alias nor a full `claude-*` id, and an
     opencode seat whose model is not a `provider/model` slug — both measured, each with the
     relaunch failing on exactly that text — and `check_bindings` (G-51) compares the descriptor
     against `taskforce.csv` BEFORE any kill, so BOTH homes must carry the same launchable value.
  2. A revived seat's folder needs `memory.md`: `discover_workers` resolves the seat-folder form and
     `boot_prompt` tells a PERSISTENT seat to read it (G-14).

`s3-11` solved both with a ~20-line subclass INSIDE its own probe. Three probes would have carried
three copies of it, and a descriptor-shape change would then have had three homes (PRIN-11). So the
subclass and the /proc + ledger readers all three need live HERE, once. Nothing else moved: every
probe still owns its own assertions, its own red arms and its own exit code.

WAY-STATION (`role.md` §1.1, `decisions.md#d-watch-is-a-way-station`). This sits on the RETIRING
side because its SUBJECT does: it exercises `watch.py`'s stage-4 arms, and task 7.35 deletes that
file into the `goal-watcher-job` (CMP-21). It moves with `acceptance-room.py` when revival does —
cheap by construction: it imports ONE module by path and takes no other kit assumption.
Superseded by: whatever acceptance substrate the ignite-side revival component ships.

USE (the filename has a hyphen, so it loads by path — the pattern `team_monitor.py` uses for
`ctx_monitor`, and `probe-lifecycle-exec.py` for `acceptance-room.py`):

    import importlib.util
    F = "/home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/team-kit/probes/revival-fixture.py"
    spec = importlib.util.spec_from_file_location("revival_fixture", F)
    fx = importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)

    room = fx.RevivalRoom(seats=(...,))
    with room:
        room.open_seat("s410-int")
        ...

⚠ EVERY SEAT A CONSUMER DECLARES MUST CARRY `mode: interactive` EXPLICITLY unless it is
deliberately testing the mode gate. MEASURED 2026-07-29: ZERO of run-2's 52 `seat.md` files declare
`mode:`, and `s4-04`'s gate routes an undeclared seat into the UNDECIDABLE refusal — so a fixture
that forgets `mode:` is testing the refusal, never the fire. Every consumer's seat tuple therefore
declares it; a seat that deliberately omits it must say so in its own comment.

──────────────────── FOUR MEASURED TRAPS A CONSUMER MUST NOT WALK INTO ────────────────────────

Each one produced a GREEN that proved nothing, measured 2026-07-29 while this file was first run.
They are stated here because a consumer that has to discover them has already shipped the vacuous
check.

  1. **CAPTURE AFTER THE KILL, BEFORE THE FIRST TICK.** `kill_harness()` reads the pid off the
     EXISTING snapshot; it does not refresh it. `check_revival`'s candidate set is
     `snap["roster_absent"]` read off disk, so a tick taken against the pre-kill snapshot sees a
     healthy room and the debounce never starts. Measured: an arm that killed and ticked twice
     reached `1/2 consecutive non-stale ticks` and reported "revival did not fire". Use
     `tick_until_absent_stable`, which re-captures before EVERY tick — including the first.
  2. **A `messages.md` ARM IS VACUOUS WITHOUT `--notify`.** Without it `watch.py` PRINTS
     `would send: …` and sends nothing, so "zero `ask` rows appeared" is true no matter what the
     loop did. Any arm asserting on the message log MUST pass `notify_to=` so a message COULD have
     landed. That is the whole difference between a control and a decoration.
  3. **`harnesses_in(ancestry(pid))` ON A HARNESS PID IS ALWAYS NON-EMPTY** — the chain STARTS at
     `pid`, so the subject reports itself. Use `harnesses_above(pid)`. The no-agent arm asks whether
     an agent is ABOVE the new harness; asking whether the new harness is a harness answers a
     different question with the same shape, in the direction that hides the failure.
  4. **`$TMUX` BEATS `TMUX_TMPDIR`, TOTALLY AND SILENTLY.** MEASURED 2026-07-29 in a shell where
     `TMUX=/tmp/tmux-1000/default,737243,0` survived:
     `TMUX_TMPDIR=<room>/tt tmux display-message -p '#{socket_path}'` answered
     **`/tmp/tmux-1000/default`** — THE LIVE SERVER. When `$TMUX` is set, tmux takes the socket named
     inside it and IGNORES `TMUX_TMPDIR` entirely. So the private server is NOT "defence in depth"
     behind the `TMUX`/`TMUX_PANE` pop, as `acceptance-room.py`'s docstring reads: **the pop is what
     makes `TMUX_TMPDIR` work at all**, and a caller who sets `TMUX_TMPDIR` while `$TMUX` survives
     addresses the live room while believing it is isolated. `AcceptanceRoom.env()` pops both, and
     `assert_private_socket` below REFUSES when either survives — that refusal is the load-bearing
     guard, not a formality. **Never build a tmux environment by hand; call `room.env()`.**

──────────────────── AND ONE SPEC CLAIM THAT IS FALSE BY CONSTRUCTION ─────────────────────────

`stage-4-revival-spec.md:330-332` (carried into `s4-10` § no-agent proof) asks the new harness's
ppid ancestry to *"reach the watch process without passing through any harness pid"*. IT CANNOT,
and a probe that asserts it would fail on a CORRECT system. Measured: the revived harness's chain
is `claude → bash → tmux: server` and stops there, because a `revive` respawns the pane IN PLACE
(`tmux respawn-pane -k`), so the tmux SERVER is the parent — and the executor itself is detached
(`setsid` + `start_new_session=True`), which is the point of Stage 3. The causal link to the loop
is not a process edge; it is the marker's `caller` (pid, starttime), stamped by the loop before the
fork. `watch_tick_traced()` exists so a consumer can measure exactly that, and `harnesses_above()`
carries the negative half.
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD_PY = KIT / "coord.py"
WATCH_PY = KIT / "watch.py"
ROOM_PY = HERE / "acceptance-room.py"
EXEC_PROBE_PY = HERE / "probe-lifecycle-exec.py"

# See refusal 1 in the header. The stub ignores every flag, so a launchable value costs nothing.
#
# ⚠ PER HARNESS, AND THAT IS A MEASURED REFUSAL, NOT TIDINESS. `validate_seat` enforces a DIFFERENT
# model SHAPE per harness: a claude seat needs a known alias or a full `claude-*` id, and an opencode
# seat needs a `provider/model` SLUG. A single `haiku` for both got the opencode revival as far as
# `claim CLAIMED; fire FIRED` and then died inside the executor at step 5 — *"opencode model 'haiku'
# is not a provider/model slug … the seat is CLOSED AND NOT RELAUNCHED"* (measured 2026-07-29, s4-10
# row LG-11a). The mode gate had worked; the FIXTURE was wrong, and the arm read as a gate failure.
STUB_MODELS = {"claude": "haiku", "opencode": "deepseek/deepseek-v4-pro"}
STUB_MODEL = STUB_MODELS["claude"]       # kept for consumers that only open claude seats


def stub_model(harness):
    """The launchable model value for `harness`. Refuses rather than guessing a shape."""
    if harness not in STUB_MODELS:
        raise FixtureRefusal(
            f"no stub model shape is known for harness {harness!r} — `validate_seat` enforces a "
            f"per-harness shape and a wrong one fails INSIDE the detached executor, where it reads "
            f"as a gate failure. Add the shape to STUB_MODELS deliberately.")
    return STUB_MODELS[harness]


class FixtureRefusal(RuntimeError):
    """The fixture refusing to act. Loud by construction (R-8) — never a warning."""


def load_by_path(path, name):
    path = Path(path)
    if not path.exists():
        raise FixtureRefusal(f"cannot load {name}: {path} does not exist")
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_room_module():
    return load_by_path(ROOM_PY, "acceptance_room")


def load_exec_probe():
    """`probe-lifecycle-exec.py` as a module — for `run_caller`, Stage 3's SIGKILL test wrapper.

    `s4-11` § Out of scope: *"Do NOT re-implement Stage 3's SIGKILL test wrapper — a second wrapper
    is a second definition of 'the instant the marker appears' and the two will disagree."* The
    wrapper is `run_caller` there; importing it is how that bound is honoured. Its module body only
    pops four env names and binds constants — `main()` runs under `__main__` alone."""
    return load_by_path(EXEC_PROBE_PY, "probe_lifecycle_exec")


# ── the room ───────────────────────────────────────────────────────────────────────────────────

def make_room_class(ar):
    """`RevivalRoom` bound to an already-loaded `acceptance_room` module. Two overrides, each
    forced by a measured refusal of the launch path (header refusals 1 and 2) and NOTHING else."""

    class RevivalRoom(ar.AcceptanceRoom):
        def _write_descriptor(self, s):
            d = self.pkg / "seats" / s["seat"]
            d.mkdir(parents=True, exist_ok=True)
            fm = [f"seat: {s['seat']}",
                  "description: stage-4 acceptance seat (stub harness — no model, no cost)",
                  f"cwd: {d}",
                  f"harness: {s['harness']}",
                  f"model: {stub_model(s['harness'])}",
                  "effort: medium",
                  "agent_type: worker",
                  "ctx-refresh: 40"]
            if s.get("mode") is not None:
                fm.append(f"mode: {s['mode']}")
            (d / "seat.md").write_text("---\n" + "\n".join(fm) + "\n---\n\n"
                                       "Stub seat. No agent ever reads this; the executable on "
                                       "PATH is a `read -t` loop.\n", encoding="utf-8")
            (d / "memory.md").write_text(f"# memory — {s['seat']}\n\n", encoding="utf-8")

        def setup(self):
            super().setup()
            # `check_bindings` (G-51) compares the descriptor against this registry BEFORE any
            # kill, so the model must agree in BOTH homes or the relaunch refuses.
            rows = ["taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id"]
            for s in self.seats:
                rows.append(f"tf-acc,{s['seat']},,{s['harness']},"
                            f"{stub_model(s['harness'])},medium,40,acc")
            (self.pkg / "taskforce.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            return self

        # ---- ledger + roster readers, all reading THIS room's package off disk ----

        def marker(self, seat=None):
            p = self.pkg / "coordination" / "lifecycle-inflight.json"
            if not p.exists():
                return {}
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return {}
            if seat is None:
                return data
            e = data.get(seat)
            return e if isinstance(e, dict) else {}

        def awaiting(self, seat):
            p = self.pkg / "coordination" / "awaiting-close.json"
            if not p.exists():
                return None
            try:
                return json.loads(p.read_text(encoding="utf-8")).get(seat)
            except (ValueError, OSError):
                return None

        def roster_row(self, seat):
            text = (self.pkg / "coordination" / "workers.md").read_text(encoding="utf-8")
            for ln in reversed(text.splitlines()):
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if len(cells) >= 3 and cells[0] == seat:
                    return {"active": cells[1], "pane": cells[2]}
            return None

        def set_roster_active(self, seat, active):
            """Flip a roster row's `active` cell in place. Used to BUILD a fixture state (a
            hand-resumed seat) and, in one disclosed red arm, to remove a race cover."""
            wm = self.pkg / "coordination" / "workers.md"
            out, hit = [], False
            for ln in wm.read_text(encoding="utf-8").splitlines():
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if len(cells) >= 3 and cells[0] == seat:
                    cells[1] = "yes" if active else "no"
                    ln = "| " + " | ".join(cells) + " |"
                    hit = True
                out.append(ln)
            if not hit:
                raise FixtureRefusal(f"no roster row for {seat} to flip")
            wm.write_text("\n".join(out) + "\n", encoding="utf-8")

        def exec_logs(self, seat):
            return sorted((self.pkg / "coordination").glob(f"lifecycle-exec-{seat}-*.log"))

        def messages(self):
            return (self.pkg / "coordination" / "messages.md").read_text(encoding="utf-8")

        def message_rows(self):
            """[{n, from, to, type, ts}] parsed from the log's own header shape
            (`coord.append_message`: `## N | from: X | to: Y | type: T | ts`).

            ⚠ A `messages.md` ARM IS VACUOUS WITHOUT `--notify` (trap 2). Assert the delivery path
            was LIVE — at least one row of SOME type landed — before reading anything into the
            absence of a row of the type under test."""
            rows = []
            for ln in self.messages().splitlines():
                if not ln.startswith("## "):
                    continue
                d = {}
                for part in ln[3:].split(" | "):
                    if ": " in part:
                        k, v = part.split(": ", 1)
                        d[k.strip()] = v.strip()
                    elif part.strip().isdigit():
                        d["n"] = part.strip()
                rows.append(d)
            return rows

        def set_mode(self, seat, mode):
            """Rewrite ONE seat descriptor's `mode:` line in place, leaving everything else byte
            identical — LG-10's control is "the SAME fixture with mode: interactive", and a second
            seat would make it a different fixture. `None` DELETES the key (the UNDECIDABLE case)."""
            p = self.pkg / "seats" / seat / "seat.md"
            out, seen = [], False
            for ln in p.read_text(encoding="utf-8").splitlines():
                if ln.startswith("mode:"):
                    seen = True
                    if mode is None:
                        continue
                    ln = f"mode: {mode}"
                out.append(ln)
            if not seen and mode is not None:
                out.insert(out.index("---", 1), f"mode: {mode}")
            p.write_text("\n".join(out) + "\n", encoding="utf-8")
            self._seat(seat)["mode"] = mode
            return p

        def injections(self):
            p = self.pkg / "coordination" / "injections.log"
            return p.read_text(encoding="utf-8") if p.exists() else ""

        def sessions_rows(self, seat=None):
            p = self.pkg / "sessions.csv"
            if not p.exists():
                return []
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if len(lines) < 2:
                return []
            header = [c.strip() for c in lines[0].split(",")]
            rows = []
            for ln in lines[1:]:
                cells = [c.strip() for c in ln.split(",")]
                row = dict(zip(header, cells))
                if seat is None or row.get("seat") == seat:
                    rows.append(row)
            return rows

        def watch_state(self):
            p = self.pkg / "coordination" / "watch-state.json"
            if not p.exists():
                return {}
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return {}

        # ---- the snapshot, and the ONE sanctioned way to mutate it ----

        def mutate_snapshot(self, fn, why):
            """Apply `fn(snap)` to the REAL capture on disk and leave a `_mutated_by_probe` stamp.

            ⚠ THE ONLY MUTATION VEHICLE ANY CONSUMER MAY USE, and it is deliberate rather than
            convenient. `check_revival`'s candidate set IS `snap["roster_absent"]` verbatim — the
            code takes no other input for it — so mutating the DETECTOR's predicate and mutating
            this field are the same act, and this one needs no edit to a file under another
            worker's custody. The stamp is `room.age()`'s discipline: a mutated snapshot must never
            be mistakable for one the sensor produced. `snapshot_is_real` still holds afterwards,
            which is the point: the fields a forger would have to fake are untouched."""
            snap = self.snapshot()
            ok, reason = ar.AcceptanceRoom.snapshot_is_real(snap)
            if not ok:
                raise FixtureRefusal(f"refusing to mutate a snapshot that is not a real capture: "
                                     f"{reason}")
            fn(snap)
            stamps = snap.setdefault("_mutated_by_probe", [])
            stamps.append({"why": why, "at": time.time()})
            (self.pkg / "state.json").write_text(json.dumps(snap, indent=1), encoding="utf-8")
            return snap

        def inject_absent_row(self, seat, liveness="no-harness", why=""):
            """Put `seat` into `roster_absent` as the sensor would shape the row. `liveness` is the
            caller's, because WHICH liveness the mutant produces is the whole discrimination."""
            pane = (self._seat(seat).get("pane") or "")
            row = {"seat": seat, "agent_type": "worker", "agent_type_source": "descriptor",
                   "pane": pane, "roster_active": True, "liveness": liveness,
                   "reason": why or "injected by revival-fixture (probe mutation)"}

            def fn(snap):
                rows = snap.setdefault("roster_absent", [])
                rows[:] = [r for r in rows if r.get("seat") != seat] + [row]
            return self.mutate_snapshot(fn, f"inject roster_absent row for {seat} "
                                            f"(liveness={liveness}): {why}")

        def clear_absent(self, why="clear roster_absent"):
            return self.mutate_snapshot(lambda s: s.__setitem__("roster_absent", []), why)

        def mutate_seat_row(self, seat, why="", **fields):
            """Set `fields` on `seat`'s row in `snap["seats"]` — the sensor-observation half.

            The idle control needs a row the SENSOR would not produce on its own within a probe's
            wall clock (`last_activity_age_s > 3600`). Mutating the row is how that state is
            reached; mutating it is also the ONLY way, because the field is derived from real pane
            activity and no fixture can wait an hour. `check_revival` reads NEITHER
            `last_activity_age_s` NOR `prompt_pending` — that is the property under test — so this
            mutation is deliberately writing fields the arm asserts are ignored."""
            def fn(snap):
                for row in snap.get("seats") or []:
                    if row.get("seat") == seat:
                        row.update(fields)
            return self.mutate_snapshot(fn, why or f"set {sorted(fields)} on {seat}'s seat row")

        # ---- actuation ----

        def watch_tick(self, *extra, check=False, timeout=600, notify_to=None, env_extra=None):
            """One `watch.py` pass — NO `--loop` (declared with no default, so its absence is a
            single pass). `notify_to` turns the flags into REAL `note` sends through coord, which
            is the only way a note reaches `messages.md`."""
            argv = [sys.executable, str(WATCH_PY), "--package", str(self.pkg), *extra]
            if notify_to:
                argv += ["--notify", "--notify-to", notify_to, "--notify-fallback", notify_to]
            return self.sh(argv, check=check, timeout=timeout, env_extra=env_extra)

        def tick_until_absent_stable(self, seat, ticks=2, recapture=True, **kw):
            """`ticks` consecutive non-stale passes. Returns the list of completed runs.

            ⚠ RE-CAPTURES BEFORE **EVERY** TICK, THE FIRST ONE INCLUDED, and the first one is the
            one that was wrong. `kill_harness()` reads its pid off the EXISTING snapshot and does
            not refresh it, so a tick taken straight after a kill reads a snapshot in which the
            seat is still healthy: the candidate set is empty, the debounce never starts, and two
            ticks reach `1/2` instead of firing. Measured 2026-07-29 (trap 1 in the module
            docstring). Re-capturing also keeps the snapshot inside `budget.STALE_AFTER_S`, without
            which a stale tick FREEZES the debounce and the run silently never reaches CRASHED.

            ⚠ PASS `recapture=False` AFTER `mutate_snapshot` / `inject_absent_row` / `age` — a
            re-capture OVERWRITES `state.json` with what the sensor sees and destroys the mutation
            the arm exists to present. The two modes are exclusive by construction."""
            out = []
            for _ in range(ticks):
                if recapture:
                    self.capture()
                out.append(self.watch_tick(**kw))
            return out

        def watch_tick_traced(self, *extra, timeout=600, notify_to=None, env_extra=None):
            """`(result, pid)` — one `watch.py` pass through `Popen`, so the CALLER'S PID IS KNOWN.

            The no-agent proof needs the causal link between the loop and the successor, and that
            link is NOT a process edge (see the module docstring's false-by-construction note): it
            is the `caller` (pid, starttime) the loop stamps onto the marker before it forks. This
            is the only way a probe can hold the loop's pid to compare against."""
            argv = [sys.executable, str(WATCH_PY), "--package", str(self.pkg), *extra]
            if notify_to:
                argv += ["--notify", "--notify-to", notify_to, "--notify-fallback", notify_to]
            proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, env=self.env(env_extra))
            out, err = proc.communicate(timeout=timeout)
            return {"returncode": proc.returncode, "stdout": out, "stderr": err}, proc.pid

    return RevivalRoom


# ── /proc readings, taken by the probe itself ──────────────────────────────────────────────────

def starttime(pid):
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
        return stat[stat.rfind(")") + 1:].split()[19]
    except (OSError, ValueError, IndexError):
        return ""


def alive(pid):
    return bool(pid) and Path(f"/proc/{pid}").exists() and starttime(pid) != ""


def pane_harness(room, pane, harness="claude"):
    """(pid, starttime, argv) of the harness under `pane`, read from /proc by the PROBE — not
    echoed back from anything `coord.py` reports, so a stubbed reader inside coord could not
    manufacture a match."""
    root = int(room.tmux("list-panes", "-t", pane, "-F", "#{pane_pid}").stdout.strip())
    rows = subprocess.run(["ps", "-eo", "pid=,ppid=,comm=,args="],
                          capture_output=True, text=True, timeout=30).stdout.splitlines()
    for ln in rows:
        parts = ln.split(None, 3)
        if len(parts) < 4 or not parts[0].isdigit():
            continue
        if int(parts[1]) == root and parts[2] == harness:
            pid = int(parts[0])
            return pid, starttime(pid), parts[3]
    return None, "", ""


def pane_harness_count(room, pane, harness="claude"):
    """How many harness processes sit under `pane`. The double-launch detector: exactly ONE is the
    property every arm of `s4-11` is defending."""
    root = int(room.tmux("list-panes", "-t", pane, "-F", "#{pane_pid}").stdout.strip())
    rows = subprocess.run(["ps", "-eo", "pid=,ppid=,comm=,args="],
                          capture_output=True, text=True, timeout=30).stdout.splitlines()
    n = 0
    for ln in rows:
        parts = ln.split(None, 3)
        if len(parts) >= 4 and parts[0].isdigit() and int(parts[1]) == root \
                and parts[2] == harness:
            n += 1
    return n


HARNESS_COMMS = {"claude", "codex", "opencode", "kimi", "gemini", "aider", "goose", "amp"}


def ancestry(pid):
    """[{pid, comm, argv}] from `pid` up to init. The no-agent arm's first reading."""
    chain, cur, seen = [], int(pid), set()
    while cur and cur > 1 and cur not in seen:
        seen.add(cur)
        try:
            stat = Path(f"/proc/{cur}/stat").read_text(encoding="utf-8", errors="replace")
            comm = stat[stat.find("(") + 1:stat.rfind(")")]
            ppid = int(stat[stat.rfind(")") + 1:].split()[1])
            argv = Path(f"/proc/{cur}/cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", "replace").strip()
        except (OSError, ValueError, IndexError):
            break
        chain.append({"pid": cur, "comm": comm, "argv": argv})
        cur = ppid
    return chain


def harnesses_in(chain):
    """Harness processes anywhere in `chain`, THE SUBJECT INCLUDED.

    ⚠ DO NOT USE THIS FOR THE NO-AGENT ARM — `ancestry(pid)` starts AT `pid`, so asked about a
    revived HARNESS this returns that harness and the arm reads "an agent was in the path" on a
    correct system, or (worse, if the sense is flipped) always-green. Use `harnesses_above`."""
    return [c for c in chain if c["comm"] in HARNESS_COMMS]


def harnesses_above(pid):
    """Harness processes STRICTLY ABOVE `pid` in its ppid chain — the no-agent arm's reading.

    Empty means nothing that runs a model sits between `pid` and init. That is the answerable form
    of "no agent in the path": the spec's "the chain reaches the watch process" is false by
    construction (module docstring), but "no harness is an ancestor" is both true on a correct
    system and FALSIFIABLE — an agent-mediated relaunch puts its own harness in the chain, which is
    exactly the red arm."""
    return harnesses_in(ancestry(pid)[1:])


# ── marker readers ─────────────────────────────────────────────────────────────────────────────

def steps(mk):
    return [str(s) for s in (mk.get("steps-completed") or [])]


def step_starting(mk, prefix):
    return next((s for s in steps(mk) if s.startswith(prefix)), "")


def wait_terminal(room, seat, timeout=240, states=("done", "FAILED")):
    """Wait for `seat`'s marker to leave `in-flight`. Returns (entry, seconds)."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        mk = room.marker(seat)
        if mk and mk.get("state") in states:
            return mk, time.monotonic() - t0
        time.sleep(0.1)
    return room.marker(seat), time.monotonic() - t0


# ── isolation ──────────────────────────────────────────────────────────────────────────────────

def assert_private_socket(env, room):
    """REFUSE unless this environment can only reach THIS ROOM'S tmux server.

    `recover-room.py:12-19` measured what an unset target does: with `TMUX`/`TMUX_PANE` unset tmux
    resolves an EMPTY target to the MOST RECENT session — which answered `build-core-daemon-mvp`,
    the LIVE room carrying the owner's console and a running daemon."""
    tt = env.get("TMUX_TMPDIR", "")
    if not tt:
        raise FixtureRefusal(
            "REFUSING TO START: this environment carries NO TMUX_TMPDIR, so every tmux command it "
            "runs reaches the DEFAULT socket — the live room.")
    resolved = Path(tt).resolve()
    if not str(resolved).startswith(str(room.tmp.resolve()) + os.sep):
        raise FixtureRefusal(
            f"REFUSING TO START: TMUX_TMPDIR is {resolved}, which is NOT inside this room's own "
            f"tree {room.tmp}.")
    for v in ("TMUX", "TMUX_PANE"):
        if env.get(v):
            raise FixtureRefusal(
                f"REFUSING TO START: {v} survives in the environment, so an inherited pane is the "
                f"default target of anything that names none.")
    return True


# ── scoring harness, shared so all three probes report the same shape ──────────────────────────

class Score:
    """PASS/FAIL rows, red arms, notes, and the exit contract every probe in this folder uses:
    0 = every arm passed · 1 = a property is broken · 2 = the probe could not run (never a pass —
    a probe that cannot execute has proven nothing, and a red arm that failed to go red makes its
    green partner vacuous, which is the same refusal)."""

    def __init__(self, min_checks=1, min_reds=1):
        self.passed, self.failed, self.reds, self.notes = [], [], [], []
        self.min_checks, self.min_reds = min_checks, min_reds

    def check(self, name, ok, detail=""):
        (self.passed if ok else self.failed).append(name)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
        return bool(ok)

    def red(self, name, went_red, detail=""):
        """`went_red` True means the deliberately-broken variant WAS rejected."""
        self.reds.append((name, bool(went_red)))
        (self.passed if went_red else self.failed).append("RED ARM: " + name)
        print(f"  {'RED ' if went_red else 'FAIL'}  red arm: {name}"
              + (f" — {detail}" if detail else ""))
        return bool(went_red)

    def note(self, text):
        self.notes.append(text)
        print(f"  note  {text}")

    def verdict(self):
        """0 = every arm passed · 1 = a property is broken · 2 = the probe is INOPERATIVE.

        ⚠ THE RED-ARM VERDICT IS EVALUATED **BEFORE** THE FAILURE LIST, and the order is the whole
        point. `red()` records a red arm that stayed green in `failed` too, so a failure-first
        return would answer 1 ("a property is broken") for a case that is really 2 ("this probe
        proved nothing"): a red arm that will not go red makes its GREEN PARTNER vacuous, so the
        run has no evidence in either direction. First draft returned 1 here and the INOPERATIVE
        branch was unreachable."""
        total = len(self.passed) + len(self.failed)
        print(f"\nCHECKS {len(self.passed)}/{total}   "
              f"RED ARMS {sum(1 for _, r in self.reds if r)}/{len(self.reds)}")
        if self.notes:
            print("\nNOT PROVEN HERE / DISCLOSED (R-6 — as prominently as what was proven):")
            for n in self.notes:
                print(f"  · {n}")
        if len(self.reds) < self.min_reds or not all(r for _, r in self.reds):
            print(f"INOPERATIVE: {len(self.reds)} red arm(s) ran (this probe asserts at least "
                  f"{self.min_reds}) and {sum(1 for _, r in self.reds if not r)} did not go red — "
                  f"every green above is vacuous")
            if self.failed:
                print("FAILED: " + "; ".join(self.failed))
            return 2
        if self.failed:
            print("FAILED: " + "; ".join(self.failed))
            return 1
        if len(self.passed) < self.min_checks:
            print(f"INOPERATIVE: only {len(self.passed)} checks ran; this probe asserts at least "
                  f"{self.min_checks}")
            return 2
        return 0


def preflight(extra_bins=()):
    """Everything that must hold before a pane is opened. A non-empty return means exit 2."""
    import shutil
    problems = []
    for b in ("tmux", "setsid", *extra_bins):
        if not shutil.which(b):
            problems.append(f"no `{b}` on PATH")
    for p, why in ((COORD_PY, "coord.py"), (WATCH_PY, "watch.py"),
                   (ROOM_PY, "the acceptance substrate")):
        if not p.exists():
            problems.append(f"no {why} at {p}")
    if not Path("/bin/bash").exists():
        problems.append("no /bin/bash (the stub harness's interpreter)")
    return problems


def kit_digests():
    import hashlib
    return {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in (COORD_PY, WATCH_PY)}


# ── the unattended-run guard, and it is a MEASURED HARM, not caution ───────────────────────────

# MEASURED 2026-07-29, and it is why every consumer of this fixture requires an explicit `--go`:
#
#   `ignite/deploy/probe-suite-scheduled.py` is a systemd USER TIMER that fires HOURLY
#   (`DEFAULT_INTERVAL_SECONDS = 3600`) and runs `deploy/probe-suite.js` over EVERY directory named
#   `probes/` under `ignite/` — `team-kit/probes` included — with coverage DERIVED, never listed, so
#   a NEW `probe-*.py` file is picked up automatically and run UNATTENDED within the hour. The
#   per-probe timeout is `DEFAULT_TIMEOUT_MS = 180000` — THREE MINUTES.
#
#   A stage-3/stage-4 acceptance run cannot fit in three minutes and it is not a tuning problem: the
#   executor's own memory schedule is `LIFECYCLE_MEM_RETRIES x LIFECYCLE_MEM_RETRY_S` = 60 s per
#   blocked fire, Stage 3's settle is `LIFECYCLE_SETTLE_S` = 10 s per revival, and the ladder needs
#   nine blocked ticks to reach abandonment.
#
#   SO IT IS KILLED MID-RUN — and a SIGKILL does not run `finally`, so `AcceptanceRoom.teardown()`
#   NEVER EXECUTES: every fire leaks a tmpfs room AND a live private tmux server. Observed in the
#   20:00Z fire: `team-kit/probes/probe-lifecycle-exec.py TIMEOUT exit=- wall_ms=180010`, and a
#   leaked `/tmp/accroom-*` tree holding a live tmux server was found on disk. This box has an
#   uncontained memory-runaway failure mode (six global OOM kills, 2026-07-28/29) and `/tmp` is a
#   RAM-backed tmpfs, so an hourly leak is RAM the box does not have.
#
# The guard therefore REFUSES fast (well under a second) and LOUDLY, with exit 2 — "this probe could
# not run", which is this family's documented meaning and is RED, never a green that hides an absent
# acceptance. A human or the console passes `--go`.
UNATTENDED_REFUSAL = (
    "REFUSING TO RUN WITHOUT `--go`.\n"
    "This is a multi-minute acceptance run that opens tmux servers, forks detached executors and\n"
    "revives real processes. `ignite/deploy/probe-suite-scheduled.py` fires hourly over every\n"
    "`probes/` directory with a 180 s per-probe timeout, and a timeout SIGKILL skips the room's\n"
    "teardown — leaking a tmpfs room and a live tmux server on a box with an uncontained\n"
    "memory-runaway failure mode. Exiting 2 (`the probe could not run`) rather than starting\n"
    "something that will be killed halfway.\n"
    "  Run it deliberately:  python3 -u {path} --go\n"
    "  The scheduled-suite defect is filed in this file's guard block; the fix is an entry in\n"
    "  probe-suite-scheduled.py's EXCLUDED_DIRS (or a per-probe budget), which is NOT in this\n"
    "  folder's write set.")


def refuse_unattended(path):
    print(UNATTENDED_REFUSAL.format(path=path))
    return 2


if __name__ == "__main__":
    print(__doc__)
    print("This module is a SUBSTRATE and scores nothing. Run one of its consumers instead:")
    for n in ("probe-s410-revival-no-agent.py", "probe-s411-revival-renewal-mutex.py",
              "probe-s412-ram-floor-refusal.py"):
        print(f"  python3 {HERE / n}")
    sys.exit(2)
