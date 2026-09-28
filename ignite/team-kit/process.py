# ---- this module is IMPORTED, never `exec`d into `coord.py`'s namespace ----------------------
# It left `coord/` for the home `spec-component-map` §3 names, under the owner's 2026-08-25 ruling
# ("SPLIT_MODULES / coordinate split"). The move-only split loaded it by `exec` into ONE shared
# namespace; it is a real module now, so everything it did not define itself is named through the
# module that owns it.
#
# ⚠ QUALIFY — NEVER `from coord import NAME`. The selftest rebinds ~60 kit names at runtime
# (`global wake, atomic_write, ...` plus the `globals()[...]` sites), and a name copied into this
# module at import time is a SNAPSHOT: every later stub would be inert. Measured 2026-08-24 on the
# same bytes — 913 ok under a copying bind vs 1039 ok / PASS through the shared namespace. Reading
# `coord.NAME` at CALL time is what keeps a rebinding visible here.
#
# ⚠ The peer imports below are CIRCULAR by construction (`launch` <-> `attest`, `ready` <-> ...)
# and that is sound ONLY because every cross-module name is read inside a function body. A
# module-level read of a peer's attribute would break the import cycle — measure before adding one.

import os
import subprocess
import time
from pathlib import Path

import coord

# ---------- process truth: is the harness actually running, and did it actually die? ----------
# Two failures on one night proved the roster is not evidence about processes:
#   G-11 — a closer's multi-line prompt was typed into the pane's SHELL, which executed it line by
#          line: the `checkin` line ran for real (row -> ACTIVE) and the completion line printed a
#          report, while the harness never started. A row said ACTIVE; nothing was running.
#   G-10 — `tmux kill-pane` SIGHUPs the pane's process group; a harness blocked elsewhere survives
#          as a GHOST (449-488 MB each) that no roster row mentions and no sensor counts. Three were
#          hand-reaped by the leader; hand-reaping does not scale to an unattended night.
# Both are answered the same way: ask the process table, never the roster.

# 7.731: DERIVED, never re-typed. A harness's descriptor keyword IS the basename it launches as
# (`harness_command` runs CLAUDE_BIN/CODEX_BIN/OPENCODE_BIN, all defaulting to those exact names),
# so the launch surface and the process-matching surface are ONE list. Re-declaring it here let a
# 4th harness reach `validate_seat` while every live pane of it read as DEAD — the same second-copy
# drift 7.689 closed in edge-runner-job.py. The name stays: it reads right at the `ps` sites.
HARNESS_UP_TIMEOUT = 25.0   # cold claude start measured ~2-4s on this box; generous, bounded
HARNESS_UP_POLL = 0.5
# 7.567: the THIRD launch outcome gets its own exit code. `exit 0` from `launch` must mean a
# harness was POSITIVELY OBSERVED running; `exit 1` means a seat was POSITIVELY refused. The
# outcome in between — this host could not observe either way — used to return the empty error
# string and read as success. It now carries this prefix, and `cmd_launch` exits the code below.
# Codes already spoken for and NOT to be reused: 2 (argparse), 3 (EXIT_NO_SEAT in
# workflow_launcher.py, 7.548's certified zero-seat semantics), 5 (cmd at coord.py:10734).
EXIT_INDETERMINATE = 4
HARNESS_UP_UNVERIFIABLE = "harness liveness INDETERMINATE"
PID_EXIT_TIMEOUT = 6.0
# Set to skip the checkin-time harness check. The escape hatch exists because a positive-absence
# verdict rests on argv shape: a harness launched under a wrapper this code cannot recognize would
# be refused a checkin it deserves. Losing a seat to a false refusal is worse than G-11.
SKIP_HARNESS_CHECK = os.environ.get("COORD_SKIP_HARNESS_CHECK") == "1"


