import os
import re
import subprocess
import sys

# ---------- identity (T1) ----------

def pane_agent(base, pane):
    """The agent this tmux pane is REGISTERED to in the roster (latest active row wins), or ''.
    This is the only identity claim the tool can verify, so it is what a claim is checked
    against."""
    if not pane:
        return ""
    _, _, rows = load_workers(base)
    hit = [r for r in rows if r["pane"] == pane and r["active"] == "yes"]
    return hit[-1]["agent"] if hit else ""


# ---- The DAEMON-EXEC identity lane (F16 / store row 7.360; run issue G-planner-0804-1501 arm 1).
#
# THE DEFECT THIS CLOSES. This tool and the daemon disagreed about what an identity IS.
# `resolve_agent` accepted `--as NAME`, and with no tmux pane the contradiction check below cannot
# fire — so a claim simply STOOD. The daemon's own gate (`server/seat-identity/identity.js`, task
# 7.11 §4b) was built to refuse exactly that: it consults kernel measurables and says in its own
# words that "there is no env var, no `--as`, no flag, and no config that can substitute for or
# override the match", because an asserted `COORD_AGENT` once outranked verified pane resolution
# and two agents ran under one roster name (G-111). Measured consequence: a daemon-fired
# `coord.py … launch` could pass the role gate ONLY by writing `--as leader` into
# `envelope/spawn-profiles.yaml` — an assertion dressed as configuration.
#
# So this lane gives the daemon path an identity it does not have to CLAIM. It follows identity.js
# link for link: the caller supplies MEASURABLES, never a name, and every link is something the
# caller cannot write.
#
#   1. `/proc/self/cgroup`  -> the transient unit this process is inside. Kernel-maintained; no env
#                              var, flag or config sets it.
#   2. `rbtv-ignite.service` -> must be ACTIVE, and its MainPID's `/proc/<pid>/environ` carries the
#                              daemon's own data root.
#   3. `heart.db` `jobs_log` -> a LIVE turn row for that unit_name. THIS is the discriminating step,
#                              and it is why link 1 alone is not enough: any local process can run
#                              `systemd-run --user --unit=rbtv-worker-<uuid>` and wear the name. The
#                              unit name is a NAMING convention, not a credential — the same thing
#                              identity.js says about a seat-folder path.
#
# FAILS CLOSED EVERYWHERE. Every unreadable, absent or ambiguous input returns '' (no identity),
# never a name — because the point of a resolver is to be the thing that says "nobody".
#
# AND IT IS PLACED LAST IN `resolve_agent` ON PURPOSE. What stood at that position was
# `sys.exit(2)`, so this lane can only ADD resolution where there was none: it never displaces a
# pane's registered roster row, and it does not touch `--as` precedence (that is arm 2's bound, not
# this one's). Zero behaviour change for every caller that already resolved.
DAEMON_IDENTITY = "ignite-daemon"
IGNITE_UNIT = "rbtv-ignite.service"
DAEMON_DATA_ROOT_DEFAULT = "/var/lib/rbtv-ignite"   # envelope/spawn-profiles.yaml's seeded data_root
# `spawn/carrier.js` mints `rbtv-worker-<sessionId>`; systemd renders that as a .service unit and
# the cgroup line carries it as the path LEAF. Anchored on the separator and on `.service` so a
# substring appearing anywhere else in the line cannot smuggle a unit name in.
DAEMON_WORKER_UNIT_RE = re.compile(r"/(rbtv-worker-[0-9A-Za-z][0-9A-Za-z-]{7,63})\.service\b")
# The TURN statuses that mean "this exec is still alive" (heart schema.sql § jobs_log). A finished
# turn's unit name must not resolve: the exec it named is gone.
DAEMON_LIVE_TURN_STATUSES = ("launching", "running")


def daemon_worker_unit(cgroup_text):
    """The daemon-spawned transient unit this cgroup text names, or ''. Pure: measurable in, name
    out — it holds no policy and reads nothing ambient."""
    m = DAEMON_WORKER_UNIT_RE.search(cgroup_text or "")
    return m.group(1) if m else ""


