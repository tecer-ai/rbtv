# ---- F17 (store row 7.361; G-planner-0804-1501 arm 2) — THE ASSERTED-IDENTITY LAUNCH BOUND ----
#
# THE DEFECT. `--as NAME` is an ASSERTION, and `resolve_agent`'s contradiction check can only fire
# when the calling pane HAS a registered roster row to contradict. With no row there is nothing to
# check the claim against, so a bare `--as leader` simply STOOD and opened panes as the leader.
# That is identity by TYPING, at the one command that
# spends plan budget and puts sessions on the live room. The daemon's own gate
# (`server/seat-identity/identity.js`) was built refusing exactly this: "there is no env var, no
# `--as`, no flag, and no config that can substitute for or override the match".
#
# WHAT IT IS KEYED ON, AND WHAT IT IS DELIBERATELY NOT KEYED ON (leader #3520, scope held):
#   `args.as_agent`  YES — the CLI's `--as` channel, the one an arbitrary process can type.
#   `args.agent`     NO  — the in-process Namespace attribute watch.py and the self-test call
#                          through. It never crosses the CLI parser, so it is not a channel an
#                          external caller reaches; keying on it would refuse the internal API.
#   `COORD_AGENT`    NO  — injected BY this tool into every launched seat's own harness command.
#   the F16 lane     NO  — `daemon_exec_identity` resolves from kernel measurables, never a claim,
#                          and it is THIS BOUND'S KEY (`gate-key-declaration.csv` K1): the bound
#                          must leave the path F16 establishes untouched, or the gate has captured
#                          its own key (`r-gate-ships-with-its-own-key`).
#
# IT VERIFIES STATE, NEVER SPELLING. A fabricated name and a real-but-unrelated one take the SAME
# branch, because the test is "does a roster row corroborate this claim", not "does this string
# look like a seat". A bound that only rejected malformed strings would have verified nothing.
#
# `--dry-run` IS ADMITTED, and that is not a hole: a dry run opens no pane, writes no surface and
# spends no budget, so there is nothing for an uncorroborated claim to spend. It is also the
# remedy the refusal offers, which is why it must stay open.
#
# `--force` DOES NOT CARRY IT. `--force` carries the ROLE gate and nothing else
# (`p-override-split-is-safety-critical`); re-attaching a second gate to it is barred outright, and
# an identity that could be forced would be an assertion again by another spelling.
CARRIER_UNIT_PREFIX = "rbtv-worker-"


def carrier_self_session(cgroup_text=None):
    """The session id THIS PROCESS can prove is its own, or '' — D43's corroborator.

    ⚠ IDENTITY, NEVER LIVENESS [T2-R8, T4-R8]. spec-supervisor §6 retires the cgroup carrier as a
    liveness predicate and keeps it as exactly this: the answer to "who am I", minted by the daemon
    at launch, which is why token minting stays untouched. It says nothing about whether any OTHER
    sitting is running — that question is `liveness.sitting_alive`, on the supervisor registry. A
    caller reading a carrier's presence as a heartbeat is reading one of the three predicates the
    redesign collapsed.

    `spawn/carrier.js` mints one transient systemd unit per daemon-launched session, named
    `rbtv-worker-<sessionId>`, and that sessionId is the `session-id` of the `sessions.csv` row
    the daemon wrote for THIS session (the heart.db invariant `unit_name ==
    'rbtv-worker-' || session_id` holds on 100% of rows — measured 2026-08-21). The paneless
    check-in therefore registers the roster `sid:` token FROM THIS FUNCTION (F-6, 2026-08-21) —
    not from whichever open row `sessions_open_ids` selects: selecting by last-open-row bound the
    roster to a stale 08-18 row on 2026-08-20 and broke this very lane. The cgroup line is
    kernel-maintained: no env var, flag or config sets it, which is the whole reason F16 keys on
    it. So this is the paneless twin of "the pane id tmux says you are in".

    Reuses `daemon_worker_unit` rather than re-deriving the pattern — one regex, one anchor. The
    parameter exists for the SELF-TEST only, the same seam `daemon_exec_identity` carries and for
    the same reason: a probe supplies measurables, never a name. Nothing in argv and nothing in
    the environment reaches it; the only caller in the tool passes nothing. Fails closed on every
    unreadable or unmatched input — no cgroup, no identity.
    """
    if cgroup_text is None:
        try:
            with open("/proc/self/cgroup", "r", encoding="utf-8") as fh:
                cgroup_text = fh.read()
        except OSError:
            return ""
    unit = daemon_worker_unit(cgroup_text)
    if not unit.startswith(CARRIER_UNIT_PREFIX):
        return ""          # fails closed if the regex above ever stops carrying this prefix
    return unit[len(CARRIER_UNIT_PREFIX):]