# ---------- lifecycle timeouts (the detached lifecycle executor) ----------
# Two TIMEOUTS, not policy numbers. `r-floor-single-source` (R-10) governs the RAM FLOOR and does
# not reach these; no floor literal belongs anywhere near them, and floor-lint.py refuses one
# outside budget.json.
#
# LIFECYCLE_SETTLE_S bounds the executor's wait for the FORKING CALLER to exit before it acts, then
# it proceeds REGARDLESS of the outcome: the executor never depends on the caller, which is the
# whole point of detaching it. By the time the fork happens the handoff is written, the transcript
# exported, the roster flipped and the sessions.csv row closed — nothing durable is left inside the
# caller's session to rescue — so the wait is courtesy, not correctness.
#
# LIFECYCLE_STALE_MIN is the age in MINUTES past which an in-flight lifecycle marker whose executor
# is NOT live reads as a FAILED renewal (the revival detector reads exactly that conjunction).
#
# ⚑ MEASURED AND FROZEN 2026-07-29 (task `s3-14`). s3-02's standing caveat on this number is
# DISCHARGED — the samples below are what discharged it. (The caveat's own wording is deliberately
# NOT re-quoted here: an acceptance control greps this block for that phrase, and a quotation of it
# reads to any matcher exactly like the caveat still standing.)
# SAMPLES — end-to-end renewal WALL CLOCK, printed by `probes/probe-lifecycle-exec.py` (s3-11),
# three probe runs on the ignite VPS, two scored renewals per run, EVERY sample recorded:
#     run 1: 10.1 s, 10.1 s   run 2: 10.1 s, 10.2 s   run 3: 10.1 s, 10.1 s
#   n = 6 · observed MAX 10.2 s · spread 0.1 s · mean 10.12 s. Each run exited 0 at 56/56 checks,
#   5/5 red arms. ⚠ THE SPREAD IS NOT ZERO, and it is recorded rather than rounded away: an
#   earlier cut of this block wrote "10.1 s x6, spread 0.0 s" from a single set of runs, and a
#   re-measurement immediately produced a 10.2 s. Six samples do not license a claim of no
#   variance — they license a claim about the ORDER of the duration, which is what is used below.
#
# ⚠ WHAT THE SAMPLES DO NOT COVER, stated WITH them so the number is never read as more than it is.
#   The probe runs a STUB `claude` that sleeps. 10.2 s therefore bounds the COORD.PY-SIDE SEQUENCE
#   and NOT a real model's boot. A real-harness sample cannot be taken without launching a paid
#   harness into a live room, so it was NOT taken and is NOT claimed: HARNESS_UP_TIMEOUT keeps
#   DERIVED headroom below rather than measured headroom.
#
# ⚑ THE MULTIPLIER IS NOT APPLIED TO THE SAMPLES, AND THAT IS THE POINT.
#   600 s / 10.2 s = 58.8x the measured max — absurd until you ask what this constant BOUNDS. It does
#   not bound the TYPICAL renewal; it bounds the LONGEST renewal this code may legitimately still
#   be inside, which is the sum of the waits it can spend (computed from these constants, not
#   recalled, 2026-07-29):
#       LIFECYCLE_SETTLE_S                            10 s
#     + MIRROR_REFRESH_TIMEOUT                       300 s
#     + HARNESS_UP_TIMEOUT                            25 s
#     + NATIVE_ID_WAIT                                 8 s
#     + PID_EXIT_TIMEOUT                               6 s
#     + LIFECYCLE_MEM_RETRIES x LIFECYCLE_MEM_RETRY_S  60 s
#     = 409 s = 6.82 min.
#   600 s is that bound x1.47, a margin of 3.18 min. THE MULTIPLIER IS 1.47x OVER THE WORST-CASE
#   WAIT SUM; the measurement's job is to report what that bound costs in the normal case, and it
#   costs a detection LAG of ~10 min on a renewal whose real work ended in ~10 s.
#   (Arithmetic computed 2026-07-29, not recalled: max(samples)=10.2 · 600/10.2=58.8 ·
#   600/409=1.467 · 600-409=191 s=3.18 min.)
#
# ⚑ WHY THE BOUND AND NOT THE MEASUREMENT SETS THE FLOOR — THE ERROR IS ASYMMETRIC. Too LONG only
#   DELAYS detection of a renewal that really did fail, and that is recoverable and visible:
#   `lifecycle_line` prints it and a leader runs `close-seat <seat> --renew`. Too SHORT reclassifies
#   a renewal that is STILL RUNNING as crashed, and Stage 4 then DOUBLE-LAUNCHES the seat — the one
#   outcome `lifecycle_stale` exists to make impossible. Any value under ~7 min buys faster
#   detection at that price. Refused, and the refusal is the reason the digits did not move.
#
# ⚑ MEASURED, AND IT DID NOT MOVE THE NUMBER EITHER: the dominant term MIRROR_REFRESH_TIMEOUT is a
#   TIMEOUT, not a duration. `refresh_mirrors_for` was RUN under the executor's scrubbed environment
#   (s3-14 item 2, re-measured 2026-07-29): TWO non-claude roots in one throwaway workspace,
#   8 managed mirror files rendered per root, 0.18 s TOTAL for both — and 0.0000 s for a claude
#   seat, which it skips by construction. Scale reference on a REAL workspace: this vault's own
#   286-managed-file mirror answers `install.py --mirror --check` (read-only) in 0.92 s.
#   ⚠ THE ELECTION IS PART OF THE MEASUREMENT: a workspace whose rbtv.json elects no mirrorable CLI
#   workers takes the SKIP branch and shells out to nothing, so a render timing taken there measures
#   the skip, not the installer. The 300 s stays as the BOUND because a hung installer can genuinely
#   reach it and the executor CONTINUES past a mirror failure rather than dying on it.
#
# It is deliberately SHORTER than CLOSING_MAX_MIN: a stuck closer merely narrows an inbox, while a
# stuck executor is a seat that is neither alive nor closed. That ordering is the load-bearing part
# and holds whatever the number becomes.
LIFECYCLE_SETTLE_S = 10
LIFECYCLE_STALE_MIN = 10   # FROZEN on measurement (s3-14): n=6, max 10.2 s; 1.47x the 409 s bound