def daemon_heart_db():
    """The LIVE daemon's own `heart.db` path, read off the running unit — or '' when unanswerable.

    ⚠ `--user` IS LOAD-BEARING AND IS NOT A STYLE CHOICE (watch.py `daemon_identity()`'s measured
    lesson). The unit is user-scoped; the SYSTEM bus answers `LoadState=not-found` / `MainPID=0` /
    exit 0, byte-identical to a unit that genuinely does not exist. coord cannot import watch
    (watch imports coord), so this asks for the two properties it needs and treats every answer
    that is not a determinate `active` as NO IDENTITY — which is the safe direction here, unlike
    watch's, where the same ambiguity had to be reported rather than resolved."""
    try:
        out = subprocess.run(["systemctl", "--user", "show", IGNITE_UNIT,
                              "--property=ActiveState,MainPID"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    if out.returncode != 0:
        return ""
    kv = {}
    for line in (out.stdout or "").splitlines():
        k, _, v = line.partition("=")
        kv[k.strip()] = v.strip()
    if kv.get("ActiveState") != "active":
        return ""
    pid = kv.get("MainPID", "")
    if not pid.isdigit() or int(pid) <= 0:
        return ""
    # The RUNNING environment, not the unit's declared `Environment=`: a deploy may carry the data
    # root in an `EnvironmentFile=`, which `show --property=Environment` does not render at all.
    root = ""
    try:
        with open(f"/proc/{pid}/environ", "rb") as fh:
            for entry in fh.read().decode("utf-8", "replace").split("\0"):
                if entry.startswith("RBTV_IGNITE_DATA_ROOT="):
                    root = entry.split("=", 1)[1]
    except OSError:
        return ""
    return os.path.join(root or DAEMON_DATA_ROOT_DEFAULT, "heart.db")


def daemon_exec_identity(cgroup_text=None, db_path=None):
    """`ignite-daemon` when this process IS a live daemon-fired exec; '' otherwise. Never raises.

    Both inputs are injectable so a probe or a self-test can supply REAL measurables against a
    throwaway store WITHOUT this function growing an assertion channel — identity.js's own
    `checkIdentity({cwd, pid})` seam, for identity.js's own reason: a probe supplies measurables,
    it does not supply a claimed name. Nothing in argv and nothing in the environment reaches
    either parameter; the only caller in the tool passes neither."""
    if cgroup_text is None:
        try:
            with open("/proc/self/cgroup", "r", encoding="utf-8") as fh:
                cgroup_text = fh.read()
        except OSError:
            return ""
    unit = daemon_worker_unit(cgroup_text)
    if not unit:
        return ""
    if db_path is None:
        db_path = daemon_heart_db()
    if not db_path or not os.path.exists(db_path):
        return ""
    import sqlite3  # stdlib; imported HERE because only a daemon exec ever reaches this line
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        try:
            # The placeholders are BUILT FROM THE CONSTANT, never hand-counted: a hand-written
            # `IN (?, ?)` silently decouples from `DAEMON_LIVE_TURN_STATUSES`, and because every
            # sqlite error here fails CLOSED, the decoupling shows up as "nobody ever resolves"
            # rather than as an exception. Measured: a mutation that added a third status left the
            # lane inert instead of reddening its own row, which is how this was found.
            placeholders = ",".join("?" * len(DAEMON_LIVE_TURN_STATUSES))
            row = con.execute(
                f"SELECT 1 FROM jobs_log WHERE unit_name = ? AND status IN ({placeholders}) "
                f"LIMIT 1",
                (unit,) + DAEMON_LIVE_TURN_STATUSES).fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return ""
    return DAEMON_IDENTITY if row else ""


def resolve_agent(args, required=True):
    """Who is calling, resolved instead of typed (T1 — F1: identity used to be hand-typed into
    every command and never verified; a sender/recipient reversal recorded leader as the sender
    of another seat's message, and impersonation-by-typo was silent).

    Order: `--as NAME` > `COORD_AGENT` (injected into every launched/renewed seat's
    harness command) > the calling pane's registered roster row > the DAEMON-EXEC lane
    (`daemon_exec_identity`, F16 — see its block above). An explicit `args.agent`
    attribute carries --as semantics — that is the internal API watch.py calls through, and it
    runs outside any pane, so no contradiction can fire there.

    A claimed identity that CONTRADICTS the calling pane's registered agent is REFUSED with the
    registered name shown; `--force` is the deliberate override. Returns '' when identity is
    unresolvable and `required` is False (the `owner` command reads that as "the human")."""
    claimed = (getattr(args, "as_agent", None) or getattr(args, "agent", None) or "").strip()
    source = "--as"
    if not claimed:
        claimed = os.environ.get("COORD_AGENT", "").strip()
        source = "COORD_AGENT"
    pane = detect_pane(getattr(args, "pane", None))
    registered = pane_agent(base_dir(args), pane) if pane else ""
    if claimed:
        if registered and registered != claimed and not getattr(args, "force", False):
            refuse(
                "identity",
                f"you claimed '{claimed}' ({source}), but this pane ({pane}) is "
                f"registered to '{registered}' in the roster.\n"
                f"Run the command without the claim to act as '{registered}', or pass --force "
                f"to override deliberately (leader acting on behalf of a seat).",
                2)
        return claimed
    if registered:
        return registered
    # F16 — the daemon-exec lane, LAST. Every line above already failed to resolve, and what stood
    # at this position was the refusal below, so this can only add an identity where there was
    # none. It is reached with NO arguments: the measurables come from the kernel and from the
    # daemon's own store, never from this call.
    daemon = daemon_exec_identity()
    if daemon:
        return daemon
    if not required:
        return ""
    print(f"error: cannot resolve who you are — no --as NAME, no COORD_AGENT in the environment, "
          f"this pane ({pane or 'not inside tmux'}) has no active roster row, and this process is "
          f"not a live daemon-fired exec.\n"
          f"Check in first: {coord_invocation(args)} checkin <your-agent> \"<what you are working "
          f"on>\" — or pass --as <your-agent>.", file=sys.stderr)
    sys.exit(2)


# ---- Every refusal this file emits names its LAYER (task s12-03, stage-1 §1.4; standing ruling
# R-8, `core-build-run-adjustments/rulings.md`).
#
# THE PROBLEM. A seat that hits a refusal cannot tell whether coord.py's OWN gate refused it or the
# HARNESS's permission classifier did. The two look alike, a bare "refused:" carries nothing that
# separates them, and the seat then sends the run at the wrong fix (W4) — this cost real run-2
# time. The prefix is the fix, and it is shaped so `grep -c 'refused \[coord'` counts them.
#
# THE LAYER IS ASSIGNED BY WHAT THE CHECK READS. That rule is the durable artifact; the site list is
# not. A refusal added tomorrow picks its layer by re-applying it — and `_selftest_checks` refuses
# both a bare `print("refused: …")` (the sweep rots on the next added refusal otherwise: two new
# commands added 12 un-layered sites in a single day) and a layer token outside this tuple.
REFUSAL_LAYERS = (
    "role gate",    # the CALLER's role/identity vs the act
    "identity",     # who the caller resolves to, vs the pane
    "state",        # the run's own recorded state forbids it
    "input",        # the arguments/body are malformed or over a bound
    "environment",  # the process/tmux/filesystem world is wrong
)

# Appended to the ROLE GATE's own refusals — the one layer a seat routinely MISREADS as a harness
# block, because "you may not run this command" is exactly what the classifier also says. Naming
# the layer in the prefix is not enough on its own: the prefix teaches a reader who already knows
# the vocabulary, and this paragraph teaches the one who does not.
ROLE_GATE_LAYER_NOTE = (
    "layer:   this refusal is coord.py's OWN role gate, NOT your harness's permission\n"
    "         classifier. Report it as \"coord role gate refused\" — the two look alike and\n"
    "         a bare \"refused\" sends the run at the wrong fix."
)


def refusal_text(layer, msg):
    """The refusal's TEXT, without the exit — the message-building half of `refuse`.

    Split out for the refusals that are RETURNED rather than printed (`wake`'s newline guard
    returns `(False, text)` and its caller prints it). Without this split that one refusal would be
    the single un-layered refusal in the file, which is precisely the rot the selftest guard exists
    to prevent — and it would be invisible to that guard, because the guard scopes to `print(`.

    The layer is NOT validated here. A ValueError raised while building a refusal would replace a
    refusal with a traceback — worse than the defect. `_selftest_checks` carries the enforcement
    instead, where a wrong token costs a red line and nothing else.
    """
    return "refused [coord " + layer + "]: " + msg


def refuse(layer, msg, code=2):
    """Emit a layered refusal on stderr and exit with `code`.

    ⚠ `code` IS NOT DECORATIVE, and it is passed explicitly at every one of this file's call sites
    rather than defaulted. The sites exit with a MIX of 1 and 2 (the role gate and the identity
    contradiction exit 2; nearly everything else exits 1), and `watch.py`'s `record_undelivered`
    path keys on coord's EXIT CODE, not on this text. Uniformizing the codes would change behaviour
    for it and for every scripted caller.

    ⚠ `_selftest_checks` defines its own local `refuse(fn, **kw)` capture helper, which SHADOWS this
    function inside that one scope. Deliberate: the fixtures called theirs long before this existed,
    and module-level callers are unaffected because they resolve the global at call time.
    """
    print(refusal_text(layer, msg), file=sys.stderr)
    sys.exit(code)


def gate(args, command):
    """Resolve the caller's identity for `command`.

    Formerly a ROLE gate too (an `allow` predicate over the caller's name, plus
    `target`/`self_legal`/`remedy`/`case` for a refusal's wording) — the role check was DELETED
    whole [T2-R10, D24, F-simplicity-7]: coord.py's design now enforces exactly two refusal
    points, the cage envelope (the sandboxed filesystem/process boundary a seat's harness runs
    inside) and the send-time refusal of an owner-ask from a non-designated seat — neither of
    which is a per-verb "who may run this" check. Every verb this file exposes is callable by any
    resolved identity now. `command` is kept as a parameter purely so a call site still reads,
    at the point it resolves who is calling, WHICH verb it is resolving for.

    For a command that also carries the memory gate, use `launch_gates` instead."""
    return resolve_agent(args, required=False)


def launch_gates(args, command, n_seats):
    """The MEMORY gate a spawning command carries. Returns the caller, or exits.

    This used to be TWO gates evaluated together — role AND memory (leader #230), so a role
    refusal never hid the memory verdict. The role half was DELETED whole
    [T2-R10, D24, F-simplicity-7]: coord.py enforces exactly two refusal points now (the cage
    envelope, and the send-time refusal of an owner-ask from a non-designated seat), and neither
    is a per-verb role check — so `launch`, `close`, and `relaunch-pane` no longer refuse on WHO
    is calling. Only the memory floor survives here.

    `--force` carries nothing at this gate (there is nothing left for it to override);
    `--force-memory` is the memory floor's only override, read directly off `args` — the
    `gate_forced`/`GATE_FLAGS` indirection that used to broker this is gone along with the role
    gate it existed to keep separate from [T2-R10, D24, F-simplicity-7]."""
    # ⚠ THE FLOOR IS READ HERE, PER LAUNCH, FROM THE RUN PACKAGE — never held as a constant
    # (task 7.82, `r-floor-single-source`). `floor_why` is not decoration: criterion 8's acceptance
    # is that the gate SAYS WHICH VALUE IT USED AND WHY, so an operator can never be silently
    # overruled by an environment or a stale copy. It is printed on PASS as well as on REFUSAL —
    # a value you only see when you are blocked is one you cannot check while things work.
    caller = resolve_agent(args, required=False)
    floor_mb, floor_why, floor_err = None, None, None
    try:
        floor_mb, floor_why = budget_mod.floor_source(package_dir(args), "refuse", None)
    except budget_mod.FloorUnreadable as exc:
        floor_err = ("budget.json IS declared for this package and could not be read: %s. That is "
                     "NOT the same as no budget being declared, and it is never treated as one — "
                     "a wrong path and an undeclared budget must not look alike." % exc)
    except budget_mod.FloorUndeclared as exc:
        floor_err = ("%s. The floor's one home is the run's budget.json (r-floor-single-source): "
                     "a launch gate may not invent a number, so it refuses instead. Declare "
                     "floors.launch_refuse_mb there, or override this gate with --force-memory and "
                     "say so on the log." % exc)

    mgate = floor_err if floor_err else process.memory_gate(n_seats, process.available_mb(), floor_mb)
    mem_forced = getattr(args, "force_memory", False)
    lines, refused = [], False

    # ⚠⚠ THE PROVENANCE LINES ARE KEPT SEPARATE FROM THE VERDICT LINES, AND THAT IS THE WHOLE
    # POINT. `lines` is printed ONLY on a refusal or an override — so folding the floor in there
    # would make the number visible exactly when a launch is BLOCKED and invisible every time one
    # SUCCEEDS. Task 7.82 criterion 8's acceptance is that the consumer says WHICH VALUE IT USED
    # AND WHY, and "which value did this launch use?" has to be answerable while things work, not
    # only while they do not. Measured: the first version of this code put them in `lines` and its
    # own comment claimed they printed on PASS. They did not.
    provenance = []
    if floor_why:
        provenance.append(f"floor: {floor_why}")
    # ⚠ AND THE SPIKE SAYS WHERE IT CAME FROM TOO. `COORD_SEAT_SPIKE_MB` no longer touches the
    # FLOOR, but it still moves the EFFECTIVE gate at n_seats > 1 (`need` below), so it is a live
    # MECHANISM even on a box where it is set nowhere — and a live mechanism is not a live
    # divergence (#1254, #1380). Criterion 8 is about the mechanism, so the mechanism reports.
    provenance.append(
        "spike: %d MB per seat (%s) — a MEASUREMENT, not a policy number"
        % (process.SEAT_SPIKE_MB, process.SEAT_SPIKE_SOURCE))
    lines.extend(provenance)
    if not mgate:
        lines.append("memory gate: PASS")
    elif mem_forced:
        lines.append(f"memory gate: REFUSED, overridden with --force-memory — {mgate}")
    else:
        lines.append(f"memory gate: REFUSED — {mgate}")
        refused = True
    verdicts = "\n  ".join(lines)
    if refused:
        # s12-03: the HEAD line names the layer. The role half of this refusal is gone
        # [T2-R10, D24, F-simplicity-7], so only the memory gate can refuse here, and the layer is
        # always `environment` (it reads available RAM, i.e. the process world).
        refuse(
            "environment",
            f"`{command}` — {verdicts}\n"
            f"--force-memory carries this gate.\n"
            f"If memory is the refusal, the right move is usually to WAIT for a seat to depart "
            f"rather than override it.",
            2)
    # Nothing refused. The floor and spike this launch actually used are stated even on the happy
    # path (task 7.82 criterion 8) — one line, on stderr, so it never pollutes a piped stdout.
    print(c("gates: " + " · ".join(provenance), C_HINT), file=sys.stderr)
    # Any override that actually carried a gate is announced, so a forced launch
    # is never silent — the WARNING wording is deliberately distinct from `refused:` (#210).
    for line in lines:
        if "overridden" in line:
            print(c(f"WARNING launching anyway: {line}", C_DEAD), file=sys.stderr)
    return caller


# ── W3 · THE STAFF CHAIR (`meta/leader`) ──────────────────────────────────────────────────────
#
# The ON-DEMAND seat a goal's taskforce staffs. It holds NO workflow node and NO checkin /
# checkout: a sitting is spawned when the chair has unread mail and ends when the mail is drained.
# Every silent stall this program closes was a correct signal delivered to an EMPTY chair.
#
# ⚠ THE LIST IS A SEAT-NAME LIST AND NOTHING ELSE. It confers no authority.
#
# ⚠ THE `consultant` ROLE IS DELETED [T2-R17, D-7-ruling] — not "unstaffed", removed. There is no
# workflow that can cast one and no code path that routes to one; a `--type ask` always reaches
# the `leader`. `work-content` / `recovery` survive only as ASK LABELS (what an ask is about),
# never as a chair. Do not reintroduce a second staff chair to "fix" this.
STAFF_SEATS = ("leader",)


def is_staff_seat(name):
    return name in STAFF_SEATS


# D24 (owner, 2026-08-19): a minted `goal-master` must NOT answer READY. It waits to be
# summoned (a goal-channel message or `@rbtv` bot tag — D11) rather than launching itself
# the moment it is materialized. This is a READINESS exclusion only.
#
# ⚠ NOT `STAFF_SEATS`. That tuple is read at four sites (`is_staff_seat`, the staff-mail
# arm, launch admission, `--route` choices). Widening it to buy this one exclusion would
# change staff mail, admission and routing at once. The owner rejected that (D24 option
# (c)). `goal-master` stays out of `STAFF_SEATS`.
SUMMONED_SEATS = ("goal-master",)


def is_summoned_seat(name):
    return name in SUMMONED_SEATS


# THE CONVERSATIONAL CHAIRS — the seats whose PRODUCT IS CONVERSATION (messages, rulings on a
# ledger, an answer to a seat) rather than files at declared paths. Read at ONE site: the D5
# outputs gate in `cmd_checkout`. It confers nothing else.
#
# ⚠ DERIVED, NEVER A THIRD NAME LIST. It is the union of the two tuples above, so a future
# summoned chair or staff chair inherits the exemption with no second place to edit.
#
# ⚠ AND IT WIDENS NEITHER SOURCE, WHICH IS THE WHOLE POINT OF ITS EXISTING. `STAFF_SEATS` is
# read at four sites (`is_staff_seat`, the staff-mail arm, launch admission, `--route` choices)
# — D24 rejected widening it to buy one behaviour. `SUMMONED_SEATS` is worse: the daemon's
# `supervisor/reconcile.js` EXECS THIS MODULE and reads `SUMMONED_SEATS` by that exact name to
# decide who is NEVER OWED. Putting `leader` there would stop reconcile waking the chair
# on its unread mail (its class B) — the chair's only wake term.
#
# ⚠ IT IS A NAME LIST BECAUSE THE DESCRIPTOR CANNOT ANSWER THE QUESTION. `agent_type: staff` is
# carried by 171 live seats, of which two are chairs and the rest are planning workers that
# declare real outputs (measured 2026-08-20). Keying on `agent_type` would exempt that whole
# population and reopen the defect D5 exists to close.
CONVERSATIONAL_CHAIRS = SUMMONED_SEATS + STAFF_SEATS


def is_conversational_chair(name):
    return name in CONVERSATIONAL_CHAIRS


# `is_leader`, `is_leader_or_closer`, `is_authorized_launcher` (the per-verb ROLE PREDICATES),
# and `gate_role_names`/`gate_roles_help`/`gate_roles_desc` (the renderers that turned one of them
# into a gated command's `-h` parenthetical or refusal text) STOOD HERE and are DELETED whole
# [T2-R10, D24, F-simplicity-7]: coord.py enforces exactly two refusal points now — the cage
# envelope and the send-time refusal of an owner-ask from a non-designated seat — and neither is a
# per-verb "who may call this" predicate. `gate()`/`launch_gates()` no longer take a role predicate
# at all, so every one of these renderers lost its only live callers in the same change; a
# renderer with no predicate left to read from is worse than a hand-written string, so it went too
# rather than being left as a landmine for a `pred=` argument nobody can supply anymore. `is_closer`
# survives below — it is read for non-gating purposes (message routing/broadcast scope), never as
# a `gate()`/`launch_gates()` predicate.
def is_closer(name):
    return bool(name) and name.startswith("closer-")


def broadcast_scope(agent, decls=None):
    """Which `to: all` broadcast TYPES reach `agent` (G-20).

    None  = every type — an ordinary seat, unchanged.
    set   = only these types reach it.
    empty = no broadcast reaches it at all.

    A seat's OWN DECLARATION (`broadcast:` in its descriptor) wins over the built-in table below,
    including over the `closer-` prefix: an explicit statement in the one file that defines the
    seat outranks a default inferred from its name. The table stays as the DEFAULT — every package
    that declares nothing behaves exactly as it did — but it is no longer the mechanism, so a seat
    is narrowed by saying so rather than by a future maintainer remembering to add its name here.

    This bounds BROADCAST ONLY. A message addressed to the seat BY NAME, or to a group it belongs
    to, always arrives — the point is to stop the room's conversation from spending a system seat's
    context, never to make a seat unreachable. (The SENDER BOUND is the one cut that may narrow a
    by-name message, and it is refused at `send` so nothing is ever accepted and then dropped.)"""
    declared = (decls or {}).get(agent) or {}
    if "broadcast" in declared:
        return declared["broadcast"]
    if is_closer(agent):
        return frozenset()          # one-shot: co-write memory, harvest, close, depart
    if agent in SPECIAL_CASE_SEATS:
        return frozenset()
    return None


def in_broadcast_scope(agent, mtype, decls=None):
    """Does a broadcast of type `mtype` reach `agent`? (True for every ordinary seat.)"""
    scope = broadcast_scope(agent, decls)
    return True if scope is None else mtype in scope