def asserted_launch_claim(args):
    """The `--as` claim no roster row corroborates, with the pane it was made from — or ('', pane).

    Reads only STATE: the claim's presence, and whether the calling pane carries an ACTIVE roster
    row. A pane that IS registered needs no bound here — a matching claim is corroborated and a
    contradicting one is already refused by `resolve_agent`.

    ⚠ `register=False` IS LOAD-BEARING. Resolving a package normally (re-)registers the run tag,
    which is a WRITE — and a guard whose whole claim is "it refused and acted on nothing" must not
    have written a registry entry first (`cmd_lifecycle_exec`'s guard 2 makes the same point in the
    same words)."""
    claim = (getattr(args, "as_agent", None) or "").strip()
    if not claim:
        return "", ""
    pane = detect_pane(getattr(args, "pane", None))
    if pane and pane_agent(base_dir(args, register=False), pane):
        return "", pane
    # ---- D43 (owner, 2026-08-20) — THE PANELESS CORROBORATION LANE ---------------------------
    # THE DEFECT D43 NAMES. A headless/caged leader has no TMUX_PANE, so the branch above can
    # never fire and `--rerun` — the D42 instrument built FOR the leader chair — was refused at
    # the one identity that holds the verb. Measured: meet's leader, checked in normally at
    # 19:45Z holding roster row `sid:c22b6807-…`, refused.
    #
    # WHAT IT CORROBORATES AGAINST, and why it is not a name lookup. D43 refuses "some active
    # `sid:` row bears this name" outright — that is G-111 impersonation by another spelling.
    # This lane asks the OPPOSITE question: `carrier_self_session` reads THIS PROCESS's OWN
    # `/proc/self/cgroup` and recovers the session id of the daemon-minted transient unit it is
    # running inside (`spawn/carrier.js` mints `rbtv-worker-<sessionId>`, and that sessionId IS
    # the `session-id` cell of the seat's `sessions.csv` row — measured 2026-08-20). The roster
    # is then keyed ON THAT TOKEN, exactly as `pane_agent` is keyed on a pane id: it answers
    # "which seat is THIS session registered as", and the claim is checked against the answer.
    # A caller cannot type its cgroup, and the token never crosses argv or the environment —
    # `carrier_self_session()` is called with no arguments, F16's `daemon_exec_identity` seam.
    #
    # ⚠ THE COMPARISON TO `claim` IS LOAD-BEARING AND IS *NOT* SYMMETRIC WITH THE PANE BRANCH
    # ABOVE. The pane branch may return corroborated for ANY registered row because
    # `resolve_agent` refuses a CONTRADICTING claim right after — but that contradiction check
    # reads `pane_agent(base, pane) if pane else ""`, and a paneless caller has no `pane`, so it
    # resolves to '' and fires on nothing. Nothing downstream would catch a mismatch here, so
    # this lane must be the thing that does.
    #
    # RESIDUAL, recorded rather than glossed (the same caveat F16 records about link 1): a
    # process that can run `systemd-run --user --unit=rbtv-worker-<sid>` could wear a unit name.
    # It would have to name the EXACT session id of the target's currently-OPEN roster row, and
    # anyone holding that capability can already spawn under the daemon's own scope. It is not a
    # new hole and it is strictly narrower than the `--pane %N` override the branch above accepts.
    sid, seat = carrier_corroborated_seat(args)
    if sid and seat == claim:
        return "", SID_PANE_PREFIX + sid
    return claim, (SID_PANE_PREFIX + sid if (sid and not pane) else pane)