# ---------- memory pre-flight (leader ruling, 2026-07-27 msg #128) ----------
# A claude seat's steady RSS is 419-549 MB but its PEAK is ~1.4 GB: boot and compaction spike ~3x
# steady state (systemd scope accounting, "1.4G memory peak"). Every launch gate tonight sized seats
# by what `ps` showed and understated the requirement threefold; the kernel answered by SIGKILLing a
# bystander — the watcher, twice, its roster row still reading ACTIVE. So this gate is not a flat
# floor over steady state: it holds a SPIKE reserve, because the spike is the risk.
# ⚑ THE NUMBER BELOW IS UNVALIDATED AND MACHINE-SPECIFIC. It is ONE systemd cgroup peak from one
# claude seat on one box, doubled — and a cgroup peak INCLUDES reclaimable page cache, so it
# counts as *required* memory the kernel would hand back under pressure. The causal OOM theory
# behind it was RETRACTED the same night it was taken (campaign issue S-8(a), owner-raised).
# It MUST NEVER travel to another machine as a constant: re-derive per box from a working-set or
# PSI-pressure metric over SEVERAL samples. Overriding it with a single fresh reading would
# repeat exactly the error that produced it. Until that measurement campaign runs, the value
# stays put (owner ruling) and is merely made settable per machine, which is what the env var
# below is for — it is the per-machine seam, not a licence to guess a better number.
# The GATE ITSELF is not in question and was ratified: seat RSS understates peak ~3x, three
# seats died `exit 137`, and the watcher was SIGKILLed twice as a BYSTANDER.
SEAT_SPIKE_MB = int(os.environ.get("COORD_SEAT_SPIKE_MB") or 1400)   # per-box override — a MEASUREMENT
# ⚠ THE SOURCE IS CAPTURED AT THE SAME INSTANT AS THE VALUE, AND THAT IS NOT PEDANTRY. The value is
# read ONCE, at import; a report that re-asked the environment at CALL time could say
# "COORD_SEAT_SPIKE_MB" while printing the built-in 1400, because a var set after import never
# reaches SEAT_SPIKE_MB. A provenance label that can disagree with the number it labels is worse
# than no label — it is a confident wrong answer at the moment someone is auditing the gate.
SEAT_SPIKE_SOURCE = ("COORD_SEAT_SPIKE_MB" if os.environ.get("COORD_SEAT_SPIKE_MB")
                     else "built-in default")

# ⚠⚠ THE FLOOR IS POLICY. IT IS ITS OWN CONSTANT AND TAKES NO ENV OVERRIDE.
# Owner ruling `r-mem-floor-2000` (2026-07-28), shape ruled by the leader (#1210 pt 3, #1269 pt 2).
#
# It used to read `SEAT_SPIKE_MB * SPIKE_RESERVE`, and that derivation is exactly why 2000 could not
# be expressed: 2000 is not 1400 x 2. Reaching it through the factors would have moved SEAT_SPIKE_MB
# — a MEASUREMENT held put by a standing owner ruling (see the block above) — in order to encode a
# POLICY number. Measurement and policy are different things and the code now says so.
#
# ⚠ AND NO `COORD_*` OVERRIDE HERE, DELIBERATELY: an env override on the floor would let an
# environment silently overrule an owner ruling with NO FILE ANYWHERE TO GREP — for the very number
# `budget.json` was just made the normative home of. The per-machine seam belongs on the spike,
# which is measured per box; the floor is decided once, by the owner.
# (`SPIKE_RESERVE` and `COORD_SPIKE_RESERVE` are deleted with this change: their only uses were
# building this product and printing it in the refusal below, and the env var was set nowhere in
# the repo. The reserve is now DERIVED FROM THE FLOOR, which is the direction that stays honest.)
#
# ⚠⚠ AND THE CONSTANT ITSELF IS NOW GONE — task 7.82, owner ruling `r-floor-single-source`:
#
#     A POLICY NUMBER MUST NEVER BE TRANSPORTED BY ARGV. argv is a COPY; a file is a REFERENCE.
#
# A module constant is the same class of copy as an argv literal: it is a number this file decided
# to believe. The floor is READ, per launch, from the run package's `budget.json` via
# `budget.read_floor()` — see `launch_gates()`. `memory_gate()` therefore takes `floor_mb` as a
# REQUIRED argument with NO DEFAULT: a default here would be the constant coming back under
# another name, and every caller must have resolved a floor before it may ask about one.


def available_mb():
    """MemAvailable in MiB, 0 when /proc/meminfo is unreadable (never gate on 'cannot tell')."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return 0
    return 0


def memory_gate(n_seats, avail_mb, floor_mb):
    """Pure: '' when it is safe to spawn `n_seats`, else the refusal reason. avail_mb == 0 means
    unmeasurable and PASSES — a broken sensor must not be able to stop a run."""
    if not avail_mb:
        return ""
    need = floor_mb + max(0, n_seats - 1) * SEAT_SPIKE_MB
    if avail_mb >= need:
        return ""
    # ⚠ THE RESERVE THIS MESSAGE CLAIMS IS DERIVED FROM THE FLOOR ACTUALLY IN FORCE — `floor_mb`,
    # the argument, not the module constant and not a separate reserve knob. The old text printed
    # `SPIKE_RESERVE`, a number that BUILT the floor; once floor and spike stopped being multiples
    # that would have printed "2 spikes of reserve" while holding 1.43, teaching a false
    # measurement at the exact moment an operator is blocked and reading it. A caller passing its
    # own `floor_mb` now gets a message about ITS floor.
    reserve = (floor_mb / SEAT_SPIKE_MB) if SEAT_SPIKE_MB else 0
    return (f"{avail_mb} MB available, {need} MB needed to spawn {n_seats} seat(s). A claude seat "
            f"peaks at ~{SEAT_SPIKE_MB} MB on boot and on every compaction — steady RSS is a third "
            f"of that — and this gate holds {reserve:.2f} spikes of reserve so a spiking seat "
            f"cannot make the kernel SIGKILL a bystander (how the watcher died twice on "
            f"2026-07-27). Close a seat first, or override with --force-memory and say so on "
            f"the log.")


# `gate_forced`/`GATE_FLAGS`/`cmd_gates` (the flag->gate binding map + the `coordinate gates`
# verb) were deleted [T2-R10, D24, F-simplicity-7]: they existed solely to stop `--force` from
# ever re-acquiring the ROLE gate's old override alongside the MEMORY gate's, and the role gate
# they guarded against is itself gone. `--force-memory` is the memory floor's only override now,
# read directly (see `launch_gates` below) — there is no second flag left for it to be confused
# with. runtime/jobs/recover-room.py no longer asserts a split at runtime for the same reason.


def ps_snapshot():
    """[(pid, ppid, argv-string)] for every process on the box, [] when ps is unavailable."""
    try:
        r = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True)
    except OSError:
        return []
    if r.returncode != 0:
        return []
    rows = []
    for line in r.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        rows.append((int(parts[0]), int(parts[1]), parts[2]))
    return rows


def descendant_pids(snapshot, root_pid):
    """Every pid at or below `root_pid` in `snapshot`. Pure — no I/O, so selftest exercises it."""
    if not root_pid:
        return []
    children = {}
    for pid, ppid, _ in snapshot:
        children.setdefault(ppid, []).append(pid)
    out, stack = [], [root_pid]
    while stack:
        pid = stack.pop()
        out.append(pid)
        stack.extend(children.get(pid, []))
    return out


def is_harness_argv(argv):
    """True when this command line starts a coordination harness. Pure. Matches the executable's
    basename and, for the node/bun-wrapped forms, any argv token that IS a harness path."""
    tokens = argv.split()
    if not tokens:
        return False
    if os.path.basename(tokens[0]) in coord.HARNESS_PROCS:
        return True
    return any(os.path.basename(t.split("=")[-1]) in coord.HARNESS_PROCS for t in tokens[1:4])


def harness_pids(snapshot, root_pid):
    """Pids of harness processes running at or below `root_pid`. Pure."""
    want = set(descendant_pids(snapshot, root_pid))
    return [pid for pid, _, argv in snapshot if pid in want and is_harness_argv(argv)]


def pane_harness_pids(pane):
    """(pids, verifiable) for the harness processes under `pane`. `verifiable` is False when the
    process table or the pane's pid could not be read at all — 'cannot tell' is NOT 'nothing is
    running', and every caller must treat the two differently (fail-safe)."""
    if not pane:
        return [], False
    root = coord.tmux_pane_pid(pane)
    if not root:
        return [], False
    snap = ps_snapshot()
    if not snap:
        return [], False
    return harness_pids(snap, root), True