def carrier_corroborated_seat(args):
    """(sid, seat) — the session id THIS PROCESS can prove is its own, and the seat name the
    roster registers AGAINST THAT SESSION. D43's lane, factored out as ONE call.

    ('', '') when this process is not running inside a daemon-minted carrier unit — the ordinary
    caged-seat and console cases, and the reason `base_dir` is reached only past that test: a
    caller with no carrier unit is answered without resolving (or registering) any package.
    (sid, '') when it IS inside one but no ACTIVE roster row carries the token.

    ⚠ ONE CORROBORATION, SHARED CALLERS. F17's `asserted_launch_claim` above and
    `_secret_add_authority` both read this rather than keeping their own copy of the predicate — a
    second copy is how two callers drift apart. (The staff-claim corroboration gate that used to be
    a third caller here was deleted [T2-R10, D24, F-simplicity-7]; a mismatched `--as` is now an
    ordinary input error, not a security refusal.)

    `register=False` is load-bearing for the reason `asserted_launch_claim` records: a guard whose
    whole claim is "it refused and acted on nothing" must not have written a registry entry first.
    """
    sid = carrier_self_session()
    if not sid:
        return "", ""
    return sid, pane_agent(base_dir(args, register=False), SID_PANE_PREFIX + sid)


# THE REFUSAL NAMES ALL THREE WAYS OUT, and that is a requirement rather than courtesy (leader
# #3520): a pane can hold a LIVE process BEFORE its roster row exists — measured on this run,
# master-path-wirer mid-boot in %82 on 2026-07-30 — and refusing that pane's `--as` is CORRECT,
# because check-in is the REGISTERING act and does not travel over `--as`. A caller in that state
# who is only told "no" has no way to tell a bug from a missing step, and that is where this run
# loses hours.
ASSERTED_LAUNCH_REFUSAL = (
    "you passed `--as {claim}` and NOTHING CORROBORATES IT: {pane_state}. `launch` opens panes and "
    "spends plan budget on the strength of who you are, and the identity contradiction check can "
    "only fire against a registered roster row — with no row, the claim simply stands. So this is "
    "identity by typing, and it is refused at the one command where that buys pane-opening "
    "authority.\n"
    "Corroborate it, any of three ways:\n"
    "  1. CHECK IN from this pane first, then re-run with no `--as` at all:\n"
    "     {invocation} checkin {claim} \"<what you are working on>\"\n"
    "     (check-in is the REGISTERING act — it does not travel over `--as`. A pane holding a live "
    "process before its roster row exists lands exactly here, and lands here correctly.)\n"
    "  2. Run it from the pane already registered to '{claim}', with no `--as`.\n"
    "  3. Add `--dry-run` to see what the launch would do — it opens nothing and spends nothing, "
    "so it is admitted on the claim alone.\n"
    "`--force` does NOT carry this bound: it carries the role gate and nothing else.")


def asserted_launch_pane_state(pane):
    """The `{pane_state}` clause of the refusal — WHAT was checked and came back empty.

    Three states, because D43 added a third: a real pane with no row, a self-provable PANELESS
    session whose roster row does not name the claim, and nothing at all. A caller told only
    "no" cannot tell a bug from a missing step, which is the whole reason this refusal names
    states rather than saying `--as` was rejected."""
    if not pane:
        return ("this process is not inside any tmux pane, and its own cgroup names no "
                "daemon-minted session either, so there is no roster row to check it against at "
                "all")
    if pane.startswith(SID_PANE_PREFIX):
        return (f"this process's OWN session ({pane}) carries no ACTIVE roster row under that "
                f"claim — a paneless caller is corroborated only when the roster row registered "
                f"against ITS OWN session id names the seat it is claiming")
    return f"this pane ({pane}) carries NO active roster row"