def pane_harness_idents(pane):
    """[(pid, starttime)] for the harness processes under `pane` — the identity form of
    pane_harness_pids, and what every teardown captures before it kills anything."""
    if not pane:
        return []
    root = coord.tmux_pane_pid(pane)
    if not root:
        return []
    return harness_idents(ps_snapshot(), root)


def proc_stat(pid):
    """(state, starttime) from /proc/<pid>/stat — fields 3 and 22 — or ("", "") when unreadable.
    Parsed by splitting after the LAST ')': the comm field can itself contain spaces and
    parentheses, so a naive whitespace split mis-indexes every later field. Same derivation the
    ignite daemon uses (carrier.js setsidStatus, "pidStarttime guard against PID reuse")."""
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", ""
    cut = raw.rfind(")")
    if cut == -1:
        return "", ""
    rest = raw[cut + 1:].split()
    # rest[0] is field 3 (state), so field 22 sits at index 19.
    return rest[0], (rest[19] if len(rest) > 19 else "")


def proc_starttime(pid):
    """Field 22 of /proc/<pid>/stat, '' when unreadable — the identity half a pid cannot supply."""
    return proc_stat(pid)[1]


def process_identity(pid):
    """(pid, starttime), or None when the pid is gone. A pid ALONE is not an identity: the kernel
    recycles pids, and a teardown is exactly when new processes start, so a remembered pid can name
    a stranger seconds later — which is how a dead seat's reaper can SIGKILL a live one.

    Pane ancestry is NOT a substitute (leader, #138): G-12's in-place respawn puts the replacement
    under the SAME pane, so an ancestry test would confirm the very process it must protect.
    starttime is the half a respawn cannot reproduce."""
    st = proc_starttime(pid)
    return (pid, st) if st else None


def harness_idents(snapshot, root_pid):
    """[(pid, starttime)] for the harness processes under `root_pid` — identity, not bare pids."""
    return [i for i in (process_identity(p) for p in harness_pids(snapshot, root_pid)) if i]


def harness_name(snapshot, pid):
    """The harness basename a matched pid is running, read off its own argv. Falls back to
    'claude' only if the pid has vanished between the snapshot and this read — the caller already
    knows SOME harness matched; this just names which one for the report line."""
    argv = next((a for p, _, a in snapshot if p == pid), "")
    tokens = argv.split()
    return os.path.basename(tokens[0]) if tokens else "claude"


def unaccounted_panes(exclude_pane=None, resolver=None):
    """[{"pane", "harness", "cwd"}] for every LIVE tmux pane, right now, that a live harness
    process occupies and whose cwd resolves to NO seat.md anywhere — N1's predicate
    (`d-n1-oneshot-sweep`), read fresh at the capacity gate's own decision moment.

    ONE-SHOT, BY CONSTRUCTION: one `ps_snapshot()`, one round of `tmux` queries, one classification
    pass, then the return — nothing here is written to disk, cached, or scheduled, and no state
    from this call reaches the next one. Restoring a standing pane sensor is barred twice over
    (T4-R8's team-monitor deletion; `d-ask9-keep-the-three-protections`); this closes N1's gap
    WITHOUT one by never outliving the function call that made it.

    `exclude_pane` MUST be the CALLING pane (`coord.detect_pane()`) — the session asking the
    capacity question is routinely a live harness pane whose own cwd resolves to nothing (the plan
    folder, the vault root: `budget.py`'s own documented ambiguity, "an owner session and a leak
    are OBSERVATIONALLY IDENTICAL"), and excluding it also removes this very call's OWN `ps`/`tmux`
    subprocesses for free — they are descendants of the excluded pane's root, never of any other
    live pane. Pre-filtering here (rather than handing every harness pane to `census()` and letting
    it sort unaccounted from cross_goal) is what keeps a DECLARED seat's own pane from being
    counted twice: a declared seat's cwd always resolves (it IS a seat folder), so it never reaches
    this function's return at all — `census()` remains the one place that owns the classification,
    this only owns not asking it about panes that would obviously answer "accounted".
    """
    resolver = resolver or coord.budget_mod.resolve_descriptor
    panes = coord.live_panes()
    if exclude_pane:
        panes = panes - {exclude_pane}
    if not panes:
        return []
    snap = ps_snapshot()
    if not snap:
        return []
    found = []
    for pane in panes:
        pid = coord.tmux_pane_pid(pane)
        if not pid:
            continue
        hpids = harness_pids(snap, pid)
        if not hpids:
            continue
        cwd = coord.pane_cwd(pane)
        if resolver(cwd):
            continue  # a descriptor exists somewhere — this pane is accounted, N1 is not about it
        found.append({"pane": pane, "harness": harness_name(snap, hpids[0]), "cwd": cwd})
    return found


def signal_pid(pid, sig):
    """Send `sig` to ONE pid. (ok, err). Isolated as a module-level function for exactly one
    reason: the self-test rebinds it. A suite that really signalled processes would be a suite
    nobody could run on a live box, and `terminate-pid`'s whole subject is WHICH pid it will
    signal — so the decision must be exercisable without the signal ever leaving the process."""
    try:
        os.kill(pid, sig)
        return True, ""
    except OSError as err:
        return False, str(err)


def seat_radius_pids(args):
    """({pid: (seat, pane)}, verifiable) — every pid at or below the pane of every CURRENT roster
    row of this run. The SEAT RADIUS, derived from the roster and the live process table, never
    from a kit-side name list.

    ⚠ `verifiable` is the whole fail-safe, and it is NOT the same value as an empty map. `ps` may
    be unavailable and tmux may be unreachable, and in both worlds this returns {} — which, read as
    "no pid belongs to a seat", would turn `terminate-pid` into an unguarded kill of any pid on the
    box at exactly the moment it can see least. Cannot-tell is never nothing (`pane_harness_pids`
    carries the same split for the same reason). The caller REFUSES on `verifiable` False.

    The radius is the whole pane subtree, not just its harness processes: a seat's pane holds its
    shell and whatever that shell started, and `terminate-pid` is non-seat-radius BY CONTRACT
    (7.153 criterion 3 arm C) — a contract about the SEAT, not about the harness binary."""
    snap = ps_snapshot()
    if not snap:
        return {}, False
    _, _, rows = coord.load_workers(coord.base_dir(args))
    current = [coord.current_row(rows, a) for a in dict.fromkeys(r["agent"] for r in rows)]
    panes = [(r["agent"], r["pane"]) for r in current if r and r.get("pane")]
    out, resolved = {}, 0
    for agent, pane in panes:
        root = coord.tmux_pane_pid(pane)
        if not root:
            continue
        resolved += 1
        for pid in descendant_pids(snap, root):
            out.setdefault(pid, (agent, pane))
    # The roster claims panes and tmux resolved NONE of them: that is a tmux the process world
    # cannot be read through, not a run whose seats hold no processes. Fail safe, same rule.
    if panes and resolved == 0:
        return {}, False
    return out, True


def ident_is_live_harness(ident):
    """True when (pid, starttime) still names the SAME live process and it is still a harness. The
    single predicate every kill in this file passes through. Pure w.r.t. its argument: it re-derives
    both halves from /proc at call time and trusts nothing remembered."""
    pid, starttime = ident
    state, live_start = proc_stat(pid)
    if not starttime or live_start != starttime or state == "Z":
        return False
    try:
        argv = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace")
    except OSError:
        return False
    return is_harness_argv(argv)


def ident_is_live_process(ident):
    """True when (pid, starttime) still names THE SAME live process — ANY process, harness or not.

    NOT a substitute for `ident_is_live_harness`, and never interchangeable with it: that predicate
    additionally requires `is_harness_argv`, which matches only the claude/codex/opencode basenames
    in HARNESS_PROCS. The lifecycle executor and its forking caller are PYTHON processes, so
    `ident_is_live_harness` reports every live one of them DEAD — silently turning the
    caller-settle wait (LIFECYCLE_SETTLE_S) into a no-op and the staleness test
    (LIFECYCLE_STALE_MIN) into "always stale". A wait that cannot wait and a test that cannot say
    "not yet" both LOOK like working code; that is why the two predicates are separate functions
    with separate names rather than one with a flag.

    Pure w.r.t. its argument, exactly as `ident_is_live_harness` is: it re-derives BOTH halves from
    /proc at call time and trusts nothing remembered. The starttime half is what makes it a guard
    at all — a pid alone is recyclable, and a teardown is exactly when new processes start. Pane
    ancestry is no substitute for it either; `process_identity` carries the reason: "G-12's
    in-place respawn puts the replacement under the SAME pane, so an ancestry test would confirm
    the very process it must protect."

    A zombie is NOT live: it has exited and its status is merely unreaped, which is precisely the
    outcome both callers are waiting for. Any read failure is False as well — an unreadable /proc
    entry is not evidence of liveness, and the fail-safe direction here is "assume it is gone",
    because the alternative is an executor that waits forever on a process it cannot see."""
    pid, starttime = ident
    state, live_start = proc_stat(pid)
    return bool(starttime) and live_start == starttime and state != "Z"


def idents_alive(idents):
    """The subset of `idents` that still name their original live harness process."""
    return [i for i in idents if ident_is_live_harness(i)]


def reaper_script(idents, delay):
    """The detached reaper's shell text. It re-derives (pid, starttime) from /proc at the moment of
    the kill and fires ONLY on an exact match of both halves — the guard that was missing when this
    reaper was gated on "the pid is A harness" rather than "the pid is THE harness" (owner
    directive 2026-07-27, msg #137). Pure, so the decision it encodes is checkable without arming
    anything. field 22 is read after the last ')', never by a naive whitespace split.

    A zombie needs no special case: its /proc/<pid>/cmdline is EMPTY, so the harness test below
    cannot match and no signal is sent."""
    specs = " ".join(f"{pid}:{st}" for pid, st in idents)
    return (
        f"sleep {delay}; for spec in {specs}; do "
        f"p=${{spec%%:*}}; want=${{spec#*:}}; "
        f"st=$(sed 's/^.*) //' /proc/$p/stat 2>/dev/null | awk '{{print $20}}'); "
        f'if [ -n "$st" ] && [ "$st" = "$want" ]; then '
        f"tr '\\0' ' ' < /proc/$p/cmdline 2>/dev/null "
        f"| grep -qE '(^| |/)(claude|codex|opencode)( |$)' && kill -9 $p; fi; done"
    )


def wait_harness_up(pane, timeout=HARNESS_UP_TIMEOUT):
    """Poll until a harness process is running under `pane`. Returns (pids, err): err is '' ONLY
    when a harness was positively observed. Positive absence returns the G-11 refusal; liveness
    this host cannot observe returns an err prefixed `HARNESS_UP_UNVERIFIABLE` (7.567), which the
    caller classifies apart from a refusal — 'cannot tell' is neither success nor failure."""
    deadline = time.time() + timeout
    while True:
        pids, verifiable = pane_harness_pids(pane)
        if pids:
            return pids, ""
        # "Cannot tell" does not improve with waiting (no pane pid, no readable process table) —
        # return at once rather than burning the whole timeout on an unanswerable question. The
        # reason is re-derived here (one extra tmux call, failure path only) because
        # `pane_harness_pids` collapses both causes into a single False, and an operator holding
        # an indeterminate exit code needs to know WHICH of the two the box hit.
        if not verifiable:
            if not pane:
                why = "no pane was given"
            elif not coord.tmux_pane_pid(pane):
                why = f"tmux could not report a pid for pane {pane}"
            else:
                why = "the process table could not be read (`ps -eo pid=,ppid=,args=` failed)"
            return [], (f"{HARNESS_UP_UNVERIFIABLE}: {why}, so neither the presence NOR the "
                        f"absence of a {'/'.join(coord.HARNESS_PROCS)} process could be observed. The "
                        f"start line WAS submitted; check by hand: tmux capture-pane -p -t {pane}")
        if time.time() >= deadline:
            break
        time.sleep(HARNESS_UP_POLL)
    return [], (f"no {'/'.join(coord.HARNESS_PROCS)} process is running in {pane} after "
                f"{timeout:.0f}s — the start line was submitted to the pane but only its shell "
                f"is there (G-11). Capture the pane to see what the shell did with it: "
                f"tmux capture-pane -p -t {pane}")


def pids_alive(pids):
    """The subset of `pids` still alive, EXCLUDING zombies.

    A zombie has exited: it holds no memory and runs no code, and only lingers because its parent
    has not reaped it. `os.kill(pid, 0)` succeeds for one, so a bare signal-0 probe reports a
    successfully killed process as a surviving ghost — caught by the live reaper proof, where a
    process the reaper HAD killed was still reported alive."""
    alive = []
    for pid in pids:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            pass
        if proc_stat(pid)[0] == "Z":
            continue
        alive.append(pid)
    return alive


def verify_pids_gone(idents, timeout=PID_EXIT_TIMEOUT):
    """Wait for the harness processes named by `idents` — (pid, starttime) pairs — to exit,
    escalating SIGTERM then SIGKILL on a straggler (G-10: kill-pane SIGHUPs the process group and a
    blocked harness survives it as a ghost nobody counts). Returns (survivors, note); survivors is
    empty on success and note says what it took.

    EVERY signal passes ident_is_live_harness first, so a recycled pid can never be hit: identity is
    re-proved from /proc at the instant of signalling, never remembered from before the kill."""
    if not idents:
        return [], ""
    deadline = time.time() + timeout
    escalated = []
    while True:
        alive = idents_alive(idents)
        if not alive:
            break
        if time.time() >= deadline:
            for sig in (15, 9):
                for ident in idents_alive(idents):
                    try:
                        os.kill(ident[0], sig)
                        escalated.append((ident[0], sig))
                    except OSError:
                        pass
                time.sleep(0.5)
            alive = idents_alive(idents)
            break
        time.sleep(0.3)
    if alive:
        return alive, (f"pid(s) {', '.join(str(p) for p, _ in alive)} SURVIVED kill-pane, SIGTERM "
                       f"and SIGKILL — a ghost holding memory; reap it by hand and say so on the log")
    if escalated:
        return [], (f"kill-pane left the harness alive; reaped by signal "
                    f"({', '.join(f'{p}:SIG{s}' for p, s in escalated)})")
    return [], ""


def arm_pid_reaper(idents, delay=4):
    """Detach a one-shot reaper for the harness processes named by `idents` — (pid, starttime)
    pairs — `delay` seconds from now. `depart` kills its OWN pane, so this process dies with it and
    can verify nothing afterwards (G-10); the reaper outlives both.

    It fires only on an exact (pid, starttime) match re-derived from /proc at kill time. The first
    version guarded on "this pid is A harness", which is not identity: a relaunch landing on a
    recycled pid would be SIGKILLed by the dead seat's reaper (owner directive, msg #137; the ignite
    daemon guards the same hazard the same way — spawn.js pid_starttime)."""
    idents = [i for i in idents if i and i[1]]
    if not idents:
        return
    try:
        subprocess.Popen(["setsid", "bash", "-c", reaper_script(idents, delay)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError:
        pass


